"""Configuration: project/data paths, analysis parameters and taxonomy.

All analysis parameters live in YAML files (``configs/default.yaml`` plus
optional override files). The models below define *types and constraints
only*: they deliberately carry no default values, so that every number used
by an analysis is visible in a config file and saved with the results.

Paths
-----
* The project root is found by walking up from the working directory (or
  this file) to the first folder containing ``pyproject.toml`` and
  ``configs/default.yaml``; ``ARIAGEN_PROJECT_ROOT`` overrides the search.
* The data root is ``paths.data_root`` (relative to the project root) unless
  ``ARIAGEN_DATA_ROOT`` is set.
* Paths written in manifests/configs are relative and ``/``-separated, so the
  same files work on Windows and Linux (see :func:`portable_path`).
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ENV_PROJECT_ROOT = "ARIAGEN_PROJECT_ROOT"
ENV_DATA_ROOT = "ARIAGEN_DATA_ROOT"
DEFAULT_CONFIG_PARTS = ("configs", "default.yaml")

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class ConfigError(ValueError):
    """Invalid, missing or non-portable configuration."""


PositiveFloat = Annotated[float, Field(gt=0)]
NonNegFloat = Annotated[float, Field(ge=0)]
Probability = Annotated[float, Field(ge=0, le=1)]


class _Strict(BaseModel):
    """Base model: unknown keys are errors (typos must not be silently ignored)."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- #
# Analysis configuration (mirrors configs/default.yaml)
# --------------------------------------------------------------------------- #
class PathsConfig(_Strict):
    data_root: str
    taxonomy_file: str
    vehicles_file: str


class TimestampsConfig(_Strict):
    gap_factor: float = Field(gt=1.0)
    max_reported_gaps: int = Field(ge=0)


class ClockOffsetConfig(_Strict):
    enabled: bool
    max_lag_s: PositiveFloat
    grid_rate_hz: PositiveFloat
    min_overlap_s: PositiveFloat
    min_correlation: float = Field(ge=-1.0, le=1.0)
    apply_if_reliable: bool


class SynchronizationConfig(_Strict):
    gaze_frame_tolerance_s: PositiveFloat
    pose_max_gap_s: PositiveFloat
    gps_max_gap_s: PositiveFloat
    clock_offset: ClockOffsetConfig


class StreamQualityConfig(_Strict):
    nominal_rate_hz: PositiveFloat | None
    short_gap_s: PositiveFloat
    medium_gap_s: PositiveFloat

    @model_validator(mode="after")
    def _ordered(self) -> StreamQualityConfig:
        if self.medium_gap_s < self.short_gap_s:
            raise ValueError("medium_gap_s must be >= short_gap_s")
        return self


class QualityConfig(_Strict):
    profiles_dir: str
    jitter_factor: float = Field(gt=1.0)
    streams: dict[str, StreamQualityConfig]
    max_plausible_speed_mps: PositiveFloat
    max_plausible_angular_rate_degps: PositiveFloat
    min_hf_quality_score: Probability
    gps_max_accuracy_m: PositiveFloat
    min_hand_confidence: Probability
    min_window_coverage: Probability


class ImuCheckConfig(_Strict):
    enabled: bool
    window_s: PositiveFloat
    min_accel_std_mps2: NonNegFloat
    min_active_fraction: Probability


class TrimmingConfig(_Strict):
    enabled: bool
    speed_source: Literal["auto", "pose", "gps"]
    grid_rate_hz: PositiveFloat
    smoothing_window_s: PositiveFloat
    speed_threshold_mps: PositiveFloat
    min_moving_duration_s: NonNegFloat
    selection: Literal["first_to_last", "longest"]
    merge_gap_s: NonNegFloat
    buffer_before_s: NonNegFloat
    buffer_after_s: NonNegFloat
    imu_check: ImuCheckConfig


class BrakingConfig(_Strict):
    decel_threshold_mps2: PositiveFloat
    onset_threshold_mps2: PositiveFloat
    min_duration_s: NonNegFloat

    @model_validator(mode="after")
    def _onset_not_above_threshold(self) -> BrakingConfig:
        if self.onset_threshold_mps2 > self.decel_threshold_mps2:
            raise ValueError("onset_threshold_mps2 must be <= decel_threshold_mps2")
        return self


class KinematicsConfig(_Strict):
    source: Literal["auto", "pose", "gps"]
    grid_rate_hz: PositiveFloat
    smoothing_window_s: PositiveFloat
    # >= 2 because jerk is the second derivative of the smoothed speed.
    savgol_polyorder: int = Field(ge=2, le=5)
    min_speed_for_heading_mps: NonNegFloat
    stop_speed_threshold_mps: NonNegFloat
    min_stop_duration_s: NonNegFloat
    braking: BrakingConfig
    lateral_reference_window_s: PositiveFloat
    approach_window_s: PositiveFloat
    approach_classes: list[str]


