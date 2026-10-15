# EgoBlur / VRS privacy pipeline — verified facts (AriaGenEScooterVsBike)

> Fact sheet compiled on 2026-10-15. EgoBlur was installed in an isolated environment outside the repository and run only in debug-encoding mode on an official Gen 2 test recording; no model weights were downloaded.


Compiled 2026-10-15. Scope: Raw Aria Gen 2 VRS → face/plate anonymisation → privacy-reviewed VRS → derived data.

**Tags**
- **VERIFIED (source)**: read in the upstream source code (git clone of `main`) and/or in the installed package.
- **VERIFIED (run)**: reproduced locally in an isolated environment.
- **DOCS ONLY**: stated in official documentation or web pages, not independently tested.
- **UNVERIFIED**: no official source found, or an inference or estimate.

**How this was checked**
- Isolated venv `<workdir>/venvs/egoblur`: Python 3.11.15 with `egoblur==2.0.1`, `torch 2.9.1+cu128`, `av 13.1.0`, `vrs (pyvrs) 1.2.2` and `moviepy 1.0.3`.
- Separate venv `<workdir>/venvs/pat` with `projectaria-tools==2.3.0` (pulls `moviepy 2.2.1`).
- conda env `<workdir>/venvs/vrscli` with the `vrs` CLI 1.4.0 from conda-forge.
- No model weights were downloaded. The project `.venv` was not touched.
- Test input: Meta's own Gen 2 sample `gen2/demo_assets/multi_stream.vrs` from the EgoBlur repo (25 streams, 641 records).
- Repo snapshots: EgoBlur `75144e1` (2026-05-05), vrs `83aef0e` (2026-10-15), pyvrs `aa0de93` (2026-10-14).
- `S=<workdir>`

---

## 1. Releases, versions and licence

**F1.1 — Latest release is v2.0.1. VERIFIED (source)**
- GitHub `facebookresearch/EgoBlur` has one release, **v2.0.1**, titled "v2.0.1 - Gen2 end-to-end VRS blur tool".
  - Published 2026-04-14T01:19:13Z; tag commit `e51ed60` is dated 2026-04-10.
  - URL: https://github.com/facebookresearch/EgoBlur/releases/tag/v2.0.1
- Release body (quote): "Starting with version 2.0.1, egoblur-vrs-blur can blur faces and license plates directly in Aria Gen2 VRS files without converting to MP4 first. It reads camera streams, runs detection, applies blur, and writes everything back into a single output VRS file. Non-camera streams (IMU, VIO, barometer, eye tracking, etc.) are copied verbatim."
- CHANGELOG.md: "## [2.0.1] - 2026-04-13 … Released VRS end-to-end blur tool using Gen 2 models" and "## [2.0.0] - 2025-12-11 … Gen 2 release (models, Python demo CLIs, etc.)".
- Last commit on `main`: 2026-05-06 ("Update README and CHANGELOG for v2.0.1 release").
- Open PR #31 proposes "Bump torch from 2.9.1 to 2.12.0"; it is not merged.

**F1.2 — PyPI `egoblur` latest is 2.0.1; nothing newer as of 2026-10-15. VERIFIED (source)**
- Source: https://pypi.org/pypi/egoblur/json
- Version history:
  - 2.0.0a1 (2025-11-17)
  - 2.0.0a2 (2025-11-18)
  - 2.0.0a3 (2025-12-05)
  - 2.0.0a4 (2025-12-08)
  - 2.0.0 (2025-12-10)
  - **2.0.1 (2026-04-15)**
- Metadata:
  - `License-Expression: Apache-2.0`
  - `Requires-Python <3.13,>=3.10`
  - Summary: "Demo utilities for running EgoBlur person and license plate blurring models."
- Console scripts declared in `pyproject.toml` and present in the venv: `egoblur-gen1`, `egoblur-gen2`, `egoblur-vrs-blur`.

**F1.3 — The code is Apache-2.0. VERIFIED (source)**
- The repo `LICENSE` is Apache License 2.0, and the GitHub API reports `apache-2.0`.
- README: "The model is licensed under the [Apache 2.0 license](LICENSE)."

