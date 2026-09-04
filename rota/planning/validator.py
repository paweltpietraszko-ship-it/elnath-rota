"""Independent HARD validator (anti-drift rule 12, arch/spec.md SECTION 2/5).
Re-derives every HARD violation from PlanningState + a final Assignment list, from scratch, without CP-SAT."""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations

from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind, AvailabilityRecord, MembershipKind,
    ShiftCatalogKind, ShiftKind, SitePlanningRegime,
)
from rota.planning.eligibility import is_all_24h_profile
from rota.planning.shift_catalog import UnclassifiedShiftError, classify_demand
from rota.planning.site_rules import day_only_n_exception_authorizing_rule_version_id, hard_rules_applicable_on, rule_allows_assignment
from rota.planning.state import PlanningState
from rota.planning.timeutil import overlap_hours, overlaps_date_range, rolling_windows
from rota.planning.work_periods import (
    WEEKLY_REST_REQUIRED_HOURS, PeriodComponent, check_emergency_pair_structure, effective_required_rest_after_hours,
    find_malformed_periods, forms_illegal_continuous_pair, group_into_periods, max_uninterrupted_free_hours,
    periods_overlap, weekly_settlement_windows,
)


@dataclass(frozen=True)
class ViolationDetail:
    """A HARD violation tagged with the rule and exact Assignment(s) it is about (R23-2: assignment_ids is
    authoritative, never parsed back out of message text -- assignment_id has no contractual format/length)."""

    rule: str
    assignment_ids: tuple[str, ...]
    message: str
    demand_ids: tuple[str, ...] = ()  # COVERAGE-01 gap/excess: only the demand can be blamed, no Assignment exists
    # ROTA-T036: explicit employee seam for REST-01/WEEKLY-REST-01 only -- the
    # persistent Deviation target for these two rules is this Employee, never
    # one of assignment_ids (which may be a cross-context boundary/other-site
    # Assignment not resolvable in the target ScheduleVersion). Every other
    # rule leaves this None and keeps its existing demand/assignment target.
    affected_employee_id: str | None = None


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
    # R5-1: raw datetime window bounds, for real hour-overlap relevance.
    maximum_rolling_7d_window_datetimes: dict[str, tuple] = field(default_factory=dict)


def _by_employee(assignments: list[Assignment]) -> dict[str, list[Assignment]]:
    grouped: dict[str, list[Assignment]] = {}
    for assignment in assignments:
        grouped.setdefault(assignment.employee_id, []).append(assignment)
    return grouped


def _not_cancelled(assignments) -> list[Assignment]:
    """CANCELLED Assignments are not actual work (arch/spec.md:257) and must not participate in any HARD check (R13-2)."""
    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def coverage_segments(window_start, window_end, overlapping: list[tuple]) -> list[tuple]:
    """Sweep-line over [window_start, window_end): each resulting sub-segment
    has one well-defined coverage count -- how many of `overlapping`
    intervals fully contain it. Pure, general-purpose; the single shared
    coverage-overlap algorithm (R3-6, ROTA-T023 tests/test_t023.py T23-55):
    COVERAGE-01 below uses it for ShiftDemand-vs-PRIMARY-count coverage, the
    absence-reference repository module reuses it unchanged for
    per-employee-per-date PRIMARY overlap/ambiguity detection. Do not
    reimplement this sweep anywhere else -- import and call this."""
    points = sorted({window_start, window_end, *(p for iv in overlapping for p in iv)})
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


