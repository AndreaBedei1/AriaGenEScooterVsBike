#!/usr/bin/env python3
"""k03_fixations.py - fixation count per km and mean fixation duration per segment
(Kegalle et al. 2025, Sec. 3.6.1 p. 9, Sec. 4.1.3 pp. 11-12, Table 3 columns 1-2, Fig. 6a).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation.

Input: Tobii Pro Lab "Data" exports (Tobii Pro Glasses 3, gaze 50 Hz, fixation filter
"Tobii I-VT (Attention)" - i.e. fixations are NOT computed by the authors' code but by Tobii Pro
Lab and delivered in 'Eye movement type' / 'Gaze event duration' / 'Fixation point X|Y').

Steps (original: 'average_fixation_count __fixation_duration.ipynb'):
  1. segment by 'Recording timestamp [ms]' with the Tobii ms bounds of the TimeMapping sheet,
     inclusive                                                        [cell 3, lines 4-6]
  2. de-duplicate the sample-level rows into fixation events with a groupby on
     (event type, event duration, fixation X, fixation Y) - NaN keys dropped  [cell 4, line 10]
     (we also report the cleaner de-duplication by 'Eye movement type index')
  3. fixation count = number of unique rows                           [cell 5, line 9]
     -> divided by the segment length in km (1.36 / 0.65 / 0.74 km, Fig. 3; NOT in the code)
  4. mean fixation duration = mean 'Gaze event duration [ms]'          [cell 6, line 9]
  5. Shapiro-Wilk, ANOVA (paper: "within-subject"), Tukey HSD (paper p. 12; not in the code).

Usage: python -I k03_fixations.py --repo REPO --out OUT [--cache OUT/cache/public]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402

import kegalle_common as kc  # noqa: E402

PAPER_T3 = {
    "fix_per_km": {1: (454.83, 84.58), 2: (460.20, 77.01), 3: (545.05, 113.9)},
    "fix_dur_ms": {1: (371.8, 89.3), 2: (332.4, 90.4), 3: (295.3, 68.8)},
    "anova_F": {"fix_per_km": 10.5, "fix_dur_ms": 23.3},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None, help="pickle cache dir for parsed xlsx (default OUT/cache/public)")
    a = ap.parse_args()
    repo, out = Path(a.repo), Path(a.out)
    cache = Path(a.cache) if a.cache else out / "cache" / "public"
    tm = kc.read_timemapping(repo / "data" / "TimeMapping_BikeComputer_EyeTracker.xlsx")
    rows = []
    for f in sorted((repo / "data" / "Data" / "Gaze data").glob("*.xlsx"), key=lambda p: int(kc.pid_from_name(p.name)[1:])):
        pid = kc.pid_from_name(f.name)
        tp = tm[tm.participant == pid]
        if tp.empty or tp.tobii_start_ms.isna().any():
            continue
        g = kc.read_gaze_xlsx(f, cache)
        for _, r in tp.iterrows():
            seg = int(r.segment)
            s = kc.tobii_segment(g, r.tobii_start_ms, r.tobii_end_ms)
            u = kc.unique_fixations_as_coded(s)
            ui = kc.unique_fixations_by_index(s)
            et = s[s["Sensor"] == "Eye Tracker"]
            rows.append(
                dict(
                    participant=pid,
                    segment=seg,
                    seg_dur_s=(r.tobii_end_ms - r.tobii_start_ms) / 1000,
                    gaze_sample_pct=100 * et["Gaze point X [MCS px]"].notna().mean(),
                    n_fix_coded=len(u),
                    n_fix_index=len(ui),
                    fix_per_km=len(u) / kc.SEGMENT_KM[seg],
                    fix_per_km_index=len(ui) / kc.SEGMENT_KM[seg],
                    fix_per_min=len(u) / ((r.tobii_end_ms - r.tobii_start_ms) / 60000),
                    fix_dur_ms=u["Gaze event duration [ms]"].mean(),
                    fix_dur_ms_index=ui["dur"].mean(),
                    fix_dur_median_ms=u["Gaze event duration [ms]"].median(),
                )
            )
        print(f"  {pid} done", file=sys.stderr)
    df = pd.DataFrame(rows)
    df.to_csv(out / "k03_fixations_by_participant_segment.csv", index=False)
    res = {"n_participants": int(df.participant.nunique()), "paper_table3": PAPER_T3, "ours": {}}
    for col in ["fix_per_km", "fix_per_km_index", "fix_dur_ms", "fix_dur_ms_index", "fix_per_min"]:
        wide = df.pivot(index="participant", columns="segment", values=col)
        res["ours"][col] = kc.full_stats(wide)
    (out / "k03_fixations_summary.json").write_text(json.dumps(kc.jsonable(res), indent=2))
    for col in ["fix_per_km", "fix_dur_ms", "fix_per_km_index", "fix_dur_ms_index", "fix_per_min"]:
        st = res["ours"][col]
        print(col, "n=", st["n_complete"], {k: f"{st['mean'][k]:.2f} ({st['sd'][k]:.2f})" for k in (1, 2, 3)},
              "RM-F=%.2f p=%.3g | 1-way F=%.2f p=%.3g" % (st["rm_anova"]["F"], st["rm_anova"]["p"],
                                                         st["oneway_anova_between"]["F"], st["oneway_anova_between"]["p"]),
              "Tukey:", [(t["a"], t["b"], round(t["p"], 4)) for t in st["tukey_hsd_between"]],
              "paired:", [(t["a"], t["b"], round(t["t"], 2), round(t["p"], 4)) for t in st["paired_t"]],
              "SW p:", [round(x["p"], 3) for x in st["shapiro"]])


if __name__ == "__main__":
    main()
