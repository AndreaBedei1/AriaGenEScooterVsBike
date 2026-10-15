"""Shared helpers for the independent re-analysis of the Kegalle et al. (2025) public data.

Paper:   H. N. Kegalle, D. Hettiachchi, J. Chan, M. Sanderson, F. D. Salim (2025).
         "Watch Out! E-scooter Coming Through!: Multimodal Sensing of Mixed Traffic Use and
         Conflicts Through Riders' Ego-centric Views". Proc. ACM IMWUT 9(1).
         DOI 10.1145/3712284 (arXiv 2502.16755). Paper text: CC BY 4.0.
Data:    https://github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis
         (commit ed5c22195ecb0d3468fe67e8da5cc9ca9a1e9cb3, 2025-03-06). The repository has NO
         licence file (GitHub API: license = null), so default copyright applies; the README asks
         users of the data/code to cite the paper. Nothing from that repository is copied here:
         this module is our own implementation written from the paper text and from reading
         the original notebooks. Line references below are "notebook:cell:line" as printed by
         our notebook dump (cell index 0-based, line 1-based).

Only numpy / pandas / scipy are used. Reading the .xlsx files needs a pandas Excel engine
(python-calamine preferred, openpyxl as fallback).
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Segment lengths in km. Fig. 3 of the paper (p. 9) labels the cycle lane 0.65 km and the roadway
# 0.74 km, but (i) the GPS distance covered inside the segments of the public speed files is
# ~0.74 km for the cycle lane and ~0.64 km for the roadway (k01 output), and (ii) the per-km values
# of Table 3 are reproduced only when the cycle lane is divided by 0.74 and the roadway by 0.65
# (k03 output). We therefore use the GPS-consistent assignment; the Fig. 3 labels look swapped.
# The code never uses lengths; the paper reports fixations, encounters and change points "per km".
SEGMENT_KM_FIG3 = {1: 1.36, 2: 0.65, 3: 0.74}
SEGMENT_KM = {1: 1.36, 2: 0.74, 3: 0.65}
if os.environ.get("KEGALLE_USE_FIG3_LENGTHS") == "1":  # opt-in to the labels as printed in Fig. 3
    SEGMENT_KM = dict(SEGMENT_KM_FIG3)
SEGMENT_NAME = {1: "Pedestrian-shared path", 2: "Cycle lane", 3: "Roadway"}

_TIME_RE = re.compile(r"^\(\s*(\d{1,2})\s*\)\s*(\d{1,2})\s*[.:]\s*(\d{1,2})\s*$")


def parse_paren_time(value) -> float:
    """Parse the hand-typed '(hh)mm.ss' strings of TimeMapping_BikeComputer_EyeTracker.xlsx.

    Returns seconds since midnight. Seconds are read as an integer string, i.e. '(15) 12.5'
    is 15:12:05 and '(14)32.0' is 14:32:00 (this reading is the one that agrees with the
    Tobii millisecond columns of the same sheet; see 00_inventory output).
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    s = str(value).strip()
    m = _TIME_RE.match(s)
    if not m:
        raise ValueError(f"unparseable time string: {value!r}")
    hh, mm, ss = (int(g) for g in m.groups())
    if mm > 59 or ss > 59:
        raise ValueError(f"out of range time: {value!r}")
    return hh * 3600 + mm * 60 + ss


def read_timemapping(path: str | os.PathLike) -> pd.DataFrame:
    """Long table: participant, segment, garmin_start_s, garmin_end_s, tobii_start_ms, tobii_end_ms.

    The sheet has a two-row header and blocks of 3 rows per participant with the participant
    number only on the first row. In one block (P10, segment 2) the start/end strings are
    shifted by one column, so we take the first two non-empty time strings of each row.
    """
    raw = pd.read_excel(path, header=None, engine=_excel_engine())
    rows = []
    pid = None
    for _, r in raw.iloc[2:].iterrows():
        if pd.notna(r.iloc[0]):
            pid = int(r.iloc[0])
        if pd.isna(r.iloc[1]):
            continue
        seg = int(r.iloc[1])
        times = [v for v in (r.iloc[2], r.iloc[3]) if pd.notna(v) and str(v).strip()]
        if len(times) != 2:
            raise ValueError(f"P{pid} seg {seg}: expected 2 Garmin times, got {times}")
        rows.append(
            dict(
                participant=f"P{pid}",
                segment=seg,
                garmin_start_raw=str(times[0]).strip(),
                garmin_end_raw=str(times[1]).strip(),
                garmin_start_s=parse_paren_time(times[0]),
                garmin_end_s=parse_paren_time(times[1]),
                tobii_start_ms=float(r.iloc[4]) if pd.notna(r.iloc[4]) else np.nan,
                tobii_end_ms=float(r.iloc[5]) if pd.notna(r.iloc[5]) else np.nan,
            )
        )
    df = pd.DataFrame(rows)
    df["garmin_dur_s"] = df.garmin_end_s - df.garmin_start_s
    df["tobii_dur_s"] = (df.tobii_end_ms - df.tobii_start_ms) / 1000.0
    return df


