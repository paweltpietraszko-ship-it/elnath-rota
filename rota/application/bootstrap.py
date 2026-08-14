"""ROTA-T010-A -- first configuration + current roster
(tasks/ROTA-T010/part_a_bootstrap_roster.md).

One application-layer write path serves both the very first save and later
resumes of the same Coordinator -> SiteProfile -> Site ->
CoordinatorSiteAssociation chain. No separate onboarding flag, no onboarding
step number, no UI here. Once (coordinator_id, site_id) already has an
active CoordinatorSiteAssociation, this operation refuses -- ordinary edits
go through require_active_coordinator_context() + the existing T009
rota.application.durable_inputs functions instead.

DECYZJA WLASCICIELA 2026-08-14 (part_a_bootstrap_roster.md): every function
below takes an explicit site_id -- multi-object management (a coordinator
managing more than one Site) is out of scope for T010, but nothing here may
assume "at most one context per coordinator" as a permanent constraint,
since Panel Sterowania (T012) will call these same functions again with a
different site_id for a second object.

Two separate reads (part_a_bootstrap_roster.md DWA ODCZYTY, DWA ZNACZENIA):
- coordinator_context_completeness(): durable, month-independent.
- month_plan_readiness(): the above plus a full CalendarDay for every day
  of one specific month. Missing target_hours is reported but never blocks
  readiness (T009 SOFT/balance concern, not a PLAN precondition).
"""
from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from datetime import date

