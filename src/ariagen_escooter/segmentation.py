"""Scene parsing: segmentation interface, label-map storage and label mapping.

Design
------
* :class:`SemanticSegmenter` is the common interface. Back-ends return label
  maps in their *native* vocabulary plus ``id2label``; a
  :class:`LabelMapping` (YAML file) converts them to the project taxonomy.
  Swapping models therefore only requires a new back-end and a mapping file.
* Heavy inference (GPU, Linux) and analysis are decoupled: label maps are
  computed once and stored per recording in ``semantic/labels.npz``
  (:class:`LabelMapStore`), then read by the semantic-gaze module.
* Label maps may be lower resolution than the RGB frames; the store records
  the size of the source image so that gaze pixel coordinates can be scaled.

Status: the store, the mapping and the frame loop are implemented and tested.
The Hugging Face back-end is EXPERIMENTAL (optional dependencies, model
download, not validated on Aria imagery). Instance ids require a detector or
tracker (planned); they are available in the synthetic data only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ariagen_escooter.config import ConfigError, read_yaml_mapping


@dataclass(frozen=True)
class SegmentationResult:
    """Output of a segmenter for one image (native or project vocabulary)."""

    labels: np.ndarray  # (H, W) integer class ids
    id2label: Mapping[int, str]
    instances: np.ndarray | None = None  # (H, W) instance/track ids, 0 = none


class SemanticSegmenter(ABC):
    """Common interface of all segmentation back-ends."""

    name: str = "abstract"

    @abstractmethod
    def segment(self, image: np.ndarray) -> SegmentationResult:
        """Segment one RGB image (H, W, 3) uint8."""


class LabelMapping:
    """Maps back-end labels to project semantic classes.

    YAML format::

        backend: <free text>
        default: unknown            # class for unmapped labels
        map:
          "Bike Lane": cycle_lane
          "Crosswalk - Plain": crossing
    """

    def __init__(self, mapping: Mapping[str, str], default: str, class_names: tuple[str, ...]):
        unknown = sorted({*mapping.values(), default} - set(class_names))
        if unknown:
            raise ConfigError(f"label mapping targets unknown project classes: {unknown}")
        self.mapping = dict(mapping)
        self.default = default
        self.class_names = class_names

    @classmethod
    def from_yaml(cls, path: Path, class_names: tuple[str, ...]) -> LabelMapping:
        data = read_yaml_mapping(path)
        return cls(data.get("map", {}), data.get("default", "unknown"), class_names)

    def lookup_table(self, id2label: Mapping[int, str]) -> np.ndarray:
        size = max(id2label) + 1 if id2label else 1
        table = np.full(size, self.class_names.index(self.default), dtype=np.uint8)
        for native_id, label in id2label.items():
            target = self.mapping.get(label, self.default)
            table[native_id] = self.class_names.index(target)
        return table

    def apply(self, result: SegmentationResult) -> np.ndarray:
        """Native label map -> project class ids (uint8)."""
        table = self.lookup_table(result.id2label)
        native = np.asarray(result.labels)
        if native.size and (native.min() < 0 or native.max() >= table.size):
            raise ValueError("label map contains ids missing from id2label")
        return table[native]


class LabelMapStore:
    """Label maps of one recording, keyed by RGB frame index (``labels.npz``)."""

    def __init__(
        self,
        frame_index: np.ndarray,
        labels: np.ndarray,
        class_names: tuple[str, ...],
        source_size: tuple[int, int],
        backend: str,
        instances: np.ndarray | None = None,
    ):
        frame_index = np.asarray(frame_index, dtype=np.int64)
        if labels.ndim != 3 or labels.shape[0] != frame_index.size:
            raise ValueError("labels must have shape (n_frames, H, W) matching frame_index")
        if instances is not None and instances.shape != labels.shape:
            raise ValueError("instances must have the same shape as labels")
        if np.unique(frame_index).size != frame_index.size:
            raise ValueError("duplicated frame indices in label store")
        if labels.size and int(labels.max()) >= len(class_names):
            raise ValueError("label ids exceed the number of class names")
        self.frame_index = frame_index
        self.labels = labels
        self.instances = instances
        self.class_names = tuple(class_names)
        self.source_size = (int(source_size[0]), int(source_size[1]))  # (width, height)
        self.backend = backend
        self._row = {int(f): i for i, f in enumerate(frame_index)}

    @property
    def map_size(self) -> tuple[int, int]:
        """(width, height) of the stored label maps."""
        return int(self.labels.shape[2]), int(self.labels.shape[1])

    def __len__(self) -> int:
        return int(self.frame_index.size)

    def has(self, frame: int) -> bool:
        return int(frame) in self._row

    def row(self, frame: int) -> int | None:
        return self._row.get(int(frame))

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        arrays: dict[str, np.ndarray] = {
            "frame_index": self.frame_index,
            "labels": self.labels,
            "class_names": np.array(self.class_names, dtype=np.str_),
            "source_size": np.array(self.source_size, dtype=np.int64),
            "backend": np.array(self.backend, dtype=np.str_),
        }
        if self.instances is not None:
            arrays["instances"] = self.instances
        with path.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        return path

    @classmethod
    def load(cls, path: Path) -> LabelMapStore:
        with np.load(path, allow_pickle=False) as data:
            return cls(
                frame_index=data["frame_index"],
                labels=data["labels"],
                class_names=tuple(str(x) for x in data["class_names"]),
                source_size=tuple(int(x) for x in data["source_size"]),
                backend=str(data["backend"]),
                instances=data["instances"] if "instances" in data.files else None,
            )

    def to_taxonomy(self, taxonomy_names: tuple[str, ...]) -> LabelMapStore:
        """Re-index labels onto the taxonomy order (by class name)."""
        unknown = sorted(set(self.class_names) - set(taxonomy_names))
        if unknown:
            raise ConfigError(f"label maps use classes not in the taxonomy: {unknown}")
        table = np.array([taxonomy_names.index(n) for n in self.class_names], dtype=np.uint8)
        return LabelMapStore(
            self.frame_index, table[self.labels], taxonomy_names, self.source_size, self.backend, self.instances
        )


def segment_frames(
    frames: Iterable[tuple[int, np.ndarray]],
    segmenter: SemanticSegmenter,
    mapping: LabelMapping,
    *,
    map_size: tuple[int, int] | None = None,
) -> LabelMapStore:
    """Run a segmenter over ``(frame_index, image)`` pairs and collect a store.

    ``map_size`` (width, height) optionally downsamples label maps with
    nearest-neighbour sampling to keep storage small.
    """
    indices: list[int] = []
    maps: list[np.ndarray] = []
    inst_maps: list[np.ndarray] = []
    have_instances = True
    source_size: tuple[int, int] | None = None
    for frame_index, image in frames:
        if source_size is None:
            source_size = (int(image.shape[1]), int(image.shape[0]))
        result = segmenter.segment(image)
        labels = mapping.apply(result)
        instances = result.instances
        if map_size is not None:
            labels = _resize_nearest(labels, map_size)
            instances = _resize_nearest(instances, map_size) if instances is not None else None
        indices.append(int(frame_index))
        maps.append(labels.astype(np.uint8))
        if instances is None:
            have_instances = False
        else:
            inst_maps.append(instances.astype(np.uint16))
    if not maps or source_size is None:
        raise ValueError("no frames to segment")
    return LabelMapStore(
        np.array(indices),
        np.stack(maps),
        mapping.class_names,
        source_size,
        segmenter.name,
        np.stack(inst_maps) if have_instances and inst_maps else None,
    )


def _resize_nearest(array: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    rows = (np.arange(height) * array.shape[0] / height).astype(np.int64)
    cols = (np.arange(width) * array.shape[1] / width).astype(np.int64)
    return array[rows[:, None], cols[None, :]]


class HuggingFaceSegmenter(SemanticSegmenter):
    """EXPERIMENTAL back-end based on Hugging Face ``transformers``.

    Works with semantic-segmentation checkpoints whose image processor offers
    ``post_process_semantic_segmentation`` (e.g. SegFormer, Mask2Former).
    Requires the ``cv`` extra (torch, transformers) and downloads the model on
    first use. Not validated on Aria fisheye imagery: treat outputs as
    provisional until a validation subset has been annotated.
    """

    name = "huggingface"

    def __init__(self, model_id: str, device: str = "cpu"):
        try:
            import torch  # noqa: F401
            from transformers import AutoImageProcessor
        except ImportError as exc:  # pragma: no cover - depends on optional extras
            raise ImportError("HuggingFaceSegmenter needs the 'cv' extra (torch, transformers)") from exc
        self.model_id = model_id
        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = self._load_model(model_id).to(device).eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        self.name = f"huggingface:{model_id}"

    @staticmethod
    def _load_model(model_id: str):  # pragma: no cover - optional dependency
        from transformers import AutoModelForSemanticSegmentation, AutoModelForUniversalSegmentation

        try:
            return AutoModelForSemanticSegmentation.from_pretrained(model_id)
        except ValueError:
            return AutoModelForUniversalSegmentation.from_pretrained(model_id)

    def segment(self, image: np.ndarray) -> SegmentationResult:  # pragma: no cover - optional dependency
        import torch

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        height, width = image.shape[:2]
        label_map = self.processor.post_process_semantic_segmentation(outputs, target_sizes=[(height, width)])[0]
        return SegmentationResult(labels=label_map.cpu().numpy().astype(np.int64), id2label=self.id2label)
