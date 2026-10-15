# Research questions

**Working title:** *Electric kick-scooter vs conventional bicycle: visual attention, head
movements and estimated riding dynamics of the same riders on the same urban route, measured
with a single wearable (Meta Project Aria Gen 2).*

The study compares, **within the same participants**, riding an electric kick-scooter and a
conventional (non-electric) bicycle along the **same urban route** in Cesena, wearing the same
Aria Gen 2 glasses as the only sensor. It is not a crash or near-miss study: nothing is
provoked, interactions are observed as they occur, and riders are described with quantitative
metrics, never labelled "safe/unsafe". Novelty and the ranking of possible contributions are
discussed in `research/scientific_contribution.md`: a within-participant bicycle/e-scooter
eye-tracking comparison already exists on short single segments (Pashkevich et al. 2022;
Trefzger et al. 2021), so the questions below are framed at route scale, with counterbalanced
and repeated rides, segment matching and several modalities.

## RQ1 - Vehicle effect

> How does riding an e-scooter versus a conventional bicycle influence visual attention, head
> movements and estimated riding dynamics under comparable urban conditions?

- Same route segments, both vehicles, same riders; outcomes: forward share and scanning
  (gaze yaw SD relative to travel, lateral glances), gaze time shares on road users and path
  surfaces, head-rotation events relative to travel, speed level and variability, deceleration
  events and stops (estimates from head-mounted VIO/GNSS).
- Primary analysis of the main study (pilot: descriptive and variance estimation only).

## RQ2 - Infrastructure effect

> How do cycling infrastructure, shared roads, intersections and pedestrian interactions
> influence behaviour across the two transport modes?

- Infrastructure classes: protected cycle path, shared pedestrian-cycle path, painted cycle lane,
  road shared with traffic, crossing, intersection, roundabout (several segments per class).
- Main effects of infrastructure and the vehicle x infrastructure interaction (secondary;
  needs the main study's sample).

## RQ3 - Perception-action relationship (exploratory)

> How do visual observations of surrounding objects and road users relate temporally to
> subsequent changes in movement and riding behaviour?

- First valid gaze on a tracked road user -> onset of deceleration (heading change and head
  turns planned) -> minimum speed. The latency is **not** a reaction time: earlier peripheral
  detection, anticipation or actions already under way cannot be excluded; events without an
  identifiable order are excluded and counted.

## RQ4 - Individual differences and repeatability

> Are behavioural patterns consistent within participants across vehicles and repeated trials?

- ICC and variance components (participant, participant x vehicle, trial) with two trials per
  vehicle (ABBA/BAAB). Pilot: rough estimates for planning.

## RQ5 - Hands and posture (exploratory)

> Do hand-tracking signals show observable differences in hand position and posture between
> bicycle and e-scooter riding, and are they reliable enough while holding a handlebar?

- First a measurement question (detection coverage and error on annotated frames,
  `methodology/hand_tracking_validation.md`); a non-detected hand is missing, never "off the
  handlebar".

## Operationalisation and implementation status

| Construct | Metric(s) | Module | Status |
|---|---|---|---|
| Data quality and coverage | rates, dropouts, gap classes, VIO status/resets, validity, window coverage | `quality` | implemented, tested |
| Gaze allocation | time share per semantic class / group / category, dwells | `gaze` | implemented, tested on synthetic data; CV models to benchmark |
| Forward-looking behaviour | gaze within +-15 deg of the travel direction | `gaze` | implemented, tested; thresholds provisional |
| Lateral scanning | lateral glances, yaw SD relative to travel | `gaze` | implemented, tested |
| Gaze dispersion / entropy | BCEA, spatial and transition entropy | `gaze` | implemented, tested |
| Fixations | I-VT (rate, duration) with sensitivity analysis | `gaze` | implemented; threshold to validate at 30 Hz |
| Head movements | head yaw relative to travel (SD), angular velocity | `gaze`, `aria` | partly implemented; +-20 deg events and frequency-band split planned |
| Speed, acceleration, jerk (estimates) | level, variability, percentiles | `trajectory`, `behaviour` | implemented, tested; validation vs GNSS/video planned |
| Deceleration events, stops (estimates) | onset, peak, duration | `behaviour` | implemented, tested |
| Route-matched segments | GNSS -> planned route segments | `route` | implemented, tested on synthetic loops |
| First observation and perception -> action | first gaze, latency, max deceleration, min speed | `events` | implemented (deceleration as action); exploratory |
| Hands | detection fraction, wrist position in CPF | `hands` | implemented (exploratory); validation planned |
| Vehicle contrasts | within-participant e-scooter - bicycle per place | `pipeline.aggregate` | implemented (descriptive) |
| Statistical models | LMM/GLMM, ICC | analysis | planned (`methodology/statistical_analysis_plan.md`) |

## Out of scope

- Crash or near-miss analysis, provoked conflicts, braking tests.
- Measurements of the vehicles themselves (brake force, steering, pedalling): no vehicle sensors.
- Stress or workload inferred from PPG or pupil size.
- Labelling riders or behaviours as safe/unsafe; identification of bystanders.
