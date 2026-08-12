"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r25.txt.

R25-1: violation classification matched by exact assignment_id (fixing
R23-2's substring bug) but not by rule, so diagnosing ONE rule violation on
a fixed Assignment wrongly "explained away" an INDEPENDENT violation of a
DIFFERENT rule on that same Assignment (DAY_ONLY-01 masking a co-occurring
SICK_LEAVE-01; SICK_LEAVE-01 masking a co-occurring REST-01).

Also covers the owner's SICK_LEAVE > LEAVE_GRANTED priority rule
(2026-08-14): when both overlap the same day, the reported reason must be
SICK_LEAVE-01 ("chorobowe"), not LEAVE_GRANTED-01 ("urlop").
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R25-1 -----------------------------------------------------------


def test_r25_1a_day_only_does_not_mask_concurrent_sick_leave():
    demand_n = ShiftDemand("2026-10-01-N", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, True)  # day_only=True
    frozen = Assignment(
        "frozen", "test-v1", "A", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_n.demand_id, None,
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_n,), existing_assignments=(frozen,), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "DAY_ONLY-01" in conditions
    assert "SICK_LEAVE-01" in conditions


def test_r25_1b_sick_leave_does_not_mask_concurrent_rest01():
    demand_d = ShiftDemand("2026-10-02-D", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    # earlier fixed PRIMARY ends 19:00 Oct1 -> only 10h rest before D starts 05:00 Oct2.
    earlier_fixed = Assignment(
        "earlier", "test-v1", "A", datetime(2026, 10, 1, 7, 0), datetime(2026, 10, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None,
    )
    frozen_d = Assignment(
        "frozen", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 2), date(2026, 10, 2), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(demand_d,),
        existing_assignments=(earlier_fixed, frozen_d), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "REST-01" in conditions
    assert "SICK_LEAVE-01" in conditions


def test_r25_1_dangling_trainee_still_forces_technical_error():
    """Regression guard: _FROZEN_BOUNDARY_RULES must not accidentally start
    treating ASSIGN (referential integrity) as an explainable autonomy
    boundary just because a TRAINEE's own assignment_id is always in the
    fixed set."""
    demand = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    frozen_conflict = Assignment(
        "frozen-1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand.demand_id, None,
    )
    dangling_trainee = Assignment(
        "dangling-t", "test-v1", "MENTEE", demand.start_datetime, demand.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "does-not-exist",
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee, mentee), memberships=(_local_membership("A"), _local_membership("MENTEE")),
        shift_demands=(demand,), existing_assignments=(frozen_conflict, dangling_trainee), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# SICK_LEAVE > LEAVE_GRANTED priority (owner decision 2026-08-14) -----------


def test_sick_leave_wins_over_leave_granted_on_overlapping_day():
    demand = ShiftDemand("2026-10-15-D", "test-v1", datetime(2026, 10, 15, 5, 0), datetime(2026, 10, 15, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 14), date(2026, 10, 20), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 10), date(2026, 10, 16), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(urlop, zwolnienie),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert all(b.condition == "SICK_LEAVE-01" for b in result.decision_payload.blockers)


def test_leave_granted_still_reported_outside_the_sick_range():
    demand = ShiftDemand("2026-10-18-D", "test-v1", datetime(2026, 10, 18, 5, 0), datetime(2026, 10, 18, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 14), date(2026, 10, 20), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 10), date(2026, 10, 16), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(urlop, zwolnienie),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert all(b.condition == "LEAVE_GRANTED-01" for b in result.decision_payload.blockers)


def test_validator_reports_only_sick_leave_on_overlapping_day():
    demand = ShiftDemand("2026-10-15-D", "test-v1", datetime(2026, 10, 15, 5, 0), datetime(2026, 10, 15, 17, 0), 1)
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 14), date(2026, 10, 20), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 10), date(2026, 10, 16), True, None, None)
    assignment = Assignment(
        "a1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    state = base_state(shift_demands=(demand,), availability_records=(urlop, zwolnienie))
    report = validate(state, [assignment])
    matching = [v for v in report.violations if "SICK_LEAVE-01" in v or "LEAVE_GRANTED-01" in v]
    assert len(matching) == 1
    assert "SICK_LEAVE-01" in matching[0]


if __name__ == "__main__":
    print("test_audit_r25_findings module OK")
