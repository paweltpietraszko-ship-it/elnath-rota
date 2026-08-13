"""Independent HARD checker for oracle witnesses and production candidates."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOAD_LIMIT_HOURS,
    LOCAL_EMPLOYEES,
    REST_MIN_HOURS,
    SITE_ID,
    demands_for_month,
)
from benchmarks.real_object_types import (
    CheckResult,
    DemandSpec,
    ExternalWindowSpec,
    LoadViolation,
    RuleSpec,
    ScenarioSpec,
)
from rota.domain import AssignmentRole, AssignmentState


@dataclass(frozen=True)
class _Work:
    assignment_id: str
    employee_id: str
    start: datetime
    end: datetime
    demand_id: str | None
    state: str


def _overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> int:
    seconds = max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())
    return int(seconds // 3600)


def _availability_reason(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> str | None:
    for record in scenario.availability:
        if record.employee_id != employee_id:
            continue
        if record.kind == "DAY_SHIFT_OFF":
            if record.start_date <= demand.start.date() <= record.end_date:
                return "DAY_SHIFT_OFF-01"
            continue
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if not _overlap(demand.start, demand.end, start, end):
            continue
        mapping = {
            "UNAVAILABLE_24H": "UNAVAILABLE-01",
            "LEAVE_GRANTED": "LEAVE_GRANTED-01",
            "SICK_LEAVE": "SICK_LEAVE-01",
        }
        if record.kind in mapping:
            return mapping[record.kind]
    return None


def _rule_reason(rule: RuleSpec, employee_id: str, demand: DemandSpec) -> str | None:
    if rule.employee_id != employee_id:
        return None
    blocked = False
    if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
        blocked = demand.kind not in rule.shift_kinds
    elif rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
        blocked = demand.start.date().isoweekday() not in rule.weekdays
    elif rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
        blocked = demand.start.date().isoweekday() in rule.weekdays and demand.kind in rule.shift_kinds
    return rule.rule_version_id if blocked else None


def _window_covers(
    scenario: ScenarioSpec,
    windows: tuple[ExternalWindowSpec, ...],
    employee_id: str,
    demand: DemandSpec,
) -> bool:
    if not scenario.external_support_enabled:
        return False
    return any(
        window.active
        and window.site_id == SITE_ID
        and window.employee_id == employee_id
        and window.start <= demand.start
        and window.end >= demand.end
        and (window.allowed_shift_kind is None or window.allowed_shift_kind == demand.kind)
        for window in windows
    )


def _boundary_rest_reason(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> str | None:
    for item in scenario.boundary_assignments:
        if item.employee_id != employee_id or item.state == "CANCELLED":
            continue
        if _overlap(item.start, item.end, demand.start, demand.end):
            return "REST-01"
        if item.end <= demand.start:
            gap = (demand.start - item.end).total_seconds() / 3600
        else:
            gap = (item.start - demand.end).total_seconds() / 3600
        if gap < REST_MIN_HOURS:
            return "REST-01"
    return None


def eligibility_reasons(
    scenario: ScenarioSpec,
    employee_id: str,
    demand: DemandSpec,
    *,
    windows: tuple[ExternalWindowSpec, ...] | None = None,
    realized: bool = False,
) -> tuple[str, ...]:
    """Independent per-demand reasons; REALIZED skips forward eligibility."""
    if realized:
        return ()
    selected_windows = scenario.external_windows if windows is None else windows
    reasons = []
    if employee_id not in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        return ("UNKNOWN_EMPLOYEE",)
    if employee_id == "C" and demand.kind == "N":
        reasons.append("DAY_ONLY-01")
    availability = _availability_reason(scenario, employee_id, demand)
    if availability:
        reasons.append(availability)
    for rule in scenario.site_rules:
        reason = _rule_reason(rule, employee_id, demand)
        if reason:
            reasons.append(reason)
    boundary_rest = _boundary_rest_reason(scenario, employee_id, demand)
    if boundary_rest:
        reasons.append(boundary_rest)
    if employee_id in EXTERNAL_EMPLOYEES and not _window_covers(
        scenario, selected_windows, employee_id, demand
    ):
        reasons.append("EXTERNAL-01")
    return tuple(dict.fromkeys(reasons))


def independently_unassignable_demands(
    scenario: ScenarioSpec,
    *,
    windows: tuple[ExternalWindowSpec, ...] | None = None,
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Demands with zero individually eligible employees, plus evidence."""
    selected_windows = scenario.external_windows if windows is None else windows
    evidence = {}
    for demand in demands_for_month(scenario):
        per_employee = {
            employee: eligibility_reasons(scenario, employee, demand, windows=selected_windows)
            for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
        }
        if all(per_employee[employee] for employee in per_employee):
            evidence[demand.demand_id] = per_employee
    return evidence


