# Project Aria Gen 2 integration notes

Facts verified on official sources on 2026-10-06 (Gen 2 documentation at
facebookresearch.github.io/projectaria_tools/gen2, the projectaria_tools GitHub repository at tag
2.3.0, PyPI, projectaria.com). Re-check them when upgrading projectaria-tools.

## Software

| Item | Verified fact | Consequence here |
|---|---|---|
| Package | `projectaria-tools`, Gen 2 support since 2.0.0; latest 2.3.0 (Aug 2026) | pinned `>=2.3.0,<2.4` in the `aria` extra |
| Platforms | wheels only for Linux x86_64/aarch64 and macOS arm64, CPython 3.10-3.12; **no Windows** | VRS stages run on Linux; Windows skips the extra; `requires-python >=3.10,<3.13` |
| Extras | `[all]` is a no-op since 2.2.0 | plain `projectaria-tools` |
| CPF | since 2.3.0 the Gen 2 default CPF is SVD-based (better on-device vs MPS gaze agreement) | gaze projections from older versions are not comparable |
| EgoBlur | `egoblur` 2.0.1 supports Gen 2 (models + VRS tool) but pins `moviepy<2` | separate `.venv-egoblur` (`setup_linux.sh --egoblur`) |
| Tested here | in WSL Ubuntu 24.04, projectaria-tools 2.3.0 installs from `uv.lock`, and every API symbol used by `AriaGen2Extractor` exists (`tests/test_aria.py::test_projectaria_api_surface`) | the extractor itself still needs a real VRS |

## Streams (Gen 2 labels; always resolve by label)

| Label | Content | Notes |
|---|---|---|
| `camera-rgb` | RGB, rolling shutter, FISHEYE624 model | profile8 2560x1920 @ 10 Hz; profile10 2016x1512 @ 30 Hz |
| `eyegaze` | on-device eye gaze (`EyeGaze`) | 30 Hz in standard profiles; yaw/pitch in CPF, `depth` (0 = unavailable), `spatial_gaze_point_in_cpf` + validity |
| `imu-left`, `imu-right` | IMUs (`MotionData`) | 800 Hz; rectify with `raw_to_rectified_accel/gyro`; Gen 2 ids differ from Gen 1 |
| `vio` | on-device VIO (`FrontendOutput`) | 10 Hz; keep `VioStatus.VALID` and `TrackingQuality.GOOD`; pose = `transform_odometry_bodyimu @ transform_bodyimu_device` |
| `vio_high_frequency` | `OpenLoopTrajectoryPose` | ~800 Hz; `transform_odometry_device`, `quality_score`, `gravity_odometry` |
| `gps` / `gps-app` | GNSS on the glasses / from the companion app | 1 Hz in profile8/profile10; Gen 2 ids are swapped w.r.t. Gen 1 |
| `slam-*`, `camera-et-*` | CV and eye-tracking cameras | not used (ET images show the participant's eyes) |
| `mic` | all microphones incl. contact mic | not used; see audio note in `privacy_pipeline.md` |

On Gen 2, `get_stream_id_from_label()` answers from a static table even if a stream is absent: the
extractor also checks `get_num_data(stream_id) > 0`, as the official tutorial does.

## Time

- `TimeDomain.DEVICE_TIME` (ns) is shared by all sensors of one device: used everywhere.
- UTC information is coarse (time-sync stream about once per minute via the companion app,
  seconds-level accuracy); MPS `utc_timestamp_ns` is "rough". Not used for alignment.
- Multi-device alignment uses the SubGHz time-domain mapping (not needed for single-rider
  sessions).
- No official procedure exists for synchronising an external smartphone GPS logger: hence the
  speed cross-correlation check implemented in `synchronization.estimate_offset_xcorr`.

## Calibration and gaze projection

- `provider.get_device_calibration()`; `get_camera_calib("camera-rgb")`; `get_transform_device_cpf()`.
- Official projection (Gen 2 tutorial): `p_device = T_device_cpf @ spatial_gaze_point_in_cpf`;
  `p_camera = T_device_camera^-1 @ p_device`; `camera_calib.project(p_camera)` (None if not
  visible). When the 3-D point is not valid, the yaw/pitch ray at a fallback depth is used
  (`aria.gaze_fallback_depth_m`).
- CPF axes: x left, y up, z forward; direction `normalize(tan(yaw), tan(pitch), 1)`; +yaw left.
- Pixel convention: integers at pixel centres; in bounds if -0.5 <= u < W-0.5.
- Camera calibration is automatically cropped/scaled to the recorded resolution when a VRS is
  opened.

## MPS (optional, cloud)

SLAM (closed/open-loop trajectory, semi-dense points), eye gaze (only 5 Hz with standard
profiles: one sample per ET-camera frame) and hand tracking; requested with `aria_mps` or Aria
Studio; requires uploading the VRS (see `privacy_pipeline.md`). Closed-loop world frame is
gravity aligned with +z up. Readers for `closed_loop_trajectory.csv` and Gen 2 eye-gaze CSVs are
implemented with pandas and tested on fixtures following the documented columns.

## Extraction command

```
python -m ariagen_escooter extract-aria data/raw/P001_S01            # Linux, aria extra
```

Writes `data/interim/<session>/<recording>/streams/{frames,gaze,imu,pose,gps}.csv`,
`inventory.csv` (all streams, counts, rates) and `extraction.json` (metadata, labels used,
extrinsics). Nothing is written to `data/raw`.

## First-pilot verification checklist (extractor not yet run on real data)

1. `inventory.csv`: expected streams present, measured rates vs profile (RGB 10 Hz, gaze 30 Hz,
   IMU 800 Hz, VIO 10 Hz, GNSS 1 Hz).
2. `validate` on the session: timestamp gaps and duplicates.
3. Overlay the projected gaze (`u_px`, `v_px`) on a sample of RGB frames (official Rerun viewer
   or a quick plot) and check plausibility.
4. VIO: fraction of VALID/GOOD samples, trajectory shape vs the route, gravity alignment (z up).
5. GNSS: fix quality and which label was used (`gps` vs `gps-app`).
6. Compare automatic trimming with the manual notes of the session.

## Sources

- Gen 2 docs: installation, changelog, StreamId-label mapper, hardware and profiles,
  calibration, coordinate frames (3-D, CPF, 2-D), on-device machine perception, MPS data formats,
  MPS data lifecycle, companion app (time-domain mapping), EgoBlur.
- Gen 2 Python tutorials 1-8 (projectaria_tools `examples/Gen2/python_notebooks`, tag 2.3.0).
- PyPI: projectaria-tools 2.3.0 (wheel tags), egoblur 2.0.1.
- Project Aria Research Community Guidelines (projectaria.com/community-guidelines).