def _excel_engine() -> str:
    try:
        import python_calamine  # noqa: F401

        return "calamine"
    except ImportError:
        return "openpyxl"


def pid_from_name(name: str) -> str:
    m = re.match(r"^(P\d+)", Path(name).name)
    if not m:
        raise ValueError(name)
    return m.group(1)


# --------------------------------------------------------------------------------------
# Garmin speed
# --------------------------------------------------------------------------------------

def read_speed_csv(path: str | os.PathLike) -> pd.DataFrame:
    """Read a GOTOES_CSV export of the Garmin FIT file.

    index_col=False is required: the 2024 files (P21-P30) have one trailing comma more than the
    header, and pandas would otherwise silently shift every column by one (speed would become NaN).
    """
    d = pd.read_csv(path, index_col=False, low_memory=False)
    d = d.loc[:, [c for c in d.columns if not str(c).startswith("Unnamed")]].copy()
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d["tod_s_file"] = (
        d["timestamp"].dt.hour * 3600 + d["timestamp"].dt.minute * 60 + d["timestamp"].dt.second
    ).astype(float)
    return d


def infer_hour_offset(file_tod_first: float, garmin_seg1_start: float) -> int:
    """Whole-hour shift between the CSV clock and the local clock used in the TimeMapping sheet.

    The original notebook (speed_data_processing.ipynb:2:6) adds a user-supplied `time_delta`
    in hours; the value is not given anywhere. Empirically it is +16 h for every file.
    """
    diff = (garmin_seg1_start - file_tod_first) % 86400
    h = int(round(diff / 3600.0)) % 24
    resid = ((garmin_seg1_start - (file_tod_first + h * 3600)) + 43200) % 86400 - 43200
    if abs(resid) > 1800:
        raise ValueError("could not infer an hour offset within 30 min")
    return h


def segment_speed(speed: pd.DataFrame, tm_p: pd.DataFrame, hour_offset: int) -> dict[int, pd.DataFrame]:
    """Inclusive [start, end] selection on the local time of day (the original used manual
    1-based inclusive row ranges, speed_data_processing.ipynb:4:6)."""
    tod_local = (speed["tod_s_file"] + hour_offset * 3600) % 86400
    out = {}
    for _, r in tm_p.iterrows():
        m = (tod_local >= r.garmin_start_s) & (tod_local <= r.garmin_end_s)
        seg = speed.loc[m].copy()
        seg["tod_local_s"] = tod_local[m]
        out[int(r.segment)] = seg
    return out


# --------------------------------------------------------------------------------------
# Tobii gaze export
# --------------------------------------------------------------------------------------

GAZE_COLS = [
    "Recording timestamp [ms]",
    "Sensor",
    "Recording name",
    "Recording date",
    "Recording start time",
    "Recording start time UTC",
    "Recording duration [ms]",
    "Recording Fixation filter name",
    "Gaze point X [MCS px]",
    "Gaze point Y [MCS px]",
    "Validity left",
    "Validity right",
    "Eye movement type",
    "Gaze event duration [ms]",
    "Eye movement type index",
    "Fixation point X [MCS px]",
    "Fixation point Y [MCS px]",
    "Accelerometer X [m/s²]",
    "Accelerometer Y [m/s²]",
    "Accelerometer Z [m/s²]",
    "Gyro X [°/s]",
    "Gyro Y [°/s]",
    "Gyro Z [°/s]",
    "Magnetometer X [μT]",
]


