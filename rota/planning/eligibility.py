"""Determine which employees may be assigned to a given ShiftDemand.

Implements MEMBERSHIP-01/02, DAY_ONLY-01, DAY_SHIFT_OFF-01, UNAVAILABLE-01,
LEAVE_GRANTED-01, LEAVE_PLAN-01 and EXTERNAL-01 eligibility checks. Rest
(REST-01) and load (LOAD-01) are cross-demand constraints and are handled
separately in the solver, not here.

ROTA-T016 (owner decision 2026-08-16): EMP-02 (Employee.active_from/
active_to gating eligibility) is retired. The program does not decide
whether an Employee may work; it plans for the current SiteMembership
roster the coordinator maintains. MEMBERSHIP-01 (membership.enabled) is the
sole remaining source of truth for "may this person be assigned here."

Audit round 12 (tests_r12.txt FINDING 2) found that the EXTERNAL_SUPPORT path
only checked the window and skipped membership.enabled, DAY_ONLY-01 and
availability blocks entirely -- i.e. an EXTERNAL employee with an active
window could be scheduled while on LEAVE_GRANTED. MEMBERSHIP.enabled and the
availability/DAY_ONLY gates are HARD rules that do not carry a
membership-kind qualifier in arch/spec.md, so they are applied identically
to LOCAL and EXTERNAL; EXTERNAL additionally requires a covering
ExternalSupportWindow (MEMBERSHIP-02, EXTERNAL-01).

ROTA-T007 (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md): applicable RESOLVED
HARD SiteRuleVersions ARE interpreted here, via
rota.planning.site_rules.rule_allows_assignment(), for the frozen initial
three-kind catalog (EMPLOYEE_ALLOWED_SHIFT_KINDS, EMPLOYEE_ALLOWED_WEEKDAYS,
EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS). This module still performs no
persistence I/O -- the caller supplies applicable_hard_rules, already
sliced from PlanningState.site_rules/site_rule_applicability. Only rule
kinds beyond that initial catalog remain a separate CONTRACT_GAP.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteProfile,
)
from rota.domain import SiteRuleVersion
from rota.planning.shift_catalog import normalized_catalog_kind
from rota.planning.site_rules import day_only_n_exception_authorizing_rule_version_id, rule_allows_assignment
from rota.planning.timeutil import overlaps_date_range


@dataclass(frozen=True)
class EligibilityCheck:
    eligible: bool
    leave_plan_collision: bool
    blocked_reason: Optional[str] = None
    # T018 B3/B4: set only when this slot's DAY_ONLY-01 gate was bypassed by
    # an applicable EMPLOYEE_DAY_ONLY_N_EXCEPTION in a fallback-enabled pass
    # -- the canonical authorizing rule_version_id (site_rules.py's single
    # min(rule_version_id) owner), for solver exceptional_n_count provenance.
    day_only_fallback_rule_version_id: Optional[str] = None


def overlaps_availability(demand: ShiftDemand, record: AvailabilityRecord) -> bool:
    """Return True if demand's interval overlaps record's inclusive calendar-date range."""
    return overlaps_date_range(demand.start_datetime, demand.end_datetime, record.start_date, record.end_date)


_BLOCKING_KIND_PRIORITY = (
    AvailabilityKind.DAY_SHIFT_OFF,
    AvailabilityKind.UNAVAILABLE_24H,
    AvailabilityKind.SICK_LEAVE,
    AvailabilityKind.LEAVE_GRANTED,
)
# Owner decision 2026-08-14: when SICK_LEAVE and LEAVE_GRANTED overlap the
# same day, the reported reason must be SICK_LEAVE-01, not LEAVE_GRANTED-01
# -- a sick note handed in during an approved vacation is the real-world
# case (sick leave interrupts the vacation), so the visible reason must
# switch from "urlop" to "chorobowe" on those days, not depend on which
# AvailabilityRecord happened to be listed first. DAY_SHIFT_OFF and
# UNAVAILABLE_24H are ranked ahead only for a fixed, deterministic order;
# no cross-priority among those was requested or is implied. This function
# returns a single reason by design (EligibilityCheck.blocked_reason is one
# solver-facing exclusion reason, not the exhaustive violation list that
# feeds DECISION_REQUIRED -- that list comes from validator.py), so unlike
# validator._check_leave_and_unavailable (FINDING R26-1) a fixed priority
# order is the correct shape here, not a bug to remove.

# arch/spec.md:393-394 freezes the condition code for UNAVAILABLE_24H as
# "UNAVAILABLE-01", not "UNAVAILABLE_24H-01" (audit round 26, FINDING
# R26-2) -- matches validator._CONDITION_CODE.
_CONDITION_CODE = {
    AvailabilityKind.DAY_SHIFT_OFF: "DAY_SHIFT_OFF-01",
    AvailabilityKind.UNAVAILABLE_24H: "UNAVAILABLE-01",
    AvailabilityKind.SICK_LEAVE: "SICK_LEAVE-01",
    AvailabilityKind.LEAVE_GRANTED: "LEAVE_GRANTED-01",
}


def _blocked_by_availability(
    demand: ShiftDemand, records: list[AvailabilityRecord]
) -> tuple[Optional[str], bool]:
    """Return (blocking_reason or None, leave_plan_collision). If multiple
    kinds block the same day, the reason follows _BLOCKING_KIND_PRIORITY
    rather than the order records happen to appear in."""
    blocking_kinds: set[AvailabilityKind] = set()
    leave_plan_collision = False
    for record in records:
        if not record.active:
            continue
        if record.kind == AvailabilityKind.DAY_SHIFT_OFF:
            if record.start_date <= demand.start_datetime.date() <= record.end_date:
                blocking_kinds.add(record.kind)
        elif record.kind in (AvailabilityKind.UNAVAILABLE_24H, AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED):
            if overlaps_availability(demand, record):
                blocking_kinds.add(record.kind)
        elif record.kind == AvailabilityKind.LEAVE_PLAN:
            if overlaps_availability(demand, record):
                leave_plan_collision = True
    for kind in _BLOCKING_KIND_PRIORITY:
        if kind in blocking_kinds:
            return _CONDITION_CODE[kind], leave_plan_collision
    return None, leave_plan_collision


def _blocked_by_site_rules(
    employee_id: str, demand: ShiftDemand, shift_kind: ShiftKind, applicable_hard_rules: list[SiteRuleVersion]
) -> Optional[str]:
    """ROTA-T007 (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md MULTIPLE RULES):
    every applicable HARD rule must pass (AND) -- the first one that doesn't
    is the blocker, identified by its exact rule_version_id, never a generic
    condition code."""
    for rule in applicable_hard_rules:
        if not rule_allows_assignment(rule, employee_id, demand.start_datetime.date(), shift_kind):
            return rule.rule_version_id
    return None


def is_all_24h_profile(profile: SiteProfile) -> bool:
    """part_b_work_period_rest.md: an all-24h profile (every StandardShift
    normalizes to catalog_kind=24h) ignores SiteMembership.can_work_24h; a
    mixed profile enforces it. A profile with no standard_shifts is not
    "all-24h"."""
    shifts = profile.standard_shifts
    return bool(shifts) and all(normalized_catalog_kind(s) == ShiftCatalogKind.H24 for s in shifts)


def _common_hard_gate(
    employee: Employee,
    membership: SiteMembership,
    demand: ShiftDemand,
    shift_kind: ShiftKind,
    profile: SiteProfile,
    availability_records: list[AvailabilityRecord],
    applicable_hard_rules: list[SiteRuleVersion],
    allow_day_only_n_fallback: bool = False,
) -> EligibilityCheck:
    """Gates that apply regardless of membership_kind: MEMBERSHIP.enabled,
    SHIFT-24-01, DAY_ONLY-01, DAY_SHIFT_OFF-01, UNAVAILABLE-01,
    LEAVE_GRANTED-01, LEAVE_PLAN-01, and (ROTA-T007) applicable HARD
    SiteRules."""
    if not membership.enabled:
        return EligibilityCheck(False, False, "MEMBERSHIP_DISABLED")
    # SHIFT-24-01 (NORMAL 24h SAME-PERSON HARD, part_b_work_period_rest.md):
    # a mixed 12h/24h profile requires can_work_24h for a catalog_kind=24h
    # demand; an all-24h profile ignores the flag. Never a bypass of the
    # other gates below -- e.g. a DAY_ONLY employee still cannot take the N
    # component of a normal 24h occurrence.
    if demand.catalog_kind == ShiftCatalogKind.H24 and not membership.can_work_24h and not is_all_24h_profile(profile):
        return EligibilityCheck(False, False, "SHIFT-24-01")
    day_only_fallback_rule_version_id = None
    if profile.day_only_blocks_n and employee.day_only and shift_kind == ShiftKind.N:
        # T018 DAY-ONLY-N-FALLBACK-01: the exception NEVER exempts DAY_ONLY-01
        # in a normal pass anymore -- only a fallback-enabled pass may consult
        # it, and only then does a legal match lift the block, still leaving
        # every other HARD gate below in force.
        if allow_day_only_n_fallback:
            day_only_fallback_rule_version_id = day_only_n_exception_authorizing_rule_version_id(
                applicable_hard_rules, employee.employee_id
            )
        if day_only_fallback_rule_version_id is None:
            return EligibilityCheck(False, False, "DAY_ONLY-01")
    reason, leave_plan_collision = _blocked_by_availability(demand, availability_records)
    if reason:
        return EligibilityCheck(False, False, reason)
    site_rule_block = _blocked_by_site_rules(employee.employee_id, demand, shift_kind, applicable_hard_rules)
    if site_rule_block:
        return EligibilityCheck(False, False, site_rule_block)
    return EligibilityCheck(True, leave_plan_collision, None, day_only_fallback_rule_version_id)


def _external_window_covers(
    employee_id: str, demand: ShiftDemand, shift_kind: ShiftKind, site_id: str, windows: list[ExternalSupportWindow]
) -> bool:
    """Audit round 13 FINDING R13-4: a window belonging to a different employee
    was accepted because employee_id was never compared."""
    for window in windows:
        if not window.active or window.site_id != site_id or window.employee_id != employee_id:
            continue
        if window.allowed_shift_kind is not None and window.allowed_shift_kind != shift_kind:
            continue
        if window.start_datetime <= demand.start_datetime and window.end_datetime >= demand.end_datetime:
            return True
    return False


def check_eligibility(
    employee: Employee,
    membership: SiteMembership,
    demand: ShiftDemand,
    shift_kind: ShiftKind,
    profile: SiteProfile,
    availability_records: list[AvailabilityRecord],
    external_windows: list[ExternalSupportWindow],
    site_id: str,
    applicable_hard_rules: list[SiteRuleVersion] = (),
    allow_day_only_n_fallback: bool = False,
) -> EligibilityCheck:
    """Return whether employee may cover demand, plus a reason code when blocked."""
    gate = _common_hard_gate(
        employee, membership, demand, shift_kind, profile, availability_records, applicable_hard_rules,
        allow_day_only_n_fallback,
    )
    if not gate.eligible:
        return gate
    if membership.membership_kind == MembershipKind.LOCAL:
        return gate
    # FINDING R16-2: SiteProfile.external_support_enabled=false means the
    # profile does not provide for X/Y at all (arch/spec.md:49-50, SITE-01);
    # an active ExternalSupportWindow does not turn on a capability the
    # profile has switched off.
    if not profile.external_support_enabled:
        return EligibilityCheck(False, False, "EXTERNAL_SUPPORT_DISABLED")
    if _external_window_covers(employee.employee_id, demand, shift_kind, site_id, external_windows):
        return gate
    return EligibilityCheck(False, False, "EXTERNAL-01")


if __name__ == "__main__":
    print("eligibility module OK")
