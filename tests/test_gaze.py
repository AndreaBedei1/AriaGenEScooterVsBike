"""Semantic gaze: geometry conventions, lookup, quality handling and metrics."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.gaze import (
    bcea,
    build_semantic_gaze,
    compute_dwells,
    derive_gaze,
    detect_fixations,
    direction_from_yaw_pitch,
    quat_to_rotmat,
    rotmat_to_quat,
    sample_weights,
    shannon_entropy,
    transition_counts,
    transition_entropy,
    window_gaze_metrics,
    yaw_pitch_from_direction,
)
from ariagen_escooter.segmentation import LabelMapStore
from ariagen_escooter.streams import NS_PER_S

NAMES = ("unknown", "road", "pedestrian", "car")


def test_cpf_convention_positive_yaw_is_left() -> None:
    d = direction_from_yaw_pitch(np.array([0.2, 0.0]), np.array([0.0, 0.1]))
    assert d[0, 0] > 0 and abs(d[0, 1]) < 1e-12  # +yaw -> +x = wearer's left
    assert d[1, 1] > 0  # +pitch -> up
    yaw, pitch = yaw_pitch_from_direction(d)
    assert np.allclose(yaw, [0.2, 0.0]) and np.allclose(pitch, [0.0, 0.1])


def test_quaternion_roundtrip() -> None:
    rng = np.random.default_rng(0)
    q = rng.normal(size=(20, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    q[q[:, 0] < 0] *= -1
    r = quat_to_rotmat(q)
    assert np.allclose(np.einsum("nij,nkj->nik", r, r), np.eye(3), atol=1e-12)
    assert np.allclose(rotmat_to_quat(r), q, atol=1e-9)


def _store() -> LabelMapStore:
    # 4x3 label map for a 400x300 image: columns of 100 px -> road | pedestrian | car | road
    labels = np.array([[[1, 2, 3, 1]] * 3, [[1, 1, 1, 1]] * 3], dtype=np.uint8)
    instances = np.array([[[0, 7, 9, 0]] * 3, [[0, 0, 0, 0]] * 3], dtype=np.uint16)
    return LabelMapStore(np.array([0, 2]), labels, NAMES, (400, 300), "test", instances)


def _frames() -> pd.DataFrame:
    return pd.DataFrame({"t_ns": [0, 100_000_000, 200_000_000], "frame_index": [0, 1, 2]})


def _gaze(u, v, valid=None, t=None) -> pd.DataFrame:
    n = len(u)
    return pd.DataFrame(
        {
            "t_ns": t if t is not None else np.zeros(n, dtype=np.int64),
            "valid": valid if valid is not None else np.ones(n, dtype=bool),
            "yaw_rad": np.zeros(n),
            "pitch_rad": np.zeros(n),
            "u_px": u,
            "v_px": v,
        }
    )


def test_lookup_status_and_classes(cfg: LoadedConfig) -> None:
    g = _gaze(
        u=[150.0, 250.0, 50.0, -10.0, 150.0, np.nan, 150.0],
        v=[100.0, 100.0, 100.0, 100.0, 100.0, np.nan, 100.0],
        valid=[True, True, True, True, True, True, False],
        t=np.array([0, 0, 0, 0, 100_000_000, 0, 0], dtype=np.int64),
    )
    table = build_semantic_gaze(
        g,
        frames=_frames(),
        store=_store(),
        pose=None,
        kinematics=None,
        cfg=cfg.analysis.gaze,
        frame_tolerance_s=0.05,
        pose_max_gap_s=0.5,
    )
    assert table["lookup_status"].tolist() == [
        "ok",
        "ok",
        "ok",
        "off_frame",
        "no_label_map",
        "no_gaze_point",
        "not_applicable",
    ]
    assert table["gaze_status"].tolist()[-1] == "invalid"
    assert table["semantic_class"].tolist()[:3] == ["pedestrian", "car", "road"]
    assert table["instance_id"].tolist()[:3] == [7, 9, 0]


def test_pixel_centre_convention_at_borders(cfg: LoadedConfig) -> None:
    # integer coordinates are pixel centres: the image spans [-0.5, W-0.5)
    g = _gaze(u=[-0.4, 399.4, 399.6], v=[0.0, 0.0, 0.0])
    table = build_semantic_gaze(
        g,
        frames=_frames(),
        store=_store(),
        pose=None,
        kinematics=None,
        cfg=cfg.analysis.gaze,
        frame_tolerance_s=0.05,
        pose_max_gap_s=0.5,
    )
    assert table["lookup_status"].tolist() == ["ok", "ok", "off_frame"]


def test_no_frame_within_tolerance(cfg: LoadedConfig) -> None:
    g = _gaze(u=[150.0], v=[100.0], t=np.array([400_000_000]))
    table = build_semantic_gaze(
        g,
        frames=_frames(),
        store=_store(),
        pose=None,
        kinematics=None,
        cfg=cfg.analysis.gaze,
        frame_tolerance_s=0.05,
        pose_max_gap_s=0.5,
    )
    assert table["lookup_status"].iat[0] == "no_frame"


def test_radius_majority_lookup(cfg: LoadedConfig) -> None:
    gaze_cfg = cfg.analysis.gaze.model_copy(update={"lookup_radius_px": 120.0})
    g = _gaze(u=[195.0], v=[150.0])  # pedestrian column, near the car column
    table = build_semantic_gaze(
        g,
        frames=_frames(),
        store=_store(),
        pose=None,
        kinematics=None,
        cfg=gaze_cfg,
        frame_tolerance_s=0.05,
        pose_max_gap_s=0.5,
    )
    assert table["semantic_class"].iat[0] in {"pedestrian", "car", "road"}
    assert 0 < table["label_agreement"].iat[0] < 1


def test_low_confidence_samples_are_excluded(cfg: LoadedConfig) -> None:
    gaze_cfg = cfg.analysis.gaze.model_copy(update={"min_confidence": 0.5})
    g = _gaze(u=[150.0, 150.0, 150.0], v=[100.0] * 3)
    g["confidence"] = [0.9, 0.2, np.nan]
    table = build_semantic_gaze(
        g,
        frames=_frames(),
        store=_store(),
        pose=None,
        kinematics=None,
        cfg=gaze_cfg,
        frame_tolerance_s=0.05,
        pose_max_gap_s=0.5,
    )
    assert table["gaze_status"].tolist() == ["valid", "low_confidence", "low_confidence"]


def test_sample_weights_are_capped() -> None:
    t = (np.array([0.0, 0.033, 0.066, 1.0, 1.033]) * NS_PER_S).astype(np.int64)
    w = sample_weights(t, 0.1)
    assert np.allclose(w, [0.033, 0.033, 0.1, 0.033, 0.033], atol=1e-3)


def _table(classes: list[str | None], dt: float = 1 / 30) -> pd.DataFrame:
    n = len(classes)
    t = (np.arange(n) * dt * NS_PER_S).astype(np.int64)
    valid = np.array([c is not None for c in classes])
    return pd.DataFrame(
        {
            "t_ns": t,
            "weight_s": sample_weights(t, 0.1),
            "gaze_status": np.where(valid, "valid", "invalid"),
            "lookup_status": np.where(valid, "ok", "not_applicable"),
            "semantic_class": [c if c is not None else None for c in classes],
            "instance_id": 0,
            "eye_yaw_deg": np.where(valid, 0.0, np.nan),
            "eye_pitch_deg": np.where(valid, 0.0, np.nan),
            "gaze_az_world_deg": np.nan,
            "gaze_el_world_deg": np.nan,
            "head_az_world_deg": np.nan,
            "travel_heading_deg": np.nan,
            "gaze_yaw_rel_travel_deg": np.nan,
            "head_yaw_rel_travel_deg": np.nan,
        }
    )


def test_dwells_bridge_short_blinks_only() -> None:
    blink = ["road"] * 6 + [None] * 3 + ["road"] * 6 + ["car"] * 6  # 0.1 s blink inside a road dwell
    dw = compute_dwells(_table(blink), bridge_gap_s=0.15)
    assert dw["semantic_class"].tolist() == ["road", "car"]
    assert dw["duration_s"].iat[0] == pytest.approx(15 / 30, abs=0.01)
    long_gap = ["road"] * 6 + [None] * 9 + ["road"] * 6
    assert len(compute_dwells(_table(long_gap), bridge_gap_s=0.15)) == 2


def test_transition_entropy_and_counts() -> None:
    seq = (["road"] * 6 + ["car"] * 6) * 4  # deterministic alternation
    dw = compute_dwells(_table(seq), 0.15)
    counts = transition_counts(dw, 0.15)
    assert counts == Counter({("road", "car"): 4, ("car", "road"): 3})
    assert transition_entropy(counts) == pytest.approx(0.0)
    assert shannon_entropy(np.full(4, 0.25)) == pytest.approx(2.0)


def test_invalid_time_never_attributed_to_a_class(cfg: LoadedConfig) -> None:
    seq = ["road"] * 30 + [None] * 30 + ["car"] * 30
    derived = derive_gaze(_table(seq), cfg.analysis.gaze)
    t1 = int(89 / 30 * NS_PER_S)
    metrics, class_time = window_gaze_metrics(derived, 0, t1, cfg.analysis.gaze, cfg.taxonomy)
    assert metrics["gaze_valid_fraction"] == pytest.approx(2 / 3, abs=0.02)
    assert metrics["share_road"] == pytest.approx(0.5, abs=0.02)
    assert metrics["share_car"] == pytest.approx(0.5, abs=0.02)
    assert class_time["unknown"] == 0.0
    assert metrics["share_group_vehicles"] == pytest.approx(metrics["share_car"])


def test_ivt_fixations(cfg: LoadedConfig) -> None:
    n = 60
    table = _table(["road"] * n)
    yaw = np.r_[np.zeros(20), np.linspace(0, 20, 3)[1:], np.full(n - 22, 20.0)]
    table["eye_yaw_deg"] = yaw
    frame, fix = detect_fixations(table, cfg.analysis.gaze)
    assert frame == "eye_in_head"
    assert len(fix) == 2
    assert fix["duration_s"].iat[0] == pytest.approx(20 / 30, abs=0.05)


def test_bcea_matches_definition() -> None:
    rng = np.random.default_rng(0)
    x, y = rng.normal(0, 2.0, 20000), rng.normal(0, 1.0, 20000)
    k = -np.log(1 - 0.682)
    assert bcea(x, y, 0.682) == pytest.approx(2 * k * np.pi * 2.0 * 1.0, rel=0.03)
