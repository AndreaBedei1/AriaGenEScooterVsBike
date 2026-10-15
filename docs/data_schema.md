# Data schema

All formats are plain and portable: YAML (manifests, configs), CSV (tables, UTF-8, `\n`, fixed
float precision), NPZ (label maps), JSON (reports). Paths stored in files are relative and
`/`-separated. The canonical column definitions are generated from the code
(`python -m ariagen_escooter schema`) and reproduced in section 4; a test keeps this document in
sync with the code.

## 1. Identifiers (pseudonymous)

| Entity | Pattern | Example | Notes |
|---|---|---|---|
| participant | `P001`..`P999` | `P007` | `SYN001`.. reserved for synthetic data |
| session | `<participant>_S<nn>` | `P007_S02` | one visit / ride session |
| recording | `<session>_R<nn>` | `P007_S02_R01` | one VRS file = one ride (a restarted ride gets a new recording with `trial.part: 2`) |
| trial | (vehicle_type, trial_number) per participant | `bicycle`, `2` | repetition of a vehicle; `ride_order` = position in the participant's whole protocol |
| route segment | `<recording>_SEG<nnn>` | `P007_S02_R01_SEG004` | |
| event | `<recording>_EV<nnn>` | `P007_S02_R01_EV012` | |

Pseudonyms are allocated with `new-session --next` (numbers are never reused). The key linking a
pseudonym to a person is kept by the study team outside the repository and outside the data
folders (`docs/privacy_pipeline.md`). Annotator and staff codes (e.g. `R01`) are also codes,
never full names.

## 2. Folder layout

```
data/raw/<session>/manifest.yaml
data/raw/<session>/<recording>/recording.vrs           (+ optional mps/, external GPS)
data/interim/<session>/<recording>/streams/*.csv       canonical streams (extract-aria)
data/interim/<session>/<recording>/annotations/*.csv   route segments and events
data/interim/<session>/<recording>/semantic/labels.npz label maps
data/interim/<session>/<recording>/inventory.csv, extraction.json, extraction_quality.json
data/interim/<session>/<recording>/annotations/segments_route.csv  map-matched route segments (to review)
data/processed/<session>/<recording>/...               outputs of `run`
data/processed/_study/                                 outputs of `aggregate`
data/synthetic/SYN001_S01/...                          SYNTHETIC / TEST DATA (self-contained)
```

A session folder may also be self-contained (`<session>/<recording>/streams/`), as the synthetic
one; the loader looks there first, then in `data/interim`.

## 3. Conventions

- **Time**: `t_ns` = int64 nanoseconds of the Aria device clock (`DEVICE_TIME`). Annotation
  files may instead use `t_start_rel_s`, `t_end_rel_s`, `t_reference_rel_s` (seconds from the
  first sample of the recording); they are converted on load. Reports add `*_rel_s` fields.
- **Eye-in-head angles**: CPF frame (x left, y up, z forward); direction
  `~ (tan(yaw), tan(pitch), 1)`; +yaw = left, +pitch = up.
- **World frame**: gravity aligned, z up (MPS world frame or gravity-aligned VIO odometry);
  azimuths counter-clockwise from +x, so +yaw relative to travel = left.
- **Pixels**: full-resolution RGB coordinates, integers at pixel centres
  (image spans [-0.5, W-0.5)), as in projectaria_tools.
- **Units** are part of column names (`_s`, `_ns`, `_m`, `_mps`, `_mps2`, `_mps3`, `_deg`,
  `_rad`, `_radps`, `_px`).
- **Missing values** are empty cells (CSV) or `null` (JSON); they are never replaced by
  invented values.

## 4. Canonical streams and annotations

### Streams

#### `frames.csv` - frames

Index of RGB frames (pixels are stored elsewhere; only timing/size here).

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `frame_index` | int | - | yes | Frame number within the recording (0-based). |
| `width_px` | int | px | no | Full-resolution image width. |
| `height_px` | int | px | no | Full-resolution image height. |

#### `gaze.csv` - gaze

