# Statistical analysis plan

**Status: draft.** The confirmatory part will be finalised and registered (e.g. on OSF) after
the pilot and before the main data collection. With the pilot (N = 3) only descriptive,
feasibility and variance-estimation analyses are planned; **no p-values are used to claim
vehicle or infrastructure effects from the pilot.**

## 1. Units, structure and data

- Hierarchy: participant -> session (day) -> ride (recording; vehicle, trial number, ride
  order) -> route segment (route-referenced, `route_segment_id`) / event -> samples.
- Analysis units are **windows** (segments, approach windows, events), each summarised from
  thousands of samples. Samples (gaze at 30 Hz, kinematics at 10 Hz) are **never** treated as
  independent observations; frame-level statistics are only used inside a window.
- Tables: `study_segment_metrics.csv`, `study_event_metrics.csv`, `study_approach_metrics.csv`,
  `rider_vehicle_by_infrastructure.csv`, `within_participant_vehicle_contrasts.csv`
  (`docs/data_schema.md`). Every window carries coverage and a `quality_flag`.
- Inclusion of a window: `quality_flag = ok` (observed + interpolable time >= 0.8 for the
  streams used); sensitivity analysis with all windows. Missing windows are reported per ride
  and segment, never imputed for primary analyses.

## 2. Descriptive analyses (pilot and main study)

- Distributions per vehicle, infrastructure class and participant: mean, median, SD,
  interquartile range, 5th/95th percentiles, counts of events (stops, deceleration events,
  lateral glances, head-turn events), coverage.
- Visualisations: per-participant paired plots (bicycle vs e-scooter per segment), route
  profiles (metric along the route for each ride), forest plots of within-participant
  differences with bootstrap intervals, quality heat maps per ride and stream.
- Data-quality descriptives are reported **before** any substantive result.

## 3. Within-participant vehicle comparison

- Primary contrast: for each participant and route segment, mean over trials of each metric per
  vehicle and the difference e-scooter - bicycle (`within_participant_vehicle_contrasts.csv`).
- Pilot: report the differences per participant and segment with bootstrap intervals over
  segments (resampling segments within participant), and their variability. No pooled test.
- Main study: linear mixed-effects models (section 7).

## 4. Repeatability (if >= 2 trials per vehicle)

- Trial 1 vs trial 2 with the same vehicle: Bland-Altman limits of agreement and ICC
  (two-way, absolute agreement for agreement questions; consistency for ranking questions;
  Koo & Li 2016), with confidence intervals. Pilot ICCs are reported only as rough estimates
  (very wide intervals with N = 3).
- Variance components from mixed models (participant, participant x vehicle, trial residual)
  quantify how much of the variation is individual and stable across vehicles (RQ4).
- Learning: ride order as a covariate; with ABBA/BAAB the linear trend is balanced within
  participants and can be estimated.

## 5. Infrastructure analyses

- Comparisons between infrastructure classes (protected cycle path, shared pedestrian-cycle
  path, painted lane, road shared with traffic, crossing, intersection, roundabout), using
  **several segments per class** so that class is not confounded with a single place.
- Approach windows before crossings, intersections and roundabouts (time-based, and
  distance-based once the route geometry is used).
- Pilot: descriptive only. Main study: infrastructure as fixed effect, segment as random effect
  (crossed with participant).

## 6. Interactions with other road users

- Event-level analyses are conditional on the presence of pedestrians, cyclists, e-scooters,
  vehicles; they compare behaviour in comparable events between vehicles (e.g. pedestrian
  interactions on shared paths), not raw event counts (traffic is not controlled).
- Exposure (road-user counts per segment, from video) as covariate.
- Perception-action latencies: descriptive, with explicit exclusion counts (order not
  identifiable, target not tracked, invalid gaze) and threshold-sensitivity curves; never
  called reaction times.

## 7. Models for the main study

- **Linear mixed models** for continuous segment-level outcomes:
  `y ~ vehicle * infrastructure + ride_order + speed_or_exposure_covariates + (1 + vehicle | participant) + (1 | route_segment)`;
  maximal random-effects structure justified by the design, simplified only when not supported
  (Barr et al. 2013), with the simplification rule fixed in advance.
- **Generalised linear mixed models** for counts (lateral glances, stops, deceleration events,
  head-turn events: Poisson/negative binomial with log(duration or distance) offset) and for
  proportions (time shares: beta or binomial with the number of valid samples; or logit
  transformation with weights). glmmTMB/lme4 (Brooks et al. 2017; Bates et al. 2015) or
  equivalent Python implementations.
- **Temporal autocorrelation**: windows are aggregated so that residual autocorrelation between
  consecutive segments is small; checked with residual ACF along the route; if present, AR(1)
  residual structures by ride or ride-level random effects. Sample-level time series (e.g.
  gaze yaw along an approach) use functional or GAMM approaches with ride-level random smooths
  (exploratory).
- **Effect sizes**: model-based differences in the original units with 95 % confidence
  intervals (profile likelihood or parametric bootstrap); standardised effects (e.g. Cohen's d
  for within-participant differences, Lakens 2013) only as secondary descriptors.
- **Multiplicity**: a small set of primary outcomes (defined below); secondary outcomes reported
  with false discovery rate control and labelled as such; exploratory analyses labelled
  exploratory.
- **Test choice** is fixed in advance by the data type and design, never by the resulting
  p-value.

Candidate primary outcomes (to confirm after the pilot): (1) forward share of gaze; (2) gaze
yaw SD relative to the travel direction (scanning); (3) head-yaw scanning rate (+-20 deg events
per minute); (4) mean speed per segment; (5) gaze share on pedestrians in pedestrian
interactions. Primary contrast: vehicle main effect; secondary: vehicle x infrastructure.

## 8. Sample size for the main study

- The pilot provides variance components and plausible effect ranges; the main-study sample is
  determined by **simulation-based power analysis** for the mixed models (Brysbaert & Stevens
  2018; Westfall et al. 2014), for the primary outcomes, with the number of segments per class
  and of trials fixed by the route and protocol.
- Pilot effect estimates are **not** used directly as the target effect (they are very
  imprecise); the target is a smallest effect of interest agreed with the project lead,
  informed by the literature (e.g. bicycle vs e-scooter roadway fixation shares 42.5 % vs
  38.6 % in Pashkevich 2022; speed differences ~0-2 km/h in Pashkevich 2022 and Trefzger 2021).
- Rules of thumb (e.g. 12 per group for pilots, Julious 2005) are not used to size the main study.

## 9. Sensitivity analyses

Fixation thresholds; gaze lookup radius and assignment rule; quality-flag threshold;
kinematic smoothing and deceleration thresholds; segment boundary uncertainty (+- boundary
error); exclusion of rides with protocol deviations; GNSS vs VIO speed.

## 10. Reporting

Data-quality and coverage first; descriptive per-participant results; model results with
intervals; explicit separation of confirmatory, secondary and exploratory analyses; all
configuration hashes and software versions (in every `report.json`) archived with the results.