def read_gaze_xlsx(path: str | os.PathLike, cache_dir: str | os.PathLike | None = None) -> pd.DataFrame:
    """Read a Tobii Pro Lab 'Data' export (.xlsx), keeping only the columns we need.

    A pickle cache (our own derived file) is written to cache_dir to avoid re-parsing 40 MB xlsx.
    """
    path = Path(path)
    if cache_dir is not None:
        cache = Path(cache_dir) / (path.stem + ".pkl")
        if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
            return pd.read_pickle(cache)
    df = pd.read_excel(path, sheet_name=0, engine=_excel_engine())
    # The 2024 exports (e.g. P23) use unit-less column names ('Recording timestamp',
    # 'Gaze point X', 'Accelerometer X', ...). The original notebooks hard-code the
    # unit-suffixed names, so they would raise KeyError on those files. Canonicalise here.
    ren = {}
    for name in GAZE_COLS + ["Recording media width", "Recording media height"]:
        base = re.sub(r" \[[^\]]*\]$", "", name)
        if name not in df.columns and base in df.columns:
            ren[base] = name
    df = df.rename(columns=ren)
    df.attrs["renamed_unitless_columns"] = len(ren)
    keep = [c for c in GAZE_COLS + ["Recording media width", "Recording media height"] if c in df.columns]
    df = df[keep].copy()
    df["export_unitless_names"] = bool(ren)
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        df.to_pickle(cache)
    return df


def tobii_segment(df: pd.DataFrame, start_ms: float, end_ms: float) -> pd.DataFrame:
    """Inclusive time window on 'Recording timestamp [ms]' (as in
    'average_fixation_count __fixation_duration.ipynb':3:6)."""
    t = df["Recording timestamp [ms]"]
    return df.loc[(t >= start_ms) & (t <= end_ms)]


def unique_fixations_as_coded(seg: pd.DataFrame) -> pd.DataFrame:
    """Re-implementation of the 'select unique records' step
    ('average_fixation_count __fixation_duration.ipynb':4:10-11): one row per distinct
    (event type, event duration, fixation X, fixation Y). Because pandas groupby drops NaN keys
    by default, only rows with a fixation point (= fixations) survive."""
    keys = [
        "Eye movement type",
        "Gaze event duration [ms]",
        "Fixation point X [MCS px]",
        "Fixation point Y [MCS px]",
    ]
    g = seg.dropna(subset=keys).groupby(keys, as_index=False)["Recording timestamp [ms]"].min()
    return g.sort_values("Recording timestamp [ms]").reset_index(drop=True)


def unique_fixations_by_index(seg: pd.DataFrame) -> pd.DataFrame:
    """Alternative, event-index based de-duplication: one row per Tobii fixation event."""
    f = seg[seg["Eye movement type"] == "Fixation"]
    g = f.groupby("Eye movement type index", as_index=False).agg(
        ts=("Recording timestamp [ms]", "min"),
        dur=("Gaze event duration [ms]", "first"),
        x=("Fixation point X [MCS px]", "first"),
        y=("Fixation point Y [MCS px]", "first"),
    )
    return g


# --------------------------------------------------------------------------------------
# Statistics (own implementations; scipy only for distributions / standard tests)
# --------------------------------------------------------------------------------------

def rm_anova(wide: np.ndarray) -> dict:
    """One-way repeated-measures ANOVA on an (n subjects x k conditions) complete array.
    Also returns the Greenhouse-Geisser epsilon and GG-corrected p."""
    y = np.asarray(wide, float)
    n, k = y.shape
    gm = y.mean()
    ss_subj = k * ((y.mean(axis=1) - gm) ** 2).sum()
    ss_cond = n * ((y.mean(axis=0) - gm) ** 2).sum()
    ss_tot = ((y - gm) ** 2).sum()
    ss_err = ss_tot - ss_subj - ss_cond
    df1, df2 = k - 1, (n - 1) * (k - 1)
    F = (ss_cond / df1) / (ss_err / df2)
    p = stats.f.sf(F, df1, df2)
    # Greenhouse-Geisser epsilon from the double-centred covariance matrix
    S = np.cov(y, rowvar=False)
    J = np.eye(k) - np.ones((k, k)) / k
    Sc = J @ S @ J
    eps = (np.trace(Sc) ** 2) / ((k - 1) * np.sum(Sc * Sc))
    p_gg = stats.f.sf(F, df1 * eps, df2 * eps)
    return dict(n=int(n), k=int(k), F=float(F), df1=df1, df2=df2, p=float(p), gg_eps=float(eps), p_gg=float(p_gg))


def oneway_between(groups: list[np.ndarray]) -> dict:
    F, p = stats.f_oneway(*groups)
    return dict(F=float(F), p=float(p), df1=len(groups) - 1, df2=int(sum(len(g) for g in groups) - len(groups)))


