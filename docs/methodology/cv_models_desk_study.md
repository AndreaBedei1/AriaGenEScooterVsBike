# Computer-vision back-ends for semantic gaze — desk study and benchmark design

> Desk study compiled on 2026-10-15 (no model downloaded or run). Decision summary: [cv_benchmark_plan.md](cv_benchmark_plan.md).


Project: AriaGenEScooterVsBike (head-mounted Project Aria Gen 2, e-scooter vs bicycle riders, Italian city).
Scope: choose candidate models for `timestamp -> gaze point -> RGB frame -> semantic class -> object ID`
and design the benchmark that will select among them. **No model was downloaded or run**: every
number below is a published number (with its hardware/resolution) or is explicitly marked as an estimate.

Date of the desk study: **2026-10-15**. All web sources were read on that date unless stated otherwise;
"version seen" = Git default branch / Hugging Face `lastModified` / arXiv version on that date.

Markers used throughout:

| Marker | Meaning |
|---|---|
| (no marker) + `[n]` | verified on the cited primary source `[n]` (see §13) |
| `[S]` | secondary source only (blog, mirror, aggregator, search snippet): treat as provisional |
| `[U]` | could not be verified (page not reachable, no published figure, or definition unavailable) |
| `[E]` | our estimate / back-of-the-envelope calculation (method stated) |
| `[P]` | our proposal (design choice), not a fact |

---

## 0. Executive summary

**Main finding.** No public model covers our taxonomy out of the box. Surfaces (cycle lane, crossing, curb,
sidewalk) are only covered by **Mapillary Vistas** models; road users by **COCO/Objects365** detectors;
**e-scooters (kick scooters) have no class in Vistas, Cityscapes, COCO or LVIS** — they exist only in
**V3Det** ("electric kick scooter") [71], loosely in Objects365 ("Scooter", definition unknown) [69]
and nuScenes/nuImages ("personal mobility vehicle") [72][73], or via open-vocabulary prompting (SAM 3,
Grounding-DINO family). A prior e-scooter egocentric study found that a pre-trained R-CNN applied
around fixations reached only 10.5 % pedestrian and 15.1 % car recall and fell back to manual coding
[115]: an in-domain benchmark is therefore a prerequisite, not an option.

**Shortlists** (motivated in §3–§6; deliberately not "largest/newest by default"):

| Approach | Shortlist (default first) |
|---|---|
| A. Semantic / panoptic | **Mask2Former Swin-L Vistas v1.2 semantic** · OneFormer (DiNAT-L/Swin-L) Vistas · Mask2Former Swin-L Vistas **panoptic** · EoMT-L (DINOv2) Cityscapes as fast, MIT-licensed baseline and fine-tuning base |
| B. Detection / instance | **RF-DETR-Seg (M/L, Apache-2.0)** · D-FINE-L/X Objects365 (365 classes) · MM-Grounding-DINO (V3Det-trained, Apache-2.0) for e-scooter/open vocabulary · **SAM 3** (text-prompted masks, gated licence) · YOLO26-seg only as AGPL reference baseline |
| C. Tracking | **BoT-SORT + camera-motion compensation (MIT)** · ByteTrack (MIT, baseline) · OC-SORT / Deep OC-SORT (MIT) · TrackTrack (MIT, CVPR 2025) · SAM 2.1 / SAM 3 mask propagation for gazed objects only |
| D. SAM family | **SAM 2.1 (Apache-2.0)** for box-prompted refinement and video propagation · SAM 3 (text prompts, gated) · MobileSAM / EfficientSAM (Apache-2.0, GTX 1660-friendly) · SAM 1 ViT-H (only SAM variant in CVAT Community) |

**Recommended default pipeline** [P]: Vistas semantic segmentation for surfaces + RF-DETR-Seg (COCO
classes) and an open-vocabulary detector for e-scooters/signs + BoT-SORT with Aria-pose-based motion
compensation + hierarchical gaze lookup with a tolerance radius equal to the *measured* gaze error.
**Alternative** [P]: Vistas *panoptic* model as single source of surfaces and road-user instances, or a
SAM 3-centric pipeline (text-prompted detection + tracking) for road users.

**Key licence warnings**: Mapillary Vistas (CC BY-NC-SA, research use) [37] `[S]` and Cityscapes (non-commercial,
no redistribution) [39] constrain every model trained on them; Mask2Former model-zoo weights are
**CC BY-NC 4.0** [11]; SegFormer weights NVIDIA non-commercial [18]; **Ultralytics YOLO/YOLOE/BoxMOT are
AGPL-3.0, trained weights included** [46][60][80]; DEIMv2 and DEVA are non-commercial [53][95];
SAM 3 and DINOv3 use custom Meta licences with gated access [64][28]; RF-DETR XL/2XL are PML 1.0 [48];
CVAT's SAM 2 tracker/interactor is not in the open-source Community edition [101].

---

## 1. Constraints that drive the choice

### 1.1 Sensor facts (Aria Gen 2 RGB)

| Item | Value | Source |
|---|---|---|
| RGB sensor | Sony IMX681, 12 MP, rolling shutter, 133° H × 99° V FOV | [1] |
| Standard recording profiles | profile8: 2560×1920 @ 10 Hz; profile10: 2016×1512 @ 30 Hz; on-device eye gaze 30 Hz in both | [2] |
| 15 Hz | **No standard profile at 15 Hz** is listed [2]; 15 Hz must come from a custom profile or from sub-sampling profile10. Design and benchmark should cover 10–30 Hz. | [2] |
| Camera model | FISHEYE624 = Fisheye62 + 4 thin-prism coefficients (fx = fy) | [3] |
| Rectification utilities | `get_linear_camera_calibration`, `distort_by_calibration` in projectaria_tools | [4] |
| Eye-tracking hardware | 400×400 IR camera per eye; gaze "up to 90 Hz" on device | [1] |
| Gaze accuracy (Gen 2) | **No numeric figure published** in the Gen 2 docs, MPS benchmark page or Meta blog [1][7][8] → `[U]`; Gen 1: median 1.5° *after* personalised calibration [5] | [5] |

Approximate angular resolution `[E]` (equidistant approximation f ≈ (W/2)/(HFOV/2); the real FISHEYE624
mapping must be computed from each device's calibration): 2016 px → **≈ 15 px/deg** (868 px/rad);
2560 px → ≈ 19 px/deg. Consequences (2016 px, centre of the image) `[E]`:

| Quantity | Pixels |
|---|---|
| gaze error 1.5° / 3° / 5° | 23 / 45 / 76 px |
| pedestrian (1.7 m) at 10 / 20 / 30 / 50 m | 147 / 74 / 49 / 30 px tall |
| traffic sign (0.6 m) at 10 / 20 / 30 m | 52 / 26 / 17 px |
| kick-scooter stem (4 cm) at 10 m | 3 px (thin structure: masks will miss it) |
| head rotation 100°/s × 33 ms (half a frame period at 15 Hz) | 3.3° ≈ 51 px |

So, for far road users, **the gaze uncertainty is of the same size as the target**. Model choice matters
less than the gaze-to-object assignment rule for those cases (§8).

### 1.2 Compute

- RTX 6000 Ada (48 GB): all candidates fit; offline batch processing is acceptable.
- GTX 1660 (6 GB): light models only (SegFormer-B0/B2, RF-DETR-N/S, SAM 2.1-tiny, MobileSAM) and annotation tooling `[E]`.
- Volume: 54,000 frames per hour of video at 15 Hz (108,000 at 30 Hz) `[E]`. A model running at 2–3 FPS
  needs ~5–8 GPU-hours per hour of video `[E]` — feasible offline, but it rules out heavy ensembles on every frame.

### 1.3 Licence context

The study is academic research with publication. Most restrictions below are compatible with that use,
but they matter (i) if a commercial partner is involved, (ii) if fine-tuned weights or derived datasets
are released, (iii) if code is distributed or offered as a service (AGPL). This is not legal advice;
check with the institution's technology-transfer office before releasing models or data.

---

## 2. Class coverage: our taxonomy vs public label spaces

Vistas class lists were parsed from mmsegmentation's dataset definitions [35] (v1.2: 66 entries incl.
"Unlabeled"; v2.0: 124 entries); the Mask2Former Vistas registration uses the v1.2 list [12]. COCO, LVIS,
Objects365, Open Images and V3Det lists were parsed from [67][68][69][70][71].

| Our class | Vistas v1.2 | Vistas v2.0 (adds) | Cityscapes-19 | COCO-80 | LVIS v1 | Objects365 | V3Det | nuScenes / nuImages |
|---|---|---|---|---|---|---|---|---|
| carriageway / road | Road, Service Lane, Parking, Lane Marking - General | Road Shoulder, Driveway, Parking Aisle, many lane-marking subclasses | road (incl. painted bike lanes) [41] `[S]` | – | – | – | – | surface classes in nuImages [73] |
| cycle lane / path | **Bike Lane** | Bike Lane, Lane Marking - Symbol (Bicycle) | none (painted lane = road; separated path = sidewalk) [41] `[S]` | – | – | – | – | – |
| sidewalk | Sidewalk, Pedestrian Area | + Traffic Island | sidewalk | – | – | – | – | – |
| crossing (zebra / cycle) | **Crosswalk - Plain, Lane Marking - Crosswalk** | + Lane Marking (only) - Crosswalk | road | – | – | Crosswalk *Sign* only | crosswalk, crosswalk sign | – |
| curb | **Curb, Curb Cut** | Curb, Curb Cut | not a class (curbs excluded from road [41] `[S]`) | – | – | – | – | – |
| road surface / defects | Pothole, Manhole, Catch Basin | + Water Valve | – | – | – | – | manhole cover | – |
| pedestrian | Person | + Person Group | person | person | person | Person | person | pedestrian.* |
| bicycle | Bicycle | Bicycle | bicycle | bicycle | bicycle | Bicycle | bicycle, pedelec | vehicle.bicycle |
| cyclist | **Bicyclist** | Bicyclist | rider (+ bicycle) | person + bicycle | person + bicycle | – | cyclist | bicycle with "has rider" attribute [72] |
| **e-scooter (kick)** | none; "Other Rider" / "Wheeled Slow" definitions `[U]` | none | none (rider definition `[U]`) | **none** | **none** ("motor_scooter", synonym "scooter", defined as having "a low-powered engine") | "Scooter" (definition `[U]`), Hoverboard | **electric kick scooter**, electric scooter, motor scooter, moped | **Portable personal mobility vehicle** (skateboard, segway, scooters; box includes rider) [72] |
| car | Car | Car | car | car | car_(automobile), cab, police_cruiser | Car, SUV, Sports Car | car | vehicle.car |
| other vehicles | Bus, Truck, Motorcycle, Motorcyclist, Caravan, Trailer, On Rails, Other Vehicle | + Vehicle Group | bus, truck, motorcycle, train | bus, truck, motorcycle, train | bus_(vehicle), truck, motorcycle, minivan, pickup_truck | Bus, Truck, Van, Motorcycle, Heavy Truck, Tricycle | motorcycle, … | vehicle.* |
| parked vehicle | – (temporal) | – | – | – | – | – | – | attribute "parked" in nuScenes `[U]` |
| traffic sign | Traffic Sign (Front/Back), Traffic Sign Frame | + Direction, Parking, Temporary, Ambiguous subclasses | traffic sign | stop sign | stop_sign, street_sign | Traffic Sign, Stop Sign, Speed Limit Sign, Crosswalk Sign | stop sign, crosswalk sign | – |
| traffic light | Traffic Light | **Traffic Light - Cyclists**, - Pedestrians, - General (Single/Upright/Horizontal), - Other | traffic light | traffic light | traffic_light | Traffic Light | traffic light | – |
| obstacle | Barrier, Pothole, Trash Can | + **Traffic Cone**, Temporary Barrier, Concrete Block, Ambiguous Barrier | – | fire hydrant, bench | cone (traffic_cone), trash_can | Traffic cone, Trash bin Can, Fire Hydrant | – | barrier, traffic cone `[U]` |
| infrastructure elements | Pole, Utility Pole, Street Light, Fence, Guard Rail, Wall, Bench, Bike Rack, Billboard, CCTV Camera, Junction Box, Mailbox, Phone Booth | + Road Median, Lane Separator, Parking Meter, Pole Group, Signage - * | pole, fence, wall | parking meter, bench | parking_meter, pole, streetlight, signboard | Street Lights, Parking meter, Bench | street light, lamppost | – |
| unknown | Unlabeled | Unlabeled | void | – | – | – | – | – |

