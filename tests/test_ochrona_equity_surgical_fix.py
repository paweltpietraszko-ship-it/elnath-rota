"""ROTA-OCHRONA-EQUITY-SURGICAL-FIX: dedicated regression proof (architect
static audit, BOARD.md review of commit 7503759, Problem B -- "brak
dedykowanego regresyjnego dowodu w repo dla absencji/delegacji przy
brakującym target, mieszanym wektorze, zachowania sufitu i REPLAN z fixed
hours"). Hand-crafted minimal PlanningState fixtures (tests/support/
minimal_state.py pattern, same style as test_third_consecutive_shift_
regime_scope.py) exercising rota.planning.solver.solve() directly -- no DB,
no app layer, isolating exactly the new OCHRONA hours-fairness path.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

from rota.domain import (
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    SitePlanningRegime,
    SiteMembership,
    WorkBalance,
)
from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.solver import solve
from tests.support.minimal_state import MONTH, base_state


def _ochrona_state(**overrides):
    base = base_state(**overrides)
    return replace(base, site=replace(base.site, planning_regime=SitePlanningRegime.OCHRONA))


def _membership(employee_id: str, kind: MembershipKind = MembershipKind.LOCAL) -> SiteMembership:
    return SiteMembership(employee_id, "test-site", kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _d_demand(day: int, month: date = MONTH) -> ShiftDemand:
    start = datetime(month.year, month.month, day, 5, 0)
    return ShiftDemand(f"{month.isoformat()[:7]}-{day:02d}-D", "test-v1", start, start + timedelta(hours=12), 1)


def _hours(outcome) -> dict[str, int]:
    hours: dict[str, int] = {}
    for a in outcome.assignments or []:
        if a.role != AssignmentRole.PRIMARY:
            continue
        h = int((a.end_datetime - a.start_datetime).total_seconds() // 3600)
        hours[a.employee_id] = hours.get(a.employee_id, 0) + h
    return hours


# --- Problem B(1): absence/delegation with a MISSING target -----------------


def test_ochrona_missing_target_is_absence_aware_not_the_t041_bug():
    """The exact ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE/FF bug this whole
    diagnosis is about: A has NO WorkBalance (missing target_hours) but has
    80h already committed via PlanningState.unassigned_committed_hours
    (absence/delegation, assembled by assembler.py in production); B also
    has no target, 0h already committed. 6 available D-demands (72h total).
    Equalizing RAW worked_hours (the deleted, buggy fallback) would push A
    toward the same worked_hours as B, piling new work on top of A's 80h.
    Equalizing COMMITTED hours (worked + offset, the fix) must leave A with
    materially fewer NEW assigned hours than B."""
    employees = (Employee("A", "A", date(2020, 1, 1), None, False), Employee("B", "B", date(2020, 1, 1), None, False))
    memberships = (_membership("A"), _membership("B"))
    demands = tuple(_d_demand(d) for d in range(1, 7))
    state = _ochrona_state(
        employees=employees, memberships=memberships, shift_demands=demands,
        work_balances=(), unassigned_committed_hours={"A": 80, "B": 0},
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    hours = _hours(outcome)
    assert hours.get("B", 0) > hours.get("A", 0), (
        f"absence-blind regression: A (80h already committed) got {hours.get('A', 0)}h new work, "
        f"B (0h committed) got {hours.get('B', 0)}h -- must not be roughly equal"
    )


# --- Problem B(2): mixed vector -- target is a ceiling, never a floor -------


def test_ochrona_mixed_vector_target_is_ceiling_not_floor():
    """A has an explicit target=12 (one WorkBalance); B has none at all
    (mixed vector, exactly what OWNER's "Ustaw wszystkim" partial-adoption
    scenario looks like). 4 D-demands (48h). Equalizing alone would want
    ~24h each; A's stated ceiling must still cap A at 12h, with B absorbing
    the rest -- the ceiling is enforced even though the equalization term
    would otherwise prefer a more even split."""
    employees = (Employee("A", "A", date(2020, 1, 1), None, False), Employee("B", "B", date(2020, 1, 1), None, False))
    memberships = (_membership("A"), _membership("B"))
    demands = tuple(_d_demand(d) for d in range(1, 5))
    state = _ochrona_state(
        employees=employees, memberships=memberships, shift_demands=demands,
        work_balances=(WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),),
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    hours = _hours(outcome)
    assert hours.get("A", 0) <= 12, f"A's stated ceiling (12h) was exceeded: {hours.get('A', 0)}h"
    assert sum(hours.values()) == 48, "every demand must still be covered"


# --- Problem B(3): REPLAN fixed hours count toward the new equalization ----


def test_ochrona_replan_fixed_hours_count_toward_equalization():
    """A already has TWO FIXED (before cutover_at) PLANNED PRIMARY
    assignments (24h total) from a prior version; B has none. 6 more open
    D-demands (72h) to redistribute. Sized so the correct (fixed-hours-
    aware) and buggy (fixed-hours-blind) behaviors give DIFFERENT, telling
    results: counting A's 24h fixed correctly, the true equalizing split is
    A_new=2/B_new=4 (both end at 48h total, spread 0); if the fixed hours
    were silently dropped from the committed-hours term (the regression
    this guards against), the solver would instead aim for equal NEW hours
    alone (A_new=3/B_new=3), leaving a real total spread of 24h (A=24+36=60,
    B=36)."""
    employees = (Employee("A", "A", date(2020, 1, 1), None, False), Employee("B", "B", date(2020, 1, 1), None, False))
    memberships = (_membership("A"), _membership("B"))
    fixed_assignments = []
    for day in (1, 2):
        fixed_start = datetime(MONTH.year, MONTH.month, day, 5, 0)
        fixed_demand = ShiftDemand(f"fixed-D-{day}", "test-v0", fixed_start, fixed_start + timedelta(hours=12), 1)
        fixed_assignments.append(Assignment(
            f"a-fixed-{day}", "test-v0", "A", fixed_start, fixed_start + timedelta(hours=12),
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, fixed_demand.demand_id, None,
        ))
    new_demands = tuple(_d_demand(d) for d in range(3, 9))
    state = _ochrona_state(
        employees=employees, memberships=memberships, shift_demands=new_demands,
        existing_assignments=tuple(fixed_assignments), work_balances=(),
        cutover_at=datetime(MONTH.year, MONTH.month, 3, 0, 0),
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    hours = _hours(outcome)
    total_committed = {"A": hours.get("A", 0) + 24, "B": hours.get("B", 0)}
    spread = max(total_committed.values()) - min(total_committed.values())
    assert spread == 0, (
        f"A's pre-existing 24h fixed assignments were not counted toward equalization: "
        f"total committed hours {total_committed}, spread {spread} (expected 0)"
    )


# --- Problem A: external support is a LAST RESORT, never a ceiling trade ---


def test_ochrona_external_support_never_traded_for_ceiling_protection():
    """OWNER 2026-09-20 (BOARD.md): 'zaproponowanie koordynatorowi
    zewnętrznego wsparcia jest możliwe gdy wszystkie inne możliwości
    polegną' -- external support is a last resort, never a soft
    alternative to a LOCAL employee exceeding their stated ceiling.
    Architect's static audit (7503759) found the ceiling-vs-prefer-local
    weight ordering was not provably correct. A is the only LOCAL
    candidate, target=12 (ceiling), but 2 D-demands (24h) exist; X is an
    eligible EXTERNAL_SUPPORT candidate for both. A HARD-feasible
    alternative (assign the second demand to X) exists, but the solver
    must still prefer overloading A past their ceiling -- X must get
    NOTHING, proving external is never chosen merely to protect a ceiling."""
    employees = (Employee("A", "A", date(2020, 1, 1), None, False), Employee("X", "X", date(2020, 1, 1), None, False))
    memberships = (_membership("A"), _membership("X", kind=MembershipKind.EXTERNAL_SUPPORT))
    demands = (_d_demand(1), _d_demand(2))
    window_start = datetime(MONTH.year, MONTH.month, 1, 0, 0)
    window_end = datetime(MONTH.year, MONTH.month, 3, 0, 0)
    windows = (ExternalSupportWindow("W1", "X", "test-site", window_start, window_end, True, None),)
    state = _ochrona_state(
        employees=employees, memberships=memberships, shift_demands=demands, external_windows=windows,
        work_balances=(WorkBalance("A", MONTH, 12, 0, 0, 0, 0, 0),),
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    hours = _hours(outcome)
    assert hours.get("X", 0) == 0, f"EXTERNAL_SUPPORT was used ({hours.get('X', 0)}h) merely to protect A's ceiling"
    assert hours.get("A", 0) == 24, f"A should absorb both demands (24h), got {hours.get('A', 0)}h"
