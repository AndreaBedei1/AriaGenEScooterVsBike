# External baseline: Kegalle et al. (2025)

What can be executed with the public material of Kegalle et al. (2025), what we reproduced,
and what can be compared with our future Aria Gen 2 recordings. Scripts:
[`replication/kegalle2025/`](../../replication/kegalle2025/README.md) (separate from the
pipeline); full study-level comparison: `replication/kegalle2025/results/paper_vs_ours.csv`.

## 1. The external material

| Item | Fact (verified 2026-10-15) |
|---|---|
| Paper | Kegalle, Hettiachchi, Chan, Sanderson, Salim. *Proc. ACM IMWUT* 9(1), 2025, 23 pp., DOI 10.1145/3712284, CC BY 4.0. arXiv:2502.16755 v1 (the version in `paper/`). Article number 217 (arXiv PDF) vs 8 (authors' README); Crossref gives none. |
| Repository | github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis, HEAD `ed5c221` (2025-03-06), 23 commits |
| Licence | **None** (no LICENSE file; GitHub `license: null`). README: "If you use this data or code in your research, please cite our paper". Consequence: cite, re-analyse locally, do **not** redistribute data or code. |
| Data present | Tobii Pro Lab exports (gaze 50 Hz, fixation filter "Tobii I-VT (Attention)", gyroscope/accelerometer ~118 samples/s, magnetometer ~10 Hz) for 14 riders (2 without IMU); Garmin 1 Hz GNSS speed and positions for 19 riders; a hand-typed segment-time sheet; YOLO encounter counts for 17 riders. All files are the **second round** of the loop. |
| Data absent | Videos (withheld for privacy, p. 217:2), AOI labels, demographics, rider frequency, interviews; no data-access procedure |
| Code | Jupyter notebooks of functions, never executed; 6 of 15 non-video functions fail on first call; the speed reader silently corrupts the 2024 files; statistics and fixation detection are not in the code (fixations come from Tobii Pro Lab) |

## 2. Reconstruction of the methods (paper section -> what was actually done)

| Method | Paper | Reconstruction |
|---|---|---|
| Exported gaze | Tobii Pro Lab export (p. 217:9) | 2-D gaze in scene-video pixels (1920x1080), 3-D gaze, per-eye direction, pupil, validity, eye-movement type from the I-VT "Attention" preset (min. fixation 60 ms observed) |
| Speed per second | Garmin, 1 Hz, standstill removed (p. 217:8) | GNSS-derived speed in km/h; timestamps need +16 h; zeros removed for means |
| Temporal segmentation | three route segments (p. 217:8, Fig. 3) | **manual** clock times per rider; segment lengths in the paper's per-km values are 1.36 / 0.74 / 0.65 km (Fig. 3 labels of cycle lane and roadway appear swapped) |
| Gaze dispersion | SD of fixation x/y, Euclidean, normalised (p. 217:9) | **code differs**: mean norm of min-max-normalised points (~0.71 by construction); the SD version is ~0.12-0.13 |
| Fixation detection | Tobii I-VT (p. 217:9) | vendor preset, thresholds unreported |
| Head movements | SD of accelerometer x,y,z (p. 217:9) | **code differs** (dimensionless min-max metric); accelerometer mixes vibration and gravity; the real SD in m/s^2 differs between segments (F = 16.0), unlike the paper's conclusion |
| Speed change points | PELT (p. 217:8) | `ruptures` PELT l2, jump 5, penalty by an AIC over an unpublished grid; the coded AIC is degenerate (drops the last segment's RSS). Counts depend on the grid by a factor 2-3. |
| Infrastructure comparison | RM-ANOVA, t-tests, Tukey (pp. 217:10-13) | not in code; Tukey HSD applied between subjects after within-subject ANOVAs |
| Interactions | YOLOv8 encounters (pp. 217:9-10) + thematic video analysis | encounters = unique track ids of COCO person/bicycle/car in a central crop, parked cars included; conflicts only qualitative |

## 3. What we reproduced (independent scripts, public data)

| Quantity | Paper | Ours |
|---|---|---|
| Speed, km/h (shared path / cycle lane / roadway) | 16.70 / 18.14 / 17.11, F = 9.95 | 16.61 / 18.02 / 17.01, F(2,36) = 9.35 |
| Fixation duration, ms | 371.8 / 332.4 / 295.3, F = 23.3 | 371.7 / 332.4 / 296.9, F = 22.4 |
| Fixations per km | 454.8 / 460.2 / 545.1, F = 10.5 | 456.0 / 462.1 / 543.5, F = 9.7 |
| "Gaze dispersion" (coded metric) | 0.61 / 0.66 / 0.64 | 0.61 / 0.64 / 0.62 |
| "Acc. dispersion" (coded metric) | 0.88 / 0.83 / 0.86 | 0.88 / 0.85 / 0.87 (n = 12) |
| Encounters per km, shared path and cycle lane | Table 4 | identical within 0.3 |
| Change points per km (penalty fitted post hoc: 30) | 7.9 / 4.3 / 10.2, total 371 | 7.47 / 3.98 / 10.04, total 373 |
| Fig. 7 correlations (fixations) | "strong" | 14 of 16 within +-0.01; none of 40 significant (n = 11-16) |

Not reproducible: roadway encounters (the released sheet duplicates the cycle-lane sheet), AOI
results (labels not released), frequent-vs-rare rider tests (rider frequency not released).

## 4. What we can compare with our Aria Gen 2 data

Design differences bound every comparison: e-scooter only (shared Lime scooters capped at
20 km/h) vs our two vehicles; Melbourne park loop vs Cesena urban loop; Tobii G3 (gaze 50 Hz,
1920x1080 scene camera) vs Aria Gen 2 (gaze 30 Hz in CPF angles, fisheye RGB); Garmin vs
Aria GNSS/VIO.

| Their metric | Our counterpart | Comparable? |
|---|---|---|
| Mean speed per segment (1 Hz GNSS, zeros removed) | Aria GNSS or VIO speed resampled to 1 Hz, zeros removed, same segment logic | **Yes** (patterns and ranges; levels differ by city and vehicle) |
| Speed change points per km | same PELT on 1 Hz speed with a **fixed, reported** penalty (30 for comparability, plus a 15-50 sensitivity band) | **Partly** (only at matched penalty; scale with speed variance) |
| Fixations per km, mean fixation duration | Aria gaze 30 Hz, our I-VT, reported per minute and per km | **Weak**: algorithm- and rate-dependent. On their data, our I-VT at 30 Hz gives 118-126 fixations/min and 271-330 ms vs Tobii's 136-158/min and 297-372 ms, with the same direction of segment effects. |
| Gaze "dispersion" (coded) | not used; we report yaw SD, pitch SD and BCEA in degrees | Their metric: **no**. Angular metrics: **yes** - on their data yaw SD 6.6 / 8.2 / 9.2 deg (F = 19.2), BCEA 299 / 403 / 400 deg^2 |
| Accelerometer "dispersion" | head angular speed from gyroscope/VIO, vibration separated by frequency band | Their metric: **no**. Gyroscope: approximately - mean 16.9 / 15.8 / 20.2 deg/s, P95 41 / 42 / 63 deg/s |
| Encounters per km | detector + tracker on Aria RGB, moving and parked separated | order of magnitude only; for us a **covariate** (exposure), not an outcome |
| Conflicts (qualitative) | annotated events and perception-action metrics | qualitative codebook seeds only |
| Gaze validity (> 75 % rule) | per-segment gaze validity from the quality report | **Yes** as a data-quality benchmark |

## 5. Consequences for our pipeline

1. Implement their two speed metrics exactly as options (1 Hz, zeros removed, PELT l2 with a
   fixed penalty, per km) so that our numbers can be placed next to theirs.
2. Use angular gaze and rotation-based head metrics as primary; never interpret their
   dispersion metrics.
3. Report fixation detector, rate and thresholds; report per minute and per km (speed differs by
   vehicle, so per-km rates mix speed and gaze).
4. Use mixed models instead of between-subject post-hoc tests, and segment boundaries from the
   route geometry (`map-segments`) instead of hand-typed clock times.
5. Do not redistribute their data; ask the authors before publishing per-participant comparisons.
