"""Membership/role/availability HARD checks split out of validator.py
(2026-09 oversized-file refactor, mechanical-only, zero behavior change):
MEMBERSHIP-01, ROLE-01, DAY_ONLY-01, DAY_SHIFT_OFF-01, UNAVAILABLE-01/
SICK_LEAVE-01/LEAVE_GRANTED-01, UNAVAILABLE_TIME-01, LEAVE_PLAN-01,
EXTERNAL-01, SITE_RULE-01/rule_version_id. Each of these mirrors the
corresponding gate in rota.planning.eligibility -- same shared oracles,
no second algorithm."""
from __future__ import annotations

from rota.domain import Assignment, AssignmentRole, AvailabilityKind, AvailabilityRecord, MembershipKind, ShiftKind
from rota.planning.availability import unavailable_time_window_overlaps
from rota.planning.eligibility import role_covers
from rota.planning.shift_catalog import dn_semantics_apply
from rota.planning.site_rules import SHIFT_KIND_SPECIFIC_RULE_KINDS, day_only_n_exception_authorizing_rule_version_id, hard_rules_applicable_on, rule_allows_assignment
from rota.planning.state import PlanningState
from rota.planning.timeutil import overlaps_date_range
from rota.planning.validator_shared import ViolationDetail, _covered_demands, _covering_demand, _demand_kind


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
            if not dn_semantics_apply(demand, state.site.planning_regime):
                # ROTA-T065 audit R3-01 fix: D/N never carries OCHRONA
                # legal meaning for an ORDINARY site, regardless of role
                # (OWNER_DECISION 2026-09-13).
                continue
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


