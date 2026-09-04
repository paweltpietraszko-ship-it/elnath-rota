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
from dataclasses import replace
from datetime import date, datetime, timedelta
from itertools import combinations

from ortools.sat.python import cp_model

from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftCatalogKind
from rota.planning.eligibility import is_all_24h_profile
from rota.planning.timeutil import overlap_hours, rolling_windows
from rota.planning.work_periods import (
    WEEKLY_REST_REQUIRED_HOURS,
    PeriodComponent,
    WorkPeriod,
    effective_required_rest_after_hours,
    find_cross_month_pair_candidates,
    find_same_month_pair_candidates,
    forms_illegal_continuous_pair,
    group_into_periods,
    periods_overlap,
    violates_rest,
    weekly_settlement_windows,
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
) -> tuple[dict[str, list[WorkPeriod]], frozenset[tuple[str | None, str]], frozenset[tuple[str | None, str]]]:
    """REST-01 counterpart of build_fixed_intervals: same source Assignments,
    grouped into WorkPeriods by (employee_id, work_period_id) so a fixed
    24h pair (same-site, same-month or a persisted boundary period) is one
    period with its own terminal-component rest, not two independent 12h
    facts. Also returns the (schedule_version_id, assignment_id) keys drawn
    from other_site_assignments only, so callers can tell a genuinely
    other-Site fixed period apart for CROSS-SITE-ZERO-GAP-01 (T022,
    OWNER-T022-03) without inventing a travel model or Assignment.site_id.

    ROTA-T052 (R4-01 audit fix, R5-01 audit fix): also returns the real
    (schedule_version_id, assignment_id) identity of every PERIODIC_TRAINING
    (S1) assignment among these -- S1 is a fixed fact (never redistributable,
    solver.fixed_existing_assignments already keeps it untouched) but must
    not act as a REST-01 wall in either direction, only as real overlap.
    Never the bare local id: it can legally repeat across different
    ScheduleVersions/Sites (B-R10-3/T036), and a collision there previously
    let one employee's S1 accidentally exempt an unrelated employee's
    ordinary PRIMARY from REST-01. WorkPeriod itself carries no role, so
    callers use this set (matched against component_keys, never
    component_ids) to tell which fixed periods are really S1."""
    other_site_list = _not_cancelled(other_site_assignments)
    other_site_keys = frozenset((a.schedule_version_id, a.assignment_id) for a in other_site_list)
    all_fixed = (*fixed_assignments, *_not_cancelled(boundary_assignments), *other_site_list)
    periodic_training_ids = frozenset(
        (a.schedule_version_id, a.assignment_id) for a in all_fixed if a.role == AssignmentRole.PERIODIC_TRAINING
    )
    components = [
        PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id)
        for a in all_fixed
    ]
    by_employee: dict[str, list[WorkPeriod]] = {}
    for period in group_into_periods(components):
        by_employee.setdefault(period.employee_id, []).append(period)
    return by_employee, other_site_keys, periodic_training_ids


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
    other_site_keys: frozenset = frozenset(), ochrona: bool = False, periodic_training_ids: frozenset = frozenset(),
) -> dict[tuple[str, str, str], tuple]:
    """T012 Part C: same_month_by_employee/cross_month_by_employee (from
    build_emergency_pair_context) name the exact (employee, candidate) pairs
    allowed to relax REST-01 as an emergency 24h -- absent/empty means no
    emergency pairing is offered, identical to today's Part B behaviour.
    Returns pair_vars for the same-month case only (cross-month needs no
    CP-SAT decision: the boundary half is already a persisted fact).
    other_site_keys (T022, OWNER-T022-03) names which fixed_periods entries
    come from a different Site, so a zero-gap continuation onto them can be
    rejected unconditionally, never relaxed by can_work_24h or rest=0.

    ochrona (ROTA-T023b, frozen addendum section 6/7): raises the
    effective rest floor to >=24h after an exact 24h target-Site
    WorkPeriod (both existing T012 forms). Never applied to an
    other-Site fixed period."""
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
        pair_vars.update(_add_one_employee_rest(
            model, x, employee_id, periods, relaxed, fixed_periods.get(employee_id, []), other_site_keys, ochrona=ochrona,
            periodic_training_ids=periodic_training_ids,
        ))
    _add_no_chain_constraints(model, pair_vars)
    return pair_vars


