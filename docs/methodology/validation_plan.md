# Validation plan

Principle: **every quantitative metric is paired with a strategy that checks its correctness,
not only with a function that computes it.** Synthetic tests (already in `tests/`) verify that
the code does what it is meant to do; they do not show that the result is valid on real riding
data. Each item below states the reference, the metric, the sample and the acceptance rule
(provisional, to be fixed with the project lead before the main study).

| Component | Reference ("ground truth") | Metrics | Sample (pilot) | Acceptance / action |
|---|---|---|---|---|
| **Stream extraction and timing** | profile nominal rates; on-device `sensor_health_stats` embedded in the VRS | effective vs nominal rate, dropout fraction, gap classes, duplicated / out-of-order / invalid timestamps (`quality.json`, `extraction_quality.json`) | every recording | report all; recordings with long gaps in core streams flagged; never interpolated beyond the configured short gaps |
| **VIO pose** | GNSS track; route geometry (planned route length); video-annotated stops | valid fraction, resets per minute, position/orientation jumps; trajectory length vs route length; speed vs GNSS speed (bias, limits of agreement); stop times vs video | every ride | no acceptance threshold on dropout assumed a priori (3-15 % was only an expectation); segments with low coverage excluded via `quality_flag` |
| **High-frequency VIO** | 10 Hz VIO | effective rate (~797 Hz on test data), quality_score, agreement with VIO at shared instants | every ride | used only for smooth orientation/velocity; never as independent evidence |
| **Gaze calibration / accuracy** | printed targets at 2, 5, 10 m and known angles, before and after each ride (30-60 s, outdoors) | median and 95th percentile angular error per participant and ride; drift between before/after | every ride | defines the lookup tolerance r and the ambiguity band; rides with large error flagged |
| **Gaze projection into RGB** | overlay of projected gaze on frames during target fixation | pixel/deg distance to target centre | 20 frames per ride | systematic offset > tolerance -> check calibration/CPF version |
| **Semantic segmentation** | manual partial labels on stratified frames | per-class IoU, confusion, gaze-hit accuracy | see `cv_benchmark_plan.md` | decision rules in that file |
| **Detection / tracking** | manual boxes and identities on clips | recall by angular size, HOTA, IDF1, ID switches, gaze-weighted identity accuracy | 30-40 clips (main study; pilot: a subset) | as above |
| **Hand tracking** | annotated frames (RGB, restricted CV cameras) | detection rate, false detections, wrist error, event precision/recall | `hand_tracking_validation.md` | exploratory unless criteria met |
| **Trimming (start/end of riding)** | manual start/end from the ride sheet and video | difference in seconds (automatic - manual) | every ride | |difference| <= 5 s typical; manual override stored in the manifest when needed |
| **Route alignment (segments)** | boundaries annotated on anonymised video at landmarks | boundary error (s, m); fraction of segments recovered | all segments of the pilot rides | boundaries of short units (crossings, roundabouts) reviewed manually |
| **Speed and decelerations** | GNSS Doppler speed (1 Hz); video-timed passages between surveyed landmarks; stops | bias and limits of agreement (Bland-Altman); deceleration onset vs video | every ride; 10 landmark pairs per ride | report agreement; decelerations remain "estimates" |
| **Head-motion metrics** | gyroscope vs VIO angular velocity; static periods; video of head turns | agreement; false head-turn events | sample of 10 min per vehicle | thresholds (e.g. +-20 deg) checked by sensitivity analysis |
| **Fixation detection (I-VT)** | manual coding on a sample (ET camera at 5 Hz is insufficient; use scene video + gaze) | event agreement, threshold sensitivity | 5 min per participant | report sensitivity; prefer sample-based metrics if unstable |
| **Annotations (segments, events)** | second annotator | Cohen's kappa (classes), boundary agreement within tolerance | 20 % of rides | annotation guide revised if kappa < 0.7 |
| **Perception-action latencies** | manual onset annotation on video for a subset of events | onset differences; share of excluded events (order not identifiable); threshold sweep | all pilot events | exploratory; never interpreted as reaction time |
| **PPG** | none available in the field (no chest strap planned) | signal-quality index, fraction of usable windows | every ride | exploratory covariate only if quality is adequate |
| **Privacy processing (EgoBlur)** | manual review of a random sample of anonymised frames + all frames used in figures | false negatives (faces/plates visible), false positives | >= 200 frames per session | re-run with lower thresholds if misses are found; log reviewed frames |

Pipeline-level checks already automated (synthetic ground truth, `tests/`): trimming interval,
GPS clock residual, first gaze, deceleration onsets, metrics on analytic signals,
deterministic outputs, data-quality classification, route alignment on a self-crossing loop,
two-vehicle identifiers in all tables, extractor on an official Gen 2 test VRS.
