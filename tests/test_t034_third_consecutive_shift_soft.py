"""ROTA-T034 (contract SHA f4a1e0b, Codex preimplementation PASS on e33d739):
SOFT ranking penalty for a third consecutive day-shift-adjacent sequence
(D/D/D, D/D/N, D/N/N) sharing solver.py::_build_day_kind_terms's existing
D/N classification -- never a second classifier, never HARD, never
DECISION_REQUIRED, never a validator rejection. N/N/N stays exclusively the
pre-existing NIGHT-STREAK-01 HARD rule.

T34-01..T34-09 exercise fairness.add_third_consecutive_shift_penalty
directly against hand-built day_kind_terms dicts -- this is the same shape
solver.py._build_day_kind_terms produces, so no second boundary reader is
implied by testing it this way. T34-10/T34-11 exercise the real vertical
wiring through rota.planning.engine.plan()/solver.solve(). T34-12 (existing
T032/T033 regressions for rhythm, NIGHT-STREAK-01, optimization_complete,
search_attempt stay green) is verified by running
tests/test_t032_soft_ranking.py and tests/test_t033_replan_must_differ.py
unchanged -- their matrices are deliberately not copied here."""
from __future__ import annotations

from datetime import date, timedelta

from ortools.sat.python import cp_model

from rota.domain import Employee, WorkBalance
from rota.planning.engine import plan
from rota.planning.fairness import add_third_consecutive_shift_penalty
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, base_state
from tests.test_t032_soft_ranking import _d_demand, _membership, _n_assignment, _n_demand

_EMPTY = (0, 0, 0, None)


def _solve_min_penalty(model, day_kind_terms, extra_constraints=None, month=MONTH):
    """Round-2 audit FINDING 1 fix: this must receive the SAME CpModel the
    caller already built its decision variables on -- CP-SAT variables are
    model-scoped by integer index, so building a second, fresh CpModel here
    (as an earlier version of this helper did) and reusing variable objects
    from the caller's model on it silently aliases unrelated variables and
    proves nothing about the caller's actual constraints."""
    penalties = []
    count = add_third_consecutive_shift_penalty(model, month, day_kind_terms, penalties)
    if extra_constraints:
        extra_constraints(model)
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    objective = sum(solver.value(p) for p in penalties) if penalties else 0
    return count, objective, solver


# --- T34-01/02/03: ranking prefers avoiding each of the three sequences ----


def test_t34_01_ranking_prefers_split_over_ddd():
    """Two employees, either could take all three D-shift days. Splitting
    them (no one gets D/D/D) must score strictly lower than concentrating
    all three on one employee."""
    model = cp_model.CpModel()
    choice = [model.new_bool_var(f"c{i}") for i in range(3)]  # 1 == "A works day i (as D)"
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {
        "A": {dates[i]: (choice[i], 0, choice[i], None) for i in range(3)},
        "B": {dates[i]: (1 - choice[i], 0, 1 - choice[i], None) for i in range(3)},
    }
    count, objective, solver = _solve_min_penalty(model, day_kind_terms)
    assert count == 2  # one bad_window candidate per employee
    assert objective == 0
    values = [solver.value(c) for c in choice]
    assert values not in ([1, 1, 1], [0, 0, 0])


def test_t34_02_ranking_prefers_split_over_ddn():
    """Same shape as T34-01 but day 3 is an N shift instead of D -- D/D/N
    must be avoided the same way."""
    model = cp_model.CpModel()
    choice = [model.new_bool_var(f"c{i}") for i in range(3)]
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {
        "A": {
            dates[0]: (choice[0], 0, choice[0], None),
            dates[1]: (choice[1], 0, choice[1], None),
            dates[2]: (0, choice[2], choice[2], None),  # day 3 is N when choice[2]==1
        },
        "B": {
            dates[0]: (1 - choice[0], 0, 1 - choice[0], None),
            dates[1]: (1 - choice[1], 0, 1 - choice[1], None),
            dates[2]: (0, 1 - choice[2], 1 - choice[2], None),
        },
    }
    count, objective, solver = _solve_min_penalty(model, day_kind_terms)
    assert count == 2
    assert objective == 0
    values = [solver.value(c) for c in choice]
    assert values not in ([1, 1, 1], [0, 0, 0])