def _apply_ochrona_floor(
    periods: list[WorkPeriod], *, ochrona: bool, other_site_keys: frozenset = frozenset(),
) -> list[WorkPeriod]:
    """ROTA-T023b (frozen addendum section 6/7): raises each target-Site
    exact-24h period's effective rest to >=24h under OCHRONA. An
    other-Site period is left untouched (section 7)."""
    if not ochrona:
        return periods
    return [
        p if _is_other_site_period(p, other_site_keys)
        else replace(p, required_rest_after_hours=effective_required_rest_after_hours(p, ochrona=True))
        for p in periods
    ]


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
            if not violates_rest(periods[i], periods[j]) and not forms_illegal_continuous_pair(periods[i], periods[j]):
                continue
            earlier_rep = rep_i if periods[i].start <= periods[j].start else rep_j
            governing_p = paired_member_p.get(earlier_rep)
            constraint = model.add(x[employee_id, rep_i] + x[employee_id, rep_j] <= 1)
            if governing_p is not None:
                constraint.only_enforce_if(governing_p.Not())


def _add_merged_pair_edges(
    model: cp_model.CpModel, x: dict, employee_id: str, period_by_id: dict, candidates_by_key: dict,
    periods: list[WorkPeriod], fixed_periods_for_employee: list[WorkPeriod], other_site_keys: frozenset,
    ochrona: bool = False, periodic_training_ids: frozenset = frozenset(),
) -> None:
    """C-R16-1: once pair=1, the two components ARE one 24h work period
    (first.start -> second.end) whose rest (emergency_24h_rest_hours) governs
    every external edge -- not either component's own ordinary rest.

    ochrona (ROTA-T023b): the merged pair is exactly a 24h target-Site
    period, so its effective rest also gets the >=24h floor."""
    for candidate, p in candidates_by_key.values():
        first_period, second_period = period_by_id[candidate.first_demand_id], period_by_id[candidate.second_demand_id]
        merged = WorkPeriod(
            employee_id, f"__merged__{candidate.first_demand_id}+{candidate.second_demand_id}", first_period.start, second_period.end,
            candidate.rest_hours, (candidate.first_demand_id, candidate.second_demand_id),
        )
        merged = replace(merged, required_rest_after_hours=effective_required_rest_after_hours(merged, ochrona=ochrona))
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
            if _rest_conflict(merged, fixed_period, periodic_training_ids) or cross_site_zero_gap:
                model.add(x[employee_id, candidate.first_demand_id] + x[employee_id, candidate.second_demand_id] <= 1)


def _add_ordinary_fixed_edges(
    model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], fixed_periods_for_employee: list[WorkPeriod],
    paired_member_p: dict, other_site_keys: frozenset, periodic_training_ids: frozenset = frozenset(),
) -> None:
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
            if not _rest_conflict(period, fixed_period, periodic_training_ids):
                continue
            constraint = model.add(x[employee_id, rep] == 0)
            if governing_p is not None and period.start <= fixed_period.start:
                # Only the FORWARD-facing role (period is the earlier side) is
                # superseded by the merged 24h wall once paired -- a fixed
                # period BEFORE this component still governs unconditionally.
                constraint.only_enforce_if(governing_p.Not())


def _add_one_employee_rest(
    model: cp_model.CpModel, x: dict, employee_id: str, periods: list[WorkPeriod], relaxed: dict, fixed_periods_for_employee: list[WorkPeriod],
    other_site_keys: frozenset = frozenset(), ochrona: bool = False, periodic_training_ids: frozenset = frozenset(),
) -> dict[tuple[str, str, str], tuple]:
    periods = _apply_ochrona_floor(periods, ochrona=ochrona)  # always target-Site (prospective demand periods)
    fixed_periods_for_employee = _apply_ochrona_floor(fixed_periods_for_employee, ochrona=ochrona, other_site_keys=other_site_keys)
    period_by_id = {p.component_ids[0]: p for p in periods}
    pair_vars, candidates_by_key = _create_pair_literals(model, x, employee_id, periods, relaxed)
    paired_member_p: dict[str, object] = {}
    for candidate, p in candidates_by_key.values():
        paired_member_p[candidate.first_demand_id] = p
        paired_member_p[candidate.second_demand_id] = p
    _add_ordinary_period_edges(model, x, employee_id, periods, candidates_by_key, paired_member_p)
    _add_merged_pair_edges(
        model, x, employee_id, period_by_id, candidates_by_key, periods, fixed_periods_for_employee, other_site_keys,
        ochrona=ochrona, periodic_training_ids=periodic_training_ids,
    )
    _add_ordinary_fixed_edges(
        model, x, employee_id, periods, fixed_periods_for_employee, paired_member_p, other_site_keys,
        periodic_training_ids=periodic_training_ids,
    )
    return pair_vars


