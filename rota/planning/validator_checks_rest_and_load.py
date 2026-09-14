"""Rest/load HARD checks split out of validator.py (2026-09 oversized-file
refactor, mechanical-only, zero behavior change): WORK_PERIOD-01, REST-01,
WEEKLY-REST-01, LOAD-01."""
from __future__ import annotations

import calendar
from datetime import timedelta
from itertools import combinations

from rota.domain import Assignment, AssignmentRole, SitePlanningRegime
from rota.planning.state import PlanningState
from rota.planning.timeutil import overlap_hours, rolling_windows
from rota.planning.work_periods import (
    WEEKLY_REST_REQUIRED_HOURS,
    PeriodComponent,
    effective_required_rest_after_hours,
    find_malformed_periods,
    forms_illegal_continuous_pair,
    group_into_periods,
    max_uninterrupted_free_hours,
    periods_overlap,
    weekly_settlement_windows,
)
from rota.planning.validator_shared import ViolationDetail, _by_employee, _not_cancelled


def _check_rest(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str]) -> float | None:
    """REST-01, per-work-period -- 24h pairs have no internal check, earlier period's rest governs, only target-touching edges count.
    ROTA-T023b sec.6/7: under OCHRONA the floor after an exact 24h target-Site WorkPeriod rises to >=24h; never applied to other-Site periods."""
    ochrona = state.site.planning_regime == SitePlanningRegime.OCHRONA
    # B-R10-3: identity is (schedule_version_id, assignment_id), not the bare local id (tests/test_audit_t009_r6.py).
    target_keys = {(a.schedule_version_id, a.assignment_id) for a in assignments}
    other_site_list = _not_cancelled(state.other_site_assignments)
    other_site_keys = {(a.schedule_version_id, a.assignment_id) for a in other_site_list}
    all_assignments = list(assignments) + other_site_list + _not_cancelled(state.boundary_assignments)
    # ROTA-T052: S1 (PERIODIC_TRAINING) still participates in overlap
    # detection below, but is exempt from the REST-01 gap requirement in
    # either direction (brief section 2 point 4) -- tracked by the real
    # (schedule_version_id, assignment_id) identity, never the bare local
    # id (R5-01 audit fix: a bare id can legally repeat across different
    # ScheduleVersions/Sites, B-R10-3/T036), and checked against
    # component_keys, not component_ids.
    periodic_training_keys = {
        (a.schedule_version_id, a.assignment_id) for a in all_assignments if a.role == AssignmentRole.PERIODIC_TRAINING
    }
    all_components = [PeriodComponent(a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id) for a in all_assignments]
    for key, ids, reasons in find_malformed_periods(all_components):
        details.append(ViolationDetail("WORK_PERIOD-01", ids, f"WORK_PERIOD-01: period {key}: {'; '.join(reasons)}"))
    min_rest = None
    for employee_id in {c.employee_id for c in all_components}:
        components = [c for c in all_components if c.employee_id == employee_id]
        # CROSS-SITE-ZERO-GAP-01 (T022-R1-5): a persisted period_id shared between a current/boundary component and
        # an other-Site component must fail closed BEFORE group_into_periods merges them into one WorkPeriod and
        # erases Site identity -- otherwise no cross-Site pair remains for the check below to see at all.
        by_period_id: dict[str, list] = {}
        for c in components:
            if c.period_id:
                by_period_id.setdefault(c.period_id, []).append(c)
        for period_id, members in by_period_id.items():
            member_keys = {(m.schedule_version_id, m.component_id) for m in members}
            if any(k in other_site_keys for k in member_keys) and any(k not in other_site_keys for k in member_keys):
                ids = tuple(m.component_id for m in members)
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} work_period_id {period_id!r} is shared across different Sites", affected_employee_id=employee_id))
        periods = group_into_periods(components)
        # Every (target, other) pair, not only sorted neighbors (B-R10-3).
        target_periods = [p for p in periods if not target_keys.isdisjoint(p.component_keys)]
        history_periods = [p for p in periods if p not in target_periods]
        pairs = [(tp, h) for tp in target_periods for h in history_periods] + list(combinations(target_periods, 2))
        for tp, other in pairs:
            earlier, later = (tp, other) if tp.start <= other.start else (other, tp)
            ids = (earlier.component_ids[-1], later.component_ids[0])
            if periods_overlap(earlier, later):
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} overlapping assignments", affected_employee_id=employee_id))
                continue
            # OWNER 2026-09-04 (T052 correction after contract PASS): S1 no
            # longer silently skips REST-01's gap requirement -- it never
            # HARD-blocks (a coordinator placement must never be rejected
            # for this), but a real rest shortfall around S1 must be
            # reported as a SOFT warning (Paweł: "nie możemy świadomie
            # pisać programu łamiącego prawo" -- the tool must not stay
            # silent about a real labor-law rest violation just because it
            # won't block it). The zero-gap/illegal-continuous-pair check
            # stays HARD-exempt for S1: it targets a specific PRIMARY
            # 12h+12h-hiding-24h pattern, not a real rest measurement, and
            # does not apply to S1's variable-duration manual fact.
            involves_periodic_training = not periodic_training_keys.isdisjoint(earlier.component_keys) or not periodic_training_keys.isdisjoint(later.component_keys)
            if involves_periodic_training:
                gap = (later.start - earlier.end).total_seconds() / 3600
                required_rest = effective_required_rest_after_hours(earlier, ochrona=ochrona and not any(k in other_site_keys for k in earlier.component_keys))
                if gap < required_rest:
                    # ROTA-T055 R2-01: quote employee_id for MonthlyPlanning.tsx's
                    # resolveWarningText(); drop the raw assignment-id pair --
                    # meaningless to a coordinator and covered by no test.
                    warnings.append(
                        f"REST-01 SOFT: '{employee_id}': S1 narusza wymagany odpoczynek "
                        f"({gap:.1f}h < {required_rest}h)"
                    )
                continue
            # CROSS-SITE-ZERO-GAP-01 (T022, OWNER-T022-03): zero-time continuation onto a different Site is illegal regardless of configured rest/can_work_24h.
            cross_site = any(k in other_site_keys for k in earlier.component_keys) != any(k in other_site_keys for k in later.component_keys)
            if (cross_site and earlier.end == later.start) or forms_illegal_continuous_pair(earlier, later):
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} {ids[0]}->{ids[1]}: zero-gap continuous work is not permitted", affected_employee_id=employee_id))
                min_rest = 0.0 if min_rest is None else min(min_rest, 0.0)
                continue
            gap = (later.start - earlier.end).total_seconds() / 3600
            min_rest = gap if min_rest is None else min(min_rest, gap)
            required_rest = effective_required_rest_after_hours(earlier, ochrona=ochrona and not any(k in other_site_keys for k in earlier.component_keys))
            if gap < required_rest:
                details.append(ViolationDetail("REST-01", ids, f"REST-01: {employee_id} {ids[0]}->{ids[1]}: only {gap:.1f}h", affected_employee_id=employee_id))
    return min_rest


