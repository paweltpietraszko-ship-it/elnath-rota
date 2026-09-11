"""ROTA-PLAN-UNKNOWN-AS-TECHNICAL-ERROR (brief.md acceptance A1/A2/A4/A5):
first PLAN and Przelicz Plan share the exact same rota.planning.engine.plan()
entry point -- there is no separate server-side code path for "recompute"
versus "first plan" (the distinction lives only in the frontend's
effective_from argument, not in engine.py's dispatch). A1 and A2 are
therefore proven by the same engine-level call.
"""
from __future__ import annotations

from datetime import date, datetime

import rota.planning.engine as engine_module
from rota.domain import Assignment, AssignmentRole, AssignmentState, Employee, MembershipKind, ShiftDemand, SiteMembership
from rota.planning.engine import plan
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _fake_solve_always(status_name: str):
    def _fake(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False, **_kwargs):
        return SolverOutcome(status_name, None, [], [], {}, [], {})
    return _fake


# A1/A2 -----------------------------------------------------------------------


def test_a1_a2_unknown_without_candidate_is_search_incomplete_not_technical_error(monkeypatch):
    monkeypatch.setattr(engine_module, "solve", _fake_solve_always("UNKNOWN"))
    state = base_state(shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "SEARCH_INCOMPLETE"
    assert result.candidates == []
    assert result.decision_payload is None
    # optimization_complete must be False -- nothing was proven either way.
    assert result.optimization_complete is False


def test_a1_search_incomplete_never_produces_a_candidate_or_decision_payload(monkeypatch):
    """No fabricated candidate and no guessed DECISION_REQUIRED (the original
    R14-2 concern) -- an honest empty terminal result."""
    monkeypatch.setattr(engine_module, "solve", _fake_solve_always("UNKNOWN"))
    state = base_state(shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.candidates == []
    assert result.decision_payload is None
    assert result.error_message is None


# A4 ---------------------------------------------------------------------------


def test_a4_model_invalid_is_still_technical_error(monkeypatch):
    monkeypatch.setattr(engine_module, "solve", _fake_solve_always("MODEL_INVALID"))
    state = base_state(shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# A5 ---------------------------------------------------------------------------


def test_a5_feasible_with_incomplete_optimization_still_shows_candidate(monkeypatch):
    """FEASIBLE + optimization_complete=False must keep showing the found
    candidate, never reduced to an empty SEARCH_INCOMPLETE -- this is a
    completely disjoint code path (_evaluate_candidate/_feasible_result),
    untouched by the UNKNOWN->SEARCH_INCOMPLETE change, but the brief
    explicitly calls out that it must not regress."""
    solved = Assignment(
        "solved-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )

    def _fake_solve(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False, **_kwargs):
        return SolverOutcome("FEASIBLE", [solved], [], [], {}, [], {}, optimization_complete=False)

    monkeypatch.setattr(engine_module, "solve", _fake_solve)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.optimization_complete is False
    assert len(result.candidates) == 1
    assert result.candidates[0][0].employee_id == "A"


if __name__ == "__main__":
    print("test_plan_unknown_search_incomplete module OK")
