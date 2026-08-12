"""Independent HARD validator (anti-drift rule 12, arch/spec.md SECTION 2/5).

Re-derives every HARD violation from PlanningState + a final Assignment list,
without reusing the solver's CP-SAT variables or its own bookkeeping of which
constraints it satisfied. A candidate is only ever reported as HARD PASS if
this module, working from scratch, finds no violation.

Does not use CP-SAT.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import timedelta

from rota.constants import REST_MIN_HOURS
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    MembershipKind,
    ShiftKind,
)
from rota.planning.state import PlanningState
from rota.planning.timeutil import overlap_hours, overlaps_date_range, rest_hours, rolling_windows


@dataclass
class IndependentValidationReport:
    hard_pass: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    monthly_hours: dict[str, int] = field(default_factory=dict)
    minimum_rest_hours: float | None = None
    maximum_rolling_7d_hours: dict[str, float] = field(default_factory=dict)
    maximum_rolling_7d_window: dict[str, tuple] = field(default_factory=dict)


def _by_employee(assignments: list[Assignment]) -> dict[str, list[Assignment]]:
    grouped: dict[str, list[Assignment]] = {}
    for assignment in assignments:
        grouped.setdefault(assignment.employee_id, []).append(assignment)
    return grouped


def _not_cancelled(assignments) -> list[Assignment]:
    """CANCELLED Assignments are not actual work (arch/spec.md:257) and must not
    participate in any HARD check -- coverage, DAY_ONLY/DAY_SHIFT_OFF/LEAVE/
    UNAVAILABLE/EXTERNAL, REST-01 or LOAD-01 (audit round 13, tests_r13.txt
    FINDING R13-2: round 12 only filtered coverage and monthly_hours)."""
    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def _check_coverage(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    """COVERAGE-01 (arch/spec.md:405-407). Only PRIMARY counts as coverage;
    TRAINEE never does (arch/spec.md:260-265)."""
    covered: dict[str, int] = {}
    for assignment in assignments:
        if not assignment.covers_demand_id or assignment.role != AssignmentRole.PRIMARY:
            continue
        covered[assignment.covers_demand_id] = covered.get(assignment.covers_demand_id, 0) + 1
    for demand in state.shift_demands:
        actual = covered.get(demand.demand_id, 0)
        if actual != demand.required_primary_count:
            violations.append(
                f"COVERAGE-01: demand {demand.demand_id} has {actual}/{demand.required_primary_count} PRIMARY"
            )


def _check_replan_preserves_fixed(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    """REPLAN (arch/spec.md SECTION 7, ASSIGN-03/04): REALIZED work and frozen
    future Assignments must not be changed by REPLAN; TRAINEE (S) is never
    moved either (arch/spec.md SECTION 8). Independently re-derives this from
    state.existing_assignments rather than trusting that the solver/engine
    construction logic preserved them correctly (anti-drift rule 12)."""
    by_id = {a.assignment_id: a for a in assignments}
    for existing in state.existing_assignments:
        if existing.state == AssignmentState.CANCELLED:
            continue
        must_preserve = (
            existing.state == AssignmentState.REALIZED
            or existing.frozen
            or existing.role == AssignmentRole.TRAINEE
        )
        if not must_preserve:
            continue
        candidate = by_id.get(existing.assignment_id)
        if candidate is None:
            violations.append(
                f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE) missing from candidate"
            )
        elif candidate != existing:
            violations.append(f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE) was modified")


def _check_membership_enabled(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    """MEMBERSHIP-01 (arch/spec.md:114): LOCAL is eligible only when
    membership.enabled. Audit round 14 FINDING R14-1: this was enforced by
    solver eligibility for newly-solved Assignments, but a pre-existing
    Assignment (existing_assignments, already covering a demand before plan()
    runs) was never checked against it at all, so a disabled membership could
    reach FEASIBLE unnoticed on both the solver and validator side.

    Audit round 15 (tests_r15.txt FINDING R15-1): a missing membership for the
    current site -- no membership record at all, or one that exists only for a
    different site (EMP-03: an Employee is not structurally owned by exactly
    one Site, so this is valid data, not corruption) -- is the same absence of
    authorization as a disabled one and must be rejected the same way."""
    membership_by_employee = {
        m.employee_id: m for m in state.memberships if m.site_id == state.site.site_id
    }
    for assignment in assignments:
        membership = membership_by_employee.get(assignment.employee_id)
        if membership is None or not membership.enabled:
            violations.append(
                f"MEMBERSHIP-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "has no enabled membership for this site"
            )


def _check_employee_active(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    """EMP-02 (arch/spec.md:102): an Assignment interval must lie entirely inside
    the Employee's active period. Audit round 13 FINDING R13-3: the validator had
    no EMP-02 check, so the solver's own EMP-02 gate could regress unnoticed
    (anti-drift rule 12). An assignment for an employee_id with no matching
    Employee record is not flagged here -- that is a referential-integrity
    concern outside this experiment's scope, not an EMP-02 violation."""
    employees_by_id = {e.employee_id: e for e in state.employees}
    for assignment in assignments:
        employee = employees_by_id.get(assignment.employee_id)
        if employee is None:
            continue
        start_date = assignment.start_datetime.date()
        end_date = assignment.end_datetime.date()
        if start_date < employee.active_from or (employee.active_to is not None and end_date > employee.active_to):
            violations.append(
                f"EMP-02: {assignment.employee_id} assignment {assignment.assignment_id} "
                f"outside active period {employee.active_from}-{employee.active_to}"
            )


