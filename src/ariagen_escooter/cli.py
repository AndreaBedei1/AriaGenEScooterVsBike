"""Command-line interface.

Usage: ``python -m ariagen_escooter <command> [options]`` (or ``ariagen-escooter``).

Commands
--------
info            environment, paths, configuration and optional components
schema          canonical data schema as Markdown
new-session     create a raw session folder with a manifest template
validate        validate a session (manifest, privacy rules, streams, annotations)
run             process a session (MVP pipeline) -> data/processed/...
make-synthetic  (re)generate the SYNTHETIC / TEST dataset
aggregate       study-level tables from processed sessions
extract-aria    Aria Gen 2 VRS -> canonical streams + raw-stream quality (Linux/macOS, 'aria' extra)
map-segments    GNSS of a ride -> segments of the planned route (annotations/segments_route.csv)
plan-rides      counterbalanced ride plan from a protocol file (configs/protocol/)
segment-frames  EXPERIMENTAL: semantic label maps from VRS frames ('aria' + 'cv' extras)
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from ariagen_escooter import __version__
from ariagen_escooter.config import ConfigError, LoadedConfig, find_project_root, load_config, portable_path
from ariagen_escooter.reporting import CORE_PACKAGES, OPTIONAL_PACKAGES, package_version


def _load(args: argparse.Namespace) -> LoadedConfig:
    overrides = [Path(p) for p in (getattr(args, "config", None) or [])]
    return load_config(overrides)


def cmd_info(args: argparse.Namespace) -> int:
    print(f"AriaGenEScooter {__version__}")
    print(f"Python {platform.python_version()} on {platform.system()} {platform.release()} ({platform.machine()})")
    try:
        cfg = _load(args)
    except ConfigError as exc:
        print(f"Configuration ERROR: {exc}")
        return 1
    print(f"Project root : {cfg.project_root}")
    print(f"Data root    : {cfg.data_root}")
    print(f"Config       : {' + '.join(cfg.sources)} (sha256 {cfg.sha256[:12]}...) OK")
    print(
        f"Taxonomy     : {len(cfg.taxonomy.infrastructure_classes)} infrastructure classes, "
        f"{len(cfg.taxonomy.event_types)} event types, {len(cfg.taxonomy.semantic_classes)} semantic classes"
    )
    print("Core packages:")
    missing_core = False
    for name in CORE_PACKAGES:
        version = package_version(name)
        missing_core |= version is None
        print(f"  {name:24s} {version or 'MISSING'}")
    print("Optional packages:")
    for name in OPTIONAL_PACKAGES:
        version = package_version(name)
        note = ""
        if name == "projectaria-tools" and version is None:
            note = "(Linux/macOS only - needed for extract-aria)"
        print(f"  {name:24s} {version or 'not installed'} {note}".rstrip())
    return 1 if missing_core else 0


def cmd_schema(args: argparse.Namespace) -> int:
    from ariagen_escooter.streams import schema_markdown

    print(schema_markdown())
    return 0


def cmd_new_session(args: argparse.Namespace) -> int:
    from ariagen_escooter.io import write_yaml
    from ariagen_escooter.session import (
        PARTICIPANT_RE,
        manifest_template,
        next_participant_id,
        validate_participant_id,
    )

    cfg = _load(args)
    root = Path(args.root) if args.root else cfg.data_root / "raw"
    if args.participant and args.next:
        print("use either --participant or --next")
        return 2
    if args.next:
        existing = [p.name.split("_")[0] for p in root.glob("P*_S*") if p.is_dir()]
        participant = next_participant_id([e for e in existing if PARTICIPANT_RE.match(e)])
    elif args.participant:
        participant = validate_participant_id(args.participant)
    else:
        print("specify --participant P001 or --next")
        return 2
    rides = None
    if args.ride:
        rides = []
        for spec in args.ride:
            try:
                vehicle, trial, order = spec.split(":")
                rides.append((vehicle, int(trial), int(order)))
            except ValueError:
                print(f"invalid --ride {spec!r}: expected VEHICLE:TRIAL:ORDER, e.g. escooter:1:2")
                return 2
            if vehicle not in cfg.vehicles.vehicle_types:
                print(f"unknown vehicle {vehicle!r}; known: {sorted(cfg.vehicles.vehicle_types)}")
                return 2
    manifest = manifest_template(participant, args.session, args.recordings, rides=rides)
    session_dir = root / manifest["session_id"]
    path = session_dir / "manifest.yaml"
    if path.exists():
        print(f"refusing to overwrite existing {path}")
        return 1
    write_yaml(manifest, path)
    for rec in manifest["recordings"]:
        (session_dir / rec["recording_id"]).mkdir(parents=True, exist_ok=True)
    print(f"created {path}")
    print(
        "next: copy the VRS into each recording folder as recording.vrs, complete the manifest "
        "(vehicle units, trial blocks; no names/e-mails/phone numbers!), then run `validate`."
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from ariagen_escooter.pipeline import validate_session

    cfg = _load(args)
    manifest, issues = validate_session(Path(args.session_dir), cfg)
    for issue in issues:
        print(issue)
    n_err = sum(i.level == "error" for i in issues)
    n_warn = sum(i.level == "warning" for i in issues)
    label = manifest.session_id if manifest else Path(args.session_dir).name
    print(f"{label}: {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


def cmd_run(args: argparse.Namespace) -> int:
    from ariagen_escooter.pipeline import process_session

    cfg = _load(args)
    out_root = Path(args.out) if args.out else None
    try:
        reports = process_session(Path(args.session_dir), cfg, out_root, make_plots=False if args.no_plots else None)
    except ConfigError as exc:
        print(exc)
        return 1
    root = out_root if out_root is not None else cfg.data_root / "processed"
    status = 0
    for rep in reports:
        trim = rep.get("trimming", {})
        interval = trim.get("trimmed_interval", {}) if isinstance(trim, dict) else {}
        print(f"{rep['recording_id']}: status={rep['status']}")
        if rep.get("notice"):
            print(f"  NOTE: {rep['notice']}")
        if interval:
            print(
                f"  trimming: {trim['method']} -> {interval['start_rel_s']:.2f}-{interval['end_rel_s']:.2f} s "
                f"(removed {trim['removed_before_s']:.1f} s before, {trim['removed_after_s']:.1f} s after)"
            )
        print(f"  outputs : {root / rep['session_id'] / rep['recording_id']}")
        for issue in rep.get("issues", []):
            print(f"  {issue}")
        status |= rep["status"] == "failed"
    return int(status)


def cmd_make_synthetic(args: argparse.Namespace) -> int:
    from ariagen_escooter.synthetic import generate_session, write_participants_table

    cfg = _load(args)
    out = Path(args.out) if args.out else cfg.project_root / "data" / "synthetic"
    session_dir = generate_session(
        out,
        participant_number=args.participant_number,
        session_number=args.session_number,
        seed=args.seed,
        speed_scale=args.speed_scale,
        taxonomy_names=cfg.taxonomy.semantic_names,
    )
    ids = sorted({p.name.split("_")[0] for p in out.glob("SYN*_S*") if p.is_dir()})
    write_participants_table(out, ids)
    print(f"SYNTHETIC / TEST DATA written to {session_dir}")
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    from ariagen_escooter.pipeline import aggregate

    cfg = _load(args)
    processed = Path(args.processed) if args.processed else cfg.data_root / "processed"
    out = Path(args.out) if args.out else processed / ("_study_synthetic" if args.synthetic else "_study")
    result = aggregate(
        processed, out, synthetic=args.synthetic, participants=Path(args.participants) if args.participants else None
    )
    if not result["tables"]:
        print("no processed tables found (did you run `run` first? use --synthetic for synthetic sessions)")
        return 1
    for name, info in result["tables"].items():
        print(f"{name}: {info}")
    print(f"written to {out}")
    return 0


def cmd_extract_aria(args: argparse.Namespace) -> int:  # pragma: no cover - needs projectaria-tools + VRS
    from ariagen_escooter.aria import INSTALL_HINT, projectaria_available
    from ariagen_escooter.session import load_manifest

    if not projectaria_available():
        print(INSTALL_HINT)
        return 1
    cfg = _load(args)
    session_dir = Path(args.session_dir)
    manifest = load_manifest(session_dir / "manifest.yaml")
    for entry in manifest.recordings:
        if args.recording and entry.recording_id != args.recording:
            continue
        if not entry.files.vrs:
            print(f"{entry.recording_id}: no VRS declared in the manifest, skipped")
            continue
        raw_dir = session_dir / entry.recording_id
        vrs = portable_path(raw_dir, entry.files.vrs)
        out = cfg.data_root / "interim" / manifest.session_id / entry.recording_id / "streams"
        mps_dir = portable_path(raw_dir, entry.files.mps_dir) if entry.files.mps_dir else None
        summary = extract_recording(vrs, out, cfg, mps_dir)
        print(f"{entry.recording_id}: {summary['streams']} -> {out}")
    print("Check inventory.csv and extraction_quality.json, then update the stream statuses in the manifest.")
    return 0


def extract_recording(vrs: Path, out: Path, cfg: LoadedConfig, mps_dir: Path | None = None) -> dict[str, object]:
    """VRS -> canonical streams + inventory + raw-stream quality (no data written next to the VRS)."""
    from ariagen_escooter.aria import AriaGen2Extractor
    from ariagen_escooter.io import write_csv, write_json
    from ariagen_escooter.quality import GapThresholds

    decimals = cfg.analysis.reporting.float_decimals
    a = cfg.analysis.aria
    q = cfg.analysis.quality
    extractor = AriaGen2Extractor(vrs, a)
    write_csv(extractor.inventory(), out.parent / "inventory.csv", decimals)
    nominal = extractor.nominal_rates()
    thresholds = {k: GapThresholds(q.jitter_factor, v.short_gap_s, v.medium_gap_s) for k, v in q.streams.items()}
    summary: dict[str, object] = {"metadata": extractor.metadata(), "nominal_rates_from_profile": nominal,
                                  "streams": {}}
    gps, gps_label = extractor.gps()
    streams = {
        "frames": extractor.frames(),
        "gaze": extractor.eye_gaze(),
        "imu": extractor.imu(),
        "pose": extractor.pose(mps_dir),
        "pose_hf": extractor.pose_high_frequency(a.pose_hf_rate_hz),
        "hands": extractor.hands() if a.export_hands else None,
        "gps": gps,
    }
    for name, df in streams.items():
        if df is None or df.empty:
            summary["streams"][name] = "missing"
            continue
        write_csv(df, out / f"{name}.csv", decimals if name != "gps" else 8)
        summary["streams"][name] = {"rows": len(df)}
    summary["gps_label"] = gps_label
    summary["extrinsics"] = extractor.sensor_extrinsics()
    summary["aria_config"] = a.model_dump()
    write_json(summary, out.parent / "extraction.json", decimals)
    write_json({"note": "timing quality of the RAW VRS streams, before any resampling",
                "streams": extractor.raw_quality(nominal, thresholds)},
               out.parent / "extraction_quality.json", decimals)
    return summary


def cmd_map_segments(args: argparse.Namespace) -> int:
    from ariagen_escooter.io import read_table, write_csv
    from ariagen_escooter.pipeline import load_recording_data
    from ariagen_escooter.route import load_route, route_segments_for_ride
    from ariagen_escooter.session import load_manifest, locate_recording

    cfg = _load(args)
    session_dir = Path(args.session_dir)
    manifest = load_manifest(session_dir / "manifest.yaml")
    geojson = Path(args.route_geojson) if args.route_geojson else cfg.project_root / "docs" / "route" / "cesena_route.geojson"
    for entry in manifest.recordings:
        trial = manifest.trial_of(entry.recording_id)
        route_id = args.route_id or trial.route_id or manifest.route.route_id
        loc = locate_recording(session_dir, manifest.session_id, entry.recording_id, cfg.data_root)
        data = load_recording_data(loc, cfg)
        gps = data.streams.get("gps")
        if gps is None:
            gps_path = loc.streams_dir / "gps.csv"
            gps = read_table(gps_path) if gps_path.is_file() else None
        if gps is None or gps.empty:
            print(f"{entry.recording_id}: no GNSS stream, skipped")
            continue
        route = load_route(geojson, route_id)
        seg = route_segments_for_ride(route, gps.dropna(subset=["lat_deg", "lon_deg"]), entry.recording_id,
                                      max_offset_m=args.max_offset_m)
        out = loc.annotations_dir / "segments_route.csv"
        write_csv(seg, out, cfg.analysis.reporting.float_decimals)
        print(f"{entry.recording_id}: {len(seg)} of {len(route.segments)} route segments -> {out}")
    print("Review the boundaries (anonymised video) before copying them into annotations/segments.csv.")
    return 0


def cmd_plan_rides(args: argparse.Namespace) -> int:
    import json

    from ariagen_escooter.protocol import load_protocol, plan_rides

    cfg = load_protocol(Path(args.protocol))
    plan = plan_rides(cfg)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        plan.rides.to_csv(out, index=False, lineterminator="\n")
        print(f"ride plan -> {out}")
    else:
        print(plan.rides.to_string(index=False))
    print(json.dumps(plan.balance, indent=2))
    return 0


def cmd_segment_frames(args: argparse.Namespace) -> int:  # pragma: no cover - needs aria + cv extras
    from ariagen_escooter.aria import AriaGen2Extractor, projectaria_available
    from ariagen_escooter.segmentation import HuggingFaceSegmenter, LabelMapping, segment_frames
    from ariagen_escooter.session import load_manifest

    if not projectaria_available():
        print("segment-frames needs the 'aria' extra (Linux/macOS)")
        return 1
    cfg = _load(args)
    hf = cfg.analysis.segmentation.huggingface
    model_id = args.model_id or hf.model_id
    mapping_file = args.mapping or hf.label_mapping_file
    if not model_id or not mapping_file:
        print("set segmentation.huggingface.model_id and label_mapping_file (or --model-id/--mapping)")
        return 2
    mapping = LabelMapping.from_yaml(portable_path(cfg.project_root, mapping_file), cfg.taxonomy.semantic_names)
    segmenter = HuggingFaceSegmenter(model_id, device=hf.device)
    session_dir = Path(args.session_dir)
    manifest = load_manifest(session_dir / "manifest.yaml")
    for entry in manifest.recordings:
        if args.recording and entry.recording_id != args.recording:
            continue
        vrs = portable_path(session_dir / entry.recording_id, entry.files.vrs or "recording.vrs")
        extractor = AriaGen2Extractor(vrs, cfg.analysis.aria)
        store = segment_frames(
            extractor.iter_rgb_frames(args.every_n),
            segmenter,
            mapping,
            map_size=(args.map_width, int(round(args.map_width * 3 / 4))),
        )
        target = portable_path(
            cfg.data_root / "interim" / manifest.session_id / entry.recording_id,
            cfg.analysis.segmentation.label_maps_file,
        )
        store.save(target)
        print(f"{entry.recording_id}: {len(store)} label maps -> {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ariagen-escooter", description="AriaGenEScooter analysis toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_config(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument(
            "--config",
            action="append",
            metavar="YAML",
            help="override file(s) merged on top of configs/default.yaml (repeatable)",
        )
        return p

    with_config(sub.add_parser("info", help="environment, paths and optional components")).set_defaults(func=cmd_info)
    sub.add_parser("schema", help="canonical data schema (Markdown)").set_defaults(func=cmd_schema)

    p = with_config(sub.add_parser("new-session", help="create a raw session folder with a manifest template"))
    p.add_argument("--participant", help="pseudonymous id, e.g. P001")
    p.add_argument("--next", action="store_true", help="use the next free participant id")
    p.add_argument("--session", type=int, default=1, help="session number (default 1)")
    p.add_argument("--recordings", type=int, default=1, help="number of recordings (default 1; ignored with --ride)")
    p.add_argument(
        "--ride",
        action="append",
        metavar="VEHICLE:TRIAL:ORDER",
        help="one recording per ride, e.g. --ride escooter:1:1 --ride bicycle:1:2 (vehicle type, repetition "
        "number for that vehicle, position in the participant's protocol); repeatable",
    )
    p.add_argument("--root", help="raw data folder (default <data_root>/raw)")
    p.set_defaults(func=cmd_new_session)

    p = with_config(sub.add_parser("validate", help="validate a session folder"))
    p.add_argument("session_dir")
    p.set_defaults(func=cmd_validate)

    p = with_config(sub.add_parser("run", help="process a session (MVP pipeline)"))
    p.add_argument("session_dir")
    p.add_argument("--out", help="output root (default <data_root>/processed)")
    p.add_argument("--no-plots", action="store_true", help="skip diagnostic figures")
    p.set_defaults(func=cmd_run)

    p = with_config(sub.add_parser("make-synthetic", help="generate the SYNTHETIC / TEST dataset"))
    p.add_argument("--out", help="output folder (default data/synthetic)")
    p.add_argument("--seed", type=int, default=20261006)
    p.add_argument("--participant-number", type=int, default=1)
    p.add_argument("--session-number", type=int, default=1)
    p.add_argument("--speed-scale", type=float, default=1.0)
    p.set_defaults(func=cmd_make_synthetic)

    p = with_config(sub.add_parser("aggregate", help="study-level tables from processed sessions"))
    p.add_argument("--processed", help="processed root (default <data_root>/processed)")
    p.add_argument("--out", help="output folder")
    p.add_argument("--synthetic", action="store_true", help="aggregate synthetic sessions only (never mixed with real)")
    p.add_argument("--participants", help="CSV with pseudonymous participant covariates")
    p.set_defaults(func=cmd_aggregate)

    p = with_config(sub.add_parser("extract-aria", help="Aria Gen 2 VRS -> canonical streams (Linux/macOS)"))
    p.add_argument("session_dir")
    p.add_argument("--recording", help="only this recording id")
    p.set_defaults(func=cmd_extract_aria)

    p = with_config(sub.add_parser("map-segments", help="GNSS -> segments of the planned route (for review)"))
    p.add_argument("session_dir")
    p.add_argument("--route-geojson", help="default docs/route/cesena_route.geojson")
    p.add_argument("--route-id", help="default: trial.route_id or the session route_id")
    p.add_argument("--max-offset-m", type=float, default=25.0, help="fixes farther from the route stay unmatched")
    p.set_defaults(func=cmd_map_segments)

    p = sub.add_parser("plan-rides", help="counterbalanced ride plan from a protocol file")
    p.add_argument("protocol", help="e.g. configs/protocol/pilot.yaml")
    p.add_argument("--out", help="CSV output (default: print)")
    p.set_defaults(func=cmd_plan_rides)

    p = with_config(sub.add_parser("segment-frames", help="EXPERIMENTAL label maps from VRS frames"))
    p.add_argument("session_dir")
    p.add_argument("--recording")
    p.add_argument("--model-id")
    p.add_argument("--mapping", help="label mapping YAML (relative to the project root)")
    p.add_argument("--every-n", type=int, default=1)
    p.add_argument("--map-width", type=int, default=160)
    p.set_defaults(func=cmd_segment_frames)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main", "build_parser", "find_project_root"]
