"""Excused-absence day counting shared by TARGET-01 (solver.py) and
WorkBalance quarterly tracking (rota/balance.py).

Owner decision 2026-08-12/2026-08-13, from real ROYALPACK/APEXIM schedules
(Grafiki/): SICK_LEAVE and LEAVE_GRANTED both reduce the expected monthly
hour quota by a flat EXCUSED_ABSENCE_HOURS_PER_DAY (8h), regardless of
actual shift length (12h D/N) -- confirmed identical hour-accounting
treatment for both kinds. T018 owner decision 2026-08-19 superseded "per
calendar day" with "per qualified workday" (see
arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md); this remains purely
an hour-accounting rule, HARD blocking behavior for each kind is separate
and unchanged (eligibility.py / validator.py already block automatic
Assignment on both).

solver.py's live TARGET-01 SOFT ranking passes kinds=(SICK_LEAVE,) only,
deliberately excluding LEAVE_GRANTED: target_hours is a coordinator input
already set with planned leave in mind (known in advance, unlike sudden
sick leave), and ROTA-REG-001's frozen reference numbers were verified
against the original PoC run using raw target_hours. Applying the
LEAVE_GRANTED reduction there too shifted its exact target hours and broke
the frozen oracle -- a materially different question from "should the
quarterly balance also treat leave like sick leave", which the owner
answered yes to (rota/balance.py uses both kinds).
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Optional

from rota.domain import AvailabilityKind, AvailabilityRecord, CalendarDay

EXCUSED_ABSENCE_KINDS = (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)
EXCUSED_ABSENCE_HOURS_PER_DAY = 8


class IncompleteAbsenceCalendarError(Exception):
    """T018 ABSENCE-WORKDAY-ACCOUNTING-01: raised when a month has at least
    one active, qualifying-kind AvailabilityRecord intersecting it but
    `calendar_days` does not cover every day of that month (missing days, a
    missing calendar entirely, or conflicting holiday values for the same
    date). Never falls back to a weekday-only guess -- CalendarDay is the
    sole source of truth for holidays."""


def _workday_holiday_map(calendar_days: tuple, month_start: date, month_end: date) -> dict:
    holiday_by_date: dict[date, bool] = {}
    for entry in calendar_days:
        if entry.date < month_start or entry.date > month_end:
            continue
        if entry.date in holiday_by_date and holiday_by_date[entry.date] != entry.holiday:
            raise IncompleteAbsenceCalendarError(f"conflicting CalendarDay entries for {entry.date}")
        holiday_by_date[entry.date] = entry.holiday
    current = month_start
    while current <= month_end:
        if current not in holiday_by_date:
            raise IncompleteAbsenceCalendarError(
                f"missing CalendarDay for {current} required for excused-absence workday accounting"
            )
        current += timedelta(days=1)
    return holiday_by_date


def _absence_dates_by_employee(records: list[AvailabilityRecord], kinds: tuple, month_start: date, month_end: date) -> dict:
    """Union of active, kind-matching absence dates per employee, clipped to
    [month_start, month_end]. Overlapping/abutting records for the same
    employee (even across kinds) must not double-count a shared day (audit
    round 21 FINDING R21-1)."""
    dates_by_employee: dict[str, set] = {}
    for record in records:
        if not record.active or record.kind not in kinds:
            continue
        overlap_start = max(record.start_date, month_start)
        overlap_end = min(record.end_date, month_end)
        if overlap_start > overlap_end:
            continue
        current = overlap_start
        employee_dates = dates_by_employee.setdefault(record.employee_id, set())
        while current <= overlap_end:
            employee_dates.add(current)
            current += timedelta(days=1)
    return dates_by_employee


def excused_absence_days_in_month(
    records: list[AvailabilityRecord], month: date, kinds: tuple = EXCUSED_ABSENCE_KINDS,
    calendar_days: Optional[tuple[CalendarDay, ...]] = None,
) -> dict[str, int]:
    """Union of active excused-absence WORKDAYS (T018 owner decision
    2026-08-19, superseding "8h per calendar day"): a qualified workday is
    ISO weekday 1..5 AND CalendarDay.holiday=False; this is a pure
    hour-accounting rule, HARD availability blocking is unaffected. Fails
    closed via IncompleteAbsenceCalendarError when a qualifying record
    intersects the month but calendar_days does not fully cover it.

    `kinds` defaults to both SICK_LEAVE and LEAVE_GRANTED (rota.balance);
    solver.py passes kinds=(SICK_LEAVE,) only -- see module docstring for
    why LEAVE_GRANTED stays out of the live TARGET-01 objective."""
    num_days = calendar.monthrange(month.year, month.month)[1]
    month_start = date(month.year, month.month, 1)
    month_end = date(month.year, month.month, num_days)
    dates_by_employee = _absence_dates_by_employee(records, kinds, month_start, month_end)
    if not dates_by_employee:
        return {}
    holiday_by_date = _workday_holiday_map(calendar_days or (), month_start, month_end)
    return {
        employee_id: sum(1 for d in dates if d.isoweekday() <= 5 and not holiday_by_date[d])
        for employee_id, dates in dates_by_employee.items()
    }


if __name__ == "__main__":
    print("absence module OK")
