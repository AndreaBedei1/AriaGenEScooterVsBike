# Project Aria Gen 2 integration

Practical notes for using Aria Gen 2 in this study. The verified technical dossier (about 100
numbered facts with URLs, quotes and tags "verified in package" / "docs only" / "unverified") is
[aria/aria_gen2_technical_notes.md](aria/aria_gen2_technical_notes.md); the recording profile and
its open points are in `configs/recording_profiles/`. Re-check facts when upgrading
projectaria-tools.

## 1. Software

| Item | Fact (2026-10-15) | Consequence here |
|---|---|---|
| Package | `projectaria-tools` 2.3.0 latest on PyPI (2.3.1 GitHub only) | pinned `>=2.3.0,<2.4` in the `aria` extra; keep 2.3.x for the whole study |
| CPF | since 2.3.0 the Gen 2 default Central Pupil Frame is SVD-based | gaze angles/projections from other versions are not comparable |
| Platforms | wheels for Linux x86_64/aarch64 and macOS arm64, CPython 3.10-3.12; no Windows | VRS stages run on Linux |
| EgoBlur | `egoblur` 2.0.1 pins `moviepy<2` (conflict with projectaria-tools) | separate `.venv-egoblur` |
| Tested here | the extractor runs on the official Gen 2 unit-test recordings of projectaria_tools (`ARIAGEN_TEST_VRS=<file> pytest tests/test_aria.py`) | smoke test only; not a riding recording |

## 2. Streams used (Gen 2 labels; resolve by label and check `get_num_data > 0`)

| Label | Content | Our profile | Canonical file |
|---|---|---|---|
| `camera-rgb` (214-1) | RGB, rolling shutter, FISHEYE624 | 15 Hz, 2016x1512 (from R_4032x3024: calibration scaled 0.5, full FOV) | `frames.csv` (timestamps only) |
| `eyegaze` (373-1) | on-device gaze: yaw/pitch (CPF), per-eye validity, vergence depth, spatial point | 30 Hz | `gaze.csv` (+ projection into RGB) |
| `vio` (371-x) | on-device VIO (`FrontendOutput`): pose, velocities, gravity, `status`, `pose_quality`, `frontend_session_uid` | 10 Hz | `pose.csv` (all samples, `valid`, status columns, `tracking_session`) |
| `vio_high_frequency` (371-x) | **IMU pre-integration on top of the 10 Hz VIO** (official wording), `quality_score`, `session_uid`; no status flag | ~800 Hz (797 Hz effective on test data) | `pose_hf.csv` (nearest-sample resampling to 100 Hz, no interpolation) |
| `handtracking` (371-x) | per hand: valid pose or none, confidence, 21 landmarks, wrist pose (device frame) | 10 Hz | `hands.csv` (presence, confidence, wrist/palm in CPF) |
| `imu-left`/`imu-right` (1202-x) | accelerometer, gyroscope | 800 Hz | `imu.csv` (time-binned to 100 Hz; raw timing checked) |
| `gps` (281-2) | glasses GNSS | 1 Hz | `gps.csv` (records without fix kept as empty) |
| `ppg`, `baro0`, `mag0`, `als`, `temperature` | other sensors | 256/50/100/9.4/1 Hz | raw timing checked; not exported yet |
| `slam-*` (1201-x), `camera-et-*` (211-x) | CV and eye cameras | 10 Hz / 5 Hz | never exported; ET images dropped from working copies |

The VRS also embeds the **full recording profile** and **on-device sensor health statistics**
(expected/actual/dropped frame counts per sensor) in the `metadata` file tag; the extractor
saves them in `extraction.json` and computes raw-stream timing quality in
`extraction_quality.json`.

## 3. Time

All sensors of one device share `TimeDomain.DEVICE_TIME` (ns): used everywhere. VIO
`unix_timestamp_ns`, high-frequency VIO `utc_timestamp` and the ET confidence bounds are not
filled in 2.3.0 (garbage values): never used. High-frequency VIO timestamps do not coincide with
IMU sample times (sub-millisecond offsets).

## 4. Data quality rules implemented

- VIO sample valid = `status == VALID` and `pose_quality == GOOD` (official rule; in 2.3.0 the
  quality is only GOOD or BAD); resets = change of `frontend_session_uid`; no interpolation
  across resets; position/orientation jumps counted.
- High-frequency VIO: `quality_score` distribution; 0.5 threshold only as reported example.
- Gaze: validity flags only (no per-sample confidence on Gen 2 on-device gaze); blink flags not
  exported (semantics unverified on test data).
- All streams: effective vs nominal rate (from the profile), dropout fraction, gaps classified
  as short / medium / long, duplicated / out-of-order / invalid timestamps; intervals labelled
  observed / interpolable / degraded / unusable (`docs/data_schema.md`).
- Dropout rates of 3-15 % seen or expected for VIO elsewhere are **not** assumed: they are
  measured per recording.

## 5. On-device vs MPS (cloud)

| Capability | On-device (in the VRS) | MPS (requires uploading the raw VRS) |
|---|---|---|
| Head trajectory | VIO 10 Hz + high-frequency ~800 Hz, odometry frame per session, resets possible | open- and closed-loop trajectories (batch optimisation; closed loop may fuse GNSS, Wi-Fi, barometer), semi-dense point cloud, online calibration of CV cameras/IMUs |
| Eye gaze | 30 Hz in our profile; yaw/pitch, per-eye, vergence | at ET-camera rate (**5 Hz** with our profile); personalised calibration option; Gen 2 CSV without confidence columns |
| Hand tracking | 10 Hz; Meta benchmark 45.0 mm mean keypoint error, 12.7 % lose-track | MPS benchmark 19.7 mm, 9.3 % lose-track |
| Privacy | nothing leaves the institution | raw VRS (video included) on Meta servers up to 30 days; region not stated |
| Use in this study | **main pipeline** | not used by default; possible improvements (closed-loop trajectories for speed/heading validation, better hand tracking) only after ethics/DPO authorisation; code readers exist (`aria.pose_source: mps_closed_loop`) |

## 6. Extraction command

```
python -m ariagen_escooter extract-aria data/raw/P001_S01      # Linux, aria extra
```

Writes `data/interim/<session>/<recording>/streams/{frames,gaze,imu,pose,pose_hf,hands,gps}.csv`,
`inventory.csv`, `extraction.json` (metadata, embedded profile, sensor health, names of
identifying tags, extrinsics) and `extraction_quality.json`. Nothing is written to `data/raw`.

## 7. Before the first pilot recording

1. Load the profile on the device in the documented snake_case format (see
   `configs/recording_profiles/README.md`); make a 2-minute outdoor test recording.
2. Check the stream list (no audio/Wi-Fi/BT), the `gps` stream, `vio_high_frequency`,
   `handtracking`, the effective rates and the sensor health statistics.
3. Overlay projected gaze on RGB frames while looking at targets at known distances.
4. Check VIO validity and resets during a short ride on each vehicle.
5. Run `validate` and `run` on the test session; review `quality.json`.
