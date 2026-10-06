"""Route segments, events/interactions and perception -> action metrics.

* Route segments (main unit of analysis) carry one infrastructure class and
  must not overlap. Events/interactions may overlap each other and any
  segment, so analysis windows such as
  ``protected_cycle_path + pedestrian_interaction`` are obtained by
  intersecting the two tables (:func:`event_context`).
* Neutral vocabulary: "event", "interaction", "risk proxy". No event is
  automatically called a hazard or near miss.

Perception -> action metrics per event (all optional, NaN + status when not
estimable)::

    first gaze on target --> action onset (first deceleration) --> max deceleration
            |                                                    --> min speed / clearance
            +--> visual anticipation = t_reference - t_first_gaze
                 perception-to-action latency = t_action_onset - t_first_gaze
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ariagen_escooter.config import EventsConfig, Taxonomy
from ariagen_escooter.streams import ANNOTATION_SPECS, NS_PER_S, Issue, coerce_table
from ariagen_escooter.synchronization import find_runs


def prepare_annotations(df: pd.DataFrame, kind: str, taxonomy: Taxonomy) -> tuple[pd.DataFrame, list[Issue]]:
    """Coerce and validate a segments/events table against schema and taxonomy."""
    spec = ANNOTATION_SPECS[kind]
    out, issues = coerce_table(df, spec)
    if any(i.level == "error" for i in issues):
        return out, issues
    id_col = "segment_id" if kind == "segments" else "event_id"
    if out[id_col].duplicated().any():
        issues.append(Issue("error", "duplicate_ids", f"duplicated {id_col}", kind))
    bad = out["t_end_ns"] <= out["t_start_ns"]
    if bad.any():
        issues.append(Issue("error", "bad_interval", f"{int(bad.sum())} rows with t_end_ns <= t_start_ns", kind))
    if kind == "segments":
        unknown = sorted(set(out["infrastructure_class"]) - set(taxonomy.infrastructure_classes))
        if unknown:
            issues.append(Issue("error", "unknown_class", f"infrastructure classes not in taxonomy: {unknown}", kind))
        ordered = out.sort_values("t_start_ns", kind="mergesort")
        overlap = ordered["t_start_ns"].to_numpy()[1:] < ordered["t_end_ns"].to_numpy()[:-1]
        if overlap.any():
            issues.append(Issue("error", "overlap", f"{int(overlap.sum())} overlapping segments", kind))
        out = ordered.reset_index(drop=True)
    else:
        unknown = sorted(set(out["event_type"]) - set(taxonomy.event_types))
        if unknown:
            issues.append(Issue("error", "unknown_type", f"event types not in taxonomy: {unknown}", kind))
        if "tags" in out.columns:
            tags = {tag for value in out["tags"] for tag in str(value).split(";") if tag.strip()}
            unknown_tags = sorted(tags - set(taxonomy.event_types))
            if unknown_tags:
                issues.append(Issue("error", "unknown_tag", f"event tags not in taxonomy: {unknown_tags}", kind))
        if "target_class" in out.columns:
            targets = {x for x in out["target_class"] if x}
            unknown_targets = sorted(targets - set(taxonomy.semantic_names))
            if unknown_targets:
                issues.append(
                    Issue("error", "unknown_target", f"target classes not in taxonomy: {unknown_targets}", kind)
                )
        if "t_reference_ns" in out.columns:
            ref = out["t_reference_ns"]
            outside = ref.notna() & ((ref < out["t_start_ns"]) | (ref > out["t_end_ns"]))
            if outside.any():
                issues.append(
                    Issue(
                        "warning",
                        "reference_outside",
                        f"{int(outside.sum())} reference times outside their event",
                        kind,
                    )
                )
        out = out.sort_values("t_start_ns", kind="mergesort").reset_index(drop=True)
    return out, issues


def segment_at(t_ns: np.ndarray, segments: pd.DataFrame) -> np.ndarray:
    """Row index of the segment containing each time (-1 if none)."""
    t = np.asarray(t_ns, dtype=np.int64)
    out = np.full(t.shape, -1, dtype=np.int64)
    for k, (start, end) in enumerate(zip(segments["t_start_ns"], segments["t_end_ns"], strict=True)):
        out[(t >= start) & (t <= end)] = k
    return out


def event_context(events: pd.DataFrame, segments: pd.DataFrame) -> pd.DataFrame:
    """Event x segment overlaps: one row per (event, overlapping segment)."""
    rows = []
    for _, ev in events.iterrows():
        e0, e1 = int(ev["t_start_ns"]), int(ev["t_end_ns"])
        for _, seg in segments.iterrows():
            s0, s1 = int(seg["t_start_ns"]), int(seg["t_end_ns"])
            overlap = min(e1, s1) - max(e0, s0)
            if overlap > 0:
                rows.append(
                    {
                        "event_id": ev["event_id"],
                        "event_type": ev["event_type"],
                        "segment_id": seg["segment_id"],
                        "infrastructure_class": seg["infrastructure_class"],
                        "overlap_s": overlap / NS_PER_S,
                        "overlap_fraction_of_event": overlap / (e1 - e0),
                    }
                )
    return pd.DataFrame(
        rows,
        columns=[
            "event_id",
            "event_type",
            "segment_id",
            "infrastructure_class",
            "overlap_s",
            "overlap_fraction_of_event",
        ],
    )


def first_gaze_on_target(
    table: pd.DataFrame,
    t_from_ns: int,
    t_to_ns: int,
    target_class: str | None,
    target_instance: int | None,
    min_dwell_s: float,
    max_sample_weight_s: float,
) -> tuple[int | None, str]:
    """First time the gaze rests on the target for >= ``min_dwell_s``.

    Matches the instance id when given, otherwise the semantic class.
    Returns (t_ns or None, status).
    """
    if not target_class and not target_instance:
        return None, "no_target_defined"
    t = table["t_ns"].to_numpy()
    window = (t >= t_from_ns) & (t <= t_to_ns)
    ok = window & (table["gaze_status"].to_numpy() == "valid") & (table["lookup_status"].to_numpy() == "ok")
    if not ok.any():
        return None, "no_valid_labelled_gaze_in_window"
    if target_instance:
        hit = ok & (table["instance_id"].to_numpy() == int(target_instance))
        if target_class:
            hit &= table["semantic_class"].to_numpy() == target_class
    else:
        hit = ok & (table["semantic_class"].to_numpy() == target_class)
    w = table["weight_s"].to_numpy()
    dt = np.r_[np.diff(t) / NS_PER_S, np.inf]
    for start, end in find_runs(hit):
        idx = np.arange(start, end + 1)
        pieces = np.split(idx, np.flatnonzero(dt[idx[:-1]] > max_sample_weight_s + 1e-9) + 1)
        for piece in pieces:
            duration = (t[piece[-1]] - t[piece[0]]) / NS_PER_S + w[piece[-1]]
            if duration >= min_dwell_s:
                return int(t[piece[0]]), "ok"
    return None, "target_not_observed"


def action_onset(
    kin: pd.DataFrame, t_from_ns: int, t_to_ns: int, threshold_mps2: float, min_duration_s: float
) -> tuple[int | None, str]:
    """First deceleration (accel <= -threshold) lasting >= min duration in [from, to]."""
    t = kin["t_ns"].to_numpy()
    accel = kin["accel_mps2"].to_numpy()
    window = (t >= t_from_ns) & (t <= t_to_ns)
    if not (window & np.isfinite(accel)).any():
        return None, "no_kinematics_in_window"
    dt = float(np.median(np.diff(t))) / NS_PER_S
    decel = window & np.isfinite(accel) & (accel <= -threshold_mps2)
    for start, end in find_runs(decel):
        if (end - start + 1) * dt >= min_duration_s:
            return int(t[start]), "ok"
    return None, "no_deceleration_detected"


def perception_action(
    events: pd.DataFrame,
    *,
    gaze_table: pd.DataFrame | None,
    kin: pd.DataFrame | None,
    segments: pd.DataFrame | None,
    cfg: EventsConfig,
    max_sample_weight_s: float,
) -> pd.DataFrame:
    """Per-event perception -> action metrics with explicit status codes."""
    rows = []
    for _, ev in events.iterrows():
        e0, e1 = int(ev["t_start_ns"]), int(ev["t_end_ns"])
        ref_value = ev.get("t_reference_ns", np.nan)
        has_ref = ref_value is not None and np.isfinite(ref_value)
        t_ref = int(ref_value) if has_ref else e0
        target_class = str(ev.get("target_class", "") or "") or None
        inst_value = ev.get("target_instance_id", np.nan)
        target_instance = (
            int(inst_value) if inst_value is not None and np.isfinite(inst_value) and inst_value > 0 else None
        )
        search_from = e0 - int(cfg.first_gaze_lookback_s * NS_PER_S)

        row: dict[str, object] = {
            "event_id": ev["event_id"],
            "event_type": ev["event_type"],
            "tags": ev.get("tags", ""),
            "target_class": target_class or "",
            "target_instance_id": target_instance or 0,
            "t_start_ns": e0,
            "t_end_ns": e1,
            "t_reference_ns": t_ref,
            "reference_source": "annotated" if has_ref else "event_start",
            "interaction_duration_s": (e1 - e0) / NS_PER_S,
        }
        if segments is not None and len(segments):
            idx = segment_at(np.array([t_ref]), segments)[0]
            row["infrastructure_class_at_reference"] = segments["infrastructure_class"].iat[idx] if idx >= 0 else ""
        else:
            row["infrastructure_class_at_reference"] = ""

        t_gaze, gaze_status = (None, "no_gaze_stream")
        if gaze_table is not None:
            # searched up to the event END: a target first seen after the reference
            # instant (e.g. a vehicle overtaking from behind) gives a negative anticipation
            t_gaze, gaze_status = first_gaze_on_target(
                gaze_table,
                search_from,
                e1,
                target_class,
                target_instance,
                cfg.first_gaze_min_dwell_s,
                max_sample_weight_s,
            )
        row["t_first_gaze_ns"] = t_gaze
        row["first_gaze_status"] = gaze_status
        row["visual_anticipation_s"] = (t_ref - t_gaze) / NS_PER_S if t_gaze is not None else np.nan

        t_act, act_status = (None, "no_kinematics")
        if kin is not None and len(kin):
            act_from = t_gaze if t_gaze is not None else search_from
            t_act, act_status = action_onset(
                kin,
                act_from,
                e1 + int(cfg.action_search_after_s * NS_PER_S),
                cfg.action_decel_threshold_mps2,
                cfg.action_min_duration_s,
            )
        row["t_action_onset_ns"] = t_act
        row["action_status"] = act_status
        row["perception_action_latency_s"] = (
            (t_act - t_gaze) / NS_PER_S if (t_act is not None and t_gaze is not None) else np.nan
        )
        if kin is not None and len(kin):
            t = kin["t_ns"].to_numpy()
            m = (t >= e0) & (t <= e1 + int(cfg.action_search_after_s * NS_PER_S))
            accel = kin["accel_mps2"].to_numpy()
            speed = kin["speed_mps"].to_numpy()
            if (m & np.isfinite(accel)).any():
                k = int(np.nanargmin(np.where(m, accel, np.nan)))
                row["max_decel_mps2"] = float(accel[k])
                row["t_max_decel_ns"] = int(t[k])
            else:
                row["max_decel_mps2"], row["t_max_decel_ns"] = np.nan, None
            row["min_speed_mps"] = (
                float(np.nanmin(np.where(m, speed, np.nan))) if (m & np.isfinite(speed)).any() else np.nan
            )
            row["speed_at_start_mps"] = _value_at(t, speed, e0)
            row["speed_at_first_gaze_mps"] = _value_at(t, speed, t_gaze) if t_gaze is not None else np.nan
        else:
            row.update(
                max_decel_mps2=np.nan,
                t_max_decel_ns=None,
                min_speed_mps=np.nan,
                speed_at_start_mps=np.nan,
                speed_at_first_gaze_mps=np.nan,
            )
        # Clearance needs the distance to the target (depth / 3-D tracking): planned.
        row["min_clearance_m"] = np.nan
        row["clearance_status"] = "not_estimable_no_distance_source"
        rows.append(row)
    return pd.DataFrame(rows)


def _value_at(t: np.ndarray, values: np.ndarray, t_query: int) -> float:
    if len(t) == 0:
        return float("nan")
    k = int(np.argmin(np.abs(t - t_query)))
    step = np.median(np.diff(t)) if len(t) > 1 else 0
    return float(values[k]) if abs(int(t[k]) - t_query) <= step else float("nan")
