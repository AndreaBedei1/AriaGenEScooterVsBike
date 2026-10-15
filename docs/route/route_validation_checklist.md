# Route validation checklist (on site, before any acquisition)

To be completed by two members of the team, riding the route **with both vehicles** in the
planned direction, at the planned time of day, on a working day without market. Record photos
of signs and surfaces (no identifiable people), and update `configs/route/cesena_routes.yaml`
and the outputs (`tools/route/build_route.py`) if anything changes. Date, team codes and
outcome go in a dated copy of this list kept with the study documents (not in the repository
if it contains photos of people).

## A. Legality for both vehicles (per segment of `route_segments.csv`)

- [ ] Every path used is signed as cycle path (fig. II.90), shared pedestrian-cycle path
      (II.92/b) or cycle lane, or is a road open to both vehicles - not a plain sidewalk
      (especially segments flagged `osm_footway_with_bicycle_access...`: S003, S005, S021, S026).
- [ ] Where an official cycle facility runs alongside a road segment (flag
      `official_cycle_facility_alongside...`: S001, S006, S007 Rotonda dei Mulini, S013-S014
      Via Cesare Battisti - cycle lane on the carriageway, S019 Viale Gramsci, S023-S024 Ponte
      Europa Unita east end, S029, S032), the facility exists and the route follows it.
- [ ] No contraflow: every one-way is ridden in its direction; no "doppio senso ciclabile" used.
- [ ] Posted speed limits <= 50 km/h (and Zona 30 where expected) on every road segment; 19 of
      32 segments of CES_A have no limit in OSM (`speed_limit_not_tagged`).
- [ ] All segments are inside the "centro abitato" signs.
- [ ] Crossings without cycle marking (`pedestrian_crossing...`: S004, S022, S028): decide
      "ride" (cycle crossing present) or "walk the vehicle" - same rule for both vehicles,
      written into the protocol.
- [ ] ZTL B streets (S009-S012): no sign excludes bicycles or e-scooters; hours of any variable
      pedestrian area checked.
- [ ] No park/green-area paths without cycle-path signs.

## B. Safety and practicality

- [ ] Surfaces suitable for 8-10" e-scooter wheels on every segment (record: asphalt, pavers,
      cracks, tram/rail lines, kerb drops); wood deck on Ponte del Risorgimento: grip when wet.
- [ ] Kerb ramps at every path transition; no steps.
- [ ] Rotonda dei Mulini and the two small roundabouts: how cyclists are expected to traverse
      them (carriageway or external cycle ring); visibility.
- [ ] Piazzale del Risorgimento and the junction Machiavelli / Zuccherificio / Europa
      (Via Emilia axis): signal phases, waiting areas, conflict points.
- [ ] Bridge ramps: gradient and visibility.
- [ ] Places where the following researcher can ride safely behind the participant.
- [ ] Safe start/end area on campus (static calibration, gaze targets, vehicle parking).
- [ ] Sensitive places along the route (schools, health facilities, places of worship) where
      recording must be paused or avoided.
- [ ] Road works or temporary diversions.

## C. Measurements to take

- [ ] Ride time with each vehicle at a normal pace (two runs) -> update the duration estimate.
- [ ] GNSS track of a test recording vs `cesena_route.gpx` (distance of fixes from the line).
- [ ] Landmarks for segment boundaries and for speed validation (10 surveyed points with photos).
- [ ] Locations of the gaze-validation targets (start/end).
- [ ] Mobile coverage (companion app) and GNSS availability under trees/bridges.

## D. Documentation

- [ ] Update `configs/route/cesena_routes.yaml` waypoints if the legal facility differs from the
      draft; rebuild the outputs; set `verification_status` in the outputs to the date of the
      check (edit `VERIFICATION` in `tools/route/build_route.py` only after the full check).
- [ ] Note open issues for the project lead (e.g. ask the Comune's Servizio Mobilità about
      signs or ordinances).
- [ ] Choose CES_A or CES_B (or a corrected variant) and freeze the route id used in the
      manifests.
