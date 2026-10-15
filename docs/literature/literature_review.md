# Literature review

Scope: visual attention, head and hand behaviour and riding dynamics of e-scooter riders and
cyclists, with emphasis on what a single head-worn device (Meta Project Aria Gen 2) can measure
in a within-participant, bicycle-vs-e-scooter field study. Compiled October 2026.

Companion files: [paper_matrix.csv](paper_matrix.csv) (one row per paper, comparable fields),
[replication_plan.md](replication_plan.md), [research_gaps.md](research_gaps.md),
[kegalle_replication.md](kegalle_replication.md), [references.bib](references.bib).

## 0. How the review was done

- **Corpus.** All 21 PDFs of the local `paper/` folder (not versioned, see `paper/README.md`)
  were read in full: Methods, Results, Discussion, tables and figures. For the book
  `978-3-031-47612-9.pdf` only the relevant chapter (Hristov et al., pp. 151-158) was read.
  Pashkevich et al. (2022), requested as a priority but missing from the folder, was read in full
  as HTML version of record (see section 7). A targeted search added 35 further items
  (2018-2026), each verified on Crossref/DataCite; their access level (full text, partial,
  abstract only) is stated wherever they are used.
- **Extraction.** Each paper was extracted into a 27-point structured note (problem, hypotheses,
  participants, vehicles, environment, route, sensors, rates, synchronisation, algorithms, CV,
  segmentation, detection/tracking, eye-tracking processing, fixation definitions, kinematics,
  statistics, results, effect sizes, limitations, code/data, reproducibility, opportunities,
  useful tables/equations, relevance, replication category) with a page reference for every
  important claim. Numbers below are as printed; effect sizes computed by us are marked
  "(computed)". Our own critical remarks are marked **Assessment**.
- **Page references** are "p. printed page" (PDF page in brackets when different) and section.
  For Pashkevich (2022) only section/table numbers are available (HTML version).
- **What this review is not**: it is not a systematic review (no protocol registration, no
  risk-of-bias scoring); it is a structured critical reading targeted at study design.

## 1. Most pertinent papers and why

| Rank | Paper | Why it matters for us |
|---|---|---|
| 1 | **Kegalle et al. 2025** (IMWUT; arXiv v1 in `paper/`) | Closest methodological baseline: naturalistic e-scooter riding with eye tracking, 1 Hz speed, change points, infrastructure comparison (shared path / cycle lane / roadway), encounters, public data. E-scooter only. Our independent re-analysis of their public data is in [kegalle_replication.md](kegalle_replication.md). |
| 2 | **Pashkevich et al. 2022** (CSTP) | The same 12 participants walked, cycled and rode an e-scooter (random order) with a Tobii Pro Glasses 2: the direct precedent for a within-participant bicycle-vs-e-scooter gaze comparison - but one 50 m segment, one pass, manual AOIs. |
| 3 | **Trefzger et al. 2021** (INFORMATIK, not in `paper/`, open access) | 24 riders on both a bicycle and an e-scooter with eye tracking on a 200 m street with good/poor surface; fixed order (bicycle first). Shows a vehicle x surface interaction on near gaze. Together with Pashkevich it **removes "first bike-vs-e-scooter gaze comparison" as a possible claim**. |
| 4 | **Dozza et al. 2023** (JSR) and **Dozza et al. 2022** (JSR, not in `paper/`) | Within-subject bicycle vs e-scooter longitudinal control on a test track (N = 34; N = 6): reference values for accelerations, decelerations, braking distance and response time. Vehicle sensors, not wearables. |
| 5 | **von Stülpnagel 2020** (TRF) | Field cycling, fixation-level mixed models, sight-vector length and gaze angle vs travel direction - two metrics that Aria pose + gaze ray can compute automatically, where the original used manual annotation. |
| 6 | **Hristov et al. 2024** (Springer chapter) | E-scooter gaze by facility type and junction zone (far / near / crossing) in Berlin and Munich; reusable zoning; no statistics. |
| 7 | **Matviienko et al. 2023** (QuantiBike, SUI) | Head-rotation metrics (+-20 deg deadband; frequency, duration, angle) related to perceived safety in VR and outdoors (cyclists). Directly computable from Aria head pose. |
| 8 | **Kchour et al. 2025** (Sensors review) and **Ma et al. 2024** (TRF review) | Map of cyclist eye-tracking methods: fixation thresholds, AOI metrics, gaps (manual AOIs, no head/kinematics in field, workload vs stress confusion). Both list Pashkevich 2022 as the only bicycle/e-scooter gaze comparison they include. |
| 9 | **Hardin et al. 2026** (arXiv, not in `paper/`) | First micromobility use of Project Aria glasses (Gen 1, one cyclist, 12 runs, gaze only); its stated future work (object-level gaze, head/IMU) is what we plan. |
| 10 | **Berge et al. 2025** (TRF, not in `paper/`) | Automatic object-level gaze for cyclists (YOLO boxes, gaze-box angle < 4 deg) linked to slowing; speed test-retest r = 0.96 across sessions. |

