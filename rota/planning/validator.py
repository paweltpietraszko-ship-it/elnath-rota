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
from itertools import combinations

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    MembershipKind,
    ShiftCatalogKind,
    ShiftKind,
)
from rota.planning.site_rules import day_only_n_exception_applies, hard_rules_applicable_on, rule_allows_assignment
from rota.planning.state import PlanningState
from rota.planning.timeutil import overlap_hours, overlaps_date_range, rolling_windows
from rota.planning.work_periods import PeriodComponent, find_malformed_periods, group_into_periods, periods_overlap


@dataclass(frozen=True)
class ViolationDetail:
    """A HARD violation tagged with the rule and the exact Assignment(s) it is
    about. FINDING R23-2 (tests_r23.txt): a caller (engine._decision_for_conflicts)
    that needs to know whether a violation is explained by a specific
    Assignment must not rely on assignment_id appearing as a substring of a
    human-readable message -- assignment_id has no contractual format or
    minimum length, so short/common IDs ("a", "mentor") can coincidentally
    match unrelated text. assignment_ids is the authoritative, exact set;
    message is for display/logging only."""

    rule: str
    assignment_ids: tuple[str, ...]
    message: str
    # tasks/ROTA-T009/review_01_architect_clarification.md COVERAGE GAP
    # DEVIATION TARGET: a coverage gap/excess has no employee/Assignment to
    # blame when nothing at all covers the gap -- the demand itself is the
    # only truthful target. Empty for every other rule.
    demand_ids: tuple[str, ...] = ()


