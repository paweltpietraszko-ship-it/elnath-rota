"""Fail-closed structural validation of real-object benchmark fixtures."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES, LOCAL_EMPLOYEES, REST_MIN_HOURS, SITE_ID, demands_for_month,
)
from benchmarks.real_object_types import ScenarioSpec

_ALLOWED_AVAILABILITY = {"DAY_SHIFT_OFF", "UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}
_ALLOWED_STATES = {"PLANNED", "REALIZED", "CANCELLED"}
_ALLOWED_KINDS = {"D", "N"}
_ALLOWED_RULES = {
    "EMPLOYEE_ALLOWED_SHIFT_KINDS",
    "EMPLOYEE_ALLOWED_WEEKDAYS",
    "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS",
}


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


def _shift_kind(start: datetime, end: datetime) -> str | None:
    if end - start != timedelta(hours=12):
        return None
    if start.time() == time(5):
        return "D"
    if start.time() == time(17):
        return "N"
    return None


def _rest_conflict(first, second) -> bool:
    if _overlap(first.start, first.end, second.start, second.end):
        return True
    if first.end <= second.start:
        gap = (second.start - first.end).total_seconds() / 3600
    else:
        gap = (first.start - second.end).total_seconds() / 3600
    return gap < REST_MIN_HOURS


def _validate_meta(scenario: ScenarioSpec, errors: list[str]) -> None:
    if not scenario.case_id:
        errors.append("case_id is empty")
    if scenario.month.day != 1:
        errors.append("month must be first day of month")
    if not isinstance(scenario.seed, int):
        errors.append("seed must be int")
    if any(step < 1 or step > 14 for step in scenario.ladder_steps):
        errors.append(f"invalid ladder steps {scenario.ladder_steps}")
    if scenario.series_level < 0:
        errors.append("series_level must be >= 0")
    if scenario.expected_status is not None and scenario.expectation_kind is None:
        errors.append("expected_status requires expectation_kind")
    if scenario.expected_status is not None and not scenario.expectation_reason.strip():
        errors.append("expected_status requires expectation_reason")
    if scenario.expected_reshuffles is not None and scenario.expected_reshuffles < 0:
        errors.append("expected_reshuffles must be >= 0")
    if len(set(scenario.expected_demand_ids)) != len(scenario.expected_demand_ids):
        errors.append("duplicate expected_demand_ids")


def _valid_weekdays(values) -> bool:
    return bool(values) and all(
        isinstance(day, int) and not isinstance(day, bool) and 1 <= day <= 7
        for day in values
    )


def _valid_shift_kinds(values) -> bool:
    return bool(values) and all(kind in _ALLOWED_KINDS for kind in values)


def _validate_availability_and_rules(scenario: ScenarioSpec, errors: list[str]) -> None:
    known = set((*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES))
    for record in scenario.availability:
        if record.employee_id not in known:
            errors.append(f"availability unknown employee {record.employee_id}")
        if record.kind not in _ALLOWED_AVAILABILITY:
            errors.append(f"unsupported availability kind {record.kind}")
        if record.end_date < record.start_date:
            errors.append(f"availability reversed range for {record.employee_id}")
    seen_rules = set()
    for rule in scenario.site_rules:
        if rule.rule_version_id in seen_rules:
            errors.append(f"duplicate rule id {rule.rule_version_id}")
        seen_rules.add(rule.rule_version_id)
        if rule.employee_id not in known:
            errors.append(f"rule unknown employee {rule.employee_id}")
        if rule.rule_kind not in _ALLOWED_RULES:
            errors.append(f"unsupported rule kind {rule.rule_kind}")
            continue
        if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
            if not _valid_shift_kinds(rule.shift_kinds):
                errors.append(f"invalid shift kinds in {rule.rule_version_id}")
        elif rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
            if not _valid_weekdays(rule.weekdays):
                errors.append(f"invalid weekdays in {rule.rule_version_id}")
        elif rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
            if not _valid_weekdays(rule.weekdays):
                errors.append(f"invalid weekdays in {rule.rule_version_id}")
            if not _valid_shift_kinds(rule.shift_kinds):
                errors.append(f"invalid shift kinds in {rule.rule_version_id}")


def _validate_windows(scenario: ScenarioSpec, errors: list[str]) -> None:
    seen = set()
    for label, windows in (("current", scenario.external_windows), ("probe", scenario.external_probe_windows)):
        for window in windows:
            if window.window_id in seen:
                errors.append(f"duplicate external window id {window.window_id}")
            seen.add(window.window_id)
            if window.employee_id not in EXTERNAL_EMPLOYEES:
                errors.append(f"{label} window employee is not X/Y: {window.employee_id}")
            if window.end <= window.start:
                errors.append(f"{label} window non-positive interval {window.window_id}")
            if window.allowed_shift_kind not in (None, "D", "N"):
                errors.append(f"invalid allowed_shift_kind {window.window_id}")


def _validate_assignment_ids(scenario: ScenarioSpec, errors: list[str]) -> None:
    seen = set()
    for label, rows in (
        ("boundary", scenario.boundary_assignments),
        ("other-site", scenario.other_site_assignments),
        ("fixed", scenario.fixed_demand_assignments),
    ):
        for item in rows:
            if item.assignment_id in seen:
                errors.append(f"duplicate assignment_id across fixture: {item.assignment_id}")
            seen.add(item.assignment_id)
            if item.end <= item.start:
                errors.append(f"{label} non-positive interval {item.assignment_id}")
            if item.state not in _ALLOWED_STATES:
                errors.append(f"{label} invalid state {item.assignment_id}")
            if item.employee_id not in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
                errors.append(f"{label} unknown employee {item.employee_id}")


def _validate_boundary(scenario: ScenarioSpec, errors: list[str]) -> None:
    for item in scenario.boundary_assignments:
        if item.employee_id not in LOCAL_EMPLOYEES:
            errors.append(f"boundary employee must be LOCAL: {item.employee_id}")
        kind = _shift_kind(item.start, item.end)
        if kind is None:
            errors.append(f"boundary is not canonical D/N geometry: {item.assignment_id}")
        if item.employee_id == "C" and kind == "N":
            errors.append(f"boundary puts DAY_ONLY C on N {item.assignment_id}")
    for item in scenario.other_site_assignments:
        if item.employee_id not in LOCAL_EMPLOYEES:
            errors.append(f"other-site context employee must be LOCAL: {item.employee_id}")
        if item.demand_id is not None:
            errors.append(f"other-site context must not cover target demand: {item.assignment_id}")


def _availability_blocks(scenario: ScenarioSpec, employee: str, demand) -> bool:
    for record in scenario.availability:
        if record.employee_id != employee:
            continue
        if record.kind == "DAY_SHIFT_OFF":
            if record.start_date <= demand.start.date() <= record.end_date:
                return True
            continue
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in {"UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}:
            if _overlap(demand.start, demand.end, start, end):
                return True
    return False


def _rule_blocks(scenario: ScenarioSpec, employee: str, demand) -> bool:
    for rule in scenario.site_rules:
        if rule.employee_id != employee:
            continue
        if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS" and demand.kind not in rule.shift_kinds:
            return True
        if rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS" and demand.start.date().isoweekday() not in rule.weekdays:
            return True
        if (
            rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS"
            and demand.start.date().isoweekday() in rule.weekdays
            and demand.kind in rule.shift_kinds
        ):
            return True
    return False


def _external_window_covers(scenario: ScenarioSpec, employee: str, demand) -> bool:
    if not scenario.external_support_enabled:
        return False
    return any(
        window.active and window.site_id == SITE_ID and window.employee_id == employee
        and window.start <= demand.start and window.end >= demand.end
        and (window.allowed_shift_kind is None or window.allowed_shift_kind == demand.kind)
        for window in scenario.external_windows
    )


def _validate_fixed_demands(scenario: ScenarioSpec, errors: list[str]) -> None:
    demands = {demand.demand_id: demand for demand in demands_for_month(scenario)}
    hard_demand_ids = set()
    for item in scenario.fixed_demand_assignments:
        demand = demands.get(item.demand_id or "")
        if demand is None:
            errors.append(f"fixed unknown demand {item.assignment_id}/{item.demand_id}")
            continue
        if item.start != demand.start or item.end != demand.end:
            errors.append(f"fixed interval does not equal demand {item.assignment_id}")
        if item.employee_id == "C" and demand.kind == "N":
            errors.append(f"fixed DAY_ONLY C on N {item.assignment_id}")
        hard = item.state == "REALIZED" or item.frozen
        if not hard:
            continue
        if demand.demand_id in hard_demand_ids:
            errors.append(f"two hard existing assignments cover {demand.demand_id}")
        hard_demand_ids.add(demand.demand_id)
        if item.state != "REALIZED":
            if _availability_blocks(scenario, item.employee_id, demand):
                errors.append(f"hard PLANNED assignment blocked by availability {item.assignment_id}")
            if _rule_blocks(scenario, item.employee_id, demand):
                errors.append(f"hard PLANNED assignment blocked by SiteRule {item.assignment_id}")
            if item.employee_id in EXTERNAL_EMPLOYEES and not _external_window_covers(scenario, item.employee_id, demand):
                errors.append(f"hard external assignment lacks valid window {item.assignment_id}")


def _validate_fixed_rest(scenario: ScenarioSpec, errors: list[str]) -> None:
    hard_existing = tuple(
        item for item in scenario.fixed_demand_assignments
        if item.state == "REALIZED" or item.frozen
    )
    work = [
        item for item in (*scenario.boundary_assignments, *scenario.other_site_assignments, *hard_existing)
        if item.state != "CANCELLED"
    ]
    grouped = {}
    for item in work:
        grouped.setdefault(item.employee_id, []).append(item)
    for employee, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.start)
        for first, second in zip(ordered, ordered[1:]):
            if _rest_conflict(first, second):
                errors.append(
                    f"fixed context REST<{REST_MIN_HOURS}h for {employee}: "
                    f"{first.assignment_id}->{second.assignment_id}"
                )


def _validate_six_day_history(scenario: ScenarioSpec, errors: list[str]) -> None:
    if 3 not in scenario.ladder_steps:
        return
    month_start = datetime.combine(scenario.month, time())
    expected = {
        (scenario.month + timedelta(days=offset), kind)
        for offset in range(-6, 0) for kind in ("D", "N")
    }
    observed = []
    for item in scenario.boundary_assignments:
        if item.state == "CANCELLED":
            continue
        if not (month_start - timedelta(days=6) <= item.start < month_start):
            continue
        kind = _shift_kind(item.start, item.end)
        if kind:
            observed.append((item.start.date(), kind))
    if set(observed) != expected or len(observed) != 12:
        errors.append("ladder step 3 requires one operative D and N on each of six predecessor days")


def validate_scenario(scenario: ScenarioSpec) -> tuple[str, ...]:
    errors: list[str] = []
    _validate_meta(scenario, errors)
    _validate_availability_and_rules(scenario, errors)
    _validate_windows(scenario, errors)
    _validate_assignment_ids(scenario, errors)
    _validate_boundary(scenario, errors)
    _validate_fixed_demands(scenario, errors)
    _validate_fixed_rest(scenario, errors)
    _validate_six_day_history(scenario, errors)
    return tuple(dict.fromkeys(errors))


def validate_series_monotonicity(scenarios) -> tuple[str, ...]:
    """A series may only add availability facts as its level increases."""
    grouped = {}
    for scenario in scenarios:
        if scenario.series_id:
            grouped.setdefault(scenario.series_id, []).append(scenario)
    errors = []
    for series_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.series_level)
        for previous, current in zip(ordered, ordered[1:]):
            if not set(previous.availability) <= set(current.availability):
                errors.append(
                    f"series {series_id} is not monotonic at "
                    f"{previous.series_level}->{current.series_level}"
                )
    return tuple(errors)


if __name__ == "__main__":
    print("real_object_input OK")
