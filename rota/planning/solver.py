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

from dataclasses import dataclass, field
from datetime import timedelta

from ortools.sat.python import cp_model

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    ShiftDemand,
    ShiftKind,
)
from rota.planning.absence import EXCUSED_ABSENCE_HOURS_PER_DAY, excused_absence_days_in_month
from rota.planning.constraints import (
    add_load_constraints, add_rest_constraints, add_same_person_24h_constraints,
    build_emergency_pair_context, build_fixed_intervals, build_fixed_periods, resolve_emergency_overrides,
)
from rota.planning.eligibility import check_eligibility
from rota.planning.fairness import add_holiday_fairness, add_weekend_fairness
from rota.planning.replan_reshuffle import build_reshuffle_count_expr, redistributable_baseline_assignments
from rota.planning.shift_catalog import classify_demand
from rota.planning.site_rules import hard_rules_applicable_on
from rota.planning.state import PlanningState
from rota.planning.work_periods import resolve_required_rest

TARGET_DEVIATION_WEIGHT = 100
SOFT_PENALTY_WEIGHT = 1
SOLVER_TIME_LIMIT_SECONDS = 30.0
MAX_MONTHLY_HOURS = 744


@dataclass
class SolverSlot:
    employee_id: str
    demand: ShiftDemand
    shift_kind: ShiftKind
    leave_plan_collision: bool
    day_off_soft_entry: bool
    # T018 B4/B5: set only via a fallback-consulted exception; feeds exceptional_n_count.
    day_only_fallback_rule_version_id: str | None = None


@dataclass
class SolverOutcome:
    status_name: str
    assignments: list[Assignment] | None
    warnings: list[str]
    unassignable_demand_ids: list[str]
    unassignable_reasons: dict[str, list[tuple[str, str]]]
    conflicting_demand_ids: list[str]
    # R3-2: demand_id -> [(employee_id, rule_version_id)] for every HARD SiteRule exclusion, even on non-unassignable demands (needed for REST-01/LOAD-01 DECISION_REQUIRED provenance).
    site_rule_exclusions: dict[str, list[tuple[str, str]]]
    # T017: additional pairwise->=15%-diverse (solved, warnings) candidates found on the SAME model after the first. Empty unless the variant search ran.
    alternatives: list[tuple[list[Assignment], list[str]]] = field(default_factory=list)


