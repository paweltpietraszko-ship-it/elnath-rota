"""REST-01 and LOAD-01 CP-SAT constraint building, split out of solver.py to
stay under SIZE_FILE (arch/spec.md SECTION 9).

Takes already-derived fixed-assignment lists as plain arguments rather than
reaching back into solver.fixed_existing_assignments() itself, the same
pattern as fairness.py -- avoids a circular import since solver.py calls
into this module.
"""
from __future__ import annotations

import calendar
from datetime import datetime

from ortools.sat.python import cp_model

from rota.constants import REST_MIN_HOURS
from rota.domain import Assignment, AssignmentState, ShiftDemand
from rota.planning.timeutil import intervals_overlap, overlap_hours, rest_hours, rolling_windows


def _not_cancelled(assignments: list[Assignment]) -> list[Assignment]:
    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def build_fixed_intervals(
    fixed_assignments: list[Assignment], boundary_assignments: list[Assignment], other_site_assignments: list[Assignment]
) -> dict[str, list[tuple[datetime, datetime]]]:
    """CANCELLED Assignments are not actual work (arch/spec.md:257) and must
    not block a replacement via REST-01/LOAD-01 (audit round 13, tests_r13.txt
    FINDING R13-2). `fixed_assignments` is expected to already exclude
    redistributable existing PRIMARY (REPLAN, solver.fixed_existing_assignments);
    boundary/other-site Assignments are outside REPLAN's scope and stay fixed
    regardless, only CANCELLED filtered here."""
    fixed: dict[str, list[tuple[datetime, datetime]]] = {}
    for assignment in (*fixed_assignments, *_not_cancelled(boundary_assignments), *_not_cancelled(other_site_assignments)):
        fixed.setdefault(assignment.employee_id, []).append((assignment.start_datetime, assignment.end_datetime))
    return fixed


def add_rest_constraints(
    model: cp_model.CpModel, x: dict, slots: list, fixed: dict[str, list[tuple[datetime, datetime]]]
) -> None:
    by_employee: dict[str, list] = {}
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


def add_load_constraints(
    model: cp_model.CpModel, x: dict, slots: list, fixed: dict[str, list[tuple[datetime, datetime]]],
    month, threshold: int, enforce_cap: bool,
) -> None:
    if not enforce_cap:
        return
    num_days = calendar.monthrange(month.year, month.month)[1]
    windows = rolling_windows(month, num_days)
    by_employee: dict[str, list] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

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


if __name__ == "__main__":
    print("constraints module OK")
