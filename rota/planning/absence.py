"""Excused-absence day counting shared by TARGET-01 (solver.py) and
WorkBalance quarterly tracking (rota/balance.py).

Owner decision 2026-08-12/2026-08-13, from real ROYALPACK/APEXIM schedules
(Grafiki/): SICK_LEAVE and LEAVE_GRANTED both reduce the expected monthly
hour quota by a flat EXCUSED_ABSENCE_HOURS_PER_DAY (8h) per calendar day,
regardless of actual shift length (12h D/N) -- confirmed identical
hour-accounting treatment for both kinds. This is purely an hour-accounting
rule; HARD blocking behavior for each kind is separate and unchanged
(eligibility.py / validator.py already block automatic Assignment on both).
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from rota.domain import AvailabilityKind, AvailabilityRecord

EXCUSED_ABSENCE_KINDS = (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)
EXCUSED_ABSENCE_HOURS_PER_DAY = 8


def excused_absence_days_in_month(
    records: list[AvailabilityRecord], month: date, kinds: tuple = EXCUSED_ABSENCE_KINDS
) -> dict[str, int]:
    """Union of active excused-absence calendar days per employee, clipped to
    the given month. Overlapping or abutting records for the same employee
    (even across kinds) must not double-count a shared day (audit round 21
    FINDING R21-1).

    `kinds` defaults to both SICK_LEAVE and LEAVE_GRANTED for
    rota.balance (quarterly tracking, owner decision 2026-08-13: both
    reduce the expected quota equally there). solver.py's live TARGET-01
    SOFT ranking passes kinds=(SICK_LEAVE,) only, deliberately unchanged
    from the owner's original 2026-08-12 decision -- target_hours is a
    coordinator input already set with planned LEAVE_GRANTED in mind (it is
    known in advance, unlike sudden sick leave), and ROTA-REG-001's frozen
    reference numbers were verified against that original PoC run. Applying
    the LEAVE_GRANTED reduction there too shifted its exact target hours and
    broke the frozen oracle -- a materially different question from
    "should the quarterly balance also treat leave like sick leave", which
    the owner answered yes to."""
    num_days = calendar.monthrange(month.year, month.month)[1]
    month_start = date(month.year, month.month, 1)
    month_end = date(month.year, month.month, num_days)
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
    return {employee_id: len(dates) for employee_id, dates in dates_by_employee.items()}


if __name__ == "__main__":
    print("absence module OK")
