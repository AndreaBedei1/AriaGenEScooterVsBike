#!/usr/bin/env python3
"""k02b_check_pelt.py - verification only: compares our numpy PELT (k02_speed_changepoints.pelt_l2)
with ruptures.Pelt(model="l2") (default min_size=2, jump=5), the library the original notebook
uses (speed_data_processing.ipynb cell 6 line 12), on every participant x segment speed signal
of the public Kegalle et al. (2025) data, for a set of penalties. Requires `ruptures`.

Usage: python -I k02b_check_pelt.py --repo REPO --out OUT
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ruptures as rpt  # noqa: E402

from k02_speed_changepoints import pelt_l2, segment_signals  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sig = segment_signals(Path(a.repo), False, "timemapping+gpsfallback")
    pens = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 3000]
    n_eq = n_tot = 0
    mism = []
    for pid, seg, y in sig:
        algo = rpt.Pelt(model="l2").fit(y)
        for p in pens:
            r = algo.predict(pen=p)
            o = pelt_l2(y, p)
            n_tot += 1
            if list(r) == list(o):
                n_eq += 1
            else:
                mism.append(dict(participant=pid, segment=seg, pen=p, ruptures=len(r) - 1, ours=len(o) - 1))
    res = dict(rpt_version=rpt.__version__, comparisons=n_tot, identical=n_eq, mismatches=mism[:50])
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "k02b_pelt_vs_ruptures.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
