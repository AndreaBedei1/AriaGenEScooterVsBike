# Research gaps

Gaps identified from the reviewed literature ([literature_review.md](literature_review.md)),
ordered from the most to the least addressable with our design. Each gap states what exists,
what is missing, and whether our study can close it. The resulting contribution options are
weighed in `docs/research/scientific_contribution.md`.

| # | Gap | What exists | What is missing | Can we address it? |
|---|---|---|---|---|
| G1 | **Route-scale, counterbalanced within-participant comparison of bicycle and e-scooter** | Same riders on both vehicles: Pashkevich 2022 (50 m, one pass, random order, N = 12), Trefzger 2021 (200 m, fixed order, N = 24), Dozza 2022/2023 and Li 2023 (test track, kinematics), Su 2025 (VR, physiology) | Several infrastructure types along one route, counterbalanced order, repetitions, naturalistic traffic, multimodal measures | **Yes**, core of the design; pilot N = 3 only for feasibility |
| G2 | **Infrastructure x vehicle interaction in the field** | Surface x vehicle on gaze (Trefzger 2021, one street); geometry x vehicle on kinematics (Distefano 2026, one mini-roundabout); e-scooter-only infrastructure effects (Kegalle 2025; Hristov 2024; Rizehbandi 2026) | Several infrastructure types x both vehicles with gaze/head data, with multiple segments per type | **Partly**: depends on the number of segments per type on the Cesena route and on the confirmatory sample |
| G3 | **Time-locked links from fixated objects to subsequent movement** | Segment-level correlations (Kegalle 2025, n.s. on re-analysis); slowing when attending a vehicle in a scripted encounter (Berge 2025) | Event-level latencies from first gaze on a specific road user to a measurable action, compared across vehicles, with explicit handling of unidentifiable order | **Partly**: depends on event counts per ride and on detector/tracker validity; exploratory in the pilot |
| G4 | **Reliability of gaze, head and speed metrics within persons** | Speed test-retest r = 0.96 (Berge 2025); repeatability on a track (Al-Hakeem 2026, abstract) | ICC of gaze/head metrics across trials and vehicles in the field | **Yes, if 2 trials per vehicle** are recorded |
| G5 | **Head behaviour across vehicles** | Cyclists: QuantiBike, Rawson 2026 (abstract); e-scooter: Chen 2025 (N = 5); shoulder glances: Pils 2021 (abstract) | Within-person comparison of head scanning between vehicles, decomposed into head and eye contributions | **Yes** (VIO + gaze); vibration must be separated |
| G6 | **Validated riding dynamics from a single head-worn device** | No published validation of head-worn VIO/IMU speed for micromobility (search in additional literature, section g) | Accuracy and coverage of VIO speed, stops and decelerations vs GNSS and annotated video while riding | **Yes**, methodological contribution |
| G7 | **Automatic semantic gaze on egocentric riding video** | Detector failure (Kegalle 2025, recall 10-15 %); single-class YOLO with 4 deg tolerance (Berge 2025); YOLO benchmarks on e-scooter video (Chen 2025 i3CE) | Validated multi-class semantic gaze (surfaces + road users + object identity) on fisheye head-worn video, with gaze uncertainty | **Partly**: benchmark planned; no public model has an e-scooter class |
| G8 | **Hand behaviour on the handlebar** | Crash risk of one-handed e-scooter riding (Pai & Dozza 2025); hand-signal studies with novices (Löcken 2020) | Any wearable hand-tracking evidence while riding; detection coverage under handlebar occlusion | **Exploratory** (RQ5): feasibility of the measurement first |
| G9 | **Physiological load in the field across vehicles** | VR only (Su 2025); HRV field cycling with weak contrasts (Fitch 2020, abstract) | Field comparison controlling exertion (pedalling vs standing) | **Not as a confirmatory aim**: PPG exploratory only |
| G10 | **Methodological reporting** | Undisclosed fixation thresholds, manual AOIs without agreement, pseudo-replication (Kchour 2025; Ma 2024; several primary studies) | Transparent, reproducible pipeline with data-quality reporting | **Yes**: quality reports, configuration hashes, open code |

## Ideas that are already substantially covered

- "First eye-tracking comparison of cyclists and e-scooter riders": **covered** by Pashkevich
  2022 and Trefzger 2021 (single short segments). Our claim must be about route scale,
  counterbalancing, repetitions, multimodality and segment matching.
- "E-scooter gaze differs by infrastructure": **covered** for e-scooters alone (Kegalle 2025;
  Hristov 2024; Rizehbandi 2026; Chen 2025).
- "Project Aria glasses can record gaze while cycling": **shown** for Gen 1 by Hardin 2026
  (one rider); our novelty is Gen 2, two vehicles, head/hand streams and on-device VIO.
- "Bicycles brake harder than e-scooters": **covered** on test tracks (Dozza 2022, 2023); in the
  field we can only estimate decelerations from head motion, not braking performance.
