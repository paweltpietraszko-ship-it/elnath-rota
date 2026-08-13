"""Independent CP-SAT reference oracle for the real-object benchmark.

The oracle intentionally does not import production PlanningEngine, solver,
eligibility, constraint builders or validator.  It encodes the frozen HARD
facts independently and asks only existence questions.
"""
from __future__ import annotations

import calendar
import time as clock
from datetime import datetime, time, timedelta
from typing import Optional

from ortools.sat.python import cp_model

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOAD_LIMIT_HOURS,
    LOCAL_EMPLOYEES,
    REST_MIN_HOURS,
    SITE_ID,
)
from benchmarks.real_object_types import (
    DemandSpec,
    ExternalWindowSpec,
    OracleClass,
    ReferenceClassification,
    ReferenceSolve,
    RuleSpec,
    ScenarioSpec,
    SolveVerdict,
)

REFERENCE_TIME_LIMIT_SECONDS = 10.0


def demands_for_month(scenario: ScenarioSpec) -> tuple[DemandSpec, ...]:
    """Build one 05-17 D and one 17-05 N demand for every calendar day."""
    days = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    demands = []
    for day_number in range(1, days + 1):
        day = scenario.month.replace(day=day_number)
        day_start = datetime.combine(day, time(5, 0))
        night_start = datetime.combine(day, time(17, 0))
        demands.append(DemandSpec(f"{day}-D", "D", day_start, night_start))
        demands.append(DemandSpec(f"{day}-N", "N", night_start, day_start + timedelta(days=1)))
    return tuple(demands)


def _intervals_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Return True for overlap of half-open intervals."""
    return start_a < end_b and end_a > start_b


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> int:
    """Return whole hours of half-open interval overlap."""
    seconds = max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())
    return int(seconds // 3600)


def _rest_conflict(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Return True when two work intervals overlap or leave <11h rest."""
    if _intervals_overlap(start_a, end_a, start_b, end_b):
        return True
    if end_a <= start_b:
        return (start_b - end_a).total_seconds() / 3600 < REST_MIN_HOURS
    return (start_a - end_b).total_seconds() / 3600 < REST_MIN_HOURS


def _availability_blocks(scenario: ScenarioSpec, employee_id: str, demand: DemandSpec) -> bool:
    """Apply benchmark-side DAY_SHIFT_OFF and hard absence semantics."""
    for record in scenario.availability:
        if record.employee_id != employee_id:
            continue
        if record.kind == "DAY_SHIFT_OFF":
            if record.start_date <= demand.start.date() <= record.end_date:
                return True
            continue
        range_start = datetime.combine(record.start_date, time())
        range_end = datetime.combine(record.end_date + timedelta(days=1), time())
        if record.kind in {"UNAVAILABLE_24H", "LEAVE_GRANTED", "SICK_LEAVE"}:
            if _intervals_overlap(demand.start, demand.end, range_start, range_end):
                return True
    return False


def _rule_allows(rule: RuleSpec, employee_id: str, demand: DemandSpec) -> bool:
    """Apply exactly the initial T007 HARD catalog used by benchmark cases."""
    if rule.employee_id != employee_id:
        return True
    if rule.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
        return demand.kind in rule.shift_kinds
    if rule.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
        return demand.start.date().isoweekday() in rule.weekdays
    if rule.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
        return not (demand.start.date().isoweekday() in rule.weekdays and demand.kind in rule.shift_kinds)
    raise ValueError(f"benchmark RuleSpec uses unsupported rule_kind: {rule.rule_kind}")


def _window_covers(window: ExternalWindowSpec, employee_id: str, demand: DemandSpec) -> bool:
    """Return True only for an exact semantically valid external window."""
    if not window.active or window.site_id != SITE_ID or window.employee_id != employee_id:
        return False
    if window.allowed_shift_kind is not None and window.allowed_shift_kind != demand.kind:
        return False
    return window.start <= demand.start and window.end >= demand.end


