# Methodology

This document describes how data are acquired, processed and analysed, which choices are
**provisional**, and what is **implemented**, **tested**, **planned** or **TBD**. Every numeric
parameter mentioned here lives in `configs/default.yaml` and is saved with each run.

Contents: 1 design - 2 sensors - 3 pipeline - 4 time - 5 trimming - 6 segments and events -
7 kinematics - 8 scene understanding - 9 semantic gaze - 10 perception -> action -
11 rider vs infrastructure - 12 validation - 13 parameters - 14 limitations - 15 references.

## 1. Study design

- Naturalistic riding on real urban routes, during normal traffic, with the participant's normal
  riding style. No manoeuvre is requested, no situation is provoked (see the ethics documents).
- Within-subject comparison across infrastructure classes along the route(s), plus
  between-subject comparison of riders in the same contexts.
- Unit of analysis: **route segment** (one infrastructure class, non-overlapping). Overlapping
  **events/interactions** are annotated separately.
- Route(s), number of participants, sessions per participant, inclusion criteria: **TBD**.

## 2. Sensors and data (Project Aria Gen 2)

Facts below were checked on the official Gen 2 documentation (Oct 2026); see
`aria_gen2_integration.md` for sources.

| Signal | Gen 2 stream label | Rate (standard profiles) | Use |
|---|---|---|---|
| RGB video | `camera-rgb` | profile8: 2560x1920 @ 10 Hz; profile10: 2016x1512 @ 30 Hz | scene understanding, semantic gaze, privacy processing |
| On-device eye gaze | `eyegaze` | 30 Hz | gaze angles (CPF), projection into RGB |
| IMU (x2) | `imu-left`, `imu-right` | 800 Hz | head motion, vibration (experimental trimming check) |
| On-device VIO | `vio`, `vio_high_frequency` | 10 Hz / ~800 Hz | head trajectory -> kinematics |
| GNSS | `gps` (glasses), `gps-app` (phone) | 1 Hz (profile8/10) | positioning, external clock checks |
| MPS (cloud, optional) | SLAM, eye gaze, hand tracking | MPS gaze only 5 Hz with standard profiles | optional; requires uploading VRS to Meta |

Other streams (SLAM/ET cameras, microphones, PPG, ALS, barometer, magnetometer) are not used by
the current analysis. Audio is not needed: the recording profile should avoid it if possible
(**TBD**, see `privacy_pipeline.md`).

**Head-mounted sensor caveat.** Aria measures the rider's head. Head translation follows the
e-scooter but includes body sway; head rotation is *not* the vehicle heading. Hence the direction
of travel is derived from the trajectory, and lateral metrics are proxies mixing vehicle motion
and body sway. A rigidly mounted vehicle IMU/GNSS (e.g. a smartphone on the handlebar) would
separate them: **TBD** (equipment decision).

## 3. Processing pipeline

```
raw VRS (+ optional MPS / external GPS)            data/raw        restricted
  -> extract-aria: canonical streams                data/interim    (Linux, projectaria-tools)
  -> anonymised copies for any video use            EgoBlur (separate environment)
  -> label maps (segmentation back-end)             data/interim/semantic
  -> annotations: route segments + events           data/interim/annotations
  -> run: validate -> sync -> trim -> kinematics -> semantic gaze -> metrics
                                                     data/processed  (report, tables, figures)
  -> aggregate: study-level long tables             data/processed/_study
```

The MVP (`python -m ariagen_escooter run`) implements everything from "validate" onwards and is
tested end-to-end on the synthetic session. Extraction is implemented against the official API
but not yet validated on a real Gen 2 recording; segmentation inference is experimental.

## 4. Timestamps and synchronisation

- All canonical streams use `t_ns`, int64 nanoseconds of the Aria **device clock**
  (`TimeDomain.DEVICE_TIME`), which all on-device sensors share. UTC information in Gen 2
  recordings is coarse (seconds-level, sampled about once per minute through the companion app),
  so it is not used for alignment.
