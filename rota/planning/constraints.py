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
from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from rota.domain import Assignment, AssignmentState, ShiftCatalogKind
from rota.planning.eligibility import is_all_24h_profile
from rota.planning.timeutil import overlap_hours, rolling_windows
from rota.planning.work_periods import (
    PeriodComponent,
    WorkPeriod,
    find_cross_month_pair_candidates,
    find_same_month_pair_candidates,
    group_into_periods,
    violates_rest,
)


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
) -> tuple[dict[str, list[WorkPeriod]], frozenset[tuple[str | None, str]]]:
    """REST-01 counterpart of build_fixed_intervals: same source Assignments,
    grouped into WorkPeriods by (employee_id, work_period_id) so a fixed
    24h pair (same-site, same-month or a persisted boundary period) is one
    period with its own terminal-component rest, not two independent 12h
    facts. Also returns the (schedule_version_id, assignment_id) keys drawn
    from other_site_assignments only, so callers can tell a genuinely
    other-Site fixed period apart for CROSS-SITE-ZERO-GAP-01 (T022,
    OWNER-T022-03) without inventing a travel model or Assignment.site_id."""
    other_site_list = _not_cancelled(other_site_assignments)
    other_site_keys = frozenset((a.schedule_version_id, a.assignment_id) for a in other_site_list)
    components = [
        PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id)
        for a in (*fixed_assignments, *_not_cancelled(boundary_assignments), *other_site_list)
    ]
    by_employee: dict[str, list[WorkPeriod]] = {}
    for period in group_into_periods(components):
        by_employee.setdefault(period.employee_id, []).append(period)
    return by_employee, other_site_keys


def _is_other_site_period(period: WorkPeriod, other_site_keys: frozenset) -> bool:
    return bool(period.component_keys) and all(k in other_site_keys for k in period.component_keys)


def _demand_periods(
    employee_id: str, employee_slots: list, site_id: str, cross_month_by_demand: dict | None = None,
) -> list[WorkPeriod]:
    # Site-scoped to match the id a real solved Assignment for this
    # occurrence would get (solver._solved_work_period_id) -- so a
    # prospective period here and an already-fixed period for the SAME
    # occurrence's other half (same site, same template) compare equal and
    # are recognized as one period, not two independently-rest-checked ones.
    # ROTA-T012 Part C: a demand named in cross_month_by_demand instead
    # reuses the persisted boundary work_period_id/terminal rest, so it
    # compares equal to that FIXED period below and skips its own rest check.
    cross_month_by_demand = cross_month_by_demand or {}
    components = []
    for s in employee_slots:
        override = cross_month_by_demand.get(s.demand.demand_id)
        if override is not None:
            period_id, rest = override.boundary_work_period_id, override.rest_hours
        else:
            period_id = f"{site_id}:{s.demand.work_period_template_id}" if s.demand.work_period_template_id else None
            rest = s.demand.required_rest_hours
        components.append(PeriodComponent(s.demand.demand_id, employee_id, s.demand.start_datetime, s.demand.end_datetime, period_id, rest))
    return group_into_periods(components)


def add_rest_constraints(
    model: cp_model.CpModel, x: dict, slots: list, fixed_periods: dict[str, list[WorkPeriod]], site_id: str,
    same_month_by_employee: dict[str, list] | None = None, cross_month_by_employee: dict[str, dict] | None = None,
    other_site_keys: frozenset = frozenset(),
) -> dict[tuple[str, str, str], tuple]:
    """T012 Part C: same_month_by_employee/cross_month_by_employee (from
    build_emergency_pair_context) name the exact (employee, candidate) pairs
    allowed to relax REST-01 as an emergency 24h -- absent/empty means no
    emergency pairing is offered, identical to today's Part B behaviour.
    Returns pair_vars for the same-month case only (cross-month needs no
    CP-SAT decision: the boundary half is already a persisted fact).
    other_site_keys (T022, OWNER-T022-03) names which fixed_periods entries
    come from a different Site, so a zero-gap continuation onto them can be
    rejected unconditionally, never relaxed by can_work_24h or rest=0."""
    by_employee: dict[str, list] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)

    pair_vars: dict[tuple[str, str, str], tuple] = {}
    for employee_id, employee_slots in by_employee.items():
        cross_month = (cross_month_by_employee or {}).get(employee_id, {})
        periods = _demand_periods(employee_id, employee_slots, site_id, cross_month)
        # C-R16-2: a demand already consumed as a cross-month current half is
        # never also offered as a same-month pair member for this employee --
        # cross-month is unconditional (no CP-SAT choice), so the only way to
        # forbid the resulting 3-component chain is to never create the
        # competing same-month pair literal in the first place.
        relaxed = {
            frozenset((c.first_demand_id, c.second_demand_id)): c
            for c in (same_month_by_employee or {}).get(employee_id, [])
            if c.first_demand_id not in cross_month and c.second_demand_id not in cross_month
        }
        pair_vars.update(_add_one_employee_rest(model, x, employee_id, periods, relaxed, fixed_periods.get(employee_id, []), other_site_keys))
    _add_no_chain_constraints(model, pair_vars)
    return pair_vars


