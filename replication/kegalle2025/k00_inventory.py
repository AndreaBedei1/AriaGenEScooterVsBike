#!/usr/bin/env python3
"""k00_inventory.py - inventory of the public Kegalle et al. (2025) dataset.

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (paper licensed CC BY 4.0).
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis
       @ ed5c221 (2025-03-06). No LICENSE file in the repository (all rights reserved by
       default); cite the paper when using the data. This script is our own code.

What it does (no counterpart in the original repository, which has no inventory step):
  * speed CSVs  : rows, sampling interval, date, local clock offset, zero-speed samples,
                  which FIT fields are populated (GPS, altitude, ...).
  * gaze XLSXs  : Tobii Pro Lab export metadata, rows per sensor, sampling intervals,
                  gaze-sample percentage, availability of accelerometer/gyroscope.
  * TimeMapping : parsed segment boundaries and Garmin-vs-Tobii duration consistency.
  * Encounters  : sheet shapes and an identity check between sheets.

Usage:
  python -I k00_inventory.py --repo /path/to/kegalle_repo --out outputs/ [--extra-gaze DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # our own helper module only
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import kegalle_common as kc  # noqa: E402


def speed_inventory(speed_dir: Path, tm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in sorted(speed_dir.glob("*.csv"), key=lambda p: int(kc.pid_from_name(p.name)[1:])):
        pid = kc.pid_from_name(f.name)
        d = kc.read_speed_csv(f)
        dt = d["timestamp"].diff().dt.total_seconds()
        tm_p = tm[tm.participant == pid]
        off = kc.infer_hour_offset(d.tod_s_file.iloc[0], tm_p.garmin_start_s.min()) if len(tm_p) else None
        populated = [c for c in d.columns if not str(c).startswith("Unnamed") and d[c].notna().any()]
        rows.append(
            dict(
                participant=pid,
                file=f.name,
                bytes=f.stat().st_size,
                rows=len(d),
                first_timestamp_in_file=str(d.timestamp.iloc[0]),
                duration_s=(d.timestamp.iloc[-1] - d.timestamp.iloc[0]).total_seconds(),
                median_dt_s=float(dt.median()),
                n_gaps_gt1s=int((dt > 1).sum()),
                hour_offset_to_local=off,
                n_zero_speed=int((d.speed == 0).sum()),
                speed_mean_kmh=float(d.speed.mean()),
                speed_max_kmh=float(d.speed.max()),
                distance_end_m=float(d.distance.iloc[-1]),
                speed_vs_ddistance_ratio=float(
                    np.nanmedian((d.speed / (d.distance.diff() / dt * 3.6)).replace([np.inf, -np.inf], np.nan))
                ),
                in_timemapping=bool(len(tm_p)),
                populated_fields=";".join(populated),
            )
        )
    return pd.DataFrame(rows)


def gaze_inventory(gaze_dir: Path, cache: Path, tm: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for f in sorted(gaze_dir.glob("*.xlsx"), key=lambda p: int(kc.pid_from_name(p.name)[1:])):
        pid = kc.pid_from_name(f.name)
        df = kc.read_gaze_xlsx(f, cache / label)
        et = df[df["Sensor"] == "Eye Tracker"]
        ts_et = et["Recording timestamp [ms]"].to_numpy(float)
        gaze_ok = et["Gaze point X [MCS px]"].notna()
        either_valid = (et["Validity left"] == "Valid") | (et["Validity right"] == "Valid")
        acc_n = int(df["Accelerometer X [m/s²]"].notna().sum()) if "Accelerometer X [m/s²]" in df else 0
        gyr_n = int(df["Gyro X [°/s]"].notna().sum()) if "Gyro X [°/s]" in df else 0
        mag_n = int(df["Magnetometer X [μT]"].notna().sum()) if "Magnetometer X [μT]" in df else 0
        acc_rows = df[df["Accelerometer X [m/s²]"].notna()] if acc_n else df.iloc[:0]
        mag_rows = df[df["Magnetometer X [μT]"].notna()] if mag_n else df.iloc[:0]
        tm_p = tm[tm.participant == pid]
        # gaze-sample percentage inside the three analysed segments only
        seg_pct = {}
        for _, r in tm_p.iterrows():
            if np.isnan(r.tobii_start_ms):
                continue
            s = kc.tobii_segment(et, r.tobii_start_ms, r.tobii_end_ms)
            seg_pct[int(r.segment)] = float(100 * s["Gaze point X [MCS px]"].notna().mean()) if len(s) else np.nan
        emt = et["Eye movement type"].value_counts().to_dict()
        rows.append(
            dict(
                set=label,
                participant=pid,
                file=f.name,
                bytes=f.stat().st_size,
                md5=hashlib.md5(f.read_bytes()).hexdigest(),
                recording_name=df["Recording name"].iloc[0],
                recording_date=df["Recording date"].iloc[0] if "Recording date" in df else None,
                media_wh=(f'{df["Recording media width"].iloc[0]}x{df["Recording media height"].iloc[0]}'
                          if "Recording media width" in df else None),
                unitless_export=bool(df["export_unitless_names"].iloc[0]),
                sensors=json.dumps(df["Sensor"].value_counts().to_dict()),
                recording_start_local=df["Recording start time"].iloc[0],
                recording_start_utc=df["Recording start time UTC"].iloc[0],
                recording_duration_s=float(df["Recording duration [ms]"].iloc[0]) / 1000,
                fixation_filter=df["Recording Fixation filter name"].iloc[0],
                rows_total=len(df),
                rows_eye_tracker=len(et),
                et_median_dt_ms=float(np.median(np.diff(ts_et))) if len(ts_et) > 1 else np.nan,
                gaze_sample_pct_whole=float(100 * gaze_ok.mean()),
                either_eye_valid_pct_whole=float(100 * either_valid.mean()),
                gaze_sample_pct_seg1=seg_pct.get(1, np.nan),
                gaze_sample_pct_seg2=seg_pct.get(2, np.nan),
                gaze_sample_pct_seg3=seg_pct.get(3, np.nan),
                n_fixation_events=int(et.loc[et["Eye movement type"] == "Fixation", "Eye movement type index"].nunique()),
                eye_movement_type_rows=json.dumps(emt),
                accelerometer_rows=acc_n,
                acc_median_dt_ms=float(np.median(np.diff(acc_rows["Recording timestamp [ms]"]))) if acc_n > 1 else np.nan,
                gyro_rows=gyr_n,
                magnetometer_rows=mag_n,
                mag_median_dt_ms=float(np.median(np.diff(mag_rows["Recording timestamp [ms]"]))) if mag_n > 1 else np.nan,
                gaze_x_min=float(et["Gaze point X [MCS px]"].min()),
                gaze_x_max=float(et["Gaze point X [MCS px]"].max()),
                gaze_y_min=float(et["Gaze point Y [MCS px]"].min()),
                gaze_y_max=float(et["Gaze point Y [MCS px]"].max()),
                in_timemapping_with_tobii=bool(len(tm_p) and tm_p.tobii_start_ms.notna().all()),
            )
        )
        print(f"  gaze {label} {pid}: {len(df)} rows; unitless-export={bool(df['export_unitless_names'].iloc[0])}", file=sys.stderr)
    return pd.DataFrame(rows)


def encounter_inventory(path: Path) -> dict:
    xl = pd.ExcelFile(path, engine=kc._excel_engine())
    sheets = {s: pd.read_excel(path, sheet_name=s, engine=kc._excel_engine()) for s in xl.sheet_names}
    names = list(sheets)
    ident = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = sheets[names[i]], sheets[names[j]]
            ident[f"{names[i]} == {names[j]}"] = bool(a.shape == b.shape and (a.values == b.values).all())
    return dict(
        sheets={s: dict(shape=list(d.shape), columns=[str(c) for c in d.columns]) for s, d in sheets.items()},
        participants=sorted({str(p).strip() for d in sheets.values() for p in d.iloc[:, 0]}, key=lambda s: int(s[1:])),
        identical_sheet_pairs=ident,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="path to the cloned Kegalle repository")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--extra-gaze", default=None,
                    help="optional directory with additional Tobii xlsx exports (e.g. files the authors "
                         "removed in commit f16da5d) to check the stated 75%% gaze-sample criterion")
    a = ap.parse_args()
    repo, out = Path(a.repo), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "cache"

    tm = kc.read_timemapping(repo / "data" / "TimeMapping_BikeComputer_EyeTracker.xlsx")
    tm["dur_diff_s"] = tm.garmin_dur_s - tm.tobii_dur_s
    tm.to_csv(out / "k00_timemapping_parsed.csv", index=False)

    sp = speed_inventory(repo / "data" / "Data" / "Speed data", tm)
    sp.to_csv(out / "k00_inventory_speed.csv", index=False)

    gz = gaze_inventory(repo / "data" / "Data" / "Gaze data", cache, tm, "public")
    if a.extra_gaze:
        gz = pd.concat([gz, gaze_inventory(Path(a.extra_gaze), cache, tm, "removed_in_history")], ignore_index=True)
    gz.to_csv(out / "k00_inventory_gaze.csv", index=False)

    enc = encounter_inventory(repo / "data" / "Encounter Counts.xlsx")

    tm_p = sorted(tm.participant.unique(), key=lambda s: int(s[1:]))
    summary = dict(
        timemapping_participants=tm_p,
        timemapping_participants_with_tobii=sorted(
            tm.loc[tm.tobii_start_ms.notna(), "participant"].unique(), key=lambda s: int(s[1:])),
        speed_participants=list(sp.participant),
        gaze_participants=list(gz.loc[gz.set == "public", "participant"]),
        encounters=enc,
        segments_with_abs_garmin_tobii_duration_diff_gt_2s=tm.loc[tm.dur_diff_s.abs() > 2,
            ["participant", "segment", "garmin_start_raw", "garmin_end_raw", "garmin_dur_s", "tobii_dur_s"]].to_dict("records"),
        tobii_gaps_between_segments=[
            dict(participant=p, seg=int(s), gap_s=float(g))
            for p, d in tm.groupby("participant")
            for s, g in zip(d.segment.iloc[1:], (d.tobii_start_ms.iloc[1:].to_numpy() - d.tobii_end_ms.iloc[:-1].to_numpy()) / 1000)
            if not np.isnan(g) and g > 1.5
        ],
        gaze_files_without_accelerometer=list(gz.loc[(gz.set == "public") & (gz.accelerometer_rows == 0), "participant"]),
    )
    (out / "k00_inventory.json").write_text(json.dumps(kc.jsonable(summary), indent=2, ensure_ascii=False))
    print(json.dumps(kc.jsonable(summary), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
