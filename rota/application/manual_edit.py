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
from rota.application.errors import NoCurrentScheduleVersion, require_real_date
from rota.domain import Assignment, AssignmentState, ScheduleVersion
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.planning.validator import validate


def _cloned_and_corrected(parent_assignments: tuple[Assignment, ...], upsert: list[Assignment]) -> list[Assignment]:
    by_id = {a.assignment_id: a for a in parent_assignments}
    for assignment in upsert:
        by_id[assignment.assignment_id] = assignment
    return list(by_id.values())


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
    return lifecycle.create_schedule_version(  # steps 9-10
        conn, version_id=child_id, site_id=site_id, month=month, parent_version_id=current_id,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=parent_snapshot.shift_demands, assignments=corrected_assignments, deviations=deviations,
        effective_from=effective_from, on_success=on_success,
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
    updated = replace(target, state=AssignmentState.CANCELLED, operational_code="NN")
    return apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[updated],
    )
