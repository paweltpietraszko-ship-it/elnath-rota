"""Independent exact-SHA reproducers for ROTA-T032 implementation audit r5."""
from datetime import date

from ortools.sat.python import cp_model

from rota.domain import Employee, WorkBalance
from rota.planning import solver
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, base_state
from tests.test_t032_soft_ranking import _d_demand, _membership, _n_assignment, _n_demand


def _employees(*ids):
    return tuple(Employee(e, e, date(2020, 1, 1), None, False) for e in ids)


def _hours_and_deviation(result, targets):
    hours = {employee_id: 0 for employee_id in targets}
    for assignment in result.candidates[0]:
        hours[assignment.employee_id] += int(
            (assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600
        )
    return hours, sum(abs(hours[e] - target) for e, target in targets.items())


def test_owner_corrected_target_priority_is_real():
    targets = {"A": 1, "B": 1, "C": 3}
    employees = _employees(*targets)
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_d_demand(1), _d_demand(5)),
        work_balances=tuple(
            WorkBalance(employee_id, MONTH, target, 0, 0, 0, 0, 0)
            for employee_id, target in targets.items()
        ),
    )
    result = plan(state)
    hours, deviation = _hours_and_deviation(result, targets)
    print("target-priority", hours, deviation)
    assert deviation == 21


def test_boundary_night_is_enforced_by_real_solver_and_validator():
    employees = _employees("A", "B")
    boundary = _n_assignment("A", 30, month=date(2026, 9, 1))
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_n_demand(1), _n_demand(2)),
        boundary_assignments=(boundary,),
        boundary_shift_demands=(_n_demand(30, month=date(2026, 9, 1)),),
        work_balances=(
            WorkBalance("A", MONTH, 24, 0, 0, 0, 0, 0),
            WorkBalance("B", MONTH, 24, 0, 0, 0, 0, 0),
        ),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    a_dates = {a.start_datetime.date() for a in result.candidates[0] if a.employee_id == "A"}
    assert not ({date(2026, 10, 1), date(2026, 10, 2)} <= a_dates)
    assert validate(state, result.candidates[0]).hard_pass


def test_timeout_while_looking_for_variant_keeps_first_candidate(monkeypatch):
    employees = _employees("A", "B")
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_d_demand(1),),
        work_balances=(
            WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),
            WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0),
        ),
    )
    real_run = solver._run_solver
    calls = 0

    def run_then_timeout(model, time_limit_seconds=solver.SOLVER_TIME_LIMIT_SECONDS, search_attempt=0):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_run(model, 1.0, search_attempt)
        return cp_model.CpSolver(), cp_model.UNKNOWN

    monkeypatch.setattr(solver, "_run_solver", run_then_timeout)
    outcome = solver.solve(state, enforce_load_cap=True)
    print("variant-timeout", outcome.status_name, outcome.assignments, outcome.optimization_complete)
    assert outcome.assignments is not None
    assert outcome.optimization_complete is False
    assert validate(state, outcome.assignments).hard_pass


def test_final_soft_feasible_incumbent_is_preserved(monkeypatch):
    employees = _employees("A", "B")
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_d_demand(1),),
        work_balances=(
            WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),
            WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0),
        ),
    )
    real_run = solver._run_solver

    def solved_but_unproven(model, time_limit_seconds=solver.SOLVER_TIME_LIMIT_SECONDS, search_attempt=0):
        solved, status = real_run(model, 1.0, search_attempt)
        assert status == cp_model.OPTIMAL
        return solved, cp_model.FEASIBLE

    monkeypatch.setattr(solver, "_run_solver", solved_but_unproven)
    outcome = solver.solve(state, enforce_load_cap=True)
    assert outcome.assignments is not None
    assert outcome.optimization_complete is False
    assert validate(state, outcome.assignments).hard_pass


def test_unknown_before_any_candidate_is_incomplete(monkeypatch):
    employees = _employees("A", "B")
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_d_demand(1),),
        work_balances=(
            WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),
            WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0),
        ),
    )
    monkeypatch.setattr(
        solver,
        "_run_solver",
        lambda *args, **kwargs: (cp_model.CpSolver(), cp_model.UNKNOWN),
    )
    outcome = solver.solve(state, enforce_load_cap=True)
    assert outcome.assignments is None
    assert outcome.optimization_complete is False


def test_large_search_attempt_is_safely_mapped_not_a_raw_exception():
    employees = _employees("A", "B")
    state = base_state(
        employees=employees,
        memberships=tuple(_membership(e.employee_id) for e in employees),
        shift_demands=(_d_demand(1),),
        work_balances=(
            WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),
            WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0),
        ),
    )
    result = plan(state, search_attempt=2**40)
    assert result.status == "FEASIBLE"
    assert validate(state, result.candidates[0]).hard_pass