The other papers of the folder provide reference values (Cameli 2025, Zhang 2026, Vetturi 2023,
Ma 2021), concepts for gaze control (Vansteenkiste 2013, 2014; Mantuano 2017; Schmidt & von
Stülpnagel 2018), workload and physiology caveats (Kchour 2026; Guo 2023; Ágoston & Borsos
2026), e-scooter safety context (Mehranfar & Jones 2024) or tooling (Taia Alaoui 2021).

## 2. What is known, by theme

### 2.1 Bicycle vs e-scooter: direct comparisons

- **Speed.** In field studies the two modes ride at similar mean speeds on the same infrastructure:
  Pashkevich 2022: bicycle 16.8 km/h (10.2-22.8), e-scooter 16.5 km/h (9.5-23.4),
  t(11) = -0.531, p = 0.607 (Sec. 3.1, Fig. 11); dz = 0.15 (computed). Trefzger 2021: the
  e-scooter was about 2 km/h slower on both surfaces (15.93 vs 17.84 km/h on good surface;
  15.34 vs 18.48 on poor), with mostly novice e-scooter riders. Ma 2021 (one rider): 8.07 vs
  8.78 mph (p. 10, Sec. 5). **Implication**: speed differences between modes are small relative
  to between-rider and between-segment variation; they cannot be the main expected effect.
- **Longitudinal control.** On a test track, bicycles braked harder than e-scooters: comfort
  -1.50 +- 0.51 vs -1.28 +- 0.42 m/s^2, harsh -3.00 +- 1.29 vs -2.21 +- 0.59, unexpected
  -3.60 +- 1.28 vs -2.23 +- 0.71 (Dozza 2023, Table 3, p. 30; vehicle effect F = 39,
  p << 0.001, p. 27); e-scooter response time longer (F = 6.7) and stop line overshot in 61 % of
  harsh e-scooter stops vs 14 % for the unassisted bicycle (p. 27, Sec. 3.2-3.3). Vetturi 2023
  found no vehicle effect in deceleration-vs-initial-speed models but with 3 riders
  (acc = 0.759 + 0.445 Vi, R^2 = 0.971, p. 412-413). Li 2023 (partial full text): e-scooters
  braked less effectively; no significant steering difference.
- **Interaction with other road users.** From infrastructure cameras in Berlin (between-subject),
  e-scooter riders used pedestrian infrastructure more than cyclists (16.3/50.7/67.7 % vs
  9.5/20.5/46.3 % at three sites) and rode faster in head-on pedestrian encounters
  (1.72 +- 0.50 vs 1.26 +- 0.38 m/s, r = 0.29) (Zhang 2026, pp. 6-7, Sec. 3). Pashkevich 2022:
  e-scooter manoeuvres correlated with overtaken/passed pedestrians (r(10) = 0.81) but not for
  bicycles (r(10) = 0.40) (Sec. 3.2, Tab. 2).
- **Gaze.** Pashkevich 2022 (Tab. 3): share of fixations on the roadway 42.5 % (bicycle) vs
  38.6 % (e-scooter), on pedestrians 34.9 % vs 37.8 %, sides 14.6 % vs 15.3 %; fixations per
  minute did not differ by mode (F = 0.272, ηp² = 0.024) but the mode x zone interaction did
  (F = 4.704, p_GG = 0.0098, ηp² = 0.300) (Tab. 4) - the interaction includes walking, so the
  bicycle-vs-e-scooter contrast alone is small. Trefzger 2021: on the poor surface gaze moved
  nearer, more on the e-scooter (nearest road section 29 % vs 19 % of visit time); on the good
  surface the vehicles hardly differed; the inferential test for gaze is not described.
  Pils 2021 (abstract only): shoulder glances executed in 57.93 % (e-scooter) vs 60.71 %
  (bicycle) of possible occasions; whether the same riders used both vehicles is not stated.