def _rest_conflict(period: WorkPeriod, fixed_period: WorkPeriod, periodic_training_ids: frozenset) -> bool:
    """ROTA-T052 (R4-01 audit fix, R5-01 audit fix): a fixed period that is
    S1 (PERIODIC_TRAINING) never creates a REST-01 wall in either direction
    -- only real time overlap against it is still a conflict. Matched
    against component_keys ((schedule_version_id, assignment_id)), never
    the bare component_ids -- a bare local id can legally repeat across
    different ScheduleVersions/Sites (B-R10-3/T036)."""
    if not periodic_training_ids.isdisjoint(fixed_period.component_keys) or not periodic_training_ids.isdisjoint(period.component_keys):
        return periods_overlap(period, fixed_period)
    return violates_rest(period, fixed_period)


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


def _clip_to_window(start: datetime, end: datetime, window_start: datetime, window_end: datetime):
    s, e = max(start, window_start), min(end, window_end)
    return (s, e) if s < e else None


def _add_one_employee_weekly_rest(
    model: cp_model.CpModel, x: dict, employee_id: str, employee_slots: list,
    fixed_intervals: list[tuple[datetime, datetime]], window_start: datetime, window_end: datetime,
) -> None:
    """One (employee, week window) instance of WEEKLY-REST-01 -- exact CP-SAT
    encoding of the pure oracle (work_periods.max_uninterrupted_free_hours):
    at least one candidate maximal gap between anchor points (window
    boundaries + every clipped slot start/end) must be >=35h AND overlap no
    already-fixed occupied interval AND have every overlapping PROSPECTIVE
    slot unassigned."""
    fixed_clipped = [c for c in (_clip_to_window(s, e, window_start, window_end) for s, e in fixed_intervals) if c is not None]
    decision_clipped: list[tuple[datetime, datetime, str]] = []
    for slot in employee_slots:
        c = _clip_to_window(slot.demand.start_datetime, slot.demand.end_datetime, window_start, window_end)
        if c is not None:
            decision_clipped.append((c[0], c[1], slot.demand.demand_id))
    if not decision_clipped and not fixed_clipped:
        return  # nothing can occupy this window at all -- trivially satisfied
    anchors = {window_start, window_end}
    for s, e in fixed_clipped:
        anchors.add(s); anchors.add(e)  # noqa: E702
    for s, e, _ in decision_clipped:
        anchors.add(s); anchors.add(e)  # noqa: E702
    ordered_anchors = sorted(anchors)
    gap_vars = []
    # R5-1: every PAIR of anchors, not just temporally adjacent ones -- an
    # unassigned prospective slot's own start/end must not fragment a
    # genuinely longer free run into gaps that individually miss 35h.
    for a, b in combinations(ordered_anchors, 2):
        if (b - a).total_seconds() / 3600 < WEEKLY_REST_REQUIRED_HOURS:
            continue
        if any(s < b and a < e for s, e in fixed_clipped):
            continue  # permanently blocked by already-fixed target-Site work
        overlapping_demand_ids = [demand_id for s, e, demand_id in decision_clipped if s < b and a < e]
        if not overlapping_demand_ids:
            return  # this gap is free regardless of any decision -- trivially satisfied
        gap_ok = model.new_bool_var(f"weekly_gap_{employee_id}_{a.isoformat()}_{b.isoformat()}")
        occ_vars = [x[employee_id, demand_id] for demand_id in overlapping_demand_ids]
        model.add(sum(occ_vars) == 0).only_enforce_if(gap_ok)
        model.add(sum(occ_vars) >= 1).only_enforce_if(gap_ok.Not())
        gap_vars.append(gap_ok)
    # An empty gap_vars list makes add_bool_or([]) UNSAT -- correct: no
    # candidate gap of >=35h exists at all for this employee/window, so no
    # decision can ever satisfy WEEKLY-REST-01 here (already-fixed work alone
    # violates it).
    model.add_bool_or(gap_vars)