Notes:

- **Vistas v1.2 vs v2.0.** v2.0 refines 66 → 124 classes [35]; additions relevant here are traffic cones,
  cyclist traffic lights, bicycle symbol markings, stop/give-way lines, temporary barriers, road median and
  lane separators. **I found no public v2.0-trained checkpoint on Hugging Face** (search of the HF model
  index for "mapillary"/"vistas" on 2026-10-15 returned only Mask2Former Swin-L semantic/panoptic and a
  MaskFormer R50, all v1.2) `[U]` for other hosts. Using v2.0 therefore implies fine-tuning.
- Vistas class definitions for "Other Rider" and "Wheeled Slow" could not be retrieved `[U]`; the project's
  current mapping `Other Rider -> escooter` (`configs/label_mappings/mapillary_vistas_v1_2.yaml`) must stay
  "provisional" until verified visually on pilot frames.
- Vistas includes imagery from head- or car-mounted cameras (e.g. GoPro, Garmin) and wide-angle lenses
  (15–20 mm), from all continents [36]: it is the closest public match to our viewpoint. Cityscapes is
  vehicle-mounted, 50 cities, daytime, good/medium weather [40].
- Italian cycle crossings are marked with two dashed white lines (50 cm dashes and gaps), DPR 495/1992
  art. 146, fig. II.437 [120] `[S]` — visually different from zebra crossings; whether Vistas annotators
  labelled such markings as "Lane Marking - Crosswalk" or "General" is `[U]` and must be checked in the benchmark.
- "Road surface" in the sense of material (asphalt vs pavers/cobblestones, common in Italian centres) is
  not a class in any dataset above → annotate at route-segment level, not per pixel [P].
- "Parked vehicle" is not a visual class anywhere; it needs temporal reasoning (§9).

---

## 3. A — Semantic and panoptic segmentation

There is no maintained public leaderboard any more (Papers with Code was shut down in July 2025 [43]
`[S]`), so numbers below come from authors' READMEs/model zoos. ss = single-scale, ms = multi-scale + flip.

### 3.1 Comparison table

| Model (version seen) | Training data | Benchmark (split, metric) | Checkpoints | Licence code / weights / data | Speed, memory (published) |
|---|---|---|---|---|---|
| **Mask2Former** Swin-L (IN21k), repo archived 2025-01-01 [10] | **Vistas v1.2** semantic | Vistas val mIoU **63.2 ss / 64.7 ms** [11] | HF `facebook/mask2former-swin-large-mapillary-vistas-semantic` (216 M params, lastModified 2023-09-11) [13] | MIT (Deformable-DETR parts Apache-2.0) [10] / **model zoo: CC BY-NC 4.0** [11]; HF tag "other" [13] / Vistas CC BY-NC-SA [37] | not published for Vistas; Cityscapes Swin-L **2.86 FPS on A100 at 1024×2048** (mmseg) [15] |
| Mask2Former Swin-L, panoptic | Vistas v1.2 panoptic | Vistas val **PQ 45.5**, mIoU 60.8 [11] | HF `facebook/mask2former-swin-large-mapillary-vistas-panoptic` (216 M) [14] | as above | as above `[E]` |
| Mask2Former R50 | Vistas v1.2 | mIoU 57.4 / 59.0 [11] | model zoo `.pkl` only [11] | as above | faster than Swin-L `[E]` |
| Mask2Former Swin-L / Swin-B | Cityscapes | val mIoU 83.3 / 84.3 (L), 83.3 / 84.5 (B) [11] | HF `facebook/mask2former-swin-large-cityscapes-semantic` etc. [124] | as above + Cityscapes terms [39] | Swin-L 2.86 FPS, Swin-T 7.18 FPS on A100, 1024×2048 [15] |
| **OneFormer** Swin-L / ConvNeXt-L / DiNAT-L | Vistas (version presumably v1.2 `[U]`) | Vistas val mIoU **62.9 / 63.2 / 64.0 ss** (64.1 / 63.8 / 64.9 ms), PQ 46.7 / 47.9 / 47.8 [16] | Vistas weights only as GitHub-linked `.pth` (not on HF) [16]; Cityscapes on HF `shi-labs/oneformer_cityscapes_swin_large` (MIT tag) [17] | MIT [16] / weights licence not stated [16] `[U]` / Vistas, Cityscapes terms | ~219–223 M params [16]; speed not published `[U]` |
| OneFormer ConvNeXt-XL (Vistas-pretrained) | Vistas → Cityscapes | Cityscapes val mIoU 84.5 ss / 85.8 ms [16] | `.pth` [16] | as above | 372 M params [16] |
| **SegFormer** B0–B5 | Cityscapes (ADE20K variants exist) | Cityscapes val mIoU B2 81.08, B5 82.25 ss (mmseg, 1024×1024 crops) [20]; paper: B5 84.0 [19] | HF `nvidia/segformer-b{0..5}-finetuned-cityscapes-1024-1024` (lastModified 2022-08) [21] | **NVIDIA licence: "non-commercially, research or evaluation purposes only"** [18] | B2 3.36 FPS, B5 1.39 FPS on V100 with sliding-window inference [20] |
| **EoMT-L** (DINOv2-L), CVPR 2025 [25] | Cityscapes | Cityscapes val mIoU **84.2** at 1024×1024 [23] | HF `tue-mps/cityscapes_semantic_eomt_large_1024` (319 M, MIT tag, 2025-09-18) [26] | MIT [22] / MIT [26] / Cityscapes terms; DINOv2 backbone Apache-2.0 [31] | **25 FPS on H100** (1024×1024, torch.compile) [23]; authors claim up to 4× faster than task-specific decoders with ViT-L [25] |
| EoMT-L (DINOv3) | COCO, ADE20K only (no Cityscapes/Vistas) | ADE20K 59.5 mIoU (512) [24] | HF `tue-mps/*_dinov3` are **deltas requiring DINOv3 access** [24] | MIT code / DINOv3 Licence [28] | 137 FPS H100 at 512² [24] |
| DINOv3 ViT-7B + Mask2Former | ADE20K | ADE20K 62.6 ss / 63.0 ms (frozen backbone) [29] | gated via Meta form / HF (manual gating) [27][30] | DINOv3 Licence (custom; ITAR/military exclusions; acknowledgement in publications) [28] | 7 B backbone: impractical for 54 k frames/h `[E]` |
| **InternImage** (UperNet / SegFormer / Mask2Former heads) | Cityscapes, Cityscapes+Mapillary, Mapillary | Cityscapes val up to **86.37 ss / 86.96 ms** (InternImage-H + Mask2Former, Mapillary pre-training, 1,094 M params) [33] | `.pth` on HF repo `OpenGVLab/InternImage` incl. Mapillary-only checkpoints (no Vistas mIoU published; version `[U]`) [33] | MIT [32] / not stated `[U]` / Vistas + Cityscapes | 1.6–7.9 TFLOPs per image (listed FLOPs) [33]; slow `[E]` |
| ViT-Adapter-L + Mask2Former | Mapillary → Cityscapes | Cityscapes val 84.9 ss / 85.8 ms (571 M) [34] | GitHub release [34] | Apache-2.0 (LICENSE file) / not stated `[U]` | heavy `[E]` |

Memory at ~2 k resolution is not published for any of these `[U]`. Weight memory alone (fp32) is
~0.9 GB for 216 M parameters `[E]`; activations at ~3 MP should keep Swin-L Mask2Former well inside
48 GB, while the GTX 1660 (6 GB) is likely insufficient at full resolution without fp16/tiling `[E]` — to be measured.

### 3.2 Discussion

- **Class coverage dominates accuracy differences.** Cityscapes-19 models cannot express cycle lanes,
  crossings or curbs (painted lanes are "road", separated paths are "sidewalk") [41] `[S]`: whatever their
  mIoU, they cannot answer our research questions on infrastructure. Vistas models can.
- The ~1 mIoU spread between Mask2Former Swin-L (63.2) and OneFormer DiNAT-L (64.0) on Vistas val [11][16]
  is far smaller than the domain shift we expect (fisheye, head-mounted, Italian markings); it should not
  drive the choice — the in-domain benchmark should.
- **Mask2Former repo is archived** [10] and weights are CC BY-NC 4.0 [11]; still, apart from a MaskFormer R50,
  it is the only Vistas checkpoint on the Hugging Face Hub (Transformers-compatible), which matters for a
  reproducible pipeline [13][124].
