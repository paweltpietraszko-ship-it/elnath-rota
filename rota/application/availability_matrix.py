"""ROTA-T010-B -- one employee availability matrix, composed read-only
(tasks/ROTA-T010/part_b_availability.md).

Base state (unconditional, nothing persisted): a new Employee has a
checkmark for Ogolna/D/N and every weekday. Employee.day_only is the one
base exception -- it blocks N from the start, independent of any dated
record (rota.planning.eligibility/validator apply it directly, not through
this module). Everything else layered on top is a dated change:
SICK_LEAVE/LEAVE_GRANTED/UNAVAILABLE_24H (rota.persistence
.availability_repository, already an append-only chain per family), plus
RESOLVED EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS and
EMPLOYEE_DAY_ONLY_N_EXCEPTION SiteRuleVersions (rota.persistence
.site_rule_assembly, the same linear-chain-per-rule_id history already used
by T005). This module writes nothing -- editing a constraint/exception
reuses the existing T005 decision_ledger append (correct dates, restore the
checkmark earlier, or start a new independent rule_id family) unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rota.domain import AvailabilityKind, AvailabilityRecord, Employee, SiteRuleVersion
from rota.persistence.availability_repository import get_current_availability_for_employee
from rota.persistence.employee_repository import get_employee
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.planning.site_rules import EMPLOYEE_DAY_ONLY_N_EXCEPTION, EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS

_RELEVANT_AVAILABILITY_KINDS = (
    AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED, AvailabilityKind.UNAVAILABLE_24H,
)
_RELEVANT_RULE_KINDS = (EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS, EMPLOYEE_DAY_ONLY_N_EXCEPTION)


@dataclass(frozen=True)
class EmployeeAvailabilityMatrix:
    employee: Employee
    availability_records: tuple[AvailabilityRecord, ...]
    weekday_and_exception_rules: tuple[SiteRuleVersion, ...]


def employee_availability_matrix(conn, *, site_id: str, employee_id: str, month: date) -> EmployeeAvailabilityMatrix:
    """Read-only composition; writes nothing. SiteRuleVersion applicability
    is scoped to `month`, matching every other current-rules read in this
    codebase (assemble_monthly_site_rules)."""
    employee = get_employee(conn, employee_id)
    availability = tuple(
        r for r in get_current_availability_for_employee(conn, employee_id)
        if r.active and r.kind in _RELEVANT_AVAILABILITY_KINDS
    )
    resolved, _, _ = assemble_monthly_site_rules(conn, site_id, month)
    rules = tuple(
        r for r in resolved
        if r.rule_kind in _RELEVANT_RULE_KINDS and r.structured_parameters.get("employee_id") == employee_id
    )
    return EmployeeAvailabilityMatrix(
        employee=employee, availability_records=availability, weekday_and_exception_rules=rules,
    )