def _check_day_only(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    day_only_ids = {e.employee_id for e in state.employees if e.day_only}
    if not state.profile.day_only_blocks_n:
        return
    for assignment in assignments:
        if assignment.employee_id not in day_only_ids:
            continue
        kind = _assignment_kind(assignment, state)
        if kind == ShiftKind.N:
            violations.append(f"DAY_ONLY-01: {assignment.employee_id} has N assignment {assignment.assignment_id}")


def _assignment_kind(assignment: Assignment, state: PlanningState) -> ShiftKind | None:
    for shift in state.profile.standard_shifts:
        if shift.start_time == assignment.start_datetime.time():
            return shift.kind
    return None


def _check_day_shift_off(state: PlanningState, assignments: list[Assignment], violations: list[str], warnings: list[str]) -> None:
    off_dates_by_employee: dict[str, set] = {}
    for record in state.availability_records:
        if record.kind != AvailabilityKind.DAY_SHIFT_OFF or not record.active:
            continue
        off_dates_by_employee.setdefault(record.employee_id, set()).add((record.start_date, record.end_date))

    for assignment in assignments:
        ranges = off_dates_by_employee.get(assignment.employee_id, set())
        start_date = assignment.start_datetime.date()
        for lo, hi in ranges:
            if lo <= start_date <= hi:
                violations.append(
                    f"DAY_SHIFT_OFF-01: {assignment.employee_id} starts assignment {assignment.assignment_id} "
                    f"on day off {start_date}"
                )
            end_date = assignment.end_datetime.date()
            if end_date != start_date and lo <= end_date <= hi:
                warnings.append(
                    f"DAY_SHIFT_OFF-01 SOFT: {assignment.employee_id} assignment {assignment.assignment_id} "
                    f"enters day off {end_date}"
                )


def _check_leave_and_unavailable(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        for record in records_by_employee.get(assignment.employee_id, []):
            if not record.active:
                continue
            if record.kind not in (AvailabilityKind.LEAVE_GRANTED, AvailabilityKind.UNAVAILABLE_24H, AvailabilityKind.SICK_LEAVE):
                continue
            overlaps = overlaps_date_range(
                assignment.start_datetime, assignment.end_datetime, record.start_date, record.end_date
            )
            if overlaps:
                violations.append(
                    f"{record.kind.value}-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                    f"overlaps {record.kind.value} {record.start_date}-{record.end_date}"
                )


def _check_leave_plan(state: PlanningState, assignments: list[Assignment], warnings: list[str]) -> None:
    """LEAVE_PLAN-01 (arch/spec.md:400-403): a collision does not block the
    Assignment but must be visible as a warning. FINDING R17-4: this was only
    ever emitted by the solver for newly-solved slots, so an existing
    Assignment colliding with LEAVE_PLAN produced no warning at all in the
    public plan() result. Covering it here reaches both existing and solved
    Assignments uniformly, since validate() always sees the full candidate."""
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        for record in records_by_employee.get(assignment.employee_id, []):
            if not record.active or record.kind != AvailabilityKind.LEAVE_PLAN:
                continue
            overlaps = overlaps_date_range(
                assignment.start_datetime, assignment.end_datetime, record.start_date, record.end_date
            )
            if overlaps:
                warnings.append(
                    f"LEAVE_PLAN-01 SOFT: {assignment.employee_id} assignment {assignment.assignment_id} "
                    f"overlaps LEAVE_PLAN {record.start_date}-{record.end_date}"
                )


def _check_external(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> None:
    """EXTERNAL-01 (arch/spec.md:419-421): X/Y are only eligible inside an active,
    confirmed ExternalSupportWindow for the right employee AND, when the window
    restricts it, the right ShiftKind (arch/spec.md:117-127). Audit round 13
    FINDING R13-4: allowed_shift_kind was never compared here."""
    membership_kind_by_employee = {
        m.employee_id: m.membership_kind for m in state.memberships if m.site_id == state.site.site_id
    }
    for assignment in assignments:
        if membership_kind_by_employee.get(assignment.employee_id) != MembershipKind.EXTERNAL_SUPPORT:
            continue
        if not state.profile.external_support_enabled:
            # FINDING R16-2: a window does not turn on a capability the
            # profile has switched off (SITE-01, arch/spec.md:49-50).
            violations.append(
                f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "uses EXTERNAL_SUPPORT but profile.external_support_enabled is false"
            )
            continue
        kind = _assignment_kind(assignment, state)
        covered = any(
            w.active and w.site_id == state.site.site_id
            and w.employee_id == assignment.employee_id
            and w.start_datetime <= assignment.start_datetime
            and w.end_datetime >= assignment.end_datetime
            and (w.allowed_shift_kind is None or w.allowed_shift_kind == kind)
            for w in state.external_windows
        )
        if not covered:
            violations.append(
                f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "has no covering active ExternalSupportWindow"
            )


def _check_rest(state: PlanningState, assignments: list[Assignment], violations: list[str]) -> float | None:
    """REST-01. boundary_assignments (end of previous month, STATE-02
    arch/spec.md:330) are included, not only other_site_assignments."""
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    grouped = _by_employee(all_assignments)
    min_rest = None
    for employee_id, employee_assignments in grouped.items():
        ordered = sorted(employee_assignments, key=lambda a: a.start_datetime)
        for prev, cur in zip(ordered, ordered[1:]):
            if prev.end_datetime > cur.start_datetime:
                violations.append(f"REST-01: {employee_id} overlapping assignments")
                continue
            gap = rest_hours(prev.start_datetime, prev.end_datetime, cur.start_datetime, cur.end_datetime)
            if min_rest is None or gap < min_rest:
                min_rest = gap
            if gap < REST_MIN_HOURS:
                violations.append(
                    f"REST-01: {employee_id} {prev.assignment_id}->{cur.assignment_id}: only {gap:.1f}h"
                )
    return min_rest


def _check_load(
    state: PlanningState, assignments: list[Assignment], violations: list[str]
) -> tuple[dict[str, float], dict[str, tuple]]:
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    grouped = _by_employee(all_assignments)
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    windows = rolling_windows(state.month, num_days)
    threshold = state.profile.rolling_7d_decision_threshold_hours
    max_load: dict[str, float] = {}
    max_window: dict[str, tuple] = {}
    for employee_id, employee_assignments in grouped.items():
        worst = 0.0
        worst_window = None
        for window_start, window_end in windows:
            hours = sum(
                overlap_hours(a.start_datetime, a.end_datetime, window_start, window_end)
                for a in employee_assignments
            )
            if hours > worst:
                worst = hours
                worst_window = (window_start.date(), (window_end - timedelta(days=1)).date())
            if hours > threshold:
                violations.append(
                    f"LOAD-01: {employee_id} has {hours}h in window {window_start.date()}-{window_end.date()}"
                )
        max_load[employee_id] = worst
        if worst_window is not None:
            max_window[employee_id] = worst_window
    return max_load, max_window


def _monthly_hours(state: PlanningState, assignments: list[Assignment]) -> dict[str, int]:
    hours: dict[str, int] = {}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return hours


def validate(state: PlanningState, assignments: list[Assignment]) -> IndependentValidationReport:
    """Recheck every HARD rule from scratch against the final Assignment set."""
    assignments = _not_cancelled(assignments)
    violations: list[str] = []
    warnings: list[str] = []

    # REPLAN (ASSIGN-03: REALIZED work MUST NOT be changed): a REALIZED
    # Assignment is immutable historical fact, not a currently-decided one.
    # Eligibility/availability HARD checks (membership, EMP-02, DAY_ONLY,
    # DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, EXTERNAL-01) only make
    # sense going forward -- data recorded after the fact (e.g. a later
    # UNAVAILABLE_24H record) must not retroactively turn already-realized
    # work into a HARD violation and break FEASIBLE for something REPLAN is
    # required to leave untouched anyway. COVERAGE-01, ASSIGN-03/04
    # preservation, REST-01 and LOAD-01 still consider every assignment,
    # since those are about real elapsed time and identity, not eligibility.
    for_eligibility_checks = [a for a in assignments if a.state != AssignmentState.REALIZED]

    _check_coverage(state, assignments, violations)
    _check_replan_preserves_fixed(state, assignments, violations)
    _check_membership_enabled(state, for_eligibility_checks, violations)
    _check_employee_active(state, for_eligibility_checks, violations)
    _check_day_only(state, for_eligibility_checks, violations)
    _check_day_shift_off(state, for_eligibility_checks, violations, warnings)
    _check_leave_and_unavailable(state, for_eligibility_checks, violations)
    _check_leave_plan(state, for_eligibility_checks, warnings)
    _check_external(state, for_eligibility_checks, violations)
    min_rest = _check_rest(state, assignments, violations)
    max_load, max_window = _check_load(state, assignments, violations)

    return IndependentValidationReport(
        hard_pass=not violations,
        violations=violations,
        warnings=warnings,
        monthly_hours=_monthly_hours(state, assignments),
        minimum_rest_hours=min_rest,
        maximum_rolling_7d_window=max_window,
        maximum_rolling_7d_hours=max_load,
    )


if __name__ == "__main__":
    print("validator module OK")