- EoMT is architecturally the simplest (plain ViT), fastest and MIT-licensed [22][23]; it is the natural
  base for **fine-tuning on Vistas v2.0 + our own labels** if off-the-shelf models fail (needs only a
  DINOv2 backbone, Apache-2.0 [31]). DINOv3 variants add gated, custom-licensed weights [28] for a few points
  on ADE20K — not justified for us now.
- InternImage-H / ViT-Adapter / DINOv3-7B are the "biggest" options; their published gains are on
  Cityscapes/ADE20K, they are 0.6–7 B parameters, and they do not change class coverage → not shortlisted.

### 3.3 Shortlist A (3–5)

| # | Candidate | Why | Cons for us | Licence | Speed |
|---|---|---|---|---|---|
| A1 (default) | Mask2Former Swin-L Vistas v1.2 **semantic** | only off-the-shelf model with Bike Lane, Crosswalk (two kinds), Curb, Curb Cut, Bicyclist, Other Rider; HF-integrated; project mapping already exists | no e-scooter, no traffic cone (v1.2); archived repo; Swin-L heavy | MIT / CC BY-NC 4.0 / Vistas NC | ~2–3 FPS at ~2 MP `[E]` from [15] |
| A2 | OneFormer DiNAT-L (or Swin-L) Vistas | best published Vistas mIoU among off-the-shelf; independent "second opinion" for agreement analysis | not on HF; NATTEN dependency for DiNAT `[U]`; weights licence unstated | MIT / `[U]` / Vistas NC | similar to A1 `[E]` |
| A3 | Mask2Former Swin-L Vistas v1.2 **panoptic** | gives *instances* of persons, bicyclists, other riders, vehicles together with surfaces → can replace a separate detector (alternative pipeline) | PQ 45.5 → instance quality must be checked against B1 | as A1 | as A1 |
| A4 | EoMT-L (DINOv2) Cityscapes 1024 | fast, MIT weights; baseline to quantify what Vistas classes add; base model for fine-tuning on Vistas v2.0 / Aria labels | 19 classes only | MIT / MIT / Cityscapes NC | 25 FPS H100 @1024² [23] |
| (A5) | SegFormer-B2 Cityscapes | runs on GTX 1660 for quick checks | NVIDIA non-commercial; 19 classes | NVIDIA NC | 3.4 FPS V100 sliding [20] |

---

## 4. B — Object detection and instance segmentation

### 4.1 Closed-vocabulary detectors

| Model (version seen) | Data | COCO val (published) | Speed (published) | Checkpoints | Licence |
|---|---|---|---|---|---|
| **RF-DETR** N/S/M/L (ICLR 2026 [49]); DINOv2 backbone [49] | COCO | AP50:95 48.4 / 53.0 / 54.7 / 56.5 [48] | 2.3 / 3.5 / 4.4 / 6.8 ms, T4 TensorRT FP16, at 384–704 px [48] | pip `rfdetr`, HF e.g. `roboflow/rf-detr-base` (Apache tag) [124] | **Apache-2.0** for N–L and all Seg models; **PML 1.0** for A/F/P and XL/2XL [48] |
| **RF-DETR-Seg** N…2XL | COCO | mask AP 40.3 … 49.9; L: 47.1 [48] | L: 8.8 ms T4 at 504 px [48] | `rfdetr` [48] | Apache-2.0 [48] |
| **D-FINE** N…X | COCO; Objects365+COCO | COCO AP 54.0 (L) / 55.8 (X); with O365 pre-training 57.3 (L) / 59.3 (X); Objects365-only checkpoints released (L E25: 44.7 AP on O365 val) [50] | L 8.07 ms, X 12.89 ms, T4 TensorRT FP16 [50] | GitHub releases [50]; HF `ustc-community/dfine-*` (Apache tag) [124] | Apache-2.0; **O365-pretrained weights "may be subject to the Objects365 dataset terms"** [50] |
| RT-DETRv2 S…X | COCO | AP 48.1 … 54.3 [51] | 217 … 74 FPS T4 [51] | HF `PekingU/rtdetr_v2_r50vd` [124]; also in Ultralytics (then AGPL) | Apache-2.0 [51] |
| DEIM (D-FINE based) | COCO, O365 | DEIM-D-FINE-X with O365: 59.5 AP [52] | – | GitHub/Drive [52] | Apache-2.0 [52] |
| DEIMv2 (DINOv3 backbones) | COCO | X: 57.8 AP [53] | X: 13.75 ms [53] | HF (since 2025-11-03) [53] | **non-commercial "DEIMv2 License"** [53] |
| **YOLO26** n…x (Jan 2026) | COCO | 40.9 … 57.5 AP (e2e 40.1 … 56.9) [44] | 1.7 … 11.8 ms T4 TensorRT10 at 640 [44] | HF `Ultralytics/YOLO26` (agpl-3.0 tag) [124] | **AGPL-3.0 or Enterprise**; trained models AGPL by default [44][46] |
| YOLO26-seg | COCO | mask AP 34.7 … 46.8 (measured by Roboflow) [48] | 2.3 … 12.9 ms [48] | as above | AGPL-3.0 |
| YOLO11 / YOLOv8 / YOLO12 | COCO | YOLO12x 55.2 AP; Ultralytics itself recommends YOLO11/YOLO26 over YOLO12 for production (training instability, memory) [45] | – | – | AGPL-3.0 [45][47] |
| Mask R-CNN (Detectron2) | COCO, LVIS, Cityscapes | R101-FPN LSJ 400 ep: box 48.9 / mask 43.7 [54] | 0.073 s/img [54] | model zoo [54] | code Apache-2.0 [125]; **model-zoo weights CC BY-SA 3.0** [54] |

### 4.2 Open-vocabulary / promptable detectors

| Model | Training data | Published results | Licence | Notes |
|---|---|---|---|---|
| Grounding DINO (T, B) | T: O365, GoldG, Cap4M; B: + COCO, OpenImage, ODinW, RefCOCO [55] | COCO zero-shot 48.4 (T) [55] | Apache-2.0 [55]; HF `IDEA-Research/grounding-dino-base` [124] | Grounding DINO 1.5 is offered through a separate API repository [55] |
| **MM-Grounding-DINO** (T/B/L) | T/B variants with **V3Det** (O365, GoldG, V3Det) [56] | COCO zero-shot 50.6 (T, with V3Det); LVIS minival APr 33.0 vs 28.1 without V3Det [56] | Apache-2.0 (HF tags) [57] | HF `openmmlab-community/mm_grounding_dino_tiny_o365v1_goldg_v3det` [57]; V3Det vocabulary contains "electric kick scooter" [71] |
| LLMDet (T/B/L) | MM-GDINO fine-tuned on GroundingCap-1M [62] `[S]` | LVIS minival AP 44.7 (T) … 51.1 (L) [62] `[S]` | Apache-2.0 (HF tag, LICENSE) [62] | candidate if MM-GDINO is insufficient |
| OWLv2 (B/16, L/14) | self-training (ST) and ST + fine-tuning (FT) variants; FT data `[U]` | LVIS AP/APr: L/14 ST 32.8/34.6; L/14 ST+FT 48.8/44.0 (README values, "may differ slightly from the paper") [58] | Apache-2.0 code and checkpoints [58] | if FT used LVIS annotations, ST is the fairer zero-shot reference `[U]` |
| YOLO-World v2.1 | O365, GoldG, CC-LiteV2 [59] | LVIS AP 26.8 / APr 19.8 (L, 640) [59] | **GPL-3.0** (commercial licence on request) [59] | real-time |
| YOLOE (v8/11) | – | LVIS AP/APr 35.2/29.1 (11-L, text prompts) [60] | **AGPL-3.0** (built on Ultralytics) [60] | prompt-free mode with built-in vocabulary [60] |
| Florence-2-large | FLD-5B (5.4 B annotations / 126 M images) [61] | COCO zero-shot 37.5, fine-tuned 43.4 [61] | MIT [61] | 0.77 B; OD + phrase grounding [61] |
| **SAM 3** (Nov 2025; SAM 3.1 Object Multiplex 2026-03-27) | SA-Co data engine, 4 M unique concepts [63][65] | SA-Co benchmark (270 k concepts) ≈ 75–80 % of human performance [66]; video: **SmartGlasses test cgF1 36.4, pHOTA 63.6** (egocentric-heavy subset) [63][65] | **SAM License** (custom Meta; ITAR/military exclusions; must ship licence copy; acknowledge in publications) [64]; HF gated (manual) [66][124] | 848 M params [63]; **30 ms/image with 100+ objects on H200**; video cost scales linearly with #objects [65] |

### 4.3 Is there an e-scooter (kick scooter) class anywhere?

- COCO: no (80 classes include person, bicycle, motorcycle, traffic light, stop sign, parking meter, bench) [67].
- LVIS v1: no kick scooter; "motor_scooter" (synonym "scooter") is defined as a vehicle "with a low-powered engine" [68]; also "cone/traffic_cone", "street_sign", "parking_meter", "wheelchair", "skateboard" [68].
- Objects365: "Scooter" (id 129), "Hoverboard", "Stroller", "Wheelchair", "Traffic cone", "Traffic Sign", "Speed Limit Sign", "Crosswalk Sign" [69]; whether "Scooter" means kick or motor scooter is `[U]`.
- Open Images V7: "Segway", "Unicycle", "Bicycle", "Traffic sign", "Stop sign", "Parking meter" — no "Scooter" [70].
- **V3Det: "electric kick scooter", "electric scooter", "motor scooter", "moped", "pedelec", "cyclist", "crosswalk"** [71]; annotations CC BY 4.0, images Flickr-owned [71].
- nuScenes/nuImages: "Portable Personal Mobility Vehicle" (skateboard, segway, scooters; box includes the rider) with 2D boxes and instance masks in nuImages [72][73]; nuImages licence `[U]` (believed non-commercial).
- Argoverse 2: WHEELED_DEVICE, WHEELED_RIDER, WHEELCHAIR categories (definitions not read) [74] `[U]`.
- A benchmark of e-scooter riders vs pedestrians "in natural scenes" exists (YOLOv3 detection + MobileNetV2 classifier, whole-pipeline recall ≈ 0.75) [116]; camera viewpoint and data availability `[U]`.

Consequence [P]: e-scooters (and rider-vs-vehicle association) must come from (a) an open-vocabulary
detector whose training vocabulary includes them (MM-GDINO with V3Det; SAM 3), (b) a rule combining
`person` + a thin vehicle under the person, or (c) fine-tuning (RF-DETR or EoMT) on a few hundred in-domain
labels (+ V3Det / nuImages crops if licences allow).

### 4.4 Shortlist B (3–5)

