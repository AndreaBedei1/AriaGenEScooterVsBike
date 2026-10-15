# Replication plan

Which methods of the reviewed literature we can replicate, adapt, not reproduce, or should
avoid, given that the **only sensor is Meta Project Aria Gen 2** (on-device eye gaze 30 Hz, RGB
2016x1512 at 15 Hz, IMU 800 Hz, VIO 10 Hz + high-frequency VIO ~800 Hz, hand tracking 10 Hz,
GNSS 1 Hz, PPG; no sensor on the vehicles). Sources and pages are in
[literature_review.md](literature_review.md) and [paper_matrix.csv](paper_matrix.csv).

## 1. Directly replicable

| Method | Source | How with Aria | Status in the code |
|---|---|---|---|
| Mean speed per segment, standstill removed | Kegalle 2025 (p. 217:8); Pashkevich 2022 (Sec. 3.1); Cameli 2025 (p. 8) | GNSS 1 Hz and VIO speed per route segment | implemented (`segment_metrics.speed_*`) |
| PELT speed change points per km, fixed penalty | Kegalle 2025 (p. 217:8, 217:11) | 1 Hz speed, l2 cost, jump 5, fixed reported penalty + sensitivity band | planned (option; reference scripts in `replication/kegalle2025/k02*`) |
| Infrastructure comparison within riders | Kegalle 2025; Mantuano 2017; Hristov 2024; Rizehbandi 2026 | route segments shared by all rides (`map-segments`) + mixed models | data structure implemented; models planned |
| AOI time shares, dwell and visit counts | Ma 2024 review (p. 62); Pashkevich 2022 (Tab. 3) | semantic gaze time shares per class / group | implemented on label maps; model selection planned |
| Gaze entropy (stationary, transition) | Guo 2023 (p. 326); Chen 2025 | semantic and spatial entropy per window | implemented |
| Horizontal / vertical gaze variability, BCEA | Guo 2023; Hristov 2024 (as "dispersion") | yaw/pitch SD and BCEA in degrees (CPF) | implemented |
| Junction zoning far / near / crossing | Hristov 2024 (p. 154) | distance along route before the junction point (route geometry) | approach windows implemented (time-based); distance-based zoning planned |
| Head-rotation events beyond +-20 deg (frequency, duration, angle) | Matviienko 2023 (PDF p. 4) | head yaw relative to the travel direction from VIO | lateral glance metrics implemented for gaze; head-yaw events planned |
| Linear fit of natural decelerations (slope, R^2) | Dozza 2023 (p. 26); Vetturi 2023 (p. 411) | VIO speed at natural stops (traffic lights, yielding) | deceleration events implemented; slope fit planned |
| NASA-TLX after each ride | Rizehbandi 2026; Kchour 2026 | short post-ride questionnaire | in the pilot protocol |
| Gaze validity threshold per rider/segment | Kegalle 2025 (> 75 %, p. 217:11) | quality report per segment | implemented (`q_gaze_*`, `quality_flag`) |

## 2. Adaptable to Aria Gen 2 only

| Method | Source | Adaptation | Caveat |
|---|---|---|---|
| Fixation detection (I-VT presets, dwell algorithms) | Kegalle 2025; Mantuano 2017; Rizehbandi 2026 | I-VT on 30 Hz CPF angles, gaze-in-world when VIO is valid, reported thresholds and sensitivity | not comparable 1:1 with 50-60 Hz vendor presets (see kegalle_replication.md) |
| Sight-vector length and gaze angle to travel direction | von Stülpnagel 2020 (pp. 229-231) | gaze ray (CPF) + VIO pose: angle automatically; length from vergence depth (short range only) or ray-ground intersection | vergence depth unreliable beyond a few metres; ground-plane assumption to validate |
| Near/far/goal gaze, look-ahead | Vansteenkiste 2013, 2014 | vertical gaze bands (proxy) and ground intersection of the gaze ray | proxy; head pitch and terrain affect it |
| Target area anchored to the heading point | Mantuano 2017 (pp. 411-412) | projection of the VIO travel direction into the RGB image | needs VIO-camera calibration (available) |
| Encounter counts | Kegalle 2025 (pp. 217:9-10) | detector + tracker on fisheye RGB; moving vs parked separated | exposure covariate only |
| Object-level gaze ("looking at the vehicle") | Berge 2025; Kchour 2026 | gaze-to-mask/box angular distance with a tolerance derived from measured gaze accuracy | Aria gaze accuracy while riding unknown: must be measured |
| Head movement | Chen 2025 (glasses IMU); Kegalle 2025 (accelerometer) | gyroscope / VIO angular velocity, low-frequency band for voluntary rotation, high band for vibration | head motion != vehicle motion |
| Vibration exposure | Ma 2021 (vehicle box); Cameli 2025 (seat IMU, ISO 2631) | head IMU spectrum / RMS in bands | head is not the vehicle frame; pedalling adds periodic motion on the bicycle |
| Speed and heading | all kinematic studies | head trajectory from VIO (gravity aligned) and GNSS | estimates, validated in the pilot against route length and GNSS |
| Interaction episodes | Zhang 2026 (TTC from cameras) | annotated events + detector tracks; distance only if depth is estimated | TTC not available without metric depth |
| Heart rate as covariate | Guo 2023 (smartwatch HR) | Aria PPG (nose pad) | motion artefacts; Meta's HR estimate not validated (Kong 2025) |