def _employee_eligible(
    scenario: ScenarioSpec, employee_id: str, demand: DemandSpec, windows: tuple[ExternalWindowSpec, ...]
) -> bool:
    """Independent per-demand eligibility for LOCAL and EXTERNAL staff."""
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
    """Return every seven-day window that overlaps the planning month."""
    days = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    month_start = datetime.combine(scenario.month, time())
    return tuple(
        (month_start + timedelta(days=offset), month_start + timedelta(days=offset + 7))
        for offset in range(-6, days - 6)
    )


def _fixed_by_demand(scenario: ScenarioSpec) -> dict[str, str]:
    """Return forced employee per demand and reject duplicate fixture claims."""
    fixed = {}
    for assignment in scenario.fixed_demand_assignments:
        if assignment.demand_id is None:
            raise ValueError(f"{scenario.case_id}: fixed demand assignment lacks demand_id")
        if assignment.demand_id in fixed:
            raise ValueError(f"{scenario.case_id}: duplicate fixed demand {assignment.demand_id}")
        fixed[assignment.demand_id] = assignment.employee_id
    return fixed


def _validate_boundary(scenario: ScenarioSpec) -> None:
    """Reject benchmark inputs that already violate REST among fixed history."""
    grouped: dict[str, list] = {}
    for assignment in scenario.boundary_assignments:
        grouped.setdefault(assignment.employee_id, []).append(assignment)
    for employee_id, work in grouped.items():
        ordered = sorted(work, key=lambda item: item.start)
        for earlier, later in zip(ordered, ordered[1:]):
            if _rest_conflict(earlier.start, earlier.end, later.start, later.end):
                raise ValueError(
                    f"{scenario.case_id}: invalid fixed boundary REST for {employee_id}: "
                    f"{earlier.assignment_id}->{later.assignment_id}"
                )