| # | Candidate | Why | Cons | Licence | Speed |
|---|---|---|---|---|---|
| B1 (default) | **RF-DETR-Seg M or L** | Apache-2.0 for code and weights of these sizes; masks + boxes; DINOv2 backbone designed to fine-tune well on small datasets [49]; best mask AP/latency in its table [48] | COCO classes only; low native input size (432–504 px for Seg-M/L) → far objects (≤ 30 px at 2 k) need tiling or a larger input; do *not* use XL/2XL (PML 1.0) | Apache-2.0 | 5.9–8.8 ms T4 [48] |
| B2 | **D-FINE-L/X Objects365(+COCO)** | Objects365 vocabulary adds Scooter, Traffic Sign, Traffic cone, Stroller, Wheelchair, Hoverboard without prompting | boxes only; O365 terms caveat [50]; "Scooter" semantics `[U]` | Apache-2.0 + O365 terms | 8.1–12.9 ms T4 [50] |
| B3 | **MM-Grounding-DINO-T/B (with V3Det)** | only permissive model whose training vocabulary contains "electric kick scooter"; prompts in our own vocabulary ("e-scooter rider", "cycle lane sign", "bollard") | slower; open-vocab false positives; box-level | Apache-2.0 | not published `[U]` |
| B4 | **SAM 3** | text prompt → masks + identities in one model; evaluated on an egocentric glasses subset; useful both as challenger and as annotation pre-labeller | gated custom licence; 848 M; video cost scales with #objects (for 30 FPS the paper used 2 H200s for up to 10 objects, 4 for up to 28) [65] | SAM License | 30 ms/img on H200 [65] |
| B5 (reference only) | YOLO26-seg (x/l) | widely used in cycling/e-scooter literature (e.g. YOLOv8 in [115]) → comparability | AGPL-3.0 incl. trained weights; distribution/service triggers source release [46] | AGPL-3.0 | 7.6–12.9 ms T4 [48] |

---

## 5. C — Multi-object tracking

### 5.1 Comparison table

| Tracker | Type | MOT17 test HOTA / IDF1 | MOT20 test HOTA / IDF1 | DanceTrack test HOTA / IDF1 | Licence | Notes |
|---|---|---|---|---|---|---|
| ByteTrack (2021) | IoU + low-score boxes | 63.1 / 77.3 (29.6 FPS) [76] | 61.3 / 75.2 [76] | val 47.1 / 51.9 [81] | MIT [76] | associates low-score boxes to recover occluded objects [76] |
| BoT-SORT(-ReID) | IoU + ReID + **camera-motion compensation** | 65.0 / 80.2 [77] | 63.3 / 77.5 [77] | – | MIT [77] | GMC via OpenCV VideoStab (C++), or `orb`/`ecc` in Python [77] |
| OC-SORT | observation-centric KF | 63.2 / 77.5 (private det.) [78] | 62.4 / 76.4 [78] | **55.1 / 54.2** [78] | MIT [78] | designed for non-linear motion and occlusion [78] |
| Deep OC-SORT | OC-SORT + appearance | 64.9 / 80.6 [79] | 63.9 / 79.2 [79] | 61.3 / 61.5 [79] | MIT [83] | |
| Hybrid-SORT-ReID | | 64.0 / 78.7 [79] | 63.9 / 78.4 [79] | 65.7 / 67.4 [79] | MIT [84] | |
| StrongSORT++ | | 64.4 / 79.5 [79] | 62.6 / 77.0 [79] | 55.6 / 55.2 [79] | **GPL-3.0** [82] | |
| UCMCTrack (AAAI 2024) | ground-plane motion, needs camera parameters | 65.8 / 81.0 [85] | – | – | MIT [85] | idea reusable with Aria poses [P] |
| **TrackTrack** (CVPR 2025) | track-perspective association | **67.1 / 83.1** [79] | 65.7 / 80.9 [79] | **66.5 / 67.8** [79] | MIT [79] | evaluated on RTX 3090 [79] |
| CAMELTrack (2025) | learned association | "state of the art on multiple benchmarks" (no numbers in abstract) [86] | | | Apache-2.0 [86] | |
| BoxMOT v12 (toolbox) | 9 trackers, same detector | MOT17 *ablation split* HOTA: botsort 69.7, bytetrack 67.7, ocsort 66.4 … [80] | | | **AGPL-3.0** [80] | convenient for benchmarking only |
| SAM 2.1 video predictor | mask propagation | SA-V test J&F 79.5 (large), 76.5 (tiny) [90] | | | Apache-2.0 [90] | 39.5 FPS (large) / 91.2 FPS (tiny) on A100 [90] |
| SAM 3 tracker | concept detection + SAM 2-style masklets | SmartGlasses pHOTA 63.6; BURST HOTA 44.5 [63] | | | SAM License [64] | |
| SAMURAI | SAM 2 + Kalman motion-aware memory, single object, zero-shot [92] | LaSOT etc. (numbers not on README) [92] `[U]` | | | Apache-2.0 [92] | |
| Cutie / XMem | semi-supervised VOS (first-frame mask) [93] | `[U]` (not on README) | | | MIT [93][94] | |
| DEVA | decoupled: image model (e.g. Grounded-SAM) + propagation [95] | – | | | **CC BY-NC-SA 4.0** [95] | |

### 5.2 Behaviour under our conditions

- **Strong ego-motion (head rotations).** Image-plane motion of static and moving objects is dominated by
  head yaw/pitch; Kalman/IoU association fails when boxes jump between frames. Camera-motion compensation
  (BoT-SORT GMC) addresses this [77]. Egocentric benchmarks report that "frequent large camera motions"
  cause occlusion/out-of-frame events and re-identification problems for SOTA trackers [89].
  With Aria we can do better than image-based GMC [P]: per-frame device rotation from on-device VIO
  (10 Hz) / high-frequency VIO (~800 Hz) is available (project `docs/aria_gen2_integration.md`), so the
  predicted track position can be rotated into the new frame through the FISHEYE624 model before association;
  a ground-plane variant à la UCMCTrack [85] also becomes possible because camera intrinsics and pose are known.
- **Low frame rate (10–15 Hz).** Tracking-by-detection accuracy drops "significantly" under frame reduction
  [87]; ColTrack reports larger advantages at low frame rates [88] `[S]`. At 15 Hz with 100°/s head rotation,
  objects move ~6.7° (~100 px) between frames `[E]` (§1.1), so IoU-only association (ByteTrack) is expected
  to be the weakest; motion-compensated (BoT-SORT) or appearance-assisted trackers should be preferred. If 15 Hz
  is obtained by sub-sampling profile10, tracking at the native 30 Hz is an option worth benchmarking [P].
- **Occlusions / partial visibility.** ByteTrack's low-score association and OC-SORT's observation-centric
  re-update target this [76][78]. SAM 2 "may … lose track of or confuse objects in crowded scenes, after long
  occlusions", struggles with thin fast-moving objects and similar-looking nearby objects [91] — relevant for
  groups of pedestrians and for scooter stems.
- **Licences.** Prefer the MIT/Apache originals (ByteTrack, BoT-SORT, OC-SORT, TrackTrack) or Apache
  re-implementations (e.g. `roboflow/trackers`, Apache-2.0 [125]); BoxMOT (AGPL) only as a test harness.

### 5.3 Shortlist C (3–5)

| # | Candidate | Why | Cons | Licence |
|---|---|---|---|---|
| C1 (default) | **BoT-SORT with CMC** (ECC/ORB, then Aria-pose compensation [P]) | explicitly handles camera motion; strong on MOT17/20 [77] | ReID model trained on pedestrians (MOT) → domain shift for cyclists/scooters `[E]` | MIT |
| C2 | ByteTrack | simplest baseline, fast | IoU-only, frame-rate sensitive [87] | MIT |
| C3 | OC-SORT / Deep OC-SORT | best of the "simple" trackers on non-linear motion (DanceTrack) [78][79] | no explicit CMC (add our pose compensation) | MIT |
| C4 | TrackTrack | highest published HOTA/IDF1 among online trackers on all three benchmarks [79] | newer, less tooling | MIT |
| C5 | SAM 2.1 propagation (or SAM 3 tracker) **only for objects near gaze** | mask-level identity for the objects that matter; reuses annotation tooling | cost per object; limitations above [91]; SAM 3 licence | Apache-2.0 / SAM License |

---

## 6. D — Segment Anything family (refinement and annotation assist)

| Model | Use for us | Published facts | Licence |
|---|---|---|---|
| **SAM 2.1** tiny / small / base+ / large (2024-09-29) | refine detector boxes into masks; propagate masks through clips for GT | 38.9–224.4 M params; 91.2–39.5 FPS on A100; SA-V test J&F 76.5–79.5 [90] | Apache-2.0 (checkpoints and code) [90] |
| **SAM 3** / SAM 3.1 | text-prompted pre-labelling ("e-scooter", "cyclist", "traffic sign", "bollard"); video tracking | see §4.2 | SAM License, gated [64][66] |
| SAM 1 (ViT-H) | the SAM interactor available in **CVAT Community** via Nuclio [101] | 641 M params (HF) [124] | Apache-2.0 [125] |
| MobileSAM | interactive annotation on the GTX 1660 | 9.66 M params, ~12 ms/image (8 ms encoder + 4 ms decoder, single GPU) [97] | Apache-2.0 [97] |
| EfficientSAM (Ti, S) | same | numbers not on README [98] `[U]` | Apache-2.0 [98] |
| Grounded-SAM-2 | Grounding DINO + SAM 2 pipeline for text-prompted video pre-labelling | – | Apache-2.0 [99][125] |

Guidance [P]:

- **Prompting SAM with the gaze point is not a ground-truth generator.** Gaze falls near object borders by
  construction (error ≈ 23–45 px, §1.1); a point prompt on the border returns the wrong object or a part. Use
  gaze-point prompts only as *suggestions* in the annotation UI, with human acceptance; prefer box prompts
  from detectors.
- Box-prompted SAM 2.1 masks can tighten detector masks for small objects; benchmark whether the
  improvement in gaze-hit accuracy justifies the cost.
- Automated AOI generation with SAM/YOLO "facilitates the analysis of longer and more complex dynamic scenes",
  but "merely postpones the decision-making process about the appropriate AOIs" and can make AOIs too small
  relative to eye-tracker inaccuracy [118].

---

## 7. E — Datasets and domain shift

### 7.1 Datasets

