"""Counterbalanced ride plans for the within-participant vehicle comparison.

The protocol (``configs/protocol/*.yaml``) fixes the participants, the vehicle
types, the number of repetitions per vehicle and how many rides fit in one
session; this module turns it into a ride plan (participant x ride order x
vehicle x trial number x session) and reports how well vehicle order is
balanced.

Schemes
-------
* 1 repetition per vehicle: AB / BA alternating between participants. With an
  odd number of participants perfect balance is impossible (e.g. 2 x AB and
  1 x BA with 3 participants): the imbalance is reported, never hidden.
* 2 repetitions per vehicle: ABBA / BAAB. Each participant's mean ride
  position is the same for both vehicles, so a linear learning or fatigue
  trend is balanced WITHIN every participant, whatever the number of
  participants.
* k > 2 repetitions: ABBA blocks repeated (plus AB for odd k), alternating
  with the complementary sequence.

The plan is a proposal for the field team; deviations (a repeated ride, a
cancelled one) are recorded in the session manifests, which remain the source
of truth for the analysis (``trial.ride_order``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ariagen_escooter.config import ConfigError, read_yaml_mapping
from ariagen_escooter.session import validate_participant_id


class ProtocolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_id: str = Field(min_length=1)
    participants: list[str] = Field(min_length=1)
    vehicles: list[str] = Field(min_length=2, max_length=2)
    repetitions_per_vehicle: int = Field(ge=1, le=6)
    rides_per_session: int = Field(ge=1)
    first_vehicle_assignment: str = Field(pattern=r"^(alternate|random)$")
    seed: int | None = None
    route_id: str
    minimum_pause_min: float = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> ProtocolConfig:
        for p in self.participants:
            validate_participant_id(p)
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("duplicated participant ids")
        if len(set(self.vehicles)) != 2:
            raise ValueError("two distinct vehicle types are required")
        if self.first_vehicle_assignment == "random" and self.seed is None:
            raise ValueError("random assignment needs a seed (reproducible plan)")
        return self


def load_protocol(path: Path) -> ProtocolConfig:
    try:
        return ProtocolConfig.model_validate(read_yaml_mapping(path))
    except ValueError as exc:
        raise ConfigError(f"invalid protocol {path.name}:\n{exc}") from exc


def vehicle_sequence(first: str, second: str, repetitions: int) -> list[str]:
    """Order of rides for one participant starting with ``first``."""
    block = [first, second, second, first]
    seq = block * (repetitions // 2)
    if repetitions % 2:
        seq += [first, second]
    return seq


@dataclass(frozen=True)
class RidePlan:
    rides: pd.DataFrame
    balance: dict[str, object]


def plan_rides(cfg: ProtocolConfig) -> RidePlan:
    """Ride plan and order-balance report for a protocol."""
    a, b = cfg.vehicles
    n = len(cfg.participants)
    if cfg.first_vehicle_assignment == "alternate":
        starts = [a if i % 2 == 0 else b for i in range(n)]
    else:
        pool = [a if i % 2 == 0 else b for i in range(n)]
        random.Random(cfg.seed).shuffle(pool)
        starts = pool
    rows = []
    for participant, first in zip(cfg.participants, starts):
        second = b if first == a else a
        counters = {a: 0, b: 0}
        for order, vehicle in enumerate(vehicle_sequence(first, second, cfg.repetitions_per_vehicle), start=1):
            counters[vehicle] += 1
            rows.append({
                "protocol_id": cfg.protocol_id,
                "participant_id": participant,
                "session_number": (order - 1) // cfg.rides_per_session + 1,
                "ride_order": order,
                "vehicle_type": vehicle,
                "trial_number": counters[vehicle],
                "route_id": cfg.route_id,
                "first_vehicle": first,
            })
    rides = pd.DataFrame(rows)
    starts_count = {v: int(sum(s == v for s in starts)) for v in cfg.vehicles}
    mean_pos = rides.groupby(["participant_id", "vehicle_type"])["ride_order"].mean().unstack()
    within_diff = (mean_pos[a] - mean_pos[b]).abs()
    balance = {
        "participants": n,
        "repetitions_per_vehicle": cfg.repetitions_per_vehicle,
        "first_vehicle_counts": starts_count,
        "first_vehicle_imbalance": abs(starts_count[a] - starts_count[b]),
        "max_within_participant_mean_position_difference": float(within_diff.max()),
        "mean_position_by_vehicle": {v: float(rides.loc[rides.vehicle_type == v, "ride_order"].mean())
                                     for v in cfg.vehicles},
        "sessions_per_participant": int(rides["session_number"].max()),
        "note": ("order balanced within each participant (ABBA)" if within_diff.max() == 0 else
                 "vehicle order not balanced within participants: model ride order / trial number as covariates"),
    }
    return RidePlan(rides, balance)
