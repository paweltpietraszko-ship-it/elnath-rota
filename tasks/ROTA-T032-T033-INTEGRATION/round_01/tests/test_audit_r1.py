"""Independent integration reproducers for accepted T032 + T033."""
from __future__ import annotations

from datetime import date, datetime

from api.routers.schedule import PlanRequest, _planning_result_out
from rota.domain import Employee, WorkBalance
from rota.persistence.db import connect
from rota.planning.engine import plan_requiring_different_result_narrow, plan_requiring_different_result_wide
from rota.planning.engine_types import PlanningResult
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import MONTH, base_state
from tests.test_t032_soft_ranking import _membership, _n_demand
from tests.test_t033_replan_must_differ import EARLY_CUTOVER


def _unknown() -> SolverOutcome:
    return SolverOutcome("UNKNOWN", None, [], [], {}, [], {}, optimization_complete=False)


def test_integration_timeout_from_narrow_baseline_is_marked_incomplete(monkeypatch):
    import rota.planning.engine as engine

    monkeypatch.setattr(
        engine,
        "_plan",
        lambda *_args, **_kwargs: PlanningResult(
            "TECHNICAL_ERROR", [], None, "solver status: UNKNOWN", [], optimization_complete=False,
        ),
    )

    result = plan_requiring_different_result_narrow(base_state(), EARLY_CUTOVER)

    assert result.status == "SEARCH_INCOMPLETE"
    assert result.optimization_complete is False


def test_integration_timeout_from_wide_search_is_marked_incomplete(monkeypatch):
    import rota.planning.engine as engine

    monkeypatch.setattr(engine, "solve", lambda *_args, **_kwargs: _unknown())

    result = plan_requiring_different_result_wide(base_state(), EARLY_CUTOVER)

    assert result.status == "SEARCH_INCOMPLETE"
    assert result.optimization_complete is False


def test_integration_api_exports_optimization_complete():
    conn = connect(":memory:")
    try:
        result = PlanningResult("FEASIBLE", [[]], None, None, [], optimization_complete=False)
        payload = _planning_result_out(conn, result).model_dump()
    finally:
        conn.close()

    assert payload["optimization_complete"] is False


def test_integration_plan_request_accepts_nonpersistent_search_attempt():
    payload = PlanRequest.model_validate({"effective_from": None, "search_attempt": 3})

    assert payload.search_attempt == 3


def test_integration_night_streak_diagnosis_survives_replan_merge():
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands,
        work_balances=(WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),),
    )

    result = plan_requiring_different_result_narrow(state, EARLY_CUTOVER)

    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload is not None
    assert any("dwóch nocek" in blocker.condition for blocker in result.decision_payload.blockers)