| Dataset | Viewpoint / camera | Labels relevant to us | Licence | Role [P] |
|---|---|---|---|---|
| Mapillary Vistas v1.2 / v2.0 | crowd-sourced street level; phones, action cams, **head- or car-mounted**, wide-angle lenses; worldwide; 25 k images ≥ Full HD [36] | 66 / 124 classes (§2) | **CC BY-NC-SA** + "Research Use License", confidentiality clause [37] `[S]` (site is JS-rendered; terms read from search snippet and Dataset Ninja [38]) | primary source for surfaces; fine-tuning with v2.0 |
| Cityscapes | vehicle-mounted stereo, 50 cities, daytime, good/medium weather; 5 k fine + 20 k coarse [40] | 19 eval classes | non-commercial; no redistribution; trained models allowed as derivative works if dataset not recoverable [39] | baseline / pre-training only |
| BDD100K | dash-cam | 10 k segmentation images (19-class set `[U]`) | official page unreachable; mirrors show UC Berkeley terms (research/non-profit; commercial for members) [106] `[S]` | not needed |
| ADE20K | general scenes | 150 classes | images non-commercial research/education; annotations BSD-3 [107] | not needed |
| COCO / LVIS / Objects365 / V3Det | web photos | road users; V3Det has e-scooters [71] | COCO annotations widely reported CC BY 4.0 `[U]` (site not readable); Objects365 "non-commercial" [75] `[S]`; V3Det annotations CC BY 4.0, Flickr images [71] | detector pre-training; e-scooter class (V3Det) |
| nuImages | car-mounted, Boston/Singapore `[U]` | boxes + instance masks + surfaces; personal-mobility class [72][73] | `[U]` (believed non-commercial) | optional e-scooter fine-tuning data |
| KITTI-360 | car: 90° stereo + **two 180° fisheye** side cameras; 2D semantic labels announced for the right perspective camera (image_01) [105] | Cityscapes-compatible 19 eval classes [105] | CC BY-NC-SA 3.0 [105] | fisheye 2D labels not mentioned on the page `[U]` → limited |
| WoodScape | 4 surround **fisheye** cameras; 10 k images (8.2 k public) [104] | 10 seg classes: road, lanes, curbs, rider, person, vehicles, bicycle, motorcycle, traffic_sign [104] | code MIT, data "proprietary" (terms in a linked file) [104] `[U]` | fisheye robustness test / augmentation |
| Ego4D | head-worn, 3,670 h, 931 wearers, 74 locations, 9 countries; includes outdoor; gaze for a subset [108] | no road-scene segmentation | licence agreement required [108] | not needed for training |
| Aria Everyday Activities (AEA) | Aria Gen 1; 143 sequences, **5 indoor locations** [111] | 3D gaze, trajectories | `[U]` | gaze-format reference only |
| Aria Digital Twin (ADT) | Aria Gen 1; 200 sequences in **2 indoor scenes** [109] | **2D segmentation GT**, depth, 3D gaze [109] | `[U]` | test the gaze-on-mask code with real GT (indoor) |
| Nymeria | Aria; 300 h, 264 participants, 50 locations, "in the wild", eye tracking [110] | body motion, narrations | `[U]` | not needed |
| Aria Gen 2 Pilot Dataset (A2PD) | **Aria Gen 2**, includes an **outdoor walking** scenario; RGB 2560×1920 @ 10 fps [9] | hand–object masks; no road labels [9] | `[U]` | **zero-cost Gen 2 fisheye/rolling-shutter test images before our pilot** |
| Cyclist-view datasets | AuRa (bike-perspective camera, masks incl. bike-lane boundaries), PanoCycle360 (helmet 360°), BikeActions, BikeScenes (LiDAR) [122] | found by search; not opened | `[U]` | check availability/licence later |
| e-scooter egocentric | Kegalle et al. 2025: Tobii Pro Glasses 3 (25 FPS) + helmet Insta360 X3 [115] | manual AOIs | dataset release `[U]` | methodological precedent |

### 7.2 Sources of domain shift and what to do

| Factor | Why it matters | Mitigation / test [P] |
|---|---|---|
| Head-mounted vs car-mounted viewpoint | higher camera, pitch towards the path, head roll, own handlebar and hands in view, sidewalks/cycle paths seen from on top; Cityscapes is car-mounted [40]; Vistas includes head-mounted imagery [36] | prefer Vistas models; map Vistas "Ego Vehicle" to `unknown`/`other`; report metrics separately for the lower image band (own vehicle) |
| Fisheye (133° × 99°) | perspective-trained models degrade on radial distortion [113][114]; rectification of >90° FOV requires "significant cropping" [113] | A/B in the benchmark: (i) native fisheye; (ii) rectified pinhole crop via `get_linear_camera_calibration` + `distort_by_calibration` [4], predictions warped back; (iii) optional cylindrical/patch rectification. Evaluate by **radial bins** (centre vs periphery) because gaze is mostly central while road users often appear peripherally |
| Rolling shutter + motion blur | skew of vertical structures (poles, people) during head yaw; blur at low light | stratify by IMU angular speed and by a blur score (e.g. variance of Laplacian); include low-light/backlit strata |
| 10–15 Hz | larger inter-frame displacement for tracking [87]; up to 33 ms gaze–frame offset at 15 Hz (§1.1) | benchmark tracking at 15 vs 30 Hz if profile10 is used; rotation-compensate gaze to the frame time [P] |
| Italian infrastructure | cycle-crossing markings (two dashed white lines, art. 146 [120] `[S]`), red-painted lanes, pavers/cobblestones, bollards | per-class confusion analysis; extra strata for crossings and shared paths |
| Anonymisation (EgoBlur) | blurred faces/plates are a further shift for person/car detection | run CV on the same input that the production pipeline will use (raw in the restricted environment vs anonymised copies) — decision for the PI/ethics plan |

How to *measure* domain shift [P]: (1) report each model's in-domain scores next to its published
in-distribution scores (e.g. Vistas val 63.2 mIoU) on the same class subset; (2) per-stratum scores with
mixed-effects models (participant as random effect) for gaze-hit correctness ~ vehicle + infrastructure +
light + head angular speed + radial position; (3) unsupervised shift monitor on the full corpus (softmax
entropy / max-probability distribution per stratum) to flag ride segments where the model is unreliable and
to direct further annotation (active sampling).

---

## 8. F — Gaze-specific issues

### 8.1 Gaze uncertainty

- Gen 2 accuracy is unpublished `[U]`; Gen 1: 1.5° median after personalised calibration [5]; Gen 1 MPS
  provides per-sample confidence intervals in radians [6]. Outdoors, with sunglasses-like lighting, head
  vibration, strong sunlight and possibly no per-participant calibration, error is likely larger `[E]`.
- **Measure it in the pilot** [P]: before/after each ride, a 30–60 s validation with printed targets at
  2, 5 and 10 m (outdoors, same light), compute median and 95th-percentile angular error per participant;
  use the median as the tolerance radius and the 95th percentile as an "ambiguous" band.
- Add temporal error [P]: at 15 Hz the nearest frame can be up to 33 ms away from a 30 Hz gaze sample; at
  100°/s this is ~3.3° (§1.1). Either restrict to gaze samples within ±8 ms of the frame timestamp, or rotate
  the gaze ray by the head rotation between the gaze time and the frame (row) time using VIO/IMU. Rolling-shutter
  row timing is `[U]` (readout time not found in the docs read).

### 8.2 Assignment rules (to be compared in the benchmark) [P]

1. **Point lookup** (current default in `docs/methodology.md`, `lookup_radius_px = 0`).
2. **Radius majority** (current option): majority class within radius r.
3. **Distance-to-mask with tolerance**: for every instance mask, compute the pixel distance from the gaze
   point to the mask (0 inside); candidates = instances with distance ≤ r. Assign the nearest; if ≥ 2
   candidates within the ambiguity band, flag `ambiguous` (counted separately, never silently resolved).
4. **Hierarchical**: road users (instances) first within r, then surfaces/infrastructure by point/majority
   lookup. Rationale: Hooge et al. recommend AOI margins at least equal to the data inaccuracy [118];
   cGOM's masks tended to be *too small* (inward of the true contour), reducing true positives [117].
   Risk: a systematic bias towards road users — quantify it on GT.
5. **Probabilistic (soft) assignment**: weight class probabilities (softmax maps / instance scores) by a
   2-D Gaussian with σ from the measured error (converted to pixels through the calibration, which varies
   with radius in the fisheye); report expected dwell time per class with uncertainty instead of a hard label.

Overlap and boundary rules follow [118]: non-overlapping AOIs, explicit rule for shared boundaries,
`none`/`unknown` for gaps, `offscreen` for gaze outside the image.

### 8.3 Small / far objects, partial visibility, ID switches

- Far road users are 30–75 px tall at 20–50 m `[E]` (§1.1). Detectors with 432–704 px input on a 2016 px
  frame down-sample them ~3–4× (to ~8–20 px) → low recall `[E]`: benchmark recall by **angular size bins**
  (< 2°, 2–5°, > 5°) and test tiling (e.g. 2×2 overlapping crops) for the detector.
- Partial visibility at the image border (fisheye periphery) and behind other road users: score recall
  separately for truncated/occluded GT.
- ID switches inflate "number of looked-at objects" and fragment dwell times; evaluate IDSW per minute and,
  more importantly, **gaze-weighted identity accuracy**: for consecutive gaze samples on GT object k, the
  fraction whose predicted track ID is the one matched to k.
- Prior egocentric e-scooter work used a 70 px crop around fixations and a pre-trained R-CNN; recall was
  10.5 % (pedestrians) and 15.1 % (cars) and the authors reverted to manual AOI coding [115]. A full-frame
  model + tolerance-based assignment avoids the crop's loss of context, but must be shown to work (§10).
- Gaze-aware detection (gaze features injected into a ViT) is an emerging research line [121]; not needed for
  the first iteration.

---

## 9. Recommended pipelines [P]

### 9.1 Default (modular)