def _demand_hours(demand: ShiftDemand) -> int:
    return int((demand.end_datetime - demand.start_datetime).total_seconds() // 3600)


def _not_cancelled(assignments) -> list[Assignment]:
    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def fixed_existing_assignments(state: PlanningState) -> list[Assignment]:
    """REPLAN (spec SECTION 7/ASSIGN-03/04): REALIZED/frozen untouchable, TRAINEE
    never moved. PLANNED non-frozen PRIMARY is redistributable (excluded);
    CANCELLED never fixed. A PRIMARY referenced by an active TRAINEE's
    mentor_primary_assignment_id is fixed regardless of its own state (R20-3)."""
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


def _already_covered_counts(state: PlanningState) -> dict[str, int]:
    """Count only fixed (REALIZED/frozen) PRIMARY coverage -- a redistributable
    (PLANNED, non-frozen) PRIMARY does not count, REPLAN may reassign its
    demand (round 12 FINDING 1 CANCELLED/TRAINEE exclusion, extended here)."""
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


@dataclass
class _DemandSlotResult:
    needed: int
    eligible_count: int
    eligible_ids: list[str]
    demand_reasons: list[tuple[str, str]]


def _process_demand(
    demand: ShiftDemand, state: PlanningState, already_covered: dict[str, int], employees_by_id: dict,
    availability_by_employee: dict, slots: list[SolverSlot], allow_day_only_n_fallback: bool = False,
) -> _DemandSlotResult | None:
    """One demand's worth of _build_slots's loop body. Returns None when the
    demand is already fully covered and contributes nothing further."""
    # R19 (owner 2026-08-12): classify every demand incl. already-covered ones -- an invalid ShiftDemand must not reach FEASIBLE silently just because it's already covered.
    shift_kind = classify_demand(demand, state.profile)
    needed = demand.required_primary_count - already_covered.get(demand.demand_id, 0)
    if needed <= 0:
        return None
    applicable_hard_rules = hard_rules_applicable_on(
        state.site_rules, state.site_rule_applicability, demand.start_datetime.date()
    )
    eligible_count, eligible_ids, demand_reasons = _collect_eligible_slots(
        demand, shift_kind, state, employees_by_id, availability_by_employee, slots, applicable_hard_rules,
        allow_day_only_n_fallback,
    )
    return _DemandSlotResult(needed, eligible_count, eligible_ids, demand_reasons)


def _build_slots(
    state: PlanningState, allow_day_only_n_fallback: bool = False,
) -> tuple[
    list[SolverSlot], dict[str, int], list[str], dict[str, list[tuple[str, str]]], dict[str, list[tuple[str, str]]]
]:
    already_covered = _already_covered_counts(state)
    employees_by_id = {e.employee_id: e for e in state.employees}
    availability_by_employee: dict[str, list] = {}
    for record in state.availability_records:
        availability_by_employee.setdefault(record.employee_id, []).append(record)

    # R3-2: captured for EVERY demand, not only unassignable ones -- a SiteRule can be the necessary cause of a cross-demand REST-01/LOAD-01 conflict.
    site_rule_ids = {r.rule_version_id for r in state.site_rules}
    site_rule_exclusions: dict[str, list[tuple[str, str]]] = {}

    slots: list[SolverSlot] = []
    still_needed: dict[str, int] = {}
    unassignable: list[str] = []
    reasons: dict[str, list[tuple[str, str]]] = {}

    for demand in state.shift_demands:
        result = _process_demand(
            demand, state, already_covered, employees_by_id, availability_by_employee, slots,
            allow_day_only_n_fallback,
        )
        if result is None:
            continue
        still_needed[demand.demand_id] = result.needed
        excluded_by_site_rule = [(e, r) for e, r in result.demand_reasons if r in site_rule_ids]
        if excluded_by_site_rule:
            site_rule_exclusions[demand.demand_id] = excluded_by_site_rule
        if result.eligible_count < result.needed:
            # R13-1: pure headcount shortage is not a cross-demand conflict, must not reach CP-SAT/REST-01 diagnosis.
            unassignable.append(demand.demand_id)
            reasons[demand.demand_id] = result.demand_reasons + [
                (employee_id, "INSUFFICIENT_COVERAGE") for employee_id in result.eligible_ids
            ]

    return slots, still_needed, unassignable, reasons, site_rule_exclusions


def _evaluate_membership_for_demand(
    membership, demand: ShiftDemand, shift_kind: ShiftKind, state: PlanningState,
    employee, records: list, applicable_hard_rules: list, slots: list[SolverSlot],
    allow_day_only_n_fallback: bool = False,
) -> tuple[bool, tuple[str, str] | None]:
    """One membership's worth of _collect_eligible_slots's loop body.
    SHIFT-24-01 is enforced by check_eligibility itself, not duplicated here."""
    result = check_eligibility(
        employee, membership, demand, shift_kind, state.profile, records,
        list(state.external_windows), state.site.site_id, applicable_hard_rules,
        allow_day_only_n_fallback,
    )
    if not result.eligible:
        return False, (employee.employee_id, result.blocked_reason or "UNKNOWN")
    day_off_soft = shift_kind == ShiftKind.N and demand.end_datetime.date() in _day_off_dates(state, employee.employee_id)
    slots.append(SolverSlot(
        employee.employee_id, demand, shift_kind, result.leave_plan_collision, day_off_soft,
        result.day_only_fallback_rule_version_id,
    ))
    return True, None


def _collect_eligible_slots(
    demand: ShiftDemand, shift_kind: ShiftKind, state: PlanningState,
    employees_by_id: dict, availability_by_employee: dict, slots: list[SolverSlot],
    applicable_hard_rules: list, allow_day_only_n_fallback: bool = False,
) -> tuple[int, list[str], list[tuple[str, str]]]:
    eligible_count = 0
    eligible_ids: list[str] = []
    reasons: list[tuple[str, str]] = []
    # R16-1: Employee is not owned by exactly one Site (EMP-03); filter out other-site memberships to avoid wrongly authorizing eligibility / duplicating the (employee_id, demand_id) CP-SAT var.
    for membership in state.memberships:
        if membership.site_id != state.site.site_id:
            continue
        employee = employees_by_id.get(membership.employee_id)
        if employee is None:
            continue
        records = availability_by_employee.get(employee.employee_id, [])
        became_eligible, reason = _evaluate_membership_for_demand(
            membership, demand, shift_kind, state, employee, records, applicable_hard_rules, slots,
            allow_day_only_n_fallback,
        )
        if became_eligible:
            eligible_count += 1
            eligible_ids.append(employee.employee_id)
        elif reason:
            reasons.append(reason)
    # R17-2: an Employee with no membership on this site never enters the loop above, so record MEMBERSHIP-01 for them here or DECISION_REQUIRED gets blockers=[].
    current_site_employee_ids = {
        m.employee_id for m in state.memberships if m.site_id == state.site.site_id
    }
    for employee_id in employees_by_id:
        if employee_id not in current_site_employee_ids:
            reasons.append((employee_id, "MEMBERSHIP-01"))
    return eligible_count, eligible_ids, reasons


def _add_coverage_constraints(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], still_needed: dict[str, int]
) -> dict[str, object]:
    """Gate each demand's coverage constraint behind an assumption literal so an
    INFEASIBLE solve traces back to the minimal conflicting demand set (R12-3:
    cross-demand REST-01 conflicts must surface as DECISION_REQUIRED)."""
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


