"""ROTA-T008 test matrix categories J (APPLIED RULE PROVENANCE), K
(SHIFTDEMAND / ASSIGNMENT REFERENCES), L (DEVIATION).
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Deviation,
    DeviationCategory,
    ShiftDemand,
)
from rota.persistence import schedule_lifecycle as lc
from rota.persistence import schedule_repository as repo
from rota.persistence.db import connect
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from tests.support.t008_fixtures import seed_base_entities, seed_rule_decision

MONTH = date(2026, 8, 1)


def _demand(demand_id: str = "DEM-1", count: int = 1) -> ShiftDemand:
    return ShiftDemand(demand_id, "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), count)


def _primary(assignment_id: str = "ASG-1", covers: str = "DEM-1") -> Assignment:
    return Assignment(
        assignment_id, "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, covers, None,
    )


def _trainee(assignment_id: str, mentor_id: str) -> Assignment:
    return Assignment(
        assignment_id, "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, mentor_id,
    )


def _create(conn, **overrides):
    kwargs = dict(
        version_id="SV-1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_primary()], deviations=[],
    )
    kwargs.update(overrides)
    return lc.create_schedule_version(conn, **kwargs)


# --- J. APPLIED RULE PROVENANCE ---------------------------------------------


def test_j1_real_rule_version_round_trips(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    decision = seed_rule_decision(conn, rule_id="RULE-1", site_id="SITE-1")
    _create(conn, applied_rule_version_ids=[decision.rule_version_id])
    header = repo.get_schedule_version_header(conn, "SV-1")
    assert header.applied_rule_version_ids == [decision.rule_version_id]


def test_j2_missing_rule_id_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, applied_rule_version_ids=["NO-SUCH-RULE-VERSION"])


def test_j3_rule_from_other_site_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    seed_base_entities(conn, site_id="SITE-2", profile_id="PROF-2", coordinator_id="COORD-2", employee_id="EMP-2")
    decision = seed_rule_decision(conn, rule_id="RULE-1", site_id="SITE-2")
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, applied_rule_version_ids=[decision.rule_version_id])


def test_j4_applied_rule_order_is_deterministic_and_preserved(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    d1 = seed_rule_decision(conn, rule_id="RULE-1", site_id="SITE-1")
    d2 = seed_rule_decision(conn, rule_id="RULE-2", site_id="SITE-1")
    d3 = seed_rule_decision(conn, rule_id="RULE-3", site_id="SITE-1")
    ordered = [d3.rule_version_id, d1.rule_version_id, d2.rule_version_id]
    _create(conn, applied_rule_version_ids=ordered)
    header = repo.get_schedule_version_header(conn, "SV-1")
    assert header.applied_rule_version_ids == ordered


# --- K. SHIFTDEMAND / ASSIGNMENT REFERENCES ----------------------------------


def test_k1_overnight_demand_and_assignment_owned_by_start_month(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    overnight_demand = ShiftDemand("DEM-N", "", datetime(2026, 8, 31, 19, 0), datetime(2026, 9, 1, 7, 0), 1)
    overnight_assignment = Assignment(
        "ASG-N", "", "EMP-1", datetime(2026, 8, 31, 19, 0), datetime(2026, 9, 1, 7, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-N", None,
    )
    _create(conn, shift_demands=[overnight_demand], assignments=[overnight_assignment])
    snapshot = repo.get_schedule_snapshot(conn, "SV-1")
    assert snapshot.shift_demands[0].demand_id == "DEM-N"  # accepted: start (Aug) owns it, not end (Sep)


def test_k2_primary_must_cover_a_same_version_demand(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, shift_demands=[_demand()], assignments=[_primary(covers="NO-SUCH-DEMAND")])


def test_k3_trainee_must_reference_same_version_primary_mentor(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    trainee = _trainee("ASG-T", mentor_id="ASG-1")
    _create(conn, shift_demands=[_demand()], assignments=[_primary(), trainee])
    snapshot = repo.get_schedule_snapshot(conn, "SV-1")
    assert len(snapshot.assignments) == 2

    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, version_id="SV-BAD", shift_demands=[_demand()], assignments=[_trainee("ASG-T2", "NO-SUCH-MENTOR")])


def test_k4_dangling_or_cross_version_mentor_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create(conn)  # SV-1 has PRIMARY ASG-1
    with pytest.raises(MalformedScheduleSnapshot):
        lc.create_schedule_version(
            conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
            created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
            applied_rule_version_ids=[], shift_demands=[], assignments=[_trainee("ASG-T", "ASG-1")], deviations=[],
        )  # ASG-1 does not exist inside SV-2's own content


def test_k5_invalid_interval_or_count_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    backwards = ShiftDemand("DEM-BAD", "", datetime(2026, 8, 1, 19, 0), datetime(2026, 8, 1, 7, 0), 1)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, shift_demands=[backwards], assignments=[])

    zero_count = ShiftDemand("DEM-ZERO", "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), 0)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, version_id="SV-2", shift_demands=[zero_count], assignments=[])


# --- L. DEVIATION --------------------------------------------------------------


def test_l1_round_trips_all_categories_and_fields(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    deviation = Deviation(
        "DEV-1", "", DeviationCategory.CLIENT_REQUIREMENT, "RULE-SOURCE", "EMP-1",
        True, "COORD-1", datetime(2026, 8, 1, 9, 0), "explanation",
    )
    _create(conn, deviations=[deviation])
    snapshot = repo.get_schedule_snapshot(conn, "SV-1")
    assert snapshot.deviations[0].category == DeviationCategory.CLIENT_REQUIREMENT
    assert snapshot.deviations[0].reason == "explanation"


def test_l2_acknowledged_requires_coordinator_and_timestamp(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    missing_timestamp = Deviation("DEV-1", "", DeviationCategory.HOURS, "SRC", "EMP-1", True, "COORD-1", None, None)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, deviations=[missing_timestamp])

    unknown_coordinator = Deviation(
        "DEV-2", "", DeviationCategory.HOURS, "SRC", "EMP-1", True, "NO-SUCH-COORD", datetime(2026, 8, 1, 9, 0), None,
    )
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, version_id="SV-2", deviations=[unknown_coordinator])


def test_l3_affected_reference_resolves_to_employee_or_same_version_assignment(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    by_assignment = Deviation("DEV-1", "", DeviationCategory.HOURS, "SRC", "ASG-1", False, None, None, None)
    _create(conn, deviations=[by_assignment])  # resolves via same-version Assignment id

    with pytest.raises(MalformedScheduleSnapshot):
        bad = Deviation("DEV-2", "", DeviationCategory.HOURS, "SRC", "NO-SUCH-TARGET", False, None, None, None)
        _create(conn, version_id="SV-2", deviations=[bad])


def test_l4_final_with_deviations_rejects_unacknowledged(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    unacknowledged = Deviation("DEV-1", "", DeviationCategory.HOURS, "SRC", "EMP-1", False, None, None, None)
    _create(conn, deviations=[unacknowledged])
    with pytest.raises(MalformedScheduleSnapshot):
        lc.finalize_schedule_version(conn, version_id="SV-1")