- `validate` and `run` report per stream: sample count, duration, median interval, estimated
  rate, decreasing timestamps (error), duplicates (warning, removed), gaps (interval >
  `gap_factor` x median; 1.5 flags single dropped samples).
- Gaze -> RGB frame: nearest frame within `gaze_frame_tolerance_s` (0.05 s, half the 10 Hz
  frame period); otherwise status `no_frame`. No interpolation of gaze.
- Continuous signals (pose, GPS) are interpolated linearly only across gaps shorter than
  `pose_max_gap_s` / `gps_max_gap_s`; longer gaps stay empty.
- External GPS loggers: a declared offset maps logger time to device time; the residual offset
  is estimated by maximising the correlation between GPS speed and pose speed (search
  +-`max_lag_s`, parabolic refinement) and applied only if reliable (correlation >=
  `min_correlation`, peak not at the boundary). Estimate, correlation and decision are always
  reported. On synthetic data a 0.6 s residual is recovered within 0.01 s.
- Known limitation: with 10 Hz RGB a gaze sample can be up to 50 ms away from its frame; during
  fast head rotations the scene moves in the image within that time, so narrow targets can be
  missed (visible in the synthetic test). Motion-compensated lookup (using head rotation and the
  camera model) is **planned**.

## 5. Ride trimming

Goal: remove the periods before departure and after arrival (adjusting glasses, talking with
the researcher, scooter standing still, activities after the route) without arbitrary manual
cuts.

Rule (all parameters configurable; values are provisional):

1. smoothed speed on a 10 Hz grid from pose (VIO) or, if absent, GPS (Doppler speed or positions);
2. *moving* = speed > `speed_threshold_mps` (2.0 m/s: above walking speed, so walking the
   scooter is not riding);
3. runs shorter than `min_moving_duration_s` (10 s) are discarded;
4. optional, experimental IMU vibration check (disabled by default, not validated);
5. riding interval = first-to-last qualifying run (stops at traffic lights stay inside) or the
   longest merged block;
6. buffers (2 s) before/after, clipped to the recording.

A manual override in the manifest (`trimming_override`, with reason and staff code) always wins;
the automatic result is still computed and the difference reported. The decision is saved in
`trimming.json` (method, reason, parameters, all runs, all timestamps). Raw data are never
modified. **Validation planned:** compare automatic and manual trimming on pilot recordings.

## 6. Route segments and events

- Taxonomy: `configs/taxonomy.yaml` (10 infrastructure classes incl. `other`/`unknown`,
  13 event types). Definitions are drafts: an annotation guide with examples is **TBD**.
- Segments: one infrastructure class, no overlaps; events: may overlap anything, have optional
  reference instant (e.g. closest approach), target class/instance and tags (e.g.
  `cyclist_interaction` + `overtaking`).
- Annotation source: manual annotation of the (anonymised) video is assumed; tool and procedure
  **TBD**. A double-coded subset with agreement statistics (e.g. Cohen's kappa for classes,
  boundary tolerance for times) is recommended. Map-matching of GNSS to a road network
  (e.g. OpenStreetMap) could pre-fill segments: **planned/optional**.
- Annotation times can be given in seconds from recording start (`*_rel_s`) and are converted.

## 7. Kinematics and behaviour metrics

- Horizontal head trajectory -> uniform 10 Hz grid -> Savitzky-Golay smoothing and
  differentiation (window 1.0 s, order 2; order 2 limits overshoot at abrupt changes).
- Signals: speed, longitudinal acceleration (d speed/dt), jerk, direction of travel (undefined
  below 1 m/s), yaw rate of travel direction, lateral acceleration, sway-free path heading,
  lateral deviation from a path smoothed over 5 s.
- Events: deceleration events (accel <= -1.0 m/s^2 for >= 0.3 s, onset extended while <= -0.3);
  stops (speed < 0.3 m/s for >= 1 s). Names are neutral: "deceleration event", not "hard braking".
