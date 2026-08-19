"""ROTA-T018 Checkpoint A: absence workday accounting.

Owner decision 2026-08-19 (arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md):
SICK_LEAVE / LEAVE_GRANTED reduce the expected monthly quota by 8h only for
a qualified workday (ISO weekday 1..5 AND CalendarDay.holiday=False), not
for every calendar day in the absence range. Fail closed via
IncompleteAbsenceCalendarError when a qualifying absence exists but the
month's CalendarDay coverage is incomplete.
"""
from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime

import pytest

from rota.balance import compute_month_balance
from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.planning.absence import IncompleteAbsenceCalendarError, excused_absence_days_in_month
from rota.planning.engine import plan
from rota.planning.solver import _sick_adjusted_targets
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _full_month_calendar(month: date, holidays: frozenset = frozenset()) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(
        CalendarDay(date(month.year, month.month, day), date(month.year, month.month, day) in holidays)
        for day in range(1, last_day + 1)
    )


def _sick(employee_id: str, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(f"sick-{employee_id}-{start}", "v1", employee_id, AvailabilityKind.SICK_LEAVE, start, end, True, None, None)


def _leave(employee_id: str, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(f"leave-{employee_id}-{start}", "v1", employee_id, AvailabilityKind.LEAVE_GRANTED, start, end, True, None, None)


# A7.1 -----------------------------------------------------------------------


def test_a7_1_sick_leave_across_two_weekends_counts_only_weekdays():
    # 2026-10-01 (Thu) .. 2026-10-12 (Mon), spanning weekends 3-4 and 10-11.
    month = date(2026, 10, 1)
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 12))
    result = excused_absence_days_in_month([record], month, calendar_days=_full_month_calendar(month))
    assert result == {"A": 8}


# A7.2 -----------------------------------------------------------------------


def test_a7_2_leave_granted_gets_identical_workday_filter_in_workbalance():
    month = date(2026, 10, 1)
    leave = _leave("A", date(2026, 10, 1), date(2026, 10, 12))
    balance = compute_month_balance("A", month, 168, [], [leave], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -(168 - 8 * 8)


# A7.3 -----------------------------------------------------------------------


def test_a7_3_weekday_holiday_excluded_from_workday_count():
    month = date(2026, 10, 1)
    # 2026-10-01 is a Thursday; mark it a public holiday.
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 1))
    calendar_days = _full_month_calendar(month, holidays=frozenset({date(2026, 10, 1)}))
    assert excused_absence_days_in_month([record], month, calendar_days=calendar_days) == {"A": 0}


# A7.4 -----------------------------------------------------------------------


def test_a7_4_weekend_holiday_still_zero_no_double_effect():
    month = date(2026, 10, 1)
    # 2026-10-03 is a Saturday; also (redundantly) marked a holiday.
    record = _sick("A", date(2026, 10, 3), date(2026, 10, 3))
    calendar_days = _full_month_calendar(month, holidays=frozenset({date(2026, 10, 3)}))
    assert excused_absence_days_in_month([record], month, calendar_days=calendar_days) == {"A": 0}


# A7.5 -----------------------------------------------------------------------


def test_a7_5_overlapping_sick_and_leave_dedup_before_workday_filter():
    month = date(2026, 10, 1)
    # Union Oct 1-5 (Thu-Mon); overlap on Oct 3 (Sat) must not double-count.
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 3))
    leave = _leave("A", date(2026, 10, 3), date(2026, 10, 5))
    calendar_days = _full_month_calendar(month)
    result = excused_absence_days_in_month([sick, leave], month, calendar_days=calendar_days)
    assert result == {"A": 3}


# A7.6 -----------------------------------------------------------------------


def test_a7_6_cross_month_range_clips_and_filters_workdays():
    month = date(2026, 10, 1)
    # 2026-09-28 (Mon) .. 2026-10-02 (Fri); only Oct 1 (Thu) and Oct 2 (Fri)
    # are inside the counted month, both workdays.
    record = _sick("A", date(2026, 9, 28), date(2026, 10, 2))
    result = excused_absence_days_in_month([record], month, calendar_days=_full_month_calendar(month))
    assert result == {"A": 2}


# A7.7 -----------------------------------------------------------------------


def test_a7_7_weekend_absence_still_hard_blocks_assignment():
    # 2026-10-03 is a Saturday; a demand that day must still be HARD-blocked
    # by the active SICK_LEAVE even though it contributes 0h target reduction.
    demand = ShiftDemand("2026-10-03-D", "test-v1", datetime(2026, 10, 3, 5, 0), datetime(2026, 10, 3, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 3), date(2026, 10, 3))
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "SICK_LEAVE-01" for b in result.decision_payload.blockers)


# A7.8 -----------------------------------------------------------------------


def test_a7_8_incomplete_calendar_with_qualifying_absence_fails_closed():
    month = date(2026, 10, 1)
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 5))
    full = _full_month_calendar(month)
    missing_one_day = full[:-1]  # drop Oct 31
    with pytest.raises(IncompleteAbsenceCalendarError):
        excused_absence_days_in_month([record], month, calendar_days=missing_one_day)


# A7.9 -----------------------------------------------------------------------


def test_a7_9_direct_plan_with_incomplete_calendar_and_sick_absence_is_technical_error():
    # Two employees so demand coverage is still reachable (no unassignable
    # short-circuit before the objective, where the calendar is consumed).
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 5))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# A7.10 ----------------------------------------------------------------------


def test_a7_10_legacy_balance_call_without_absence_or_calendar_keeps_result():
    balance = compute_month_balance("A", date(2026, 10, 1), 156, [], [])
    assert balance.month_balance == -156


# A7.11 -- existing Round 23 reproducers, oracle unchanged ------------------


def test_a7_11a_round23_solver_l4_march_2027_reduces_target_to_56():
    month = date(2027, 3, 1)
    sick = _sick("B", date(2027, 3, 2), date(2027, 3, 19))
    state = base_state(
        employees=(), memberships=(), month=month, calendar_days=_full_month_calendar(month),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 56


def test_a7_11b_round23_quarter_balance_leave_march_2027_reduces_target_to_56():
    month = date(2027, 3, 1)
    leave = _leave("B", date(2027, 3, 2), date(2027, 3, 19))
    balance = compute_month_balance("B", month, 168, [], [leave], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -56


def test_a7_11c_round23_solver_l4_excludes_weekday_public_holiday():
    month = date(2027, 5, 1)
    sick = _sick("B", date(2027, 5, 1), date(2027, 5, 7))
    state = base_state(
        employees=(), memberships=(), month=month,
        calendar_days=_full_month_calendar(month, holidays=frozenset({date(2027, 5, 3)})),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 136


# A7.12 -----------------------------------------------------------------------


def test_a7_12_march_2027_workbalance_target_56_at_target_168():
    month = date(2027, 3, 1)
    sick = _sick("B", date(2027, 3, 2), date(2027, 3, 19))
    balance = compute_month_balance("B", month, 168, [], [sick], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -56


if __name__ == "__main__":
    print("test_t018 module OK")
