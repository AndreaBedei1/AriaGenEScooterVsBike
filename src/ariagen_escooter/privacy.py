"""Privacy-by-design utilities.

Implemented here (and tested):

* data tiers (raw identifiable / pseudonymised research / anonymised public);
* a scanner that rejects direct identifiers in manifests (names, e-mails,
  phone numbers, Italian fiscal codes...);
* GPS protection: removal of start/end zones, removal of declared privacy
  zones, relative coordinates, spatial generalisation;
* region blurring of images given detection boxes (gaussian or pixelation)
  and an anonymisation loop with a per-frame log.

Face / licence-plate DETECTION requires a detector back-end. The intended
back-end is Meta's EgoBlur (see docs/privacy_pipeline.md); it is not bundled
and not yet validated here - only the :class:`RegionDetector` interface is.
Nothing in this module deletes original data.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

from ariagen_escooter.config import BlurConfig
from ariagen_escooter.trajectory import EARTH_RADIUS_M, latlon_to_local_xy, local_xy_to_latlon


class DataTier(str, Enum):
    """Where data may live and who may access them."""

    RAW_IDENTIFIABLE = "raw_identifiable"  # data/raw: VRS, raw video, precise GPS - restricted
    PSEUDONYMISED_RESEARCH = "pseudonymised_research"  # data/interim, data/processed - study team
    ANONYMISED_PUBLIC = "anonymised_public"  # data/public - only after explicit review/export


DATA_TIER_BY_FOLDER = {
    "raw": DataTier.RAW_IDENTIFIABLE,
    "interim": DataTier.PSEUDONYMISED_RESEARCH,
    "processed": DataTier.PSEUDONYMISED_RESEARCH,
    "public": DataTier.ANONYMISED_PUBLIC,
}

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\w.])(?:\+|00)?\d(?:[\s-]?\d){8,13}(?![\w.])")
_FISCAL_CODE = re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b", re.IGNORECASE)


@dataclass(frozen=True)
class PrivacyFinding:
    path: str
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: {self.kind} ({self.detail})"


def scan_for_identifiers(data: Any, forbidden_keys: Sequence[str], path: str = "") -> list[PrivacyFinding]:
    """Recursively flag forbidden keys and identifier-like values (e-mail, phone, fiscal code).

    Values are never echoed back in full (only their type), so that the
    report itself does not leak the identifier.
    """
    findings: list[PrivacyFinding] = []
    forbidden = {k.lower() for k in forbidden_keys}
    if isinstance(data, Mapping):
        for key, value in data.items():
            child = f"{path}.{key}" if path else str(key)
            if str(key).lower() in forbidden:
                findings.append(PrivacyFinding(child, "forbidden_key", f"key {key!r} is a direct identifier"))
            findings.extend(scan_for_identifiers(value, forbidden_keys, child))
    elif isinstance(data, (list, tuple)):
        for i, value in enumerate(data):
            findings.extend(scan_for_identifiers(value, forbidden_keys, f"{path}[{i}]"))
    elif isinstance(data, str):
        if _EMAIL.search(data):
            findings.append(PrivacyFinding(path, "email_like_value", "value looks like an e-mail address"))
        if _PHONE.search(data):
            findings.append(PrivacyFinding(path, "phone_like_value", "value looks like a phone number"))
        if _FISCAL_CODE.search(data):
            findings.append(PrivacyFinding(path, "fiscal_code_like_value", "value looks like an Italian fiscal code"))
    return findings


# --------------------------------------------------------------------------- #
# GPS
# --------------------------------------------------------------------------- #
def haversine_m(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    """Great-circle distance (m) from points to one reference point."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def trim_endpoints(gps: pd.DataFrame, radius_m: float) -> pd.DataFrame:
    """Remove fixes within ``radius_m`` of the first and of the last fix.

    Protects start/arrival locations (home, workplace, meeting point).
    """
    if gps.empty or radius_m <= 0:
        return gps.copy()
    lat, lon = gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy()
    near_start = haversine_m(lat, lon, lat[0], lon[0]) <= radius_m
    near_end = haversine_m(lat, lon, lat[-1], lon[-1]) <= radius_m
    return gps.loc[~(near_start | near_end)].reset_index(drop=True)


@dataclass(frozen=True)
class PrivacyZone:
    lat_deg: float
    lon_deg: float
    radius_m: float


def remove_privacy_zones(gps: pd.DataFrame, zones: Iterable[PrivacyZone]) -> pd.DataFrame:
    """Remove fixes inside declared zones (zones are kept in a non-versioned local file)."""
    keep = np.ones(len(gps), dtype=bool)
    lat, lon = gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy()
    for zone in zones:
        keep &= haversine_m(lat, lon, zone.lat_deg, zone.lon_deg) > zone.radius_m
    return gps.loc[keep].reset_index(drop=True)


