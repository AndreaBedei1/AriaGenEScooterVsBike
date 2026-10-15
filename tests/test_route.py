"""Route alignment (GNSS -> distance along the route -> route segments)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.route import crossing_time, load_route, project_along, route_segments_for_ride
from ariagen_escooter.streams import ANNOTATION_SPECS, coerce_table
from ariagen_escooter.trajectory import local_xy_to_latlon

LAT0, LON0 = 44.14, 12.24


def _figure_eight(tmp_path: Path) -> Path:
    """A loop that crosses itself (like the Cesena candidate route) with 4 segments."""
    s = np.linspace(0, 2 * np.pi, 400)
    x, y = 200 * np.sin(s), 100 * np.sin(2 * s)  # self-crossing at the origin
    lat, lon = local_xy_to_latlon(x, y, LAT0, LON0)
    seglen = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    total = float(seglen[-1])
    bounds = np.linspace(0, total, 5)
    feats = [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": np.column_stack([lon, lat]).tolist()},
              "properties": {"feature": "route", "route_id": "T"}}]
    classes = ["protected_cycle_path", "road_shared_with_traffic", "roundabout", "shared_pedestrian_cycle_path"]
    for k in range(4):
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": []},
                      "properties": {"feature": "segment", "route_id": "T", "segment_id": f"T_S{k + 1:03d}",
                                     "from_m": bounds[k], "to_m": bounds[k + 1], "infrastructure_class": classes[k]}})
    path = tmp_path / "route.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    return path


def _ride(route, speed=5.0, noise=3.0, rate=1.0, seed=1):
    lat, lon = route.lat, route.lon
    x, y = (np.asarray(v) for v in __import__("ariagen_escooter.trajectory", fromlist=["x"]).latlon_to_local_xy(
        lat, lon, LAT0, LON0))
    cum = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    t = np.arange(0, cum[-1] / speed, 1 / rate)
    s = t * speed
    xs, ys = np.interp(s, cum, x), np.interp(s, cum, y)
    rng = np.random.default_rng(seed)
    xs, ys = xs + rng.normal(0, noise, xs.size), ys + rng.normal(0, noise, ys.size)
    glat, glon = local_xy_to_latlon(xs, ys, LAT0, LON0)
    gps = pd.DataFrame({"t_ns": (t * 1e9).astype(np.int64) + 10**12, "lat_deg": glat, "lon_deg": glon,
                        "accuracy_m": noise})
    return gps, s


def test_projection_is_monotonic_through_self_crossing(tmp_path: Path) -> None:
    route = load_route(_figure_eight(tmp_path), "T")
    gps, s_true = _ride(route)
    proj = project_along(route, gps["t_ns"], gps["lat_deg"], gps["lon_deg"])
    ok = proj["along_m"].notna().to_numpy()
    assert ok.mean() > 0.95
    err = np.abs(proj["along_m"].to_numpy()[ok] - s_true[ok])
    assert np.median(err) < 5.0 and err.max() < 25.0  # never jumps to the other branch of the crossing


def test_segments_for_ride_recover_boundaries(tmp_path: Path) -> None:
    route = load_route(_figure_eight(tmp_path), "T")
    gps, _ = _ride(route, speed=5.0)
    seg = route_segments_for_ride(route, gps, "P001_S01_R01")
    assert seg["route_segment_id"].tolist() == ["T_S001", "T_S002", "T_S003", "T_S004"]
    expected = route.segments["from_m"].to_numpy()[1:] / 5.0
    starts = (seg["t_start_ns"].to_numpy()[1:] - 10**12) / 1e9
    assert np.allclose(starts, expected, atol=2.0)  # within ~2 s with 3 m GNSS noise at 1 Hz
    assert (seg["t_end_ns"].to_numpy()[:-1] == seg["t_start_ns"].to_numpy()[1:]).all()  # contiguous
    _, issues = coerce_table(seg, ANNOTATION_SPECS["segments"])
    assert not [i for i in issues if i.level == "error"]


def test_off_route_fixes_stay_unmatched(tmp_path: Path) -> None:
    route = load_route(_figure_eight(tmp_path), "T")
    gps, _ = _ride(route)
    lat, lon = local_xy_to_latlon(np.array([5000.0]), np.array([5000.0]), LAT0, LON0)
    gps.loc[10, ["lat_deg", "lon_deg"]] = [lat[0], lon[0]]
    proj = project_along(route, gps["t_ns"], gps["lat_deg"], gps["lon_deg"])
    assert np.isnan(proj["along_m"].iat[10])


def test_crossing_time_interpolates() -> None:
    t = np.array([0, 10, 20]) * 10**9
    t_cross, j = crossing_time(t, np.array([0.0, 50.0, 100.0]), 75.0)
    assert j == 2 and t_cross == pytest.approx(15e9)
    assert crossing_time(t, np.array([0.0, 50.0, 100.0]), 150.0) == (None, None)


def test_committed_route_geojson_is_loadable(project_root: Path) -> None:
    path = project_root / "docs" / "route" / "cesena_route.geojson"
    route = load_route(path, "CES_A")
    assert 3500 < route.length_m < 4800
    assert (route.segments["to_m"] > route.segments["from_m"]).all()
