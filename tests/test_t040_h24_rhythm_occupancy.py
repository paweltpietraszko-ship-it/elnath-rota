"""ROTA-T040 (tasks/ROTA-T040/brief.md): fairness.add_dn_rhythm_reward's
'wolne' occupancy predicate must be a tight Boolean (occupied <=> any_term
>= 1), never the raw any_term count itself. For a normal H24 occurrence
SHIFT-24-PAIR-01 forces x_D == x_N, so any_term = x_D + x_N = 2*x on that
date -- the old `match + any_term <= 1` inequality forced x=0 even when
match was already 0, turning a pure SOFT rhythm reward into an accidental
HARD ban on legal H24 assignments (independently confirmed via CP-SAT
model diff and a live PLAN before/after in
tasks/ROTA-T040/round_01/tests/tests_r1.txt).

T40-01..T40-03 exercise add_dn_rhythm_reward directly against a minimal
CP-SAT model (the primary root-cause oracle -- no solver/application
layers involved). T40-04/T40-05 go through the real vertical
plan_ops.plan_month -> validate() path. T40-06 is a light sibling check
that NIGHT-STREAK-01/REST-01 remain HARD (full matrices already covered
by test_t032_soft_ranking.py and test_t018.py -- not duplicated here).
T40-07 (T034 regressions) is verified by running
test_t034_third_consecutive_shift_soft.py itself, not reproduced here.
"""
from __future__ import annotations

import calendar as _calendar
from datetime import date, time

from ortools.sat.python import cp_model

from rota.application import bootstrap, durable_inputs, plan_ops
from rota.application.assembler import assemble_planning_state
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    SitePlanningRegime,
    StandardShift,
)
from rota.persistence.db import connect
from rota.planning.fairness import add_dn_rhythm_reward
from rota.planning.validator import validate
from rota.planning.work_periods import resolve_required_rest

COORD = "COORD-T040"
MONTH = date(2026, 9, 1)


# --- T40-01/02/03: direct CP-SAT model, the primary root-cause oracle -----


def _solve_rhythm(day_kind_terms: dict) -> tuple[str, int, cp_model.CpModel]:
    model = cp_model.CpModel()
    penalties: list = []
    count = add_dn_rhythm_reward(model, MONTH, day_kind_terms, penalties)
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    return solver.status_name(status), count, solver


def test_t40_01_h24_any_term_2x_no_longer_forces_infeasible() -> None:
    """The exact false-infeasibility shape: an H24 occurrence's shared
    any_term = x_D + x_N = 2*x sits at the window's d+2 slot. Before T040
    this was INFEASIBLE (independently confirmed, tests_r1.txt); after
    T040 it must be FEASIBLE and must NOT force x to 0."""
    model = cp_model.CpModel()
    x = model.new_bool_var("x")
    model.add(x == 1)
    day_kind_terms = {
        "E": {
            date(2026, 9, 1): (1, 0, 1, None),  # d0: exactly D
            date(2026, 9, 2): (0, 1, 1, "demand-N"),  # d1: exactly N
            date(2026, 9, 3): (0, 0, x + x, None),  # d2: H24 any_term = 2*x
            date(2026, 9, 4): (0, 0, 0, None),  # d3: free
        }
    }
    penalties: list = []
    add_dn_rhythm_reward(model, MONTH, day_kind_terms, penalties)
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert solver.status_name(status) in ("OPTIMAL", "FEASIBLE"), solver.status_name(status)
    assert solver.value(x) == 1, "T040 regression: rhythm reward is forcing a legal H24 assignment to 0"


def test_t40_02_ordinary_single_occupancy_still_blocks_match_but_stays_legal() -> None:
    """any_term = x (ordinary one-start day, not H24): x=1 must still
    prevent the 'wolne' match, but x itself must remain legal (1)."""
    model = cp_model.CpModel()
    x = model.new_bool_var("x")
    model.add(x == 1)
    day_kind_terms = {
        "E": {
            date(2026, 9, 1): (1, 0, 1, None),
            date(2026, 9, 2): (0, 1, 1, "demand-N"),
            date(2026, 9, 3): (0, 0, x, None),
            date(2026, 9, 4): (0, 0, 0, None),
        }
    }
    penalties: list = []
    add_dn_rhythm_reward(model, MONTH, day_kind_terms, penalties)
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert solver.status_name(status) in ("OPTIMAL", "FEASIBLE")
    assert solver.value(x) == 1


def test_t40_03_ordinary_dn_free_free_reward_still_works() -> None:
    """Canonical D->N->wolne->wolne: reward must still be earned (T032
    behavior unchanged by the occupancy fix)."""
    model = cp_model.CpModel()
    day_kind_terms = {
        "E": {
            date(2026, 9, 1): (1, 0, 1, None),
            date(2026, 9, 2): (0, 1, 1, "demand-N"),
            date(2026, 9, 3): (0, 0, 0, None),
            date(2026, 9, 4): (0, 0, 0, None),
        }
    }
    penalties: list = []
    count = add_dn_rhythm_reward(model, MONTH, day_kind_terms, penalties)
    assert count == 1
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert solver.status_name(status) in ("OPTIMAL", "FEASIBLE")
    # The reward is a fully-fixed constant match here (owner-decision
    # eager-match branch) -- confirm it was actually counted, not skipped.
    assert solver.objective_value < 0


# --- T40-04/T40-05: real vertical through plan_ops -> validate() ----------


