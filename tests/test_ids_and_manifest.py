"""Pseudonymous identifiers and session manifests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ariagen_escooter.config import ConfigError
from ariagen_escooter.io import read_yaml
from ariagen_escooter.session import (
    SessionManifest,
    load_manifest,
    make_participant_id,
    make_recording_id,
    make_session_id,
    manifest_template,
    next_participant_id,
    participant_of,
    validate_participant_id,
    validate_recording_id,
    validate_session_id,
)


def test_id_construction() -> None:
    assert make_participant_id(7) == "P007"
    assert make_participant_id(7, synthetic=True) == "SYN007"
    assert make_session_id("P007", 2) == "P007_S02"
    assert make_recording_id("P007_S02", 1) == "P007_S02_R01"
    assert participant_of("P007_S02_R01") == "P007"


@pytest.mark.parametrize("bad", ["P7", "p001", "P0001", "Mario", "P001 ", "SYN01", ""])
def test_invalid_participant_ids(bad: str) -> None:
    with pytest.raises(ValueError):
        validate_participant_id(bad)


def test_invalid_session_and_recording_ids() -> None:
    for bad in ["P001_S1", "P001-S01", "S01"]:
        with pytest.raises(ValueError):
            validate_session_id(bad)
    for bad in ["P001_S01_R1", "P001_S01", "P001_S01_R01x"]:
        with pytest.raises(ValueError):
            validate_recording_id(bad)


def test_next_participant_id_never_reuses_numbers() -> None:
    assert next_participant_id([]) == "P001"
    assert next_participant_id(["P001", "P004", "SYN009"]) == "P005"
    assert next_participant_id(["P001"], synthetic=True) == "SYN001"


def test_example_and_synthetic_manifests_validate(project_root: Path, synthetic_session: Path) -> None:
    example = load_manifest(project_root / "configs" / "example_session.yaml")
    assert not example.synthetic and example.participant_id.startswith("P")
    synthetic = load_manifest(synthetic_session / "manifest.yaml")
    assert synthetic.synthetic and synthetic.participant_id.startswith("SYN")


def test_manifest_template_validates() -> None:
    manifest = SessionManifest.model_validate(manifest_template("P003", 2, n_recordings=2))
    assert [r.recording_id for r in manifest.recordings] == ["P003_S02_R01", "P003_S02_R02"]


def _base(project_root: Path) -> dict:
    return read_yaml(project_root / "configs" / "example_session.yaml")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(session_id="P002_S01"),  # session of another participant
        lambda d: d.update(synthetic=True),  # synthetic flag with a real P id
        lambda d: d["recordings"][0].update(recording_id="P001_S02_R01"),  # recording of another session
        lambda d: d["recordings"][0]["streams"].update(lidar="available"),  # unknown stream key
        lambda d: d.update(participant_name="x"),  # unknown key (typo or identifier)
        lambda d: d["recordings"][0].update(
            trimming_override={"start_rel_s": 10, "end_rel_s": 5, "reason": "abc", "decided_by": "R1"}
        ),
    ],
)
def test_inconsistent_manifests_are_rejected(project_root: Path, mutate) -> None:
    data = _base(project_root)
    mutate(data)
    with pytest.raises(ValidationError):
        SessionManifest.model_validate(data)


def test_load_manifest_reports_file_name(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text("manifest_version: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="manifest.yaml"):
        load_manifest(path)
