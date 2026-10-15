#!/usr/bin/env python3
"""k07_compare_with_paper.py - collects the numbers produced by k01-k05 next to the values printed
in Kegalle et al. (2025, Proc. ACM IMWUT 9(1), DOI 10.1145/3712284, CC BY 4.0) into one CSV.
Data: github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
(no LICENSE file; cite the paper). Own code.

Usage: python -I k07_compare_with_paper.py --out OUT
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    o = Path(ap.parse_args().out)
    rows = []

    def add(item, seg, paper, ours, source, note=""):
        rows.append(dict(item=item, segment=seg, paper=paper, ours=ours,
                         diff=(None if paper is None or ours is None else round(ours - paper, 4)), source=source, note=note))

    sp = json.loads((o / "k01_speed_summary_nozeros_timemapping_gpsfallback.json").read_text())
    for s in ("1", "2", "3"):
        c = sp["table2_comparison"][s]
        for k in ("mean", "sd", "min", "max"):
            add(f"Table2 speed {k} (km/h)", s, c["paper"][k], round(c["ours"][k], 3), "k01 nozeros, TimeMapping + GPS fallback for P4")
    st = sp["stats"]
    add("Speed RM-ANOVA F", "all", 9.95, round(st["rm_anova"]["F"], 3), "k01")
    pt = {(p["a"], p["b"]): p["t"] for p in st["paired_t"]}
    add("Speed paired t ped vs cycle", "1-2", -4.338, round(pt[(1, 2)], 3), "k01")
    add("Speed paired t cycle vs road", "2-3", 2.80, round(pt[(2, 3)], 3), "k01")
    add("Speed paired t ped vs road (paper: n.s.)", "1-3", None, round(pt[(1, 3)], 3), "k01",
        "paper text names cycle-vs-roadway both as significant and as n.s.; the n.s. pair must be ped-vs-road")

    cp = json.loads((o / "k02_cp_pen30_keepzeros.json").read_text())["ours"]
    for s, pm, psd in (("1", 7.9, 4.1), ("2", 4.3, 1.7), ("3", 10.2, 5.9)):
        add("Change points per km, mean", s, pm, round(cp["mean_per_km"][s], 3), "k02 PELT l2 pen=30 (post-hoc), zeros kept",
            "penalty grid not published; pen=30 is the value closest to the paper")
        add("Change points per km, SD", s, psd, round(cp["sd_per_km"][s], 3), "k02")
    add("Change points total", "all", 371, cp["total"], "k02")

    fx = json.loads((o / "k03_fixations_summary.json").read_text())["ours"]
    for s, (pm, psd) in {"1": (454.83, 84.58), "2": (460.20, 77.01), "3": (545.05, 113.9)}.items():
        add("Table3 fixations per km mean", s, pm, round(fx["fix_per_km"]["mean"][s], 2), "k03 (lengths 1.36/0.74/0.65)")
        add("Table3 fixations per km SD", s, psd, round(fx["fix_per_km"]["sd"][s], 2), "k03")
    for s, (pm, psd) in {"1": (371.8, 89.3), "2": (332.4, 90.4), "3": (295.3, 68.8)}.items():
        add("Table3 fixation duration mean (ms)", s, pm, round(fx["fix_dur_ms"]["mean"][s], 2), "k03")
        add("Table3 fixation duration SD (ms)", s, psd, round(fx["fix_dur_ms"]["sd"][s], 2), "k03")
    add("Fixations/km RM-ANOVA F", "all", 10.5, round(fx["fix_per_km"]["rm_anova"]["F"], 3), "k03")
    add("Fixation duration RM-ANOVA F", "all", 23.3, round(fx["fix_dur_ms"]["rm_anova"]["F"], 3), "k03")

    ds = json.loads((o / "k04_dispersion_summary.json").read_text())["ours"]
    for s, (pm, psd) in {"1": (0.61, 0.08), "2": (0.66, 0.06), "3": (0.64, 0.11)}.items():
        add("Table3 gaze dispersion mean", s, pm, round(ds["gaze_coded_seg_fix"]["mean"][s], 3), "k04 coded metric on unique fixations")
        add("Table3 gaze dispersion SD", s, psd, round(ds["gaze_coded_seg_fix"]["sd"][s], 3), "k04")
    for s, (pm, psd) in {"1": (0.88, 0.04), "2": (0.83, 0.11), "3": (0.86, 0.06)}.items():
        add("Table3 acc dispersion mean", s, pm, round(ds["acc_coded_seg"]["mean"][s], 3), "k04 coded metric, n=12")
        add("Table3 acc dispersion SD", s, psd, round(ds["acc_coded_seg"]["sd"][s], 3), "k04")

    en = json.loads((o / "k05_summary.json").read_text())
    for s in ("1", "2", "3"):
        for c in ("pedestrians", "cycles", "cars"):
            v = en["table4"][s][c]
            add(f"Table4 {c} per km mean", s, v["paper"][0], round(v["ours_mean"], 2), "k05",
                "segment-3 sheet is a duplicate of segment 2 in the public file" if s == "3" else "")
            add(f"Table4 {c} per km SD", s, v["paper"][1], round(v["ours_sd"], 2), "k05")
    fig7 = pd.read_csv(o / "k05_fig7_correlations.csv")
    for _, r in fig7.iterrows():
        add(f"Fig7 r({r.metric},{r.encounter})", str(r.segment), r.paper, round(r.pearson, 3), "k05 Pearson",
            f"n={r.n}, p={r.pearson_p:.3f}" + ("; roadway encounters unavailable" if r.segment == 3 else ""))
    df = pd.DataFrame(rows)
    df.to_csv(o / "k07_paper_vs_ours.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
