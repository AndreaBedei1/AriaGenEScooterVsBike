"""Configuration loading: strict schema, overrides, taxonomy consistency."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ariagen_escooter.config import AnalysisConfig, ConfigError, LoadedConfig, deep_merge, load_config


def test_default_config_loads(cfg: LoadedConfig) -> None:
    assert cfg.analysis.config_version == 1
    assert cfg.sources == ("configs/default.yaml",)
    assert len(cfg.sha256) == 64
    assert "protected_cycle_path" in cfg.taxonomy.infrastructure_classes
    assert cfg.taxonomy.semantic_names[0] == "unknown"


def test_config_hash_is_stable(project_root: Path) -> None:
    assert load_config(project_root=project_root).sha256 == load_config(project_root=project_root).sha256


def test_models_have_no_hidden_defaults(project_root: Path) -> None:
    """Every analysis parameter must come from the YAML file (no defaults in code)."""
    data = yaml.safe_load((project_root / "configs" / "default.yaml").read_text(encoding="utf-8"))
    data["trimming"].pop("speed_threshold_mps")
    with pytest.raises(Exception, match="speed_threshold_mps"):
        AnalysisConfig.model_validate(data)


def test_unknown_key_is_rejected(project_root: Path) -> None:
    with pytest.raises(ConfigError, match="speed_treshold_mps"):
        load_config([{"trimming": {"speed_treshold_mps": 1.0}}], project_root=project_root)


@pytest.mark.parametrize(
    "override",
    [
        {"trimming": {"speed_threshold_mps": -1.0}},
        {"kinematics": {"braking": {"onset_threshold_mps2": 5.0}}},
        {"gaze": {"forward": {"pitch_min_deg": 20.0}}},
        {
            "gaze": {
                "vertical_bands": [
                    {"name": "a", "min_deg": -10, "max_deg": 10},
                    {"name": "b", "min_deg": 0, "max_deg": 20},
                ]
            }
        },
        {"kinematics": {"approach_classes": ["not_a_class"]}},
        {"kinematics": {"savgol_polyorder": 1}},
    ],
)
def test_invalid_values_are_rejected(project_root: Path, override: dict) -> None:
    with pytest.raises(ConfigError):
        load_config([override], project_root=project_root)


def test_override_file_is_merged(project_root: Path, tmp_path: Path) -> None:
    override = tmp_path / "override.yaml"
    override.write_text("trimming:\n  speed_threshold_mps: 1.7\n", encoding="utf-8")
    cfg = load_config([override], project_root=project_root)
    assert cfg.analysis.trimming.speed_threshold_mps == 1.7
    assert cfg.analysis.trimming.min_moving_duration_s == 10.0  # untouched keys kept
    assert cfg.sha256 != load_config(project_root=project_root).sha256


def test_deep_merge_does_not_mutate_inputs() -> None:
    base = {"a": {"b": 1, "c": 2}}
    merged = deep_merge(base, {"a": {"b": 3}})
    assert merged == {"a": {"b": 3, "c": 2}}
    assert base == {"a": {"b": 1, "c": 2}}


def test_taxonomy_groups_reference_existing_classes(cfg: LoadedConfig) -> None:
    names = set(cfg.taxonomy.semantic_names)
    for members in cfg.taxonomy.semantic_groups.values():
        assert set(members) <= names
    required = {
        "protected_cycle_path",
        "painted_cycle_lane",
        "shared_pedestrian_cycle_path",
        "road_shared_with_traffic",
        "pedestrian_or_shared_space",
        "crossing",
        "intersection",
        "roundabout",
    }
    assert required <= set(cfg.taxonomy.infrastructure_classes)
    for event in (
        "pedestrian_interaction",
        "cyclist_interaction",
        "escooter_interaction",
        "vehicle_interaction",
        "overtaking",
        "stopping",
        "obstacle",
        "narrow_section",
        "parked_vehicle",
    ):
        assert event in cfg.taxonomy.event_types


def test_effective_yaml_roundtrip(cfg: LoadedConfig) -> None:
    assert yaml.safe_load(cfg.effective_yaml()) == cfg.merged
