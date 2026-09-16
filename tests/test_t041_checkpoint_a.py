"""ROTA-T041 Checkpoint A: solver-result correctness.

tasks/ROTA-T041/brief.md section 4:
- 4.1 OWNER-T041-01 (T41-A01..A06) originally covered an equal-split
  fallback for an incomplete target_hours vector among available LOCAL
  employees. ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE (2026-09-15)
  removed that fallback entirely: PLAN/REPLAN now refuse to reach the
  solver at all while any active LOCAL membership lacks a target_hours
  (rota.application.plan_ops.require_complete_target_hours), so an
  incomplete vector is no longer a real solver-level scenario -- see
  tests/test_target_hours_required.py for that gate's own coverage.
  A01/A02/A04/A05 (the fallback-specific cases, including a unit-level
  proof against the now-deleted solver._available_local_employee_ids)
  are removed accordingly, per the brief's own instruction to replace
  historical fallback tests with gate tests rather than keep two
  contradictory contracts. A03 (complete-vector TARGET-01 regression)
  remains -- that behavior is unchanged and still real.
- 4.2 AUDIT-1 C-03 -- COVERAGE-01 must not double-count a PRIMARY that
  actually belongs to a different, independently legal, concurrent
  demand, while still catching real gaps/excess and never letting a
  false or absent covers_demand_id hide real coverage (T41-A07..A13).

A12 (ROTA-T022's H24 malicious-tag protection stays green) is exercised by
re-running
tests/test_t022_planning_integrity.py::test_c_interval_covered_component_hidden_behind_other_tag_fails
as a narrow regression (see brief section 10), not duplicated here.
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, SITE_ID, base_state

VERSION_ID = "test-v1"


# --- shared helpers (mirrors tests/test_t022_planning_integrity.py conventions) --


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _membership(employee_id: str, kind: MembershipKind = MembershipKind.LOCAL) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _wb(employee_id: str, target_hours: int) -> WorkBalance:
    return WorkBalance(employee_id, MONTH, target_hours, 0, 0, 0, 0, 0)


def _demand(demand_id: str, start: datetime, end: datetime, count: int = 1, **kwargs) -> ShiftDemand:
    return ShiftDemand(demand_id, VERSION_ID, start, end, count, **kwargs)


def _primary(assignment_id: str, employee_id: str, demand: ShiftDemand, *, frozen: bool = False, **kwargs) -> Assignment:
    return Assignment(
        assignment_id, VERSION_ID, employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, demand.demand_id, None, **kwargs,
    )


def _spanning_primary(assignment_id: str, employee_id: str, start: datetime, end: datetime, covers_demand_id: str, *, frozen: bool = True, **kwargs) -> Assignment:
    return Assignment(
        assignment_id, VERSION_ID, employee_id, start, end,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, covers_demand_id, None, **kwargs,
    )


def _dn_demands_for_days(days: range) -> tuple[ShiftDemand, ...]:
    """1 D + 1 N demand (12h each, base_profile shape) per day, needing
    exactly 1 PRIMARY each -- 24h/day of real work, fully interchangeable
    among identical LOCAL employees."""
    demands = []
    for day in days:
        demands.append(_demand(f"D{day}", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0)))
        demands.append(_demand(f"N{day}", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0)))
    return tuple(demands)


def _worked_hours(candidate: list[Assignment]) -> dict[str, int]:
    hours: dict[str, int] = {}
    for a in candidate:
        if a.role != AssignmentRole.PRIMARY or a.state == AssignmentState.CANCELLED:
            continue
        h = int((a.end_datetime - a.start_datetime).total_seconds() // 3600)
        hours[a.employee_id] = hours.get(a.employee_id, 0) + h
    return hours


# --- 4.1 missing target_hours fallback fairness (T41-A01..A06) -----------


def test_t41_a03_complete_target_vector_keeps_target01_unchanged():
    """Regression: when every available LOCAL has a target, TARGET-01/
    target-equity behave exactly as before the fallback exists -- distinct,
    individually-achievable targets summing to the same 720h are matched
    exactly, not silently flattened to an equal split."""
    employees = tuple(_employee(f"E{i}") for i in range(1, 6))
    memberships = tuple(_membership(e.employee_id) for e in employees)
    demands = _dn_demands_for_days(range(1, 31))
    # Every shift is a 12h block, so only targets that are themselves
    # multiples of 12 are exactly achievable -- these are, and still sum
    # to the fixture's 720h of total work.
    targets = {"E1": 120, "E2": 132, "E3": 144, "E4": 156, "E5": 168}
    work_balances = tuple(_wb(eid, t) for eid, t in targets.items())
    state = base_state(employees=employees, memberships=memberships, shift_demands=demands, work_balances=work_balances)

    result = plan(state)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    report = validate(state, candidate)
    assert report.hard_pass, report.violations

    hours = _worked_hours(candidate)
    assert hours == targets


# --- 4.2 legal overlapping demands / COVERAGE-01 (T41-A07..A13) ----------


def _overlapping_pair():
    d1 = _demand("OVL-1", datetime(2026, 10, 5, 18, 0), datetime(2026, 10, 6, 6, 0))
    d2 = _demand("OVL-2", datetime(2026, 10, 5, 22, 0), datetime(2026, 10, 6, 10, 0))
    return d1, d2


def test_t41_a07_two_legal_overlapping_demands_correctly_assigned_passes():
    d1, d2 = _overlapping_pair()
    a1 = _primary("A1", "E1", d1)
    a2 = _primary("A2", "E2", d2)
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert report.hard_pass, report.violations


def test_t41_a08_same_pair_one_person_leaves_real_undercoverage_fails():
    d1, d2 = _overlapping_pair()
    a1 = _primary("A1", "E1", d1)
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E1"),))
    report = validate(state, [a1])
    assert not report.hard_pass
    assert any("COVERAGE-01" in v and d2.demand_id in v for v in report.violations)


def test_t41_a09_two_people_on_one_demand_is_real_excess_fails():
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0))
    a1 = _primary("A1", "E1", d)
    a2 = _primary("A2", "E2", d)
    state = base_state(shift_demands=(d,), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("COVERAGE-01" in v and "excess" in v for v in report.violations)


def test_t41_a10_false_tag_does_not_hide_real_coverage_or_manufacture_it():
    """A1 is really on D2 (its own interval matches D2 exactly) but is
    falsely tagged to D1. D1 must still show as uncovered (the false tag
    cannot manufacture coverage for it); D2 must still show as covered
    (geometry, not the tag, decides what's really there)."""
    d1 = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0))
    d2 = _demand("D2", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0))
    a1 = _spanning_primary("A1", "E1", d2.start_datetime, d2.end_datetime, "D1")
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E1"),))
    report = validate(state, [a1])
    assert not report.hard_pass
    assert any("COVERAGE-01" in v and d1.demand_id in v and "gap" in v for v in report.violations)
    assert not any("COVERAGE-01" in v and d2.demand_id in v for v in report.violations)


