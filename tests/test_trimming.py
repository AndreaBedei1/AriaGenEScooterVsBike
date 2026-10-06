"""Ride trimming: raw session -> detected riding interval -> trimmed session."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.session import TrimmingOverride
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.trimming import slice_by_time, speed_for_trimming, trim_recording

RATE = 20.0
T0 = 5_000_000_000_000


def _pose_from_speed(keys: list[tuple[float, float]], duration: float = 200.0) -> pd.DataFrame:
    t = np.arange(0.0, duration, 1.0 / RATE)
    kt, kv = np.array(keys).T
    speed = np.interp(t, kt, kv)
    x = np.cumsum(speed) / RATE
    rng = np.random.default_rng(3)
    return pd.DataFrame(
        {
            "t_ns": (T0 + t * NS_PER_S).astype(np.int64),
            "x_m": x + rng.normal(0, 0.01, t.size),
            "y_m": rng.normal(0, 0.01, t.size),
            "z_m": np.full(t.size, 1.7),
        }
    )


# idle 0-20 s, walking the scooter at 1.1 m/s 20-30 s, idle, ride 40-170 s with a
# 6 s stop at a traffic light (100-106 s), idle after arrival.
KEYS = [
    (0, 0),
    (20, 0),
    (20.5, 1.1),
    (29.5, 1.1),
    (30, 0),
    (40, 0),
    (45, 5),
    (98, 5),
    (100, 0),
    (106, 0),
    (110, 5),
    (165, 5),
    (170, 0),
    (200, 0),
]


def _trim(cfg: LoadedConfig, pose: pd.DataFrame, override=None, **changes):
    t_cfg = cfg.analysis.trimming.model_copy(update=changes) if changes else cfg.analysis.trimming
    signal = speed_for_trimming(pose, None, t_cfg, polyorder=2, pose_max_gap_s=0.5, gps_max_gap_s=3.0)
    t = pose["t_ns"].to_numpy()
    return trim_recording(
        t_cfg, recording_start_ns=int(t[0]), recording_end_ns=int(t[-1]), signal=signal, override=override
    )


def test_detects_riding_interval_and_ignores_walking(cfg: LoadedConfig) -> None:
    result = _trim(cfg, _pose_from_speed(KEYS))
    d = result.as_dict()
    assert result.method == "automatic" and result.status == "ok"
    # speed crosses 2 m/s at 42 s (accelerating 1 m/s^2) and at 168 s (decelerating)
    assert d["detected_riding_interval"]["start_rel_s"] == pytest.approx(42.0, abs=0.4)
    assert d["detected_riding_interval"]["end_rel_s"] == pytest.approx(168.0, abs=0.4)
    assert d["trimmed_interval"]["start_rel_s"] == pytest.approx(40.0, abs=0.4)  # 2 s buffer
    assert d["removed_before_s"] > 35 and d["removed_after_s"] > 25
    assert all(r["start_rel_s"] > 35 for r in d["moving_runs"])  # walking never counted as moving
    assert "first to last" in d["reason"] and d["parameters"]["speed_threshold_mps"] == 2.0


def test_stop_does_not_split_ride_with_first_to_last(cfg: LoadedConfig) -> None:
    d = _trim(cfg, _pose_from_speed(KEYS)).as_dict()
    assert sum(r["kept"] for r in d["moving_runs"]) == 2  # split by the traffic light
    assert d["trimmed_interval"]["duration_s"] > 125  # ...but the ride is kept whole


def test_longest_selection_with_small_merge_gap(cfg: LoadedConfig) -> None:
    d = _trim(cfg, _pose_from_speed(KEYS), selection="longest", merge_gap_s=2.0).as_dict()
    assert d["detected_riding_interval"]["start_rel_s"] > 100  # second block (55 s) is the longest


def test_manual_override_wins_and_keeps_automatic_result(cfg: LoadedConfig) -> None:
    override = TrimmingOverride(start_rel_s=50.0, end_rel_s=150.0, reason="glasses adjusted at 45 s", decided_by="R01")
    result = _trim(cfg, _pose_from_speed(KEYS), override=override)
    d = result.as_dict()
    assert result.method == "manual_override"
    assert d["trimmed_interval"]["start_rel_s"] == pytest.approx(50.0)
    assert d["automatic_result"]["method"] == "automatic"
    assert d["automatic_result"]["difference_vs_override_s"]["start"] == pytest.approx(-10.0, abs=0.5)
    assert d["manual_override"]["decided_by"] == "R01"


def test_no_movement_keeps_full_recording(cfg: LoadedConfig) -> None:
    result = _trim(cfg, _pose_from_speed([(0, 0), (200, 0)]))
    assert result.method == "not_trimmed" and result.status == "failed"
    assert result.trim_start_ns == result.recording_start_ns and result.trim_end_ns == result.recording_end_ns


def test_missing_speed_source_and_disabled_trimming(cfg: LoadedConfig) -> None:
    t_cfg = cfg.analysis.trimming
    res = trim_recording(t_cfg, recording_start_ns=0, recording_end_ns=10 * NS_PER_S, signal=None)
    assert res.method == "not_trimmed" and res.status == "failed" and "no speed source" in res.reason
    res = trim_recording(
        t_cfg.model_copy(update={"enabled": False}), recording_start_ns=0, recording_end_ns=10, signal=None
    )
    assert res.method == "not_trimmed" and res.status == "ok"


def test_gps_doppler_speed_is_used_when_pose_missing(cfg: LoadedConfig) -> None:
    t = np.arange(0, 200, 1.0)
    kt, kv = np.array(KEYS).T
    gps = pd.DataFrame(
        {
            "t_ns": (T0 + t * NS_PER_S).astype(np.int64),
            "lat_deg": 45.0,
            "lon_deg": 13.0,
            "speed_mps": np.interp(t, kt, kv),
        }
    )
    signal = speed_for_trimming(None, gps, cfg.analysis.trimming, polyorder=2, pose_max_gap_s=0.5, gps_max_gap_s=3.0)
    assert signal is not None and signal.source == "gps_doppler_speed"


def test_imu_check_without_imu_warns(cfg: LoadedConfig) -> None:
    t_cfg = cfg.analysis.trimming.model_copy(
        update={"imu_check": cfg.analysis.trimming.imu_check.model_copy(update={"enabled": True})}
    )
    pose = _pose_from_speed(KEYS)
    signal = speed_for_trimming(pose, None, t_cfg, polyorder=2, pose_max_gap_s=0.5, gps_max_gap_s=3.0)
    t = pose["t_ns"].to_numpy()
    res = trim_recording(t_cfg, recording_start_ns=int(t[0]), recording_end_ns=int(t[-1]), signal=signal, imu=None)
    assert res.status == "warning" and res.warnings


def test_slicing_never_modifies_input() -> None:
    df = pd.DataFrame({"t_ns": np.arange(10), "v": np.arange(10.0)})
    out = slice_by_time(df, 3, 6)
    assert out["t_ns"].tolist() == [3, 4, 5, 6] and len(df) == 10
    assert slice_by_time(None, 0, 1) is None
