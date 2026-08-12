"""Pure interval/time arithmetic shared by the solver and the independent validator.

Sharing this module is a deliberate choice: these are deterministic math
helpers (overlap, rest gap, rolling windows), not planning judgment. The
independent HARD validator (anti-drift rule 12) must not trust the solver's
internal constraint bookkeeping, but reusing the same interval arithmetic
does not reintroduce that risk.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from rota.constants import LOAD_WINDOW_DAYS


def overlap_hours(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> int:
    """Return whole hours of overlap between two half-open intervals."""
    seconds = max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())
    return int(seconds // 3600)


def intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Return True if the two half-open intervals share any time."""
    return a_start < b_end and a_end > b_start


def overlaps_date_range(interval_start: datetime, interval_end: datetime, range_start: date, range_end: date) -> bool:
    """Return True if [interval_start, interval_end) overlaps the inclusive calendar-date range."""
    range_start_dt = datetime(range_start.year, range_start.month, range_start.day)
    range_end_dt = datetime(range_end.year, range_end.month, range_end.day) + timedelta(days=1)
    return intervals_overlap(interval_start, interval_end, range_start_dt, range_end_dt)


def rest_hours(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    """Return the rest gap in hours between two non-overlapping intervals."""
    if a_start <= b_start:
        gap = (b_start - a_end).total_seconds() / 3600
    else:
        gap = (a_start - b_end).total_seconds() / 3600
    return gap


def rolling_windows(month_start: date, num_days: int) -> list[tuple[datetime, datetime]]:
    """Return every LOAD_WINDOW_DAYS-day rolling window that overlaps the month.

    LOAD-01 (arch/spec.md:409-417) and STATE-02 (boundary context sufficient for
    cross-month validation, arch/spec.md:330) together require windows that start
    up to LOAD_WINDOW_DAYS-1 days before month_start, not only windows starting on
    or after day 1 -- otherwise a window straddling the previous month's last few
    days and this month's first days is never checked (found in audit round 12,
    tests_r12.txt FINDING 5).
    """
    windows = []
    first_offset = -(LOAD_WINDOW_DAYS - 1)
    last_offset = num_days - LOAD_WINDOW_DAYS
    month_start_dt = datetime(month_start.year, month_start.month, month_start.day)
    for offset in range(first_offset, last_offset + 1):
        window_start = month_start_dt + timedelta(days=offset)
        window_end = window_start + timedelta(days=LOAD_WINDOW_DAYS)
        windows.append((window_start, window_end))
    return windows


if __name__ == "__main__":
    a = datetime(2026, 10, 1, 5, 0)
    b = datetime(2026, 10, 1, 17, 0)
    c = datetime(2026, 10, 1, 17, 0)
    d = datetime(2026, 10, 2, 5, 0)
    print(f"overlap_hours(a,b,b,d) = {overlap_hours(a, b, b, d)}")
    print(f"rest_hours(a,b,c,d) = {rest_hours(a, b, c, d)}")
    print(f"rolling_windows: {len(rolling_windows(date(2026, 10, 1), 31))} windows")
