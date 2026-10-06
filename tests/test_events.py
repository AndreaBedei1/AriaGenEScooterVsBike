"""Segments/events validation, context windows and perception -> action metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.events import (
    action_onset,
    event_context,
    first_gaze_on_target,
    perception_action,
    prepare_annotations,
)
from ariagen_escooter.gaze import sample_weights
from ariagen_escooter.pipeline import _annotation_rel_to_ns
from ariagen_escooter.streams import NS_PER_S


def _s(x: float) -> int:
    return int(round(x * NS_PER_S))


def _segments() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "segment_id": ["S1", "S2"],
            "t_start_ns": [_s(0), _s(10)],
            "t_end_ns": [_s(10), _s(20)],
            "infrastructure_class": ["protected_cycle_path", "crossing"],
            "source": "manual",
        }
    )


def test_segments_validation(cfg: LoadedConfig) -> None:
    ok, issues = prepare_annotations(_segments(), "segments", cfg.taxonomy)
    assert not issues
    bad = _segments()
    bad.loc[1, "infrastructure_class"] = "motorway"
    bad.loc[1, "t_start_ns"] = _s(9)  # overlap
    _, issues = prepare_annotations(bad, "segments", cfg.taxonomy)
    assert {i.code for i in issues} == {"unknown_class", "overlap"}


def test_events_validation(cfg: LoadedConfig) -> None:
    ev = pd.DataFrame(
        {
            "event_id": ["E1"],
            "t_start_ns": [_s(2)],
            "t_end_ns": [_s(1)],
            "event_type": ["hazard"],
            "tags": ["overtaking;near_miss"],
            "target_class": ["unicorn"],
            "source": "manual",
        }
    )
    _, issues = prepare_annotations(ev, "events", cfg.taxonomy)
    assert {"bad_interval", "unknown_type", "unknown_tag", "unknown_target"} <= {i.code for i in issues}


def test_relative_seconds_are_converted() -> None:
    df = pd.DataFrame({"t_start_rel_s": [1.5], "t_end_rel_s": [2.0], "t_reference_rel_s": [np.nan]})
    out = _annotation_rel_to_ns(df, start_ns=1_000)
    assert out["t_start_ns"].iat[0] == 1_000 + 1_500_000_000
    assert np.isnan(out["t_reference_ns"].iat[0])


def test_event_context_overlaps() -> None:
    ev = pd.DataFrame(
        {"event_id": ["E1"], "event_type": ["pedestrian_interaction"], "t_start_ns": [_s(8)], "t_end_ns": [_s(12)]}
    )
    ctx = event_context(ev, _segments())
    assert ctx["infrastructure_class"].tolist() == ["protected_cycle_path", "crossing"]
    assert ctx["overlap_fraction_of_event"].tolist() == pytest.approx([0.5, 0.5])


def _gaze_table(classes: list[str | None], instances: list[int] | None = None, start: float = 0.0) -> pd.DataFrame:
    n = len(classes)
    t = (np.round((start + np.arange(n) / 30) * NS_PER_S)).astype(np.int64)
    valid = np.array([c is not None for c in classes])
    return pd.DataFrame(
        {
            "t_ns": t,
            "weight_s": sample_weights(t, 0.1),
            "gaze_status": np.where(valid, "valid", "invalid"),
            "lookup_status": np.where(valid, "ok", "not_applicable"),
            "semantic_class": classes,
            "instance_id": instances if instances is not None else [0] * n,
        }
    )


def test_first_gaze_requires_min_dwell_and_matches_instance() -> None:
    classes = ["road"] * 30 + ["pedestrian"] * 2 + ["road"] * 10 + ["pedestrian"] * 10
    instances = [0] * 30 + [5] * 2 + [0] * 10 + [4] * 5 + [5] * 5
    table = _gaze_table(classes, instances)
    t, status = first_gaze_on_target(table, 0, _s(5), "pedestrian", None, 0.1, 0.1)
    assert status == "ok" and t == table["t_ns"].iat[42]  # the 2-sample glance at 1.0 s is too short
    t, status = first_gaze_on_target(table, 0, _s(5), "pedestrian", 5, 0.1, 0.1)
    assert t == table["t_ns"].iat[47]
    assert first_gaze_on_target(table, 0, _s(5), None, None, 0.1, 0.1) == (None, "no_target_defined")
    assert first_gaze_on_target(table, 0, _s(5), "car", None, 0.1, 0.1) == (None, "target_not_observed")


def _kin(keys) -> pd.DataFrame:
    t = np.arange(0, 30, 0.1)
    kt, kv = np.array(keys).T
    speed = np.interp(t, kt, kv)
    return pd.DataFrame(
        {"t_ns": (t * NS_PER_S).astype(np.int64), "speed_mps": speed, "accel_mps2": np.gradient(speed, 0.1)}
    )


def test_action_onset() -> None:
    kin = _kin([(0, 5), (10, 5), (12, 3), (30, 3)])
    t, status = action_onset(kin, 0, _s(20), 0.5, 0.2)
    assert status == "ok" and t / NS_PER_S == pytest.approx(10.0, abs=0.15)
    assert action_onset(kin, _s(15), _s(20), 0.5, 0.2) == (None, "no_deceleration_detected")


def test_perception_action_latency_and_anticipation(cfg: LoadedConfig) -> None:
    gaze = _gaze_table(["road"] * 240 + ["pedestrian"] * 60 + ["road"] * 300)  # first look at 8.0 s
    kin = _kin([(0, 5), (9, 5), (11, 2), (30, 2)])  # deceleration from 9.0 s
    events = pd.DataFrame(
        {
            "event_id": ["E1"],
            "event_type": ["pedestrian_interaction"],
            "tags": [""],
            "target_class": ["pedestrian"],
            "target_instance_id": [np.nan],
            "t_start_ns": [_s(7)],
            "t_end_ns": [_s(15)],
            "t_reference_ns": [_s(12)],
        }
    )
    row = perception_action(
        events, gaze_table=gaze, kin=kin, segments=_segments(), cfg=cfg.analysis.events, max_sample_weight_s=0.1
    ).iloc[0]
    assert row["first_gaze_status"] == "ok" and row["action_status"] == "ok"
    assert row["visual_anticipation_s"] == pytest.approx(4.0, abs=0.05)
    assert row["perception_action_latency_s"] == pytest.approx(1.0, abs=0.15)
    assert row["infrastructure_class_at_reference"] == "crossing"
    assert row["clearance_status"].startswith("not_estimable") and np.isnan(row["min_clearance_m"])


def test_missing_gaze_gives_nan_with_reason(cfg: LoadedConfig) -> None:
    events = pd.DataFrame({"event_id": ["E1"], "event_type": ["stopping"], "t_start_ns": [_s(7)], "t_end_ns": [_s(15)]})
    row = perception_action(
        events, gaze_table=None, kin=None, segments=None, cfg=cfg.analysis.events, max_sample_weight_s=0.1
    ).iloc[0]
    assert row["first_gaze_status"] == "no_gaze_stream" and row["action_status"] == "no_kinematics"
    assert np.isnan(row["perception_action_latency_s"]) and np.isnan(row["visual_anticipation_s"])