**F1.4 — The model weights are Apache-2.0 (Gen 2 explicitly; Gen 1 via the shared model licence page and the Hugging Face card). DOCS ONLY**
- https://www.projectaria.com/tools/egoblur/ (FAQ): "Yes. Both the Gen 2 face and license plate models are licensed under Apache 2.0, meaning they are available for both research and commercial applications."
- https://www.projectaria.com/tools/egoblur/license/ is titled "EgoBlur Model License Agreement". Its body is the full Apache License 2.0 text and it does not distinguish Gen 1 from Gen 2.
- Hugging Face card https://huggingface.co/projectaria/EgoBlur (`license: apache-2.0`; Gen 1-era card): "now available under an open-source license (Apache 2.0) for both commercial and non-commercial use."
  - The HF repo contains only `README.md` and `.gitattributes`. There are **no weights** on HF.

**F1.5 — How the weights are obtained. DOCS ONLY (the download itself was not exercised)**
- Weights come from the email-gated form at https://www.projectaria.com/tools/egoblur/#download.
- Page text: "By submitting your email and accessing the EgoBlur model, you agree to abide by the model license agreement and to receive emails in relation to the model. Download EgoBlur Gen 1 and Gen 2. If you are a researcher in AI or ML research, access the EgoBlur models and accompanying tools here."
- README table: models `ego_blur_face_gen1`, `ego_blur_lp_gen1`, `ego_blur_face_gen2`, `ego_blur_lp_gen2`, each "zipped" and linked to the website. Files are TorchScript, e.g. `ego_blur_face_gen2.jit`.
- The Gen 1 C++ README fetches the zips with `wget -O face.zip "<downloadable_link_fetched_from_website>"`.
- Availability caveat — issue #32 (Jul–Aug 2026): the download buttons were broken for about a month. A Meta maintainer commented on 2026-08-06: "Our team has fixed the issue and I've verified the links are back."
  - Download links in CI also changed in March 2026 (PRs #24 and #25).
  - **Archive the zips and record their SHA-256 hashes.**

## 2. EgoBlur Gen 2 models

**F2.1 — Model names. VERIFIED (source)**
- `ego_blur_face_gen2` and `ego_blur_lp_gen2`, loaded as TorchScript.
- Detection classes: `ClassID.FACE = 0`, `ClassID.LICENSE_PLATE = 1` (`gen2/script/predictor.py`).

**F2.2 — Architecture and size. DOCS ONLY (structure partly VERIFIED (source))**
- FAQ: "EgoBlur Gen 2 is based on the Faster R-CNN model with a ResNeXt backbone."
- FAQ: "Both the Gen 2 face and license plate models are approximately 400 MB each and have ~104 million parameters."
- FAQ: "The Gen 2 face model is fine-tuned on the Gen 1 face model. The Gen 2 license plate model is trained from scratch. Both models are trained using Meta's publicly available Detectron2 and Detectron2go libraries."
- FAQ: "The Gen 2 models are trained on both egocentric Aria data and non-egocentric data. Although we have only quantitatively evaluated on Aria data…"
- FAQ: "The models output rectangular bounding boxes, not masks or labels."
- Source code consistent with this: the code patches Detectron2 `Instances` fields (`proposal_boxes`, `objectness_logits`, `pred_boxes`, …).
- Preprocessing: ResizeShortestEdge with `RESIZE_MIN_GEN2 = RESIZE_MAX_GEN2 = 1200` (`gen2/script/constants.py`).
  - RGB 2560×1920 is downscaled to about 1200×900.
  - SLAM 512×512 is **upscaled** to 1200×1200.

**F2.3 — Gen 1 paper numbers (arXiv:2308.13093v2, 6 Sep 2023). VERIFIED (source: PDF text)**
- Architecture: "ResNext-101-32x8 FPN-based FasterRCNN model using Detectron2". Training was weakly supervised with RetinaFace as teacher. Evaluation uses IoU 0.5 and COCO AP/AR.
- CCV2 faces (259,656 boxes):
  - EgoBlur AP 0.99, AR 0.998
  - RetinaFace 0.99 / 0.998
  - MediaPipe 0.979 / 0.99
  - AR stays between 0.992 and 1.0 across age, gender, Fitzpatrick, Monk and country buckets.
- Aria Pilot Dataset faces (18,508 frames, 23,242 boxes), EgoBlur:
  - Grayscale: AP 0.866, AR 0.899
  - RGB: AP 0.895, AR 0.938
  - RetinaFace for comparison: gray 0.806 / 0.825, RGB 0.877 / 0.905
- Hard cases, recall on RGB / grayscale:

  | Case | RGB recall | Grayscale recall |
  |---|---|---|
  | truncated | **0.430** | **0.502** |
  | lighting-too-dark | 0.854 | 0.758 |
  | occluded | 0.892 | 0.876 |
  | non-frontal | 0.928 | 0.880 |
  | wearing-glasses | 0.957 | 0.914 |

- Licence plates (Aria LP set, 56,561 frames): grayscale AP 0.963 / AR 0.982; RGB AP 0.929 / AR 0.992.
- The paper says regions are processed "with a Gaussian blur". The released Python code actually uses a box blur (see F3.9).

**F2.4 — There are no published Gen 2 accuracy numbers. DOCS ONLY / UNVERIFIED**
- The EgoBlur page gives speed figures only:
  - "Based on a 2MP RGB image, … approximately 21ms on a GPU and 1.5 seconds on a CPU."
  - "Based on a 0.3MP gray scale image, both models run in approximately 25ms on a GPU and 1.6 seconds on a CPU."
- The page contradicts itself on the benchmark:
  - Intro: "EgoBlur Gen 2 is benchmarked against the Aria Gen 2 Pilot Dataset and CCV2 Dataset."
  - FAQ: "The Gen 2 models are benchmarked against an internal Aria Gen 2 Evaluation Dataset."
- No AP or AR values are given anywhere. The README points to the Gen 1 paper: "See gen 1 paper for model details".
- **For an ethics or methods section, Gen 2 recall on our data has to be measured by us** (manual QA sample).

**F2.5 — Per-camera default score thresholds (`gen2/script/constants.py`). VERIFIED (source, identical in the installed package)**

| `--camera_name` | face | licence plate |
|---|---|---|
| camera-rgb | 0.67416 | 0.74475 |
| slam-front-left / slam-front-right | 0.69862 | 0.95245 |
| slam-side-left / slam-side-right | 0.68160 | 0.95242 |

- With no `--camera_name` and no explicit threshold, the **camera-rgb values are used** (`_get_threshold`).
- How the thresholds were derived is not documented (commit `51816aa`, "Set default parameter for SLAM and RGB", 2025-11-25).
- Other defaults in `egoblur-gen2` and `egoblur-vrs-blur`:
  - `--nms_iou_threshold` default is **0.5** in the code, but the README says 0.3.
  - `--scale_factor_detections` default is 1.0. The Gen 1 C++ tool defaulted to 1.15.

## 3. VRS support (`egoblur-vrs-blur`, file `gen2/script/vrs_blur_gen2.py`)

**F3.1 — Full CLI (from `--help` in the venv). VERIFIED (run)**
```
egoblur-vrs-blur --input_vrs_path IN --output_vrs_path OUT
  [--stream_ids ID [ID ...]]            # default: 214-1 1201-1 1201-2 1201-3 1201-4
  [--face_model_path P] [--lp_model_path P]   # at least one required (unless --debug_encoding_only)
  [--camera_name {slam-front-left,slam-front-right,slam-side-left,slam-side-right,camera-rgb}]
  [--face_model_score_threshold F] [--lp_model_score_threshold F]
  [--nms_iou_threshold F (0.5)] [--scale_factor_detections F (1.0)]
  [--encoding_quality INT (CRF, default 18)] [--encoding_preset STR (default ultrafast)]
  [--batch_size INT (1)] [--debug_encoding_only] [--aug_using_cpu]
```
- Other CLIs:
  - `egoblur-gen2`: PNG/JPEG/MP4 input; has `--camera_name`; preserves the input FPS.
  - `egoblur-gen1`: Gen 1 models; has `--output_video_fps`.
  - Gen 1 VRS is handled only by the separate C++ tool `ego_blur_vrs_mutation` (`gen1/tools`). It needs libtorch 2.1 and CUDA 12.1, and has known build and segfault issues (#12, #32).

**F3.2 — Streams processed by default: RGB `214-1` and SLAM/CV `1201-1..4` only. VERIFIED (source + run)**
- Eye-tracking cameras `211-1` and `211-2` are **not** processed by default.
- The pyvrs `AsyncImageFilter` yields every image stream ("By default, all image streams are filtered, while the others are copied as is." — pyvrs `csrc/filter/OssAsyncImageFilter.h`).
- EgoBlur then writes non-target image records back unchanged: `if stream_id not in target_sids: image_filter.write_processed_image(image_buffer)`.
- Meta's Gen 1 C++ mutator does the same deliberately (comment `// If not Eye Tracking image`; only `214` and `1201` are blurred).

**F3.3 — All other streams are copied verbatim, nothing is dropped, and timestamps and record order are preserved. VERIFIED (run)**
- Test: `egoblur-vrs-blur --debug_encoding_only` on `multi_stream.vrs`, then a comparison with the `vrs` CLI and pyvrs.
- Totals:
  - 641 → 641 records.
  - Same 25 stream IDs.
  - Identical sequence of (stream, record type, timestamp).
  - Identical file tags and identical stream tags for all 25 streams.
- Check 1: `vrs compare in.vrs out.vrs - 214 - 1201` returns "Files are equivalent". `vrs checksum` with the same filter gives `d85141f05348315e` for both files.
  - This covers ET cameras 211-1/2 (image bytes identical), audio 231-1 (Opus, 8 channels, 16 kHz), barometer 247, PPG 248, GPS 281-1/2, Wi-Fi 282-1, Bluetooth 283-1, temperature 246, battery 240, time-domain mapping 285, hand tracking 371-1, VIO 371-2/3, eye gaze 373-1, ALS 500-1, IMU 1202-1/2 and magnetometer 1203-1.
- Check 2: `vrs compare … + 214 + 1201` returns "Files differ" (payload sizes change).
- Mechanism (source): the C++ `Copier` copies non-image streams; `writer.addTags(filteredReader_.reader.getTags())` copies the file tags; image records are re-created with `record.timestamp`.

**F3.4 — Target camera frames are always decoded and re-encoded to H.265, at the original resolution. VERIFIED (source + run)**
- Encoder settings:
  - libx265 (CPU) with `crf=18`, `preset=ultrafast`, `gop_size=1` (all intra), `bframes=0`.
  - Pixel format `yuv420p` for RGB and `gray` for SLAM.
  - `hevc_nvenc` (`rc=constqp`, `qp=18`) is used for RGB only, and only if available. **The PyPI PyAV 13.1.0 wheel has no `hevc_nvenc`** (checked: `'hevc_nvenc' in av.codecs_available` is False), so everything is CPU-encoded unless you build your own FFmpeg/PyAV.
- The image spec is kept unchanged, e.g. `video/2560x1920/pixel=yuv_i420_split/codec=H.265` and `video/512x512/pixel=grey8/codec=H.265`.
- The source profile in the sample was H.265 at qp 22, all intra (`iframe_period 0`).
- Generation loss measured with no blur applied (debug mode):
  - RGB PSNR 42.8 / 39.3 dB.
  - SLAM PSNR about 38.1–48.0 dB.
  - No frame misalignment: out[i] versus in[i−1] is about 20–23 dB, so frames are not shifted.
- SLAM payloads shrink, e.g. 39,144 → 22,753 bytes. File 1,977,116 → 1,834,069 bytes.
- **Re-encoding happens even when there are zero detections.** It can slightly affect later SLAM/MPS processing on the blurred file (UNVERIFIED magnitude).

**F3.5 — Gen 2 only. Non-H.265 frames pass through UNBLURRED without raising an error. VERIFIED (source + run)**
- The code assumes H.265 for every target stream: `H265Decoder` → `av.CodecContext.create("hevc","r")`.
- If decoding returns None, the frame passes through: `# Can't decode — pass through original bytes.`
- Test: feeding JPEG bytes or raw grey8 bytes returns `None`, with only an FFmpeg log line ("No start code is found").
- So on **Gen 1 VRS** (JPEG RGB / raw SLAM), or on any corrupt packet, the output would contain **original unblurred frames** and the run would still look successful.
- **QA rule:** check that the logged "Stream X: N frames" equals the number of data records of each target stream.

**F3.6 — Per-camera thresholds are global per run. VERIFIED (source)**
- `--camera_name` is a single value applied to **all** `--stream_ids` in a run.
- Defaults are the camera-rgb thresholds. On SLAM streams this means a licence-plate threshold of 0.745 instead of the tuned 0.952, i.e. more aggressive.
- To get tuned thresholds, run the tool several times in a chain: `--stream_ids 214-1 --camera_name camera-rgb`, then `--stream_ids 1201-1 1201-2 --camera_name slam-front-left`, and so on.
- Non-target image streams are passed through byte-identical (F3.3), so chaining does not re-encode streams twice.

**F3.7 — Hardware. DOCS ONLY + VERIFIED (run, environment)**
- README: Python 3.10–3.12; "CUDA toolkit (optional): 12.8".
- README: "We do not recommend running this tool on macOS. The EgoBlur models run on CPU only on Mac… For best performance, use a Linux machine with a CUDA-capable GPU."
- The device is chosen as `cuda:<current>` if available, otherwise CPU.
- `torch 2.9.1+cu128` sees CUDA on this workstation: GPU0 RTX 6000 Ada, GPU1 GTX 1660 SUPER.
- No VRAM requirement is documented.
- Rough cost estimate (UNVERIFIED):
  - Profile 8 records RGB at 10 Hz plus 4 SLAM cameras at 30 Hz, i.e. about 130 frames per recorded second.
  - At about 21–25 ms per model per frame on GPU (FAQ), face + LP costs about 6 GPU-seconds per recorded second at batch 1, before CPU encoding.
  - On CPU, at about 1.5 s per model per frame, it is impractical.

**F3.8 — Operational details. VERIFIED (source/run)**
- The output is first written to `tempfile.mkstemp()` in `$TMPDIR` (default `/tmp`), then moved into place. Set `TMPDIR` to a disk with enough space.
- The output file mode is **0600**.
- The output carries **no provenance tag**: file and stream tags are identical to the raw file. You cannot tell a blurred VRS from a raw one by metadata. Add a tag yourself (F5.3).

**F3.9 — Blur method: box blur inside an ellipse. VERIFIED (source)**
- `visualize()` applies `cv2.blur` (box filter, kernel = image H/2 × W/2) inside each box.
- It then composites only an **ellipse inscribed in the box** (`cv2.ellipse`), so the box corners stay sharp.
- With the default `scale_factor_detections = 1.0`, the edges of the face (chin, hair, ears) can remain visible. Consider about 1.15, the Gen 1 C++ default.
- Known issues:
  - #18 (open): pets' faces are often blurred.
  - #14 (open): inference time increases with batch size.
  - #11 (open): TorchScript device-mismatch question; original weights and config are not shared.

## 4. Dependency conflict

**F4.1 — `egoblur 2.0.1` cannot share an environment with current projectaria-tools. VERIFIED (run + source)**
- `egoblur 2.0.1` requires `moviepy>=1.0.3,<2.0`, `torch==2.9.1`, `torchvision==0.24.1`, `av>=12,<14` and `vrs==1.2.2`.
- `projectaria-tools` 2.1.2, 2.1.3, 2.1.4, 2.2.0 and **2.3.0** (latest, 2026-08-25) all have the hard requirement `moviepy>=2.0`.
- Versions ≤2.1.1 only had `moviepy==1.0.3; extra == "all"`.
- `uv pip compile` result for `egoblur==2.0.1` + `projectaria-tools==2.3.0`: "egoblur==2.0.1 and projectaria-tools==2.3.0 are incompatible."
- Unpinned, the resolver downgrades to `projectaria-tools==2.1.1`.
- **Keep EgoBlur in its own venv.** Both venvs read each other's VRS output fine (F5.4).
- Not resolved upstream: there has been no egoblur release since 2026-04-15.

## 5. Dropping or filtering streams in a VRS

**F5.1 — `vrs` CLI (official). DOCS + VERIFIED (run, vrs 1.4.0 conda-forge)**
- Install, as in the Aria docs: `conda install vrs --channel=conda-forge` (or pixi).
  - Docs: https://facebookresearch.github.io/projectaria_tools/docs/data_formats/aria_vrs/aria_vrs_tools_installation
- Stream filter syntax: `+`/`-` followed by `<recordable_type_id>[-<instance_id>]`. The help text says: "Notice the space between the `+` or `-` sign, and the argument that follows!"
  - There is **no `--exclude` flag**.
  - Docs: https://facebookresearch.github.io/vrs/docs/VrsCliTool
- Commands:
  - Drop both ET cameras, all microphones, and Wi-Fi/BT scans:
    `vrs copy raw.vrs --to out.vrs - 211 - 231 - 282 - 283`
    (tested `- 211 - 231`: 22 streams kept, 211-1/2 and 231-1 gone).
  - Drop the SLAM cameras after hand-tracking or MPS extraction:
    `vrs copy in.vrs --to out.vrs - 1201`
  - Keep only selected streams:
    `vrs copy in.vrs --to out.vrs + 214-1 + 1202-1 + 373-1`
  - Trim by time: `--range +2 +12`, `--after +2`, `--before -1`.
  - Overwrite tags:
    `--file-tag <name> <value>` and `--stream-tag <stream-id> <name> <value>` (requires a full stream ID such as `1201-1`; `1201` alone is rejected).
  - Zero out all image and audio payloads: the help text gives `vrs copy --zero-vrs <file.vrs> --to <output.vrs>`. The docs page calls the option `--zero`; the shipped CLI uses `--zero-vrs`.
  - Integrity checks: `vrs check f.vrs`, `vrs checksum f.vrs [filters]`, `vrs compare a.vrs b.vrs [filters]`.
- Aria-specific doc quote: "As an example, we are here removing the EyeTracking stream (["211-1"]): `vrs copy original.vrs --to new.vrs - 211`" (https://facebookresearch.github.io/projectaria_tools/docs/data_formats/aria_vrs/aria_vrs_command_line).
- Caveat in the VRS docs: "Stream instance ID numbers might not be preserved in the output VRS file." In the test, 371-1/2/3 kept their IDs. Always look up the hand-tracking and VIO streams **by flavor** (`device/oatmeal/hand`, `…/vio`, `…/vio_high_frequency`), as the Aria stream-ID doc instructs.

**F5.2 — MPS-specific trimming. DOCS ONLY (Gen 1 page)**
- Source: https://facebookresearch.github.io/projectaria_tools/docs/ARK/troubleshooting/reduce_vrs_file_size
- "MPS does not need the following sensor streams…: RGB Sensor Streams (214-1) … Microphone Sensor Streams (231-1)"
- "`vrs copy <path/to/recording.vrs> --to <path/to/recording_norgb.vrs> - 214-1`"
- So you can upload a VRS without RGB and audio for MPS. This is not restated in the Gen 2 docs (UNVERIFIED for Gen 2).

**F5.3 — Residual identifiers sit in tags, and EgoBlur copies them. VERIFIED (run)**
- File tags in the Gen 2 sample:
  - `device_serial`
  - `session_id`
  - `capture_time_epoch`
  - `realtime_clock_sample_ns`
  - `calib_json` (contains a `Serial`)
  - `os_fingerprint`
  - `acro_info`
  - `metadata`, a JSON with:
    - `client.name`, `client.notes`, `campaign.c_project_name`/`c_task_name`, `cohort`, `hash_ca_id`, `session_uuid`
    - `device.serial`, `device.uuid`
    - `recording.device_system_utc_timestamp_ns`
    - the full recording `profile`
- **All 25 streams** also carry `device_serial` and `session_id` as stream tags.
- `--file-tag` alone does not clean these. `--stream-tag` must be applied per stream ID.
- A tested override of `device_serial` (file tag + 214-1 + 1201-1) still opens in projectaria-tools 2.3.0 with calibration. Overriding `calib_json` or `metadata` was not tested.

**F5.4 — projectaria-tools 2.3.0 reads the processed files. VERIFIED (run)**
- `create_vrs_data_provider` opens all of these with calibration, RGB frame 0, eye gaze (6) and hand tracking (6) intact:
  - the EgoBlur output,
  - the `vrs copy - 211 - 231` output,
  - the re-tagged copies.
- `gen2_mp_csv_exporter --vrs-path no_et_audio.vrs --output-folder …` exports `eye_gaze/generalized_eye_gaze.csv`, `hand_tracking/hand_tracking_results.csv`, `slam/open_loop_trajectory.csv` and `slam/online_calibration.jsonl` **without the ET images or audio**.
- Note: `open_loop_trajectory.csv` contains `utc_timestamp_ns` and `session_uid`.

**F5.5 — Other routes. VERIFIED (source)**
- pyvrs `FilteredFileReader` (Python binding) exposes only time filters (`after`, `before`, `range`).
- `AsyncImageFilter` has `discard_record(ImageBuffer)`, so a custom pyvrs script could drop image records.
- No projectaria-tools CLI for stream filtering was found. The installed CLIs are `vrs_to_mp4`, `gen2_mp_csv_exporter`, `viewer_mps`, `aria_rerun_viewer` and `aria_dataset_downloader`.

## 6. Project Aria Research Community Guidelines and MPS data lifecycle

**F6.1 — Research Community Guidelines (last updated September 7, 2023, so they predate Gen 2). DOCS ONLY**
- URL: https://www.projectaria.com/community-guidelines/
- Quotes:
  - "Ensuring that you provide appropriate notice to individuals whose data may be captured, and that you obtain consent of such individuals, in each case as may be required under applicable law"
  - "Ensuring that the external LED recording indicator is clearly visible"
  - "Complying with any regional requirements for additional bystander signaling … research partners are the controller when meeting GDPR or UK GDPR requirements, which includes the responsibility to ensure that it is clear to bystanders who you work for via your transparency/notice measures"
  - "Providing contact details to inquiring bystanders who want to receive more information about the research"
  - "Not using the device in any private venue or building without appropriate authorization"
  - "Not recording sensitive activities or in sensitive places, including restrooms, medical or health facilities, bedrooms or hotel rooms, religious facilities or prayer rooms, locker/changing rooms, private homes (without consent of all household members)"
  - "Creating and maintaining secure data management practices, such as deleting unnecessary or unused data, factory resetting devices between wearers…"
  - "Implementing applicable data privacy practices, such as setting retention periods, deletion and data access protocols, obfuscating or de-identifying personally identifiable information such as faces and license plates"
  - "Not attempting to identify any bystander whose image or personally identifiable information have been blurred or obfuscated…"
  - "Complying with reasonable deletion requests, when requested by a participant or a bystander, without undue delay"
  - "Violating the Project Aria Research Community Guidelines can result in, among other things, expulsion from the program and forfeiture of research devices."

**F6.2 — Gen 2 MPS Data Lifecycle. DOCS ONLY**
- URL: https://facebookresearch.github.io/projectaria_tools/gen2/ark/mps/mps_data_lifecycle
- Quotes:
  - "Raw Aria sequences (VRS files) are uploaded to secure cloud storage via MPS CLI."
  - "The data is only uploaded to Meta servers to serve MPS requests and is deleted after 30 days"
  - "Meta's data management processes mandate that this raw data cannot be stored for more than 30 days"
  - "Partner data is only used to serve MPS requests. Partner data is not available to Meta researchers or Meta's affiliates."
  - "The whole process is automated and only engineers in the core MPS team can access the pipeline under explicit permission from the customer."
  - "All MPS output (trajectories, semi-dense point clouds etc.) continue to be stored in secure cloud storage, for up to 30 days…"
  - "The MPS pipeline generates statistics about how the algorithms are performing as well as the console logs from processing. These aggregated statistics are used by the Project Aria MPS team to help improve our offerings."
- Aria Studio MPS page: "Uploading — VRS file is being encrypted and uploaded to the cloud."
- **The processing location or region and the legal transfer basis are not stated** on any MPS page checked (UNVERIFIED). The projectaria.com privacy-policy link redirects to the general Meta policy at facebook.com/privacy/policy.
- No mechanism for deletion on request before the 30 days is documented.

**F6.3 — What Gen 2 MPS needs. DOCS ONLY**
- Source: https://facebookresearch.github.io/projectaria_tools/gen2/ark/mps
- "Eye Gaze … The recording must include the eye tracking camera stream." So if you drop 211-x, MPS eye gaze is no longer possible.
- "Closed loop trajectory - created via batch optimization, using multi-sensors' input (SLAM, IMU, barometer, Wi-Fi and GPS)".
- "Cloud Hand Tracking processing is available for all recordings made with CV cameras (>=10fps) and IMU enabled."
- Implication: any MPS request means unblurred (or EgoBlur-processed) SLAM and ET imagery leaves the institution for up to 30 days.
- The Gen 2 on-device outputs (373-1 eye gaze, 371-x hand tracking and VIO) are already in the VRS and exportable locally (F5.4).

## 7. Eye-tracking camera images

**F7.1 — No official Meta guidance on ET-image privacy was found. UNVERIFIED (absence after searching projectaria.com, the Gen 1/Gen 2 docs, the EgoBlur repo/FAQ and the AEA paper)**
- What is verified:
  - Meta's tools intentionally leave ET images untouched: Gen 1 C++ comment `// If not Eye Tracking image`; Gen 2 FAQ: "eye tracking … copied verbatim".
  - Gen 2 ET cameras record 200×200 grey8 frames, H.265, IR LED on, 5 Hz in profile 8 (sample metadata; VERIFIED (run)).
  - The AEA dataset paper blurred "faces and licenses on all images in RGB and monochrome scene camera streams" only (arXiv:2402.13349).
- Our assessment (UNVERIFIED): IR periocular images may contain iris texture and other biometric-capable traits of the **participant**. EgoBlur provides no protection for them.
- Recording profiles can be customised ("copy and customize recording profiles", https://facebookresearch.github.io/projectaria_tools/gen2/ark/companion-app/recording-profiles). Whether ET cameras, microphones and Wi-Fi/BT can be disabled per profile was **not verified**. The sample metadata does show per-sensor profile blocks (`et_cameras`, `audio`, `gps`, `ble`, …).

## 8. Summary by stream (Gen 2 IDs from https://facebookresearch.github.io/projectaria_tools/gen2/technical-specs/vrs/streamid-label-mapper)

| Stream | What `egoblur-vrs-blur` (default) does | Residual privacy content |
|---|---|---|
| 214-1 RGB | face/LP blur, then H.265 re-encode at CRF 18 | missed faces (Gen 1 paper: truncated-face recall about 0.43–0.50), plus bodies, clothing, tattoos, house numbers, screens, documents, other vehicles' markings |
| 1201-1..4 SLAM | blur + re-encode, with RGB thresholds unless chained per camera | same as RGB, in grayscale |
| 211-1/2 ET cameras | **copied unchanged** | participant periocular IR images (possible biometric) |
| 231-1 microphones (8 ch, Opus 16 kHz) | **copied unchanged** | bystander speech and voices, conversation content |
| 281-1/2 GPS | **copied unchanged** | lat/lon/alt/speed/heading, UTC, raw NMEA, i.e. home and work locations |
| 282-1 Wi-Fi, 283-1 Bluetooth | **copied unchanged** | `ssid`, `bssid_mac`, `mac_address`, `unique_id` of nearby devices (bystander identifiers) |
| 248-1 PPG, 373-1 eye gaze, 371-x hand tracking/VIO, 1202/1203 IMU/mag, 247 baro, 246 temp, 500 ALS, 285, 240 | **copied unchanged** | participant health and behavioural signals; VIO and trajectory give location relative to start |
| File and stream tags | **copied unchanged** | device serial, session UUID, capture time, free-text recording name/notes, project and cohort names |

## 9. Reproduction (all paths under `<workdir>`)
- Upstream sources: `src/egoblur_repo`, `src/vrs_repo`, `src/pyvrs_repo`. Saved web pages: `web/*.txt`, `web/arxiv/egoblur.txt`, `web/arxiv/aea.txt`.
- Debug blur run:
  `TMPDIR=<workdir>/vrstest/tmp venvs/egoblur/bin/egoblur-vrs-blur --input_vrs_path vrstest/in.vrs --output_vrs_path vrstest/out_debug.vrs --debug_encoding_only`
- Stream comparison:
  - `venvs/vrscli/bin/vrs compare vrstest/in.vrs vrstest/out_debug.vrs - 214 - 1201`
  - `scripts/compare_vrs.py`, `scripts/psnr_vrs.py`, `scripts/shift_check.py`
- Stream drop: `venvs/vrscli/bin/vrs copy vrstest/in.vrs --to vrstest/no_et_audio.vrs - 211 - 231`
- Readability check: `scripts/pat_check.py` (projectaria-tools 2.3.0 venv)
- Dependency resolution: `resolve/req.in` with `uv pip compile`
