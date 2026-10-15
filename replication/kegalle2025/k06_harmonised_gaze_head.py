#!/usr/bin/env python3
"""k06_harmonised_gaze_head.py - Aria-comparable (angle-based) gaze and head metrics computed on the
public Kegalle et al. (2025) Tobii exports. NOT an analysis of the paper: this is our own
harmonised re-analysis, meant as an external reference for Project Aria Gen 2 data
(eye gaze 30 Hz in CPF angles, IMU gyroscope).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation.

Per participant x segment (Tobii windows of the TimeMapping sheet):
  * eye-in-head gaze direction: mean of the left/right 'Gaze direction [HUCS norm]' unit vectors
    (one eye if only one is valid); yaw = atan2(x, z), pitch = atan2(y, z) in degrees
    (sign convention irrelevant for the dispersion metrics below)
  * yaw SD, pitch SD, BCEA (P = 0.682: 2*k*pi*sd_yaw*sd_pitch*sqrt(1-rho^2), k = -ln(1-P)) [deg^2]
  * harmonised I-VT: gaze resampled to a 30 Hz grid (sample-and-hold of the last valid sample
    within 40 ms, otherwise missing), angular speed between consecutive grid samples,
    fixation = run of samples with speed < 50 deg/s lasting >= 100 ms (the provisional
    parameters of our Aria pipeline); fixations per minute, per km, mean duration
  * same I-VT on the native 50 Hz samples (to separate the effect of the sampling rate)
  * head: gyroscope magnitude |omega| (deg/s): mean and P95 (12 participants; P16/P25 lack IMU)
Segment lengths: GPS-consistent 1.36 / 0.74 / 0.65 km (see kegalle_common.SEGMENT_KM).

Usage: python -I k06_harmonised_gaze_head.py --repo REPO --out OUT [--vt 50] [--min-fix-ms 100] [--hz 30]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import kegalle_common as kc  # noqa: E402

DIR_L = ["Gaze direction left X [HUCS norm]", "Gaze direction left Y [HUCS norm]", "Gaze direction left Z [HUCS norm]"]
DIR_R = ["Gaze direction right X [HUCS norm]", "Gaze direction right Y [HUCS norm]", "Gaze direction right Z [HUCS norm]"]
GYR = ["Gyro X [°/s]", "Gyro Y [°/s]", "Gyro Z [°/s]"]


def read_dirs(path: Path) -> pd.DataFrame:
    """Read the gaze-direction and gyroscope columns (not part of the shared cache)."""
    df = pd.read_excel(path, sheet_name=0, engine=kc._excel_engine())
    ren = {}
    for name in DIR_L + DIR_R + GYR + ["Recording timestamp [ms]"]:
        base = name.split(" [")[0]
        if name not in df.columns and base in df.columns:
            ren[base] = name
    df = df.rename(columns=ren)
    keep = ["Recording timestamp [ms]", "Sensor"] + [c for c in DIR_L + DIR_R + GYR if c in df.columns]
    return df[keep].copy()


def cyclopean(et: pd.DataFrame) -> pd.DataFrame:
    L = et[DIR_L].to_numpy(float)
    R = et[DIR_R].to_numpy(float)
    v = np.where(np.isnan(L), 0, L) + np.where(np.isnan(R), 0, R)
    nvalid = (~np.isnan(L[:, 0])).astype(int) + (~np.isnan(R[:, 0])).astype(int)
    v[nvalid == 0] = np.nan
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    out = pd.DataFrame({"t": et["Recording timestamp [ms]"].to_numpy(float) / 1000.0, "x": v[:, 0], "y": v[:, 1], "z": v[:, 2]})
    out["yaw"] = np.degrees(np.arctan2(out.x, out.z))
    out["pitch"] = np.degrees(np.arctan2(out.y, out.z))
    return out


def ivt(t: np.ndarray, vec: np.ndarray, vt: float, min_fix_s: float) -> tuple[int, float]:
    """Count fixations (runs below vt deg/s, duration >= min_fix_s); missing samples break runs."""
    dots = np.clip(np.einsum("ij,ij->i", vec[1:], vec[:-1]), -1, 1)
    ang = np.degrees(np.arccos(dots))
    dt = np.diff(t)
    speed = ang / dt
    slow = speed < vt  # NaN -> False -> breaks a run
    n, durs, start = 0, [], None
    for i, s in enumerate(np.append(slow, False)):
        if s and start is None:
            start = i
        elif not s and start is not None:
            dur = t[i] - t[start]
            if dur >= min_fix_s:
                n += 1
                durs.append(dur)
            start = None
    return n, float(np.mean(durs) * 1000) if durs else float("nan")


def resample(c: pd.DataFrame, hz: float, hold_s: float = 0.04) -> tuple[np.ndarray, np.ndarray]:
    valid = c.dropna(subset=["x"])
    grid = np.arange(c.t.min(), c.t.max(), 1.0 / hz)
    idx = np.searchsorted(valid.t.to_numpy(), grid, side="right") - 1
    ok = (idx >= 0)
    vec = np.full((len(grid), 3), np.nan)
    tv = valid.t.to_numpy()
    xv = valid[["x", "y", "z"]].to_numpy()
    sel = np.where(ok)[0]
    near = grid[sel] - tv[idx[sel]] <= hold_s
    vec[sel[near]] = xv[idx[sel[near]]]
    return grid, vec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vt", type=float, default=50.0)
    ap.add_argument("--min-fix-ms", type=float, default=100.0)
    ap.add_argument("--hz", type=float, default=30.0)
    a = ap.parse_args()
    repo, out = Path(a.repo), Path(a.out)
    tm = kc.read_timemapping(repo / "data" / "TimeMapping_BikeComputer_EyeTracker.xlsx")
    k_bcea = -math.log(1 - 0.682)
    rows = []
    for f in sorted((repo / "data" / "Data" / "Gaze data").glob("*.xlsx"), key=lambda p: int(kc.pid_from_name(p.name)[1:])):
        pid = kc.pid_from_name(f.name)
        tp = tm[tm.participant == pid]
        if tp.empty or tp.tobii_start_ms.isna().any():
            continue
        df = read_dirs(f)
        et = df[df["Sensor"] == "Eye Tracker"]
        gy = df[df[GYR[0]].notna()] if GYR[0] in df and df[GYR[0]].notna().any() else None
        for _, r in tp.iterrows():
            seg = int(r.segment)
            e = kc.tobii_segment(et, r.tobii_start_ms, r.tobii_end_ms)
            c = cyclopean(e)
            cv = c.dropna(subset=["x"])
            sy, sp = cv.yaw.std(ddof=1), cv.pitch.std(ddof=1)
            rho = np.corrcoef(cv.yaw, cv.pitch)[0, 1]
            dur_min = (r.tobii_end_ms - r.tobii_start_ms) / 60000
            g_t, g_v = resample(c, a.hz)
            n30, d30 = ivt(g_t, g_v, a.vt, a.min_fix_ms / 1000)
            n50, d50 = ivt(c.t.to_numpy(), c[["x", "y", "z"]].to_numpy(), a.vt, a.min_fix_ms / 1000)
            row = dict(participant=pid, segment=seg, valid_pct=100 * len(cv) / max(len(c), 1),
                       yaw_sd_deg=sy, pitch_sd_deg=sp, bcea_deg2=2 * k_bcea * math.pi * sy * sp * math.sqrt(max(0, 1 - rho ** 2)),
                       ivt30_fix_per_min=n30 / dur_min, ivt30_fix_per_km=n30 / kc.SEGMENT_KM[seg], ivt30_mean_dur_ms=d30,
                       ivt50_fix_per_min=n50 / dur_min, ivt50_mean_dur_ms=d50)
            if gy is not None:
                gs = kc.tobii_segment(gy, r.tobii_start_ms, r.tobii_end_ms)
                w = np.linalg.norm(gs[GYR].to_numpy(float), axis=1)
                row.update(gyro_mean_dps=float(np.mean(w)), gyro_p95_dps=float(np.percentile(w, 95)))
            rows.append(row)
        print(f"  {pid}", file=sys.stderr)
    d = pd.DataFrame(rows)
    d.to_csv(out / "k06_harmonised_by_participant_segment.csv", index=False)
    res = {"config": vars(a), "segment_km": kc.SEGMENT_KM, "metrics": {}}
    for col in [c for c in d.columns if c not in ("participant", "segment")]:
        st = kc.full_stats(d.pivot(index="participant", columns="segment", values=col))
        res["metrics"][col] = {k: st[k] for k in ("n_complete", "mean", "sd", "rm_anova", "paired_t")}
        print(col, "n=", st["n_complete"], {k: f"{st['mean'][k]:.2f} ({st['sd'][k]:.2f})" for k in (1, 2, 3)},
              "RM-F=%.2f p=%.3g" % (st["rm_anova"]["F"], st["rm_anova"]["p"]))
    (out / "k06_harmonised_summary.json").write_text(json.dumps(kc.jsonable(res), indent=2))


if __name__ == "__main__":
    main()