Eye gaze (combined/cyclopean), eye-in-head angles in the CPF frame and optional projection into the RGB image.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `valid` | bool | - | yes | Tracking valid according to the source (False = no usable gaze). |
| `yaw_rad` | float | rad | yes | Gaze yaw in CPF; positive = towards the wearer's left. |
| `pitch_rad` | float | rad | yes | Gaze pitch in CPF; positive = up. |
| `u_px` | float | px | no | Gaze point column in the full-resolution RGB image (projectaria_tools convention: integers at pixel centres). |
| `v_px` | float | px | no | Gaze point row in the full-resolution RGB image. |
| `confidence` | float | 0-1 | no | Source-provided confidence, if any. |
| `depth_m` | float | m | no | Vergence-based gaze depth, if provided (unreliable at distance). |
| `spatial_point_valid` | bool | - | no | 3-D (vergence) gaze point valid (Aria). |
| `left_valid` | bool | - | no | Left-eye gaze valid (Aria vergence block). |
| `right_valid` | bool | - | no | Right-eye gaze valid (Aria vergence block). |

#### `imu.csv` - imu

Head-mounted IMU (accelerometer + gyroscope) in the stated IMU frame.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `accel_x_mps2` | float | m/s^2 | yes | Specific force, x axis. |
| `accel_y_mps2` | float | m/s^2 | yes | Specific force, y axis. |
| `accel_z_mps2` | float | m/s^2 | yes | Specific force, z axis. |
| `gyro_x_radps` | float | rad/s | yes | Angular velocity, x axis. |
| `gyro_y_radps` | float | rad/s | yes | Angular velocity, y axis. |
| `gyro_z_radps` | float | rad/s | yes | Angular velocity, z axis. |

#### `pose.csv` - pose

Head (CPF) pose in a gravity-aligned local world frame (z up), e.g. from on-device VIO or MPS SLAM.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `x_m` | float | m | yes | Position x (horizontal). |
| `y_m` | float | m | yes | Position y (horizontal). |
| `z_m` | float | m | yes | Position z (up). |
| `qw` | float | - | no | Orientation quaternion w (world <- CPF). |
| `qx` | float | - | no | Orientation quaternion x. |
| `qy` | float | - | no | Orientation quaternion y. |
| `qz` | float | - | no | Orientation quaternion z. |
| `quality` | float | 0-1 | no | Source quality indicator, if any. |
| `valid` | bool | - | no | Sample usable (VIO: status VALID and pose quality GOOD). |
| `vio_status` | str | - | no | VIO status as reported (VALID, FILTER_NOT_INITIALIZED, INVALID). |
| `tracking_quality` | str | - | no | VIO pose quality as reported (GOOD, BAD, ...). |
| `visual_tracking_quality` | str | - | no | VIO visual tracking quality, if reported. |
| `tracking_session` | str | - | no | VIO session id; a change marks a tracking reset. |

#### `pose_hf.csv` - pose_hf

High-frequency head pose (Aria on-device VIO at ~800 Hz = IMU pre-integration on top of the 10 Hz VIO, NOT independent visual estimates), resampled by nearest sample to a configured rate.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `x_m` | float | m | yes | Position x (horizontal). |
| `y_m` | float | m | yes | Position y (horizontal). |
| `z_m` | float | m | yes | Position z (up). |
| `qw` | float | - | no | Orientation quaternion w (world <- CPF). |
| `qx` | float | - | no | Orientation quaternion x. |
| `qy` | float | - | no | Orientation quaternion y. |
| `qz` | float | - | no | Orientation quaternion z. |
| `quality` | float | 0-1 | no | quality_score of the high-frequency VIO sample. |
| `valid` | bool | - | no | Sample usable (VIO: status VALID and pose quality GOOD). |
| `vio_status` | str | - | no | VIO status as reported (VALID, FILTER_NOT_INITIALIZED, INVALID). |
| `tracking_quality` | str | - | no | VIO pose quality as reported (GOOD, BAD, ...). |
| `visual_tracking_quality` | str | - | no | VIO visual tracking quality, if reported. |
| `tracking_session` | str | - | no | VIO session id; a change marks a tracking reset. |

#### `hands.csv` - hands

