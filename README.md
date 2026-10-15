# AriaGenEScooterVsBike

Research codebase and study design for a **within-participant comparison of riding an electric
kick-scooter and a conventional bicycle** on the same urban route (Cesena, Italy), using
**Meta Project Aria Gen 2** glasses as the **only sensor**: how the vehicle and the
infrastructure affect the rider's **visual attention**, **head movements** and **estimated
riding dynamics**, how reliably a single wearable can measure them, and how consistent each
person is across vehicles and repeated rides.

> **Status (October 2026): design phase.** No recording of the new study exists yet. The
> codebase (inherited from the e-scooter-only project and extended) is tested on synthetic data
> and smoke-tested on official Aria Gen 2 test recordings, **not on riding data**. The route is a
> desk draft not yet verified on site. Ethics approvals have **not** been obtained; no
> acquisition with participants may start before them.

## Study in brief

- **Design**: every participant rides both vehicles on the same loop, same direction,
  counterbalanced order, 1 or 2 trials per vehicle (ABBA/BAAB with two). Pilot: 3 participants,
  feasibility only. Details: [docs/study_overview.md](docs/study_overview.md) (Italian),
  [pilot protocol](docs/methodology/pilot_protocol.md).
- **Research questions**: RQ1 vehicle effect; RQ2 infrastructure effect across modes; RQ3
  perception-action timing (exploratory); RQ4 individual consistency and repeatability; RQ5 hands
  and posture (exploratory). [docs/research_questions.md](docs/research_questions.md).
- **What is new** (after reviewing the literature): a bicycle vs e-scooter eye-tracking
  comparison on the same riders already exists on short single segments (Pashkevich 2022,
  Trefzger 2021). Our contribution is a counterbalanced, repeated, route-scale, segment-matched,
  multimodal comparison and a validation of single-wearable sensing.
  [docs/research/scientific_contribution.md](docs/research/scientific_contribution.md).
- **Sensor**: Aria Gen 2 only (RGB 15 Hz, on-device gaze 30 Hz, VIO 10 Hz + high-frequency VIO
  ~800 Hz, hand tracking 10 Hz, IMU 800 Hz, GNSS 1 Hz, PPG); no sensor on the vehicles. Speed
  and decelerations are **estimates** from head motion. [Aria notes](docs/aria_gen2_integration.md),
  [metrics catalog](docs/methodology/metrics_catalog.md).
