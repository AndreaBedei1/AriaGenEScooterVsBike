"""Canonical stream and annotation schemas, coercion and timestamp validation.

Every source (Aria VRS, MPS outputs, external GPS, synthetic generator) is
converted to the same small set of tables. All timestamps are ``t_ns``:
int64 nanoseconds in the **device clock** of the recording (Aria DEVICE_TIME).
Streams are optional: the pipeline adapts to what is available.

The column definitions below are the single source of truth; the tables in
``docs/data_schema.md`` are generated from them (``ariagen-escooter schema``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

ColumnKind = Literal["int", "float", "bool", "str"]
IssueLevel = Literal["error", "warning", "info"]

NS_PER_S = 1_000_000_000


@dataclass(frozen=True)
class Issue:
    """A validation finding. Errors block processing, warnings are reported."""

    level: IssueLevel
    code: str
    message: str
    where: str = ""

    def __str__(self) -> str:
        location = f"[{self.where}] " if self.where else ""
        return f"{self.level.upper():7s} {location}{self.code}: {self.message}"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: ColumnKind
    unit: str
    description: str
    required: bool = True


@dataclass(frozen=True)
class TableSpec:
    name: str
    filename_stem: str
    description: str
    columns: tuple[ColumnSpec, ...]
    time_column: str | None = "t_ns"

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns if c.required)

    def column(self, name: str) -> ColumnSpec:
        for col in self.columns:
            if col.name == name:
                return col
        raise KeyError(name)


def _c(name: str, kind: ColumnKind, unit: str, description: str, required: bool = True) -> ColumnSpec:
    return ColumnSpec(name, kind, unit, description, required)


T_NS = _c("t_ns", "int", "ns", "Timestamp in the device clock (Aria DEVICE_TIME).")
# Optional tracking-status columns of pose streams (kept for quality control:
# invalid samples are written with valid = false instead of being dropped).
POSE_STATUS_COLUMNS = (
    _c("valid", "bool", "-", "Sample usable (VIO: status VALID and pose quality GOOD).", required=False),
    _c("vio_status", "str", "-", "VIO status as reported (VALID, FILTER_NOT_INITIALIZED, INVALID).", required=False),
    _c("tracking_quality", "str", "-", "VIO pose quality as reported (GOOD, BAD, ...).", required=False),
    _c("visual_tracking_quality", "str", "-", "VIO visual tracking quality, if reported.", required=False),
    _c("tracking_session", "str", "-", "VIO session id; a change marks a tracking reset.", required=False),
)

STREAM_SPECS: dict[str, TableSpec] = {
    "frames": TableSpec(
        "frames",
        "frames",
        "Index of RGB frames (pixels are stored elsewhere; only timing/size here).",
        (
            T_NS,
            _c("frame_index", "int", "-", "Frame number within the recording (0-based)."),
            _c("width_px", "int", "px", "Full-resolution image width.", required=False),
            _c("height_px", "int", "px", "Full-resolution image height.", required=False),
        ),
    ),
    "gaze": TableSpec(
        "gaze",
        "gaze",
        "Eye gaze (combined/cyclopean), eye-in-head angles in the CPF frame and "
        "optional projection into the RGB image.",
        (
            T_NS,
            _c("valid", "bool", "-", "Tracking valid according to the source (False = no usable gaze)."),
            _c("yaw_rad", "float", "rad", "Gaze yaw in CPF; positive = towards the wearer's left."),
            _c("pitch_rad", "float", "rad", "Gaze pitch in CPF; positive = up."),
            _c(
                "u_px",
                "float",
                "px",
                "Gaze point column in the full-resolution RGB image "
                "(projectaria_tools convention: integers at pixel centres).",
                required=False,
            ),
            _c("v_px", "float", "px", "Gaze point row in the full-resolution RGB image.", required=False),
            _c("confidence", "float", "0-1", "Source-provided confidence, if any.", required=False),
            _c(
                "depth_m",
                "float",
                "m",
                "Vergence-based gaze depth, if provided (unreliable at distance).",
                required=False,
            ),
            _c("spatial_point_valid", "bool", "-", "3-D (vergence) gaze point valid (Aria).", required=False),
            _c("left_valid", "bool", "-", "Left-eye gaze valid (Aria vergence block).", required=False),
            _c("right_valid", "bool", "-", "Right-eye gaze valid (Aria vergence block).", required=False),
        ),
    ),
    "imu": TableSpec(
        "imu",
        "imu",
        "Head-mounted IMU (accelerometer + gyroscope) in the stated IMU frame.",
        (
            T_NS,
            _c("accel_x_mps2", "float", "m/s^2", "Specific force, x axis."),
            _c("accel_y_mps2", "float", "m/s^2", "Specific force, y axis."),
            _c("accel_z_mps2", "float", "m/s^2", "Specific force, z axis."),
            _c("gyro_x_radps", "float", "rad/s", "Angular velocity, x axis."),
            _c("gyro_y_radps", "float", "rad/s", "Angular velocity, y axis."),
            _c("gyro_z_radps", "float", "rad/s", "Angular velocity, z axis."),
        ),
    ),
    "pose": TableSpec(
        "pose",
        "pose",
        "Head (CPF) pose in a gravity-aligned local world frame (z up), e.g. from on-device VIO or MPS SLAM.",
        (
            T_NS,
            _c("x_m", "float", "m", "Position x (horizontal)."),
            _c("y_m", "float", "m", "Position y (horizontal)."),
            _c("z_m", "float", "m", "Position z (up)."),
            _c("qw", "float", "-", "Orientation quaternion w (world <- CPF).", required=False),
            _c("qx", "float", "-", "Orientation quaternion x.", required=False),
            _c("qy", "float", "-", "Orientation quaternion y.", required=False),
            _c("qz", "float", "-", "Orientation quaternion z.", required=False),
            _c("quality", "float", "0-1", "Source quality indicator, if any.", required=False),
            *POSE_STATUS_COLUMNS,
        ),
    ),
    "pose_hf": TableSpec(
        "pose_hf",
        "pose_hf",
        "High-frequency head pose (Aria on-device VIO at ~800 Hz = IMU pre-integration on top of the "
        "10 Hz VIO, NOT independent visual estimates), resampled by nearest sample to a configured rate.",
        (
            T_NS,
            _c("x_m", "float", "m", "Position x (horizontal)."),
            _c("y_m", "float", "m", "Position y (horizontal)."),
            _c("z_m", "float", "m", "Position z (up)."),
            _c("qw", "float", "-", "Orientation quaternion w (world <- CPF).", required=False),
            _c("qx", "float", "-", "Orientation quaternion x.", required=False),
            _c("qy", "float", "-", "Orientation quaternion y.", required=False),
            _c("qz", "float", "-", "Orientation quaternion z.", required=False),
            _c("quality", "float", "0-1", "quality_score of the high-frequency VIO sample.", required=False),
            *POSE_STATUS_COLUMNS,
        ),
    ),
    "hands": TableSpec(
        "hands",
        "hands",
        "On-device hand tracking: per hand presence, confidence, wrist and palm positions in the CPF frame "
        "(x left, y up, z forward). Absent = not detected (occlusion, out of view, tracking loss); it is never "
        "evidence that the hand left the handlebar.",
        (
            T_NS,
            *(
                col
                for side in ("left", "right")
                for col in (
                    _c(f"{side}_present", "bool", "-", f"{side.capitalize()} hand detected by the tracker."),
                    _c(f"{side}_confidence", "float", "0-1", "Tracker confidence (empty if absent).", required=False),
                    _c(f"{side}_wrist_x_m", "float", "m", "Wrist position x (CPF).", required=False),
                    _c(f"{side}_wrist_y_m", "float", "m", "Wrist position y (CPF).", required=False),
                    _c(f"{side}_wrist_z_m", "float", "m", "Wrist position z (CPF).", required=False),
                    _c(f"{side}_palm_x_m", "float", "m", "Palm centre x (CPF).", required=False),
                    _c(f"{side}_palm_y_m", "float", "m", "Palm centre y (CPF).", required=False),
                    _c(f"{side}_palm_z_m", "float", "m", "Palm centre z (CPF).", required=False),
                )
            ),
        ),
    ),
    "gps": TableSpec(
        "gps",
        "gps",
        "GNSS fixes (glasses, companion phone or external logger) mapped to device time.",
        (
            T_NS,
            _c("lat_deg", "float", "deg", "WGS84 latitude."),
            _c("lon_deg", "float", "deg", "WGS84 longitude."),
            _c("alt_m", "float", "m", "Altitude.", required=False),
            _c("accuracy_m", "float", "m", "Horizontal accuracy reported by the receiver.", required=False),
            _c("speed_mps", "float", "m/s", "Receiver speed (Doppler), if available.", required=False),
            _c("vertical_accuracy_m", "float", "m", "Vertical accuracy reported by the receiver.", required=False),
        ),
    ),
}

ANNOTATION_SPECS: dict[str, TableSpec] = {
    "segments": TableSpec(
        "segments",
        "segments",
        "Route segments: non-overlapping, semantically homogeneous stretches of the ride.",
        (
            _c("segment_id", "str", "-", "Unique id, e.g. <recording_id>_SEG001."),
            _c("t_start_ns", "int", "ns", "Segment start (device clock)."),
            _c("t_end_ns", "int", "ns", "Segment end (device clock), > start."),
            _c("infrastructure_class", "str", "-", "One of taxonomy.infrastructure_classes."),
            _c(
                "route_segment_id",
                "str",
                "-",
                "Id of the physical route segment (docs/route/route_segments.csv) for comparisons of the same "
                "place across rides and vehicles.",
                required=False,
            ),
            _c("source", "str", "-", "manual | map_matching | synthetic | ..."),
            _c("annotator", "str", "-", "Pseudonymous annotator code (never a full name).", required=False),
            _c("notes", "str", "-", "Free text (no personal data).", required=False),
        ),
        time_column=None,
    ),
    "events": TableSpec(
        "events",
        "events",
        "Events/interactions: intervals that may overlap each other and any segment.",
        (
            _c("event_id", "str", "-", "Unique id, e.g. <recording_id>_EV001."),
            _c("t_start_ns", "int", "ns", "Event start (device clock)."),
            _c("t_end_ns", "int", "ns", "Event end (device clock), > start."),
            _c("t_reference_ns", "int", "ns", "Reference instant, e.g. closest approach (optional).", required=False),
            _c("event_type", "str", "-", "One of taxonomy.event_types."),
            _c("tags", "str", "-", "Extra event types, ';'-separated (e.g. overtaking).", required=False),
            _c(
                "target_class", "str", "-", "Semantic class of the interaction target (for first gaze).", required=False
            ),
            _c("target_instance_id", "int", "-", "Instance/track id of the target, if known.", required=False),
            _c("source", "str", "-", "manual | synthetic | detector | ..."),
            _c("annotator", "str", "-", "Pseudonymous annotator code.", required=False),
            _c("notes", "str", "-", "Free text (no personal data).", required=False),
        ),
        time_column=None,
    ),
}


def coerce_table(df: pd.DataFrame, spec: TableSpec) -> tuple[pd.DataFrame, list[Issue]]:
    """Check required columns and coerce known columns to their declared kinds.

    Unknown extra columns are kept (sources may carry additional fields).
    Integer columns with missing values are returned as float (NaN) only for
    optional columns; missing values in required integer columns are errors.
    """
    issues: list[Issue] = []
    missing = [c for c in spec.required_columns if c not in df.columns]
    if missing:
        issues.append(Issue("error", "missing_columns", f"missing required columns {missing}", spec.name))
        return df, issues
    out = df.copy()
    for col in spec.columns:
        if col.name not in out.columns:
            continue
        series = out[col.name]
        try:
            if col.kind == "int":
                if series.isna().any():
                    if col.required:
                        issues.append(Issue("error", "missing_values", f"{col.name} has empty cells", spec.name))
                        continue
                    out[col.name] = pd.to_numeric(series, errors="raise").astype("float64")
                else:
                    out[col.name] = pd.to_numeric(series, errors="raise").astype("int64")
            elif col.kind == "float":
                out[col.name] = pd.to_numeric(series, errors="raise").astype("float64")
            elif col.kind == "bool":
                out[col.name] = _to_bool(series)
            else:
                out[col.name] = series.astype("string").fillna("").astype(str)
        except (ValueError, TypeError) as exc:
            issues.append(Issue("error", "bad_dtype", f"{col.name}: {exc}", spec.name))
    return out, issues


def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    mapping = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
    lowered = series.astype(str).str.strip().str.lower()
    unknown = sorted(set(lowered) - set(mapping))
    if unknown:
        raise ValueError(f"cannot interpret {unknown[:5]} as booleans")
    return lowered.map(mapping).astype(bool)


@dataclass
class TimestampReport:
    """Quality summary of a timestamp vector."""

    stream: str
    n_samples: int
    start_ns: int | None
    end_ns: int | None
    duration_s: float
    median_dt_s: float | None
    estimated_rate_hz: float | None
    n_non_monotonic: int
    n_duplicates: int
    n_gaps: int
    max_gap_s: float | None
    gaps: list[dict[str, float]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    def as_dict(self) -> dict[str, object]:
        return {
            "stream": self.stream,
            "n_samples": self.n_samples,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "duration_s": self.duration_s,
            "median_dt_s": self.median_dt_s,
            "estimated_rate_hz": self.estimated_rate_hz,
            "n_non_monotonic": self.n_non_monotonic,
            "n_duplicates": self.n_duplicates,
            "n_gaps": self.n_gaps,
            "max_gap_s": self.max_gap_s,
            "gaps": self.gaps,
            "issues": [str(i) for i in self.issues],
        }


def check_timestamps(
    t_ns: np.ndarray, stream: str, gap_factor: float, max_reported_gaps: int, t0_ns: int | None = None
) -> TimestampReport:
    """Validate a timestamp vector: monotonicity, duplicates, gaps, rate.

    Gaps are intervals longer than ``gap_factor`` x the median interval.
    ``t0_ns`` (e.g. recording start) is used to express gap positions in seconds.
    """
    t = np.asarray(t_ns, dtype=np.int64)
    n = int(t.size)
    issues: list[Issue] = []
    if n == 0:
        issues.append(Issue("warning", "empty_stream", "no samples", stream))
        return TimestampReport(stream, 0, None, None, 0.0, None, None, 0, 0, 0, None, [], issues)
    dt = np.diff(t)
    n_non_mono = int(np.sum(dt < 0))
    n_dup = int(np.sum(dt == 0))
    if n_non_mono:
        issues.append(Issue("error", "non_monotonic", f"{n_non_mono} decreasing timestamps", stream))
    if n_dup:
        issues.append(Issue("warning", "duplicates", f"{n_dup} duplicated timestamps", stream))
    positive = dt[dt > 0]
    median_dt = float(np.median(positive)) / NS_PER_S if positive.size else None
    rate = (1.0 / median_dt) if median_dt else None
    gaps: list[dict[str, float]] = []
    n_gaps = 0
    max_gap = float(dt.max()) / NS_PER_S if dt.size else None
    if median_dt:
        gap_idx = np.flatnonzero(dt > gap_factor * median_dt * NS_PER_S)
        n_gaps = int(gap_idx.size)
        origin = t[0] if t0_ns is None else t0_ns
        for i in gap_idx[:max_reported_gaps]:
            gaps.append(
                {
                    "start_rel_s": (int(t[i]) - origin) / NS_PER_S,
                    "duration_s": float(dt[i]) / NS_PER_S,
                }
            )
        if n_gaps:
            issues.append(Issue("warning", "gaps", f"{n_gaps} gaps > {gap_factor:g} x median interval", stream))
    return TimestampReport(
        stream=stream,
        n_samples=n,
        start_ns=int(t[0]),
        end_ns=int(t[-1]),
        duration_s=float(t[-1] - t[0]) / NS_PER_S,
        median_dt_s=median_dt,
        estimated_rate_hz=rate,
        n_non_monotonic=n_non_mono,
        n_duplicates=n_dup,
        n_gaps=n_gaps,
        max_gap_s=max_gap,
        gaps=gaps,
        issues=issues,
    )


def sort_and_deduplicate(df: pd.DataFrame, time_column: str = "t_ns") -> pd.DataFrame:
    """Stable sort by time and drop exact duplicate timestamps (first kept)."""
    out = df.sort_values(time_column, kind="mergesort")
    out = out.drop_duplicates(subset=[time_column], keep="first")
    return out.reset_index(drop=True)


def schema_markdown() -> str:
    """Markdown tables of all canonical schemas (used to generate docs/data_schema.md)."""
    lines: list[str] = []
    for title, specs in (("Streams", STREAM_SPECS), ("Annotations", ANNOTATION_SPECS)):
        lines.append(f"### {title}\n")
        for spec in specs.values():
            lines.append(f"#### `{spec.filename_stem}.csv` - {spec.name}\n")
            lines.append(f"{spec.description}\n")
            lines.append("| Column | Type | Unit | Required | Description |")
            lines.append("|---|---|---|---|---|")
            for col in spec.columns:
                req = "yes" if col.required else "no"
                lines.append(f"| `{col.name}` | {col.kind} | {col.unit} | {req} | {col.description} |")
            lines.append("")
    return "\n".join(lines)