```
VRS -> RGB frames (native 2016x1512, FISHEYE624 calib) + gaze (30 Hz) + VIO poses
 1. Surfaces / infrastructure : Mask2Former Swin-L Vistas v1.2 semantic (A1)
                                -> LabelMapping YAML -> taxonomy label map (per frame, fp16, stored downsampled x2)
 2. Road users               : RF-DETR-Seg-L, COCO classes person/bicycle/car/motorcycle/bus/truck/traffic light (B1)
                                + MM-Grounding-DINO (V3Det) prompts: "electric kick scooter", "traffic sign",
                                  "bollard", "traffic cone" (B3)  [or SAM 3 (B4) if the licence is acceptable]
                                + rider association: person box overlapping a bicycle/kick-scooter box -> cyclist / e-scooter rider
                                + SAM 2.1 box-prompted mask refinement for objects within 2x tolerance of gaze (optional)
 3. Tracking                 : BoT-SORT, CMC = Aria VIO rotation (fallback ECC); class by track-level majority vote
 4. Parked vehicle           : vehicle track static in the world frame (ground-plane position from pose + calibration,
                                displacement < threshold over >= 2 s) -> parked_vehicle
 5. Gaze lookup              : time-aligned gaze (±8 ms or rotation-compensated) -> hierarchical rule (§8.2 #4),
                                r = measured median gaze error, ambiguity band = P95; soft variant (§8.2 #5) for sensitivity analysis
 6. QA                       : coverage, ambiguous fraction, entropy-based shift monitor per segment
```

Why this default: every component has a permissive or research-compatible licence except the Vistas
model (unavoidable for surfaces) and SAM 3 (optional); each stage can be swapped independently in the
benchmark; compute ≈ dominated by A1 (~2–3 FPS `[E]`).

### 9.2 Alternative 1 — panoptic unification

Mask2Former Swin-L **Vistas panoptic** (A3) for both surfaces and instances (Person, Bicyclist, Motorcyclist,
Other Rider, vehicles), OC-SORT/BoT-SORT on its instance masks, open-vocabulary detector only to re-label
"Other Rider"/"Wheeled Slow" instances as e-scooter or not. Fewer models and consistent masks; risk: PQ 45.5
[11] instance quality and missing e-scooter class.

### 9.3 Alternative 2 — promptable foundation model for road users

SAM 3 text prompts (pedestrian, cyclist, e-scooter, car, bus, truck, motorcycle, traffic sign, traffic light)
with its built-in tracker for road users, Vistas semantic for surfaces. Strongest open-vocabulary option and
evaluated on smart-glasses video [63], but gated custom licence [64], 848 M parameters and per-object video
cost [65].

### 9.4 Annotation-assist pipeline (for ground truth, not for results)

CVAT Community (MIT, self-hosted; SAM 1 interactor via Nuclio) [101] or X-AnyLabeling (GPL-3.0 desktop app;
SAM 1/2/3, Grounding DINO, ByteTrack/BoT-SORT/SAM 2-video, MOT export) [102] or Label Studio (Apache-2.0)
[103]. **CVAT's SAM 2 interactor and SAM 2 tracker are not available in the Community edition** (Online /
Enterprise only) [101]; using CVAT Online would upload identifiable video to a third party → requires a data
processing agreement and ethics approval. Recommended [P]: self-hosted tool + locally run SAM 2.1 / SAM 3
pre-labels exported as editable polygons.

---

## 10. Benchmark plan [P]

### 10.1 Questions the benchmark must answer

1. Which surface model (A1–A4, native vs rectified) gives the best class at the gaze point and per-class IoU for path surfaces?
2. Which detector/instance model (B1–B5, with/without tiling, with/without SAM refinement) gives the best recall of road users by angular size, and which option recognises e-scooters?
3. Which tracker (C1–C5, 15 vs 30 Hz, with/without pose-based compensation) keeps identities of gazed objects?
4. Which gaze-assignment rule (§8.2) and tolerance radius best reproduce manual gaze coding, and how large is the residual error in the downstream quantities (time share per class per route segment)?

### 10.2 Stratified sampling

Strata (full factorial is too large; use a balanced incomplete design and require minimum counts per main effect):

| Factor | Levels |
|---|---|
| Vehicle | e-scooter, bicycle |
| Infrastructure (from `segments.csv`) | protected cycle path · painted cycle lane · shared pedestrian–cycle path · road shared with traffic · crossing/intersection/roundabout (merged) · pedestrian/shared space |
| Light | daylight-diffuse · daylight-direct/backlit/low sun · dusk/artificial light |
| Head motion (IMU/VIO angular speed) | < 30°/s · 30–100°/s · > 100°/s |
| Also recorded as covariates | participant, ride, traffic density (no. of road users), radial position of gaze, blur score |

Sampling units [P]:
- **Gaze-point set** (primary): random gaze samples (valid gaze) stratified as above, with ≥ 2 s spacing
  within a ride to limit autocorrelation and a cap per participant × stratum to limit clustering.
- **Dense/partial segmentation set**: frames drawn from the same strata; label path surfaces, curbs, crossings
  and all road users as polygons; everything else `ignore`. (Full dense labelling costs > 1.5 h/image for
  Cityscapes [42] and ~94 min/image for Vistas [36] — not affordable at scale.)
- **Tracking set**: 10 s clips (150 frames at 15 Hz) centred on annotated interaction events
  (`events.csv`: pedestrian/cyclist/e-scooter/vehicle interactions) plus random clips.
- Hold-out rule: split by participant (no participant in both a tuning set and the test set) if any fine-tuning or threshold tuning is done.

### 10.3 Ground truth protocol and tools

| GT type | Content | Tool [P] | Effort `[E]` |
|---|---|---|---|
| Gaze-point labels | for each sampled gaze point: semantic class (taxonomy incl. `unknown`), object identity (instance), and whether the decision needed the tolerance ring (point inside object / within r / ambiguous) | small custom web form or CVAT points task; overlay of gaze point with rings at r and P95 | ~10–20 s per point |
| Partial segmentation | polygons/masks for surfaces + road users, `ignore` elsewhere | CVAT Community (MIT) with SAM 1 interactor, or X-AnyLabeling (GPL-3.0, local) with SAM 2.1/SAM 3 pre-labels | ~20–40 min per frame with SAM assistance `[E]` (to be timed in a pilot) |
| Tracking | boxes + IDs for road users on clips, key-frames every 5 frames + interpolation / SAM 2 propagation, export MOT format | CVAT (track mode) or X-AnyLabeling (MOT export) | ~30–60 min per clip `[E]` |
| Gaze accuracy | validation targets (§8.1) | own script | 1 min per participant session |

Quality control: written annotation guide with Italian examples (cycle crossings, shared paths, bollards,
pavers); **20 % double annotation**; Cohen's κ for gaze-point classes (target ≥ 0.8), inter-annotator IoU
for masks (gives the ceiling for model IoU); adjudication of disagreements; annotators blind to model outputs
for the test set (pre-labels only for the training/tuning set, or measure the anchoring bias on a subset).

### 10.4 Metrics

| Level | Metric | Notes |
|---|---|---|
| Pixel (surfaces) | per-class IoU on labelled pixels; mIoU over the path-surface group; confusion matrix (cycle lane ↔ road ↔ sidewalk; crossing ↔ road) | Boundary IoU optional for curbs |
| Object (road users) | precision / recall / F1 at IoU ≥ 0.5 per class; **recall by angular-size bin** (< 2°, 2–5°, > 5°) and by radial bin; mask AP for instance models | e-scooter and cyclist reported separately |
| Tracking | **HOTA (DetA, AssA)**, IDF1, ID switches per minute, fragmentation — via TrackEval (MIT, MOTChallenge format) [100] | also gaze-weighted identity accuracy (§8.3) |
| Gaze (primary) | **gaze-hit accuracy** = fraction of gaze samples whose predicted class (and object) equals GT, at tolerance r ∈ {0, 0.5, 1, 2} × measured median error; ambiguous rate | per stratum, with 95 % CIs |
| Downstream | absolute error and Bland–Altman agreement of **time share per class per route segment** and of first-gaze latency for events, automated vs manual | this is what the papers will report |
| Cost | GPU-seconds per frame, peak VRAM, failure rate | measured on the RTX 6000 Ada |

### 10.5 Sample size reasoning

- Proportions (gaze-hit accuracy): n = z²·p(1−p)/E². For p ≈ 0.8: **n ≈ 246 for ±5 pp**, 683 for ±3 pp;
  p ≈ 0.7: 323 / 897 `[E]`. With clustering, multiply by DEFF = 1 + (m−1)·ICC (e.g. m = 25 points per
  participant, ICC = 0.05 → DEFF 2.2) `[E]` → spread samples over many participants.
- Paired model comparison (McNemar, α = 0.05, power 0.8): to detect a 5 pp difference with 15 % discordant
  pairs needs **≈ 470 gaze points**; 3 pp needs ≈ 1,300 `[E]`.
- Proposed sizes [P]: **~2,000 gaze points** (≥ 250 in each vehicle × main-infrastructure cell, 8 cells),
  **~150–200 partially labelled frames** (≥ 20 per infrastructure group, both vehicles, ≥ 30 low-light),
  **30–40 tracking clips** (≈ 4,500–6,000 frames). IoU and HOTA CIs by bootstrap over frames/clips clustered
  by participant. Re-assess after the first 25 % of labels (variance-based re-estimation).

### 10.6 Decision criteria (pre-register before looking at test results)

1. **Licence gate**: usable for academic research and publication; flag NC/AGPL/gated components; prefer permissive when performance is equivalent.
2. **Coverage gate**: the pipeline outputs every must-have class (path surfaces, pedestrian, cyclist, e-scooter, car, other vehicles, traffic sign/light) directly or through a documented rule.
3. **Primary metric**: class-level gaze-hit accuracy at r = measured median gaze error. Choose the cheapest
   candidate that is **non-inferior** to the best by ≤ 3 pp (paired bootstrap / McNemar) — not the largest model by default.
4. **Floors** (provisional, to be agreed with the PI): no vehicle × infrastructure cell below 0.70 gaze-hit
   accuracy; VRU recall ≥ 0.8 for objects > 2°; IDSW ≤ 1 per gazed object per minute; time-share error ≤ 5 pp
   per class per segment (Bland–Altman limits reported).
5. **Fallback**: classes that fail the floors after A/B (native vs rectified, tiling, rule choice) → fine-tune
   (EoMT/RF-DETR on Vistas v2.0 + participant-disjoint Aria labels) or code them manually; report which.
6. **Throughput**: whole dataset processable in ≤ 1 week on the RTX 6000 Ada.

### 10.7 Order of work

1. Before the pilot: run candidates qualitatively on A2PD outdoor-walking Gen 2 frames [9] (fisheye, rolling
   shutter) to catch gross failures; verify the Vistas "Other Rider"/"Wheeled Slow" semantics visually.
2. Pilot: gaze-accuracy validation; collect strata; build the gaze-point GT first (cheapest, most decisive).
3. Benchmark A and B on the gaze-point set; then segmentation and tracking sets for the finalists only.
4. Freeze pipeline + thresholds; document versions (model ids, commit hashes, licence) in the run metadata.

---

## 11. Licence warnings (summary)