from rota.application.errors import CoordinatorContextAlreadyActive
from rota.domain import (
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    Site,
    SiteProfile,
)
from rota.persistence.calendar_repository import list_calendar_days
from rota.persistence.coordinator_repository import (
    CoordinatorNotFound,
    get_coordinator,
    list_associations_for_coordinator,
    save_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.employee_repository import get_employee, list_memberships_for_site
from rota.persistence.site_profile_repository import get_site_profile, save_site_profile
from rota.persistence.site_repository import SiteNotFound, get_site, save_site
from rota.persistence.work_balance_repository import get_work_balance_target


def _has_active_association(conn, *, coordinator_id: str, site_id: str) -> bool:
    return any(
        a.site_id == site_id and a.active
        for a in list_associations_for_coordinator(conn, coordinator_id)
    )


def _require_id_match(label: str, actual: tuple[str, ...], expected: tuple[str, ...]) -> None:
    if actual != expected:
        raise ValueError(f"{label} {actual!r} != {expected!r}")


def bootstrap_or_resume_coordinator_context(
    conn,
    *,
    coordinator_id: str,
    site_id: str,
    coordinator: Coordinator | None = None,
    site_profile: SiteProfile | None = None,
    site: Site | None = None,
    association: CoordinatorSiteAssociation | None = None,
) -> None:
    """The one small write operation from part_a_bootstrap_roster.md. Persists
    whichever of the four entities are supplied this call -- callers resume
    a partial context over several calls by re-supplying the same
    coordinator_id/site_id with more pieces filled in each time.

    Sequential-consistency guard only (human error / engine failure threat
    model, not concurrent multi-client writers): rejects a *second*
    bootstrap call arriving after the first already went active, not a true
    simultaneous race between two in-flight calls."""
    if _has_active_association(conn, coordinator_id=coordinator_id, site_id=site_id):
        raise CoordinatorContextAlreadyActive(
            f"({coordinator_id!r}, {site_id!r}) already has an active context; "
            "use the T009 authorized edit operations instead"
        )

    if coordinator is not None:
        _require_id_match("coordinator.coordinator_id", (coordinator.coordinator_id,), (coordinator_id,))
        save_coordinator(conn, coordinator)
    if site_profile is not None:
        save_site_profile(conn, site_profile)
    if site is not None:
        _require_id_match("site.site_id", (site.site_id,), (site_id,))
        save_site(conn, site)
    if association is not None:
        _require_id_match(
            "association (coordinator_id, site_id)",
            (association.coordinator_id, association.site_id), (coordinator_id, site_id),
        )
        save_coordinator_site_association(conn, association)


@dataclass(frozen=True)
class ContextCompleteness:
    complete: bool
    missing: tuple[str, ...]


def coordinator_context_completeness(conn, *, coordinator_id: str, site_id: str) -> ContextCompleteness:
    """Durable, month-independent: active Coordinator/SiteProfile/Site/
    Association, >=1 standard shift, >=1 active LOCAL SiteMembership with an
    existing Employee."""
    missing: list[str] = []

    try:
        coordinator = get_coordinator(conn, coordinator_id)
        if not coordinator.active:
            missing.append(f"coordinator {coordinator_id!r} is not active")
    except CoordinatorNotFound:
        missing.append(f"coordinator {coordinator_id!r} does not exist")

    try:
        site = get_site(conn, site_id)
        if not site.active:
            missing.append(f"site {site_id!r} is not active")
        else:
            profile = get_site_profile(conn, site.profile_id)
            if not profile.active:
                missing.append(f"site profile {site.profile_id!r} is not active")
            elif not profile.standard_shifts:
                missing.append(f"site profile {site.profile_id!r} has no standard shifts")
    except SiteNotFound:
        missing.append(f"site {site_id!r} does not exist")

    if not _has_active_association(conn, coordinator_id=coordinator_id, site_id=site_id):
        missing.append(f"no active CoordinatorSiteAssociation for ({coordinator_id!r}, {site_id!r})")

    memberships = list_memberships_for_site(conn, site_id)
    has_local_roster = any(
        m.enabled and m.membership_kind == MembershipKind.LOCAL and _employee_exists(conn, m.employee_id)
        for m in memberships
    )
    if not has_local_roster:
        missing.append(f"site {site_id!r} has no active LOCAL SiteMembership")

    return ContextCompleteness(complete=not missing, missing=tuple(missing))


def _employee_exists(conn, employee_id: str) -> bool:
    try:
        get_employee(conn, employee_id)
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class MonthPlanReadiness:
    ready: bool
    missing: tuple[str, ...]
    target_hours_warnings: tuple[str, ...]


def month_plan_readiness(conn, *, coordinator_id: str, site_id: str, month: date) -> MonthPlanReadiness:
    """Context completeness plus a full CalendarDay for every day of
    `month`. Computed independently per month -- the same Site can be ready
    for one month and not ready for another. Missing target_hours never
    blocks readiness; it is reported separately for the existing T009
    SOFT/balance concern."""
    if month.day != 1:
        raise ValueError(f"month {month} is not the first day of its month")

    completeness = coordinator_context_completeness(conn, coordinator_id=coordinator_id, site_id=site_id)
    missing = list(completeness.missing)

    days_in_month = _calendar.monthrange(month.year, month.month)[1]
    range_start = date(month.year, month.month, 1)
    range_end = date(month.year, month.month, days_in_month)
    existing_days = {d.date for d in list_calendar_days(conn, range_start, range_end)}
    for day in range(1, days_in_month + 1):
        current = date(month.year, month.month, day)
        if current not in existing_days:
            missing.append(f"missing CalendarDay for {current.isoformat()}")

    target_hours_warnings: list[str] = []
    if completeness.complete:
        for m in list_memberships_for_site(conn, site_id):
            if m.enabled and m.membership_kind == MembershipKind.LOCAL:
                if get_work_balance_target(conn, m.employee_id, range_start) is None:
                    target_hours_warnings.append(
                        f"missing target_hours for employee {m.employee_id!r}, month {range_start.isoformat()}"
                    )

    return MonthPlanReadiness(
        ready=not missing,
        missing=tuple(missing),
        target_hours_warnings=tuple(target_hours_warnings),
    )


def current_roster(conn, *, site_id: str) -> tuple[Employee, ...]:
    """Bierzaca obsada: Employee rows for every enabled=true SiteMembership
    of this Site. Disabling (enabled=false) removes an Employee from this
    read without deleting the Employee row or its membership history; a
    later re-enable of the same membership makes it reappear here."""
    memberships = list_memberships_for_site(conn, site_id)
    return tuple(get_employee(conn, m.employee_id) for m in memberships if m.enabled)
