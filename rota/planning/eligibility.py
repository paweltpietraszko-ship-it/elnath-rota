"""Determine which employees may be assigned to a given ShiftDemand.

Implements MEMBERSHIP-01/02, EMP-02, DAY_ONLY-01, DAY_SHIFT_OFF-01,
UNAVAILABLE-01, LEAVE_GRANTED-01, LEAVE_PLAN-01 and EXTERNAL-01 eligibility
checks. Rest (REST-01) and load (LOAD-01) are cross-demand constraints and
are handled separately in the solver, not here.

SiteRuleVersion (RESOLVED) is intentionally not interpreted here: rule_kind
catalog is CONTRACT_GAP per rota.domain.RuleParameters. Any active resolved
SiteRule beyond what is modeled through AvailabilityRecord/Employee fields is
out of scope for this experiment and is not silently applied.
"""
from __future__ import annotations

from dataclasses import dataclass

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
) -> tuple[bool, bool]:
    """Return (hard_blocked, leave_plan_collision)."""
    hard_blocked = False
    leave_plan_collision = False
    for record in records:
        if not record.active:
            continue
        if record.kind == AvailabilityKind.DAY_SHIFT_OFF:
            if demand.start_datetime.date() >= record.start_date and demand.start_datetime.date() <= record.end_date:
                hard_blocked = True
        elif record.kind in (AvailabilityKind.UNAVAILABLE_24H, AvailabilityKind.LEAVE_GRANTED):
            if overlaps_availability(demand, record):
                hard_blocked = True
        elif record.kind == AvailabilityKind.LEAVE_PLAN:
            if overlaps_availability(demand, record):
                leave_plan_collision = True
    return hard_blocked, leave_plan_collision


def _local_eligible(
    employee: Employee,
    membership: SiteMembership,
    demand: ShiftDemand,
    shift_kind: ShiftKind,
    profile: SiteProfile,
    availability_records: list[AvailabilityRecord],
) -> EligibilityCheck:
    if not membership.enabled or not _employee_active(employee, demand):
        return EligibilityCheck(False, False)
    if profile.day_only_blocks_n and employee.day_only and shift_kind == ShiftKind.N:
        return EligibilityCheck(False, False)
    hard_blocked, leave_plan_collision = _blocked_by_availability(demand, availability_records)
    return EligibilityCheck(not hard_blocked, leave_plan_collision)


def _external_eligible(
    membership: SiteMembership,
    demand: ShiftDemand,
    shift_kind: ShiftKind,
    site_id: str,
    windows: list[ExternalSupportWindow],
) -> EligibilityCheck:
    for window in windows:
        if not window.active or window.site_id != site_id:
            continue
        if window.allowed_shift_kind is not None and window.allowed_shift_kind != shift_kind:
            continue
        if window.start_datetime <= demand.start_datetime and window.end_datetime >= demand.end_datetime:
            return EligibilityCheck(True, False)
    return EligibilityCheck(False, False)


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
    """Return whether employee may cover demand, and any LEAVE_PLAN SOFT collision."""
    if membership.membership_kind == MembershipKind.LOCAL:
        return _local_eligible(employee, membership, demand, shift_kind, profile, availability_records)
    return _external_eligible(membership, demand, shift_kind, site_id, external_windows)


if __name__ == "__main__":
    print("eligibility module OK")
