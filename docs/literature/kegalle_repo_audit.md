# Kegalle et al. (2025) — public repository: audit, independent re-analysis, and how it maps to our Aria Gen 2 study

> Full audit compiled on 2026-10-15. Summary and consequences: [kegalle_replication.md](kegalle_replication.md); scripts: replication/kegalle2025/.


Prepared 2026-10-15 for the AriaGenEScooterVsBike project. Paper: Kegalle, Hettiachchi, Chan,
Sanderson, Salim (2025), "Watch Out! E-scooter Coming Through!: Multimodal Sensing of Mixed Traffic
Use and Conflicts Through Riders' Ego-centric Views", *Proc. ACM IMWUT* 9(1), DOI 10.1145/3712284
(arXiv 2502.16755). Companion paper: Kegalle et al. (2024), *AHs '24*, DOI 10.1145/3652920.3653056.
Page numbers refer to the arXiv PDF (pages numbered 217:1 to 217:23).

Paths used below:
- clone: `<workdir>/ext/kegalle_repo` (untrusted; nothing was run from inside it)
- our scripts: `<workdir>/kegalle_replication/` (outputs in `<workdir>/kegalle_replication/outputs/`)
- isolated environment: `<workdir>/venvs/kegalle` (uv venv, Python 3.12; numpy 2.5.4, pandas 3.0.6,
  scipy 1.18.1, python-calamine 0.8.3, openpyxl 3.1.5; plus ruptures 1.1.10, statsmodels 0.15.0
  and matplotlib 3.11.2, used only for verification and for the harness)
- `S=<workdir>`

---------------------------------------------------------------------------------------------------

## 0. Main findings

1. **There is no licence.** The repository has no LICENSE file, and the GitHub API reports
   `license: null`, so default copyright applies (all rights reserved). The README only asks users
   of the data or code to cite the paper. The paper itself is CC BY 4.0.
2. **What is public.** Tobii Pro Lab exports for 14 riders (xlsx, 572 MB) and Garmin 1 Hz exports
   for 19 riders (CSV with GPS). There is also a hand-typed segment time sheet and a YOLO
   encounter-count sheet for 17 riders. **Videos, AOI annotations and demographics are not
   public**, and no data-access procedure is described.
3. **The notebooks are libraries of functions, never executed, and partly broken.** They contain
   no calls and no stored outputs. Of the 15 non-video functions, 6 raise errors on first call
   (both fixation summaries and all four gaze/acc dispersion functions):
   `os.listdir` called with 3 arguments, an undefined `out_file`, an undefined
   `participant_number`, and the removed `DataFrame.append`. The CSV reader silently shifts every
   column of the 2024 speed files (P21–P30), and the gaze code expects CSV column names that the
   2024 exports do not use. Fixation detection is not in the code at all: it is Tobii Pro Lab's
   I-VT (Attention) filter. Statistics (ANOVA, t-tests, Tukey) and correlations are not in the
   code either.
4. **Most of the quantitative results can be reproduced with our own code.** We wrote clean-room
   scripts k00–k07 and re-ran them on the public data. Agreement is close for:
   - Table 2 speed: cycle lane min/max identical; means within 0.12 km/h; RM-ANOVA F 9.35 vs 9.95.
   - Table 3 fixation duration: within 0.1–1.6 ms; F 22.4 vs 23.3.
   - Table 3 fixations/km: within 2/km; F 9.7 vs 10.5.
   - Table 3 "gaze dispersion" and "acc. dispersion": within 0.02.
   - Table 4 encounters/km for the shared path and the cycle lane: identical to 0.3/km.
   - Fig. 7 correlations for fixations: identical to ±0.01, but n = 13 and none is significant.
   - Speed change points per km: 7.47 / 3.98 / 10.04 (total 373) vs 7.9 / 4.3 / 10.2 (total 371),
     using a penalty fitted post hoc (see point 6).
5. **The two "dispersion" metrics are not what the paper says they are.**
   - The paper describes an SD-based dispersion following Wintersberger et al. (p. 9). The code
     instead takes the mean distance of min–max-normalised samples from the corner of their own
     bounding box.
   - That value sits near 0.71 for 2-D data and 0.87 for 3-D data by construction, which is
     exactly the range of Table 3 (0.61–0.66 and 0.83–0.88).
   - The unit "[m/s²]" in Table 3 is therefore wrong (the values are dimensionless). The metric
     is close to insensitive to head-movement amplitude.
   - The real SD of the accelerometer differs strongly between segments (RM F = 16.0,
     p = 5e-5), whereas the paper reports no difference.
6. **The change-point "AIC" selection is degenerate.**
   - The penalty grid (`penalty_range`, `num_penalties`) is not published.
   - The coded AIC drops the RSS of the last segment, so zero change points always scores
     AIC = 2, which beats every other solution. In practice the result equals PELT run at roughly
     the upper end of the grid.
   - The published counts are matched only post hoc, with an effective penalty of about 30
     (km/h)², per segment, zeros kept, per km.
7. **The segment lengths in Fig. 3 appear swapped.** The GPS traces put the cycle lane at about
   0.74 km and the roadway at about 0.64 km. The paper's own per-km numbers (Tables 3 and 4) are
   reproduced only with cycle lane = 0.74 km and roadway = 0.65 km; Fig. 3 prints 0.65 and 0.74.
8. **Data defects.**
   - In `Encounter Counts.xlsx` the "Route Segment 3" sheet is an exact copy of
     "Route Segment 2", so the roadway encounters (Table 4, Fig. 7 segment 3) cannot be
     reproduced.
   - For P4 the hand-typed Garmin times fall about 12 min outside the speed file; we used GPS
     boundary crossings instead.
   - P13's Tobii and Garmin segment times disagree by 6 min.
   - P16 and P25 exports contain no accelerometer data.
9. **Statistical issues.**
   - After within-subject ANOVAs the gaze post-hoc tests are between-subject Tukey HSD tests. This
     explains "significant ANOVA, no significant pair" for fixation duration: paired t-tests give
     p ≤ 0.024 for all pairs.
   - The Fig. 7 correlations rest on 11–16 riders and none reaches p < 0.05 (0 of 40), yet they
     are interpreted as "strong".
10. **What this means for us.**
    - Speed level and change-point frequency per segment are comparable with ours if we use their
      exact definitions (1 Hz GNSS speed, zeros, per km, PELT l2 with a fixed, reported penalty).
    - Fixation metrics are only loosely comparable: Tobii 50 Hz with the I-VT Attention preset vs
      Aria 30 Hz with our I-VT.
    - Their two dispersion metrics should be reproduced only for compatibility and never
      interpreted. We should use angular metrics instead.
    - We computed angular reference values from their raw gaze-direction vectors and gyroscope
      (k06; §8.3). These are the most useful cross-study anchors.

---------------------------------------------------------------------------------------------------

## 1. Repository facts

