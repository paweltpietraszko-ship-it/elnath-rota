"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r26.txt.

R26-1: the SICK_LEAVE > LEAVE_GRANTED priority rule (owner decision
2026-08-14) was implemented as "pick one winning kind for the whole
Assignment," which (a) dropped an independent LEAVE_GRANTED-01 or
SICK_LEAVE-01 blocker when the two records actually blocked the Assignment
on different days, and (b) invented an UNAVAILABLE_24H > SICK_LEAVE priority
that was never decided. Both must be reported unless the SICK_LEAVE and
LEAVE_GRANTED records' own date ranges intersect each other.

R26-2: arch/spec.md:393-394 freezes the condition code for UNAVAILABLE_24H
as "UNAVAILABLE-01", not "UNAVAILABLE_24H-01".

R26-3: a REST-01 between one fixed Assignment and one solver-created
(movable) Assignment is a solver/mapping bug (TECHNICAL_ERROR), not a
coordinator autonomy boundary (DECISION_REQUIRED) -- only REST-01 between
two fixed facts is a genuine boundary.
"""
from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime

import rota.planning.engine as engine_module
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
from rota.planning.solver import SolverOutcome
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _full_month_calendar(month: date) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


# FINDING R26-1 -------------------------------------------------------------


def test_r26_1a_leave_granted_and_sick_leave_on_different_days_are_both_reported():
    """Night Assignment 02.10 17:00 -> 03.10 05:00; LEAVE_GRANTED ends 02.10,
    SICK_LEAVE starts 03.10 -- the two records never overlap each other, so
    both must be reported, not just SICK_LEAVE-01."""
    demand_n = ShiftDemand("2026-10-02-N", "test-v1", datetime(2026, 10, 2, 17, 0), datetime(2026, 10, 3, 5, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_n.demand_id, None,
    )
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 9, 25), date(2026, 10, 2), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 3), date(2026, 10, 10), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_n,), existing_assignments=(frozen,), availability_records=(urlop, zwolnienie),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z zapisem: Urlop" in conditions
    assert "Koliduje z zapisem: Chorobowe" in conditions


def test_r26_1a_reversed_record_order_gives_same_result():
    demand_n = ShiftDemand("2026-10-02-N", "test-v1", datetime(2026, 10, 2, 17, 0), datetime(2026, 10, 3, 5, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_n.demand_id, None,
    )
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 9, 25), date(2026, 10, 2), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 3), date(2026, 10, 10), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_n,), existing_assignments=(frozen,), availability_records=(zwolnienie, urlop),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z zapisem: Urlop" in conditions
    assert "Koliduje z zapisem: Chorobowe" in conditions


def test_r26_1b_unavailable_24h_and_sick_leave_no_established_priority_both_reported():
    demand_d = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_d,), existing_assignments=(frozen,), availability_records=(unavailable, sick),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z checkbox: Ogólna dostępność" in conditions
    assert "Koliduje z zapisem: Chorobowe" in conditions


def test_r26_1_sick_leave_still_wins_over_leave_granted_on_the_actual_shared_day():
    """Guard: R26-1's fix must not regress the owner's original SICK_LEAVE >
    LEAVE_GRANTED decision when the records genuinely share a day."""
    demand = ShiftDemand("2026-10-15-D", "test-v1", datetime(2026, 10, 15, 5, 0), datetime(2026, 10, 15, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    urlop = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 14), date(2026, 10, 20), True, None, None)
    zwolnienie = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 10), date(2026, 10, 16), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(urlop, zwolnienie),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert all(b.condition == "Koliduje z zapisem: Chorobowe" for b in result.decision_payload.blockers)


# FINDING R26-2 -------------------------------------------------------------


def test_r26_2_unavailable_condition_code_is_canonical():
    demand_d = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_d,), existing_assignments=(frozen,), availability_records=(unavailable,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z checkbox: Ogólna dostępność" in conditions
    assert "UNAVAILABLE_24H-01" not in conditions


def test_r26_2_validator_emits_canonical_code_directly():
    demand_d = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    assignment = Assignment(
        "a1", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_d.demand_id, None,
    )
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(shift_demands=(demand_d,), availability_records=(unavailable,))
    report = validate(state, [assignment])
    assert any(d.rule == "UNAVAILABLE-01" for d in report.violation_details)
    assert not any(d.rule == "UNAVAILABLE_24H-01" for d in report.violation_details)


# FINDING R26-3 ---------------------------------------------------------------


def test_r26_3_rest_between_fixed_and_solver_created_assignment_is_technical_error(monkeypatch):
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    earlier_fixed = Assignment(
        "earlier", "test-v1", "A", datetime(2026, 10, 1, 7, 0), datetime(2026, 10, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None,
    )
    demand_d = ShiftDemand("2026-10-02-D", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    solved = Assignment(
        "solved-1", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_d.demand_id, None,
    )

    def _fake_solve(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False):
        return SolverOutcome("OPTIMAL", [solved], [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake_solve)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_d,), existing_assignments=(earlier_fixed,),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


def test_r26_3_sibling_rest_between_two_fixed_assignments_stays_decision_required():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    demand_d = ShiftDemand("2026-10-02-D", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    earlier_fixed = Assignment(
        "earlier", "test-v1", "A", datetime(2026, 10, 1, 7, 0), datetime(2026, 10, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None,
    )
    frozen_d = Assignment(
        "frozen-d", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand_d,), existing_assignments=(earlier_fixed, frozen_d),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z odpoczynkiem dobowym" in conditions


if __name__ == "__main__":
    print("test_audit_r26_findings module OK")
