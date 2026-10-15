# Privacy pipeline

Video recorded in public space captures **participants and bystanders** (faces, licence plates,
bodies, voices if audio were recorded) and **precise locations**. This document describes the
technical and organisational measures planned for the bicycle vs e-scooter study. Legal
assessments (legal basis, DPIA, retention) are decisions of the data controller with the DPO:
they are marked **TBD** and must be settled before any acquisition. Nothing here is legal advice.
Verified technical facts and sources: [privacy/egoblur_and_vrs_privacy.md](privacy/egoblur_and_vrs_privacy.md)
and [aria/aria_gen2_technical_notes.md](aria/aria_gen2_technical_notes.md).

## 1. Principles

1. **Privacy by design and by default** (GDPR art. 25): collect only what the research
   questions need; process locally; pseudonymise early; anonymise faces and plates before any
   viewing; aggregate before publication.
2. **Separation of identities and research data**: the pseudonymisation key and consent forms
   never enter this repository or the data folders.
3. **Originals are never modified or deleted automatically**: every step writes new files.
   Deletion follows the retention policy (**TBD**) and deletion requests, by authorised staff.
4. **Raw identifiable data stay in a restricted tier**; only derived, reviewed data may leave it.
5. **No upload** of VRS files, videos or frames to MPS, other cloud services or third-party APIs
   without explicit authorisation (ethics committee, DPO, data processing agreement).
6. **"Anonymised" video is not declared free of personal data**: blurring covers faces and
   plates only, misses some, and leaves bodies, clothing, house numbers, places and times.

## 2. From raw VRS to research data

```
Raw VRS (on the glasses)            -> USB copy to encrypted restricted storage (data/raw, never versioned)
  |  1. stream inventory + integrity (vrs check / checksum; extract-aria inventory)
  v
Raw VRS (restricted, kept as original; retention TBD; no automatic deletion)
  |  2. face / licence-plate anonymisation of the image streams (EgoBlur Gen 2, local GPU)
  |  3. stream filtering of the copy: drop ET cameras, microphones (if any), Wi-Fi/BT scans (if any),
  |     SLAM cameras after hand-tracking extraction; overwrite identifying file/stream tags
  v
Privacy-reviewed VRS (restricted)   -> manual QA sample of blurred frames (logged)
  |  4. extract-aria (local): canonical streams, quality reports (no images written)
  v
Derived research data (pseudonymised; data/interim, data/processed)
  |  5. analysis, aggregation, GPS protection, release review
  v
Shareable outputs (aggregated results; reviewed derived data only after approval)
```

Step 4 can also read the raw VRS inside the restricted environment (the extractor writes no
images); any **viewing** of video for annotation uses the privacy-reviewed copy.

## 3. Data tiers

| Tier | Folder | Content | Access |
|---|---|---|---|
| Raw identifiable | `data/raw/` | original VRS (RGB, CV and eye-tracking cameras, IMU, GNSS, on-device gaze/VIO/hand tracking, PPG), manifests | designated staff only, encrypted storage (**TBD**: institutional system) |
| Privacy-reviewed | restricted storage next to raw | anonymised and filtered VRS copies, QA logs | authorised annotators |
| Pseudonymised research | `data/interim/`, `data/processed/` | canonical streams, annotations, label maps, metrics, quality reports; pseudonymous ids; may contain precise GNSS | study team |
| Anonymised / shareable | `data/public/` (staging) | aggregated metrics, generalised or relative trajectories, reviewed media | per release decision (**TBD**) |
| Synthetic | `data/synthetic/` | artificial test data | public (versioned) |

`raw`, `interim`, `processed`, `public` are excluded from git, as are VRS, video, audio and
model files anywhere, and the local `paper/` folder (copyrighted PDFs).

## 4. Participants: pseudonymisation

- Pseudonyms `P001`.. (`new-session --next`; numbers never reused). The key (pseudonym <->
  identity, consent forms, contacts) is kept by the PI or a designated person in a separate,
  access-controlled, encrypted location (**TBD**). File names matching `*participant_key*` /
  `*pseudonym_key*` are ignored by git as a safety net.
- Manifests contain pseudonyms, coarse conditions and internal device/vehicle codes only (no
  serial numbers, plates or e-scooter "contrassegno" codes). `validate` rejects forbidden keys
  and values that look like e-mails, phone numbers or Italian fiscal codes.
- Participant covariates are coarse categories (age band, riding frequency per vehicle, vision
  correction); final list **TBD** with the ethics committee.
- **VRS metadata contain identifiers** (verified on official Gen 2 recordings): device and
  nose-pad serials, device UUID, session ids, client name/notes, calibration JSON with serials,
  capture time. They stay in the raw tier; copies leaving it must have them overwritten
  (`vrs copy --file-tag/--stream-tag`; every stream carries `device_serial` and `session_id`
  tags) or must not be VRS at all (canonical CSV streams). The extractor reports which
  identifying tags exist without copying their values.