def test_t41_a11_t022_spanning_manual_primary_evaluated_by_real_time():
    """A single manual PRIMARY spans an adjacent D+N pair, tagged only to
    D -- both are ADJACENT (not competing/overlapping with each other), so
    COVERAGE-01 must still recognize real-time coverage of both."""
    d_demand = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0))
    n_demand = _demand("N1", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0))
    a = _spanning_primary("A1", "E1", d_demand.start_datetime, n_demand.end_datetime, "D1")
    state = base_state(shift_demands=(d_demand, n_demand), memberships=(_membership("E1"),))
    report = validate(state, [a])
    assert not any("COVERAGE-01" in v for v in report.violations), report.violations


def test_t41_a13_same_tag_on_two_overlapping_demands_not_auto_redistributed():
    """Two independent, fully-overlapping demands; both real assignments
    tag the SAME one. The tagged demand shows real excess (2/1); the
    other is left at 0 -- geometry must not silently hand the second
    person to the untagged demand."""
    tagged = _demand("TAGGED", datetime(2026, 10, 5, 18, 0), datetime(2026, 10, 6, 6, 0))
    other = _demand("OTHER", datetime(2026, 10, 5, 18, 0), datetime(2026, 10, 6, 6, 0))
    a1 = _spanning_primary("A1", "E1", tagged.start_datetime, tagged.end_datetime, "TAGGED")
    a2 = _spanning_primary("A2", "E2", tagged.start_datetime, tagged.end_datetime, "TAGGED")
    state = base_state(shift_demands=(tagged, other), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("COVERAGE-01" in v and "TAGGED" in v and "excess" in v for v in report.violations)
    assert any("COVERAGE-01" in v and "OTHER" in v and "gap" in v for v in report.violations)
