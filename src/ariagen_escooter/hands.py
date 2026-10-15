"""EXPLORATORY hand-tracking descriptors per time window.

Aria Gen 2 on-device hand tracking is computed from the CV (SLAM) cameras of the
glasses. While riding, the hands rest on the handlebar at the lower edge of the
field of view and are often occluded or out of view: detection rates and
positional accuracy are unknown for this use and must be measured on annotated
pilot frames before any substantive interpretation (see
docs/methodology/hand_tracking_validation.md).

Rules implemented here:

* a hand that is not detected is MISSING, never "off the handlebar";
* positional descriptors use only detected samples and always report how many
  samples they rest on;
* positions are in the CPF frame of the head (x left, y up, z forward), so they
  mix arm posture with head posture: they describe hands relative to the head,
  not relative to the vehicle.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HAND_METRIC_PREFIX = "hand_"


def _in_window(hands: pd.DataFrame, t0: int, t1: int) -> pd.DataFrame:
    t = hands["t_ns"].to_numpy(dtype=np.int64)
    return hands[(t >= t0) & (t <= t1)]


def window_hand_metrics(hands: pd.DataFrame | None, t0: int, t1: int, min_confidence: float) -> dict[str, float]:
    """Detection fractions and robust position summaries of each hand in [t0, t1]."""
    out: dict[str, float] = {}
    if hands is None or hands.empty:
        return out
    w = _in_window(hands, t0, t1)
    out[f"{HAND_METRIC_PREFIX}n_samples"] = float(len(w))
    if w.empty:
        return out
    present = {}
    for side in ("left", "right"):
        col = f"{side}_present"
        if col not in w.columns:
            continue
        p = w[col].astype(bool).to_numpy()
        conf = w.get(f"{side}_confidence")
        if conf is not None:
            p = p & (np.nan_to_num(conf.to_numpy(dtype=np.float64), nan=0.0) >= min_confidence)
        present[side] = p
        out[f"{HAND_METRIC_PREFIX}{side}_detected_fraction"] = float(p.mean())
        n = int(p.sum())
        out[f"{HAND_METRIC_PREFIX}{side}_n_detected"] = float(n)
        for axis, name in (("x", "lateral"), ("y", "vertical"), ("z", "forward")):
            key = f"{side}_wrist_{axis}_m"
            if key in w.columns and n:
                vals = w[key].to_numpy(dtype=np.float64)[p]
                out[f"{HAND_METRIC_PREFIX}{side}_wrist_{name}_median_m"] = float(np.nanmedian(vals))
                q75, q25 = np.nanpercentile(vals, [75, 25])
                out[f"{HAND_METRIC_PREFIX}{side}_wrist_{name}_iqr_m"] = float(q75 - q25)
    if len(present) == 2:
        both = present["left"] & present["right"]
        out[f"{HAND_METRIC_PREFIX}both_detected_fraction"] = float(both.mean())
        cols = [f"{s}_wrist_{a}_m" for s in ("left", "right") for a in "xyz"]
        if both.any() and all(c in w.columns for c in cols):
            left = w[cols[:3]].to_numpy(dtype=np.float64)[both]
            right = w[cols[3:]].to_numpy(dtype=np.float64)[both]
            out[f"{HAND_METRIC_PREFIX}inter_wrist_distance_median_m"] = float(np.nanmedian(np.linalg.norm(left - right, axis=1)))
    return out
