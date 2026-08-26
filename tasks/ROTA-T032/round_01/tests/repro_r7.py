"""Narrow independent reproducer for T032 correction 52212a6."""
from ortools.sat.python import cp_model

from rota.planning import solver as solver_module
from rota.planning.engine import plan
from tests.test_t017 import _symmetric_pool_state


def test_timeout_after_second_candidate_keeps_incomplete_flag(monkeypatch):
    real_run_solver = solver_module._run_solver
    call_count = 0

    def timeout_on_third(model, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        solved, status = real_run_solver(model, *args, **kwargs)
        if call_count == 3:
            return solved, cp_model.UNKNOWN
        return solved, status

    monkeypatch.setattr(solver_module, "_run_solver", timeout_on_third)
    result = plan(_symmetric_pool_state(6))

    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 2
    assert result.optimization_complete is False
