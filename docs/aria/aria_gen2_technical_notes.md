# Aria Gen 2: verified technical facts for AriaGenEScooterVsBike

> Technical dossier compiled on 2026-10-15 from the official Project Aria documentation, the projectaria_tools source at tag 2.3.0, the installed package and the official Gen 2 unit-test recordings. Working files mentioned below (introspection scripts) were kept outside the repository.


Compiled 2026-10-15. Sources: the official Project Aria Gen 2 docs, the `facebookresearch/projectaria_tools` source at tag `2.3.0` (main checked at commit `0990209`, 2026-10-15), projectaria.com and meta.com, and the installed `projectaria-tools 2.3.0`. The installed environment was not modified.

## How to read the tags

| Tag | Meaning |
|---|---|
| **VERIFIED IN PACKAGE** | Confirmed by introspecting the installed `projectaria-tools 2.3.0` (`dir()`, docstrings, enum members, pybind signatures). Where the fact is about data values, it was also confirmed by running the installed package on the three official Gen 2 test recordings shipped in the repo (`data/gen2/*.vrs`; they use profiles `profile4`, `profile5` and `profile8_copy` and are only a few seconds long). |
| **DOCS ONLY** | Stated in the official docs or projectaria.com/meta.com. Not checkable in the package (for example hardware specs). |
| **SOURCE CODE (2.3.0)** | Read in the C++/pybind source at tag 2.3.0. The docs say nothing on it. |
| **NOT FOUND — UNVERIFIED** | Neither the docs nor the code answer it. Do not assume it. |

## Abbreviations

