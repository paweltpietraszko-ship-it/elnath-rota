"""Operation 6 (tasks/ROTA-T009/brief.md): thin commands for existing
durable facts needed by the coordinator workflow. Each validates
coordinator context and delegates to the existing repository -- no new
abstraction beyond that.
"""
from __future__ import annotations

from datetime import date

from rota.application.context import require_active_coordinator_context
from rota.application.errors import InvalidCoordinatorContext
from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    Site,
    SiteMembership,
    SiteProfile,
)
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.employee_repository import save_employee, save_external_support_window, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import get_site, save_site
from rota.persistence.work_balance_repository import save_work_balance_target


def _require_payload_belongs_to_site(payload_site_id: str, site_id: str) -> None:
    """R4-3-B: the coordinator's active context for site_id must not
    authorize mutating a payload whose own Site scope is a different Site."""
    if payload_site_id != site_id:
        raise InvalidCoordinatorContext(
            f"payload belongs to site {payload_site_id!r}, not the authorized site {site_id!r}"
        )


def add_external_support_window(conn, *, coordinator_id: str, site_id: str, window: ExternalSupportWindow) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(window.site_id, site_id)
    save_external_support_window(conn, window)


def append_availability(
    conn, *, coordinator_id: str, site_id: str, availability_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, active: bool, note: str | None = None,
):
    """Covers append/supersede (a new version in the same family) and
    deactivate (active=False) alike -- the append-only chain primitive
    already models all three as one operation."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    return append_availability_version(
        conn, availability_id=availability_id, employee_id=employee_id, kind=kind,
        start_date=start_date, end_date=end_date, active=active, note=note,
    )


def update_employee(conn, *, coordinator_id: str, site_id: str, employee: Employee) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_employee(conn, employee)


def update_membership(conn, *, coordinator_id: str, site_id: str, membership: SiteMembership) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(membership.site_id, site_id)
    save_site_membership(conn, membership)


def set_target_hours(
    conn, *, coordinator_id: str, site_id: str, employee_id: str, month: date, target_hours: int,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_work_balance_target(conn, employee_id=employee_id, month=month, target_hours=target_hours)


def set_calendar_day(conn, *, coordinator_id: str, site_id: str, day: CalendarDay) -> None:
    """ROTA-T011-A (A-1): calendar_days is keyed by date alone, not scoped to
    a Site -- site_id here authorizes the coordinator's write, exactly like
    set_target_hours, and is never itself persisted."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_calendar_day(conn, day)


def update_site_profile(conn, *, coordinator_id: str, site_id: str, profile: SiteProfile) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    owning_site = get_site(conn, site_id)
    if profile.profile_id != owning_site.profile_id:
        raise InvalidCoordinatorContext(
            f"profile {profile.profile_id!r} does not belong to the authorized site {site_id!r}"
        )
    save_site_profile(conn, profile)


def update_site(conn, *, coordinator_id: str, site_id: str, site: Site) -> None:
    """ROTA-T011-C (B-2=W1): a plain upsert like update_employee/
    update_membership -- Site is a MUTABLE CURRENT-STATE ENTITY (T008),
    not a versioned one. profile_id may never change here: rebinding a
    Site to a different profile silently changes its standard-shift
    catalog and retroactively changes training-readiness qualification
    (training._qualifies_for_readiness reads the CURRENT profile, R6-4).
    That rebind is a separate, explicitly named operation with its own
    product question about retroactivity -- never a side effect of an
    ordinary name/active edit. profile_id stays settable only through
    bootstrap_or_resume_coordinator_context."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(site.site_id, site_id)
    owning_site = get_site(conn, site_id)
    if site.profile_id != owning_site.profile_id:
        raise InvalidCoordinatorContext(
            f"update_site must not rebind profile_id ({owning_site.profile_id!r} -> {site.profile_id!r}); "
            "changing a Site's profile is a separate, explicit operation"
        )
    save_site(conn, site)


def update_coordinator(conn, *, coordinator_id: str, site_id: str, coordinator: Coordinator) -> None:
    """ROTA-T011-C (ROZSTRZYGNIĘCIE WŁAŚCICIELA 2026-08-14): deliberately no
    coordinator-identity check -- the acting coordinator may write another
    coordinator's own record (rename it, set active=False). This is an
    accepted product decision, not an oversight: this product has no
    multi-user-per-installation model (each coordinator gets their own
    installation) and login/permissions are separate, deferred work.
    Literal copy of update_employee's shape -- Coordinator carries no
    site_id to compare against."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_coordinator(conn, coordinator)


def update_association(conn, *, coordinator_id: str, site_id: str, association: CoordinatorSiteAssociation) -> None:
    """ROTA-T011-C (B-2=W1): a plain upsert -- save_coordinator_site_
    association has no WHERE clause and already allows active: 1 -> 0.
    The CAS-guarded activation path stays exclusive to bootstrap/resume;
    this is the ordinary edit path for a context that already exists.
    No coordinator-identity check either, same accepted decision as
    update_coordinator: only association.site_id is checked, matching the
    authorized site."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(association.site_id, site_id)
    save_coordinator_site_association(conn, association)
