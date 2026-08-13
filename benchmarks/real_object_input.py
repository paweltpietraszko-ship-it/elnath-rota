"""Fail-closed validation of benchmark fixtures before oracle or production."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    REST_MIN_HOURS,
    SITE_ID,
    demands_for_month,
)
from benchmarks.real_object_types import BenchmarkInputError, DemandSpec, ScenarioSpec

_ALLOWED_AVAILABILITY = {"DAY_SHIFT_OFF", "UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}
_ALLOWED_STATES = {"PLANNED", "REALIZED", "CANCELLED"}
_ALLOWED_KINDS = {"D", "N"}
_ALLOWED_RULES = {
    "EMPLOYEE_ALLOWED_SHIFT_KINDS",
    "EMPLOYEE_ALLOWED_WEEKDAYS",
    "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS",
}


def _overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def _shift_kind(start: datetime, end: datetime) -> str | None:
    if end - start != timedelta(hours=12):
        return None
    if start.time() == time(5, 0):
        return "D"
    if start.time() == time(17, 0):
        return "N"
    return None


def _availability_blocks(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> bool:
    for record in scenario.availability:
        if record.employee_id != employee_id:
            continue
        if record.kind == "DAY_SHIFT_OFF" and record.start_date <= demand.start.date() <= record.end_date:
            return True
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in {"UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}:
            if _overlap(demand.start, demand.end, start, end):
                return True
    return False


def _rule_blocks(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> bool:
    for rule in scenario.site_rules:
        if rule.employee_id != employee_id:
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


def _external_window_covers(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> bool:
    if not scenario.external_support_enabled:
        return False
    return any(
        window.active
        and window.site_id == SITE_ID
        and window.employee_id == employee_id
        and window.start <= demand.start
        and window.end >= demand.end
        and (window.allowed_shift_kind is None or window.allowed_shift_kind == demand.kind)
        for window in scenario.external_windows
    )


def _validate_meta(scenario: ScenarioSpec, errors: list[str]) -> None:
    if not scenario.case_id:
        errors.append("case_id is empty")
    if scenario.month.day != 1:
        errors.append("month must be the first day of month")
    if not isinstance(scenario.seed, int):
        errors.append("seed must be int")
    invalid_steps = [step for step in scenario.ladder_steps if step < 1 or step > 14]
    if invalid_steps:
        errors.append(f"invalid ladder steps {invalid_steps}")
    if scenario.series_level < 0:
        errors.append("series_level must be >= 0")


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
        if rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
            if not rule.weekdays or any(day < 1 or day > 7 for day in rule.weekdays):
                errors.append(f"invalid weekdays in {rule.rule_version_id}")
        elif not rule.shift_kinds or any(kind not in _ALLOWED_KINDS for kind in rule.shift_kinds):
            errors.append(f"invalid shift kinds in {rule.rule_version_id}")


def _validate_windows(scenario: ScenarioSpec, errors: list[str]) -> None:
    for label, windows in (("current", scenario.external_windows), ("probe", scenario.external_probe_windows)):
        seen = set()
        for window in windows:
            if window.window_id in seen:
                errors.append(f"duplicate {label} external window id {window.window_id}")
            seen.add(window.window_id)
            if window.employee_id not in EXTERNAL_EMPLOYEES:
                errors.append(f"external window employee is not X/Y: {window.employee_id}")
            if window.end <= window.start:
                errors.append(f"external window non-positive interval {window.window_id}")
            if window.allowed_shift_kind not in (None, "D", "N"):
                errors.append(f"invalid allowed_shift_kind {window.window_id}")


def _validate_rest(items, errors: list[str], label: str) -> None:
    grouped = {}
    for item in items:
        if item.state == "CANCELLED":
            continue
        grouped.setdefault(item.employee_id, []).append(item)
    for employee_id, work in grouped.items():
        ordered = sorted(work, key=lambda item: item.start)
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.end > later.start:
                errors.append(f"{label} overlap for {employee_id}: {earlier.assignment_id}->{later.assignment_id}")
            elif (later.start - earlier.end).total_seconds() / 3600 < REST_MIN_HOURS:
                errors.append(f"{label} REST<{REST_MIN_HOURS}h for {employee_id}: {earlier.assignment_id}->{later.assignment_id}")


def _validate_fixed_shape(item, errors: list[str], label: str) -> str | None:
    known = set((*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES))
    if item.employee_id not in known:
        errors.append(f"{label} unknown employee {item.employee_id}")
    if item.state not in _ALLOWED_STATES:
        errors.append(f"{label} invalid state {item.assignment_id}")
    elif item.state == "CANCELLED":
        errors.append(f"{label} CANCELLED is not an operative fixed fact {item.assignment_id}")
    if item.end <= item.start:
        errors.append(f"{label} non-positive interval {item.assignment_id}")
        return None
    kind = _shift_kind(item.start, item.end)
    if kind is None:
        errors.append(f"{label} interval is not canonical D/N geometry {item.assignment_id}")
    elif item.employee_id == "C" and kind == "N":
        errors.append(f"{label} puts DAY_ONLY C on N {item.assignment_id}")
    return kind


def _validate_fixed_family(scenario: ScenarioSpec, errors: list[str]) -> None:
    demands = {demand.demand_id: demand for demand in demands_for_month(scenario)}
    all_items = [
        *(('boundary', item) for item in scenario.boundary_assignments),
        *(('fixed', item) for item in scenario.fixed_demand_assignments),
    ]
    seen_ids: set[str] = set()
    for label, item in all_items:
        if item.assignment_id in seen_ids:
            errors.append(f"duplicate assignment id across fixed inputs {item.assignment_id}")
        seen_ids.add(item.assignment_id)
        _validate_fixed_shape(item, errors, label)
        if label == "fixed":
            _validate_fixed_demand(scenario, item, demands, errors)
    _validate_rest([item for _, item in all_items], errors, "fixed/boundary")


def _validate_fixed_demand(scenario, item, demands, errors: list[str]) -> None:
    demand = demands.get(item.demand_id or "")
    if demand is None:
        errors.append(f"fixed unknown demand {item.assignment_id}/{item.demand_id}")
        return
    if item.start != demand.start or item.end != demand.end:
        errors.append(f"fixed interval does not equal demand {item.assignment_id}")
    if item.employee_id == "C" and demand.kind == "N":
        errors.append(f"fixed DAY_ONLY C on N {item.assignment_id}")
    if not (item.state == "REALIZED" or item.frozen):
        return
    if item.state != "REALIZED" and _availability_blocks(scenario, item.employee_id, demand):
        errors.append(f"fixed PLANNED assignment blocked by availability {item.assignment_id}")
    if item.state != "REALIZED" and _rule_blocks(scenario, item.employee_id, demand):
        errors.append(f"fixed PLANNED assignment blocked by SiteRule {item.assignment_id}")
    if (
        item.state != "REALIZED" and item.employee_id in EXTERNAL_EMPLOYEES
        and not _external_window_covers(scenario, item.employee_id, demand)
    ):
        errors.append(f"fixed external assignment lacks valid window {item.assignment_id}")


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
        if not (month_start - timedelta(days=6) <= item.start < month_start):
            continue
        if item.state != "REALIZED":
            errors.append(f"six-day history must be REALIZED: {item.assignment_id}")
            continue
        kind = _shift_kind(item.start, item.end)
        if kind is not None:
            observed.append((item.start.date(), kind))
    if set(observed) != expected or len(observed) != 12:
        errors.append("ladder step 3 requires exactly one REALIZED D and N on each of six predecessor days")


def validate_scenario(scenario: ScenarioSpec) -> tuple[str, ...]:
    errors: list[str] = []
    _validate_meta(scenario, errors)
    _validate_availability_and_rules(scenario, errors)
    _validate_windows(scenario, errors)
    _validate_fixed_family(scenario, errors)
    _validate_six_day_history(scenario, errors)
    return tuple(dict.fromkeys(errors))


def validate_scenario_or_raise(scenario: ScenarioSpec) -> None:
    errors = validate_scenario(scenario)
    if errors:
        raise BenchmarkInputError(f"{scenario.case_id}: " + "; ".join(errors))


if __name__ == "__main__":
    print("real_object_input OK")
