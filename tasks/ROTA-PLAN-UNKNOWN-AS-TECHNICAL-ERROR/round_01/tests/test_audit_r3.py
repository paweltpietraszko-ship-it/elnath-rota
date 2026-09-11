from __future__ import annotations

import pytest

import rota.planning.engine as engine
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import base_state


def _outcome(status: str) -> SolverOutcome:
    return SolverOutcome(status, None, [], [], {}, [], {}, optimization_complete=False)


@pytest.mark.parametrize(
    "dispatch",
    [
        lambda state, outcome, monkeypatch: engine._dispatch_or_continue(state, outcome),
        lambda state, outcome, monkeypatch: engine._dispatch_stage3(state, outcome),
        lambda state, outcome, monkeypatch: (
            monkeypatch.setattr(engine, "solve", lambda *_args, **_kwargs: outcome)
            or engine._resolve_without_load_cap(state)
        ),
    ],
)
@pytest.mark.parametrize(
    ("solver_status", "product_status"),
    [("UNKNOWN", "SEARCH_INCOMPLETE"), ("MODEL_INVALID", "TECHNICAL_ERROR")],
)
def test_all_three_plan_dispatches_split_timeout_from_failure(
    monkeypatch, dispatch, solver_status: str, product_status: str,
) -> None:
    result = dispatch(base_state(), _outcome(solver_status), monkeypatch)
    assert result is not None
    assert result.status == product_status
    assert result.candidates == []
    assert result.decision_payload is None
    if solver_status == "UNKNOWN":
        assert result.error_message is None
        assert result.optimization_complete is False
    else:
        assert result.error_message == "solver status: MODEL_INVALID"

