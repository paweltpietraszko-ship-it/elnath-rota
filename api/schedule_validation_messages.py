"""ROTA-CLOUD-REVIEW-FIXES F6/O4: pure presentation of the HARD violations
the month read already computed (open_month -> validate). Turns each
structured ViolationDetail into one Polish sentence for the existing
MonthViewOut.warnings banner. Never parses the English `message`, never
shows raw ids/codes, never drops a violation it does not recognize, and
never invents a person or a date it could not resolve.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

from rota.domain import Assignment, Employee, ShiftDemand, SiteRuleVersion
from rota.planning.validator_shared import ViolationDetail

_UNKNOWN_RULE_LABEL = "naruszenie reguły planowania"
_SITE_RULE_LABEL = "reguła obiektu"
_MISSING_DETAILS = "część szczegółów niedostępna"
_NO_DETAILS = "brak szczegółów osoby i daty"


def _day(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}"


def _label(rule: str, labels: Mapping[str, str], site_rules_by_id: Mapping[str, SiteRuleVersion]) -> str:
    if rule in labels:
        return labels[rule]
    site_rule = site_rules_by_id.get(rule)
    if site_rule is not None:
        description = (site_rule.description or "").strip()
        return f"{_SITE_RULE_LABEL} „{description}”" if description else _SITE_RULE_LABEL
    return _UNKNOWN_RULE_LABEL


def describe_violation(
    detail: ViolationDetail,
    *,
    labels: Mapping[str, str],
    assignments_by_id: Mapping[str, Assignment],
    demands_by_id: Mapping[str, ShiftDemand],
    employees_by_id: Mapping[str, Employee],
    site_rules_by_id: Mapping[str, SiteRuleVersion],
) -> str:
    names: list[str] = []
    days: list[str] = []
    missing = False

    def add_person(employee_id: str) -> None:
        nonlocal missing
        employee = employees_by_id.get(employee_id)
        if employee is None:
            missing = True
        elif employee.display_name not in names:
            names.append(employee.display_name)

    for assignment_id in detail.assignment_ids:
        assignment = assignments_by_id.get(assignment_id)
        if assignment is None:
            missing = True
            continue
        add_person(assignment.employee_id)
        day = _day(assignment.start_datetime.date())
        if day not in days:
            days.append(day)
    if detail.affected_employee_id is not None:
        add_person(detail.affected_employee_id)
    for demand_id in detail.demand_ids:
        demand = demands_by_id.get(demand_id)
        if demand is None:
            missing = True
            continue
        when = f"{_day(demand.start_datetime.date())} {demand.start_datetime:%H:%M}–{demand.end_datetime:%H:%M}"
        if when not in days:
            days.append(when)

    parts = [p for p in (", ".join(names), ", ".join(days)) if p]
    if not parts:
        parts.append(_NO_DETAILS)
    elif missing:
        parts.append(_MISSING_DETAILS)
    return f"Naruszenie: {_label(detail.rule, labels, site_rules_by_id)} — {'; '.join(parts)}."


def describe_violations(details: Iterable[ViolationDetail], **lookups) -> list[str]:
    messages: list[str] = []
    for detail in details:
        message = describe_violation(detail, **lookups)
        if message not in messages:
            messages.append(message)
    return messages
