"""Semantic gaze: timestamp -> gaze point -> semantic class/object -> metrics.

Conventions
-----------
* Eye-in-head angles follow the Aria CPF (central pupil frame) convention
  used by projectaria_tools: direction ~ (tan(yaw), tan(pitch), 1) with
  +x = wearer's left, +y = up, +z = forward. Positive yaw = LEFT.
* World azimuths are counter-clockwise from the world +x axis (z up), so a
  positive yaw relative to the direction of travel also means LEFT.
* The pose quaternion (qw, qx, qy, qz) rotates CPF vectors into the world.

Data-quality rules (never invent data)
--------------------------------------
* Each sample is weighted by the time to the next sample, capped at
  ``max_sample_weight_s``; time inside longer gaps is unobserved.
* ``gaze_status``: valid | invalid (tracking lost, NaN angles) |
  low_confidence. Only valid samples are looked up.
* ``lookup_status``: ok | no_gaze_point (no image projection) | off_frame
  (projection outside the image) | no_frame (no RGB frame within tolerance) |
  no_label_map (frame not segmented) | not_applicable (gaze not valid).
* Class shares are computed over labelled time only and always reported
  together with validity/coverage fractions. No interpolation of gaze.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ariagen_escooter.config import GazeConfig, Taxonomy
from ariagen_escooter.segmentation import LabelMapStore
from ariagen_escooter.streams import NS_PER_S
from ariagen_escooter.synchronization import find_runs, interpolate_to_grid, nearest_indices
from ariagen_escooter.trajectory import unwrap_nan_aware, wrap_angle

GAZE_STATUS = ("valid", "invalid", "low_confidence")
LOOKUP_STATUS = ("ok", "no_gaze_point", "off_frame", "no_frame", "no_label_map", "not_applicable")


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #
def direction_from_yaw_pitch(yaw_rad: np.ndarray, pitch_rad: np.ndarray) -> np.ndarray:
    """Unit gaze directions in CPF, shape (N, 3)."""
    yaw = np.asarray(yaw_rad, dtype=np.float64)
    pitch = np.asarray(pitch_rad, dtype=np.float64)
    d = np.stack([np.tan(yaw), np.tan(pitch), np.ones_like(yaw)], axis=-1)
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def yaw_pitch_from_direction(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Inverse of :func:`direction_from_yaw_pitch` (valid for forward directions, z > 0)."""
    d = np.asarray(d, dtype=np.float64)
    return np.arctan2(d[..., 0], d[..., 2]), np.arctan2(d[..., 1], d[..., 2])


def quat_to_rotmat(q: np.ndarray) -> np.ndarray:
    """Rotation matrices from (w, x, y, z) quaternions, shape (N, 3, 3)."""
    q = np.asarray(q, dtype=np.float64)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack(
        [
            np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], axis=-1),
            np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], axis=-1),
            np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], axis=-1),
        ],
        axis=-2,
    )