def to_relative_coordinates(gps: pd.DataFrame, rotate_to_first_heading: bool = True) -> pd.DataFrame:
    """Replace lat/lon by metres relative to the first fix (absolute position removed).

    With ``rotate_to_first_heading`` the trajectory is also rotated so that the
    initial direction of travel is +y, which removes the absolute orientation.
    """
    out = gps.drop(columns=[c for c in ("lat_deg", "lon_deg") if c in gps.columns]).copy()
    if gps.empty:
        out["x_rel_m"], out["y_rel_m"] = [], []
        return out
    x, y = latlon_to_local_xy(
        gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy(), gps["lat_deg"].iat[0], gps["lon_deg"].iat[0]
    )
    if rotate_to_first_heading:
        moved = np.flatnonzero(np.hypot(x, y) > 1e-6)
        if moved.size:
            k = moved[0]
            angle = np.arctan2(y[k], x[k]) - np.pi / 2
            c, s = np.cos(-angle), np.sin(-angle)
            x, y = c * x - s * y, s * x + c * y
    out["x_rel_m"], out["y_rel_m"] = x, y
    return out


def generalize_coordinates(gps: pd.DataFrame, grid_m: float) -> pd.DataFrame:
    """Snap fixes to the centres of a ``grid_m`` metric grid.

    The grid is anchored at longitude 0 and at the whole-degree latitude closest
    to the data, so the same grid is used for every session in a city.
    """
    out = gps.copy()
    if gps.empty:
        return out
    lat, lon = gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy()
    ref_lat = float(np.round(np.mean(lat)))
    x, y = latlon_to_local_xy(lat, lon, ref_lat, 0.0)
    xs = (np.floor(x / grid_m) + 0.5) * grid_m
    ys = (np.floor(y / grid_m) + 0.5) * grid_m
    out["lat_deg"], out["lon_deg"] = local_xy_to_latlon(xs, ys, ref_lat, 0.0)
    return out


# --------------------------------------------------------------------------- #
# Image regions
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Detection:
    """Axis-aligned box in pixel coordinates (x0, y0) inclusive - (x1, y1) exclusive."""

    x0: float
    y0: float
    x1: float
    y1: float
    score: float
    label: str  # e.g. "face", "license_plate"


class RegionDetector(ABC):
    """Interface for face / licence-plate detectors (e.g. an EgoBlur adapter)."""

    name: str = "abstract"

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[Detection]:
        """Return detections for one RGB image (H, W, 3)."""


def blur_regions(image: np.ndarray, detections: Sequence[Detection], cfg: BlurConfig) -> np.ndarray:
    """Return a copy of ``image`` with every detection box blurred (input untouched)."""
    out = np.array(image, copy=True)
    height, width = out.shape[:2]
    for det in detections:
        bw, bh = det.x1 - det.x0, det.y1 - det.y0
        mx, my = cfg.margin_fraction * bw, cfg.margin_fraction * bh
        x0 = int(max(0, np.floor(det.x0 - mx)))
        y0 = int(max(0, np.floor(det.y0 - my)))
        x1 = int(min(width, np.ceil(det.x1 + mx)))
        y1 = int(min(height, np.ceil(det.y1 + my)))
        if x1 <= x0 or y1 <= y0:
            continue
        region = out[y0:y1, x0:x1].astype(np.float64)
        if cfg.method == "gaussian":
            sigma = max(1.0, cfg.gaussian_sigma_fraction * max(x1 - x0, y1 - y0))
            sig = (sigma, sigma, 0) if region.ndim == 3 else (sigma, sigma)
            blurred = gaussian_filter(region, sigma=sig, mode="nearest")
        else:
            blurred = _pixelate(region, cfg.pixelate_blocks)
        out[y0:y1, x0:x1] = np.clip(np.rint(blurred), 0, 255).astype(out.dtype)
    return out


def _pixelate(region: np.ndarray, blocks: int) -> np.ndarray:
    h, w = region.shape[:2]
    out = region.copy()
    ys = np.linspace(0, h, min(blocks, h) + 1).astype(int)
    xs = np.linspace(0, w, min(blocks, w) + 1).astype(int)
    for i in range(len(ys) - 1):
        for j in range(len(xs) - 1):
            cell = region[ys[i] : ys[i + 1], xs[j] : xs[j + 1]]
            if cell.size:
                out[ys[i] : ys[i + 1], xs[j] : xs[j + 1]] = cell.mean(axis=(0, 1))
    return out


@dataclass
class AnonymizationLog:
    detector: str
    score_threshold: float
    n_frames: int = 0
    n_detections: dict[str, int] = field(default_factory=dict)
    frames_with_detections: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "detector": self.detector,
            "score_threshold": self.score_threshold,
            "n_frames": self.n_frames,
            "frames_with_detections": self.frames_with_detections,
            "n_detections": dict(sorted(self.n_detections.items())),
        }


def anonymize_frames(
    frames: Iterable[tuple[int, np.ndarray]],
    detector: RegionDetector,
    cfg: BlurConfig,
    score_threshold: float,
    log: AnonymizationLog | None = None,
) -> Iterator[tuple[int, np.ndarray, list[Detection]]]:
    """Detect and blur regions frame by frame; originals are never overwritten.

    The caller writes the anonymised frames to a NEW location. Recall of the
    detector is never perfect: a manual QA sample is part of the procedure
    (docs/privacy_pipeline.md).
    """
    log = log if log is not None else AnonymizationLog(detector.name, score_threshold)
    for index, image in frames:
        detections = [d for d in detector.detect(image) if d.score >= score_threshold]
        log.n_frames += 1
        if detections:
            log.frames_with_detections += 1
        for det in detections:
            log.n_detections[det.label] = log.n_detections.get(det.label, 0) + 1
        yield index, blur_regions(image, detections, cfg), detections
