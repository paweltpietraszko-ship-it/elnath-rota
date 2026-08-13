"""Independent HARD checker for production candidates from real-object cases.

It does not call rota.planning.validator or production eligibility helpers.
The checker intentionally re-derives the benchmark's HARD facts.
"""
from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta

from benchmarks.real_object_oracle import demands_for_month
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOAD_LIMIT_HOURS,
    LOCAL_EMPLOYEES,
    REST_MIN_HOURS,
    SITE_ID,
)
from benchmarks.real_object_types import CheckResult, DemandSpec, RuleSpec, ScenarioSpec
from rota.domain import Assignment, AssignmentRole, AssignmentState


def _overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Return True when two half-open intervals overlap."""
    return start_a < end_b and end_a > start_b


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> int:
    """Return whole overlap hours."""
    seconds = max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())
    return int(seconds // 3600)


def _rest_gap_hours(first, second) -> float:
    """Return chronological rest gap in hours."""
    return (second.start_datetime - first.end_datetime).total_seconds() / 3600


def _availability_error(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> str | None:
    """Return one independent availability blocker if present."""
    for record in scenario.availability:
        if record.employee_id != employee_id:
            continue
        if record.kind == "DAY_SHIFT_OFF":
            if record.start_date <= demand.start.date() <= record.end_date:
                return "DAY_SHIFT_OFF-01"
            continue
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in {"UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}:
            if _overlap(demand.start, demand.end, start, end):
                return record.kind
    return None


def _rule_error(rule: RuleSpec, employee_id: str, demand: DemandSpec) -> bool:
    """Return True when this one T007 benchmark rule blocks the assignment."""
    if rule.employee_id != employee_id:
        return False
    if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
        return demand.kind not in rule.shift_kinds
    if rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
        return demand.start.date().isoweekday() not in rule.weekdays
    if rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
        return demand.start.date().isoweekday() in rule.weekdays and demand.kind in rule.shift_kinds
    return True


def _external_covered(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> bool:
    """Check the full ExternalSupportWindow boundary independently."""
    if not scenario.external_support_enabled:
        return False
    for window in scenario.external_windows:
        if not window.active or window.employee_id != employee_id or window.site_id != SITE_ID:
            continue
        if window.allowed_shift_kind is not None and window.allowed_shift_kind != demand.kind:
            continue
        if window.start <= demand.start and window.end >= demand.end:
            return True
    return False


def _eligibility_errors(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> list[str]:
    """Return all benchmark-side eligibility errors for one demand assignment."""
    errors = []
    if employee_id not in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        return [f"unknown employee {employee_id}"]
    if employee_id == "C" and demand.kind == "N":
        errors.append(f"DAY_ONLY-01 {employee_id}/{demand.demand_id}")
    blocker = _availability_error(scenario, employee_id, demand)
    if blocker:
        errors.append(f"{blocker} {employee_id}/{demand.demand_id}")
    for rule in scenario.site_rules:
        if _rule_error(rule, employee_id, demand):
            errors.append(f"{rule.rule_version_id} {employee_id}/{demand.demand_id}")
    if employee_id in EXTERNAL_EMPLOYEES and not _external_covered(scenario, employee_id, demand):
        errors.append(f"EXTERNAL-01 {employee_id}/{demand.demand_id}")
    return errors


def _coverage_and_eligibility(scenario: ScenarioSpec, assignments: list[Assignment]) -> list[str]:
    """Check exact automatic coverage, intervals and per-demand eligibility."""
    demands = {demand.demand_id: demand for demand in demands_for_month(scenario)}
    covered = {demand_id: [] for demand_id in demands}
    errors = []
    for assignment in assignments:
        if assignment.state == AssignmentState.CANCELLED or assignment.role != AssignmentRole.PRIMARY:
            continue
        demand = demands.get(assignment.covers_demand_id or "")
        if demand is None:
            errors.append(f"unknown covers_demand_id {assignment.assignment_id}")
            continue
        covered[demand.demand_id].append(assignment)
        if assignment.start_datetime != demand.start or assignment.end_datetime != demand.end:
            errors.append(f"automatic interval mismatch {assignment.assignment_id}")
        errors.extend(_eligibility_errors(scenario, assignment.employee_id, demand))
    for demand_id, items in covered.items():
        if len(items) != 1:
            errors.append(f"COVERAGE-01 {demand_id}: {len(items)}/1")
    return errors


def _synthetic_assignment(spec) -> Assignment:
    """Create a checker-only Assignment-shaped boundary object."""
    return Assignment(
        spec.assignment_id, "checker-boundary", spec.employee_id, spec.start, spec.end,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None,
    )


def _rest_errors(scenario: ScenarioSpec, assignments: list[Assignment]) -> list[str]:
    """Check REST-01 including benchmark boundary history."""
    work = [item for item in assignments if item.state != AssignmentState.CANCELLED]
    work.extend(_synthetic_assignment(item) for item in scenario.boundary_assignments)
    by_employee: dict[str, list[Assignment]] = {}
    for assignment in work:
        by_employee.setdefault(assignment.employee_id, []).append(assignment)
    errors = []
    for employee_id, employee_work in by_employee.items():
        ordered = sorted(employee_work, key=lambda item: item.start_datetime)
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.end_datetime > later.start_datetime:
                errors.append(f"REST-01 overlap {employee_id}: {earlier.assignment_id}->{later.assignment_id}")
                continue
            gap = _rest_gap_hours(earlier, later)
            if gap < REST_MIN_HOURS:
                errors.append(f"REST-01 {employee_id}: {gap:g}h {earlier.assignment_id}->{later.assignment_id}")
    return errors


def _rolling_windows(scenario: ScenarioSpec) -> tuple[tuple[datetime, datetime], ...]:
    """Return every seven-day window overlapping the month."""
    count = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    start = datetime.combine(scenario.month, time())
    return tuple((start + timedelta(days=offset), start + timedelta(days=offset + 7)) for offset in range(-6, count - 6))


def _load_metrics(scenario: ScenarioSpec, assignments: list[Assignment]) -> tuple[list[str], tuple[tuple[str, int], ...]]:
    """Check LOAD-01 and return per-employee worst window hours."""
    work = [item for item in assignments if item.state != AssignmentState.CANCELLED]
    work.extend(_synthetic_assignment(item) for item in scenario.boundary_assignments)
    errors = []
    maxima = []
    for employee_id in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        employee_work = [item for item in work if item.employee_id == employee_id]
        worst = 0
        for window_start, window_end in _rolling_windows(scenario):
            hours = sum(
                _overlap_hours(item.start_datetime, item.end_datetime, window_start, window_end)
                for item in employee_work
            )
            worst = max(worst, hours)
            if hours > LOAD_LIMIT_HOURS:
                errors.append(f"LOAD-01 {employee_id}: {hours}h from {window_start.date()}")
        maxima.append((employee_id, worst))
    return errors, tuple(maxima)


def _fixed_errors(scenario: ScenarioSpec, assignments: list[Assignment]) -> list[str]:
    """Check that benchmark fixed demand facts remain present and unchanged."""
    errors = []
    by_demand = {
        assignment.covers_demand_id: assignment
        for assignment in assignments
        if assignment.role == AssignmentRole.PRIMARY and assignment.state != AssignmentState.CANCELLED
    }
    for fixed in scenario.fixed_demand_assignments:
        actual = by_demand.get(fixed.demand_id)
        if actual is None:
            errors.append(f"fixed demand missing {fixed.demand_id}")
            continue
        if actual.employee_id != fixed.employee_id:
            errors.append(f"fixed employee changed {fixed.demand_id}: {fixed.employee_id}->{actual.employee_id}")
        if actual.start_datetime != fixed.start or actual.end_datetime != fixed.end:
            errors.append(f"fixed interval changed {fixed.demand_id}")
    return errors


def _monthly_hours(assignments: list[Assignment]) -> tuple[tuple[str, int], ...]:
    """Return deterministic PRIMARY monthly hours by employee."""
    hours = {employee: 0 for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY or assignment.state == AssignmentState.CANCELLED:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return tuple(sorted(hours.items()))


def check_candidate(scenario: ScenarioSpec, assignments: list[Assignment]) -> CheckResult:
    """Independently verify a production FEASIBLE candidate."""
    errors = _coverage_and_eligibility(scenario, assignments)
    errors.extend(_fixed_errors(scenario, assignments))
    errors.extend(_rest_errors(scenario, assignments))
    load_errors, maxima = _load_metrics(scenario, assignments)
    errors.extend(load_errors)
    monthly = _monthly_hours(assignments)
    if scenario.strict_monthly_hours:
        observed = dict(monthly)
        for employee, expected in scenario.strict_monthly_hours:
            if observed.get(employee) != expected:
                errors.append(f"monthly hours {employee}: {observed.get(employee)}/{expected}")
    return CheckResult(tuple(dict.fromkeys(errors)), monthly, maxima)


if __name__ == "__main__":
    print("real_object_checker OK")