class FixationConfig(_Strict):
    reference_frame: Literal["auto", "world", "eye_in_head"]
    velocity_threshold_deg_s: PositiveFloat
    min_duration_s: NonNegFloat


class ForwardConfig(_Strict):
    reference: Literal["auto", "travel", "head"]
    yaw_half_width_deg: float = Field(gt=0, le=180)
    pitch_min_deg: float = Field(ge=-90, le=90)
    pitch_max_deg: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def _ordered(self) -> ForwardConfig:
        if self.pitch_min_deg >= self.pitch_max_deg:
            raise ValueError("pitch_min_deg must be < pitch_max_deg")
        return self


class LateralGlanceConfig(_Strict):
    yaw_threshold_deg: float = Field(gt=0, lt=180)
    min_duration_s: NonNegFloat


class DispersionConfig(_Strict):
    bcea_probability: float = Field(gt=0, lt=1)
    entropy_bin_deg: PositiveFloat


class VerticalBand(_Strict):
    name: str
    min_deg: float = Field(ge=-90, le=90)
    max_deg: float = Field(ge=-90, le=90)


class GazeConfig(_Strict):
    min_confidence: Probability | None
    max_sample_weight_s: PositiveFloat
    lookup_radius_px: NonNegFloat
    dwell_bridge_gap_s: NonNegFloat
    fixation: FixationConfig
    forward: ForwardConfig
    lateral_glance: LateralGlanceConfig
    dispersion: DispersionConfig
    vertical_bands: list[VerticalBand]

    @model_validator(mode="after")
    def _bands(self) -> GazeConfig:
        names = [b.name for b in self.vertical_bands]
        if len(set(names)) != len(names):
            raise ValueError("vertical_bands names must be unique")
        bands = sorted(self.vertical_bands, key=lambda b: b.min_deg)
        for band in bands:
            if band.min_deg >= band.max_deg:
                raise ValueError(f"vertical band {band.name!r}: min_deg must be < max_deg")
        for prev, nxt in zip(bands, bands[1:], strict=False):
            if nxt.min_deg < prev.max_deg:
                raise ValueError("vertical_bands must not overlap")
        return self


class EventsConfig(_Strict):
    first_gaze_lookback_s: NonNegFloat
    first_gaze_min_dwell_s: NonNegFloat
    action_decel_threshold_mps2: PositiveFloat
    action_min_duration_s: NonNegFloat
    action_search_after_s: NonNegFloat


class AriaConfig(_Strict):
    rgb_label: str
    eye_gaze_label: str
    imu_label: str
    gps_labels: list[str]
    pose_source: Literal["vio", "vio_high_frequency", "mps_closed_loop"]
    pose_rate_hz: PositiveFloat
    pose_hf_rate_hz: PositiveFloat
    export_hands: bool
    imu_rate_hz: PositiveFloat
    gaze_projection: Literal["spatial_point_if_valid", "fixed_depth"]
    gaze_fallback_depth_m: PositiveFloat


class HuggingFaceConfig(_Strict):
    model_id: str | None
    label_mapping_file: str | None
    device: str


class SegmentationConfig(_Strict):
    backend: Literal["precomputed", "huggingface"]
    label_maps_file: str
    huggingface: HuggingFaceConfig


class GpsPrivacyConfig(_Strict):
    endpoint_radius_m: NonNegFloat
    generalization_grid_m: PositiveFloat


class BlurConfig(_Strict):
    method: Literal["gaussian", "pixelate"]
    margin_fraction: NonNegFloat
    gaussian_sigma_fraction: PositiveFloat
    pixelate_blocks: int = Field(ge=1)


class PrivacyConfig(_Strict):
    forbidden_manifest_keys: list[str]
    gps: GpsPrivacyConfig
    blur: BlurConfig


class ReportingConfig(_Strict):
    float_decimals: int = Field(ge=1, le=12)
    plots: bool
    sample_level_tables: bool


class AnalysisConfig(_Strict):
    config_version: Literal[1]
    paths: PathsConfig
    timestamps: TimestampsConfig
    synchronization: SynchronizationConfig
    quality: QualityConfig
    trimming: TrimmingConfig
    kinematics: KinematicsConfig
    gaze: GazeConfig
    events: EventsConfig
    aria: AriaConfig
    segmentation: SegmentationConfig
    privacy: PrivacyConfig
    reporting: ReportingConfig


# --------------------------------------------------------------------------- #
# Taxonomy (configs/taxonomy.yaml)
# --------------------------------------------------------------------------- #
class SemanticClassDef(_Strict):
    id: int = Field(ge=0)
    name: str
    parent: str
    description: str


