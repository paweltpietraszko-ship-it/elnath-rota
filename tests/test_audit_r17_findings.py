"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r17.txt.

R17-1: a demand already fully covered by existing_assignments gets no
SolverSlot, so the LOAD-01 cap is never added for that employee even though
the capped solve reports OPTIMAL; a LOAD-01-only violation surfacing there
was misclassified as TECHNICAL_ERROR.

R17-2: an employee with no membership at all for the current site (or only
for a different site) produced DECISION_REQUIRED with blockers=[].

R17-3: UnclassifiedShiftError (a ShiftDemand matching no StandardShift)
propagated out of the public plan() instead of becoming TECHNICAL_ERROR.

R17-4: a LEAVE_PLAN collision on a pre-existing Assignment produced no
warning in the public PlanningResult (only newly-solved slots did).

R17-5: CANCELLED existing Assignments were still counted toward the
TARGET-01 SOFT objective, skewing which candidate the solver picks.
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
    WorkBalance,
)
from rota.planning.engine import plan
from tests.support.minimal_state import MONTH, ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str, site_id: str = SITE_ID) -> SiteMembership:
    return SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R17-1 -----------------------------------------------------------


def test_r17_1_existing_only_load01_is_decision_required_not_technical_error():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    existing = tuple(
        Assignment(f"e{d}", "test-v1", "A", datetime(2026, 9, d, 5, 0), datetime(2026, 9, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None)
        for d in range(25, 31)
    )
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), existing_assignments=existing)
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert result.decision_payload.load_blocker.hours == 72


# FINDING R17-2 -------------------------------------------------------------


def test_r17_2a_missing_membership_gives_concrete_blocker():
    """T013: MEMBERSHIP-01 is coordinator-invisible and never suggests a
    roster change -- only the coordinator decides staffing (section E)."""
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(), shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.blocking_shift_demands
    assert not any(b.employee_id == "A" for b in result.decision_payload.blockers)
    assert [o.text for o in result.decision_payload.unblocking_options] == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]


def test_r17_2b_other_site_only_membership_gives_concrete_blocker():
    """T013: same invisibility for the other-site-only membership case."""
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A", "other-site"),), shift_demands=(DEMAND_D,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.blocking_shift_demands
    assert not any(b.employee_id == "A" for b in result.decision_payload.blockers)
    assert [o.text for o in result.decision_payload.unblocking_options] == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]


# FINDING R17-3 -------------------------------------------------------------


def test_r17_3_unclassified_shift_is_technical_error_not_an_exception():
    bad_demand = ShiftDemand("bad-1", "test-v1", datetime(2026, 10, 1, 8, 0), datetime(2026, 10, 1, 16, 0), 1)
    state = base_state(shift_demands=(bad_demand,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# FINDING R17-4 -------------------------------------------------------------


def test_r17_4_leave_plan_warning_visible_for_existing_assignment():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    leave_plan = AvailabilityRecord("lp1", "lp1v1", "A", AvailabilityKind.LEAVE_PLAN, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    existing = Assignment(
        "existing-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,),
        availability_records=(leave_plan,), existing_assignments=(existing,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert any("LEAVE_PLAN-01" in w for w in result.warnings)


# FINDING R17-5 -------------------------------------------------------------


def test_r17_5_cancelled_excluded_from_target01_objective():
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    cancelled = tuple(
        Assignment(f"c{d}", "test-v1", "A", datetime(2026, 9, d, 5, 0), datetime(2026, 9, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, None, None)
        for d in (1, 2)
    )
    work_balances = (WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 0, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(DEMAND_D,), existing_assignments=cancelled, work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    solved = [a for a in result.candidates[0] if a.state != AssignmentState.CANCELLED]
    assert [a.employee_id for a in solved] == ["A"]


if __name__ == "__main__":
    print("test_audit_r17_findings module OK")
