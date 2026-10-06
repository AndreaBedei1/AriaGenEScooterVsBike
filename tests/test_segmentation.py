"""Segmentation interface, label mappings and label-map storage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ariagen_escooter.config import ConfigError, LoadedConfig
from ariagen_escooter.segmentation import (
    LabelMapping,
    LabelMapStore,
    SegmentationResult,
    SemanticSegmenter,
    segment_frames,
)


class _HalfSegmenter(SemanticSegmenter):
    """Dummy back-end: left half 'Road', right half 'Person' (native vocabulary)."""

    name = "dummy"

    def segment(self, image: np.ndarray) -> SegmentationResult:
        labels = np.zeros(image.shape[:2], dtype=np.int64)
        labels[:, image.shape[1] // 2 :] = 1
        return SegmentationResult(labels, {0: "Road", 1: "Person"})


def test_label_mapping_and_unknown_default(cfg: LoadedConfig) -> None:
    mapping = LabelMapping({"Road": "road", "Person": "pedestrian"}, "unknown", cfg.taxonomy.semantic_names)
    result = SegmentationResult(np.array([[0, 1, 2]]), {0: "Road", 1: "Person", 2: "Bird"})
    out = mapping.apply(result)
    names = cfg.taxonomy.semantic_names
    assert [names[i] for i in out[0]] == ["road", "pedestrian", "unknown"]
    with pytest.raises(ConfigError):
        LabelMapping({"Road": "highway"}, "unknown", names)


@pytest.mark.parametrize("name", ["mapillary_vistas_v1_2.yaml", "cityscapes.yaml"])
def test_shipped_mapping_files_target_taxonomy(cfg: LoadedConfig, project_root: Path, name: str) -> None:
    mapping = LabelMapping.from_yaml(project_root / "configs" / "label_mappings" / name, cfg.taxonomy.semantic_names)
    assert set(mapping.mapping.values()) <= set(cfg.taxonomy.semantic_names)
    assert len(mapping.mapping) in (65, 19)


def test_store_roundtrip_and_reindex(tmp_path: Path, cfg: LoadedConfig) -> None:
    store = LabelMapStore(
        np.array([3, 5]),
        np.array([[[0, 1]], [[1, 1]]], dtype=np.uint8),
        ("road", "car"),
        (200, 100),
        "unit",
        np.array([[[0, 4]], [[4, 4]]], dtype=np.uint16),
    )
    path = store.save(tmp_path / "labels.npz")
    loaded = LabelMapStore.load(path)
    assert loaded.class_names == ("road", "car") and loaded.source_size == (200, 100)
    assert loaded.has(5) and not loaded.has(4) and loaded.map_size == (2, 1)
    reindexed = loaded.to_taxonomy(cfg.taxonomy.semantic_names)
    assert reindexed.labels[0, 0, 1] == cfg.taxonomy.semantic_id("car")
    with pytest.raises(ConfigError):
        LabelMapStore(np.array([0]), np.zeros((1, 1, 1), np.uint8), ("lava",), (1, 1), "x").to_taxonomy(
            cfg.taxonomy.semantic_names
        )


def test_store_rejects_inconsistent_input() -> None:
    with pytest.raises(ValueError):
        LabelMapStore(np.array([0, 0]), np.zeros((2, 2, 2), np.uint8), ("a",), (2, 2), "x")
    with pytest.raises(ValueError):
        LabelMapStore(np.array([0]), np.full((1, 2, 2), 3, np.uint8), ("a", "b"), (2, 2), "x")


def test_segment_frames_with_downsampling(cfg: LoadedConfig) -> None:
    mapping = LabelMapping({"Road": "road", "Person": "pedestrian"}, "unknown", cfg.taxonomy.semantic_names)
    frames = [(i, np.zeros((60, 80, 3), np.uint8)) for i in (0, 1, 2)]
    store = segment_frames(frames, _HalfSegmenter(), mapping, map_size=(8, 6))
    assert len(store) == 3 and store.map_size == (8, 6) and store.source_size == (80, 60)
    assert store.labels[0, 0, 0] == cfg.taxonomy.semantic_id("road")
    assert store.labels[0, 0, -1] == cfg.taxonomy.semantic_id("pedestrian")
    assert store.instances is None
