"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r12.txt.

One test (or small group) per finding from the round-12 adversarial audit of
experiment/rota-solo-build commit c438fec. Each reproduces the exact failure
mode described in the audit and asserts the corrected behavior.
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
    ExternalSupportWindow,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str, enabled: bool = True) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _external_membership(employee_id: str, enabled: bool = True) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.EXTERNAL_SUPPORT, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING 1 -----------------------------------------------------------------


def test_finding1_cancelled_assignment_does_not_count_as_coverage():
    cancelled = Assignment(
        "existing-1", "test-v1", "ghost", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(shift_demands=(DEMAND_D,), existing_assignments=(cancelled,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.blocking_shift_demands[0].demand_id == DEMAND_D.demand_id


def test_finding1_trainee_with_covers_demand_id_is_not_coverage():
    malformed_trainee = Assignment(
        "existing-2", "test-v1", "mentee", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, DEMAND_D.demand_id, "mentor-1",
    )
    state = base_state(shift_demands=(DEMAND_D,))
    report = validate(state, [malformed_trainee])
    assert not report.hard_pass
    assert any("COVERAGE-01" in v for v in report.violations)


# FINDING 2 -------------------------------------------------------------------


def _external_window(employee_id: str) -> ExternalSupportWindow:
    return ExternalSupportWindow(
        f"win-{employee_id}", employee_id, SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None
    )


def test_finding2_disabled_external_membership_is_not_eligible():
    employee = Employee("X", "X", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_external_membership("X", enabled=False),),
        external_windows=(_external_window("X"),), shift_demands=(DEMAND_D,),
    )
    assert plan(state).status == "DECISION_REQUIRED"


def test_finding2_external_employee_outside_active_period_is_still_eligible():
    """SUPERSEDED by ROTA-T016 (owner decision 2026-08-16): round-12 finding 2
    originally proved EMP-02 blocked this EXTERNAL employee because the
    demand fell before Employee.active_from. T016 retires EMP-02 entirely --
    the program does not gate eligibility on Employee active period, only on
    SiteMembership/MEMBERSHIP-01 and the other still-active HARD rules. The
    same fixture (enabled EXTERNAL_SUPPORT membership, a covering
    ExternalSupportWindow, active_from set after the demand date) must now
    reach FEASIBLE since nothing else blocks it -- this is the corrected
    regression for the retirement, not a relaxation of a bug."""
    employee = Employee("Y", "Y", date(2026, 10, 2), None, False)
    state = base_state(
        employees=(employee,), memberships=(_external_membership("Y"),),
        external_windows=(_external_window("Y"),), shift_demands=(DEMAND_D,),
    )
    assert plan(state).status == "FEASIBLE"


def test_finding2_unavailable_external_maps_to_decision_required_not_technical_error():
    employee = Employee("Z", "Z", date(2026, 9, 1), None, False)
    unavailable = AvailabilityRecord("a1", "a1v1", "Z", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_external_membership("Z"),),
        external_windows=(_external_window("Z"),), shift_demands=(DEMAND_D,),
        availability_records=(unavailable,),
    )
    assert plan(state).status == "DECISION_REQUIRED"


# FINDING 3 -------------------------------------------------------------------


def test_finding3_rest01_combination_conflict_is_decision_required():
    demand_n = ShiftDemand("2026-10-01-N", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1)
    demand_d2 = ShiftDemand("2026-10-02-D", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(demand_n, demand_d2))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    blocked_ids = {b.demand_id for b in result.decision_payload.blocking_shift_demands}
    assert blocked_ids == {"2026-10-01-N", "2026-10-02-D"}
    assert any(b.employee_id == "A" and b.condition == "REST-01" for b in result.decision_payload.blockers)


# FINDING 4 -------------------------------------------------------------------


def test_finding4_decision_required_has_concrete_blockers():
    employee = Employee("B", "B", date(2026, 9, 1), None, False)
    leave = AvailabilityRecord("a2", "a2v1", "B", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("B"),),
        shift_demands=(DEMAND_D,), availability_records=(leave,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.blockers
    assert result.decision_payload.blockers[0].employee_id == "B"
    assert result.decision_payload.blockers[0].condition == "LEAVE_GRANTED-01"


# FINDING 5 -------------------------------------------------------------------


def _boundary_day(day: int) -> Assignment:
    start = datetime(2026, 9, day, 5, 0)
    end = datetime(2026, 9, day, 17, 0)
    return Assignment(f"boundary-{day}", "prev-v1", "C", start, end, AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None)


def test_finding5_load01_window_crossing_month_boundary_is_checked():
    boundary = tuple(_boundary_day(d) for d in range(26, 31))
    new_assignment = Assignment(
        "new-oct1", "test-v1", "C", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    state = base_state(boundary_assignments=boundary)
    report = validate(state, [new_assignment])
    assert not report.hard_pass
    assert any("LOAD-01" in v for v in report.violations)


# FINDING 6 -------------------------------------------------------------------


def test_finding6_validator_checks_external01():
    employee_x_assignment = Assignment(
        "x-assign", "test-v1", "X", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    state = base_state(memberships=(_external_membership("X"),))
    report = validate(state, [employee_x_assignment])
    assert not report.hard_pass
    assert any("EXTERNAL-01" in v for v in report.violations)


def test_finding6_validator_checks_boundary_rest():
    boundary = Assignment(
        "boundary-1", "prev-v1", "C", datetime(2026, 9, 30, 17, 0), datetime(2026, 10, 1, 4, 0),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None,
    )
    new_assignment = Assignment(
        "new-1", "test-v1", "C", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    state = base_state(boundary_assignments=(boundary,))
    report = validate(state, [new_assignment])
    assert not report.hard_pass
    assert any("REST-01" in v for v in report.violations)


if __name__ == "__main__":
    print("test_audit_r12_findings module OK")