def test_t34_03_ranking_prefers_split_over_dnn():
    """Days 2 and 3 are N shifts -- D/N/N must be avoided the same way."""
    model = cp_model.CpModel()
    choice = [model.new_bool_var(f"c{i}") for i in range(3)]
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {
        "A": {
            dates[0]: (choice[0], 0, choice[0], None),
            dates[1]: (0, choice[1], choice[1], None),
            dates[2]: (0, choice[2], choice[2], None),
        },
        "B": {
            dates[0]: (1 - choice[0], 0, 1 - choice[0], None),
            dates[1]: (0, 1 - choice[1], 1 - choice[1], None),
            dates[2]: (0, 1 - choice[2], 1 - choice[2], None),
        },
    }
    count, objective, solver = _solve_min_penalty(model, day_kind_terms)
    assert count == 2
    assert objective == 0
    values = [solver.value(c) for c in choice]
    assert values not in ([1, 1, 1], [0, 0, 0])


# --- T34-04: one window never contributes more than one penalty -----------


def test_t34_04_one_window_contributes_at_most_one_penalty():
    """day3's d_term and n_term are (artificially, for this unit test) the
    same free variable -- both D/D/D and D/D/N are simultaneously
    recognizable, but only ONE bad_window variable may be created for the
    window, and forcing it to 1 must cost exactly 1, never 2."""
    model = cp_model.CpModel()
    v = model.new_bool_var("v")
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {
        "A": {
            dates[0]: (1, 0, 1, None),  # fixed D
            dates[1]: (1, 0, 1, None),  # fixed D
            dates[2]: (v, v, v, None),  # simultaneously "D" and "N" when v==1
        },
    }
    count, objective, _ = _solve_min_penalty(model, day_kind_terms, extra_constraints=lambda m: m.add(v == 1))
    assert count == 1
    assert objective == 1


# --- T34-05/T34-06: month-boundary windows use existing facts only --------


def test_t34_05_boundary_persisted_dd_plus_current_day_either_kind():
    """Two persisted D days just before the month start, plus a single
    free current-month day that could be D or N -- either choice must
    trigger the penalty (D/D/D or D/D/N), using only the already-present
    day_kind_terms facts (no second history read)."""
    d_minus2 = MONTH - timedelta(days=2)
    d_minus1 = MONTH - timedelta(days=1)

    for forced_kind in ("d", "n"):
        model = cp_model.CpModel()
        cur_d = model.new_bool_var("cur_d")
        cur_n = model.new_bool_var("cur_n")
        model.add(cur_d + cur_n == 1)
        if forced_kind == "d":
            model.add(cur_d == 1)
        else:
            model.add(cur_n == 1)
        day_kind_terms = {
            "A": {
                d_minus2: (1, 0, 1, None),
                d_minus1: (1, 0, 1, None),
                MONTH: (cur_d, cur_n, cur_d + cur_n, None),
            },
        }
        penalties = []
        add_third_consecutive_shift_penalty(model, MONTH, day_kind_terms, penalties)
        assert penalties
        model.minimize(sum(penalties))
        solver = cp_model.CpSolver()
        status = solver.solve(model)
        assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        objective = sum(solver.value(p) for p in penalties)
        assert objective == 1, f"forced_kind={forced_kind} must still trigger the boundary penalty"


def test_t34_06_boundary_persisted_single_d_plus_current_two_days():
    """Round-2 audit FINDING 2 fix: the window must be three literally
    CONSECUTIVE dates (month_start-1, month_start, month_start+1) -- an
    earlier version used month_start-2, skipping month_start-1 entirely,
    so it silently tested a non-adjacent, always-impossible shape while
    still asserting count == 0 (true for the wrong reason). A single
    persisted D the day before the month start, plus the first two
    in-month days as real decision variables forced in turn to D/D, D/N
    or N/N, must trigger the corresponding penalty (objective == 1) each
    time -- mirrors T34-05's pattern, forcing on ONE model rather than
    trusting an all-fixed skip."""
    d_minus1 = MONTH - timedelta(days=1)
    d0 = MONTH
    d1 = MONTH + timedelta(days=1)
    for day0_kind, day1_kind in (("d", "d"), ("d", "n"), ("n", "n")):
        model = cp_model.CpModel()
        cur_d0 = model.new_bool_var("cur_d0")
        cur_n0 = model.new_bool_var("cur_n0")
        cur_d1 = model.new_bool_var("cur_d1")
        cur_n1 = model.new_bool_var("cur_n1")
        model.add(cur_d0 + cur_n0 == 1)
        model.add(cur_d1 + cur_n1 == 1)
        model.add(cur_d0 == 1 if day0_kind == "d" else cur_n0 == 1)
        model.add(cur_d1 == 1 if day1_kind == "d" else cur_n1 == 1)
        day_kind_terms = {
            "A": {
                d_minus1: (1, 0, 1, None),
                d0: (cur_d0, cur_n0, cur_d0 + cur_n0, None),
                d1: (cur_d1, cur_n1, cur_d1 + cur_n1, None),
            },
        }
        penalties = []
        count = add_third_consecutive_shift_penalty(model, MONTH, day_kind_terms, penalties)
        assert count >= 1
        model.minimize(sum(penalties))
        solver = cp_model.CpSolver()
        status = solver.solve(model)
        assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        objective = sum(solver.value(p) for p in penalties)
        assert objective == 1, f"{day0_kind}/{day1_kind} must trigger the boundary penalty"