def rotmat_to_quat(r: np.ndarray) -> np.ndarray:
    """(w, x, y, z) quaternions from rotation matrices (N, 3, 3), w >= 0."""
    r = np.asarray(r, dtype=np.float64)
    m00, m11, m22 = r[..., 0, 0], r[..., 1, 1], r[..., 2, 2]
    w = np.sqrt(np.maximum(0.0, 1 + m00 + m11 + m22)) / 2
    x = np.sqrt(np.maximum(0.0, 1 + m00 - m11 - m22)) / 2
    y = np.sqrt(np.maximum(0.0, 1 - m00 + m11 - m22)) / 2
    z = np.sqrt(np.maximum(0.0, 1 - m00 - m11 + m22)) / 2
    x = np.copysign(x, r[..., 2, 1] - r[..., 1, 2])
    y = np.copysign(y, r[..., 0, 2] - r[..., 2, 0])
    z = np.copysign(z, r[..., 1, 0] - r[..., 0, 1])
    q = np.stack([w, x, y, z], axis=-1)
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def interpolate_quaternions(
    t_src_ns: np.ndarray,
    q_src: np.ndarray,
    t_query_ns: np.ndarray,
    max_gap_ns: int,
    breaks_ns: np.ndarray | None = None,
) -> np.ndarray:
    """Normalised linear interpolation (nlerp) of orientations, gap-aware.

    Consecutive quaternions are first aligned to the same hemisphere. Accurate
    for the small rotations between consecutive pose samples.
    """
    q = np.asarray(q_src, dtype=np.float64).copy()
    for i in range(1, len(q)):
        if np.dot(q[i - 1], q[i]) < 0:
            q[i] = -q[i]
    out = np.stack(
        [interpolate_to_grid(t_src_ns, q[:, k], t_query_ns, max_gap_ns, breaks_ns) for k in range(4)], axis=-1
    )
    norm = np.linalg.norm(out, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore"):
        return out / norm


def sample_weights(t_ns: np.ndarray, max_weight_s: float) -> np.ndarray:
    """Duration represented by each sample (s): time to the next sample, capped."""
    t = np.asarray(t_ns, dtype=np.int64)
    if t.size == 0:
        return np.zeros(0)
    dt = np.diff(t) / NS_PER_S
    last = float(np.median(dt)) if dt.size else max_weight_s
    return np.minimum(np.r_[dt, last], max_weight_s)


# --------------------------------------------------------------------------- #
# Sample-level semantic gaze table
# --------------------------------------------------------------------------- #
def _lookup(
    u: np.ndarray, v: np.ndarray, rows: np.ndarray, store: LabelMapStore, radius_px: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Class id, instance id and agreement at (u, v) for samples with a map row.

    Returns (class_id, instance_id, agreement, inside) with -1 / NaN where not
    applicable; ``inside`` tells whether the point lies inside the image.
    """
    n = u.size
    cls = np.full(n, -1, dtype=np.int64)
    inst = np.zeros(n, dtype=np.int64)
    agree = np.full(n, np.nan)
    src_w, src_h = store.source_size
    map_w, map_h = store.map_size
    # projectaria_tools pixel convention: integer coordinates at pixel centres,
    # the image spans [-0.5, W - 0.5) x [-0.5, H - 0.5).
    inside = (u >= -0.5) & (u < src_w - 0.5) & (v >= -0.5) & (v < src_h - 0.5)
    use = inside & (rows >= 0)
    if not use.any():
        return cls, inst, agree, inside
    sx, sy = map_w / src_w, map_h / src_h
    col = np.clip(np.floor((u[use] + 0.5) * sx).astype(np.int64), 0, map_w - 1)
    row = np.clip(np.floor((v[use] + 0.5) * sy).astype(np.int64), 0, map_h - 1)
    frame_rows = rows[use]
    if radius_px <= 0:
        cls[use] = store.labels[frame_rows, row, col]
        agree[use] = 1.0
    else:
        r = radius_px * (sx + sy) / 2.0
        span = int(np.ceil(r))
        dr, dc = np.mgrid[-span : span + 1, -span : span + 1]
        disc = (dr**2 + dc**2) <= r**2
        dr, dc = dr[disc], dc[disc]
        out_cls = np.empty(frame_rows.size, dtype=np.int64)
        out_agree = np.empty(frame_rows.size)
        for k in range(frame_rows.size):
            rr = row[k] + dr
            cc = col[k] + dc
            keep = (rr >= 0) & (rr < map_h) & (cc >= 0) & (cc < map_w)
            values = store.labels[frame_rows[k], rr[keep], cc[keep]].astype(np.int64)
            counts = np.bincount(values)
            best = np.flatnonzero(counts == counts.max())
            centre = int(store.labels[frame_rows[k], row[k], col[k]])
            choice = centre if centre in best else int(best[0])
            out_cls[k] = choice
            out_agree[k] = counts[choice] / values.size
        cls[use] = out_cls
        agree[use] = out_agree
    if store.instances is not None:
        inst[use] = store.instances[frame_rows, row, col]
    return cls, inst, agree, inside


def build_semantic_gaze(
    gaze: pd.DataFrame,
    *,
    frames: pd.DataFrame | None,
    store: LabelMapStore | None,
    pose: pd.DataFrame | None,
    kinematics: pd.DataFrame | None,
    cfg: GazeConfig,
    frame_tolerance_s: float,
    pose_max_gap_s: float,
) -> pd.DataFrame:
    """Sample-level table: validity, frame match, semantic class, angles per frame of reference."""
    t = gaze["t_ns"].to_numpy(dtype=np.int64)
    n = t.size
    yaw = gaze["yaw_rad"].to_numpy(dtype=np.float64)
    pitch = gaze["pitch_rad"].to_numpy(dtype=np.float64)
    valid = gaze["valid"].to_numpy(dtype=bool) & np.isfinite(yaw) & np.isfinite(pitch)
    status = np.where(valid, "valid", "invalid").astype(object)
    if cfg.min_confidence is not None and "confidence" in gaze.columns:
        conf = gaze["confidence"].to_numpy(dtype=np.float64)
        low = valid & ~(conf >= cfg.min_confidence)  # NaN confidence counts as low
        status[low] = "low_confidence"
        valid = valid & ~low

    u = gaze["u_px"].to_numpy(dtype=np.float64) if "u_px" in gaze.columns else np.full(n, np.nan)
    v = gaze["v_px"].to_numpy(dtype=np.float64) if "v_px" in gaze.columns else np.full(n, np.nan)

    lookup = np.full(n, "not_applicable", dtype=object)
    frame_index = np.full(n, -1, dtype=np.int64)
    frame_dt_ms = np.full(n, np.nan)
    class_id = np.full(n, -1, dtype=np.int64)
    instance = np.zeros(n, dtype=np.int64)
    agreement = np.full(n, np.nan)

    has_point = valid & np.isfinite(u) & np.isfinite(v)
    lookup[valid & ~has_point] = "no_gaze_point"
    if frames is not None and len(frames):
        ft = frames["t_ns"].to_numpy(dtype=np.int64)
        fidx = frames["frame_index"].to_numpy(dtype=np.int64)
        match, delta = nearest_indices(t, ft, int(frame_tolerance_s * NS_PER_S))
        matched = match >= 0
        frame_index[matched] = fidx[match[matched]]
        frame_dt_ms[matched] = delta[matched] / 1e6
    else:
        matched = np.zeros(n, dtype=bool)
    lookup[has_point & ~matched] = "no_frame"
    if store is not None:
        rows = np.array([store.row(f) if f >= 0 and store.has(f) else -1 for f in frame_index], dtype=np.int64)
        cls, inst, agree, inside = _lookup(u, v, rows, store, cfg.lookup_radius_px)
        cand = has_point & matched
        lookup[cand & ~inside] = "off_frame"
        lookup[cand & inside & (rows < 0)] = "no_label_map"
        ok = cand & inside & (rows >= 0)
        lookup[ok] = "ok"
        class_id[ok], instance[ok], agreement[ok] = cls[ok], inst[ok], agree[ok]
        names = np.array(store.class_names, dtype=object)
        semantic = np.where(class_id >= 0, names[np.clip(class_id, 0, None)], None)
    else:
        lookup[has_point & matched] = "no_label_map"
        semantic = np.full(n, None, dtype=object)

    table = pd.DataFrame(
        {
            "t_ns": t,
            "weight_s": sample_weights(t, cfg.max_sample_weight_s),
            "gaze_status": status,
            "lookup_status": lookup,
            "frame_index": frame_index,
            "frame_dt_ms": frame_dt_ms,
            "u_px": u,
            "v_px": v,
            "semantic_class": semantic,
            "instance_id": instance,
            "label_agreement": agreement,
            "eye_yaw_deg": np.degrees(np.where(valid, yaw, np.nan)),
            "eye_pitch_deg": np.degrees(np.where(valid, pitch, np.nan)),
        }
    )
    _add_world_angles(table, valid, yaw, pitch, pose, kinematics, pose_max_gap_s)
    return table


def _add_world_angles(
    table: pd.DataFrame,
    valid: np.ndarray,
    yaw: np.ndarray,
    pitch: np.ndarray,
    pose: pd.DataFrame | None,
    kinematics: pd.DataFrame | None,
    pose_max_gap_s: float,
) -> None:
    n = len(table)
    nan = np.full(n, np.nan)
    cols = {
        "gaze_az_world_deg": nan.copy(),
        "gaze_el_world_deg": nan.copy(),
        "head_az_world_deg": nan.copy(),
        "travel_heading_deg": nan.copy(),
        "gaze_yaw_rel_travel_deg": nan.copy(),
        "head_yaw_rel_travel_deg": nan.copy(),
    }
    quat_cols = ["qw", "qx", "qy", "qz"]
    if pose is not None and len(pose) >= 2 and all(c in pose.columns for c in quat_cols):
        t = table["t_ns"].to_numpy()
        q = interpolate_quaternions(
            pose["t_ns"].to_numpy(),
            pose[quat_cols].to_numpy(),
            t,
            int(pose_max_gap_s * NS_PER_S),
            pose.attrs.get("tracking_breaks_ns"),
        )
        have_q = np.all(np.isfinite(q), axis=1)
        rot = np.full((n, 3, 3), np.nan)
        rot[have_q] = quat_to_rotmat(q[have_q])
        d_cpf = direction_from_yaw_pitch(np.where(valid, yaw, 0.0), np.where(valid, pitch, 0.0))
        d_world = np.einsum("nij,nj->ni", rot, d_cpf)
        forward_world = rot[:, :, 2]
        gaze_ok = valid & have_q
        az = np.arctan2(d_world[:, 1], d_world[:, 0])
        el = np.arcsin(np.clip(d_world[:, 2], -1, 1))
        head_az = np.arctan2(forward_world[:, 1], forward_world[:, 0])
        cols["gaze_az_world_deg"] = np.degrees(np.where(gaze_ok, az, np.nan))
        cols["gaze_el_world_deg"] = np.degrees(np.where(gaze_ok, el, np.nan))
        cols["head_az_world_deg"] = np.degrees(np.where(have_q, head_az, np.nan))
        if kinematics is not None and len(kinematics) >= 2:
            kt = kinematics["t_ns"].to_numpy()
            step = int(np.median(np.diff(kt)))
            heading = interpolate_to_grid(kt, unwrap_nan_aware(kinematics["heading_rad"].to_numpy()), t, 2 * step)
            cols["travel_heading_deg"] = np.degrees(wrap_angle(heading))
            cols["gaze_yaw_rel_travel_deg"] = np.degrees(wrap_angle(np.where(gaze_ok, az, np.nan) - heading))
            cols["head_yaw_rel_travel_deg"] = np.degrees(wrap_angle(np.where(have_q, head_az, np.nan) - heading))
    for name, values in cols.items():
        table[name] = values


# --------------------------------------------------------------------------- #
# Derived gaze events
# --------------------------------------------------------------------------- #
def labelled_mask(table: pd.DataFrame) -> np.ndarray:
    return (table["gaze_status"].to_numpy() == "valid") & (table["lookup_status"].to_numpy() == "ok")


def compute_dwells(table: pd.DataFrame, bridge_gap_s: float) -> pd.DataFrame:
    """Dwells: consecutive labelled samples on the same semantic class.

    Interruptions (invalid/unlabelled samples) up to ``bridge_gap_s`` do not
    split a dwell if the class is the same before and after; the bridged time
    is part of the dwell duration (blinks inside a dwell).
    """
    cols = [
        "dwell_id",
        "semantic_class",
        "instance_id",
        "t_start_ns",
        "t_end_ns",
        "duration_s",
        "n_samples",
        "gap_before_s",
    ]
    mask = labelled_mask(table)
    if not mask.any():
        return pd.DataFrame(columns=cols)
    sub = table.loc[mask, ["t_ns", "weight_s", "semantic_class", "instance_id"]].reset_index(drop=True)
    t = sub["t_ns"].to_numpy()
    w = sub["weight_s"].to_numpy()
    cls = sub["semantic_class"].to_numpy()
    gap = np.r_[np.inf, (t[1:] - t[:-1]) / NS_PER_S - w[:-1]]
    new = np.r_[True, cls[1:] != cls[:-1]] | (gap > bridge_gap_s + 1e-9)
    dwell_no = np.cumsum(new) - 1
    rows = []
    for k in range(int(dwell_no.max()) + 1):
        idx = np.flatnonzero(dwell_no == k)
        first, last = idx[0], idx[-1]
        instances = [int(x) for x in sub["instance_id"].to_numpy()[idx] if int(x) != 0]
        rows.append(
            {
                "semantic_class": cls[first],
                "instance_id": Counter(instances).most_common(1)[0][0] if instances else 0,
                "t_start_ns": int(t[first]),
                "t_end_ns": int(t[last] + round(w[last] * NS_PER_S)),
                "duration_s": float((t[last] - t[first]) / NS_PER_S + w[last]),
                "n_samples": int(idx.size),
                "gap_before_s": float(gap[first]) if np.isfinite(gap[first]) else np.nan,
            }
        )
    df = pd.DataFrame(rows)
    df.insert(0, "dwell_id", [f"DW{i + 1:05d}" for i in range(len(df))])
    return df[cols]


def transition_counts(dwells: pd.DataFrame, bridge_gap_s: float) -> Counter:
    """Counts of class->class transitions between adjacent dwells (self-transitions excluded).

    Transitions across unobserved gaps longer than ``bridge_gap_s`` are not counted.
    """
    counts: Counter = Counter()
    if len(dwells) < 2:
        return counts
    cls = dwells["semantic_class"].to_numpy()
    gaps = dwells["gap_before_s"].to_numpy()
    for k in range(1, len(dwells)):
        if cls[k] != cls[k - 1] and np.isfinite(gaps[k]) and gaps[k] <= bridge_gap_s + 1e-9:
            counts[(cls[k - 1], cls[k])] += 1
    return counts


def shannon_entropy(probabilities: np.ndarray) -> float:
    p = np.asarray(probabilities, dtype=np.float64)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum()) if p.size else float("nan")


def transition_entropy(counts: Counter) -> float:
    """Gaze transition entropy (bits): sum_i pi_i H(p_i.), pi_i = share of transitions from i."""
    if not counts:
        return float("nan")
    origins: dict[str, Counter] = {}
    for (a, b), c in counts.items():
        origins.setdefault(a, Counter())[b] += c
    total = sum(counts.values())
    h = 0.0
    for row in origins.values():
        n_row = sum(row.values())
        h += (n_row / total) * shannon_entropy(np.array(list(row.values()), dtype=np.float64) / n_row)
    return h


def reference_angles(table: pd.DataFrame, reference: str) -> tuple[str, np.ndarray, np.ndarray]:
    """Yaw/pitch (deg) in the requested forward reference: travel or head (auto picks travel if available)."""
    has_travel = np.isfinite(table["gaze_yaw_rel_travel_deg"].to_numpy()).any()
    if reference == "travel" or (reference == "auto" and has_travel):
        return "travel", table["gaze_yaw_rel_travel_deg"].to_numpy(), table["gaze_el_world_deg"].to_numpy()
    return "head", table["eye_yaw_deg"].to_numpy(), table["eye_pitch_deg"].to_numpy()


def detect_fixations(table: pd.DataFrame, cfg: GazeConfig) -> tuple[str, pd.DataFrame]:
    """I-VT fixation detection on gaze direction (world or eye-in-head frame)."""
    fc = cfg.fixation
    has_world = np.isfinite(table["gaze_az_world_deg"].to_numpy()).any()
    frame = "world" if fc.reference_frame == "world" or (fc.reference_frame == "auto" and has_world) else "eye_in_head"
    if frame == "world":
        az = np.radians(table["gaze_az_world_deg"].to_numpy())
        el = np.radians(table["gaze_el_world_deg"].to_numpy())
        d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=-1)
    else:
        d = direction_from_yaw_pitch(
            np.radians(table["eye_yaw_deg"].to_numpy()), np.radians(table["eye_pitch_deg"].to_numpy())
        )
    t = table["t_ns"].to_numpy()
    w = table["weight_s"].to_numpy()
    ok = np.all(np.isfinite(d), axis=1) & (table["gaze_status"].to_numpy() == "valid")
    dt = np.diff(t) / NS_PER_S
    contiguous = ok[:-1] & ok[1:] & (dt <= cfg.max_sample_weight_s + 1e-9)
    cosang = np.clip(np.einsum("ij,ij->i", d[:-1], d[1:]), -1.0, 1.0)
    vel = np.full(len(t), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        fwd = np.degrees(np.arccos(cosang)) / dt
    vel[:-1] = np.where(contiguous, fwd, np.nan)
    # last sample of a contiguous chain takes the backward velocity
    back = np.r_[np.nan, np.where(contiguous, fwd, np.nan)]
    vel = np.where(np.isnan(vel), back, vel)
    candidate = ok & (vel < fc.velocity_threshold_deg_s)
    cols = ["fixation_id", "t_start_ns", "t_end_ns", "duration_s", "n_samples", "semantic_class", "instance_id"]
    rows = []
    semantic = table["semantic_class"].to_numpy()
    instances = table["instance_id"].to_numpy()
    labelled = labelled_mask(table)
    # split candidate runs where samples are not contiguous in time
    breaks = np.r_[False, ~contiguous]
    run_mask = candidate.copy()
    for start, end in find_runs(run_mask):
        segments_ = np.split(np.arange(start, end + 1), np.flatnonzero(breaks[start + 1 : end + 1]) + 1)
        for idx in segments_:
            if idx.size == 0:
                continue
            duration = float((t[idx[-1]] - t[idx[0]]) / NS_PER_S + w[idx[-1]])
            if duration < fc.min_duration_s:
                continue
            lab = idx[labelled[idx]]
            if lab.size:
                weights: Counter = Counter()
                for i in lab:
                    weights[semantic[i]] += w[i]
                dominant = weights.most_common(1)[0][0]
                inst = Counter(int(instances[i]) for i in lab if semantic[i] == dominant).most_common(1)[0][0]
            else:
                dominant, inst = None, 0
            rows.append(
                {
                    "t_start_ns": int(t[idx[0]]),
                    "t_end_ns": int(t[idx[-1]] + round(w[idx[-1]] * NS_PER_S)),
                    "duration_s": duration,
                    "n_samples": int(idx.size),
                    "semantic_class": dominant,
                    "instance_id": inst,
                }
            )
    df = pd.DataFrame(rows, columns=cols[1:])
    df.insert(0, "fixation_id", [f"FX{i + 1:05d}" for i in range(len(df))])
    return frame, df


def detect_lateral_glances(table: pd.DataFrame, cfg: GazeConfig) -> tuple[str, pd.DataFrame]:
    """Runs where |gaze yaw w.r.t. the forward reference| exceeds the threshold."""
    gc = cfg.lateral_glance
    reference, yaw, _ = reference_angles(table, cfg.forward.reference)
    t = table["t_ns"].to_numpy()
    w = table["weight_s"].to_numpy()
    ok = np.isfinite(yaw)
    dt = np.r_[np.diff(t) / NS_PER_S, np.inf]
    rows = []
    for side, mask in (("left", ok & (yaw > gc.yaw_threshold_deg)), ("right", ok & (yaw < -gc.yaw_threshold_deg))):
        for start, end in find_runs(mask):
            idx = np.arange(start, end + 1)
            pieces = np.split(idx, np.flatnonzero(dt[idx[:-1]] > cfg.max_sample_weight_s + 1e-9) + 1)
            for piece in pieces:
                duration = float((t[piece[-1]] - t[piece[0]]) / NS_PER_S + w[piece[-1]])
                if duration < gc.min_duration_s:
                    continue
                rows.append(
                    {
                        "side": side,
                        "t_start_ns": int(t[piece[0]]),
                        "t_end_ns": int(t[piece[-1]] + round(w[piece[-1]] * NS_PER_S)),
                        "duration_s": duration,
                        "max_abs_yaw_deg": float(np.max(np.abs(yaw[piece]))),
                    }
                )
    df = pd.DataFrame(rows, columns=["side", "t_start_ns", "t_end_ns", "duration_s", "max_abs_yaw_deg"])
    df = df.sort_values("t_start_ns", kind="mergesort").reset_index(drop=True)
    df.insert(0, "glance_id", [f"LG{i + 1:04d}" for i in range(len(df))])
    return reference, df


# --------------------------------------------------------------------------- #
# Window metrics
# --------------------------------------------------------------------------- #
def _weighted_sd(x: np.ndarray, w: np.ndarray) -> float:
    if w.sum() <= 0 or x.size < 2:
        return float("nan")
    mean = np.average(x, weights=w)
    return float(np.sqrt(np.average((x - mean) ** 2, weights=w)))


def bcea(yaw_deg: np.ndarray, pitch_deg: np.ndarray, probability: float) -> float:
    """Bivariate contour ellipse area (deg^2): 2k*pi*sx*sy*sqrt(1-rho^2), k = -ln(1-P)."""
    ok = np.isfinite(yaw_deg) & np.isfinite(pitch_deg)
    if ok.sum() < 3:
        return float("nan")
    x, y = yaw_deg[ok], pitch_deg[ok]
    sx, sy = x.std(ddof=1), y.std(ddof=1)
    if sx == 0 or sy == 0:
        return 0.0
    rho = float(np.corrcoef(x, y)[0, 1])
    k = -np.log(1.0 - probability)
    return float(2.0 * k * np.pi * sx * sy * np.sqrt(max(0.0, 1.0 - rho**2)))


def spatial_entropy(yaw_deg: np.ndarray, pitch_deg: np.ndarray, weights: np.ndarray, bin_deg: float) -> float:
    """Shannon entropy (bits) of the time-weighted 2-D gaze-angle histogram."""
    ok = np.isfinite(yaw_deg) & np.isfinite(pitch_deg)
    if not ok.any():
        return float("nan")
    bx = np.floor(yaw_deg[ok] / bin_deg).astype(np.int64)
    by = np.floor(pitch_deg[ok] / bin_deg).astype(np.int64)
    acc: dict[tuple[int, int], float] = {}
    for i, j, wt in zip(bx, by, weights[ok], strict=True):
        acc[(i, j)] = acc.get((i, j), 0.0) + float(wt)
    p = np.array(list(acc.values()))
    return shannon_entropy(p / p.sum())


@dataclass(frozen=True)
class GazeDerived:
    """Sample table plus derived events, computed once per recording."""

    table: pd.DataFrame
    dwells: pd.DataFrame
    fixations: pd.DataFrame
    fixation_frame: str
    glances: pd.DataFrame
    forward_reference: str


def derive_gaze(table: pd.DataFrame, cfg: GazeConfig) -> GazeDerived:
    dwells = compute_dwells(table, cfg.dwell_bridge_gap_s)
    frame, fixations = detect_fixations(table, cfg)
    reference, glances = detect_lateral_glances(table, cfg)
    return GazeDerived(table, dwells, fixations, frame, glances, reference)


def window_gaze_metrics(
    derived: GazeDerived, t0_ns: int, t1_ns: int, cfg: GazeConfig, taxonomy: Taxonomy
) -> tuple[dict[str, float], dict[str, float]]:
    """Gaze metrics over [t0, t1] -> (metrics, seconds per semantic class)."""
    table = derived.table
    t = table["t_ns"].to_numpy()
    m = (t >= t0_ns) & (t <= t1_ns)
    w = table["weight_s"].to_numpy()
    valid = table["gaze_status"].to_numpy() == "valid"
    labelled = labelled_mask(table)
    duration = (t1_ns - t0_ns) / NS_PER_S
    observed = float(w[m].sum())
    valid_time = float(w[m & valid].sum())
    labelled_time = float(w[m & labelled].sum())

    sem = table["semantic_class"].to_numpy()
    class_time = {name: 0.0 for name in taxonomy.semantic_names}
    for name, wt in zip(sem[m & labelled], w[m & labelled], strict=True):
        class_time[name] += float(wt)

    def share(names: list[str]) -> float:
        return sum(class_time[n] for n in names) / labelled_time if labelled_time > 0 else float("nan")

    metrics: dict[str, float] = {
        "gaze_duration_s": duration,
        "gaze_sample_coverage": observed / duration if duration > 0 else float("nan"),
        "gaze_valid_fraction": valid_time / observed if observed > 0 else float("nan"),
        "gaze_labelled_fraction": labelled_time / valid_time if valid_time > 0 else float("nan"),
        "gaze_labelled_time_s": labelled_time,
    }
    for name in taxonomy.semantic_names:
        metrics[f"share_{name}"] = share([name])
    for group, members in taxonomy.semantic_groups.items():
        metrics[f"share_group_{group}"] = share(members)
    probs = np.array([v for v in class_time.values() if v > 0])
    metrics["semantic_entropy_bits"] = shannon_entropy(probs / probs.sum()) if probs.size else float("nan")
    metrics["semantic_entropy_norm"] = (
        metrics["semantic_entropy_bits"] / np.log2(len(taxonomy.semantic_names)) if probs.size else float("nan")
    )

    dw = derived.dwells
    dw_in = dw[(dw["t_start_ns"] >= t0_ns) & (dw["t_start_ns"] <= t1_ns)] if len(dw) else dw
    counts = transition_counts(dw_in, cfg.dwell_bridge_gap_s) if len(dw_in) else Counter()
    n_trans = int(sum(counts.values()))
    minutes = labelled_time / 60.0
    metrics.update(
        {
            "n_dwells": int(len(dw_in)),
            "dwell_mean_s": float(dw_in["duration_s"].mean()) if len(dw_in) else float("nan"),
            "dwell_median_s": float(dw_in["duration_s"].median()) if len(dw_in) else float("nan"),
            "n_transitions": n_trans,
            "transition_rate_per_min": n_trans / minutes if minutes > 0 else float("nan"),
            "transition_entropy_bits": transition_entropy(counts),
        }
    )

    fx = derived.fixations
    fx_in = fx[(fx["t_start_ns"] >= t0_ns) & (fx["t_start_ns"] <= t1_ns)] if len(fx) else fx
    valid_min = valid_time / 60.0
    metrics.update(
        {
            "n_fixations": int(len(fx_in)),
            "fixation_rate_per_min": len(fx_in) / valid_min if valid_min > 0 else float("nan"),
            "fixation_mean_s": float(fx_in["duration_s"].mean()) if len(fx_in) else float("nan"),
            "fixation_median_s": float(fx_in["duration_s"].median()) if len(fx_in) else float("nan"),
        }
    )

    reference, yaw_ref, pitch_ref = reference_angles(table, cfg.forward.reference)
    ref_ok = m & valid & np.isfinite(yaw_ref) & np.isfinite(pitch_ref)
    ref_time = float(w[ref_ok].sum())
    fwd = ref_ok & (np.abs(yaw_ref) <= cfg.forward.yaw_half_width_deg)
    fwd &= (pitch_ref >= cfg.forward.pitch_min_deg) & (pitch_ref <= cfg.forward.pitch_max_deg)
    metrics["forward_reference_coverage"] = ref_time / valid_time if valid_time > 0 else float("nan")
    metrics["forward_share"] = float(w[fwd].sum()) / ref_time if ref_time > 0 else float("nan")
    gl = derived.glances
    gl_in = gl[(gl["t_start_ns"] >= t0_ns) & (gl["t_start_ns"] <= t1_ns)] if len(gl) else gl
    ref_min = ref_time / 60.0
    metrics["lateral_glances_left"] = int((gl_in["side"] == "left").sum()) if len(gl_in) else 0
    metrics["lateral_glances_right"] = int((gl_in["side"] == "right").sum()) if len(gl_in) else 0
    metrics["lateral_glance_rate_per_min"] = len(gl_in) / ref_min if ref_min > 0 else float("nan")
    metrics["lateral_glance_mean_s"] = float(gl_in["duration_s"].mean()) if len(gl_in) else float("nan")
    metrics["gaze_yaw_sd_deg"] = _weighted_sd(yaw_ref[ref_ok], w[ref_ok])
    metrics["gaze_pitch_sd_deg"] = _weighted_sd(pitch_ref[ref_ok], w[ref_ok])
    metrics["gaze_bcea_deg2"] = bcea(yaw_ref[ref_ok], pitch_ref[ref_ok], cfg.dispersion.bcea_probability)
    metrics["gaze_spatial_entropy_bits"] = spatial_entropy(
        yaw_ref[ref_ok], pitch_ref[ref_ok], w[ref_ok], cfg.dispersion.entropy_bin_deg
    )
    for band in cfg.vertical_bands:
        in_band = ref_ok & (pitch_ref >= band.min_deg) & (pitch_ref < band.max_deg)
        metrics[f"vertical_share_{band.name}"] = float(w[in_band].sum()) / ref_time if ref_time > 0 else float("nan")
    head_rel = table["head_yaw_rel_travel_deg"].to_numpy()
    head_ok = m & np.isfinite(head_rel)
    metrics["head_yaw_rel_travel_sd_deg"] = _weighted_sd(head_rel[head_ok], w[head_ok])
    return metrics, class_time
