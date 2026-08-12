"""Tests for the contract items implemented after round 19 PASS:
- owner decision on ShiftDemand/StandardShift validation symmetry (R19);
- weekend fairness and holiday fairness SOFT ranking (arch/spec.md SECTION 3);
- REPLAN redistribution semantics (arch/spec.md SECTION 7, ASSIGN-03/04).
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


# Owner decision from tests_r19.txt WYMAGA_DECYZJI ---------------------------


def test_shift_demand_classification_is_symmetric_covered_vs_uncovered():
    bad_demand = ShiftDemand("bad-1", "test-v1", datetime(2026, 10, 1, 8, 0), datetime(2026, 10, 1, 16, 0), 1)
    existing = Assignment(
        "existing-1", "test-v1", "A", bad_demand.start_datetime, bad_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, bad_demand.demand_id, None,
    )
    state = base_state(shift_demands=(bad_demand,), existing_assignments=(existing,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# Weekend fairness ------------------------------------------------------------


def test_weekend_fairness_splits_weekend_demands_evenly():
    demand_sat = ShiftDemand("2026-10-03-D", "test-v1", datetime(2026, 10, 3, 5, 0), datetime(2026, 10, 3, 17, 0), 1)
    demand_sun = ShiftDemand("2026-10-04-D", "test-v1", datetime(2026, 10, 4, 5, 0), datetime(2026, 10, 4, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand_sat, demand_sun),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    employee_ids = {a.employee_id for a in result.candidates[0]}
    assert employee_ids == {"A", "B"}


# Holiday fairness ------------------------------------------------------------


def test_holiday_fairness_prefers_employee_with_less_historical_holiday_work():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    history = (
        Assignment("h1", "prev-v1", "A", datetime(2026, 1, 1, 5, 0), datetime(2026, 1, 1, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None),
    )
    calendar_days = (CalendarDay(date(2026, 10, 1), True),)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(DEMAND_D,), holiday_history=history, calendar_days=calendar_days,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0][0].employee_id == "B"


# REPLAN ------------------------------------------------------------------


def test_replan_redistributes_when_previously_assigned_employee_becomes_unavailable():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    original = Assignment(
        "orig-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    sick = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(DEMAND_D,), existing_assignments=(original,), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert [a.employee_id for a in result.candidates[0]] == ["B"]
    assert "orig-1" not in {a.assignment_id for a in result.candidates[0]}


def test_replan_preserves_frozen_assignment_unchanged():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    state = base_state(
        employees=(employee_a,), memberships=(_local_membership("A"),),
        shift_demands=(DEMAND_D,), existing_assignments=(frozen,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0] == [frozen]


def test_replan_preserves_realized_assignment_even_if_employee_now_unavailable():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    realized = Assignment(
        "realized-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, DEMAND_D.demand_id, None,
    )
    now_sick = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee_a,), memberships=(),
        shift_demands=(DEMAND_D,), existing_assignments=(realized,), availability_records=(now_sick,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0] == [realized]


def test_replan_preserves_trainee_assignment_always():
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    mentor = Employee("MENTOR", "MENTOR", date(2026, 9, 1), None, False)
    mentor_primary = Assignment(
        "mentor-primary-1", "test-v1", "MENTOR", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    trainee = Assignment(
        "s-1", "test-v1", "MENTEE", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 11, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-primary-1",
    )
    state = base_state(
        employees=(mentee, mentor), memberships=(_local_membership("MENTEE"), _local_membership("MENTOR")),
        shift_demands=(DEMAND_D,), existing_assignments=(mentor_primary, trainee),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert sorted(result.candidates[0], key=lambda a: a.assignment_id) == sorted(
        [mentor_primary, trainee], key=lambda a: a.assignment_id
    )


def test_validator_flags_tampered_fixed_assignment_independently():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    state = base_state(employees=(employee_a,), memberships=(_local_membership("A"),), existing_assignments=(frozen,))
    tampered = Assignment(
        "frozen-1", "test-v1", "A", DEMAND_D.start_datetime, datetime(2026, 10, 1, 18, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    report = validate(state, [tampered])
    assert not report.hard_pass
    assert any("ASSIGN-03/04" in v for v in report.violations)


if __name__ == "__main__":
    print("test_replan_and_soft_ranking module OK")