## 3. Requiring sensors we do not have

| Method | Source | Missing sensor |
|---|---|---|
| Brake actuation, braking response time to a command | Dozza 2022, 2023 | brake lever sensors, external trigger |
| Steering angle, handlebar roll, slalom metrics | Dozza 2022; Li 2023 | handlebar potentiometer / vehicle IMU |
| Vehicle-frame vibration and comfort classes (ISO 2631) | Cameli 2025; Ma 2021 | vehicle / seat IMU |
| Trajectories of all road users, minimum TTC / distance | Zhang 2026; Distefano 2026; Dozza 2023 (LiDAR) | infrastructure cameras, drone, LiDAR |
| Cadence, power | Cameli 2025; Kchour 2025 review | cadence / power meter |
| EEG workload indices | Kchour 2026 | EEG headset |
| EDA / skin conductance | Su 2025; Guo 2023 review items | EDA sensor |
| Third-person and 360 deg video | Kegalle 2025 | follower camera, helmet 360 camera |
| Pupil diameter | Ágoston 2026 | measured on device but not exposed by projectaria-tools 2.3.0 |

## 4. Scientifically weakly justified (not replicated)

| Method | Source | Why |
|---|---|---|
| "Gaze dispersion" / "accelerometer dispersion" as coded | Kegalle 2025 | not a dispersion; near-constant by construction |
| AIC-based PELT penalty selection as coded | Kegalle 2025 | degenerate (always favours no change point at the top of the grid) |
| Between-subject post hoc after within-subject ANOVA; frame-level rows as independent observations | Kegalle 2025; Kchour 2026; Su 2025 | wrong error structure, inflated certainty |
| Heart-rate change-point counts as "stress" | Guo 2023 | threshold unreported; exertion and slope confounds |
| Pupil diameter as workload outdoors without luminance control | Ágoston 2026 (exploratory) | illumination dominates pupil size |
| Machine-learning prediction of workload with random frame splits | Kchour 2026 | train/test leakage |
| Descriptive "significant" claims without tests | Hristov 2024 | no inferential basis |
| Fixed vehicle order | Trefzger 2021 | order and learning confounded with vehicle |

## 5. Our possible extensions

1. **Segment-matched within-participant contrasts**: the same physical route segment ridden with
   both vehicles and repeated, aligned by route geometry (implemented: route builder +
   `map-segments` + `within_participant_vehicle_contrasts.csv`).
2. **Time-locked perception-action**: first valid gaze on a tracked road user -> onset of
   deceleration / heading change / head turn, with explicit exclusion rules
   (`events.perception_action` implemented for decelerations; extension to heading and head
   turns planned).
3. **Gaze-in-world and gaze relative to the travel direction** from VIO, instead of image-space
   AOIs (implemented).
4. **Head rotation vs eye rotation decomposition** for scanning (eye-in-head + head-in-world)
   per vehicle (data available; metrics planned).
5. **Repeatability (ICC) of gaze, head and speed metrics** across trials and vehicles (planned;
   requires 2 trials per vehicle).
6. **Validation of single-wearable riding dynamics** (VIO speed and decelerations vs GNSS,
   route length and video-annotated stops) - an open methodological gap.
7. **Hand-tracking coverage while riding** as an exploratory feasibility result (RQ5).