def _attributed_overlap_intervals(assignment: Assignment, demand, demand_by_id: dict) -> list[tuple]:
    """ROTA-T045: single shared owner of "which sub-interval of this PRIMARY
    actually counts as coverage of this demand", reused by both COVERAGE-01
    and SHIFT-24-PAIR-01 (previously duplicated only in COVERAGE-01; T045
    fixed SHIFT-24-PAIR-01 falsely trusting raw time-overlap alone).

    ROTA-T041 OWNER-T041-01 section 4.2 / AUDIT-1 C-03: pure geometry over
    every PRIMARY overlapping a demand double-counted a PRIMARY that
    actually belongs to a DIFFERENT, independently legal, CONCURRENT
    demand -- two legal overlapping demands, one person each correctly
    tagged, produced a false COVERAGE-01 excess on both (arch/spec.md:58,
    485 and ROTA-T012 explicitly allow overlapping catalog occurrences,
    one demand per occurrence).

    covers_demand_id now disambiguates, but only where it matters: when
    the assignment's own tagged demand genuinely overlaps (competes in
    time with) the demand being checked, and only for the actually
    competing sub-interval. A ROTA-T022-accepted manual PRIMARY spanning
    two ADJACENT (non-overlapping) demands with a single tag is still
    counted by real time for both -- there is no competition to resolve
    there, so geometry alone still governs exactly as before (T022
    requires this: a spanning/manual PRIMARY's real covered time, not its
    tag, decides what it covers). A tag pointing nowhere in this version's
    demands, or whose own claimed target it doesn't actually overlap,
    falls back to plain geometry against whatever it really does overlap
    -- a false or absent tag can never hide real coverage.

    ROTA-T041 AUDIT round-2 FINDING T41-A-R2-03 (tests_r2.txt): the tag
    used to exclude the WHOLE assignment from `demand` once any part of the
    tagged demand and `demand` overlapped, even for a sub-interval where
    the tagged demand had already ended (or not yet started) and so was
    never actually competing there. Only the genuinely competing
    sub-interval (the overlap of the tagged demand and `demand` themselves)
    is now excluded; a non-concurrent tail/head of the same assignment
    still counts toward `demand` by plain geometry, exactly as T022
    requires for a spanning/manual PRIMARY."""
    a_start = max(assignment.start_datetime, demand.start_datetime)
    a_end = min(assignment.end_datetime, demand.end_datetime)
    if a_start >= a_end:
        return []
    excluded_start = excluded_end = None
    tagged = demand_by_id.get(assignment.covers_demand_id)
    if tagged is not None and tagged.demand_id != demand.demand_id:
        competes = tagged.start_datetime < demand.end_datetime and tagged.end_datetime > demand.start_datetime
        tag_is_real = assignment.start_datetime < tagged.end_datetime and assignment.end_datetime > tagged.start_datetime
        if competes and tag_is_real:
            excluded_start = max(tagged.start_datetime, demand.start_datetime)
            excluded_end = min(tagged.end_datetime, demand.end_datetime)
    if excluded_start is None:
        return [(a_start, a_end)]
    result = []
    if a_start < excluded_start:
        result.append((a_start, min(a_end, excluded_start)))
    if a_end > excluded_end:
        result.append((max(a_start, excluded_end), a_end))
    return result


def _check_coverage(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """COVERAGE-01: derived from each PRIMARY's actual interval overlap, via
    the shared attribution owner `_attributed_overlap_intervals` (ROTA-T045)."""
    primary = [a for a in assignments if a.role == AssignmentRole.PRIMARY]
    demand_by_id = {d.demand_id: d for d in state.shift_demands}
    for demand in state.shift_demands:
        overlapping = []
        for a in primary:
            overlapping.extend(_attributed_overlap_intervals(a, demand, demand_by_id))
        segments = coverage_segments(demand.start_datetime, demand.end_datetime, overlapping)
        bad_segments = [s for s in segments if s[2] != demand.required_primary_count]
        if bad_segments:
            details.append(_coverage_violation_detail(demand, bad_segments))


def _check_trainee_mentor_reference(assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """TRAINEE.mentor_primary_assignment_id must resolve to a same-candidate PRIMARY whose interval contains it (SECTION 8)."""
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
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) references missing mentor_primary_assignment_id {mentor_id}"))
        elif target.role != AssignmentRole.PRIMARY:
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) mentor_primary_assignment_id {mentor_id} is not PRIMARY (role={target.role.value})"))
        elif assignment.start_datetime < target.start_datetime or assignment.end_datetime > target.end_datetime:
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) interval is not inside mentor {mentor_id}'s interval ({target.start_datetime}-{target.end_datetime})"))


