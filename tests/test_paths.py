"""Path portability: no absolute paths, relative '/'-separated paths, env overrides."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ariagen_escooter.config import ConfigError, find_project_root, is_absolute_any, load_config, portable_path
from ariagen_escooter.io import read_yaml

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".md", ".ps1", ".sh", ".csv", ".json", ".cfg", ".txt"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "raw", "interim", "processed", "public"}
# Built from pieces so that this file does not match itself.
ABSOLUTE_PATTERNS = [
    re.compile(r"\b[A-Za-z]:" + r"[\\/](?:Users|Andrea|home|Documents|Desktop)", re.IGNORECASE),
    re.compile(r"(?<![\w.])/" + r"home/[a-z_][\w.-]*/", re.IGNORECASE),
    re.compile(r"(?<![\w.])/" + r"Users/[A-Za-z][\w.-]*/"),
]


def _repo_text_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def test_no_hardcoded_absolute_paths(project_root: Path) -> None:
    offenders = []
    for path in _repo_text_files(project_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in ABSOLUTE_PATTERNS:
            match = pattern.search(text)
            if match:
                offenders.append(f"{path.relative_to(project_root).as_posix()}: {match.group(0)!r}")
    assert not offenders, "absolute user paths found:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    "value", ["C:\\data\\x.vrs", "C:/data/x.vrs", "/srv/data/x.vrs", "\\\\server\\share\\x.vrs", "D:x.vrs", "/x"]
)
def test_absolute_paths_are_rejected(tmp_path: Path, value: str) -> None:
    assert is_absolute_any(value)
    with pytest.raises(ConfigError):
        portable_path(tmp_path, value)


def test_relative_paths_are_portable(tmp_path: Path) -> None:
    assert portable_path(tmp_path, "rec/streams/gaze.csv") == tmp_path / "rec" / "streams" / "gaze.csv"
    # Windows-edited manifests with backslashes still work on Linux
    assert portable_path(tmp_path, "rec\\streams\\gaze.csv") == tmp_path / "rec" / "streams" / "gaze.csv"


def test_project_root_found_from_nested_folder(project_root: Path) -> None:
    nested = project_root / "src" / "ariagen_escooter"
    assert find_project_root(nested) == project_root


def test_data_root_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, project_root: Path) -> None:
    monkeypatch.setenv("ARIAGEN_DATA_ROOT", str(tmp_path))
    cfg = load_config(project_root=project_root)
    assert cfg.data_root == tmp_path
    monkeypatch.delenv("ARIAGEN_DATA_ROOT")
    assert load_config(project_root=project_root).data_root == project_root / "data"


def test_default_config_paths_are_relative(project_root: Path) -> None:
    data = read_yaml(project_root / "configs" / "default.yaml")
    for key in ("data_root", "taxonomy_file"):
        assert not is_absolute_any(data["paths"][key])
    assert not is_absolute_any(data["segmentation"]["label_maps_file"])


def test_manifest_file_paths_are_relative(synthetic_session: Path, project_root: Path) -> None:
    for manifest in [synthetic_session / "manifest.yaml", project_root / "configs" / "example_session.yaml"]:
        data = read_yaml(manifest)
        for rec in data["recordings"]:
            for value in (rec.get("files") or {}).values():
                if value:
                    assert not is_absolute_any(value), f"{manifest.name}: {value}"
