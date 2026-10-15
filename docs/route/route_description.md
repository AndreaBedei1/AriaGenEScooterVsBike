# Experimental route in Cesena (desk draft)

**Status: DESK DRAFT, NOT VERIFIED ON SITE.** The geometry follows real OpenStreetMap ways and
was cross-checked with the Comune di Cesena open data, an independent router and a terrain
model, but OSM tags do not prove signs, ordinances or surface conditions. The checklist in
[route_validation_checklist.md](route_validation_checklist.md) must be completed on site before
any acquisition.

Files: interactive map [cesena_route_map.html](cesena_route_map.html) (open in a browser;
needs internet for the map tiles), [cesena_route.geojson](cesena_route.geojson),
[cesena_route.gpx](cesena_route.gpx), [route_segments.csv](route_segments.csv),
[route_points.csv](route_points.csv), [route_summary.json](route_summary.json). Legal and
infrastructure sources: [legal_and_infrastructure_notes.md](legal_and_infrastructure_notes.md).
Rebuild: `uv sync --extra route` then
`python tools/route/build_route.py --elevation --brouter --official-data`.

## 1. Recommendation

| | **CES_A - Savio loop (recommended)** | CES_B - east loop (alternative) |
|---|---|---|
| Length (OSM geometry) | **4.25 km** | 3.66 km |
| Independent check (BRouter, same waypoints, trekking profile) | 3.96 km | 3.63 km |
| Estimated riding time at 12-16 km/h (+ up to 30 s per signal) | **16-24 min** | 14-21 min |
| Infrastructure (by length) | road shared with traffic 2.10 km; shared pedestrian-cycle paths 1.55 km; protected cycle path 0.38 km; roundabouts 0.18 km (3); crossings 0.04 km | road 2.29 km; shared paths 0.96 km; protected cycle path 0.15 km; roundabouts 0.22 km (2); crossings 0.04 km |
| Along official cycle facilities (Comune layer, +-15 m) | 2.77 km (65 %) | 2.10 km (57 %) |
| Junctions on the route | 12 intersections, 5 signalised nodes, 3 roundabout entries | 13, 5, 2 |
| Historic centre | skirts the north-east edge (ZTL B, about 0.6 km on Via Mura F. Comandini / Via Mura Porta Fiume / Via Armellini) | same |
| Savio river | crossed twice (Ponte del Risorgimento cycle path, Ponte Europa Unita) | not crossed |
| Elevation (EU-DEM 25 m) | 25-42 m, total ascent ~31 m (bridge ramps; DEM does not resolve bridges) | 25-42 m, ~27 m |

**Why CES_A**: its length and expected duration match the 15-20 min target; it combines
separated cycle paths, shared pedestrian-cycle paths, a cycle lane on the carriageway
(Via Cesare Battisti, official layer), moderate-traffic urban streets, signalised
intersections, three roundabouts, river bridges and the edge of the historic centre, with
plausible pedestrian and cyclist interactions; and it is a single loop without riding the same
stretch twice. **CES_B** is the fallback if the west-bank links (paths along Viale Matteotti and
Viale della Resistenza, bridge decks) turn out unsuitable on site; it is shorter, has more road
riding and repeats the Machiavelli path in both directions.

## 2. Itinerary of CES_A (clockwise)

Start and end: Campus universitario di Cesena (ex Zuccherificio), Via dell'Università 50.

1. **Campus -> Via Machiavelli cycle path (southbound)**, 0.0-0.8 km: path parallel to Via
   Machiavelli (OSM: cycleway, then footway with bicycle access, paving stones; official layer:
   existing cycle path at sidewalk level). Crossing at the Ponte Europa Unita junction.
2. **To Rotonda dei Mulini**, 0.8-1.07 km: a short stretch on Via Machiavelli (official layer
   shows a separated cycle path alongside: if present, both vehicles must use it), signalised
   junction with Via Zuccherificio / Viale Europa (urban Via Emilia axis: crossed, not ridden),
   **Rotonda dei Mulini** (single-lane roundabout; the official layer shows a cycle facility
   around it: check which one riders must use).
3. **Via Mulini / Viale Rasi e Spinelli eastbound**, 1.07-1.40 km: urban street, signalised
   junction with Via Curiel.
4. **Historic-centre edge**, 1.40-2.01 km: Piazzetta Porta Trova, **Via Mura Federico
   Comandini** (one-way southbound, ZTL B: rules apply to motor vehicles only), Via Mura Porta
   Fiume (one-way), Via Carlo Armellini.
5. **Via Cesare Battisti westbound**, 2.01-2.35 km: 30 km/h street with a cycle lane on the
   carriageway (official layer; Biciplan "present and optimal"), signalised crossing with Via
   Curiel / Via Rosselli, Piazzale del Risorgimento (Biciplan critical point).
