"""Data-quality control of the canonical streams (and of raw VRS streams at extraction).

Principles
----------
* Quality is MEASURED per recording and per stream; nothing is assumed from
  the device specifications (e.g. VIO dropout rates seen elsewhere are not
  taken as given).
* Gaps are never filled silently. The timeline of each stream is split into
  intervals classified by the length of the interruption::

      observed      consecutive valid samples closer than jitter_factor x nominal period
      interpolable  short gap (<= short_gap_s): smooth signals MAY be interpolated,
                    and the interpolated time is reported as such
      degraded      medium gap (<= medium_gap_s): not interpolated; metrics over
                    windows touching it report reduced coverage
      unusable      long gap, invalid samples, or outside the stream's span

* Every window metric can carry the fractions of observed / interpolable /
  degraded / unusable time of the streams it uses (:func:`window_quality`).

The high-frequency VIO stream of Aria Gen 2 (~800 Hz) is IMU pre-integration
on top of the 10 Hz VIO (official on-device MP documentation): its samples are
not independent visual measurements, and its quality is checked separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ariagen_escooter.streams import NS_PER_S

INTERVAL_STATUSES = ("observed", "interpolable", "degraded", "unusable")
GAP_CLASSES = ("dropped_samples", "short_gap", "medium_gap", "long_gap")

# Recording-profile keys (camelCase as in our draft profile, snake_case as in
# the official Gen 2 profiles) -> canonical stream.
PROFILE_STREAM_KEYS: dict[str, tuple[str, ...]] = {
    "frames": ("rgbCamera", "rgb_camera"),
    "gaze": ("et",),
    "imu": ("imus",),
    "pose": ("vio",),
    "pose_hf": ("vio_high_frequency_pose", "vioHighFrequencyPose", "vio_high_frequency"),
    "hands": ("ht",),
    "gps": ("gps",),
    "ppg": ("ppg",),
}


@dataclass(frozen=True)
class GapThresholds:
    """Gap classification for one stream (seconds)."""

    jitter_factor: float
    short_gap_s: float
    medium_gap_s: float


# --------------------------------------------------------------------------- #
# Recording profiles
# --------------------------------------------------------------------------- #
def nominal_rates_from_profile(profile: dict[str, Any]) -> dict[str, float]:
    """Nominal rates (Hz) of the canonical streams declared in a recording profile."""
    out: dict[str, float] = {}
    for stream, keys in PROFILE_STREAM_KEYS.items():
        for key in keys:
            block = profile.get(key)
            if isinstance(block, dict):
                rate = block.get("rateHz", block.get("rate_hz"))
                if rate is not None:
                    out[stream] = float(rate)
                    break
    return out


def canonical_nominal_rates(profile_rates: dict[str, float], imu_rate_hz: float,
                            pose_hf_rate_hz: float) -> dict[str, float]:
    """Nominal rates of the CANONICAL streams: profile rates, except for the
    streams that the extractor resamples (IMU bin-averaged, high-frequency VIO
    nearest-sample), whose canonical rate is the resampling rate."""
    out = dict(profile_rates)
    if "imu" in out:
        out["imu"] = imu_rate_hz
    out["pose_hf"] = pose_hf_rate_hz
    return out


def load_profile(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: a recording profile must be a JSON object")
    return data


# --------------------------------------------------------------------------- #
# Sample timing
# --------------------------------------------------------------------------- #
def timing_quality(
    t_ns: np.ndarray,
    stream: str,
    nominal_rate_hz: float | None,
    thresholds: GapThresholds,
    *,
    span: tuple[int, int] | None = None,
    max_listed_gaps: int = 50,
) -> dict[str, Any]:
    """Timing quality of one stream: invalid/duplicated/out-of-order timestamps,
    effective vs nominal rate, estimated dropped samples and classified gaps.

    ``span`` (device-time start/end of the recording) is used to report a late
    start / early end of the stream and to express gap positions in seconds.
    Without ``nominal_rate_hz`` the median interval is used as reference (and
    the dropout estimate is then only relative to the stream's own cadence).
    """
    t = np.asarray(t_ns, dtype=np.int64)
    out: dict[str, Any] = {"stream": stream, "n_samples": int(t.size), "nominal_rate_hz": nominal_rate_hz}
    if t.size == 0:
        out["status"] = "empty"
        return out
    invalid = t <= 0
    if span is not None:
        invalid |= (t < span[0] - 10 * NS_PER_S) | (t > span[1] + 10 * NS_PER_S)
    dt = np.diff(t)
    out["n_invalid_timestamps"] = int(invalid.sum())
    out["n_out_of_order"] = int(np.sum(dt < 0))
    out["n_duplicates"] = int(np.sum(dt == 0))
    tv = np.unique(t[~invalid])  # sorted, unique, plausible
    if tv.size < 2:
        out["status"] = "too_few_samples"
        return out
    d = np.diff(tv).astype(np.float64) / NS_PER_S
    median_dt = float(np.median(d))
    period = 1.0 / nominal_rate_hz if nominal_rate_hz else median_dt
    duration = float(tv[-1] - tv[0]) / NS_PER_S
    expected = duration / period + 1.0
    out.update(
        {
            "start_ns": int(tv[0]),
            "end_ns": int(tv[-1]),
            "duration_s": duration,
            "median_interval_s": median_dt,
            "median_rate_hz": 1.0 / median_dt if median_dt > 0 else None,
            "effective_rate_hz": (tv.size - 1) / duration if duration > 0 else None,
            "reference_period_s": period,
            "expected_samples": expected,
            "dropout_fraction": max(0.0, 1.0 - tv.size / expected),
        }
    )
    if nominal_rate_hz and out["effective_rate_hz"]:
        out["rate_deviation_percent"] = 100.0 * (out["effective_rate_hz"] - nominal_rate_hz) / nominal_rate_hz
    if span is not None:
        out["start_delay_s"] = (int(tv[0]) - span[0]) / NS_PER_S
        out["end_advance_s"] = (span[1] - int(tv[-1])) / NS_PER_S
    is_gap = d > thresholds.jitter_factor * period
    gap_idx = np.flatnonzero(is_gap)
    classes = np.array([classify_gap(float(d[i]), thresholds) for i in gap_idx], dtype=object)
    out["n_missing_samples_estimated"] = int(np.sum(np.maximum(np.round(d[is_gap] / period) - 1, 0)))
    out["gap_counts"] = {c: int(np.sum(classes == c)) for c in GAP_CLASSES}
    out["gap_time_s"] = {c: float(np.sum(d[gap_idx][classes == c])) for c in GAP_CLASSES}
    out["max_gap_s"] = float(d.max())
    origin = span[0] if span is not None else int(tv[0])
    order = np.argsort(-d[gap_idx])[:max_listed_gaps]
    out["largest_gaps"] = [
        {"start_rel_s": (int(tv[gap_idx[i]]) - origin) / NS_PER_S, "duration_s": float(d[gap_idx[i]]),
         "class": str(classes[i])}
        for i in sorted(order, key=lambda k: gap_idx[k])
    ]
    out["status"] = "ok"
    return out


def classify_gap(duration_s: float, thresholds: GapThresholds) -> str:
    """Class of an inter-sample interval already known to exceed normal jitter."""
    if duration_s <= thresholds.short_gap_s:
        return "short_gap"
    if duration_s <= thresholds.medium_gap_s:
        return "medium_gap"
    return "long_gap"


def classify_intervals(
    t_ns: np.ndarray,
    valid: np.ndarray | None,
    span: tuple[int, int],
    nominal_rate_hz: float | None,
    thresholds: GapThresholds,
    *,
    stream: str,
    breaks_ns: np.ndarray | None = None,
) -> pd.DataFrame:
    """Split the recording span into observed / interpolable / degraded / unusable intervals.

    Only VALID samples count as observations. ``breaks_ns`` are instants where
    continuity is broken although samples exist (e.g. a VIO reset: the
    odometry frame changes), so the interval across a break is never
    "observed" or "interpolable".
    """
    t = np.asarray(t_ns, dtype=np.int64)
    ok = np.ones(t.size, dtype=bool) if valid is None else np.asarray(valid, dtype=bool)
    tv = np.unique(t[ok & (t >= span[0]) & (t <= span[1])])
    rows: list[tuple[int, int, str, str]] = []
    if tv.size == 0:
        rows.append((span[0], span[1], "unusable", "no_valid_samples"))
        return _merge_intervals(rows, stream)
    d = np.diff(tv).astype(np.float64) / NS_PER_S
    period = 1.0 / nominal_rate_hz if nominal_rate_hz else (float(np.median(d)) if d.size else 0.0)
    if tv[0] > span[0]:
        rows.append((span[0], int(tv[0]), "unusable", "before_first_valid_sample"))
    brk = np.sort(np.asarray(breaks_ns, dtype=np.int64)) if breaks_ns is not None else np.empty(0, np.int64)
    for i, gap in enumerate(d):
        a, b = int(tv[i]), int(tv[i + 1])
        crosses_break = brk.size > 0 and np.any((brk > a) & (brk <= b))
        if crosses_break:
            status, reason = ("degraded", "tracking_reset") if gap <= thresholds.medium_gap_s else ("unusable", "tracking_reset")
        elif gap <= thresholds.jitter_factor * period:
            status, reason = "observed", ""
        else:
            cls = classify_gap(gap, thresholds)
            status = {"short_gap": "interpolable", "medium_gap": "degraded", "long_gap": "unusable"}[cls]
            reason = cls
        rows.append((a, b, status, reason))
    if tv[-1] < span[1]:
        rows.append((int(tv[-1]), span[1], "unusable", "after_last_valid_sample"))
    return _merge_intervals(rows, stream)


def _merge_intervals(rows: list[tuple[int, int, str, str]], stream: str) -> pd.DataFrame:
    merged: list[list[Any]] = []
    for a, b, status, reason in rows:
        if b <= a:
            continue
        if merged and merged[-1][2] == status and merged[-1][1] == a:
            merged[-1][1] = b
            if reason and reason not in merged[-1][3]:
                merged[-1][3] = (merged[-1][3] + ";" + reason).strip(";")
        else:
            merged.append([a, b, status, reason])
    df = pd.DataFrame(merged, columns=["t_start_ns", "t_end_ns", "status", "reason"])
    df.insert(0, "stream", stream)
    df["duration_s"] = (df["t_end_ns"] - df["t_start_ns"]) / NS_PER_S
    return df


def status_fractions(intervals: pd.DataFrame, t0: int, t1: int) -> dict[str, float]:
    """Fraction of [t0, t1] in each interval status (one stream's intervals)."""
    total = float(t1 - t0)
    out = {s: 0.0 for s in INTERVAL_STATUSES}
    if total <= 0 or intervals is None or intervals.empty:
        out["unusable"] = 1.0 if total > 0 else np.nan
        return out
    a = np.clip(intervals["t_start_ns"].to_numpy(dtype=np.int64), t0, t1)
    b = np.clip(intervals["t_end_ns"].to_numpy(dtype=np.int64), t0, t1)
    for status, length in zip(intervals["status"], (b - a).astype(np.float64)):
        out[status] += length / total
    covered = sum(out.values())
    out["unusable"] += max(0.0, 1.0 - covered)  # time not covered by any interval
    return out


def window_quality(
    intervals: pd.DataFrame | None, t0: int, t1: int, streams: tuple[str, ...], min_coverage: float
) -> dict[str, object]:
    """Per-stream observed/interpolable/degraded/unusable fractions for a window,
    plus a summary flag: ``ok`` if every listed stream that exists has
    observed + interpolable >= ``min_coverage``, else ``low_coverage``."""
    out: dict[str, object] = {}
    flag = "ok"
    if intervals is None or intervals.empty:
        return {"quality_flag": "no_quality_information"}
    for stream in streams:
        sub = intervals[intervals["stream"] == stream]
        if sub.empty:
            continue
        fr = status_fractions(sub, t0, t1)
        for status in INTERVAL_STATUSES:
            out[f"q_{stream}_{status}"] = fr[status]
        if fr["observed"] + fr["interpolable"] < min_coverage:
            flag = "low_coverage"
    out["quality_flag"] = flag
    return out


# --------------------------------------------------------------------------- #
# Stream-specific checks
# --------------------------------------------------------------------------- #
def _quat_angle_deg(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    dot = np.abs(np.sum(q1 * q2, axis=1)) / (np.linalg.norm(q1, axis=1) * np.linalg.norm(q2, axis=1))
    return np.degrees(2.0 * np.arccos(np.clip(dot, -1.0, 1.0)))


def tracking_breaks(pose: pd.DataFrame) -> np.ndarray:
    """Device times where the VIO tracking session changes (reset): first sample of the new session."""
    if "tracking_session" not in pose.columns or pose.empty:
        return np.empty(0, dtype=np.int64)
    session = pose["tracking_session"].astype(str).to_numpy()
    t = pose["t_ns"].to_numpy(dtype=np.int64)
    change = np.flatnonzero(session[1:] != session[:-1]) + 1
    return t[change]


def pose_quality(pose: pd.DataFrame, max_speed_mps: float, max_angular_rate_degps: float,
                 min_quality_score: float | None = None) -> dict[str, Any]:
    """VIO status / tracking quality, resets, quality score and pose discontinuities."""
    out: dict[str, Any] = {"n_samples": int(len(pose))}
    if pose.empty:
        return out
    for col in ("vio_status", "tracking_quality", "visual_tracking_quality"):
        if col in pose.columns:
            out[f"{col}_counts"] = pose[col].astype(str).value_counts().sort_index().to_dict()
    valid = pose["valid"].astype(bool).to_numpy() if "valid" in pose.columns else np.ones(len(pose), bool)
    out["valid_fraction"] = float(valid.mean())
    breaks = tracking_breaks(pose)
    out["n_tracking_sessions"] = int(pose["tracking_session"].nunique()) if "tracking_session" in pose.columns else None
    out["n_resets"] = int(breaks.size)
    out["reset_times_ns"] = [int(x) for x in breaks[:50]]
    if "quality" in pose.columns:
        q = pose["quality"].to_numpy(dtype=np.float64)
        finite = q[np.isfinite(q)]
        if finite.size:
            out["quality_score"] = {"min": float(finite.min()), "p05": float(np.percentile(finite, 5)),
                                    "median": float(np.median(finite))}
            if min_quality_score is not None:
                out["quality_score"]["fraction_below_threshold"] = float(np.mean(finite < min_quality_score))
                out["quality_score"]["threshold"] = min_quality_score
    # Discontinuities between consecutive VALID samples of the same session.
    p = pose[valid]
    t = p["t_ns"].to_numpy(dtype=np.int64)
    if t.size >= 2:
        same = np.ones(t.size - 1, bool)
        if "tracking_session" in p.columns:
            s = p["tracking_session"].astype(str).to_numpy()
            same = s[1:] == s[:-1]
        dt = np.diff(t) / NS_PER_S
        xyz = p[["x_m", "y_m", "z_m"]].to_numpy(dtype=np.float64)
        step = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            jump = same & (dt > 0) & (step / dt > max_speed_mps)
        out["n_position_jumps"] = int(jump.sum())
        out["position_jump_times_ns"] = [int(x) for x in t[1:][jump][:50]]
        if {"qw", "qx", "qy", "qz"} <= set(p.columns):
            q = p[["qw", "qx", "qy", "qz"]].to_numpy(dtype=np.float64)
            ang = _quat_angle_deg(q[:-1], q[1:])
            with np.errstate(divide="ignore", invalid="ignore"):
                rot_jump = same & (dt > 0) & (ang / dt > max_angular_rate_degps)
            out["n_orientation_jumps"] = int(rot_jump.sum())
    return out


def gaze_quality(gaze: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"n_samples": int(len(gaze))}
    if gaze.empty:
        return out
    out["valid_fraction"] = float(gaze["valid"].astype(bool).mean())
    for col in ("spatial_point_valid", "left_valid", "right_valid"):
        if col in gaze.columns:
            out[f"{col}_fraction"] = float(gaze[col].astype(bool).mean())
    if "u_px" in gaze.columns:
        out["projected_in_image_fraction"] = float(np.isfinite(gaze["u_px"].to_numpy(dtype=np.float64)).mean())
    if "depth_m" in gaze.columns:
        out["depth_available_fraction"] = float(np.isfinite(gaze["depth_m"].to_numpy(dtype=np.float64)).mean())
    if "confidence" in gaze.columns and gaze["confidence"].notna().any():
        out["confidence_median"] = float(gaze["confidence"].median())
    else:
        out["confidence_note"] = "no per-sample confidence (Aria Gen 2 on-device gaze provides validity flags only)"
    return out


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def hands_quality(hands: pd.DataFrame, min_confidence: float) -> dict[str, Any]:
    """Presence and confidence of each hand. Absence = hand NOT DETECTED by the
    tracker (occlusion, out of view, tracking loss): it is NOT evidence that the
    hand left the handlebar."""
    out: dict[str, Any] = {"n_samples": int(len(hands)),
                           "note": "absent = not detected; never interpreted as hand off the handlebar"}
    if hands.empty:
        return out
    t = hands["t_ns"].to_numpy(dtype=np.int64)
    for side in ("left", "right"):
        col = f"{side}_present"
        if col not in hands.columns:
            continue
        present = hands[col].astype(bool).to_numpy()
        conf = hands.get(f"{side}_confidence")
        info: dict[str, Any] = {"present_fraction": float(present.mean())}
        if conf is not None:
            c = conf.to_numpy(dtype=np.float64)[present]
            c = c[np.isfinite(c)]
            if c.size:
                info["confidence_median"] = float(np.median(c))
                info["low_confidence_fraction_of_present"] = float(np.mean(c < min_confidence))
        absences = [(a, b) for a, b in _runs(~present)]
        durations = [(t[min(b + 1, t.size - 1)] - t[a]) / NS_PER_S for a, b in absences]
        info["n_absence_episodes"] = len(absences)
        info["longest_absence_s"] = float(max(durations)) if durations else 0.0
        out[side] = info
    if {"left_present", "right_present"} <= set(hands.columns):
        both = hands["left_present"].astype(bool) & hands["right_present"].astype(bool)
        out["both_present_fraction"] = float(both.mean())
    return out


def gps_quality(gps: pd.DataFrame, max_accuracy_m: float) -> dict[str, Any]:
    out: dict[str, Any] = {"n_samples": int(len(gps))}
    if gps.empty:
        return out
    lat = gps["lat_deg"].to_numpy(dtype=np.float64)
    lon = gps["lon_deg"].to_numpy(dtype=np.float64)
    fix = np.isfinite(lat) & np.isfinite(lon) & ~((lat == 0) & (lon == 0))
    out["fix_fraction"] = float(fix.mean())
    if "accuracy_m" in gps.columns:
        acc = gps["accuracy_m"].to_numpy(dtype=np.float64)[fix]
        acc = acc[np.isfinite(acc)]
        if acc.size:
            out["accuracy_m"] = {"median": float(np.median(acc)), "p90": float(np.percentile(acc, 90)),
                                 "max": float(acc.max())}
            out["fraction_within_accuracy_threshold"] = float(np.mean(acc <= max_accuracy_m))
            out["accuracy_threshold_m"] = max_accuracy_m
    if "speed_mps" in gps.columns:
        out["speed_available_fraction"] = float(gps["speed_mps"].notna().mean())
    return out


def frames_quality(frames: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"n_frames": int(len(frames))}
    if frames.empty:
        return out
    idx = frames["frame_index"].to_numpy(dtype=np.int64)
    out["n_index_gaps"] = int(np.sum(np.diff(np.sort(idx)) > 1))
    return out


# --------------------------------------------------------------------------- #
# Recording-level report
# --------------------------------------------------------------------------- #
def valid_mask(name: str, df: pd.DataFrame) -> np.ndarray | None:
    """Which samples count as observations for interval classification."""
    if name in {"gaze", "pose", "pose_hf"} and "valid" in df.columns:
        return df["valid"].astype(bool).to_numpy()
    if name == "hands" and {"left_present", "right_present"} & set(df.columns):
        cols = [c for c in ("left_present", "right_present") if c in df.columns]
        return df[cols].astype(bool).any(axis=1).to_numpy()
    if name == "gps" and {"lat_deg", "lon_deg"} <= set(df.columns):
        lat, lon = df["lat_deg"].to_numpy(dtype=np.float64), df["lon_deg"].to_numpy(dtype=np.float64)
        return np.isfinite(lat) & np.isfinite(lon) & ~((lat == 0) & (lon == 0))
    return None


def recording_quality(
    streams: dict[str, pd.DataFrame],
    span: tuple[int, int],
    nominal_rates: dict[str, float],
    thresholds: dict[str, GapThresholds],
    *,
    max_speed_mps: float,
    max_angular_rate_degps: float,
    min_hf_quality_score: float,
    gps_max_accuracy_m: float,
    min_hand_confidence: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Quality report and classified intervals for all available canonical streams."""
    report: dict[str, Any] = {"span_ns": [int(span[0]), int(span[1])], "streams": {}}
    intervals = []
    for name, df in streams.items():
        if name not in thresholds or df is None:
            continue
        th = thresholds[name]
        rate = nominal_rates.get(name)
        entry = {"timing": timing_quality(df["t_ns"].to_numpy(), name, rate, th, span=span)}
        breaks = None
        if name in {"pose", "pose_hf"}:
            breaks = tracking_breaks(df)
            entry["tracking"] = pose_quality(df, max_speed_mps, max_angular_rate_degps,
                                             min_hf_quality_score if name == "pose_hf" else None)
        elif name == "gaze":
            entry["validity"] = gaze_quality(df)
        elif name == "hands":
            entry["validity"] = hands_quality(df, min_hand_confidence)
        elif name == "gps":
            entry["validity"] = gps_quality(df, gps_max_accuracy_m)
        elif name == "frames":
            entry["validity"] = frames_quality(df)
        iv = classify_intervals(df["t_ns"].to_numpy(), valid_mask(name, df), span, rate, th, stream=name,
                                breaks_ns=breaks)
        entry["interval_fractions"] = status_fractions(iv, span[0], span[1])
        report["streams"][name] = entry
        intervals.append(iv)
    table = pd.concat(intervals, ignore_index=True) if intervals else pd.DataFrame(
        columns=["stream", "t_start_ns", "t_end_ns", "status", "reason", "duration_s"])
    return report, table
