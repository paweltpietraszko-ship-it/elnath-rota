"""Independent CP-SAT reference oracle for ROTA-REAL-OBJECT-01.

This module never imports production PlanningEngine, solver, eligibility,
constraint builders or validator. Every FEASIBLE witness is rechecked by the
separate benchmark checker before it is allowed to classify production.
"""
from __future__ import annotations

import time as clock
from datetime import date, datetime, time, timedelta
from typing import Optional

from ortools.sat.python import cp_model

from benchmarks.real_object_checker import check_reference_witness
from benchmarks.real_object_input import validate_scenario_or_raise
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOAD_LIMIT_HOURS,
    LOCAL_EMPLOYEES,
    REST_MIN_HOURS,
    SITE_ID,
    demands_for_month,
)
from benchmarks.real_object_types import (
    ExternalWindowSpec,
    OracleClass,
    ReferenceClassification,
    ReferenceSolve,
    RuleSpec,
    ScenarioSpec,
    SolveVerdict,
)

REFERENCE_TIME_LIMIT_SECONDS = 10.0


def _intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> int:
    seconds = max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())
    return int(seconds // 3600)


def _rest_conflict(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    if _intervals_overlap(start_a, end_a, start_b, end_b):
        return True
    if end_a <= start_b:
        return (start_b - end_a).total_seconds() / 3600 < REST_MIN_HOURS
    return (start_a - end_b).total_seconds() / 3600 < REST_MIN_HOURS


def _context_assignments(scenario: ScenarioSpec):
    return (*scenario.boundary_assignments, *scenario.other_site_assignments)


def _availability_blocks(scenario: ScenarioSpec, employee_id: str, demand) -> bool:
    for record in scenario.availability:
        if record.employee_id != employee_id:
            continue
        if record.kind == "DAY_SHIFT_OFF" and record.start_date <= demand.start.date() <= record.end_date:
            return True
        start = datetime.combine(record.start_date, time())
        end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in {"UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}:
            if _intervals_overlap(demand.start, demand.end, start, end):
                return True
    return False


def _rule_allows(rule: RuleSpec, employee_id: str, demand) -> bool:
    if rule.employee_id != employee_id:
        return True
    if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
        return demand.kind in rule.shift_kinds
    if rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
        return demand.start.date().isoweekday() in rule.weekdays
    if rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
        return not (
            demand.start.date().isoweekday() in rule.weekdays
            and demand.kind in rule.shift_kinds
        )
    return False


def _window_covers(window: ExternalWindowSpec, employee_id: str, demand) -> bool:
    if not window.active or window.site_id != SITE_ID or window.employee_id != employee_id:
        return False
    if window.allowed_shift_kind is not None and window.allowed_shift_kind != demand.kind:
        return False
    return window.start <= demand.start and window.end >= demand.end


def _employee_eligible(scenario, employee_id: str, demand, windows) -> bool:
    if employee_id == "C" and demand.kind == "N":
        return False
    if _availability_blocks(scenario, employee_id, demand):
        return False
    if any(not _rule_allows(rule, employee_id, demand) for rule in scenario.site_rules):
        return False
    if employee_id in LOCAL_EMPLOYEES:
        return True
    if employee_id not in EXTERNAL_EMPLOYEES or not scenario.external_support_enabled:
        return False
    return any(_window_covers(window, employee_id, demand) for window in windows)


def _rolling_windows(scenario: ScenarioSpec) -> tuple[tuple[datetime, datetime], ...]:
    month_start = datetime.combine(scenario.month, time())
    days = len(demands_for_month(scenario)) // 2
    return tuple(
        (month_start + timedelta(days=offset), month_start + timedelta(days=offset + 7))
        for offset in range(-6, days)
    )


def _hard_fixed_by_demand(scenario: ScenarioSpec) -> dict[str, str]:
    fixed = {}
    for assignment in scenario.fixed_demand_assignments:
        if (assignment.state == "REALIZED" or assignment.frozen) and assignment.demand_id:
            fixed[assignment.demand_id] = assignment.employee_id
    return fixed


def _add_coverage(model, demands, variables) -> None:
    employees = (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    for demand in demands:
        model.add(sum(variables[(employee, demand.demand_id)] for employee in employees) == 1)


def _add_eligibility(model, scenario, demands, windows, variables) -> None:
    for demand in demands:
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
            if not _employee_eligible(scenario, employee, demand, windows):
                model.add(variables[(employee, demand.demand_id)] == 0)


def _add_fixed_demands(model, scenario, variables) -> None:
    for demand_id, employee in _hard_fixed_by_demand(scenario).items():
        model.add(variables[(employee, demand_id)] == 1)


def _add_rest(model, scenario, demands, variables) -> None:
    employees = (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    context = _context_assignments(scenario)
    for employee in employees:
        for index, first in enumerate(demands):
            for second in demands[index + 1:]:
                if _rest_conflict(first.start, first.end, second.start, second.end):
                    model.add(variables[(employee, first.demand_id)] + variables[(employee, second.demand_id)] <= 1)
        for demand in demands:
            blocked = any(
                item.employee_id == employee and item.state != "CANCELLED"
                and _rest_conflict(item.start, item.end, demand.start, demand.end)
                for item in context
            )
            if blocked:
                model.add(variables[(employee, demand.demand_id)] == 0)


def _add_load(model, scenario, demands, variables) -> None:
    context = _context_assignments(scenario)
    for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        history = [item for item in context if item.employee_id == employee and item.state != "CANCELLED"]
        for window_start, window_end in _rolling_windows(scenario):
            fixed_hours = sum(_overlap_hours(item.start, item.end, window_start, window_end) for item in history)
            terms = [
                _overlap_hours(demand.start, demand.end, window_start, window_end)
                * variables[(employee, demand.demand_id)]
                for demand in demands
            ]
            model.add(sum(terms) + fixed_hours <= LOAD_LIMIT_HOURS)


def _build_model(scenario: ScenarioSpec, windows, enforce_load: bool):
    demands = demands_for_month(scenario)
    model = cp_model.CpModel()
    variables = {
        (employee, demand.demand_id): model.new_bool_var(f"x_{employee}_{demand.demand_id}")
        for demand in demands for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    }
    _add_coverage(model, demands, variables)
    _add_eligibility(model, scenario, demands, windows, variables)
    _add_fixed_demands(model, scenario, variables)
    _add_rest(model, scenario, demands, variables)
    if enforce_load:
        _add_load(model, scenario, demands, variables)
    return model, demands, variables


def _status_name(status: int) -> str:
    mapping = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    return mapping.get(status, f"STATUS_{status}")


def _solve_built_model(scenario, model, demands, variables, *, windows, enforce_load) -> ReferenceSolve:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = REFERENCE_TIME_LIMIT_SECONDS
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = scenario.seed
    started = clock.perf_counter()
    status = solver.solve(model)
    elapsed = clock.perf_counter() - started
    name = _status_name(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        witness = tuple(
            (demand.demand_id, employee)
            for demand in demands
            for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
            if solver.value(variables[(employee, demand.demand_id)])
        )
        checked = check_reference_witness(scenario, witness, windows=windows, enforce_load=enforce_load)
        if checked.errors:
            return ReferenceSolve(
                SolveVerdict.UNKNOWN, witness, elapsed, "WITNESS_CHECK_FAILED", False,
                checked.errors, checked.load_violations,
            )
        return ReferenceSolve(SolveVerdict.FEASIBLE, witness, elapsed, name, False, (), checked.load_violations)
    if status == cp_model.INFEASIBLE:
        return ReferenceSolve(SolveVerdict.INFEASIBLE, (), elapsed, name, False)
    return ReferenceSolve(SolveVerdict.UNKNOWN, (), elapsed, name, status == cp_model.UNKNOWN)


def solve_reference(
    scenario: ScenarioSpec,
    *,
    enforce_load: bool,
    windows: Optional[tuple[ExternalWindowSpec, ...]] = None,
) -> ReferenceSolve:
    selected = scenario.external_windows if windows is None else windows
    model, demands, variables = _build_model(scenario, selected, enforce_load)
    return _solve_built_model(
        scenario, model, demands, variables,
        windows=selected, enforce_load=enforce_load,
    )


def _claim_window(scenario: ScenarioSpec, window_start: date, window_end: date):
    valid = {
        (start.date(), (end - timedelta(days=1)).date()): (start, end)
        for start, end in _rolling_windows(scenario)
    }
    return valid.get((window_start, window_end))


def _add_claimed_load_equality(
    model, scenario, demands, variables, employee_id, start_dt, end_dt, hours,
) -> None:
    context_hours = sum(
        _overlap_hours(item.start, item.end, start_dt, end_dt)
        for item in _context_assignments(scenario)
        if item.employee_id == employee_id and item.state != "CANCELLED"
    )
    terms = [
        _overlap_hours(demand.start, demand.end, start_dt, end_dt)
        * variables[(employee_id, demand.demand_id)]
        for demand in demands
    ]
    model.add(sum(terms) + context_hours == hours)


def verify_load_claim(
    scenario: ScenarioSpec,
    *,
    employee_id: str,
    window_start: date,
    window_end: date,
    hours: int,
) -> ReferenceSolve:
    validate_scenario_or_raise(scenario)
    boundaries = _claim_window(scenario, window_start, window_end)
    if (
        employee_id not in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
        or hours <= LOAD_LIMIT_HOURS or boundaries is None
    ):
        return ReferenceSolve(
            SolveVerdict.UNKNOWN, (), 0.0, "INVALID_LOAD_CLAIM", False,
            ("load certificate has invalid employee/window/hours",),
        )
    model, demands, variables = _build_model(scenario, scenario.external_windows, enforce_load=False)
    _add_claimed_load_equality(
        model, scenario, demands, variables, employee_id,
        boundaries[0], boundaries[1], hours,
    )
    return _solve_built_model(
        scenario, model, demands, variables,
        windows=scenario.external_windows, enforce_load=False,
    )


def _inconclusive(
    capped: ReferenceSolve,
    uncapped: Optional[ReferenceSolve] = None,
    *,
    probe: Optional[ReferenceSolve] = None,
    probe_uncapped: Optional[ReferenceSolve] = None,
) -> ReferenceClassification:
    return ReferenceClassification(
        OracleClass.INCONCLUSIVE, capped, uncapped,
        with_external_probe=probe,
        with_external_probe_uncapped=probe_uncapped,
    )


def _combined_probe_windows(scenario: ScenarioSpec) -> tuple[ExternalWindowSpec, ...]:
    by_id = {
        window.window_id: window
        for window in (*scenario.external_windows, *scenario.external_probe_windows)
    }
    return tuple(by_id[key] for key in sorted(by_id))


def _classify_feasible_current(scenario, capped) -> ReferenceClassification:
    if not scenario.external_windows:
        return ReferenceClassification(OracleClass.KNOWN_FEASIBLE, capped)
    no_external = solve_reference(scenario, enforce_load=False, windows=())
    if no_external.verdict == SolveVerdict.UNKNOWN:
        return ReferenceClassification(OracleClass.INCONCLUSIVE, capped, without_external=no_external)
    if no_external.verdict == SolveVerdict.INFEASIBLE:
        return ReferenceClassification(
            OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT,
            capped, without_external=no_external,
        )
    return ReferenceClassification(OracleClass.KNOWN_FEASIBLE, capped, without_external=no_external)


def _classify_hard_shortage(scenario, capped, uncapped) -> ReferenceClassification:
    if not scenario.external_probe_windows:
        return ReferenceClassification(OracleClass.PROVEN_STAFFING_SHORTAGE, capped, uncapped)
    probe_windows = _combined_probe_windows(scenario)
    probe = solve_reference(scenario, enforce_load=True, windows=probe_windows)
    if probe.verdict == SolveVerdict.UNKNOWN:
        return _inconclusive(capped, uncapped, probe=probe)
    if probe.verdict == SolveVerdict.FEASIBLE:
        return ReferenceClassification(
            OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED,
            capped, uncapped, with_external_probe=probe,
        )
    probe_uncapped = solve_reference(scenario, enforce_load=False, windows=probe_windows)
    if probe_uncapped.verdict != SolveVerdict.INFEASIBLE:
        return _inconclusive(capped, uncapped, probe=probe, probe_uncapped=probe_uncapped)
    return ReferenceClassification(
        OracleClass.PROVEN_STAFFING_SHORTAGE,
        capped, uncapped,
        with_external_probe=probe,
        with_external_probe_uncapped=probe_uncapped,
    )


def classify_reference(scenario: ScenarioSpec) -> ReferenceClassification:
    validate_scenario_or_raise(scenario)
    capped = solve_reference(scenario, enforce_load=True)
    if capped.verdict == SolveVerdict.UNKNOWN:
        return _inconclusive(capped)
    if capped.verdict == SolveVerdict.FEASIBLE:
        return _classify_feasible_current(scenario, capped)
    uncapped = solve_reference(scenario, enforce_load=False)
    if uncapped.verdict == SolveVerdict.UNKNOWN:
        return _inconclusive(capped, uncapped)
    if uncapped.verdict == SolveVerdict.FEASIBLE:
        return ReferenceClassification(OracleClass.LOAD_DECISION_REQUIRED, capped, uncapped)
    return _classify_hard_shortage(scenario, capped, uncapped)


if __name__ == "__main__":
    from benchmarks.real_object_scenarios import core_scenarios

    first = core_scenarios()[0]
    print(first.case_id, classify_reference(first).expected_class)