- **Physiology.** Only in VR: Su 2025 (partial full text), within-subject, counterbalanced:
  lower normalised skin conductance on the e-scooter simulator; the analysis treats 4 Hz samples
  as observations (Assessment: inflated t-values; exertion confound of pedalling vs standing).
- **Safety epidemiology** (between populations, not exposure-matched): e-scooter ED visits
  20.7 vs 5.5 per million miles for bicycles, quoted in Mehranfar & Jones 2024 (p. 354);
  surface transitions up to x60 crash risk (p. 346); vibration and small wheels (pp. 365-366).

**Bottom line.** Within-subject comparisons exist but are short (50-200 m), single-pass,
single-modality (gaze + mean speed, or kinematics on a track, or physiology in VR), with manual
AOIs and, in one case, a fixed order. No study combines gaze, head, hands and riding dynamics
in naturalistic traffic, along a route with several infrastructure types, with repetitions.

### 2.2 E-scooter riders' gaze and infrastructure

- **Kegalle 2025** (N = 23 recruited; speed n = 19, gaze n = 14; Melbourne):
  speed 16.70 (1.84) / 18.14 (1.00) / 17.11 (1.75) km/h on shared path / cycle lane / roadway,
  F = 9.95 (Table 2, p. 217:11); fixations per km 454.83 / 460.20 / 545.05 (F = 10.5) and mean
  fixation duration 371.8 / 332.4 / 295.3 ms (F = 23.3) (Table 3, p. 217:12); "road ahead" holds
  78.6 % of fixations; PELT speed change points 7.9 / 4.3 / 10.2 (per km, p. 217:11).
  An off-the-shelf Faster R-CNN on 70-px gaze patches reached 10.5 % recall for pedestrians and
  15.1 % for cars, so AOIs were coded manually (p. 217:9). Videos are withheld for privacy
  (p. 217:2). Assessment and re-analysis: see [kegalle_replication.md](kegalle_replication.md)
  (e.g. the "gaze/acc dispersion" metrics in the code are not standard deviations; post-hoc
  tests ignore the repeated-measures design).
- **Kegalle 2024** (AHs, 4 pp.): preliminary qualitative version (N = 15) of the same study;
  superseded.
- **Hristov 2024** (N = 22, Berlin + Munich, Dikablis 60 Hz): frontal attention ratio 23.7 %
  (roadway) to 34.0 % (bike street); frontal glance duration longest on protected bike lanes
  (0.66 s) and shortest on the roadway (0.50 s) (Fig. 8-9, pp. 156-157); far/near/crossing
  zoning of junctions (p. 154). Assessment: no statistics despite "significant"; AOIs cover only
  45-56 % of gaze time; facility confounded with city.
- **Chen 2025** (ICTD; arXiv full text; N = 5): gaze entropy and head-movement SD (glasses IMU)
  by infrastructure and traffic scenario; descriptive only.
- **Rizehbandi 2026** (N = 28, three Zagreb routes, randomised): mean fixation duration
  278 / 410 / 314 ms (ηp² = 0.225) and NASA-TLX 5.80 / 2.50 / 8.58 (ηG² = 0.346); LMM
  ICC = 0.173; route and infrastructure confounded (one route per type).

### 2.3 Cyclists' gaze in the field

- **Near/far control and speed.** Vansteenkiste 2013 (lab): gaze mostly on the near path (41 %)
  and goal (40 %); higher speed shifts gaze further, narrower lanes pull it nearer (p. 224-226,
  Table 1); optokinetic nystagmus rather than "travel fixations". Vansteenkiste 2014 (curve,
  lab): with speed, gaze moves from the lane centre (41.26 % -> 16.91 %) to the inside edge
  (21.23 % -> 55.48 %) (pp. 4-6); exact look-ahead distance could not be measured without head
  tracking (p. 10).
- **Infrastructure and pedestrians.** Mantuano 2017 (Bologna, N = 13 analysed, 30 Hz ASL):
  where the cycle path shares space with pedestrians, fewer fixations in the target area (33 %
  vs 44 %) and more on pedestrians (relative frequency 0.61 vs 0.11) (pp. 412-414, Tables 3-5).
  Assessment: one-tailed uncorrected unpaired Z-tests on a paired design.
