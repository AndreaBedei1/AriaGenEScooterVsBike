# Hand tracking while riding: validation plan (RQ5, exploratory)

On-device hand tracking of Aria Gen 2 may or may not work while the hands hold a handlebar.
Until it is measured, every hand-related result is exploratory and a non-detected hand is
**missing / unknown**, never "hand off the handlebar".

## 1. What the device provides (verified, `docs/aria/aria_gen2_technical_notes.md` section 5)

- Stream `handtracking`, rate set by the profile (`ht.rate_hz`: 10 Hz in our profile; the
  official template uses 10 Hz, predefined profiles 30 Hz).
- Per sample and hand: `None` when no valid pose is found; otherwise a confidence, 21 landmarks,
  wrist pose (SE3) and derived wrist/palm normals, in the **device frame** (we convert to CPF).
- Computed from the CV (SLAM) cameras, not the RGB camera: the CV cameras must be recorded
  (our profile records them at 10 Hz, the documented minimum for hand tracking).
- Meta's own benchmark (hand-object interaction, 30 fps): on-device mean keypoint error
  45.0 mm, lose-track ratio 12.7 % (MPS: 19.7 mm, 9.3 %). No figure for gloves, distance,
  lighting or handlebar grip. The extractor exports presence, confidence, wrist and palm
  position (`hands.csv`); joint angles and per-finger confidences are not exposed in Python.

## 2. Questions

1. Effective rate and dropouts of the `handtracking` stream while riding (vs the 10 Hz nominal).
2. Detection coverage per hand, per vehicle (handlebar width and height differ), per
   manoeuvre (straight, turns, stops) and per light condition.
3. Confidence distribution of detections; relation between confidence and correctness.
4. Positional plausibility: wrist positions relative to the head consistent with a two-handed
   grip; stability over straight riding; change at turns and stops.
5. Whether genuine events (one hand off the handlebar for an arm signal, adjusting glasses,
   ringing the bell) are detectable, and with which false-alarm rate.
6. Systematic differences between bicycle and e-scooter that are due to the measurement
   (field of view, occlusion) rather than to behaviour.

## 3. Ground truth

- **Source**: the RGB stream (anonymised copy) and, for authorised staff only, the CV camera
  streams of the restricted raw VRS (hands are often better visible in the lower CV cameras).
  CV camera images are not shared and are removed from released data (see privacy pipeline).
- **Sample**: per ride, 150 frames stratified by manoeuvre (straight 50 %, turns 25 %, stops
  and starts 25 %), plus **all** frames within +-2 s of annotated hand events (arm signals,
  bell, glasses adjustment) taken from the ride sheet and video review. Pilot total:
  ~1,800-2,500 frames (3 participants x 2 vehicles x 1-2 trials), annotated in the hand-tracking
  timestamps' nearest RGB frame.
- **Labels per hand**: `on_handlebar` / `off_handlebar` / `not_visible` (out of view or fully
  occluded) / `uncertain`; for visible hands, a 2-D wrist point in the image (to compare with
  the projected tracker wrist).
- **Double annotation** of 20 % of frames; Cohen's kappa for the categorical label; pixel
  distance between annotators for the wrist point (sets the ceiling of measurable accuracy).

## 4. Metrics

| Metric | Definition |
|---|---|
| Effective rate, dropout, gaps | from `quality.json` (stream `hands`) |
| Detection rate | P(tracker reports the hand | hand visible), per hand, vehicle, manoeuvre |
| False detection rate | P(tracker reports the hand | hand not visible) |
| Presence agreement | tracker present vs `on_handlebar` + `off_handlebar` labels (kappa) |
| Wrist reprojection error | distance (px and deg) between the tracker wrist projected into the RGB frame and the annotated wrist point, for visible hands |
| Off-handlebar event detection | precision/recall of a candidate rule (wrist leaves the handlebar region by > d for > t) against annotated events, with threshold sweep |
| Confidence calibration | detection correctness by confidence decile |

## 5. Decision criteria (provisional, to agree with the project lead)

- Hand metrics enter descriptive results only if detection rate >= 0.8 for visible hands in
  both vehicles and wrist error is small relative to the posture differences of interest.
- If detection is adequate but not on both hands or not in turns, results are restricted to the
  conditions where it is adequate, and reported as such.
- If detection is inadequate, RQ5 is reported as a negative feasibility result (itself useful),
  and MPS hand tracking (cloud, more accurate in Meta's benchmark) is considered **only** after
  ethics/DPO authorisation of the upload.

## 6. Implementation status

Implemented: extraction of presence/confidence/wrist/palm (CPF), quality checks (presence
fraction, absence episodes, confidence), window descriptors (`hands.py`), smoke test on the
official Gen 2 test recording (hands detected with confidence ~0.9999 in one test sequence,
absent in another). Planned: projection of the wrist into the RGB frame, event rule,
annotation task.
