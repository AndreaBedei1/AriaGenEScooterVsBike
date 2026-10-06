# Data folders and access tiers

| Folder | Tier | Content | Versioned in git |
|---|---|---|---|
| `raw/` | **raw identifiable** | Session manifests, Aria VRS files, MPS outputs, external GPS logs. Contains faces, licence plates, voices and precise locations of participants and bystanders. | **Never** |
| `interim/` | pseudonymised research data (restricted) | Canonical streams extracted from VRS, label maps, annotations. Still linked to pseudonymous IDs; may contain precise GPS. | **Never** |
| `processed/` | pseudonymised research data | Analysis outputs (reports, metric tables, figures). | **Never** |
| `public/` | anonymised / shareable | Staging area for datasets **explicitly prepared and reviewed** for sharing (derived metrics, generalised trajectories, anonymised media). Published through a data repository, not git. | **Never** |
| `synthetic/` | SYNTHETIC / TEST DATA | Small artificial session used by tests and the MVP demo. Not experimental data. | Yes |

Rules (details in `docs/privacy_pipeline.md`):

1. Original data are **never deleted or modified automatically**; every step writes new files.
2. No real names, e-mail addresses or phone numbers anywhere in these folders. The key
   linking pseudonymous IDs to people is kept by the study team outside this repository.
3. Nothing leaves `raw/`/`interim/`/`processed/` for sharing without the anonymisation
   steps and a documented review.
4. The data root can be moved to another disk (e.g. on the Linux machine) by setting
   the environment variable `ARIAGEN_DATA_ROOT`.
