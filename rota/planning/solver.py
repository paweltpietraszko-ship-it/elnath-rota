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
from datetime import date, datetime, timedelta

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
from rota.planning.fairness import add_holiday_fairness, add_weekend_fairness
from rota.planning.shift_catalog import classify_demand
from rota.planning.state import PlanningState
from rota.planning.timeutil import intervals_overlap, overlap_hours, rest_hours, rolling_windows

TARGET_DEVIATION_WEIGHT = 100
SOFT_PENALTY_WEIGHT = 1
SOLVER_TIME_LIMIT_SECONDS = 30.0
MAX_MONTHLY_HOURS = 744
SICK_LEAVE_HOURS_PER_DAY = 8


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
    unassignable_reasons: dict[str, list[tuple[str, str]]]
    conflicting_demand_ids: list[str]


def _demand_hours(demand: ShiftDemand) -> int:
    return int((demand.end_datetime - demand.start_datetime).total_seconds() // 3600)


def _not_cancelled(assignments) -> list[Assignment]:
    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def fixed_existing_assignments(state: PlanningState) -> list[Assignment]:
    """REPLAN (arch/spec.md SECTION 7 / ASSIGN-03/04): REALIZED work and
    frozen future Assignments are untouchable; TRAINEE (S) is never created
    or moved by the solver (arch/spec.md SECTION 8) so it always passes
    through unchanged too. A PRIMARY Assignment that is PLANNED, non-frozen,
    AND covers a specific demand (covers_demand_id set) is redistributable:
    REPLAN may keep the same employee or hand that demand to someone else, so
    it is deliberately excluded here and the demand re-enters normal
    eligibility/coverage as if unassigned. A PRIMARY Assignment with no
    covers_demand_id is not "covering a demand" in the first place -- there
    is nothing for REPLAN to redistribute it relative to -- so it stays fixed
    regardless of frozen, the same as REALIZED work. CANCELLED is never
    fixed (it is not real work at all, arch/spec.md:257).

    Modeling note: S protection was originally expressed only via the
    coordinator setting frozen=True on the mentor's underlying PRIMARY
    Assignment when attaching S to it. FINDING R20-3 (tests_r20.txt) showed
    that is not sufficient by itself: ASSIGN-05 says a manual Assignment is
    NOT automatically frozen, so a mentor PRIMARY with an attached TRAINEE
    can legitimately have frozen=False, and REPLAN redistributing it away
    left the TRAINEE's mentor_primary_assignment_id pointing at an
    Assignment no longer in the candidate. A PRIMARY referenced by any
    active (non-CANCELLED) TRAINEE.mentor_primary_assignment_id is now also
    fixed, regardless of its own frozen/state -- frozen=True remains a valid
    independent way to pin it too, but is no longer the only one."""
    mentor_linked_ids = {
        assignment.mentor_primary_assignment_id
        for assignment in state.existing_assignments
        if assignment.role == AssignmentRole.TRAINEE
        and assignment.state != AssignmentState.CANCELLED
        and assignment.mentor_primary_assignment_id
    }
    fixed = []
    for assignment in state.existing_assignments:
        if assignment.state == AssignmentState.CANCELLED:
            continue
        redistributable = (
            assignment.role == AssignmentRole.PRIMARY
            and assignment.covers_demand_id is not None
            and assignment.state == AssignmentState.PLANNED
            and not assignment.frozen
            and assignment.assignment_id not in mentor_linked_ids
        )
        if not redistributable:
            fixed.append(assignment)
    return fixed


def frozen_conflict_blockers(state: PlanningState) -> list[tuple[str, str, str, str]]:
    """Diagnose fixed (non-redistributable, non-REALIZED) PRIMARY Assignments
    that currently conflict with eligibility/availability data (FINDING
    R20-2, tests_r20.txt): ASSIGN-04 blocks REPLAN from moving a frozen
    Assignment, and R20-3's mentor-link protection blocks it from moving a
    PRIMARY an active TRAINEE depends on even when frozen=False -- either way
    it is not exempt from HARD scrutiny the way REALIZED is. A fixed
    Assignment whose employee is no longer eligible (new UNAVAILABLE_24H/
    LEAVE_GRANTED/SICK_LEAVE, disabled membership, ...) is a normal autonomy
    boundary the coordinator must resolve, not a technical failure. Returns
    (employee_id, reason, demand_id, assignment_id) for every such conflict --
    assignment_id lets the caller (engine._decision_for_conflicts, FINDING
    R22-2) attribute exactly which validator violation messages are already
    explained by a diagnosed frozen conflict, instead of assuming a frozen
    conflict explains every non-LOAD-01 violation in the report."""
    demands_by_id = {d.demand_id: d for d in state.shift_demands}
    employees_by_id = {e.employee_id: e for e in state.employees}
    memberships_by_employee = {
        m.employee_id: m for m in state.memberships if m.site_id == state.site.site_id
    }
    availability_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        availability_by_employee.setdefault(record.employee_id, []).append(record)

    conflicts: list[tuple[str, str, str, str]] = []
    for assignment in fixed_existing_assignments(state):
        if assignment.state == AssignmentState.REALIZED:
            continue
        if assignment.role != AssignmentRole.PRIMARY or not assignment.covers_demand_id:
            continue
        demand = demands_by_id.get(assignment.covers_demand_id)
        employee = employees_by_id.get(assignment.employee_id)
        membership = memberships_by_employee.get(assignment.employee_id)
        if demand is None:
            continue
        if employee is None or membership is None:
            conflicts.append((assignment.employee_id, "MEMBERSHIP-01", assignment.covers_demand_id, assignment.assignment_id))
            continue
        shift_kind = classify_demand(demand, state.profile)
        result = check_eligibility(
            employee, membership, demand, shift_kind, state.profile,
            availability_by_employee.get(assignment.employee_id, []),
            list(state.external_windows), state.site.site_id,
        )
        if not result.eligible:
            conflicts.append(
                (assignment.employee_id, result.blocked_reason or "UNKNOWN", assignment.covers_demand_id, assignment.assignment_id)
            )
    return conflicts


def _already_covered_counts(state: PlanningState) -> dict[str, int]:
    """Count only fixed (REALIZED/frozen) PRIMARY coverage. A redistributable
    (PLANNED, non-frozen) PRIMARY Assignment does not count -- REPLAN may
    reassign its demand, so the demand must be re-solved, not treated as
    already satisfied (audit round 12 FINDING 1 established the CANCELLED/
    TRAINEE exclusion; REPLAN extends the same "not a fixed fact" reasoning
    to redistributable PRIMARY)."""
    counts: dict[str, int] = {}
    for assignment in fixed_existing_assignments(state):
        if assignment.role != AssignmentRole.PRIMARY or not assignment.covers_demand_id:
            continue
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


def _build_slots(
    state: PlanningState,
) -> tuple[list[SolverSlot], dict[str, int], list[str], dict[str, list[tuple[str, str]]]]:
    already_covered = _already_covered_counts(state)
    employees_by_id = {e.employee_id: e for e in state.employees}
    availability_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        availability_by_employee.setdefault(record.employee_id, []).append(record)

    slots: list[SolverSlot] = []
    still_needed: dict[str, int] = {}
    unassignable: list[str] = []
    reasons: dict[str, list[tuple[str, str]]] = {}

    for demand in state.shift_demands:
        # FINDING R19 (tests_r19.txt WYMAGA_DECYZJI, resolved by owner
        # 2026-08-12): PlanningEngine -- not the assembler -- verifies every
        # ShiftDemand matches a StandardShift, for demands already fully
        # covered by existing_assignments too. Classifying only uncovered
        # demands meant an invalid ShiftDemand could reach FEASIBLE silently
        # whenever it happened to already be covered; the invariant must hold
        # the same way regardless of coverage status.
        shift_kind = classify_demand(demand, state.profile)
        needed = demand.required_primary_count - already_covered.get(demand.demand_id, 0)
        if needed <= 0:
            continue
        still_needed[demand.demand_id] = needed
        eligible_count, eligible_ids, demand_reasons = _collect_eligible_slots(
            demand, shift_kind, state, employees_by_id, availability_by_employee, slots,
        )
        if eligible_count < needed:
            # FINDING R13-1: a pure headcount shortage (not enough eligible
            # employees for required_primary_count) is not a cross-demand
            # conflict and must not reach CP-SAT/REST-01 diagnosis at all.
            unassignable.append(demand.demand_id)
            reasons[demand.demand_id] = demand_reasons + [
                (employee_id, "INSUFFICIENT_COVERAGE") for employee_id in eligible_ids
            ]

    return slots, still_needed, unassignable, reasons


def _collect_eligible_slots(
    demand: ShiftDemand, shift_kind: ShiftKind, state: PlanningState,
    employees_by_id: dict, availability_by_employee: dict, slots: list[SolverSlot],
) -> tuple[int, list[str], list[tuple[str, str]]]:
    eligible_count = 0
    eligible_ids: list[str] = []
    reasons: list[tuple[str, str]] = []
    # FINDING R16-1: an Employee is not structurally owned by exactly one Site
    # (EMP-03), so state.memberships can legitimately contain a membership for
    # a different site. Without this filter, an other-site-only membership
    # wrongly authorized eligibility, and a multi-site Employee was iterated
    # once per membership, duplicating the same (employee_id, demand_id) CP-SAT
    # variable in the coverage constraint's term list.
    for membership in state.memberships:
        if membership.site_id != state.site.site_id:
            continue
        employee = employees_by_id.get(membership.employee_id)
        if employee is None:
            continue
        records = availability_by_employee.get(employee.employee_id, [])
        result = check_eligibility(
            employee, membership, demand, shift_kind, state.profile, records,
            list(state.external_windows), state.site.site_id,
        )
        if not result.eligible:
            reasons.append((employee.employee_id, result.blocked_reason or "UNKNOWN"))
            continue
        eligible_count += 1
        eligible_ids.append(employee.employee_id)
        day_off_soft = shift_kind == ShiftKind.N and demand.end_datetime.date() in _day_off_dates(
            state, employee.employee_id
        )
        slots.append(
            SolverSlot(employee.employee_id, demand, shift_kind, result.leave_plan_collision, day_off_soft)
        )
    # FINDING R17-2: an Employee with no membership at all for the current
    # site never enters the loop above (the R16-1 site filter skips other-site
    # memberships before check_eligibility is ever called), so no rejection
    # reason was ever recorded for them -- DECISION_REQUIRED then had
    # blockers=[] instead of a concrete MEMBERSHIP-01 entry.
    current_site_employee_ids = {
        m.employee_id for m in state.memberships if m.site_id == state.site.site_id
    }
    for employee_id in employees_by_id:
        if employee_id not in current_site_employee_ids:
            reasons.append((employee_id, "MEMBERSHIP-01"))
    return eligible_count, eligible_ids, reasons


def _fixed_intervals(state: PlanningState) -> dict[str, list[tuple[datetime, datetime]]]:
    """CANCELLED Assignments are not actual work (arch/spec.md:257) and must not
    block a replacement via REST-01/LOAD-01 (audit round 13, tests_r13.txt
    FINDING R13-2). A redistributable existing PRIMARY (REPLAN) is excluded
    the same way -- it is not a fixed fact and must not force a REST-01
    conflict against its own possible replacement; boundary/other-site
    Assignments are outside REPLAN's scope and stay fixed regardless."""
    fixed: dict[str, list[tuple[datetime, datetime]]] = {}
    for assignment in (
        *fixed_existing_assignments(state),
        *_not_cancelled(state.boundary_assignments),
        *_not_cancelled(state.other_site_assignments),
    ):
        fixed.setdefault(assignment.employee_id, []).append(
            (assignment.start_datetime, assignment.end_datetime)
        )
    return fixed


def _add_coverage_constraints(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], still_needed: dict[str, int]
) -> dict[str, object]:
    """Gate each demand's coverage constraint behind an assumption literal so an
    INFEASIBLE solve can be traced back to the minimal conflicting demand set
    (audit round 12 FINDING 3: cross-demand REST-01 conflicts must surface as
    DECISION_REQUIRED, not TECHNICAL_ERROR)."""
    by_demand: dict[str, list[SolverSlot]] = {}
    for slot in slots:
        by_demand.setdefault(slot.demand.demand_id, []).append(slot)
    assumptions: dict[str, object] = {}
    for demand_id, needed in still_needed.items():
        terms = [x[s.employee_id, demand_id] for s in by_demand.get(demand_id, [])]
        assume_var = model.new_bool_var(f"assume_{demand_id}")
        model.add(sum(terms) == needed).only_enforce_if(assume_var)
        assumptions[demand_id] = assume_var
    return assumptions


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


