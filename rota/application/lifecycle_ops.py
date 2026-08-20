"""Operation 10 (tasks/ROTA-T009/brief.md): revalidate / finalize / restore.

Revalidate/finalize never move assignments -- they refresh Deviations and
applied_rule_version_ids in place, which is not the "material assignment
correction" the owner versioning rule targets. Restore only moves the T008
current reference.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.application.assembler import assemble_planning_state, resolved_rule_version_ids
from rota.application.context import require_active_coordinator_context
from rota.application.deviation_mapping import materialize_deviations
from rota.application.errors import NoCurrentScheduleVersion, ScheduleVersionNotWorking
from rota.domain import ScheduleVersion
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import site_memory
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_version_header
from rota.planning.validator import validate
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind


def _require_current_working(conn, site_id: str, month: date) -> ScheduleVersion:
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    header = get_schedule_version_header(conn, current_id)
    if header.status.value.startswith("FINAL"):
        raise ScheduleVersionNotWorking(f"{current_id} is FINAL and cannot be revalidated in place")
    return header


def _fresh_deviations(conn, site_id: str, month: date, header: ScheduleVersion):
    """In-memory only: assembles fresh context and re-derives the complete
    current Deviation set. Callers decide separately whether/how to persist."""
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    report = validate(state, list(state.existing_assignments))
    all_rules = state.site_rules + state.unresolved_site_rules
    deviations = materialize_deviations(report.violation_details, all_rules)
    return state, deviations


def revalidate(conn, *, site_id: str, month: date, coordinator_id: str | None = None) -> ScheduleVersion:
    """R4-3-A/R5-4: the acting coordinator is whoever the caller identifies
    via coordinator_id; the version's own created_by is only a fallback for
    callers that don't (yet) supply an actor."""
    header = _require_current_working(conn, site_id, month)
    acting_coordinator_id = coordinator_id if coordinator_id is not None else header.created_by
    require_active_coordinator_context(conn, coordinator_id=acting_coordinator_id, site_id=site_id)
    state, deviations = _fresh_deviations(conn, site_id, month, header)
    return lifecycle.replace_working_snapshot(
        conn, version_id=header.version_id, applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=state.shift_demands, assignments=list(state.existing_assignments), deviations=deviations,
    )


def _finalize_action_hook(*, site_id, month, coordinator_id, header, acknowledged, acknowledged_deviation_ids, reason, responds_to_decision_required_id, recorded_at):
    target_status = "FINAL_WITH_DEVIATIONS" if acknowledged else "FINAL_NO_DEVIATIONS"

    def _hook(open_conn) -> None:
        site_memory.record_coordinator_action_no_commit(
            open_conn, action_kind=CoordinatorActionKind.SCHEDULE_FINALIZED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=header.effective_from, month=month, schedule_version_id=header.version_id,
            affected_entities=(
                [AffectedEntity("SCHEDULE_VERSION", header.version_id)]
                + [AffectedEntity("DEVIATION", d.deviation_id) for d in acknowledged]
            ),
            before_state={"status": header.status.value},
            after_state={"status": target_status, "acknowledged_deviation_ids": sorted(acknowledged_deviation_ids)},
            note=reason, source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=header.version_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        site_memory.invalidate_current_decision_required_no_commit(open_conn, site_ids=[site_id], months=[month])

    return _hook


def finalize(
    conn, *, site_id: str, month: date, coordinator_id: str, acknowledged_deviation_ids: set[str],
    acknowledged_at: datetime | None = None, reason: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> ScheduleVersion:
    """Finalize always revalidates fresh first. Succeeds only when the
    caller acknowledges the exact current (freshly re-derived) Deviation
    set. R4-1: the ONLY persisting call is the single atomic
    finalize_schedule_version(..., deviations=...), replacing the snapshot
    with acknowledged Deviations AND transitioning to FINAL in one
    transaction -- a prior two-call sequence could leave a persisted-but-
    unfinalized acknowledgement if the second call failed.

    ROTA-T019b: `reason` is also this one SCHEDULE_FINALIZED action's note
    (brief.md section 9) -- one action regardless of Deviation count."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    header = _require_current_working(conn, site_id, month)
    state, fresh_deviations = _fresh_deviations(conn, site_id, month, header)
    current_ids = {d.deviation_id for d in fresh_deviations}
    if current_ids != set(acknowledged_deviation_ids):
        raise ValueError(f"acknowledged_deviation_ids must exactly match the current Deviation set {current_ids}")
    stamp = acknowledged_at or datetime.now()
    acknowledged = [
        replace(d, acknowledged=True, acknowledged_by=coordinator_id, acknowledged_at=stamp, reason=reason)
        for d in fresh_deviations
    ]
    hook = _finalize_action_hook(
        site_id=site_id, month=month, coordinator_id=coordinator_id, header=header, acknowledged=acknowledged,
        acknowledged_deviation_ids=acknowledged_deviation_ids, reason=reason,
        responds_to_decision_required_id=responds_to_decision_required_id, recorded_at=datetime.now(),
    )
    return lifecycle.finalize_schedule_version(
        conn, version_id=header.version_id, applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=state.shift_demands, assignments=list(state.existing_assignments), deviations=acknowledged,
        on_success=hook,
    )


def restore(
    conn, *, site_id: str, month: date, coordinator_id: str, version_id: str,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    """Moves only the current reference; never deletes later history.
    Editing a restored FINAL naturally creates a new child first via the
    normal manual-correction/REPLAN entry points, which never require the
    current version to be WORKING before starting a child."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    previous_current_id = get_current_version_id(conn, site_id, month)
    recorded_at = datetime.now()

    def _hook(open_conn) -> None:
        site_memory.record_coordinator_action_no_commit(
            open_conn, action_kind=CoordinatorActionKind.SCHEDULE_RESTORED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=recorded_at.date(), month=month, schedule_version_id=version_id,
            affected_entities=[AffectedEntity("SCHEDULE_VERSION", version_id)],
            before_state={"current_version_id": previous_current_id}, after_state={"current_version_id": version_id},
            note=note, source_kind=ActionSourceKind.CURRENT_SCHEDULE_POINTER, source_id=version_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        site_memory.invalidate_current_decision_required_no_commit(open_conn, site_ids=[site_id], months=[month])

    lifecycle.restore_schedule_version(conn, site_id=site_id, month=month, version_id=version_id, on_success=_hook)