def _sick_adjusted_targets(state: PlanningState) -> dict[str, int]:
    """SICK_LEAVE-01: a qualified workday counts 8h against target_hours
    regardless of shift length, clamped at 0. SICK_LEAVE only -- extending to
    LEAVE_GRANTED broke ROTA-REG-001's frozen hours; LEAVE_GRANTED gets the
    8h/day treatment only in rota/balance.py."""
    absence_days_by_employee = excused_absence_days_in_month(
        state.availability_records, state.month, kinds=(AvailabilityKind.SICK_LEAVE,),
        calendar_days=state.calendar_days,
    )
    return {
        wb.employee_id: max(0, wb.target_hours - EXCUSED_ABSENCE_HOURS_PER_DAY * absence_days_by_employee.get(wb.employee_id, 0))
        for wb in state.work_balances
    }


def _add_objective(model: cp_model.CpModel, x: dict, slots: list[SolverSlot], state: PlanningState) -> None:
    target_by_employee = _sick_adjusted_targets(state)
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
    add_holiday_fairness(model, x, by_employee, holiday_dates, _base_holiday_hours(state, holiday_dates), penalties)

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


def _fixed_holiday_hours(state: PlanningState, holiday_dates: set) -> dict[str, int]:
    """R23-1: a fixed (REALIZED/frozen/mentor-linked) PRIMARY already on a
    holiday date must count toward fairness just like historical hours do."""
    hours: dict[str, int] = {}
    for assignment in fixed_existing_assignments(state):
        if assignment.role != AssignmentRole.PRIMARY or assignment.start_datetime.date() not in holiday_dates:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return hours


def _base_holiday_hours(state: PlanningState, holiday_dates: set) -> dict[str, int]:
    """Historical + current-run fixed holiday hours combined -- the base each
    employee's newly-solved holiday hours are added to before comparing."""
    base = dict(_historical_holiday_hours(state))
    for employee_id, hours in _fixed_holiday_hours(state, holiday_dates).items():
        base[employee_id] = base.get(employee_id, 0) + hours
    return base


def _solved_work_period_id(state: PlanningState, slot: SolverSlot) -> str:
    """Deterministic site-scoped work_period_id: shared work_period_template_id
    when present (24h pair), else a standalone id from the demand_id."""
    template_id = slot.demand.work_period_template_id or slot.demand.demand_id
    return f"{state.site.site_id}:{template_id}"


def _extract_assignments(
    solver: cp_model.CpSolver, x: dict, slots: list[SolverSlot], state: PlanningState, overrides: dict | None = None,
) -> list[Assignment]:
    overrides = overrides or {}
    assignments = []
    for slot in slots:
        key = (slot.employee_id, slot.demand.demand_id)
        if solver.value(x[key]):
            # T012-C: emergency-produced Assignments reuse their pair's work_period_id/rest instead of the B default.
            work_period_id, rest_hours = overrides.get(key) or (_solved_work_period_id(state, slot), resolve_required_rest(slot.demand.required_rest_hours))
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
                    work_period_id=work_period_id,
                    required_rest_after_hours=rest_hours,
                )
            )
    return assignments


def _collect_warnings(assignments: list[Assignment], slots: list[SolverSlot]) -> list[str]:
    """DAY_SHIFT_OFF-01 SOFT only; LEAVE_PLAN-01 SOFT moved to
    validator._check_leave_plan (R17-4) to avoid duplicating the warning."""
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


def _run_solver(model: cp_model.CpModel) -> tuple[cp_model.CpSolver, int]:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(model)
    return solver, status