def _add_no_chain_constraints(model: cp_model.CpModel, pair_vars: dict[tuple[str, str, str], tuple]) -> None:
    """T012 Part C section 2: for one employee, D1+D2 and D2+D3 may not both
    be active -- caps every emergency chain at exactly 2 components without
    blocking a different employee from using either pair (PER EMPLOYEE, not
    globally per demand)."""
    touching: dict[tuple[str, str], list] = {}
    for (employee_id, first_id, second_id), (p, _rest) in pair_vars.items():
        touching.setdefault((employee_id, first_id), []).append(p)
        touching.setdefault((employee_id, second_id), []).append(p)
    for p_list in touching.values():
        if len(p_list) > 1:
            model.add(sum(p_list) <= 1)


def _create_pair_literals(model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], relaxed: dict) -> tuple[dict, dict]:
    # A period's representative CP-SAT variable is its earliest component --
    # add_same_person_24h_constraints (solver.py) already forces every
    # component of the same period to an identical value for this employee,
    # so any one component faithfully stands in for "this occurrence is
    # assigned to employee_id" here.
    pair_vars: dict[tuple[str, str, str], tuple] = {}
    candidates_by_key: dict[frozenset, tuple] = {}
    for i in range(len(periods)):
        for j in range(i + 1, len(periods)):
            rep_i, rep_j = periods[i].component_ids[0], periods[j].component_ids[0]
            candidate = relaxed.get(frozenset((rep_i, rep_j)))
            if candidate is None:
                continue
            # T012-C emergency 24h: relax to an optional pairing instead of
            # an outright block -- p can only reach 1 when both are assigned
            # (p <= x_i, p <= x_j), and forces itself to 1 whenever both are.
            p = model.new_bool_var(f"pair_{employee_id}_{rep_i}_{rep_j}")
            model.add(p <= x[employee_id, rep_i])
            model.add(p <= x[employee_id, rep_j])
            model.add(x[employee_id, rep_i] + x[employee_id, rep_j] <= 1 + p)
            pair_vars[employee_id, candidate.first_demand_id, candidate.second_demand_id] = (p, candidate.rest_hours)
            candidates_by_key[frozenset((rep_i, rep_j))] = (candidate, p)
    return pair_vars, candidates_by_key


def _periods_abut(a: WorkPeriod, b: WorkPeriod) -> bool:
    earlier, later = (a, b) if a.start <= b.start else (b, a)
    return earlier.end == later.start


def _forms_illegal_continuous_pair(a: WorkPeriod, b: WorkPeriod) -> bool:
    """T022-F4/OWNER-T022-02: two ORDINARY (non-emergency-candidate) 12h
    periods that abut with a zero gap silently total 24h continuous work
    for one employee -- illegal in a normal pass regardless of configured
    rest=0. The T012 emergency mechanism (pair literals) remains the only
    automatic route to join them; overlap is REST-01's own concern via
    violates_rest. Scoped to an exact 24h combined span so an unrelated
    zero-gap transition (e.g. INNY/other durations) is not swept in."""
    earlier, later = (a, b) if a.start <= b.start else (b, a)
    return earlier.end == later.start and (later.end - earlier.start) == timedelta(hours=24)


