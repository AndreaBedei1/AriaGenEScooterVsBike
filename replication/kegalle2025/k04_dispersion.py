#!/usr/bin/env python3
"""k04_dispersion.py - "gaze dispersion" and "accelerometer (head-movement) dispersion" per segment
(Kegalle et al. 2025, Sec. 3.6.1 p. 9, Sec. 4.1.3 p. 12, Table 3 columns 3-4, Fig. 6b).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation.

The paper (p. 9, following Wintersberger et al. 2022) describes: "average values for gaze standard
deviation based on fixations in the x and y axes ... Euclidean distance using normalised pixel
values", and the same for accelerometer x, y, z ("head movements").
The code does something different (average_gaze_dispersion.ipynb cell 1-3;
average_acc_dispersion.ipynb cell 1-3):
    x' = (x - min x) / (max x - min x)     (min-max over the file it is given, i.e. a segment)
    d_i = sqrt(x'_i^2 + y'_i^2)            (+ z'^2 for the accelerometer)
    dispersion = mean_i d_i
i.e. the mean distance of every normalised SAMPLE from the (min, min) corner of its own bounding
box - not a standard deviation, and on raw 'Gaze point X/Y' samples, not on fixations. For roughly
centred data this quantity is ~0.71 (2-D) and ~0.87 (3-D) by construction, which is what Table 3
reports (0.61-0.66 and 0.83-0.88). We compute:
  coded_seg   : the coded metric with min/max taken within each segment (most likely usage)
  coded_rec   : same, with min/max over the whole recording
  coded_seg_fix / coded_seg_fixsamples : the coded metric applied to unique fixation points /
                to the sample-level fixation rows (the variant that matches Table 3 best)
  sd_fix_norm : as described - sqrt(SD(x/W)^2 + SD(y/H)^2) of unique fixation points, W x H =
                1920 x 1080 scene-camera pixels (Tobii Pro Glasses 3)
  sd_gaze_norm: same on all gaze samples
  acc_sd      : sqrt(SD(ax)^2 + SD(ay)^2 + SD(az)^2) in m/s^2 (as described; matches the
                [m/s^2] unit printed in Table 3)
P16 and P25 exports contain no accelerometer/gyroscope columns -> acc metrics n = 12.

Usage: python -I k04_dispersion.py --repo REPO --out OUT
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

import kegalle_common as kc  # noqa: E402

PAPER_T3 = {"gaze_disp": {1: (0.61, 0.08), 2: (0.66, 0.06), 3: (0.64, 0.11)},
            "acc_disp": {1: (0.88, 0.04), 2: (0.83, 0.11), 3: (0.86, 0.06)}}
W, H = 1920.0, 1080.0
GX, GY = "Gaze point X [MCS px]", "Gaze point Y [MCS px]"
AX, AY, AZ = "Accelerometer X [m/s²]", "Accelerometer Y [m/s²]", "Accelerometer Z [m/s²]"


def mm(v: pd.Series, lo=None, hi=None) -> pd.Series:
    lo = v.min() if lo is None else lo
    hi = v.max() if hi is None else hi
    return (v - lo) / (hi - lo)


def coded_mean_norm(df: pd.DataFrame, cols, ref: pd.DataFrame | None = None) -> float:
    ref = df if ref is None else ref
    parts = [mm(df[c], ref[c].min(), ref[c].max()) ** 2 for c in cols]
    return float(np.sqrt(sum(parts)).mean())  # pandas: NaN rows propagate and are skipped by mean


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None)
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
        et_all = g[g["Sensor"] == "Eye Tracker"]
        acc_all = g[g[AX].notna()] if AX in g and g[AX].notna().any() else None
        for _, r in tp.iterrows():
            seg = int(r.segment)
            s = kc.tobii_segment(g, r.tobii_start_ms, r.tobii_end_ms)
            et = s[s["Sensor"] == "Eye Tracker"]
            u = kc.unique_fixations_as_coded(s)
            row = dict(participant=pid, segment=seg)
            row["gaze_coded_seg"] = coded_mean_norm(et, [GX, GY])
            row["gaze_coded_rec"] = coded_mean_norm(et, [GX, GY], ref=et_all)
            row["gaze_coded_seg_fix"] = coded_mean_norm(
                u.rename(columns={"Fixation point X [MCS px]": GX, "Fixation point Y [MCS px]": GY}), [GX, GY])
            fs = et[et["Eye movement type"] == "Fixation"].rename(
                columns={GX: "_gx", GY: "_gy", "Fixation point X [MCS px]": GX, "Fixation point Y [MCS px]": GY})
            row["gaze_coded_seg_fixsamples"] = coded_mean_norm(fs, [GX, GY])
            row["gaze_sd_fix_norm"] = float(np.hypot((u["Fixation point X [MCS px]"] / W).std(ddof=1),
                                                     (u["Fixation point Y [MCS px]"] / H).std(ddof=1)))
            row["gaze_sd_gaze_norm"] = float(np.hypot((et[GX] / W).std(ddof=1), (et[GY] / H).std(ddof=1)))
            if acc_all is not None:
                acc = s[s[AX].notna()]
                row["acc_coded_seg"] = coded_mean_norm(acc, [AX, AY, AZ])
                row["acc_coded_rec"] = coded_mean_norm(acc, [AX, AY, AZ], ref=acc_all)
                row["acc_sd_ms2"] = float(np.sqrt(sum(acc[c].std(ddof=1) ** 2 for c in (AX, AY, AZ))))
                row["acc_n"] = len(acc)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out / "k04_dispersion_by_participant_segment.csv", index=False)
    res = {"paper_table3": PAPER_T3, "ours": {}}
    for col in [c for c in df.columns if c.startswith(("gaze_", "acc_")) and c != "acc_n"]:
        wide = df.pivot(index="participant", columns="segment", values=col)
        st = kc.full_stats(wide)
        res["ours"][col] = st
        print(col, "n=", st["n_complete"], {k: f"{st['mean'][k]:.3f} ({st['sd'][k]:.3f})" for k in (1, 2, 3)},
              "RM-F=%.2f p=%.3g | 1-way F=%.2f p=%.3g" % (st["rm_anova"]["F"], st["rm_anova"]["p"],
                                                         st["oneway_anova_between"]["F"], st["oneway_anova_between"]["p"]),
              "SW p:", [round(x["p"], 3) for x in st["shapiro"]])
    (out / "k04_dispersion_summary.json").write_text(json.dumps(kc.jsonable(res), indent=2))


if __name__ == "__main__":
    main()
