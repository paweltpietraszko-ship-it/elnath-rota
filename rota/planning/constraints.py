"""REST-01 and LOAD-01 CP-SAT constraint building, split out of solver.py to
stay under SIZE_FILE (arch/spec.md SECTION 9).

Takes already-derived fixed-assignment lists as plain arguments rather than
reaching back into solver.fixed_existing_assignments() itself, the same
pattern as fairness.py -- avoids a circular import since solver.py calls
into this module.

ROTA-T012 Part B: REST-01 is now per-work-period, via
rota.planning.work_periods (the same pure module the independent validator
uses) -- a candidate demand and a fixed Assignment both normalize into
PeriodComponent/WorkPeriod, so a normal 24h occurrence's two components
never get an internal-rest constraint against each other (they merge into
one period), and every other pair uses its own configured
required_rest_hours/required_rest_after_hours, not the old global
REST_MIN_HOURS. LOAD-01 is unaffected -- contiguous 24h components already
sum to the correct real worked hours without merging.
"""
from __future__ import annotations

import calendar
from datetime import datetime

from ortools.sat.python import cp_model

from rota.domain import Assignment, AssignmentState, ShiftCatalogKind
from rota.planning.timeutil import overlap_hours, rolling_windows
from rota.planning.work_periods import PeriodComponent, WorkPeriod, group_into_periods, violates_rest


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
    regardless, only CANCELLED filtered here. LOAD-01 only, kept in its
    original raw-interval shape -- see build_fixed_periods for REST-01."""
    fixed: dict[str, list[tuple[datetime, datetime]]] = {}
    for assignment in (*fixed_assignments, *_not_cancelled(boundary_assignments), *_not_cancelled(other_site_assignments)):
        fixed.setdefault(assignment.employee_id, []).append((assignment.start_datetime, assignment.end_datetime))
    return fixed


def build_fixed_periods(
    fixed_assignments: list[Assignment], boundary_assignments: list[Assignment], other_site_assignments: list[Assignment]
) -> dict[str, list[WorkPeriod]]:
    """REST-01 counterpart of build_fixed_intervals: same source Assignments,
    grouped into WorkPeriods by (employee_id, work_period_id) so a fixed
    24h pair (same-site or cross-site, same-month or a persisted boundary
    period) is one period with its own terminal-component rest, not two
    independent 12h facts."""
    components = [
        PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours)
        for a in (*fixed_assignments, *_not_cancelled(boundary_assignments), *_not_cancelled(other_site_assignments))
    ]
    by_employee: dict[str, list[WorkPeriod]] = {}
    for period in group_into_periods(components):
        by_employee.setdefault(period.employee_id, []).append(period)
    return by_employee


def _demand_periods(employee_id: str, employee_slots: list, site_id: str) -> list[WorkPeriod]:
    # Site-scoped to match the id a real solved Assignment for this
    # occurrence would get (solver._solved_work_period_id) -- so a
    # prospective period here and an already-fixed period for the SAME
    # occurrence's other half (same site, same template) compare equal and
    # are recognized as one period, not two independently-rest-checked ones.
    components = [
        PeriodComponent(s.demand.demand_id, employee_id, s.demand.start_datetime, s.demand.end_datetime,
                         f"{site_id}:{s.demand.work_period_template_id}" if s.demand.work_period_template_id else None,
                         s.demand.required_rest_hours)
        for s in employee_slots
    ]
    return group_into_periods(components)


def add_rest_constraints(
    model: cp_model.CpModel, x: dict, slots: list, fixed_periods: dict[str, list[WorkPeriod]], site_id: str,
) -> None:
    by_employee: dict[str, list] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

    for employee_id, employee_slots in by_employee.items():
        periods = _demand_periods(employee_id, employee_slots, site_id)
        # A period's representative CP-SAT variable is its earliest
        # component -- add_same_person_24h_constraints (solver.py) already
        # forces every component of the same period to an identical value
        # for this employee, so any one component faithfully stands in for
        # "this occurrence is assigned to employee_id" here.
        for i in range(len(periods)):
            for j in range(i + 1, len(periods)):
                if violates_rest(periods[i], periods[j]):
                    rep_i, rep_j = periods[i].component_ids[0], periods[j].component_ids[0]
                    model.add(x[employee_id, rep_i] + x[employee_id, rep_j] <= 1)
        for period in periods:
            rep = period.component_ids[0]
            for fixed_period in fixed_periods.get(employee_id, []):
                # Same period_key = this prospective period is the still-open
                # other half of an already-fixed component of the SAME
                # occurrence -- no rest check between them (WYMAGANIA REST
                # #3); add_same_person_24h_constraints ties them to the
                # identical employee instead.
                if period.period_key == fixed_period.period_key:
                    continue
                if violates_rest(period, fixed_period):
                    model.add(x[employee_id, rep] == 0)


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


def _demands_by_h24_template(shift_demands: list) -> dict[str, list]:
    by_template: dict[str, list] = {}
    for demand in shift_demands:
        if demand.catalog_kind == ShiftCatalogKind.H24 and demand.work_period_template_id:
            by_template.setdefault(demand.work_period_template_id, []).append(demand)
    return by_template


def _constrain_both_open(model: cp_model.CpModel, x: dict, d1_id: str, d2_id: str, eligible_by_key: dict, template_id: str) -> None:
    employees = eligible_by_key.get((template_id, d1_id), set()) | eligible_by_key.get((template_id, d2_id), set())
    for employee_id in employees:
        has_1, has_2 = (employee_id, d1_id) in x, (employee_id, d2_id) in x
        if has_1 and has_2:
            model.add(x[employee_id, d1_id] == x[employee_id, d2_id])
        elif has_1:
            model.add(x[employee_id, d1_id] == 0)
        elif has_2:
            model.add(x[employee_id, d2_id] == 0)


def _constrain_one_fixed(model: cp_model.CpModel, x: dict, open_demand_id: str, fixed_employees: set[str], eligible_by_key: dict, template_id: str) -> None:
    for employee_id in eligible_by_key.get((template_id, open_demand_id), set()):
        if (employee_id, open_demand_id) not in x:
            continue
        model.add(x[employee_id, open_demand_id] == (1 if employee_id in fixed_employees else 0))


def add_same_person_24h_constraints(
    model: cp_model.CpModel, x: dict, slots: list, shift_demands: list, fixed_primary_by_demand: dict[str, set[str]],
) -> None:
    """SHIFT-24-PAIR-01 (NORMAL 24h SAME-PERSON HARD, part_b_work_period_rest.md):
    a normal 24h occurrence's two demand components (sharing
    work_period_template_id, both catalog_kind=24h) must go to the SAME
    employee(s), or to neither -- generalizes to required_primary_count>1
    since every employee's presence is constrained independently. If one
    component is already fixed (REALIZED/frozen) to a set of employees, the
    still-open component is forced onto that exact same set rather than
    left free; if both are fixed, there is nothing left for CP-SAT to
    decide (the independent validator still re-checks the final pair).
    Only templates with exactly two distinct demand_ids (across
    shift_demands, not just open slots) are constrained -- a malformed/
    partial pair should not occur given generate_catalog_demands, and this
    module does not guess at one."""
    eligible_by_key: dict[tuple[str, str], set[str]] = {}
    for slot in slots:
        template_id = slot.demand.work_period_template_id
        if template_id and slot.demand.catalog_kind == ShiftCatalogKind.H24:
            eligible_by_key.setdefault((template_id, slot.demand.demand_id), set()).add(slot.employee_id)

    for template_id, demands in _demands_by_h24_template(shift_demands).items():
        if len(demands) != 2:
            continue
        d1, d2 = sorted(demands, key=lambda d: d.demand_id)
        fixed1, fixed2 = fixed_primary_by_demand.get(d1.demand_id), fixed_primary_by_demand.get(d2.demand_id)
        if fixed1 and fixed2:
            continue
        if fixed1:
            _constrain_one_fixed(model, x, d2.demand_id, fixed1, eligible_by_key, template_id)
        elif fixed2:
            _constrain_one_fixed(model, x, d1.demand_id, fixed2, eligible_by_key, template_id)
        else:
            _constrain_both_open(model, x, d1.demand_id, d2.demand_id, eligible_by_key, template_id)


if __name__ == "__main__":
    print("constraints module OK")
