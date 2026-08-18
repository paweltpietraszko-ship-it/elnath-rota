"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r13.txt.

One group of tests per finding from the round-13 re-audit of
experiment/rota-solo-build commit e410843, including the sibling cases the
audit explicitly called out as missing from the round-12 regression suite.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
)
from rota.planning.eligibility import check_eligibility
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R13-1 ---------------------------------------------------------------


def test_r13_1a_pure_load_conflict_is_load01_not_rest01():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,))
    state = replace(state, profile=replace(state.profile, rolling_7d_decision_threshold_hours=11))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert result.decision_payload.load_blocker.employee_id == "A"
    assert all(b.condition == "LOAD-01" for b in result.decision_payload.blockers)


def test_r13_1b_load_conflict_crossing_month_boundary_is_load01():
    employee = Employee("C", "C", date(2026, 9, 1), None, False)
    boundary = tuple(
        Assignment(f"boundary-{d}", "prev-v1", "C", datetime(2026, 9, d, 5, 0), datetime(2026, 9, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None)
        for d in range(26, 31)
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("C"),),
        shift_demands=(DEMAND_D,), boundary_assignments=boundary,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert any(b.condition == "LOAD-01" for b in result.decision_payload.blockers)


def test_r13_1c_pure_headcount_shortage_is_not_rest01():
    demand_two = ShiftDemand("2026-10-01-D2", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 2)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(demand_two,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is None
    assert all(b.condition != "REST-01" for b in result.decision_payload.blockers)


# FINDING R13-2 ---------------------------------------------------------------


def test_r13_2a_cancelled_does_not_block_replacement_end_to_end():
    cancelled = Assignment(
        "existing-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, DEMAND_D.demand_id, None,
    )
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(DEMAND_D,), existing_assignments=(cancelled,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"


def test_r13_2b_cancelled_excluded_from_validator_rest_and_load():
    cancelled = Assignment(
        "cancelled-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, DEMAND_D.demand_id, None,
    )
    replacement = Assignment(
        "replacement-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(shift_demands=(DEMAND_D,), memberships=(_local_membership("A"),))
    report = validate(state, [cancelled, replacement])
    assert report.hard_pass, report.violations
    assert report.monthly_hours == {"A": 12}


# FINDING R13-3 ---------------------------------------------------------------


def test_r13_3_validator_does_not_emit_emp02():
    """SUPERSEDED by ROTA-T016 (owner decision 2026-08-16): round-13 finding
    R13-3 originally proved the independent validator was missing an EMP-02
    check that the solver's own eligibility gate already had. T016 retires
    EMP-02 from both eligibility and the validator, so the corrected
    regression is the opposite assertion: an Assignment outside the
    Employee's (now legacy, non-operational) active period must NOT be
    reported as an EMP-02 violation. An enabled membership is supplied so
    the result isn't obscured by MEMBERSHIP-01."""
    employee = Employee("A", "A", date(2026, 10, 2), None, False)
    assignment = Assignment(
        "a1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,))
    report = validate(state, [assignment])
    assert report.hard_pass
    assert not any("EMP-02" in v for v in report.violations)


# FINDING R13-4 ---------------------------------------------------------------


def test_r13_4a_solver_rejects_window_belonging_to_other_employee():
    employee_x = Employee("X", "X", date(2026, 9, 1), None, False)
    membership_x = SiteMembership("X", SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    window_for_y = ExternalSupportWindow("win-y", "Y", SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None)
    state = base_state(employees=(employee_x,))
    result = check_eligibility(
        employee_x, membership_x, DEMAND_D, ShiftKind.D, state.profile, [], [window_for_y], SITE_ID,
    )
    assert not result.eligible


def test_r13_4b_validator_checks_allowed_shift_kind():
    demand_n = ShiftDemand("2026-10-01-N", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1)
    assignment_n = Assignment(
        "a1", "test-v1", "X", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_n.demand_id, None,
    )
    membership_x = SiteMembership("X", SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    window_d_only = ExternalSupportWindow("win-x", "X", SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, ShiftKind.D)
    state = base_state(memberships=(membership_x,), external_windows=(window_d_only,))
    report = validate(state, [assignment_n])
    assert not report.hard_pass
    assert any("EXTERNAL-01" in v for v in report.violations)


if __name__ == "__main__":
    print("test_audit_r13_findings module OK")
