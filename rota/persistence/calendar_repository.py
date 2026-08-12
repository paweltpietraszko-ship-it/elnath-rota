"""CalendarDay persistence (tasks/ROTA-T008/brief.md CALENDARDAY --
DURABLE REPRODUCIBILITY CHOICE). PlanningEngine MUST NOT read this table
directly -- only this repository does, for a later application-layer caller.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from rota.domain import CalendarDay


def save_calendar_day(conn: sqlite3.Connection, day: CalendarDay) -> None:
    with conn:
        conn.execute(
            """INSERT INTO calendar_days (date, holiday) VALUES (?, ?)
               ON CONFLICT(date) DO UPDATE SET holiday=excluded.holiday""",
            (day.date.isoformat(), int(day.holiday)),
        )


def get_calendar_day(conn: sqlite3.Connection, target_date: date) -> CalendarDay:
    row = conn.execute("SELECT date, holiday FROM calendar_days WHERE date = ?", (target_date.isoformat(),)).fetchone()
    if row is None:
        raise KeyError(target_date)
    day, holiday = row
    return CalendarDay(date=date.fromisoformat(day), holiday=bool(holiday))


def list_calendar_days(conn: sqlite3.Connection, range_start: date, range_end: date) -> list[CalendarDay]:
    rows = conn.execute(
        "SELECT date, holiday FROM calendar_days WHERE date >= ? AND date <= ? ORDER BY date",
        (range_start.isoformat(), range_end.isoformat()),
    ).fetchall()
    return [CalendarDay(date=date.fromisoformat(day), holiday=bool(holiday)) for day, holiday in rows]


if __name__ == "__main__":
    print("persistence.calendar_repository module OK")
