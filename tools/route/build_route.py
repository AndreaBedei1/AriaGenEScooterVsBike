"""Build the candidate experimental routes in Cesena from OpenStreetMap data.

Reproducible desk study (no field data): downloads the street network of the
study area from OpenStreetMap (Overpass API, via OSMnx), classifies every way
by infrastructure type, legality for BOTH a conventional bicycle and an
e-scooter and surface suitability, computes legal routes through the
waypoints declared in ``configs/route/cesena_routes.yaml`` and writes:

    docs/route/cesena_route.geojson        routes, segments and points (WGS84)
    docs/route/cesena_route.gpx            one track per route + waypoints
    docs/route/route_segments.csv          infrastructure segments with OSM way ids and flags
    docs/route/route_points.csv            intersections, signals, roundabouts, crossings
    docs/route/route_summary.json          lengths, composition, provenance
    docs/route/cesena_route_map.html       interactive Leaflet map (open in a browser)

The geometry follows real OSM ways (never straight lines between waypoints).
OSM tags do not prove the legal regime of a facility: every output is marked
``verification_status = desk_draft_not_verified_on_site``.

Requirements: the optional ``route`` extra (``uv sync --extra route``):
osmnx, networkx, requests. Network access to Overpass is needed the first time
(responses are cached in ``.cache/osmnx``). Optional checks:
``--elevation`` (OpenTopoData EU-DEM 25 m), ``--brouter`` (independent
routing engine, length comparison) and ``--official-data`` (Comune di Cesena
open data, CC BY 4.0: cycle-path layer and ZTL / pedestrian-area polygons,
used to annotate every segment).

Usage (from the repository root)::

    python tools/route/build_route.py
    python tools/route/build_route.py --elevation --brouter --official-data

Map data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
OSM_ATTRIBUTION = "Map data (c) OpenStreetMap contributors, ODbL 1.0"
VERIFICATION = "desk_draft_not_verified_on_site"
EXTRA_WAY_TAGS = [
    "cycleway", "cycleway:left", "cycleway:right", "cycleway:both", "bicycle", "foot", "segregated",
    "surface", "smoothness", "maxspeed", "oneway:bicycle", "sidewalk", "lit", "width", "motor_vehicle",
    "access", "zone:traffic", "zone:maxspeed", "junction", "bridge", "footway", "crossing", "vehicle",
    "moped", "living_street", "bicycle_road", "cyclestreet",
]
EXTRA_NODE_TAGS = ["crossing", "highway", "traffic_signals", "crossing:markings", "bicycle", "kerb", "barrier", "junction"]
DRIVABLE = {"residential", "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link", "primary",
            "primary_link", "trunk", "trunk_link", "living_street", "service", "road"}
CYCLE_CLASSES = {"protected_cycle_path", "shared_pedestrian_cycle_path", "footway_bicycle_allowed",
                 "painted_cycle_lane", "cycle_crossing"}
# OSM-derived class -> infrastructure class of configs/taxonomy.yaml
TAXONOMY_CLASS = {
    "protected_cycle_path": "protected_cycle_path",
    "shared_pedestrian_cycle_path": "shared_pedestrian_cycle_path",
    "footway_bicycle_allowed": "shared_pedestrian_cycle_path",
    "painted_cycle_lane": "painted_cycle_lane",
    "road_30": "road_shared_with_traffic",
    "road_shared_with_traffic": "road_shared_with_traffic",
    "living_street": "road_shared_with_traffic",
    "service_road": "road_shared_with_traffic",
    "cycle_crossing": "crossing",
    "pedestrian_crossing": "crossing",
    "pedestrian_area": "pedestrian_or_shared_space",
}
COLORS = {
    "protected_cycle_path": "#1b9e77",
    "shared_pedestrian_cycle_path": "#66a61e",
    "painted_cycle_lane": "#a6761d",
    "road_shared_with_traffic": "#e7298a",
    "roundabout": "#d95f02",
    "crossing": "#7570b3",
    "pedestrian_or_shared_space": "#e6ab02",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def first(value: Any) -> Any:
    return value[0] if isinstance(value, list) else value


def text(value: Any) -> str:
    value = first(value)
    return "" if value is None or (isinstance(value, float) and math.isnan(value)) else str(value)


def speed_limit(value: Any) -> float | None:
    try:
        return float(text(value).split()[0])
    except (ValueError, IndexError):
        return None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


# --------------------------------------------------------------------------- #
# Classification and legality
# --------------------------------------------------------------------------- #
def classify(d: dict[str, Any], rules: dict[str, Any]) -> str:
    """OSM way tags -> project class (or 'excluded:<reason>')."""
    h, b, f = text(d.get("highway")), text(d.get("bicycle")), text(d.get("foot"))
    if h in rules["major_highways"]:
        return "excluded:major_road"
    if b == "no" or h in {"steps", "corridor", "construction", "proposed", "bridleway", "elevator", "platform", "busway"}:
        return "excluded:no_bicycles"
    if h == "cycleway":
        if f in {"designated", "yes"} and text(d.get("segregated")) != "yes":
            return "shared_pedestrian_cycle_path"
        return "protected_cycle_path"
    if h == "footway" and text(d.get("footway")) == "crossing":
        return "cycle_crossing" if b in {"designated", "yes"} else "pedestrian_crossing"
    if h in {"footway", "path"}:
        if b == "designated":
            return "shared_pedestrian_cycle_path"
        if b in {"yes", "permissive"}:
            return "footway_bicycle_allowed"
        return "excluded:footway_without_bicycle_access"
    if h == "pedestrian":
        if b in {"yes", "designated", "permissive"} and rules["allow_pedestrian_areas"]:
            return "pedestrian_area"
        return "excluded:pedestrian_area"
    if h in {"service", "track"}:
        if text(d.get("access")) in {"private", "no"}:
            return "excluded:private"
        return "service_road"
    if h in {"residential", "unclassified", "tertiary", "tertiary_link", "living_street", "road"}:
        limit = speed_limit(d.get("maxspeed"))
        if limit is not None and limit > rules["max_speed_limit_kmh"]:
            return "excluded:speed_limit_above_50"
        lanes = " ".join(text(d.get(k)) for k in ("cycleway", "cycleway:left", "cycleway:right", "cycleway:both"))
        if "track" in lanes:
            return "protected_cycle_path"
        if "lane" in lanes:
            return "painted_cycle_lane"
        if h == "living_street":
            return "living_street"
        return "road_30" if limit is not None and limit <= 30 else "road_shared_with_traffic"
    return "excluded:other"


def edge_cost(d: dict[str, Any], cls: str, rules: dict[str, Any]) -> float | None:
    """Routing cost of a directed edge, or None if it may not be ridden by BOTH vehicles."""
    if cls.startswith("excluded"):
        return None
    surface = text(d.get("surface"))
    if surface in rules["excluded_surfaces"]:
        return None
    if not rules["allow_contraflow"] and str(d.get("reversed")) == "True" and str(d.get("oneway")) == "True":
        return None
    w = rules["class_weights"][cls]
    if surface == "wood":
        w *= rules["wood_surface_penalty"]
    elif surface in rules["caution_surfaces"]:
        w *= rules["caution_surface_penalty"]
    elif not surface and cls in CYCLE_CLASSES:
        w *= rules["unknown_surface_penalty_on_paths"]
    if text(d.get("highway")) == "tertiary":
        w *= rules["tertiary_penalty"]
    return float(d["length"]) * w


def flags_for(d: dict[str, Any], cls: str, rules: dict[str, Any]) -> list[str]:
    out = []
    surface = text(d.get("surface"))
    if surface in rules["caution_surfaces"]:
        out.append(f"surface_{surface}_check_grip_and_vibration")
    if not surface:
        out.append("surface_unknown_in_osm")
    if cls == "footway_bicycle_allowed":
        out.append("osm_footway_with_bicycle_access_verify_signs_and_escooter_legality")
    if cls == "shared_pedestrian_cycle_path":
        out.append("shared_with_pedestrians_verify_signs")
    if cls == "pedestrian_crossing":
        out.append("pedestrian_crossing_without_cycle_crossing_in_osm_verify_marking_or_dismount")
    if text(d.get("motor_vehicle")) in {"permit", "destination"} or text(d.get("zone:traffic")):
        out.append("restricted_traffic_zone_verify_ztl_rules")
    if text(d.get("oneway")) == "True" or text(d.get("oneway")) == "yes":
        out.append("oneway_same_direction_for_both_vehicles")
    if speed_limit(d.get("maxspeed")) is None and text(d.get("highway")) in DRIVABLE:
        out.append("speed_limit_not_tagged_verify")
    return out


# --------------------------------------------------------------------------- #
# Network and routing
# --------------------------------------------------------------------------- #
def load_network(cfg: dict[str, Any], cache_dir: Path):
    import osmnx as ox

    ox.settings.use_cache = True
    ox.settings.cache_folder = str(cache_dir)
    ox.settings.http_user_agent = "AriaGenEScooterVsBike-route-study (research, non-commercial)"
    ox.settings.useful_tags_way = sorted(set(ox.settings.useful_tags_way) | set(EXTRA_WAY_TAGS))
    ox.settings.useful_tags_node = sorted(set(ox.settings.useful_tags_node) | set(EXTRA_NODE_TAGS))
    west, south, east, north = cfg["area"]["bbox"]
    return ox.graph_from_bbox((west, south, east, north), network_type="all", simplify=False,
                              retain_all=True, truncate_by_edge=True)


def legal_graph(G, rules: dict[str, Any]):
    import networkx as nx

    H = nx.MultiDiGraph()
    H.graph.update(G.graph)
    for u, v, k, d in G.edges(keys=True, data=True):
        cls = classify(d, rules)
        cost = edge_cost(d, cls, rules)
        if cost is not None:
            H.add_edge(u, v, key=k, **d, cls=cls, cost=cost)
    for n in H.nodes:
        H.nodes[n].update(G.nodes[n])
    largest = max(nx.strongly_connected_components(H), key=len)
    return H.subgraph(largest).copy()


def _point_segment_distance(lat: float, lon: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    k, c = 111_320.0, math.cos(math.radians(lat))
    px, py = lon * k * c, lat * k
    ax, ay, bx, by = a[1] * k * c, a[0] * k, b[1] * k * c, b[0] * k
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def route_through(H, waypoints: list[dict[str, Any]], rules: dict[str, Any]) -> tuple[list[int], list[dict]]:
    """Cheapest legal path through the waypoints (forced edges for cycle_edge/edge snaps)."""
    import networkx as nx

    used: set[tuple[int, int]] = set()

    def cost(u, v, data):
        m = min(e["cost"] for e in data.values())
        return m * (rules["reuse_penalty"] if (u, v) in used or (v, u) in used else 1.0)

    def coords(n):
        return H.nodes[n]["y"], H.nodes[n]["x"]

    def nearest_node(lat, lon):
        return min(H.nodes, key=lambda n: haversine_m(lat, lon, *coords(n)))

    def nearest_edge(lat, lon, cycle_only):
        best = None
        for u, v, d in H.edges(data=True):
            if cycle_only and d["cls"] not in CYCLE_CLASSES:
                continue
            dist = _point_segment_distance(lat, lon, coords(u), coords(v))
            if best is None or dist < best[0]:
                best = (dist, u, v)
        return best

    first_wp = waypoints[0]
    current = nearest_node(first_wp["lat"], first_wp["lon"])
    path, legs = [current], []
    for wp in waypoints[1:]:
        if wp["snap"] in {"cycle_edge", "edge"}:
            dist, u, v = nearest_edge(wp["lat"], wp["lon"], wp["snap"] == "cycle_edge")
            options = []
            for a, b in ((u, v), (v, u)):
                if H.has_edge(a, b):
                    try:
                        options.append((nx.shortest_path_length(H, current, a, weight=cost), a, b))
                    except nx.NetworkXNoPath:
                        continue
            _, a, b = min(options)
            leg = nx.shortest_path(H, current, a, weight=cost) + [b]
        else:
            target = nearest_node(wp["lat"], wp["lon"])
            dist = haversine_m(wp["lat"], wp["lon"], *coords(target))
            leg = nx.shortest_path(H, current, target, weight=cost)
        for x, y in zip(leg[:-1], leg[1:]):
            used.add((x, y))
        legs.append({"label": wp["label"], "snap": wp["snap"], "snap_distance_m": round(float(dist), 1),
                     "n_nodes": len(leg)})
        path += leg[1:]
        current = leg[-1]
    return path, legs


# --------------------------------------------------------------------------- #
# Route description
# --------------------------------------------------------------------------- #
def describe_route(G, H, path: list[int], rules: dict[str, Any]) -> dict[str, Any]:
    edges, cum = [], 0.0
    for u, v in zip(path[:-1], path[1:]):
        d = min(H[u][v].values(), key=lambda e: e["cost"])
        cls = d["cls"]
        tax = "roundabout" if text(d.get("junction")) in {"roundabout", "circular"} else TAXONOMY_CLASS[cls]
        length = float(d["length"])
        edges.append({
            "u": u, "v": v, "from_m": cum, "to_m": cum + length, "length_m": length,
            "osm_way_id": text(d.get("osmid")), "name": text(d.get("name")), "highway": text(d.get("highway")),
            "osm_class": cls, "infrastructure_class": tax, "surface": text(d.get("surface")) or "unknown",
            "maxspeed": text(d.get("maxspeed")), "oneway": text(d.get("oneway")),
            "flags": flags_for(d, cls, rules),
            "coords": [(H.nodes[u]["y"], H.nodes[u]["x"]), (H.nodes[v]["y"], H.nodes[v]["x"])],
        })
        cum += length

    # Segments: runs of edges with the same (infrastructure class, OSM class, street name).
    segments: list[dict[str, Any]] = []
    for e in edges:
        key = (e["infrastructure_class"], e["osm_class"], e["name"])
        if segments and segments[-1]["key"] == key:
            s = segments[-1]
            s["to_m"] = e["to_m"]
            s["coords"].append(e["coords"][1])
            s["edges"].append(e)
        else:
            segments.append({"key": key, "from_m": e["from_m"], "to_m": e["to_m"],
                             "coords": list(e["coords"]), "edges": [e]})
    # Merge very short connector pieces (< 12 m) into the previous segment, except
    # roundabouts and crossings, which are kept as their own units of analysis.
    merged: list[dict[str, Any]] = []
    for s in segments:
        short = (s["to_m"] - s["from_m"]) < 12.0 and s["key"][0] not in {"roundabout", "crossing"}
        if merged and short:
            merged[-1]["to_m"] = s["to_m"]
            merged[-1]["coords"] += s["coords"][1:]
            merged[-1]["edges"] += s["edges"]
        else:
            merged.append(s)
    for i, s in enumerate(merged, start=1):
        lengths = Counter()
        surfaces, ways, flags, speeds, highways = Counter(), [], [], set(), set()
        for e in s["edges"]:
            lengths[e["osm_class"]] += e["length_m"]
            surfaces[e["surface"]] += e["length_m"]
            for w in str(e["osm_way_id"]).strip("[]").split(","):
                w = w.strip()
                if w and w not in ways:
                    ways.append(w)
            flags += [f for f in e["flags"] if f not in flags]
            if e["maxspeed"]:
                speeds.add(e["maxspeed"])
            highways.add(e["highway"])
        s.update({
            "seq": i,
            "infrastructure_class": s["key"][0],
            "osm_class": lengths.most_common(1)[0][0],
            "street_name": s["key"][2] or "(unnamed)",
            "length_m": s["to_m"] - s["from_m"],
            "surface": surfaces.most_common(1)[0][0],
            "osm_highway": ";".join(sorted(highways)),
            "maxspeed": ";".join(sorted(speeds)) or "not_tagged",
            "osm_way_ids": ";".join(ways),
            "flags": ";".join(flags),
        })

    # Points along the route.
    points: list[dict[str, Any]] = []
    node_pos = {}
    for e in edges:
        node_pos.setdefault(e["u"], e["from_m"])
        node_pos.setdefault(e["v"], e["to_m"])
    undirected = G.to_undirected(as_view=True)
    last_inter = -1e9
    for n in path[1:-1]:
        nd = G.nodes[n]
        at = node_pos[n]
        hw = text(nd.get("highway"))
        if hw == "traffic_signals":
            points.append({"kind": "traffic_signals", "node": n, "at_m": at})
        elif hw == "crossing":
            points.append({"kind": "crossing_node", "node": n, "at_m": at,
                           "detail": text(nd.get("crossing")) or text(nd.get("crossing:markings"))})
        roads = {text(d.get("osmid")) for _, _, d in undirected.edges(n, data=True)
                 if text(d.get("highway")) in DRIVABLE and text(d.get("junction")) != "roundabout"}
        names = {text(d.get("name")) for _, _, d in undirected.edges(n, data=True)
                 if text(d.get("highway")) in DRIVABLE and text(d.get("name"))}
        majors = {text(d.get("name")) or text(d.get("highway")) for _, _, d in undirected.edges(n, data=True)
                  if text(d.get("highway")) in rules["major_highways"]}
        if len(roads) >= 3 and len(names) >= 2 and at - last_inter > 25.0:
            points.append({"kind": "intersection", "node": n, "at_m": at, "detail": " / ".join(sorted(names)),
                           "major_road": ";".join(sorted(majors))})
            last_inter = at
    in_rb = False
    for s in merged:
        if s["infrastructure_class"] == "roundabout" and not in_rb:
            points.append({"kind": "roundabout_entry", "node": s["edges"][0]["u"], "at_m": s["from_m"],
                           "detail": s["street_name"]})
        in_rb = s["infrastructure_class"] == "roundabout"
    for p in points:
        p["lat"], p["lon"] = G.nodes[p["node"]]["y"], G.nodes[p["node"]]["x"]
    points.sort(key=lambda p: p["at_m"])

    coords = [(H.nodes[n]["y"], H.nodes[n]["x"]) for n in path]
    composition = Counter()
    for e in edges:
        composition[e["infrastructure_class"]] += e["length_m"]
    osm_composition = Counter()
    for e in edges:
        osm_composition[e["osm_class"]] += e["length_m"]
    surfaces = Counter()
    for e in edges:
        surfaces[e["surface"]] += e["length_m"]
    return {"edges": edges, "segments": merged, "points": points, "coords": coords, "length_m": cum,
            "composition_m": dict(composition.most_common()), "osm_class_m": dict(osm_composition.most_common()),
            "surface_m": dict(surfaces.most_common())}


def duration_estimate(desc: dict[str, Any], rules: dict[str, Any]) -> dict[str, float]:
    lo_kmh, hi_kmh = rules["duration_speed_range_kmh"]
    n_signals = sum(1 for p in desc["points"] if p["kind"] == "traffic_signals")
    d_lo, d_hi = rules["signal_delay_range_s"]
    return {
        "riding_time_min_low": desc["length_m"] / (hi_kmh / 3.6) / 60 + n_signals * d_lo / 60,
        "riding_time_min_high": desc["length_m"] / (lo_kmh / 3.6) / 60 + n_signals * d_hi / 60,
        "assumed_speed_range_kmh": [lo_kmh, hi_kmh],
        "n_traffic_signal_nodes": n_signals,
    }


# --------------------------------------------------------------------------- #
# Optional external checks
# --------------------------------------------------------------------------- #
def elevation_profile(coords: list[tuple[float, float]], step_m: float = 40.0) -> dict[str, Any]:
    import requests

    sample, acc, last = [coords[0]], 0.0, coords[0]
    for c in coords[1:]:
        acc += haversine_m(*last, *c)
        last = c
        if acc >= step_m:
            sample.append(c)
            acc = 0.0
    sample.append(coords[-1])
    elevations: list[float] = []
    for i in range(0, len(sample), 100):
        chunk = sample[i:i + 100]
        locs = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in chunk)
        r = requests.post("https://api.opentopodata.org/v1/eudem25m", data={"locations": locs}, timeout=60)
        r.raise_for_status()
        elevations += [res["elevation"] for res in r.json()["results"]]
    dist = [0.0]
    for a, b in zip(sample[:-1], sample[1:]):
        dist.append(dist[-1] + haversine_m(*a, *b))
    grades = [abs(e2 - e1) / (d2 - d1) * 100 for e1, e2, d1, d2 in zip(elevations, elevations[1:], dist, dist[1:])
              if d2 - d1 > 20 and e1 is not None and e2 is not None]
    ascent = sum(max(0.0, e2 - e1) for e1, e2 in zip(elevations, elevations[1:]) if e1 is not None and e2 is not None)
    valid = [e for e in elevations if e is not None]
    return {"source": "OpenTopoData eudem25m (EU-DEM v1.1, 25 m)", "n_samples": len(sample),
            "min_m": min(valid), "max_m": max(valid), "total_ascent_m": ascent,
            "max_abs_grade_percent_over_samples": max(grades) if grades else None,
            "note": "25 m DEM: bridges and short ramps are not resolved; check on site."}


def brouter_check(waypoints: list[dict[str, Any]], profile: str = "trekking") -> dict[str, Any]:
    import requests

    lonlats = "|".join(f"{w['lon']:.6f},{w['lat']:.6f}" for w in waypoints)
    url = "https://brouter.de/brouter"
    r = requests.get(url, params={"lonlats": lonlats, "profile": profile, "alternativeidx": 0, "format": "geojson"},
                     timeout=120)
    r.raise_for_status()
    props = r.json()["features"][0]["properties"]
    return {"engine": "BRouter (brouter.de)", "profile": profile, "track_length_m": float(props["track-length"]),
            "note": "independent bicycle router through the same waypoints; it does not apply this project's "
                    "e-scooter rules, so only the order of magnitude is comparable"}


OFFICIAL_SOURCES = {
    "cycle_paths": (
        "https://servizisit.unionevallesavio.it/geoserverckan/Cesena/OD_PISTE_CICLABILI_2019_LINE_SDO_preview/wfs"
        "?service=WFS&version=1.3.0&request=GetFeature"
        "&typename=Cesena_public:OD_PISTE_CICLABILI_2019_LINE_SDO_preview&outputformat=application/json"
        "&srsName=EPSG:4326"
    ),
    "ztl": (
        "https://servizisit.unionevallesavio.it/geoserverckan/Cesena/OD_ZTL_SDO_preview/wfs"
        "?service=WFS&version=1.3.0&request=GetFeature&typename=Cesena_public:OD_ZTL_SDO_preview"
        "&outputformat=application/json&srsName=EPSG:4326"
    ),
}
OFFICIAL_ATTRIBUTION = ("Comune di Cesena / Unione dei Comuni Valle del Savio open data (CC BY 4.0): "
                        "'Piste Ciclabili' (2019 layer) and 'Zone Traffico Limitato'")


def load_official(cache_dir: Path) -> dict[str, Any]:
    """Download (once) the official cycle-path and ZTL layers of the Comune di Cesena."""
    import requests

    cache_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, url in OFFICIAL_SOURCES.items():
        path = cache_dir / f"cesena_{key}.geojson"
        if not path.is_file():
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            path.write_bytes(r.content)
        out[key] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _lines(geom: dict[str, Any]) -> list[list[list[float]]]:
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


def _point_in_polygon(lon: float, lat: float, rings: list[list[list[float]]]) -> bool:
    inside = False
    for ring in rings:  # even-odd rule over all rings (holes included)
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def annotate_official(desc: dict[str, Any], official: dict[str, Any], tolerance_m: float = 15.0) -> None:
    """Annotate segments with the official cycle-path category within ``tolerance_m``
    (the layer is published with 4-decimal coordinates, about 10 m) and the ZTL /
    pedestrian-area polygon containing the segment midpoint."""
    existing = []
    for f in official["cycle_paths"]["features"]:
        props = f.get("properties") or {}
        if str(props.get("LEGENDA", "")).upper() != "ESISTENTE":
            continue
        layer = str(props.get("LAYER", "")).strip()
        for line in _lines(f["geometry"]):
            for a, b in zip(line[:-1], line[1:]):
                existing.append(((a[1], a[0]), (b[1], b[0]), layer))
    zones = []
    for f in official["ztl"]["features"]:
        geom, tipo = f["geometry"], str((f.get("properties") or {}).get("TIPO", ""))
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            zones.append((tipo, poly))
    for s in desc["segments"]:
        pts, acc = [s["coords"][0]], 0.0
        for a, b in zip(s["coords"][:-1], s["coords"][1:]):
            seg = haversine_m(*a, *b)
            n = max(1, int(seg // 5.0))
            pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
            acc += seg
        hits = Counter()
        n_hit = 0
        for la, lo in pts:
            near = [(d, layer) for a, b, layer in existing
                    if abs(a[0] - la) < 0.0005 and abs(a[1] - lo) < 0.0007
                    and (d := _point_segment_distance(la, lo, a, b)) <= tolerance_m]
            if near:
                n_hit += 1
                hits[min(near)[1]] += 1
        s["official_cycle_overlap"] = n_hit / len(pts)
        s["official_cycle_category"] = hits.most_common(1)[0][0] if hits else ""
        mid = pts[len(pts) // 2]
        s["official_zone"] = ";".join(sorted({tipo for tipo, poly in zones if _point_in_polygon(mid[1], mid[0], poly)}))
        cat = s["official_cycle_category"][:2]
        suggested = {"01": "protected_cycle_path", "02": "protected_cycle_path_or_shared_path_at_sidewalk_level",
                     "03": "painted_cycle_lane", "04": "shared_pedestrian_cycle_path"}.get(cat, "")
        s["official_suggested_class"] = suggested if s["official_cycle_overlap"] >= 0.5 else ""
        extra = []
        if s["official_cycle_overlap"] >= 0.5 and s["infrastructure_class"] in {"road_shared_with_traffic",
                                                                                 "roundabout"}:
            extra.append("official_cycle_facility_alongside_riders_must_use_it_where_present_cds_art182c9_verify")
        if s["official_zone"]:
            extra.append(f"inside_official_zone_{s['official_zone']}_check_access_and_speed_rules")
        s["flags"] = ";".join([f for f in s["flags"].split(";") if f] + extra)


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #
def write_geojson(path: Path, routes: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    features = []
    for r in routes:
        d = r["desc"]
        features.append({"type": "Feature", "geometry": {"type": "LineString",
                         "coordinates": [[round(lo, 7), round(la, 7)] for la, lo in d["coords"]]},
                         "properties": {"feature": "route", "route_id": r["route_id"], "name": r["name"],
                                        "recommended": r["recommended"], "length_m": round(d["length_m"], 1),
                                        "direction": "as drawn (first to last coordinate)",
                                        "verification_status": VERIFICATION}})
        for s in d["segments"]:
            features.append({"type": "Feature", "geometry": {"type": "LineString",
                             "coordinates": [[round(lo, 7), round(la, 7)] for la, lo in s["coords"]]},
                             "properties": {"feature": "segment", "route_id": r["route_id"],
                                            "segment_id": f"{r['route_id']}_S{s['seq']:03d}",
                                            "infrastructure_class": s["infrastructure_class"],
                                            "osm_class": s["osm_class"], "street_name": s["street_name"],
                                            "from_m": round(s["from_m"], 1), "to_m": round(s["to_m"], 1),
                                            "length_m": round(s["length_m"], 1), "surface": s["surface"],
                                            "maxspeed": s["maxspeed"], "flags": s["flags"],
                                            "official_cycle_overlap": s.get("official_cycle_overlap"),
                                            "official_cycle_category": s.get("official_cycle_category", ""),
                                            "official_zone": s.get("official_zone", ""),
                                            "osm_way_ids": s["osm_way_ids"]}})
        for i, p in enumerate(d["points"], start=1):
            features.append({"type": "Feature", "geometry": {"type": "Point",
                             "coordinates": [round(p["lon"], 7), round(p["lat"], 7)]},
                             "properties": {"feature": "point", "route_id": r["route_id"],
                                            "point_id": f"{r['route_id']}_P{i:03d}", "kind": p["kind"],
                                            "at_m": round(p["at_m"], 1), "detail": p.get("detail", ""),
                                            "major_road": p.get("major_road", "")}})
    data = {"type": "FeatureCollection", "name": "cesena_route", "metadata": meta, "features": features}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_gpx(path: Path, routes: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="AriaGenEScooterVsBike tools/route/build_route.py" '
             'xmlns="http://www.topografix.com/GPX/1/1">',
             f"  <metadata><name>Cesena candidate routes ({VERIFICATION})</name>"
             f"<desc>{html.escape(OSM_ATTRIBUTION)}. Generated {meta['generated_utc']}.</desc></metadata>"]
    for r in routes:
        for wp in r["waypoints"]:
            lines.append(f'  <wpt lat="{wp["lat"]:.6f}" lon="{wp["lon"]:.6f}"><name>{html.escape(r["route_id"])}: '
                         f'{html.escape(wp["label"])}</name></wpt>')
    for r in routes:
        lines.append(f"  <trk><name>{html.escape(r['route_id'])} - {html.escape(r['name'])}</name>"
                     f"<desc>{r['desc']['length_m']:.0f} m; {VERIFICATION}</desc><trkseg>")
        lines += [f'    <trkpt lat="{la:.7f}" lon="{lo:.7f}"/>' for la, lo in r["desc"]["coords"]]
        lines.append("  </trkseg></trk>")
    lines.append("</gpx>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_segments_csv(path: Path, routes: list[dict[str, Any]]) -> None:
    cols = ["route_id", "segment_id", "seq", "from_m", "to_m", "length_m", "infrastructure_class", "osm_class",
            "street_name", "osm_highway", "surface", "maxspeed", "official_cycle_overlap", "official_cycle_category",
            "official_suggested_class", "official_zone", "osm_way_ids", "flags", "verification_status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(cols)
        for r in routes:
            for s in r["desc"]["segments"]:
                w.writerow([r["route_id"], f"{r['route_id']}_S{s['seq']:03d}", s["seq"], f"{s['from_m']:.1f}",
                            f"{s['to_m']:.1f}", f"{s['length_m']:.1f}", s["infrastructure_class"], s["osm_class"],
                            s["street_name"], s["osm_highway"], s["surface"], s["maxspeed"],
                            "" if s.get("official_cycle_overlap") is None else f"{s['official_cycle_overlap']:.2f}",
                            s.get("official_cycle_category", ""), s.get("official_suggested_class", ""),
                            s.get("official_zone", ""), s["osm_way_ids"],
                            s["flags"], VERIFICATION])


def write_points_csv(path: Path, routes: list[dict[str, Any]]) -> None:
    cols = ["route_id", "point_id", "kind", "at_m", "lat", "lon", "osm_node_id", "detail", "major_road"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(cols)
        for r in routes:
            for i, p in enumerate(r["desc"]["points"], start=1):
                w.writerow([r["route_id"], f"{r['route_id']}_P{i:03d}", p["kind"], f"{p['at_m']:.1f}",
                            f"{p['lat']:.7f}", f"{p['lon']:.7f}", p["node"], p.get("detail", ""),
                            p.get("major_road", "")])


def context_network(G, rules: dict[str, Any], bbox: list[float]) -> list[dict[str, Any]]:
    """Cycle facilities of the area (for map context), grouped by OSM way."""
    west, south, east, north = bbox
    ways: dict[str, dict[str, Any]] = {}
    for u, v, d in G.edges(data=True):
        if str(d.get("reversed")) == "True":
            continue
        cls = classify(d, {**rules, "allow_pedestrian_areas": True})
        surface = text(d.get("surface"))
        if cls in {"protected_cycle_path", "shared_pedestrian_cycle_path", "footway_bicycle_allowed",
                   "painted_cycle_lane"}:
            kind = "unsuitable_surface" if surface in rules["excluded_surfaces"] else cls
        elif cls == "pedestrian_area":
            kind = "pedestrian_area"
        else:
            continue
        a, b = (G.nodes[u]["y"], G.nodes[u]["x"]), (G.nodes[v]["y"], G.nodes[v]["x"])
        if not (south <= a[0] <= north and west <= a[1] <= east):
            continue
        ways.setdefault(f"{text(d.get('osmid'))}|{kind}", {"kind": kind, "name": text(d.get("name")),
                                                           "surface": surface or "unknown", "segs": []})["segs"].append(
            [[round(a[0], 6), round(a[1], 6)], [round(b[0], 6), round(b[1], 6)]])
    return [{"id": k.split("|")[0], **v} for k, v in ways.items()]


def write_map(path: Path, routes: list[dict[str, Any]], context: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    payload = {"routes": [], "context": context, "colors": COLORS, "meta": meta}
    for r in routes:
        d = r["desc"]
        arrows, acc = [], 0.0
        for a, b in zip(d["coords"][:-1], d["coords"][1:]):
            seg = haversine_m(*a, *b)
            acc += seg
            if acc >= 120.0 and seg > 3.0:
                arrows.append([round((a[0] + b[0]) / 2, 6), round((a[1] + b[1]) / 2, 6),
                               round(bearing_deg(*a, *b), 1)])
                acc = 0.0
        payload["routes"].append({
            "route_id": r["route_id"], "name": r["name"], "recommended": r["recommended"],
            "length_m": round(d["length_m"]), "duration": r["duration"],
            "segments": [{"id": f"{r['route_id']}_S{s['seq']:03d}", "cls": s["infrastructure_class"],
                          "osm": s["osm_class"], "name": s["street_name"], "len": round(s["length_m"]),
                          "from": round(s["from_m"]), "surface": s["surface"], "maxspeed": s["maxspeed"],
                          "flags": s["flags"], "off_cycle": s.get("official_cycle_overlap"),
                          "off_cat": s.get("official_cycle_category", ""), "off_zone": s.get("official_zone", ""),
                          "coords": [[round(la, 6), round(lo, 6)] for la, lo in s["coords"]]}
                         for s in d["segments"]],
            "points": [{"kind": p["kind"], "at": round(p["at_m"]), "lat": round(p["lat"], 6),
                        "lon": round(p["lon"], 6), "detail": p.get("detail", ""), "major": p.get("major_road", "")}
                       for p in d["points"]],
            "arrows": arrows,
            "start": [round(d["coords"][0][0], 6), round(d["coords"][0][1], 6)],
        })
    template = (Path(__file__).parent / "map_template.html").read_text(encoding="utf-8")
    out = template.replace("/*__PAYLOAD__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    path.write_text(out, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "route" / "cesena_routes.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "route")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache" / "osmnx")
    parser.add_argument("--elevation", action="store_true", help="query OpenTopoData EU-DEM for a slope summary")
    parser.add_argument("--brouter", action="store_true", help="cross-check lengths with BRouter (trekking profile)")
    parser.add_argument("--official-data", action="store_true",
                        help="annotate segments with the Comune di Cesena cycle-path and ZTL open data")
    args = parser.parse_args(argv)

    import osmnx as ox

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    rules = cfg["rules"]
    G = load_network(cfg, args.cache)
    H = legal_graph(G, rules)
    meta = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "generator": "tools/route/build_route.py",
        "config": args.config.resolve().relative_to(ROOT).as_posix(),
        "osmnx_version": ox.__version__,
        "osm_source": "OpenStreetMap via Overpass API (osmnx cache in .cache/osmnx)",
        "attribution": OSM_ATTRIBUTION,
        "bbox_wsen": cfg["area"]["bbox"],
        "network_nodes": G.number_of_nodes(), "network_edges": G.number_of_edges(),
        "legal_graph_nodes": H.number_of_nodes(), "legal_graph_edges": H.number_of_edges(),
        "verification_status": VERIFICATION,
    }
    official = None
    if args.official_data:
        official = load_official(args.cache.parent / "opendata")
        meta["official_data"] = OFFICIAL_ATTRIBUTION
    routes = []
    for rc in cfg["routes"]:
        path, legs = route_through(H, rc["waypoints"], rules)
        desc = describe_route(G, H, path, rules)
        if official is not None:
            annotate_official(desc, official)
        r = {**rc, "desc": desc, "legs": legs, "duration": duration_estimate(desc, rules)}
        if args.elevation:
            try:
                r["elevation"] = elevation_profile(desc["coords"])
            except Exception as exc:  # noqa: BLE001 - optional external service
                r["elevation"] = {"error": str(exc)}
        if args.brouter:
            try:
                r["brouter"] = brouter_check(rc["waypoints"])
            except Exception as exc:  # noqa: BLE001 - optional external service
                r["brouter"] = {"error": str(exc)}
        routes.append(r)
        print(f"{rc['route_id']}: {desc['length_m']:.0f} m, {len(desc['segments'])} segments, "
              f"{len(desc['points'])} points")

    args.out.mkdir(parents=True, exist_ok=True)
    write_geojson(args.out / "cesena_route.geojson", routes, meta)
    write_gpx(args.out / "cesena_route.gpx", routes, meta)
    write_segments_csv(args.out / "route_segments.csv", routes)
    write_points_csv(args.out / "route_points.csv", routes)
    write_map(args.out / "cesena_route_map.html", routes, context_network(G, rules, cfg["area"]["bbox"]), meta)
    summary = {"metadata": meta, "routes": []}
    for r in routes:
        d = r["desc"]
        kinds = Counter(p["kind"] for p in d["points"])
        summary["routes"].append({
            "route_id": r["route_id"], "name": r["name"], "recommended": r["recommended"],
            "length_m": round(d["length_m"], 1), "n_segments": len(d["segments"]),
            "infrastructure_composition_m": {k: round(v, 1) for k, v in d["composition_m"].items()},
            "osm_class_composition_m": {k: round(v, 1) for k, v in d["osm_class_m"].items()},
            "surface_composition_m": {k: round(v, 1) for k, v in d["surface_m"].items()},
            "points": dict(kinds),
            "official_cycle_overlap_m": None if official is None else round(sum(
                seg["length_m"] * seg.get("official_cycle_overlap", 0.0) for seg in d["segments"]), 1),
            "official_zones_m": None if official is None else {
                z: round(sum(seg["length_m"] for seg in d["segments"] if seg.get("official_zone") == z), 1)
                for z in sorted({seg.get("official_zone", "") for seg in d["segments"]}) if z},
            "major_roads_crossed": sorted({p["major_road"] for p in d["points"] if p.get("major_road")}),
            "duration_estimate": {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r["duration"].items()},
            "waypoint_snapping": r["legs"],
            "elevation": r.get("elevation"),
            "brouter_crosscheck": r.get("brouter"),
        })
    (args.out / "route_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