- **Route**: candidate loop CES_A, 4.25 km, about 16-24 min of riding, from the Campus (Via
  dell'Università 50); alternative CES_B, 3.66 km. **Open the interactive map**:
  [docs/route/cesena_route_map.html](docs/route/cesena_route_map.html) (in a browser; tiles need
  internet). [Route description](docs/route/route_description.md),
  [on-site checklist](docs/route/route_validation_checklist.md).
- **Main analyses**: data-quality control per stream; route-referenced segment metrics (gaze,
  head, estimated dynamics); within-participant e-scooter minus bicycle contrasts; repeatability;
  mixed-effects models in the main study ([statistical analysis plan](docs/methodology/statistical_analysis_plan.md)).
- **Literature**: [review](docs/literature/literature_review.md),
  [comparison matrix](docs/literature/paper_matrix.csv), [gaps](docs/literature/research_gaps.md),
  [replication plan](docs/literature/replication_plan.md),
  [Kegalle et al. 2025 baseline](docs/literature/kegalle_replication.md),
  [references.bib](docs/literature/references.bib).

## Implemented / tested / planned / TBD

| Component | Status |
|---|---|
| Portable configuration (YAML, strict validation), hierarchical taxonomy with `unknown` | implemented, tested |
| Two-vehicle schema: manifest v2 (trials, vehicle units), vehicle catalogue with optional per-vehicle overrides; v1 manifests still read | implemented, tested |
| Data-quality control: rates, dropouts, gap classes, timestamp errors, VIO status/resets/jumps, gaze/hand/GNSS validity, observed/interpolable/degraded/unusable intervals, window quality flags | implemented, tested (synthetic and official Gen 2 test recordings) |
| Synchronisation, ride trimming, kinematics (valid VIO only, no interpolation across resets), semantic gaze, perception -> action | implemented, tested on synthetic data |
| Aria Gen 2 extraction (VRS -> canonical streams incl. high-frequency VIO and hand tracking; raw-stream quality; embedded profile and sensor health) | implemented; smoke-tested on official Gen 2 test VRS; **not run on riding data** |
| Route builder (OpenStreetMap legal routing for both vehicles, official open-data cross-check, GeoJSON/GPX/map) | implemented; outputs are a desk draft |
| GNSS -> planned-route segments (`map-segments`) | implemented, tested on synthetic loops |
| Counterbalanced ride plans (`plan-rides`) | implemented, tested |
| Study aggregation incl. vehicle x infrastructure and within-participant contrasts | implemented, tested (descriptive) |
| Exploratory hand descriptors | implemented; validity while riding unknown |
| Independent re-analysis of Kegalle et al. (2025) public data (`replication/`) | implemented, verified on the public data |
| Privacy utilities (tiers, GPS protection, region blurring, identifier scanner) | implemented, tested |
| EgoBlur on Gen 2 VRS + stream filtering | documented and checked on an official sample (debug mode); **not run on study data** |
| Segmentation / detection / tracking back-ends | segmentation interface + mappings only; models selected, **benchmark planned** |
| Head-turn events, PELT change points, gaze ground distance, PPG heart rate | planned |
| Mixed-effects models, ICC | planned (statistical analysis plan) |
| Annotation guide, final route, recording profile on the device, approvals, retention, DPIA | **TBD** |

## Repository structure

```
AriaGenEScooterVsBike/
  README.md, pyproject.toml, uv.lock, setup_linux.sh, setup_windows.ps1
  configs/
    default.yaml             analysis parameters (shared by both vehicles)
    vehicles.yaml            e-scooter / bicycle catalogue
    taxonomy.yaml            infrastructure classes, event types, hierarchical semantic classes
    example_session.yaml     manifest v2 example (one e-scooter and one bicycle ride)
    recording_profiles/      Aria Gen 2 recording profile of the study + verification notes
    protocol/pilot.yaml      pilot ride plan (3 participants, ABBA/BAAB)
    route/cesena_routes.yaml waypoints and rules of the candidate routes
    label_mappings/          Mapillary Vistas / Cityscapes -> project classes
  src/ariagen_escooter/      package (config, session, streams, quality, aria, synchronization,
                             trimming, trajectory, behaviour, gaze, hands, events, route,
                             protocol, segmentation, privacy, pipeline, reporting, cli, ...)
  tools/route/               route builder and map template (optional 'route' extra)
  replication/kegalle2025/   independent re-analysis scripts (external data not included)
  tests/                     unit, end-to-end and portability tests
  data/                      raw/ interim/ processed/ public/ (never versioned) + synthetic/
  paper/                     local PDFs of the literature (not versioned; README only)
  docs/
    study_overview.md        synthesis for the project lead (Italian)
    research_questions.md  methodology.md  data_schema.md  privacy_pipeline.md  aria_gen2_integration.md
    literature/  methodology/  research/  route/  aria/  privacy/  ethics/ (Italian)
    presentation/            overview deck of the former e-scooter-only phase (outdated)
```

## Setup

The virtual environment is machine specific: never copy `.venv` between Windows and Linux. Both
scripts use [uv](https://docs.astral.sh/uv/) with the committed universal `uv.lock` (Python 3.11
from `.python-version`), falling back to `venv + pip` if uv is missing.

```bash
./setup_linux.sh                         # core + aria + dev, then tests (Linux: all stages incl. VRS)
./setup_linux.sh --extras aria,route     # + route builder (osmnx)
./setup_linux.sh --egoblur               # + separate .venv-egoblur for Meta EgoBlur
```

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1   # analysis, docs; no VRS (no Windows wheels)
```

Extras: `aria` (projectaria-tools 2.3.x, Linux/macOS), `route` (osmnx, requests), `cv`
(experimental segmentation), `dev` (pytest, ruff), `presentation` (python-pptx). Manual
equivalent: `uv sync --frozen --extra aria --extra dev`.

## Quick start

```bash
python -m ariagen_escooter info
python -m ariagen_escooter run data/synthetic/SYN001_S01            # SYNTHETIC demo
python -m ariagen_escooter plan-rides configs/protocol/pilot.yaml    # pilot ride plan
python tools/route/build_route.py --elevation --brouter --official-data   # rebuild route outputs (network)
```

Real session (after approvals): `new-session --participant P001 --ride escooter:1:1 --ride
bicycle:1:2` -> copy VRS -> `extract-aria` (Linux) -> anonymise copies for viewing (EgoBlur) ->
`map-segments` (review) -> annotate events -> `validate` -> `run` -> `aggregate`. Formats:
[docs/data_schema.md](docs/data_schema.md).

## Data and privacy rules (summary)

`data/raw`, `interim`, `processed`, `public` and `paper/` are never versioned; VRS, video, audio
and model files are ignored everywhere. Originals are never modified or deleted by the code.
Pseudonyms only. Faces and plates are anonymised before any viewing; eye-camera images and
device identifiers are removed from working copies; no MPS or other cloud upload without
authorisation. [docs/privacy_pipeline.md](docs/privacy_pipeline.md); ethics documents (Italian):
[docs/ethics/](docs/ethics/).

## Tests

```bash
python -m pytest -q                       # ~175 tests, ~11 s, no hardware or real data
ARIAGEN_TEST_VRS=<official Gen 2 test .vrs> python -m pytest tests/test_aria.py   # optional extractor smoke test
python -m ruff check src tests tools replication
```

## Tested environments

| System | Python | Notes |
|---|---|---|
| Ubuntu 24.04 (this phase, Oct 2026) | 3.11 (uv) | all tests pass; projectaria-tools 2.3.0; extractor smoke test on official Gen 2 test recordings |
| Windows 11 / WSL Ubuntu 24.04 (previous phase) | 3.11 | all tests passed before the two-vehicle changes; **Windows not re-tested in this phase** |

## Licence and citation

**TBD** (project lead and institution). External material keeps its own terms: OpenStreetMap
data (ODbL) and Comune di Cesena open data (CC BY 4.0) in the route outputs; Kegalle et al.
(2025) data and code are not redistributed (no licence; cite the paper).