# --- T34-07/T34-08: missing facts and two-in-a-row are never penalized ----


def test_t34_07_missing_boundary_fact_is_not_guessed():
    """Only the last day of a would-be window has any entry at all -- the
    first two dates are entirely absent from day_kind_terms (not merely
    zero-valued), and must never be treated as a guessed D or N."""
    d2 = MONTH + timedelta(days=2)
    day_kind_terms = {"A": {d2: (1, 0, 1, None)}}
    model = cp_model.CpModel()
    penalties = []
    count = add_third_consecutive_shift_penalty(model, MONTH, day_kind_terms, penalties)
    assert count == 0
    assert penalties == []


def test_t34_08_only_two_consecutive_shifts_never_penalized():
    """Two fixed D days with the third day genuinely free (no assignment
    at all, any_term == 0) must never create a penalty."""
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {
        "A": {
            dates[0]: (1, 0, 1, None),
            dates[1]: (1, 0, 1, None),
            dates[2]: _EMPTY,
        },
    }
    model = cp_model.CpModel()
    penalties = []
    count = add_third_consecutive_shift_penalty(model, MONTH, day_kind_terms, penalties)
    assert count == 0
    assert penalties == []


# --- T34-09: N/N/N is untouched by T034, stays NIGHT-STREAK-01 HARD only --


def test_t34_09_nnn_creates_no_t034_penalty_but_is_still_hard_blocked():
    dates = [MONTH + timedelta(days=i) for i in range(3)]
    day_kind_terms = {"A": {d: (0, 1, 1, None) for d in dates}}
    model = cp_model.CpModel()
    penalties = []
    count = add_third_consecutive_shift_penalty(model, MONTH, day_kind_terms, penalties)
    assert count == 0
    assert penalties == []

    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    three_nights = (_n_assignment("A", 1), _n_assignment("A", 2), _n_assignment("A", 3))
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    state = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=three_nights, shift_demands=demands)
    report = validate(state, list(three_nights))
    assert any(v.rule == "NIGHT-STREAK-01" for v in report.violation_details)


# --- T34-10: real vertical solve() wiring test -----------------------------


def test_t34_10_vertical_solve_prefers_split_over_all_on_one():
    """No target_hours at all (target_by_employee stays empty, so TARGET-01
    and equity contribute nothing) -- with two equally eligible employees
    and three D-shift demands, the only thing left to break the tie is
    T034: the result must not concentrate all three on a single employee."""
    employee_a = Employee("A", "A", date(2020, 1, 1), None, False)
    employee_b = Employee("B", "B", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_membership("A"), _membership("B")),
        shift_demands=demands,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    hours_by_employee: dict[str, int] = {}
    for a in result.candidates[0]:
        hours_by_employee[a.employee_id] = hours_by_employee.get(a.employee_id, 0) + 12
    assert hours_by_employee.get("A", 0) != 36
    assert hours_by_employee.get("B", 0) != 36


# --- T34-11: TARGET-01's mathematical protection covers the new SOFT too --


def test_t34_11_target01_priority_over_third_shift_penalty():
    """Employee A's target exactly matches all three D-shifts (36h);
    employee B's target is 0. The only assignment with zero total TARGET-01
    deviation is 'all three on A' -- which necessarily creates a D/D/D
    sequence. The solver must still pick it: a better T034 SOFT score
    (achieved by splitting, at the cost of 24h combined target deviation)
    must never win over TARGET-01."""
    employee_a = Employee("A", "A", date(2020, 1, 1), None, False)
    employee_b = Employee("B", "B", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 0, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_membership("A"), _membership("B")),
        shift_demands=demands, work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    hours_by_employee: dict[str, int] = {}
    for a in result.candidates[0]:
        hours_by_employee[a.employee_id] = hours_by_employee.get(a.employee_id, 0) + 12
    assert hours_by_employee.get("A", 0) == 36
    assert hours_by_employee.get("B", 0) == 0


if __name__ == "__main__":
    print("test_t034_third_consecutive_shift_soft module OK")