- **Eye-tracking camera images** show the participant's periocular region in infrared (possibly
  biometric). They are not needed (gaze is computed on the device), not blurred by EgoBlur,
  never viewed except for authorised technical checks, never shared, and dropped from every
  copy (`vrs copy ... - 211`). No official Meta guidance on these images was found.
- **PPG** (nose-pad) is a physiological signal of the participant: used at most as an
  exploratory covariate, never shared at individual level.

## 5. Bystanders (people incidentally recorded)

During acquisition (aligned with the Project Aria Research Community Guidelines, which make the
research institution the controller):

- the Aria **recording LED** stays visible; recording is stopped on request; contact details
  are given on request;
- a **first-layer notice** worn by the participant and the following researcher (short text,
  study contact, QR code to the full notice); for body-worn cameras the CJEU (C-422/24, 18 Dec
  2025) considered art. 13 GDPR applicable with a layered approach; exact form **TBD** with the DPO;
- the route avoids sensitive places (health facilities, places of worship, schools at entry
  times, private premises); recording is not started in private venues;
- bystanders are never identified or re-identified; deletion requests are honoured without
  undue delay.

Our recording profile has **no audio, no Wi-Fi and no Bluetooth scans** (to be confirmed on a
test recording: the effect of omitting them is undocumented). Wi-Fi/BT scans, if present,
contain identifiers of nearby devices (SSID, MAC addresses) and must be dropped.

## 6. Face and licence-plate anonymisation (EgoBlur Gen 2)

Verified facts (October 2026; details and sources in the fact sheet):

- `egoblur` 2.0.1 (PyPI, Apache-2.0 code and Gen 2 weights) provides `egoblur-vrs-blur`
  (Aria **Gen 2** VRS in -> VRS out) and `egoblur-gen2` (images/videos). Gen 2 models
  `ego_blur_face_gen2` and `ego_blur_lp_gen2` are downloaded after accepting the licence (not
  distributed with this repository).
- **What it processes**: RGB (214-1) and CV/SLAM cameras (1201-1..4): detection, blurring and
  **re-encoding to H.265** (same resolution; re-encoded even where nothing is detected).
- **What it copies unchanged** (verified by running the tool on an official Gen 2 sample and
  comparing streams): eye-tracking cameras, audio, GNSS, Wi-Fi/BT, PPG, eye gaze, hand tracking,
  VIO, IMU, barometer, magnetometer, all file and stream tags. **Timestamps and record order are
  preserved.**
- Frames it cannot decode are written back **unblurred without an error**: compare the frame
  count logged per stream with the record count.
- One threshold pair applies to all processed streams in a run; camera-specific thresholds need
  one run per camera. No accuracy figures are published for Gen 2 models (Gen 1 paper: Aria RGB
  faces AP 0.895 / AR 0.938; recall on truncated faces about 0.43-0.50).
- `egoblur` pins `moviepy<2`, projectaria-tools >= 2.1.2 needs `moviepy>=2`: separate
  environment (`./setup_linux.sh --egoblur` -> `.venv-egoblur`).

Planned procedure (Linux, local GPU; **not yet run on study data**):

```
.venv-egoblur/bin/egoblur-vrs-blur --input_vrs_path <raw>/recording.vrs \
    --output_vrs_path <restricted>/anonymised/<recording>.vrs \
    --face_model_path <models>/ego_blur_face_gen2.jit --lp_model_path <models>/ego_blur_lp_gen2.jit
vrs copy <restricted>/anonymised/<recording>.vrs --to <restricted>/reviewed/<recording>.vrs - 211 - 231 - 282 - 283
# after hand-tracking extraction and QA, a release copy may also drop the CV cameras: - 1201
```

Quality assurance (minimum; **TBD** with the PI): manual review of >= 200 randomly sampled
anonymised frames per session plus all frames used in figures or shared material, by authorised
staff; log of reviewed frames, misses and corrections; lower thresholds or manual masking if
misses are found. Residual identifiable content (bodies, clothing, tattoos, house numbers,
screens, vehicle markings, the place itself) remains: the reviewed video is still personal data.

## 7. Location data

Implemented and tested functions (`ariagen_escooter.privacy`):

| Function | Effect |
|---|---|
| `trim_endpoints(gps, radius_m)` | removes fixes within `privacy.gps.endpoint_radius_m` (200 m) of start and end |
| `remove_privacy_zones(gps, zones)` | removes fixes inside declared zones (non-versioned local file) |
| `to_relative_coordinates(gps)` | metres from the first fix, rotated to the first direction of travel |
| `generalize_coordinates(gps, grid_m)` | snaps fixes to a `privacy.gps.generalization_grid_m` (50 m) grid |

The study route is a fixed public loop starting at the campus, which limits the sensitivity of
the traces (no home/work locations of participants by design). Analyses use route-referenced
segments; shared data would contain at most the route-referenced segment ids or generalised
geometry (**TBD**).

