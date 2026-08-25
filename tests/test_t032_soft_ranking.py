"""ROTA-T032: NIGHT-STREAK-01 HARD (max two consecutive N), target equity and
D/N/wolne/wolne SOFT ranking, search_attempt passthrough.

Owner-corrected contract (tasks/ROTA-T032/brief.md @ 2d609c0), then further
corrected live 2026-08-25: the strict "prove TARGET-01 OPTIMAL, freeze, then
optimize equity/rhythm" two-phase design was replaced by ONE combined
weighted objective (isolated measurement: the two-phase split alone took a
5-employee/62-demand fixture from 0.37s OPTIMAL to 30s+ unproven FEASIBLE for
the exact same terms) -- the coordinator, not the solver, decides whether a
FEASIBLE candidate is good enough (existing T017 1-3 candidates + REPLAN),
so `optimization_complete=False` is an honest, expected outcome, never an
error to work around with an arbitrary sub-budget.
"""
from __future__ import annotations

import calendar as calendar_module
from dataclasses import replace
from datetime import date, datetime, timedelta

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.planning.decision_guidance import _BUILT_IN_CONDITION_TEXT
from rota.planning.engine import plan
from rota.planning.engine_types import PlanningResult
from rota.planning.solver import solve
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, ReadinessSource, ReadinessState, SITE_ID, base_state


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _n_demand(day: int, month: date = MONTH) -> ShiftDemand:
    start = datetime(month.year, month.month, day, 17, 0)
    return ShiftDemand(f"{month.isoformat()[:7]}-{day:02d}-N", "test-v1", start, start + timedelta(hours=12), 1)


def _d_demand(day: int, month: date = MONTH) -> ShiftDemand:
    start = datetime(month.year, month.month, day, 5, 0)
    return ShiftDemand(f"{month.isoformat()[:7]}-{day:02d}-D", "test-v1", start, start + timedelta(hours=12), 1)


def _n_assignment(employee_id: str, day: int, month: date = MONTH, state: AssignmentState = AssignmentState.PLANNED) -> Assignment:
    demand = _n_demand(day, month)
    return Assignment(
        f"a-{demand.demand_id}-{employee_id}", "test-v1", employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, state, False, demand.demand_id, None,
    )


def _full_month_calendar(month: date) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


# --- NIGHT-STREAK-01 HARD ---------------------------------------------------


def test_t32_n1_two_consecutive_n_legal_three_blocked():
    """N/N legal for one employee; a validator re-check of an injected N/N/N
    (day 3 forced onto the same employee) must fail with NIGHT-STREAK-01."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    two_nights = (_n_assignment("A", 1), _n_assignment("A", 2))
    two_demands = (_n_demand(1), _n_demand(2))
    state = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=two_nights, shift_demands=two_demands)
    report = validate(state, list(two_nights))
    assert not any(d.rule == "NIGHT-STREAK-01" for d in report.violation_details)

    three_nights = two_nights + (_n_assignment("A", 3),)
    three_demands = two_demands + (_n_demand(3),)
    state3 = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=three_nights, shift_demands=three_demands)
    report3 = validate(state3, list(three_nights))
    assert any(d.rule == "NIGHT-STREAK-01" for d in report3.violation_details)


def test_t32_n3_d_n_n_and_n_gap_n_are_not_a_streak():
    """D,N,N (day1 D not N) and N,gap,N (a day off in between) must never be
    flagged -- only three literal consecutive N start dates count."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    d1 = _d_demand(1)
    d_then_two_n = (
        Assignment("a-d1", "test-v1", "A", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d1.demand_id, None),
        _n_assignment("A", 2), _n_assignment("A", 3),
    )
    demands1 = (d1, _n_demand(2), _n_demand(3))
    state = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=d_then_two_n, shift_demands=demands1)
    report = validate(state, list(d_then_two_n))
    assert not any(v.rule == "NIGHT-STREAK-01" for v in report.violation_details)

    n_gap_n = (_n_assignment("A", 1), _n_assignment("A", 3))
    demands2 = (_n_demand(1), _n_demand(3))
    state2 = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=n_gap_n, shift_demands=demands2)
    report2 = validate(state2, list(n_gap_n))
    assert not any(v.rule == "NIGHT-STREAK-01" for v in report2.violation_details)


def test_t32_n5_trainee_and_cancelled_do_not_create_n():
    """A TRAINEE assignment and a CANCELLED PRIMARY on N never count toward
    the streak, even three in a row."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    trainee = replace(_n_assignment("A", 1), role=AssignmentRole.TRAINEE, mentor_primary_assignment_id="other")
    cancelled = replace(_n_assignment("A", 2), state=AssignmentState.CANCELLED)
    real_n = _n_assignment("A", 3)
    assignments = (trainee, cancelled, real_n)
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    state = base_state(employees=(employee,), memberships=(_membership("A"),), existing_assignments=assignments, shift_demands=demands)
    report = validate(state, list(assignments))
    assert not any(v.rule == "NIGHT-STREAK-01" for v in report.violation_details)


def test_t32_n2_boundary_assignment_extends_streak_across_month():
    """A persisted N on the last day of the PREVIOUS month plus two N's at
    the start of the current month is a three-in-a-row streak too."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    prev_month = date(2026, 9, 1)
    boundary_n = _n_assignment("A", 30, month=prev_month)
    boundary_demand = _n_demand(30, month=prev_month)
    two_nights = (_n_assignment("A", 1), _n_assignment("A", 2))
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), existing_assignments=two_nights,
        shift_demands=(_n_demand(1), _n_demand(2)),
        boundary_assignments=(boundary_n,), boundary_shift_demands=(boundary_demand,),
    )
    report = validate(state, list(two_nights))
    assert any(v.rule == "NIGHT-STREAK-01" for v in report.violation_details)


