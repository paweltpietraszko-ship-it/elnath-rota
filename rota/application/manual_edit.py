"""Operation 8 (tasks/ROTA-T009/brief.md + review_01/review_02
clarifications): manual schedule edit + validation, via the atomic manual
correction flow. Covers add/edit/cancel PRIMARY, split coverage, coverage
gap repair, add/edit/cancel TRAINEE, and freeze/unfreeze -- all through one
small "supply the corrected Assignment objects" mechanism, matched by
assignment_id against the cloned parent snapshot, rather than a separate
class per button.
"""
from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta
from itertools import combinations
from typing import Optional

from rota.application.assembler import assemble_planning_state, resolved_rule_version_ids
from rota.application.context import require_active_coordinator_context
from rota.application.deviation_mapping import materialize_deviations
from rota.application.errors import NoCurrentScheduleVersion, NotWorkedRequiresPlannedPrimary, require_real_date
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ScheduleVersion,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import site_memory
from rota.persistence.decision_ledger import record_decision_no_commit
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.planning.validator import validate
from rota.planning.work_periods import (
    WEEKLY_REST_REQUIRED_HOURS,
    PeriodComponent,
    effective_required_rest_after_hours,
    forms_illegal_continuous_pair,
    group_into_periods,
    max_uninterrupted_free_hours,
    violates_rest,
    weekly_settlement_windows,
)
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind, NewRuleContent


def _cloned_and_corrected(parent_assignments: tuple[Assignment, ...], upsert: list[Assignment]) -> list[Assignment]:
    by_id = {a.assignment_id: a for a in parent_assignments}
    for assignment in upsert:
        by_id[assignment.assignment_id] = assignment
    return list(by_id.values())


def _employee_violating_pairs(
    employee_id: str, assignments: list[Assignment], target_ids: set[int], other_site_ids: set[int], *, ochrona: bool,
) -> list[tuple[Assignment, Assignment, float, int]]:
    """D-R19-2: group this employee's Assignments into WorkPeriods exactly as
    validator._check_rest does, but keyed by Python object identity (never a
    bare assignment_id string) -- a local id reused by a genuinely different
    ScheduleVersion (boundary or another Site) can never shadow or be
    shadowed, regardless of which side of the edge it is on. T022 (PH-1):
    also catches the H12+H12 zero-gap continuous-pair shape and a
    cross-Site zero-gap abutment, not only violates_rest's gap<rest test --
    mirrors validator._check_rest's own additional REST-01 triggers.

    ROTA-T023b (frozen addendum section 6/7): under OCHRONA, an exact 24h
    target-Site period's effective required rest is >=24h -- same shared
    oracle validator._check_rest uses, never a second calculation. Never
    applied when `earlier` is an other-Site period."""
    by_synthetic_id = {str(id(a)): a for a in assignments}
    components = [
        PeriodComponent(str(id(a)), employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id)
        for a in assignments
    ]
    periods = group_into_periods(components)
    target_periods = [p for p in periods if any(id(by_synthetic_id[cid]) in target_ids for cid in p.component_ids)]
    history_periods = [p for p in periods if p not in target_periods]
    candidates = [(tp, h) for tp in target_periods for h in history_periods] + list(combinations(target_periods, 2))
    pairs = []
    for tp, other in candidates:
        earlier, later = (tp, other) if tp.start <= other.start else (other, tp)
        earlier_is_other_site = any(id(by_synthetic_id[cid]) in other_site_ids for cid in earlier.component_ids)
        later_is_other_site = any(id(by_synthetic_id[cid]) in other_site_ids for cid in later.component_ids)
        cross_site = earlier_is_other_site != later_is_other_site
        zero_gap_violation = (cross_site and earlier.end == later.start) or forms_illegal_continuous_pair(earlier, later)
        effective_earlier = replace(earlier, required_rest_after_hours=effective_required_rest_after_hours(earlier, ochrona=ochrona and not earlier_is_other_site))
        if not violates_rest(effective_earlier, later) and not zero_gap_violation:
            continue
        earlier_a, later_a = by_synthetic_id[earlier.component_ids[-1]], by_synthetic_id[later.component_ids[0]]
        gap_hours = (later_a.start_datetime - earlier_a.end_datetime).total_seconds() / 3600
        pairs.append((earlier_a, later_a, gap_hours, effective_earlier.required_rest_after_hours))
    return pairs


