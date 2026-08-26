"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r15.txt.

FINDING R15-1: an existing Assignment for an employee with no membership at
all for the current site -- or a membership only for a different site
(EMP-03: an Employee is not structurally owned by exactly one Site, so this
is valid data) -- was still accepted as FEASIBLE. Round 14 only caught the
disabled-membership case, not the missing-membership case.

FINDING R15-2: the uncapped LOAD-01 fallback built a DECISION_REQUIRED from
over_threshold alone, ignoring any other HARD violation the independent
validator found in the same candidate (e.g. DAY_ONLY-01), silently dropping
it from the payload.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import rota.planning.engine as engine_module
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
DEMAND_N = ShiftDemand("2026-10-01-N", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1)


def _local_membership(employee_id: str, site_id: str = SITE_ID) -> SiteMembership:
    return SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _existing_covering_assignment() -> Assignment:
    return Assignment(
        "existing-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )


# FINDING R15-1 -----------------------------------------------------------


def test_r15_1a_existing_assignment_with_no_membership_at_all_is_not_feasible():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(), shift_demands=(DEMAND_D,),
        existing_assignments=(_existing_covering_assignment(),),
    )
    result = plan(state)
    assert result.status != "FEASIBLE"


def test_r15_1b_existing_assignment_with_membership_for_other_site_only_is_not_feasible():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A", site_id="different-site"),),
        shift_demands=(DEMAND_D,), existing_assignments=(_existing_covering_assignment(),),
    )
    result = plan(state)
    assert result.status != "FEASIBLE"


# FINDING R15-2 -------------------------------------------------------------


def test_r15_2_uncapped_load_fallback_does_not_mask_day_only(monkeypatch):
    solved = Assignment(
        "solved-1", "test-v1", "A", DEMAND_N.start_datetime, DEMAND_N.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_N.demand_id, None,
    )

    def _fake_solve(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False, **_kwargs):
        if enforce_load_cap:
            return SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})
        return SolverOutcome("OPTIMAL", [solved], [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake_solve)
    # DAY_ONLY employee on N -> independent validator finds DAY_ONLY-01 on
    # top of the real LOAD-01 trigger (threshold=11h < 12h shift).
    employee = Employee("A", "A", date(2026, 9, 1), None, True)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_N,))
    state = replace(state, profile=replace(state.profile, rolling_7d_decision_threshold_hours=11))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


if __name__ == "__main__":
    print("test_audit_r15_findings module OK")
