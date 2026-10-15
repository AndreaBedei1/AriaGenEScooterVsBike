"""End-to-end processing of a session (MVP) and study-level aggregation.

Per recording::

    load canonical streams + annotations + label maps
      -> validate timestamps
      -> data-quality control (rates, dropouts, classified gaps, VIO status/resets,
         gaze/hand validity, GNSS fixes) -> quality.json + quality_intervals.csv
      -> GPS clock-offset check (speed cross-correlation)
      -> ride trimming (raw -> detected riding interval -> trimmed)
      -> kinematics + behaviour metrics
      -> semantic gaze + gaze metrics
      -> segment / approach / event (perception -> action) tables
      -> report.json, tables/*.csv, trimming.json, figures/*.png

Each recording is processed with the configuration of its vehicle type
(shared parameters + optional ``analysis_overrides`` of configs/vehicles.yaml);
vehicle, trial number and ride order are carried in every output table.

The input files are only read; outputs go to ``<out_root>/<session>/<recording>/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ariagen_escooter import __version__
from ariagen_escooter.behaviour import (
    approach_behaviour,
    detect_braking_events,
    detect_stops,
    segment_behaviour,
    window_metrics,
)
from ariagen_escooter.config import AnalysisConfig, ConfigError, LoadedConfig, portable_path, read_yaml_mapping
from ariagen_escooter.events import event_context, perception_action, prepare_annotations
from ariagen_escooter.gaze import GazeDerived, build_semantic_gaze, derive_gaze, window_gaze_metrics
from ariagen_escooter.hands import window_hand_metrics
from ariagen_escooter.io import find_table, read_table, sha256_file, write_json, write_yaml
from ariagen_escooter.privacy import scan_for_identifiers
from ariagen_escooter.quality import (
    GapThresholds,
    canonical_nominal_rates,
    load_profile,
    nominal_rates_from_profile,
    recording_quality,
    tracking_breaks,
    window_quality,
)
from ariagen_escooter.reporting import SYNTHETIC_NOTICE, run_info, with_ids, write_report, write_tables
from ariagen_escooter.segmentation import LabelMapStore
from ariagen_escooter.session import (
    MANIFEST_FILENAME,
    RecordingEntry,
    RecordingLocation,
    SessionManifest,
    locate_recording,
)
from ariagen_escooter.streams import (
    NS_PER_S,
    STREAM_SPECS,
    Issue,
    check_timestamps,
    coerce_table,
    sort_and_deduplicate,
)
from ariagen_escooter.synchronization import OffsetEstimate, estimate_offset_xcorr, to_ns
from ariagen_escooter.trajectory import compute_kinematics, latlon_to_local_xy, speed_profile
from ariagen_escooter.trimming import SpeedSignal, slice_by_time, speed_for_trimming, trim_recording

DEVICE_CLOCK_STREAMS = ("frames", "gaze", "imu", "pose", "pose_hf", "hands")
QUALITY_WINDOW_STREAMS = ("pose", "gaze", "frames", "hands")
MANIFEST_STREAM_FILES = {
    "rgb": "frames",
    "eye_gaze": "gaze",
    "imu": "imu",
    "pose": "pose",
    "pose_high_frequency": "pose_hf",
    "hand_tracking": "hands",
    "gps_device": "gps",
    "gps_phone": "gps",
    "gps_external": "gps",
}
EVENT_GAZE_COLUMNS = (
    "gaze_valid_fraction",
    "gaze_labelled_fraction",
    "forward_share",
    "share_group_pedestrians",
    "share_group_other_vulnerable_road_users",
    "share_group_vehicles",
    "share_group_infrastructure",
    "lateral_glances_left",
    "lateral_glances_right",
    "n_fixations",
)


@dataclass
class RecordingData:
    recording_id: str
    location: RecordingLocation
    streams: dict[str, pd.DataFrame]
    segments: pd.DataFrame | None
    events: pd.DataFrame | None
    label_store: LabelMapStore | None
    inputs: dict[str, Path]
    issues: list[Issue] = field(default_factory=list)

    def recording_span(self) -> tuple[int, int] | None:
        starts, ends = [], []
        for name in DEVICE_CLOCK_STREAMS:
            df = self.streams.get(name)
            if df is not None and len(df):
                starts.append(int(df["t_ns"].min()))
                ends.append(int(df["t_ns"].max()))
        return (min(starts), max(ends)) if starts else None


def _annotation_rel_to_ns(df: pd.DataFrame, start_ns: int | None) -> pd.DataFrame:
    """Accept annotation times as seconds from recording start (``*_rel_s``)."""
    out = df.copy()
    for base in ("t_start", "t_end", "t_reference"):
        rel, ns = f"{base}_rel_s", f"{base}_ns"
        if ns not in out.columns and rel in out.columns:
            if start_ns is None:
                raise ConfigError("annotations use *_rel_s times but the recording start is unknown")
            values = pd.to_numeric(out[rel], errors="coerce")
            out[ns] = np.where(values.notna(), np.round(values * NS_PER_S) + start_ns, np.nan)
    return out


def load_recording_data(location: RecordingLocation, cfg: LoadedConfig) -> RecordingData:
    """Load whatever canonical files exist for a recording (all are optional)."""
    issues: list[Issue] = []
    streams: dict[str, pd.DataFrame] = {}
    inputs: dict[str, Path] = {}
    for name, spec in STREAM_SPECS.items():
        path = find_table(location.streams_dir, spec.filename_stem)
        if path is None:
            continue
        df, found = coerce_table(read_table(path), spec)
        issues.extend(Issue(i.level, i.code, i.message, f"{location.recording_id}/{name}") for i in found)
        if not any(i.level == "error" for i in found):
            streams[name] = df
            inputs[f"streams/{name}"] = path
    data = RecordingData(location.recording_id, location, streams, None, None, None, inputs, issues)
    span = data.recording_span()

    for kind in ("segments", "events"):
        path = find_table(location.annotations_dir, kind)
        if path is None:
            continue
        try:
            raw = _annotation_rel_to_ns(read_table(path), span[0] if span else None)
        except ConfigError as exc:
            issues.append(Issue("error", "annotation_time", str(exc), f"{location.recording_id}/{kind}"))
            continue
        df, found = prepare_annotations(raw, kind, cfg.taxonomy)
        issues.extend(Issue(i.level, i.code, i.message, f"{location.recording_id}/{kind}") for i in found)
        if not any(i.level == "error" for i in found):
            setattr(data, kind, df)
            inputs[f"annotations/{kind}"] = path

    label_path = portable_path(location.work_dir, cfg.analysis.segmentation.label_maps_file)
    if label_path.is_file():
        try:
            data.label_store = LabelMapStore.load(label_path).to_taxonomy(cfg.taxonomy.semantic_names)
            inputs["semantic/labels"] = label_path
        except (ConfigError, ValueError, KeyError) as exc:
            issues.append(Issue("error", "label_maps", str(exc), f"{location.recording_id}/semantic"))
    return data


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_session(session_dir: Path, cfg: LoadedConfig) -> tuple[SessionManifest | None, list[Issue]]:
    """Validate manifest, privacy rules, streams, timestamps and annotations."""
    from pydantic import ValidationError

    issues: list[Issue] = []
    path = session_dir / MANIFEST_FILENAME
    if not path.is_file():
        return None, [Issue("error", "no_manifest", f"{MANIFEST_FILENAME} not found", session_dir.name)]
    raw = read_yaml_mapping(path)
    for finding in scan_for_identifiers(raw, cfg.analysis.privacy.forbidden_manifest_keys):
        issues.append(Issue("error", "privacy", str(finding), "manifest"))
    try:
        manifest = SessionManifest.model_validate(raw)
    except ValidationError as exc:
        issues.append(Issue("error", "manifest_schema", str(exc).replace("\n", " | "), "manifest"))
        return None, issues
    if session_dir.name != manifest.session_id:
        issues.append(Issue("warning", "folder_name", f"folder {session_dir.name!r} != session_id", "manifest"))
    a = cfg.analysis
    profile = manifest.equipment.recording_profile
    if profile and not manifest.synthetic and _profile_path(cfg, profile) is None:
        issues.append(Issue("warning", "profile_unknown",
                            f"recording profile {profile!r} not found in configs/{a.quality.profiles_dir}: "
                            "nominal rates fall back to observed median intervals", "manifest"))
    for entry in manifest.recordings:
        where = entry.recording_id
        trial = manifest.trial_of(entry.recording_id)
        if trial.vehicle_type not in cfg.vehicles.vehicle_types:
            issues.append(Issue("error", "unknown_vehicle",
                                f"vehicle_type {trial.vehicle_type!r} not in configs/vehicles.yaml "
                                f"({sorted(cfg.vehicles.vehicle_types)})", where))
        loc = locate_recording(session_dir, manifest.session_id, entry.recording_id, cfg.data_root)
        if not loc.streams_dir.is_dir():
            issues.append(Issue("warning", "no_streams", "no canonical streams yet (run extract-aria on Linux)", where))
            continue
        data = load_recording_data(loc, cfg)
        issues.extend(data.issues)
        span = data.recording_span()
        for name, df in data.streams.items():
            rep = check_timestamps(
                df["t_ns"].to_numpy(),
                name,
                a.timestamps.gap_factor,
                a.timestamps.max_reported_gaps,
                span[0] if span else None,
            )
            issues.extend(Issue(i.level, i.code, i.message, f"{where}/{name}") for i in rep.issues)
        for key, status in entry.streams.items():
            stream = MANIFEST_STREAM_FILES.get(key)
            if stream is None:
                continue
            present = stream in data.streams
            if status.value == "available" and not present:
                issues.append(
                    Issue(
                        "warning", "stream_missing", f"manifest says {key} available but {stream}.csv not found", where
                    )
                )
        if data.label_store is not None and "frames" in data.streams:
            unknown = set(data.label_store.frame_index.tolist()) - set(data.streams["frames"]["frame_index"].tolist())
            if unknown:
                issues.append(
                    Issue("warning", "label_frames", f"{len(unknown)} label maps refer to unknown frames", where)
                )
        if entry.trimming_override is not None and span is not None:
            duration = (span[1] - span[0]) / NS_PER_S
            if entry.trimming_override.start_rel_s >= duration:
                issues.append(
                    Issue("error", "override_outside", "trimming_override starts after the recording end", where)
                )
    return manifest, issues


# --------------------------------------------------------------------------- #
# Processing
# --------------------------------------------------------------------------- #
def _profile_path(cfg: LoadedConfig, name: str) -> Path | None:
    path = cfg.project_root / "configs" / cfg.analysis.quality.profiles_dir / f"{name}.json"
    return path if path.is_file() else None


def nominal_rates(cfg: LoadedConfig, manifest: SessionManifest) -> tuple[dict[str, float], str]:
    """Nominal canonical-stream rates: recording profile (if known), config overrides."""
    a = cfg.analysis
    rates: dict[str, float] = {}
    source = "observed_median_interval"
    name = manifest.equipment.recording_profile
    path = _profile_path(cfg, name) if name else None
    if path is not None:
        rates = nominal_rates_from_profile(load_profile(path))
        source = f"recording_profile:{name}"
    rates = canonical_nominal_rates(rates, a.aria.imu_rate_hz, a.aria.pose_hf_rate_hz) if rates else rates
    for stream, sq in a.quality.streams.items():
        if sq.nominal_rate_hz is not None:
            rates[stream] = sq.nominal_rate_hz
            source += f"+config:{stream}"
    return rates, source


def _valid_pose(df: pd.DataFrame | None) -> tuple[pd.DataFrame | None, np.ndarray]:
    """Keep only valid pose samples; return the tracking-reset instants (breaks)."""
    if df is None:
        return None, np.empty(0, dtype=np.int64)
    breaks = tracking_breaks(df)
    out = df[df["valid"].astype(bool)].reset_index(drop=True) if "valid" in df.columns else df
    out.attrs["tracking_breaks_ns"] = breaks
    return out, breaks


def _gps_offset(
    pose: pd.DataFrame, gps: pd.DataFrame, a: AnalysisConfig, breaks: np.ndarray | None = None
) -> tuple[OffsetEstimate, SpeedSignal | None]:
    co = a.synchronization.clock_offset
    grid, pose_speed = speed_profile(
        pose["t_ns"].to_numpy(),
        pose["x_m"].to_numpy(),
        pose["y_m"].to_numpy(),
        rate_hz=co.grid_rate_hz,
        window_s=a.trimming.smoothing_window_s,
        polyorder=a.kinematics.savgol_polyorder,
        max_gap_s=a.synchronization.pose_max_gap_s,
        breaks_ns=breaks,
    )
    t_gps = gps["t_ns"].to_numpy()
    if "speed_mps" in gps.columns and gps["speed_mps"].notna().mean() > 0.9:
        gps_speed = gps["speed_mps"].to_numpy()
    else:
        lat0, lon0 = float(gps["lat_deg"].iat[0]), float(gps["lon_deg"].iat[0])
        x, y = latlon_to_local_xy(gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy(), lat0, lon0)
        t_gps, gps_speed = speed_profile(
            t_gps,
            x,
            y,
            rate_hz=co.grid_rate_hz,
            window_s=a.trimming.smoothing_window_s,
            polyorder=a.kinematics.savgol_polyorder,
            max_gap_s=a.synchronization.gps_max_gap_s,
        )
    estimate = estimate_offset_xcorr(
        grid,
        pose_speed,
        t_gps,
        gps_speed,
        max_lag_s=co.max_lag_s,
        grid_rate_hz=co.grid_rate_hz,
        min_overlap_s=co.min_overlap_s,
        min_correlation=co.min_correlation,
        max_gap_ref_ns=to_ns(a.synchronization.pose_max_gap_s),
        max_gap_tgt_ns=to_ns(a.synchronization.gps_max_gap_s),
    )
    return estimate, SpeedSignal(grid, pose_speed, "pose")


def _clip_segments(segments: pd.DataFrame | None, t0: int, t1: int) -> pd.DataFrame | None:
    if segments is None:
        return None
    seg = segments[(segments["t_end_ns"] > t0) & (segments["t_start_ns"] < t1)].copy()
    clipped = (seg["t_start_ns"] < t0) | (seg["t_end_ns"] > t1)
    seg["t_start_ns"] = seg["t_start_ns"].clip(lower=t0)
    seg["t_end_ns"] = seg["t_end_ns"].clip(upper=t1)
    seg["clipped_by_trimming"] = clipped
    return seg.reset_index(drop=True)


def _kinematics(
    trimmed: dict[str, pd.DataFrame], a: AnalysisConfig, t0: int, t1: int, breaks: np.ndarray | None = None
) -> tuple[pd.DataFrame | None, str | None]:
    order = {"auto": ("pose", "gps"), "pose": ("pose",), "gps": ("gps",)}[a.kinematics.source]
    for source in order:
        df = trimmed.get(source)
        if df is None or len(df) < 2:
            continue
        if source == "pose":
            x, y, gap = df["x_m"].to_numpy(), df["y_m"].to_numpy(), a.synchronization.pose_max_gap_s
        else:
            x, y = latlon_to_local_xy(
                df["lat_deg"].to_numpy(),
                df["lon_deg"].to_numpy(),
                float(df["lat_deg"].iat[0]),
                float(df["lon_deg"].iat[0]),
            )
            gap = a.synchronization.gps_max_gap_s
        kin = compute_kinematics(
            df["t_ns"].to_numpy(),
            x,
            y,
            a.kinematics,
            max_gap_s=gap,
            start_ns=t0,
            end_ns=t1,
            breaks_ns=breaks if source == "pose" else None,
        )
        return kin, source
    return None, None


def _class_time_rows(window_type: str, window_id: str, class_time: dict[str, float]) -> list[dict[str, object]]:
    total = sum(class_time.values())
    return [
        {
            "window_type": window_type,
            "window_id": window_id,
            "semantic_class": name,
            "time_s": seconds,
            "share": seconds / total if total > 0 else np.nan,
        }
        for name, seconds in class_time.items()
    ]


def process_recording(
    session_dir: Path,
    manifest: SessionManifest,
    entry: RecordingEntry,
    cfg: LoadedConfig,
    out_root: Path,
    make_plots: bool | None = None,
) -> dict[str, object]:
    """Process one recording; returns the report dictionary (also written to disk)."""
    trial = manifest.trial_of(entry.recording_id)
    if cfg.vehicle_type != trial.vehicle_type:
        cfg = cfg.for_vehicle(trial.vehicle_type)
    a = cfg.analysis
    decimals = a.reporting.float_decimals
    loc = locate_recording(session_dir, manifest.session_id, entry.recording_id, cfg.data_root)
    out_dir = out_root / manifest.session_id / entry.recording_id
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_recording_data(loc, cfg)
    issues = list(data.issues)
    report: dict[str, object] = {
        "report_version": 1,
        "generated_by": f"ariagen_escooter {__version__}",
        "synthetic": manifest.synthetic,
        "notice": SYNTHETIC_NOTICE if manifest.synthetic else None,
        "participant_id": manifest.participant_id,
        "session_id": manifest.session_id,
        "recording_id": entry.recording_id,
        "trial": trial.model_dump(),
        "vehicle": cfg.vehicles.vehicle_types[trial.vehicle_type].model_dump(),
        "config": {"sources": list(cfg.sources), "sha256": cfg.sha256, "vehicle_type": cfg.vehicle_type},
        "inputs": {
            key: {"file": path.relative_to(loc.work_dir).as_posix(), "sha256": sha256_file(path)}
            for key, path in sorted(data.inputs.items())
        },
        "streams_available": sorted(data.streams),
    }
    write_yaml(cfg.merged, out_dir / "effective_config.yaml")
    write_json(run_info(), out_dir / "run_info.json", None)

    span = data.recording_span()
    if span is None:
        issues.append(Issue("error", "no_device_streams", "no frames/gaze/imu/pose stream found", entry.recording_id))
    timestamps: dict[str, object] = {}
    for name, df in list(data.streams.items()):
        rep = check_timestamps(
            df["t_ns"].to_numpy(),
            name,
            a.timestamps.gap_factor,
            a.timestamps.max_reported_gaps,
            span[0] if span else None,
        )
        timestamps[name] = rep.as_dict()
        issues.extend(Issue(i.level, i.code, i.message, f"{entry.recording_id}/{name}") for i in rep.issues)
        if rep.n_duplicates and not rep.n_non_monotonic:
            data.streams[name] = sort_and_deduplicate(df)
    report["timestamps"] = timestamps
    if any(i.level == "error" for i in issues):
        report["status"] = "failed"
        report["issues"] = [str(i) for i in issues]
        write_report(report, out_dir, decimals)
        return report
    assert span is not None
    rec_start, rec_end = span
    streams = dict(data.streams)

    # --- Data quality (on all samples, invalid ones included) ---------------------
    q = a.quality
    rates, rate_source = nominal_rates(cfg, manifest)
    thresholds = {k: GapThresholds(q.jitter_factor, v.short_gap_s, v.medium_gap_s) for k, v in q.streams.items()}
    quality_report, quality_intervals = recording_quality(
        streams,
        span,
        rates,
        thresholds,
        max_speed_mps=q.max_plausible_speed_mps,
        max_angular_rate_degps=q.max_plausible_angular_rate_degps,
        min_hf_quality_score=q.min_hf_quality_score,
        gps_max_accuracy_m=q.gps_max_accuracy_m,
        min_hand_confidence=q.min_hand_confidence,
    )
    quality_report["nominal_rates_source"] = rate_source
    write_json(quality_report, out_dir / "quality.json", decimals)
    report["quality_summary"] = {
        name: {
            "effective_rate_hz": entry_q["timing"].get("effective_rate_hz"),
            "nominal_rate_hz": entry_q["timing"].get("nominal_rate_hz"),
            "dropout_fraction": entry_q["timing"].get("dropout_fraction"),
            "interval_fractions": entry_q["interval_fractions"],
        }
        for name, entry_q in quality_report["streams"].items()
    }
    # Only valid pose samples are used from here on; resets break continuity.
    streams["pose"], pose_breaks = _valid_pose(streams.get("pose"))
    if streams["pose"] is None:
        streams.pop("pose")
    if "pose_hf" in streams:
        streams["pose_hf"], _ = _valid_pose(streams["pose_hf"])

    # --- GPS clock offset ------------------------------------------------------
    sync: dict[str, object] = {"gaze_frame_tolerance_s": a.synchronization.gaze_frame_tolerance_s}
    if "gps" in streams and "pose" in streams and a.synchronization.clock_offset.enabled:
        estimate, _ = _gps_offset(streams["pose"], streams["gps"], a, pose_breaks)
        applied = bool(estimate.reliable and a.synchronization.clock_offset.apply_if_reliable)
        if applied and estimate.offset_s is not None:
            gps = streams["gps"].copy()
            gps["t_ns"] = gps["t_ns"] + to_ns(estimate.offset_s)
            streams["gps"] = gps
        sync["gps_clock_offset"] = {
            **estimate.as_dict(),
            "applied": applied,
            "declared_external_gps_offset_ns": entry.clock.external_gps_offset_ns,
        }
        if not estimate.reliable:
            issues.append(Issue("warning", "gps_offset_unreliable", estimate.reason, entry.recording_id))
    report["synchronization"] = sync

    # --- Trimming ----------------------------------------------------------------
    signal = speed_for_trimming(
        streams.get("pose"),
        streams.get("gps"),
        a.trimming,
        polyorder=a.kinematics.savgol_polyorder,
        pose_max_gap_s=a.synchronization.pose_max_gap_s,
        gps_max_gap_s=a.synchronization.gps_max_gap_s,
        pose_breaks_ns=pose_breaks,
    )
    trim = trim_recording(
        a.trimming,
        recording_start_ns=rec_start,
        recording_end_ns=rec_end,
        signal=signal,
        imu=streams.get("imu"),
        override=entry.trimming_override,
    )
    trim_dict = trim.as_dict()
    write_json(trim_dict, out_dir / "trimming.json", decimals)
    report["trimming"] = trim_dict
    if trim.status != "ok":
        issues.append(Issue("warning", "trimming", trim.reason, entry.recording_id))
    t0, t1 = trim.trim_start_ns, trim.trim_end_ns
    trimmed = {name: slice_by_time(df, t0, t1) for name, df in streams.items()}
    if trimmed.get("pose") is not None:
        trimmed["pose"].attrs["tracking_breaks_ns"] = pose_breaks
    segments = _clip_segments(data.segments, t0, t1)
    events = None
    if data.events is not None:
        events = data.events[(data.events["t_end_ns"] > t0) & (data.events["t_start_ns"] < t1)].reset_index(drop=True)

    # --- Kinematics ---------------------------------------------------------------
    kin, kin_source = _kinematics(trimmed, a, t0, t1, pose_breaks)
    stops = detect_stops(kin, a.kinematics) if kin is not None else None
    braking = detect_braking_events(kin, a.kinematics) if kin is not None else None
    report["kinematics"] = {
        "source": kin_source,
        "grid_rate_hz": a.kinematics.grid_rate_hz,
        "n_stops": None if stops is None else len(stops),
        "n_decel_events": None if braking is None else len(braking),
        "note": "head-mounted sensor: speed/heading describe the rider's head trajectory (an ESTIMATE of the "
        "vehicle's motion, not a measurement of the vehicle)",
        "tracking_resets_in_ride": int(np.sum((pose_breaks >= t0) & (pose_breaks <= t1))),
    }
    if kin is None:
        issues.append(
            Issue("warning", "no_kinematics", "no pose or GPS stream: behaviour metrics skipped", entry.recording_id)
        )

    # --- Semantic gaze ------------------------------------------------------------------
    derived: GazeDerived | None = None
    gaze = trimmed.get("gaze")
    if gaze is not None and len(gaze):
        table = build_semantic_gaze(
            gaze,
            frames=trimmed.get("frames"),
            store=data.label_store,
            pose=trimmed.get("pose"),
            kinematics=kin,
            cfg=a.gaze,
            frame_tolerance_s=a.synchronization.gaze_frame_tolerance_s,
            pose_max_gap_s=a.synchronization.pose_max_gap_s,
        )
        derived = derive_gaze(table, a.gaze)
        report["gaze"] = {
            "n_samples": len(table),
            "gaze_status_counts": table["gaze_status"].value_counts().sort_index().to_dict(),
            "lookup_status_counts": table["lookup_status"].value_counts().sort_index().to_dict(),
            "fixation_reference_frame": derived.fixation_frame,
            "forward_reference": derived.forward_reference,
            "label_maps": None if data.label_store is None else data.label_store.backend,
        }
    else:
        issues.append(Issue("warning", "no_gaze", "no gaze stream: gaze metrics skipped", entry.recording_id))

    # --- Window metrics ---------------------------------------------------------------------
    ids = {
        "participant_id": manifest.participant_id,
        "session_id": manifest.session_id,
        "recording_id": entry.recording_id,
        "synthetic": manifest.synthetic,
        "vehicle_type": trial.vehicle_type,
        "vehicle_code": trial.vehicle_code,
        "trial_number": trial.trial_number,
        "ride_order": trial.ride_order,
        "trial_part": trial.part,
        "route_id": trial.route_id or manifest.route.route_id,
        "recording_profile": manifest.equipment.recording_profile,
        "weather": manifest.conditions.weather,
        "light": manifest.conditions.light,
        "road_surface": manifest.conditions.road_surface,
        "traffic_density": manifest.conditions.traffic_density,
    }
    class_rows: list[dict[str, object]] = []
    ride: dict[str, object] = {}
    if kin is not None and braking is not None and stops is not None:
        ride.update(window_metrics(kin, t0, t1, braking, stops))
    if derived is not None:
        metrics, class_time = window_gaze_metrics(derived, t0, t1, a.gaze, cfg.taxonomy)
        ride.update(metrics)
        class_rows += _class_time_rows("ride", entry.recording_id, class_time)
    ride.update(window_hand_metrics(trimmed.get("hands"), t0, t1, q.min_hand_confidence))
    ride.update(window_quality(quality_intervals, t0, t1, QUALITY_WINDOW_STREAMS, q.min_window_coverage))
    report["ride_summary"] = ride

    segment_table = None
    approach_table = None
    if segments is not None and len(segments):
        base = segments[["segment_id", "infrastructure_class", "t_start_ns", "t_end_ns", "clipped_by_trimming"]].copy()
        if kin is not None and braking is not None and stops is not None:
            beh = segment_behaviour(kin, segments, braking, stops).drop(columns=["infrastructure_class"])
            base = base.merge(beh, on="segment_id", how="left")
            approach_table = with_ids(approach_behaviour(kin, segments, braking, stops, a.kinematics), ids)
        if derived is not None:
            gaze_rows = []
            for _, seg in segments.iterrows():
                metrics, class_time = window_gaze_metrics(
                    derived, int(seg["t_start_ns"]), int(seg["t_end_ns"]), a.gaze, cfg.taxonomy
                )
                gaze_rows.append({"segment_id": seg["segment_id"], **metrics})
                class_rows += _class_time_rows("segment", seg["segment_id"], class_time)
            base = base.merge(pd.DataFrame(gaze_rows).drop(columns=["gaze_duration_s"]), on="segment_id", how="left")
        extra_rows = []
        for _, seg in segments.iterrows():
            s0, s1 = int(seg["t_start_ns"]), int(seg["t_end_ns"])
            extra_rows.append({
                "segment_id": seg["segment_id"],
                **window_hand_metrics(trimmed.get("hands"), s0, s1, q.min_hand_confidence),
                **window_quality(quality_intervals, s0, s1, QUALITY_WINDOW_STREAMS, q.min_window_coverage),
            })
        base = base.merge(pd.DataFrame(extra_rows), on="segment_id", how="left")
        if "route_segment_id" in segments.columns:
            base = base.merge(segments[["segment_id", "route_segment_id"]], on="segment_id", how="left")
        segment_table = with_ids(base, ids)

    event_table = context_table = None
    if events is not None and len(events):
        pa = perception_action(
            events,
            gaze_table=None if derived is None else derived.table,
            kin=kin,
            segments=segments,
            cfg=a.events,
            max_sample_weight_s=a.gaze.max_sample_weight_s,
        )
        if derived is not None:
            extra = []
            for _, ev in events.iterrows():
                metrics, class_time = window_gaze_metrics(
                    derived, int(ev["t_start_ns"]), int(ev["t_end_ns"]), a.gaze, cfg.taxonomy
                )
                target = str(ev.get("target_class", "") or "")
                row = {"event_id": ev["event_id"], **{f"ev_{k}": metrics[k] for k in EVENT_GAZE_COLUMNS}}
                row["ev_share_target_class"] = metrics.get(f"share_{target}", np.nan) if target else np.nan
                extra.append(row)
                class_rows += _class_time_rows("event", ev["event_id"], class_time)
            pa = pa.merge(pd.DataFrame(extra), on="event_id", how="left")
        q_rows = [
            {"event_id": ev["event_id"],
             **window_quality(quality_intervals, int(ev["t_start_ns"]), int(ev["t_end_ns"]),
                              QUALITY_WINDOW_STREAMS, q.min_window_coverage)}
            for _, ev in events.iterrows()
        ]
        pa = pa.merge(pd.DataFrame(q_rows), on="event_id", how="left")
        event_table = with_ids(pa, ids)
        if segments is not None:
            context_table = with_ids(event_context(events, segments), ids)

    sample_tables = a.reporting.sample_level_tables
    tables = {
        "segment_metrics": segment_table,
        "approach_metrics": approach_table,
        "event_metrics": event_table,
        "event_context": context_table,
        "decel_events": braking,
        "stops": stops,
        "gaze_class_time": pd.DataFrame(class_rows) if class_rows else None,
        "quality_intervals": with_ids(quality_intervals, ids) if len(quality_intervals) else None,
        "fixations": None if derived is None else derived.fixations,
        "dwells": None if derived is None else derived.dwells,
        "lateral_glances": None if derived is None else derived.glances,
        "kinematics": kin if sample_tables else None,
        "semantic_gaze": (None if derived is None else derived.table) if sample_tables else None,
    }
    written = write_tables(tables, out_dir, decimals)

    figures: dict[str, str] = {}
    plots = a.reporting.plots if make_plots is None else make_plots
    if plots:
        from ariagen_escooter.visualization import plot_overview, plot_trajectory

        title = f"{entry.recording_id}"
        path = plot_overview(
            out_dir / "figures" / "overview.png",
            title=title,
            t0_ns=rec_start,
            speed_raw=(signal.grid_ns, signal.speed_mps) if signal is not None else None,
            trimming=trim_dict,
            kin=kin,
            segments=segments,
            events=events,
            gaze_table=None if derived is None else derived.table,
            class_names=cfg.taxonomy.semantic_names,
            yaw_column=None
            if derived is None
            else ("gaze_yaw_rel_travel_deg" if derived.forward_reference == "travel" else "eye_yaw_deg"),
            synthetic=manifest.synthetic,
        )
        figures["overview"] = path.relative_to(out_dir).as_posix()
        if kin is not None:
            path = plot_trajectory(
                out_dir / "figures" / "trajectory.png",
                title=title,
                kin=kin,
                segments=segments,
                events=events,
                synthetic=manifest.synthetic,
            )
            figures["trajectory"] = path.relative_to(out_dir).as_posix()

    report["counts"] = {
        "segments": 0 if segments is None else len(segments),
        "events": 0 if events is None else len(events),
    }
    report["outputs"] = {
        "tables": written,
        "trimming": "trimming.json",
        "quality": "quality.json",
        "effective_config": "effective_config.yaml",
        "run_info": "run_info.json (non-deterministic metadata)",
        "figures": figures,
    }
    report["issues"] = [str(i) for i in issues]
    report["status"] = "warning" if any(i.level == "warning" for i in issues) else "ok"
    write_report(report, out_dir, decimals)
    return report


def process_session(
    session_dir: Path, cfg: LoadedConfig, out_root: Path | None = None, make_plots: bool | None = None
) -> list[dict[str, object]]:
    """Validate and process every recording of a session."""
    manifest, issues = validate_session(session_dir, cfg)
    errors = [i for i in issues if i.level == "error"]
    if manifest is None or errors:
        raise ConfigError("session validation failed:\n" + "\n".join(str(i) for i in errors or issues))
    root = out_root if out_root is not None else cfg.data_root / "processed"
    return [process_recording(session_dir, manifest, entry, cfg, root, make_plots) for entry in manifest.recordings]


# --------------------------------------------------------------------------- #
# Study-level aggregation
# --------------------------------------------------------------------------- #
def aggregate(
    processed_root: Path, out_dir: Path, *, synthetic: bool = False, participants: Path | None = None
) -> dict[str, object]:
    """Concatenate per-recording tables into study-level long tables.

    Real and synthetic data are never mixed: ``synthetic=False`` aggregates
    only real sessions, ``synthetic=True`` only synthetic ones.
    Produces ``study_segment_metrics.csv`` (one row per route segment, with
    participant/session/condition columns, ready for mixed-effects models
    behaviour ~ infrastructure + (1 | rider) ...), ``study_event_metrics.csv``
    and a descriptive ``rider_by_infrastructure.csv``.
    """
    out: dict[str, object] = {"synthetic": synthetic, "tables": {}}
    for name in ("segment_metrics", "event_metrics", "approach_metrics"):
        frames = []
        for path in sorted(processed_root.glob(f"*/*/tables/{name}.csv")):
            df = pd.read_csv(path)
            if "synthetic" in df.columns:
                df = df[df["synthetic"].astype(bool) == synthetic]
            if len(df):
                frames.append(df)
        if not frames:
            continue
        study = pd.concat(frames, ignore_index=True)
        if participants is not None and participants.is_file():
            covariates = pd.read_csv(participants)
            study = study.merge(covariates, on="participant_id", how="left", validate="many_to_one")
        out_path = out_dir / f"study_{name}.csv"
        out_dir.mkdir(parents=True, exist_ok=True)
        study.to_csv(out_path, index=False, float_format="%.6f", lineterminator="\n")
        out["tables"][name] = {
            "file": out_path.name,
            "rows": len(study),
            "recordings": int(study["recording_id"].nunique()),
        }
        if name == "segment_metrics":
            metrics = [
                c
                for c in (
                    "speed_mean_mps",
                    "speed_sd_mps",
                    "decel_max_mps2",
                    "jerk_rms_mps3",
                    "forward_share",
                    "share_group_pedestrians",
                    "share_group_vehicles",
                    "gaze_valid_fraction",
                )
                if c in study.columns
            ]
            summary = (
                study.groupby(["participant_id", "infrastructure_class"])
                .agg(
                    n_segments=("segment_id", "count"),
                    total_duration_s=("duration_s", "sum"),
                    **{m: (m, "mean") for m in metrics},
                )
                .reset_index()
            )
            summary_path = out_dir / "rider_by_infrastructure.csv"
            summary.to_csv(summary_path, index=False, float_format="%.6f", lineterminator="\n")
            out["tables"]["rider_by_infrastructure"] = {"file": summary_path.name, "rows": len(summary)}
            if "vehicle_type" in study.columns:
                for table_name, frame in vehicle_tables(study, metrics).items():
                    path = out_dir / f"{table_name}.csv"
                    frame.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")
                    out["tables"][table_name] = {"file": path.name, "rows": len(frame)}
    return out


def vehicle_tables(study: pd.DataFrame, metrics: list[str]) -> dict[str, pd.DataFrame]:
    """Descriptive vehicle tables (no inference; see docs/methodology/statistical_analysis_plan.md).

    * ``rider_vehicle_by_infrastructure``: participant x vehicle x infrastructure
      class, means over segments, number of segments and of trials;
    * ``within_participant_vehicle_contrasts``: for each participant and place
      (route_segment_id when segments are aligned to the planned route, else
      infrastructure class), the mean of each metric per vehicle over trials and
      the difference escooter - bicycle. Rows exist only where BOTH vehicles were
      observed at that place; low-coverage windows are excluded first.
    """
    data = study.copy()
    if "quality_flag" in data.columns:
        data = data[data["quality_flag"].fillna("ok") == "ok"]
    out: dict[str, pd.DataFrame] = {}
    keys = ["participant_id", "vehicle_type", "infrastructure_class"]
    out["rider_vehicle_by_infrastructure"] = (
        data.groupby(keys)
        .agg(n_segments=("segment_id", "count"), n_trials=("trial_number", "nunique"),
             total_duration_s=("duration_s", "sum"), **{m: (m, "mean") for m in metrics})
        .reset_index()
    )
    place = "route_segment_id" if "route_segment_id" in data.columns and data["route_segment_id"].notna().any() \
        else "infrastructure_class"
    per_trial = data.groupby(["participant_id", place, "vehicle_type", "trial_number"])[metrics].mean().reset_index()
    per_vehicle = per_trial.groupby(["participant_id", place, "vehicle_type"]).agg(
        n_trials=("trial_number", "nunique"), **{m: (m, "mean") for m in metrics}).reset_index()
    wide = per_vehicle.pivot(index=["participant_id", place], columns="vehicle_type")
    wide.columns = [f"{m}__{v}" for m, v in wide.columns]
    wide = wide.reset_index()
    if {"escooter", "bicycle"} <= set(per_vehicle["vehicle_type"]):
        both = wide[[f"n_trials__{v}" for v in ("escooter", "bicycle")]].notna().all(axis=1)
        wide = wide[both].copy()
        for m in metrics:
            wide[f"{m}__diff_escooter_minus_bicycle"] = wide[f"{m}__escooter"] - wide[f"{m}__bicycle"]
        wide.insert(2, "place_key", place)
        out["within_participant_vehicle_contrasts"] = wide.reset_index(drop=True)
    return out
