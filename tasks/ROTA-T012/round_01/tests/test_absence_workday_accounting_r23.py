"""Owner decision 2026-08-19: excused absence counts working days only."""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date

from rota.balance import compute_month_balance
from rota.domain import AvailabilityKind, AvailabilityRecord, CalendarDay, WorkBalance
from rota.planning.solver import _sick_adjusted_targets
from tests.support.minimal_state import base_state


def _absence(kind: AvailabilityKind, month: date, start_day: int, end_day: int) -> AvailabilityRecord:
    return AvailabilityRecord(
        f"{kind.value}-{start_day}-{end_day}", "audit-v1", "B", kind,
        date(month.year, month.month, start_day), date(month.year, month.month, end_day),
        True, None, None,
    )


def _calendar(month: date, holidays: set[date] = frozenset()) -> tuple[CalendarDay, ...]:
    last_day = calendar.monthrange(month.year, month.month)[1]
    return tuple(
        CalendarDay(date(month.year, month.month, day), date(month.year, month.month, day) in holidays)
        for day in range(1, last_day + 1)
    )


def test_solver_l4_2_to_19_march_reduces_target_by_14_workdays_not_18_calendar_days() -> None:
    month = date(2027, 3, 1)
    sick = _absence(AvailabilityKind.SICK_LEAVE, month, 2, 19)
    state = replace(
        base_state(), month=month, calendar_days=_calendar(month),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 56


def test_quarter_balance_leave_2_to_19_march_reduces_target_by_14_workdays() -> None:
    month = date(2027, 3, 1)
    leave = _absence(AvailabilityKind.LEAVE_GRANTED, month, 2, 19)
    balance = compute_month_balance("B", month, 168, [], [leave], calendar_days=_calendar(month))
    assert balance.month_balance == -56


def test_solver_l4_excludes_weekday_public_holiday_from_workday_count() -> None:
    month = date(2027, 5, 1)
    sick = _absence(AvailabilityKind.SICK_LEAVE, month, 1, 7)
    state = replace(
        base_state(), month=month,
        calendar_days=_calendar(month, {date(2027, 5, 3)}),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 136