def _finalize(
    solver: cp_model.CpSolver, status: int, x: dict, slots: list[SolverSlot],
    state: PlanningState, assumptions: dict[str, object], site_rule_exclusions: dict[str, list[tuple[str, str]]],
    pair_vars: dict | None = None, cross_month_by_employee: dict | None = None,
) -> SolverOutcome:
    status_name = solver.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        conflicting = _conflicting_demand_ids(solver, status, assumptions)
        return SolverOutcome(status_name, None, [], [], {}, conflicting, site_rule_exclusions)
    overrides = resolve_emergency_overrides(solver, pair_vars or {}, cross_month_by_employee or {}, state.site.site_id)
    assignments = _extract_assignments(solver, x, slots, state, overrides)
    warnings = _collect_warnings(assignments, slots)
    return SolverOutcome(status_name, assignments, warnings, [], {}, [], site_rule_exclusions)


def _exceptional_n_expr(x: dict, slots: list[SolverSlot]):
    """T018 B5: sum of x[employee, demand] over slots legal only via a
    fallback-consulted exception (one assignment = one usage, B4/R1)."""
    return sum(
        x[slot.employee_id, slot.demand.demand_id]
        for slot in slots if slot.day_only_fallback_rule_version_id is not None
    )


def _candidate_signature(solver: cp_model.CpSolver, x: dict, slots: list[SolverSlot]) -> frozenset:
    """T017 canonical S(C): (demand_id, employee_id) pairs actually selected -- never assignment_id/order/work_period_id/TRAINEE/CANCELLED."""
    return frozenset((slot.demand.demand_id, slot.employee_id) for slot in slots if solver.value(x[slot.employee_id, slot.demand.demand_id]))