6. **Ponte del Risorgimento cycle path westbound**, 2.35-2.66 km: separated path beside the
   bridge (deck tagged wood in OSM: grip when wet), then **cycle path along Viale Matteotti**
   (separated track beside the urban Via Emilia), 2.66-2.90 km.
7. **North along Viale della Resistenza / Viale Gramsci**, 2.90-3.24 km: shared path (official
   cycle path alongside Viale Gramsci: if the router's short road stretch has a parallel path,
   use the path), small roundabout at the west end of Ponte Europa Unita.
8. **Ponte Europa Unita eastbound**, 3.24-3.56 km: side path of the bridge (footway with
   bicycle access in OSM; official layer: cycle path), crossing at the east end, roundabout.
9. **Via Calvino cycle path and residential streets back to campus**, 3.56-4.25 km: shared path
   along Via Calvino, then Via Quasimodo, Via Sapegno and Via Saba (residential, Zona 30 to
   verify) to Via dell'Università.

Segment-by-segment data (ids `CES_A_S001`..`S032`, distances, OSM way ids, surfaces, official
category, flags) are in [route_segments.csv](route_segments.csv); intersections, signals,
roundabout entries and crossing nodes with their distance along the route in
[route_points.csv](route_points.csv).

## 3. How the route was built

1. **Network**: all OSM ways in the area (8,238 nodes, 16,606 directed edges; OSMnx 2.1.1,
   Overpass API, 2026-10-15), tags kept: highway, cycleway*, bicycle, foot, segregated,
   surface, maxspeed, oneway, junction, crossing, access.
2. **Classification and legality for BOTH vehicles**: excluded were primary/secondary/trunk
   roads (ridden along; crossing at junctions allowed), roads with limits above 50 km/h, ways
   without bicycle access, pedestrian areas, private service roads, surfaces unsuitable for
   small wheels (gravel, compacted, dirt, grass, sett, cobblestone...), and **contraflow**
   (both vehicles must ride every segment in the same direction; e-scooters may not use
   contraflow cycle lanes).
3. **Legal routing** (largest strongly connected component: 5,152 nodes) through waypoints that
   force the route onto the intended places, with a cost that prefers cycle facilities, penalises
   wood/paving stones and unknown surfaces, and penalises re-using an edge.
4. **Checks**: Comune di Cesena open data (cycle paths 2019 layer and ZTL polygons, CC BY 4.0)
   annotated on every segment; BRouter length comparison; EU-DEM elevation profile.
5. **Flags** on every segment for on-site verification: surface unknown or caution, footway with
   bicycle access (is it signed as cycle path / shared path?), pedestrian crossing without cycle
   marking (ride or dismount?), restricted traffic zone, one-way, untagged speed limit, official
   cycle facility alongside a road segment (CdS art. 182 c. 9: if present it must be used).

## 4. Legal constraints applied (as of 15 Oct 2026; see legal notes for sources)

- E-scooters: helmet for all ages; minimum age 14; identification plate ("contrassegno")
  mandatory since 17/05/2026 and third-party insurance since 16/07/2026; direction indicators
  and brakes on both wheels; motor <= 0.5 kW; 20 km/h maximum (6 km/h in pedestrian areas);
  only urban roads with limits <= 50 km/h, cycle paths, cycle lanes and shared pedestrian-cycle
  paths; never on sidewalks; no contraflow; both hands on the handlebar.
- Bicycles: cycle facilities must be used where present (art. 182 c. 9); the same facilities
  are used by both vehicles in this study.
- ZTL rules in Cesena apply to motor vehicles; pedestrian areas are avoided by design (both
  vehicles would have to keep walking pace or dismount).
- Parks and green areas are forbidden to both except on signed cycle paths (municipal rule).
- **Helmets for cyclists too** (not mandatory for adults) to keep the two conditions
  comparable and safe.

## 5. Known issues and open points

- The paths along Via Machiavelli and on Ponte Europa Unita are tagged in OSM as footways with
  bicycle access; the official layer calls the Machiavelli one a cycle path at sidewalk level.
  **Signs decide** whether an e-scooter may ride there.
- The router used short road stretches where the official layer shows a parallel cycle
  facility (Via Machiavelli near Rotonda dei Mulini; Viale Gramsci; Rotonda dei Mulini itself):
  probably missing connections in OSM. On site, the legal facility must be followed and the
  route file updated.
- Via Zuccherificio, Piazzale del Risorgimento, Ponte del Risorgimento and Viale Matteotti carry
  the urban Via Emilia traffic: the route only crosses them or rides their separated cycle
  tracks.
- Surfaces: 1.38 km of CES_A has no surface tag; 0.64 km is paving stones (vibration on the
  e-scooter) and 0.31 km wood deck (grip when wet).
- North of the campus, OSM tags Via Machiavelli at 70 km/h: not used.
- Weekly market (Wednesday, Saturday) and events in the centre: avoid these days.
- Elevation from a 25 m DEM does not resolve bridges: ramps to check on site.