def add_weekly_rest_constraints(
    model: cp_model.CpModel, x: dict, slots: list, target_fixed: dict[str, list[tuple[datetime, datetime]]],
    month: date, ochrona: bool,
) -> None:
    """WEEKLY-REST-01 (ROTA-T023b, frozen addendum section 6/7): OCHRONA
    only -- ORDINARY Sites skip entirely. Per employee and per complete
    settlement-week window (weekly_settlement_windows), occupied time is
    only target-Site work -- target_fixed must already exclude
    state.other_site_assignments (build_fixed_intervals called with an
    empty other_site_assignments list); slots are already target-Site
    prospective decisions."""
    if not ochrona:
        return
    windows = weekly_settlement_windows(month)
    if not windows:
        return
    by_employee: dict[str, list] = {}
    for slot in slots:
        by_employee.setdefault(slot.employee_id, []).append(slot)
    # R5-1: an employee represented only by already-fixed target-Site work
    # (no prospective slot this pass) must still be checked -- iterate the
    # union, not only employees with a candidate slot.
    for employee_id in set(by_employee) | set(target_fixed):
        employee_slots = by_employee.get(employee_id, [])
        fixed_intervals = target_fixed.get(employee_id, [])
        for window_start, window_end in windows:
            _add_one_employee_weekly_rest(model, x, employee_id, employee_slots, fixed_intervals, window_start, window_end)


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


def add_max_two_consecutive_night_constraints(
    model: cp_model.CpModel, day_kind_terms: dict[str, dict], month: date,
) -> dict[tuple[str, date], tuple[object, list[str]]]:
    """NIGHT-STREAK-01 HARD (ROTA-T032, owner-corrected 2026-08-25): the same
    employee never has non-CANCELLED PRIMARY N on three consecutive start
    dates. day_kind_terms[employee_id][d] = (d_term, n_term, any_term,
    n_demand_id) is built once by the caller (solver.py) from newly-selected
    PRIMARY (x), non-CANCELLED fixed target-Site PRIMARY, and target-Site
    boundary_assignments matched to boundary_shift_demands -- the same
    source fairness.add_dn_rhythm_reward and validator._check_night_streak
    use, so all three can never disagree about what counts as N. TRAINEE,
    CANCELLED and other_site_assignments never enter day_kind_terms at all
    (built that way by the caller) and so never participate here.

    A date missing from day_kind_terms[employee_id] contributes 0 (not-N),
    matching the fixed/boundary-data-missing policy used everywhere else in
    this module (e.g. build_fixed_periods/build_fixed_intervals). Extends
    across the month boundary automatically wherever the caller already put
    a constant boundary term at a date before `month` -- no history store,
    no persistence, no special-cased look-back window here.

    Returns one assumption literal per (employee_id, window_start_date) that
    involves at least one real decision term, keyed with the window's own N
    demand_ids (for DECISION_REQUIRED diagnosis, mirroring
    _add_coverage_constraints) -- a window built entirely from fixed/
    boundary constants is enforced unconditionally instead (nothing for a
    coordinator to decide if it is ever inconsistent; that is an anti-drift
    validator concern like any other fixed-fact HARD conflict)."""
    num_days = calendar.monthrange(month.year, month.month)[1]
    month_start = date(month.year, month.month, 1)
    month_end = date(month.year, month.month, num_days)
    empty = (0, 0, 0, None)
    assumptions: dict[tuple[str, date], tuple[object, list[str]]] = {}
    for employee_id, by_date in day_kind_terms.items():
        window_start = month_start - timedelta(days=2)
        last_start = month_end - timedelta(days=2)
        while window_start <= last_start:
            dates = [window_start, window_start + timedelta(days=1), window_start + timedelta(days=2)]
            entries = [by_date.get(d, empty) for d in dates]
            terms = [e[1] for e in entries]
            demand_ids = [e[3] for e in entries if e[3] is not None]
            # A term contributes at most 1 (a BoolVar, or a fixed/boundary
            # constant, both single-occurrence per employee/day in practice)
            # -- if the worst case across all three dates cannot exceed 2,
            # this window can never be violated, so it is never even a
            # candidate for the CP-SAT model: no wasted constraint, and no
            # vacuously-true assumption literal that could otherwise show up
            # in an unrelated INFEASIBLE proof's minimal core.
            worst_case = sum(t if isinstance(t, int) else 1 for t in terms)
            if worst_case <= 2:
                window_start += timedelta(days=1)
                continue
            if all(isinstance(t, int) for t in terms):
                model.add(sum(terms) <= 2)
                window_start += timedelta(days=1)
                continue
            assume_var = model.new_bool_var(f"assume_night_streak_{employee_id}_{window_start.isoformat()}")
            model.add(sum(terms) <= 2).only_enforce_if(assume_var)
            assumptions[employee_id, window_start] = (assume_var, demand_ids)
            window_start += timedelta(days=1)
    return assumptions


if __name__ == "__main__":
    print("constraints module OK")
