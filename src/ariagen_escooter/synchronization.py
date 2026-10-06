"""Time-series primitives: grids, gap-aware interpolation, nearest matching,
run detection and clock-offset estimation.

Principles
----------
* All timestamps are int64 nanoseconds in the device clock.
* Interpolation is linear and **never** bridges gaps longer than a configured
  maximum, never extrapolates, and is never applied to categorical data.
* Nearest-neighbour matching uses an explicit tolerance; samples without a
  partner inside the tolerance are reported as unmatched (index -1).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ariagen_escooter.streams import NS_PER_S


def to_ns(seconds: float) -> int:
    return int(round(seconds * NS_PER_S))


def find_runs(mask: np.ndarray) -> np.ndarray:
    """Start/end indices (inclusive) of consecutive True runs, shape (k, 2)."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0:
        return np.empty((0, 2), dtype=np.int64)
    d = np.diff(m.astype(np.int8))
    starts = np.flatnonzero(d == 1) + 1
    ends = np.flatnonzero(d == -1)
    if m[0]:
        starts = np.r_[0, starts]
    if m[-1]:
        ends = np.r_[ends, m.size - 1]
    return np.column_stack([starts, ends]).astype(np.int64)


def make_grid(start_ns: int, end_ns: int, rate_hz: float) -> np.ndarray:
    """Uniform int64 grid from ``start_ns`` to at most ``end_ns`` (inclusive)."""
    if end_ns < start_ns:
        return np.empty(0, dtype=np.int64)
    step = NS_PER_S / rate_hz
    n = int(np.floor((end_ns - start_ns) / step + 1e-9)) + 1
    return (start_ns + np.round(np.arange(n) * step)).astype(np.int64)


def interpolate_to_grid(
    t_src_ns: np.ndarray, values: np.ndarray, t_query_ns: np.ndarray, max_gap_ns: int
) -> np.ndarray:
    """Gap-aware linear interpolation of one signal at query times.

    Returns NaN where the query time is outside the sampled range or falls in
    an interval between two valid samples longer than ``max_gap_ns``. NaN
    values in ``values`` are treated as missing samples. Queries that coincide
    with a valid sample always return that sample.
    """
    t = np.asarray(t_src_ns, dtype=np.int64)
    v = np.asarray(values, dtype=np.float64)
    q = np.asarray(t_query_ns, dtype=np.int64)
    out = np.full(q.shape, np.nan)
    ok = np.isfinite(v)
    t, v = t[ok], v[ok]
    if t.size == 0 or q.size == 0:
        return out
    if t.size == 1:
        out[q == t[0]] = v[0]
        return out
    origin = t[0]
    ts = (t - origin).astype(np.float64)
    qs = (q - origin).astype(np.float64)
    inside = (q >= t[0]) & (q <= t[-1])
    right = np.clip(np.searchsorted(t, q, side="left"), 1, t.size - 1)
    left = right - 1
    exact = t[np.clip(np.searchsorted(t, q, side="left"), 0, t.size - 1)] == q
    bracket_ok = (t[right] - t[left]) <= max_gap_ns
    use = inside & (bracket_ok | exact)
    out[use] = np.interp(qs[use], ts, v)
    return out


def nearest_indices(query_ns: np.ndarray, ref_ns: np.ndarray, tolerance_ns: int) -> tuple[np.ndarray, np.ndarray]:
    """Index of the nearest reference time for each query (-1 if beyond tolerance).

    Returns ``(index, delta_ns)`` where ``delta_ns = ref - query`` (NaN when
    unmatched). Ties go to the earlier reference sample. ``ref_ns`` must be sorted.
    """
    ref = np.asarray(ref_ns, dtype=np.int64)
    q = np.asarray(query_ns, dtype=np.int64)
    idx = np.full(q.shape, -1, dtype=np.int64)
    delta = np.full(q.shape, np.nan)
    if ref.size == 0 or q.size == 0:
        return idx, delta
    if np.any(np.diff(ref) < 0):
        raise ValueError("reference timestamps must be sorted")
    pos = np.searchsorted(ref, q, side="left")
    left = np.clip(pos - 1, 0, ref.size - 1)
    right = np.clip(pos, 0, ref.size - 1)
    d_left = np.abs(q - ref[left])
    d_right = np.abs(ref[right] - q)
    best = np.where(d_right < d_left, right, left)
    d = ref[best] - q
    ok = np.abs(d) <= tolerance_ns
    idx[ok] = best[ok]
    delta[ok] = d[ok].astype(np.float64)
    return idx, delta


