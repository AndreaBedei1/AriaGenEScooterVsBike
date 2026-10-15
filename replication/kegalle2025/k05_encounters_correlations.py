#!/usr/bin/env python3
"""k05_encounters_correlations.py - road-user "encounters" per km (Table 4) and their correlation
with the rider metrics (Fig. 7) (Kegalle et al. 2025, Sec. 3.6.1 pp. 9-10, Sec. 4.1.4 p. 13).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation.

The encounter counts in 'data/Encounter Counts.xlsx' are the OUTPUT of the authors' video pipeline
(YOLOv8x + ultralytics tracking on a centre crop, then a manual correction - see
'yolov8_region_counter (updated).ipynb' and 'Object count correction method.ipynb'); the videos are
not public, so the counts cannot be regenerated. Columns: pedestrians (COCO class 0 'person'),
cycles (class 1 'bicycle'), cars (class 2 'car' only; trucks/buses/motorbikes not counted).
!! In the public file the sheets 'Route Segment 2' and 'Route Segment 3' are identical, so the
   roadway counts are missing; segment-3 results below are computed on a copy of the cycle-lane
   counts and are reported only to document the problem.
Correlation method is not stated in the paper; we report Pearson and Spearman (pairwise complete,
participants present in both tables).

Usage: python -I k05_encounters_correlations.py --repo REPO --out OUT --cp-csv OUT/k02_cp_pen30_keepzeros.csv
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

import kegalle_common as kc  # noqa: E402

PAPER_T4 = {1: {"pedestrians": (31.1, 14.5), "cycles": (4.5, 2.8), "cars": (71.8, 20.6)},
            2: {"pedestrians": (4.2, 2.9), "cycles": (2.4, 2.0), "cars": (83.7, 49.3)},
            3: {"pedestrians": (17.1, 8.4), "cycles": (1.4, 1.7), "cars": (187.2, 41.4)}}
# Fig. 7 (p. 14): rows metric x segment, columns pedestrian, cycle, car, total
PAPER_FIG7 = {
    ("n_cp", 1): [0.24, 0.19, 0.22, 0.31], ("n_cp", 2): [-0.29, -0.09, 0.17, 0.16], ("n_cp", 3): [0.19, 0.25, 0.35, 0.37],
    ("fix_count", 1): [-0.14, 0.01, -0.03, -0.09], ("fix_count", 2): [0.35, 0.38, -0.37, -0.40], ("fix_count", 3): [0.08, 0.36, 0.29, 0.37],
    ("fix_dur", 1): [0.31, 0.12, 0.32, 0.42], ("fix_dur", 2): [-0.23, -0.34, 0.40, 0.44], ("fix_dur", 3): [-0.06, -0.23, 0.17, 0.23],
    ("acc_disp", 1): [0.49, 0.03, 0.25, 0.36], ("acc_disp", 2): [0.03, 0.54, 0.12, 0.14], ("acc_disp", 3): [-0.04, -0.69, 0.23, 0.17],
    ("gaze_disp", 1): [0.15, 0.34, 0.14, 0.21], ("gaze_disp", 2): [0.11, -0.35, 0.07, 0.08], ("gaze_disp", 3): [0.07, 0.34, -0.14, -0.16],
}
ENC = ["pedestrians", "cycles", "cars", "total"]


def read_encounters(path: Path) -> pd.DataFrame:
    xl = pd.ExcelFile(path, engine=kc._excel_engine())
    rows = []
    for seg, sh in enumerate(xl.sheet_names, start=1):
        d = pd.read_excel(path, sheet_name=sh, engine=kc._excel_engine())
        d.columns = [str(c).strip() for c in d.columns]
        for _, r in d.iterrows():
            rows.append(dict(participant=str(r.iloc[0]).strip(), segment=seg, pedestrians=r["pedestrians"],
                             cycles=r["cycles"], cars=r["cars"]))
    e = pd.DataFrame(rows)
    e["total"] = e.pedestrians + e.cycles + e.cars
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cp-csv", required=True, help="per participant x segment change-point table from k02")
    ap.add_argument("--fix-csv", default=None, help="default OUT/k03_fixations_by_participant_segment.csv")
    ap.add_argument("--disp-csv", default=None, help="default OUT/k04_dispersion_by_participant_segment.csv")
    ap.add_argument("--gaze-col", default="gaze_coded_seg_fix")
    ap.add_argument("--acc-col", default="acc_coded_seg")
    a = ap.parse_args()
    repo, out = Path(a.repo), Path(a.out)
    enc = read_encounters(repo / "data" / "Encounter Counts.xlsx")
    for c in ENC:
        enc[c + "_per_km"] = enc[c] / enc.segment.map(kc.SEGMENT_KM)
    enc.to_csv(out / "k05_encounters_long.csv", index=False)

    t4 = {}
    for seg in (1, 2, 3):
        e = enc[enc.segment == seg]
        t4[seg] = {c: dict(ours_mean=float(e[c + "_per_km"].mean()), ours_sd=float(e[c + "_per_km"].std(ddof=1)),
                           ours_mean_fig3_lengths=float((e[c] / kc.SEGMENT_KM_FIG3[seg]).mean()),
                           paper=PAPER_T4[seg].get(c)) for c in ["pedestrians", "cycles", "cars"]}
        t4[seg]["n"] = int(len(e))

    cp = pd.read_csv(a.cp_csv)[["participant", "segment", "n_cp"]]
    fx = pd.read_csv(a.fix_csv or out / "k03_fixations_by_participant_segment.csv")
    fx = fx.rename(columns={"fix_per_km": "fix_count", "fix_dur_ms": "fix_dur"})[["participant", "segment", "fix_count", "fix_dur"]]
    ds = pd.read_csv(a.disp_csv or out / "k04_dispersion_by_participant_segment.csv")
    ds = ds.rename(columns={a.gaze_col: "gaze_disp", a.acc_col: "acc_disp"})[["participant", "segment", "gaze_disp", "acc_disp"]]
    m = enc.merge(cp, on=["participant", "segment"], how="left").merge(fx, on=["participant", "segment"], how="left") \
        .merge(ds, on=["participant", "segment"], how="left")
    m.to_csv(out / "k05_merged_metrics_encounters.csv", index=False)

    corr_rows = []
    for (metric, seg), paper_vals in PAPER_FIG7.items():
        d = m[m.segment == seg]
        for j, e in enumerate(ENC):
            x = d[[metric, e]].dropna()
            n = len(x)
            pr = stats.pearsonr(x[metric], x[e]) if n > 2 and x[metric].std() > 0 else (np.nan, np.nan)
            sr = stats.spearmanr(x[metric], x[e]) if n > 2 else (np.nan, np.nan)
            corr_rows.append(dict(metric=metric, segment=seg, encounter=e, n=n, pearson=float(pr[0]), pearson_p=float(pr[1]),
                                  spearman=float(sr[0]), paper=paper_vals[j]))
    cr = pd.DataFrame(corr_rows)
    cr["abs_diff_pearson"] = (cr.pearson - cr.paper).abs()
    cr["abs_diff_spearman"] = (cr.spearman - cr.paper).abs()
    cr.to_csv(out / "k05_fig7_correlations.csv", index=False)
    agg = cr.groupby("segment")[["abs_diff_pearson", "abs_diff_spearman"]].mean().to_dict()
    bym = cr[cr.segment < 3].groupby("metric")[["abs_diff_pearson", "abs_diff_spearman"]].mean().to_dict()
    res = dict(table4=t4, sheets_2_and_3_identical=bool((enc[enc.segment == 2][ENC].values == enc[enc.segment == 3][ENC].values).all()),
               fig7_mean_abs_diff_by_segment=agg, fig7_mean_abs_diff_by_metric_seg1_2=bym,
               config=dict(cp_csv=str(a.cp_csv), gaze_col=a.gaze_col, acc_col=a.acc_col, segment_km=kc.SEGMENT_KM))
    (out / "k05_summary.json").write_text(json.dumps(kc.jsonable(res), indent=2))
    print(json.dumps(kc.jsonable(res), indent=1))
    print(cr[cr.segment < 3].round(2).to_string())


if __name__ == "__main__":
    main()
