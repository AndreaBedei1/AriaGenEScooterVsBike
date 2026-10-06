"""Project Aria Gen 2 adapter: VRS (+ MPS outputs) -> canonical streams.

Requirements (verified on the official docs/PyPI, 2026-10): projectaria-tools
>= 2.3.0, which publishes wheels only for Linux (x86_64, aarch64) and macOS
arm64, CPython 3.10-3.12. There is NO Gen 2 support on Windows: run the
extraction on the Linux machine (``pip install -e ".[aria]"``).

STATUS
------
* The pure-pandas MPS readers below are tested with small fixtures that follow
  the documented column names.
* :class:`AriaGen2Extractor` follows the official projectaria-tools 2.3.0 Gen 2
  tutorials and Python bindings, but has NOT yet been run on a real Gen 2
  recording. Verify it on the first pilot VRS before trusting its output
  (``ariagen-escooter extract-aria`` writes an inventory to help).

Conventions (official docs): streams are resolved by label; timestamps use
``TimeDomain.DEVICE_TIME`` (ns); eye gaze is reported in the CPF frame
(x left, y up, z forward; +yaw = left); on Gen 2 the default CPF is SVD-based
since projectaria-tools 2.3.0, so gaze projections made with older versions
are not comparable.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ariagen_escooter.config import AriaConfig
from ariagen_escooter.gaze import quat_to_rotmat, rotmat_to_quat

# Gen 2 labels (official StreamId <-> label mapping). Ids differ from Gen 1!
GEN2_STREAM_LABELS = {
    "camera-rgb": "RGB camera (214-1)",
    "slam-front-left": "CV camera (1201-1)",
    "slam-front-right": "CV camera (1201-2)",
    "slam-side-left": "CV camera (1201-3)",
    "slam-side-right": "CV camera (1201-4)",
    "camera-et-left": "eye-tracking camera (211-1)",
    "camera-et-right": "eye-tracking camera (211-2)",
    "imu-left": "IMU (1202-1)",
    "imu-right": "IMU (1202-2)",
    "mag0": "magnetometer (1203-1)",
    "baro0": "barometer (247-1)",
    "gps": "glasses GNSS (281-2)",
    "gps-app": "companion-app GNSS (281-1)",
    "mic": "microphones incl. contact mic (231-1)",
    "ppg": "PPG (248-1)",
    "als": "ambient light (500-1)",
    "temperature": "device temperature (246-1)",
    "eyegaze": "on-device eye gaze (373-1)",
    "handtracking": "on-device hand tracking (371-x)",
    "vio": "on-device VIO, FrontendOutput (371-x)",
    "vio_high_frequency": "on-device VIO high frequency (371-x)",
}

INSTALL_HINT = (
    "projectaria-tools >= 2.3.0 is required. It is available only on Linux "
    "(x86_64/aarch64) and macOS arm64 with Python 3.10-3.12: on the Linux "
    "machine run  pip install -e '.[aria]'  (or ./setup_linux.sh --extras aria)."
)


def projectaria_available() -> bool:
    try:
        import projectaria_tools  # noqa: F401
    except ImportError:
        return False
    return True


def timedelta_to_ns(value: timedelta) -> int:
    """Official conversion of EyeGaze/MPS ``tracking_timestamp`` (microsecond timedelta)."""
    return (value // timedelta(microseconds=1)) * 1000


def gravity_alignment(gravity: np.ndarray) -> np.ndarray:
    """Rotation mapping the measured gravity direction onto -z (world z up)."""
    a = np.asarray(gravity, dtype=np.float64)
    a = a / np.linalg.norm(a)
    b = np.array([0.0, 0.0, -1.0])
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.isclose(c, -1.0):  # gravity along +z: rotate 180 deg about x
        return np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1.0 + c)


def poses_to_canonical(t_ns: np.ndarray, t_world_cpf: np.ndarray, quality: np.ndarray | None = None) -> pd.DataFrame:
    """(N, 4, 4) world <- CPF transforms -> canonical pose table."""
    t_world_cpf = np.asarray(t_world_cpf, dtype=np.float64)
    quat = rotmat_to_quat(t_world_cpf[:, :3, :3])
    data = {
        "t_ns": np.asarray(t_ns, dtype=np.int64),
        "x_m": t_world_cpf[:, 0, 3],
        "y_m": t_world_cpf[:, 1, 3],
        "z_m": t_world_cpf[:, 2, 3],
        "qw": quat[:, 0],
        "qx": quat[:, 1],
        "qy": quat[:, 2],
        "qz": quat[:, 3],
    }
    if quality is not None:
        data["quality"] = np.asarray(quality, dtype=np.float64)
    return pd.DataFrame(data)


# --------------------------------------------------------------------------- #
# MPS readers (pure pandas - tested with fixtures following the documented columns)
# --------------------------------------------------------------------------- #
MPS_CLOSED_LOOP_COLUMNS = (
    "tracking_timestamp_us",
    "tx_world_device",
    "ty_world_device",
    "tz_world_device",
    "qx_world_device",
    "qy_world_device",
    "qz_world_device",
    "qw_world_device",
)
MPS_EYE_GAZE_GEN2_COLUMNS = ("tracking_timestamp_us", "yaw_rads_cpf", "pitch_rads_cpf")


def read_mps_closed_loop_trajectory(path: Path, t_device_cpf: np.ndarray | None = None) -> pd.DataFrame:
    """MPS ``closed_loop_trajectory.csv`` -> canonical pose.

    The MPS world frame is gravity aligned with +z up (gravity_world = [0, 0, -9.81]).
    Without ``t_device_cpf`` (4x4, from the device calibration) the orientation
    refers to the Device frame, not the CPF, so quaternion columns are omitted.
    """
    df = pd.read_csv(path)
    missing = [c for c in MPS_CLOSED_LOOP_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing MPS columns {missing}")
    t_ns = df["tracking_timestamp_us"].to_numpy(dtype=np.int64) * 1000
    quality = df["quality_score"].to_numpy() if "quality_score" in df.columns else None
    if t_device_cpf is None:
        out = pd.DataFrame(
            {
                "t_ns": t_ns,
                "x_m": df["tx_world_device"].to_numpy(),
                "y_m": df["ty_world_device"].to_numpy(),
                "z_m": df["tz_world_device"].to_numpy(),
            }
        )
        if quality is not None:
            out["quality"] = quality
        return out
    q = df[["qw_world_device", "qx_world_device", "qy_world_device", "qz_world_device"]].to_numpy()
    t_world_device = np.tile(np.eye(4), (len(df), 1, 1))
    t_world_device[:, :3, :3] = quat_to_rotmat(q)
    t_world_device[:, :3, 3] = df[["tx_world_device", "ty_world_device", "tz_world_device"]].to_numpy()
    return poses_to_canonical(t_ns, t_world_device @ np.asarray(t_device_cpf, dtype=np.float64), quality)


def read_mps_eye_gaze(path: Path) -> pd.DataFrame:
    """MPS eye-gaze CSV (Gen 2 columns) -> canonical gaze without image projection.

    Gen 2 MPS gaze has one sample per eye-tracking camera frame (5 Hz with the
    standard profiles), versus 30 Hz for on-device gaze.
    """
    df = pd.read_csv(path)
    missing = [c for c in MPS_EYE_GAZE_GEN2_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing MPS eye-gaze columns {missing}")
    yaw = df["yaw_rads_cpf"].to_numpy(dtype=np.float64)
    pitch = df["pitch_rads_cpf"].to_numpy(dtype=np.float64)
    return pd.DataFrame(
        {
            "t_ns": df["tracking_timestamp_us"].to_numpy(dtype=np.int64) * 1000,
            "valid": np.isfinite(yaw) & np.isfinite(pitch),
            "yaw_rad": yaw,
            "pitch_rad": pitch,
        }
    )


# --------------------------------------------------------------------------- #
# VRS extraction (projectaria-tools; NOT yet validated on a real Gen 2 VRS)
# --------------------------------------------------------------------------- #
class AriaGen2Extractor:  # pragma: no cover - requires projectaria-tools and a VRS file
    """Extract canonical streams from one Aria Gen 2 VRS file."""

    def __init__(self, vrs_path: Path, cfg: AriaConfig):
        try:
            from projectaria_tools.core import data_provider
        except ImportError as exc:
            raise ImportError(INSTALL_HINT) from exc
        self.cfg = cfg
        self.vrs_path = Path(vrs_path)
        self.provider = data_provider.create_vrs_data_provider(str(self.vrs_path))
        if self.provider is None:
            raise ValueError(f"cannot open VRS file {self.vrs_path.name}")
        self.calibration = self.provider.get_device_calibration()
        self.t_device_cpf = np.asarray(self.calibration.get_transform_device_cpf().to_matrix())

    # -- discovery -------------------------------------------------------------------
    def stream_id(self, label: str) -> Any | None:
        """Stream id for a label, or None if absent (Gen 2 maps labels statically,
        so the number of samples is checked as in the official tutorial)."""
        sid = self.provider.get_stream_id_from_label(label)
        if sid is None or self.provider.get_num_data(sid) == 0:
            return None
        return sid

    def inventory(self) -> pd.DataFrame:
        from projectaria_tools.core.sensor_data import TimeDomain

        rows = []
        for sid in self.provider.get_all_streams():
            n = self.provider.get_num_data(sid)
            first = self.provider.get_first_time_ns(sid, TimeDomain.DEVICE_TIME) if n else None
            last = self.provider.get_last_time_ns(sid, TimeDomain.DEVICE_TIME) if n else None
            rate = (n - 1) / ((last - first) / 1e9) if n > 1 and last and first and last > first else None
            rows.append(
                {
                    "stream_id": str(sid),
                    "label": self.provider.get_label_from_stream_id(sid),
                    "n_samples": n,
                    "first_device_ns": first,
                    "last_device_ns": last,
                    "mean_rate_hz": rate,
                }
            )
        return pd.DataFrame(rows)

    def metadata(self) -> dict[str, object]:
        meta = self.provider.get_metadata()
        return {
            "recording_profile": getattr(meta, "recording_profile", None),
            "duration_sec": getattr(meta, "duration_sec", None),
            "time_sync_mode": str(getattr(meta, "time_sync_mode", "")),
        }

    # -- streams -----------------------------------------------------------------------
    def frames(self) -> pd.DataFrame | None:
        sid = self.stream_id(self.cfg.rgb_label)
        if sid is None:
            return None
        width, height = (int(x) for x in self.calibration.get_camera_calib(self.cfg.rgb_label).get_image_size())
        times = []
        for i in range(self.provider.get_num_data(sid)):
            _, record = self.provider.get_image_data_by_index(sid, i)
            times.append(int(record.capture_timestamp_ns))
        return pd.DataFrame(
            {"t_ns": times, "frame_index": np.arange(len(times)), "width_px": width, "height_px": height}
        )

    def iter_rgb_frames(self, every_n: int = 1) -> Iterator[tuple[int, np.ndarray]]:
        """Yield (frame_index, RGB array) without writing identifiable frames to disk."""
        sid = self.stream_id(self.cfg.rgb_label)
        if sid is None:
            return
        for i in range(0, self.provider.get_num_data(sid), every_n):
            image, _ = self.provider.get_image_data_by_index(sid, i)
            yield i, image.to_numpy_array()

    def eye_gaze(self) -> pd.DataFrame | None:
        sid = self.stream_id(self.cfg.eye_gaze_label)
        if sid is None:
            return None
        camera = self.calibration.get_camera_calib(self.cfg.rgb_label)
        t_camera_device = np.linalg.inv(np.asarray(camera.get_transform_device_camera().to_matrix()))
        t_camera_cpf = t_camera_device @ self.t_device_cpf
        rows = []
        for i in range(self.provider.get_num_data(sid)):
            eg = self.provider.get_eye_gaze_data_by_index(sid, i)
            yaw, pitch = float(eg.yaw), float(eg.pitch)
            valid = bool(eg.combined_gaze_valid) and np.isfinite(yaw) and np.isfinite(pitch)
            u = v = np.nan
            if valid:
                if self.cfg.gaze_projection == "spatial_point_if_valid" and bool(eg.spatial_gaze_point_valid):
                    p_cpf = np.asarray(eg.spatial_gaze_point_in_cpf, dtype=np.float64).reshape(3)
                else:
                    d = np.array([np.tan(yaw), np.tan(pitch), 1.0])
                    p_cpf = self.cfg.gaze_fallback_depth_m * d / np.linalg.norm(d)
                p_cam = (t_camera_cpf @ np.r_[p_cpf, 1.0])[:3]
                uv = camera.project(p_cam)
                if uv is not None:
                    u, v = float(uv[0]), float(uv[1])
            depth = float(eg.depth)
            rows.append(
                {
                    "t_ns": timedelta_to_ns(eg.tracking_timestamp),
                    "valid": valid,
                    "yaw_rad": yaw if valid else np.nan,
                    "pitch_rad": pitch if valid else np.nan,
                    "u_px": u,
                    "v_px": v,
                    "depth_m": depth if depth > 0 else np.nan,
                }
            )
        return pd.DataFrame(rows)

    def imu(self) -> pd.DataFrame | None:
        sid = self.stream_id(self.cfg.imu_label)
        if sid is None:
            return None
        imu_calib = self.calibration.get_imu_calib(self.cfg.imu_label)
        t, acc, gyr = [], [], []
        for i in range(self.provider.get_num_data(sid)):
            m = self.provider.get_imu_data_by_index(sid, i)
            t.append(int(m.capture_timestamp_ns))
            acc.append(np.asarray(imu_calib.raw_to_rectified_accel(np.asarray(m.accel_msec2))))
            gyr.append(np.asarray(imu_calib.raw_to_rectified_gyro(np.asarray(m.gyro_radsec))))
        t_arr, acc_arr, gyr_arr = np.asarray(t, dtype=np.int64), np.asarray(acc), np.asarray(gyr)
        rate = (len(t_arr) - 1) / ((t_arr[-1] - t_arr[0]) / 1e9) if len(t_arr) > 1 else self.cfg.imu_rate_hz
        k = max(1, int(round(rate / self.cfg.imu_rate_hz)))
        n = (len(t_arr) // k) * k
        block = lambda a: a[:n].reshape(-1, k, *a.shape[1:]).mean(axis=1)  # noqa: E731 - simple low-pass + decimation
        t_out = t_arr[:n].reshape(-1, k).mean(axis=1).round().astype(np.int64)
        acc_out, gyr_out = block(acc_arr), block(gyr_arr)
        return pd.DataFrame(
            {
                "t_ns": t_out,
                "accel_x_mps2": acc_out[:, 0],
                "accel_y_mps2": acc_out[:, 1],
                "accel_z_mps2": acc_out[:, 2],
                "gyro_x_radps": gyr_out[:, 0],
                "gyro_y_radps": gyr_out[:, 1],
                "gyro_z_radps": gyr_out[:, 2],
            }
        )

    def gps(self) -> tuple[pd.DataFrame | None, str | None]:
        for label in self.cfg.gps_labels:
            sid = self.stream_id(label)
            if sid is None:
                continue
            rows = []
            for i in range(self.provider.get_num_data(sid)):
                g = self.provider.get_gps_data_by_index(sid, i)
                lat, lon = float(g.latitude), float(g.longitude)
                if not (np.isfinite(lat) and np.isfinite(lon)) or (lat == 0.0 and lon == 0.0):
                    continue
                rows.append(
                    {
                        "t_ns": int(g.capture_timestamp_ns),
                        "lat_deg": lat,
                        "lon_deg": lon,
                        "alt_m": float(g.altitude),
                        "accuracy_m": float(g.accuracy),
                        "speed_mps": float(g.speed),
                    }
                )
            if rows:
                return pd.DataFrame(rows), label
        return None, None

    def pose(self, mps_dir: Path | None = None) -> pd.DataFrame | None:
        source = self.cfg.pose_source
        if source == "mps_closed_loop":
            if mps_dir is None:
                raise ValueError("pose_source mps_closed_loop requires the MPS output folder")
            return read_mps_closed_loop_trajectory(mps_dir / "slam" / "closed_loop_trajectory.csv", self.t_device_cpf)
        from projectaria_tools.core.sensor_data import TrackingQuality, VioStatus

        if source == "vio":
            sid = self.stream_id("vio")
            if sid is None:
                return None
            t, mats, gravity = [], [], None
            for i in range(self.provider.get_num_data(sid)):
                f = self.provider.get_vio_data_by_index(sid, i)
                if f.status != VioStatus.VALID or f.pose_quality != TrackingQuality.GOOD:
                    continue
                t_odo_device = (f.transform_odometry_bodyimu @ f.transform_bodyimu_device).to_matrix()
                t.append(int(f.capture_timestamp_ns))
                mats.append(np.asarray(t_odo_device) @ self.t_device_cpf)
                if gravity is None:
                    gravity = np.asarray(f.gravity_in_odometry, dtype=np.float64)
            quality = None
        else:
            sid = self.stream_id("vio_high_frequency")
            if sid is None:
                return None
            n = self.provider.get_num_data(sid)
            first = self.provider.get_vio_high_freq_data_by_index(sid, 0)
            t_first = timedelta_to_ns(first.tracking_timestamp)
            t_last = timedelta_to_ns(self.provider.get_vio_high_freq_data_by_index(sid, n - 1).tracking_timestamp)
            rate = (n - 1) / ((t_last - t_first) / 1e9) if n > 1 and t_last > t_first else self.cfg.pose_rate_hz
            step = max(1, int(round(rate / self.cfg.pose_rate_hz)))
            t, mats, q, gravity = [], [], [], None
            for i in range(0, n, step):
                p = self.provider.get_vio_high_freq_data_by_index(sid, i)
                t.append(timedelta_to_ns(p.tracking_timestamp))
                mats.append(np.asarray(p.transform_odometry_device.to_matrix()) @ self.t_device_cpf)
                q.append(float(p.quality_score))
                if gravity is None:
                    gravity = np.asarray(p.gravity_odometry, dtype=np.float64)
            quality = np.asarray(q)
        if not t:
            return None
        align = np.eye(4)
        align[:3, :3] = gravity_alignment(gravity if gravity is not None else np.array([0.0, 0.0, -1.0]))
        return poses_to_canonical(np.asarray(t), align @ np.asarray(mats), quality)

    def sensor_extrinsics(self) -> dict[str, list[list[float]]]:
        """Transforms needed later (device <- CPF, device <- IMU, device <- RGB camera)."""
        out = {"T_device_cpf": self.t_device_cpf.tolist()}
        try:
            out["T_device_imu"] = np.asarray(
                self.calibration.get_transform_device_sensor(self.cfg.imu_label).to_matrix()
            ).tolist()
        except Exception:  # noqa: BLE001 - optional information
            pass
        camera = self.calibration.get_camera_calib(self.cfg.rgb_label)
        out["T_device_rgb"] = np.asarray(camera.get_transform_device_camera().to_matrix()).tolist()
        return out
