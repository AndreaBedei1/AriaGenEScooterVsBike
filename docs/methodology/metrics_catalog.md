# Metrics catalog

What can actually be measured with Meta Project Aria Gen 2 alone, for each metric family. The
complete table (definition, streams, algorithm, useful rate, filters, uncertainty, validity
conditions, limitations, references, feasibility, validation, pilot priority, implementation
status) is [metrics_feasibility.csv](metrics_feasibility.csv) (48 rows). Literature sources are
in `docs/literature/`; device facts in `docs/aria/aria_gen2_technical_notes.md`.

## 1. Three kinds of quantities

| Class | Meaning | Examples | How it is reported |
|---|---|---|---|
| **A. Direct measurement** | a quantity the glasses measure on the wearer | eye-in-head gaze angles (CPF), head angular velocity (gyroscope), head orientation (VIO), hand pose when the tracker reports one | as measured, with validity and coverage |
| **B. Indirect estimate** | a property of the riding, inferred from head-worn signals through a model | forward speed, decelerations, stops, heading change, lateral oscillation, perception-action latency | always named "estimate"; method, assumptions and validation stated; never presented as a vehicle measurement |
| **C. Not identifiable** | not observable with the glasses alone | brake force, steering torque/angle, pedalling force/cadence, throttle, frame roll, metric distance/TTC to others without validated reconstruction, lateral lane position, cognitive workload/stress | not computed; mentioned only as limits |

Semantic-gaze metrics are "A + model": the gaze is measured, the class or object under it comes
from a segmentation/detection model whose error must be measured (CV benchmark).

## 2. Families and decisions for the pilot

| Family | Core in the pilot | Secondary | Exploratory | Excluded |
|---|---|---|---|---|
| Eye tracking | gaze validity; eye-in-head yaw/pitch SD; forward share; lateral glances | BCEA; spatial entropy; vertical bands; fixation rate/duration (I-VT, with sensitivity analysis) | gaze ground distance; visual anticipation | saccade rate (30 Hz too low); pupil diameter (not exposed); blink rate (semantics unverified) |
| Semantic gaze | - | time share per class/group (after the CV benchmark) | dwell on objects, first gaze on road users, object-level gaze, transition entropy | - |
| Head movement | head angular velocity (low band); head yaw relative to travel and scanning events (+-20 deg); head orientation | head-movement variability | - | - |
| Estimated riding dynamics | forward speed; speed level/variability per segment; deceleration events; stops | heading change / yaw rate; speed change points per km (fixed penalty) | jerk; lateral oscillation proxy; head vibration exposure | - |
| Hand tracking | - | - | detection fraction per hand; wrist position relative to head; turn-signal gestures (candidate) | interpreting non-detection as hand off the handlebar |
| Interaction | annotated interaction episodes (duration) | road-user exposure counts (moving vs parked) | speed / head response after first observation | - |
| Perception-action | - | - | latency from first valid gaze on a target to action onset | interpretation as reaction time |
| Physiology | - | - | heart rate from PPG as exertion covariate (if signal quality allows) | HRV / stress indices |

Rationale for the core set: these quantities are measured or estimated with known methods,
have reference values in the literature (Kegalle 2025; Pashkevich 2022; Matviienko 2023;
Dozza 2023) and their validity can be checked in the pilot with simple references (GNSS, route
geometry, annotated video). Semantic gaze and perception-action depend on CV models and event
counts that the pilot must first establish.

## 3. Notes per family

### Eye tracking
- On-device gaze is 30 Hz in our profile, reported as yaw/pitch in the Central Pupil Frame with
  validity flags only (no per-sample confidence; the confidence-interval fields are not
  populated on Gen 2). No official accuracy figure is published for Gen 2: the angular
  tolerance used for "looking at an object" must be measured in the pilot (targets at known
  angles before and after each ride).