def _check_role(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """ROLE-01 (ROTA-T065-CONFIGURABLE-ROLES section 8): independent
    anti-drift mirror of eligibility.py's role_covers -- the same shared
    function both call, so there is exactly one ROLE-01 owner (brief
    section 8: "jeden gate"), run here against the final/manual Assignment
    set exactly as _check_membership_enabled/_check_external mirror their
    eligibility.py counterparts. required_role_id is None for every
    OCHRONA/legacy demand, so this is a strict no-op there. Applies
    identically to LOCAL and EXTERNAL_SUPPORT membership -- no separate
    branch for either.

    Prefers _covering_demand (the assignment's OWN tagged demand): unlike
    D/N classification (a property of the moment in time, identical for
    every demand overlapping it), required_role is a property of the
    SPECIFIC posted position -- brief section 17 T65-01 explicitly allows
    two demands with different roles to occupy the exact same interval
    (two different roles both on duty at once), so an overlap match would
    falsely blame a correctly-tagged assignment for a same-interval
    sibling's role.

    ROTA-T065 audit R2-01 fix: an untagged Assignment (covers_demand_id=
    None -- the public manual-correction DTO permits this) has no single
    demand to prefer, so it falls back to every demand whose interval
    actually overlaps it (_covered_demands) -- fail closed, matching
    _check_day_only's T022-R1-2 precedent, rather than silently passing
    an untagged manual write through the gate."""
    membership_by_employee = {m.employee_id: m for m in state.memberships if m.site_id == state.site.site_id}
    for assignment in assignments:
        tagged = _covering_demand(assignment, state)
        candidate_demands = [tagged] if tagged is not None else _covered_demands(assignment, state)
        membership = membership_by_employee.get(assignment.employee_id)
        for demand in candidate_demands:
            if demand is None or demand.required_role_id is None:
                continue
            # No local membership at all is the same fail-closed outcome as
            # a membership whose position doesn't match -- role_covers
            # needs a membership object to compare against, so a missing
            # one is never silently skipped.
            covered = membership is not None and role_covers(demand, membership, state.role_coverage_authorizations)
            if not covered:
                details.append(ViolationDetail(
                    "ROLE-01", (assignment.assignment_id,),
                    f"ROLE-01: {assignment.employee_id} assignment {assignment.assignment_id} covers demand "
                    f"{demand.demand_id} requiring role {demand.required_role_name}, not permitted for this membership",
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


_RELEVANT_UNAVAILABILITY_KINDS = (
    AvailabilityKind.UNAVAILABLE_24H, AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED,
    # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 5: same whole-day
    # validator gate as the other kinds above.
    AvailabilityKind.DELEGACJA,
)

# arch/spec.md:393-394 freezes UNAVAILABLE_24H's code as "UNAVAILABLE-01" (not "UNAVAILABLE_24H-01", R26-2); every other kind's code matches its enum value.
_CONDITION_CODE = {
    AvailabilityKind.UNAVAILABLE_24H: "UNAVAILABLE-01",
    AvailabilityKind.SICK_LEAVE: "SICK_LEAVE-01",
    AvailabilityKind.LEAVE_GRANTED: "LEAVE_GRANTED-01",
    AvailabilityKind.DELEGACJA: "DELEGACJA-01",
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


def _check_unavailable_time_window(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """UNAVAILABLE_TIME-01 (ROTA-T065-ORDINARY-TIME-AVAILABILITY brief.md
    section 9): same shared oracle as eligibility.py, no second overlap
    algorithm -- a real assignment overlapping an active daily hourly
    window is always caught, even if it reached this validator via a
    conscious Manual Correction."""
    records_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        records_by_employee.setdefault(record.employee_id, []).append(record)

    for assignment in assignments:
        for record in records_by_employee.get(assignment.employee_id, []):
            if unavailable_time_window_overlaps(record, assignment.start_datetime, assignment.end_datetime):
                details.append(ViolationDetail(
                    "UNAVAILABLE_TIME-01", (assignment.assignment_id,),
                    f"UNAVAILABLE_TIME-01: {assignment.employee_id} assignment {assignment.assignment_id} "
                    f"overlaps hourly window {record.start_time}-{record.end_time} ({record.start_date}-{record.end_date})",
                ))


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
        # ROTA-T065 audit R3-01 fix: only demands where D/N carries real
        # OCHRONA legal meaning (dn_semantics_apply) contribute a required
        # kind here -- a role-bearing/ORDINARY demand's technical D/N must
        # never turn a window's allowed_shift_kind restriction into a block.
        covered_demands = _covered_demands(assignment, state)
        dn_relevant_demands = [d for d in covered_demands if dn_semantics_apply(d, state.site.planning_regime)]
        kinds = {_demand_kind(d, state.profile) for d in dn_relevant_demands}
        if None in kinds:
            # T022-R2-1: an unclassifiable covered demand cannot be verified against any window, restricted or not.
            details.append(ViolationDetail("EXTERNAL-01", (assignment.assignment_id,), f"EXTERNAL-01: {assignment.employee_id} assignment {assignment.assignment_id} covers an unclassifiable demand"))
            continue
        if not covered_demands:
            # Preserves the pre-T065 edge case (an assignment covering no
            # demand at all): only an unrestricted window can match.
            kinds = {None}
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
            # ROTA-T065 audit R3-01 fix: dn_relevant=False skips only the
            # shift-kind-specific rule kinds below -- EMPLOYEE_ALLOWED_
            # WEEKDAYS is purely date-based and still applies to every demand.
            dn_relevant = dn_semantics_apply(demand, state.site.planning_regime)
            shift_kind = _demand_kind(demand, state.profile)
            anchor_date = demand.start_datetime.date()
            applicable = hard_rules_applicable_on(state.site_rules, state.site_rule_applicability, anchor_date)
            evaluable = [
                r for r in applicable
                if shift_kind is not None or r.rule_kind not in SHIFT_KIND_SPECIFIC_RULE_KINDS
            ]
            unevaluable_dn_specific = [
                r for r in applicable
                if shift_kind is None and r.rule_kind in SHIFT_KIND_SPECIFIC_RULE_KINDS and dn_relevant
            ]
            if unevaluable_dn_specific:
                # T022-R1-2: an applicable shift-kind-specific HARD rule's
                # compliance cannot be verified for an unclassifiable
                # demand -- fail closed rather than silently skip.
                details.append(ViolationDetail("SITE_RULE-01", (assignment.assignment_id,), f"SITE_RULE-01: {assignment.employee_id} assignment {assignment.assignment_id} covers unclassifiable demand {demand.demand_id} with applicable HARD SiteRules"))
            for rule in evaluable:
                if not dn_relevant and rule.rule_kind in SHIFT_KIND_SPECIFIC_RULE_KINDS:
                    continue
                if rule_allows_assignment(rule, assignment.employee_id, anchor_date, shift_kind):
                    continue
                details.append(ViolationDetail(rule.rule_version_id, (assignment.assignment_id,), f"{rule.rule_version_id}: {assignment.employee_id} assignment {assignment.assignment_id} violates {rule.rule_kind} (demand {demand.demand_id})"))


if __name__ == "__main__":
    print("planning.validator_checks_availability module OK")
