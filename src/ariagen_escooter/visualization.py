"""Diagnostic figures (matplotlib, non-interactive backend).

Figures are for quality control, not for publication: they show the trimming
decision, kinematics, route segments, events and the semantic gaze timeline
so that a researcher can spot problems quickly.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from ariagen_escooter.streams import NS_PER_S  # noqa: E402

_CLASS_COLORS = {
    "road": "#7f7f7f",
    "cycle_lane": "#d62728",
    "sidewalk": "#c7a26a",
    "crossing": "#f2f2f2",
    "curb": "#8c564b",
    "pedestrian": "#1f77b4",
    "cyclist": "#17becf",
    "bicycle": "#9edae5",
    "escooter": "#e377c2",
    "motorcycle": "#ff9896",
    "car": "#ff7f0e",
    "large_vehicle": "#ffbb78",
    "parked_vehicle": "#bcbd22",
    "traffic_sign": "#ffd700",
    "traffic_light": "#2ca02c",
    "obstacle": "#000000",
    "vegetation": "#98df8a",
    "building": "#c5b0d5",
    "sky": "#aec7e8",
    "other": "#dbdb8d",
    "unknown": "#ffffff",
}
_SEGMENT_COLORS = plt.get_cmap("tab10")


def _rel(t_ns, t0: int) -> np.ndarray:
    return (np.asarray(t_ns, dtype=np.float64) - t0) / NS_PER_S


def plot_overview(
    out_path: Path,
    *,
    title: str,
    t0_ns: int,
    speed_raw: tuple[np.ndarray, np.ndarray] | None,
    trimming: dict,
    kin: pd.DataFrame | None,
    segments: pd.DataFrame | None,
    events: pd.DataFrame | None,
    gaze_table: pd.DataFrame | None,
    class_names: tuple[str, ...],
    yaw_column: str | None,
    synthetic: bool,
) -> Path:
    """Four stacked panels sharing the time axis (seconds from recording start)."""
    fig, axes = plt.subplots(
        4, 1, figsize=(14, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1.3, 2, 2]}, layout="constrained"
    )
    ax_speed, ax_ctx, ax_sem, ax_yaw = axes

    if speed_raw is not None:
        ax_speed.plot(_rel(speed_raw[0], t0_ns), speed_raw[1], color="0.6", lw=1, label="speed (trimming input)")
    if kin is not None and len(kin):
        ax_speed.plot(_rel(kin["t_ns"], t0_ns), kin["speed_mps"], color="tab:blue", lw=1.5, label="speed (kinematics)")
    trimmed = trimming["trimmed_interval"]
    ax_speed.axvspan(
        trimmed["start_rel_s"], trimmed["end_rel_s"], color="tab:green", alpha=0.12, label="trimmed session"
    )
    detected = trimming["detected_riding_interval"]
    for key in ("start_rel_s", "end_rel_s"):
        if detected.get(key) is not None:
            ax_speed.axvline(detected[key], color="tab:green", ls="--", lw=1)
    threshold = trimming["parameters"].get("speed_threshold_mps")
    if threshold:
        ax_speed.axhline(threshold, color="tab:red", ls=":", lw=1, label="moving threshold")
    ax_speed.set_ylabel("speed [m/s]")
    ax_speed.legend(loc="upper right", fontsize=8)
    ax_speed.set_title(title + (" - SYNTHETIC DATA" if synthetic else ""), fontsize=11)

    ax_ctx.set_ylim(0, 2)
    ax_ctx.set_yticks([0.5, 1.5], ["events", "segments"])
    handles = []
    if segments is not None and len(segments):
        classes = sorted(segments["infrastructure_class"].unique())
        for _, seg in segments.iterrows():
            color = _SEGMENT_COLORS(classes.index(seg["infrastructure_class"]) % 10)
            ax_ctx.axvspan(
                *_rel([seg["t_start_ns"], seg["t_end_ns"]], t0_ns), ymin=0.5, ymax=1.0, color=color, alpha=0.6
            )
        handles = [Patch(color=_SEGMENT_COLORS(i % 10), alpha=0.6, label=c) for i, c in enumerate(classes)]
    if events is not None and len(events):
        for k, (_, ev) in enumerate(events.iterrows()):
            x0, x1 = _rel([ev["t_start_ns"], ev["t_end_ns"]], t0_ns)
            y = 0.1 + 0.8 * ((k % 3) / 3)
            ax_ctx.plot([x0, x1], [y, y], lw=5, color="tab:purple", solid_capstyle="butt")
            ax_ctx.text(x0, y + 0.12, ev["event_type"], fontsize=6)
    if handles:
        ax_ctx.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.005, 1.0), fontsize=7, borderaxespad=0)

    if gaze_table is not None and len(gaze_table):
        t = _rel(gaze_table["t_ns"], t0_ns)
        names = list(class_names)
        sem = gaze_table["semantic_class"].to_numpy()
        ok = np.array([s is not None and s in names for s in sem])
        ys = np.array([names.index(s) if k else np.nan for s, k in zip(sem, ok, strict=True)])
        colors = [_CLASS_COLORS.get(s, "#000000") if k else "none" for s, k in zip(sem, ok, strict=True)]
        ax_sem.scatter(t[ok], ys[ok], c=[c for c, k in zip(colors, ok, strict=True) if k], s=4, marker="|")
        invalid = gaze_table["gaze_status"].to_numpy() != "valid"
        ax_sem.scatter(t[invalid], np.full(invalid.sum(), -1), s=4, marker="|", color="red")
        ax_sem.set_yticks(range(-1, len(names)), ["invalid"] + names, fontsize=6)
        ax_sem.set_ylabel("gaze on")
        if yaw_column and yaw_column in gaze_table.columns:
            ax_yaw.plot(t, gaze_table[yaw_column], lw=0.6, color="tab:orange", label=yaw_column)
            if "head_yaw_rel_travel_deg" in gaze_table.columns and yaw_column == "gaze_yaw_rel_travel_deg":
                ax_yaw.plot(
                    t, gaze_table["head_yaw_rel_travel_deg"], lw=1, color="tab:gray", label="head yaw rel. travel"
                )
            ax_yaw.axhline(0, color="k", lw=0.5)
            ax_yaw.set_ylabel("yaw [deg] (+ = left)")
            ax_yaw.legend(loc="upper right", fontsize=7)
    ax_yaw.set_xlabel("time from recording start [s]")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path


def plot_trajectory(
    out_path: Path,
    *,
    title: str,
    kin: pd.DataFrame,
    segments: pd.DataFrame | None,
    events: pd.DataFrame | None,
    synthetic: bool,
) -> Path:
    """Planar trajectory (local metric frame) coloured by infrastructure class."""
    fig, ax = plt.subplots(figsize=(7, 7))
    t = kin["t_ns"].to_numpy()
    ax.plot(kin["x_m"], kin["y_m"], color="0.75", lw=3, zorder=1)
    if segments is not None and len(segments):
        classes = sorted(segments["infrastructure_class"].unique())
        for _, seg in segments.iterrows():
            m = (t >= seg["t_start_ns"]) & (t <= seg["t_end_ns"])
            color = _SEGMENT_COLORS(classes.index(seg["infrastructure_class"]) % 10)
            ax.plot(kin["x_m"][m], kin["y_m"][m], color=color, lw=2, zorder=2)
        ax.legend(handles=[Patch(color=_SEGMENT_COLORS(i % 10), label=c) for i, c in enumerate(classes)], fontsize=8)
    if events is not None and len(events):
        for _, ev in events.iterrows():
            k = int(np.argmin(np.abs(t - ev["t_start_ns"])))
            ax.plot(kin["x_m"].iat[k], kin["y_m"].iat[k], "k^", ms=6, zorder=3)
            ax.annotate(ev["event_id"].split("_")[-1], (kin["x_m"].iat[k], kin["y_m"].iat[k]), fontsize=7)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("x [m] (local frame)")
    ax.set_ylabel("y [m] (local frame)")
    ax.set_title(title + (" - SYNTHETIC DATA" if synthetic else ""), fontsize=10)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
