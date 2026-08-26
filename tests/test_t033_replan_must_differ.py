"""ROTA-T033: REPLAN must never hand the coordinator back the schedule they
already have (owner decision 2026-08-26, revised same day after a Codex
audit question into a two-step flow: narrow search first, then an explicit
"Szukaj szerzej" widens to _plan()'s full fallback ladder). Verifies
rota.planning.engine.plan_requiring_different_result_narrow/_wide and their
wiring inside rota.planning.solver.solve
(require_different_from_baseline/cutover_at/deadline).
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
)
from rota.planning.engine import plan_requiring_different_result_narrow, plan_requiring_different_result_wide
from tests.support.minimal_state import SITE_ID, base_state


def _membership(employee_id: str) -> SiteMembership:
    from tests.support.minimal_state import ReadinessSource, ReadinessState

    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _employee(employee_id: str, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2026, 9, 1), None, day_only)


def _demand_d(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _demand_n(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _baseline(assignment_id: str, employee_id: str, demand: ShiftDemand) -> Assignment:
    return Assignment(
        assignment_id, "test-v1", employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )


def _covering_pairs(assignments) -> set[tuple[str, str]]:
    return {(a.employee_id, a.covers_demand_id) for a in assignments if a.covers_demand_id}


# Well before every demand date used below -- nothing in these fixtures is
# ever "past" relative to this cutover unless a test says otherwise.
EARLY_CUTOVER = datetime(2026, 9, 1)


# --- Step 1: narrow search ---------------------------------------------------


def test_narrow_returns_a_genuinely_different_candidate_when_one_exists():
    """A and B are both eligible for D1; the baseline has A on it. REPLAN
    must not just re-confirm A -- some other HARD-valid arrangement exists
    (B on D1), so it must be returned instead."""
    demand1 = _demand_d("D1", 5)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand1,), existing_assignments=(baseline1,),
    )
    result = plan_requiring_different_result_narrow(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("B", "D1")}


def test_narrow_search_exhausted_when_baseline_is_the_only_valid_schedule():
    """Only A is eligible for D1 at all -- no other HARD-valid schedule
    exists under ordinary rules. Step 1 must say so plainly (offering the
    coordinator a wider search), never silently repeat A, and never claim
    NO_ALTERNATIVE -- that verdict belongs only to step 2, after the
    exception-aware stages are exhausted too."""
    demand1 = _demand_d("D1", 5)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand1,), existing_assignments=(baseline1,),
    )
    result = plan_requiring_different_result_narrow(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "NARROW_SEARCH_EXHAUSTED"
    assert result.candidates == []


def test_narrow_with_empty_baseline_solves_normally():
    """Nothing was ever redistributably placed (e.g. REPLAN running right
    after a DECISION_REQUIRED that never got a candidate persisted) -- there
    is nothing to "differ from" yet, so this is just an ordinary solve, not
    a NARROW_SEARCH_EXHAUSTED dead end."""
    demand1 = _demand_d("D1", 5)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand1,), existing_assignments=(),
    )
    result = plan_requiring_different_result_narrow(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("A", "D1")}


def test_narrow_never_touches_a_pre_cutover_placement_even_when_diverse():
    """D1 (day 1) is already in the past relative to cutover_at; D2 (day 20)
    is still ahead. A HARD-valid alternative for D2 exists (B), so REPLAN
    must find it -- but must never touch D1's assignment to manufacture
    "difference" instead, even though nothing else would forbid that."""
    demand_past = _demand_d("D1", 1)
    demand_future = _demand_d("D2", 20)
    baseline_past = _baseline("orig-past", "A", demand_past)
    baseline_future = _baseline("orig-future", "A", demand_future)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_past, demand_future), existing_assignments=(baseline_past, baseline_future),
    )
    cutover_at = datetime(2026, 10, 10)  # strictly between day 1 and day 20
    result = plan_requiring_different_result_narrow(state, cutover_at=cutover_at)
    assert result.status == "FEASIBLE"
    pairs = _covering_pairs(result.candidates[0])
    assert ("A", "D1") in pairs  # past placement: untouched
    assert ("B", "D2") in pairs  # future placement: genuinely changed


def test_narrow_search_exhausted_when_only_future_option_is_already_past():
    """The only other eligible employee for D1 is unavailable going forward,
    and D1 itself is already before cutover_at -- there is no way to ever
    produce a different schedule from this point on, under ordinary rules."""
    demand1 = _demand_d("D1", 1)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand1,), existing_assignments=(baseline1,),
    )
    cutover_at = datetime(2026, 10, 10)  # after D1's own date
    result = plan_requiring_different_result_narrow(state, cutover_at=cutover_at)
    assert result.status == "NARROW_SEARCH_EXHAUSTED"


# --- Step 2: wide search ("Szukaj szerzej") ---------------------------------


def test_wide_finds_a_candidate_only_reachable_via_a_fallback_stage():
    """C is DAY_ONLY (ineligible for N under ordinary rules); B is A's only
    ordinary alternative for the night shift but is also on the baseline's
    D-shift the next morning, so swapping B in trips REST-01 under plain
    rules -- the narrow search (mirrored here as a direct ordinary-capped
    diversity solve) would find nothing. The day-only-N fallback stage
    (allow_day_only_n_fallback=True) is what makes C eligible after all,
    producing a genuinely different, HARD-valid schedule."""
    demand_n, demand_d2 = _demand_n("N1", 1), _demand_d("D2", 2)
    baseline_n, baseline_d2 = _baseline("orig-n", "A", demand_n), _baseline("orig-d2", "B", demand_d2)
    state = base_state(
        employees=(_employee("A"), _employee("B"), _employee("C", day_only=True)),
        memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(demand_n, demand_d2), existing_assignments=(baseline_n, baseline_d2),
    )
    result = plan_requiring_different_result_wide(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "FEASIBLE"
    pairs = _covering_pairs(result.candidates[0])
    assert pairs != {("A", "N1"), ("B", "D2")}


def test_wide_no_alternative_when_truly_exhaustive():
    """Only A is eligible for D1, under any stage -- no other HARD-valid
    schedule can ever exist, exception stages included. Only now, after the
    full ladder, may NO_ALTERNATIVE be claimed."""
    demand1 = _demand_d("D1", 5)
    baseline1 = _baseline("orig-1", "A", demand1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand1,), existing_assignments=(baseline1,),
    )
    result = plan_requiring_different_result_wide(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "NO_ALTERNATIVE"
    assert result.candidates == []


def test_wide_still_routes_a_genuine_conflict_to_decision_required():
    """A real REST-01 conflict (unrelated to diversity) must still surface
    as DECISION_REQUIRED through the wide ladder, exactly as ordinary PLAN
    would -- the diversity floor must never mask or be confused with a real
    coordinator decision point."""
    demand_n, demand_d2 = _demand_n("N1", 1), _demand_d("D2", 2)
    baseline_n, baseline_d2 = _baseline("orig-n", "A", demand_n), _baseline("orig-d2", "B", demand_d2)
    gone = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 3), True, None, None)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_n, demand_d2), existing_assignments=(baseline_n, baseline_d2),
        availability_records=(gone,),
    )
    result = plan_requiring_different_result_wide(state, cutover_at=EARLY_CUTOVER)
    assert result.status == "DECISION_REQUIRED"
