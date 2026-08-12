"""CP-SAT adapter: map PlanningState -> OR-Tools CP-SAT model -> raw solver output.

Per Frozen Execution Contract v0.4 SECTION 5.4/5.5: OR-Tools CP-SAT performs
the combinatorial search. This module only maps Rota domain data to
constraints/objective and maps the CP-SAT result back to plain Assignment
objects. It does not implement scheduling search itself.

Generic over month/profile/employees: every constraint below reads its shape
(days, shifts, employees, thresholds) from PlanningState/SiteProfile, nothing
is hardcoded to October 2026 or to employees A-E.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from rota.constants import REST_MIN_HOURS
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    ShiftDemand,
    ShiftKind,
)
from rota.planning.eligibility import check_eligibility
from rota.planning.shift_catalog import classify_demand
from rota.planning.state import PlanningState
from rota.planning.timeutil import intervals_overlap, overlap_hours, rest_hours, rolling_windows

TARGET_DEVIATION_WEIGHT = 100
SOFT_PENALTY_WEIGHT = 1
SOLVER_TIME_LIMIT_SECONDS = 30.0


@dataclass
class SolverSlot:
    employee_id: str
    demand: ShiftDemand
    shift_kind: ShiftKind
    leave_plan_collision: bool
    day_off_soft_entry: bool


@dataclass
class SolverOutcome:
    status_name: str
    assignments: list[Assignment] | None
    warnings: list[str]
    unassignable_demand_ids: list[str]


def _demand_hours(demand: ShiftDemand) -> int:
    return int((demand.end_datetime - demand.start_datetime).total_seconds() // 3600)


def _already_covered_counts(state: PlanningState) -> dict[str, int]:
    counts: dict[str, int] = {}
    for assignment in state.existing_assignments:
        if assignment.role == AssignmentRole.PRIMARY and assignment.covers_demand_id:
            counts[assignment.covers_demand_id] = counts.get(assignment.covers_demand_id, 0) + 1
    return counts


def _day_off_dates(state: PlanningState, employee_id: str) -> set:
    dates = set()
    for record in state.availability_records:
        if record.employee_id != employee_id or not record.active:
            continue
        if record.kind == AvailabilityKind.DAY_SHIFT_OFF:
            current = record.start_date
            while current <= record.end_date:
                dates.add(current)
                current = current + timedelta(days=1)
    return dates


def _build_slots(state: PlanningState) -> tuple[list[SolverSlot], dict[str, int], list[str]]:
    already_covered = _already_covered_counts(state)
    memberships_by_employee = {m.employee_id: m for m in state.memberships}
    employees_by_id = {e.employee_id: e for e in state.employees}
    availability_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        availability_by_employee.setdefault(record.employee_id, []).append(record)

    slots: list[SolverSlot] = []
    still_needed: dict[str, int] = {}
    unassignable: list[str] = []

    for demand in state.shift_demands:
        needed = demand.required_primary_count - already_covered.get(demand.demand_id, 0)
        if needed <= 0:
            continue
        still_needed[demand.demand_id] = needed
        shift_kind = classify_demand(demand, state.profile)
        eligible_count = _collect_eligible_slots(
            demand, shift_kind, state, employees_by_id, memberships_by_employee,
            availability_by_employee, slots,
        )
        if eligible_count == 0:
            unassignable.append(demand.demand_id)

    return slots, still_needed, unassignable


def _collect_eligible_slots(
    demand: ShiftDemand, shift_kind: ShiftKind, state: PlanningState,
    employees_by_id: dict, memberships_by_employee_list: dict,
    availability_by_employee: dict, slots: list[SolverSlot],
) -> int:
    eligible_count = 0
    for membership in state.memberships:
        employee = employees_by_id.get(membership.employee_id)
        if employee is None:
            continue
        records = availability_by_employee.get(employee.employee_id, [])
        result = check_eligibility(
            employee, membership, demand, shift_kind, state.profile, records,
            list(state.external_windows), state.site.site_id,
        )
        if not result.eligible:
            continue
        eligible_count += 1
        day_off_soft = shift_kind == ShiftKind.N and demand.end_datetime.date() in _day_off_dates(
            state, employee.employee_id
        )
        slots.append(
            SolverSlot(employee.employee_id, demand, shift_kind, result.leave_plan_collision, day_off_soft)
        )
    return eligible_count


def _fixed_intervals(state: PlanningState) -> dict[str, list[tuple[datetime, datetime]]]:
    fixed: dict[str, list[tuple[datetime, datetime]]] = {}
    for assignment in (*state.existing_assignments, *state.boundary_assignments, *state.other_site_assignments):
        fixed.setdefault(assignment.employee_id, []).append(
            (assignment.start_datetime, assignment.end_datetime)
        )
    return fixed


def _add_coverage_constraints(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], still_needed: dict[str, int]
) -> None:
    by_demand: dict[str, list[SolverSlot]] = {}
    for slot in slots:
        by_demand.setdefault(slot.demand.demand_id, []).append(slot)
    for demand_id, needed in still_needed.items():
        terms = [x[s.employee_id, demand_id] for s in by_demand.get(demand_id, [])]
        model.add(sum(terms) == needed)


def _add_rest_constraints(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], fixed: dict[str, list[tuple[datetime, datetime]]]
) -> None:
    by_employee: dict[str, list[SolverSlot]] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

    for employee_id, employee_slots in by_employee.items():
        for i in range(len(employee_slots)):
            for j in range(i + 1, len(employee_slots)):
                a, b = employee_slots[i], employee_slots[j]
                if _violates_rest(a.demand, b.demand):
                    model.add(x[employee_id, a.demand.demand_id] + x[employee_id, b.demand.demand_id] <= 1)
        for slot in employee_slots:
            for fixed_start, fixed_end in fixed.get(employee_id, []):
                if _violates_rest_against(slot.demand, fixed_start, fixed_end):
                    model.add(x[employee_id, slot.demand.demand_id] == 0)


def _violates_rest(demand_a: ShiftDemand, demand_b: ShiftDemand) -> bool:
    if intervals_overlap(demand_a.start_datetime, demand_a.end_datetime, demand_b.start_datetime, demand_b.end_datetime):
        return True
    gap = rest_hours(demand_a.start_datetime, demand_a.end_datetime, demand_b.start_datetime, demand_b.end_datetime)
    return gap < REST_MIN_HOURS


def _violates_rest_against(demand: ShiftDemand, fixed_start: datetime, fixed_end: datetime) -> bool:
    if intervals_overlap(demand.start_datetime, demand.end_datetime, fixed_start, fixed_end):
        return True
    gap = rest_hours(demand.start_datetime, demand.end_datetime, fixed_start, fixed_end)
    return gap < REST_MIN_HOURS


def _add_load_constraints(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], fixed: dict[str, list[tuple[datetime, datetime]]],
    state: PlanningState, enforce_cap: bool,
) -> None:
    if not enforce_cap:
        return
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    windows = rolling_windows(state.month, num_days)
    by_employee: dict[str, list[SolverSlot]] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

    threshold = state.profile.rolling_7d_decision_threshold_hours
    for employee_id, employee_slots in by_employee.items():
        for window_start, window_end in windows:
            fixed_hours = sum(
                overlap_hours(fs, fe, window_start, window_end) for fs, fe in fixed.get(employee_id, [])
            )
            terms = []
            for slot in employee_slots:
                hrs = overlap_hours(slot.demand.start_datetime, slot.demand.end_datetime, window_start, window_end)
                if hrs:
                    terms.append(hrs * x[employee_id, slot.demand.demand_id])
            if terms or fixed_hours:
                model.add(sum(terms) + fixed_hours <= threshold)


def _add_objective(model: cp_model.CpModel, x: dict, slots: list[SolverSlot], state: PlanningState) -> None:
    target_by_employee = {wb.employee_id: wb.target_hours for wb in state.work_balances}
    fixed_hours_by_employee: dict[str, int] = {}
    for assignment in state.existing_assignments:
        hours = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        fixed_hours_by_employee[assignment.employee_id] = fixed_hours_by_employee.get(assignment.employee_id, 0) + hours

    penalties = []
    by_employee: dict[str, list[SolverSlot]] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

    for employee_id, target in target_by_employee.items():
        employee_slots = by_employee.get(employee_id, [])
        worked = sum(_demand_hours(s.demand) * x[employee_id, s.demand.demand_id] for s in employee_slots)
        worked += fixed_hours_by_employee.get(employee_id, 0)
        pos = model.new_int_var(0, 744, f"target_over_{employee_id}")
        neg = model.new_int_var(0, 744, f"target_under_{employee_id}")
        model.add(worked - target == pos - neg)
        penalties.append(TARGET_DEVIATION_WEIGHT * (pos + neg))

    for slot in slots:
        if slot.leave_plan_collision or slot.day_off_soft_entry:
            penalties.append(SOFT_PENALTY_WEIGHT * x[slot.employee_id, slot.demand.demand_id])

    model.minimize(sum(penalties))


def _extract_assignments(
    solver: cp_model.CpSolver, x: dict, slots: list[SolverSlot], state: PlanningState
) -> list[Assignment]:
    assignments = []
    for slot in slots:
        key = (slot.employee_id, slot.demand.demand_id)
        if solver.value(x[key]):
            assignments.append(
                Assignment(
                    assignment_id=f"solved-{slot.demand.demand_id}-{slot.employee_id}",
                    schedule_version_id=state.schedule_version_id,
                    employee_id=slot.employee_id,
                    start_datetime=slot.demand.start_datetime,
                    end_datetime=slot.demand.end_datetime,
                    role=AssignmentRole.PRIMARY,
                    state=AssignmentState.PLANNED,
                    frozen=False,
                    covers_demand_id=slot.demand.demand_id,
                    mentor_primary_assignment_id=None,
                )
            )
    return assignments


def _collect_warnings(assignments: list[Assignment], slots: list[SolverSlot]) -> list[str]:
    warnings = []
    assigned = {(a.employee_id, a.covers_demand_id) for a in assignments}
    for slot in slots:
        if (slot.employee_id, slot.demand.demand_id) not in assigned:
            continue
        if slot.day_off_soft_entry:
            warnings.append(
                f"DAY_SHIFT_OFF-01 SOFT: {slot.employee_id} prior N enters day off until 05:00 "
                f"on {slot.demand.end_datetime.date()}"
            )
        if slot.leave_plan_collision:
            warnings.append(f"LEAVE_PLAN-01 SOFT: {slot.employee_id} assigned during LEAVE_PLAN")
    return warnings


def solve(state: PlanningState, enforce_load_cap: bool = True) -> SolverOutcome:
    """Build and solve the CP-SAT model for one PlanningState. Pure mapping, no domain judgment."""
    slots, still_needed, unassignable = _build_slots(state)
    if unassignable:
        return SolverOutcome("NO_ELIGIBLE_EMPLOYEE", None, [], unassignable)

    model = cp_model.CpModel()
    x = {
        (s.employee_id, s.demand.demand_id): model.new_bool_var(f"x_{s.employee_id}_{s.demand.demand_id}")
        for s in slots
    }
    fixed = _fixed_intervals(state)

    _add_coverage_constraints(model, x, slots, still_needed)
    _add_rest_constraints(model, x, slots, fixed)
    _add_load_constraints(model, x, slots, fixed, state, enforce_load_cap)
    _add_objective(model, x, slots, state)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolverOutcome(status_name, None, [], [])

    assignments = _extract_assignments(solver, x, slots, state)
    warnings = _collect_warnings(assignments, slots)
    return SolverOutcome(status_name, assignments, warnings, [])


if __name__ == "__main__":
    print("solver module OK")