def _add_coverage(
    model: cp_model.CpModel, demands: tuple[DemandSpec, ...], variables: dict[tuple[str, str], cp_model.IntVar]
) -> None:
    """COVERAGE-01: exactly one PRIMARY per benchmark demand."""
    employees = (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    for demand in demands:
        model.add(sum(variables[(employee, demand.demand_id)] for employee in employees) == 1)


def _add_eligibility(
    model: cp_model.CpModel,
    scenario: ScenarioSpec,
    demands: tuple[DemandSpec, ...],
    windows: tuple[ExternalWindowSpec, ...],
    variables: dict[tuple[str, str], cp_model.IntVar],
) -> None:
    """Set impossible employee/demand pairs to zero."""
    for demand in demands:
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
            if not _employee_eligible(scenario, employee, demand, windows):
                model.add(variables[(employee, demand.demand_id)] == 0)


def _add_fixed_demands(
    model: cp_model.CpModel,
    scenario: ScenarioSpec,
    variables: dict[tuple[str, str], cp_model.IntVar],
) -> None:
    """Force already-fixed benchmark demand assignments."""
    for demand_id, employee in _fixed_by_demand(scenario).items():
        key = (employee, demand_id)
        if key not in variables:
            raise ValueError(f"{scenario.case_id}: unknown fixed demand {demand_id}")
        model.add(variables[key] == 1)


def _add_rest(
    model: cp_model.CpModel,
    scenario: ScenarioSpec,
    demands: tuple[DemandSpec, ...],
    variables: dict[tuple[str, str], cp_model.IntVar],
) -> None:
    """REST-01 against candidate demands and fixed boundary history."""
    for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        for index, first in enumerate(demands):
            for second in demands[index + 1:]:
                if _rest_conflict(first.start, first.end, second.start, second.end):
                    model.add(variables[(employee, first.demand_id)] + variables[(employee, second.demand_id)] <= 1)
        for demand in demands:
            if any(
                fixed.employee_id == employee
                and _rest_conflict(fixed.start, fixed.end, demand.start, demand.end)
                for fixed in scenario.boundary_assignments
            ):
                model.add(variables[(employee, demand.demand_id)] == 0)


def _add_load(
    model: cp_model.CpModel,
    scenario: ScenarioSpec,
    demands: tuple[DemandSpec, ...],
    variables: dict[tuple[str, str], cp_model.IntVar],
) -> None:
    """LOAD-01 using actual overlap hours and six-day boundary context."""
    for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
        fixed = [item for item in scenario.boundary_assignments if item.employee_id == employee]
        for window_start, window_end in _rolling_windows(scenario):
            fixed_hours = sum(_overlap_hours(item.start, item.end, window_start, window_end) for item in fixed)
            terms = [
                _overlap_hours(demand.start, demand.end, window_start, window_end)
                * variables[(employee, demand.demand_id)]
                for demand in demands
            ]
            model.add(sum(terms) + fixed_hours <= LOAD_LIMIT_HOURS)


def _build_model(
    scenario: ScenarioSpec, windows: tuple[ExternalWindowSpec, ...], enforce_load: bool
) -> tuple[cp_model.CpModel, tuple[DemandSpec, ...], dict[tuple[str, str], cp_model.IntVar]]:
    """Build an independent existence model for one scenario."""
    _validate_boundary(scenario)
    demands = demands_for_month(scenario)
    model = cp_model.CpModel()
    variables = {
        (employee, demand.demand_id): model.new_bool_var(f"x_{employee}_{demand.demand_id}")
        for demand in demands
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    }
    _add_coverage(model, demands, variables)
    _add_eligibility(model, scenario, demands, windows, variables)
    _add_fixed_demands(model, scenario, variables)
    _add_rest(model, scenario, demands, variables)
    if enforce_load:
        _add_load(model, scenario, demands, variables)
    return model, demands, variables


def solve_reference(
    scenario: ScenarioSpec,
    *,
    enforce_load: bool,
    windows: Optional[tuple[ExternalWindowSpec, ...]] = None,
) -> ReferenceSolve:
    """Solve one independent existence question and return a reproducible witness."""
    selected_windows = scenario.external_windows if windows is None else windows
    model, demands, variables = _build_model(scenario, selected_windows, enforce_load)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = REFERENCE_TIME_LIMIT_SECONDS
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    started = clock.perf_counter()
    status = solver.solve(model)
    elapsed = clock.perf_counter() - started
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        witness = tuple(
            (demand.demand_id, employee)
            for demand in demands
            for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
            if solver.value(variables[(employee, demand.demand_id)])
        )
        return ReferenceSolve(SolveVerdict.FEASIBLE, witness, elapsed)
    if status == cp_model.INFEASIBLE:
        return ReferenceSolve(SolveVerdict.INFEASIBLE, (), elapsed)
    return ReferenceSolve(SolveVerdict.UNKNOWN, (), elapsed)


def _inconclusive(capped: ReferenceSolve, uncapped: Optional[ReferenceSolve] = None) -> ReferenceClassification:
    """Build an explicit inconclusive classification."""
    return ReferenceClassification(OracleClass.INCONCLUSIVE, capped, uncapped)


def classify_reference(scenario: ScenarioSpec) -> ReferenceClassification:
    """Classify a case before production PlanningEngine is called."""
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


def _classify_feasible_current(scenario: ScenarioSpec, capped: ReferenceSolve) -> ReferenceClassification:
    """Distinguish ordinary feasibility from feasibility that requires X/Y."""
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


def _classify_hard_shortage(
    scenario: ScenarioSpec, capped: ReferenceSolve, uncapped: ReferenceSolve
) -> ReferenceClassification:
    """Check whether an explicit coordinator-provided X/Y probe resolves shortage."""
    if scenario.external_probe_windows:
        windows_by_id = {window.window_id: window for window in (*scenario.external_windows, *scenario.external_probe_windows)}
        probe = solve_reference(scenario, enforce_load=True, windows=tuple(windows_by_id.values()))
        if probe.verdict == SolveVerdict.UNKNOWN:
            return ReferenceClassification(OracleClass.INCONCLUSIVE, capped, uncapped, with_external_probe=probe)
        if probe.verdict == SolveVerdict.FEASIBLE:
            return ReferenceClassification(
                OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED,
                capped, uncapped, with_external_probe=probe,
            )
    return ReferenceClassification(OracleClass.PROVEN_STAFFING_SHORTAGE, capped, uncapped)


if __name__ == "__main__":
    from benchmarks.real_object_scenarios import core_scenarios

    first = core_scenarios()[0]
    print(first.case_id, classify_reference(first).expected_class)
