"""WorkBalance computation: monthly and quarter-cumulative hour balance.

Deliberately NOT part of PlanningEngine. arch/spec.md's WorkBalance SCOPE
BOUNDARY: "WorkBalance śledzi godziny narastająco w kwartale, w tym saldo
nadgodzin do oddania w następnym okresie (unresolved_carryover) -- to
odpowiedzialność koordynatora, w zakresie Rota. Rota NIE oblicza rozliczeń
kadrowych ani list płac." This module computes the running balance signal
from Assignment + AvailabilityRecord data; it does not block anything (HARD
or otherwise) and produces no report/UI. A caller decides how to surface the
resulting number (owner instruction 2026-08-13: "jak najprościej ... czerwone
podsumowanie z liczbą" -- that display decision belongs to whatever consumes
WorkBalance, not to this module).

WorkBalance has no site_id (EMP-03: an Employee is not owned by one Site),
so callers must supply every relevant Assignment for the employee across all
sites for the month/quarter, not just one PlanningState's worth.
"""
from __future__ import annotations

from datetime import date

from rota.domain import Assignment, AssignmentRole, AssignmentState, AvailabilityRecord, WorkBalance
from rota.planning.absence import EXCUSED_ABSENCE_HOURS_PER_DAY, excused_absence_days_in_month


def quarter_start(month: date) -> date:
    """First day of the calendar quarter containing month (owner decision
    2026-08-13: calendar quarters, I-III/IV-VI/VII-IX/X-XII)."""
    quarter_index = (month.month - 1) // 3
    return date(month.year, quarter_index * 3 + 1, 1)


def _hours_in_month(assignments: list[Assignment], employee_id: str, month: date, state_filter: AssignmentState) -> int:
    hours = 0
    for assignment in assignments:
        if assignment.employee_id != employee_id or assignment.role != AssignmentRole.PRIMARY:
            continue
        if assignment.state != state_filter:
            continue
        if (assignment.start_datetime.year, assignment.start_datetime.month) != (month.year, month.month):
            continue
        hours += int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
    return hours


def compute_month_balance(
    employee_id: str, month: date, target_hours: int,
    assignments: list[Assignment], availability_records: list[AvailabilityRecord],
    quarter_balance_before: int = 0,
) -> WorkBalance:
    """Compute one month's WorkBalance. `quarter_balance_before` is the
    running balance carried in from earlier months of the same calendar
    quarter (0 for the quarter's first month, or when computing a single
    month in isolation).

    Owner decision 2026-08-13: both SICK_LEAVE and LEAVE_GRANTED reduce the
    expected monthly quota by EXCUSED_ABSENCE_HOURS_PER_DAY (8h) per day here
    -- distinct from solver.py's live TARGET-01 objective, which stays
    SICK_LEAVE-only (see absence.py docstring for why).

    unresolved_carryover: arch/spec.md marks its exact lifecycle OPEN. This
    computes it as the running quarter_balance not yet explicitly resolved
    by the coordinator; nothing beyond that is invented here."""
    realized_hours = _hours_in_month(assignments, employee_id, month, AssignmentState.REALIZED)
    planned_hours = _hours_in_month(assignments, employee_id, month, AssignmentState.PLANNED)
    absence_days = excused_absence_days_in_month(availability_records, month).get(employee_id, 0)
    effective_target = max(0, target_hours - EXCUSED_ABSENCE_HOURS_PER_DAY * absence_days)
    month_balance = realized_hours - effective_target
    running_quarter_balance = quarter_balance_before + month_balance
    return WorkBalance(
        employee_id=employee_id,
        month=month,
        target_hours=target_hours,
        planned_hours=planned_hours,
        realized_hours=realized_hours,
        month_balance=month_balance,
        unresolved_carryover=running_quarter_balance,
        quarter_balance=running_quarter_balance,
    )


def compute_quarter_balance(
    employee_id: str, quarter_first_month: date, target_hours_by_month: dict[date, int],
    assignments: list[Assignment], availability_records: list[AvailabilityRecord],
) -> list[WorkBalance]:
    """Compute WorkBalance for every month of one calendar quarter in order,
    carrying the running balance forward. The last entry's quarter_balance is
    the number to surface at quarter end; each entry's own month_balance is
    the number to surface at that month's end."""
    balances = []
    running_balance = 0
    for offset in range(3):
        month = _add_months(quarter_first_month, offset)
        target_hours = target_hours_by_month.get(month, 0)
        balance = compute_month_balance(employee_id, month, target_hours, assignments, availability_records, running_balance)
        running_balance = balance.quarter_balance
        balances.append(balance)
    return balances


def _add_months(month: date, offset: int) -> date:
    total = (month.year * 12 + (month.month - 1)) + offset
    year, month_index = divmod(total, 12)
    return date(year, month_index + 1, 1)


if __name__ == "__main__":
    print(f"quarter_start(2026-08) = {quarter_start(date(2026, 8, 1))}")
