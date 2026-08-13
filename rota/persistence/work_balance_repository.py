"""WorkBalance target-hours CRUD + reconstruction (tasks/ROTA-T008/brief.md
WORKBALANCE -- RECONSTRUCTED, NOT STORED). Only target_hours is persisted;
the balance itself is always recomputed from CURRENT-version Assignment data
(cross-Site, EMP-03) and AvailabilityRecord history via rota.balance, never
stored as a second truth.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from rota.balance import MissingTargetHoursError, compute_month_balance, compute_quarter_balance, quarter_start
from rota.domain import WorkBalance
from rota.persistence.availability_repository import list_active_overlapping
from rota.persistence.schedule_repository import get_current_assignments_for_employees


def save_work_balance_target(conn: sqlite3.Connection, *, employee_id: str, month: date, target_hours: int) -> None:
    if month.day != 1:
        raise ValueError(f"month {month} is not the first day of its month")
    if conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,)).fetchone() is None:
        raise KeyError(f"unknown employee {employee_id!r}")
    with conn:
        conn.execute(
            """INSERT INTO work_balance_targets (employee_id, month, target_hours) VALUES (?, ?, ?)
               ON CONFLICT(employee_id, month) DO UPDATE SET target_hours = excluded.target_hours""",
            (employee_id, month.isoformat(), target_hours),
        )


def get_work_balance_target(conn: sqlite3.Connection, employee_id: str, month: date) -> int | None:
    row = conn.execute(
        "SELECT target_hours FROM work_balance_targets WHERE employee_id = ? AND month = ?",
        (employee_id, month.isoformat()),
    ).fetchone()
    return row[0] if row else None


def list_work_balance_targets(conn: sqlite3.Connection, employee_id: str) -> dict[date, int]:
    rows = conn.execute(
        "SELECT month, target_hours FROM work_balance_targets WHERE employee_id = ? ORDER BY month",
        (employee_id,),
    ).fetchall()
    return {date.fromisoformat(month): target_hours for month, target_hours in rows}


def _add_months(month: date, count: int) -> date:
    zero_based = month.month - 1 + count
    return date(month.year + zero_based // 12, zero_based % 12 + 1, 1)


def _month_bounds(month: date) -> tuple[datetime, datetime]:
    return datetime(month.year, month.month, 1), datetime.combine(_add_months(month, 1), datetime.min.time())


def reconstruct_month_balance(
    conn: sqlite3.Connection, *, employee_id: str, month: date, quarter_balance_before: int = 0,
) -> WorkBalance:
    target_hours = get_work_balance_target(conn, employee_id, month)
    interval_start, interval_end = _month_bounds(month)
    assignments = get_current_assignments_for_employees(conn, [employee_id], interval_start, interval_end)
    availability = list_active_overlapping(conn, employee_id, interval_start.date(), _add_months(month, 1))
    if target_hours is None:
        raise MissingTargetHoursError(f"no work_balance_targets entry for employee {employee_id!r}, month {month}")
    return compute_month_balance(employee_id, month, target_hours, assignments, availability, quarter_balance_before)


def reconstruct_quarter_balance(
    conn: sqlite3.Connection, *, employee_id: str, quarter_first_month: date,
) -> list[WorkBalance]:
    start_month = quarter_start(quarter_first_month)
    end_of_quarter = _add_months(start_month, 3)
    interval_start = datetime.combine(start_month, datetime.min.time())
    interval_end = datetime.combine(end_of_quarter, datetime.min.time())
    assignments = get_current_assignments_for_employees(conn, [employee_id], interval_start, interval_end)
    availability = list_active_overlapping(conn, employee_id, start_month, end_of_quarter)
    target_hours_by_month = {
        month: hours for month, hours in list_work_balance_targets(conn, employee_id).items()
        if start_month <= month < end_of_quarter
    }
    return compute_quarter_balance(employee_id, start_month, target_hours_by_month, assignments, availability)


if __name__ == "__main__":
    print("persistence.work_balance_repository module OK")