def external_unlock_pairs(scenario: ScenarioSpec) -> set[tuple[str, str]]:
    """Pairs made eligible by explicit probe windows and not by current state."""
    current = scenario.external_windows
    combined_by_id = {window.window_id: window for window in (*current, *scenario.external_probe_windows)}
    combined = tuple(combined_by_id.values())
    pairs = set()
    for demand in demands_for_month(scenario):
        for employee in EXTERNAL_EMPLOYEES:
            before = eligibility_reasons(scenario, employee, demand, windows=current)
            after = eligibility_reasons(scenario, employee, demand, windows=combined)
            if before and "EXTERNAL-01" in before and not after:
                pairs.add((demand.demand_id, employee))
    return pairs


def _from_candidate(assignments: Iterable) -> list[_Work]:
    work = []
    for item in assignments:
        role = item.role.value if hasattr(item.role, "value") else str(item.role)
        state = item.state.value if hasattr(item.state, "value") else str(item.state)
        if role != AssignmentRole.PRIMARY.value or state == AssignmentState.CANCELLED.value:
            continue
        work.append(_Work(
            item.assignment_id, item.employee_id, item.start_datetime, item.end_datetime,
            item.covers_demand_id, state,
        ))
    return work


def _from_witness(scenario: ScenarioSpec, witness: tuple[tuple[str, str], ...]) -> list[_Work]:
    demands = {demand.demand_id: demand for demand in demands_for_month(scenario)}
    work = []
    for demand_id, employee_id in witness:
        demand = demands.get(demand_id)
        if demand is None:
            marker = datetime.combine(scenario.month, time())
            work.append(_Work(
                f"oracle-{demand_id}-{employee_id}", employee_id, marker, marker,
                demand_id, "PLANNED",
            ))
            continue
        work.append(_Work(
            f"oracle-{demand_id}-{employee_id}", employee_id, demand.start, demand.end,
            demand_id, "PLANNED",
        ))
    return work


def _coverage_and_eligibility(
    scenario: ScenarioSpec,
    work: list[_Work],
    windows: tuple[ExternalWindowSpec, ...],
) -> list[str]:
    demands = {demand.demand_id: demand for demand in demands_for_month(scenario)}
    covered = {demand_id: [] for demand_id in demands}
    errors = []
    for item in work:
        demand = demands.get(item.demand_id or "")
        if demand is None:
            errors.append(f"unknown covers_demand_id {item.assignment_id}")
            continue
        covered[demand.demand_id].append(item)
        if item.start != demand.start or item.end != demand.end:
            errors.append(f"automatic interval mismatch {item.assignment_id}")
        realized = item.state == AssignmentState.REALIZED.value
        reasons = eligibility_reasons(
            scenario, item.employee_id, demand, windows=windows, realized=realized,
        )
        errors.extend(f"{reason} {item.employee_id}/{demand.demand_id}" for reason in reasons)
    for demand_id, items in covered.items():
        if len(items) != 1:
            errors.append(f"COVERAGE-01 {demand_id}: {len(items)}/1")
    return errors


def _synthetic_boundary(scenario: ScenarioSpec) -> list[_Work]:
    return [
        _Work(item.assignment_id, item.employee_id, item.start, item.end, item.demand_id, item.state)
        for item in scenario.boundary_assignments if item.state != "CANCELLED"
    ]


def _rest_errors(scenario: ScenarioSpec, work: list[_Work]) -> list[str]:
    all_work = [*work, *_synthetic_boundary(scenario)]
    grouped: dict[str, list[_Work]] = {}
    for item in all_work:
        grouped.setdefault(item.employee_id, []).append(item)
    errors = []
    for employee_id, employee_work in grouped.items():
        ordered = sorted(employee_work, key=lambda item: item.start)
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.end > later.start:
                errors.append(f"REST-01 overlap {employee_id}: {earlier.assignment_id}->{later.assignment_id}")
                continue
            gap = (later.start - earlier.end).total_seconds() / 3600
            if gap < REST_MIN_HOURS:
                errors.append(f"REST-01 {employee_id}: {gap:g}h {earlier.assignment_id}->{later.assignment_id}")
    return errors