def mask_interval(t_ns: np.ndarray, start_ns: int, end_ns: int) -> np.ndarray:
    t = np.asarray(t_ns, dtype=np.int64)
    return (t >= start_ns) & (t <= end_ns)


@dataclass(frozen=True)
class OffsetEstimate:
    """Result of a clock-offset estimation.

    ``offset_s`` must be ADDED to the target timestamps to align them with the
    reference clock.
    """

    offset_s: float | None
    correlation: float | None
    overlap_s: float
    resolution_s: float
    reliable: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "offset_s": self.offset_s,
            "correlation": self.correlation,
            "overlap_s": self.overlap_s,
            "resolution_s": self.resolution_s,
            "reliable": self.reliable,
            "reason": self.reason,
        }


def estimate_offset_xcorr(
    t_ref_ns: np.ndarray,
    v_ref: np.ndarray,
    t_tgt_ns: np.ndarray,
    v_tgt: np.ndarray,
    *,
    max_lag_s: float,
    grid_rate_hz: float,
    min_overlap_s: float,
    min_correlation: float,
    max_gap_ref_ns: int,
    max_gap_tgt_ns: int,
) -> OffsetEstimate:
    """Estimate a constant clock offset by maximising the Pearson correlation.

    For every candidate offset on a grid of step ``1/grid_rate_hz`` within
    ``+-max_lag_s`` the target signal is re-interpolated with shifted
    timestamps and correlated with the reference on their common support. The
    best candidate is refined by parabolic interpolation of the correlation
    peak. The estimate is flagged unreliable if the overlap is too short, the
    correlation too low, or the peak lies on the search boundary.
    """
    resolution = 1.0 / grid_rate_hz
    t_ref = np.asarray(t_ref_ns, dtype=np.int64)
    t_tgt = np.asarray(t_tgt_ns, dtype=np.int64)
    if t_ref.size < 2 or t_tgt.size < 2:
        return OffsetEstimate(None, None, 0.0, resolution, False, "not enough samples")
    lag_steps = int(np.floor(max_lag_s * grid_rate_hz))
    start = max(t_ref[0], t_tgt[0]) + to_ns(max_lag_s)
    end = min(t_ref[-1], t_tgt[-1]) - to_ns(max_lag_s)
    overlap_s = max(0.0, (end - start) / NS_PER_S)
    if overlap_s < min_overlap_s:
        return OffsetEstimate(None, None, overlap_s, resolution, False, "overlap shorter than min_overlap_s")
    grid = make_grid(int(start), int(end), grid_rate_hz)
    ref = interpolate_to_grid(t_ref, v_ref, grid, max_gap_ref_ns)
    lags = np.arange(-lag_steps, lag_steps + 1)
    corr = np.full(lags.size, np.nan)
    for k, lag in enumerate(lags):
        shift = to_ns(lag * resolution)
        tgt = interpolate_to_grid(t_tgt + shift, v_tgt, grid, max_gap_tgt_ns)
        ok = np.isfinite(ref) & np.isfinite(tgt)
        if ok.sum() < 3:
            continue
        a, b = ref[ok], tgt[ok]
        if a.std() == 0 or b.std() == 0:
            continue
        corr[k] = float(np.corrcoef(a, b)[0, 1])
    if not np.isfinite(corr).any():
        return OffsetEstimate(None, None, overlap_s, resolution, False, "correlation undefined (flat signals)")
    best = int(np.nanargmax(corr))
    offset = float(lags[best]) * resolution
    if 0 < best < lags.size - 1 and np.isfinite(corr[best - 1]) and np.isfinite(corr[best + 1]):
        y0, y1, y2 = corr[best - 1], corr[best], corr[best + 1]
        denom = y0 - 2.0 * y1 + y2
        if denom < 0:
            offset += 0.5 * (y0 - y2) / denom * resolution
    peak = float(corr[best])
    on_boundary = best in (0, lags.size - 1)
    reasons = []
    if peak < min_correlation:
        reasons.append(f"correlation {peak:.3f} < {min_correlation}")
    if on_boundary:
        reasons.append("peak on search boundary (offset may exceed max_lag_s)")
    reliable = not reasons
    return OffsetEstimate(offset, peak, overlap_s, resolution, reliable, "; ".join(reasons) or "ok")
