# Scientific contribution: what is actually new?

This document weighs six candidate contributions against the literature
(`docs/literature/literature_review.md`, `research_gaps.md`) and ranks them by **scientific
solidity** (identifiability, measurement validity, feasibility with N = 3 now and a larger
sample later), not by apparent novelty.

**Important correction to the original idea.** A within-participant eye-tracking comparison of
cyclists and e-scooter riders **already exists**: Pashkevich et al. (2022; N = 12, random mode
order, one 50 m shared path, one pass) and Trefzger et al. (2021; N = 24, fixed order bicycle ->
e-scooter, 200 m street, good/poor surface). Both are short, single-pass, manual-AOI studies
with gaze and mean speed only. The study must therefore not be presented as "the first
comparison"; its value lies in scale, design control, multimodality and measurement validity.

## 1. Candidate contributions

### A. Within-subject multimodal comparison of the two vehicles on the same segments

| Aspect | Assessment |
|---|---|
| Prior work | Pashkevich 2022; Trefzger 2021 (gaze + speed, short segments); Dozza 2022/2023, Li 2023 (kinematics on track); Pils 2021 (shoulder glances, abstract); Su 2025 (VR physiology) |
| Difference | 3.5-4.5 km urban loop with several infrastructure types; counterbalanced order; optional repetitions; segment-matched contrasts (same physical place); gaze + head + estimated dynamics from one device |
| Real novelty | **Moderate**: design and scale, not the question itself |
| Method | Route segments from geometry (`map-segments`), window metrics with quality flags, mixed models with participant random effects (see statistical analysis plan) |
| Observables | gaze time shares, forward share, yaw/pitch SD, BCEA, scanning (lateral glances), head yaw relative to travel, speed level and variability, deceleration events, stops |
| Limits | Traffic differs between rides; vehicle differences in posture (seated vs standing) change head height and pitch; pedalling adds head motion on the bicycle |
| Probability of informative results | **High** for descriptive differences and effect-size estimates; confirmatory inference needs the main study |
| Identifiability risks | Order/learning (mitigated by counterbalancing and repetitions); time-of-day/traffic (recorded as covariates); fatigue (pauses) |
| Complexity | Moderate (pipeline mostly implemented) |

### B. Semantic gaze and interactions (what was looked at, which object, then what)

| Aspect | Assessment |
|---|---|
| Prior work | Manual AOIs (most studies); detector failure (Kegalle 2025); single-class YOLO + 4 deg tolerance linked to slowing (Berge 2025); YOLO-assisted coding (Kchour 2026) |
| Difference | Multi-class semantic gaze with object identity (tracking), gaze uncertainty, time-locked to subsequent movement, compared between vehicles |
| Real novelty | **High** if valid |
| Method | Segmentation + detection + tracking on fisheye RGB; gaze projected with calibration; angular tolerance from measured gaze accuracy; first-gaze -> action-onset latencies with exclusion rules |
| Observables | first valid gaze on a target, dwell on target, action onset (deceleration / heading change / head turn) |
| Limits | No public model with an e-scooter class; domain shift (head-mounted fisheye); 15 Hz RGB vs 30 Hz gaze; peripheral vision invisible to gaze; actions may start before the first recorded gaze |
| Probability of informative results | **Medium-low in the pilot** (few events of each type); medium in a larger study |
| Identifiability risks | **High**: latency is not a reaction time; order ambiguity; detector misses bias first-gaze times; selection of events with both gaze and action |
| Complexity | High (benchmark + annotation + tracking) |

### C. Head and hand behaviour

| Aspect | Assessment |
|---|---|
| Prior work | Head: QuantiBike (cyclists), Rawson 2026 (abstract), Chen 2025 (e-scooter, N = 5), Pils 2021 (abstract). Hands: crash-risk evidence (Pai & Dozza 2025), hand signals (Löcken 2020) |
| Difference | Within-person head scanning across vehicles (head vs eye contributions); first wearable hand-tracking evidence while riding |
| Real novelty | Head: **moderate**. Hands: **high but uncertain** |
| Method | Head yaw relative to travel from VIO; rotation events; vibration separated by band. Hands: detection coverage and position relative to CPF |
| Limits | Head: vehicle heading is estimated from the trajectory, not measured. Hands: on-device HT computed from the CV cameras; handlebar grip at the lower edge of the field of view; benchmark error 45 mm and 12.7 % lose-track in a different task |
| Probability of informative results | Head: **high**. Hands: **unknown until measured** |
| Identifiability risks | Hands: absence of detection != hand off the handlebar |
| Complexity | Head: low. Hands: medium (annotation of frames) |

### D. Infrastructure-dependent vehicle effects (vehicle x infrastructure)

