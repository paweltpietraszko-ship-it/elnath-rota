"""Round-3 reproducer: do not discard an already-different valid REPLAN result."""
from __future__ import annotations

from rota.planning.engine_types import PlanningResult
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import base_state
from tests.test_t033_replan_must_differ import (
    EARLY_CUTOVER,
    _baseline,
    _demand_d,
    _employee,
    _membership,
)


def test_replan_keeps_valid_baseline_result_when_empty_current_schedule_means_it_is_already_different(monkeypatch):
    """After DECISION_REQUIRED no candidate was saved. Once an external
    window repairs the input, ordinary planning can already return the first
    real schedule. It is necessarily different from the empty current
    schedule and must not be discarded just because a redundant second solve
    reaches the shared deadline.
    """
    import rota.planning.engine as engine

    demand = _demand_d("D1", 5)
    candidate = _baseline("new-1", "A", demand)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand,), existing_assignments=(),
    )
    calls = []

    monkeypatch.setattr(
        engine,
        "_plan",
        lambda *_args, **_kwargs: PlanningResult("FEASIBLE", [[candidate]], None, None, []),
    )

    def redundant_timeout(*_args, **_kwargs):
        calls.append("second-solve")
        return SolverOutcome("UNKNOWN", None, [], [], {}, [], {}, optimization_complete=False)

    monkeypatch.setattr(engine, "solve", redundant_timeout)

    result = engine.plan_requiring_different_result_narrow(state, EARLY_CUTOVER)

    assert result.status == "FEASIBLE"
    assert result.optimization_complete is False
    assert result.candidates == [[candidate]]


def test_same_class_when_ordinary_result_completes_a_partial_current_schedule(monkeypatch):
    """Sibling path: filling a previously empty demand is also already a
    real change. The valid ordinary result must not be thrown away before a
    redundant diversity solve.
    """
    import rota.planning.engine as engine

    demand_1, demand_2 = _demand_d("D1", 5), _demand_d("D2", 6)
    existing = _baseline("old-1", "A", demand_1)
    added = _baseline("new-2", "B", demand_2)
    state = base_state(
        employees=(_employee("A"), _employee("B")),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_1, demand_2), existing_assignments=(existing,),
    )
    calls = []
    monkeypatch.setattr(
        engine,
        "_plan",
        lambda *_args, **_kwargs: PlanningResult("FEASIBLE", [[existing, added]], None, None, []),
    )

    def redundant_timeout(*_args, **_kwargs):
        calls.append("second-solve")
        return SolverOutcome("UNKNOWN", None, [], [], {}, [], {}, optimization_complete=False)

    monkeypatch.setattr(engine, "solve", redundant_timeout)

    result = engine.plan_requiring_different_result_narrow(state, EARLY_CUTOVER)

    assert result.status == "FEASIBLE"
    assert result.optimization_complete is False
    assert result.candidates == [[existing, added]]
