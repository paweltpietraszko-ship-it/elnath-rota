"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r14.txt.

FINDING R14-1: an existing (pre-solve) Assignment for an employee whose LOCAL
membership is disabled was never checked against MEMBERSHIP-01, so it could
reach FEASIBLE unnoticed on both the solver and validator side.

FINDING R14-2: engine.plan() retried without the LOAD-01 cap for *any*
non-assignments outcome, including a genuine solver failure (UNKNOWN,
MODEL_INVALID), and then guessed a LOAD-01 cause from whatever the uncapped
solve happened to return -- producing an untyped DECISION_REQUIRED
(load_blocker=None) instead of TECHNICAL_ERROR.
"""
from __future__ import annotations

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


def _local_membership(employee_id: str, enabled: bool = True) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R14-1 -----------------------------------------------------------


def test_r14_1_existing_assignment_with_disabled_membership_is_not_feasible():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    existing = Assignment(
        "existing-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A", enabled=False),),
        shift_demands=(DEMAND_D,), existing_assignments=(existing,),
    )
    result = plan(state)
    assert result.status != "FEASIBLE"


# FINDING R14-2 -------------------------------------------------------------


def _fake_solve_always(status_name: str):
    def _fake(state, enforce_load_cap=True):
        return SolverOutcome(status_name, None, [], [], {}, [], {})
    return _fake


def test_r14_2a_unknown_status_is_technical_error_not_decision_required(monkeypatch):
    monkeypatch.setattr(engine_module, "solve", _fake_solve_always("UNKNOWN"))
    state = base_state(shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


def test_r14_2b_model_invalid_status_is_technical_error_not_decision_required(monkeypatch):
    monkeypatch.setattr(engine_module, "solve", _fake_solve_always("MODEL_INVALID"))
    state = base_state(shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


def test_r14_2c_uncapped_success_without_real_load_trigger_is_technical_error(monkeypatch):
    solved = Assignment(
        "solved-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    calls = {"count": 0}

    def _fake_solve(state, enforce_load_cap=True, allow_emergency_24h=False):
        calls["count"] += 1
        if enforce_load_cap:
            return SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})
        return SolverOutcome("OPTIMAL", [solved], [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake_solve)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert calls["count"] == 3


if __name__ == "__main__":
    print("test_audit_r14_findings module OK")
