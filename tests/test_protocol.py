"""Counterbalanced ride plans."""

from __future__ import annotations

from pathlib import Path

import pytest

from ariagen_escooter.cli import main
from ariagen_escooter.protocol import ProtocolConfig, load_protocol, plan_rides, vehicle_sequence


def _cfg(**kw) -> ProtocolConfig:
    base = dict(protocol_id="T", participants=["P001", "P002", "P003"], vehicles=["escooter", "bicycle"],
                repetitions_per_vehicle=2, rides_per_session=4, first_vehicle_assignment="alternate",
                seed=None, route_id="CES_A", minimum_pause_min=10)
    base.update(kw)
    return ProtocolConfig.model_validate(base)


def test_sequences() -> None:
    assert vehicle_sequence("A", "B", 1) == ["A", "B"]
    assert vehicle_sequence("A", "B", 2) == ["A", "B", "B", "A"]
    assert vehicle_sequence("A", "B", 3) == ["A", "B", "B", "A", "A", "B"]


def test_two_repetitions_balance_order_within_each_participant() -> None:
    plan = plan_rides(_cfg())
    assert plan.balance["max_within_participant_mean_position_difference"] == 0.0
    assert plan.balance["first_vehicle_counts"] == {"escooter": 2, "bicycle": 1}
    p1 = plan.rides[plan.rides.participant_id == "P001"]
    assert p1["vehicle_type"].tolist() == ["escooter", "bicycle", "bicycle", "escooter"]
    assert p1["trial_number"].tolist() == [1, 1, 2, 2]


def test_one_repetition_reports_imbalance_and_sessions() -> None:
    plan = plan_rides(_cfg(repetitions_per_vehicle=1, rides_per_session=1))
    assert plan.balance["first_vehicle_imbalance"] == 1
    assert plan.balance["sessions_per_participant"] == 2
    assert "not balanced" in plan.balance["note"]


def test_random_assignment_is_reproducible() -> None:
    a = plan_rides(_cfg(first_vehicle_assignment="random", seed=7)).rides
    b = plan_rides(_cfg(first_vehicle_assignment="random", seed=7)).rides
    assert a.equals(b)
    with pytest.raises(ValueError):
        _cfg(first_vehicle_assignment="random", seed=None)


def test_committed_pilot_protocol_and_cli(project_root: Path, tmp_path: Path) -> None:
    cfg = load_protocol(project_root / "configs" / "protocol" / "pilot.yaml")
    assert len(cfg.participants) == 3
    assert main(["plan-rides", str(project_root / "configs" / "protocol" / "pilot.yaml"),
                 "--out", str(tmp_path / "plan.csv")]) == 0
    assert (tmp_path / "plan.csv").read_text(encoding="utf-8").count("\n") == 13
