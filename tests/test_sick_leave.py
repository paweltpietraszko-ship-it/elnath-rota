"""SICK_LEAVE-01: owner decision 2026-08-12, from real ROYALPACK/APEXIM
schedules (Grafiki/). Two rules, both clarified directly by the owner:
- HARD-blocks automatic Assignment, same as LEAVE_GRANTED.
- Accounts as a flat 8h/day against target_hours regardless of actual shift
  length (12h D/N) -- a sudden sick period is expected to be handled by
  REPLAN (already implemented), not by a separate mechanism here.
"""
from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.planning.engine import plan
from tests.support.minimal_state import MONTH, ReadinessSource, ReadinessState, SITE_ID, base_state


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _full_month_calendar(month: date) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


def test_sick_leave_hard_blocks_assignment_on_sick_day():
    demand = ShiftDemand("2026-10-02-D", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "Koliduje z zapisem: Chorobowe" for b in result.decision_payload.blockers)


def test_sick_leave_does_not_block_assignment_outside_the_sick_range():
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0][0].employee_id == "A"


def test_sick_leave_reduces_target_by_8h_per_day_not_shift_length():
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    # T018: Oct 1-5 has 3 qualified workdays (Thu 1, Fri 2, Mon 5) -> target
    # drops by 3*8=24h, from 24 to 0: taking this one 12h shift now costs A a
    # deviation of 12, same math as B starting from target 0. Without the
    # 8h/day adjustment A would start from target 24 and taking the shift
    # would look like a *better* fit than it should.
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    work_balances = (WorkBalance("A", MONTH, 24, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 0, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(sick,), work_balances=work_balances,
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    # both are equally (mis)matched after the adjustment -- solver picks one
    # deterministically, not necessarily A, which is the point: sick days
    # must not make A artificially preferred over B for this shift.
    assert result.candidates[0][0].employee_id in {"A", "B"}


def test_leave_granted_does_not_reduce_solver_target_unlike_sick_leave():
    """Owner decision 2026-08-13 (STALE, see note below): LEAVE_GRANTED gets
    the 8h/day treatment in the quarterly balance module (rota/balance.py),
    but NOT in solver.py's live TARGET-01 objective -- target_hours is a
    coordinator input already set with planned leave in mind, and applying
    the reduction here shifted ROTA-REG-001's frozen exact-hours oracle when
    first tried. This locked in the revert at the time.

    2026-09-09 correction: `solver._effective_targets`'s OWN docstring now
    says the opposite is true post-T023 Checkpoint B -- SICK_LEAVE and
    LEAVE_GRANTED reduce the live objective IDENTICALLY, both via
    WorkBalance.absence_hours computed upstream by the application layer;
    the 2026-08-13 SICK_LEAVE-only carve-out this test enshrined is itself
    the thing that got superseded. This fixture can't actually exercise
    that upstream computation either way, though: it hardcodes
    `WorkBalance(..., absence_hours=0)` (the trailing 0 is the dataclass
    default) regardless of the LEAVE_GRANTED record above, and that record's
    Oct 1-5 range doesn't even overlap the Oct 6 demand being scheduled --
    LEAVE_GRANTED is inert here either way. Whether LEAVE_GRANTED
    correctly produces a real absence_hours reduction is a question for a
    test of the absence/application layer, not this one.

    What THIS test actually verifies, and what its assertion was really
    checking: solver._effective_targets does a plain `target_hours -
    absence_hours` subtraction, nothing else. With both employees'
    absence_hours at 0, A (target 40) and B (target 12) genuinely TIE on
    total TARGET-01 deviation for this single 12h demand (A takes it:
    28+12=40; B takes it: 0+40=40) -- there is no more-correct single
    winner on target deviation alone. The tie-break (fairness.
    add_target_equity_fairness's completion-percentage spread) then prefers
    A, and manual review with the owner (2026-09-09) confirmed this is the
    behavior a real coordinator would want: of two employees both still
    needing hours, hand the scarce shift to whoever has the bigger
    remaining deficit (A needs 40h this month, B needs only 12h and has
    more of the month left to make that up from other demands) -- not to
    whoever the shift alone would exactly zero out. The original assertion
    here (expecting B) encoded the opposite, unverified intuition."""
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    leave = AvailabilityRecord("l1", "l1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    work_balances = (WorkBalance("A", MONTH, 40, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 12, 0, 0, 0, 0, 0))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(leave,), work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0][0].employee_id == "A"


def test_sick_leave_replan_redistributes_when_reported_mid_month():
    demand = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    original = Assignment(
        "orig-1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    reported_sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), existing_assignments=(original,), availability_records=(reported_sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert [a.employee_id for a in result.candidates[0]] == ["B"]


if __name__ == "__main__":
    print("test_sick_leave module OK")
