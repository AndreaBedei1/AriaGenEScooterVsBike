"""Aria adapter: MPS readers (pure pandas) and, on Linux/macOS, the projectaria-tools API surface."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ariagen_escooter.aria import (
    gravity_alignment,
    poses_to_canonical,
    projectaria_available,
    read_mps_closed_loop_trajectory,
    read_mps_eye_gaze,
    timedelta_to_ns,
)
from ariagen_escooter.gaze import quat_to_rotmat
from ariagen_escooter.streams import STREAM_SPECS, coerce_table


def _closed_loop_csv(path: Path) -> Path:
    """Fixture following the documented MPS closed_loop_trajectory.csv columns."""
    n = 5
    pd.DataFrame(
        {
            "graph_uid": ["g"] * n,
            "tracking_timestamp_us": np.arange(n) * 1000 + 10_000_000,
            "utc_timestamp_ns": -1,
            "tx_world_device": np.arange(n, dtype=float),
            "ty_world_device": 0.0,
            "tz_world_device": 1.6,
            "qx_world_device": 0.0,
            "qy_world_device": 0.0,
            "qz_world_device": np.sin(0.25),
            "qw_world_device": np.cos(0.25),
            "device_linear_velocity_x_device": 1.0,
            "device_linear_velocity_y_device": 0.0,
            "device_linear_velocity_z_device": 0.0,
            "angular_velocity_x_device": 0.0,
            "angular_velocity_y_device": 0.0,
            "angular_velocity_z_device": 0.0,
            "gravity_x_world": 0.0,
            "gravity_y_world": 0.0,
            "gravity_z_world": -9.81,
            "quality_score": 0.9,
        }
    ).to_csv(path, index=False)
    return path


def test_read_mps_closed_loop_without_cpf(tmp_path: Path) -> None:
    pose = read_mps_closed_loop_trajectory(_closed_loop_csv(tmp_path / "closed_loop_trajectory.csv"))
    assert pose["t_ns"].tolist()[:2] == [10_000_000_000, 10_001_000_000]
    assert "qw" not in pose.columns  # orientation would refer to the Device frame, not the CPF
    _, issues = coerce_table(pose, STREAM_SPECS["pose"])
    assert not issues


def test_read_mps_closed_loop_with_cpf(tmp_path: Path) -> None:
    pose = read_mps_closed_loop_trajectory(_closed_loop_csv(tmp_path / "c.csv"), t_device_cpf=np.eye(4))
    q = pose[["qw", "qx", "qy", "qz"]].to_numpy()
    assert np.allclose(np.abs(q[:, 3]), np.sin(0.25)) and np.allclose(pose["x_m"], np.arange(5))
    assert np.allclose(quat_to_rotmat(q)[0][:2, :2], [[np.cos(0.5), -np.sin(0.5)], [np.sin(0.5), np.cos(0.5)]])


def test_read_mps_eye_gaze_gen2(tmp_path: Path) -> None:
    path = tmp_path / "general_eye_gaze.csv"
    pd.DataFrame(
        {
            "tracking_timestamp_us": [1, 200_001],
            "yaw_rads_cpf": [0.1, np.nan],
            "pitch_rads_cpf": [-0.05, 0.0],
            "left_yaw_rads_cpf": 0.0,
            "right_yaw_rads_cpf": 0.0,
            "left_pitch_rads_cpf": 0.0,
            "right_pitch_rads_cpf": 0.0,
        }
    ).to_csv(path, index=False)
    gaze = read_mps_eye_gaze(path)
    assert gaze["t_ns"].tolist() == [1_000, 200_001_000]
    assert gaze["valid"].tolist() == [True, False]
    with pytest.raises(ValueError):
        pd.DataFrame({"tracking_timestamp_us": [1]}).to_csv(tmp_path / "bad.csv", index=False)
        read_mps_eye_gaze(tmp_path / "bad.csv")


def test_gravity_alignment_maps_gravity_to_minus_z() -> None:
    for g in ([0.0, 0.0, -9.81], [0.0, -9.81, 0.0], [3.0, 1.0, -9.0], [0.0, 0.0, 9.81]):
        r = gravity_alignment(np.array(g))
        assert np.allclose(r @ (np.array(g) / np.linalg.norm(g)), [0, 0, -1], atol=1e-9)
        assert np.allclose(r @ r.T, np.eye(3), atol=1e-9)


def test_timedelta_conversion_and_pose_table() -> None:
    assert timedelta_to_ns(timedelta(microseconds=1_234_567)) == 1_234_567_000
    mats = np.tile(np.eye(4), (2, 1, 1))
    mats[1, :3, 3] = [1.0, 2.0, 3.0]
    pose = poses_to_canonical(np.array([0, 10]), mats)
    assert pose[["x_m", "y_m", "z_m"]].iloc[1].tolist() == [1.0, 2.0, 3.0]
    assert pose["qw"].tolist() == [1.0, 1.0]


@pytest.mark.aria
@pytest.mark.skipif(not projectaria_available(), reason="projectaria-tools not installed (Linux/macOS only)")
def test_projectaria_api_surface() -> None:
    """Every projectaria-tools symbol used by AriaGen2Extractor exists in the installed version."""
    from projectaria_tools.core import data_provider, mps
    from projectaria_tools.core.sensor_data import TimeDomain, TrackingQuality, VioStatus

    assert hasattr(data_provider, "create_vrs_data_provider")
    assert TimeDomain.DEVICE_TIME is not None and VioStatus.VALID is not None and TrackingQuality.GOOD is not None
    provider_cls = data_provider.VrsDataProvider
    for name in (
        "get_stream_id_from_label",
        "get_num_data",
        "get_all_streams",
        "get_label_from_stream_id",
        "get_first_time_ns",
        "get_last_time_ns",
        "get_metadata",
        "get_device_calibration",
        "get_image_data_by_index",
        "get_eye_gaze_data_by_index",
        "get_imu_data_by_index",
        "get_gps_data_by_index",
        "get_vio_data_by_index",
        "get_vio_high_freq_data_by_index",
    ):
        assert hasattr(provider_cls, name), name
    assert hasattr(mps, "EyeGaze") and hasattr(mps, "get_eyegaze_point_at_depth")
