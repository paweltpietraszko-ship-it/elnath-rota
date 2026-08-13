"""Operation 6 (tasks/ROTA-T009/brief.md): thin commands for existing
durable facts needed by the coordinator workflow. Each validates
coordinator context and delegates to the existing repository -- no new
abstraction beyond that.
"""
from __future__ import annotations

from datetime import date

from rota.application.context import require_active_coordinator_context
from rota.domain import AvailabilityKind, Employee, ExternalSupportWindow, SiteMembership, SiteProfile
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.employee_repository import save_employee, save_external_support_window, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.work_balance_repository import save_work_balance_target


def add_external_support_window(conn, *, coordinator_id: str, site_id: str, window: ExternalSupportWindow) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
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
    save_site_membership(conn, membership)


def set_target_hours(
    conn, *, coordinator_id: str, site_id: str, employee_id: str, month: date, target_hours: int,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_work_balance_target(conn, employee_id=employee_id, month=month, target_hours=target_hours)


def update_site_profile(conn, *, coordinator_id: str, site_id: str, profile: SiteProfile) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_site_profile(conn, profile)