## 8. Where processing happens: on-device, local, cloud

| Option | What it is | Data transferred | Advantages | Implications for ethics / DPO |
|---|---|---|---|---|
| **On-device** (Aria Gen 2 machine perception) | eye gaze (30 Hz), VIO (10 Hz + ~800 Hz high-frequency), hand tracking (10 Hz) computed on the glasses and stored in the VRS | none beyond the institution | no upload; available immediately; our main pipeline relies on it | describe in the information sheet which signals the device computes |
| **Local** (institution computers) | extraction (`projectaria-tools`), EgoBlur, segmentation/detection, analysis | none (encrypted storage, restricted access) | full control; reproducible versions | institutional security measures, access logs, encryption |
| **Cloud MPS** (Meta Machine Perception Services) | closed-loop SLAM trajectories and semi-dense points, MPS eye gaze, MPS hand tracking (more accurate than on-device in Meta's benchmark: 19.7 vs 45.0 mm) | **the raw VRS is uploaded** (encrypted) to Meta cloud storage; raw data and outputs kept up to 30 days; processing region not stated; MPS eye gaze needs the ET camera stream, hand tracking the CV cameras | closed-loop trajectories (batch optimisation; may fuse GNSS and Wi-Fi when present), semi-dense points, online calibration, more accurate hand tracking; MPS gaze runs at the ET-camera rate (5 Hz with our profile, vs 30 Hz on device) and the Gen 2 CSV has no confidence columns | **not used by default**; requires ethics approval, DPO assessment (processor agreement, transfer, retention), explicit participant information/consent, possibly anonymised and filtered uploads (RGB/audio can be dropped for SLAM per the Gen 1 docs; not verified for Gen 2) |

The main pipeline works without MPS (`aria.pose_source: vio`). MPS readers exist in the code
for the case it is authorised later (`mps_closed_loop`, MPS eye gaze).

## 9. Sharing and publication

Allowed by default: aggregated results (no cell with fewer than 3 participants, cf. the Garante
rules for research), synthetic data, code. Anything else (derived per-segment metrics,
generalised trajectories, reviewed media) requires: identifier scan, GPS processing, manual
review, a release note listing what was removed, and approval (**TBD**: ethics committee, DPO,
data management plan, repository and licence).

## 10. Legal and ethical framework (to be confirmed by the DPO)

- GDPR (Reg. (EU) 2016/679): art. 5, 6 (legal basis **TBD**), 9 (eye-region images and PPG
  may raise special-category questions: **TBD** with the DPO), 13 (information to bystanders,
  layered approach), 25, 35 (a DPIA is very likely required: wearable device, systematic
  recording of public spaces, location data), 89 (research safeguards).
- Italian Codice privacy (d.lgs. 196/2003 as amended) and the Garante's *Regole deontologiche
  per trattamenti a fini statistici o di ricerca scientifica* (provv. n. 515 of 19 Dec 2018).
- EDPB Guidelines 3/2019 on video devices.
- Project Aria Research Community Guidelines (LED visible, notice, stop on request, no sensitive
  places, de-identification, no re-identification, retention and deletion protocols, device
  reset between wearers).
- Ethics references: Kelly et al. (2013), Am J Prev Med 44(3):314-319,
  doi:10.1016/j.amepre.2012.11.006; Mok, Cornish & Tarr (2015), Integr Psychol Behav Sci
  49(2):309-322, doi:10.1007/s12124-014-9289-8; Raina et al. (2023), EgoBlur, arXiv:2308.13093.

## 11. Per-session checklist

Before: approvals in place; consent signed and stored with the key (not in the repo);
pseudonym allocated; device reset between wearers; recording profile checked (no audio/Wi-Fi/BT);
LED visible, notice worn; route free of sensitive places; helmet and road-rules briefing;
vehicles compliant (e-scooter contrassegno, insurance, indicators; bicycle lights).
After: VRS copied over USB to encrypted storage; copy verified (`vrs check`, checksum); manifest
completed without identifiers; `validate` passes; anonymised + filtered copy produced before any
viewing; QA sample logged; technical issues and deletion requests recorded.

## 12. Status

| Item | Status |
|---|---|
| Tier folders, `.gitignore` rules, manifest identifier scanner | implemented, tested |
| GPS protection functions | implemented, tested |
| Region blurring utility, detector interface, anonymisation loop (frames outside VRS) | implemented, tested (fake detector) |
| Report of identifying VRS tags at extraction (names only) | implemented, smoke-tested on an official Gen 2 test recording |
| EgoBlur environment (`setup_linux.sh --egoblur`) | implemented; tool behaviour per stream verified on an official sample in debug-encoding mode; not run with model weights on study data |
| VRS stream filtering and tag overwriting procedure | documented (verified commands); not yet applied |
| Legal basis, DPIA, retention period, release policy, key custody, bystander notice | **TBD** (controller, DPO, ethics committee) |
