"""Synthetic generator reproducibility and command-line interface."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.cli import main
from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.io import read_yaml
from ariagen_escooter.segmentation import LabelMapStore
from ariagen_escooter.synthetic import generate_session


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory: pytest.TempPathFactory, cfg: LoadedConfig) -> Path:
    return generate_session(tmp_path_factory.mktemp("syn"), taxonomy_names=cfg.taxonomy.semantic_names)


@pytest.mark.slow
def test_committed_synthetic_data_matches_generator(regenerated: Path, synthetic_session: Path) -> None:
    """The committed dataset is exactly what the code generates (tolerant to last-digit float differences)."""
    rec = "SYN001_S01_R01"
    for sub in (
        "streams/frames.csv",
        "streams/gaze.csv",
        "streams/imu.csv",
        "streams/pose.csv",
        "streams/gps.csv",
        "annotations/segments.csv",
        "annotations/events.csv",
    ):
        new = pd.read_csv(regenerated / rec / sub)
        old = pd.read_csv(synthetic_session / rec / sub)
        pd.testing.assert_frame_equal(new, old, check_exact=False, rtol=1e-6, atol=1e-6)
    a = LabelMapStore.load(regenerated / rec / "semantic" / "labels.npz")
    b = LabelMapStore.load(synthetic_session / rec / "semantic" / "labels.npz")
    assert np.mean(a.labels != b.labels) < 1e-4 and a.class_names == b.class_names
    assert read_yaml(regenerated / "manifest.yaml") == read_yaml(synthetic_session / "manifest.yaml")


def test_synthetic_data_is_clearly_marked(synthetic_session: Path) -> None:
    manifest = read_yaml(synthetic_session / "manifest.yaml")
    assert manifest["synthetic"] is True and manifest["participant_id"].startswith("SYN")
    assert "SYNTHETIC / TEST DATA" in (synthetic_session / "README.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in (synthetic_session.parent / "README.md").read_text(encoding="utf-8")


def test_cli_info_and_schema(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["info"]) == 0
    assert "Data root" in capsys.readouterr().out
    assert main(["schema"]) == 0
    assert "`gaze.csv`" in capsys.readouterr().out


def test_cli_new_session(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            ["new-session", "--participant", "P004", "--session", "2", "--root", str(tmp_path),
             "--ride", "escooter:1:1", "--ride", "bicycle:1:2"]
        )
        == 0
    )
    manifest = tmp_path / "P004_S02" / "manifest.yaml"
    assert manifest.is_file() and (tmp_path / "P004_S02" / "P004_S02_R01").is_dir()
    assert (
        main(["new-session", "--participant", "P004", "--session", "2", "--root", str(tmp_path)]) == 1
    )  # no overwrite
    assert main(["new-session", "--next", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "P005_S01" / "manifest.yaml").is_file()
    assert main(["validate", str(tmp_path / "P004_S02")]) == 0  # template is valid (streams still missing)
    # without --ride the vehicle type is a placeholder that validation rejects
    assert main(["validate", str(tmp_path / "P005_S01")]) == 1
    assert main(["new-session", "--participant", "P006", "--ride", "car:1:1", "--root", str(tmp_path)]) == 2


def test_cli_validate_rejects_identifiers(
    tmp_path: Path, synthetic_session: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    session = tmp_path / "SYN001_S01"
    session.mkdir()
    text = (synthetic_session / "manifest.yaml").read_text(encoding="utf-8")
    (session / "manifest.yaml").write_text(
        text.replace("notes: SYNTHETIC", "notes: call +39 333 1234567 SYNTHETIC", 1), encoding="utf-8"
    )
    assert main(["validate", str(session)]) == 1
    assert "phone_like_value" in capsys.readouterr().out


@pytest.mark.slow
def test_cli_run_and_aggregate(tmp_path: Path, synthetic_session: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", str(synthetic_session), "--out", str(tmp_path), "--no-plots"]) == 0
    out = capsys.readouterr().out
    assert "SYNTHETIC" in out and "trimming: automatic" in out
    assert main(["aggregate", "--processed", str(tmp_path), "--synthetic", "--out", str(tmp_path / "study")]) == 0
    assert (tmp_path / "study" / "study_segment_metrics.csv").is_file()