- Per window (segment, event, approach, whole ride): distance, speed mean/median/SD/CV/P85/max,
  acceleration P95, maximum deceleration, RMS jerk and |jerk| P95, number of deceleration events
  and stops, stop time, yaw-rate SD, lateral acceleration P95, lateral deviation RMS, path heading
  change, sinuosity, coverage.
- Approach windows: 5 s before entering crossings, intersections and roundabouts.
- Smoothness metrics from the motor-control literature (spectral arc length, log dimensionless
  jerk; Balasubramanian et al. 2012, 2015) are noise-sensitive on head data and are **not**
  implemented; RMS jerk is reported instead.

## 8. Scene understanding (semantic segmentation)

- Interface `SemanticSegmenter` -> native label map + `id2label`; a `LabelMapping` (YAML) maps it
  onto the project's 21 semantic classes; label maps are stored per frame in
  `semantic/labels.npz` (possibly at reduced resolution) and read by the semantic-gaze step.
  Heavy inference (Linux, GPU) is decoupled from analysis.
- Candidate pre-trained models (verified on Hugging Face, Oct 2026), **experimental back-end, not
  validated on Aria imagery**:
  - Mask2Former Swin-L trained on Mapillary Vistas v1.2 (65 classes incl. bike lane, crosswalk,
    curb, sidewalk, bicyclist; ~866 MB). Vistas is licensed for non-commercial research.
  - SegFormer / Mask2Former trained on Cityscapes (19 classes; no cycle lane, crossing or curb
    classes: bike lanes are "road", curbs are "sidewalk"). NVIDIA SegFormer weights are for
    non-commercial research/evaluation.
- Gaps: no public segmentation class for e-scooters (Vistas "Other Rider" is the closest);
  "parked vehicle" needs temporal reasoning; Aria RGB is a wide fisheye (models are trained on
  rectilinear images; rectification vs direct use to be evaluated). Open-vocabulary detectors
  (OWLv2, Grounding DINO; models trained with V3Det include "electric kick scooter") are
  candidates for e-scooters and object instances: **planned**.
- Validation **planned**: manually labelled frame subset from the pilot, per-class IoU for the
  classes used in the analysis.

## 9. Semantic gaze

`timestamp -> gaze point -> RGB frame -> semantic class/object -> metrics`

- Projection (extraction step): official approach of the Gen 2 tutorials - the 3-D gaze point
  (`spatial_gaze_point_in_cpf`, when valid) or the yaw/pitch ray at a fallback depth (5 m,
  provisional), transformed with the device calibration (`T_device_cpf`, RGB camera extrinsics)
  and projected with the RGB camera model. Since projectaria-tools 2.3.0 the Gen 2 CPF is
  SVD-based; projections from older versions are not comparable.
- Conventions: CPF x left, y up, z forward; +yaw = left, +pitch = up; pixel coordinates have
  integer values at pixel centres.
- Quality rules: `gaze_status` (valid / invalid / low_confidence) and `lookup_status` (ok /
  no_gaze_point / off_frame / no_frame / no_label_map); each sample weighs the time to the next
  sample, capped at 0.1 s; invalid or unlabelled time is never attributed to a class; shares are
  reported with coverage, validity and labelled fractions; gaze is never interpolated.
- Lookup: label of the pixel under the gaze point, or majority within a radius reflecting gaze
  accuracy (`lookup_radius_px`, 0 by default, provisional).
- Reference frames: eye-in-head (CPF) angles; with head pose, gaze azimuth/elevation in the world
  and gaze yaw **relative to the direction of travel** (forward-looking and lateral metrics use it
  when available; coverage reported).
- Metrics per window: time share per class and group (pedestrians, other vulnerable road users,
  vehicles, infrastructure, ...), dwells (consecutive samples on one class; blinks <= 0.15 s
  bridged), transitions and transition entropy, stationary (semantic) entropy, I-VT fixations
  (50 deg/s, >= 0.1 s; provisional - the threshold depends on sampling rate and head motion),
  forward share, lateral glances, yaw/pitch SD, BCEA (P = 0.682), spatial entropy (5 deg bins),
  vertical bands (proxy for near/far, not a distance), head-yaw SD relative to travel.
