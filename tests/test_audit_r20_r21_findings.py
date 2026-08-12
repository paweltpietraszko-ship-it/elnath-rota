"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r20.txt and
tests_r21.txt.

R20-1: holiday fairness used a static pre-solve rank that stayed constant
regardless of how many holiday demands were actually assigned, so it could
keep preferring the same employee past the point of equal distribution.

R20-2: a future frozen (or TRAINEE-mentor-linked) PRIMARY Assignment that
currently conflicts with UNAVAILABLE_24H/LEAVE_GRANTED/SICK_LEAVE/disabled
membership was mapped to TECHNICAL_ERROR instead of DECISION_REQUIRED --
ASSIGN-04 forbids REPLAN from moving it, but that is a normal autonomy
boundary, not a technical failure.

R20-3: REPLAN could redistribute a mentor's PRIMARY away while preserving
the TRAINEE that depends on it, leaving mentor_primary_assignment_id
dangling in an otherwise-FEASIBLE candidate.

R21-1: two overlapping/abutting active SICK_LEAVE records for the same
employee summed their day counts instead of unioning the calendar dates,
double-counting the shared day(s) against target_hours.
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R20-1 -----------------------------------------------------------


def test_r20_1_holiday_fairness_finds_the_true_equal_split():
    demands = tuple(
        ShiftDemand(f"2026-10-0{d}-D", "test-v1", datetime(2026, 10, d, 5, 0), datetime(2026, 10, d, 17, 0), 1)
        for d in (1, 2, 3)
    )
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    history = (
        Assignment("h1", "prev-v1", "B", datetime(2026, 1, 1, 5, 0), datetime(2026, 1, 1, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None),
    )
    calendar_days = tuple(CalendarDay(date(2026, 10, d), True) for d in (1, 2, 3))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=demands, holiday_history=history, calendar_days=calendar_days,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    counts: dict[str, int] = {}
    for a in result.candidates[0]:
        counts[a.employee_id] = counts.get(a.employee_id, 0) + 1
    # historical B=12h, A=0h; three new 12h holiday demands; true optimum is
    # A gets 2 (0+24=24h) and B gets 1 (12+12=24h) -> perfectly balanced.
    assert counts == {"A": 2, "B": 1}


# FINDING R20-2 -------------------------------------------------------------


def _frozen_primary(availability_kind: AvailabilityKind):
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    record = AvailabilityRecord("r1", "r1v1", "A", availability_kind, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    return base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(DEMAND_D,), existing_assignments=(frozen,), availability_records=(record,),
    )


def test_r20_2a_frozen_conflict_with_unavailable_is_decision_required():
    result = plan(_frozen_primary(AvailabilityKind.UNAVAILABLE_24H))
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "UNAVAILABLE-01" for b in result.decision_payload.blockers)


def test_r20_2b_frozen_conflict_with_leave_granted_is_decision_required():
    result = plan(_frozen_primary(AvailabilityKind.LEAVE_GRANTED))
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "LEAVE_GRANTED-01" for b in result.decision_payload.blockers)


def test_r20_2c_frozen_conflict_with_sick_leave_is_decision_required():
    result = plan(_frozen_primary(AvailabilityKind.SICK_LEAVE))
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "SICK_LEAVE-01" for b in result.decision_payload.blockers)


def test_r20_2d_mentor_linked_non_frozen_conflict_is_decision_required():
    """The mentor-link protection (R20-3) makes a PRIMARY fixed even with
    frozen=False; that path must also be diagnosed, not just frozen=True."""
    mentor = Employee("A", "A", date(2026, 9, 1), None, False)
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    mentor_primary = Assignment(
        "mentor-primary", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    trainee = Assignment(
        "t-1", "test-v1", "MENTEE", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-primary",
    )
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(mentor, mentee), memberships=(_local_membership("A"), _local_membership("MENTEE")),
        shift_demands=(DEMAND_D,), existing_assignments=(mentor_primary, trainee), availability_records=(unavailable,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "UNAVAILABLE-01" for b in result.decision_payload.blockers)


# FINDING R20-3 -------------------------------------------------------------


def test_r20_3_replan_does_not_dangle_trainee_reference_when_mentor_redistributed():
    mentor = Employee("A", "A", date(2026, 9, 1), None, False)
    backup = Employee("B", "B", date(2026, 9, 1), None, False)
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    mentor_primary = Assignment(
        "mentor-primary", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    trainee = Assignment(
        "t-1", "test-v1", "MENTEE", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-primary",
    )
    state = base_state(
        employees=(mentor, backup, mentee),
        memberships=(_local_membership("A"), _local_membership("B"), _local_membership("MENTEE")),
        shift_demands=(DEMAND_D,), existing_assignments=(mentor_primary, trainee),
    )
    result = plan(state)
    # mentor-link protection keeps the demand pinned to A (not redistributed
    # to B) precisely so the TRAINEE reference never dangles.
    assert result.status == "FEASIBLE"
    assignment_ids = {a.assignment_id for a in result.candidates[0]}
    assert "mentor-primary" in assignment_ids
    assert "t-1" in assignment_ids


def test_r20_3_validator_independently_flags_dangling_trainee_reference():
    trainee = Assignment(
        "t-1", "test-v1", "MENTEE", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "does-not-exist",
    )
    state = base_state()
    report = validate(state, [trainee])
    assert not report.hard_pass
    assert any("does-not-exist" in v for v in report.violations)


# FINDING R21-1 ---------------------------------------------------------------


def test_r21_1_overlapping_sick_ranges_union_not_sum():
    from rota.planning.solver import _sick_leave_days_in_month

    # Two active records both covering Oct 3: union is Oct 1-5 (5 days), not
    # 3+3=6 days -- the bug summed each record's own day count instead of
    # unioning per-employee calendar dates.
    sick_1 = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 3), True, None, None)
    sick_2 = AvailabilityRecord("s2", "s2v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 3), date(2026, 10, 5), True, None, None)
    state = base_state(availability_records=(sick_1, sick_2))
    assert _sick_leave_days_in_month(state) == {"A": 5}


if __name__ == "__main__":
    print("test_audit_r20_r21_findings module OK")
