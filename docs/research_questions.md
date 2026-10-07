# Research questions

**Working title:** *Multimodal naturalistic study of visual attention and riding behaviour in e-scooter users*
(Italian: *Studio naturalistico multimodale dell'attenzione visiva e del comportamento di guida in utilizzatori di e-scooter*).

The study observes **everyday e-scooter riding** on real urban routes with Project Aria Gen 2
glasses. It is **not** a crash or near-miss study: no situation is provoked, and interactions are
studied as they occur naturally. Riders are never labelled with subjective categories
("safe", "aggressive", "good rider"); behaviour is first described with quantitative metrics.

The main unit of analysis is the **route segment** (a semantically homogeneous stretch of the
route with one infrastructure class). Events/interactions are time windows that can overlap any
segment (e.g. `protected_cycle_path + pedestrian_interaction`).

## RQ1 - Infrastructure and surrounding traffic

> How do infrastructure and surrounding traffic conditions influence visual attention and riding
> behaviour in e-scooter users?

- **RQ1a** - Do infrastructure classes (protected cycle path, painted cycle lane, shared
  pedestrian-cycle path, road shared with traffic, pedestrian/shared space, crossing,
  intersection, roundabout) differ in gaze allocation (time share per semantic class,
  forward-looking share, lateral scanning, gaze dispersion/entropy) and in riding dynamics
  (speed level and variability, deceleration events, jerk, lateral oscillation)?
- **RQ1b** - How do interactions with other road users (pedestrians, cyclists, other e-scooters,
  vehicles, parked vehicles, obstacles, narrow sections) modify gaze and behaviour *within* a
  given infrastructure class?
- **RQ1c** - How do riders behave when approaching crossings, intersections and roundabouts
  (approach speed, deceleration, scanning before entry)?

## RQ2 - Rider-specific patterns

> Are there consistent rider-specific behavioural and visual-attention patterns across different
> urban contexts?

- Decomposition: `behaviour = rider effect + infrastructure effect + rider x infrastructure`.
- Comparisons supported by the data structure: the same rider in different contexts; different
  riders in the same context; persistence of individual patterns (e.g. intraclass correlation);
  patterns shared by all riders and induced by the infrastructure.
- Riding styles, if any, must **emerge from the data** (e.g. clustering of metric profiles),
  after the quantitative metrics are validated - never be assigned a priori.

## RQ3 - Perception -> action

> How does visual perception precede and relate to subsequent riding actions?

```
first gaze at the interaction target -> action onset (first deceleration) -> maximum deceleration
                                                                         -> minimum speed / clearance
visual anticipation = reference instant (e.g. closest approach) - first gaze
perception-to-action latency = action onset - first gaze
```

- Does the timing of the first observation of a target (pedestrian, cyclist, vehicle...) relate
  to the timing and intensity of the subsequent response?
- Do anticipation and latency depend on infrastructure, interaction type and rider?
- Neutral terms only (`interaction`, `event`, `risk proxy`) until validated definitions exist.

## Operationalisation and implementation status

| Construct | Metric(s) | Module | Status |
|---|---|---|---|
| Gaze allocation | time share per semantic class / group, dwell duration | `gaze` | implemented, tested on synthetic data |
| Forward-looking behaviour | share of gaze within a window around the direction of travel | `gaze` | implemented, tested; thresholds provisional |
| Lateral scanning | lateral glances (count, rate, duration, side), yaw SD | `gaze` | implemented, tested; thresholds provisional |
| Gaze dispersion / entropy | BCEA, spatial entropy, stationary and transition entropy | `gaze` | implemented, tested |
| Fixations | I-VT fixations (rate, duration) | `gaze` | implemented, tested; threshold to validate on pilot data |
| Near vs far gaze | vertical gaze bands (proxy only) | `gaze` | implemented as a proxy; depth-based estimate planned |
| Speed, acceleration, jerk | level, variability, percentiles, RMS jerk | `trajectory`, `behaviour` | implemented, tested |
| Deceleration events, stops | onset, peak, duration, speed drop | `behaviour` | implemented, tested |
| Trajectory stability | yaw-rate SD, lateral deviation RMS, sinuosity | `behaviour` | implemented (head-mounted proxy) |
| Approach behaviour | speed/deceleration before crossings, intersections, roundabouts | `behaviour` | implemented, tested |
| First observation of a target | first gaze on class/instance with minimum dwell | `events` | implemented, tested on synthetic data |
| Perception -> action | anticipation, latency, max deceleration, min speed | `events` | implemented, tested on synthetic data |
| Minimum clearance / risk proxies | distance to target, TTC-like measures | `events` | **planned** (needs distance estimation) |
| Steering responses | heading/lateral manoeuvres as actions | `events` | **planned** |
| Rider vs infrastructure effects | mixed-effects models, ICC | analysis | data structure ready; **models planned** |
| Riding styles | data-driven clustering | analysis | **planned**, after metric validation |

## Hypotheses and analysis plan - TBD

Confirmatory hypotheses, sample size, power analysis and the statistical analysis plan are
**TBD** and should be fixed (ideally pre-registered) after the pilot. Candidate directions to be
discussed, *not commitments*: shared pedestrian-cycle paths may be associated with more gaze on
pedestrians and lower, more variable speeds than protected cycle paths; approaches to crossings
and roundabouts may show more lateral scanning; rider-level consistency may be substantial for
speed metrics.

## Out of scope

- Crash or near-miss analysis, provoked or staged conflicts, braking tests.
- Labelling riders or behaviours as safe/unsafe/aggressive.
- Identification of bystanders (faces and licence plates are anonymised; see `privacy_pipeline.md`).
