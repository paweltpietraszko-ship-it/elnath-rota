"""Shift-pattern HARD checks split out of validator.py (2026-09
oversized-file refactor, mechanical-only, zero behavior change):
NIGHT-STREAK-01, THIRD-CONSECUTIVE-SHIFT-01, SHIFT-24-PAIR-01,
SHIFT-24-01 (via the emergency-pair path)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftCatalogKind, ShiftKind
from rota.planning.eligibility import is_all_24h_profile
from rota.planning.shift_catalog import dn_semantics_apply
from rota.planning.state import PlanningState
from rota.planning.work_periods import check_emergency_pair_structure
from rota.planning.validator_shared import (
    ViolationDetail,
    _attributed_overlap_intervals,
    _covering_demand,
    _demand_kind,
    _is_well_formed_normal_h24_pair,
    _not_cancelled,
)


def _check_night_streak(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """NIGHT-STREAK-01 (ROTA-T032, owner-corrected 2026-08-25): independent
    from-scratch mirror of the solver HARD -- the same employee never has
    non-CANCELLED PRIMARY N on three consecutive start dates. N is
    recognized exclusively via classify_demand on the assignment's own
    covering ShiftDemand (never assignment start-hour/duration guessing).
    `assignments` is already CANCELLED-filtered by validate(); target-Site
    boundary_assignments extend the check across the month boundary (T032
    section 3.3) -- other_site_assignments and TRAINEE never participate."""
    n_dates_by_employee: dict[str, set] = {}
    assignment_by_employee_date: dict[tuple[str, date], str] = {}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        assignment_by_employee_date[assignment.employee_id, assignment.start_datetime.date()] = assignment.assignment_id
        demand = _covering_demand(assignment, state)
        # ROTA-T065 audit R3-01 fix: D/N never carries OCHRONA legal
        # meaning for an ORDINARY site, regardless of role.
        if demand is not None and dn_semantics_apply(demand, state.site.planning_regime) and _demand_kind(demand, state.profile) == ShiftKind.N:
            n_dates_by_employee.setdefault(assignment.employee_id, set()).add(assignment.start_datetime.date())

    for boundary in state.boundary_assignments:
        if boundary.role != AssignmentRole.PRIMARY or boundary.state == AssignmentState.CANCELLED:
            continue
        demand = _covering_demand(boundary, state)
        if demand is not None and dn_semantics_apply(demand, state.site.planning_regime) and _demand_kind(demand, state.profile) == ShiftKind.N:
            n_dates_by_employee.setdefault(boundary.employee_id, set()).add(boundary.start_datetime.date())

    for employee_id, dates in n_dates_by_employee.items():
        for d in dates:
            if (d + timedelta(days=1)) in dates and (d + timedelta(days=2)) in dates:
                ids = tuple(
                    assignment_by_employee_date[employee_id, dd]
                    for dd in (d, d + timedelta(days=1), d + timedelta(days=2))
                    if (employee_id, dd) in assignment_by_employee_date
                )
                details.append(ViolationDetail(
                    "NIGHT-STREAK-01", ids,
                    f"NIGHT-STREAK-01: {employee_id} has N on three consecutive dates starting {d}",
                ))


def _check_third_consecutive_shift(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """THIRD-CONSECUTIVE-SHIFT-01 (ROTA-T058, OWNER_CORRECTED 2026-09-08):
    independent from-scratch mirror of the solver HARD
    (constraints.add_max_two_consecutive_primary_shift_constraint) -- the
    same employee never has non-CANCELLED PRIMARY service (any D/N
    combination, not just N) on three consecutive start dates. Unlike
    _check_night_streak, no D/N classification is needed at all -- any real
    PRIMARY occupies its start date regardless of covering-demand kind, and
    a 24h D+N occurrence still shares one start date (this only tracks
    dates, never double-counts same-date components). This is the automatic
    solver's own HARD, but this check runs on EVERY assignments list
    validate() sees, including a manual correction's -- section 2.2: the
    HARD does not block a coordinator's deliberate manual write, it only
    ever materializes as a named Deviation via the existing
    validate -> materialize_deviations -> coordinator action path.
    `assignments` is already CANCELLED-filtered by validate(); target-Site
    boundary_assignments extend the check across the month boundary,
    exactly like NIGHT-STREAK-01 -- other_site_assignments and TRAINEE/
    PERIODIC_TRAINING never participate.

    Code audit round 4 (tests_r4.txt R4-01): state.boundary_assignments'
    own context window is genuinely unbounded (any date, arbitrarily far in
    the past or future), unlike constraints.add_max_two_consecutive_
    primary_shift_constraint's solver-side window, which only ever reaches
    [month_start-2, month_end+2]. Without the same bound here, a fully
    unrelated triple from some other month (e.g. real history from months
    ago) surfaced as a THIRD-CONSECUTIVE-SHIFT-01 ViolationDetail with no
    assignment_ids at all, and materialize_deviations then had nothing to
    attach it to -- UnknownDeviationSource on every subsequent unrelated
    manual correction. Only boundary facts inside this month's own solver
    window can ever combine with something in `assignments` anyway (a
    window entirely outside it is already this month's own past/future
    problem, not something this validate() call is even asked about)."""
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    month_start = date(state.month.year, state.month.month, 1)
    month_end = date(state.month.year, state.month.month, num_days)
    relevant_start = month_start - timedelta(days=2)
    relevant_end = month_end + timedelta(days=2)

    dates_by_employee: dict[str, set] = {}
    # Code audit round 7 (tests_r7.txt R7-01): a real 24h service is TWO
    # Assignments (D+N components) sharing one start date -- a plain dict
    # keyed by (employee_id, date) kept only the last one written, silently
    # dropping the other's assignment_id from this rule's own violation
    # attribution (manual_edit's freeze-the-cause fix could then only ever
    # freeze one of the two, leaving the other redistributable). Every id
    # for a given (employee_id, date) is kept, not just one.
    assignment_ids_by_employee_date: dict[tuple[str, date], list[str]] = {}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        d = assignment.start_datetime.date()
        assignment_ids_by_employee_date.setdefault((assignment.employee_id, d), []).append(assignment.assignment_id)
        dates_by_employee.setdefault(assignment.employee_id, set()).add(d)

    for boundary in state.boundary_assignments:
        if boundary.role != AssignmentRole.PRIMARY or boundary.state == AssignmentState.CANCELLED:
            continue
        d = boundary.start_datetime.date()
        if not (relevant_start <= d <= relevant_end):
            continue
        dates_by_employee.setdefault(boundary.employee_id, set()).add(d)

    for employee_id, dates in dates_by_employee.items():
        for d in dates:
            if (d + timedelta(days=1)) in dates and (d + timedelta(days=2)) in dates:
                ids = tuple(
                    assignment_id
                    for dd in (d, d + timedelta(days=1), d + timedelta(days=2))
                    for assignment_id in assignment_ids_by_employee_date.get((employee_id, dd), ())
                )
                details.append(ViolationDetail(
                    "THIRD-CONSECUTIVE-SHIFT-01", ids,
                    f"THIRD-CONSECUTIVE-SHIFT-01: {employee_id} has a real service on three consecutive dates starting {d}",
                ))


def _check_24h_same_person(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """SHIFT-24-PAIR-01: a 24h occurrence's two components need identical PRIMARY employee(s). Employee sets are derived
    from actual interval coverage, not covers_demand_id tags (T022-F2); malformed/wrong-cardinality provenance fails
    closed instead of being skipped (T022-F3), including a missing work_period_template_id itself (T022-R1-3).

    ROTA-T045: employee sets use the same shared attribution owner as
    COVERAGE-01 (`_attributed_overlap_intervals`), not raw time-overlap.
    Raw overlap previously swept in a PRIMARY genuinely covering a
    DIFFERENT, independently legal, concurrent demand that merely overlapped
    one H24 half in time -- a false SHIFT-24-PAIR-01 mismatch, the exact
    COVERAGE-01 false-positive T041/AUDIT-1 C-03 already fixed for the other
    HARD check. A false/missing/wrong tag still can never hide real H24
    coverage (T022-F2 unchanged): the shared helper only excludes a
    sub-interval when the tag both points elsewhere and genuinely competes
    there."""
    primary = [a for a in assignments if a.role == AssignmentRole.PRIMARY]
    demand_by_id = {d.demand_id: d for d in state.shift_demands}
    by_template: dict[str, list] = {}
    for d in state.shift_demands:
        if d.catalog_kind == ShiftCatalogKind.H24:
            key = d.work_period_template_id or f"__no_template__{d.demand_id}"
            by_template.setdefault(key, []).append(d)
    for template_id, demands in by_template.items():
        member_ids = {d.demand_id for d in demands}
        ids = tuple(a.assignment_id for a in primary if a.covers_demand_id in member_ids)
        if len(demands) != 2:
            details.append(ViolationDetail("SHIFT-24-PAIR-01", ids, f"SHIFT-24-PAIR-01: template {template_id} has {len(demands)} H24 demand(s) (expected 2)"))
            continue
        d1, d2 = demands
        if not _is_well_formed_normal_h24_pair(d1, d2):
            details.append(ViolationDetail("SHIFT-24-PAIR-01", ids, f"SHIFT-24-PAIR-01: template {template_id} malformed normal-H24 provenance"))
            continue
        emp1 = {a.employee_id for a in primary if _attributed_overlap_intervals(a, d1, demand_by_id)}
        emp2 = {a.employee_id for a in primary if _attributed_overlap_intervals(a, d2, demand_by_id)}
        if emp1 != emp2:
            coverage_ids = tuple(
                a.assignment_id for a in primary
                if _attributed_overlap_intervals(a, d1, demand_by_id) or _attributed_overlap_intervals(a, d2, demand_by_id)
            )
            details.append(ViolationDetail("SHIFT-24-PAIR-01", coverage_ids, f"SHIFT-24-PAIR-01: template {template_id} mismatch {sorted(emp1)} vs {sorted(emp2)}"))


def _check_emergency_pairs(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """T012-C section 11: independently confirm every emergency-shaped work period (plain-12h pair, never katalog 24h),
    never trusting solver pair literals. Malformed -> SHIFT-24-PAIR-01; missing can_work_24h -> SHIFT-24-01."""
    # A not-yet-persisted ShiftDemand's schedule_version_id can be "" even though its Assignment carries the real one -- key by the ASSIGNMENT's id.
    all_target_assignments = list(assignments) + _not_cancelled(state.boundary_assignments)
    current_by_id = {d.demand_id: d for d in state.shift_demands}
    demand_by_key = {(d.schedule_version_id, d.demand_id): d for d in state.boundary_shift_demands}
    for a in all_target_assignments:
        if a.covers_demand_id in current_by_id:
            demand_by_key[a.schedule_version_id, a.covers_demand_id] = current_by_id[a.covers_demand_id]
    membership_by_employee = {m.employee_id: m for m in state.memberships if m.site_id == state.site.site_id}
    all_24h = is_all_24h_profile(state.profile)
    groups: dict[tuple[str, str], list[Assignment]] = {}
    for a in all_target_assignments:
        if a.role != AssignmentRole.PRIMARY or not a.work_period_id:
            continue
        demand = demand_by_key.get((a.schedule_version_id, a.covers_demand_id))
        if demand is not None and demand.catalog_kind == ShiftCatalogKind.H24:
            continue
        groups.setdefault((a.employee_id, a.work_period_id), []).append(a)
    for (employee_id, work_period_id), members in groups.items():
        if len(members) < 2:
            continue
        membership = membership_by_employee.get(employee_id)
        can_work_24h = membership.can_work_24h if membership is not None else True
        for finding in check_emergency_pair_structure(members, demand_by_key, can_work_24h, all_24h):
            details.append(ViolationDetail(finding.code, finding.assignment_ids, f"{finding.code}: {work_period_id}: {finding.reason}"))


if __name__ == "__main__":
    print("planning.validator_checks_patterns module OK")
