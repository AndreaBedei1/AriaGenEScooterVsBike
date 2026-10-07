# Privacy pipeline

Video recorded in public space captures **participants and bystanders** (faces, licence plates,
voices) and **precise locations**. This document describes the technical and organisational
measures planned in the project. Legal assessments (legal basis, DPIA, retention) are decisions of
the data controller with the DPO: they are marked **TBD** and must be confirmed before the pilot.
Nothing here is legal advice.

## 1. Principles

1. **Privacy by design and by default** (GDPR art. 25): collect only what the research
   questions need; process locally; pseudonymise early; anonymise before any viewing or sharing
   of video; aggregate before publication.
2. **Separation of identities and research data**: the pseudonymisation key never enters this
   repository or the data folders.
3. **Originals are never modified or deleted automatically**: every processing step writes new
   files. Deletion follows the retention policy (**TBD**) and deletion requests.
4. **Raw identifiable data stay in a restricted tier**; only derived, reviewed data may leave it.

## 2. Data tiers

| Tier | Folder | Content | Access |
|---|---|---|---|
| Raw identifiable | `data/raw/` | VRS (video, audio, GNSS), MPS outputs, external GPS logs, manifests | designated staff only, encrypted storage (**TBD**: institutional system) |
| Pseudonymised research | `data/interim/`, `data/processed/` | canonical streams, annotations, label maps, metrics; pseudonymous ids; may contain precise GPS | study team |
| Anonymised / shareable | `data/public/` (staging) | aggregated metrics, generalised or relative trajectories, anonymised media - after review | per release decision (**TBD**) |
| Synthetic | `data/synthetic/` | artificial test data | public (versioned) |

Folders `raw`, `interim`, `processed` and `public` are excluded from git (`.gitignore`), as are
video, VRS, audio and model files anywhere in the repository.

## 3. Participants: pseudonymisation

- Each participant receives a pseudonym `P001`.. (`new-session --next`; numbers never reused).
- The **key** (pseudonym <-> identity, consent forms, contact details) is kept by the PI or a
  designated person in a separate, access-controlled, encrypted location (**TBD**: system and
  responsible person). File names matching `*participant_key*` / `*pseudonym_key*` are ignored
  by git as a safety net.
- Manifests contain only pseudonyms, coarse conditions and internal equipment codes.
  `validate` rejects forbidden keys (name, surname, e-mail, phone, address, birth date, fiscal
  code, ... - list in `configs/default.yaml`) and values that look like e-mail addresses, phone
  numbers or Italian fiscal codes (the report does not echo the value).
- Participant covariates for analysis are coarse categories only (e.g. age band); the final list
  is **TBD** with the ethics committee.
- Eye-tracking camera images show the participant's eyes: they are not needed by the analysis,
  are not anonymised by EgoBlur and must never be shared.

## 4. Bystanders (people incidentally recorded)

Measures during acquisition (aligned with the Project Aria Research Community Guidelines, which
make the research institution the data controller):

- the Aria **recording LED** must stay visible; the privacy switch disables recording;
- a **first-layer notice** for bystanders (e.g. a badge or sign with a short text, the study
  contact and a QR code to the full information notice). For body-worn cameras the CJEU
  (C-422/24, 18 Dec 2025) considered art. 13 GDPR applicable, with a layered approach accepted;
  the exact form for this study is **TBD** with the DPO;
- recording is stopped if a bystander asks; contact details are given on request;
- the route avoids sensitive places (restrooms, health facilities, places of worship, schools,
  private premises...) - **TBD** in the route definition;
- bystanders are never identified or re-identified; deletion requests are honoured.

Processing measures: faces and licence plates are anonymised before any viewing for annotation
and before any sharing (section 5); analyses use derived data (classes, metrics), not identities.

## 5. Video anonymisation (faces, licence plates)

**Tool: Meta EgoBlur** (verified Oct 2026; code and Gen 2 weights under Apache-2.0).

- `pip install egoblur` (2.0.1) provides `egoblur-gen2` (images/videos) and `egoblur-vrs-blur`
  (Aria **Gen 2** VRS in -> blurred VRS out; RGB stream 214-1 and SLAM streams 1201-1..4 by
  default; other streams copied unchanged; frames re-encoded in H.265; CUDA GPU recommended).
- Gen 2 models `ego_blur_face_gen2` and `ego_blur_lp_gen2` (TorchScript, ~400 MB each) are
  downloaded manually from the EgoBlur page after accepting the licence: they are not
  distributed with this repository.
- **Environment:** egoblur 2.0.1 pins `moviepy<2`, projectaria-tools 2.3.0 needs `moviepy>=2`:
  they cannot share an environment (verified with the resolver). `./setup_linux.sh --egoblur`
  creates a separate `.venv-egoblur`.
- Default score thresholds depend on the camera (`camera-rgb`: faces 0.67416, plates 0.74475);
  `egoblur-vrs-blur` applies one threshold pair to all processed streams, so run it per camera
  if camera-specific thresholds are wanted.

Planned procedure (Linux; **not yet run** - no real recording available):

```
.venv-egoblur/bin/egoblur-vrs-blur --input_vrs_path data/raw/<s>/<r>/recording.vrs \
    --output_vrs_path <restricted>/anonymised/<r>.vrs \
    --face_model_path <models>/ego_blur_face_gen2.jit --lp_model_path <models>/ego_blur_lp_gen2.jit \
    --camera_name camera-rgb
```

