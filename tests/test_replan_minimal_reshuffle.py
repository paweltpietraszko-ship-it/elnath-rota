"""ROTA-T006 required test matrix (tasks/ROTA-T006/brief.md REQUIRED TEST MATRIX
A-I), verifying REPLAN-MIN-01 (arch/FROZEN_ADDENDUM_REPLAN_MIN_01.md).
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.planning.engine import plan
from rota.planning.replan_reshuffle import build_reshuffle_count_expr, redistributable_baseline_assignments
from rota.planning.solver import fixed_existing_assignments
from tests.support.minimal_state import MONTH, ReadinessSource, ReadinessState, SITE_ID, base_state


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _employee(employee_id: str, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2026, 9, 1), None, day_only)


def _demand_d(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _demand_n(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _baseline(assignment_id: str, employee_id: str, demand: ShiftDemand, frozen: bool = False) -> Assignment:
    return Assignment(
        assignment_id, "test-v1", employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, demand.demand_id, None,
    )


def _covering_pairs(assignments) -> set[tuple[str, str]]:
    return {(a.employee_id, a.covers_demand_id) for a in assignments if a.covers_demand_id}


def _balance(employee_id: str, target_hours: int) -> WorkBalance:
    return WorkBalance(employee_id, MONTH, target_hours, 0, 0, 0, 0, 0)


# A. ONE CHANGE BEATS BETTER SOFT --------------------------------------------


def test_a_one_change_beats_a_better_soft_two_change_swap():
    """Literal brief.md matrix A: an existing HARD-valid solution changes
    EXACTLY 1 baseline placement; a competing HARD-valid solution changes
    >=2 with better ordinary SOFT. The 1-change solution must win.

    demand4's baseline holder (D) is forced out unconditionally, so the
    achievable minimum can never be 0 -- the only real choice is between
    "1" (only D4 changes) and "3" (D4 changes AND the A/B swap below), not
    between "0" and "2"."""
    demand1, demand2, demand4 = _demand_d("D1", 1), _demand_d("D2", 2), _demand_d("D4", 4)
    baseline1, baseline2 = _baseline("orig-1", "A", demand1), _baseline("orig-2", "B", demand2)
    baseline4 = _baseline("orig-4", "D", demand4)
    # A has a LEAVE_PLAN collision on demand1 -- swapping A<->B removes that
    # SOFT penalty entirely, but requires changing BOTH baseline placements
    # on top of D4's already-mandatory change.
    leave_plan = AvailabilityRecord("lp1", "lp1v1", "A", AvailabilityKind.LEAVE_PLAN, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    d_gone = AvailabilityRecord("u1", "u1v1", "D", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 31), True, None, None)
    state = base_state(
        employees=(_employee("A"), _employee("B"), _employee("D"), _employee("E")),
        memberships=(_membership("A"), _membership("B"), _membership("D"), _membership("E")),
        shift_demands=(demand1, demand2, demand4), existing_assignments=(baseline1, baseline2, baseline4),
        availability_records=(leave_plan, d_gone),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    # What matters: A and B's OWN baselines are untouched despite the swap's
    # better SOFT score -- who ends up covering D4 (B taking a second shift,
    # or E) is an incidental tie-break between two equally 1-reshuffle
    # solutions, not part of what this test asserts.
    pairs = _covering_pairs(result.candidates[0])
    assert ("A", "D1") in pairs
    assert ("B", "D2") in pairs
    assert any(emp in ("B", "E") and dem == "D4" for emp, dem in pairs)


# B. ESCALATE ONLY WHEN NECESSARY --------------------------------------------


def test_b_escalates_to_two_changes_only_when_one_is_hard_infeasible():
    demand_n, demand_d2 = _demand_n("N1", 1), _demand_d("D2", 2)
    baseline_n, baseline_d2 = _baseline("orig-n", "A", demand_n), _baseline("orig-d2", "B", demand_d2)
    # A becomes fully unavailable -- only B can cover the vacated N-shift
    # (C is DAY_ONLY, ineligible for N), but B already holds the D-shift the
    # next morning: REST-01 forbids one employee holding both. The only
    # HARD-valid outcome moves B to the N-shift and hands the D-shift to C.
    gone = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 3), True, None, None)
    state = base_state(
        employees=(_employee("A"), _employee("B"), _employee("C", day_only=True)),
        memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(demand_n, demand_d2), existing_assignments=(baseline_n, baseline_d2),
        availability_records=(gone,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("B", "N1"), ("C", "D2")}


# C. SOFT BREAKS TIE ----------------------------------------------------------


def test_c_soft_ranking_breaks_a_tie_between_equal_reshuffle_counts():
    demand1, demand2, demand3 = _demand_d("D1", 1), _demand_d("D2", 2), _demand_d("D3", 3)
    baseline2, baseline3 = _baseline("orig-2", "B", demand2), _baseline("orig-1", "A", demand1)
    baseline_c = _baseline("orig-3", "C", demand3)
    gone = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    # Both B and C are free to also take the vacated demand1 -- either choice
    # is a 1-reshuffle solution (only demand1's baseline changes). B's target
    # exactly matches taking it on (24h); C's does not (would overshoot).
    state = base_state(
        employees=(_employee("A"), _employee("B"), _employee("C")),
        memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(demand1, demand2, demand3), existing_assignments=(baseline_c, baseline2, baseline3),
        availability_records=(gone,), work_balances=(_balance("B", 24), _balance("C", 12)),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    pairs = _covering_pairs(result.candidates[0])
    assert ("B", "D1") in pairs
    assert ("B", "D2") in pairs
    assert ("C", "D3") in pairs


# D. ABSENCE IS NOT SPECIAL ---------------------------------------------------


def test_d_minimal_reshuffle_also_applies_to_a_non_absence_trigger():
    """Same shape as an absence-forced vacancy, but the trigger is
    LEAVE_GRANTED (an approved-leave decision, not sickness/absence) --
    confirms the mechanism reacts to eligibility loss generically, not to
    one hardcoded AvailabilityKind."""
    demand1, demand2 = _demand_d("D1", 1), _demand_d("D2", 2)
    baseline1, baseline2 = _baseline("orig-1", "A", demand1), _baseline("orig-2", "B", demand2)
    granted_leave = AvailabilityRecord("lg1", "lg1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(_employee("A"), _employee("B"), _employee("C")),
        memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(demand1, demand2), existing_assignments=(baseline1, baseline2),
        availability_records=(granted_leave,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    pairs = _covering_pairs(result.candidates[0])
    assert ("C", "D1") in pairs
    assert ("B", "D2") in pairs  # B's baseline untouched


# E. REALIZED / FROZEN --------------------------------------------------------


def test_e_frozen_and_realized_assignments_are_excluded_from_the_baseline_set():
    demand1 = _demand_d("D1", 1)
    frozen = _baseline("frozen-1", "A", demand1, frozen=True)
    realized = _baseline("realized-1", "B", _demand_d("D2", 2))
    realized = Assignment(**{**realized.__dict__, "state": AssignmentState.REALIZED})
    redistributable = _baseline("orig-3", "C", _demand_d("D3", 3))
    state = base_state(existing_assignments=(frozen, realized, redistributable))
    baseline = redistributable_baseline_assignments(state)
    assert [a.assignment_id for a in baseline] == ["orig-3"]


def test_e_replan_still_leaves_frozen_and_realized_untouched():
    demand1, demand2, demand3 = _demand_d("D1", 1), _demand_d("D2", 2), _demand_d("D3", 3)
    frozen = _baseline("frozen-1", "A", demand1, frozen=True)
    realized_raw = _baseline("realized-1", "A", demand2)
    realized = Assignment(**{**realized_raw.__dict__, "state": AssignmentState.REALIZED})
    redistributable = _baseline("orig-3", "B", demand3)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand1, demand2, demand3), existing_assignments=(frozen, realized, redistributable),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert frozen in result.candidates[0]
    assert realized in result.candidates[0]


# F. SAME PERSON / SAME DEMAND -------------------------------------------------


def test_f_reshuffle_count_ignores_assignment_id_when_employee_and_demand_match():
    """A baseline Assignment's own row id ("orig-1", arbitrary/technical) has
    no bearing on the count -- only whether the same employee still covers
    the same demand does."""
    from ortools.sat.python import cp_model

    demand1 = _demand_d("D1", 1)
    baseline = _baseline("orig-1", "A", demand1)
    model = cp_model.CpModel()
    x = {("A", "D1"): model.new_bool_var("x")}
    model.add(x[("A", "D1")] == 1)
    expr = build_reshuffle_count_expr(x, [baseline])
    solver = cp_model.CpSolver()
    solver.solve(model)
    assert solver.value(expr) == 0


# G. NEW DEMAND ----------------------------------------------------------------


def test_g_new_demand_without_baseline_is_not_itself_a_reshuffle():
    demand1, demand2 = _demand_d("D1", 1), _demand_d("D2", 2)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand1, demand2), existing_assignments=(baseline1,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    pairs = _covering_pairs(result.candidates[0])
    assert ("A", "D1") in pairs  # untouched baseline
    assert any(emp == "B" and dem == "D2" for emp, dem in pairs)


# H. INITIAL PLAN UNAFFECTED --------------------------------------------------


def test_h_no_existing_assignments_means_no_reshuffle_machinery_at_all():
    state = base_state()
    assert redistributable_baseline_assignments(state) == []


def test_h_initial_planning_keeps_ordinary_soft_ranking_unchanged():
    demand_sat, demand_sun = _demand_d("SAT", 3), _demand_d("SUN", 4)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_sat, demand_sun),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert {a.employee_id for a in result.candidates[0]} == {"A", "B"}


# I. STATUS BOUNDARIES ---------------------------------------------------------


def test_i_decision_required_is_not_bypassed_to_hunt_for_a_smaller_reshuffle():
    demand1 = _demand_d("D1", 1)
    # required_primary_count=2 with only one eligible employee -> a genuine
    # staffing shortfall (NO_ELIGIBLE_EMPLOYEE), independent of demand1.
    understaffed = ShiftDemand("D2", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 2)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand1, understaffed), existing_assignments=(baseline1,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def test_i_infeasible_phase1_routes_to_existing_conflict_handling():
    """A rigorous phase-1 INFEASIBLE (the HARD model itself has no valid
    schedule, not just an unproven minimum) must still reach
    DECISION_REQUIRED via the existing conflict-detection path, not
    TECHNICAL_ERROR -- distinguishes INFEASIBLE from the FEASIBLE/UNKNOWN/
    MODEL_INVALID fail-closed cases below."""
    demand_n, demand_d2 = _demand_n("N1", 1), _demand_d("D2", 2)
    baseline_n, baseline_d2 = _baseline("orig-n", "A", demand_n), _baseline("orig-d2", "B", demand_d2)
    gone = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 3), True, None, None)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_n, demand_d2), existing_assignments=(baseline_n, baseline_d2),
        availability_records=(gone,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def _replan_state_with_baseline():
    demand1 = _demand_d("D1", 1)
    baseline1 = _baseline("orig-1", "A", demand1)
    return base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand1,), existing_assignments=(baseline1,),
    )


def _assert_phase1_status_fails_closed(monkeypatch, forced_status_name: str, expected_status: str = "TECHNICAL_ERROR"):
    """Regression for FINDING R2-1: forces solver.py's phase-1 _run_solver
    call to return the given non-OPTIMAL, non-INFEASIBLE status and
    confirms plan() fails closed to `expected_status` instead of treating an
    unproven incumbent as the proven reshuffle minimum. ROTA-PLAN-UNKNOWN-
    AS-TECHNICAL-ERROR: UNKNOWN's own fail-closed result is now
    SEARCH_INCOMPLETE, not TECHNICAL_ERROR -- FEASIBLE-without-proof and
    MODEL_INVALID are unaffected and keep the default."""
    from ortools.sat.python import cp_model

    import rota.planning.solver as solver_module

    forced_status = getattr(cp_model, forced_status_name)

    class _FakeSolver:
        def status_name(self, status):
            return forced_status_name

        def value(self, expr):  # pragma: no cover -- must never be called
            raise AssertionError(f"{forced_status_name} phase 1 must not read an unproven objective value")

    real_run_solver = solver_module._run_solver
    call_count = {"n": 0}

    def fake_run_solver(model, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeSolver(), forced_status
        return real_run_solver(model, *args, **kwargs)

    monkeypatch.setattr(solver_module, "_run_solver", fake_run_solver)
    result = plan(_replan_state_with_baseline())
    assert result.status == expected_status


def test_i_phase1_feasible_without_proof_fails_closed_to_technical_error(monkeypatch):
    _assert_phase1_status_fails_closed(monkeypatch, "FEASIBLE")


def test_i_phase1_unknown_fails_closed_to_search_incomplete(monkeypatch):
    _assert_phase1_status_fails_closed(monkeypatch, "UNKNOWN", expected_status="SEARCH_INCOMPLETE")


def test_i_phase1_model_invalid_fails_closed_to_technical_error(monkeypatch):
    _assert_phase1_status_fails_closed(monkeypatch, "MODEL_INVALID")


# Baseline/fixed partition regression (guards replan_reshuffle.py's
# duplicated mentor_linked_ids logic against silently drifting out of sync
# with solver.fixed_existing_assignments) -----------------------------------


def test_baseline_and_fixed_partition_all_non_cancelled_existing_assignments():
    demand1, demand2, demand3 = _demand_d("D1", 1), _demand_d("D2", 2), _demand_d("D3", 3)
    frozen = _baseline("frozen-1", "A", demand1, frozen=True)
    realized_raw = _baseline("realized-1", "A", demand2)
    realized = Assignment(**{**realized_raw.__dict__, "state": AssignmentState.REALIZED})
    cancelled_raw = _baseline("cancelled-1", "A", demand3)
    cancelled = Assignment(**{**cancelled_raw.__dict__, "state": AssignmentState.CANCELLED})
    redistributable = _baseline("orig-4", "B", _demand_d("D4", 4))
    existing = (frozen, realized, cancelled, redistributable)
    state = base_state(existing_assignments=existing)

    fixed_ids = {a.assignment_id for a in fixed_existing_assignments(state)}
    baseline_ids = {a.assignment_id for a in redistributable_baseline_assignments(state)}
    non_cancelled_ids = {a.assignment_id for a in existing if a.state != AssignmentState.CANCELLED}

    assert fixed_ids & baseline_ids == set()
    assert fixed_ids | baseline_ids == non_cancelled_ids