def paired_tests(wide: np.ndarray, labels=(1, 2, 3)) -> list[dict]:
    out = []
    k = wide.shape[1]
    for i in range(k):
        for j in range(i + 1, k):
            t, p = stats.ttest_rel(wide[:, i], wide[:, j])
            out.append(dict(a=labels[i], b=labels[j], t=float(t), p=float(p), p_bonf=float(min(1.0, p * 3))))
    return out


def tukey(groups: list[np.ndarray], labels=(1, 2, 3)) -> list[dict]:
    res = stats.tukey_hsd(*groups)
    out = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            out.append(dict(a=labels[i], b=labels[j], diff=float(res.statistic[i, j]), p=float(res.pvalue[i, j])))
    return out


def shapiro_by_column(wide: np.ndarray, labels=(1, 2, 3)) -> list[dict]:
    out = []
    for j in range(wide.shape[1]):
        W, p = stats.shapiro(wide[:, j])
        out.append(dict(segment=labels[j], W=float(W), p=float(p)))
    return out


def full_stats(wide_df: pd.DataFrame) -> dict:
    """wide_df: index participant, columns 1,2,3. Rows with NaN are dropped (complete cases)."""
    w = wide_df.dropna()
    arr = w[[1, 2, 3]].to_numpy(float)
    groups = [arr[:, j] for j in range(3)]
    return dict(
        n_complete=int(len(w)),
        participants=list(w.index),
        mean={int(c): float(w[c].mean()) for c in (1, 2, 3)},
        sd={int(c): float(w[c].std(ddof=1)) for c in (1, 2, 3)},
        min={int(c): float(w[c].min()) for c in (1, 2, 3)},
        max={int(c): float(w[c].max()) for c in (1, 2, 3)},
        shapiro=shapiro_by_column(arr),
        rm_anova=rm_anova(arr),
        oneway_anova_between=oneway_between(groups),
        paired_t=paired_tests(arr),
        tukey_hsd_between=tukey(groups),
    )


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


# --------------------------------------------------------------------------------------
# GPS-based segmentation (our addition; used as fallback when the hand-typed TimeMapping
# times fall outside a speed file, which happens for P4, and as a sensitivity check)
# --------------------------------------------------------------------------------------

def _local_xy(lat, lon, lat0=-37.78):
    return np.asarray(lat) * 111320.0, np.asarray(lon) * 111320.0 * math.cos(math.radians(lat0))


def boundary_points_from_reference(speed_by_pid: dict, tm: pd.DataFrame) -> np.ndarray:
    """Median GPS position (lat, lon) of the 4 route boundaries (seg1 start, seg2 start,
    seg3 start, seg3 end) over all participants whose TimeMapping times fall in their file."""
    pts = [[] for _ in range(4)]
    for pid, d in speed_by_pid.items():
        tp = tm[tm.participant == pid]
        if tp.empty:
            continue
        bt = [
            tp.loc[tp.segment == 1, "garmin_start_s"].item(),
            tp.loc[tp.segment == 2, "garmin_start_s"].item(),
            tp.loc[tp.segment == 3, "garmin_start_s"].item(),
            tp.loc[tp.segment == 3, "garmin_end_s"].item(),
        ]
        for k, t in enumerate(bt):
            r = d[d["tod_local_s"] == t]
            if len(r) == 1:
                pts[k].append((r.position_lat.item(), r.position_long.item()))
    return np.array([np.median(np.array(p), axis=0) for p in pts])


def gps_boundary_times(d: pd.DataFrame, bpts: np.ndarray, near_m: float = 40.0) -> list[float]:
    """Sequentially find when the rider passes each boundary point (closest approach after
    first coming within `near_m` metres, searched after the previous boundary)."""
    x, y = _local_xy(d.position_lat.to_numpy(), d.position_long.to_numpy())
    tod = d["tod_local_s"].to_numpy()
    out = []
    start = 0
    min_gap = [0, 60, 30, 30]
    for k in range(4):
        bx, by = _local_xy(bpts[k, 0], bpts[k, 1])
        dist = np.hypot(x - bx, y - by)
        lo = start
        if k > 0:
            lo = int(np.searchsorted(tod, out[-1] + min_gap[k]))
        if k == 0:
            win = np.arange(0, min(len(d), 120))
            i = int(win[np.argmin(dist[win])])
        else:
            cand = np.where(dist[lo:] < near_m)[0]
            if len(cand) == 0:
                raise ValueError(f"boundary {k} never approached within {near_m} m")
            j0 = lo + int(cand[0])
            win = np.arange(j0, min(len(d), j0 + 30))
            i = int(win[np.argmin(dist[win])])
        out.append(float(tod[i]))
    return out