def _check_load(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> tuple[dict[str, float], dict[str, tuple], dict[str, tuple]]:
    all_assignments = list(assignments) + _not_cancelled(state.other_site_assignments) + _not_cancelled(state.boundary_assignments)
    grouped = _by_employee(all_assignments)
    num_days = calendar.monthrange(state.month.year, state.month.month)[1]
    windows = rolling_windows(state.month, num_days)
    threshold = state.profile.rolling_7d_decision_threshold_hours
    max_load: dict[str, float] = {}
    max_window: dict[str, tuple] = {}
    # R5-1: display-friendly max_window (calendar dates) can't answer real overlap for an overnight shift -- callers needing real relevance (engine._load_decision) use the datetime form below.
    max_window_datetimes: dict[str, tuple] = {}
    for employee_id, employee_assignments in grouped.items():
        worst = 0.0
        worst_window = None
        worst_window_datetimes = None
        ids = tuple(a.assignment_id for a in employee_assignments)
        for window_start, window_end in windows:
            hours = sum(overlap_hours(a.start_datetime, a.end_datetime, window_start, window_end) for a in employee_assignments)
            if hours > worst:
                worst = hours
                worst_window = (window_start.date(), (window_end - timedelta(days=1)).date())
                worst_window_datetimes = (window_start, window_end)
            if hours > threshold:
                details.append(ViolationDetail("LOAD-01", ids, f"LOAD-01: {employee_id} has {hours}h in window {window_start.date()}-{window_end.date()}"))
        max_load[employee_id] = worst
        if worst_window is not None:
            max_window[employee_id] = worst_window
            max_window_datetimes[employee_id] = worst_window_datetimes
    return max_load, max_window, max_window_datetimes


def _check_weekly_rest(
    state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail], warnings: list[str],
) -> None:
    """WEEKLY-REST-01 (ROTA-T023b sec.6/7): OCHRONA only. Per employee/complete settlement-week window
    (weekly_settlement_windows), target-Site non-CANCELLED work only (PRIMARY+TRAINEE); PASS needs >=35h free somewhere.
    Architect review A1: same-Site state.boundary_assignments (previous-month work spilling into day 1) also occupies
    time here -- matches solver's target_fixed exactly; state.other_site_assignments stays excluded (sec.7).

    OWNER 2026-09-04 (T052 correction after contract PASS): S1 still never
    HARD-blocks this HARD rule (never occupies time for the check above),
    but if adding S1's hours back in would push a week that otherwise
    clears 35h below it, that is a real labor-law rest violation the
    coordinator caused -- reported as a SOFT warning, never silently
    dropped (Paweł: the tool must not stay quiet about a real violation
    just because it won't block the save)."""
    if state.site.planning_regime != SitePlanningRegime.OCHRONA:
        return
    windows = weekly_settlement_windows(state.month)
    by_employee: dict[str, list[tuple]] = {}
    s1_intervals_by_employee: dict[str, list[tuple]] = {}
    for a in list(assignments) + _not_cancelled(state.boundary_assignments):
        # T52-07: S1 (PERIODIC_TRAINING) does not occupy time for this
        # check -- it must never interrupt/shorten the 35h weekly rest
        # window (brief section 2 point 4).
        if a.role == AssignmentRole.PERIODIC_TRAINING:
            s1_intervals_by_employee.setdefault(a.employee_id, []).append((a.start_datetime, a.end_datetime))
            continue
        by_employee.setdefault(a.employee_id, []).append((a.start_datetime, a.end_datetime))
    for employee_id, intervals in by_employee.items():
        s1_intervals = s1_intervals_by_employee.get(employee_id, [])
        for window_start, window_end in windows:
            free = max_uninterrupted_free_hours(window_start, window_end, intervals)
            week_label = f"{window_start.date()}-{(window_end - timedelta(days=1)).date()}"
            if free < WEEKLY_REST_REQUIRED_HOURS:
                ids = tuple(
                    a.assignment_id for a in assignments
                    if a.employee_id == employee_id and a.start_datetime < window_end and a.end_datetime > window_start
                )
                details.append(ViolationDetail("WEEKLY-REST-01", ids, f"WEEKLY-REST-01: {employee_id} only {free:.1f}h uninterrupted rest in week {week_label}", affected_employee_id=employee_id))
            elif s1_intervals:
                free_with_s1 = max_uninterrupted_free_hours(window_start, window_end, intervals + s1_intervals)
                if free_with_s1 < WEEKLY_REST_REQUIRED_HOURS:
                    # ROTA-T055 R2-01: quote employee_id for resolveWarningText().
                    warnings.append(
                        f"WEEKLY-REST-01 SOFT: '{employee_id}': S1 narusza 35h nieprzerwanego odpoczynku "
                        f"w tygodniu {week_label} ({free_with_s1:.1f}h)"
                    )


if __name__ == "__main__":
    print("planning.validator_checks_rest_and_load module OK")
