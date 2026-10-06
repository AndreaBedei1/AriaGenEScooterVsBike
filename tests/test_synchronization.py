"""Timestamp validation, gap-aware interpolation, nearest matching, clock offsets."""

from __future__ import annotations

import numpy as np
import pytest

from ariagen_escooter.streams import NS_PER_S, check_timestamps, sort_and_deduplicate
from ariagen_escooter.synchronization import (
    estimate_offset_xcorr,
    find_runs,
    interpolate_to_grid,
    make_grid,
    nearest_indices,
    to_ns,
)


def test_find_runs() -> None:
    mask = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 1], dtype=bool)
    assert find_runs(mask).tolist() == [[1, 2], [4, 4], [7, 9]]
    assert find_runs(np.zeros(3, bool)).shape == (0, 2)
    assert find_runs(np.ones(3, bool)).tolist() == [[0, 2]]


def test_make_grid_is_exact_and_inclusive() -> None:
    grid = make_grid(1_000, 1_000 + NS_PER_S, 10.0)
    assert grid.size == 11 and grid[0] == 1_000 and grid[-1] == 1_000 + NS_PER_S
    assert np.all(np.diff(grid) == NS_PER_S // 10)


def test_timestamp_report_detects_problems() -> None:
    t = (np.array([0.0, 0.1, 0.2, 0.2, 0.15, 0.5, 0.6]) * NS_PER_S).astype(np.int64)
    rep = check_timestamps(t, "x", gap_factor=1.5, max_reported_gaps=10)
    assert rep.n_duplicates == 1 and rep.n_non_monotonic == 1
    assert rep.n_gaps == 1 and rep.gaps[0]["duration_s"] == pytest.approx(0.35)
    assert not rep.ok
    clean = check_timestamps((np.arange(10) * 0.1 * NS_PER_S).astype(np.int64), "y", 1.5, 10)
    assert clean.ok and clean.estimated_rate_hz == pytest.approx(10.0)


def test_sort_and_deduplicate() -> None:
    import pandas as pd

    df = pd.DataFrame({"t_ns": [3, 1, 2, 2], "v": [30, 10, 20, 21]})
    out = sort_and_deduplicate(df)
    assert out["t_ns"].tolist() == [1, 2, 3] and out["v"].tolist() == [10, 20, 30]


def test_interpolation_never_bridges_long_gaps() -> None:
    t = (np.array([0.0, 0.1, 0.2, 1.2, 1.3]) * NS_PER_S).astype(np.int64)
    v = np.array([0.0, 1.0, 2.0, 12.0, 13.0])
    q = (np.array([0.05, 0.2, 0.7, 1.25, 1.4, -0.1]) * NS_PER_S).astype(np.int64)
    out = interpolate_to_grid(t, v, q, max_gap_ns=to_ns(0.5))
    assert out[0] == pytest.approx(0.5)
    assert out[1] == pytest.approx(2.0)  # exact sample next to a gap is kept
    assert np.isnan(out[2])  # inside the 1 s gap: no invented data
    assert out[3] == pytest.approx(12.5)
    assert np.isnan(out[4]) and np.isnan(out[5])  # no extrapolation


def test_interpolation_treats_nan_as_missing() -> None:
    t = (np.arange(6) * 0.1 * NS_PER_S).astype(np.int64)
    v = np.array([0, 1, np.nan, np.nan, np.nan, 5.0])
    out = interpolate_to_grid(t, v, t, max_gap_ns=to_ns(0.15))
    assert np.isnan(out[2:5]).all() and out[1] == 1 and out[5] == 5


def test_nearest_matching_with_jitter_and_tolerance() -> None:
    frames = (np.arange(0, 1.0, 0.1) * NS_PER_S).astype(np.int64)
    frames = np.delete(frames, 5)  # dropped frame at 0.5 s
    rng = np.random.default_rng(1)
    gaze = (np.arange(0, 1.0, 1 / 30) * NS_PER_S + rng.normal(0, 1e6, 30)).astype(np.int64)
    idx, delta = nearest_indices(gaze, frames, tolerance_ns=to_ns(0.05))
    matched = idx >= 0
    assert np.all(np.abs(delta[matched]) <= to_ns(0.05))
    near_drop = np.abs(gaze - to_ns(0.5)) < to_ns(0.04)
    assert np.all(idx[near_drop] == -1)  # nothing within tolerance of the dropped frame
    expected = np.min(np.abs(gaze[:, None] - frames[None, :]), axis=1) <= to_ns(0.05)
    assert np.array_equal(matched, expected)


def test_nearest_tie_goes_to_earlier_sample() -> None:
    idx, _ = nearest_indices(np.array([15]), np.array([10, 20]), tolerance_ns=10)
    assert idx[0] == 0


def _speed_profile(t_s: np.ndarray) -> np.ndarray:
    return np.interp(t_s, [0, 10, 20, 30, 40, 55, 60, 80, 90, 100], [0, 5, 5, 2, 5, 5, 0, 4, 1, 0])


def test_clock_offset_is_recovered() -> None:
    t_ref = np.arange(0, 100, 0.05)
    t_gps_true = np.arange(0, 100, 1.0)
    true_error = 0.8  # GPS timestamps are 0.8 s late
    est = estimate_offset_xcorr(
        (t_ref * NS_PER_S).astype(np.int64),
        _speed_profile(t_ref),
        ((t_gps_true + true_error) * NS_PER_S).astype(np.int64),
        _speed_profile(t_gps_true),
        max_lag_s=5.0,
        grid_rate_hz=10.0,
        min_overlap_s=30.0,
        min_correlation=0.9,
        max_gap_ref_ns=to_ns(0.5),
        max_gap_tgt_ns=to_ns(3.0),
    )
    assert est.reliable
    assert est.offset_s == pytest.approx(-true_error, abs=0.05)


def test_clock_offset_flags_unreliable_cases() -> None:
    t = np.arange(0, 20, 0.1)
    short = estimate_offset_xcorr(
        (t * NS_PER_S).astype(np.int64),
        _speed_profile(t),
        (t * NS_PER_S).astype(np.int64),
        _speed_profile(t),
        max_lag_s=5.0,
        grid_rate_hz=10.0,
        min_overlap_s=30.0,
        min_correlation=0.9,
        max_gap_ref_ns=to_ns(0.5),
        max_gap_tgt_ns=to_ns(0.5),
    )
    assert not short.reliable and short.offset_s is None
    t = np.arange(0, 100, 0.1)
    flat = estimate_offset_xcorr(
        (t * NS_PER_S).astype(np.int64),
        np.ones_like(t),
        (t * NS_PER_S).astype(np.int64),
        np.ones_like(t),
        max_lag_s=5.0,
        grid_rate_hz=10.0,
        min_overlap_s=30.0,
        min_correlation=0.9,
        max_gap_ref_ns=to_ns(0.5),
        max_gap_tgt_ns=to_ns(0.5),
    )
    assert not flat.reliable
