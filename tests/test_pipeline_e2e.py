"""End-to-end MVP on the committed SYNTHETIC session: correctness vs ground truth,
deterministic outputs, no absolute paths, real/synthetic separation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.pipeline import aggregate, process_session, validate_session
from conftest import rel_s

pytestmark = pytest.mark.slow


def _gt(synthetic_session: Path) -> dict:
    return json.loads((synthetic_session / "ground_truth.json").read_text(encoding="utf-8"))


def _out(processed_synthetic) -> Path:
    root, _ = processed_synthetic
    return root / "SYN001_S01" / "SYN001_S01_R01"


def test_validation_passes(cfg: LoadedConfig, synthetic_session: Path) -> None:
    manifest, issues = validate_session(synthetic_session, cfg)
    assert manifest is not None and manifest.synthetic
    assert not [i for i in issues if i.level == "error"]
    assert any(i.code == "gaps" for i in issues)  # the three dropped frames are reported


def test_report_structure_and_synthetic_notice(processed_synthetic) -> None:
    report = json.loads((_out(processed_synthetic) / "report.json").read_text(encoding="utf-8"))
    assert report["synthetic"] is True and "SYNTHETIC" in report["notice"]
    assert report["status"] in {"ok", "warning"}
    assert set(report["streams_available"]) == {"frames", "gaze", "gps", "imu", "pose"}
    for name in ("segment_metrics", "event_metrics", "approach_metrics", "semantic_gaze", "kinematics"):
        assert (_out(processed_synthetic) / report["outputs"]["tables"][name]).is_file()
    assert (_out(processed_synthetic) / "figures" / "overview.png").stat().st_size > 10_000


def test_trimming_matches_ground_truth(processed_synthetic, synthetic_session: Path) -> None:
    gt = _gt(synthetic_session)["riding"]
    trim = json.loads((_out(processed_synthetic) / "trimming.json").read_text(encoding="utf-8"))
    assert trim["method"] == "automatic"
    assert trim["detected_riding_interval"]["start_rel_s"] == pytest.approx(gt["speed_above_2mps_first_rel_s"], abs=0.3)
    assert trim["detected_riding_interval"]["end_rel_s"] == pytest.approx(gt["speed_above_2mps_last_rel_s"], abs=0.3)
    assert trim["removed_before_s"] > 20 and trim["removed_after_s"] > 10  # pre-ride handling and post-ride removed


def test_gps_clock_offset_recovered(processed_synthetic, synthetic_session: Path) -> None:
    report = json.loads((_out(processed_synthetic) / "report.json").read_text(encoding="utf-8"))
    offset = report["synchronization"]["gps_clock_offset"]
    assert offset["applied"] and offset["reliable"]
    assert offset["offset_s"] == pytest.approx(_gt(synthetic_session)["expected_gps_offset_correction_s"], abs=0.05)


def test_perception_action_matches_ground_truth(processed_synthetic, synthetic_session: Path) -> None:
    gt = _gt(synthetic_session)["events"]
    events = pd.read_csv(_out(processed_synthetic) / "tables" / "event_metrics.csv")
    for _, row in events.iterrows():
        truth = gt[row["event_id"]]
        if truth["first_gaze_rel_s"] is None:
            assert pd.isna(row["t_first_gaze_ns"])
        else:
            # scripted fixation start; small delays come from frame/gaze misalignment during head turns
            assert rel_s(row["t_first_gaze_ns"]) == pytest.approx(truth["first_gaze_rel_s"], abs=0.2), row["event_id"]
        if truth["action_onset_rel_s"] is not None and truth["first_gaze_rel_s"] is not None:
            assert rel_s(row["t_action_onset_ns"]) == pytest.approx(truth["action_onset_rel_s"], abs=0.3), row[
                "event_id"
            ]
    ped = events.set_index("event_id").loc["SYN001_S01_R01_EV001"]
    assert ped["perception_action_latency_s"] == pytest.approx(0.45, abs=0.25)
    assert ped["infrastructure_class_at_reference"] == "protected_cycle_path"
    overtaken = events.set_index("event_id").loc["SYN001_S01_R01_EV005"]
    assert overtaken["visual_anticipation_s"] < 0  # car first seen after it came alongside


def test_segment_table_is_analysis_ready(processed_synthetic) -> None:
    seg = pd.read_csv(_out(processed_synthetic) / "tables" / "segment_metrics.csv")
    for col in (
        "participant_id",
        "session_id",
        "infrastructure_class",
        "speed_mean_mps",
        "forward_share",
        "share_group_pedestrians",
        "gaze_valid_fraction",
        "weather",
    ):
        assert col in seg.columns
    assert seg["infrastructure_class"].tolist() == [
        "protected_cycle_path",
        "crossing",
        "road_shared_with_traffic",
        "roundabout",
        "shared_pedestrian_cycle_path",
    ]
    by_class = seg.set_index("infrastructure_class")
    assert by_class.loc["crossing", "speed_mean_mps"] < by_class.loc["protected_cycle_path", "speed_mean_mps"]
    assert by_class.loc["road_shared_with_traffic", "share_group_vehicles"] > 0


def test_outputs_are_deterministic(
    cfg: LoadedConfig, synthetic_session: Path, processed_synthetic, tmp_path: Path
) -> None:
    process_session(synthetic_session, cfg, tmp_path, make_plots=True)  # same options as the fixture
    first = _out(processed_synthetic)
    second = tmp_path / "SYN001_S01" / "SYN001_S01_R01"
    files = ["report.json", "trimming.json", "effective_config.yaml"] + [
        f"tables/{p.name}" for p in sorted((first / "tables").glob("*.csv"))
    ]
    for name in files:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_outputs_contain_no_absolute_paths(processed_synthetic, project_root: Path) -> None:
    out = _out(processed_synthetic)
    root_variants = {str(project_root), project_root.as_posix(), str(out.parent.parent)}
    for name in ["report.json", "trimming.json", "effective_config.yaml", "run_info.json"]:
        text = (out / name).read_text(encoding="utf-8")
        assert not any(v in text for v in root_variants), name


def test_aggregation_never_mixes_real_and_synthetic(processed_synthetic, tmp_path: Path) -> None:
    root, _ = processed_synthetic
    result = aggregate(root, tmp_path / "study", synthetic=True)
    assert result["tables"]["segment_metrics"]["rows"] == 5
    summary = pd.read_csv(tmp_path / "study" / "rider_by_infrastructure.csv")
    assert set(summary["participant_id"]) == {"SYN001"}
    assert aggregate(root, tmp_path / "real", synthetic=False)["tables"] == {}
