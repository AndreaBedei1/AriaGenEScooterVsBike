# Recording profiles

Profiles used (or proposed) for Aria Gen 2 acquisitions. The quality-control step reads the
nominal stream rates from the profile named in the session manifest
(`equipment.recording_profile: <name>` -> `<name>.json`).

| File | Status |
|---|---|
| `driver_dataset_v1_raw_for_ht.json` | Profile supplied by the project lead, kept **verbatim**. Not yet tested on the device. |

## Points to verify before the first recording

Checked against the official Gen 2 documentation and the profiles embedded in the official
Gen 2 test recordings (projectaria-tools 2.3.0; details and sources in
`docs/aria/aria_gen2_technical_notes.md`):

1. **Key naming.** Official profiles use snake_case keys (`slam_cameras`, `et_cameras`,
   `rgb_camera`, `device_info`, `rate_hz`, `video_config`, `ir_led`); acceptance of the camelCase
   keys above is not documented. Export a predefined profile from the device
   (`aria_gen2 device profile pull profile8`, Client SDK >= 2.5.0) and copy its encoding.
2. **High-frequency VIO.** The stream label is `vio_high_frequency`; the documented profile key is
   `vio_high_frequency_pose: {rate_hz: 800}`. Add it explicitly (older profiles without the key
   still produced the stream, but this is not guaranteed).
3. **Eye-tracking algorithm.** The profile does not set `et.type` (`ET_GEOMETRICAL` appears in the
   embedded profiles; the ML variant is selected by `profile8_ml_et`, whose exact key is not
   documented). Fix it explicitly so that all participants use the same algorithm.
4. **GPS with custom profiles.** The documentation warns that GPS data could not be retrieved
   in some custom-profile recordings: make a short outdoor test recording and check the `gps`
   stream before the pilot.
5. **PPG at 256 Hz** is within the hardware range but differs from all predefined profiles
   (128 Hz).
6. **RGB 2016x1512 from R_4032x3024**: the calibration is rescaled by 0.5 with full field of view;
   whether the sensor bins or the ISP downscales is not documented.
7. **Audio, Bluetooth and Wi-Fi** are absent from the profile (privacy-positive); the effect of
   omitting them is not documented: check the stream list of a test recording.
