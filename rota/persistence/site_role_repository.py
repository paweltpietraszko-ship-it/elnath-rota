"""ROTA-T065-CONFIGURABLE-ROLES: single owner of a Site's own role catalog
(SiteRoleDefinition) and of coordinator-issued, time-bounded coverage
authorizations (RoleCoverageAuthorization). Neither table is a global
enum -- every row is scoped to one site_id.

Renaming/retiring a role only affects `active` on this current-state row;
it never rewrites already-persisted historical text (ShiftDemand.
required_role_name, ScheduleVersionEmployeePosition.role_name -- see
rota/persistence/schedule_repository.py for those historical reads).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from rota.domain import RoleCoverageAuthorization, SiteRoleDefinition


class UnknownSite(Exception):
    """Raised when a role/authorization references a missing Site."""


class UnknownSiteRole(Exception):
    """Raised when an authorization's covered_role_id doesn't name an
    existing SiteRoleDefinition belonging to that same Site."""


def write_site_role_in_open_transaction(conn: sqlite3.Connection, role: SiteRoleDefinition) -> None:
    """Same write as save_site_role, without its own `with conn:` -- for a
    caller composing this with another write in one already-open
    transaction."""
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (role.site_id,)).fetchone()
    if site_row is None:
        raise UnknownSite(role.site_id)
    conn.execute(
        """INSERT INTO site_roles (role_id, site_id, display_name, active)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(role_id) DO UPDATE SET
            display_name=excluded.display_name, active=excluded.active""",
        (role.role_id, role.site_id, role.display_name, int(role.active)),
    )


def save_site_role(conn: sqlite3.Connection, role: SiteRoleDefinition) -> None:
    with conn:
        write_site_role_in_open_transaction(conn, role)


def _row_to_role(row: tuple) -> SiteRoleDefinition:
    role_id, site_id, display_name, active = row
    return SiteRoleDefinition(role_id=role_id, site_id=site_id, display_name=display_name, active=bool(active))


def get_site_role(conn: sqlite3.Connection, role_id: str) -> SiteRoleDefinition:
    row = conn.execute(
        "SELECT role_id, site_id, display_name, active FROM site_roles WHERE role_id = ?", (role_id,)
    ).fetchone()
    if row is None:
        raise KeyError(role_id)
    return _row_to_role(row)


def list_site_roles(conn: sqlite3.Connection, site_id: str, *, include_inactive: bool = True) -> list[SiteRoleDefinition]:
    query = "SELECT role_id, site_id, display_name, active FROM site_roles WHERE site_id = ?"
    params: tuple = (site_id,)
    if not include_inactive:
        query += " AND active = 1"
    rows = conn.execute(query + " ORDER BY display_name", params).fetchall()
    return [_row_to_role(row) for row in rows]


def write_role_coverage_authorization_in_open_transaction(
    conn: sqlite3.Connection, authorization: RoleCoverageAuthorization
) -> None:
    """Same write as save_role_coverage_authorization, without its own
    `with conn:`."""
    if authorization.end_datetime <= authorization.start_datetime:
        raise ValueError("RoleCoverageAuthorization.end_datetime must be after start_datetime")
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (authorization.site_id,)).fetchone()
    employee_row = conn.execute(
        "SELECT 1 FROM employees WHERE employee_id = ?", (authorization.employee_id,)
    ).fetchone()
    if site_row is None or employee_row is None:
        raise UnknownSite((authorization.site_id, authorization.employee_id))
    role_row = conn.execute(
        "SELECT 1 FROM site_roles WHERE role_id = ? AND site_id = ?",
        (authorization.covered_role_id, authorization.site_id),
    ).fetchone()
    if role_row is None:
        raise UnknownSiteRole((authorization.covered_role_id, authorization.site_id))
    conn.execute(
        """INSERT INTO role_coverage_authorizations
           (authorization_id, site_id, employee_id, covered_role_id, start_datetime, end_datetime, active)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(authorization_id) DO UPDATE SET
            covered_role_id=excluded.covered_role_id, start_datetime=excluded.start_datetime,
            end_datetime=excluded.end_datetime, active=excluded.active""",
        (
            authorization.authorization_id, authorization.site_id, authorization.employee_id,
            authorization.covered_role_id, authorization.start_datetime.isoformat(),
            authorization.end_datetime.isoformat(), int(authorization.active),
        ),
    )


def save_role_coverage_authorization(conn: sqlite3.Connection, authorization: RoleCoverageAuthorization) -> None:
    with conn:
        write_role_coverage_authorization_in_open_transaction(conn, authorization)


def _row_to_authorization(row: tuple) -> RoleCoverageAuthorization:
    authorization_id, site_id, employee_id, covered_role_id, start_dt, end_dt, active = row
    return RoleCoverageAuthorization(
        authorization_id=authorization_id, site_id=site_id, employee_id=employee_id,
        covered_role_id=covered_role_id, start_datetime=datetime.fromisoformat(start_dt),
        end_datetime=datetime.fromisoformat(end_dt), active=bool(active),
    )


def get_role_coverage_authorization(conn: sqlite3.Connection, authorization_id: str) -> RoleCoverageAuthorization:
    row = conn.execute(
        "SELECT authorization_id, site_id, employee_id, covered_role_id, start_datetime, end_datetime, active "
        "FROM role_coverage_authorizations WHERE authorization_id = ?",
        (authorization_id,),
    ).fetchone()
    if row is None:
        raise KeyError(authorization_id)
    return _row_to_authorization(row)


def list_role_coverage_authorizations_for_site(conn: sqlite3.Connection, site_id: str) -> list[RoleCoverageAuthorization]:
    rows = conn.execute(
        "SELECT authorization_id, site_id, employee_id, covered_role_id, start_datetime, end_datetime, active "
        "FROM role_coverage_authorizations WHERE site_id = ? ORDER BY authorization_id",
        (site_id,),
    ).fetchall()
    return [_row_to_authorization(row) for row in rows]


if __name__ == "__main__":
    print("persistence.site_role_repository module OK")
