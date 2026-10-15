# Computer vision: candidate selection and benchmark plan

Decision document for the scene-understanding part of semantic gaze
(`timestamp -> gaze -> RGB frame -> semantic class -> object id`). Evidence, versions, licences
and the 125 sources are in [cv_models_desk_study.md](cv_models_desk_study.md). **No model has
been downloaded, trained or run**: this phase only selects candidates and defines how they
will be compared on our own annotated Aria frames.

## 1. Constraints

- Aria Gen 2 RGB: wide fisheye (FISHEYE624 model), rolling shutter, 2016x1512 at 15 Hz in our
  profile; head-mounted, so strong ego-rotation, own handlebar/hands in the lower image band.
- Gaze 30 Hz vs frames 15 Hz: a gaze sample can be up to 33 ms from its frame (about 3 deg of
  image motion at 100 deg/s head rotation). No published Gen 2 gaze accuracy (Gen 1: about
  1.5 deg after calibration): the angular tolerance must be measured in the pilot.
- Models trained on car-mounted rectilinear images (Cityscapes, BDD100K) are **not assumed**
  to be accurate on head-mounted fisheye video; Mapillary Vistas includes head-mounted and
  wide-angle imagery and is the closest public domain, but still a shift.
- GPUs: RTX 6000 Ada (48 GB) and GTX 1660 (6 GB). Throughput target: the whole dataset in
  under a week on the RTX 6000.

## 2. Class coverage decides before accuracy

| Our class (taxonomy) | Best public source | Gap |
|---|---|---|
| road, cycle_lane, sidewalk, crossing, curb | Mapillary Vistas v1.2 (Bike Lane, Crosswalk - Plain, Lane Marking - Crosswalk, Curb, Curb Cut, Sidewalk) | Cityscapes cannot express cycle lanes, crossings or curbs; Italian cycle-crossing markings must be checked |
| pedestrian, cyclist, bicycle, car, motorcycle, large/other vehicles | COCO / Objects365 detectors; Vistas (Person, Bicyclist, vehicles) | cyclist = person + bicycle association rule |
| **escooter** | no class in Vistas, Cityscapes, COCO, LVIS; **V3Det "electric kick scooter"** (open-vocabulary MM-Grounding-DINO), nuImages "personal mobility", SAM 3 prompts | needs open-vocabulary detection or fine-tuning; current Vistas mapping "Other Rider -> escooter" is provisional |
| parked_vehicle | none (temporal) | static vehicle track in the world frame (VIO + calibration) |
| traffic_sign, traffic_light, obstacle, infrastructure_element | Vistas, Objects365 | - |
| path_surface_unspecified, unknown | fallback classes of our hierarchy | used when a distinction is unreliable - **never a guessed class** |

Road-surface material (asphalt vs pavers) is annotated at route-segment level from the route
data, not per pixel.

## 3. Shortlist (deliberately not "largest/newest by default")

| Approach | Default | Alternatives | Main reasons / cautions |
|---|---|---|---|
| A. Semantic segmentation (surfaces, infrastructure) | **Mask2Former Swin-L, Vistas v1.2 semantic** (mIoU 63.2 on Vistas val) | OneFormer Vistas (64.0) as second opinion; Mask2Former Vistas **panoptic** (surfaces + instances); EoMT-L Cityscapes (MIT, fast) as baseline/fine-tuning base | only Vistas models have the needed surface classes; weights CC BY-NC 4.0 and Vistas data CC BY-NC-SA: research use only |
| B. Detection / instance segmentation (road users) | **RF-DETR-Seg M/L** (Apache-2.0 code and weights) | D-FINE Objects365 (more classes); **MM-Grounding-DINO with V3Det** (e-scooter vocabulary, Apache-2.0); SAM 3 (text prompts, gated licence); YOLO26-seg only as AGPL reference | small far objects need tiling or larger input; e-scooters only via open vocabulary or fine-tuning |
| C. Tracking (object identity) | **BoT-SORT with camera-motion compensation**, compensation from Aria VIO rotation | ByteTrack (baseline), OC-SORT / Deep OC-SORT, TrackTrack; SAM 2.1 propagation only for objects near the gaze | 15 Hz + head rotation = large inter-frame motion; IoU-only association expected weakest |
| D. Segment Anything (refinement / annotation assist) | **SAM 2.1** (Apache-2.0) | SAM 3 (gated), MobileSAM/EfficientSAM (GTX 1660) | annotation pre-labelling must not bias test labels |

Licence summary: MIT/Apache components preferred; Vistas- and Cityscapes-trained weights are
non-commercial; Ultralytics YOLO/YOLOE and BoxMOT are AGPL-3.0 (weights included); SAM 3 and
DINOv3 use gated custom Meta licences; CVAT's SAM 2 features exist only in the hosted editions
(not usable with identifiable video without a data-processing agreement).