| Short form | Full reference |
|---|---|
| `D` | `https://facebookresearch.github.io/projectaria_tools/gen2` (Gen 2 docs site. URLs checked HTTP 200; unknown paths return 404.) |
| `G` | `https://github.com/facebookresearch/projectaria_tools/blob/2.3.0` |
| `NB` | `G/examples/Gen2/python_notebooks/` (official Gen 2 tutorials. The docs site links to these instead of hosting its own tutorial pages, since 2.3.0.) |
| AEC | Auto-exposure controller |
| CPF | Central Pupil Frame (the gaze reference frame) |
| CV cameras | The 4 computer-vision cameras. "SLAM cameras" means the same thing. |
| ET | Eye tracking. ML ET is the machine-learning ET algorithm; "geometric ET" is the older algorithm. |
| GNSS | Global navigation satellite system (GPS, Galileo, etc.) |
| HF VIO | The high-frequency VIO stream (`vio_high_frequency`) |
| HT | Hand tracking |
| MP | Machine perception (the algorithms that run on the glasses) |
| MPS | Machine Perception Services (Meta's cloud post-processing) |
| PPG | Photoplethysmography (heart-rate optical sensor) |
| VIO | Visual-inertial odometry (on-device 6-DoF tracking) |
| VRS | The recording file format |

---

## 0. Versions and changelog (as of 2026-10-15)

**0.1 Package versions.** [VERIFIED (PyPI JSON API)]
- `projectaria-tools`: the latest PyPI release is **2.3.0**, uploaded 2026-08-25. This is the version installed. Earlier releases: 2.2.0 (2026-08-13), 2.1.4 (2026-06-11), 2.1.3, 2.1.2.
- GitHub `main` has `version.txt = 2.3.1` and a 2.3.1 changelog entry, but **2.3.1 is not on PyPI**. Its contents are minor: Python 3.13/3.14 wheels, streaming-viewer CPU use, and `vrs_to_mp4 --help` text. There is no reason to upgrade.
- `projectaria-mps` 1.4.0 (2026-09-02). `projectaria-client-sdk` 2.5.1. `projectaria-vrs-health-check` 1.3.1 on PyPI; the docs changelog already lists 1.3.2.
- Changelog: `D/research-tools/projectariatools/changelog`

**0.2 Changes in 2.3.0 that matter to us.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "`getT_Device_Cpf()` and `getT_Cpf_Sensor()` take a `CpfType` (`CadBased`, `SvdBased`, `Default`) instead of a `bool useSvd`."
- "On Gen2, `get_transform_device_cpf()` now returns the SVD-aligned CPF by default … On-device vs MPS eye gaze agreement improves from 44.05 mrad to 8.74 mrad."
- Installed: `CpfType {CadBased:0, SvdBased:1, Default:2}`. Signature: `get_transform_device_cpf(cpf_type=CpfType.Default)`.
- **Consequence.** The on-device gaze player converts gaze into CPF using `getT_Device_Cpf()` with the default type (`G/core/data_provider/VrsDataProviderFactory.cpp`, `setT_Cpf_DeviceForEyeGazePlayers`). So the CPF that gaze is expressed in depends on the projectaria-tools version. **Pin 2.3.0 for the whole study.**

**0.3 Change in 2.2.0.** [DOCS ONLY] "Official support for ML Eye Tracking (ML ET) … Both are returned as the same `EyeGaze` structure." It also adds `EyeGazeConfiguration` field provenance, the `502-1 battery-status` stream, `rescale_camera_calibration()`, and NVDEC decoding.

**0.4 Fix in 2.1.4.** [DOCS ONLY] "Fixed `AlsDataLayout` … gain_{…} … (these previously read as 0 for every sample)." Use ≥2.1.4 for ALS.

**0.5 Open GitHub PR #398 (not documented).**
- What it says: "Aria Gen 2 glasses can skip blurry RGB frames on purpose." VRS Health Check currently counts those skips as dropped frames.
- The PR adds a per-image `intentional_drop_count` field. That field is **absent in 2.3.0**: `ImageDataRecord` has only `arrival_timestamp_ns, camera_id, capture_timestamp_ns, exposure_duration, frame_number, gain, group_id, group_mask, temperature`.
- Consequence: gaps in RGB `frame_number` may be deliberate skips.
- Source: https://github.com/facebookresearch/projectaria_tools/pull/398 [VERIFIED IN PACKAGE that the field is absent]

---

## 1. Aria Gen 2 hardware

Main source: `D/technical-specs/device/hardware`

**1.1 Sensors.** [DOCS ONLY] "4 CV cameras, RGB camera, 2 eye tracking cameras, 7 spatial microphones, 2 IMUs, barometer, magnetometer, GNSS, ALS (with UV), PPG, contact microphone." A proximity sensor detects when the glasses are worn.

**1.2 RGB camera.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "Sony IMX681 sensor … rolling shutter … 133° horizontal and 99° vertical field of view, with a 12 megapixel, 1.0 μm pixel sensor capable of full-resolution (4032 × 3024) capture at 24 fps."
- "The RGB pipeline supports functions such as binning, downscaling, and cropping … A dedicated on-device color ISP … auto-exposure and auto-white balance."
- Package check: in a test recording at 2016×1512, the RGB calibration is `FISHEYE624`, image size `[2016,1512]`, f ≈ 875.4 px.

**1.3 CV (SLAM) cameras.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "field-of-view of 119°x119° … global shutter … 4.6 µm pixels in a 512 × 512 array … dynamic range capability exceeding 110 dB."
- Package check: `FISHEYE624`, 512×512.

**1.4 Eye-tracking cameras.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "for each eye … a 400x400 pixel resolution infrared (IR) camera and 8 IR LEDs … gaze estimations at up to 90 Hz framerate. Alternatively, the data … can be recorded and processed off-device."
- Package check: the calibration model is `KANNALA_BRANDT_K3`. It is automatically rescaled to 200×200 when the recording is 200×200.

**1.5 IMUs.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "dual 6-axis gyroscopes and accelerometers with a maximum sampling rate of 1600 Hz and a typical sampling rate of 800 Hz."
- Package check (test recording):
  - Sensor model `ICM47688`.
  - VIO online calibration reports `accel_saturation_threshold_m_sec2 = 153.8` (about ±15.7 g) and `gyro_saturation_threshold_rad_sec = 34.2` (about ±1960 °/s).
  - The docs do not state these ranges. This matters for e-scooter vibration analysis.

**1.6 Magnetometer.** [DOCS ONLY + VERIFIED IN PACKAGE] "ultra-low noise … maximum sampling rate of 400 Hz and a typical sampling rate of 100 Hz." Package check: model `BMM350`.

**1.7 Barometer.** [DOCS ONLY + VERIFIED IN PACKAGE] "maximum sampling rate of 240 Hz max and a typical sampling rate of 100 Hz." The predefined profiles use 50 Hz. Package check: model `BMP581`.

**1.8 GNSS.** [DOCS ONLY]
- The tools docs say: "support across bands such as L1, L1 + L5, E1, and E1 + E5 … supports L1 + L5 (GPS) and E1 + E5 (Galileo) dual-frequency signals."
- **This conflicts with projectaria.com/glasses**, which lists "Global Navigation Satellite System (L1)".
- The `constellations_enabled` field in each recorded GNSS sample shows which bands were actually used (see 9.1).

**1.9 PPG.** [DOCS ONLY + VERIFIED IN PACKAGE] "integrated into the nosepad … The PPG sampling rate is typically 128 Hz, with a maximum of 512 Hz." Package check: `PpgConfiguration.sensor_model = "MAX86177"`.

**1.10 ALS.** [DOCS ONLY]
- "The VD6281 sensor provides correlated color temperature (CCT) and lux measurements. It features 5 channels (red, green, blue, IR, UVA), with an additional clear channel for flicker detection."
- The ALS page (`D/technical-specs/device/als`) adds: "**Usable dynamic range** is roughly 1 lux to ~20,000+ lux." Bright outdoor scenes can exceed this (see 10.2).

**1.11 Microphones.** [DOCS ONLY] 7 acoustic microphones, up to 48 kHz. Contact microphone "Knowles V2S200D, embedded within the glasses' nosepad."

**1.12 On-device accelerators.** [DOCS ONLY] "H265 HEVC and audio data using OPUS encoders … 3D articulated hand tracking, eye-tracking with gaze per eye output, and advanced signals such as pupil diameter and blink detection, as well as 6DoF localization."

**1.13 Battery.** [DOCS ONLY]
- "Supports 6–8 hours of continuous recording use with a custom lithium-ion battery." (hardware page)
- projectaria.com/glasses says "6-8 hours".
- No profile-specific recording durations are published. [NOT FOUND — UNVERIFIED for our profile]

**1.14 Weight and sizes.** [DOCS ONLY] Not in the tools docs. Meta blog (https://www.meta.com/blog/aria-gen-2-research-glasses-under-the-hood-reality-labs/): "weighing in at 74 – 76g, depending on size"; "eight size variations".

**1.15 On-device storage capacity.** [NOT FOUND — UNVERIFIED] Not stated in the tools docs, projectaria.com or the Meta blog. A third-party "128 GB" figure appears to belong to Gen 1.

**1.16 Multi-device time alignment.** [DOCS ONLY] SubGHz radio: "measured time offset error … less than 10 μs." This is irrelevant for a single-device study.

---

## 2. Recording profiles

Sources: `D/technical-specs/device/profile` and `D/ark/companion-app/recording-profiles`

**2.1 Predefined profiles.** [DOCS ONLY]

| | profile8 (recording) | profile9 (streaming) | profile10 (recording) | mp_streaming_demo |
|---|---|---|---|---|
| IMU | 800 | 800 | 800 | 800 |
| Magnetometer | 100 | 100 | 100 | — |
| Barometer | 50 | 50 | 50 | — |
| GPS | 1 | — | 1 | — |
| CV cameras | 30 Hz, H265 QP22 | 10 | 30 | 10, QP30 |
| RGB | 10 Hz, 2560×1920, QP22 | 5 Hz, 2560×1920 | **30 Hz, 2016×1512, QP22** | 10 Hz, 2016×1512 |
| ET cameras | 5 Hz, 200×200, QP22 | — | 5 | 5 |
| ET | 30 | 30 | 30 | 30 |
| HT | 30 | 30 | 30 | 10 |
| VIO | 10 | 10 | 10 | 10 |
| PPG | 128 | 128 | 128 | 128 |
| Temperature | 1 | 1 | 1 | 1 |
| ALS | 9.434 Hz / 3200 µs | 9.434 | 10 | — |
| Device info | 30000 ms | 10000 | 30000 | 10000 |

Rates are in Hz unless stated. All four profiles include audio (OPUS, 16 kHz); profiles 8 and 10 also include BLE and Wi-Fi scans.

- The Gen 2 eye-tracking tutorial (`NB/Tutorial_8_eyetracking.ipynb`) names two more profiles: **`profile8_ml_et`** (recording) and **`profile9_ml_et`** (streaming) select the ML eye-tracking algorithm. Plain `profile8` selects the geometric one. **These two profiles are missing from the profile spec page.** [DOCS ONLY]
- The test recordings also contain older profiles: `profile4` ("All sensors and MP verticals enabled with high data rate": ET 90 Hz, RGB `R_2016x1512` 30 Hz) and `profile5`. [VERIFIED IN PACKAGE]

**2.2 Custom profiles are supported, with explicit caveats.** [DOCS ONLY]
- "Custom profiles: User-defined configurations for advanced or experimental use. These may not be stable and are not recommended for general use."
- "There have been reports of **issues retrieving certain sensor data (e.g., GPS) when using custom profiles**."
- "Meta does not guarantee stability, data quality, or tool compatibility for custom profile configurations."
- Recommended practice: "base your custom profile on one of the pre-defined profiles (e.g., profile8)". The documented template is profile8 with RGB 5 Hz, SLAM 10 Hz and HT 10 Hz.

How to load a custom profile:
- **Companion App:** "Make a copy" of a profile, or paste JSON with "+" (`D/ark/companion-app/recording-profiles`).
- **Client SDK CLI:** `aria_gen2 recording start --json-profile <file> --recording-name <name>` (`D/ark/client-sdk/recording`).
- **Client SDK, version 2.5.0 onwards:** `aria_gen2 device profile add|remove|pull` (`D/ark/client-sdk/changelog`).
- **Python:** `RecordingConfig.custom_profile` ("Custom recording profile in JSON format"; `D/technical-specs/client-sdk/api`).

**2.3 JSON key naming.** [DOCS ONLY + VERIFIED IN PACKAGE]
- The documented template and the full profile JSON embedded in real recordings (see 2.9) both use **snake_case keys**: `imus, magnetometer, barometer, audio, gps, ble, wifi, slam_cameras, et_cameras, rgb_camera, et, ht, vio, vio_high_frequency_pose, device_info, ppg, temperature, als, name, description, type, tags`.
- **Our draft uses camelCase** (`slamCameras`, `etCameras`, `rgbCamera`, `deviceInfo`). Whether camelCase is accepted is **NOT FOUND — UNVERIFIED**. Use snake_case, or `aria_gen2 device profile pull profile8` to obtain the canonical file.
- Value formats from the template and embedded profiles:
  - `"ir_led": "TRUE"` is a string.
  - `"resolution": "R_200x200"` is the ET camera resolution.
  - Encoder quality is `"video_config": {"cqp": {"qp": N}}`.
  - The embedded `profile8_copy` contains `"type": "RECORDING"`, which matches our draft. The Client SDK `ProfileType` enum is `UNDEFINED / RECORDING / STREAMING`.
- The embedded profiles contain keys the docs never mention: `et.type`, `rgb_camera.denoising_level` and `sharpening_level`, `vio.extract_image_keypoints` and `output_tracks`, `slam_cameras.ispm_correction`, `audio.mic_selection` and `bt_hfp_capture`, `public`, `recommended`.

**2.4 What `R_4032x3024` with width/height 2016×1512 means.**
- The template pairs `"resolution": "R_4032x3024"` with `"width": 2560, "height": 1920`, which gives profile8's 2560×1920 output. [DOCS ONLY]
- Older profiles 4 and 5 instead use `"resolution": "R_2016x1512"` with no width or height. [VERIFIED IN PACKAGE]
- Whether 2016×1512 is produced by **sensor binning or ISP downscaling** is **NOT FOUND — UNVERIFIED**. The only hardware statement is "binning, downscaling, and cropping".
- What the source does show (`G/core/calibration/loader/AriaCalibRescaleAndCrop.cpp`) [SOURCE CODE (2.3.0)]:
  - 4032×3024 → 2016×1512: scale 0.5, offset (0,0). This is the full field of view, isotropic, no crop.
  - 4032×3024 → 2560×1920: scale 0.635, no crop.
  - 4032×3024 → 2560×3024: scale 1.0 with a 640 px horizontal crop.
  - `VrsDataProviderFactory` applies these rescalings to the stored calibration automatically.
- **Action:** run `aria_gen2 device profile pull profile10` to see how Meta encodes its tested 2016×1512 @ 30 Hz profile, then copy that encoding.

**2.5 What switches on on-device machine perception (MP).**
- Docs: "Profiles are used to precisely configure the frequency and types of machine perception algorithm calculations" (`D/ark/device/on_device_mp`). The keys are `et.rate_hz`, `ht.rate_hz` and `vio.rate_hz`.
- The embedded `profile8_copy` has `"et": {"rate_hz": 30, "type": "ET_GEOMETRICAL"}`. [VERIFIED IN PACKAGE]
- **The `et.type` value that selects ML ET is NOT FOUND — UNVERIFIED.** Pull `profile8_ml_et` to get it. Our draft has no `et.type`, so the algorithm the device will run is **undetermined**.

**2.6 Does `vio` also turn on high-frequency VIO?**
- The template carries a separate key, `"vio_high_frequency_pose": {"rate_hz": 800}`. [DOCS ONLY]
- The on-device MP page says Gen 2 "Additionally … also produces" high-frequency output, which implies it always does.
- Package evidence (test recordings): `profile4` and `profile5` have **no** `vio_high_frequency_pose` key, yet still contain an 800 Hz `vio_high_frequency` stream. `profile8_copy` does include the key. [VERIFIED IN PACKAGE]
- Whether current firmware needs the key is **NOT FOUND — UNVERIFIED**. **Recommendation: include `vio_high_frequency_pose: {rate_hz: 800}` explicitly.**

**2.7 ET camera rate is capped when on-device gaze is on.**
- `NB/Tutorial_8_eyetracking.ipynb`: "the ET cameras are capped at 5 Hz whenever on-device gaze is enabled … cameras top out at **90 Hz**."
- Our setting (ET cameras 5 Hz with on-device ET 30 Hz) is consistent with this. [DOCS ONLY]

**2.8 Stream labels and numeric IDs (Gen 2).** Source: `D/technical-specs/vrs/streamid-label-mapper` [DOCS ONLY + VERIFIED IN PACKAGE]

| Stream | VRS stream ID | Label |
|---|---|---|
| ET camera left / right | 211-1 / 211-2 | `camera-et-left` / `camera-et-right` |
| RGB camera | 214-1 | `camera-rgb` |
| Microphones | 231-1 | `mic` |
| Temperature | 246-1 | `temperature` |
| Barometer | 247-1 | `baro0` |
| PPG | 248-1 | `ppg` |
| Device GNSS | **281-2** | `gps` |
| Phone location (Companion App) | 281-1 | `gps-app` |
| Wi-Fi | 282-1 | `wps` |
| Bluetooth | 283-1 | `bluetooth` |
| ALS | 500-1 | `als` |
| SLAM cameras | 1201-1…4 | `slam-front-left`, `slam-front-right`, `slam-side-left`, `slam-side-right` |
| IMUs | 1202-1 / 1202-2 | `imu-left` / `imu-right` |
| Magnetometer | 1203-1 | `mag0` |
| Eye gaze (on-device) | 373-1 | `eyegaze` |
| HT, VIO, HF VIO (on-device) | 371-x | see below |

Also in the source mapper: `241-1 emg`, `502-1 battery-status`, and `285-1` (time-sync/UTC stream).

- The on-device MP pose streams are **dynamic 371-x**. "If handtracking stream exists": `371-1 handtracking`, `371-2 vio`, `371-3 vio_high_frequency`. Otherwise: `371-1 vio`, `371-2 vio_high_frequency`.
- They are identified by flavor strings `device/oatmeal/hand`, `device/oatmeal/vio` and `device/oatmeal/vio_high_frequency`.
- **The stream label is `vio_high_frequency`.** `vio_high_frequency_pose` is only the profile key.
- Package check: all three test recordings resolve to exactly these labels (`371-1 handtracking`, `371-2 vio`, `371-3 vio_high_frequency`, `373-1 eyegaze`).
- ⚠ The quick-reference table at `D/technical-specs` lists **wrong** labels (`rgb 214-1`, `slam-left`, `eyetracking 231-1`, `handtracking 232-1`). Use the mapper page.
- ⚠ `get_stream_id_from_label` "returns an id for every label the glasses *could* record, so it is not on its own a presence check" (Tutorial 8). Also check `get_num_data(sid) > 0`.

**2.9 Reading the recording profile from a VRS file.** [VERIFIED IN PACKAGE; NOT documented]
- `provider.get_metadata().recording_profile` returns the profile **name** only, for example `"profile8_copy"` or `"profile4"`.
- The **full profile JSON** sits in `provider.get_file_tags()["metadata"]` under `recording.profile`. The same `metadata` tag also contains:
  - `recording.sensor_health_stats`: on-device per-sensor drops, time errors and score.
  - `recording.stop_event`
  - `client.name`
  - `client.session_uuid`
  - `device.serial`
  - `device.nose_pad_serial`
  - `device.uuid`
  - `calib_json`, which embeds serial numbers.
- Other file tags: `device_serial`, `session_id`, `capture_time_epoch`, `os_fingerprint`.
- **Privacy:** strip or hash all of these identifiers before release.

---

## 3. On-device VIO and high-frequency VIO

**3.1 10 Hz VIO outputs.** [DOCS ONLY] From `D/ark/device/on_device_mp`: "The VIO output is generated at 10Hz with the following output: 3-DOF position; 3-DOF linear velocity; 3-DOF orientation in quaternion form; 3-DOF angular velocity; Estimated direction of gravity for the odometry frame." VIO fuses "four CV cameras and two IMUs".

**3.2 How high-frequency VIO is computed (exact quote).** [DOCS ONLY + VERIFIED IN PACKAGE]
- `D/ark/device/on_device_mp`: "*Additionally, Aria Gen2 also produces high-frequency VIO output (the fields of the output are the same regular VIO) at IMU rate (800Hz), by performing IMU pre-integration on top of the regular 10Hz VIO output. The high-frequency VIO output can be useful for applications where low-latency VIO poses are needed.*"
- `NB/Tutorial_6_vio_and_trajectory.ipynb`: "VIO High Frequency results are generated directly from the on-device VIO results by performing IMU integration between VIO poses, hence provides a much higher data rate at approximately **800Hz**."
- So it is **not** an independent estimate. It is IMU pre-integration anchored on the 10 Hz VIO poses.
- Note that "the fields … are the same" is inaccurate at the API level. High-frequency VIO uses `OpenLoopTrajectoryPose` (fact 3.7), which has **no** `status`, `pose_quality`, visual quality or online calibration.

**3.3 `FrontendOutput` (10 Hz VIO): fields and enums.** [VERIFIED IN PACKAGE]
- Fields:

  | Field | Docstring / note |
  |---|---|
  | `frontend_session_uid` | "Uid tag for the Frontend session. Regenerate on Frontend reset." |
  | `frame_id` | |
  | `capture_timestamp_ns` | "Center capture time of the frame set." |
  | `unix_timestamp_ns` | Unreliable, see 3.5 |
  | `status` | `VioStatus` |
  | `pose_quality` | `TrackingQuality` |
  | `visual_tracking_quality` | `VisualTrackingQuality` |
  | `online_calib` | `OnlineCalibState`: `cam_parameters`, `imu_model_parameters`, `dt_ref_cam`, `t_cam_body_imu` |
  | `gravity_in_odometry` | |
  | `transform_odometry_bodyimu` | |
  | `transform_bodyimu_device` | |
  | `linear_velocity_in_odometry` | |
  | `angular_velocity_in_bodyimu` | |
  | `camera_serials` | |

- Enums:
  - `VioStatus {VALID:0, FILTER_NOT_INITIALIZED:1, INVALID:2}`
  - `TrackingQuality {UNKNOWN:0, GOOD:1, BAD:2, UNRECOVERABLE:3}`
  - `VisualTrackingQuality {UNKNOWN:0, BAD:1, GOOD:2}`
- Tutorial 6: "**Always check `status == VioStatus.VALID` and `pose_quality == TrackingQuality.GOOD`** for VIO data validity!"
- [SOURCE CODE (2.3.0)] `G/core/data_provider/players/VioPlayer.cpp`:
  - `pose_quality` is set from a boolean, `is_tracker_healthy ? GOOD : BAD`. **UNKNOWN and UNRECOVERABLE are never produced.**
  - `visual_tracking_quality` comes from `is_map_tracking_healthy`.
  - The VRS layout also holds `reset_status`, `odometry_uuid`, `num_track_measurements` and `num_keypoints`. **None of these are exposed in Python.**
- Source comment in `FrontendTypes.h`: "when visual tracking is lost, VIO still tracks with IMU only (integration for seconds, and TLIO for longer)." A visually BAD but VIO GOOD sample is therefore plausible.

**3.4 Frames and units.** [DOCS ONLY + VERIFIED IN PACKAGE]
- Device pose = `transform_odometry_bodyimu @ transform_bodyimu_device` (Tutorial 6 code).
- "body IMU is the IMU that is picked as the reference for motion tracking … this is often `imu-left`."
- Linear velocity is in m/s in the odometry frame. Angular velocity is in rad/s in the body-IMU frame.
- Test recordings show `gravity_in_odometry = [0, 0, -9.81]`, so the odometry frame is gravity-aligned with z up. This is observed, not stated in the docs.
- The odometry frame origin is arbitrary for each session.

**3.5 VIO timestamps.** [VERIFIED IN PACKAGE]
- On all test recordings, `capture_timestamp_ns` equals the `slam-front-left` frame timestamps exactly.
- **`unix_timestamp_ns` is not filled by `VioPlayer` in 2.3.0.** The test files return garbage values: −2.86e18, 3.33e18 and 0. **Do not use it.** For UTC, use the UTC time domain or GPS `utc_time_ms`.

**3.6 Resets.** [DOCS ONLY + SOURCE CODE (2.3.0)]
- A reset shows up as a change of `frontend_session_uid` ("Session identifier (resets on VIO restart)", Tutorial 6).
- For high-frequency VIO, `session_uid` is copied from `frontend_session_uuid` (source).
- For MPS open-loop output: "When the session_uid is the same, poses and velocities are defined in the same coordinate frame."
- VRS Health Check computes `Pose Data Class (vio).reset_frequency_per_min` (`D/ark/vrs_health_check/changelog`).
- The docs give no further procedure for handling resets. [NOT FOUND — UNVERIFIED]

**3.7 High-frequency VIO data type.** [VERIFIED IN PACKAGE + SOURCE CODE (2.3.0)]
- `get_vio_high_freq_data_by_index` / `_by_time_ns` return `mps::OpenLoopTrajectoryPose`:

  | Field | Note |
  |---|---|
  | `tracking_timestamp` | `datetime.timedelta` in device time (µs). Source: `capture_timestamp_ns` = "Latest IMU timestamp used to estimate this pose result". |
  | `transform_odometry_device` | |
  | `device_linear_velocity_odometry` | |
  | `angular_velocity_device` | |
  | `gravity_odometry` | |
  | `quality_score` | "float between [0, 1] … qualityScore = 1: we are confident …; 0: no confidence" |
  | `session_uid` | |
  | `utc_timestamp` | Unreliable, see below |

- **`utc_timestamp` is not filled for on-device data.** It is the same garbage constant in every file (81 277 days).
- There is no status or tracking-quality enum. Validity must be inferred from `quality_score`, `session_uid` continuity and the bracketing 10 Hz VIO status.
- Tutorial 6 filters `quality_score > 0.5` as an example. That threshold is not normative. In the test recordings `quality_score` was 1.0 for every sample.

**3.8 High-frequency VIO observed behaviour (test recordings).** [VERIFIED IN PACKAGE]
- Nominal rate 800.0 Hz. Effective 786.8–796.9 Hz.
- Median Δt is 1.252–1.255 ms, which matches the IMU's effective ~797 Hz.
- There were occasional 2.5 ms gaps, i.e. single missing samples.
- No non-monotonic timestamps were seen.
- **The timestamps do not match IMU sample timestamps**: 0 of 235 matched. The median offset to the nearest `imu-right` sample was 0.26–0.32 ms.
- High-frequency poses agree with the 10 Hz VIO pose at the nearest timestamp to within ≤0.21 mm.
- The stream starts about 23–65 ms before the first VIO record and ends about 33 ms after the last.
- `get_vio_high_freq_configuration` gives `nominal_rate_hz=800`, `message_version="0.1"`.

**3.9 Data-quality statements in the docs.**
- VRS Health Check: "`longest_consecutive_drop` … Ignored on `Pose Data Class (vio)`, `Pose Data Class (vio_high_frequency)` … whose sample cadence does not make a consecutive-drop count meaningful." The VIO drop-ratio threshold is fail 5% / warn 2%. [DOCS ONLY]
- Any statement on high-frequency VIO dropouts, invalid timestamps or drift magnitude is **NOT FOUND — UNVERIFIED**.

**3.10 MPS open-loop trajectory (offline counterpart).** [DOCS ONLY] Source: `D/technical-specs/mps/data_formats/slam/mps_trajectory`
- Columns: `tracking_timestamp_us, utc_timestamp_ns (-1 if unavailable), session_uid, {tx,ty,tz,qx,qy,qz,qw}_odometry_device, device_linear_velocity_{x,y,z}_odometry, angular_velocity_{x,y,z}_device, gravity_{x,y,z}_odometry, quality_score`.
- The docs say "IMU rate, which is 1kHz". ⚠ That is Gen 1 wording and inconsistent with Gen 2's 800 Hz IMU.
- MPS basics (`D/technical-specs/mps/data_formats/slam/basics`):
  - Device time "is strictly monotonic, has stable clock speed, and is accurate in duration".
  - UTC "is not guaranteed to be monotonic … do not compute duration between two UTC timestamps".

**3.11 Inconsistent axis descriptions in the docs.** [DOCS ONLY]
- `D/technical-specs/device/calibration`: device frame is "X-axis: Points to the right … Y-axis: Points downward … Z-axis: Points forward"; the origin is `slam-front-left`.
- `D/technical-specs/coordinate/3d-coor`: the camera frame "axes points to left, up and forward".
- Trust the calibration transforms, not these prose descriptions.

---

## 4. On-device eye tracking (ET)

**4.1 Documented outputs.** [DOCS ONLY] From `D/ark/device/on_device_mp`:
- Per eye, "up to 90Hz":
  - "origin and direction of the individual gaze ray"
  - "3-DOF position of the entrance pupil"
  - "diameter of the pupil"
  - "Whether the eye is blinking"
- Combined: "origin and direction of the combined gaze ray; Vergence depth …; Distance between the left/right eye pupils, a.k.a, IPD".

**4.2 Two on-device algorithms share one stream.** [DOCS ONLY + VERIFIED IN PACKAGE] From Tutorial 8:
- Geometric ET is used by `profile8`. ML ET is used by `profile8_ml_et` and `profile9_ml_et`.
- Both write `eyegaze` (373-1). "A single recording contains **one** of them, never both."
- ML ET "delivers noticeably better gaze quality."
- On ML ET, blink, entrance-pupil position and pupil diameter are "**not produced**". `GAZE_ORIGIN` and `GAZE_ORIGIN_COMBINED` are `HARDCODED` ("a device constant, not this wearer's anatomy").
- Identifying the algorithm:
  - `algorithm_name` is "often empty — it is not a reliable way to tell the two … apart".
  - Use field provenance instead. "all-`SUPPORTED` therefore means the stream is not ML ET."
  - Package check: all three test recordings report all-SUPPORTED, i.e. geometric. The `profile8_copy` file says `et.type=ET_GEOMETRICAL` and `algorithm_version='1.0'`.

**4.3 Python `EyeGaze` fields.** [VERIFIED IN PACKAGE]
- Top level:

  | Field | Note |
  |---|---|
  | `tracking_timestamp` | timedelta, device time |
  | `session_uid` | |
  | `yaw`, `pitch` | Combined gaze, radians, CPF |
  | `depth` | "0 indicates that the depth is not available" |
  | `yaw_low`, `yaw_high`, `pitch_low`, `pitch_high` | Confidence interval |
  | `combined_gaze_origin_in_cpf` | |
  | `combined_gaze_valid` | |
  | `spatial_gaze_point_in_cpf` | |
  | `spatial_gaze_point_valid` | |
  | `vergence` | `EyeGazeVergence`, below |

- `vergence` (`EyeGazeVergence`):

  | Field(s) | Note |
  |---|---|
  | `left_yaw`, `right_yaw` | |
  | `left_pitch`, `right_pitch` | |
  | `left/right_yaw_low/high` | |
  | `tx/ty/tz_left_eye`, `tx/ty/tz_right_eye` | Per-eye gaze origin, CPF |
  | `left_blink`, `right_blink` | |
  | `left_gaze_valid`, `right_gaze_valid` | |
  | `left_blink_valid`, `right_blink_valid` | |

- **Pupil diameter and entrance-pupil position are NOT readable from Python.** Tutorial 8: "those members are **not currently bound into the Python `EyeGazeVergence`**." Package check: `hasattr(vergence, "left_pupil_diameter_meter") == False`.
- The raw VRS layout also holds `convergence_distance_meter`, `interocular_distance_meter`, foveated gaze and `tracker_timestamp_ns`. None of these are exposed in Python (`G/core/data_provider/data_layout/EyeGazeMetadata.h`).
- Reading them would need raw VRS access, for example `pyvrs`, which is not installed. [NOT FOUND — UNVERIFIED]

**4.4 Confidence and validity on Gen 2 on-device ET.** [VERIFIED IN PACKAGE + SOURCE CODE (2.3.0)]
- The only per-sample quality signals are the boolean flags `combined_gaze_valid`, `spatial_gaze_point_valid`, `left/right_gaze_valid` and `left/right_blink_valid`.
- **The `*_low` / `*_high` confidence bounds are not populated (0.0)** on on-device Gen 2 data, and `session_uid` is empty.
- On one test recording, 108 of 115 samples had valid combined gaze.
- Source bug in `G/core/data_provider/players/EyeGazePlayer.cpp`: when the left entrance-pupil position is invalid, the code sets the *right* validity flag to `true`. Not user-visible, because the field is not bound in Python.
- Recording-level calibration information: `EyeGazeConfiguration.user_calibrated` and `user_calibration_error` ("Lower is better").

**4.5 How on-device ET values are derived.** [SOURCE CODE (2.3.0)]
- `yaw = atan2(x, z)` and `pitch = atan2(y, z)` of the combined direction, transformed into CPF.
- `depth = |spatial_gaze_point − combined_origin|`.
- The timestamp is `system_timestamp_ns`.
- CPF transform: `T_Cpf_Device = getT_Device_Cpf(Default).inverse()`. Default is the SVD-based CPF on Gen 2 since 2.3.0.

**4.6 Rates.** [DOCS ONLY + VERIFIED IN PACKAGE]
- On-device ET runs at the profile's `et.rate_hz`: 30 Hz in profile8. The `profile4` test recording has a nominal 90 Hz.
- **MPS gaze runs at the ET-camera rate.** Tutorial 8: "MPS emits one gaze sample per ET camera frame, so the output rate is the ET camera rate, not the 30 Hz of the on-device `eyegaze` stream. ET cameras default to 5 Hz."
- **With our profile: on-device gaze is 30 Hz and MPS gaze is 5 Hz.**

**4.7 Published accuracy figures.** [NOT FOUND — UNVERIFIED] No official angular-accuracy figure for Gen 2 ET exists in the docs. The only related numbers are:
- On-device vs MPS agreement: 44.05 → 8.74 mrad (changelog 2.3.0).
- Tutorial 8, sample recording: general vs personalized gaze land "about 200 px apart on a 2560 px wide frame, nearly all of it in pitch". Personalization matters.

**4.8 Calibration procedure.** [DOCS ONLY] Source: `D/ark/companion-app/start` (#eye-tracking-calibration)
- What it is: Companion App → glasses details → **Eye Tracking Calibration**. The wearer fixes on a number, points their nose along an arrow, and freezes on a blinking dot, with the phone held "at arm's length" like a selfie.
- Requirements:
  - A phone with face tracking: a TrueDepth camera, or Android with ARCore Depth.
  - "Even, moderate lighting."
  - "Calibration is per wearer, per pair of glasses."
- The app asks the wearer to recalibrate "at most once a week".
- The calibration is written as a VRS recording. Passed to MPS as `--calib`, it produces `personalized_eye_gaze.csv`.

**4.9 CPF definition.** [DOCS ONLY + VERIFIED IN PACKAGE]
- `D/technical-specs/coordinate/cpf-coor`: "the middle-point interpolation of the left and right nominal pupil coordinate frame … **Using CPF-based poses is generally not recommended**."
- `D/technical-specs/coordinate/3d-coor`: "X-axis points left, Y-axis points up, and the Z-axis points forward".
- An SVD-based CPF was added in 2.1.2 and is the Gen 2 default since 2.3.0 (fact 0.2).
- Package check on a test recording, `T_device_cpf` translation:
  - CadBased: [0.0630, 0.0195, −0.0295]
  - SvdBased: [0.0625, 0.0195, −0.0302]
  - Default equals SvdBased.

**4.10 Official way to project gaze into the RGB image.** [DOCS ONLY + VERIFIED IN PACKAGE]
- Tutorial 8: "projecting a gaze point into a camera image is a two-step transform, `CPF -> Device -> Camera`, followed by `camera_calib.project(...)`", using `device_calibration.get_transform_device_cpf()`.
- Helper: `mps.utils.get_gaze_vector_reprojection(eye_gaze, stream_id_label, device_calibration, camera_calibration, depth_m=1.0, make_upright=False)`. It projects `spatial_gaze_point_in_cpf` when valid. Otherwise it uses yaw/pitch at `depth_m`.
- For Gen 2, use `mps.get_gaze_vergence_point(l_origin, l_yaw, l_pitch, r_origin, r_yaw, r_pitch) -> (point, is_real)`. The other helpers "hardcode a 63 mm inter-pupillary distance and assume both eyes share one pitch".
- When `is_real` is False the point is "a **synthetic fallback placed 10 m straight ahead**". This happens when vergence is <0.75°, the rays diverge, closest approach exceeds 3 cm, or convergence is beyond about 6 m.

---

## 5. On-device hand tracking (HT)

**5.1 Documented outputs.** [DOCS ONLY] From `D/ark/device/on_device_mp`: "outputs at 30Hz for each hand (left and right): 3-DOF position of the wrist; 3-DOF rotation of the wrist; 3-DOF positions of the 21 finger joint landmarks … in the device frame of reference."

**5.2 Stream, rate and API.** [VERIFIED IN PACKAGE]
- Label `handtracking` (371-1 when present).
- Profile key `ht.rate_hz`. Our 10 Hz equals the documented custom template.
- Getters: `get_hand_pose_data_by_index` / `_by_time_ns` → `mps::HandTrackingResult`. `get_interpolated_hand_pose_data(stream_id, timestamp_ns, time_domain=DEVICE_TIME)`.
- `get_hand_pose_configuration` → `nominal_rate_hz`, `is_wrist_palm_only`, `user_profile`.
- Test recordings: nominal 30 Hz. Both hands present in 9 of 9 samples. Confidence about 0.9999.

**5.3 Data structure.** [VERIFIED IN PACKAGE]
- `HandTrackingResult`:
  - `tracking_timestamp`: timedelta, device time.
  - `left_hand`, `right_hand`: "None if no valid pose was found". This is the per-hand validity signal.
- Each `OneSide` (one hand):

  | Field / method | Note |
  |---|---|
  | `confidence` | "Tracking confidence score for this hand" |
  | `landmark_positions_device` | 21 × 3D points, metres, device frame |
  | `transform_device_wrist` | SE3 |
  | `wrist_and_palm_normal_device` | `.palm_normal_device`, `.wrist_normal_device` |
  | `get_wrist_position_device()`, `get_palm_position_device()` | Helpers |

- `HandLandmark` indices: `THUMB_FINGERTIP 0, INDEX_FINGERTIP 1, MIDDLE_FINGERTIP 2, RING_FINGERTIP 3, PINKY_FINGERTIP 4, WRIST 5, THUMB_INTERMEDIATE 6, THUMB_DISTAL 7, INDEX_PROXIMAL 8 … PINKY_DISTAL 19, PALM_CENTER 20`.
- [SOURCE CODE (2.3.0)] `G/core/data_provider/players/HandPosePlayer.cpp`:
  - A hand is `None` when the raw `hand_valid` flag is false.
  - **Normals are derived, not measured.** The wrist normal is "−Y of T_Device_Wrist". The palm normal is estimated from landmarks.
  - The VRS layout also holds 22 joint angles and 5 per-finger confidences. **Neither is exposed in Python.**

**5.4 Frame and time base.** [DOCS ONLY + VERIFIED IN PACKAGE]
- "All Handtracking results in Aria are stored in the `Device` coordinate frame" (Tutorial 7). That is `slam-front-left`, in metres.
- "the on-device hand-tracking data are calculated from the SLAM cameras, not RGB cameras" (Tutorial 7).
- Test recording: HT timestamps lie within 0.001 ms of `slam-front-left` frames.
- To align with RGB, use `get_interpolated_hand_pose_data`. Its rules:
  - Returns None if the bracketing samples are more than 100 ms apart.
  - Interpolates each hand only when both bracketing samples contain that hand.
  - Landmarks are interpolated linearly and the wrist with SE3 interpolation.
  - Confidence is the min of the two samples.

**5.5 SLAM cameras are required.**
- On-device HT uses the SLAM cameras (5.4).
- MPS HT: "available for all recordings made with CV cameras (>=10fps) and IMU enabled" (`D/technical-specs/mps/data_formats/hand_tracking/hand_tracking_outputs`). [DOCS ONLY]
- Whether on-device HT still runs if `slam_cameras` are not *recorded* is **NOT FOUND — UNVERIFIED**. Our plan records them and drops them only from the released dataset, so this does not arise.

**5.6 Accuracy and limitations.** [DOCS ONLY] Source: `D/technical-specs/mps/benchmarks/performance`
- HOI dataset (30 fps, all 4 CV cameras, 7 participants, with "frequent hand occlusions" and "out-of-field-of-view segments"):
  - **On-device HT: mean keypoint error 45.0 mm, lose-track ratio 12.7%.**
  - MPS HT 3.2.0: 19.7 mm, 9.3%, precision 0.969, recall 0.915.
- Bystander-hand rejection is reported for MPS only. For bystanders closer than 50 cm, precision is 0.93 and recall 0.72.
- **The docs do not cover:** gloves, lighting, hand-to-camera distance limits, or performance at 10 Hz. [NOT FOUND — UNVERIFIED]

**5.7 MPS hand-tracking CSV.** [DOCS ONLY]
- Columns:
  - `tracking_timestamp_us`: SLAM-frame time.
  - `left/right_tracking_confidence`: "-1.0 indicates that the … hand data is missing".
  - `t{x,y,z}_{left,right}_landmark_{0..20}_device`.
  - `t{x,y,z}_*_device_wrist`, `q{x,y,z,w}_*_device_wrist`.
  - `n{x,y,z}_*_palm_device`, `n{x,y,z}_*_wrist_device`.
- `summary.json` contains `mean_confidence`, `total_frames`, `valid_frame_fraction`.
- Tutorial 7: on the sample recording, MPS HT "already lands exactly on RGB frame times, at 30 Hz".

---

## 6. MPS (Machine Perception Services) for Gen 2

**6.1 Services offered.** [DOCS ONLY] Source: `D/ark/mps`
- **SLAM:**
  - Open-loop and closed-loop 6-DoF trajectories. Closed loop is "created via batch optimization, using multi-sensors' input (SLAM, IMU, barometer, Wi-Fi and GPS)".
  - Semi-dense point cloud and observations.
  - Online calibration.
  - Multi-Sequence Trajectory ("Multi-SLAM").
- **Eye Gaze.**
- **Hand Tracking.**
- MPS CLI changelog (`D/ark/mps/changelog`): 1.1.0 "Support Hand Tracking for Aria Gen 2"; 1.2.0 "Multi-SLAM … Gen 2"; **1.4.0 "Add Eye Gaze processing for Aria Gen 2 recordings"** plus optional `--calib`.

**6.2 Recording requirements.** [DOCS ONLY]
- SLAM: "the recording profile must have CV cameras + IMU enabled".
- HT: CV cameras ≥10 fps plus IMU.
- Eye Gaze: "The recording must include the eye tracking camera stream". Error 122: "An Aria Gen 2 recording requested for Eye Gaze has no eye tracking camera stream" (`D/ark/support/mps`).
- Our profile meets all three: SLAM 10 Hz, IMU 800 Hz, ET cameras 5 Hz.
- Closed loop *uses* Wi-Fi and GPS when present. Whether dropping Wi-Fi degrades it is **NOT FOUND — UNVERIFIED**.

**6.3 Output files.** [DOCS ONLY]
- `eye_gaze/{general_eye_gaze.csv, personalized_eye_gaze.csv, calibration_params.json, summary.json}`
- `hand_tracking/{hand_tracking_results.csv, summary.json}`
- `slam/{closed_loop_trajectory.csv, open_loop_trajectory.csv, online_calibration.jsonl, semidense_points.csv.gz, semidense_observations.csv.gz, summary.json}`
- `vrs_health_check.json`
- Gen 2 eye-gaze CSV (`D/technical-specs/mps/data_formats/eye_gaze/eye_gaze_outputs`):
  - Columns: `tracking_timestamp_us, yaw_rads_cpf, pitch_rads_cpf, left/right_yaw_rads_cpf, left/right_pitch_rads_cpf, t{x,y,z}_{left,right}_eye_cpf`.
  - "The Gen2 CSV does not store a depth or 3D gaze point". The reader back-fills these from the vergence of the two eye rays. "Check `spatial_gaze_point_valid`".
  - There are no confidence columns in Gen 2.
- Online calibration (`…/slam/mps_calibration`): SLAM cameras and IMUs are optimized per session. RGB is "Copied from factory calibration". "use online calibration by default" for geometry.
- Closed-loop gravity is "fixed value `[0, 0, -9.81]`". Frames sharing a `graph_uid` share the same world frame.

**6.4 How to request MPS.** [DOCS ONLY]
- Install with `pip install projectaria-mps`.
- Single recordings: `aria_mps single -i <vrs or dir> [--features EYE_GAZE SLAM HAND_TRACKING] [--calib calibration.vrs] [--force]`. All three features are requested by default.
- Multi-SLAM: `aria_mps multi -i <dir> -o <out>`.
- Aria Studio has an "MPS Requests" page (`D/ark/aria_studio/mps`).
- Local stages: hashing, health check, then "**the recording is encrypted on your machine**", then upload (resumable within 24 h), processing and download (`D/technical-specs/mps/mps_cli_guide`).
- Supported platforms: Linux x64 and macOS ARM. Linux ARM64 is not supported (`D/ark/mps/start`).

**6.5 Data lifecycle and privacy.** [DOCS ONLY] Source: `D/ark/mps/mps_data_lifecycle`
- "The data is only uploaded to Meta servers to serve MPS requests and is deleted after 30 days."
- "Raw partner data (VRS files) is stored for no more than 30 days."
- "Partner data is only used to serve MPS requests. Partner data is not available to Meta researchers or Meta's affiliates."
- "only engineers in the core MPS team can access the pipeline under explicit permission from the customer."
- MPS outputs "continue to be stored in secure cloud storage, for up to 30 days".
- "The MPS pipeline generates statistics … These aggregated statistics are used by the Project Aria MPS team to help improve our offerings."
- ⚠ Uploading means the full raw VRS leaves our premises, including RGB video of bystanders. This must be covered by the ethics and DPIA documents.

---

## 7. VRS APIs in projectaria-tools 2.3.0

All facts in this section are [VERIFIED IN PACKAGE].

**7.1 Opening a file and listing streams.**
- `data_provider.create_vrs_data_provider(path)`.
- `get_all_streams()`, `get_label_from_stream_id()`, `get_stream_id_from_label()` (see the caveat in 2.8).
- `get_sensor_data_type()` returns a `SensorDataType` with values `IMAGE, IMU, GPS, WPS, AUDIO, BAROMETER, BLUETOOTH, MAGNETOMETER, PPG, ALS, VIO=13, VIO_HIGH_FREQ=14, EYE_GAZE=15, HAND_POSE=16, NEURAL_BAND_BATCH=17`.
- Counts and rates: `get_num_data()`, `get_nominal_rate_hz()`, `get_timestamps_ns(sid, TimeDomain)`.

**7.2 Per-stream getters.** Each stream has `get_*_data_by_index(sid, i)` and `get_*_data_by_time_ns(sid, t, time_domain, TimeQueryOptions)`. Configuration comes from `get_*_configuration(sid)`.

| Stream | Getter name | Returns |
|---|---|---|
| VIO | `get_vio_data_*` | `FrontendOutput` |
| HF VIO | `get_vio_high_freq_data_*` | `OpenLoopTrajectoryPose` |
| HT | `get_hand_pose_data_*` (+ `get_interpolated_hand_pose_data`) | `HandTrackingResult` |
| ET | `get_eye_gaze_data_*` | `EyeGaze` |
| GPS | `get_gps_data_*` | `GpsData` |
| PPG | `get_ppg_data_*` | `PpgData` |
| Barometer | `get_barometer_data_*` | `BarometerData` |
| Magnetometer | `get_magnetometer_data_*` | `MotionData` |
| IMU | `get_imu_data_*` | `MotionData` |
| ALS | `get_als_data_*` | `AlsData` |
| Temperature | `get_temperature_data_*` | `TemperatureData` |
| Images | `get_image_data_*` | `(ImageData, ImageDataRecord)` |
| Audio | `get_audio_data_*` | |
| Wi-Fi / BT | `get_wps_*`, `get_bluetooth_*` | |

**7.3 Time domains.**
- `TimeDomain {RECORD_TIME:0, DEVICE_TIME:1, HOST_TIME:2, TIME_CODE:3, TIC_SYNC:4, SUBGHZ:5, UTC:6}`.
- Docstrings:
  - DEVICE_TIME: "We **strongly recommend** to always work with the device timestamp when dealing with single-device Aria data."
  - UTC: "captured at 1 sample per minute".
- Tutorial 4: UTC has "only seconds-level accuracy". Gen 2 HOST_TIME is "Timestamps when sensor data is saved to the device (not when captured)".
- `TimeQueryOptions {BEFORE, AFTER, CLOSEST}`.
- `supports_time_domain` docstring: "Audio, Barometer, GPS and Ppg data does not have host timestamps."
- Conversions: `convert_from_device_time_to_synctime_ns(t, TimeSyncMode{TIME_CODE, TIC_SYNC, SUBGHZ, UTC})` and its inverse. `get_time_sync_mode()` returns `MetadataTimeSyncMode {NotEnabled, Timecode, Ntp, TicSyncClient, TicSyncServer, SubGhz, Utc}`.
- Note: PR #390 ("Restore Gen2 time sync", merged 2026-08-12, before the 2.3.0 release) fixed Gen 2 UTC/SubGHz conversion failures. On a 0-second test excerpt, UTC conversion returned −1, which is inconclusive. **Validate UTC mapping on our own data**, or use GPS `utc_time_ms` as the external time reference.

**7.4 Sequential access.**
- `deliver_queued_sensor_data([options])`: "Orders data by device timestamp".
- `get_default_deliver_queued_options()` provides `activate_stream`, `deactivate_stream_all`, `set_subsample_rate(sid, n)`, `set_truncate_first_device_time_ns` and `set_truncate_last_device_time_ns`.
- `SensorData` provides `.vio_data()`, `.vio_high_freq_data()`, `.eye_gaze_data()`, `.hand_pose_data()`, `.gps_data()`, `.ppg_data()`, … and `.get_time_ns(TimeDomain)`.

**7.5 Metadata.**
- `get_metadata()` returns `VrsMetadata` with `device_id, device_serial, duration_sec, start_time_epoch_sec, end_time_epoch_sec, filename, recording_profile, shared_session_id, time_sync_mode`.
- `get_file_tags()` returns these keys: `calib_json, capture_time_epoch, device_serial, device_type ("Oatmeal"), device_version, metadata (JSON), monotonic_clock_sample_ns, os_fingerprint, processing_clock_sample_ns, realtime_clock_sample_ns, session_id`.
- For the profile JSON and the privacy-relevant identifiers inside these tags, see 2.9.

**7.6 Exporting on-device MP to CSV.** [DOCS ONLY] `gen2_mp_csv_exporter --vrs-path … --output-folder … --vio-high-freq-subsample-rate N` writes MPS-format files: `slam/open_loop_trajectory.csv` (from `vio_high_frequency`), `slam/online_calibration.jsonl` (from `vio`), `eye_gaze/generalized_eye_gaze.csv` and `hand_tracking/hand_tracking_results.csv` (`D/research-tools/projectariatools/tools/exportcsv`).

---

## 8. Camera calibration

**8.1 Camera models.** [DOCS ONLY + VERIFIED IN PACKAGE]
- `D/technical-specs/device/calibration`: "FisheyeRadTanThinPrism: Used for RGB and SLAM cameras"; "KannalaBrandtK3: Used for eye tracking cameras".
- `D/technical-specs/device/calibration_insights/camera_intrinsics_models`: Fisheye624 = 6 radial (k0–k5) + 2 tangential (p0, p1) + **4** thin-prism parameters (s0–s3). ⚠ The calibration page says "s0-s2".
- `CameraModelType {LINEAR:0, SPHERICAL:1, KANNALA_BRANDT_K3:2, FISHEYE624:3, FISHEYE62:4}`.
- Test recordings: `camera-rgb` and `slam-*` use FISHEYE624; `camera-et-*` use KANNALA_BRANDT_K3.

**8.2 Projection API.** [VERIFIED IN PACKAGE]
- `CameraCalibration.project(point_in_camera) -> pixel | None`: "with a number of validity checks to ensure the point is visible".
- `unproject(pixel) -> ray | None`.
- Also `project_no_checks`, `is_visible`, `get_valid_radius`, `get_transform_device_camera`, `get_focal_lengths`, `get_principal_point`, `get_image_size`.
- Recommendation in `D/technical-specs/coordinate/cpf-coor`: "We recommend using relative poses between physical sensors" (`T_sensor1_sensor2 = T_Device_sensor1.inverse() * T_Device_sensor2`).

**8.3 Rectification (official procedure, Tutorial 2).** [VERIFIED IN PACKAGE]
1. `calibration.get_linear_camera_calibration(image_width, image_height, focal_length, label='', T_Device_Camera=SE3(), time_offset_sec_device_camera=0.0)`.
2. `calibration.distort_by_calibration(arraySrc, dstCalib, srcCalib, method=InterpolationMethod.BILINEAR)`.

Also available: `get_spherical_camera_calibration` and `rotate_camera_calib_cw90deg`.

**8.4 Rolling-shutter readout time.**
- The hardware page says only that the RGB sensor is "rolling shutter". [DOCS ONLY]
- `CameraCalibration.get_readout_time_sec()` exists but returned **None for every camera** in all three test recordings.
- In VIO online calibration, the SLAM-camera `readout_time_sec` is 0.0 (global shutter).
- **The Gen 2 RGB readout time is NOT FOUND — UNVERIFIED** (not in the docs or the factory calibration).

**8.5 Calibration when the resolution differs.** [VERIFIED IN PACKAGE + SOURCE CODE (2.3.0)]
- `VrsDataProviderFactory` compares each camera's calibration size with the recorded image size and calls `tryCropAndScaleCameraCalibration`. This works only for supported mappings (listed in 2.4; ET 400→200 uses scale 0.5). Any other resolution throws `"Unsupported camera rescale input"`.
- Test recording at 2016×1512: the returned RGB calibration is already 2016×1512, f ≈ 875.4.
- Manual alternatives: `calibration.rescale_camera_calibration(calib, new_resolution, device_version, canonical_camera_label=None)` or `CameraCalibration.rescale(new_resolution, scale, origin_offset)`.

---

## 9. GPS / GNSS on Gen 2

**9.1 `GpsData` fields.** [VERIFIED IN PACKAGE + SOURCE CODE (2.3.0)] Units come from `G/core/data_provider/data_layout/GpsMetadata.h`.

| Field | Meaning / unit |
|---|---|
| `capture_timestamp_ns` | Device time |
| `utc_time_ms` | UTC, milliseconds |
| `provider` | Typically `"gps"` |
| `latitude`, `longitude` | Degrees |
| `altitude` | Metres |
| `accuracy` | "Horizontal accuracy in meters" |
| `verticalAccuracy` | "Vertical accuracy in meters" (camelCase in Python) |
| `speed` | "Speed over ground [m/s]" |
| `raw_measurements` | Gen 2 only: "Raw satellite measurements (such as pseudo-range)" |
| `navigation_messages` | Gen 2 only: ephemeris |
| `constellations_enabled` | Gen 2 only, e.g. `GPS_L5`, `GALILEO_E5` |
| `raw_data` | Deprecated on Gen 2 |

- Class docstring: "GPS sensor data are already rectified".
- ⚠ In the VRS layout, latitude and longitude are **float32**. At 44.5°N the representable step is about 0.42 m in latitude (about 0.08 m in longitude). This is small next to GNSS error, but do not over-interpret sub-metre differences.
- Raw GNSS measurements are available, so post-processed positioning is possible in principle. The docs give no guidance. [NOT FOUND]

**9.2 What is missing from the GPS data.** [NOT FOUND — UNVERIFIED]
- There is no fix-validity flag, satellite count, DOP or heading/course field.
- VRS Health Check notes that "Records with no fix at all, which are normal indoors, stay healthy" and counts `no_fix_samples` (`D/ark/vrs_health_check/changelog`). How "no fix" is encoded in `GpsData` is not documented. Infer it from `accuracy`, `utc_time_ms` and zero coordinates on our own data.

**9.3 Streams.** [DOCS ONLY + VERIFIED IN PACKAGE]
- `gps` (281-2) is the device GNSS receiver. `gps-app` (281-1) is location "from Companion App", i.e. the phone. **Privacy:** check whether `gps-app` is populated.
- GPS has no host time domain.
- None of the test recordings contained GPS samples, so these values are unverified on real data.

**9.4 Risks.** [DOCS ONLY]
- The custom-profile GPS retrieval issue (quoted in 2.2).
- Health Check (`AriaGen2_Default`) GPS drop ratio thresholds: fail 2% / warn 1% for recordings over 60 s.
- "bad" records include a negative capture timestamp and a UTC time before 2020.

---

## 10. PPG, ALS, barometer, magnetometer, temperature

**10.1 PPG.** [VERIFIED IN PACKAGE + DOCS ONLY]
- `PpgData`:
  - `capture_timestamp_ns`.
  - `value`: int32, "Raw sensor light exposure measurement, there is no unit".
  - `led_current_ma`.
  - `integration_time_us`.
- `PpgConfiguration`: `sensor_model` (MAX86177), `nominal_rate_hz`, `device_id`, `description`.
- Hardware rate: typically 128 Hz, maximum 512 Hz. **Our 256 Hz is within hardware limits but is not used by any predefined profile.**
- **The docs say nothing on PPG signal quality, motion artefacts, wavelength/channel or heart-rate extraction.** [NOT FOUND — UNVERIFIED]
- Test data: `led_current_ma` was 10.0 and 25.1 mA in different files, so the LED current is adaptive and must be modelled.

**10.2 ALS.** [DOCS ONLY + VERIFIED IN PACKAGE] Source: `D/technical-specs/device/als`
- `AlsData` fields: `red/green/blue/uv/ir/clear_channel_normalized`, `uv/ir/clear_flux_watt_per_square_meter`, `gain_*`, `exposure_time_us`, `cct`, `lux`. The `visible_*` fields are "always 0" on Gen 2.
- Lux and CCT are computed on-device using factory calibration.
- On-device auto-exposure (AEC): "`exposureTimeUs` **varies per frame** in the range 1600 µs – 92800 µs"; gains are constant.
- Saturation: "The device does **not** record an explicit saturation flag per sample". A recipe is given using 145.636 ADC counts/µs with an 80% margin.
- Nominal rate: "nominally **10 Hz** (configurable)".
- What the profile's `exposure_time_us: 3200` means when AEC is active is **NOT FOUND — UNVERIFIED**. It is presumably the initial value. Test samples showed 3200 and 92800 µs.

**10.3 Barometer.** [VERIFIED IN PACKAGE + SOURCE CODE]
- `BarometerData`: `capture_timestamp_ns`, `pressure` (Pa), `temperature` (°C).
- ⚠ `temperature` was 0.0 in 2 of the 3 test recordings, so it is not reliably populated.
- Calibration is "Offset + Slope".

**10.4 Magnetometer.** [VERIFIED IN PACKAGE] `MotionData.mag_tesla` (in tesla) and `mag_valid`. Label `mag0`. Calibration "Bias + Rectification".

**10.5 IMU.** [VERIFIED IN PACKAGE] `MotionData`: `accel_msec2`, `gyro_radsec`, `accel_valid`, `gyro_valid`, `temperature`, `capture_timestamp_ns`, `arrival_timestamp_ns`.

**10.6 Temperature.** [VERIFIED IN PACKAGE] `TemperatureData`: `sensor_name`, `temperature_celsius`. The test recording had 0 samples.

---

## 11. Official statements on data quality

**11.1 Custom-profile risks.** [DOCS ONLY] Quoted in 2.2. Also: "Synchronization issues between sensors; Missing data streams … **These issues may not be immediately apparent**."

**11.2 VIO validity rules.** [DOCS ONLY] Check `status == VALID` and `pose_quality == GOOD` (3.3). Resets are signalled by `frontend_session_uid` (3.6). High-frequency VIO has only `quality_score` (3.7).

**11.3 VRS Health Check.** [DOCS ONLY] Source: `D/ark/vrs_health_check/configuration_and_thresholds`
- It runs automatically inside the MPS CLI and writes `vrs_health_check.json`.
- Configurations: `AriaGen2_Default`, `AriaGen2_Location`, `AriaGen2_Handtracking`, `AriaGen2_CI`.
- Key thresholds from the changelog:
  - Periodic-stream drop ratio: fail 0.02 (short clips) / 0.01 (long).
  - SLAM camera drop ratio: fail 0.005 / 0.001.
  - GPS drop ratio: fail 0.02 / 0.01.
  - HT drop ratio: fail 5% / warn 2%.
  - Not applied to VIO or HF VIO: `longest_consecutive_drop`.
  - Added for VIO: `reset_frequency_per_min`.

**11.4 On-device health statistics inside the VRS.** [VERIFIED IN PACKAGE; NOT documented]
- `metadata.recording.sensor_health_stats` holds, for each sensor (e.g. `VIO_RESULT`, `VIO_HIGH_FREQUENCY_POSE`, `ET_RESULT`, `HT_RESULT`, `GNSS`, `PPG`, `IMU_1`, `IMU_2`):
  - `expected_frame_count`, `actual_frame_count`, `dropped_frame_count`
  - `early_time_error_count`, `late_time_error_count`
  - `sequential_drops`
  - `score`
- These are useful as a per-recording quality-control log.

**11.5 Intentional RGB frame skips.** PR #398 is open (fact 0.5).

**11.6 Fields that are uninitialized in 2.3.0.** [VERIFIED IN PACKAGE] VIO `unix_timestamp_ns`, HF VIO `utc_timestamp`, and the on-device ET `*_low/*_high` bounds and `session_uid`.

**11.7 Timestamp caveat for WebRTC streaming only.** [DOCS ONLY] For WebRTC streaming, image `capture_timestamp_ns` "is the **host receive time**". This does not apply to VRS recorded on the glasses: "use the VRS written to the glasses, which carries true device capture timestamps" (`D/ark/companion-app/recording`).

**11.8 What the docs do not cover.** [NOT FOUND — UNVERIFIED]
- On-device VIO drift magnitude and accuracy.
- How to handle high-frequency VIO dropouts or resets beyond `session_uid`.
- ET angular accuracy.
- PPG quality.
- Behaviour when required streams (audio, BLE, Wi-Fi) are omitted from a profile.

---

## 12. Our custom profile vs. the docs

| Our setting | Documented reference | Verdict |
|---|---|---|
| Key names `slamCameras / etCameras / rgbCamera / deviceInfo` | Template and embedded profiles use `slam_cameras / et_cameras / rgb_camera / device_info` | ⚠ **Rename to snake_case**; camelCase acceptance is unverified |
| imus 800 Hz | All profiles 800 | ✅ |
| magnetometer 100 Hz | profile8 100 | ✅ |
| barometer 50 Hz | profile8 50 | ✅ |
| gps 1 Hz | profile8 1 | ✅ but note the custom-profile GPS warning → test-record and verify `gps` samples |
| slam_cameras 10 Hz, H265 qp30 | Template 10 Hz; mp_streaming_demo QP30 | ✅. HT and MPS HT need ≥10 fps, so this is the minimum; MPS benchmarks are at 30 fps |
| et_cameras 5 Hz, R_200x200, ir_led "TRUE" | profile8 identical | ✅. Capped at 5 Hz anyway while on-device ET runs. MPS gaze will be 5 Hz |
| rgb_camera 15 Hz, R_4032x3024 + 2016×1512, qp28 | profile10: 2016×1512 @ 30 Hz; template uses R_4032x3024 + width/height | ✅ plausible. Binning vs downscaling is undocumented; calibration rescale is supported (scale 0.5, full FOV). Compare with `profile pull profile10` |
| et 30 Hz | profile8 30 | ✅. **Algorithm unspecified**: add `et.type` (`ET_GEOMETRICAL` seen) or base the profile on `profile8_ml_et`. ML ET is better but has no pupil or blink output |
| ht 10 Hz | Template 10 | ✅ |
| vio 10 Hz | All 10 | ✅ |
| vio_high_frequency(_pose) ~800 Hz | Template key `vio_high_frequency_pose: {rate_hz: 800}`; stream label `vio_high_frequency` | ✅. Add the key explicitly. Expect ~797 Hz effective. It is IMU pre-integration on 10 Hz VIO |
| device_info 30000 ms | profile8 30000 | ✅ |
| ppg 256 Hz | Predefined 128; HW typical 128, max 512 | ⚠ Within HW range but untested by Meta; consider 128 |
| temperature 1 Hz | 1 | ✅ |
| als 9.434 Hz, 3200 µs | profile8 identical | ✅. AEC overrides exposure; saturation risk outdoors above ~20 klx |
| type RECORDING | Present in embedded profile8_copy | ✅ |
| Omitted: audio, ble, wifi, tags | All predefined profiles include audio; profiles 8 and 10 include BLE and Wi-Fi | ⚠ Effect undocumented (privacy-positive). Verify by test recording. MPS closed loop may use Wi-Fi |

---

## Appendix: excerpts of package introspection (projectaria-tools 2.3.0)

```
VioStatus {'VALID': 0, 'FILTER_NOT_INITIALIZED': 1, 'INVALID': 2}
TrackingQuality {'UNKNOWN': 0, 'GOOD': 1, 'BAD': 2, 'UNRECOVERABLE': 3}
VisualTrackingQuality {'UNKNOWN': 0, 'BAD': 1, 'GOOD': 2}
TimeDomain {'RECORD_TIME': 0, 'DEVICE_TIME': 1, 'HOST_TIME': 2, 'TIME_CODE': 3, 'TIC_SYNC': 4, 'SUBGHZ': 5, 'UTC': 6}
CpfType {'CadBased': 0, 'SvdBased': 1, 'Default': 2}
FieldProvenance {'SUPPORTED': 0, 'CALCULATED': 1, 'HARDCODED': 2, 'NOT_PRODUCED': 3}
SingleFieldId {'GAZE_ORIGIN','GAZE_DIRECTION','ENTRANCE_PUPIL_POSITION','PUPIL_DIAMETER','BLINK'}
CombinedFieldId {'GAZE_ORIGIN_COMBINED','GAZE_DIRECTION_COMBINED','CONVERGENCE_DISTANCE','INTEROCULAR_DISTANCE','FOVEATED_GAZE','SPATIAL_GAZE_POINT'}
get_vio_high_freq_data_by_index(...) -> projectaria::tools::mps::OpenLoopTrajectoryPose
get_eye_gaze_data_by_index(...)      -> projectaria::tools::mps::EyeGaze
get_hand_pose_data_by_index(...)     -> projectaria::tools::mps::HandTrackingResult
FrontendOutput: angular_velocity_in_bodyimu, camera_serials, capture_timestamp_ns, frame_id, frontend_session_uid,
  gravity_in_odometry, linear_velocity_in_odometry, online_calib, pose_quality, status, transform_bodyimu_device,
  transform_odometry_bodyimu, unix_timestamp_ns, visual_tracking_quality
OpenLoopTrajectoryPose: angular_velocity_device, device_linear_velocity_odometry, gravity_odometry, quality_score,
  session_uid, tracking_timestamp, transform_odometry_device, utc_timestamp
HandTrackingResult.OneSide: confidence, get_palm_position_device, get_wrist_position_device, landmark_positions_device,
  transform_device_wrist, wrist_and_palm_normal_device(.palm_normal_device, .wrist_normal_device)
GpsData: accuracy, altitude, capture_timestamp_ns, constellations_enabled, latitude, longitude, navigation_messages,
  provider, raw_data, raw_measurements, speed, utc_time_ms, verticalAccuracy
PpgData: capture_timestamp_ns, integration_time_us, led_current_ma, value
VrsMetadata: device_id, device_serial, duration_sec, end_time_epoch_sec, filename, recording_profile, shared_session_id,
  start_time_epoch_sec, time_sync_mode

Test VRS (profile8_copy; ~3.9 s excerpt of a 29 s recording): vio n=39 @10.00 Hz all VALID/GOOD, 1 session uid; vio_high_frequency n=3075,
  nominal 800, effective 796.9 Hz, dt median 1.255 ms; eyegaze 30 Hz (115 samples, 108 combined-valid);
  handtracking 30 Hz; camera-rgb 2560x1920 @10 Hz; ET cams 5 Hz; ppg 128.4 Hz; als 10 Hz.
```

Scripts used are in `<scratchpad>/introspect/` (`intro1.py`, `intro2.py`, `intro3.py`, `vrs_probe.py`, `hf_offset.py`, `tags*.py`) with their outputs.
