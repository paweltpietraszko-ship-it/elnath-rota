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
from datetime import date, datetime

from rota.application.assembler import assemble_planning_state, resolved_rule_version_ids
from rota.application.context import require_active_coordinator_context
from rota.application.deviation_mapping import materialize_deviations
from rota.application.errors import NoCurrentScheduleVersion, NotWorkedRequiresPlannedPrimary, require_real_date
from rota.domain import Assignment, AssignmentRole, AssignmentState, RuleCategory, RuleEnforcement, RuleResolution, ScheduleVersion
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.decision_ledger import record_decision_no_commit
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.planning.validator import validate
from rota.planning.work_periods import resolve_required_rest
from rota.site_memory_types import NewRuleContent


def _cloned_and_corrected(parent_assignments: tuple[Assignment, ...], upsert: list[Assignment]) -> list[Assignment]:
    by_id = {a.assignment_id: a for a in parent_assignments}
    for assignment in upsert:
        by_id[assignment.assignment_id] = assignment
    return list(by_id.values())


def _rest_override_pairs(state, corrected_assignments: list[Assignment], report) -> list[tuple[Assignment, Assignment, float, int]]:
    """ROTA-T012-D: independently re-derive each REST-01 pair's actual gap
    from the SAME data the validator saw (Assignment.end_datetime/
    required_rest_after_hours), never by parsing ViolationDetail.message.

    D-R19-2: a ViolationDetail names bare local assignment_ids, and a
    different valid ScheduleVersion (boundary or another Site) may reuse the
    same local id -- the TARGET correction's own corrected_assignments is
    always searched first (a real REST-01 pair always has at least one
    target-side member, per validator._check_rest's target/history pairing),
    and only an id absent there falls back to cross-context lookup.

    D-R19-3: the recorded required_rest_hours is the RESOLVED value
    (resolve_required_rest -- legacy None means the applied REST_MIN_HOURS
    fallback), matching what the validator actually enforced, not the raw
    (possibly None) Assignment field."""
    current_by_id = {a.assignment_id: a for a in corrected_assignments}
    context_by_id = {a.assignment_id: a for a in (*state.other_site_assignments, *state.boundary_assignments)}
    pairs = []
    for detail in report.violation_details:
        if detail.rule != "REST-01" or len(detail.assignment_ids) != 2:
            continue
        earlier = current_by_id.get(detail.assignment_ids[0]) or context_by_id.get(detail.assignment_ids[0])
        later = current_by_id.get(detail.assignment_ids[1]) or context_by_id.get(detail.assignment_ids[1])
        if earlier is None or later is None:
            continue
        gap_hours = (later.start_datetime - earlier.end_datetime).total_seconds() / 3600
        pairs.append((earlier, later, gap_hours, resolve_required_rest(earlier.required_rest_after_hours)))
    return pairs


def _rest_override_rule_content(child_id: str, pairs: list[tuple[Assignment, Assignment, float, int]]) -> tuple[str, str, NewRuleContent, date]:
    """T012 REST OVERRIDE AUDIT RECORD (arch/spec.md): CONFIRMED_EXCEPTION,
    INFORMATIONAL, RESOLVED -- never executable, never in this child's
    applied_rule_version_ids (created only inside on_success, after that
    list was already computed)."""
    employee_ids = sorted({earlier.employee_id for earlier, _, _, _ in pairs})
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
    }
    statement = (
        f"Manual correction {child_id} knowingly overrides REST-01 for {len(pairs)} pair(s), "
        f"employees {', '.join(employee_ids)}."
    )
    rule_content = NewRuleContent(
        category=RuleCategory.CONFIRMED_EXCEPTION, rule_kind="REST_OVERRIDE_RECORD",
        structured_parameters=structured_parameters, enforcement=RuleEnforcement.INFORMATIONAL,
        resolution_status=RuleResolution.RESOLVED, effective_to=max(a.end_datetime.date() for a in all_members),
        description=None, source=None, reason=None,
    )
    return f"REST-OVERRIDE:{child_id}", statement, rule_content, min(a.start_datetime.date() for a in all_members)


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


def apply_manual_correction(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    upsert_assignments: list[Assignment], on_success=None,
) -> ScheduleVersion:
    """review_02_architect_clarification.md ATOMIC MANUAL CORRECTION FLOW,
    steps 1-11. Manual state may be saved even with a coordinator-created
    HARD violation the solver would never produce -- validation here only
    feeds Deviation materialization, it never blocks the save. Everything
    through step 8 is in-memory; step 9 is the single T008 lifecycle call
    that atomically writes the child and switches current. Never calls
    REPLAN automatically."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    require_real_date(effective_from)
    current_id = get_current_version_id(conn, site_id, month)  # step 1
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month}) to correct")
    parent_snapshot = get_schedule_snapshot(conn, current_id)

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
    rest_override = _rest_override_rule_content(child_id, rest_pairs) if rest_pairs else None
    return lifecycle.create_schedule_version(  # steps 9-10
        conn, version_id=child_id, site_id=site_id, month=month, parent_version_id=current_id,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=parent_snapshot.shift_demands, assignments=corrected_assignments, deviations=deviations,
        effective_from=effective_from,
        on_success=_with_rest_override_hook(site_id, coordinator_id, rest_override, on_success),
    )


def freeze_or_unfreeze(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    assignment_id: str, frozen: bool,
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
        upsert_assignments=[updated],
    )


def mark_not_worked(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date, assignment_id: str,
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
        upsert_assignments=[updated],
    )
