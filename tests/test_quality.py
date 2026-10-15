"""Data-quality control: timing, gap classes, interval classification, stream checks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.quality import (
    GapThresholds,
    canonical_nominal_rates,
    classify_intervals,
    gaze_quality,
    gps_quality,
    hands_quality,
    nominal_rates_from_profile,
    pose_quality,
    recording_quality,
    status_fractions,
    timing_quality,
    tracking_breaks,
    window_quality,
)
from ariagen_escooter.synchronization import interpolate_to_grid

NS = 1_000_000_000
TH = GapThresholds(jitter_factor=1.5, short_gap_s=0.5, medium_gap_s=2.0)


def _times(rate: float, duration: float, drop: slice | None = None, t0: int = 5 * NS) -> np.ndarray:
    t = (t0 + np.arange(int(duration * rate)) * NS / rate).astype(np.int64)
    if drop is not None:
        t = np.delete(t, np.arange(t.size)[drop])
    return t


def test_timing_counts_dropouts_and_classifies_gaps() -> None:
    t = _times(10.0, 60.0)
    t = np.delete(t, [100, 200, 201, 202, 203, 204] + list(range(300, 320)))  # 0.2 s, 0.6 s, 2.1 s gaps
    rep = timing_quality(t, "pose", 10.0, TH, span=(int(t[0]), int(t[-1])))
    assert rep["status"] == "ok"
    assert rep["gap_counts"] == {"dropped_samples": 0, "short_gap": 1, "medium_gap": 1, "long_gap": 1}
    assert rep["n_missing_samples_estimated"] == 26
    assert rep["dropout_fraction"] == pytest.approx(26 / 600, abs=2e-3)
    assert rep["rate_deviation_percent"] < 0


def test_timing_flags_duplicates_out_of_order_and_invalid() -> None:
    t = _times(30.0, 5.0)
    t = np.r_[t[:10], t[9], t[11:20], t[25], t[20:25], t[26:], 0]
    rep = timing_quality(t, "gaze", 30.0, TH, span=(int(t[1]), int(t[-2])))
    assert rep["n_duplicates"] == 1 and rep["n_out_of_order"] >= 1 and rep["n_invalid_timestamps"] == 1


def test_effective_rate_deviation_from_nominal() -> None:
    t = _times(797.0, 10.0)  # high-frequency VIO is ~797 Hz, nominal 800
    rep = timing_quality(t, "pose_hf", 800.0, GapThresholds(1.5, 0.05, 0.5))
    assert rep["effective_rate_hz"] == pytest.approx(797.0, rel=1e-3)
    assert rep["rate_deviation_percent"] == pytest.approx(-0.375, abs=0.05)


def test_interval_classification_never_hides_gaps() -> None:
    t = _times(10.0, 20.0)
    t = np.delete(t, list(range(50, 53)) + list(range(100, 110)) + list(range(150, 180)))
    span = (int(t[0]) - NS, int(t[-1]) + NS)
    iv = classify_intervals(t, None, span, 10.0, TH, stream="pose")
    status = dict(zip(iv["reason"], iv["status"]))
    assert status["short_gap"] == "interpolable" and status["medium_gap"] == "degraded"
    assert status["long_gap"] == "unusable" and status["before_first_valid_sample"] == "unusable"
    fr = status_fractions(iv, *span)
    assert sum(fr.values()) == pytest.approx(1.0)
    assert fr["unusable"] > 0.1


def test_invalid_samples_and_resets_are_not_observed() -> None:
    t = _times(10.0, 10.0)
    valid = np.ones(t.size, bool)
    valid[30:40] = False  # 1.1 s without valid samples -> degraded
    iv = classify_intervals(t, valid, (int(t[0]), int(t[-1])), 10.0, TH, stream="pose",
                            breaks_ns=np.array([t[70]]))
    assert "tracking_reset" in ";".join(iv["reason"])
    assert (iv["status"] == "degraded").sum() >= 1


def test_pose_quality_detects_resets_and_jumps() -> None:
    t = _times(10.0, 10.0)
    x = np.linspace(0, 50, t.size)
    x[60] += 30.0  # 30 m in 0.1 s: discontinuity
    pose = pd.DataFrame({"t_ns": t, "x_m": x, "y_m": 0.0, "z_m": 1.6, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                         "valid": True, "vio_status": "VALID", "tracking_quality": "GOOD",
                         "tracking_session": ["a"] * 80 + ["b"] * (t.size - 80)})
    pose.loc[5, ["valid", "tracking_quality"]] = [False, "BAD"]
    rep = pose_quality(pose, max_speed_mps=15.0, max_angular_rate_degps=720.0)
    assert rep["n_resets"] == 1 and rep["n_tracking_sessions"] == 2
    assert rep["n_position_jumps"] == 2  # into and out of the outlier
    assert rep["tracking_quality_counts"] == {"BAD": 1, "GOOD": t.size - 1}
    assert tracking_breaks(pose).tolist() == [int(t[80])]


def test_interpolation_never_crosses_a_reset() -> None:
    t = np.array([0, 100, 200, 300]) * 1_000_000
    v = np.array([0.0, 1.0, 50.0, 51.0])
    q = np.array([150]) * 1_000_000
    assert np.isfinite(interpolate_to_grid(t, v, q, 500_000_000))
    assert np.isnan(interpolate_to_grid(t, v, q, 500_000_000, breaks_ns=np.array([t[2]])))[0]


def test_gaze_hands_gps_checks() -> None:
    gaze = pd.DataFrame({"t_ns": [0, 1, 2], "valid": [True, False, True], "yaw_rad": 0.0, "pitch_rad": 0.0,
                         "u_px": [1.0, np.nan, np.nan], "left_valid": [True, False, True]})
    g = gaze_quality(gaze)
    assert g["valid_fraction"] == pytest.approx(2 / 3) and g["projected_in_image_fraction"] == pytest.approx(1 / 3)
    assert "confidence_note" in g
    t = _times(10.0, 3.0)
    hands = pd.DataFrame({"t_ns": t, "left_present": [True] * 10 + [False] * 15 + [True] * 5,
                          "left_confidence": 0.9, "right_present": False})
    h = hands_quality(hands, 0.5)
    assert h["left"]["present_fraction"] == pytest.approx(0.5) and h["left"]["n_absence_episodes"] == 1
    assert "never interpreted" in h["note"]
    gps = pd.DataFrame({"t_ns": [0, 1, 2, 3], "lat_deg": [44.1, np.nan, 44.1, 0.0], "lon_deg": [12.2, np.nan, 12.2, 0.0],
                        "accuracy_m": [3.0, np.nan, 15.0, np.nan]})
    q = gps_quality(gps, 10.0)
    assert q["fix_fraction"] == 0.5 and q["fraction_within_accuracy_threshold"] == 0.5


def test_profile_rates_snake_and_camel_case() -> None:
    camel = {"rgbCamera": {"rateHz": 15}, "et": {"rateHz": 30}, "imus": {"rateHz": 800}, "vio": {"rateHz": 10},
             "ht": {"rateHz": 10}, "gps": {"rateHz": 1}}
    snake = {"rgb_camera": {"rate_hz": 15}, "et": {"rate_hz": 30}, "vio_high_frequency_pose": {"rate_hz": 800}}
    assert nominal_rates_from_profile(camel) == {"frames": 15, "gaze": 30, "imu": 800, "pose": 10, "hands": 10, "gps": 1}
    assert nominal_rates_from_profile(snake) == {"frames": 15, "gaze": 30, "pose_hf": 800}
    assert canonical_nominal_rates({"imu": 800.0}, 100.0, 100.0) == {"imu": 100.0, "pose_hf": 100.0}


def test_recording_quality_and_window_flags() -> None:
    t = _times(10.0, 30.0)
    pose = pd.DataFrame({"t_ns": t, "x_m": np.linspace(0, 100, t.size), "y_m": 0.0, "z_m": 0.0})
    gaze_t = _times(30.0, 30.0)
    gaze = pd.DataFrame({"t_ns": gaze_t, "valid": np.r_[np.ones(450, bool), np.zeros(gaze_t.size - 450, bool)],
                         "yaw_rad": 0.0, "pitch_rad": 0.0})
    span = (int(t[0]), int(t[-1]))
    th = {"pose": TH, "gaze": GapThresholds(1.5, 0.1, 0.5)}
    rep, iv = recording_quality({"pose": pose, "gaze": gaze}, span, {"pose": 10.0, "gaze": 30.0}, th,
                                max_speed_mps=15, max_angular_rate_degps=720, min_hf_quality_score=0.5,
                                gps_max_accuracy_m=10, min_hand_confidence=0.5)
    assert set(rep["streams"]) == {"pose", "gaze"} and set(iv["stream"]) == {"pose", "gaze"}
    first = window_quality(iv, span[0], span[0] + 10 * NS, ("pose", "gaze"), 0.8)
    second = window_quality(iv, span[0] + 20 * NS, span[1], ("pose", "gaze"), 0.8)
    assert first["quality_flag"] == "ok" and second["quality_flag"] == "low_coverage"
    assert second["q_gaze_unusable"] > 0.9


def test_hand_metrics_use_only_detected_samples() -> None:
    from ariagen_escooter.hands import window_hand_metrics

    t = _times(10.0, 2.0)
    n = t.size
    hands = pd.DataFrame({"t_ns": t, "left_present": [True] * 10 + [False] * (n - 10), "left_confidence": 0.9,
                          "left_wrist_x_m": 0.2, "left_wrist_y_m": -0.3, "left_wrist_z_m": 0.3,
                          "right_present": True, "right_confidence": [0.2] * 5 + [0.9] * (n - 5),
                          "right_wrist_x_m": -0.2, "right_wrist_y_m": -0.3, "right_wrist_z_m": 0.3})
    m = window_hand_metrics(hands, int(t[0]), int(t[-1]), min_confidence=0.5)
    assert m["hand_left_detected_fraction"] == pytest.approx(0.5)
    assert m["hand_right_detected_fraction"] == pytest.approx(0.75)  # low-confidence detections excluded
    assert m["hand_left_wrist_vertical_median_m"] == pytest.approx(-0.3)
    assert m["hand_inter_wrist_distance_median_m"] == pytest.approx(0.4)
    assert window_hand_metrics(None, 0, 1, 0.5) == {}