- Methodological notes: fixation definitions differ across the field (Hessels et al. 2018); in
  head-mounted mobile settings eye and head movements must be considered together (Kothari et
  al. 2020); frame-by-frame vs fixation-by-fixation dwell estimates differ (Vansteenkiste et al.
  2015). The I-VT on 30 Hz data is a coarse event detector and must be validated on pilot data.

## 10. Perception -> action

For each event with a target (class and optionally instance id):

- **first gaze**: first time the gaze rests on the target for >= 0.1 s, searched from 5 s before
  the event start to the event end;
- **reference instant**: annotated (e.g. closest approach) or event start;
- **visual anticipation** = reference - first gaze (negative if seen after the reference, e.g. a
  vehicle overtaking from behind);
- **action onset**: first deceleration below -0.5 m/s^2 for >= 0.2 s after the first gaze (or
  from the search start), up to 3 s after the event end;
- **perception-to-action latency** = action onset - first gaze;
- maximum deceleration, minimum speed, speed at first gaze, interaction duration, infrastructure
  class at the reference instant;
- **minimum clearance**: not estimable yet (needs distance to the target: depth estimation,
  3-D tracking or stereo) -> NaN with explicit status; **planned**.

Every missing quantity carries a status code (`no_target_defined`, `target_not_observed`,
`no_deceleration_detected`, `no_gaze_stream`, ...). Thresholds and smoothing strongly affect
onset detection: sensitivity analyses over plausible parameter ranges are **planned** before any
confirmatory use. Only deceleration is considered as action; steering responses are **planned**.

## 11. Rider effect vs infrastructure effect

- `segment_metrics.csv` (one row per segment) carries participant, session, recording, route,
  conditions and all metrics; `aggregate` concatenates sessions and can join pseudonymous
  participant covariates. This long format supports mixed-effects models such as
  `metric ~ infrastructure + conditions + (1 + infrastructure | participant)`, intraclass
  correlations and descriptive rider x infrastructure tables (`rider_by_infrastructure.csv`).
- Synthetic and real data are never aggregated together.
- Model specification, covariates, multiple-comparison strategy and software are **TBD**
  (statistical analysis plan after the pilot).

## 12. Validation strategy

| Level | What | Status |
|---|---|---|
| Synthetic ground truth | trimming, GPS clock residual, first gaze, action onset, metrics on analytic signals | **done** (automated tests) |
| Determinism and portability | byte-identical outputs on repeated runs; Windows and Linux runs | **done** (tests; WSL Ubuntu run) |
| Extraction | stream inventory, rates, gaze overlay on frames, VIO validity on the first pilot VRS | planned |
| Trimming | automatic vs manual start/end on pilot sessions | planned |
| Segmentation | IoU on a labelled frame subset | planned |
| Gaze | accuracy check with targets at known positions (calibration routine TBD) | planned |
| Annotations | double coding, agreement statistics | planned |
| Parameters | sensitivity analyses for thresholds marked provisional | planned |

## 13. Key parameters (provisional unless stated)

| Parameter | Value | Rationale |
|---|---|---|
| `trimming.speed_threshold_mps` | 2.0 | above walking speed, below cruising speed |
| `trimming.min_moving_duration_s` | 10 | ignore short movements (repositioning) |
| `trimming.buffer_before_s` / `after` | 2 / 2 | keep departure/arrival dynamics |
| `kinematics.smoothing_window_s`, `savgol_polyorder` | 1.0 s, 2 | noise vs temporal resolution |
| `kinematics.braking.decel_threshold_mps2` | 1.0 | descriptive event detection, not a safety threshold |
| `synchronization.gaze_frame_tolerance_s` | 0.05 | half frame period at 10 Hz |
| `gaze.max_sample_weight_s` | 0.1 | ~3 samples at 30 Hz; longer gaps unobserved |
| `gaze.dwell_bridge_gap_s` | 0.15 | typical blink duration order |
| `gaze.fixation.velocity_threshold_deg_s` | 50 | to validate (sampling rate 30 Hz, head motion) |
| `gaze.forward.yaw_half_width_deg` | 15 | definition of "forward" window |
| `gaze.lateral_glance.yaw_threshold_deg` | 30 | definition of "lateral glance" |
| `events.first_gaze_min_dwell_s` | 0.1 | avoid counting saccades passing over a target |
| `events.action_decel_threshold_mps2` | 0.5 | onset of a voluntary deceleration |