def _sick_leave_days_in_month(state: PlanningState) -> dict[str, int]:
    """Count active SICK_LEAVE calendar days per employee inside the current
    month only -- target_hours is a monthly figure, so a sick period spanning
    into another month must not discount days outside this one.

    FINDING R21-1 (tests_r21.txt): two active SICK_LEAVE records for the same
    employee can legitimately overlap or abut (e.g. an extension logged as a
    second record instead of editing the first) -- a shared calendar day must
    count once, not once per record. Unions per-employee calendar dates
    instead of summing each record's own day count."""
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    month_start = date(state.month.year, state.month.month, 1)
    month_end = date(state.month.year, state.month.month, num_days)
    dates_by_employee: dict[str, set] = {}
    for record in state.availability_records:
        if not record.active or record.kind != AvailabilityKind.SICK_LEAVE:
            continue
        overlap_start = max(record.start_date, month_start)
        overlap_end = min(record.end_date, month_end)
        if overlap_start > overlap_end:
            continue
        current = overlap_start
        employee_dates = dates_by_employee.setdefault(record.employee_id, set())
        while current <= overlap_end:
            employee_dates.add(current)
            current += timedelta(days=1)
    return {employee_id: len(dates) for employee_id, dates in dates_by_employee.items()}


def _add_objective(model: cp_model.CpModel, x: dict, slots: list[SolverSlot], state: PlanningState) -> None:
    # SICK_LEAVE-01 (owner decision 2026-08-12): a sick day counts as
    # SICK_LEAVE_HOURS_PER_DAY (8h) against target_hours regardless of the
    # employee's actual shift length (12h D/N) -- reduce the expected
    # monthly quota, not the worked-hours side of the deviation. Clamped at
    # 0 so a sick period longer than the original target cannot invert it
    # into a negative expectation.
    sick_days_by_employee = _sick_leave_days_in_month(state)
    target_by_employee = {
        wb.employee_id: max(0, wb.target_hours - SICK_LEAVE_HOURS_PER_DAY * sick_days_by_employee.get(wb.employee_id, 0))
        for wb in state.work_balances
    }
    # FINDING R17-5: a CANCELLED existing Assignment is not actual work
    # (arch/spec.md:257) and must not count toward the TARGET-01 objective,
    # consistent with coverage/REST-01/LOAD-01/validator filtering already
    # applied elsewhere. A redistributable PRIMARY (REPLAN) is excluded the
    # same way -- its hours are not fixed until re-solved. TRAINEE (S) is
    # not PRIMARY demand coverage and does not count toward target_hours
    # (matches validator._monthly_hours, which is also PRIMARY-only).
    fixed_hours_by_employee: dict[str, int] = {}
    for assignment in fixed_existing_assignments(state):
        if assignment.role != AssignmentRole.PRIMARY:
            continue
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
        pos = model.new_int_var(0, MAX_MONTHLY_HOURS, f"target_over_{employee_id}")
        neg = model.new_int_var(0, MAX_MONTHLY_HOURS, f"target_under_{employee_id}")
        model.add(worked - target == pos - neg)
        penalties.append(TARGET_DEVIATION_WEIGHT * (pos + neg))

    for slot in slots:
        if slot.leave_plan_collision or slot.day_off_soft_entry:
            penalties.append(SOFT_PENALTY_WEIGHT * x[slot.employee_id, slot.demand.demand_id])

    add_weekend_fairness(model, x, by_employee, _fixed_weekend_hours(state), penalties)
    holiday_dates = {cd.date for cd in state.calendar_days if cd.holiday}
    add_holiday_fairness(model, x, by_employee, holiday_dates, _historical_holiday_hours(state), penalties)

    model.minimize(sum(penalties))


