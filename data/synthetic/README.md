# data/synthetic - SYNTHETIC / TEST DATA

**Everything in this folder is artificial. It is not experimental data, it does not
describe any real person, route or event, and it must never be analysed, reported or
shared as if it were real.**

Purpose: verify the software (portability, validation, trimming, synchronisation,
metrics, reports) without Aria hardware and without personal data.

| File | Content |
|---|---|
| `SYN001_S01/manifest.yaml` | Session manifest (`synthetic: true`, participant `SYN001`) |
| `SYN001_S01/SYN001_S01_R01/streams/*.csv` | Canonical streams: RGB frame index (10 Hz, 3 dropped frames), eye gaze (30 Hz, blinks, one tracking loss), head pose (20 Hz), simplified IMU (50 Hz), external GPS (1 Hz, deliberate +0.6 s clock residual) |
| `SYN001_S01/SYN001_S01_R01/annotations/*.csv` | Route segments (5 infrastructure classes) and 8 events/interactions |
| `SYN001_S01/SYN001_S01_R01/semantic/labels.npz` | 96x72 label maps + instance ids rendered from a procedural 3-D scene |
| `SYN001_S01/ground_truth.json` | Values the pipeline should recover (riding interval, clock residual, first gaze and action onset per event) |
| `participants.csv` | Synthetic participant covariates (coarse categories) |

The data are generated deterministically by `ariagen_escooter.synthetic`
(`python -m ariagen_escooter make-synthetic`); a test checks that the committed files
match the generator. Known simplifications (pinhole camera at the CPF, IMU axes equal
to CPF axes, no VIO drift) are listed in `ground_truth.json`. GNSS coordinates are
placed in the Adriatic Sea on purpose.
