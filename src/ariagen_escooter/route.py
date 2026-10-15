"""Route alignment: GNSS fixes -> distance along the planned route -> route segments.

The candidate routes (docs/route/cesena_route.geojson, built by
tools/route/build_route.py) define physical segments by distance along the
route (``from_m`` / ``to_m``). Aligning every ride to the same segments lets
the analysis compare the SAME place across rides, trials and vehicles - the
core of the within-participant design - independently of spontaneous events.

Method (linear referencing with a monotonic search window):

1. route polyline and fixes are projected to a local metric frame;
2. each fix is projected onto the polyline, searching only between
   ``previous position - backtrack_m`` and ``previous position +
   max_speed_mps x dt + slack_m`` (the loop crosses itself, so an
   unconstrained nearest projection would jump between visits);
3. fixes farther than ``max_offset_m`` from the route stay unmatched (NaN):
   detours are never forced onto the route;
4. the time at which a segment boundary is crossed is interpolated between the
   two fixes that bracket it; a segment is reported only if both boundaries
   are crossed, together with an uncertainty estimate (GNSS accuracy / speed).

Boundaries from 1 Hz GNSS are approximate (metres to a second): manual review
of the boundaries of short units (crossings, roundabouts) on the anonymised
video is part of the validation plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.trajectory import latlon_to_local_xy


@dataclass(frozen=True)
class RouteGeometry:
    route_id: str
    lat: np.ndarray
    lon: np.ndarray
    segments: pd.DataFrame  # segment_id, from_m, to_m, infrastructure_class (+ extra)

    @property
    def length_m(self) -> float:
        x, y = latlon_to_local_xy(self.lat, self.lon, float(self.lat[0]), float(self.lon[0]))
        return float(np.sum(np.hypot(np.diff(x), np.diff(y))))


def load_route(path: Path, route_id: str) -> RouteGeometry:
    """Route line and its segments from the GeoJSON written by tools/route/build_route.py."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    line = None
    rows = []
    for f in data["features"]:
        props = f.get("properties") or {}
        if props.get("route_id") != route_id:
            continue
        if props.get("feature") == "route":
            line = np.asarray(f["geometry"]["coordinates"], dtype=np.float64)
        elif props.get("feature") == "segment":
            rows.append({k: props.get(k) for k in ("segment_id", "from_m", "to_m", "infrastructure_class",
                                                     "osm_class", "street_name")})
    if line is None:
        raise ValueError(f"route {route_id!r} not found in {Path(path).name}")
    seg = pd.DataFrame(rows).sort_values("from_m").reset_index(drop=True)
    return RouteGeometry(route_id, line[:, 1], line[:, 0], seg)


