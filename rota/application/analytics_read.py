"""ROTA-T019: coordinator analytics read model (tasks/ROTA-T019/brief.md).

Single application-level entry point for the future "Analityka" screen.
Read-only, no new subsystem: composes existing LOCAL roster + WorkBalance
inputs (rota.balance, existing persistence reads) into one deterministic
view. EXTERNAL_SUPPORT/X-Y never gets a row here (WINDOW-03, T019-R1-1).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from rota.balance import compute_month_balance, compute_quarter_balance, quarter_start
from rota.domain import MembershipKind
from rota.persistence.employee_repository import list_employees, list_memberships_for_site
from rota.persistence.schedule_repository import get_current_assignments_for_employees
from rota.persistence.work_balance_repository import absence_facts_for_employees, list_work_balance_targets_for_employees
from rota.planning.absence import IncompleteAbsenceReferenceError, canonical_hours_in_range


class AnalyticsDataStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    MONTH_AVAILABLE_QUARTER_UNAVAILABLE = "MONTH_AVAILABLE_QUARTER_UNAVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class AnalyticsHoursScope(str, Enum):
    ALL_SITES = "ALL_SITES"


@dataclass(frozen=True)
class AnalyticsMonthData:
    month: date
    target_hours: int
    effective_target_hours: int
    planned_hours: int
    realized_hours: int
    month_balance: int
    quarter_balance: Optional[int]
    unresolved_carryover: Optional[int]


@dataclass(frozen=True)
class EmployeeAnalyticsRow:
    employee_id: str
    display_name: str
    status: AnalyticsDataStatus
    month_data: Optional[AnalyticsMonthData]
    quarter_months: tuple[AnalyticsMonthData, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class CoordinatorAnalyticsView:
    site_id: str
    month: date
    quarter_first_month: date
    hours_scope: AnalyticsHoursScope
    rows: tuple[EmployeeAnalyticsRow, ...]


def _add_months(month: date, offset: int) -> date:
    total = (month.year * 12 + (month.month - 1)) + offset
    year, month_index = divmod(total, 12)
    return date(year, month_index + 1, 1)


def _to_analytics_month_data(wb) -> AnalyticsMonthData:
    effective_target = wb.planned_hours + wb.realized_hours - wb.month_balance
    return AnalyticsMonthData(
        month=wb.month, target_hours=wb.target_hours, effective_target_hours=effective_target,
        planned_hours=wb.planned_hours, realized_hours=wb.realized_hours, month_balance=wb.month_balance,
        quarter_balance=wb.quarter_balance, unresolved_carryover=wb.unresolved_carryover,
    )


def _degraded_row(employee_id, display_name, status, month_data, warning) -> EmployeeAnalyticsRow:
    return EmployeeAnalyticsRow(
        employee_id=employee_id, display_name=display_name, status=status,
        month_data=month_data, quarter_months=(), warnings=(warning,),
    )


def _first_blocking_quarter_month(quarter_months_list: list[date], absence_facts):
    """Attribution-only pass over the same shared canonical_hours_in_range
    primitive compute_month_balance already calls internally -- never
    recomputes hours/balance. Used solely to name which quarter month
    blocks the warning text (T019-R3-2: the balance itself stays fully
    delegated to rota.balance.compute_quarter_balance)."""
    for quarter_month in quarter_months_list:
        month_end = _add_months(quarter_month, 1) - timedelta(days=1)
        try:
            canonical_hours_in_range(absence_facts, quarter_month, month_end)
        except IncompleteAbsenceReferenceError as exc:
            return quarter_month, str(exc)
    return quarter_months_list[0], ""


def _quarter_row(
    employee_id: str, display_name: str, month: date, quarter_months_list: list[date],
    targets: dict[date, int], assignments, absence_facts, month_data_only: AnalyticsMonthData,
) -> EmployeeAnalyticsRow:
    """Full-quarter attempt, only reached once the requested month is
    already known computable and every quarter month has a target_hours
    entry (section 10.3/10.4). Delegates the entire running-balance
    computation to the canonical rota.balance.compute_quarter_balance."""
    target_by_month = {quarter_month: targets[quarter_month] for quarter_month in quarter_months_list}
    try:
        quarter_balances = compute_quarter_balance(
            employee_id, quarter_months_list[0], target_by_month, assignments, absence_facts,
        )
    except IncompleteAbsenceReferenceError:
        blocking_month, error_text = _first_blocking_quarter_month(quarter_months_list, absence_facts)
        warning = f"quarter analytics unavailable for employee '{employee_id}', month {blocking_month.isoformat()}: {error_text}"
        return _degraded_row(
            employee_id, display_name, AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE,
            month_data_only, warning,
        )

    quarter_months_tuple = tuple(_to_analytics_month_data(wb) for wb in quarter_balances)
    requested_index = quarter_months_list.index(month)
    return EmployeeAnalyticsRow(
        employee_id=employee_id, display_name=display_name, status=AnalyticsDataStatus.AVAILABLE,
        month_data=quarter_months_tuple[requested_index], quarter_months=quarter_months_tuple, warnings=(),
    )


def _row_for_employee(
    employee_id: str, display_name: str, month: date, quarter_months_list: list[date],
    targets: dict[date, int], assignments, absence_facts,
) -> EmployeeAnalyticsRow:
    requested_target = targets.get(month)
    if requested_target is None:
        warning = f"analytics unavailable for employee '{employee_id}', month {month.isoformat()}: missing target_hours"
        return _degraded_row(employee_id, display_name, AnalyticsDataStatus.UNAVAILABLE, None, warning)

    try:
        month_only = compute_month_balance(
            employee_id, month, requested_target, assignments, absence_facts, quarter_balance_before=0,
        )
    except IncompleteAbsenceReferenceError as exc:
        warning = f"analytics unavailable for employee '{employee_id}', month {month.isoformat()}: {exc}"
        return _degraded_row(employee_id, display_name, AnalyticsDataStatus.UNAVAILABLE, None, warning)

    month_data_only = AnalyticsMonthData(
        month=month, target_hours=requested_target,
        effective_target_hours=month_only.planned_hours + month_only.realized_hours - month_only.month_balance,
        planned_hours=month_only.planned_hours, realized_hours=month_only.realized_hours,
        month_balance=month_only.month_balance, quarter_balance=None, unresolved_carryover=None,
    )

    missing_month = next((m for m in quarter_months_list if m not in targets), None)
    if missing_month is not None:
        warning = f"quarter analytics unavailable for employee '{employee_id}': missing target_hours for {missing_month.isoformat()}"
        return _degraded_row(
            employee_id, display_name, AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE,
            month_data_only, warning,
        )

    return _quarter_row(
        employee_id, display_name, month, quarter_months_list, targets, assignments, absence_facts, month_data_only,
    )


def analytics_for_site_month(conn, *, site_id: str, month: date) -> CoordinatorAnalyticsView:
    if month.day != 1:
        raise ValueError(f"month {month} is not the first day of its month")

    quarter_first_month = quarter_start(month)
    quarter_months_list = [_add_months(quarter_first_month, offset) for offset in range(3)]
    quarter_end_exclusive = _add_months(quarter_first_month, 3)

    memberships = list_memberships_for_site(conn, site_id)
    roster_ids = sorted(
        m.employee_id for m in memberships if m.enabled and m.membership_kind == MembershipKind.LOCAL
    )
    if not roster_ids:
        return CoordinatorAnalyticsView(
            site_id=site_id, month=month, quarter_first_month=quarter_first_month,
            hours_scope=AnalyticsHoursScope.ALL_SITES, rows=(),
        )

    display_names = {e.employee_id: e.display_name for e in list_employees(conn)}
    targets_by_employee = list_work_balance_targets_for_employees(
        conn, roster_ids, quarter_first_month, quarter_end_exclusive
    )

    interval_start = datetime.combine(quarter_first_month, datetime.min.time())
    interval_end = datetime.combine(quarter_end_exclusive, datetime.min.time())
    assignments = get_current_assignments_for_employees(conn, roster_ids, interval_start, interval_end)
    absence_facts_by_employee = absence_facts_for_employees(
        conn, roster_ids, quarter_first_month, quarter_end_exclusive - timedelta(days=1)
    )

    assignments_by_employee: dict[str, list] = {}
    for assignment in assignments:
        assignments_by_employee.setdefault(assignment.employee_id, []).append(assignment)

    rows = tuple(
        _row_for_employee(
            employee_id, display_names.get(employee_id, employee_id), month, quarter_months_list,
            targets_by_employee.get(employee_id, {}), assignments_by_employee.get(employee_id, []),
            absence_facts_by_employee.get(employee_id, []),
        )
        for employee_id in roster_ids
    )
    return CoordinatorAnalyticsView(
        site_id=site_id, month=month, quarter_first_month=quarter_first_month,
        hours_scope=AnalyticsHoursScope.ALL_SITES, rows=rows,
    )


if __name__ == "__main__":
    print("application.analytics_read module OK")
