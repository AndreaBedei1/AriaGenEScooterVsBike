"""Privacy utilities: identifier scanning, GPS protection, region blurring."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.config import LoadedConfig
from ariagen_escooter.privacy import (
    DATA_TIER_BY_FOLDER,
    AnonymizationLog,
    DataTier,
    Detection,
    PrivacyZone,
    RegionDetector,
    anonymize_frames,
    blur_regions,
    generalize_coordinates,
    haversine_m,
    remove_privacy_zones,
    scan_for_identifiers,
    to_relative_coordinates,
    trim_endpoints,
)
from ariagen_escooter.trajectory import latlon_to_local_xy, local_xy_to_latlon


def _keys(cfg: LoadedConfig) -> list[str]:
    return cfg.analysis.privacy.forbidden_manifest_keys


def test_scanner_flags_direct_identifiers(cfg: LoadedConfig) -> None:
    data = {
        "participant_id": "P001",
        "nome": "x",
        "notes": "contact mario.rossi@example.org or +39 333 1234567",
        "recordings": [{"notes": "CF RSSMRA80A01H501U"}],
    }
    kinds = {(f.path, f.kind) for f in scan_for_identifiers(data, _keys(cfg))}
    assert ("nome", "forbidden_key") in kinds
    assert ("notes", "email_like_value") in kinds
    assert ("notes", "phone_like_value") in kinds
    assert ("recordings[0].notes", "fiscal_code_like_value") in kinds


def test_scanner_does_not_echo_values(cfg: LoadedConfig) -> None:
    findings = scan_for_identifiers({"notes": "mario.rossi@example.org"}, _keys(cfg))
    assert findings and all("mario" not in str(f) for f in findings)


def test_scanner_accepts_valid_manifests(cfg: LoadedConfig, synthetic_session, project_root) -> None:
    from ariagen_escooter.io import read_yaml

    for path in (synthetic_session / "manifest.yaml", project_root / "configs" / "example_session.yaml"):
        assert scan_for_identifiers(read_yaml(path), _keys(cfg)) == []


def _track(n: int = 200, step_m: float = 10.0) -> pd.DataFrame:
    x = np.arange(n) * step_m
    lat, lon = local_xy_to_latlon(x, np.zeros(n), 45.0, 13.0)
    return pd.DataFrame({"t_ns": np.arange(n) * 1_000_000_000, "lat_deg": lat, "lon_deg": lon})


def test_trim_endpoints_removes_start_and_end_zones() -> None:
    gps = _track()
    out = trim_endpoints(gps, radius_m=205.0)
    d_start = haversine_m(
        out["lat_deg"].to_numpy(), out["lon_deg"].to_numpy(), gps["lat_deg"].iat[0], gps["lon_deg"].iat[0]
    )
    d_end = haversine_m(
        out["lat_deg"].to_numpy(), out["lon_deg"].to_numpy(), gps["lat_deg"].iat[-1], gps["lon_deg"].iat[-1]
    )
    assert d_start.min() > 205.0 and d_end.min() > 205.0
    assert len(out) == len(gps) - 2 * 21  # points 0..200 m from each end
    assert len(gps) == 200  # input untouched


def test_privacy_zones_are_removed() -> None:
    gps = _track()
    zone = PrivacyZone(float(gps["lat_deg"].iat[100]), float(gps["lon_deg"].iat[100]), 55.0)
    out = remove_privacy_zones(gps, [zone])
    assert len(out) == len(gps) - 11
    assert (haversine_m(out["lat_deg"].to_numpy(), out["lon_deg"].to_numpy(), zone.lat_deg, zone.lon_deg) > 55.0).all()


def test_relative_coordinates_hide_position_and_orientation() -> None:
    out = to_relative_coordinates(_track(20))
    assert "lat_deg" not in out.columns and "lon_deg" not in out.columns
    assert out["x_rel_m"].iat[0] == pytest.approx(0.0) and out["y_rel_m"].iat[0] == pytest.approx(0.0)
    # initial direction of travel rotated to +y
    assert out["x_rel_m"].iat[5] == pytest.approx(0.0, abs=1e-6)
    assert out["y_rel_m"].iat[5] == pytest.approx(50.0, rel=1e-3)


def test_generalization_snaps_to_grid() -> None:
    gps = _track(50, step_m=7.0)
    out = generalize_coordinates(gps, grid_m=50.0)
    x0, y0 = latlon_to_local_xy(gps["lat_deg"].to_numpy(), gps["lon_deg"].to_numpy(), 45.0, 13.0)
    x1, y1 = latlon_to_local_xy(out["lat_deg"].to_numpy(), out["lon_deg"].to_numpy(), 45.0, 13.0)
    assert np.hypot(x1 - x0, y1 - y0).max() <= 50.0 * np.sqrt(2) / 2 + 0.01
    assert out[["lat_deg", "lon_deg"]].drop_duplicates().shape[0] < len(gps)


def test_blur_changes_only_the_region(cfg: LoadedConfig) -> None:
    rng = np.random.default_rng(0)
    image = rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)
    original = image.copy()
    det = Detection(40, 30, 80, 70, 0.9, "face")
    out = blur_regions(image, [det], cfg.analysis.privacy.blur)
    assert out.shape == image.shape and out.dtype == image.dtype
    changed = np.any(out != image, axis=2)
    ys, xs = np.nonzero(changed)
    margin = cfg.analysis.privacy.blur.margin_fraction * 40
    assert xs.min() >= 40 - margin - 1 and xs.max() <= 80 + margin + 1
    assert ys.min() >= 30 - margin - 1 and ys.max() <= 70 + margin + 1
    assert out[30:70, 40:80].std() < image[30:70, 40:80].std() / 2
    assert np.array_equal(image, original)  # input never modified


def test_pixelate_method(cfg: LoadedConfig) -> None:
    blur = cfg.analysis.privacy.blur.model_copy(
        update={"method": "pixelate", "pixelate_blocks": 4, "margin_fraction": 0.0}
    )
    image = np.tile(np.arange(64, dtype=np.uint8), (64, 1))
    out = blur_regions(image, [Detection(0, 0, 64, 64, 1.0, "license_plate")], blur)
    assert len(np.unique(out)) == 4


class _FakeDetector(RegionDetector):
    name = "fake"

    def detect(self, image: np.ndarray) -> list[Detection]:
        return [Detection(0, 0, 10, 10, 0.95, "face"), Detection(20, 20, 30, 30, 0.2, "license_plate")]


def test_anonymize_frames_logs_and_keeps_originals(cfg: LoadedConfig) -> None:
    frames = [(i, np.full((40, 40, 3), 100 + i, dtype=np.uint8)) for i in range(3)]
    originals = [f.copy() for _, f in frames]
    log = AnonymizationLog("fake", 0.5)
    results = list(anonymize_frames(frames, _FakeDetector(), cfg.analysis.privacy.blur, 0.5, log))
    assert [len(d) for _, _, d in results] == [1, 1, 1]  # low-score plate filtered
    assert log.as_dict()["n_detections"] == {"face": 3}
    for (_, original), kept in zip(frames, originals):
        assert np.array_equal(original, kept)


def test_data_tiers() -> None:
    assert DATA_TIER_BY_FOLDER["raw"] is DataTier.RAW_IDENTIFIABLE
    assert DATA_TIER_BY_FOLDER["public"] is DataTier.ANONYMISED_PUBLIC
