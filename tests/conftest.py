"""Shared fixtures. All tests run without Aria hardware or real data."""

from __future__ import annotations

from pathlib import Path

import pytest

from ariagen_escooter.config import LoadedConfig, find_project_root, load_config

PROJECT_ROOT = find_project_root(Path(__file__).parent)
SYNTHETIC_SESSION = PROJECT_ROOT / "data" / "synthetic" / "SYN001_S01"
T0_NS = 12_345_000_000_000  # device-clock origin of the synthetic session


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def cfg() -> LoadedConfig:
    return load_config(project_root=PROJECT_ROOT)


@pytest.fixture(scope="session")
def synthetic_session() -> Path:
    assert (SYNTHETIC_SESSION / "manifest.yaml").is_file(), "committed synthetic session missing"
    return SYNTHETIC_SESSION


@pytest.fixture(scope="session")
def processed_synthetic(tmp_path_factory: pytest.TempPathFactory, cfg: LoadedConfig, synthetic_session: Path):
    """Run the MVP pipeline once on the committed synthetic session."""
    from ariagen_escooter.pipeline import process_session

    out = tmp_path_factory.mktemp("processed")
    reports = process_session(synthetic_session, cfg, out, make_plots=True)
    return out, reports


def rel_s(t_ns: float) -> float:
    return (t_ns - T0_NS) / 1e9