- **Risk, space and gaze.** von Stülpnagel 2020 (Freiburg, N = 18, 60 Hz SMI): faster riding ->
  longer sight vectors (B = 0.13) and smaller gaze angles to the travel direction (B = -0.19);
  higher perceived risk -> shorter fixations and sight vectors, wider angles; large open vista
  spaces raise perceived risk (pp. 232-234, Tables 3-4). Schmidt & von Stülpnagel 2018:
  dwell time follows the locations later rated dangerous (r up to .63, p. 36).
- **Separated cycle lanes and speed.** Cameli 2025 (Florence, N = 20, Tobii G3 50 Hz,
  instrumented bike): section speeds 12.02-15.58 km/h, related to separation element
  (F(4,95) = 30.655, Table 2 p. 8); speed correlates with front fixation duration (r = 0.469).
- **Workload.** Kchour 2026 (Gdansk, 13 recruited, 10 usable gaze, 7 usable EEG): glance types
  38 % / 36 % / 25 % (saccade / fixation / long fixation, duration-based); section effects small
  (Cramér's V 0.095-0.180); machine-learning scores probably inflated by train/test leakage
  (Assessment); no pupil or heart-rate data.
- **Aria in cycling.** Hardin 2026 (preprint, full text): one cyclist, Aria Gen 1, 12 runs on
  three Oxford loops; fixations about 20 % shorter in car lanes than bus lanes (g = -0.21);
  event types not distinguishable; object-level gaze and head/IMU listed as future work.
- **Automatic object gaze.** Berge 2025 (full text, accepted manuscript): YOLOv4 car boxes,
  "looking at the vehicle" if gaze-box angle < 4 deg; more looking when instructed
  (27.4 % -> 44.5 %, t(33) = -4.06); riders slowed more when attending to the vehicle;
  maximum speed correlated r = 0.96 between sessions.

### 2.4 Reviews of cyclist eye tracking

- **Kchour 2025** (25 studies; PRISMA): fixation thresholds range from 100 ms to > 200 ms and
  are often undisclosed (Table 6, p. 12); intersections impose the highest visual workload;
  calls for automatic AOIs and multimodal data (pp. 22-27). Assessment: 8 driver-only studies
  included against its own criterion.
- **Ma 2024** (35 studies): % fixation/dwell time per AOI is the dominant metric (19/35); fixation
  minimum 90-200 ms; inconsistent glance/dwell/visit terminology; gaze treated as attention
  (peripheral vision ignored); workload and stress conflated; manual AOI annotation; very few
  field studies with head or kinematic data (pp. 60-66). It cites 120 Hz as desirable for
  fixation detection (p. 64): our on-device gaze is 30 Hz.
- **Mehranfar & Jones 2024** (168 records, e-scooter safety): no eye-tracking study among the
  included records; bicycle comparisons are between populations and rarely exposure-adjusted.

### 2.5 Head movements

- Matviienko 2023 (QuantiBike): in VR (N = 12), perceived safety correlates with the frequency
  (left rs = -0.43) and duration (rs = -0.34 / -0.37) of head rotations beyond +-20 deg, not
  with their angle (rs = -0.12); outdoors (N = 8) only at the uncontrolled left turn
  (rs = -0.49 / -0.75) (Table 1-2, PDF pp. 4-9). Head-in-bicycle rotation came from AirPods + a
  handlebar phone; Assessment: several statistical inconsistencies (e.g. a correlation
  reported as significant that cannot be with n = 8).
- Rawson 2026 (abstract only): lateral head movement as an indicator of visual demand at
  intersections, highest for unprotected left turns.
- Chen 2025: near cars and buses, horizontal gaze variability exceeded head-movement variability
  ("eyes scan, head steady").
- **No study compares head behaviour between bicycle and e-scooter with a wearable**, apart from
  the shoulder-glance abstract of Pils 2021.

### 2.6 Hands and posture

- Pai & Dozza 2025 (naturalistic rental e-scooters, 6868 trips): single-handed riding was the
  strongest risk factor for safety-critical events (OR 6.51) - an e-scooter does not
  self-stabilise like a bicycle.
- Löcken 2020 and Brunner 2020 (abstracts): novices could signal by hand and perform rear checks
  while staying stable after training. Garman 2020 (abstract): rider body position and handlebar
  interaction maintain e-scooter stability.
- **No study uses wearable hand tracking during riding.** On-device Aria hand tracking was
  benchmarked by Meta at 45.0 mm mean keypoint error and 12.7 % lose-track ratio in a
  hand-object-interaction dataset (MPS performance page), not while holding a handlebar.

### 2.7 Simulators and physiology

- Guo 2023 (VR bicycle simulator, N = 50, Tobii 120 Hz in the HMD, smartwatch HR at 1 Hz):
  protected and curbside lanes raised perceived safety (β = 1.531 / 1.286) and reduced
  horizontal gaze variability; mean heart rate did not differ; the "stress" result rests on
  heart-rate change-point counts with an unreported threshold, coinciding with a 4 % downhill
  (exertion confound) (pp. 327-333).
- Ágoston & Borsos 2026 (bicycle simulator, N = 50, Pupil Labs Neon): infrastructure, not the
  share of autonomous vehicles, shaped gaze (saccade amplitude, W = 0.1456); pupil diameter
  changes overlapped across conditions (ΔP -0.026 to +0.030 mm) and were treated as exploratory.
- Kong 2025 (Aria Gen 2 Pilot Dataset, full text): PPG-based heart rate is provided but not yet
  validated. **Implication**: PPG on the nose pad during riding is at best an exploratory
  exertion/arousal covariate; pupil diameter is not exposed by projectaria-tools 2.3.0 (see
  `docs/aria/aria_gen2_technical_notes.md`).

### 2.8 Methods that recur, and their problems

| Topic | Practice in the literature | Problem for us |
|---|---|---|
| Fixation detection | Vendor I-VT presets (Tobii "Attention" 100 deg/s, min 60 ms), ASL dwell (>= 100 ms in 1 deg), SMI BeGaze, duration-only coding; often undisclosed (Kchour 2025 Table 6; Ma 2024 p. 64) | Thresholds depend on sampling rate and head motion; head-mounted gaze while riding mixes VOR/pursuit; Aria gaze is 30 Hz. Report algorithm and thresholds, run sensitivity analyses, prefer gaze-in-world for events. |
| AOI coding | Manual, frame-by-frame or fixation-by-fixation, rarely with inter-rater agreement | Not scalable to 20-min rides; automation needs validation (Kegalle's detector failed). |
| Speed | Segment length / time, GNSS 1 Hz, bike computers, video landmarks | Head-worn VIO gives continuous estimates; it must be validated (no published method). |
| Head movement | Accelerometer "dispersion" (Kegalle), AirPods yaw (QuantiBike), glasses IMU SD (Chen) | Accelerometer mixes vibration and gravity; use rotation (gyro/VIO), separate vibration bands. |
| Statistics | RM-ANOVA with between-subject post hoc, frame-level rows as independent, fixed participant effects, uncorrected multiple tests | Use mixed models with participant random effects, window-level summaries, effect sizes with CIs (see `docs/methodology/statistical_analysis_plan.md`). |
| Design | Fixed segment order, single pass, one route per infrastructure type | Confounds route, order and familiarity with infrastructure and vehicle. |

## 3. Reference values (for plausibility checks, not as hypotheses)

| Quantity | Bicycle | E-scooter | Source |
|---|---|---|---|
| Mean speed, shared path (km/h) | 16.8 | 16.5 | Pashkevich 2022, Sec. 3.1 |
| Mean speed, good / poor surface (km/h) | 17.84 / 18.48 | 15.93 / 15.34 | Trefzger 2021 (page not recorded) |
| Speed by infrastructure (km/h) | 12.0-15.6 (protected path sections) | 16.7 / 18.1 / 17.1 (shared / cycle lane / road) | Cameli 2025 Table 2 p. 8; Kegalle 2025 Table 2 p. 217:11 |
| Comfort / harsh braking (m/s^2) | -1.50 / -3.00 | -1.28 / -2.21 | Dozza 2023 Table 3 p. 30 |
| Comfort acceleration (m/s^2) | 0.45 | 0.56 | Dozza 2023 Table 2 p. 28 |
| Fixations on roadway / pedestrians (%) | 42.5 / 34.9 | 38.6 / 37.8 | Pashkevich 2022 Tab. 3 |
| Mean fixation duration (ms) | 180 (Bologna, 30 Hz ASL) | 295-372 (Tobii I-VT Attention) | Mantuano 2017 Table 3 p. 412; Kegalle 2025 Table 3 p. 217:12 |
| Eye-in-head yaw SD (deg) | - | 6.6 / 8.2 / 9.2 (shared / cycle lane / road) | our computation on Kegalle public data ([kegalle_replication.md](kegalle_replication.md)) |
| Head angular speed mean / P95 (deg/s) | - | 15.8-20.2 / 41-63 | same |
| Head rotation beyond +-20 deg, outdoors | frequency 1.5-4.5 per situation | - | Matviienko 2023 Table 2 (PDF p. 8) |

## 4. Implications for the design of this study

1. The contribution cannot be "the first comparison of cyclists and e-scooter riders with eye
   tracking" (Pashkevich 2022; Trefzger 2021). It can be a **within-participant, counterbalanced,
   repeated, route-scale and multimodal** comparison from a single wearable, with
   **segment-matched** contrasts (same physical place, both vehicles) and **time-locked**
   perception-action analyses (see `docs/research/scientific_contribution.md`).
2. Order must be counterbalanced (Trefzger's fixed order is its main weakness) and repetitions
   are needed to separate vehicle effects from learning and from trial-to-trial noise.
3. Infrastructure must vary within the route, with several segments per type, so that route and
   infrastructure are not confounded (Rizehbandi 2026; Kegalle 2025).
4. Fixation-based metrics need explicit, reported definitions adapted to 30 Hz head-mounted gaze
   and sensitivity analyses; sample-based and angular metrics (time shares, yaw SD, BCEA, gaze
   angle to travel direction) are more robust and more comparable across devices.
5. AOI automation must be validated against manual ground truth before use (Kegalle's detector
   failure; Berge's 4 deg tolerance; gaze accuracy degrades with motion, Hooge 2022).
6. Physiological signals (PPG) and pupil size are not interpretable as stress or workload in
   the field without controls (exertion differs between pedalling and standing; illumination);
   they are exploratory at most.
7. Statistics must respect the repeated-measures structure (mixed models, participant random
   effects, window-level units, effect sizes with intervals); a 3-participant pilot supports
   only feasibility and variance estimates (Julious 2005; Brysbaert & Stevens 2018).

## 5. Paper-by-paper notes (folder `paper/`)

Short summaries; the full structured notes (27 points, all page references) were used to build
[paper_matrix.csv](paper_matrix.csv).

| Paper | Design and data | Main results (page) | Key limitations / Assessment |
|---|---|---|---|
| Kegalle 2025, IMWUT 9(1) | Naturalistic, e-scooter only (Lime, 20 km/h cap), Melbourne loop ridden twice; Tobii G3 (50 Hz in exports), Garmin 1 Hz, Insta360, follower GoPro; N = 23 (19 speed, 14 gaze) | Speed and fixation results above (pp. 217:11-12); encounters per km by YOLOv8 (Table 4, p. 217:12); thematic analysis of conflicts (pp. 217:14-16) | No vehicle contrast; fixed segment order; manual AOIs without agreement; between-subject Tukey after RM-ANOVA; dispersion metrics ill-defined (code differs); videos withheld (p. 217:2) |
| Kegalle 2024, AHs | Same study, N = 15, preliminary | Qualitative only (pp. 308-309) | Superseded; "lowest speed" claim contradicted by the 2025 paper |
| Hristov 2024, Springer | E-scooter, 22 riders, Berlin/Munich, Dikablis 60 Hz, QR markers on handlebar | Facility and junction-zone attention ratios (pp. 156-157) | No statistics; AOIs cover ~half of gaze time; city x facility confound |
| Matviienko 2023, SUI | Cyclists, VR N = 12 + outdoor N = 8, AirPods + phone head-in-bike angles | Frequency/duration of head turns vs perceived safety (PDF pp. 4-9) | Small N, drift, statistical inconsistencies |
| Kchour 2025, Sensors | Review, 25 studies | Thresholds (Table 6, p. 12), gaps (pp. 22-27) | AI-assisted screening; driver-only studies included |
| Ma 2024, TRF | Review, 35 studies | Metrics and terminology (pp. 60-66) | No PRISMA flow or quality appraisal |
| Mehranfar & Jones 2024, TRF | Review, 168 records on e-scooter safety | Injury, helmet, infrastructure findings (pp. 351-369) | No risk-of-bias assessment; count inconsistencies (168 vs 186) |
| Kchour 2026, TRF | Bicycle, ET (Pupil Invisible) + EEG (NeuroSky) + GNSS/INS, N = 13 | Small section effects; ML scores (pp. 11-19) | Frame rows as units, fixed participant effects, probable leakage |
| Guo 2023, TRF | VR bicycle simulator, N = 50, Tobii 120 Hz, HR 1 Hz | Lanes raise perceived safety, reduce gaze spread (pp. 327-332) | HR "stress" via undefined change points; exertion confound |
| Ágoston & Borsos 2026, TRF | Bicycle simulator, N = 50, Pupil Neon | Infrastructure effects on saccade amplitude (pp. 8-12) | Detector and rates unreported; pupil exploratory |
| Mantuano 2017, CSTP | Bologna field, N = 13, ASL 30 Hz | Shared path: less target gaze, more pedestrian gaze (pp. 412-414) | One-tailed unpaired tests; one segment |
| von Stülpnagel 2020, TRF | Freiburg field, N = 18, SMI 60 Hz, LMMs | Sight vector / gaze angle vs speed and risk (pp. 232-234) | Manual speed (inter-coder r = 0.57); table label errors |
| Schmidt & von Stülpnagel 2018, ET4S | Same data, workshop | Dwell vs hazard maps (pp. 36-37) | Inconsistent df; sparse reporting |
| Vansteenkiste 2013, AAP | Lab, N = 12, SMI 50 Hz | Near/far gaze vs speed and width (pp. 224-226) | Indoor taped lanes |
| Vansteenkiste 2014, PLoS ONE | Lab curve, N = 17 | Gaze to inside edge with speed (pp. 4-6) | No head tracking; NoData up to 31 % |
| Cameli 2025, Discov. Appl. Sci. | Florence, bicycle, N = 20, Tobii G3 + seat IMU | Speed by separation element (p. 8) | Text/table mismatches; repeated measures ignored |
| Dozza 2023, JSR | Test track, 4 vehicles, N = 34, vehicle IMU + LiDAR | Decelerations, braking distance, response time (pp. 27-30) | Controlled manoeuvres only |
| Vetturi 2023, Transp. Res. Proc. | Braking test, 3 riders, video | No vehicle effect; acc-vs-speed model (pp. 412-413) | N = 3 |
| Zhang 2026, TRF | Berlin infrastructure cameras, between-subject | Pedestrian-infrastructure use, encounter speeds (pp. 6-7) | Reported p inconsistent with χ² |
| Ma 2021, AAP | One rider, instrumented e-scooter vs bicycle | Vibration events 50 vs 8 (pp. 10-11) | N = 1 |
| Taia Alaoui 2021, IFAC | Body IMUs, mode classification incl. kick-scooters | High F1 (pp. 84-85) | Sample-level CV leakage; leg-pushed scooters |

## 6. Gaps and opportunities

Summarised in [research_gaps.md](research_gaps.md); contribution options are assessed in
`docs/research/scientific_contribution.md`.

## 7. Access and verification notes

- **Pashkevich 2022** is closed access and is not in `paper/`. Its full text was read as the
  HTML version of record on ScienceDirect, through the University of Bologna subscription
  available in the user's browser session (no file stored). The project lead should be aware
  that this access route was used; to cite pages, add the PDF to the local `paper/` folder.
- Items marked "abstract only" (e.g. Pils 2021, Rawson 2026, White 2023, Fitch 2020) are cited
  only for what their abstracts state; their designs must be checked before relying on them.
- The open-access check service Unpaywall rejected the placeholder address first proposed;
  one retry used another placeholder (never the user's address); OpenAlex was used afterwards.
- No copyrighted PDF is versioned in this repository.

## 8. Bibliographic discrepancies found

- Kegalle 2025: article number 217 (arXiv PDF) vs 8 (authors' repository); Crossref has none.
- Kchour 2025: printed as Sensors 2025, 25(1):22, published online 24 Dec 2024.
- Trefzger 2021: the DataCite record has a wrong title and lists three of the four authors.
- Schmidt & von Stülpnagel 2018: registered as an article by ETH; it is an ET4S 2018 workshop paper.
- Ágoston & Borsos 2026 and Ma 2024: running headers omit "Traffic" from the journal name.
- Zhang 2026: χ² = 2.78 gives p ≈ 0.095, reported as p < 0.05; site counts 664 vs 1664.
