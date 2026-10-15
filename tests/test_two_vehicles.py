"""Two-vehicle design end to end (SYNTHETIC data): ids, per-vehicle config, quality, contrasts.

The bicycle ride below is the synthetic e-scooter ride relabelled: this test
checks the data plumbing only, not any vehicle difference.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.io import read_json, read_yaml, write_yaml
from ariagen_escooter.pipeline import aggregate, process_session, validate_session


@pytest.fixture(scope="module")
def two_vehicle_run(tmp_path_factory: pytest.TempPathFactory, cfg: LoadedConfig, synthetic_session: Path):
    root = tmp_path_factory.mktemp("two")
    session = root / "SYN001_S01"
    shutil.copytree(synthetic_session, session)
    shutil.copytree(session / "SYN001_S01_R01", session / "SYN001_S01_R02")
    m = read_yaml(session / "manifest.yaml")
    m["equipment"]["vehicles"].append(
        {"vehicle_code": "SYN_BIKE", "vehicle_type": "bicycle", "model": None, "characteristics": {}, "notes": ""}
    )
    rec2 = {**m["recordings"][0], "recording_id": "SYN001_S01_R02"}
    rec2["trial"] = {**rec2["trial"], "vehicle_type": "bicycle", "vehicle_code": "SYN_BIKE", "ride_order": 2}
    m["recordings"].append(rec2)
    write_yaml(m, session / "manifest.yaml")
    out = root / "processed"
    reports = process_session(session, cfg, out, make_plots=False)
    study = root / "study"
    result = aggregate(out, study, synthetic=True)
    return session, out, reports, study, result


def test_validation_accepts_two_vehicle_session(two_vehicle_run, cfg: LoadedConfig) -> None:
    session = two_vehicle_run[0]
    manifest, issues = validate_session(session, cfg)
    assert manifest is not None and not [i for i in issues if i.level == "error"]


def test_vehicle_and_trial_ids_in_every_table(two_vehicle_run) -> None:
    _, out, reports, _, _ = two_vehicle_run
    assert [r["trial"]["vehicle_type"] for r in reports] == ["escooter", "bicycle"]
    assert reports[1]["config"]["vehicle_type"] == "bicycle"
    seg = pd.read_csv(out / "SYN001_S01" / "SYN001_S01_R02" / "tables" / "segment_metrics.csv")
    assert set(seg["vehicle_type"]) == {"bicycle"} and set(seg["ride_order"]) == {2}
    assert {"quality_flag", "q_pose_observed", "q_gaze_observed"} <= set(seg.columns)
    q = read_json(out / "SYN001_S01" / "SYN001_S01_R01" / "quality.json")
    assert {"pose", "gaze", "frames", "imu", "gps"} <= set(q["streams"])
    assert q["nominal_rates_source"] == "observed_median_interval"  # synthetic: no recording profile file
    intervals = pd.read_csv(out / "SYN001_S01" / "SYN001_S01_R01" / "tables" / "quality_intervals.csv")
    assert set(intervals["status"]) <= {"observed", "interpolable", "degraded", "unusable"}
    # the simulated tracking loss of the synthetic ride is visible as a non-observed gaze interval
    assert (intervals[(intervals["stream"] == "gaze")]["status"] != "observed").any()


def test_within_participant_contrasts(two_vehicle_run) -> None:
    _, _, _, study, result = two_vehicle_run
    assert "within_participant_vehicle_contrasts" in result["tables"]
    c = pd.read_csv(study / "within_participant_vehicle_contrasts.csv")
    assert (c["place_key"] == "infrastructure_class").all()
    assert c["speed_mean_mps__diff_escooter_minus_bicycle"].abs().max() < 1e-9  # identical relabelled data
    r = pd.read_csv(study / "rider_vehicle_by_infrastructure.csv")
    assert set(r["vehicle_type"]) == {"escooter", "bicycle"}
