"""Trajectory processing: local coordinates and kinematics on a uniform grid.

Important methodological note
-----------------------------
Aria is head-mounted. Pose/VIO positions describe the rider's HEAD, which
translates with the e-scooter but also sways relative to it; head rotation is
NOT the vehicle heading. Therefore:

* speed / acceleration / jerk are derived from the (smoothed) horizontal head
  trajectory and approximate the vehicle's longitudinal kinematics;
* heading is the direction of TRAVEL (velocity direction), not head yaw;
* lateral metrics mix vehicle lateral motion and body sway (proxy only).

A rigidly mounted vehicle IMU/GNSS would be needed to separate the two; this
is listed as an open methodological decision (docs/methodology.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from ariagen_escooter.config import KinematicsConfig
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.synchronization import find_runs, interpolate_to_grid, make_grid

# Mean Earth radius (IUGG), metres.
EARTH_RADIUS_M = 6_371_008.8


def latlon_to_local_xy(
    lat_deg: np.ndarray, lon_deg: np.ndarray, origin_lat_deg: float, origin_lon_deg: float
) -> tuple[np.ndarray, np.ndarray]:
    """Local east/north metres around an origin (equirectangular approximation).

    Adequate for city-scale routes (a few kilometres); use a proper map
    projection for larger areas.
    """
    lat = np.radians(np.asarray(lat_deg, dtype=np.float64))
    lon = np.radians(np.asarray(lon_deg, dtype=np.float64))
    lat0, lon0 = np.radians(origin_lat_deg), np.radians(origin_lon_deg)
    x = (lon - lon0) * np.cos(lat0) * EARTH_RADIUS_M
    y = (lat - lat0) * EARTH_RADIUS_M
    return x, y


def local_xy_to_latlon(
    x_m: np.ndarray, y_m: np.ndarray, origin_lat_deg: float, origin_lon_deg: float
) -> tuple[np.ndarray, np.ndarray]:
    """Inverse of :func:`latlon_to_local_xy`."""
    lat0 = np.radians(origin_lat_deg)
    lat = origin_lat_deg + np.degrees(np.asarray(y_m, dtype=np.float64) / EARTH_RADIUS_M)
    lon = origin_lon_deg + np.degrees(np.asarray(x_m, dtype=np.float64) / (EARTH_RADIUS_M * np.cos(lat0)))
    return lat, lon


def odd_window(window_s: float, rate_hz: float, polyorder: int) -> int:
    """Savitzky-Golay window length in samples: odd and > polyorder."""
    n = int(round(window_s * rate_hz))
    n = max(n, polyorder + 2)
    return n if n % 2 == 1 else n + 1


def savgol_nan_aware(y: np.ndarray, window: int, polyorder: int, deriv: int = 0, delta: float = 1.0) -> np.ndarray:
    """Savitzky-Golay filter applied separately to each finite chunk.

    Chunks shorter than ``window`` are returned as NaN (no extrapolation over gaps).
    """
    y = np.asarray(y, dtype=np.float64)
    out = np.full_like(y, np.nan)
    for start, end in find_runs(np.isfinite(y)):
        chunk = y[start : end + 1]
        if chunk.size < window:
            continue
        out[start : end + 1] = savgol_filter(chunk, window, polyorder, deriv=deriv, delta=delta, mode="interp")
    return out


def unwrap_nan_aware(angle_rad: np.ndarray) -> np.ndarray:
    """np.unwrap applied per finite chunk."""
    a = np.asarray(angle_rad, dtype=np.float64)
    out = np.full_like(a, np.nan)
    for start, end in find_runs(np.isfinite(a)):
        out[start : end + 1] = np.unwrap(a[start : end + 1])
    return out


def wrap_angle(angle_rad: np.ndarray) -> np.ndarray:
    """Wrap to (-pi, pi]."""
    a = np.asarray(angle_rad, dtype=np.float64)
    return np.pi - np.mod(np.pi - a, 2.0 * np.pi)


def speed_profile(
    t_ns: np.ndarray,
    x_m: np.ndarray,
    y_m: np.ndarray,
    *,
    rate_hz: float,
    window_s: float,
    polyorder: int,
    max_gap_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Smoothed horizontal speed on a uniform grid -> (grid_ns, speed_mps)."""
    t = np.asarray(t_ns, dtype=np.int64)
    grid = make_grid(int(t[0]), int(t[-1]), rate_hz)
    max_gap = int(max_gap_s * NS_PER_S)
    xg = interpolate_to_grid(t, x_m, grid, max_gap)
    yg = interpolate_to_grid(t, y_m, grid, max_gap)
    window = odd_window(window_s, rate_hz, polyorder)
    dt = 1.0 / rate_hz
    vx = savgol_nan_aware(xg, window, polyorder, deriv=1, delta=dt)
    vy = savgol_nan_aware(yg, window, polyorder, deriv=1, delta=dt)
    return grid, np.hypot(vx, vy)