## 14. Main limitations (current)

Head-mounted kinematics; 10 Hz RGB vs 30 Hz gaze; fisheye RGB vs rectilinear training data;
no distance-to-target yet; provisional thresholds; extraction not yet run on a real Gen 2 VRS;
annotation procedure not yet defined.

## 15. References

Eye tracking and gaze metrics

- Salvucci, D. D., & Goldberg, J. H. (2000). Identifying fixations and saccades in eye-tracking protocols. *Proc. ETRA 2000*, 71-78. https://doi.org/10.1145/355017.355028
- Holmqvist, K., Nystrom, M., Andersson, R., Dewhurst, R., Jarodzka, H., & van de Weijer, J. (2011). *Eye tracking: A comprehensive guide to methods and measures.* Oxford University Press.
- Hessels, R. S., Niehorster, D. C., Nystrom, M., Andersson, R., & Hooge, I. T. C. (2018). Is the eye-movement field confused about fixations and saccades? *Royal Society Open Science*, 5(8), 180502. https://doi.org/10.1098/rsos.180502
- Kothari, R., Yang, Z., Kanan, C., Bailey, R., Pelz, J. B., & Diaz, G. J. (2020). Gaze-in-wild: A dataset for studying eye and head coordination in everyday activities. *Scientific Reports*, 10, 2539. https://doi.org/10.1038/s41598-020-59251-5
- Krejtz, K., Duchowski, A., Szmidt, T., Krejtz, I., Gonzalez Perilli, F., Pires, A., Vilaro, A., & Villalobos, N. (2015). Gaze transition entropy. *ACM Transactions on Applied Perception*, 13(1), 4. https://doi.org/10.1145/2834121
- Shiferaw, B., Downey, L., & Crewther, D. (2019). A review of gaze entropy as a measure of visual scanning efficiency. *Neuroscience & Biobehavioral Reviews*, 96, 353-366. https://doi.org/10.1016/j.neubiorev.2018.12.007
- Steinman, R. M. (1965). Effect of target size, luminance, and color on monocular fixation. *JOSA*, 55(9), 1158. https://doi.org/10.1364/JOSA.55.001158
- Crossland, M. D., & Rubin, G. S. (2002). The use of an infrared eyetracker to measure fixation stability. *Optometry and Vision Science*, 79(11), 735-739. https://doi.org/10.1097/00006324-200211000-00011
- Vansteenkiste, P., Cardon, G., Philippaerts, R., & Lenoir, M. (2015). Measuring dwell time percentage from head-mounted eye-tracking data - comparison of a frame-by-frame and a fixation-by-fixation analysis. *Ergonomics*, 58(5), 712-721. https://doi.org/10.1080/00140139.2014.990524

Movement smoothness

- Balasubramanian, S., Melendez-Calderon, A., & Burdet, E. (2012). A robust and sensitive metric for quantifying movement smoothness. *IEEE TBME*, 59(8), 2126-2136. https://doi.org/10.1109/TBME.2011.2179545
- Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015). On the analysis of movement smoothness. *J NeuroEng Rehabil*, 12, 112. https://doi.org/10.1186/s12984-015-0090-9

Cycling and e-scooter studies (gaze, dynamics, naturalistic methods)