class Taxonomy(_Strict):
    taxonomy_version: int = Field(ge=1)
    infrastructure_classes: dict[str, str]
    event_types: dict[str, str]
    semantic_categories: dict[str, str]
    semantic_classes: list[SemanticClassDef]
    semantic_groups: dict[str, list[str]]

    @model_validator(mode="after")
    def _consistent(self) -> Taxonomy:
        for vocabulary in (self.infrastructure_classes, self.event_types, self.semantic_groups):
            for key in vocabulary:
                if not _SNAKE.match(key):
                    raise ValueError(f"taxonomy name {key!r} is not snake_case")
        ids = [c.id for c in self.semantic_classes]
        if ids != list(range(len(ids))):
            raise ValueError("semantic class ids must be 0..N-1 in order")
        names = [c.name for c in self.semantic_classes]
        if len(set(names)) != len(names):
            raise ValueError("semantic class names must be unique")
        for name in names:
            if not _SNAKE.match(name):
                raise ValueError(f"semantic class name {name!r} is not snake_case")
        if "unknown" not in names or "unknown" not in self.semantic_categories:
            raise ValueError("the taxonomy must contain an 'unknown' class and category")
        for cls in self.semantic_classes:
            if cls.parent not in self.semantic_categories:
                raise ValueError(f"semantic class {cls.name!r}: unknown parent category {cls.parent!r}")
        for group, members in self.semantic_groups.items():
            unknown = sorted(set(members) - set(names))
            if unknown:
                raise ValueError(f"semantic group {group!r} references unknown classes {unknown}")
        return self

    @property
    def semantic_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.semantic_classes)

    def semantic_parent(self, name: str) -> str:
        """Level-1 category of a semantic class (hierarchical taxonomy)."""
        for cls in self.semantic_classes:
            if cls.name == name:
                return cls.parent
        raise KeyError(f"unknown semantic class {name!r}")

    def semantic_id(self, name: str) -> int:
        try:
            return self.semantic_names.index(name)
        except ValueError:
            raise KeyError(f"unknown semantic class {name!r}") from None


# --------------------------------------------------------------------------- #
# Vehicle catalogue (configs/vehicles.yaml)
# --------------------------------------------------------------------------- #
class VehicleType(_Strict):
    label: str
    description: str
    propulsion: str
    rider_posture: str
    legal_max_speed_kmh: PositiveFloat | None
    analysis_overrides: dict[str, Any]


class VehicleCatalogue(_Strict):
    vehicles_version: int = Field(ge=1)
    vehicle_types: dict[str, VehicleType]
    characteristics_fields: dict[str, str]

    @model_validator(mode="after")
    def _names(self) -> VehicleCatalogue:
        for key in self.vehicle_types:
            if not _SNAKE.match(key):
                raise ValueError(f"vehicle type {key!r} is not snake_case")
        if not self.vehicle_types:
            raise ValueError("at least one vehicle type is required")
        return self


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LoadedConfig:
    """Validated configuration plus provenance information."""

    analysis: AnalysisConfig
    taxonomy: Taxonomy
    merged: dict[str, Any]
    sources: tuple[str, ...]
    sha256: str
    project_root: Path
    vehicles: VehicleCatalogue
    vehicle_type: str | None = None

    @property
    def data_root(self) -> Path:
        return resolve_data_root(self.analysis.paths, self.project_root)

    def for_vehicle(self, vehicle_type: str) -> LoadedConfig:
        """Configuration for rides with ``vehicle_type``: shared parameters plus the
        vehicle's ``analysis_overrides`` (configs/vehicles.yaml), re-validated.

        With empty overrides the analysis parameters are identical for all
        vehicles, but the vehicle type is still recorded with the run.
        """
        try:
            vt = self.vehicles.vehicle_types[vehicle_type]
        except KeyError:
            known = sorted(self.vehicles.vehicle_types)
            raise ConfigError(f"unknown vehicle_type {vehicle_type!r}; known: {known}") from None
        merged = deep_merge(self.merged, vt.analysis_overrides) if vt.analysis_overrides else copy.deepcopy(self.merged)
        try:
            analysis = AnalysisConfig.model_validate(merged)
        except ValidationError as exc:
            raise ConfigError(f"invalid analysis_overrides for vehicle {vehicle_type!r}:\n{exc}") from exc
        sources = self.sources + ((f"vehicles.yaml:{vehicle_type}",) if vt.analysis_overrides else ())
        return LoadedConfig(
            analysis=analysis,
            taxonomy=self.taxonomy,
            merged=merged,
            sources=sources,
            sha256=_canonical_sha256(merged),
            project_root=self.project_root,
            vehicles=self.vehicles,
            vehicle_type=vehicle_type,
        )

    def effective_yaml(self) -> str:
        """Human-readable dump of the merged configuration (key order preserved)."""
        return yaml.safe_dump(self.merged, sort_keys=False, allow_unicode=True)


