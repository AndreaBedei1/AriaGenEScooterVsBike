#!/usr/bin/env python3
"""k02_speed_changepoints.py - speed change points per segment (Kegalle et al. 2025, Sec. 3.6.1, 4.1.2, Fig. 5).

Paper: Kegalle, Hettiachchi, Chan, Sanderson, Salim (2025), "Watch Out! E-scooter Coming
Through!...", Proc. ACM IMWUT 9(1), DOI 10.1145/3712284 (CC BY 4.0). Companion: Kegalle et al.
(2024) AHs '24, DOI 10.1145/3652920.3653056 ("PELT ... optimal penalty using AIC").
Data:  github.com/HiruniNuwanthika/Electric-Scooter-Riders-Multi-Modal-Data-Analysis @ ed5c221
       (no LICENSE file -> all rights reserved by default; cite the paper). Own implementation:
       PELT is re-implemented here in numpy (no `ruptures` dependency); k02b_check_pelt.py
       cross-checks it against ruptures 1.1.x.

Reconstructed algorithm (speed_data_processing.ipynb, cell 6, lines 1-47):
  * signal = per-second Garmin speed (km/h) of ONE route segment
  * PELT, least-squares (l2) cost  C(a,b) = sum_{t=a}^{b-1} (y_t - mean(y_a..y_{b-1}))^2,
    ruptures defaults min_size = 2 and jump = 5 (candidate change points every 5 s)  [line 12]
  * penalties = linspace(penalty_range[0], penalty_range[1], num_penalties)        [line 15]
    -> penalty_range and num_penalties are function arguments whose values are NOT published.
  * for each penalty: breakpoints B (last element = n), k = len(B),
    RSS = sum of l2 costs of all segments EXCEPT the last one                         [lines 23-31]
    "AIC" = 2k - 2*log(exp(-RSS/(2n))) = 2k + RSS/n                                   [lines 7-9]
  * keep the penalty with the smallest "AIC" (strict <, first wins)                    [lines 34-38]
  * number of change points = len(B) - 1.
Consequence of the coded criterion: when the grid contains a penalty large enough to return no
change point, RSS = 0 and AIC = 2, which beats every non-empty solution (AIC >= 4). Otherwise each
extra change point costs 2 AIC units, i.e. roughly an l2 penalty of 2n, so the result is driven by
the (unknown) upper end of the penalty grid. Variants offered here:
  --aic original  : exactly the coded criterion (bug included)
  --aic fixed     : same formula, RSS over ALL segments
  --aic gaussian  : n*ln(RSS/n) + 2*(2m+2), m = number of change points
  --aic none      : no selection, a single fixed penalty (--pen)
Zero-speed samples: the paper removes them before the speed analysis; whether they were removed
before PELT is not stated (option --drop-zeros).

Usage:
  python -I k02_speed_changepoints.py --repo REPO --out OUT [--pen-lo 1 --pen-hi 100 --pen-num 50]
         [--aic original|fixed|gaussian|none] [--pen 50] [--drop-zeros] [--sweep]
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
from k01_speed import load_speed_files, segment_bounds  # noqa: E402

PAPER = dict(mean={1: 7.9, 2: 4.3, 3: 10.2}, sd={1: 4.1, 2: 1.7, 3: 5.9}, total=371)


def l2_cost(y: np.ndarray, a: int, b: int) -> float:
    seg = y[a:b]
    return float(seg.var() * (b - a))


class _Cost:
    """O(1) least-squares segment cost from cumulative sums."""

    def __init__(self, y: np.ndarray):
        y = np.asarray(y, float)
        self.s1 = np.concatenate([[0.0], np.cumsum(y)])
        self.s2 = np.concatenate([[0.0], np.cumsum(y * y)])

    def __call__(self, a: int, b: int) -> float:
        m = b - a
        s = self.s1[b] - self.s1[a]
        return max(0.0, float(self.s2[b] - self.s2[a] - s * s / m))


_PELT_CACHE: dict = {}


def pelt_l2(y: np.ndarray, pen: float, min_size: int = 2, jump: int = 5) -> list[int]:
    """PELT (Killick et al. 2012) with the candidate grid / pruning rule used by ruptures.Pelt.
    Returns sorted breakpoints (end indices) including len(y)."""
    key = (y.tobytes(), float(pen), min_size, jump)
    if key in _PELT_CACHE:
        return _PELT_CACHE[key]
    n = len(y)
    if n < min_size:
        return [n]
    cost = _Cost(y)
    ind = [k for k in range(0, n, jump) if k >= min_size] + [n]
    F = {0: 0.0}
    back = {0: None}
    admissible: list[int] = []
    for bkp in ind:
        new_adm = (math.floor((bkp - min_size) / jump)) * jump
        admissible.append(new_adm)
        cand = [(t, F[t] + cost(t, bkp) + pen) for t in admissible if t in F]
        if not cand:
            continue
        best_t, best_v = cand[0]
        for t, v in cand[1:]:
            if v < best_v:
                best_t, best_v = t, v
        F[bkp] = best_v
        back[bkp] = best_t
        admissible = [t for t, v in cand if v <= best_v + pen]
    bkps = []
    b = n
    while b is not None and b > 0:
        bkps.append(b)
        b = back[b]
    res = sorted(bkps)
    _PELT_CACHE[key] = res
    return res


def select_by_aic(y: np.ndarray, penalties: np.ndarray, variant: str) -> tuple[list[int], float, float]:
    n = len(y)
    best = (None, None, np.inf)
    for pen in penalties:
        B = pelt_l2(y, float(pen))
        k = len(B)
        segs = list(zip([0] + B[:-1], B))
        if variant == "original":
            rss = sum(l2_cost(y, a, b) for a, b in segs[:-1])
            aic = 2 * k - 2 * np.log(np.exp(-rss / (2 * n)))
        elif variant == "fixed":
            rss = sum(l2_cost(y, a, b) for a, b in segs)
            aic = 2 * k + rss / n
        elif variant == "gaussian":
            rss = sum(l2_cost(y, a, b) for a, b in segs)
            m = k - 1
            aic = n * np.log(max(rss, 1e-12) / n) + 2 * (2 * m + 2)
        else:
            raise ValueError(variant)
        if aic < best[2]:
            best = (B, float(pen), float(aic))
    return best


def segment_signals(repo: Path, drop_zeros: bool, segmentation: str) -> list[tuple[str, int, np.ndarray]]:
    tm = kc.read_timemapping(repo / "data" / "TimeMapping_BikeComputer_EyeTracker.xlsx")
    files = load_speed_files(repo, tm)
    bpts = kc.boundary_points_from_reference(files, tm)
    out = []
    for pid, d in files.items():
        bounds, _, _ = segment_bounds(pid, d, tm, bpts, segmentation)
        for seg, (a, b) in bounds.items():
            s = d[(d.tod_local_s >= a) & (d.tod_local_s <= b)]
            y = s["speed"].to_numpy(float)
            if drop_zeros:
                y = y[y > 0]
            out.append((pid, seg, y))
    return out


def run_once(signals, aic: str, pen_lo: float, pen_hi: float, pen_num: int, pen: float) -> pd.DataFrame:
    rows = []
    for pid, seg, y in signals:
        if aic == "none":
            B, bp, val = pelt_l2(y, pen), pen, float("nan")
        else:
            B, bp, val = select_by_aic(y, np.linspace(pen_lo, pen_hi, pen_num), aic)
        rows.append(dict(participant=pid, segment=seg, n=len(y), n_cp=len(B) - 1, best_pen=bp, aic=val,
                         cp_idx=" ".join(map(str, B[:-1])), cp_per_km=(len(B) - 1) / kc.SEGMENT_KM[seg]))
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> dict:
    g = df.groupby("segment")
    return dict(
        mean={int(s): float(v) for s, v in g.n_cp.mean().items()},
        sd={int(s): float(v) for s, v in g.n_cp.std(ddof=1).items()},
        mean_per_km={int(s): float(v) for s, v in g.cp_per_km.mean().items()},
        sd_per_km={int(s): float(v) for s, v in g.cp_per_km.std(ddof=1).items()},
        median_per_km={int(s): float(v) for s, v in g.cp_per_km.median().items()},
        total=int(df.n_cp.sum()),
        n_participants=int(df.participant.nunique()),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aic", default="original", choices=["original", "fixed", "gaussian", "none"])
    ap.add_argument("--pen-lo", type=float, default=1.0)
    ap.add_argument("--pen-hi", type=float, default=100.0)
    ap.add_argument("--pen-num", type=int, default=100)
    ap.add_argument("--pen", type=float, default=50.0, help="fixed penalty when --aic none")
    ap.add_argument("--drop-zeros", action="store_true")
    ap.add_argument("--segmentation", default="timemapping+gpsfallback",
                    choices=["timemapping+gpsfallback", "timemapping", "gps"])
    ap.add_argument("--sweep", action="store_true", help="run the sensitivity grid and write a table")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    signals = segment_signals(Path(a.repo), a.drop_zeros, a.segmentation)
    zt = "dropzeros" if a.drop_zeros else "keepzeros"

    if not a.sweep:
        df = run_once(signals, a.aic, a.pen_lo, a.pen_hi, a.pen_num, a.pen)
        tag = f"{a.aic}_{a.pen_lo:g}-{a.pen_hi:g}x{a.pen_num}_{zt}" if a.aic != "none" else f"pen{a.pen:g}_{zt}"
        df.to_csv(out / f"k02_cp_{tag}.csv", index=False)
        res = dict(config=vars(a), ours=summarise(df), paper=PAPER)
        (out / f"k02_cp_{tag}.json").write_text(json.dumps(kc.jsonable(res), indent=2))
        print(json.dumps(kc.jsonable(res["ours"]), indent=1))
        return

    rows = []
    grids = [(0.1, 10), (1, 10), (1, 50), (1, 100), (1, 200), (1, 500), (1, 1000), (10, 1000), (1, 5000)]
    for aic in ["original", "fixed", "gaussian"]:
        for lo, hi in grids:
            for num in [10, 50, 100]:
                s = summarise(run_once(signals, aic, lo, hi, num, 0))
                rows.append(dict(mode=aic, pen_lo=lo, pen_hi=hi, pen_num=num, zeros=zt, **{
                    f"mean_s{k}": s["mean"][k] for k in (1, 2, 3)}, **{
                    f"perkm_s{k}": s["mean_per_km"][k] for k in (1, 2, 3)}, total=s["total"]))
                print(rows[-1], file=sys.stderr)
    for pen in [5, 10, 15, 20, 25, 30, 35, 40, 50, 100, 200, 300, 500, 1000, 2000]:
        s = summarise(run_once(signals, "none", 0, 0, 0, pen))
        rows.append(dict(mode="fixed-penalty", pen_lo=pen, pen_hi=pen, pen_num=1, zeros=zt, **{
            f"mean_s{k}": s["mean"][k] for k in (1, 2, 3)}, **{
            f"perkm_s{k}": s["mean_per_km"][k] for k in (1, 2, 3)}, **{
            f"sdperkm_s{k}": s["sd_per_km"][k] for k in (1, 2, 3)}, total=s["total"]))
        print(rows[-1], file=sys.stderr)
    sw = pd.DataFrame(rows)
    sw.to_csv(out / f"k02_cp_sweep_{zt}.csv", index=False)


if __name__ == "__main__":
    main()