## 4. Default pipeline (to be confirmed by the benchmark)

1. Surfaces: Vistas semantic model -> `LabelMapping` -> taxonomy label map per frame
   (implemented interface: `segmentation.py`, `configs/label_mappings/`).
2. Road users: detector (COCO classes) + open-vocabulary prompts for e-scooters, signs,
   bollards; rider association (person over bicycle/kick-scooter).
3. Tracking with VIO-based motion compensation; class by track-level majority.
4. Parked vehicles: tracks static in the world frame for >= 2 s.
5. Gaze lookup: time-aligned gaze (or rotation-compensated to the frame time), hierarchical
   rule (road-user instances within tolerance r first, then surfaces), r = measured median gaze
   error, "ambiguous" band = measured 95th percentile; soft (probabilistic) assignment as a
   sensitivity analysis. Gaze outside the image -> `offscreen`; no label -> `unknown`.
6. QA per segment: coverage, ambiguous fraction, model-uncertainty monitor.

Alternatives: (i) panoptic Vistas model for both surfaces and instances; (ii) SAM 3 text-prompted
detection + tracking for road users.

## 5. Benchmark plan

**Questions.** (1) best surface model, native fisheye vs rectified pinhole crop; (2) best
road-user recall by angular size and e-scooter recognition; (3) identity stability of gazed
objects at 15 Hz with/without VIO compensation; (4) best gaze-assignment rule and tolerance,
and the residual error in the downstream quantity (time share per class per route segment).

**Sampling (stratified, participant-disjoint test split).** Strata: vehicle (2) x infrastructure
(6 groups) x light (3) x head angular speed (3), with participant, traffic density, radial
position of the gaze and blur recorded as covariates. Units:
- ~2,000 **gaze points** (primary; >= 250 per vehicle x main-infrastructure cell), spaced >= 2 s;
- 150-200 **partially labelled frames** (surfaces + road users; everything else `ignore`);
- 30-40 **tracking clips** of 10 s around annotated interactions plus random clips.

**Ground truth.** Written annotation guide with Italian examples (cycle crossings with dashed
lines, shared paths, bollards, pavers); self-hosted CVAT Community or X-AnyLabeling with local
SAM pre-labels for training/tuning only; 20 % double annotation (Cohen's kappa >= 0.8 for
gaze-point classes; inter-annotator IoU as the ceiling for model IoU); annotation on
EgoBlur-anonymised frames by authorised staff only.

**Metrics.** Per-class IoU and confusion (cycle lane / road / sidewalk; crossing / road);
precision/recall per class and by angular-size and radial bins; HOTA, IDF1, ID switches per
minute and gaze-weighted identity accuracy; **gaze-hit accuracy** at r in {0, 0.5, 1, 2} x
measured gaze error, ambiguous rate; Bland-Altman agreement of time share per class per segment
and of first-gaze times vs manual coding; GPU-seconds per frame and peak memory.

**Sample-size reasoning.** For a gaze-hit accuracy near 0.8, about 250 points give +-5
percentage points; with clustering by participant (design effect ~2) and paired model
comparisons (McNemar, 5 pp difference), about 2,000 points are needed in total.

**Decision rules (fixed before looking at test results).** Licence gate; coverage gate (every
must-have class directly or via a documented rule); choose the cheapest candidate non-inferior
to the best by <= 3 pp in gaze-hit accuracy; provisional floors (to agree with the project
lead): >= 0.70 gaze-hit accuracy in every vehicle x infrastructure cell, road-user recall
>= 0.8 for objects larger than 2 deg, <= 1 ID switch per gazed object per minute, time-share
error <= 5 pp per class per segment. Classes failing the floors -> fine-tuning on
participant-disjoint Aria labels, remapping to the parent fallback class, or manual coding -
always reported.

**Order of work.** (1) Before the pilot, qualitative runs on public Aria Gen 2 outdoor frames
(Aria Gen 2 Pilot Dataset) to catch gross failures and to check the Vistas "Other Rider" /
"Wheeled Slow" semantics; (2) pilot: gaze-accuracy targets and stratified frame collection;
(3) gaze-point ground truth first; (4) benchmark A and B on gaze points, then segmentation and
tracking sets for the finalists; (5) freeze models, versions and thresholds in the run metadata.

## 6. Status

Implemented: segmentation interface, label maps per frame, label mappings (Vistas v1.2,
Cityscapes; provisional), gaze lookup with radius and validity rules, hierarchical taxonomy.
Planned: detector/tracker integration, rectification A/B, soft assignment, annotation guide and
tool set-up, benchmark scripts. Nothing has been evaluated on Aria riding imagery.
