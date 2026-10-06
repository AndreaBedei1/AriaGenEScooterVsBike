"""Report assembly: deterministic tables/JSON plus separate run metadata.

``report.json`` and every CSV in ``tables/`` are deterministic for a given
input and configuration (no timestamps, host names or absolute paths), so two
runs can be compared byte by byte. Non-deterministic metadata (creation time,
library versions, platform) are written to ``run_info.json``.
"""

from __future__ import annotations

import datetime as dt
import platform
import sys
from importlib import metadata
from pathlib import Path

import pandas as pd

from ariagen_escooter import __version__
from ariagen_escooter.io import write_csv, write_json

SYNTHETIC_NOTICE = "SYNTHETIC / TEST DATA - not experimental results"

CORE_PACKAGES = ("numpy", "pandas", "scipy", "pydantic", "PyYAML", "matplotlib")
OPTIONAL_PACKAGES = ("projectaria-tools", "torch", "torchvision", "transformers", "opencv-python-headless", "pytest")


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def run_info() -> dict[str, object]:
    """Non-deterministic run metadata (kept out of report.json on purpose)."""
    return {
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "package_version": __version__,
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "packages": {name: package_version(name) for name in CORE_PACKAGES},
    }


def write_tables(tables: dict[str, pd.DataFrame | None], out_dir: Path, float_decimals: int) -> dict[str, str]:
    """Write each non-empty table as CSV; return {name: relative path}."""
    written: dict[str, str] = {}
    for name, df in tables.items():
        if df is None:
            continue
        path = write_csv(df, out_dir / "tables" / f"{name}.csv", float_decimals)
        written[name] = path.relative_to(out_dir).as_posix()
    return written


def write_report(report: dict[str, object], out_dir: Path, float_decimals: int) -> Path:
    return write_json(report, out_dir / "report.json", float_decimals)


def ids_frame(n: int, ids: dict[str, object]) -> pd.DataFrame:
    """Constant identifier/covariate columns to prepend to per-window tables."""
    return pd.DataFrame({key: [value] * n for key, value in ids.items()})


def with_ids(df: pd.DataFrame, ids: dict[str, object]) -> pd.DataFrame:
    if df is None:
        return df
    return pd.concat([ids_frame(len(df), ids), df.reset_index(drop=True)], axis=1)