On-device hand tracking: per hand presence, confidence, wrist and palm positions in the CPF frame (x left, y up, z forward). Absent = not detected (occlusion, out of view, tracking loss); it is never evidence that the hand left the handlebar.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `left_present` | bool | - | yes | Left hand detected by the tracker. |
| `left_confidence` | float | 0-1 | no | Tracker confidence (empty if absent). |
| `left_wrist_x_m` | float | m | no | Wrist position x (CPF). |
| `left_wrist_y_m` | float | m | no | Wrist position y (CPF). |
| `left_wrist_z_m` | float | m | no | Wrist position z (CPF). |
| `left_palm_x_m` | float | m | no | Palm centre x (CPF). |
| `left_palm_y_m` | float | m | no | Palm centre y (CPF). |
| `left_palm_z_m` | float | m | no | Palm centre z (CPF). |
| `right_present` | bool | - | yes | Right hand detected by the tracker. |
| `right_confidence` | float | 0-1 | no | Tracker confidence (empty if absent). |
| `right_wrist_x_m` | float | m | no | Wrist position x (CPF). |
| `right_wrist_y_m` | float | m | no | Wrist position y (CPF). |
| `right_wrist_z_m` | float | m | no | Wrist position z (CPF). |
| `right_palm_x_m` | float | m | no | Palm centre x (CPF). |
| `right_palm_y_m` | float | m | no | Palm centre y (CPF). |
| `right_palm_z_m` | float | m | no | Palm centre z (CPF). |

#### `gps.csv` - gps

GNSS fixes (glasses, companion phone or external logger) mapped to device time.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `t_ns` | int | ns | yes | Timestamp in the device clock (Aria DEVICE_TIME). |
| `lat_deg` | float | deg | yes | WGS84 latitude. |
| `lon_deg` | float | deg | yes | WGS84 longitude. |
| `alt_m` | float | m | no | Altitude. |
| `accuracy_m` | float | m | no | Horizontal accuracy reported by the receiver. |
| `speed_mps` | float | m/s | no | Receiver speed (Doppler), if available. |
| `vertical_accuracy_m` | float | m | no | Vertical accuracy reported by the receiver. |

### Annotations

#### `segments.csv` - segments

Route segments: non-overlapping, semantically homogeneous stretches of the ride.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `segment_id` | str | - | yes | Unique id, e.g. <recording_id>_SEG001. |
| `t_start_ns` | int | ns | yes | Segment start (device clock). |
| `t_end_ns` | int | ns | yes | Segment end (device clock), > start. |
| `infrastructure_class` | str | - | yes | One of taxonomy.infrastructure_classes. |
| `route_segment_id` | str | - | no | Id of the physical route segment (docs/route/route_segments.csv) for comparisons of the same place across rides and vehicles. |
| `source` | str | - | yes | manual | map_matching | synthetic | ... |
| `annotator` | str | - | no | Pseudonymous annotator code (never a full name). |
| `notes` | str | - | no | Free text (no personal data). |

#### `events.csv` - events

Events/interactions: intervals that may overlap each other and any segment.

| Column | Type | Unit | Required | Description |
|---|---|---|---|---|
| `event_id` | str | - | yes | Unique id, e.g. <recording_id>_EV001. |
| `t_start_ns` | int | ns | yes | Event start (device clock). |
| `t_end_ns` | int | ns | yes | Event end (device clock), > start. |
| `t_reference_ns` | int | ns | no | Reference instant, e.g. closest approach (optional). |
| `event_type` | str | - | yes | One of taxonomy.event_types. |
| `tags` | str | - | no | Extra event types, ';'-separated (e.g. overtaking). |
| `target_class` | str | - | no | Semantic class of the interaction target (for first gaze). |
| `target_instance_id` | int | - | no | Instance/track id of the target, if known. |
| `source` | str | - | yes | manual | synthetic | detector | ... |
| `annotator` | str | - | no | Pseudonymous annotator code. |
| `notes` | str | - | no | Free text (no personal data). |

Validation rules: unique ids; `t_end > t_start`; classes/types/tags/targets must exist in
`configs/taxonomy.yaml`; segments must not overlap; reference times outside their event are
reported as warnings.

### Label maps - `semantic/labels.npz`