def _add_ordinary_period_edges(model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], candidates_by_key: dict, paired_member_p: dict) -> None:
    """C-R16-1 (part_c_emergency_24h.md section 3): ordinary standalone
    component REST stays active only while its own pair is NOT chosen. Only
    the temporally EARLIER side of a comparison ever governs a rest edge
    (Part B directionality), so only that side's pair status matters here --
    a fixed/earlier neighbour's own rest into this component is untouched."""
    for i in range(len(periods)):
        for j in range(i + 1, len(periods)):
            rep_i, rep_j = periods[i].component_ids[0], periods[j].component_ids[0]
            if frozenset((rep_i, rep_j)) in candidates_by_key:
                continue  # internal edge, already relaxed by the pair literal itself
            if not violates_rest(periods[i], periods[j]) and not _forms_illegal_continuous_pair(periods[i], periods[j]):
                continue
            earlier_rep = rep_i if periods[i].start <= periods[j].start else rep_j
            governing_p = paired_member_p.get(earlier_rep)
            constraint = model.add(x[employee_id, rep_i] + x[employee_id, rep_j] <= 1)
            if governing_p is not None:
                constraint.only_enforce_if(governing_p.Not())


def _add_merged_pair_edges(model: cp_model.CpModel, x: dict, employee_id: str, period_by_id: dict, candidates_by_key: dict, periods: list[WorkPeriod], fixed_periods_for_employee: list[WorkPeriod], other_site_keys: frozenset) -> None:
    """C-R16-1: once pair=1, the two components ARE one 24h work period
    (first.start -> second.end) whose rest (emergency_24h_rest_hours) governs
    every external edge -- not either component's own ordinary rest."""
    for candidate, p in candidates_by_key.values():
        first_period, second_period = period_by_id[candidate.first_demand_id], period_by_id[candidate.second_demand_id]
        merged = WorkPeriod(
            employee_id, f"__merged__{candidate.first_demand_id}+{candidate.second_demand_id}", first_period.start, second_period.end,
            candidate.rest_hours, (candidate.first_demand_id, candidate.second_demand_id),
        )
        member_ids = {candidate.first_demand_id, candidate.second_demand_id}
        for other in periods:
            if other.component_ids[0] in member_ids or not violates_rest(merged, other):
                continue
            model.add(x[employee_id, other.component_ids[0]] == 0).only_enforce_if(p)
        for fixed_period in fixed_periods_for_employee:
            # CROSS-SITE-ZERO-GAP-01 (T022, OWNER-T022-03): an emergency pair
            # merged into a 24h period still cannot abut a different-Site
            # fixed period with zero gap, even though the pair itself is a
            # legal same-Site 24h occurrence.
            cross_site_zero_gap = _is_other_site_period(fixed_period, other_site_keys) and _periods_abut(merged, fixed_period)
            if violates_rest(merged, fixed_period) or cross_site_zero_gap:
                model.add(x[employee_id, candidate.first_demand_id] + x[employee_id, candidate.second_demand_id] <= 1)


def _add_ordinary_fixed_edges(model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], fixed_periods_for_employee: list[WorkPeriod], paired_member_p: dict, other_site_keys: frozenset) -> None:
    for period in periods:
        rep = period.component_ids[0]
        governing_p = paired_member_p.get(rep)
        for fixed_period in fixed_periods_for_employee:
            # Same period_key = this prospective period is the still-open
            # other half of an already-fixed component of the SAME
            # occurrence (normal 24h, or a T012-C cross-month pair) -- no
            # rest check between them (WYMAGANIA REST #3);
            # add_same_person_24h_constraints ties normal 24h components to
            # the identical employee instead, and a cross-month pair's
            # earlier half is already fixed to one employee by definition.
            if period.period_key == fixed_period.period_key:
                continue
            # CROSS-SITE-ZERO-GAP-01 (T022, OWNER-T022-03): zero-time
            # continuation onto a different Site's fixed work is illegal
            # even when the earlier persisted rest is 0 and can_work_24h is
            # true -- never relaxed by an emergency pair's governing_p.
            cross_site_zero_gap = _is_other_site_period(fixed_period, other_site_keys) and _periods_abut(period, fixed_period)
            if cross_site_zero_gap:
                model.add(x[employee_id, rep] == 0)
                continue
            if not violates_rest(period, fixed_period):
                continue
            constraint = model.add(x[employee_id, rep] == 0)
            if governing_p is not None and period.start <= fixed_period.start:
                # Only the FORWARD-facing role (period is the earlier side) is
                # superseded by the merged 24h wall once paired -- a fixed
                # period BEFORE this component still governs unconditionally.
                constraint.only_enforce_if(governing_p.Not())


