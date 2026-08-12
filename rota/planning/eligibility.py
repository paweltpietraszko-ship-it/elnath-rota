"""Determine which employees may be assigned to a given ShiftDemand.

Implements MEMBERSHIP-01/02, EMP-02, DAY_ONLY-01, DAY_SHIFT_OFF-01,
UNAVAILABLE-01, LEAVE_GRANTED-01, LEAVE_PLAN-01 and EXTERNAL-01 eligibility
checks. Rest (REST-01) and load (LOAD-01) are cross-demand constraints and
are handled separately in the solver, not here.

Audit round 12 (tests_r12.txt FINDING 2) found that the EXTERNAL_SUPPORT path
only checked the window and skipped membership.enabled, EMP-02 (active
period), DAY_ONLY-01 and availability blocks entirely -- i.e. an EXTERNAL
employee with an active window could be scheduled while on LEAVE_GRANTED.
EMP-02, MEMBERSHIP.enabled and the availability/DAY_ONLY gates are HARD rules
that do not carry a membership-kind qualifier in arch/spec.md, so they are
now applied identically to LOCAL and EXTERNAL; EXTERNAL additionally requires
a covering ExternalSupportWindow (MEMBERSHIP-02, EXTERNAL-01).

SiteRuleVersion (RESOLVED) is intentionally not interpreted here: rule_kind
catalog is CONTRACT_GAP per rota.domain.RuleParameters. Any active resolved
SiteRule beyond what is modeled through AvailabilityRecord/Employee fields is
out of scope for this experiment and is not silently applied.
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
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteProfile,
)
from rota.planning.timeutil import overlaps_date_range


@dataclass(frozen=True)
class EligibilityCheck:
    eligible: bool
    leave_plan_collision: bool
    blocked_reason: Optional[str] = None


def overlaps_availability(demand: ShiftDemand, record: AvailabilityRecord) -> bool:
    """Return True if demand's interval overlaps record's inclusive calendar-date range."""
    return overlaps_date_range(demand.start_datetime, demand.end_datetime, record.start_date, record.end_date)


def _employee_active(employee: Employee, demand: ShiftDemand) -> bool:
    start_date = demand.start_datetime.date()
    end_date = demand.end_datetime.date()
    if start_date < employee.active_from:
        return False
    if employee.active_to is not None and end_date > employee.active_to:
        return False
    return True


def _blocked_by_availability(
    demand: ShiftDemand, records: list[AvailabilityRecord]
) -> tuple[Optional[str], bool]:
    """Return (blocking_reason or None, leave_plan_collision)."""
    reason = None
    leave_plan_collision = False
    for record in records:
        if not record.active:
            continue
        if record.kind == AvailabilityKind.DAY_SHIFT_OFF:
            if record.start_date <= demand.start_datetime.date() <= record.end_date:
                reason = "DAY_SHIFT_OFF-01"
        elif record.kind == AvailabilityKind.UNAVAILABLE_24H:
            if overlaps_availability(demand, record):
                reason = "UNAVAILABLE-01"
        elif record.kind == AvailabilityKind.LEAVE_GRANTED:
            if overlaps_availability(demand, record):
                reason = "LEAVE_GRANTED-01"
        elif record.kind == AvailabilityKind.LEAVE_PLAN:
            if overlaps_availability(demand, record):
                leave_plan_collision = True
    return reason, leave_plan_collision


def _common_hard_gate(
    employee: Employee,
    membership: SiteMembership,
    demand: ShiftDemand,
    shift_kind: ShiftKind,
    profile: SiteProfile,
    availability_records: list[AvailabilityRecord],
) -> EligibilityCheck:
    """Gates that apply regardless of membership_kind: MEMBERSHIP.enabled, EMP-02,
    DAY_ONLY-01, DAY_SHIFT_OFF-01, UNAVAILABLE-01, LEAVE_GRANTED-01, LEAVE_PLAN-01."""
    if not membership.enabled:
        return EligibilityCheck(False, False, "MEMBERSHIP_DISABLED")
    if not _employee_active(employee, demand):
        return EligibilityCheck(False, False, "EMP-02")
    if profile.day_only_blocks_n and employee.day_only and shift_kind == ShiftKind.N:
        return EligibilityCheck(False, False, "DAY_ONLY-01")
    reason, leave_plan_collision = _blocked_by_availability(demand, availability_records)
    if reason:
        return EligibilityCheck(False, False, reason)
    return EligibilityCheck(True, leave_plan_collision, None)


def _external_window_covers(
    demand: ShiftDemand, shift_kind: ShiftKind, site_id: str, windows: list[ExternalSupportWindow]
) -> bool:
    for window in windows:
        if not window.active or window.site_id != site_id:
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
) -> EligibilityCheck:
    """Return whether employee may cover demand, plus a reason code when blocked."""
    gate = _common_hard_gate(employee, membership, demand, shift_kind, profile, availability_records)
    if not gate.eligible:
        return gate
    if membership.membership_kind == MembershipKind.LOCAL:
        return gate
    if _external_window_covers(demand, shift_kind, site_id, external_windows):
        return gate
    return EligibilityCheck(False, False, "EXTERNAL-01")


if __name__ == "__main__":
    print("eligibility module OK")