| Aspect | Assessment |
|---|---|
| Prior work | Trefzger 2021 (surface x vehicle on gaze, one street); Distefano 2026 (geometry x vehicle, kinematics); e-scooter-only infrastructure studies |
| Difference | Several infrastructure types x both vehicles, gaze/head in the field |
| Real novelty | **Moderate-high** |
| Method | Mixed models with vehicle x infrastructure interaction, random slopes when the data allow |
| Limits | Interactions need many more observations than main effects; few segments per type on a 4 km route; infrastructure types are not randomised (place confound) |
| Probability of informative results | **Low with N = 3**; moderate in a properly sized study |
| Identifiability risks | Place-specific features (traffic, visibility) confounded with infrastructure class; use several segments per class |
| Complexity | Low once A exists |

### E. Repeatability and individual behaviour

| Aspect | Assessment |
|---|---|
| Prior work | Speed test-retest (Berge 2025); track repeatability (Al-Hakeem 2026, abstract); no gaze/head reliability in the field |
| Difference | ICC of gaze, head and speed metrics across repeated rides with each vehicle; between- vs within-person variance |
| Real novelty | **Moderate-high** (practically useful for sizing future studies) |
| Method | Two trials per vehicle; ICC(2,1)/(3,1) with intervals; variance components from mixed models |
| Limits | Learning between trials; traffic variation; N = 3 gives very imprecise ICCs |
| Probability of informative results | **Medium** (pilot: variance estimates; main study: ICCs) |
| Identifiability risks | Learning confounded with trial number (model trial order) |
| Complexity | Low (protocol cost: double the riding time) |

### F. Single-wearable sensing (what can be inferred from one head-worn device)

| Aspect | Assessment |
|---|---|
| Prior work | No published validation of head-worn VIO speed for micromobility (search section g); Hardin 2026 (Aria Gen 1, gaze only); Aria datasets without riding validation |
| Difference | Systematic measurement of coverage and validity of on-device VIO, gaze, hand tracking and GNSS while riding two vehicles; speed/deceleration estimates vs GNSS, route length and annotated video; semantic-gaze validation |
| Real novelty | **High** (methodological) |
| Method | Quality reports (implemented), validation plan (`docs/methodology/validation_plan.md`) |
| Observables | dropout, gaps, resets, valid fractions; speed error vs references; trimming agreement; segmentation IoU; gaze-hit accuracy |
| Limits | No ground-truth vehicle speed (no wheel sensor): references are GNSS, route geometry and video-annotated events |
| Probability of informative results | **High** (results are informative whatever the vehicle effect) |
| Identifiability risks | Low; reference quality must be documented |
| Complexity | Moderate |

## 2. Ranking by scientific solidity

1. **F - single-wearable measurement validity** (high feasibility, high methodological novelty,
   informative regardless of the substantive outcome).
2. **A - segment-matched, counterbalanced within-participant comparison** of gaze, head scanning
   and estimated dynamics (solid design; moderate novelty; primary substantive aim).
3. **E - repeatability** (if two trials per vehicle are affordable).
4. **C-head** (part of A) - **C-hands** exploratory.
5. **D - vehicle x infrastructure interactions** (needs the main study; exploratory in the pilot).
6. **B - semantic gaze -> action latencies** (highest novelty, highest identification risk;
   exploratory until the CV benchmark and event counts justify it).

## 3. Proposal

**Main research question.** *Within the same riders and on the same urban route segments, how
do visual attention (gaze allocation and scanning) and head movements differ between riding an
electric kick-scooter and a conventional bicycle, and how reliably can these behaviours and the
associated riding dynamics be measured with a single head-worn device?*

**Core contributions (at most three):**

1. A counterbalanced, segment-matched, within-participant comparison of gaze, head scanning and
   estimated riding dynamics between e-scooter and bicycle along a multi-infrastructure urban
   route (A, with C-head).
2. A validation of single-wearable sensing for micromobility research: data quality, coverage
   and accuracy of on-device VIO, gaze and hand tracking while riding, and of the derived speed,
   stop and deceleration estimates (F).
3. Within-person repeatability of these metrics across rides and vehicles (E) - conditional on
   recording two trials per vehicle.

**Primary analyses (main study, to be pre-registered after the pilot):** vehicle effect on
segment-level gaze and head metrics and on speed level/variability, in mixed models with
participant random effects and infrastructure class as covariate; measurement-validity
statistics (F).

**Exploratory analyses:** vehicle x infrastructure interactions (D); perception-action latencies
on validated events (B); hand detection and posture (C-hands, RQ5); PPG as exertion/arousal
covariate; pupil-related measures are not available in projectaria-tools 2.3.0.

**Pilot (N = 3) outputs:** feasibility, data quality per stream, variance components and
plausible effect ranges to size the main study, protocol problems - **no confirmatory claims**.