| Component | Licence | Implication for us |
|---|---|---|
| Mapillary Vistas data | CC BY-NC-SA + research-use licence, confidentiality [37] `[S]` | research only; share-alike/NC may extend to derived models; do not redistribute data |
| Cityscapes data | non-commercial, no redistribution; trained models allowed as abstract derivatives [39] | OK for research |
| Mask2Former model zoo weights | **CC BY-NC 4.0** [11] (HF tag "other" [13]) | non-commercial only |
| SegFormer weights | NVIDIA, research/evaluation only [18] | non-commercial only |
| Ultralytics YOLOv8/11/12/26, YOLOE | **AGPL-3.0** incl. trained models; Enterprise licence otherwise [46][60] | distributing code/weights or offering a service requires releasing full source under AGPL |
| YOLO-World | GPL-3.0 [59] | copyleft on distribution |
| BoxMOT | AGPL-3.0 [80] | test harness only |
| StrongSORT | GPL-3.0 [82] | copyleft on distribution |
| DEIMv2 | non-commercial licence (PRC law) [53] | avoid |
| DEVA | CC BY-NC-SA 4.0 [95] | non-commercial |
| RF-DETR XL/2XL, A/F/P | PML 1.0 [48] | avoid; N–L and Seg are Apache-2.0 |
| D-FINE O365 weights | Apache-2.0 code; "may be subject to the Objects365 dataset terms" [50] | check O365 terms (reported non-commercial [75] `[S]`) |
| SAM 3, DINOv3 | custom Meta licences; gated; ITAR/military exclusions; must ship licence; acknowledge in publications [64][28] | OK for research; record acceptance |
| Detectron2 model zoo | CC BY-SA 3.0 [54] | share-alike |
| CVAT | MIT; SAM 2 features only Online/Enterprise [101] | self-host Community or use local tools |
| X-AnyLabeling | GPL-3.0 [102] | fine for internal use |
| Permissive | MIT/Apache-2.0: Mask2Former/OneFormer/EoMT code, EoMT weights, RF-DETR N–L & Seg, D-FINE, RT-DETR, DEIM, Grounding DINO, MM-GDINO, OWLv2, Florence-2, LLMDet, SAM 1/2/2.1, MobileSAM, EfficientSAM, ByteTrack, BoT-SORT, OC-SORT, Deep OC-SORT, Hybrid-SORT, TrackTrack, UCMCTrack, CAMELTrack, Cutie, XMem, SAMURAI, TrackEval, Label Studio | – |

---

## 12. Open points / not verified

- Aria **Gen 2** eye-gaze accuracy (no published number) → measure (§8.1). RGB rolling-shutter readout time.
- Why the study plans 15 Hz although standard profiles are 10 Hz / 30 Hz [2].
- Official definitions of Vistas "Other Rider", "Wheeled Slow"; how Italian cycle crossings were labelled in Vistas.
- Mapillary Vistas licence text (site JS-rendered; read via search snippet and Dataset Ninja), BDD100K licence (official page unreachable), COCO terms (site JS-rendered), nuImages/Objects365/WoodScape data terms, licences of Aria datasets.
- Inference speed/VRAM of every model at 2016×1512 on our GPUs (no published numbers at that size).
- OneFormer Vistas weights licence and Vistas version; InternImage Mapillary checkpoints' Vistas version and accuracy.
- Objects365 "Scooter" semantics; Argoverse 2 class definitions; nuImages licence.
- Speed of MM-Grounding-DINO / OWLv2 / Florence-2 at our resolution; Cutie, SAMURAI benchmark numbers.
- Cyclist-view datasets (AuRa, PanoCycle360, BikeActions) — found by search, not opened.

### 12.1 Maintenance signal (GitHub API `pushed_at`, read 2026-10-15 [125])

| Repository | Last push | Note |
|---|---|---|
| facebookresearch/Mask2Former | 2024-07-29 | **archived** (read-only) |
| SHI-Labs/OneFormer | 2024-10-03 | |
| tue-mps/eomt | 2026-10-12 | active |
| NVlabs/SegFormer | 2024-08-02 | |
| OpenGVLab/InternImage | 2025-03-25 | |
| open-mmlab/mmsegmentation · mmdetection | 2024-08-13 · 2024-08-21 | low activity since 2024 → prefer not to depend on it at runtime [P] |
| facebookresearch/detectron2 | 2026-09-30 | |
| ultralytics/ultralytics | 2026-10-15 | active (AGPL) |
| mikel-brostrom/boxmot | 2026-10-13 | active (AGPL) |
| roboflow/trackers · roboflow/supervision | 2026-10-15 | active (Apache-2.0 · MIT) |
| hkchengrex/Cutie · XMem · DEVA | 2024-11-08 · 2024-11-15 · 2025-04-26 | |
| yangchris11/samurai | 2025-03-18 | |
| ChaoningZhang/MobileSAM · yformer/EfficientSAM | 2026-05-05 · 2024-12-24 | |
| IDEA-Research/Grounded-SAM-2 | 2025-11-11 | |
| cvat-ai/cvat | 2026-10-15 | active |
| RF-DETR, D-FINE, RT-DETR, GroundingDINO, SAM 2/3, ByteTrack, BoT-SORT, OC-SORT, TrackTrack, YOLOE, YOLO-World | not collected (API rate limit) `[U]` | |

---

## 13. Sources (all read 2026-10-15 unless stated; "seen" = version/date observed)

