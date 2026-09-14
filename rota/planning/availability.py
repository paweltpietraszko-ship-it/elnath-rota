"""ROTA-T065-ORDINARY-TIME-AVAILABILITY brief.md section 4: the ONE pure
interval-overlap oracle for AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
shared identically by rota.planning.eligibility (automatic PLAN) and
rota.planning.validator (manual correction/REPLAN recheck) -- no second
overlap algorithm anywhere.

V1 scope (brief.md section 3): the window is same-day and repeats every
calendar day in the record's inclusive [start_date, end_date] range;
overnight windows are rejected at the write boundary
(rota.persistence.availability_repository), never interpreted here.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from rota.domain import AvailabilityKind, AvailabilityRecord
from rota.planning.timeutil import intervals_overlap


def unavailable_time_window_overlaps(
    record: AvailabilityRecord, start_datetime: datetime, end_datetime: datetime
) -> bool:
    """True if the half-open real work interval [start_datetime,
    end_datetime) has a non-empty intersection with any daily occurrence
    of record's [start_time, end_time) window, for a day within record's
    inclusive [start_date, end_date] range. start_datetime/end_datetime
    come from a ShiftDemand or an Assignment -- both expose the same two
    fields, so either can be passed directly."""
    if record.kind != AvailabilityKind.UNAVAILABLE_TIME_WINDOW or not record.active:
        return False
    if record.start_time is None or record.end_time is None:
        return False
    if end_datetime <= start_datetime:
        return False
    day = max(start_datetime.date(), record.start_date)
    last_day = min(end_datetime.date(), record.end_date)
    while day <= last_day:
        window_start = datetime.combine(day, record.start_time)
        window_end = datetime.combine(day, record.end_time)
        if intervals_overlap(start_datetime, end_datetime, window_start, window_end):
            return True
        day += timedelta(days=1)
    return False


if __name__ == "__main__":
    print("planning.availability module OK")
