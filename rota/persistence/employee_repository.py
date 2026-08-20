"""Employee + SiteMembership + ExternalSupportWindow persistence
(tasks/ROTA-T008/brief.md MUTABLE CURRENT-STATE ENTITIES).

Employee remains cross-Site (EMP-03) -- no Employee.site_id is persisted.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from rota.domain import (
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    SiteMembership,
)


class EmployeeNotFound(Exception):
    """Raised when employee_id has no matching row."""


class InvalidEmployeeActivePeriod(Exception):
    """Raised when active_to < active_from."""


class UnknownEmployeeOrSite(Exception):
    """Raised when a membership/window references a missing Employee or Site."""


def write_employee_in_open_transaction(conn: sqlite3.Connection, employee: Employee) -> None:
    """Same write as save_employee, without its own `with conn:` -- for a
    caller (ROTA-T019b durable_inputs.update_employee) that must combine
    this write with a coordinator-action index insert inside one already-
    open transaction."""
    if employee.active_to is not None and employee.active_to < employee.active_from:
        raise InvalidEmployeeActivePeriod((employee.active_from, employee.active_to))
    conn.execute(
        """INSERT INTO employees (employee_id, display_name, active_from, active_to, day_only)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(employee_id) DO UPDATE SET
            display_name=excluded.display_name, active_from=excluded.active_from,
            active_to=excluded.active_to, day_only=excluded.day_only""",
        (
            employee.employee_id, employee.display_name, employee.active_from.isoformat(),
            employee.active_to.isoformat() if employee.active_to else None, int(employee.day_only),
        ),
    )


def save_employee(conn: sqlite3.Connection, employee: Employee) -> None:
    with conn:
        write_employee_in_open_transaction(conn, employee)


def _row_to_employee(row: tuple) -> Employee:
    employee_id, display_name, active_from, active_to, day_only = row
    return Employee(
        employee_id=employee_id, display_name=display_name,
        active_from=date.fromisoformat(active_from),
        active_to=date.fromisoformat(active_to) if active_to else None,
        day_only=bool(day_only),
    )


def get_employee(conn: sqlite3.Connection, employee_id: str) -> Employee:
    row = conn.execute(
        "SELECT employee_id, display_name, active_from, active_to, day_only FROM employees WHERE employee_id = ?",
        (employee_id,),
    ).fetchone()
    if row is None:
        raise EmployeeNotFound(employee_id)
    return _row_to_employee(row)


def list_employees(conn: sqlite3.Connection) -> list[Employee]:
    rows = conn.execute(
        "SELECT employee_id, display_name, active_from, active_to, day_only FROM employees ORDER BY employee_id"
    ).fetchall()
    return [_row_to_employee(row) for row in rows]


def list_employees_by_ids(conn: sqlite3.Connection, employee_ids: list[str]) -> dict[str, Employee]:
    """ROTA-T020: batch-fetch Employee rows for a roster in one SELECT,
    avoiding one get_employee() call per row when building a printable
    schedule."""
    if not employee_ids:
        return {}
    placeholders = ",".join("?" for _ in employee_ids)
    rows = conn.execute(
        f"SELECT employee_id, display_name, active_from, active_to, day_only "
        f"FROM employees WHERE employee_id IN ({placeholders})",
        (*employee_ids,),
    ).fetchall()
    return {row[0]: _row_to_employee(row) for row in rows}


def write_site_membership_in_open_transaction(conn: sqlite3.Connection, membership: SiteMembership) -> None:
    """Same write as save_site_membership, without its own `with conn:` --
    for a caller (e.g. rota/application/training.py) that must combine this
    write with another one inside a single already-open transaction, since
    nested `with conn:` blocks each commit independently in Python's sqlite3
    module and cannot be composed into one atomic unit by nesting alone."""
    employee_row = conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (membership.employee_id,)).fetchone()
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (membership.site_id,)).fetchone()
    if employee_row is None or site_row is None:
        raise UnknownEmployeeOrSite((membership.employee_id, membership.site_id))
    conn.execute(
        """INSERT INTO site_memberships
           (employee_id, site_id, membership_kind, enabled, readiness_state, readiness_source, can_work_24h)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(employee_id, site_id) DO UPDATE SET
            membership_kind=excluded.membership_kind, enabled=excluded.enabled,
            readiness_state=excluded.readiness_state, readiness_source=excluded.readiness_source,
            can_work_24h=excluded.can_work_24h""",
        (
            membership.employee_id, membership.site_id, membership.membership_kind.value,
            int(membership.enabled), membership.readiness_state.value, membership.readiness_source.value,
            int(membership.can_work_24h),
        ),
    )


def save_site_membership(conn: sqlite3.Connection, membership: SiteMembership) -> None:
    with conn:
        write_site_membership_in_open_transaction(conn, membership)


def _row_to_membership(row: tuple) -> SiteMembership:
    employee_id, site_id, kind, enabled, readiness_state, readiness_source, can_work_24h = row
    return SiteMembership(
        employee_id=employee_id, site_id=site_id, membership_kind=MembershipKind(kind),
        enabled=bool(enabled), readiness_state=ReadinessState(readiness_state),
        readiness_source=ReadinessSource(readiness_source),
        # Legacy (pre-T012) rows have NULL here: default=True.
        can_work_24h=bool(can_work_24h) if can_work_24h is not None else True,
    )


def list_memberships_for_site(conn: sqlite3.Connection, site_id: str) -> list[SiteMembership]:
    rows = conn.execute(
        "SELECT employee_id, site_id, membership_kind, enabled, readiness_state, readiness_source, can_work_24h "
        "FROM site_memberships WHERE site_id = ? ORDER BY employee_id",
        (site_id,),
    ).fetchall()
    return [_row_to_membership(row) for row in rows]


def list_memberships_for_employee(conn: sqlite3.Connection, employee_id: str) -> list[SiteMembership]:
    rows = conn.execute(
        "SELECT employee_id, site_id, membership_kind, enabled, readiness_state, readiness_source, can_work_24h "
        "FROM site_memberships WHERE employee_id = ? ORDER BY site_id",
        (employee_id,),
    ).fetchall()
    return [_row_to_membership(row) for row in rows]


def write_external_support_window_in_open_transaction(conn: sqlite3.Connection, window: ExternalSupportWindow) -> None:
    """Same write as save_external_support_window, without its own
    `with conn:` (ROTA-T019b atomicity)."""
    if window.end_datetime <= window.start_datetime:
        raise ValueError("ExternalSupportWindow.end_datetime must be after start_datetime")
    employee_row = conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (window.employee_id,)).fetchone()
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (window.site_id,)).fetchone()
    if employee_row is None or site_row is None:
        raise UnknownEmployeeOrSite((window.employee_id, window.site_id))
    conn.execute(
        """INSERT INTO external_support_windows
           (window_id, employee_id, site_id, start_datetime, end_datetime, active, allowed_shift_kind)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(window_id) DO UPDATE SET
            employee_id=excluded.employee_id, site_id=excluded.site_id,
            start_datetime=excluded.start_datetime, end_datetime=excluded.end_datetime,
            active=excluded.active, allowed_shift_kind=excluded.allowed_shift_kind""",
        (
            window.window_id, window.employee_id, window.site_id,
            window.start_datetime.isoformat(), window.end_datetime.isoformat(),
            int(window.active), window.allowed_shift_kind.value if window.allowed_shift_kind else None,
        ),
    )


def save_external_support_window(conn: sqlite3.Connection, window: ExternalSupportWindow) -> None:
    with conn:
        write_external_support_window_in_open_transaction(conn, window)


def _row_to_window(row: tuple) -> ExternalSupportWindow:
    window_id, employee_id, site_id, start_dt, end_dt, active, allowed_kind = row
    return ExternalSupportWindow(
        window_id=window_id, employee_id=employee_id, site_id=site_id,
        start_datetime=datetime.fromisoformat(start_dt), end_datetime=datetime.fromisoformat(end_dt),
        active=bool(active), allowed_shift_kind=ShiftKind(allowed_kind) if allowed_kind else None,
    )


def get_external_support_window(conn: sqlite3.Connection, window_id: str) -> ExternalSupportWindow:
    row = conn.execute(
        "SELECT window_id, employee_id, site_id, start_datetime, end_datetime, active, allowed_shift_kind "
        "FROM external_support_windows WHERE window_id = ?",
        (window_id,),
    ).fetchone()
    if row is None:
        raise KeyError(window_id)
    return _row_to_window(row)


def list_windows_for_site(conn: sqlite3.Connection, site_id: str) -> list[ExternalSupportWindow]:
    rows = conn.execute(
        "SELECT window_id, employee_id, site_id, start_datetime, end_datetime, active, allowed_shift_kind "
        "FROM external_support_windows WHERE site_id = ? ORDER BY window_id",
        (site_id,),
    ).fetchall()
    return [_row_to_window(row) for row in rows]


def list_windows_for_employee(conn: sqlite3.Connection, employee_id: str) -> list[ExternalSupportWindow]:
    rows = conn.execute(
        "SELECT window_id, employee_id, site_id, start_datetime, end_datetime, active, allowed_shift_kind "
        "FROM external_support_windows WHERE employee_id = ? ORDER BY window_id",
        (employee_id,),
    ).fetchall()
    return [_row_to_window(row) for row in rows]


if __name__ == "__main__":
    print("persistence.employee_repository module OK")