def _add_one_employee_rest(
    model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], relaxed: dict, fixed_periods_for_employee: list[WorkPeriod],
    other_site_keys: frozenset = frozenset(),
) -> dict[tuple[str, str, str], tuple]:
    period_by_id = {p.component_ids[0]: p for p in periods}
    pair_vars, candidates_by_key = _create_pair_literals(model, x, employee_id, periods, relaxed)
    paired_member_p: dict[str, object] = {}
    for candidate, p in candidates_by_key.values():
        paired_member_p[candidate.first_demand_id] = p
        paired_member_p[candidate.second_demand_id] = p
    _add_ordinary_period_edges(model, x, employee_id, periods, candidates_by_key, paired_member_p)
    _add_merged_pair_edges(model, x, employee_id, period_by_id, candidates_by_key, periods, fixed_periods_for_employee, other_site_keys)
    _add_ordinary_fixed_edges(model, x, employee_id, periods, fixed_periods_for_employee, paired_member_p, other_site_keys)
    return pair_vars


def build_emergency_pair_context(state, slots: list) -> tuple[dict[str, list], dict[str, dict]]:
    """T012 Part C PAIR CANDIDATE: filters the pure work_periods candidate
    lists down to (employee, candidate) combinations actually allowed to use
    them -- base slot-eligibility for every named demand, plus can_work_24h
    on a mixed profile (an all-24h profile never offers this option)."""
    if is_all_24h_profile(state.profile):
        return {}, {}
    slot_employees_by_demand: dict[str, set] = {}
    for slot in slots:
        slot_employees_by_demand.setdefault(slot.demand.demand_id, set()).add(slot.employee_id)
    can_pair = {m.employee_id for m in state.memberships if m.site_id == state.site.site_id and m.can_work_24h}

    same_month_by_employee: dict[str, list] = {}
    for candidate in find_same_month_pair_candidates(state.shift_demands):
        eligible = (
            slot_employees_by_demand.get(candidate.first_demand_id, set())
            & slot_employees_by_demand.get(candidate.second_demand_id, set())
            & can_pair
        )
        for employee_id in eligible:
            same_month_by_employee.setdefault(employee_id, []).append(candidate)

    cross_month_by_employee: dict[str, dict] = {}
    for candidate in find_cross_month_pair_candidates(
        list(state.boundary_assignments), list(state.boundary_shift_demands), list(state.shift_demands)
    ):
        if candidate.employee_id not in can_pair:
            continue
        if candidate.employee_id not in slot_employees_by_demand.get(candidate.current_demand_id, set()):
            continue
        cross_month_by_employee.setdefault(candidate.employee_id, {})[candidate.current_demand_id] = candidate
    return same_month_by_employee, cross_month_by_employee


def resolve_emergency_overrides(
    solver: cp_model.CpSolver, pair_vars: dict[tuple[str, str, str], tuple],
    cross_month_by_employee: dict[str, dict], site_id: str,
) -> dict[tuple[str, str], tuple[str, int]]:
    """After solving: (employee_id, demand_id) -> (work_period_id,
    required_rest_after_hours) for every Assignment the emergency mechanism
    actually produced -- same-month only when its pair variable solved to 1,
    cross-month unconditionally (the boundary half is already a persisted
    fact, not a decision)."""
    overrides: dict[tuple[str, str], tuple[str, int]] = {}
    for (employee_id, first_id, second_id), (p, rest_hours) in pair_vars.items():
        if not solver.value(p):
            continue
        # C-R13-1: identity MUST include site_id + employee_id + the ordered
        # demand pair -- two Sites with the same profile/date, a shared
        # employee, and identical local demand ids must never collide.
        work_period_id = f"{site_id}:emergency:{employee_id}:{first_id}+{second_id}"
        overrides[employee_id, first_id] = (work_period_id, rest_hours)
        overrides[employee_id, second_id] = (work_period_id, rest_hours)
    for employee_id, by_demand in (cross_month_by_employee or {}).items():
        for demand_id, candidate in by_demand.items():
            overrides[employee_id, demand_id] = (candidate.boundary_work_period_id, candidate.rest_hours)
    return overrides


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
