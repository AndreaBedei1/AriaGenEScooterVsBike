"""Ride trimming: raw session -> detected riding interval -> trimmed session.

Removes non-representative periods before departure and after arrival
(adjusting the glasses, talking to the researcher, scooter standing still,
activities after the end of the route).

The detection is a transparent, configurable rule - not a validated model:

1. smoothed speed on a uniform grid (pose/VIO speed, or GPS speed);
2. "moving" where speed > ``speed_threshold_mps``;
3. moving runs shorter than ``min_moving_duration_s`` are discarded;
4. optional (experimental) IMU vibration check per run;
5. riding interval = first-to-last qualifying run (default) or the longest
   block of runs merged across gaps < ``merge_gap_s``;
6. buffers added before/after, clipped to the recording.

A manual override declared in the manifest always wins; the automatic result
is still computed and reported. Raw data are never modified: the result is a
:class:`TrimResult` saved as ``trimming.json`` with all parameters, the reason
and every timestamp used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from ariagen_escooter.config import TrimmingConfig
from ariagen_escooter.session import TrimmingOverride
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.synchronization import find_runs, interpolate_to_grid, make_grid, to_ns
from ariagen_escooter.trajectory import latlon_to_local_xy, odd_window, savgol_nan_aware, speed_profile

TrimMethod = Literal["automatic", "manual_override", "not_trimmed"]


@dataclass
class TrimResult:
    method: TrimMethod
    status: Literal["ok", "warning", "failed"]
    reason: str
    recording_start_ns: int
    recording_end_ns: int
    trim_start_ns: int
    trim_end_ns: int
    detected_start_ns: int | None
    detected_end_ns: int | None
    speed_source: str | None
    parameters: dict[str, object]
    runs: list[dict[str, object]] = field(default_factory=list)
    automatic: dict[str, object] | None = None
    override: dict[str, object] | None = None
    warnings: list[str] = field(default_factory=list)

    def rel(self, t_ns: int | None) -> float | None:
        return None if t_ns is None else (t_ns - self.recording_start_ns) / NS_PER_S

    def as_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "status": self.status,
            "reason": self.reason,
            "speed_source": self.speed_source,
            "recording_interval": {
                "start_ns": self.recording_start_ns,
                "end_ns": self.recording_end_ns,
                "duration_s": (self.recording_end_ns - self.recording_start_ns) / NS_PER_S,
            },
            "detected_riding_interval": {
                "start_ns": self.detected_start_ns,
                "end_ns": self.detected_end_ns,
                "start_rel_s": self.rel(self.detected_start_ns),
                "end_rel_s": self.rel(self.detected_end_ns),
            },
            "trimmed_interval": {
                "start_ns": self.trim_start_ns,
                "end_ns": self.trim_end_ns,
                "start_rel_s": self.rel(self.trim_start_ns),
                "end_rel_s": self.rel(self.trim_end_ns),
                "duration_s": (self.trim_end_ns - self.trim_start_ns) / NS_PER_S,
            },
            "removed_before_s": (self.trim_start_ns - self.recording_start_ns) / NS_PER_S,
            "removed_after_s": (self.recording_end_ns - self.trim_end_ns) / NS_PER_S,
            "moving_runs": self.runs,
            "automatic_result": self.automatic,
            "manual_override": self.override,
            "parameters": self.parameters,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class SpeedSignal:
    grid_ns: np.ndarray
    speed_mps: np.ndarray
    source: str


def speed_for_trimming(
    pose: pd.DataFrame | None,
    gps: pd.DataFrame | None,
    cfg: TrimmingConfig,
    *,
    polyorder: int,
    pose_max_gap_s: float,
    gps_max_gap_s: float,
    pose_breaks_ns: np.ndarray | None = None,
) -> SpeedSignal | None:
    """Smoothed speed on the trimming grid from the configured source."""
    order = {"auto": ("pose", "gps"), "pose": ("pose",), "gps": ("gps",)}[cfg.speed_source]
    for source in order:
        if source == "pose" and pose is not None and len(pose) >= 2:
            grid, speed = speed_profile(
                pose["t_ns"].to_numpy(),
                pose["x_m"].to_numpy(),
                pose["y_m"].to_numpy(),
                rate_hz=cfg.grid_rate_hz,
                window_s=cfg.smoothing_window_s,
                polyorder=polyorder,
                max_gap_s=pose_max_gap_s,
                breaks_ns=pose_breaks_ns,
            )
            return SpeedSignal(grid, speed, "pose")
        if source == "gps" and gps is not None and len(gps) >= 2:
            t = gps["t_ns"].to_numpy()
            if "speed_mps" in gps.columns and gps["speed_mps"].notna().mean() > 0.9:
                grid = make_grid(int(t[0]), int(t[-1]), cfg.grid_rate_hz)
                raw = interpolate_to_grid(t, gps["speed_mps"].to_numpy(), grid, int(gps_max_gap_s * NS_PER_S))
                window = odd_window(cfg.smoothing_window_s, cfg.grid_rate_hz, polyorder)
                return SpeedSignal(grid, savgol_nan_aware(raw, window, polyorder), "gps_doppler_speed")
            lat0, lon0 = float(gps["lat_deg"].iloc[0]), float(gps["lon_deg"].iloc[0])
            x, y = latlon_to_local_xy(gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy(), lat0, lon0)
            grid, speed = speed_profile(
                t,
                x,
                y,
                rate_hz=cfg.grid_rate_hz,
                window_s=cfg.smoothing_window_s,
                polyorder=polyorder,
                max_gap_s=gps_max_gap_s,
            )
            return SpeedSignal(grid, speed, "gps_positions")
    return None


def imu_activity(imu: pd.DataFrame, grid_ns: np.ndarray, window_s: float) -> np.ndarray:
    """Rolling std of |acceleration| (centred window) sampled at grid times."""
    t = imu["t_ns"].to_numpy()
    mag = np.sqrt(imu["accel_x_mps2"] ** 2 + imu["accel_y_mps2"] ** 2 + imu["accel_z_mps2"] ** 2)
    dt = np.median(np.diff(t)) / NS_PER_S if len(t) > 1 else np.nan
    if not np.isfinite(dt) or dt <= 0:
        return np.full(grid_ns.shape, np.nan)
    n = max(3, int(round(window_s / dt)))
    rolling = pd.Series(mag.to_numpy()).rolling(n, center=True, min_periods=max(3, n // 2)).std().to_numpy()
    return interpolate_to_grid(t, rolling, grid_ns, int(2 * window_s * NS_PER_S))


def detect_riding_interval(
    signal: SpeedSignal,
    cfg: TrimmingConfig,
    *,
    recording_start_ns: int,
    recording_end_ns: int,
    imu: pd.DataFrame | None = None,
) -> TrimResult:
    """Automatic detection (no override). See module docstring for the rule."""
    params = cfg.model_dump()
    grid, speed = signal.grid_ns, signal.speed_mps
    moving = np.isfinite(speed) & (speed > cfg.speed_threshold_mps)
    dt = 1.0 / cfg.grid_rate_hz
    activity = None
    warnings: list[str] = []
    if cfg.imu_check.enabled:
        if imu is None or imu.empty:
            warnings.append("imu_check enabled but no IMU stream: check skipped")
        else:
            activity = imu_activity(imu, grid, cfg.imu_check.window_s)

    runs: list[dict[str, object]] = []
    kept: list[tuple[int, int]] = []
    for start, end in find_runs(moving):
        duration = (end - start + 1) * dt
        entry: dict[str, object] = {
            "start_rel_s": (int(grid[start]) - recording_start_ns) / NS_PER_S,
            "end_rel_s": (int(grid[end]) - recording_start_ns) / NS_PER_S,
            "duration_s": duration,
            "max_speed_mps": float(np.nanmax(speed[start : end + 1])),
        }
        if duration < cfg.min_moving_duration_s:
            entry.update(kept=False, reason=f"shorter than min_moving_duration_s ({cfg.min_moving_duration_s:g} s)")
        elif activity is not None:
            active = activity[start : end + 1] >= cfg.imu_check.min_accel_std_mps2
            fraction = float(np.mean(active))
            entry["imu_active_fraction"] = fraction
            if fraction < cfg.imu_check.min_active_fraction:
                entry.update(kept=False, reason="IMU activity below threshold (experimental check)")
            else:
                entry.update(kept=True, reason="qualifying run")
                kept.append((int(start), int(end)))
        else:
            entry.update(kept=True, reason="qualifying run")
            kept.append((int(start), int(end)))
        runs.append(entry)

    if not kept:
        return TrimResult(
            method="not_trimmed",
            status="failed",
            reason=(
                f"no movement run with speed > {cfg.speed_threshold_mps:g} m/s lasting "
                f">= {cfg.min_moving_duration_s:g} s; full recording kept (manual override recommended)"
            ),
            recording_start_ns=recording_start_ns,
            recording_end_ns=recording_end_ns,
            trim_start_ns=recording_start_ns,
            trim_end_ns=recording_end_ns,
            detected_start_ns=None,
            detected_end_ns=None,
            speed_source=signal.source,
            parameters=params,
            runs=runs,
            warnings=warnings,
        )

    if cfg.selection == "first_to_last":
        start_idx, end_idx = kept[0][0], kept[-1][1]
        rule = "first to last qualifying run"
    else:
        blocks: list[list[int]] = [[kept[0][0], kept[0][1]]]
        for s, e in kept[1:]:
            if (s - blocks[-1][1]) * dt <= cfg.merge_gap_s:
                blocks[-1][1] = e
            else:
                blocks.append([s, e])
        start_idx, end_idx = max(blocks, key=lambda b: b[1] - b[0])
        rule = f"longest block of runs merged across gaps <= {cfg.merge_gap_s:g} s"

    detected_start, detected_end = int(grid[start_idx]), int(grid[end_idx])
    trim_start = max(recording_start_ns, detected_start - to_ns(cfg.buffer_before_s))
    trim_end = min(recording_end_ns, detected_end + to_ns(cfg.buffer_after_s))
    n_discarded = sum(1 for r in runs if not r["kept"])
    reason = (
        f"riding interval = {rule} (speed > {cfg.speed_threshold_mps:g} m/s from {signal.source} "
        f"for >= {cfg.min_moving_duration_s:g} s); buffers -{cfg.buffer_before_s:g} s/+{cfg.buffer_after_s:g} s; "
        f"{len(kept)} run(s) kept, {n_discarded} discarded"
    )
    return TrimResult(
        method="automatic",
        status="warning" if warnings else "ok",
        reason=reason,
        recording_start_ns=recording_start_ns,
        recording_end_ns=recording_end_ns,
        trim_start_ns=trim_start,
        trim_end_ns=trim_end,
        detected_start_ns=detected_start,
        detected_end_ns=detected_end,
        speed_source=signal.source,
        parameters=params,
        runs=runs,
        warnings=warnings,
    )


def trim_recording(
    cfg: TrimmingConfig,
    *,
    recording_start_ns: int,
    recording_end_ns: int,
    signal: SpeedSignal | None,
    imu: pd.DataFrame | None = None,
    override: TrimmingOverride | None = None,
) -> TrimResult:
    """Full trimming decision: manual override > automatic detection > not trimmed."""
    automatic: TrimResult | None = None
    if cfg.enabled and signal is not None:
        automatic = detect_riding_interval(
            signal, cfg, recording_start_ns=recording_start_ns, recording_end_ns=recording_end_ns, imu=imu
        )

    if override is not None:
        start = recording_start_ns + to_ns(override.start_rel_s)
        end = min(recording_end_ns, recording_start_ns + to_ns(override.end_rel_s))
        warnings = []
        if end <= start:
            raise ValueError("manual trimming override lies outside the recording")
        comparison = None
        if automatic is not None:
            comparison = automatic.as_dict()
            if automatic.method == "automatic":
                d_start = (automatic.trim_start_ns - start) / NS_PER_S
                d_end = (automatic.trim_end_ns - end) / NS_PER_S
                comparison["difference_vs_override_s"] = {"start": d_start, "end": d_end}
        return TrimResult(
            method="manual_override",
            status="ok",
            reason=f"manual override: {override.reason} (decided by {override.decided_by})",
            recording_start_ns=recording_start_ns,
            recording_end_ns=recording_end_ns,
            trim_start_ns=start,
            trim_end_ns=end,
            detected_start_ns=automatic.detected_start_ns if automatic else None,
            detected_end_ns=automatic.detected_end_ns if automatic else None,
            speed_source=automatic.speed_source if automatic else None,
            parameters=cfg.model_dump(),
            runs=automatic.runs if automatic else [],
            automatic=comparison,
            override=override.model_dump(),
            warnings=warnings,
        )

    if automatic is not None:
        return automatic

    reason = "trimming disabled in configuration" if not cfg.enabled else "no speed source (pose or GPS) available"
    return TrimResult(
        method="not_trimmed",
        status="ok" if not cfg.enabled else "failed",
        reason=reason + "; full recording kept",
        recording_start_ns=recording_start_ns,
        recording_end_ns=recording_end_ns,
        trim_start_ns=recording_start_ns,
        trim_end_ns=recording_end_ns,
        detected_start_ns=None,
        detected_end_ns=None,
        speed_source=None,
        parameters=cfg.model_dump(),
        warnings=[] if not cfg.enabled else ["define a manual trimming_override in the manifest"],
    )


def slice_by_time(df: pd.DataFrame | None, start_ns: int, end_ns: int, column: str = "t_ns") -> pd.DataFrame | None:
    """Rows with start <= t <= end (returns a copy; the input is untouched)."""
    if df is None:
        return None
    t = df[column].to_numpy()
    return df.loc[(t >= start_ns) & (t <= end_ns)].reset_index(drop=True)
