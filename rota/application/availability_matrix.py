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
from rota.persistence.availability_repository import get_availability_history, get_current_availability_for_employee
from rota.persistence.employee_repository import get_employee
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.planning.site_rules import EMPLOYEE_DAY_ONLY_N_EXCEPTION, EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS
from rota.planning.state import SiteRuleApplicability

_RELEVANT_AVAILABILITY_KINDS = (
    AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED, AvailabilityKind.UNAVAILABLE_24H,
)
_RELEVANT_RULE_KINDS = (EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS, EMPLOYEE_DAY_ONLY_N_EXCEPTION)


@dataclass(frozen=True)
class EmployeeAvailabilityMatrix:
    employee: Employee
    availability_records: tuple[AvailabilityRecord, ...]
    weekday_and_exception_rules: tuple[SiteRuleVersion, ...]
    # R3-4: assemble_monthly_site_rules's resolved SiteRuleVersion list keeps
    # each version's OWN effective_from/effective_to (when it was written),
    # not the ACTUAL currently-effective days -- a "rejects" decision that
    # ends a ban early leaves the same version object unchanged but shrinks
    # its real applicability. Without these per-day slices, an early
    # checkmark restore was invisible: the resolved-rules list looked
    # identical before and after. Keyed by rule_version_id (not embedded in
    # each rule) so the shape stays exactly what assemble_monthly_site_rules
    # already produces, no re-derivation.
    rule_applicability: tuple[SiteRuleApplicability, ...]


def employee_availability_matrix(conn, *, site_id: str, employee_id: str, month: date) -> EmployeeAvailabilityMatrix:
    """Read-only composition; writes nothing. SiteRuleVersion applicability
    is scoped to `month`, matching every other current-rules read in this
    codebase (assemble_monthly_site_rules)."""
    employee = get_employee(conn, employee_id)
    availability = tuple(
        r for r in get_current_availability_for_employee(conn, employee_id)
        if r.active and r.kind in _RELEVANT_AVAILABILITY_KINDS
    )
    resolved, _, applicability = assemble_monthly_site_rules(conn, site_id, month)
    rules = tuple(
        r for r in resolved
        if r.rule_kind in _RELEVANT_RULE_KINDS and r.structured_parameters.get("employee_id") == employee_id
    )
    relevant_ids = {r.rule_version_id for r in rules}
    rule_applicability = tuple(a for a in applicability if a.rule_version_id in relevant_ids)
    return EmployeeAvailabilityMatrix(
        employee=employee, availability_records=availability, weekday_and_exception_rules=rules,
        rule_applicability=rule_applicability,
    )


def availability_history(conn, *, availability_id: str) -> list[AvailabilityRecord]:
    """ROTA-T011-A (A-4): the full version chain for one availability_id
    family, oldest first. An unknown family returns an empty list, matching
    the repository's own behavior -- no exception invented here."""
    return get_availability_history(conn, availability_id)