| Item | Value |
|---|---|
| URL | https://github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis |
| Clone | `git clone --depth 50` (the whole history is 23 commits, so the clone is complete: `is-shallow = false`) |
| HEAD commit | `ed5c22195ecb0d3468fe67e8da5cc9ca9a1e9cb3`, 2025-03-06 13:03:26 +1100, "Merge pull request #2 from danula/patch-1" |
| Created / last push | 2024-07-06 / 2025-03-06 (GitHub API); 2 stars, 2 forks |
| Size | working tree 1.2 GB, of which `.git` 609 MB; data 574 MB |
| Licence | **None.** No LICENSE / COPYING file in any commit; GitHub API `"license": null`, `/license` endpoint returns 404. There is no copyright line or licence text to quote. |
| Citation instructions | README "Citation" section (README.md:56-78), quoted below; no CITATION.cff |
| Paper licence | "This work is licensed under a Creative Commons Attribution 4.0 International License. © 2025 Copyright held by the owner/author(s)." (paper p. 1); Crossref also lists CC BY 4.0 |
| Article number | The arXiv PDF says "Article 217"; the README BibTeX says `articleno = {8}`; Crossref gives vol. 9, issue 1, pages 1–23 with no article number. Check against the ACM DL before citing. |

README citation text (README.md:57-59), verbatim:

> If you use this data or code in your research, please cite our paper:
> Hiruni Nuwanthika Kegalle, Danula Hettiachchi, Jeffrey Chan, Mark Sanderson, and Flora D. Salim. 2025. Watch Out! E-scooter Coming Through!: Multimodal Sensing of Mixed Traffic Use and Conflicts Through Riders' Ego-centric Views. Proc. ACM Interact. Mob. Wearable Ubiquitous Technol. 9, 1, Article 8 (March 2025), 23 pages. https://doi.org/10.1145/3712284

The README also contains a BibTeX entry (README.md:61-78) and acknowledgements: ARC Centre of
Excellence for Automated Decision-Making and Society CE200100005, and Lime Network Pty Ltd.

**Practical implication.** With no licence, we may read and cite the work, and describe and
re-analyse the data for research. We should not redistribute their data or code, for example
inside our repository or as supplementary material. Any figure or table derived from their data
must cite the paper.

If we want to publish comparisons that rely on their per-participant data, we should ask the
authors for permission or a licence. Contact details are on p. 1 of the paper.

None of our scripts copies their code. They are written from the paper and from our reading of the
notebooks. The only place their code runs is the test harness (§6), which reads the notebooks
directly from the clone at run time.

## 2. Repository structure

```
README.md                                              5.6 kB
figures/workflow.png                                   93 kB   (= Fig. 4 of the paper)
.gitattributes                                         "* text=auto"
average_acc_dispersion.ipynb                           2.4 kB
average_fixation_count __fixation_duration.ipynb       5.4 kB
average_gaze_dispersion.ipynb                          2.3 kB
speed_data_processing.ipynb                            9.6 kB
object_tracking_of_video.ipynb                         4.1 kB
yolov8_region_counter (updated).ipynb                  8.6 kB
Object count correction method.ipynb                   1.9 kB
fixation_screen_shots_from_video.ipynb                 2.4 kB
.ipynb_checkpoints/  3 checkpoint notebooks (one contains a worked example with outputs, see §4.8)
data/TimeMapping_BikeComputer_EyeTracker.xlsx          15 kB
data/Encounter Counts.xlsx                             12 kB
data/Data/Gaze data/P{3,4,7,10,11,13,14,15,16,17,23,25,28,30}.xlsx   14 files, 571.6 MB
data/Data/Speed data/P{3,4,7,9,10,11,12,14,15,16,17,21,...,30}_2.csv 19 files, 2.37 MB
```

- All notebooks have kernel metadata "Python 3 (ipykernel)" 3.7.13.
- All analysis notebooks have `execution_count` null for the function cells: they were saved
  without being run and contain no outputs. The only exception is the checkpoint copy of
  "Object count correction".
- There are no `.py` files. The README refers to `average_acc_dispersion.py` and similar names,
  but only `.ipynb` files exist.
- There is no requirements file and no environment specification.

### History worth knowing

- **bb0cf01** (2024-10-18) added the data: 20 gaze files and 22 speed files.
- **f16da5d** (2024-10-30, "Removed below threshold gaze data") deleted:
  - gaze files P6, P12, P21, P22, P24 and P29;
  - speed files P6_2, P13_2 and P26_2.
- The deleted files are still in the git history. We extracted the 6 gaze files, read-only and
  into a separate directory (`<workdir>/ext/kegalle_removed_gaze`), only to check the stated 75% rule
  (§5.2). They are not used in any analysis.

## 3. README content

- **Dataset description.**
  - Gaze data: "Collected using Tobii Pro 3 Glasses".
  - Speed data: "Recorded continuously with a Garmin Edge 130 Plus bike computer".
  - A sheet with segment start and end times for each rider.
  - Route: pedestrian-shared path, then cycle lane, then roadway.
- **Contents.** ".xlsx worksheets containing gaze data, .csv files with speed per second, and start
  and end timestamps for each route segment"; "Python scripts for pre processing and feature
  calculation"; "Detailed documentation". There is no documentation beyond the README.
- **Workflow (README:34-54).**
  1. Gaze: segment with the TimeMapping sheet, then extract fixation data, then select unique
     records; then compute acc dispersion, fixation count/duration and gaze dispersion.
  2. Speed: timezone mapping, then segmentation with the TimeMapping sheet, then change-point
     detection, then plotting, then mapping timestamps to the video.
  3. "Fixation on Video": "We have not included the recorded videos due to privacy concerns";
     extract fixation timestamps and x/y, then save the corresponding frames.
- **Abstract** identical to the paper.
- **There is no data-access or request procedure** in the README or the paper. The paper's only
  statement is "we have made the dataset (excluding collected videos due to privacy concerns) and
  analysis code publicly available" (p. 2).

## 4. File-by-file analysis

References use the form `notebook:cell:line`. Cell indices are 0-based and line numbers 1-based,
as printed by our dump. Every cell is a code cell.

### 4.1 `speed_data_processing.ipynb` — Garmin speed: segmentation and change points