- Fixation-based metrics are reported with algorithm, frame (eye-in-head or world) and
  thresholds; results are given per minute (not only per km, because speed differs by vehicle).
  On the Kegalle public data, our I-VT at 30 Hz produced 118-126 fixations/min and 271-330 ms
  vs 136-158/min and 297-372 ms for Tobii's 50 Hz "Attention" preset: absolute values are
  algorithm-dependent, directions of effects agreed.
- The CPF definition changed in projectaria-tools 2.3.0 (SVD-based): keep 2.3.x for the whole study.

### Semantic gaze
- Pipeline: timestamp -> gaze (CPF) -> nearest RGB frame (15 Hz, tolerance half a frame) ->
  projection with the device calibration -> class / instance under the gaze with a radius from
  the measured gaze accuracy -> dwell and transitions. Gaze is never interpolated; samples
  without a frame or a label map are "unobserved", not assigned.
- With 15 Hz RGB a gaze sample can be up to 33 ms from its frame; during fast head rotations the
  image content moves; motion-compensated lookup is planned.

### Head movement
- Two complementary sources: gyroscope (direct, 800 Hz, decimated) and VIO orientation (10 Hz,
  ~800 Hz high-frequency pre-integrated). The vehicle heading is not measured: head yaw relative
  to the travel direction uses the heading of the smoothed trajectory (undefined at low speed).
- Pedalling produces periodic head motion on the bicycle that is absent on the e-scooter:
  voluntary rotations (< ~5 Hz) and vibration must be separated before comparing vehicles.

### Estimated riding dynamics
- Speed is the horizontal speed of the head trajectory (VIO, gravity aligned), with GNSS as
  fallback and reference; it describes the rider's head, which translates with the vehicle but
  also sways. Decelerations are derivatives of this estimate - not braking measurements.
- Only valid VIO samples are used; no interpolation across tracking resets; every window reports
  observed / interpolable / degraded / unusable fractions and a quality flag.
- The high-frequency VIO (~800 Hz) is IMU pre-integration on top of the 10 Hz VIO (official
  documentation): it is not 800 independent visual measurements per second and is used for
  smooth orientation/velocity, not as extra evidence.

### Hand tracking (RQ5, exploratory)
- On-device hand tracking is computed from the CV (SLAM) cameras, at 10 Hz in our profile.
  While riding, hands are at the lower edge of the field of view and partly occluded by the
  handlebar. A non-detected hand is **missing**, never "off the handlebar".
- Positions are in the head frame: they mix arm posture with head posture.

### Perception-action
- Latency = action onset - first valid gaze on the target. It is not a psychophysiological
  reaction time: the target may have been seen peripherally earlier, the action may be planned
  or already under way, and other factors may trigger it. Events without an identifiable order
  (action before first gaze, target never tracked, gaze invalid around onset) are excluded and
  counted. Threshold sensitivity is part of the analysis.

### Physiology (PPG) and pupil
- PPG (nose pad) during riding suffers motion artefacts; Meta's heart-rate estimate is not yet
  validated; exertion differs between pedalling and standing. PPG can at most be an exploratory
  exertion/arousal covariate on segments with good signal quality. It is not a stress or
  workload measure.
- Pupil diameter is computed on the device but not exposed by projectaria-tools 2.3.0; outdoors
  it would be dominated by illumination anyway.

## 4. Implementation status (summary)

Implemented and tested on synthetic data: gaze validity and coverage, yaw/pitch SD, BCEA,
spatial and transition entropy, I-VT fixations, forward share, lateral glances, vertical bands,
semantic time shares and dwells (with label maps), speed and its statistics, decelerations,
stops, jerk, heading/yaw rate, lateral oscillation proxy, perception-action latencies
(deceleration as action), hand detection and wrist descriptors, data-quality fractions.
Planned: head-yaw scanning events, frequency-band separation of head motion, PELT change points,
gaze ground distance, object-level gaze from tracks, road-user exposure counts, PPG heart rate.
None has been validated on real riding data yet.