def _rolling_windows(scenario: ScenarioSpec) -> tuple[tuple[datetime, datetime], ...]:
    count = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    month_start = datetime.combine(scenario.month, time())
    return tuple(
        (month_start + timedelta(days=offset), month_start + timedelta(days=offset + 7))
        for offset in range(-6, count)
    )


def _load_metrics(
    scenario: ScenarioSpec, work: list[_Work],
) -> tuple[tuple[tuple[str, int], ...], tuple[LoadViolation, ...]]:
    all_work = [*work, *_synthetic_boundary(scenario)]
    maxima = []
    violations = []
    for employee_id in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        employee_work = [item for item in all_work if item.employee_id == employee_id]
        worst = 0
        for window_start, window_end in _rolling_windows(scenario):
            hours = sum(_overlap_hours(item.start, item.end, window_start, window_end) for item in employee_work)
            worst = max(worst, hours)
            if hours > LOAD_LIMIT_HOURS:
                violations.append(LoadViolation(
                    employee_id, window_start.date(), (window_end - timedelta(days=1)).date(), hours,
                ))
        maxima.append((employee_id, worst))
    return tuple(maxima), tuple(violations)


def _fixed_errors(scenario: ScenarioSpec, work: list[_Work]) -> list[str]:
    by_demand = {item.demand_id: item for item in work if item.demand_id}
    errors = []
    for fixed in scenario.fixed_demand_assignments:
        if not (fixed.state == "REALIZED" or fixed.frozen):
            continue
        actual = by_demand.get(fixed.demand_id)
        if actual is None:
            errors.append(f"fixed demand missing {fixed.demand_id}")
            continue
        if actual.employee_id != fixed.employee_id:
            errors.append(f"fixed employee changed {fixed.demand_id}: {fixed.employee_id}->{actual.employee_id}")
        if actual.start != fixed.start or actual.end != fixed.end:
            errors.append(f"fixed interval changed {fixed.demand_id}")
    return errors


def _monthly_hours(work: list[_Work], scenario: ScenarioSpec) -> tuple[tuple[str, int], ...]:
    hours = {employee: 0 for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)}
    for item in work:
        if (item.start.year, item.start.month) != (scenario.month.year, scenario.month.month):
            continue
        worked = int((item.end - item.start).total_seconds() // 3600)
        hours[item.employee_id] = hours.get(item.employee_id, 0) + worked
    return tuple(sorted(hours.items()))


def _check_work(
    scenario: ScenarioSpec,
    work: list[_Work],
    *,
    windows: tuple[ExternalWindowSpec, ...],
    enforce_load: bool,
    enforce_strict_hours: bool,
) -> CheckResult:
    errors = _coverage_and_eligibility(scenario, work, windows)
    errors.extend(_fixed_errors(scenario, work))
    errors.extend(_rest_errors(scenario, work))
    maxima, violations = _load_metrics(scenario, work)
    if enforce_load:
        errors.extend(
            f"LOAD-01 {item.employee_id}: {item.hours}h from {item.window_start}"
            for item in violations
        )
    monthly = _monthly_hours(work, scenario)
    if enforce_strict_hours and scenario.strict_monthly_hours:
        observed = dict(monthly)
        for employee, expected in scenario.strict_monthly_hours:
            if observed.get(employee) != expected:
                errors.append(f"monthly hours {employee}: {observed.get(employee)}/{expected}")
    return CheckResult(tuple(dict.fromkeys(errors)), monthly, maxima, violations)


def check_candidate(scenario: ScenarioSpec, assignments: Iterable) -> CheckResult:
    """Independent check of one production FEASIBLE candidate."""
    return _check_work(
        scenario, _from_candidate(assignments), windows=scenario.external_windows,
        enforce_load=True, enforce_strict_hours=True,
    )


def check_reference_witness(
    scenario: ScenarioSpec,
    witness: tuple[tuple[str, str], ...],
    *,
    windows: tuple[ExternalWindowSpec, ...],
    enforce_load: bool,
) -> CheckResult:
    """Independent check of every witness returned by the reference oracle."""
    return _check_work(
        scenario, _from_witness(scenario, witness), windows=windows,
        enforce_load=enforce_load, enforce_strict_hours=False,
    )


if __name__ == "__main__":
    print("real_object_checker OK")
