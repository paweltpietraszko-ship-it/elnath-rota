"""Independent HARD checker and small scenario-ground-truth helpers."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Iterable

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES, LOAD_LIMIT_HOURS, LOCAL_EMPLOYEES, REST_MIN_HOURS, SITE_ID,
    demands_for_month,
)
from benchmarks.real_object_types import (
    CheckResult, DemandSpec, ExpectationKind, LoadViolation, ScenarioSpec,
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


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


def _overlap_hours(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> int:
    seconds = max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())
    return int(seconds // 3600)


def _rest_conflict(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    if _overlap(a_start, a_end, b_start, b_end):
        return True
    if a_end <= b_start:
        return (b_start - a_end).total_seconds() / 3600 < REST_MIN_HOURS
    return (a_start - b_end).total_seconds() / 3600 < REST_MIN_HOURS


def _availability_reason(scenario: ScenarioSpec, employee: str, demand: DemandSpec) -> str | None:
    mapping = {
        "UNAVAILABLE_24H": "UNAVAILABLE-01",
        "LEAVE_GRANTED": "LEAVE_GRANTED-01",
        "SICK_LEAVE": "SICK_LEAVE-01",
    }
    for record in scenario.availability:
        if record.employee_id != employee:
            continue
        if record.kind == "DAY_SHIFT_OFF":
            if record.start_date <= demand.start.date() <= record.end_date:
                return "DAY_SHIFT_OFF-01"
            continue
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in mapping and _overlap(demand.start, demand.end, start, end):
            return mapping[record.kind]
    return None


def _rule_reason(scenario: ScenarioSpec, employee: str, demand: DemandSpec) -> str | None:
    for rule in scenario.site_rules:
        if rule.employee_id != employee:
            continue
        if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS" and demand.kind not in rule.shift_kinds:
            return rule.rule_version_id
        if (
            rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS"
            and demand.start.date().isoweekday() not in rule.weekdays
        ):
            return rule.rule_version_id
        if (
            rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS"
            and demand.start.date().isoweekday() in rule.weekdays
            and demand.kind in rule.shift_kinds
        ):
            return rule.rule_version_id
    return None


def _window_covers(scenario: ScenarioSpec, windows, employee: str, demand: DemandSpec) -> bool:
    if not scenario.external_support_enabled:
        return False
    return any(
        window.active
        and window.site_id == SITE_ID
        and window.employee_id == employee
        and window.start <= demand.start
        and window.end >= demand.end
        and (window.allowed_shift_kind is None or window.allowed_shift_kind == demand.kind)
        for window in windows
    )


def eligibility_reasons(
    scenario: ScenarioSpec,
    employee: str,
    demand: DemandSpec,
    *,
    windows=None,
) -> tuple[str, ...]:
    """Return direct per-demand HARD exclusions, without solving a schedule."""
    selected_windows = scenario.external_windows if windows is None else windows
    if employee not in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        return ("UNKNOWN_EMPLOYEE",)
    reasons = []
    if employee == "C" and demand.kind == "N":
        reasons.append("DAY_ONLY-01")
    if reason := _availability_reason(scenario, employee, demand):
        reasons.append(reason)
    if reason := _rule_reason(scenario, employee, demand):
        reasons.append(reason)
    if employee in EXTERNAL_EMPLOYEES and not _window_covers(
        scenario, selected_windows, employee, demand
    ):
        reasons.append("EXTERNAL")
    return tuple(dict.fromkeys(reasons))


def _fixed_context(scenario: ScenarioSpec):
    hard_existing = tuple(
        item for item in scenario.fixed_demand_assignments
        if item.state == "REALIZED" or item.frozen
    )
    return (*scenario.boundary_assignments, *scenario.other_site_assignments, *hard_existing)


def _context_rest_blocks(scenario: ScenarioSpec, employee: str, demand: DemandSpec) -> bool:
    for item in _fixed_context(scenario):
        if item.state == "CANCELLED" or item.employee_id != employee:
            continue
        if item.demand_id == demand.demand_id:
            continue
        if _rest_conflict(item.start, item.end, demand.start, demand.end):
            return True
    return False


def eligible_employees_for_demand(
    scenario: ScenarioSpec,
    demand: DemandSpec,
    *,
    windows=None,
) -> tuple[str, ...]:
    return tuple(
        employee
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
        if not eligibility_reasons(scenario, employee, demand, windows=windows)
        and not _context_rest_blocks(scenario, employee, demand)
    )


def _demand_map(scenario: ScenarioSpec) -> dict[str, DemandSpec]:
    return {demand.demand_id: demand for demand in demands_for_month(scenario)}


def _combined_probe_windows(scenario: ScenarioSpec):
    by_id = {
        window.window_id: window
        for window in (*scenario.external_windows, *scenario.external_probe_windows)
    }
    return tuple(by_id[key] for key in sorted(by_id))


def _rolling_windows(scenario: ScenarioSpec) -> tuple[tuple[datetime, datetime], ...]:
    start = datetime.combine(scenario.month, time())
    days = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    return tuple(
        (start + timedelta(days=offset), start + timedelta(days=offset + 7))
        for offset in range(-6, days)
    )


def _forced_load_error(scenario: ScenarioSpec) -> str | None:
    demands = _demand_map(scenario)
    employee = scenario.expected_employee_id
    if not employee or not scenario.expected_demand_ids:
        return "FORCED_LOAD lacks expected employee/demands"
    forced = []
    for demand_id in scenario.expected_demand_ids:
        demand = demands.get(demand_id)
        if demand is None:
            return f"FORCED_LOAD unknown demand {demand_id}"
        eligible = eligible_employees_for_demand(scenario, demand)
        if eligible != (employee,):
            return f"{demand_id} is not forced solely to {employee}: {eligible}"
        forced.append(demand)
    if not any(
        sum(_overlap_hours(d.start, d.end, start, end) for d in forced) > LOAD_LIMIT_HOURS
        for start, end in _rolling_windows(scenario)
    ):
        return "FORCED_LOAD facts do not exceed 60h in any rolling 7-day window"
    return None


def _fixed_load_hours(scenario: ScenarioSpec, employee: str) -> int:
    work = [
        item for item in _fixed_context(scenario)
        if item.state != "CANCELLED" and item.employee_id == employee
    ]
    return max(
        (
            sum(_overlap_hours(item.start, item.end, start, end) for item in work)
            for start, end in _rolling_windows(scenario)
        ),
        default=0,
    )


def validate_ground_truth(scenario: ScenarioSpec) -> tuple[str, ...]:
    """Validate only the short construction claim declared by this scenario."""
    kind = scenario.expectation_kind
    if scenario.expected_status is None or kind is None:
        return ()
    if not scenario.expectation_reason.strip():
        return ("expectation_reason is empty",)
    demands = _demand_map(scenario)
    errors = []
    if kind == ExpectationKind.SIMPLE_SHORTAGE:
        if not scenario.expected_demand_ids:
            return ("SIMPLE_SHORTAGE lacks expected_demand_ids",)
        for demand_id in scenario.expected_demand_ids:
            demand = demands.get(demand_id)
            if demand is None:
                errors.append(f"unknown shortage demand {demand_id}")
            elif eligible_employees_for_demand(scenario, demand):
                errors.append(
                    f"{demand_id} still has eligible employees "
                    f"{eligible_employees_for_demand(scenario, demand)}"
                )
    elif kind == ExpectationKind.REST_PAIR_SHORTAGE:
        if len(scenario.expected_demand_ids) != 2 or not scenario.expected_employee_id:
            return ("REST_PAIR_SHORTAGE requires two demands and one employee",)
        first = demands.get(scenario.expected_demand_ids[0])
        second = demands.get(scenario.expected_demand_ids[1])
        if first is None or second is None:
            return ("REST_PAIR_SHORTAGE references unknown demand",)
        expected = (scenario.expected_employee_id,)
        if eligible_employees_for_demand(scenario, first) != expected:
            errors.append("first REST pair demand is not restricted to expected employee")
        if eligible_employees_for_demand(scenario, second) != expected:
            errors.append("second REST pair demand is not restricted to expected employee")
        if not _rest_conflict(first.start, first.end, second.start, second.end):
            errors.append("REST pair demands do not conflict")
    elif kind == ExpectationKind.EXTERNAL_BEFORE:
        demand = demands.get(scenario.expected_demand_ids[0]) if scenario.expected_demand_ids else None
        employee = scenario.expected_employee_id
        if demand is None or employee is None:
            return ("EXTERNAL_BEFORE lacks expected demand/employee",)
        if eligible_employees_for_demand(scenario, demand):
            errors.append("external-before demand is already coverable")
        if employee not in eligible_employees_for_demand(
            scenario, demand, windows=_combined_probe_windows(scenario)
        ):
            errors.append("probe window does not unlock expected external employee")
    elif kind == ExpectationKind.EXTERNAL_AFTER:
        demand = demands.get(scenario.expected_demand_ids[0]) if scenario.expected_demand_ids else None
        employee = scenario.expected_employee_id
        if demand is None or employee is None:
            return ("EXTERNAL_AFTER lacks expected demand/employee",)
        if employee not in eligible_employees_for_demand(scenario, demand):
            errors.append("confirmed external employee is not eligible")
        local = tuple(
            worker for worker in LOCAL_EMPLOYEES
            if worker in eligible_employees_for_demand(scenario, demand)
        )
        if local:
            errors.append(f"external-after demand is still locally coverable: {local}")
    elif kind == ExpectationKind.FORCED_LOAD:
        if error := _forced_load_error(scenario):
            errors.append(error)
    elif kind == ExpectationKind.FIXED_LOAD:
        if not scenario.expected_employee_id:
            return ("FIXED_LOAD lacks expected_employee_id",)
        observed = _fixed_load_hours(scenario, scenario.expected_employee_id)
        should_exceed = scenario.expected_status.value == "DECISION_REQUIRED"
        if should_exceed != (observed > LOAD_LIMIT_HOURS):
            errors.append(
                f"fixed load ground truth mismatch: {observed}h "
                f"for expected {scenario.expected_status.value}"
            )
    elif kind == ExpectationKind.REPLAN:
        if scenario.expected_reshuffles is None:
            errors.append("REPLAN lacks expected_reshuffles")
    return tuple(errors)


def _from_candidate(assignments: Iterable) -> list[_Work]:
    rows = []
    for item in assignments:
        role = item.role.value if hasattr(item.role, "value") else str(item.role)
        state = item.state.value if hasattr(item.state, "value") else str(item.state)
        if role != AssignmentRole.PRIMARY.value or state == AssignmentState.CANCELLED.value:
            continue
        rows.append(_Work(
            item.assignment_id, item.employee_id, item.start_datetime, item.end_datetime,
            item.covers_demand_id, state,
        ))
    return rows


def _context_work(scenario: ScenarioSpec) -> list[_Work]:
    return [
        _Work(item.assignment_id, item.employee_id, item.start, item.end, item.demand_id, item.state)
        for item in (*scenario.boundary_assignments, *scenario.other_site_assignments)
        if item.state != "CANCELLED"
    ]


def _coverage_and_eligibility(scenario: ScenarioSpec, work: list[_Work]) -> list[str]:
    demands = _demand_map(scenario)
    covered = {demand_id: [] for demand_id in demands}
    errors = []
    for item in work:
        demand = demands.get(item.demand_id or "")
        if demand is None:
            errors.append(f"unknown covers_demand_id {item.assignment_id}")
            continue
        covered[demand.demand_id].append(item)
        if item.start != demand.start or item.end != demand.end:
            errors.append(f"assignment interval mismatch {item.assignment_id}")
        if item.state != AssignmentState.REALIZED.value:
            reasons = eligibility_reasons(scenario, item.employee_id, demand)
            errors.extend(f"{reason} {item.employee_id}/{demand.demand_id}" for reason in reasons)
    errors.extend(
        f"COVERAGE-01 {demand_id}: {len(items)}/1"
        for demand_id, items in covered.items() if len(items) != 1
    )
    return errors


def _rest_errors(scenario: ScenarioSpec, work: list[_Work]) -> list[str]:
    grouped: dict[str, list[_Work]] = {}
    for item in [*work, *_context_work(scenario)]:
        grouped.setdefault(item.employee_id, []).append(item)
    errors = []
    for employee, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.start)
        for first, second in zip(ordered, ordered[1:]):
            if _rest_conflict(first.start, first.end, second.start, second.end):
                errors.append(f"REST-01 {employee}: {first.assignment_id}->{second.assignment_id}")
    return errors


def _load_metrics(
    scenario: ScenarioSpec, work: list[_Work],
) -> tuple[tuple[tuple[str, int], ...], tuple[LoadViolation, ...]]:
    all_work = [*work, *_context_work(scenario)]
    maxima, violations = [], []
    for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        rows = [item for item in all_work if item.employee_id == employee]
        worst = 0
        for start, end in _rolling_windows(scenario):
            hours = sum(_overlap_hours(item.start, item.end, start, end) for item in rows)
            worst = max(worst, hours)
            if hours > LOAD_LIMIT_HOURS:
                violations.append(
                    LoadViolation(employee, start.date(), (end - timedelta(days=1)).date(), hours)
                )
        maxima.append((employee, worst))
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
        elif actual.employee_id != fixed.employee_id:
            errors.append(f"fixed employee changed {fixed.demand_id}")
        elif actual.start != fixed.start or actual.end != fixed.end:
            errors.append(f"fixed interval changed {fixed.demand_id}")
    return errors


def _monthly_hours(work: list[_Work], scenario: ScenarioSpec) -> tuple[tuple[str, int], ...]:
    hours = {employee: 0 for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)}
    for item in work:
        if (item.start.year, item.start.month) != (scenario.month.year, scenario.month.month):
            continue
        hours[item.employee_id] = hours.get(item.employee_id, 0) + int(
            (item.end - item.start).total_seconds() // 3600
        )
    return tuple(sorted(hours.items()))


def check_candidate(scenario: ScenarioSpec, assignments: Iterable) -> CheckResult:
    work = _from_candidate(assignments)
    errors = _coverage_and_eligibility(scenario, work)
    errors.extend(_fixed_errors(scenario, work))
    errors.extend(_rest_errors(scenario, work))
    maxima, violations = _load_metrics(scenario, work)
    errors.extend(
        f"LOAD-01 {item.employee_id}: {item.hours}h from {item.window_start}"
        for item in violations
    )
    monthly = _monthly_hours(work, scenario)
    if scenario.strict_monthly_hours:
        observed = dict(monthly)
        for employee, expected in scenario.strict_monthly_hours:
            if observed.get(employee) != expected:
                errors.append(f"monthly hours {employee}: {observed.get(employee)}/{expected}")
    return CheckResult(tuple(dict.fromkeys(errors)), monthly, maxima, violations)


def reshuffle_count(scenario: ScenarioSpec, assignments: Iterable) -> int:
    """Count changed redistributable baseline (employee_id, demand_id) pairs."""
    baseline = {
        (item.employee_id, item.demand_id)
        for item in scenario.fixed_demand_assignments
        if item.state == "PLANNED" and not item.frozen and item.demand_id
    }
    candidate = {
        (item.employee_id, item.covers_demand_id)
        for item in assignments
        if (item.role.value if hasattr(item.role, "value") else str(item.role))
        == AssignmentRole.PRIMARY.value
        and (item.state.value if hasattr(item.state, "value") else str(item.state))
        != AssignmentState.CANCELLED.value
        and item.covers_demand_id
    }
    return sum(pair not in candidate for pair in baseline)


if __name__ == "__main__":
    print("real_object_checker OK")