def test_t32_n_decision_guidance_label_present():
    assert _BUILT_IN_CONDITION_TEXT["NIGHT-STREAK-01"] == "Koliduje z limitem dwóch nocek pod rząd"


def test_t32_night_streak_blocks_solver_from_producing_three_in_a_row():
    """Real solve() with only one eligible employee and three N demands (no
    D, no coverage alternative) must never return three consecutive N's --
    NIGHT-STREAK-01 is wired as an actual CP-SAT HARD constraint, not only
    validated after the fact."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    outcome = solve(state, enforce_load_cap=False)
    if outcome.assignments is not None:
        report = validate(state, outcome.assignments)
        assert not any(v.rule == "NIGHT-STREAK-01" for v in report.violation_details)
    else:
        # A single employee cannot cover three mandatory N's without ever
        # exceeding the limit -- INFEASIBLE (surfaced by engine.py as
        # DECISION_REQUIRED, not a solver bug) is the only other legal outcome.
        assert outcome.status_name == "INFEASIBLE"


def test_t32_n7_night_streak_conflict_is_decision_required_not_technical_error():
    """A genuinely unsolvable NIGHT-STREAK-01 conflict (one employee, three
    mandatory N's, no alternative) must reach DECISION_REQUIRED with a
    NIGHT-STREAK-01 blocker -- never TECHNICAL_ERROR, never mislabelled REST-01."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload is not None
    assert any(b.condition == _BUILT_IN_CONDITION_TEXT["NIGHT-STREAK-01"] for b in result.decision_payload.blockers)


# --- optimization_complete / PlanningResult backward compatibility ---------


def test_t32_t8_optimization_complete_defaults_true_old_constructors_still_valid():
    old_style = PlanningResult("FEASIBLE", [], None, None, [])
    assert old_style.optimization_complete is True


def test_t32_optimization_complete_reflects_real_solve_status():
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demand = _d_demand(1)
    work_balances = (WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand,), work_balances=work_balances)
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.optimization_complete is True


# --- search_attempt: seed/order only, never the model ----------------------


def test_t32_c3_search_attempt_never_changes_hard_validity():
    employee_a = Employee("A", "A", date(2020, 1, 1), None, False)
    employee_b = Employee("B", "B", date(2020, 1, 1), None, False)
    demand = _d_demand(1)
    work_balances = (WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand,), work_balances=work_balances,
    )
    for attempt in (0, 1, 2):
        outcome = solve(state, search_attempt=attempt)
        assert outcome.assignments is not None
        report = validate(state, outcome.assignments)
        assert report.hard_pass


# --- Target equity ------------------------------------------------------


def test_t32_a4_zero_target_does_not_crash_or_divide_by_zero():
    employee_zero = Employee("Z", "Z", date(2020, 1, 1), None, False)
    employee_other = Employee("O", "O", date(2020, 1, 1), None, False)
    demand = _d_demand(1)
    work_balances = (WorkBalance("Z", MONTH, 0, 0, 0, 0, 0, 0), WorkBalance("O", MONTH, 12, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_zero, employee_other), memberships=(_membership("Z"), _membership("O")),
        shift_demands=(demand,), work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"


def test_t32_a6_equal_targets_more_even_split_than_unweighted_baseline():
    """Four employees, equal targets, demand exceeds what any one person
    should take alone -- the real solve (equity active) must not concentrate
    almost everything on a single employee while others get ~nothing."""
    employees = tuple(Employee(e, e, date(2020, 1, 1), None, False) for e in ("A", "B", "C", "D"))
    memberships = tuple(_membership(e.employee_id) for e in employees)
    demands = tuple(_d_demand(day) for day in range(1, 9))  # 8 x 12h = 96h total
    work_balances = tuple(WorkBalance(e.employee_id, MONTH, 24, 0, 0, 0, 0, 0) for e in employees)  # 24h each, sums to 96h exactly
    state = base_state(employees=employees, memberships=memberships, shift_demands=demands, work_balances=work_balances)
    result = plan(state)
    assert result.status == "FEASIBLE"
    hours_by_employee: dict[str, int] = {}
    for a in result.candidates[0]:
        hours_by_employee[a.employee_id] = hours_by_employee.get(a.employee_id, 0) + 12
    # Perfectly matchable (4 x 24h == 96h) -- equity must find the even split, not a skewed one.
    assert all(hours_by_employee.get(e.employee_id, 0) == 24 for e in employees)


if __name__ == "__main__":
    print("test_t032_soft_ranking module OK")