def _rest_override_pairs(state, corrected_assignments: list[Assignment], report) -> list[tuple[Assignment, Assignment, float, int]]:
    """ROTA-T012-D: independently re-derive each REST-01 pair's actual gap
    and required rest from the SAME data the validator saw, never by parsing
    ViolationDetail.message. D-R19-3/ROTA-T023b: required_rest_hours is the
    EFFECTIVE value (work_periods.effective_required_rest_after_hours --
    the OCHRONA 24h floor when it applies, else the resolved configured
    value), matching what the validator actually enforced."""
    if not any(detail.rule == "REST-01" for detail in report.violation_details):
        return []
    ochrona = state.site.planning_regime == SitePlanningRegime.OCHRONA
    target_ids = {id(a) for a in corrected_assignments}
    other_site_ids = {id(a) for a in state.other_site_assignments}
    by_employee: dict[str, list[Assignment]] = {}
    for assignment in (*corrected_assignments, *state.other_site_assignments, *state.boundary_assignments):
        by_employee.setdefault(assignment.employee_id, []).append(assignment)
    pairs = []
    for employee_id, assignments in by_employee.items():
        pairs.extend(_employee_violating_pairs(employee_id, assignments, target_ids, other_site_ids, ochrona=ochrona))
    return pairs


def _weekly_rest_override_facts(state, corrected_assignments: list[Assignment], report) -> list[dict]:
    """ROTA-T023b: independently re-derive each WEEKLY-REST-01 violation's
    observed facts from the SAME data the validator saw, via the shared
    pure oracle (work_periods.weekly_settlement_windows/
    max_uninterrupted_free_hours) -- never a second weekly calculation,
    never parsed out of ViolationDetail.message. Mirrors
    _rest_override_pairs's own reconstruction discipline. Target-Site
    non-CANCELLED work only, matching validator._check_weekly_rest
    exactly (corrected_assignments is exactly what validate() saw) --
    architect review A1: also includes same-Site state.boundary_assignments,
    still excludes state.other_site_assignments."""
    if not any(detail.rule == "WEEKLY-REST-01" for detail in report.violation_details):
        return []
    windows = weekly_settlement_windows(state.month)
    by_employee: dict[str, list[tuple[datetime, datetime]]] = {}
    for a in list(corrected_assignments) + list(state.boundary_assignments):
        if a.state != AssignmentState.CANCELLED:
            by_employee.setdefault(a.employee_id, []).append((a.start_datetime, a.end_datetime))
    facts = []
    for employee_id, intervals in by_employee.items():
        for window_start, window_end in windows:
            free = max_uninterrupted_free_hours(window_start, window_end, intervals)
            if free < WEEKLY_REST_REQUIRED_HOURS:
                facts.append({
                    "employee_id": employee_id,
                    "week_start": window_start.date().isoformat(),
                    "week_end": (window_end - timedelta(days=1)).date().isoformat(),
                    "observed_max_uninterrupted_rest_hours": round(free, 2),
                    "required_rest_hours": WEEKLY_REST_REQUIRED_HOURS,
                })
    return facts


def _rest_override_rule_content(
    child_id: str, pairs: list[tuple[Assignment, Assignment, float, int]], weekly_facts: list[dict],
) -> tuple[str, str, NewRuleContent, date]:
    """T012/T023b REST OVERRIDE AUDIT RECORD (arch/spec.md +
    FROZEN_ADDENDUM_OCHRONA_REST_RULES_01 section 8): CONFIRMED_EXCEPTION,
    INFORMATIONAL, RESOLVED -- never executable, never in this child's
    applied_rule_version_ids. One logical child correction produces at
    most ONE such record even when it overrides both REST-01 pairs and
    WEEKLY-REST-01 facts."""
    employee_ids = sorted({earlier.employee_id for earlier, _, _, _ in pairs} | {f["employee_id"] for f in weekly_facts})
    all_members = [a for earlier, later, _, _ in pairs for a in (earlier, later)]
    structured_parameters = {
        "child_version_id": child_id,
        "affected_employee_ids": employee_ids,
        "assignment_ids": sorted({a.assignment_id for a in all_members}),
        "work_period_ids": sorted({a.work_period_id for a in all_members if a.work_period_id}),
        "rest_pairs": [
            {
                "employee_id": earlier.employee_id, "earlier_assignment_id": earlier.assignment_id,
                "later_assignment_id": later.assignment_id, "actual_gap_hours": round(gap_hours, 2),
                "required_rest_hours": required_rest_hours,
            }
            for earlier, later, gap_hours, required_rest_hours in pairs
        ],
        "weekly_rest_facts": weekly_facts,
    }
    parts = []
    if pairs:
        parts.append(f"REST-01 for {len(pairs)} pair(s)")
    if weekly_facts:
        parts.append(f"WEEKLY-REST-01 for {len(weekly_facts)} employee-week(s)")
    statement = f"Manual correction {child_id} knowingly overrides " + " and ".join(parts) + f", employees {', '.join(employee_ids)}."
    end_dates = [a.end_datetime.date() for a in all_members] + [date.fromisoformat(f["week_end"]) for f in weekly_facts]
    start_dates = [a.start_datetime.date() for a in all_members] + [date.fromisoformat(f["week_start"]) for f in weekly_facts]
    rule_content = NewRuleContent(
        category=RuleCategory.CONFIRMED_EXCEPTION, rule_kind="REST_OVERRIDE_RECORD",
        structured_parameters=structured_parameters, enforcement=RuleEnforcement.INFORMATIONAL,
        resolution_status=RuleResolution.RESOLVED, effective_to=max(end_dates),
        description=None, source=None, reason=None,
    )
    return f"REST-OVERRIDE:{child_id}", statement, rule_content, min(start_dates)