@dataclass
class IndependentValidationReport:
    hard_pass: bool
    violations: list[str] = field(default_factory=list)
    violation_details: list[ViolationDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    monthly_hours: dict[str, int] = field(default_factory=dict)
    minimum_rest_hours: float | None = None
    maximum_rolling_7d_hours: dict[str, float] = field(default_factory=dict)
    maximum_rolling_7d_window: dict[str, tuple] = field(default_factory=dict)
    # ROTA-T007 (audit round 5 FINDING R5-1): raw (datetime, datetime) window
    # boundaries per employee, for callers that need real hour-overlap
    # relevance rather than the calendar-date display form above.
    maximum_rolling_7d_window_datetimes: dict[str, tuple] = field(default_factory=dict)


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


def _coverage_segments(demand_start, demand_end, overlapping: list[tuple]) -> list[tuple]:
    """Sweep-line over [demand_start, demand_end): breakpoints are the demand
    bounds plus every (already demand-clipped) PRIMARY interval's own bounds.
    Each resulting sub-segment has a single, well-defined coverage count."""
    points = sorted({demand_start, demand_end, *(p for iv in overlapping for p in iv)})
    segments = []
    for a, b in zip(points, points[1:]):
        if a >= b:
            continue
        count = sum(1 for s, e in overlapping if s <= a and b <= e)
        segments.append((a, b, count))
    return segments


def _coverage_violation_detail(demand, bad_segments: list[tuple]) -> ViolationDetail:
    first_start, first_end, first_count = bad_segments[0]
    kind = "gap" if first_count < demand.required_primary_count else "excess"
    return ViolationDetail(
        "COVERAGE-01", (),
        f"COVERAGE-01: demand {demand.demand_id} has a coverage {kind} in "
        f"{len(bad_segments)} interval(s), e.g. {first_count}/{demand.required_primary_count} "
        f"PRIMARY during {first_start}-{first_end}",
        demand_ids=(demand.demand_id,),
    )


def _check_coverage(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """COVERAGE-01 (arch/spec.md:405-407), narrowed by
    tasks/ROTA-T009/review_01_architect_clarification.md to interval-geometric
    semantics: only PRIMARY counts as coverage, TRAINEE never does
    (arch/spec.md:260-265). Coverage is derived from each PRIMARY's actual
    [start_datetime, end_datetime) interval overlapping the demand -- not
    merely from covers_demand_id tagging -- because a truthful manual
    correction (e.g. one employee covering the tail of a D shift and the
    start of the following N) may legitimately span more than one standard
    demand. Every instant of the demand must have exactly
    required_primary_count overlapping PRIMARY coverage; sequential pieces
    are valid when their union covers it exactly."""
    primary = [a for a in assignments if a.role == AssignmentRole.PRIMARY]
    for demand in state.shift_demands:
        overlapping = [
            (max(a.start_datetime, demand.start_datetime), min(a.end_datetime, demand.end_datetime))
            for a in primary
            if a.start_datetime < demand.end_datetime and a.end_datetime > demand.start_datetime
        ]
        segments = _coverage_segments(demand.start_datetime, demand.end_datetime, overlapping)
        bad_segments = [s for s in segments if s[2] != demand.required_primary_count]
        if bad_segments:
            details.append(_coverage_violation_detail(demand, bad_segments))


def _check_trainee_mentor_reference(assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """FINDING R20-3 (tests_r20.txt): a TRAINEE's mentor_primary_assignment_id
    must resolve inside the same candidate. Independently re-derived from the
    final assignment list, not from solver.fixed_existing_assignments()'s own
    bookkeeping of what it decided to keep (anti-drift rule 12) -- catches a
    dangling reference regardless of which code path produced it.

    FINDING R22-3 (tests_r22.txt): resolving to *some* assignment_id is not
    enough -- arch/spec.md:263-265 requires TRAINEE.mentor_primary_assignment_id
    to reference a PRIMARY. A reference that resolves to another TRAINEE (or
    anything non-PRIMARY) is just as semantically broken as a dangling one.

    FINDING R23-3 (tests_r23.txt): existing and having role=PRIMARY is still
    not enough -- arch/spec.md SECTION 8 describes S as added to the mentor's
    *own* shift, so the TRAINEE's interval must fall entirely inside the
    referenced PRIMARY's interval. A PRIMARY from a different day (or one that
    starts after / ends before the TRAINEE) is not the mentor present during
    that training."""
    by_id = {a.assignment_id: a for a in assignments}
    for assignment in assignments:
        if assignment.role != AssignmentRole.TRAINEE:
            continue
        mentor_id = assignment.mentor_primary_assignment_id
        if not mentor_id:
            continue
        target = by_id.get(mentor_id)
        ids = (assignment.assignment_id, mentor_id)
        if target is None:
            details.append(ViolationDetail(
                "ASSIGN", ids,
                f"ASSIGN: {assignment.assignment_id} (TRAINEE) references missing "
                f"mentor_primary_assignment_id {mentor_id}",
            ))
        elif target.role != AssignmentRole.PRIMARY:
            details.append(ViolationDetail(
                "ASSIGN", ids,
                f"ASSIGN: {assignment.assignment_id} (TRAINEE) mentor_primary_assignment_id {mentor_id} "
                f"is not PRIMARY (role={target.role.value})",
            ))
        elif assignment.start_datetime < target.start_datetime or assignment.end_datetime > target.end_datetime:
            details.append(ViolationDetail(
                "ASSIGN", ids,
                f"ASSIGN: {assignment.assignment_id} (TRAINEE) interval is not inside mentor "
                f"{mentor_id}'s interval ({target.start_datetime}-{target.end_datetime})",
            ))


def _check_replan_preserves_fixed(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
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
        ids = (existing.assignment_id,)
        if candidate is None:
            details.append(ViolationDetail(
                "ASSIGN-03/04", ids,
                f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE) missing from candidate",
            ))
        elif candidate != existing:
            details.append(ViolationDetail(
                "ASSIGN-03/04", ids,
                f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE) was modified",
            ))


def _check_membership_enabled(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
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
            details.append(ViolationDetail(
                "MEMBERSHIP-01", (assignment.assignment_id,),
                f"MEMBERSHIP-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "has no enabled membership for this site",
            ))


def _check_day_only(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """ROTA-T010-B: a RESOLVED HARD EMPLOYEE_DAY_ONLY_N_EXCEPTION rule
    applicable on the assignment's date exempts only this check (DAY_ONLY-01
    for N) -- eligibility.py's _common_hard_gate must reach the identical
    verdict (part_b_availability.md: 'Eligibility i validator muszą byc
    zgodne')."""
    day_only_ids = {e.employee_id for e in state.employees if e.day_only}
    if not state.profile.day_only_blocks_n:
        return
    for assignment in assignments:
        if assignment.employee_id not in day_only_ids:
            continue
        kind = _assignment_kind(assignment, state)
        if kind != ShiftKind.N:
            continue
        applicable = hard_rules_applicable_on(
            state.site_rules, state.site_rule_applicability, assignment.start_datetime.date()
        )
        if day_only_n_exception_applies(applicable, assignment.employee_id):
            continue
        details.append(ViolationDetail(
            "DAY_ONLY-01", (assignment.assignment_id,),
            f"DAY_ONLY-01: {assignment.employee_id} has N assignment {assignment.assignment_id}",
        ))


def _assignment_kind(assignment: Assignment, state: PlanningState) -> ShiftKind | None:
    for shift in state.profile.standard_shifts:
        if shift.start_time == assignment.start_datetime.time():
            return shift.kind
    return None


def _check_day_shift_off(
    state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str]
) -> None:
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
                details.append(ViolationDetail(
                    "DAY_SHIFT_OFF-01", (assignment.assignment_id,),
                    f"DAY_SHIFT_OFF-01: {assignment.employee_id} starts assignment {assignment.assignment_id} "
                    f"on day off {start_date}",
                ))
            end_date = assignment.end_datetime.date()
            if end_date != start_date and lo <= end_date <= hi:
                warnings.append(
                    f"DAY_SHIFT_OFF-01 SOFT: {assignment.employee_id} assignment {assignment.assignment_id} "
                    f"enters day off {end_date}"
                )


_RELEVANT_UNAVAILABILITY_KINDS = (
    AvailabilityKind.UNAVAILABLE_24H,
    AvailabilityKind.SICK_LEAVE,
    AvailabilityKind.LEAVE_GRANTED,
)

# arch/spec.md:393-394 freezes the condition code for UNAVAILABLE_24H as
# "UNAVAILABLE-01", not "UNAVAILABLE_24H-01" -- the AvailabilityKind enum
# value and the frozen rule code intentionally differ here (audit round 26,
# FINDING R26-2). Every other kind's code matches its enum value.
_CONDITION_CODE = {
    AvailabilityKind.UNAVAILABLE_24H: "UNAVAILABLE-01",
    AvailabilityKind.SICK_LEAVE: "SICK_LEAVE-01",
    AvailabilityKind.LEAVE_GRANTED: "LEAVE_GRANTED-01",
}


def _check_leave_and_unavailable(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """Owner decision 2026-08-14 is narrow: on a day where a SICK_LEAVE record
    and a LEAVE_GRANTED record both cover that day, only SICK_LEAVE-01 is
    reported for that Assignment -- not both. FINDING R26-1 (tests_r26.txt):
    an earlier version picked one "winning" kind for the *entire* Assignment
    via a fixed priority order, which (a) dropped LEAVE_GRANTED-01 when it and
    SICK_LEAVE blocked the same Assignment on genuinely different days, and
    (b) invented an UNAVAILABLE_24H > SICK_LEAVE priority that was never
    decided. Every overlapping kind is now reported independently; the only
    suppression is LEAVE_GRANTED when its own record's date range actually
    intersects an overlapping SICK_LEAVE record's date range (the owner's
    "same day" scope), not merely because both happen to touch the Assignment
    somewhere."""
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        overlapping_by_kind: dict[AvailabilityKind, AvailabilityRecord] = {}
        for record in records_by_employee.get(assignment.employee_id, []):
            if not record.active or record.kind not in _RELEVANT_UNAVAILABILITY_KINDS:
                continue
            overlaps = overlaps_date_range(
                assignment.start_datetime, assignment.end_datetime, record.start_date, record.end_date
            )
            if overlaps:
                overlapping_by_kind.setdefault(record.kind, record)

        sick = overlapping_by_kind.get(AvailabilityKind.SICK_LEAVE)
        leave = overlapping_by_kind.get(AvailabilityKind.LEAVE_GRANTED)
        suppress_leave_granted = (
            sick is not None and leave is not None
            and max(sick.start_date, leave.start_date) <= min(sick.end_date, leave.end_date)
        )

        for kind in _RELEVANT_UNAVAILABILITY_KINDS:
            record = overlapping_by_kind.get(kind)
            if record is None:
                continue
            if kind == AvailabilityKind.LEAVE_GRANTED and suppress_leave_granted:
                continue
            code = _CONDITION_CODE[kind]
            details.append(ViolationDetail(
                code, (assignment.assignment_id,),
                f"{code}: {assignment.employee_id} assignment {assignment.assignment_id} "
                f"overlaps {kind.value} {record.start_date}-{record.end_date}",
            ))


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


def _check_external(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
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
            details.append(ViolationDetail(
                "EXTERNAL-01", (assignment.assignment_id,),
                f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "uses EXTERNAL_SUPPORT but profile.external_support_enabled is false",
            ))
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
            details.append(ViolationDetail(
                "EXTERNAL-01", (assignment.assignment_id,),
                f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                "has no covering active ExternalSupportWindow",
            ))


def _check_site_rules(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """ROTA-T007 (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md INDEPENDENT
    VALIDATION): re-checks every applicable HARD SiteRule against every
    PRIMARY Assignment independently of solver eligibility filtering
    (anti-drift rule 12). The violation's rule code IS the exact
    rule_version_id, never a generic condition code, so it flows straight
    into Blocker.condition unchanged."""
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        shift_kind = _assignment_kind(assignment, state)
        if shift_kind is None:
            continue
        applicable = hard_rules_applicable_on(
            state.site_rules, state.site_rule_applicability, assignment.start_datetime.date()
        )
        for rule in applicable:
            if rule_allows_assignment(rule, assignment.employee_id, assignment.start_datetime.date(), shift_kind):
                continue
            details.append(ViolationDetail(
                rule.rule_version_id, (assignment.assignment_id,),
                f"{rule.rule_version_id}: {assignment.employee_id} assignment {assignment.assignment_id} "
                f"violates {rule.rule_kind}",
            ))


def _check_24h_same_person(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """SHIFT-24-PAIR-01: a 24h occurrence's two components need identical PRIMARY employee(s) -- identity, REALIZED counts too."""
    demands_by_id = {d.demand_id: d for d in state.shift_demands}
    by_template: dict[str, dict[str, set[str]]] = {}
    for a in assignments:
        demand = demands_by_id.get(a.covers_demand_id)
        if a.role != AssignmentRole.PRIMARY or demand is None or demand.catalog_kind != ShiftCatalogKind.H24 or not demand.work_period_template_id:
            continue
        by_template.setdefault(demand.work_period_template_id, {}).setdefault(demand.demand_id, set()).add(a.employee_id)
    for template_id, by_demand in by_template.items():
        if len(by_demand) != 2:
            continue
        (d1, emp1), (d2, emp2) = sorted(by_demand.items())
        if emp1 != emp2:
            ids = tuple(a.assignment_id for a in assignments if a.covers_demand_id in (d1, d2))
            details.append(ViolationDetail("SHIFT-24-PAIR-01", ids, f"SHIFT-24-PAIR-01: template {template_id} mismatch {sorted(emp1)} vs {sorted(emp2)}"))


def _check_rest(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> float | None:
    """REST-01, per-work-period -- 24h pairs have no internal check, earlier period's rest governs, only target-touching edges count."""
    # B-R10-3: identity is (schedule_version_id, assignment_id), not the bare local id (tests/test_audit_t009_r6.py).
    target_keys = {(a.schedule_version_id, a.assignment_id) for a in assignments}
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    all_components = [PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id) for a in all_assignments]
    for key, ids, reasons in find_malformed_periods(all_components):
        details.append(ViolationDetail("WORK_PERIOD-01", ids, f"WORK_PERIOD-01: period {key}: {'; '.join(reasons)}"))
    min_rest = None
    for employee_id in {c.employee_id for c in all_components}:
        components = [c for c in all_components if c.employee_id == employee_id]
        periods = group_into_periods(components)
        # Every (target, other) pair, not only sorted neighbors (B-R10-3).
        target_periods = [p for p in periods if not target_keys.isdisjoint(p.component_keys)]
        history_periods = [p for p in periods if p not in target_periods]
        pairs = [(tp, h) for tp in target_periods for h in history_periods] + list(combinations(target_periods, 2))
        for tp, other in pairs:
            earlier, later = (tp, other) if tp.start <= other.start else (other, tp)
            ids = (earlier.component_ids[-1], later.component_ids[0])
            if periods_overlap(earlier, later):
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} overlapping assignments"))
                continue
            gap = (later.start - earlier.end).total_seconds() / 3600
            min_rest = gap if min_rest is None else min(min_rest, gap)
            if gap < earlier.required_rest_after_hours:
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} {ids[0]}->{ids[1]}: only {gap:.1f}h"))
    return min_rest


def _check_load(
    state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]
) -> tuple[dict[str, float], dict[str, tuple], dict[str, tuple]]:
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    grouped = _by_employee(all_assignments)
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    windows = rolling_windows(state.month, num_days)
    threshold = state.profile.rolling_7d_decision_threshold_hours
    max_load: dict[str, float] = {}
    max_window: dict[str, tuple] = {}
    # ROTA-T007 (audit round 5 FINDING R5-1): the display-friendly max_window
    # (calendar dates only) can't answer "does this Assignment overlap the
    # actual worst window" correctly for an overnight shift that starts the
    # day before the window but still contributes hours to it -- callers
    # that need real relevance (engine._load_decision) need the original
    # datetime boundaries, not their date()-rounded display form.
    max_window_datetimes: dict[str, tuple] = {}
    for employee_id, employee_assignments in grouped.items():
        worst = 0.0
        worst_window = None
        worst_window_datetimes = None
        ids = tuple(a.assignment_id for a in employee_assignments)
        for window_start, window_end in windows:
            hours = sum(
                overlap_hours(a.start_datetime, a.end_datetime, window_start, window_end)
                for a in employee_assignments
            )
            if hours > worst:
                worst = hours
                worst_window = (window_start.date(), (window_end - timedelta(days=1)).date())
                worst_window_datetimes = (window_start, window_end)
            if hours > threshold:
                details.append(ViolationDetail(
                    "LOAD-01", ids,
                    f"LOAD-01: {employee_id} has {hours}h in window {window_start.date()}-{window_end.date()}",
                ))
        max_load[employee_id] = worst
        if worst_window is not None:
            max_window[employee_id] = worst_window
            max_window_datetimes[employee_id] = worst_window_datetimes
    return max_load, max_window, max_window_datetimes


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
    details: list[ViolationDetail] = []
    warnings: list[str] = []

    # REPLAN (ASSIGN-03: REALIZED work MUST NOT be changed): a REALIZED
    # Assignment is immutable historical fact, not a currently-decided one.
    # Eligibility/availability HARD checks (membership, DAY_ONLY,
    # DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, EXTERNAL-01) only make
    # sense going forward -- data recorded after the fact (e.g. a later
    # UNAVAILABLE_24H record) must not retroactively turn already-realized
    # work into a HARD violation and break FEASIBLE for something REPLAN is
    # required to leave untouched anyway. COVERAGE-01, ASSIGN-03/04
    # preservation, REST-01 and LOAD-01 still consider every assignment,
    # since those are about real elapsed time and identity, not eligibility.
    for_eligibility_checks = [a for a in assignments if a.state != AssignmentState.REALIZED]

    _check_coverage(state, assignments, details)
    _check_replan_preserves_fixed(state, assignments, details)
    _check_trainee_mentor_reference(assignments, details)
    _check_membership_enabled(state, for_eligibility_checks, details)
    _check_day_only(state, for_eligibility_checks, details)
    _check_day_shift_off(state, for_eligibility_checks, details, warnings)
    _check_leave_and_unavailable(state, for_eligibility_checks, details)
    _check_leave_plan(state, for_eligibility_checks, warnings)
    _check_external(state, for_eligibility_checks, details)
    _check_site_rules(state, for_eligibility_checks, details)
    _check_24h_same_person(state, assignments, details)
    min_rest = _check_rest(state, assignments, details)
    max_load, max_window, max_window_datetimes = _check_load(state, assignments, details)

    return IndependentValidationReport(
        hard_pass=not details,
        violations=[d.message for d in details],
        violation_details=details,
        warnings=warnings,
        monthly_hours=_monthly_hours(state, assignments),
        minimum_rest_hours=min_rest,
        maximum_rolling_7d_window=max_window,
        maximum_rolling_7d_window_datetimes=max_window_datetimes,
        maximum_rolling_7d_hours=max_load,
    )


if __name__ == "__main__":
    print("validator module OK")
