"""rota/balance.py: quarterly WorkBalance tracking, owner request 2026-08-13.

Not part of PlanningEngine/plan() -- a pure function surfacing the number a
coordinator needs to see manual overtime that HARD/SOFT scheduling rules
never blocked (e.g. someone hand-assigned 24h/month beyond target).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from rota.balance import MissingTargetHoursError, compute_month_balance, compute_quarter_balance, quarter_start
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
)
from rota.planning.absence import DailyAbsenceFact


def _shift(day: int, month: int = 10, year: int = 2026, hours: int = 12, employee_id: str = "A") -> Assignment:
    start = datetime(year, month, day, 5, 0)
    end = start + timedelta(hours=hours)
    return Assignment(f"r{year}-{month}-{day}", "v1", employee_id, start, end, AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None)


def test_quarter_start_maps_month_to_calendar_quarter():
    assert quarter_start(date(2026, 1, 1)) == date(2026, 1, 1)
    assert quarter_start(date(2026, 3, 31)) == date(2026, 1, 1)
    assert quarter_start(date(2026, 4, 1)) == date(2026, 4, 1)
    assert quarter_start(date(2026, 8, 15)) == date(2026, 7, 1)
    assert quarter_start(date(2026, 12, 31)) == date(2026, 10, 1)


def test_month_balance_flags_manual_overassignment_not_blocked_by_hard():
    # 15 x 12h REALIZED = 180h against a 156h target -> 24h over, exactly the
    # "coordinator hand-typed 24h too much" scenario nothing else catches.
    assignments = [_shift(d) for d in range(1, 16)]
    balance = compute_month_balance("A", date(2026, 10, 1), 156, assignments, [])
    assert balance.realized_hours == 180
    assert balance.month_balance == 24
    assert balance.quarter_balance == 24
    assert balance.unresolved_carryover == 24


def test_quarter_balance_accumulates_across_three_months():
    assignments = []
    for month in (10, 11, 12):
        assignments.extend(_shift(d, month=month) for d in range(1, 16))
    target_by_month = {date(2026, 10, 1): 156, date(2026, 11, 1): 156, date(2026, 12, 1): 156}
    balances = compute_quarter_balance("A", quarter_start(date(2026, 10, 1)), target_by_month, assignments, [])
    assert [b.month_balance for b in balances] == [24, 24, 24]
    assert [b.quarter_balance for b in balances] == [24, 48, 72]


def test_leave_granted_reduces_effective_target_by_8h_per_day_for_balance():
    """ROTA-T023 Checkpoint B: T018's flat-8/workday oracle is preserved only
    as the PRE_PLAN_LEAVE source (brief.md section 18) -- exercised here
    directly via DailyAbsenceFact instead of the retired calendar_days param.
    LEAVE_GRANTED 2026-10-01..05 has exactly 3 qualified workdays (Thu 1,
    Fri 2, Mon 5 -- Sat 3/Sun 4 excluded) -> 24h reduction; target 156 ->
    effective 132."""
    assignments = [_shift(d, hours=int(132 / 10)) for d in range(6, 16)]
    facts = [
        DailyAbsenceFact(date(2026, 10, d), AvailabilityKind.LEAVE_GRANTED, "PRE_PLAN_LEAVE", "BOUND", 8)
        for d in (1, 2, 5)
    ]
    total_realized = sum(int((a.end_datetime - a.start_datetime).total_seconds() // 3600) for a in assignments)
    balance = compute_month_balance("A", date(2026, 10, 1), 156, assignments, facts)
    assert balance.realized_hours == total_realized
    assert balance.month_balance == total_realized - 132


def test_no_assignments_gives_negative_balance_not_a_crash():
    balance = compute_month_balance("A", date(2026, 10, 1), 156, [], [])
    assert balance.realized_hours == 0
    assert balance.month_balance == -156


def test_planned_hours_alone_trigger_the_balance_owner_decision_2026_08_14():
    """Overtime must be visible from already-scheduled (PLANNED) hours, not
    only after they become REALIZED -- impending overtime is worth flagging
    before it is worked."""
    assignments = [
        Assignment(f"p{d}", "v1", "A", datetime(2026, 10, d, 5, 0), datetime(2026, 10, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None)
        for d in range(1, 16)
    ]
    balance = compute_month_balance("A", date(2026, 10, 1), 156, assignments, [])
    assert balance.planned_hours == 180
    assert balance.realized_hours == 0
    assert balance.month_balance == 24


def test_planned_and_realized_combine_in_the_same_month_balance():
    realized = [_shift(d) for d in range(1, 6)]  # 5*12=60h REALIZED
    planned = [
        Assignment(f"p{d}", "v1", "A", datetime(2026, 10, d, 5, 0), datetime(2026, 10, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None)
        for d in range(6, 16)  # 10*12=120h PLANNED
    ]
    balance = compute_month_balance("A", date(2026, 10, 1), 156, realized + planned, [])
    assert balance.realized_hours == 60
    assert balance.planned_hours == 120
    assert balance.month_balance == 60 + 120 - 156


def test_missing_month_target_raises_instead_of_defaulting_to_zero():
    target_by_month = {date(2026, 10, 1): 156, date(2026, 11, 1): 156}  # December missing
    with pytest.raises(MissingTargetHoursError):
        compute_quarter_balance("A", quarter_start(date(2026, 10, 1)), target_by_month, [], [])


if __name__ == "__main__":
    print("test_balance module OK")