def _with_rest_override_hook(site_id: str, coordinator_id: str, rest_override, caller_on_success):
    if rest_override is None:
        return caller_on_success
    rule_id, statement, rule_content, earliest_date = rest_override

    def _hook(conn) -> None:
        record_decision_no_commit(
            conn, site_id=site_id, rule_id=rule_id, statement=statement, coordinator_id=coordinator_id,
            recorded_at=datetime.now(), effective_from=earliest_date, rel=None, rule_content=rule_content,
        )
        if caller_on_success is not None:
            caller_on_success(conn)

    return _hook


def _assignment_state(a: Assignment) -> dict:
    return {
        "schedule_version_id": a.schedule_version_id, "assignment_id": a.assignment_id, "employee_id": a.employee_id,
        "start_datetime": a.start_datetime, "end_datetime": a.end_datetime, "role": a.role.value,
        "state": a.state.value, "frozen": a.frozen, "covers_demand_id": a.covers_demand_id,
        "mentor_primary_assignment_id": a.mentor_primary_assignment_id, "operational_code": a.operational_code,
        "work_period_id": a.work_period_id, "required_rest_after_hours": a.required_rest_after_hours,
    }


def _with_manual_action_hook(
    *, action_kind: CoordinatorActionKind, site_id: str, month: date, coordinator_id: str,
    effective_from: date, parent_id: str, child_id: str, parent_snapshot_by_id: dict,
    upsert_assignments: list[Assignment],
    note: Optional[str], responds_to_decision_required_id: Optional[str], caller_on_success, extra_state=None,
):
    """ROTA-T019b: one action per apply_manual_correction call, regardless of
    any REST_OVERRIDE_RECORD hook already composed in. before/after are the
    caller-supplied changed Assignment facts (section 7.4) -- never the whole
    snapshot. extra_state (training only) runs AFTER caller_on_success so it
    can read the just-written derived readiness fact (section 19)."""
    recorded_at = datetime.now()

    def _hook(conn) -> None:
        if caller_on_success is not None:
            caller_on_success(conn)
        before_facts = [
            _assignment_state(parent_snapshot_by_id[a.assignment_id])
            for a in upsert_assignments if a.assignment_id in parent_snapshot_by_id
        ]
        # R5-1: upsert_assignments still carry the PARENT's schedule_version_id
        # (built via replace() off the parent snapshot); _insert_content
        # persists them under child_id regardless, so after must reflect that.
        after_facts = [_assignment_state(replace(a, schedule_version_id=child_id)) for a in upsert_assignments]
        entities = sorted({a.employee_id for a in upsert_assignments})
        before_state = {"parent_version_id": parent_id, "assignments": before_facts}
        after_state = {"child_version_id": child_id, "assignments": after_facts}
        if extra_state is not None:
            extra_before, extra_after = extra_state(conn)
            if extra_before is not None:
                before_state.update(extra_before)
            if extra_after is not None:
                after_state.update(extra_after)
        site_memory.record_coordinator_action_no_commit(
            conn, action_kind=action_kind, origin_site_id=site_id, affected_site_ids=[site_id],
            coordinator_id=coordinator_id, recorded_at=recorded_at, effective_from=effective_from, month=month,
            schedule_version_id=child_id,
            affected_entities=(
                [AffectedEntity("EMPLOYEE", e) for e in entities]
                + [AffectedEntity("ASSIGNMENT", a.assignment_id) for a in upsert_assignments]
            ),
            before_state=before_state, after_state=after_state,
            note=note, source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=child_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        site_memory.invalidate_current_decision_required_no_commit(conn, site_ids=[site_id], months=[month])

    return _hook


def _build_correction_hook(
    *, site_id, month, coordinator_id, effective_from, parent_id, child_id, parent_snapshot_by_id, upsert_assignments,
    note, responds_to_decision_required_id, action_kind, extra_state, rest_override, on_success,
):
    hook = _with_rest_override_hook(site_id, coordinator_id, rest_override, on_success)
    return _with_manual_action_hook(
        action_kind=action_kind, site_id=site_id, month=month, coordinator_id=coordinator_id,
        effective_from=effective_from, parent_id=parent_id, child_id=child_id,
        parent_snapshot_by_id=parent_snapshot_by_id,
        upsert_assignments=upsert_assignments, note=note,
        responds_to_decision_required_id=responds_to_decision_required_id, caller_on_success=hook,
        extra_state=extra_state,
    )


def apply_manual_correction(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    upsert_assignments: list[Assignment], on_success=None, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
    _action_kind: CoordinatorActionKind = CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION,
    _extra_state=None,
) -> ScheduleVersion:
    """review_02_architect_clarification.md ATOMIC MANUAL CORRECTION FLOW,
    steps 1-11: a coordinator-created HARD violation only feeds Deviation
    materialization, never blocks the save. Never calls REPLAN automatically.
    _action_kind (ROTA-T019b, internal): freeze_or_unfreeze/mark_not_worked/
    training.mark_training_realized pass their own kind through this same
    mechanism instead of a second, generic action row."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    require_real_date(effective_from)
    current_id = get_current_version_id(conn, site_id, month)  # step 1
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month}) to correct")
    parent_snapshot = get_schedule_snapshot(conn, current_id)
    parent_snapshot_by_id = {a.assignment_id: a for a in parent_snapshot.assignments}
    corrected_assignments = _cloned_and_corrected(parent_snapshot.assignments, upsert_assignments)  # steps 4-5
    state, _ = assemble_planning_state(  # step 6
        conn, site_id=site_id, month=month, schedule_version_id=current_id,
        shift_demands=list(parent_snapshot.shift_demands), assignments=corrected_assignments, deviations=[],
    )
    report = validate(state, corrected_assignments)  # step 7
    all_rules = state.site_rules + state.unresolved_site_rules
    deviations = materialize_deviations(report.violation_details, all_rules)  # step 8

    child_id = f"SV-{uuid.uuid4().hex}"
    rest_pairs = _rest_override_pairs(state, corrected_assignments, report)
    weekly_facts = _weekly_rest_override_facts(state, corrected_assignments, report)
    rest_override = _rest_override_rule_content(child_id, rest_pairs, weekly_facts) if (rest_pairs or weekly_facts) else None
    hook = _build_correction_hook(
        site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        parent_id=current_id, child_id=child_id, parent_snapshot_by_id=parent_snapshot_by_id,
        upsert_assignments=upsert_assignments,
        note=note, responds_to_decision_required_id=responds_to_decision_required_id, action_kind=_action_kind,
        extra_state=_extra_state, rest_override=rest_override, on_success=on_success,
    )
    return lifecycle.create_schedule_version(  # steps 9-10
        conn, version_id=child_id, site_id=site_id, month=month, parent_version_id=current_id,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=parent_snapshot.shift_demands, assignments=corrected_assignments, deviations=deviations,
        effective_from=effective_from, on_success=hook,
        pre_check=lambda c: site_memory.validate_decision_required_link_no_commit(
            c, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
        ),
    )


def freeze_or_unfreeze(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    assignment_id: str, frozen: bool, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> ScheduleVersion:
    """freeze/unfreeze is the same material-correction mechanism with a
    single field changed; kept as a named entry point for callers rather
    than making them hand-build the Assignment copy themselves."""
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    snapshot = get_schedule_snapshot(conn, current_id)
    target = next(a for a in snapshot.assignments if a.assignment_id == assignment_id)
    updated = replace(target, frozen=frozen)
    return apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[updated], note=note, responds_to_decision_required_id=responds_to_decision_required_id,
        _action_kind=CoordinatorActionKind.ASSIGNMENT_FREEZE_CHANGED,
    )


def mark_not_worked(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date, assignment_id: str,
    note: Optional[str] = None, responds_to_decision_required_id: Optional[str] = None,
) -> ScheduleVersion:
    """ROTA-T010-D (part_d_nn.md): a previously PLANNED PRIMARY the employee
    did not work becomes state=CANCELLED + operational_code="NN" on the
    child version; the parent version keeps its original PLANNED row
    unchanged. Same manual-correction mechanism as freeze_or_unfreeze --
    the demand is untouched, so a normal REPLAN-free re-validation
    materializes a COVERAGE Deviation unless the coordinator also supplies
    a replacement Assignment in a later manual correction."""
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    snapshot = get_schedule_snapshot(conn, current_id)
    target = next(a for a in snapshot.assignments if a.assignment_id == assignment_id)
    if target.role != AssignmentRole.PRIMARY or target.state != AssignmentState.PLANNED:
        raise NotWorkedRequiresPlannedPrimary(
            f"assignment {assignment_id!r} is role={target.role.value} state={target.state.value}, "
            "not a PLANNED PRIMARY -- NN cannot be applied"
        )
    updated = replace(target, state=AssignmentState.CANCELLED, operational_code="NN")
    return apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[updated], note=note, responds_to_decision_required_id=responds_to_decision_required_id,
        _action_kind=CoordinatorActionKind.ASSIGNMENT_NOT_WORKED,
    )