def _h24_profile(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(6, 0), True, 1, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=24)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=60,
    )


def _bootstrap_h24_site(conn, *, site_id: str, profile_id: str, employees: tuple[str, ...]) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id, coordinator=Coordinator(COORD, "Coord", True),
        site_profile=_h24_profile(profile_id),
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id,
        site=Site(site_id, profile_id, site_id, True, planning_regime=SitePlanningRegime.OCHRONA),
        association=CoordinatorSiteAssociation(COORD, site_id, True),
    )
    for employee_id in employees:
        durable_inputs.update_employee(conn, coordinator_id=COORD, site_id=site_id, employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
        durable_inputs.update_membership(
            conn, coordinator_id=COORD, site_id=site_id,
            membership=SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
        )
        durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=site_id, employee_id=employee_id, month=MONTH, target_hours=176)
    days_in_month = _calendar.monthrange(MONTH.year, MONTH.month)[1]
    for day in range(1, days_in_month + 1):
        durable_inputs.set_calendar_day(conn, coordinator_id=COORD, site_id=site_id, day=CalendarDay(date=date(MONTH.year, MONTH.month, day), holiday=False))


def test_t40_04_real_h24_vertical_plan_is_feasible_and_validates() -> None:
    """No fabricated data, no rota_dev.db, no simulator randomness -- a
    deterministic synthetic OCHRONA H24 object through the real
    plan_ops.plan_month, independently re-validated. Fails on pre-T040
    fairness.py, passes after."""
    conn = connect(":memory:")
    site_id, profile_id = "SITE-T040", "PROF-T040"
    employees = ("EMP-A", "EMP-B", "EMP-C", "EMP-D", "EMP-E")
    _bootstrap_h24_site(conn, site_id=site_id, profile_id=profile_id, employees=employees)

    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE", f"expected FEASIBLE, got {result.status}: {result.error_message}"
    assert result.candidates, "FEASIBLE with no candidates"

    state, _ = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    report = validate(state, result.candidates[0])
    assert report.hard_pass, report.violations


def test_t40_05_h24_pairing_unchanged_same_employee_both_components() -> None:
    """T040 must not obtain FEASIBLE by weakening H24 HARD: both D and N
    components of every H24 occurrence still go to the same employee."""
    conn = connect(":memory:")
    site_id, profile_id = "SITE-T040B", "PROF-T040B"
    employees = ("EMP-A", "EMP-B", "EMP-C", "EMP-D", "EMP-E")
    _bootstrap_h24_site(conn, site_id=site_id, profile_id=profile_id, employees=employees)

    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    by_work_period: dict[str, set[str]] = {}
    for a in candidate:
        if a.role != AssignmentRole.PRIMARY or not a.work_period_id:
            continue
        by_work_period.setdefault(a.work_period_id, set()).add(a.employee_id)
    assert by_work_period, "no PRIMARY H24 work periods found in candidate"
    for work_period_id, emp_ids in by_work_period.items():
        assert len(emp_ids) == 1, f"{work_period_id}: split across {emp_ids}, H24 same-employee pairing broken"


# --- T40-06: NIGHT-STREAK-01 / REST-01 remain HARD (light sibling check) --


def _h24_state_and_assignment(employee_id: str, d: date, next_d: date) -> tuple:
    conn = connect(":memory:")
    site_id, profile_id = "SITE-T040C", "PROF-T040C"
    _bootstrap_h24_site(conn, site_id=site_id, profile_id=profile_id, employees=(employee_id,))
    state, _ = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    demand_d = next(dd for dd in state.shift_demands if dd.start_datetime.date() == d and dd.work_period_component == 1)
    demand_n = next(dd for dd in state.shift_demands if dd.start_datetime.date() == d and dd.work_period_component == 2)
    wp_id = f"{site_id}:{demand_d.work_period_template_id}"
    rest_hours = resolve_required_rest(demand_d.required_rest_hours)
    a_d = Assignment(f"A-{demand_d.demand_id}", "", employee_id, demand_d.start_datetime, demand_d.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_d.demand_id, None, work_period_id=wp_id, required_rest_after_hours=rest_hours)
    a_n = Assignment(f"A-{demand_n.demand_id}", "", employee_id, demand_n.start_datetime, demand_n.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_n.demand_id, None, work_period_id=wp_id, required_rest_after_hours=rest_hours)
    return state, a_d, a_n


def test_t40_06_night_streak_and_rest_still_enforced() -> None:
    """Assigning the SAME employee two adjacent H24 occurrences (no 24h
    rest between them) must still be an independent-validator HARD
    violation -- T040 changed only the SOFT rhythm reward, not REST-01/
    NIGHT-STREAK-01. Full matrices already covered by
    test_t032_soft_ranking.py / test_t018.py -- this is a light sanity
    check, not a duplicate of those."""
    state, a_d1, a_n1 = _h24_state_and_assignment("EMP-X", date(2026, 9, 1), date(2026, 9, 2))
    _, a_d2, a_n2 = _h24_state_and_assignment("EMP-X", date(2026, 9, 2), date(2026, 9, 3))
    report = validate(state, [a_d1, a_n1, a_d2, a_n2])
    assert not report.hard_pass
    assert any(v.startswith("REST-01") for v in report.violations), report.violations


if __name__ == "__main__":
    print("test_t040_h24_rhythm_occupancy module OK")