def compute_kinematics(
    t_ns: np.ndarray,
    x_m: np.ndarray,
    y_m: np.ndarray,
    cfg: KinematicsConfig,
    *,
    max_gap_s: float,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> pd.DataFrame:
    """Kinematic signals on a uniform grid from a horizontal trajectory.

    Columns: t_ns, x_m, y_m (smoothed), speed_mps, accel_mps2 (longitudinal,
    d speed/dt), jerk_mps3, heading_rad (direction of travel, NaN below
    ``min_speed_for_heading_mps``), yaw_rate_radps (rate of change of the
    travel direction), lateral_accel_mps2 (speed x yaw rate), path_heading_rad
    (direction of the path smoothed over ``lateral_reference_window_s``, i.e.
    without body sway), lateral_dev_m (signed deviation from that smoothed
    path, positive = left), stopped (bool).
    """
    t = np.asarray(t_ns, dtype=np.int64)
    rate = cfg.grid_rate_hz
    start = int(t[0]) if start_ns is None else max(int(start_ns), int(t[0]))
    end = int(t[-1]) if end_ns is None else min(int(end_ns), int(t[-1]))
    grid = make_grid(start, end, rate)
    max_gap = int(max_gap_s * NS_PER_S)
    xg = interpolate_to_grid(t, x_m, grid, max_gap)
    yg = interpolate_to_grid(t, y_m, grid, max_gap)
    p = cfg.savgol_polyorder
    w = odd_window(cfg.smoothing_window_s, rate, p)
    dt = 1.0 / rate

    xs = savgol_nan_aware(xg, w, p, 0, dt)
    ys = savgol_nan_aware(yg, w, p, 0, dt)
    vx = savgol_nan_aware(xg, w, p, 1, dt)
    vy = savgol_nan_aware(yg, w, p, 1, dt)
    speed = np.hypot(vx, vy)
    accel = savgol_nan_aware(speed, w, p, 1, dt)
    jerk = savgol_nan_aware(speed, w, p, 2, dt)

    heading = np.where(speed >= cfg.min_speed_for_heading_mps, np.arctan2(vy, vx), np.nan)
    yaw_rate = savgol_nan_aware(unwrap_nan_aware(heading), w, p, 1, dt)
    lateral_accel = speed * yaw_rate

    w_ref = odd_window(cfg.lateral_reference_window_s, rate, p)
    xr = savgol_nan_aware(xg, w_ref, p, 0, dt)
    yr = savgol_nan_aware(yg, w_ref, p, 0, dt)
    txr = savgol_nan_aware(xg, w_ref, p, 1, dt)
    tyr = savgol_nan_aware(yg, w_ref, p, 1, dt)
    norm = np.hypot(txr, tyr)
    with np.errstate(invalid="ignore", divide="ignore"):
        nx, ny = -tyr / norm, txr / norm  # left normal of the reference path
        lateral_dev = (xs - xr) * nx + (ys - yr) * ny
    lateral_dev = np.where(norm >= cfg.min_speed_for_heading_mps, lateral_dev, np.nan)
    path_heading = np.where(norm >= cfg.min_speed_for_heading_mps, np.arctan2(tyr, txr), np.nan)

    return pd.DataFrame(
        {
            "t_ns": grid,
            "x_m": xs,
            "y_m": ys,
            "speed_mps": speed,
            "accel_mps2": accel,
            "jerk_mps3": jerk,
            "heading_rad": heading,
            "yaw_rate_radps": yaw_rate,
            "lateral_accel_mps2": lateral_accel,
            "path_heading_rad": path_heading,
            "lateral_dev_m": lateral_dev,
            "stopped": np.isfinite(speed) & (speed < cfg.stop_speed_threshold_mps),
        }
    )
