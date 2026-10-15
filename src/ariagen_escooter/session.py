"""Pseudonymous identifiers, session manifests and on-disk session layout.

Identifier convention (see README "Naming conventions")::

    participant  P001            (synthetic data: SYN001)
    session      P001_S01        (participant + session number)
    recording    P001_S01_R01    (session + recording number)

Identifiers are pseudonyms. The key linking a pseudonym to a real person is
kept by the study team OUTSIDE this repository and outside the data folders
(see docs/privacy_pipeline.md); no name, e-mail or phone number is ever stored
in a manifest.

Manifest versions
-----------------
* ``manifest_version: 1`` - original e-scooter-only format (one vehicle,
  ``equipment.escooter_code``); still accepted: every recording is read as
  an e-scooter ride, trial 1.
* ``manifest_version: 2`` - two-vehicle study: every recording declares a
  ``trial`` (vehicle type, vehicle unit, repetition number, overall ride
  order) and ``equipment.vehicles`` lists the vehicle units used. A
  participant can have several sessions (days), each with rides on one or
  both vehicles; the identity of every repetition is kept in the ids.

Layout of a session directory (raw or self-contained synthetic)::

    <session_dir>/manifest.yaml
    <session_dir>/<recording_id>/recording.vrs        (raw Aria data, if any)
    <session_dir>/<recording_id>/streams/*.csv        (canonical streams)
    <session_dir>/<recording_id>/annotations/*.csv    (segments, events)
    <session_dir>/<recording_id>/semantic/labels.npz  (label maps)

For real data the canonical streams/annotations normally live under
``<data_root>/interim/<session_id>/<recording_id>/`` instead; both locations
are searched (session directory first).
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ariagen_escooter.config import ConfigError, read_yaml_mapping

PARTICIPANT_RE = re.compile(r"^(?P<prefix>P|SYN)(?P<num>\d{3})$")
SESSION_RE = re.compile(r"^(?P<participant>(?:P|SYN)\d{3})_S(?P<num>\d{2})$")
RECORDING_RE = re.compile(r"^(?P<session>(?:P|SYN)\d{3}_S\d{2})_R(?P<num>\d{2})$")

MANIFEST_FILENAME = "manifest.yaml"
STREAM_KEYS = (
    "rgb",
    "eye_gaze",
    "imu",
    "pose",
    "pose_high_frequency",
    "hand_tracking",
    "gps_device",
    "gps_phone",
    "gps_external",
    "ppg",
    "mps_slam",
    "mps_eye_gaze",
    "mps_hand_tracking",
)
VEHICLE_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# --------------------------------------------------------------------------- #
# Identifiers
# --------------------------------------------------------------------------- #
def make_participant_id(number: int, synthetic: bool = False) -> str:
    if not 1 <= number <= 999:
        raise ValueError("participant number must be in 1..999")
    return f"{'SYN' if synthetic else 'P'}{number:03d}"


def make_session_id(participant_id: str, number: int) -> str:
    validate_participant_id(participant_id)
    if not 1 <= number <= 99:
        raise ValueError("session number must be in 1..99")
    return f"{participant_id}_S{number:02d}"


def make_recording_id(session_id: str, number: int) -> str:
    validate_session_id(session_id)
    if not 1 <= number <= 99:
        raise ValueError("recording number must be in 1..99")
    return f"{session_id}_R{number:02d}"


def validate_participant_id(value: str) -> str:
    if not PARTICIPANT_RE.match(value):
        raise ValueError(f"invalid participant id {value!r} (expected P001..P999 or SYN001..SYN999)")
    return value


def validate_session_id(value: str) -> str:
    if not SESSION_RE.match(value):
        raise ValueError(f"invalid session id {value!r} (expected e.g. P001_S01)")
    return value


def validate_recording_id(value: str) -> str:
    if not RECORDING_RE.match(value):
        raise ValueError(f"invalid recording id {value!r} (expected e.g. P001_S01_R01)")
    return value


def participant_of(session_or_recording_id: str) -> str:
    match = re.match(r"^((?:P|SYN)\d{3})_", session_or_recording_id)
    if not match:
        raise ValueError(f"cannot extract participant from {session_or_recording_id!r}")
    return match.group(1)


def is_synthetic_id(identifier: str) -> bool:
    return identifier.startswith("SYN")


def next_participant_id(existing: Iterable[str], synthetic: bool = False) -> str:
    """Next free pseudonymous id (max existing number + 1). Never reuses numbers."""
    prefix = "SYN" if synthetic else "P"
    numbers = [
        int(m.group("num")) for m in (PARTICIPANT_RE.match(x) for x in existing) if m and m.group("prefix") == prefix
    ]
    return make_participant_id(max(numbers, default=0) + 1, synthetic)


# --------------------------------------------------------------------------- #
# Manifest models
# --------------------------------------------------------------------------- #
class StreamStatus(str, Enum):
    available = "available"
    partial = "partial"
    missing = "missing"
    unknown = "unknown"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TechnicalIssue(_Model):
    description: str = Field(min_length=3)
    severity: Literal["info", "minor", "major", "blocking"]
    streams: list[str] = Field(default_factory=list)


class TrimmingOverride(_Model):
    """Manual riding interval, seconds relative to the first sample of the recording."""

    start_rel_s: float = Field(ge=0)
    end_rel_s: float = Field(gt=0)
    reason: str = Field(min_length=3)
    decided_by: str = Field(min_length=1, description="Staff code/role, not a full name.")

    @model_validator(mode="after")
    def _ordered(self) -> TrimmingOverride:
        if self.end_rel_s <= self.start_rel_s:
            raise ValueError("end_rel_s must be > start_rel_s")
        return self


class RecordingFiles(_Model):
    """Paths relative to the recording directory ('/'-separated, never absolute)."""

    vrs: str | None = None
    mps_dir: str | None = None
    external_gps: str | None = None


class ClockInfo(_Model):
    external_gps_offset_ns: int | None = None
    method: str | None = None
    uncertainty_s: float | None = Field(default=None, ge=0)


class RecordingEntry(_Model):
    recording_id: str
    trial: TrialInfo | None = None
    files: RecordingFiles = Field(default_factory=RecordingFiles)
    streams: dict[str, StreamStatus]
    clock: ClockInfo = Field(default_factory=ClockInfo)
    device_time_start_ns: int | None = None
    device_time_end_ns: int | None = None
    trimming_override: TrimmingOverride | None = None
    notes: str = ""
    technical_issues: list[TechnicalIssue] = Field(default_factory=list)

    @field_validator("recording_id")
    @classmethod
    def _rid(cls, value: str) -> str:
        return validate_recording_id(value)

    @field_validator("streams")
    @classmethod
    def _stream_keys(cls, value: dict[str, StreamStatus]) -> dict[str, StreamStatus]:
        unknown = sorted(set(value) - set(STREAM_KEYS))
        if unknown:
            raise ValueError(f"unknown stream keys {unknown}; allowed: {list(STREAM_KEYS)}")
        return value


class RouteInfo(_Model):
    route_id: str = Field(min_length=1)
    variant: str | None = None
    description: str = ""


class Timing(_Model):
    date: dt.date | None = None
    start_time_local: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str | None = None


class Conditions(_Model):
    weather: Literal["dry", "drizzle", "rain", "fog", "snow", "unknown"] = "unknown"
    road_surface: Literal["dry", "wet", "mixed", "unknown"] = "unknown"
    light: Literal["daylight", "twilight", "dark", "unknown"] = "unknown"
    traffic_density: Literal["low", "medium", "high", "unknown"] = "unknown"
    temperature_c: float | None = None
    notes: str = ""


class VehicleUnit(_Model):
    """One physical vehicle used in a session (internal code, never a plate/serial number)."""

    vehicle_code: str = Field(min_length=1)
    vehicle_type: str = Field(description="Key of configs/vehicles.yaml, e.g. escooter, bicycle.")
    model: str | None = None
    # Measured or declared characteristics, units in the key names (e.g.
    # wheel_diameter_in, mass_kg, motor_power_w, max_speed_kmh, brakes, frame_size).
    characteristics: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    notes: str = ""

    @field_validator("vehicle_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if not VEHICLE_TYPE_RE.match(value):
            raise ValueError(f"vehicle_type {value!r} must be snake_case")
        return value


class Equipment(_Model):
    aria_device_code: str | None = None
    recording_profile: str | None = None
    # manifest_version 1 only (e-scooter-only study):
    escooter_code: str | None = None
    escooter_model: str | None = None
    # manifest_version 2: vehicle units used in this session
    vehicles: list[VehicleUnit] = Field(default_factory=list)
    external_gps_logger: str | None = None


class TrialInfo(_Model):
    """Which ride of the protocol a recording belongs to (manifest_version 2).

    ``trial_number`` counts repetitions of the same vehicle type for the
    participant (1, 2, ...); ``ride_order`` is the position of this ride in
    the participant's whole protocol (1 = first ride of the study, across
    sessions and vehicles) and supports order/learning analyses. A trial that
    had to be restarted is split over several recordings with the same trial
    and increasing ``part``.
    """

    vehicle_type: str
    vehicle_code: str | None = None
    trial_number: int = Field(ge=1)
    ride_order: int = Field(ge=1)
    part: int = Field(default=1, ge=1)
    route_id: str | None = Field(default=None, description="Overrides the session route for this ride.")
    route_direction: str | None = None
    rider_reported_issues: str = ""

    @field_validator("vehicle_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if not VEHICLE_TYPE_RE.match(value):
            raise ValueError(f"vehicle_type {value!r} must be snake_case")
        return value


class SessionManifest(_Model):
    manifest_version: Literal[1, 2]
    synthetic: bool
    participant_id: str
    session_id: str
    protocol_version: str = Field(min_length=1)
    route: RouteInfo
    timing: Timing = Field(default_factory=Timing)
    conditions: Conditions = Field(default_factory=Conditions)
    equipment: Equipment = Field(default_factory=Equipment)
    recordings: list[RecordingEntry] = Field(min_length=1)
    notes: str = ""
    technical_issues: list[TechnicalIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ids_consistent(self) -> SessionManifest:
        validate_participant_id(self.participant_id)
        validate_session_id(self.session_id)
        if participant_of(self.session_id) != self.participant_id:
            raise ValueError("session_id does not belong to participant_id")
        if self.synthetic != is_synthetic_id(self.participant_id):
            raise ValueError("synthetic data must use SYN ids and real data P ids")
        seen: set[str] = set()
        for rec in self.recordings:
            if not rec.recording_id.startswith(self.session_id + "_"):
                raise ValueError(f"recording {rec.recording_id} does not belong to {self.session_id}")
            if rec.recording_id in seen:
                raise ValueError(f"duplicated recording id {rec.recording_id}")
            seen.add(rec.recording_id)
        if self.manifest_version == 1:
            if any(rec.trial is not None for rec in self.recordings) or self.equipment.vehicles:
                raise ValueError("trial/vehicles require manifest_version 2")
            return self
        # manifest_version 2
        if self.equipment.escooter_code or self.equipment.escooter_model:
            raise ValueError("manifest_version 2 lists vehicles in equipment.vehicles (escooter_code is v1 only)")
        units = {v.vehicle_code: v for v in self.equipment.vehicles}
        if len(units) != len(self.equipment.vehicles):
            raise ValueError("duplicated vehicle_code in equipment.vehicles")
        keys: set[tuple[str, int, int]] = set()
        for rec in self.recordings:
            if rec.trial is None:
                raise ValueError(f"{rec.recording_id}: manifest_version 2 requires a trial block")
            t = rec.trial
            if t.vehicle_code is not None:
                unit = units.get(t.vehicle_code)
                if unit is None:
                    raise ValueError(f"{rec.recording_id}: vehicle_code {t.vehicle_code!r} not in equipment.vehicles")
                if unit.vehicle_type != t.vehicle_type:
                    raise ValueError(f"{rec.recording_id}: vehicle_code {t.vehicle_code!r} is a {unit.vehicle_type}")
            key = (t.vehicle_type, t.trial_number, t.part)
            if key in keys:
                raise ValueError(f"{rec.recording_id}: duplicated trial {key} (use part=2 for a restarted trial)")
            keys.add(key)
        return self

    def trial_of(self, recording_id: str) -> TrialInfo:
        """Trial of a recording; version-1 manifests are e-scooter rides, trial 1."""
        rec = self.recording(recording_id)
        if rec.trial is not None:
            return rec.trial
        return TrialInfo(vehicle_type="escooter", vehicle_code=self.equipment.escooter_code, trial_number=1,
                         ride_order=1, part=1 + self.recordings.index(rec))

    def recording(self, recording_id: str) -> RecordingEntry:
        for rec in self.recordings:
            if rec.recording_id == recording_id:
                return rec
        raise KeyError(recording_id)


def load_manifest(path: Path) -> SessionManifest:
    """Load and validate a session manifest (``manifest.yaml``)."""
    data = read_yaml_mapping(path)
    try:
        return SessionManifest.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid manifest {path.name}:\n{exc}") from exc


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RecordingLocation:
    """Where the canonical files of one recording live."""

    recording_id: str
    raw_dir: Path
    work_dir: Path

    @property
    def streams_dir(self) -> Path:
        return self.work_dir / "streams"

    @property
    def annotations_dir(self) -> Path:
        return self.work_dir / "annotations"

    @property
    def semantic_dir(self) -> Path:
        return self.work_dir / "semantic"


def locate_recording(session_dir: Path, session_id: str, recording_id: str, data_root: Path) -> RecordingLocation:
    """Self-contained session dir first, then ``<data_root>/interim/<session>/<recording>``."""
    raw_dir = session_dir / recording_id
    if (raw_dir / "streams").is_dir():
        return RecordingLocation(recording_id, raw_dir, raw_dir)
    return RecordingLocation(recording_id, raw_dir, data_root / "interim" / session_id / recording_id)


def manifest_template(
    participant_id: str,
    session_number: int,
    n_recordings: int = 1,
    rides: list[tuple[str, int, int]] | None = None,
) -> dict:
    """Manifest skeleton (version 2) for a new real session, to be completed by the researcher.

    ``rides`` lists ``(vehicle_type, trial_number, ride_order)`` per recording;
    by default ``n_recordings`` placeholder rides are created with vehicle
    type ``TBD`` that ``validate`` will reject until it is filled in.
    """
    session_id = make_session_id(participant_id, session_number)
    if rides is None:
        rides = [("tbd", r, r) for r in range(1, n_recordings + 1)]
    recordings = []
    for r, (vehicle_type, trial_number, ride_order) in enumerate(rides, start=1):
        recordings.append(
            {
                "recording_id": make_recording_id(session_id, r),
                "trial": {
                    "vehicle_type": vehicle_type,
                    "vehicle_code": None,
                    "trial_number": trial_number,
                    "ride_order": ride_order,
                    "part": 1,
                    "route_id": None,
                    "route_direction": None,
                    "rider_reported_issues": "",
                },
                "files": {"vrs": "recording.vrs", "mps_dir": None, "external_gps": None},
                "streams": {key: "unknown" for key in STREAM_KEYS},
                "clock": {"external_gps_offset_ns": None, "method": None, "uncertainty_s": None},
                "trimming_override": None,
                "notes": "",
                "technical_issues": [],
            }
        )
    return {
        "manifest_version": 2,
        "synthetic": False,
        "participant_id": participant_id,
        "session_id": session_id,
        "protocol_version": "TBD",
        "route": {"route_id": "TBD", "variant": None, "description": ""},
        "timing": {"date": None, "start_time_local": None, "timezone": None},
        "conditions": {
            "weather": "unknown",
            "road_surface": "unknown",
            "light": "unknown",
            "traffic_density": "unknown",
            "temperature_c": None,
            "notes": "",
        },
        "equipment": {
            "aria_device_code": None,
            "recording_profile": None,
            "vehicles": [],
            "external_gps_logger": None,
        },
        "recordings": recordings,
        "notes": "",
        "technical_issues": [],
    }