Quality assurance (**TBD** details): published accuracy refers to Gen 1 models (paper: Aria RGB
faces AP 0.895 / AR 0.938, plates AP 0.929 / AR 0.992; weaker on truncated faces); no figures
are published for Gen 2 models nor for Italian/EU plates. Therefore: manual review of a random
sample of anonymised frames per session (plus all frames used in figures or shared material),
lower thresholds if misses are found, and a log of reviewed frames and corrections.

The package also provides `privacy.blur_regions` (gaussian/pixelation of detection boxes),
`RegionDetector` (detector interface) and `anonymize_frames` (loop with log), tested with a fake
detector; an EgoBlur adapter for this interface is **planned** (only needed if frames are
processed outside VRS files).

## 6. Audio

Standard Gen 2 profiles record the microphones (voices of participants and bystanders). Audio is
not needed for the research questions: use a profile without audio if available, otherwise never
extract or share the `mic` stream and drop it from any anonymised copy (**TBD**: profile choice;
check that anonymised VRS copies do not keep audio, since EgoBlur copies non-camera streams).

## 7. Location data

Precise GNSS traces can reveal home/work places and routines. Implemented and tested functions
(`ariagen_escooter.privacy`):

| Function | Effect |
|---|---|
| `trim_endpoints(gps, radius_m)` | removes fixes within `privacy.gps.endpoint_radius_m` (200 m) of start and end |
| `remove_privacy_zones(gps, zones)` | removes fixes inside declared zones (kept in a non-versioned local file, e.g. `configs/local/privacy_zones.yaml`) |
| `to_relative_coordinates(gps)` | replaces lat/lon by metres from the first fix, rotated to the first direction of travel |
| `generalize_coordinates(gps, grid_m)` | snaps fixes to a `privacy.gps.generalization_grid_m` (50 m) grid |

Analyses use the head trajectory in a local metric frame (VIO) and segment classes; absolute
coordinates are needed only to define segments. Shared data would contain at most the geometry
needed for the analysis, generalised or relative (**TBD**).

## 8. Cloud processing (MPS) - avoided by default

Meta's Machine Perception Services require **uploading the raw VRS** (video, audio, GNSS) to
Meta's cloud. Meta states that raw uploads are deleted after at most 30 days and that partner
data are not available to Meta researchers; the processing location is not stated. Using MPS
would therefore need a DPO assessment (processor agreement, transfers, participant information).
The default pipeline uses only on-device data stored in the VRS (VIO and eye gaze), so **no
upload is needed**. MPS-based options exist in the code (`aria.pose_source: mps_closed_loop`,
MPS readers) but are off by default.

## 9. Sharing and publication

Allowed by default: aggregated results (no cell with fewer than 3 participants, cf. the Garante
rules for research), synthetic data, code. Anything else (derived per-segment metrics, generalised
trajectories, anonymised media) requires: identifier scan, GPS processing, manual review, a
release note listing what was removed, and approval (**TBD**: ethics committee, DPO, data
management plan, repository and licence).

## 10. Legal and ethical framework (to be confirmed by the DPO)

- GDPR (Reg. (EU) 2016/679): art. 5 (minimisation, storage limitation with research
  derogations), 6 (legal basis **TBD**), 9 (video is not special-category data per se), 13
  (information to bystanders recorded directly, layered approach), 25 (by design), 35 (DPIA:
  the Garante list of 11 Oct 2018 includes processing with innovative technologies such as
  **wearable devices** combined with other criteria; systematic monitoring of public areas and
  location data are further criteria -> a DPIA is very likely required), 89 (research
  safeguards, pseudonymisation).
- Italian Codice privacy (d.lgs. 196/2003 as amended) and the Garante's *Regole deontologiche
  per trattamenti a fini statistici o di ricerca scientifica* (provv. n. 515 of 19 Dec 2018).
- EDPB Guidelines 3/2019 on video devices (masking/scrambling recommended; irreversible blurring
  counts as erasure).
- Project Aria Research Community Guidelines (LED visible, stop on request, no sensitive places,
  de-identification of faces and plates, no re-identification, honour deletion requests).
- Ethics references: Kelly et al. (2013), *An ethical framework for automated, wearable cameras
  in health behavior research*, Am J Prev Med 44(3):314-319, doi:10.1016/j.amepre.2012.11.006;
  Mok, Cornish & Tarr (2015), *Too much information: visual research ethics in the age of
  wearable cameras*, Integr Psychol Behav Sci 49(2):309-322, doi:10.1007/s12124-014-9289-8.

## 11. Per-session checklist

Before: consent signed and stored with the key (not in the repo) - pseudonym allocated - device
reset between wearers - LED visible, badge/notice worn - route free of sensitive places - helmet
and road rules briefing.
After: VRS copied to restricted storage over USB - copy verified - manifest completed without
identifiers - `validate` passes - anonymised copy produced before any viewing for annotation -
technical issues and deletion requests recorded.

## 12. Status

| Item | Status |
|---|---|
| Tier folders, `.gitignore` rules, manifest identifier scanner | implemented, tested |
| GPS protection functions | implemented, tested |
| Region blurring utility, detector interface, anonymisation loop | implemented, tested (fake detector) |
| EgoBlur environment (`setup_linux.sh --egoblur`) | implemented, not yet executed |
| EgoBlur run on Gen 2 VRS + QA sampling | planned (needs a real recording and the model weights) |
| Audio handling, recording profile without audio | TBD |
| Legal basis, DPIA, retention period, release policy, key custody | TBD (controller, DPO, ethics committee) |