def _polyline(route: RouteGeometry) -> tuple[np.ndarray, np.ndarray, float, float]:
    lat0, lon0 = float(np.mean(route.lat)), float(np.mean(route.lon))
    x, y = latlon_to_local_xy(route.lat, route.lon, lat0, lon0)
    pts = np.column_stack([x, y])
    cum = np.r_[0.0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    return pts, cum, lat0, lon0


def project_along(
    route: RouteGeometry,
    t_ns: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    *,
    max_offset_m: float = 25.0,
    backtrack_m: float = 15.0,
    max_speed_mps: float = 15.0,
    slack_m: float = 30.0,
    start_window_m: float = 150.0,
) -> pd.DataFrame:
    """Distance along the route of each fix (NaN when off-route or unmatched)."""
    pts, cum, lat0, lon0 = _polyline(route)
    a, b = pts[:-1], pts[1:]
    ab = b - a
    seg_len2 = np.maximum(np.sum(ab * ab, axis=1), 1e-12)
    x, y = latlon_to_local_xy(np.asarray(lat, float), np.asarray(lon, float), lat0, lon0)
    t = np.asarray(t_ns, dtype=np.int64)
    along = np.full(t.size, np.nan)
    offset = np.full(t.size, np.nan)
    prev_s, prev_t = None, None
    for i in range(t.size):
        if not (np.isfinite(x[i]) and np.isfinite(y[i])):
            continue
        p = np.array([x[i], y[i]])
        u = np.clip(np.sum((p - a) * ab, axis=1) / seg_len2, 0.0, 1.0)
        proj = a + u[:, None] * ab
        dist = np.hypot(*(p - proj).T)
        s_cand = cum[:-1] + u * np.sqrt(seg_len2)
        if prev_s is None:
            lo, hi = 0.0, start_window_m
        else:
            dt = (t[i] - prev_t) / NS_PER_S
            lo, hi = prev_s - backtrack_m, prev_s + max_speed_mps * dt + slack_m
        ok = (s_cand >= lo) & (s_cand <= hi) & (dist <= max_offset_m)
        if not ok.any():
            continue
        k = np.flatnonzero(ok)[np.argmin(dist[ok])]
        along[i], offset[i] = s_cand[k], dist[k]
        prev_s, prev_t = max(s_cand[k], prev_s or 0.0), t[i]
    return pd.DataFrame({"t_ns": t, "along_m": along, "offset_m": offset})


def crossing_time(
    t_ns: np.ndarray, along: np.ndarray, s: float, tol_m: float = 1.0
) -> tuple[float | None, int | None]:
    """First time the (monotonic) along-route distance reaches ``s`` (interpolated), and the bracket index.

    ``tol_m`` accepts a first/last matched fix within that distance of ``s``
    (used at the start and end of the route, where no bracketing fix exists).
    """
    ok = np.isfinite(along)
    t, d = np.asarray(t_ns, dtype=np.int64)[ok], np.asarray(along)[ok]
    idx = np.flatnonzero(d >= s)
    if idx.size == 0:
        if d.size and d.max() >= s - tol_m:
            return float(t[int(np.argmax(d))]), None
        return None, None
    j = int(idx[0])
    if j == 0:
        return (float(t[0]) if d[0] - s < tol_m else None), None
    d0, d1 = d[j - 1], d[j]
    frac = (s - d0) / (d1 - d0) if d1 > d0 else 1.0
    return float(t[j - 1] + frac * (t[j] - t[j - 1])), j


def route_segments_for_ride(
    route: RouteGeometry,
    gps: pd.DataFrame,
    recording_id: str,
    *,
    max_offset_m: float = 25.0,
    end_tolerance_m: float = 20.0,
) -> pd.DataFrame:
    """Annotation table (segments.csv schema) of the route segments traversed in a ride.

    The first and last boundary of the route (start/end of the loop) accept the
    first/last matched fix within ``end_tolerance_m``."""
    proj = project_along(route, gps["t_ns"].to_numpy(), gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy(),
                         max_offset_m=max_offset_m)
    t, along = proj["t_ns"].to_numpy(), proj["along_m"].to_numpy()
    acc = gps["accuracy_m"].to_numpy(dtype=float) if "accuracy_m" in gps.columns else np.full(len(gps), np.nan)
    rows = []
    first_m, last_m = float(route.segments["from_m"].min()), float(route.segments["to_m"].max())
    for _, seg in route.segments.iterrows():
        s0, s1 = float(seg["from_m"]), float(seg["to_m"])
        t0, j0 = crossing_time(t, along, s0, end_tolerance_m if s0 <= first_m else 1.0)
        t1, j1 = crossing_time(t, along, s1, end_tolerance_m if s1 >= last_m else 1.0)
        if t0 is None or t1 is None or t1 <= t0:
            continue
        unc = []
        for j in (j0, j1):
            if j is None:
                continue
            ok = np.flatnonzero(np.isfinite(along))
            a_, b_ = ok[j - 1], ok[j]
            speed = (along[b_] - along[a_]) / max((t[b_] - t[a_]) / NS_PER_S, 1e-9)
            if speed > 0.5 and np.isfinite(acc[a_]):
                unc.append(acc[a_] / speed)
        rows.append({
            "segment_id": f"{recording_id}_SEG{len(rows) + 1:03d}",
            "t_start_ns": int(round(t0)),
            "t_end_ns": int(round(t1)),
            "infrastructure_class": seg["infrastructure_class"],
            "route_segment_id": seg["segment_id"],
            "source": "map_matching",
            "annotator": "",
            "notes": (f"GNSS linear referencing on {route.route_id}; boundary uncertainty ~"
                      f"{max(unc):.1f} s" if unc else f"GNSS linear referencing on {route.route_id}"),
        })
    return pd.DataFrame(rows, columns=["segment_id", "t_start_ns", "t_end_ns", "infrastructure_class",
                                       "route_segment_id", "source", "annotator", "notes"])