def _check_replan_preserves_fixed(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """REPLAN (SECTION 7, ASSIGN-03/04): REALIZED, frozen, TRAINEE, PERIODIC_TRAINING (T52-11: S1 is a manual
    coordinator fact, never solver-moved) and any mentor-linked PRIMARY must not change -- mirrors
    solver.fixed_existing_assignments/replan_reshuffle's mentor-linked-PRIMARY protection (T022-F5)."""
    by_id = {a.assignment_id: a for a in assignments}
    mentor_linked_ids = {
        a.mentor_primary_assignment_id
        for a in state.existing_assignments
        if a.role == AssignmentRole.TRAINEE and a.state != AssignmentState.CANCELLED and a.mentor_primary_assignment_id
    }
    for existing in state.existing_assignments:
        if existing.state == AssignmentState.CANCELLED:
            continue
        must_preserve = (
            existing.state == AssignmentState.REALIZED or existing.frozen
            or existing.role in (AssignmentRole.TRAINEE, AssignmentRole.PERIODIC_TRAINING)
            or existing.assignment_id in mentor_linked_ids
        )
        if not must_preserve:
            continue
        candidate = by_id.get(existing.assignment_id)
        ids = (existing.assignment_id,)
        if candidate is None:
            details.append(ViolationDetail("ASSIGN-03/04", ids, f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE/mentor-linked) missing from candidate"))
        elif candidate != existing:
            details.append(ViolationDetail("ASSIGN-03/04", ids, f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE/mentor-linked) was modified"))


def _check_membership_enabled(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """MEMBERSHIP-01: LOCAL is eligible only when membership.enabled -- no membership at all, or only for a different site, is the same absence of authorization (R15-1)."""
    membership_by_employee = {m.employee_id: m for m in state.memberships if m.site_id == state.site.site_id}
    for assignment in assignments:
        membership = membership_by_employee.get(assignment.employee_id)
        if membership is None or not membership.enabled:
            details.append(ViolationDetail("MEMBERSHIP-01", (assignment.assignment_id,), f"MEMBERSHIP-01: {assignment.employee_id} assignment {assignment.assignment_id} has no enabled membership for this site"))


def _check_day_only(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str]) -> None:
    """T010-B/T018: an applicable RESOLVED HARD EMPLOYEE_DAY_ONLY_N_EXCEPTION exempts only DAY_ONLY-01 for N, with a SOFT provenance warning."""
    day_only_ids = {e.employee_id for e in state.employees if e.day_only}
    if not state.profile.day_only_blocks_n:
        return
    for assignment in assignments:
        if assignment.employee_id not in day_only_ids:
            continue
        for demand in _covered_demands(assignment, state):
            kind = _demand_kind(demand, state.profile)
            if kind is None:
                # T022-R1-2: an unclassifiable covered demand cannot be ruled out as N -- fail closed rather than silently skip.
                details.append(ViolationDetail("DAY_ONLY-01", (assignment.assignment_id,), f"DAY_ONLY-01: {assignment.employee_id} covers unclassifiable demand {demand.demand_id}, cannot verify not-N"))
                continue
            if kind != ShiftKind.N:
                continue
            # B-R11-1/T022-F1: anchor is the covered ShiftDemand's own start, never the Assignment's -- a spanning PRIMARY cannot hide N behind a different tag.
            anchor_date = demand.start_datetime.date()
            applicable = hard_rules_applicable_on(state.site_rules, state.site_rule_applicability, anchor_date)
            authorizing_id = day_only_n_exception_authorizing_rule_version_id(applicable, assignment.employee_id)
            if authorizing_id is None:
                details.append(ViolationDetail("DAY_ONLY-01", (assignment.assignment_id,), f"DAY_ONLY-01: {assignment.employee_id} has N assignment {assignment.assignment_id} (demand {demand.demand_id})"))
                continue
            # ROTA-T055 R2-01 (OWNER 2026-09-04: "WSZYSTKO co widzi koordynator
            # jest po polsku i bez nic nie mówiących symboli systemowych"):
            # this warning was previously computed and discarded everywhere --
            # T055 is the first path that reaches a coordinator-facing screen,
            # so its wording is rewritten to plain Polish with the employee
            # quoted for MonthlyPlanning.tsx's existing resolveWarningText().
            # R3-02 audit fix: this rule is about an employee normally
            # restricted to day-only shifts (Employee.day_only) who has an
            # authorized shift-rule exception allowing this particular N --
            # it has nothing to do with DAY_SHIFT_OFF (a day-off/availability
            # record, a completely different mechanism); the first wording
            # wrongly said "dnia wolnego" (day off), giving a false reason.
            # The demand/reguła ids stay as parenthetical technical references
            # (no display-name lookup exists for either today) -- R3-01 audit
            # fix strips this prefix and these ids from what the coordinator
            # actually sees, in MonthlyPlanning.tsx's resolveWarningText();
            # the "DAY_ONLY-N-FALLBACK-01 SOFT" prefix itself stays in this
            # raw string only for grep-based classification (tests/test_t018.py
            # and others), matching the "RULE-CODE SOFT: ..." shape the
            # REST-01 SOFT/WEEKLY-REST-01 SOFT warnings already use (T052).
            warnings.append(
                f"DAY_ONLY-N-FALLBACK-01 SOFT: '{assignment.employee_id}' ma nockę mimo ograniczenia do zmian dziennych, "
                f"na mocy wyjątku zmianowego (zapotrzebowanie {demand.demand_id}, data {anchor_date}, reguła {authorizing_id})"
            )


def _covering_demand(assignment: Assignment, state: PlanningState):
    for demand in state.shift_demands:
        if demand.demand_id == assignment.covers_demand_id:
            return demand
    for demand in state.boundary_shift_demands:
        if demand.demand_id == assignment.covers_demand_id and demand.schedule_version_id == assignment.schedule_version_id:
            return demand
    return None


def _covered_demands(assignment: Assignment, state: PlanningState) -> list:
    """T022-F1: every state.shift_demands whose interval actually overlaps this Assignment (same interval-truth
    COVERAGE-01 uses) -- a spanning PRIMARY cannot hide a covered demand behind a different covers_demand_id tag.
    Falls back to the tagged demand only when the interval overlaps no current-month demand at all."""
    overlapping = [d for d in state.shift_demands if assignment.start_datetime < d.end_datetime and assignment.end_datetime > d.start_datetime]
    if overlapping:
        return overlapping
    demand = _covering_demand(assignment, state)
    return [demand] if demand is not None else []


def _demand_kind(demand, profile) -> ShiftKind | None:
    # T022-R3-1: classify_demand is the frozen, single legacy-fallback implementation (brief.md:124-126) -- no local duplicate.
    try:
        return classify_demand(demand, profile)
    except UnclassifiedShiftError:
        return None


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
        if demand is not None and _demand_kind(demand, state.profile) == ShiftKind.N:
            n_dates_by_employee.setdefault(assignment.employee_id, set()).add(assignment.start_datetime.date())

    for boundary in state.boundary_assignments:
        if boundary.role != AssignmentRole.PRIMARY or boundary.state == AssignmentState.CANCELLED:
            continue
        demand = _covering_demand(boundary, state)
        if demand is not None and _demand_kind(demand, state.profile) == ShiftKind.N:
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


def _check_day_shift_off(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str]) -> None:
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
                details.append(ViolationDetail("DAY_SHIFT_OFF-01", (assignment.assignment_id,), f"DAY_SHIFT_OFF-01: {assignment.employee_id} starts assignment {assignment.assignment_id} on day off {start_date}"))
            end_date = assignment.end_datetime.date()
            if end_date != start_date and lo <= end_date <= hi:
                # ROTA-T055 R2-01: Polish wording + quoted employee_id, see
                # the DAY_ONLY-N-FALLBACK-01 SOFT note above. assignment_id
                # is dropped -- the date already identifies which day off for
                # a coordinator, and there is no display-name lookup for it.
                warnings.append(f"DAY_SHIFT_OFF-01 SOFT: '{assignment.employee_id}' ma zmianę kończącą się w trakcie dnia wolnego ({end_date})")


_RELEVANT_UNAVAILABILITY_KINDS = (AvailabilityKind.UNAVAILABLE_24H, AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)

# arch/spec.md:393-394 freezes UNAVAILABLE_24H's code as "UNAVAILABLE-01" (not "UNAVAILABLE_24H-01", R26-2); every other kind's code matches its enum value.
_CONDITION_CODE = {
    AvailabilityKind.UNAVAILABLE_24H: "UNAVAILABLE-01",
    AvailabilityKind.SICK_LEAVE: "SICK_LEAVE-01",
    AvailabilityKind.LEAVE_GRANTED: "LEAVE_GRANTED-01",
}


def _check_leave_and_unavailable(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """Owner decision 2026-08-14: when SICK_LEAVE/LEAVE_GRANTED intersect, only SICK_LEAVE-01 is reported; other kinds report independently (R26-1)."""
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        overlapping_by_kind: dict[AvailabilityKind, AvailabilityRecord] = {}
        for record in records_by_employee.get(assignment.employee_id, []):
            if not record.active or record.kind not in _RELEVANT_UNAVAILABILITY_KINDS:
                continue
            if overlaps_date_range(assignment.start_datetime, assignment.end_datetime, record.start_date, record.end_date):
                overlapping_by_kind.setdefault(record.kind, record)

        sick = overlapping_by_kind.get(AvailabilityKind.SICK_LEAVE)
        leave = overlapping_by_kind.get(AvailabilityKind.LEAVE_GRANTED)
        suppress_leave_granted = sick is not None and leave is not None and max(sick.start_date, leave.start_date) <= min(sick.end_date, leave.end_date)

        for kind in _RELEVANT_UNAVAILABILITY_KINDS:
            record = overlapping_by_kind.get(kind)
            if record is None:
                continue
            if kind == AvailabilityKind.LEAVE_GRANTED and suppress_leave_granted:
                continue
            code = _CONDITION_CODE[kind]
            details.append(ViolationDetail(code, (assignment.assignment_id,), f"{code}: {assignment.employee_id} assignment {assignment.assignment_id} overlaps {kind.value} {record.start_date}-{record.end_date}"))


def _check_leave_plan(state: PlanningState, assignments: list[Assignment], warnings: list[str]) -> None:
    """LEAVE_PLAN-01: a collision doesn't block the Assignment but must be visible as a warning (R17-4: reaches both existing and solved Assignments uniformly)."""
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        for record in records_by_employee.get(assignment.employee_id, []):
            if not record.active or record.kind != AvailabilityKind.LEAVE_PLAN:
                continue
            if overlaps_date_range(assignment.start_datetime, assignment.end_datetime, record.start_date, record.end_date):
                # ROTA-T055 R2-01: Polish wording + quoted employee_id, same
                # reasoning as DAY_ONLY-N-FALLBACK-01 SOFT above.
                warnings.append(
                    f"LEAVE_PLAN-01 SOFT: '{assignment.employee_id}' ma zmianę pokrywającą się z planowanym urlopem "
                    f"({record.start_date}–{record.end_date})"
                )


def _check_external(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """EXTERNAL-01: X/Y need an active, confirmed ExternalSupportWindow for the right employee and, when restricted, the right ShiftKind (R13-4)."""
    membership_kind_by_employee = {m.employee_id: m.membership_kind for m in state.memberships if m.site_id == state.site.site_id}
    for assignment in assignments:
        if membership_kind_by_employee.get(assignment.employee_id) != MembershipKind.EXTERNAL_SUPPORT:
            continue
        if not state.profile.external_support_enabled:
            # R16-2: a window doesn't turn on a capability the profile switched off (SITE-01).
            details.append(ViolationDetail("EXTERNAL-01", (assignment.assignment_id,), f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} uses EXTERNAL_SUPPORT but profile.external_support_enabled is false"))
            continue
        # T022-F1: a window must cover EVERY kind the Assignment's actual interval touches, not just the tagged demand's kind.
        covered_demands = _covered_demands(assignment, state)
        kinds = {_demand_kind(d, state.profile) for d in covered_demands}
        if None in kinds:
            # T022-R2-1: an unclassifiable covered demand cannot be verified against any window, restricted or not.
            details.append(ViolationDetail("EXTERNAL-01", (assignment.assignment_id,), f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} covers an unclassifiable demand"))
            continue
        kinds = kinds or {None}
        covered = any(
            w.active and w.site_id == state.site.site_id
            and w.employee_id == assignment.employee_id
            and w.start_datetime <= assignment.start_datetime
            and w.end_datetime >= assignment.end_datetime
            and all(w.allowed_shift_kind is None or w.allowed_shift_kind == k for k in kinds)
            for w in state.external_windows
        )
        if not covered:
            details.append(ViolationDetail("EXTERNAL-01", (assignment.assignment_id,), f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} has no covering active ExternalSupportWindow"))


def _check_site_rules(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """ROTA-T007: re-checks every applicable HARD SiteRule against every PRIMARY. Violation code IS the exact rule_version_id.
    T022-F1: every actually-covered ShiftDemand gets its own weekday anchor/kind, never the Assignment's own start date."""
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        for demand in _covered_demands(assignment, state):
            shift_kind = _demand_kind(demand, state.profile)
            anchor_date = demand.start_datetime.date()
            applicable = hard_rules_applicable_on(state.site_rules, state.site_rule_applicability, anchor_date)
            if shift_kind is None:
                # T022-R1-2: an applicable HARD rule's compliance cannot be verified for an unclassifiable demand -- fail closed rather than silently skip.
                if applicable:
                    details.append(ViolationDetail("SITE_RULE-01", (assignment.assignment_id,), f"SITE_RULE-01: {assignment.employee_id} assignment {assignment.assignment_id} covers unclassifiable demand {demand.demand_id} with applicable HARD SiteRules"))
                continue
            for rule in applicable:
                if rule_allows_assignment(rule, assignment.employee_id, anchor_date, shift_kind):
                    continue
                details.append(ViolationDetail(rule.rule_version_id, (assignment.assignment_id,), f"{rule.rule_version_id}: {assignment.employee_id} assignment {assignment.assignment_id} violates {rule.rule_kind} (demand {demand.demand_id})"))


def _is_well_formed_normal_h24_pair(d1, d2) -> bool:
    """T022-F3: fail-closed shape check -- components 1 and 2, each exactly 12h, directly consecutive, opposite D/N,
    matching template id, and matching required_rest_hours/required_primary_count (T022-R1-3)."""
    if {d1.work_period_component, d2.work_period_component} != {1, 2}:
        return False
    first, second = (d1, d2) if d1.work_period_component == 1 else (d2, d1)
    if first.shift_kind is None or second.shift_kind is None or first.shift_kind == second.shift_kind:
        return False
    if first.end_datetime != second.start_datetime:
        return False
    if first.required_rest_hours != second.required_rest_hours or first.required_primary_count != second.required_primary_count:
        return False
    hours1 = (first.end_datetime - first.start_datetime).total_seconds() / 3600
    hours2 = (second.end_datetime - second.start_datetime).total_seconds() / 3600
    return hours1 == 12 and hours2 == 12


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


def _check_rest(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str]) -> float | None:
    """REST-01, per-work-period -- 24h pairs have no internal check, earlier period's rest governs, only target-touching edges count.
    ROTA-T023b sec.6/7: under OCHRONA the floor after an exact 24h target-Site WorkPeriod rises to >=24h; never applied to other-Site periods."""
    ochrona = state.site.planning_regime == SitePlanningRegime.OCHRONA
    # B-R10-3: identity is (schedule_version_id, assignment_id), not the bare local id (tests/test_audit_t009_r6.py).
    target_keys = {(a.schedule_version_id, a.assignment_id) for a in assignments}
    other_site_list = _not_cancelled(state.other_site_assignments)
    other_site_keys = {(a.schedule_version_id, a.assignment_id) for a in other_site_list}
    all_assignments = list(assignments) + other_site_list + _not_cancelled(state.boundary_assignments)
    # ROTA-T052: S1 (PERIODIC_TRAINING) still participates in overlap
    # detection below, but is exempt from the REST-01 gap requirement in
    # either direction (brief section 2 point 4) -- tracked by the real
    # (schedule_version_id, assignment_id) identity, never the bare local
    # id (R5-01 audit fix: a bare id can legally repeat across different
    # ScheduleVersions/Sites, B-R10-3/T036), and checked against
    # component_keys, not component_ids.
    periodic_training_keys = {
        (a.schedule_version_id, a.assignment_id) for a in all_assignments if a.role == AssignmentRole.PERIODIC_TRAINING
    }
    all_components = [PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id) for a in all_assignments]
    for key, ids, reasons in find_malformed_periods(all_components):
        details.append(ViolationDetail("WORK_PERIOD-01", ids, f"WORK_PERIOD-01: period {key}: {'; '.join(reasons)}"))
    min_rest = None
    for employee_id in {c.employee_id for c in all_components}:
        components = [c for c in all_components if c.employee_id == employee_id]
        # CROSS-SITE-ZERO-GAP-01 (T022-R1-5): a persisted period_id shared between a current/boundary component and
        # an other-Site component must fail closed BEFORE group_into_periods merges them into one WorkPeriod and
        # erases Site identity -- otherwise no cross-Site pair remains for the check below to see at all.
        by_period_id: dict[str, list] = {}
        for c in components:
            if c.period_id:
                by_period_id.setdefault(c.period_id, []).append(c)
        for period_id, members in by_period_id.items():
            member_keys = {(m.schedule_version_id, m.component_id) for m in members}
            if any(k in other_site_keys for k in member_keys) and any(k not in other_site_keys for k in member_keys):
                ids = tuple(m.component_id for m in members)
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} work_period_id {period_id!r} is shared across different Sites", affected_employee_id=employee_id))
        periods = group_into_periods(components)
        # Every (target, other) pair, not only sorted neighbors (B-R10-3).
        target_periods = [p for p in periods if not target_keys.isdisjoint(p.component_keys)]
        history_periods = [p for p in periods if p not in target_periods]
        pairs = [(tp, h) for tp in target_periods for h in history_periods] + list(combinations(target_periods, 2))
        for tp, other in pairs:
            earlier, later = (tp, other) if tp.start <= other.start else (other, tp)
            ids = (earlier.component_ids[-1], later.component_ids[0])
            if periods_overlap(earlier, later):
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} overlapping assignments", affected_employee_id=employee_id))
                continue
            # OWNER 2026-09-04 (T052 correction after contract PASS): S1 no
            # longer silently skips REST-01's gap requirement -- it never
            # HARD-blocks (a coordinator placement must never be rejected
            # for this), but a real rest shortfall around S1 must be
            # reported as a SOFT warning (Paweł: "nie możemy świadomie
            # pisać programu łamiącego prawo" -- the tool must not stay
            # silent about a real labor-law rest violation just because it
            # won't block it). The zero-gap/illegal-continuous-pair check
            # stays HARD-exempt for S1: it targets a specific PRIMARY
            # 12h+12h-hiding-24h pattern, not a real rest measurement, and
            # does not apply to S1's variable-duration manual fact.
            involves_periodic_training = not periodic_training_keys.isdisjoint(earlier.component_keys) or not periodic_training_keys.isdisjoint(later.component_keys)
            if involves_periodic_training:
                gap = (later.start - earlier.end).total_seconds() / 3600
                required_rest = effective_required_rest_after_hours(earlier, ochrona=ochrona and not any(k in other_site_keys for k in earlier.component_keys))
                if gap < required_rest:
                    # ROTA-T055 R2-01: quote employee_id for MonthlyPlanning.tsx's
                    # resolveWarningText(); drop the raw assignment-id pair --
                    # meaningless to a coordinator and covered by no test.
                    warnings.append(
                        f"REST-01 SOFT: '{employee_id}': S1 narusza wymagany odpoczynek "
                        f"({gap:.1f}h < {required_rest}h)"
                    )
                continue
            # CROSS-SITE-ZERO-GAP-01 (T022, OWNER-T022-03): zero-time continuation onto a different Site is illegal regardless of configured rest/can_work_24h.
            cross_site = any(k in other_site_keys for k in earlier.component_keys) != any(k in other_site_keys for k in later.component_keys)
            if (cross_site and earlier.end == later.start) or forms_illegal_continuous_pair(earlier, later):
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} {ids[0]}->{ids[1]}: zero-gap continuous work is not permitted", affected_employee_id=employee_id))
                min_rest = 0.0 if min_rest is None else min(min_rest, 0.0)
                continue
            gap = (later.start - earlier.end).total_seconds() / 3600
            min_rest = gap if min_rest is None else min(min_rest, gap)
            required_rest = effective_required_rest_after_hours(earlier, ochrona=ochrona and not any(k in other_site_keys for k in earlier.component_keys))
            if gap < required_rest:
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} {ids[0]}->{ids[1]}: only {gap:.1f}h", affected_employee_id=employee_id))
    return min_rest


def _check_load(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> tuple[dict[str, float], dict[str, tuple], dict[str, tuple]]:
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    grouped = _by_employee(all_assignments)
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    windows = rolling_windows(state.month, num_days)
    threshold = state.profile.rolling_7d_decision_threshold_hours
    max_load: dict[str, float] = {}
    max_window: dict[str, tuple] = {}
    # R5-1: display-friendly max_window (calendar dates) can't answer real overlap for an overnight shift -- callers needing real relevance (engine._load_decision) use the datetime form below.
    max_window_datetimes: dict[str, tuple] = {}
    for employee_id, employee_assignments in grouped.items():
        worst = 0.0
        worst_window = None
        worst_window_datetimes = None
        ids = tuple(a.assignment_id for a in employee_assignments)
        for window_start, window_end in windows:
            hours = sum(overlap_hours(a.start_datetime, a.end_datetime, window_start, window_end) for a in employee_assignments)
            if hours > worst:
                worst = hours
                worst_window = (window_start.date(), (window_end - timedelta(days=1)).date())
                worst_window_datetimes = (window_start, window_end)
            if hours > threshold:
                details.append(ViolationDetail("LOAD-01", ids, f"LOAD-01: {employee_id} has {hours}h in window {window_start.date()}-{window_end.date()}"))
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


def _is_full_hour(dt) -> bool:
    return dt.minute == 0 and dt.second == 0 and dt.microsecond == 0


def _check_full_hour(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """OWNER-T022-01: no partial-hour work anywhere. Defense-in-depth for malformed in-memory/legacy state reaching
    plan()/validate() without having passed the persistence-layer write-time guard. Covers every work boundary named
    by the contract -- current/boundary demands, current/boundary/other-Site Assignments (incl. REALIZED, since a
    pre-T022 fractional-hour historical row is still invalid) and the profile catalog itself (T022-R1-1)."""
    for demand in (*state.shift_demands, *state.boundary_shift_demands):
        if not _is_full_hour(demand.start_datetime) or not _is_full_hour(demand.end_datetime):
            details.append(ViolationDetail("FULL_HOUR-01", (), f"FULL_HOUR-01: demand {demand.demand_id} start/end is not a full clock hour", demand_ids=(demand.demand_id,)))
    for assignment in (*assignments, *state.existing_assignments, *state.boundary_assignments, *state.other_site_assignments, *state.holiday_history):
        if not _is_full_hour(assignment.start_datetime) or not _is_full_hour(assignment.end_datetime):
            details.append(ViolationDetail("FULL_HOUR-01", (assignment.assignment_id,), f"FULL_HOUR-01: assignment {assignment.assignment_id} start/end is not a full clock hour"))
    for shift in state.profile.standard_shifts:
        if not _is_full_hour(shift.start_time) or not _is_full_hour(shift.end_time):
            details.append(ViolationDetail("FULL_HOUR-01", (), f"FULL_HOUR-01: profile StandardShift kind={shift.kind.value} start/end is not a full clock hour"))


def _check_weekly_rest(
    state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str],
) -> None:
    """WEEKLY-REST-01 (ROTA-T023b sec.6/7): OCHRONA only. Per employee/complete settlement-week window
    (weekly_settlement_windows), target-Site non-CANCELLED work only (PRIMARY+TRAINEE); PASS needs >=35h free somewhere.
    Architect review A1: same-Site state.boundary_assignments (previous-month work spilling into day 1) also occupies
    time here -- matches solver's target_fixed exactly; state.other_site_assignments stays excluded (sec.7).

    OWNER 2026-09-04 (T052 correction after contract PASS): S1 still never
    HARD-blocks this HARD rule (never occupies time for the check above),
    but if adding S1's hours back in would push a week that otherwise
    clears 35h below it, that is a real labor-law rest violation the
    coordinator caused -- reported as a SOFT warning, never silently
    dropped (Paweł: the tool must not stay quiet about a real violation
    just because it won't block the save)."""
    if state.site.planning_regime != SitePlanningRegime.OCHRONA:
        return
    windows = weekly_settlement_windows(state.month)
    by_employee: dict[str, list[tuple]] = {}
    s1_intervals_by_employee: dict[str, list[tuple]] = {}
    for a in list(assignments) + _not_cancelled(state.boundary_assignments):
        # T52-07: S1 (PERIODIC_TRAINING) does not occupy time for this
        # check -- it must never interrupt/shorten the 35h weekly rest
        # window (brief section 2 point 4).
        if a.role == AssignmentRole.PERIODIC_TRAINING:
            s1_intervals_by_employee.setdefault(a.employee_id, []).append((a.start_datetime, a.end_datetime))
            continue
        by_employee.setdefault(a.employee_id, []).append((a.start_datetime, a.end_datetime))
    for employee_id, intervals in by_employee.items():
        s1_intervals = s1_intervals_by_employee.get(employee_id, [])
        for window_start, window_end in windows:
            free = max_uninterrupted_free_hours(window_start, window_end, intervals)
            week_label = f"{window_start.date()}-{(window_end - timedelta(days=1)).date()}"
            if free < WEEKLY_REST_REQUIRED_HOURS:
                ids = tuple(
                    a.assignment_id for a in assignments
                    if a.employee_id == employee_id and a.start_datetime < window_end and a.end_datetime > window_start
                )
                details.append(ViolationDetail("WEEKLY-REST-01", ids, f"WEEKLY-REST-01: {employee_id} only {free:.1f}h uninterrupted rest in week {week_label}", affected_employee_id=employee_id))
            elif s1_intervals:
                free_with_s1 = max_uninterrupted_free_hours(window_start, window_end, intervals + s1_intervals)
                if free_with_s1 < WEEKLY_REST_REQUIRED_HOURS:
                    # ROTA-T055 R2-01: quote employee_id for resolveWarningText().
                    warnings.append(
                        f"WEEKLY-REST-01 SOFT: '{employee_id}': S1 narusza 35h nieprzerwanego odpoczynku "
                        f"w tygodniu {week_label} ({free_with_s1:.1f}h)"
                    )


def validate(state: PlanningState, assignments: list[Assignment]) -> IndependentValidationReport:
    """Recheck every HARD rule from scratch against the final Assignment set."""
    details: list[ViolationDetail] = []
    warnings: list[str] = []
    # T022-R2-2: full-hour is a structural input-shape check, not a real-work check -- it must see every Assignment
    # including CANCELLED, before state-based filtering makes a malformed boundary invisible.
    _check_full_hour(state, assignments, details)
    assignments = _not_cancelled(assignments)

    # REPLAN (ASSIGN-03: REALIZED work MUST NOT be changed): eligibility/availability HARD checks (membership,
    # DAY_ONLY, DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, EXTERNAL-01) only make sense going forward -- data
    # recorded after the fact must not retroactively break FEASIBLE for something REPLAN must leave untouched.
    # COVERAGE-01, ASSIGN-03/04, REST-01 and LOAD-01 still consider every assignment (real elapsed time/identity).
    for_eligibility_checks = [a for a in assignments if a.state != AssignmentState.REALIZED]

    _check_coverage(state, assignments, details)
    _check_replan_preserves_fixed(state, assignments, details)
    _check_trainee_mentor_reference(assignments, details)
    _check_membership_enabled(state, for_eligibility_checks, details)
    _check_day_only(state, for_eligibility_checks, details, warnings)
    _check_night_streak(state, assignments, details)
    _check_day_shift_off(state, for_eligibility_checks, details, warnings)
    _check_leave_and_unavailable(state, for_eligibility_checks, details)
    _check_leave_plan(state, for_eligibility_checks, warnings)
    _check_external(state, for_eligibility_checks, details)
    _check_site_rules(state, for_eligibility_checks, details)
    _check_24h_same_person(state, assignments, details)
    _check_emergency_pairs(state, assignments, details)
    min_rest = _check_rest(state, assignments, details, warnings)
    _check_weekly_rest(state, assignments, details, warnings)
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