| Ref | What it does |
|---|---|
| :0:1-6 | imports pandas, **ruptures**, numpy, matplotlib, datetime |
| :1 | comments only: "Download fit file / convert to csv / convert to local time". Conversion is outside the code; the CSV header `GOTOES_CSV` shows the FIT files were converted with the GOTOES online converter. |
| :2:2-18 `process_garmin_data(input_csv, output_csv, time_delta)` | reads the CSV; `local_time = timestamp + time_delta hours` (:2:6); keeps `timestamp, local_time, speed`; adds `local_time_part`, the clock time as text. `time_delta` is not given anywhere. Empirically it must be **+16 h** for all 19 files: the GOTOES timestamps are UTC−6, and Melbourne in winter is UTC+10. |
| :4:1-12 `segment_speed_file(input_csv, output_dir, row_ranges)` | cuts segments by **manual 1-based inclusive row ranges**, `df.iloc[start-1:end]` (:4:6). The row ranges themselves are not published; only the hand-typed clock times in TimeMapping are. |
| :6:1-47 `detect_speed_change_points(input_csv, output_csv, penalty_range, num_penalties)` | runs on one segment's speed signal (:6:3). `algo = rpt.Pelt(model="l2").fit(signal)` (:6:12) uses the ruptures defaults `min_size=2, jump=5`. `penalties = np.linspace(*penalty_range, num_penalties)` (:6:15) — **values not published**. For each penalty: `result = algo.predict(pen)`, `num_params = len(result)` (this includes the final index n), and RSS summed over `result[:-1]` (:6:27), i.e. **the last segment is omitted**. "AIC" = `2k − 2 log(exp(−RSS/(2n)))` = `2k + RSS/n` (:6:7-9); the minimum is kept with strict `<` (:6:35). Change-point times are taken from `local_time_part[i-1]` (:6:41). |
| :8:1-37 | plots speed with vertical lines at the change points (for visual validation) |
| :10:1-31 | converts change-point clock times to video times using one manually chosen pair (`csv_time_example`, `video_time_example`). Used to look up the GoPro footage that explains each speed change (AHs '24 §3.3). |

### 4.2 `average_fixation_count __fixation_duration.ipynb` — fixations

| Ref | What it does / problems |
|---|---|
| :1:1-4 | converts minutes and seconds to ms |
| :2:2-9 `extract_fixation_duration_data(directory_path, out_file)` | reads **`.csv`** files (the public data are `.xlsx`) and keeps `Recording timestamp [ms]`, `Eye movement type`, `Gaze event duration [ms]`, `Fixation point X/Y [MCS px]`. Bug: `participant_number = filename[1:-5]` (:2:5) assumes a 5-character extension, so "P16.csv" becomes "1". |
| :3:2-7 `segment_fixation_data(in_file, start_min, start_sec, end_min, end_sec, out)` | keeps an inclusive window on `Recording timestamp [ms]` (:3:6). Takes minutes and seconds, while TimeMapping gives ms. |
| :4:3-12 `select_unique_records` | `groupby(['Eye movement type','Gaze event duration [ms]','Fixation point X [MCS px]','Fixation point Y [MCS px]']).first()` (:4:10). Sample-level rows are collapsed into events. Because groupby drops NaN keys, only rows that have a fixation point (fixations) survive. |
| :5:2-12 `calculate_avg_fixation_count` | fixation count = `len(df)` of the unique records (:5:9). **Bugs:** `os.listdir(directory_path, seg_number, out_file)` raises TypeError (:5:4); `participant_number` is undefined (:5:11); `DataFrame.append` was removed in pandas 2.0. No division by distance: "per km" exists only in the paper. |
| :6:2-13 `calculate_avg_fixation_duration` | mean of `Gaze event duration [ms]` over the unique fixations (:6:9). Same three bugs. |

There is **no fixation algorithm in the code**. Fixations come from the Tobii Pro Lab export, whose
column `Recording Fixation filter name` reads `Tobii I-VT (Attention)` in every file (§5.2).

### 4.3 `average_gaze_dispersion.ipynb` — "gaze dispersion"

| Ref | What it does / problems |
|---|---|
| :1:1-2 | `min_max_normalize(s) = (s − min s)/(max s − min s)` |
| :2:1-6 `calculate_euclidean_distance(in_file)` | `pd.read_csv(in_file, out_file)` raises NameError, because `out_file` is not a parameter (:2:2). x' and y' are min–max-normalised `Gaze point X/Y [MCS px]` (:2:3-4). `Euclidean Distance = sqrt(x'^2 + y'^2)` (:2:5). |
| :3:1-10 `avg_gaze_dispersion` | the per-segment mean of `Euclidean Distance` (:3:8). Same `listdir`, `participant_number` and `append` bugs. |

**Formula as coded:** $D_{gaze} = \frac{1}{N}\sum_i \sqrt{\tilde x_i^2 + \tilde y_i^2}$, with
$\tilde x = (x - \min x)/(\max x - \min x)$ taken over the file being processed (a segment).

This is the mean distance from the (min x, min y) corner, **not a dispersion**. For a symmetric
cloud centred in its bounding box it is about $\sqrt{0.5^2+0.5^2}=0.71$.

### 4.4 `average_acc_dispersion.ipynb` — "head movements"

This notebook is identical to §4.3, with `Accelerometer X/Y/Z [m/s²]` and a 3-D norm (:2:3-6).
For centred data the value is about $\sqrt{3}\cdot 0.5 = 0.87$. It has the same bugs.

The signal is the linear accelerometer of the glasses: gravity plus head translation plus
vibration from the vehicle. It is not head rotation.

### 4.5 `object_tracking_of_video.ipynb` — video pre-processing for YOLO

| Ref | What it does |
|---|---|
| :0:1-4 | imports `cv2` and `ultralytics.YOLO`, `torch`, `numpy` |
| :1:1 | `YOLO('yolov8x.pt')`, the largest YOLOv8 model |
| :3:1-47 | writes a segment of the video (start and end in minutes and seconds) **centre-cropped** to `crop_width_percentage` of the width (value not given) |
| :4:1-2 | `!git clone ultralytics` and `cd examples/YOLOv8-Region-Counter` |
| :5:2 | commented command: `yolov8_region_counter.py --source … --weights yolov8x.pt --save-img --classes <class_numbers>` |

### 4.6 `yolov8_region_counter (updated).ipynb` — encounter counting

This is a modified copy of the Ultralytics "YOLOv8-Region-Counter" example. Its upstream licence is
AGPL-3.0; that matters only if one reuses this file.

| Ref | What it does / problems |
|---|---|
| :1:17-29 | static centre mask `create_dynamic_polygon_mask(width_percentage=0.3, height_percentage=0.9)`: only the central 30% of the width and 90% of the height is analysed |
| :1:32-42 | `run()` defaults to `weights="yolov8n.pt"` and `device="cpu"`; the paper and :1:1 of §4.5 use yolov8x |
| :1:56-60 | uses `imageio.get_reader`, but **`imageio` is never imported** (NameError) |
| :1:65-69, :1:116-118 | `frame_skip_count = 5`, but the skip is commented out, so the printed progress percentage is wrong by ×5 |
| :1:80 | `model.track(masked_frame, persist=True, classes=classes)`: Ultralytics' default tracker (BoT-SORT), default confidence and IoU thresholds |
| :1:100-105 | the counts are **numbers of unique track IDs** for COCO class 0 (person), 1 (bicycle) and 2 (car). Trucks, buses and motorcycles are not counted. ID switches inflate the counts. |
| :1:107-110 | a "moving car" filter is commented out, so **parked cars count as "motor vehicle encounters"** |

### 4.7 `Object count correction method.ipynb` — manual correction of the counts

`correct_object_count(seg_no, persons, bicycles, cars, bike_marks_seg2, bike_marks_seg3)` (:0:1-20):

- **Segment 1:** persons = persons − bicycles, because a cyclist is detected as both a person and
  a bicycle.
- **Segments 2 and 3:** if bicycles > the number of painted bicycle symbols on the lane
  (`bike_marks_seg2`, `bike_marks_seg3`), then bicycles = bicycles − marks and
  persons = persons − bicycles; otherwise bicycles = 0.

The checkpoint copy (`.ipynb_checkpoints/Object count correction-checkpoint.ipynb`) shows a worked
example with outputs: marks = 23 on the cycle lane and 11 on the roadway; raw counts (50, 5, 104)
become (45, 5, 104). The "encounters" are therefore YOLO track counts with heuristic corrections,
**not** interactions or conflicts.

### 4.8 `fixation_screen_shots_from_video.ipynb` — frames for manual AOI coding

`load_data` (:1:1-15) reads the fixation timestamps and `Fixation point X/Y`. `extract_frames_with_dot`
(:2:1-20) takes a frame with `moviepy` `get_frame(t)` at each fixation and draws a red dot. This is
the input to the **manual AOI annotation** (Table 5, Fig. 8).

The paper's 70-px OpenCV crop and Faster R-CNN step (p. 9) is **not in the repository**, and
neither are the AOI labels.

### 4.9 `figures/workflow.png`

Identical to Fig. 4. Note that "Object Detection" hangs under **Tobii Pro Glasses**, so encounters
were counted on the Tobii scene video (25 fps, 1920×1080). The companion AHs '24 paper (Fig. 2)
instead attributes "number of road user encounters" to the **Insta360** camera.

## 5. Method reconstruction and code–paper mapping

### 5.1 Topic-by-topic

| Topic | Paper (section, page) | Code | Reconstruction and discrepancies |
|---|---|---|---|
| Eye tracker and export | §3.1 p. 5: Tobii Pro Glasses 3, scene video 25 fps. §3.6.1 p. 9: data extracted with Tobii Pro Lab. | §4.2–4.4 column names | Tobii Pro Lab "Data export". Gaze 50 Hz (median Δt 20 ms in all files). Magnetometer about 10 Hz. Accelerometer and gyroscope median Δt 8 ms, ≈118 samples/s. Coordinates in MCS px of the 1920×1080 scene video; gaze points can fall outside the frame (x up to 2883). The 2023 exports use unit-suffixed headers (`Recording timestamp [ms]`); the 2024 exports (P23, P25, P28, P30) use unit-less headers (`Recording timestamp`). The code hard-codes the former, so it raises KeyError on 2024 files. |
| Fixation detection | p. 9: "Tobii Pro Velocity-Threshold Identification Gaze Filter"; fixation-by-fixation analysis | none (the export's `Eye movement type`) | The export states `Tobii I-VT (Attention)` in all 14 files (and in the 6 removed ones). The preset's parameters are not stated in the paper. Per Tobii Pro Lab documentation (to verify for their software version), the Attention preset uses a 100°/s velocity threshold, against 30°/s for the "Fixation" preset, with gap fill-in, merging of adjacent fixations, and short fixations discarded. Consistent with that, the minimum fixation duration is exactly 60 ms in every file, and 12% of fixations are under 100 ms. |
| Speed source | §3.1 p. 6: Garmin Edge 130 Plus "collected GPS and speed data". §3.6.1 p. 8: "riding speed at one-second intervals … extracted using Garmin Connect … converted to include local timestamps". | §4.1 | FIT converted to GOTOES CSV, `speed` in km/h. No wheel sensor is mentioned, so speed is GNSS-derived. Median ratio of `speed` to Δdistance/Δt × 3.6 is 0.95. The files also carry GPS lat/lon, altitude and temperature. The timestamps are UTC−6 and need +16 h to reach local time; the code's `time_delta` is unspecified. |
| Zero removal | p. 8: "removing stand-still situations (speed = 0 km/h)" | not in the code | We applied it to mean speed. Whether zeros were removed before PELT is unspecified; the paper numbers match better without removal (§7.2). |
| Segmentation (temporal) | §3.5 p. 8; Fig. 3; p. 9 "We annotated the data corresponding to each segment" | manual row ranges (§4.1 :4) and minute/second windows (§4.2 :3) | **Manual.** Boundaries come from the hand-typed `TimeMapping` sheet: Garmin as "(hh)mm.ss" clock strings with inconsistent typing (`(15)8.08`, `(14) 46.9`, `(13)55:56`, `(11) 44. 23`); Tobii as ms since recording start, rounded to whole seconds. The infrastructure labels are fixed by route position, the same for all riders. See §5.3 for quality checks. |
| Segment lengths | Fig. 3: shared path 1.36 km, cycle lane 0.65 km, roadway 0.74 km | none | GPS distance inside the segments is about 1.35 / 0.74 / 0.64 km (GPS-based boundaries, §7.1). The paper's per-km values are reproduced only with **1.36 / 0.74 / 0.65**, so the cycle-lane and roadway labels in Fig. 3 are swapped. |
| Gaze dispersion | p. 9: "average values for gaze standard deviation based on fixations in the x and y axes … Euclidean distance using normalised pixel values" (after Wintersberger et al. 2022). p. 12: "Euclidean distance from average values for the gaze standard deviation" | §4.3 | **Code ≠ paper.** The code computes the mean of the per-sample norm of min–max-normalised raw gaze points — no SD. Table 3 (0.61–0.66) is reproduced to within 0.02 by the coded metric applied to segment-wise unique fixation points (§7.3). The SD version gives 0.12–0.13. |
| Head movements | p. 9: "standard deviation of accelerometer data, reflecting head movements along x, y and z … Euclidean distance using normalised pixel values" (*sic*). Table 3 unit [m/s²]. | §4.4 | **Code ≠ paper.** The coded min–max mean-norm metric reproduces Table 3 (0.88 / 0.85 / 0.87 vs 0.88 / 0.83 / 0.86), so the values are dimensionless, not m/s². Only 12 of 14 riders have accelerometer data (P16 and P25 do not), which the paper does not report. The SD in m/s² is 2.38 / 2.00 / 2.23 and differs significantly (§7.3). |
| Speed change points | p. 8: PELT [25] "partitioned the speed time series into multiple intervals". AHs '24 §3.3: "optimal penalty using Akaike Information Criterion". §4.1.2 p. 11: 371 change points; means 7.9 / 4.3 / 10.2 "per participant", while the Fig. 5 axis is "per km". | §4.1 :6 | ruptures PELT, l2 cost, `jump=5` (change points can only fall on multiples of 5 s), `min_size=2`, run per segment. The penalty grid is unpublished and the AIC is degenerate (§7.2). The paper's numbers match **per km** values (§7.2), so the text's "per participant" means per participant per km. |
| Infrastructure comparisons | §4.1.1: Shapiro–Wilk, RM-ANOVA, pairwise t-tests. §4.1.3: Shapiro–Wilk, "ANOVA with the individual route segments as within-subject conditions", Tukey HSD; t-tests frequent vs infrequent. §4.1.5: ANOVA plus Tukey on AOIs. | **none** | Reconstructed in k01/k03/k04. The fixation F values match RM-ANOVA, not one-way ANOVA (§7.3). The Tukey HSD p-values match the **between-subjects** Tukey (scipy `tukey_hsd`); for example, fixations/km road vs shared path p = 0.043 (significant, as the paper says) and fixation duration shows no significant pair (as the paper says). No multiple-comparison correction is mentioned for the speed t-tests. |
| Encounters ("interactions") | p. 9-10: YOLO v8.0 [28 = LearnOpenCV tutorial] "extracted the number of pedestrian, cyclist and car encounters"; accuracy checked on 7 random videos: 74.4% / 71.4% / 82.9% | §4.5–4.7; data in `Encounter Counts.xlsx` | YOLOv8x tracking on a centre crop and mask (30% × 90%); unique track IDs; manual correction for cyclists counted as persons and for painted bike symbols; parked cars included. "Encounter" means "tracked object in the central field of view", not an interaction. |
| Conflicts / interactions | §3.6.2 p. 10: thematic analysis of Insta360 and GoPro videos (2 researchers, codebook); §4.2 | **none** | Entirely qualitative. No automatic conflict detection, no TTC or distance measure, no event annotations in the repository. |
| AOIs | p. 9: 70-px region and Faster R-CNN (recall 10.5% pedestrians, 15.1% cars), then manual AOI assignment by 2 researchers | only frame extraction (§4.8) | AOI labels not public, so Table 5 and Fig. 8 cannot be reproduced. |
| Correlations | §4.1.4, Fig. 7 | **none** | The method is unstated. Pearson on the per-participant segment values reproduces Fig. 7 for fixation count and duration to ±0.01 (§7.4). |

### 5.2 Paper-internal and code–paper discrepancies

1. **Speed pairwise tests (p. 10).** The text calls cycle lane vs roadway both significant
   (t = 2.80) and not significant. The non-significant pair must be shared path vs roadway: ours
   gives t = −1.51, p = 0.15.
2. **"Per participant" vs "per km" (§4.1.2 vs Fig. 5).** The numbers are per km (§7.2).
3. **Change points and familiarity.** "Total 371 change points" combined with means 7.9 / 4.3 / 10.2
   and n = 19 is only consistent with per-km means.
4. **Gaze and head dispersion definitions** (paper) vs code (min–max mean-norm). The Table 3 unit
   [m/s²] and "[MCS px]" are wrong for the coded metric, which is dimensionless.
5. **Accelerometer n.** It is 12, not 14 (P16 and P25 have no IMU columns); not reported.
6. **Gaze dispersion input.** The code uses raw `Gaze point X/Y` samples; the paper says
   "fixations". Table 3 matches fixation points better (§7.3).
7. **Post-hoc tests.** Within-subject ANOVAs are followed by between-subject Tukey HSD tests.
8. **"Least head movements" on the cycle lane** (abstract and §5.1) is not supported: the ANOVA on
   their metric is not significant (their own p. 12). The gyroscope (k06) shows the roadway highest,
   while the cycle lane and the shared path do not differ (p = 0.24).
9. **Companion AHs '24 paper.** It says lanes shared with motor vehicles had "the lowest average
   speeds". In the public 2023 subset (11 riders with speed) the shared path is lowest
   (17.46 / 18.46 / 17.66 km/h for shared path / cycle lane / roadway). The AHs paper used 15
   riders; the overlap is unknown.
10. **Where encounters were counted.** Encounter source camera: Tobii in the workflow figure,
    Insta360 in the AHs '24 paper.
11. **Default weights.** The default weights in the region-counter notebook are yolov8n, while the
    paper uses YOLOv8x via `object_tracking_of_video.ipynb:1:1`.
12. **Round used.** Every public file is the **second round** (`Recording name` P*_2, CSV P*_2).
    The paper motivates two rounds (p. 5) but never states that only round 2 was analysed.
13. **Encounters per km.** These also use 0.74 km for the cycle lane, consistent with point 7 of §0.

### 5.3 Quality of the hand-typed segment boundaries (k00, k01)

- **Garmin vs Tobii agreement.** For most riders the two clocks agree within ±4 s. Offsets of
  +8 to +17 s appear for P23 and P30.
- **P13:** the Tobii segments sit 339–404 s earlier than the Garmin times, and the seg-1 durations
  differ (262 vs 327 s). P13's speed file was removed by the authors anyway.
- **P14 seg 1:** the Tobii end is 25.6 s early (a 25 s gap before seg 2).
- **P7 seg 1:** the Tobii end is 9.6 s early.
- **P3 seg 1:** the Tobii start is 18.9 s early.
- **Tobii gaps between seg 1 and seg 2** of 12–25 s for P7, P13, P14 and P22, so some gaze
  samples are never assigned.
- **P4:** the TimeMapping Garmin times (18:08:32–18:16:37) lie outside the P4_2.csv time span
  (17:56:35–18:06:18), an offset of about 712 s, so the authors' row ranges for P4 are
  unrecoverable. We used GPS boundary crossings for P4.
- **P9:** segment 1 starts 3 s before the file begins.
- **Spatial consistency.** Locating each boundary on the GPS trace: the median spread is 8–11 m,
  but 2024 riders (P21, P23, P24, P29, P30) are 40–132 m off, i.e. 10–27 s, so boundaries were
  placed inconsistently.

## 6. Data inventory and what can be executed

### 6.1 Data actually present

| Data | Riders | Format / units | Rates and size | Notes |
|---|---|---|---|---|
| Speed (`Speed data/P*_2.csv`) | 19: P3, 4, 7, 9, 10, 11, 12, 14, 15, 16, 17, 21, 22, 23, 24, 25, 28, 29, 30 | GOTOES CSV, 123 columns; populated: `timestamp` (UTC−6), `position_lat/long` (deg), `altitude` (m), `distance` (m, cumulative), `speed` (km/h), `temperature` (°C), `heart_rate` = 255 (placeholder) | 1 Hz; 534–831 s per file (the whole loop, about 2.95 km); 2.37 MB | 2023-08-13 to 2023-09-02 (P3–P17) and 2024-07-06 to 2024-07-16 (P21–P30). The 2024 files have a trailing extra comma, so `pd.read_csv` without `index_col=False` shifts the columns and `speed` becomes NaN. **GPS traces are included** (start/end at about −37.780, 144.960, Princes Park area, Melbourne). Zero-speed samples: 2–189 per file. |
| Gaze and IMU (`Gaze data/P*.xlsx`) | 14: P3, 4, 7, 10, 11, 13, 14, 15, 16, 17, 23, 25, 28, 30 | Tobii Pro Lab export, sheet "Data", 48–49 columns. Gaze point 2D (MCS px) and 3D (HUCS mm); left and right gaze-direction unit vectors (HUCS); pupil position and diameter; validity; `Eye movement type` / index / duration; fixation point; gyroscope (°/s); accelerometer (m/s²); magnetometer (µT); events (sync port) | gaze 50 Hz; IMU about 118 samples/s; magnetometer about 10 Hz; recordings 593–908 s; 11–60 MB each, 572 MB total; 23,095 fixation events | Recording names P*_2 (round 2); start times local AEST. **P16 and P25: no accelerometer or gyroscope** (11 MB files). Gaze-sample % over the whole recording is 76.0–98.1, all above 75; P3 is at 76.0. |
| Segment times (`TimeMapping_BikeComputer_EyeTracker.xlsx`) | 20 riders (P3, 4, 7, 9, 10–17, 21–25, 28–30); Tobii ms for 18 (not P9, P24) | 3 rows per rider: Garmin "(hh)mm.ss" local strings; Tobii start/end ms | — | Manually typed; inconsistencies in §5.3 |
| Encounters (`Encounter Counts.xlsx`) | 17 (no P4, P9, P24) | 3 sheets × (rider, pedestrians, cycles, "cars "): raw counts per segment, after correction | — | **The "Route Segment 3" sheet is identical to "Route Segment 2"**, so the roadway counts are missing |
| Video, scene frames, AOI labels, demographics, rider frequency, interview data | — | — | — | **Not public** ("privacy concerns"). No data-access procedure. |

**Exclusions check (k00 with the removed files).**

- Whole-recording gaze-sample % of the files the authors removed:
  - P12 62.9%, P21 55.9%, P22 52.4%, P29 63.2% — all below 75%, consistent with the stated rule.
    These are 4 of the 6 riders the paper says were excluded for low gaze rate.
  - P24 97.1%, but its file is `P24_1` (round 1), consistent with an aborted round 2.
  - P6 91.7%, but P6 is absent from the TimeMapping sheet.
- The paper counts 14 + 6 + 3 = 23 riders.

### 6.2 What ran and what did not: original notebooks

The harness is `<workdir>/kegalle_replication/harness_original/run_original_notebooks.py`; its log is
`outputs/original_notebooks_run_log.json`. It runs under Python 3.12, pandas 3.0.6, ruptures
1.1.10, from outside the clone, with `-I`. It execs the notebook cells read from the clone and
calls each function on public data.

| Function | Result |
|---|---|
| `process_garmin_data(P10_2.csv, time_delta=16)` | OK. Local times match TimeMapping (17:00:35 …). |
| `process_garmin_data(P21_2.csv, 16)` | Runs **silently wrong**: `speed` 0/775 non-null, `timestamp` = 1969-12-31 (latitudes read as epoch ns), caused by the column shift. |
| `segment_speed_file(…, row_ranges)` | OK, with row ranges we derived from TimeMapping (P10: (2, 258), (259, 391), (392, 513)). |
| `detect_speed_change_points` | OK. P10 segment 1: grid (1, 30, 100) gives pen 27.07, AIC 23.86, 10 change points; grid (1, 100, 100) gives pen 63, 7 change points; grid (1, 10000, 100) gives **0 change points, AIC = 2.000**, the degenerate case. Our numpy re-implementation returns identical indices, penalties and AIC. |
| `plot_speed_with_vertical_lines`, `get_video_time_df` | OK |
| `extract_fixation_duration_data` | Runs, after we converted xlsx to CSV ourselves. Output file named `P1_fix.csv` instead of P16: bug at :2:5. |
| `segment_fixation_data`, `select_unique_records` | OK. P16 seg 1: 549 unique fixations, mean 476.17 ms, identical to our k03. |
| `calculate_avg_fixation_count` / `_duration` | `TypeError: listdir() takes at most 1 argument (3 given)` (cell 5:4, cell 6:4). Fixing it would next raise `NameError participant_number`, then `AttributeError DataFrame.append` on pandas ≥ 2. |
| `calculate_euclidean_distance` (gaze and acc) | `NameError: name 'out_file' is not defined` (cell 2:2) |
| `avg_gaze_dispersion`, `avg_acc_dispersion` | `TypeError: listdir() …` (cell 3:3) |
| `correct_object_count(2, 4, 18, 94, 23, 11)` | OK; prints (4, 0, 94), as in the checkpoint |
| `object_tracking_of_video`, `yolov8_region_counter`, `fixation_screen_shots_from_video` | Not runnable: `ModuleNotFoundError cv2 / moviepy`. More fundamentally, **no videos are public**. `run()` would also fail with `NameError imageio`. |

### 6.3 Our clean-room scripts

All scripts take `--repo` and `--out`, use numpy, pandas and scipy only, and carry a header with the
paper citation, the repository commit, the licence status and the original file:cell:line
references.

| Script | Reproduces | Notes |
|---|---|---|
| `kegalle_common.py` | helpers: TimeMapping parser, GOTOES reader (`index_col=False`), +16 h offset inference, Tobii column canonicalisation for 2023/2024 headers, unique-fixation de-duplication (as coded and by event index), RM-ANOVA with Greenhouse–Geisser, paired t, Tukey, Shapiro, GPS boundary detection | segment lengths 1.36 / 0.74 / 0.65 km; set `KEGALLE_USE_FIG3_LENGTHS=1` to use the Fig. 3 labels |
| `k00_inventory.py` | inventory (§6.1) | `--extra-gaze` for the removed files |
| `k01_speed.py` | Table 2 and the speed tests | `--segmentation timemapping+gpsfallback` (default) / `timemapping` / `gps`; `--keep-zeros` |
| `k02_speed_changepoints.py` | §4.1.2, Fig. 5 | numpy PELT; `--aic original|fixed|gaussian|none`; `--sweep` |
| `k02b_check_pelt.py` | verification | our PELT vs `ruptures.Pelt(model="l2")`: **684/684 identical** |
| `k03_fixations.py` | Table 3, fixation columns | |
| `k04_dispersion.py` | Table 3, dispersion columns | coded and described variants |
| `k05_encounters_correlations.py` | Table 4, Fig. 7 | |
| `k06_harmonised_gaze_head.py` | **not in the paper**: angle-based, Aria-comparable reference metrics | §8.3 |
| `k07_compare_with_paper.py` | `outputs/k07_paper_vs_ours.csv`, every paper number next to ours | |
| `run_all.sh` | runs everything (≈4 min; the xlsx parse is cached in `outputs/cache/`, 382 MB) | |

## 7. Numerical comparison with the paper

The full table is in `outputs/k07_paper_vs_ours.csv`.

### 7.1 Speed (Table 2, p. 11; tests p. 10). n = 19, zeros removed.

Segmentation for this table: TimeMapping, with GPS boundary crossings for P4.

| Segment | Paper mean (SD) [min, max] | Ours |
|---|---|---|
| Shared path | 16.70 (1.84) [13.21, 19.84] | 16.61 (1.77) [13.18, 19.20] |
| Cycle lane | 18.14 (1.00) [15.82, 19.65] | 18.02 (1.01) [**15.82, 19.65**] |
| Roadway | 17.11 (1.75) [13.93, 20.00] | 17.01 (1.73) [**13.93**, 19.93] |
| RM-ANOVA | F = 9.95 | F(2, 36) = 9.35, p = 5e-4 (GG ε = 0.87, p_GG = 1e-3) |
| t shared path vs cycle lane | −4.338 | −3.99 (p = 9e-4) |
| t cycle lane vs roadway | 2.80 | 2.67 (p = 0.016) |
| shared path vs roadway | "n.s." | t = −1.51, p = 0.15 |

- **Variants.**
  - Without P4 (n = 18): F = 14.3.
  - Zeros kept: F = 8.46.
  - GPS-only boundaries: 16.47 / 18.09 / 17.00 and F = 10.00, the closest F, but every rider is
    re-segmented.
- **Why the residual gap.** The authors' manual row ranges (unpublished) differ by a few seconds
  from the typed clock times. The largest effect is P4 (shared-path max 19.84 in the paper vs 18.96
  for our P4 and 19.20 overall).
- **Conclusion.** Reproduced qualitatively, and quantitatively within about 0.1 km/h.
- **Batch effect not discussed in the paper.** The 2024 riders were 1–2 km/h slower on every
  segment (§5.2, item 9).

### 7.2 Speed change points (p. 11, Fig. 5)

- **Sensitivity sweep** (`outputs/k02_cp_sweep_{keepzeros,dropzeros}.csv`).
  - Under the coded AIC, the result equals PELT at roughly the top penalty of the grid: grids
    (1, 50), (1, 100) and (1, 200) give exactly the fixed-penalty results for 50, 100 and 200.
  - Any grid that reaches a "no change point" penalty returns 0 change points: grid (1, 5000) gives
    6 change points in total.
- **Best post-hoc match:** penalty 30, zeros kept, per km, lengths 1.36 / 0.74 / 0.65.

| | Paper | Ours (pen = 30) |
|---|---|---|
| Shared path, per km | 7.9 (4.1) | 7.47 (3.59) |
| Cycle lane, per km | 4.3 (1.7) | 3.98 (1.71) |
| Roadway, per km | 10.2 (5.9) | 10.04 (5.94) |
| Total | 371 | 373 |

- With zeros dropped: 7.08 / 3.98 / 9.31, total 354.
- The "per participant" counts at pen = 30 are 10.2 / 2.9 / 6.5, which do **not** match, so the
  paper reports per-km values.
- **Caveat.** pen ≈ 30 is fitted to the paper's numbers. It is evidence that the published values
  come from PELT on per-segment 1 Hz speed, but the authors' actual grid remains unknown. The
  change-point count changes by a factor of 2 to 3 over plausible grids (pen 15–50), so **the
  metric is not reproducible without the grid**.
- **Additional property.** Because `jump = 5`, change points can only fall on 5-s multiples from
  the segment start. At the segment start the e-scooter often accelerates (P10: change points at
  5 s and 10 s).

### 7.3 Gaze (Table 3, p. 12). n = 14 (acc n = 12).

| Measure | Paper | Ours | Note |
|---|---|---|---|
| Fixations per km | 454.83 (84.58) / 460.20 (77.01) / 545.05 (113.9) | 456.04 (83.58) / 462.07 (77.33) / 543.52 (113.07) | Only with 0.74 / 0.65 km (with the Fig. 3 lengths: 456 / 526 / 477) |
| ANOVA fixations | F = 10.5; Tukey: road > shared path | RM F(2, 26) = 9.68, p = 7e-4 (one-way F = 3.89); between-subject Tukey road vs shared path p = 0.043, others n.s. | Matches the paper's mixture of RM-ANOVA and between-subject Tukey |
| Fixation duration (ms) | 371.8 (89.3) / 332.4 (90.4) / 295.3 (68.8) | 371.72 (89.33) / 332.37 (90.74) / 296.88 (71.70) | Reproduced |
| ANOVA duration | F = 23.3; no Tukey pair significant | RM F = 22.43, p = 2e-6; between-subject Tukey all p > 0.06; **paired t all p ≤ 0.024** | The paper's "no pair" is an artefact of the post-hoc test |
| Gaze "dispersion" | 0.61 (0.08) / 0.66 (0.06) / 0.64 (0.11) | coded metric on unique fixation points: 0.608 (0.084) / 0.643 (0.070) / 0.620 (0.100); on raw gaze samples as literally coded: 0.705 / 0.694 / 0.680 | RM F = 0.93, n.s. (paper: n.s.). The real SD of normalised fixation positions is 0.121 / 0.130 / 0.129 (n.s.). |
| Acc "dispersion" | 0.88 (0.04) / 0.83 (0.11) / 0.86 (0.06) [m/s²] | coded: 0.881 (0.049) / 0.851 (0.115) / 0.865 (0.043), dimensionless, n = 12 | n.s. (F = 0.67), as in the paper. The **SD in m/s²: 2.38 / 2.00 / 2.23, RM F = 16.0, p = 5e-5** (cycle lane lowest). |

- Fixations are counted as in the code (the groupby de-duplication). De-duplicating by Tobii event
  index differs by at most 0.2 fixations/km.
- **Not reproducible:**
  - the frequent-vs-infrequent t-tests (T = 0.88, 0.78, 0.22), because rider frequency is not in
    the data;
  - Table 5 and Fig. 8 (AOIs), because the labels are not in the data.

### 7.4 Encounters (Table 4, p. 12) and correlations (Fig. 7, p. 14)

| Encounters per km (n = 17) | Paper | Ours |
|---|---|---|
| Shared path: pedestrians / cycles / cars | 31.1 (14.5) / 4.5 (2.8) / 71.8 (20.6) | 31.1 (14.5) / 4.5 (2.8) / 71.8 (20.6) |
| Cycle lane (÷ 0.74 km) | 4.2 (2.9) / 2.4 (2.0) / 83.7 (49.3) | 4.2 (2.9) / 2.4 (2.0) / 84.0 (49.5) |
| Roadway | 17.1 (8.4) / 1.4 (1.7) / 187.2 (41.4) | **not reproducible**: the sheet is a copy of the cycle lane |

Fig. 7, Pearson on segment values, riders present in both tables:

- **Fixation count and duration** (n = 13): 14 of 16 coefficients within ±0.01 of the paper. The
  "total" column for segment 2 differs by about 0.08.
- **Gaze dispersion** (coded, fixations; n = 13): mean |Δ| = 0.09.
- **Acceleration dispersion** (n = 11): mean |Δ| = 0.13. Notably, segment-1 cycles gives −0.41
  against the paper's 0.03.
- **Change points** (pen = 30; n = 16): mean |Δ| = 0.11.
- **Segment 3:** all differ (mean |Δ| = 0.37), as expected given the duplicated sheet.
- **None of the 40 segment-1/2 correlations has p < 0.05.** The smallest p is 0.08. The paper's
  "strong" correlations (0.49, 0.54, −0.69) rest on n = 11–13.

## 8. What we can compare with our future Aria Gen 2 data

### 8.1 Design differences that bound every comparison

| Dimension | Kegalle et al. | Our study |
|---|---|---|
| Design | E-scooter only; within-subject across 3 infrastructures; round 2 of 2 | Within-subject **e-scooter vs bicycle**, same riders, same route |
| Vehicle | Shared Lime e-scooters capped at 20 km/h; riders' own app accounts | Our vehicles; cap and model to report. A speed cap compresses speed variance, and cyclists can exceed it. |
| City and context | Melbourne (park surroundings), winter (Aug–Sep 2023, Jul 2024), high-vis jackets, a following researcher | Our city and route. Infrastructure types and legality differ (e-scooters on pedestrian-shared paths may not be allowed in our jurisdiction — to check). |
| Sensors | Tobii G3 (gaze 50 Hz, scene camera 25 fps 1920×1080, IMU about 100 Hz); Garmin 1 Hz GNSS speed; Insta360; GoPro | Aria Gen 2: gaze 30 Hz (CPF angles), RGB 10 or 30 Hz (fisheye), IMU 800 Hz, VIO 10 Hz / about 800 Hz, GNSS 1 Hz, hand tracking |
| Sample | 23 recruited; speed n = 19, gaze n = 14, acc n = 12, encounters n = 17 | Plan a power analysis. Their effects have n = 11–19. |

### 8.2 Metric-by-metric mapping

The right-hand column says whether a comparison is meaningful and what to do.

| Their metric (sensor, definition) | Our Aria stream and definition to use | Meaningful? |
|---|---|---|
| **Mean speed per segment** (Garmin GNSS, 1 Hz, km/h, zeros removed) | GNSS `gps` 1 Hz or VIO-derived speed, **resampled to 1 Hz**, zeros (< 0.3 m/s) removed, same segment logic | **Yes**, the most comparable metric. Caveats: different route, vehicle cap and season. Use their values as a reference range (16.6–18.1 km/h); compare patterns, not levels. |
| **Speed change points per km** (ruptures PELT l2, min_size 2, jump 5, per segment, AIC over an unknown grid) | Same PELT on 1 Hz speed, **fixed, reported penalty**. Report pen = 30 (km/h)² for comparability with their published values, plus a sensitivity band (pen 15–50). Never use their degenerate AIC. | **Partly.** Only per km and only at a matched penalty. The count scales with speed variance (capped e-scooters vs bicycles), so also report a scale-free version (penalty proportional to the segment's speed variance) for our e-scooter/bicycle contrast. VIO speed at 10 Hz must be decimated to 1 Hz before PELT, or the counts are not comparable. |
| **Fixation count per km and mean fixation duration** (Tobii Pro Lab I-VT Attention, 50 Hz; events de-duplicated) | Aria `eyegaze` 30 Hz, I-VT on angular velocity (our 50°/s, ≥ 100 ms), counted **per minute and per km** | **Weak.** Fixation metrics depend on algorithm and sampling rate. On their own data (k06), our I-VT at 30 Hz gives 118–126 fixations/min and 271–330 ms mean duration, against Tobii's 136–158/min and 297–372 ms. The **direction** of segment effects agrees (shared path has the longest fixations; RM F = 61). Per-km values also mix in speed: bicycle vs e-scooter speed differences alone change fixations/km, so per-minute is primary for our vehicle contrast. |
| **"Gaze dispersion"** (min–max mean-norm of fixation points in scene px) | Compute **only for back-compatibility** (same formula on fixation points projected into RGB pixels, min–max within segment). The primary metrics are eye-in-head **yaw SD, pitch SD and BCEA (P = 0.682) in degrees** from CPF angles. | Their coded metric: **no**, because it is not a dispersion and is near-constant by construction. Angular metrics: **yes**. k06 gives their yaw SD as 6.6 / 8.2 / 9.2° (shared path / cycle lane / roadway; RM F = 19.2, p = 7e-6), pitch SD about 6–7° (n.s.) and BCEA 299 / 403 / 400 deg², directly comparable with Aria CPF yaw/pitch at 30 Hz. Caveats: Tobii HUCS vs Aria CPF frames (signs irrelevant for SD); Aria 30 Hz vs Tobii 50 Hz has little effect on SD; spectacles and calibration differ. |
| **"Accelerometer dispersion"** (Tobii accelerometer about 100 Hz, min–max mean-norm) | Do **not** reproduce for interpretation. Head movement from **gyroscope / VIO rotation**: mean and P95 of \|ω\| (°/s) after decimating Aria IMU (800 Hz) to about 100 Hz with low-pass filtering, plus head-yaw SD relative to travel direction from VIO | Their metric: **no**. Gyroscope: **yes, approximately.** k06 gives \|ω\| mean 16.9 / 15.8 / 20.2 °/s (roadway highest, p < 0.001) and P95 41 / 42 / 63 °/s (n = 12). Caveats: IMU mounting and filtering differ; vibration enters both; bicycle vs e-scooter vibration differs (small wheels, no suspension), so separate head rotation (low frequency, under about 5 Hz) from vibration (high frequency). |
| **Encounters per km** (YOLOv8x tracking IDs, centre 30% × 90% of the Tobii scene video, classes person / bicycle / car, manual corrections, parked cars included) | Our scene-understanding pipeline on Aria RGB (fisheye, 10 or 30 Hz), counting **unique tracked road users per km**, with moving and parked objects separated, and with the FOV and crop documented | **Order of magnitude only.** Counts depend on FOV, frame rate, detector, tracker (ID switches) and crop. For cross-study context use their shared path and cycle lane values only; roadway is unavailable. For our e-scooter vs bicycle contrast the count is a **covariate** (traffic exposure), not an outcome. |
| **Interactions / conflicts** (qualitative thematic analysis of 360° and follower videos) | Our event annotations: interaction episodes and perception → action with maximum deceleration, minimum speed, speed at first gaze, interaction duration | **Qualitative only.** They provide no quantitative conflict definition. Their themes (bell use, off-road manoeuvres, hand signals, verbal requests, yielding at crossings) are useful as codebook seeds. |
| **AOI fixation shares** (manual AOI per fixation; 8 classes; road ahead 78.6%) | Semantic gaze: class under the gaze point (time share, dwells), plus "forward" share from gaze yaw relative to travel | **Loose.** Different taxonomy (their AOIs are scene regions plus road-user types), method (fixation-by-fixation manual vs sample-wise automatic) and data (not public). Compare only "road ahead / forward" and "pedestrian / vehicle" shares, as broad ranges. |
| **Gaze-sample validity** (≥ 75% rule; 76–98% in the public data) | Aria `gaze_status` validity per segment | **Yes**, as a data-quality benchmark. Adopt an explicit threshold and report it per segment. |

### 8.3 Concrete reference values for our analysis plan

Values are from their public data computed with our definitions (k06, n = 14, acc n = 12),
given as shared path / cycle lane / roadway, with SD in brackets:

- eye-in-head yaw SD: 6.62 (1.53) / 8.16 (2.15) / 9.21 (1.39)°
- pitch SD: 6.24 (1.64) / 6.71 (2.30) / 6.06 (1.47)°
- BCEA (P = 0.682): 299 (110) / 403 (201) / 400 (116) deg²
- I-VT (30 Hz, 50°/s, ≥ 100 ms): 117.8 (17.3) / 126.3 (20.9) / 123.7 (19.1) fixations per minute;
  mean duration 330 (73) / 284 (72) / 271 (64) ms
- head |ω| mean: 16.9 (3.5) / 15.8 (4.4) / 20.2 (4.6) °/s; P95: 41 (11) / 42 (19) / 63 (24) °/s
- speed (zeros removed): 16.6 (1.8) / 18.0 (1.0) / 17.0 (1.7) km/h
- PELT change points per km at pen = 30: 7.5 (3.6) / 4.0 (1.7) / 10.0 (5.9)

### 8.4 Recommendations

1. **Implement their two speed metrics exactly**, as parameterised options in our pipeline:
   1 Hz speed, zeros removed, PELT l2 with jump 5, min_size 2 and a fixed penalty, reported per km.
   Speed and change points are the only directly comparable quantitative outcomes.
2. **Report angular gaze and head metrics as primary.** Report their "dispersion" metrics only in
   a footnote, labelled with their actual formula.
3. **Report fixation metrics per minute as well as per km.** State the detector, sampling rate and
   thresholds. Cite the Tobii I-VT Attention vs our I-VT gap measured on their data (§8.2).
4. **Do not use their roadway encounter counts,** and do not rely on their Fig. 7 correlations
   (n.s., n ≤ 16).
5. **Correct the segment lengths when citing.** Their per-km values use cycle lane 0.74 km and
   roadway 0.65 km, not the Fig. 3 labels.
6. **Do not copy or redistribute any of their data or code** into our repository, because there is
   no licence. Keep the clean-room scripts, with their attribution headers, in the scratchpad or
   in an external analysis folder. Contact the authors before publishing derived per-participant
   comparisons.

## 9. Output files (in `<workdir>/kegalle_replication/outputs/`)

- **Inventory (k00):**
  - `k00_inventory.json`
  - `k00_inventory_gaze.csv` (includes the removed-in-history files)
  - `k00_inventory_speed.csv`
  - `k00_timemapping_parsed.csv`
- **Speed (k01):** `k01_speed_by_participant_segment_*.csv` and `k01_speed_summary_*.json`, for
  6 variants: {nozeros, keepzeros} × {timemapping+gpsfallback, timemapping, gps}.
- **Change points (k02):**
  - `k02_cp_pen30_keepzeros.{csv,json}`
  - `k02_cp_original_1-30x100_keepzeros.{csv,json}`
  - `k02_cp_sweep_{keepzeros,dropzeros}.csv`
  - `k02b_pelt_vs_ruptures.json`
- **Fixations (k03):** `k03_fixations_by_participant_segment.csv`, `k03_fixations_summary.json`
- **Dispersion (k04):** `k04_dispersion_by_participant_segment.csv`, `k04_dispersion_summary.json`
- **Encounters and correlations (k05):**
  - `k05_encounters_long.csv`
  - `k05_merged_metrics_encounters.csv`
  - `k05_fig7_correlations.csv`
  - `k05_summary.json`
- **Harmonised metrics (k06):** `k06_harmonised_by_participant_segment.csv`,
  `k06_harmonised_summary.json`
- **Comparison (k07):** `k07_paper_vs_ours.csv`
- **Original-notebook harness:** `original_notebooks_run_log.json` and
  `original_harness_work/` (small CSVs only)
- **Full run:** `run_all.log`