- Mantuano, A., Bernardi, S., & Rupi, F. (2017). Cyclist gaze behavior in urban space: An eye-tracking experiment on the bicycle network of Bologna. *Case Studies on Transport Policy*, 5(2), 408-416. https://doi.org/10.1016/j.cstp.2016.06.001
- Rupi, F., & Krizek, K. J. (2019). Visual eye gaze while cycling: Analyzing eye tracking at signalized intersections in urban conditions. *Sustainability*, 11(21), 6089. https://doi.org/10.3390/su11216089
- Vansteenkiste, P., Zeuwts, L., Cardon, G., Philippaerts, R., & Lenoir, M. (2014). The implications of low quality bicycle paths on gaze behavior of cyclists: A field test. *Transportation Research Part F*, 23, 81-87. https://doi.org/10.1016/j.trf.2013.12.019
- Kchour, F., Cafiso, S., & Pappalardo, G. (2024). Understanding cyclists' visual behavior using eye-tracking technology: A systematic review. *Sensors*, 25(1), 22. https://doi.org/10.3390/s25010022
- Pashkevich, A., Burghardt, T. E., Pulawska-Obiedowska, S., & Sucha, M. (2022). Visual attention and speeds of pedestrians, cyclists, and electric scooter riders when using shared road - a field eye tracker experiment. *Case Studies on Transport Policy*, 10(1), 549-558. https://doi.org/10.1016/j.cstp.2022.01.015
- Chen, D., Hosseini, A., Smith, A., Zheng, Z., Xiang, D., Heydarian, A., Shoghli, O., & Campbell, B. (2025). Impact of road infrastructure and traffic scenarios on e-scooterists' riding and gaze behavior. *ICTD 2025* (ASCE), 373-383. https://doi.org/10.1061/9780784486207.032
- Kegalle, H. N., Hettiachchi, D., Chan, J., Sanderson, M., & Salim, F. D. (2025). Watch Out! E-scooter Coming Through!: Multimodal sensing of mixed traffic use and conflicts through riders' ego-centric views. *Proc. ACM IMWUT*, 9(1). https://doi.org/10.1145/3712284
- Rizehbandi, S., Fiolic, M., Babic, D., Cvahte Ojstersek, T., & Babic, D. (2026). Visual attention and perceived workload of e-scooter riders across selected urban route conditions. *Sustainability*, 18(17), 8851. https://doi.org/10.3390/su18178851
- Garman, C. M. R., Como, S. G., Campbell, I. C., Wishart, J., O'Brien, K., & McLean, S. (2020). Micro-mobility vehicle dynamics and rider kinematics during electric scooter riding. SAE Technical Paper 2020-01-0935. https://doi.org/10.4271/2020-01-0935
- Dozza, M., Violin, A., & Rasch, A. (2022). A data-driven framework for the safe integration of micro-mobility into the transport system: Comparing bicycles and e-scooters in field trials. *Journal of Safety Research*, 81, 67-77. https://doi.org/10.1016/j.jsr.2022.01.007
- Dozza, M., Li, T., Billstein, L., Svernlov, C., & Rasch, A. (2023). How do different micro-mobility vehicles affect longitudinal control? Results from a field experiment. *Journal of Safety Research*, 84, 24-32. https://doi.org/10.1016/j.jsr.2022.10.005
- White, E., Guo, F., Han, S., Mollenhauer, M., Broaddus, A., Sweeney, T., Robinson, S., Novotny, A., & Buehler, R. (2023). What factors contribute to e-scooter crashes: A first look using a naturalistic riding approach. *Journal of Safety Research*, 85, 182-191. https://doi.org/10.1016/j.jsr.2023.02.002
- Kazemzadeh, K., Haghani, M., & Sprei, F. (2023). Electric scooter safety: An integrative review. *Sustainable Cities and Society*, 89, 104313. https://doi.org/10.1016/j.scs.2022.104313
- Dozza, M., & Werneke, J. (2014). Introducing naturalistic cycling data: What factors influence bicyclists' safety in the real world? *Transportation Research Part F*, 24, 83-91. https://doi.org/10.1016/j.trf.2014.04.001

Scene understanding datasets

- Neuhold, G., Ollmann, T., Rota Bulo, S., & Kontschieder, P. (2017). The Mapillary Vistas dataset for semantic understanding of street scenes. *ICCV 2017*, 5000-5009. https://doi.org/10.1109/ICCV.2017.534
