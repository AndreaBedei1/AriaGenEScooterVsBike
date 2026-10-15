#!/usr/bin/env bash
# Re-run the independent re-analysis of the Kegalle et al. (2025) public data.
# Usage: run_all.sh <path-to-cloned-repo> <python-with-numpy-pandas-scipy-calamine> [outdir]
# Every script is run with `python -I` from outside the cloned (untrusted) repository.
set -euo pipefail
REPO=${1:?repo path}; PY=${2:?python}; HERE=$(cd "$(dirname "$0")" && pwd); OUT=${3:-$HERE/outputs}
cd "$HERE/.."   # never run from inside the clone
# EXTRA_GAZE (optional): directory with the 6 gaze xlsx the authors removed in commit f16da5d,
# extracted with `git show bb0cf01:"data/Data/Gaze data/P12.xlsx"` etc. (used only to check the 75% rule)
"$PY" -I "$HERE/k00_inventory.py" --repo "$REPO" --out "$OUT" ${EXTRA_GAZE:+--extra-gaze "$EXTRA_GAZE"}
for seg in timemapping+gpsfallback timemapping gps; do
  "$PY" -I "$HERE/k01_speed.py" --repo "$REPO" --out "$OUT" --segmentation "$seg"
  "$PY" -I "$HERE/k01_speed.py" --repo "$REPO" --out "$OUT" --segmentation "$seg" --keep-zeros
done
"$PY" -I "$HERE/k02_speed_changepoints.py" --repo "$REPO" --out "$OUT" --aic none --pen 30
"$PY" -I "$HERE/k02_speed_changepoints.py" --repo "$REPO" --out "$OUT" --aic original --pen-lo 1 --pen-hi 30 --pen-num 100
"$PY" -I "$HERE/k02_speed_changepoints.py" --repo "$REPO" --out "$OUT" --sweep
"$PY" -I "$HERE/k02_speed_changepoints.py" --repo "$REPO" --out "$OUT" --sweep --drop-zeros
"$PY" -I "$HERE/k03_fixations.py" --repo "$REPO" --out "$OUT"
"$PY" -I "$HERE/k04_dispersion.py" --repo "$REPO" --out "$OUT"
"$PY" -I "$HERE/k05_encounters_correlations.py" --repo "$REPO" --out "$OUT" --cp-csv "$OUT/k02_cp_pen30_keepzeros.csv"
# optional checks (need `ruptures`, `matplotlib`):
#   "$PY" -I "$HERE/k02b_check_pelt.py" --repo "$REPO" --out "$OUT"
#   (the harness that executes the authors' original notebooks is not distributed here)
"$PY" -I "$HERE/k06_harmonised_gaze_head.py" --repo "$REPO" --out "$OUT"
"$PY" -I "$HERE/k07_compare_with_paper.py" --out "$OUT"
