"""Small, deterministic file I/O helpers (tables, YAML, JSON, hashes).

Outputs are written byte-for-byte reproducibly: fixed float precision, ``\\n``
line endings, UTF-8, no timestamps inside analysis outputs. Run metadata that
is intrinsically non-deterministic (creation time, library versions) goes to a
separate ``run_info.json``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

TABLE_SUFFIXES = (".csv", ".csv.gz", ".parquet")


def find_table(directory: Path, stem: str) -> Path | None:
    """Return ``directory/stem`` with the first existing supported suffix, else None."""
    for suffix in TABLE_SUFFIXES:
        candidate = directory / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def read_table(path: Path) -> pd.DataFrame:
    """Read a CSV (optionally gzipped) or Parquet table."""
    name = path.name.lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(path)  # requires pyarrow (not a core dependency)
    if name.endswith(".csv") or name.endswith(".csv.gz"):
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path.name}")


def write_csv(df: pd.DataFrame, path: Path, float_decimals: int = 6) -> Path:
    """Write a CSV deterministically (fixed precision, LF line endings)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format=f"%.{float_decimals}f", lineterminator="\n")
    return path


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(data: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(to_builtin(data), sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def to_builtin(value: Any, float_decimals: int | None = None) -> Any:
    """Convert numpy/pandas/Path objects to JSON/YAML-safe builtins.

    NaN and infinities become ``None`` (JSON has no NaN). Floats are rounded
    when ``float_decimals`` is given, which keeps reports compact and stable.
    """
    if isinstance(value, Mapping):
        return {str(k): to_builtin(v, float_decimals) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v, float_decimals) for v in value]
    if isinstance(value, np.ndarray):
        return [to_builtin(v, float_decimals) for v in value.tolist()]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return round(number, float_decimals) if float_decimals is not None else number
    if value is None or isinstance(value, str):
        return value
    if value is pd.NA or value is pd.NaT:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_json(data: Any, path: Path, float_decimals: int | None = 6) -> Path:
    """Write JSON deterministically (UTF-8, 2-space indent, LF, NaN -> null)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(to_builtin(data, float_decimals), indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