1. Aria Gen 2 hardware — https://facebookresearch.github.io/projectaria_tools/gen2/technical-specs/device/hardware
2. Aria Gen 2 recording profiles — https://facebookresearch.github.io/projectaria_tools/gen2/technical-specs/device/profile
3. Aria camera intrinsic models (FISHEYE624) — https://facebookresearch.github.io/projectaria_tools/gen2/technical-specs/device/calibration_insights/camera_intrinsics_models
4. projectaria_tools image utilities (`get_linear_camera_calibration`, `distort_by_calibration`) — https://facebookresearch.github.io/projectaria_tools/docs/data_utilities/advanced_code_snippets/image_utilities
5. Project Aria paper (Gen 1; 1.5° median gaze error after calibration; RGB rolling shutter) — https://arxiv.org/abs/2308.13561 (read at https://ar5iv.labs.arxiv.org/html/2308.13561)
6. MPS eye gaze (Gen 1) — https://facebookresearch.github.io/projectaria_tools/docs/data_formats/mps/mps_eye_gaze
7. Meta blog "Inside Aria Gen 2" — https://ai.meta.com/blog/aria-gen-2-research-glasses-under-the-hood-reality-labs/
8. Aria Gen 2 MPS benchmarks — https://facebookresearch.github.io/projectaria_tools/gen2/technical-specs/mps/benchmarks/performance
9. Aria Gen 2 Pilot Dataset (arXiv 2510.16134v1, 2025-10-17) — https://arxiv.org/html/2510.16134
10. Mask2Former repository (archived 2025-01-01) — https://github.com/facebookresearch/Mask2Former
11. Mask2Former MODEL_ZOO (results; weights CC BY-NC 4.0) — https://github.com/facebookresearch/Mask2Former/blob/main/MODEL_ZOO.md
12. Mask2Former Vistas registration (v1.2 list) — https://github.com/facebookresearch/Mask2Former/blob/main/mask2former/data/datasets/register_mapillary_vistas.py
13. HF `facebook/mask2former-swin-large-mapillary-vistas-semantic` (seen lastModified 2023-09-11) — https://huggingface.co/facebook/mask2former-swin-large-mapillary-vistas-semantic
14. HF `facebook/mask2former-swin-large-mapillary-vistas-panoptic` (2023-09-07) — https://huggingface.co/facebook/mask2former-swin-large-mapillary-vistas-panoptic
15. mmsegmentation Mask2Former README (Cityscapes FPS on A100) — https://github.com/open-mmlab/mmsegmentation/blob/main/configs/mask2former/README.md
16. OneFormer repository — https://github.com/SHI-Labs/OneFormer
17. HF `shi-labs/oneformer_cityscapes_swin_large` (MIT tag, 2023-01-20) — https://huggingface.co/shi-labs/oneformer_cityscapes_swin_large
18. SegFormer repository (licence statement) — https://github.com/NVlabs/SegFormer
19. SegFormer paper — https://arxiv.org/abs/2105.15203
20. mmsegmentation SegFormer README (Cityscapes FPS on V100) — https://github.com/open-mmlab/mmsegmentation/blob/main/configs/segformer/README.md
21. HF `nvidia/segformer-b5-finetuned-cityscapes-1024-1024` (2022-08-09) — https://huggingface.co/nvidia/segformer-b5-finetuned-cityscapes-1024-1024
22. EoMT repository — https://github.com/tue-mps/eomt
23. EoMT DINOv2 model zoo — https://github.com/tue-mps/eomt/blob/master/model_zoo/dinov2.md
24. EoMT DINOv3 model zoo — https://github.com/tue-mps/eomt/blob/master/model_zoo/dinov3.md
25. EoMT paper (CVPR 2025) — https://arxiv.org/abs/2503.19108
26. HF `tue-mps/cityscapes_semantic_eomt_large_1024` (MIT, 2025-09-18) — https://huggingface.co/tue-mps/cityscapes_semantic_eomt_large_1024
27. DINOv3 repository — https://github.com/facebookresearch/dinov3
28. DINOv3 Licence — https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md
29. DINOv3 paper (arXiv 2508.10104v1) — https://arxiv.org/html/2508.10104
30. HF `facebook/dinov3-vitl16-pretrain-lvd1689m` (gated manual) — https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m
31. HF `facebook/dinov2-large` (Apache-2.0) — https://huggingface.co/facebook/dinov2-large
32. InternImage repository — https://github.com/OpenGVLab/InternImage
33. InternImage segmentation README — https://github.com/OpenGVLab/InternImage/tree/master/segmentation
34. ViT-Adapter segmentation — https://github.com/czczup/ViT-Adapter/tree/main/segmentation ; licence (Apache-2.0) https://github.com/czczup/ViT-Adapter/blob/main/LICENSE.md
35. mmsegmentation Mapillary v1/v2 class lists — https://github.com/open-mmlab/mmsegmentation/blob/main/mmseg/datasets/mapillary.py
36. Neuhold et al., Mapillary Vistas, ICCV 2017 (25 k images, 66 classes, cameras incl. head-mounted; ~94 min/image) — https://openaccess.thecvf.com/content_ICCV_2017/papers/Neuhold_The_Mapillary_Vistas_ICCV_2017_paper.pdf
37. Mapillary Vistas page (CC BY-NC-SA, Research Use License, confidentiality; JS-rendered, terms seen via search snippet) — https://www.mapillary.com/dataset/vistas `[S]`
38. Dataset Ninja, Mapillary Vistas (CC BY-NC-SA 4.0) — https://datasetninja.com/mapillary-vistas-dataset `[S]`
39. Cityscapes licence — https://www.cityscapes-dataset.com/license/
40. Cityscapes dataset overview — https://www.cityscapes-dataset.com/dataset-overview/
41. Cityscapes class definitions (mirror) — https://app.segments.ai/segments/cityscapes `[S]`
42. Cordts et al., Cityscapes (> 1.5 h per image) — https://arxiv.org/abs/1604.01685
43. Papers with Code shutdown — https://www.codesota.com/papers-with-code/shutdown ; https://hyper.ai/en/news/42900 `[S]`
44. Ultralytics YOLO26 docs — https://docs.ultralytics.com/models/yolo26/
45. Ultralytics YOLO12 docs — https://docs.ultralytics.com/models/yolo12/
46. Ultralytics licensing — https://www.ultralytics.com/license
47. Ultralytics repository (AGPL-3.0) — https://github.com/ultralytics/ultralytics
48. RF-DETR repository (tables, per-size licences) — https://github.com/roboflow/rf-detr
49. RF-DETR paper (ICLR 2026; DINOv2 backbone) — https://arxiv.org/abs/2511.09554 ; https://arxiv.org/html/2511.09554v2
50. D-FINE repository — https://github.com/Peterande/D-FINE
51. RT-DETR / RT-DETRv2 repository — https://github.com/lyuwenyu/RT-DETR
52. DEIM repository and LICENSE (Apache) — https://github.com/Intellindust-AI-Lab/DEIM
53. DEIMv2 repository and LICENSE.md (non-commercial) — https://github.com/Intellindust-AI-Lab/DEIMv2 ; https://github.com/Intellindust-AI-Lab/DEIMv2/blob/main/LICENSE.md
54. Detectron2 MODEL_ZOO (weights CC BY-SA 3.0) — https://github.com/facebookresearch/detectron2/blob/main/MODEL_ZOO.md
55. Grounding DINO repository — https://github.com/IDEA-Research/GroundingDINO
56. MM-Grounding-DINO configs/README — https://github.com/open-mmlab/mmdetection/tree/main/configs/mm_grounding_dino
57. HF `openmmlab-community/mm_grounding_dino_tiny_o365v1_goldg_v3det` (Apache-2.0, 2025-07-23) — https://huggingface.co/openmmlab-community/mm_grounding_dino_tiny_o365v1_goldg_v3det
58. OWL-ViT / OWLv2 (scenic) — https://github.com/google-research/scenic/tree/main/scenic/projects/owl_vit
59. YOLO-World repository — https://github.com/AILab-CVC/YOLO-World
60. YOLOE repository — https://github.com/THU-MIG/yoloe
61. Florence-2-large model card — https://huggingface.co/microsoft/Florence-2-large
62. LLMDet — https://huggingface.co/iSEE-Laboratory/llmdet_large ; https://arxiv.org/abs/2501.18954 `[S]` for numbers
63. SAM 3 repository (SAM 3.1 news 2026-03-27; benchmarks) — https://github.com/facebookresearch/sam3
64. SAM License — https://github.com/facebookresearch/sam3/blob/main/LICENSE
65. SAM 3 paper (arXiv 2511.16719v2, 2026-03-28; 30 ms/image on H200; video scaling) — https://arxiv.org/abs/2511.16719
66. HF `facebook/sam3` (gated) — https://huggingface.co/facebook/sam3
67. COCO class list — https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml
68. LVIS v1 categories — https://github.com/facebookresearch/detectron2/blob/main/detectron2/data/datasets/lvis_v1_categories.py
69. Objects365 class list — https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/Objects365.yaml
70. Open Images V7 class list — https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/open-images-v7.yaml
71. V3Det categories and licence — https://github.com/V3Det/V3Det/blob/main/category_name_13204_v3det_2023_v1.txt ; https://github.com/V3Det/V3Det
72. nuScenes annotator instructions (personal mobility) — https://github.com/nutonomy/nuscenes-devkit/blob/master/docs/instructions_nuscenes.md
73. nuImages annotator instructions — https://github.com/nutonomy/nuscenes-devkit/blob/master/docs/instructions_nuimages.md
74. Argoverse 2 categories — https://github.com/argoverse/av2-api/blob/main/src/av2/datasets/sensor/constants.py
75. Objects365 licence label — https://hyper.ai/en/datasets/17725 `[S]`
76. ByteTrack — https://github.com/ifzhang/ByteTrack
77. BoT-SORT — https://github.com/NirAharon/BoT-SORT
78. OC-SORT — https://github.com/noahcao/OC_SORT
79. TrackTrack paper, CVPR 2025 (Tables 1–3 incl. comparators) — https://openaccess.thecvf.com/content/CVPR2025/papers/Shim_Focusing_on_Tracks_for_Online_Multi-Object_Tracking_CVPR_2025_paper.pdf ; code (MIT) https://github.com/kamkyu94/TrackTrack
80. BoxMOT (v12.0.0) — https://github.com/mikel-brostrom/boxmot
81. DanceTrack — https://github.com/DanceTrack/DanceTrack
82. StrongSORT (GPL-3.0) — https://github.com/dyhBUPT/StrongSORT
83. Deep OC-SORT (MIT) — https://github.com/GerardMaggiolino/Deep-OC-SORT
84. Hybrid-SORT (MIT) — https://github.com/ymzis69/HybridSORT
85. UCMCTrack — https://github.com/corfyi/UCMCTrack
86. CAMELTrack — https://arxiv.org/abs/2505.01257 ; https://github.com/TrackingLaboratory/CAMELTrack
87. SR-Track, AAAI 2024 — https://ojs.aaai.org/index.php/AAAI/article/view/28115
88. ColTrack, ICCV 2023 — https://arxiv.org/abs/2308.05911 `[S]`
89. EgoTracks — https://arxiv.org/abs/2301.03213
90. SAM 2 repository — https://github.com/facebookresearch/sam2
91. SAM 2 paper (v2, Appendix C limitations) — https://arxiv.org/abs/2408.00714
92. SAMURAI — https://github.com/yangchris11/samurai
93. Cutie — https://github.com/hkchengrex/Cutie
94. XMem — https://github.com/hkchengrex/XMem
95. DEVA (LICENSE.md: CC BY-NC-SA 4.0) — https://github.com/hkchengrex/Tracking-Anything-with-DEVA
96. Segment Anything (SAM 1) — https://github.com/facebookresearch/segment-anything
97. MobileSAM — https://github.com/ChaoningZhang/MobileSAM
98. EfficientSAM — https://github.com/yformer/EfficientSAM
99. Grounded-SAM-2 — https://github.com/IDEA-Research/Grounded-SAM-2
100. TrackEval — https://github.com/JonathonLuiten/TrackEval
101. CVAT (MIT) — https://github.com/cvat-ai/cvat ; AI models by edition — https://docs.cvat.ai/docs/annotation/auto-annotation/ai-models/ ; SAM 2 tracker — https://docs.cvat.ai/docs/annotation/auto-annotation/segment-anything-2-tracker/
102. X-AnyLabeling (GPL-3.0) — https://github.com/CVHub520/X-AnyLabeling
103. Label Studio (Apache-2.0) — https://github.com/HumanSignal/label-studio
104. WoodScape — https://github.com/valeoai/WoodScape
105. KITTI-360 — https://www.cvlibs.net/datasets/kitti-360/
106. BDD100K terms (official https://doc.bdd100k.com/license.html unreachable; mirror) — https://huggingface.co/datasets/dgural/bdd100k `[S]`
107. ADE20K terms — https://ade20k.csail.mit.edu/terms/
108. Ego4D — https://arxiv.org/abs/2110.07058 ; https://ego4d-data.org/docs/start-here/
109. Aria Digital Twin — https://arxiv.org/abs/2306.06362
110. Nymeria — https://arxiv.org/abs/2406.09905
111. Aria Everyday Activities — https://arxiv.org/abs/2402.13349
112. Project Aria datasets — https://www.projectaria.com/datasets/
113. RectConv (fisheye without retraining) — https://arxiv.org/abs/2404.08187
114. Distortion Extenders (perspective → fisheye, 2026-08-28) — https://arxiv.org/abs/2608.27860
115. Kegalle et al., "Watch Out! E-scooter Coming Through!", Proc. ACM IMWUT 9(1), 2025 — https://arxiv.org/abs/2502.16755 (local copy `paper/2502.16755v1.pdf`, §3.6) ; https://dl.acm.org/doi/10.1145/3712284
116. Apurv et al., Detection of E-scooter Riders in Naturalistic Scenes — https://arxiv.org/abs/2111.14060
117. Wolf et al. 2018, cGOM, J. Eye Movement Research — https://pmc.ncbi.nlm.nih.gov/articles/PMC7909988/
118. Hooge et al. 2026, "The fundamentals of eye tracking part 6: Working with areas of interest", Behavior Research Methods — https://pmc.ncbi.nlm.nih.gov/articles/PMC12913287/
119. Orquin, Ashby & Clarke 2016 (AOI as signal detection) — https://doi.org/10.1002/bdm.1867 (not read)
120. DPR 495/1992 art. 146 (cycle crossings) quoted in — https://www.comune.novara.it/it/amministrazione/consiglio-comunale/mozioni/pdf/750_Oggetto.pdf `[S]` ; Udine guide — https://www.comune.udine.it/ocmultibinary/download/10119/138218/1/386091bf7bae83215d4b0a6f115230c4.pdf/file/attraversamenti_ciclabili_3.pdf
121. Lall & Liu, Eyes on Target: gaze-aware detection — https://arxiv.org/abs/2511.01237
122. Cyclist-view datasets (search results, not opened) — https://link.springer.com/article/10.1007/s41315-025-00502-x ; https://www.nature.com/articles/s41597-026-07128-z ; https://arxiv.org/abs/2601.10521 ; https://arxiv.org/abs/2510.25901 `[U]`
123. (reserved)
124. Hugging Face model API metadata (licence tags, lastModified, parameter counts, gating) — `https://huggingface.co/api/models/<model-id>`
125. GitHub repository API metadata (SPDX licence, archived flag) — `https://api.github.com/repos/<owner>/<repo>` (e.g. roboflow/trackers Apache-2.0, facebookresearch/segment-anything Apache-2.0, facebookresearch/detectron2 Apache-2.0)
