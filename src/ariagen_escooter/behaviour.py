"""Quantitative riding-behaviour metrics from the kinematics grid.

Only descriptive, quantitative metrics are produced - no subjective labels
("safe", "aggressive", "good rider"...). Riding styles, if any, should emerge
later from data-driven analyses of these metrics.

Inputs are the outputs of :func:`ariagen_escooter.trajectory.compute_kinematics`.
All windows are closed intervals [t0, t1] in device nanoseconds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ariagen_escooter.config import KinematicsConfig
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.synchronization import find_runs

# Numerical guard (not an analysis parameter): sinuosity = path length / chord is
# undefined when start and end points (almost) coincide, e.g. while stopped.
_MIN_CHORD_FOR_SINUOSITY_M = 1.0


def _dt(kin: pd.DataFrame) -> float:
    t = kin["t_ns"].to_numpy()
    return float(np.median(np.diff(t))) / NS_PER_S if len(t) > 1 else float("nan")


def detect_stops(kin: pd.DataFrame, cfg: KinematicsConfig) -> pd.DataFrame:
    """Stops: speed < stop threshold for >= min_stop_duration_s."""
    dt = _dt(kin)
    rows = []
    for start, end in find_runs(kin["stopped"].to_numpy(dtype=bool)):
        duration = (end - start + 1) * dt
        if duration >= cfg.min_stop_duration_s:
            rows.append(
                {
                    "t_start_ns": int(kin["t_ns"].iat[start]),
                    "t_end_ns": int(kin["t_ns"].iat[end]),
                    "duration_s": duration,
                }
            )
    df = pd.DataFrame(rows, columns=["t_start_ns", "t_end_ns", "duration_s"])
    df.insert(0, "stop_id", [f"STOP{i + 1:03d}" for i in range(len(df))])
    return df


def detect_braking_events(kin: pd.DataFrame, cfg: KinematicsConfig) -> pd.DataFrame:
    """Deceleration events (neutral naming): accel <= -threshold for >= min duration.

    The onset is extended backwards while accel <= -onset_threshold; the end is
    extended forwards likewise. Reported: onset, peak deceleration and its time,
    speed at onset/end, speed drop.
    """
    b = cfg.braking
    accel = kin["accel_mps2"].to_numpy()
    speed = kin["speed_mps"].to_numpy()
    t = kin["t_ns"].to_numpy()
    dt = _dt(kin)
    strong = np.isfinite(accel) & (accel <= -b.decel_threshold_mps2)
    mild = np.isfinite(accel) & (accel <= -b.onset_threshold_mps2)
    rows = []
    used_until = -1
    for start, end in find_runs(strong):
        if (end - start + 1) * dt < b.min_duration_s or start <= used_until:
            continue
        onset = start
        while onset - 1 >= 0 and mild[onset - 1]:
            onset -= 1
        stop = end
        while stop + 1 < len(mild) and mild[stop + 1]:
            stop += 1
        used_until = stop
        window = accel[onset : stop + 1]
        peak_rel = int(np.nanargmin(window))
        rows.append(
            {
                "t_onset_ns": int(t[onset]),
                "t_end_ns": int(t[stop]),
                "duration_s": (stop - onset + 1) * dt,
                "peak_decel_mps2": float(window[peak_rel]),
                "t_peak_ns": int(t[onset + peak_rel]),
                "speed_onset_mps": float(speed[onset]),
                "speed_end_mps": float(speed[stop]),
                "speed_drop_mps": float(speed[onset] - speed[stop]),
            }
        )
    cols = [
        "t_onset_ns",
        "t_end_ns",
        "duration_s",
        "peak_decel_mps2",
        "t_peak_ns",
        "speed_onset_mps",
        "speed_end_mps",
        "speed_drop_mps",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df.insert(0, "decel_event_id", [f"DEC{i + 1:03d}" for i in range(len(df))])
    return df


def _nan_stat(values: np.ndarray, fn) -> float:
    v = values[np.isfinite(values)]
    return float(fn(v)) if v.size else float("nan")


def window_metrics(
    kin: pd.DataFrame,
    t0_ns: int,
    t1_ns: int,
    braking: pd.DataFrame,
    stops: pd.DataFrame,
) -> dict[str, float]:
    """Behaviour metrics over a time window (segment, event, approach window...)."""
    t = kin["t_ns"].to_numpy()
    m = (t >= t0_ns) & (t <= t1_ns)
    dt = _dt(kin)
    duration = (t1_ns - t0_ns) / NS_PER_S
    speed = kin["speed_mps"].to_numpy()[m]
    accel = kin["accel_mps2"].to_numpy()[m]
    jerk = kin["jerk_mps3"].to_numpy()[m]
    yaw_rate = kin["yaw_rate_radps"].to_numpy()[m]
    lat_acc = kin["lateral_accel_mps2"].to_numpy()[m]
    lat_dev = kin["lateral_dev_m"].to_numpy()[m]
    x = kin["x_m"].to_numpy()[m]
    y = kin["y_m"].to_numpy()[m]
    # route-level heading change uses the sway-free path heading
    heading = kin["path_heading_rad"].to_numpy()[m]

    n = int(m.sum())
    coverage = float(np.isfinite(speed).sum() / n) if n else float("nan")
    distance = float(np.nansum(speed) * dt) if n else float("nan")
    finite_xy = np.isfinite(x) & np.isfinite(y)
    if finite_xy.sum() >= 2:
        xf, yf = x[finite_xy], y[finite_xy]
        chord = float(np.hypot(xf[-1] - xf[0], yf[-1] - yf[0]))
        path = float(np.sum(np.hypot(np.diff(xf), np.diff(yf))))
        sinuosity = path / chord if chord > _MIN_CHORD_FOR_SINUOSITY_M else float("nan")
    else:
        sinuosity = float("nan")
    unwrapped = np.unwrap(heading[np.isfinite(heading)]) if np.isfinite(heading).sum() > 1 else np.array([])
    heading_change = float(np.degrees(np.sum(np.abs(np.diff(unwrapped))))) if unwrapped.size else float("nan")
    mean_speed = _nan_stat(speed, np.mean)
    sd_speed = _nan_stat(speed, np.std)

    def _in(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if df.empty:
            return df
        return df[(df[col] >= t0_ns) & (df[col] <= t1_ns)]

    win_braking = _in(braking, "t_onset_ns")
    win_stops = stops if stops.empty else stops[(stops["t_end_ns"] >= t0_ns) & (stops["t_start_ns"] <= t1_ns)]
    stop_time = 0.0
    for _, row in win_stops.iterrows():
        stop_time += (min(row["t_end_ns"], t1_ns) - max(row["t_start_ns"], t0_ns)) / NS_PER_S

    return {
        "duration_s": duration,
        "kinematics_coverage": coverage,
        "distance_m": distance,
        "speed_mean_mps": mean_speed,
        "speed_median_mps": _nan_stat(speed, np.median),
        "speed_sd_mps": sd_speed,
        "speed_cv": sd_speed / mean_speed if mean_speed and mean_speed > 0 else float("nan"),
        "speed_p85_mps": _nan_stat(speed, lambda v: np.percentile(v, 85)),
        "speed_max_mps": _nan_stat(speed, np.max),
        "accel_p95_mps2": _nan_stat(accel, lambda v: np.percentile(v, 95)),
        "decel_max_mps2": _nan_stat(accel, np.min),
        "jerk_rms_mps3": _nan_stat(jerk, lambda v: np.sqrt(np.mean(v**2))),
        "jerk_p95_abs_mps3": _nan_stat(np.abs(jerk), lambda v: np.percentile(v, 95)),
        "n_decel_events": int(len(win_braking)),
        "n_stops": int(len(win_stops)),
        "stop_time_s": stop_time,
        "yaw_rate_sd_degps": _nan_stat(np.degrees(yaw_rate), np.std),
        "lateral_accel_p95_abs_mps2": _nan_stat(np.abs(lat_acc), lambda v: np.percentile(v, 95)),
        "lateral_dev_rms_m": _nan_stat(lat_dev, lambda v: np.sqrt(np.mean(v**2))),
        "heading_change_total_deg": heading_change,
        "path_sinuosity": sinuosity,
    }


def segment_behaviour(
    kin: pd.DataFrame, segments: pd.DataFrame, braking: pd.DataFrame, stops: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for _, seg in segments.iterrows():
        metrics = window_metrics(kin, int(seg["t_start_ns"]), int(seg["t_end_ns"]), braking, stops)
        rows.append({"segment_id": seg["segment_id"], "infrastructure_class": seg["infrastructure_class"], **metrics})
    return pd.DataFrame(rows)


def approach_behaviour(
    kin: pd.DataFrame, segments: pd.DataFrame, braking: pd.DataFrame, stops: pd.DataFrame, cfg: KinematicsConfig
) -> pd.DataFrame:
    """Behaviour in the window preceding entry into crossings/intersections/roundabouts."""
    rows = []
    t = kin["t_ns"].to_numpy()
    speed = kin["speed_mps"].to_numpy()
    window_ns = int(cfg.approach_window_s * NS_PER_S)
    for _, seg in segments.iterrows():
        if seg["infrastructure_class"] not in cfg.approach_classes:
            continue
        entry = int(seg["t_start_ns"])
        start = entry - window_ns
        metrics = window_metrics(kin, start, entry, braking, stops)
        idx = int(np.argmin(np.abs(t - entry))) if len(t) else -1
        coverage_ok = start >= t[0] if len(t) else False
        rows.append(
            {
                "segment_id": seg["segment_id"],
                "infrastructure_class": seg["infrastructure_class"],
                "approach_window_s": cfg.approach_window_s,
                "approach_complete": bool(coverage_ok),
                "speed_at_entry_mps": float(speed[idx]) if idx >= 0 else float("nan"),
                "approach_speed_mean_mps": metrics["speed_mean_mps"],
                "approach_speed_min_mps": _nan_stat(speed[(t >= start) & (t <= entry)], np.min),
                "approach_decel_max_mps2": metrics["decel_max_mps2"],
                "approach_n_decel_events": metrics["n_decel_events"],
                "approach_stopped": metrics["n_stops"] > 0,
            }
        )
    return pd.DataFrame(rows)