| Array | Shape / type | Content |
|---|---|---|
| `frame_index` | (N,) int64 | RGB frame of each map (must exist in `frames.csv`) |
| `labels` | (N, H, W) uint8 | class ids, indexing `class_names` |
| `class_names` | (C,) str | names (re-indexed onto the taxonomy on load) |
| `source_size` | (2,) int64 | (width, height) of the RGB images the maps refer to |
| `backend` | str | producer, e.g. `synthetic_renderer`, `huggingface:<model>` |
| `instances` | (N, H, W) uint16, optional | instance/track ids (0 = none) |

Maps may be lower resolution than the RGB frames; gaze coordinates are scaled.

## 5. Session manifest (`manifest.yaml`)

Validated by `SessionManifest` (unknown keys are errors) and scanned for direct identifiers.
A documented example is `configs/example_session.yaml` (version 2, one e-scooter and one
bicycle ride).

| Field | Description |
|---|---|
| `manifest_version` | `2` for the two-vehicle study; `1` (e-scooter-only format) is still read: every recording is then an e-scooter ride, trial 1 |
| `synthetic` | true only for synthetic data (`SYN` ids) |
| `participant_id`, `session_id` | pseudonymous ids, consistency checked |
| `protocol_version` | version of the acquisition / ethics procedure |
| `route` | `route_id` (e.g. `CES_A`, see `docs/route/`), `variant`, `description` |
| `timing` | `date` (may be generalised for sharing), `start_time_local`, `timezone` |
| `conditions` | `weather`, `road_surface`, `light`, `traffic_density` (coarse categories), `temperature_c`, `notes` |
| `equipment` | internal code of the Aria device, `recording_profile` (name of `configs/recording_profiles/<name>.json`, used for nominal rates), `vehicles[]` (v2: `vehicle_code`, `vehicle_type` from `configs/vehicles.yaml`, `model`, `characteristics`, `notes`), external GPS logger; v1 only: `escooter_code`, `escooter_model` |
| `recordings[]` | `recording_id`; v2 `trial` (`vehicle_type`, `vehicle_code`, `trial_number`, `ride_order`, `part`, optional `route_id`/`route_direction`, `rider_reported_issues`); relative `files` (vrs, mps_dir, external_gps); stream status (`available` / `partial` / `missing` / `unknown`) for rgb, eye_gaze, imu, pose, pose_high_frequency, hand_tracking, gps_device, gps_phone, gps_external, ppg, mps_*; clock information; device time span; optional `trimming_override`; notes; technical issues |
| `notes`, `technical_issues[]` | session-level notes and issues (`description`, `severity`, `streams`) |

Rules (v2): every recording has a trial; a `vehicle_code` must be declared in `equipment.vehicles`
with the same type; `(vehicle_type, trial_number, part)` is unique within a session. A participant
may have several sessions (days), each with one or more rides; `ride_order` keeps the global order
of rides of that participant across sessions (checked by the study team, not by the code).

## 6. Outputs of `run`

`data/processed/<session>/<recording>/`:

| File | Content |
|---|---|
| `report.json` | deterministic summary: ids, trial and vehicle, synthetic notice, config hash and sources (including the vehicle type), input hashes, timestamp checks, quality summary, synchronisation, trimming, kinematics and gaze summaries, whole-ride metrics, counts, issues, output list |
| `quality.json` | data-quality report per stream: timing (effective vs nominal rate, dropout fraction, duplicated / out-of-order / invalid timestamps, classified gaps), VIO status / tracking quality / resets / pose discontinuities, high-frequency VIO quality score, gaze validity, hand detection, GNSS fixes and accuracy, interval fractions; source of the nominal rates |
| `trimming.json` | trimming decision: method, reason, parameters, all moving runs, recording / detected / trimmed intervals (ns and s), removed durations, manual override and automatic comparison |
| `effective_config.yaml` | merged configuration actually used |
| `run_info.json` | non-deterministic metadata (UTC time, versions, platform) |
| `tables/segment_metrics.csv` | one row per route segment: ids, conditions, infrastructure class, behaviour metrics, gaze metrics |
| `tables/approach_metrics.csv` | windows before crossings / intersections / roundabouts |
| `tables/event_metrics.csv` | one row per event: perception -> action metrics with status codes, gaze summary in the event window |
| `tables/event_context.csv` | event x overlapping segment (overlap seconds and fraction) |
| `tables/decel_events.csv`, `stops.csv` | detected deceleration events and stops |
| `tables/gaze_class_time.csv` | long format: window type/id x semantic class -> seconds and share |
| `tables/fixations.csv`, `dwells.csv`, `lateral_glances.csv` | derived gaze events |
| `tables/quality_intervals.csv` | per stream: intervals `observed` / `interpolable` / `degraded` / `unusable` with reason (gap class, tracking reset, no valid samples) |
| `tables/kinematics.csv` | 10 Hz kinematics grid (sample level) |
| `tables/semantic_gaze.csv` | sample-level gaze: status, frame match, class, instance, angles in all frames of reference |
| `figures/overview.png`, `trajectory.png` | diagnostic figures |