def find_project_root(start: Path | None = None) -> Path:
    """Locate the repository root (folder with pyproject.toml and configs/default.yaml)."""
    env = os.environ.get(ENV_PROJECT_ROOT)
    if env:
        root = Path(env).expanduser()
        if not root.joinpath(*DEFAULT_CONFIG_PARTS).is_file():
            raise ConfigError(f"{ENV_PROJECT_ROOT}={env!r} does not contain configs/default.yaml")
        return root.resolve()
    starts = [Path(start) if start is not None else Path.cwd(), Path(__file__).resolve().parent]
    for begin in starts:
        begin = begin.resolve()
        for candidate in (begin, *begin.parents):
            if (candidate / "pyproject.toml").is_file() and candidate.joinpath(*DEFAULT_CONFIG_PARTS).is_file():
                return candidate
    raise ConfigError(
        f"Project root not found: run from inside the AriaGenEScooter repository or set {ENV_PROJECT_ROOT}."
    )


def resolve_data_root(paths: PathsConfig, project_root: Path) -> Path:
    """Data root from ARIAGEN_DATA_ROOT, else ``paths.data_root`` (relative to the project)."""
    raw = os.environ.get(ENV_DATA_ROOT) or paths.data_root
    path = Path(raw).expanduser()
    return path if path.is_absolute() else project_root / path


def is_absolute_any(path: str) -> bool:
    """True if ``path`` is absolute on *either* Windows or POSIX (non-portable)."""
    win = PureWindowsPath(path)
    return PurePosixPath(path).is_absolute() or win.is_absolute() or bool(win.drive) or bool(win.root)


def portable_path(base: Path, relative: str) -> Path:
    """Resolve a relative, ``/``-separated path stored in a manifest or config.

    Absolute paths are rejected: they would tie the data to one machine/OS.
    Backslashes are accepted and normalised so Windows-edited files still work.
    """
    if not relative or not relative.strip():
        raise ConfigError("empty path")
    if is_absolute_any(relative):
        raise ConfigError(f"absolute paths are not portable and not allowed here: {relative!r}")
    parts = PurePosixPath(relative.replace("\\", "/")).parts
    return base.joinpath(*parts)


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base`` (mappings merge, rest replaces)."""
    merged = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError:
        raise ConfigError(f"configuration file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def _canonical_sha256(data: Mapping[str, Any]) -> str:
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_taxonomy(path: Path) -> Taxonomy:
    try:
        return Taxonomy.model_validate(read_yaml_mapping(path))
    except ValidationError as exc:
        raise ConfigError(f"invalid taxonomy {path}:\n{exc}") from exc


def load_vehicles(path: Path) -> VehicleCatalogue:
    try:
        return VehicleCatalogue.model_validate(read_yaml_mapping(path))
    except ValidationError as exc:
        raise ConfigError(f"invalid vehicle catalogue {path}:\n{exc}") from exc


def load_config(
    overrides: Sequence[Path | Mapping[str, Any]] = (),
    *,
    base: Path | None = None,
    project_root: Path | None = None,
) -> LoadedConfig:
    """Load ``configs/default.yaml`` (or ``base``), deep-merge overrides, validate.

    ``overrides`` are applied in order; each is a YAML file or a mapping.
    The taxonomy file is resolved relative to the directory of the base file.
    """
    root = project_root if project_root is not None else find_project_root()
    base_path = base if base is not None else root.joinpath(*DEFAULT_CONFIG_PARTS)
    merged = read_yaml_mapping(base_path)
    sources = [_display_path(base_path, root)]
    for item in overrides:
        if isinstance(item, Mapping):
            merged = deep_merge(merged, item)
            sources.append("<mapping>")
        else:
            merged = deep_merge(merged, read_yaml_mapping(Path(item)))
            sources.append(_display_path(Path(item), root))
    try:
        analysis = AnalysisConfig.model_validate(merged)
    except ValidationError as exc:
        raise ConfigError(f"invalid configuration ({' + '.join(sources)}):\n{exc}") from exc
    taxonomy = load_taxonomy(portable_path(base_path.parent, analysis.paths.taxonomy_file))
    vehicles = load_vehicles(portable_path(base_path.parent, analysis.paths.vehicles_file))
    unknown = sorted(set(analysis.kinematics.approach_classes) - set(taxonomy.infrastructure_classes))
    if unknown:
        raise ConfigError(f"kinematics.approach_classes not in taxonomy: {unknown}")
    return LoadedConfig(
        analysis=analysis,
        taxonomy=taxonomy,
        merged=merged,
        sources=tuple(sources),
        sha256=_canonical_sha256(merged),
        project_root=root,
        vehicles=vehicles,
    )


def _display_path(path: Path, root: Path) -> str:
    """Path relative to the project root when possible (no absolute paths in reports)."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name