def _search_additional_candidates(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], state: PlanningState,
    pair_vars: dict | None, cross_month_by_employee: dict | None,
    first_solver: cp_model.CpSolver, still_needed: dict[str, int],
) -> tuple[list[tuple[list[Assignment], list[str]]], SolverOutcome | None]:
    """T017: up to 2 more pairwise->=15%-diverse variants on the SAME model --
    frozen lexicographic minima/objective already apply, a diversity cut is
    the only new HARD constraint. Returns (alternatives, override); a
    non-None override means a technical status was hit and the WHOLE result
    must fail closed (never masked as "no more variants")."""
    n = sum(still_needed.values())
    if n <= 0 or n - (k := (15 * n + 99) // 100) < 0:
        return [], None
    signature = _candidate_signature(first_solver, x, slots)
    alternatives: list[tuple[list[Assignment], list[str]]] = []
    for _ in range(2):
        model.add(sum(x[employee_id, demand_id] for demand_id, employee_id in signature) <= n - k)
        solver, status = _run_solver(model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            overrides = resolve_emergency_overrides(solver, pair_vars or {}, cross_month_by_employee or {}, state.site.site_id)
            assignments = _extract_assignments(solver, x, slots, state, overrides)
            alternatives.append((assignments, _collect_warnings(assignments, slots)))
            signature = _candidate_signature(solver, x, slots)
        elif status == cp_model.INFEASIBLE:
            break  # proof no further qualifying variant exists -- a valid, complete result
        else:
            return alternatives, SolverOutcome(solver.status_name(status), None, [], [], {}, [], {})
    return alternatives, None


def _solve_lexicographic_phases(
    model: cp_model.CpModel, x: dict, slots: list[SolverSlot], state: PlanningState,
    assumptions: dict[str, object], site_rule_exclusions: dict[str, list[tuple[str, str]]],
    pair_vars: dict | None, cross_month_by_employee: dict | None, phase_exprs: list,
    still_needed: dict[str, int], search_variants: bool = False,
) -> SolverOutcome:
    """Shared lexicographic-minimum engine for REPLAN-MIN-01 (reshuffle count) and T018 B5 (exceptional_n_count); T017 variant search runs after (search_variants)."""
    for expr in phase_exprs:
        model.minimize(expr)
        phase_solver, phase_status = _run_solver(model)
        if phase_status == cp_model.INFEASIBLE:
            # Rigorous proof, not approximation -- existing infeasibility/
            # conflict path (round 2 FINDING R2-1).
            return _finalize(phase_solver, phase_status, x, slots, state, assumptions, site_rule_exclusions, pair_vars, cross_month_by_employee)
        if phase_status != cp_model.OPTIMAL:
            # FEASIBLE/UNKNOWN/MODEL_INVALID don't PROVE this phase's
            # minimum -- fail closed to TECHNICAL_ERROR rather than freeze
            # an unproven incumbent as if it were the true minimum.
            return SolverOutcome(phase_solver.status_name(phase_status), None, [], [], {}, [], {})
        model.add(expr == round(phase_solver.value(expr)))

    _add_objective(model, x, slots, state)
    final_solver, final_status = _run_solver(model)
    outcome = _finalize(final_solver, final_status, x, slots, state, assumptions, site_rule_exclusions, pair_vars, cross_month_by_employee)
    if not search_variants or outcome.assignments is None:
        return outcome
    alternatives, override = _search_additional_candidates(
        model, x, slots, state, pair_vars, cross_month_by_employee, final_solver, still_needed,
    )
    if override is not None:
        return override
    outcome.alternatives = alternatives
    return outcome


def solve(
    state: PlanningState, enforce_load_cap: bool = True, allow_emergency_24h: bool = False,
    allow_day_only_n_fallback: bool = False,
) -> SolverOutcome:
    """Build and solve the CP-SAT model for one PlanningState. Pure mapping, no domain judgment."""
    slots, still_needed, unassignable, reasons, site_rule_exclusions = _build_slots(state, allow_day_only_n_fallback)
    if unassignable:
        return SolverOutcome("NO_ELIGIBLE_EMPLOYEE", None, [], unassignable, reasons, [], site_rule_exclusions)

    model = cp_model.CpModel()
    x = {
        (s.employee_id, s.demand.demand_id): model.new_bool_var(f"x_{s.employee_id}_{s.demand.demand_id}")
        for s in slots
    }
    fixed_assignments = fixed_existing_assignments(state)
    fixed = build_fixed_intervals(fixed_assignments, list(state.boundary_assignments), list(state.other_site_assignments))
    fixed_periods = build_fixed_periods(fixed_assignments, list(state.boundary_assignments), list(state.other_site_assignments))
    fixed_primary_by_demand: dict[str, set[str]] = {}
    for a in fixed_assignments:
        if a.role == AssignmentRole.PRIMARY and a.covers_demand_id:
            fixed_primary_by_demand.setdefault(a.covers_demand_id, set()).add(a.employee_id)

    # T012-C: candidates/eligibility are computed only when this pass allows
    # emergency 24h -- the first (normal) capped pass never even builds them.
    same_month_by_employee, cross_month_by_employee = build_emergency_pair_context(state, slots) if allow_emergency_24h else ({}, {})
    assumptions = _add_coverage_constraints(model, x, slots, still_needed)
    pair_vars = add_rest_constraints(model, x, slots, fixed_periods, state.site.site_id, same_month_by_employee, cross_month_by_employee)
    add_same_person_24h_constraints(model, x, slots, list(state.shift_demands), fixed_primary_by_demand)
    add_load_constraints(
        model, x, slots, fixed, state.month, state.profile.rolling_7d_decision_threshold_hours, enforce_load_cap
    )
    model.add_assumptions(list(assumptions.values()))

    # T018 B5: reshuffle (REPLAN-MIN-01, only when a baseline exists) always
    # precedes exceptional_n; the exceptional phase is skipped entirely when
    # allow_day_only_n_fallback is False (no exceptional slot can exist).
    phase_exprs = []
    baseline = redistributable_baseline_assignments(state)
    if baseline:
        phase_exprs.append(build_reshuffle_count_expr(x, baseline))
    if allow_day_only_n_fallback:
        phase_exprs.append(_exceptional_n_expr(x, slots))

    # T017: search variants only for a capped pass -- an uncapped Stage 4
    # candidate is always routed to LOAD DECISION_REQUIRED, never a
    # multi-candidate FEASIBLE source.
    return _solve_lexicographic_phases(
        model, x, slots, state, assumptions, site_rule_exclusions, pair_vars, cross_month_by_employee, phase_exprs,
        still_needed, search_variants=enforce_load_cap,
    )


def _conflicting_demand_ids(solver: cp_model.CpSolver, status: int, assumptions: dict[str, object]) -> list[str]:
    if status != cp_model.INFEASIBLE:
        return []
    core_indices = set(solver.sufficient_assumptions_for_infeasibility())
    return [demand_id for demand_id, var in assumptions.items() if var.index in core_indices]


def eligible_employees_for_demands(state: PlanningState, demand_ids: list[str]) -> list[str]:
    """Every employee_id eligible for >=1 given demand -- used for best-effort
    Blocker entries; not a proof any one of them is individually the cause."""
    slots, _, _, _, _ = _build_slots(state)
    demand_id_set = set(demand_ids)
    employees = {slot.employee_id for slot in slots if slot.demand.demand_id in demand_id_set}
    return sorted(employees)


if __name__ == "__main__":
    print("solver module OK")
