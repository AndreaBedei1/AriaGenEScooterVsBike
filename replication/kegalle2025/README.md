# Independent re-analysis of the Kegalle et al. (2025) public data

Stand-alone scripts, **separate from the project pipeline**, that recompute the quantitative
results of:

> Kegalle, H. N., Hettiachchi, D., Chan, J., Sanderson, M., Salim, F. D. (2025). Watch Out!
> E-scooter Coming Through!: Multimodal Sensing of Mixed Traffic Use and Conflicts Through
> Riders' Ego-centric Views. *Proc. ACM IMWUT* 9(1). https://doi.org/10.1145/3712284
> (paper licensed CC BY 4.0; article number 217 in the arXiv PDF, 8 in the authors' README:
> check the ACM Digital Library before citing).

from the data the authors published at
https://github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis
(verified at commit `ed5c22195ecb0d3468fe67e8da5cc9ca9a1e9cb3`, 2025-03-06).

## Licence and citation of the external material

- The external repository has **no licence file** (GitHub reports `license: null`): default
  copyright applies. Its README asks users of the data or code to cite the paper above.
- Therefore **no data and no code of the authors are included here**. These scripts are our own
  implementations written from the paper text and from reading the notebooks; each header names
  the original notebook/cell it corresponds to. They read the data from a local clone whose path
  is passed on the command line.
- `results/paper_vs_ours.csv` contains only study-level numbers (the paper's published values
  next to ours). Per-participant outputs are not versioned.
- Before publishing comparisons that rely on the authors' per-participant data, ask the authors
  for permission (contacts on p. 1 of the paper).

## Run

```bash
git clone https://github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis <somewhere>/kegalle_repo
uv venv <somewhere>/venv-kegalle --python 3.12
uv pip install --python <somewhere>/venv-kegalle/bin/python numpy pandas scipy python-calamine openpyxl
bash replication/kegalle2025/run_all.sh <somewhere>/kegalle_repo <somewhere>/venv-kegalle/bin/python <outdir>
```

Every script runs with `python -I` from outside the cloned (untrusted) repository; the first
run parses ~570 MB of xlsx (a few minutes; cached in `<outdir>/cache`). Optional checks need
`ruptures` (k02b: our PELT vs `ruptures.Pelt`, 684/684 identical change points).

| Script | Reproduces |
|---|---|
| `kegalle_common.py` | helpers (time mapping parser, GOTOES reader, Tobii column names, RM-ANOVA, GPS boundaries) |
| `k00_inventory.py` | inventory of the released data |
| `k01_speed.py` | Table 2 (speed per segment) and speed tests |
| `k02_speed_changepoints.py` | PELT speed change points (Sec. 4.1.2, Fig. 5), penalty sweep |
| `k02b_check_pelt.py` | verification against `ruptures` |
| `k03_fixations.py` | Table 3, fixation count per km and duration |
| `k04_dispersion.py` | Table 3, "gaze/acc dispersion" (as coded and as described) |
| `k05_encounters_correlations.py` | Table 4, Fig. 7 |
| `k06_harmonised_gaze_head.py` | NOT in the paper: angle-based gaze and head metrics comparable with Aria |
| `k07_compare_with_paper.py` | `paper_vs_ours.csv` |

Verified on 2026-10-15: two independent runs (original location and this folder) gave
identical `paper_vs_ours.csv`. Findings and limits: `docs/literature/kegalle_replication.md`.
