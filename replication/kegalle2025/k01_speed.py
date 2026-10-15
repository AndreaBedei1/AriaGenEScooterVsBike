#!/usr/bin/env python3
"""k01_speed.py - average speed per route segment (Kegalle et al. 2025, Sec. 3.6.1 and 4.1.1, Table 2).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation.

Steps and the original code they correspond to:
  1. Read the GOTOES CSV export of the Garmin Edge 130 Plus FIT file (1 Hz, `speed` in km/h).
     [speed_data_processing.ipynb cell 2, lines 2-10: reads CSV, adds `time_delta` hours]
     We infer the hour shift (it is +16 h for all 19 files) instead of passing it by hand.
  2. Cut the three segments with the hand-typed local times of TimeMapping_BikeComputer_EyeTracker.xlsx
     (inclusive bounds). [cell 4, lines 4-10: manual 1-based inclusive row ranges]
  3. Remove stand-still samples (speed == 0) - stated in the paper (Sec. 3.6.1, p. 8), NOT in the code.
  4. Mean speed per participant x segment; Table 2 = mean (SD), min, max over participants.
  5. Shapiro-Wilk per segment, one-way repeated-measures ANOVA, paired t-tests
     (paper p. 10: F = 9.95; t = -4.338 ped-vs-cycle, t = 2.80 "cycle-vs-roadway").
     None of these tests exists in the repository; they are reconstructed from the paper text.

Usage:
  python -I k01_speed.py --repo /path/to/kegalle_repo --out outputs/ [--keep-zeros]
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

PAPER_TABLE2 = {  # Table 2, p. 11: mean (SD), min, max in km/h
    1: dict(mean=16.70, sd=1.84, min=13.21, max=19.84),
    2: dict(mean=18.14, sd=1.00, min=15.82, max=19.65),
    3: dict(mean=17.11, sd=1.75, min=13.93, max=20.00),
}
PAPER_TESTS = dict(rm_anova_F=9.95, t_ped_vs_cycle=-4.338, t_cycle_vs_road=2.80)


def load_speed_files(repo: Path, tm: pd.DataFrame) -> dict:
    files = {}
    for f in sorted((repo / "data" / "Data" / "Speed data").glob("*.csv")):
        pid = kc.pid_from_name(f.name)
        tm_p = tm[tm.participant == pid]
        if tm_p.empty:
            continue
        d = kc.read_speed_csv(f)
        off = kc.infer_hour_offset(d.tod_s_file.iloc[0], tm_p.garmin_start_s.min())
        d["tod_local_s"] = (d["tod_s_file"] + off * 3600) % 86400
        d.attrs["hour_offset"] = off
        files[pid] = d
    return files


def segment_bounds(pid: str, d: pd.DataFrame, tm: pd.DataFrame, bpts, mode: str) -> tuple[dict, str, list]:
    """Return {segment: (start_s, end_s)} in local seconds-of-day, the source used, and the
    GPS-derived boundary times (for the comparison table)."""
    tp = tm[tm.participant == pid]
    tmb = {int(r.segment): (r.garmin_start_s, r.garmin_end_s) for _, r in tp.iterrows()}
    g = kc.gps_boundary_times(d, bpts)
    gpsb = {1: (g[0], g[1] - 1), 2: (g[1], g[2] - 1), 3: (g[2], g[3])}
    t0, t1 = d.tod_local_s.min(), d.tod_local_s.max()
    tm_inside = all(t0 - 5 <= a and b <= t1 + 5 for a, b in tmb.values())
    if mode == "gps":
        return gpsb, "gps", g
    if mode == "timemapping" or tm_inside:
        return tmb, "timemapping", g
    return gpsb, "gps-fallback", g


def segment_table(repo: Path, keep_zeros: bool, mode: str) -> pd.DataFrame:
    tm = kc.read_timemapping(repo / "data" / "TimeMapping_BikeComputer_EyeTracker.xlsx")
    files = load_speed_files(repo, tm)
    bpts = kc.boundary_points_from_reference(files, tm)
    rows = []
    for pid, d in files.items():
        bounds, src, g = segment_bounds(pid, d, tm, bpts, mode)
        tp = tm[tm.participant == pid].set_index("segment")
        for seg, (a, b) in bounds.items():
            s = d[(d.tod_local_s >= a) & (d.tod_local_s <= b)]
            v = s["speed"] if keep_zeros else s.loc[s["speed"] > 0, "speed"]
            rows.append(
                dict(
                    participant=pid,
                    segment=seg,
                    bounds_source=src,
                    start_s=a,
                    end_s=b,
                    tm_minus_gps_start_s=float(tp.loc[seg, "garmin_start_s"] - [g[0], g[1], g[2]][seg - 1]),
                    n_samples=len(s),
                    n_zero=int((s["speed"] == 0).sum()),
                    gps_distance_m=float(s.distance.iloc[-1] - s.distance.iloc[0]) if len(s) else 0.0,
                    mean_speed_kmh=float(v.mean()) if len(v) else float("nan"),
                    sd_speed_kmh=float(v.std(ddof=1)) if len(v) > 1 else float("nan"),
                    hour_offset=d.attrs["hour_offset"],
                )
            )
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-zeros", action="store_true", help="do not drop speed==0 samples")
    ap.add_argument("--segmentation", choices=["timemapping+gpsfallback", "timemapping", "gps"],
                    default="timemapping+gpsfallback",
                    help="segment boundaries: hand-typed TimeMapping times (authors), GPS boundary "
                         "crossings (ours), or TimeMapping with GPS fallback when the typed times fall "
                         "outside the file (only P4)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = ("keepzeros" if a.keep_zeros else "nozeros") + "_" + a.segmentation.replace("+", "_")

    long = segment_table(Path(a.repo), a.keep_zeros, a.segmentation)
    long.to_csv(out / f"k01_speed_by_participant_segment_{tag}.csv", index=False)
    wide = long.pivot(index="participant", columns="segment", values="mean_speed_kmh")
    st = kc.full_stats(wide)
    long["duration_s"] = long.end_s - long.start_s + 1
    seg_geo = long.groupby("segment")[["duration_s", "gps_distance_m", "n_zero"]].mean().to_dict()
    comp = {
        int(s): dict(
            ours=dict(mean=st["mean"][s], sd=st["sd"][s], min=st["min"][s], max=st["max"][s]),
            paper=PAPER_TABLE2[s],
        )
        for s in (1, 2, 3)
    }
    res = dict(
        variant=tag,
        n_participants=int(wide.shape[0]),
        bounds_source=long.groupby("participant").bounds_source.first().value_counts().to_dict(),
        tm_minus_gps_start_s_abs_median=float(long.tm_minus_gps_start_s.abs().median()),
        tm_minus_gps_start_s_abs_max=float(long.tm_minus_gps_start_s.abs().max()),
        segment_mean_duration_s=seg_geo["duration_s"],
        segment_mean_gps_distance_m=seg_geo["gps_distance_m"],
        table2_comparison=comp,
        stats=st,
        paper_tests=PAPER_TESTS,
    )
    (out / f"k01_speed_summary_{tag}.json").write_text(json.dumps(kc.jsonable(res), indent=2))
    print(json.dumps(kc.jsonable(dict(n=res["n_participants"], src=res["bounds_source"], table2=comp, rm_anova=st["rm_anova"],
                                      paired=st["paired_t"], shapiro=st["shapiro"],
                                      seg_dur=seg_geo["duration_s"], seg_dist=seg_geo["gps_distance_m"])), indent=1))


if __name__ == "__main__":
    main()