def _fixed_weekend_hours(state: PlanningState) -> dict[str, int]:
    hours: dict[str, int] = {}
    for assignment in fixed_existing_assignments(state):
        if assignment.role != AssignmentRole.PRIMARY or assignment.start_datetime.weekday() < 5:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return hours


def _historical_holiday_hours(state: PlanningState) -> dict[str, int]:
    hours: dict[str, int] = {}
    for assignment in state.holiday_history:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return hours


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
    """DAY_SHIFT_OFF-01 SOFT only; LEAVE_PLAN-01 SOFT moved to
    validator._check_leave_plan (FINDING R17-4), which sees the full
    existing+solved candidate instead of only newly-solved slots -- keeping
    it here too would have duplicated the warning for solved Assignments."""
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
    return warnings


def solve(state: PlanningState, enforce_load_cap: bool = True) -> SolverOutcome:
    """Build and solve the CP-SAT model for one PlanningState. Pure mapping, no domain judgment."""
    slots, still_needed, unassignable, reasons = _build_slots(state)
    if unassignable:
        return SolverOutcome("NO_ELIGIBLE_EMPLOYEE", None, [], unassignable, reasons, [])

    model = cp_model.CpModel()
    x = {
        (s.employee_id, s.demand.demand_id): model.new_bool_var(f"x_{s.employee_id}_{s.demand.demand_id}")
        for s in slots
    }
    fixed = _fixed_intervals(state)

    assumptions = _add_coverage_constraints(model, x, slots, still_needed)
    _add_rest_constraints(model, x, slots, fixed)
    _add_load_constraints(model, x, slots, fixed, state, enforce_load_cap)
    _add_objective(model, x, slots, state)
    model.add_assumptions(list(assumptions.values()))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        conflicting = _conflicting_demand_ids(solver, status, assumptions)
        return SolverOutcome(status_name, None, [], [], {}, conflicting)

    assignments = _extract_assignments(solver, x, slots, state)
    warnings = _collect_warnings(assignments, slots)
    return SolverOutcome(status_name, assignments, warnings, [], {}, [])


def _conflicting_demand_ids(solver: cp_model.CpSolver, status: int, assumptions: dict[str, object]) -> list[str]:
    if status != cp_model.INFEASIBLE:
        return []
    core_indices = set(solver.sufficient_assumptions_for_infeasibility())
    return [demand_id for demand_id, var in assumptions.items() if var.index in core_indices]


def eligible_employees_for_demands(state: PlanningState, demand_ids: list[str]) -> list[str]:
    """Return every employee_id eligible for at least one of the given demands.

    Used by the engine to build best-effort Blocker entries for a conflicting
    demand set; this is not a proof that each listed employee is individually
    the cause, only that they are part of the candidate pool for it.
    """
    slots, _, _, _ = _build_slots(state)
    demand_id_set = set(demand_ids)
    employees = {slot.employee_id for slot in slots if slot.demand.demand_id in demand_id_set}
    return sorted(employees)


if __name__ == "__main__":
    print("solver module OK")
