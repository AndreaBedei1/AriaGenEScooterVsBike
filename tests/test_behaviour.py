"""Kinematics and behaviour metrics on analytic trajectories."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.behaviour import approach_behaviour, detect_braking_events, detect_stops, window_metrics
from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.trajectory import compute_kinematics, latlon_to_local_xy, local_xy_to_latlon, wrap_angle

RATE = 20.0


def _kin(cfg: LoadedConfig, speed_keys, duration=60.0, lateral=None, noise=0.0, gap=None):
    t = np.arange(0.0, duration, 1.0 / RATE)
    kt, kv = np.array(speed_keys).T
    speed = np.interp(t, kt, kv)
    x = np.cumsum(speed) / RATE
    y = lateral(t) if lateral is not None else np.zeros_like(t)
    rng = np.random.default_rng(0)
    x, y = x + rng.normal(0, noise, t.size), y + rng.normal(0, noise, t.size)
    if gap is not None:
        keep = ~((t > gap[0]) & (t < gap[1]))
        t, x, y = t[keep], x[keep], y[keep]
    t_ns = (t * NS_PER_S).astype(np.int64)
    return compute_kinematics(t_ns, x, y, cfg.analysis.kinematics, max_gap_s=0.5)


def test_constant_speed_straight_line(cfg: LoadedConfig) -> None:
    kin = _kin(cfg, [(0, 4.0), (60, 4.0)], noise=0.005)
    inner = kin.iloc[20:-20]
    assert inner["speed_mps"].mean() == pytest.approx(4.0, abs=0.02)
    assert inner["accel_mps2"].abs().max() < 0.2
    assert np.degrees(inner["heading_rad"]).mean() == pytest.approx(0.0, abs=0.5)
    assert inner["lateral_dev_m"].abs().max() < 0.05
    assert detect_braking_events(kin, cfg.analysis.kinematics).empty


def test_deceleration_event_onset_and_peak(cfg: LoadedConfig) -> None:
    # 5 -> 1 m/s between 20 and 22 s (-2 m/s^2), then back to 5 m/s
    kin = _kin(cfg, [(0, 5), (20, 5), (22, 1), (30, 1), (34, 5), (60, 5)])
    events = detect_braking_events(kin, cfg.analysis.kinematics)
    assert len(events) == 1
    ev = events.iloc[0]
    assert ev["t_onset_ns"] / NS_PER_S == pytest.approx(20.0, abs=0.5)
    assert ev["peak_decel_mps2"] == pytest.approx(-2.0, abs=0.35)
    assert ev["speed_drop_mps"] == pytest.approx(4.0, abs=0.4)


def test_stops_and_window_metrics(cfg: LoadedConfig) -> None:
    kin = _kin(cfg, [(0, 4), (10, 4), (12, 0), (18, 0), (20, 4), (60, 4)])
    stops = detect_stops(kin, cfg.analysis.kinematics)
    assert len(stops) == 1
    assert stops["duration_s"].iat[0] == pytest.approx(6.0, abs=0.8)
    braking = detect_braking_events(kin, cfg.analysis.kinematics)
    m = window_metrics(kin, int(25 * NS_PER_S), int(55 * NS_PER_S), braking, stops)
    assert m["distance_m"] == pytest.approx(120.0, rel=0.02)
    assert m["speed_mean_mps"] == pytest.approx(4.0, abs=0.05)
    assert m["n_stops"] == 0 and m["kinematics_coverage"] == pytest.approx(1.0)
    whole = window_metrics(kin, int(0 * NS_PER_S), int(59.9 * NS_PER_S), braking, stops)
    assert whole["n_stops"] == 1 and whole["stop_time_s"] == pytest.approx(stops["duration_s"].iat[0], abs=0.2)


def test_lateral_oscillation_is_measured(cfg: LoadedConfig) -> None:
    straight = _kin(cfg, [(0, 4), (60, 4)])
    kin = _kin(cfg, [(0, 4), (60, 4)], lateral=lambda t: 0.2 * np.sin(2 * np.pi * 0.5 * t))
    args = (int(10 * NS_PER_S), int(50 * NS_PER_S))
    m0 = window_metrics(
        straight,
        *args,
        detect_braking_events(straight, cfg.analysis.kinematics),
        detect_stops(straight, cfg.analysis.kinematics),
    )
    m = window_metrics(
        kin, *args, detect_braking_events(kin, cfg.analysis.kinematics), detect_stops(kin, cfg.analysis.kinematics)
    )
    # sway of 0.14 m RMS, partly attenuated by the light smoothing of the trajectory
    assert 0.07 < m["lateral_dev_rms_m"] < 0.16
    assert m0["lateral_dev_rms_m"] < 0.01
    assert m["yaw_rate_sd_degps"] > 5 * max(m0["yaw_rate_sd_degps"], 0.1)


def test_gaps_produce_nan_not_invented_values(cfg: LoadedConfig) -> None:
    kin = _kin(cfg, [(0, 4), (60, 4)], gap=(30.0, 33.0))
    t = kin["t_ns"].to_numpy() / NS_PER_S
    inside = (t > 30.2) & (t < 32.8)
    assert kin.loc[inside, "speed_mps"].isna().all()
    assert kin.loc[(t > 35) & (t < 55), "speed_mps"].notna().all()


def test_approach_window(cfg: LoadedConfig) -> None:
    kin = _kin(cfg, [(0, 5), (20, 5), (24, 2), (60, 2)])
    seg = pd.DataFrame(
        {
            "segment_id": ["S1"],
            "infrastructure_class": ["roundabout"],
            "t_start_ns": [int(25 * NS_PER_S)],
            "t_end_ns": [int(40 * NS_PER_S)],
        }
    )
    out = approach_behaviour(
        kin,
        seg,
        detect_braking_events(kin, cfg.analysis.kinematics),
        detect_stops(kin, cfg.analysis.kinematics),
        cfg.analysis.kinematics,
    )
    assert out["approach_complete"].iat[0]
    assert out["speed_at_entry_mps"].iat[0] == pytest.approx(2.0, abs=0.1)
    assert out["approach_decel_max_mps2"].iat[0] < -0.5


def test_local_projection_roundtrip() -> None:
    lat, lon = local_xy_to_latlon(np.array([100.0, -250.0]), np.array([30.0, 500.0]), 45.0, 13.0)
    x, y = latlon_to_local_xy(lat, lon, 45.0, 13.0)
    assert np.allclose(x, [100.0, -250.0], atol=1e-6) and np.allclose(y, [30.0, 500.0], atol=1e-6)


def test_wrap_angle() -> None:
    assert np.allclose(wrap_angle(np.array([0.0, np.pi, -np.pi, 3 * np.pi / 2])), [0.0, np.pi, np.pi, -np.pi / 2])