Every per-window table starts with the identifiers `participant_id`, `session_id`, `recording_id`,
`synthetic`, `vehicle_type`, `vehicle_code`, `trial_number`, `ride_order`, `trial_part`, `route_id`,
`recording_profile` and the session conditions. Segment and event tables also carry the window
quality columns `q_<stream>_<status>` (fractions of observed / interpolable / degraded / unusable
time for pose, gaze, frames, hands) and `quality_flag` (`ok` / `low_coverage`), and segment tables
carry `route_segment_id` when the segments come from the planned route and the EXPLORATORY hand
columns `hand_*` (detection fractions, wrist position medians/IQR in CPF, inter-wrist distance).

Main columns of `segment_metrics.csv` (behaviour): `duration_s`, `kinematics_coverage`,
`distance_m`, `speed_mean_mps`, `speed_median_mps`, `speed_sd_mps`, `speed_cv`, `speed_p85_mps`,
`speed_max_mps`, `accel_p95_mps2`, `decel_max_mps2`, `jerk_rms_mps3`, `jerk_p95_abs_mps3`,
`n_decel_events`, `n_stops`, `stop_time_s`, `yaw_rate_sd_degps`, `lateral_accel_p95_abs_mps2`,
`lateral_dev_rms_m`, `heading_change_total_deg`, `path_sinuosity`; (gaze):
`gaze_sample_coverage`, `gaze_valid_fraction`, `gaze_labelled_fraction`, `share_<class>`,
`share_group_<group>`, `semantic_entropy_bits`, `n_dwells`, `dwell_mean_s`, `n_transitions`,
`transition_entropy_bits`, `n_fixations`, `fixation_mean_s`, `forward_share`,
`forward_reference_coverage`, `lateral_glances_left/right`, `lateral_glance_rate_per_min`,
`gaze_yaw_sd_deg`, `gaze_pitch_sd_deg`, `gaze_bcea_deg2`, `gaze_spatial_entropy_bits`,
`vertical_share_<band>`, `head_yaw_rel_travel_sd_deg`.

Main columns of `event_metrics.csv`: `t_first_gaze_ns`, `first_gaze_status`,
`visual_anticipation_s`, `t_action_onset_ns`, `action_status`, `perception_action_latency_s`,
`max_decel_mps2`, `min_speed_mps`, `speed_at_first_gaze_mps`, `interaction_duration_s`,
`infrastructure_class_at_reference`, `min_clearance_m` + `clearance_status` (not estimable yet),
`ev_*` gaze summaries in the event window.

## 7. Study level (`aggregate`)

`study_segment_metrics.csv`, `study_event_metrics.csv`, `study_approach_metrics.csv` (rows from
all processed recordings, real and synthetic never mixed), `rider_by_infrastructure.csv`
(participant x infrastructure class: number of segments, total duration, mean of key metrics),
`rider_vehicle_by_infrastructure.csv` (participant x vehicle x infrastructure class) and
`within_participant_vehicle_contrasts.csv` (participant x place - route segment when aligned to the
planned route, else infrastructure class - with the per-vehicle means over trials and the difference
escooter - bicycle; only places observed with both vehicles; windows flagged `low_coverage` are
excluded). These are DESCRIPTIVE tables: inference follows
`docs/methodology/statistical_analysis_plan.md`.

Optional participant covariates (`--participants`): one row per pseudonymous `participant_id`
with coarse categories only (e.g. age band, riding experience, riding frequency, vision
correction). Never names, exact birth dates or contact details. The final list of covariates is
**TBD** (ethics approval).
