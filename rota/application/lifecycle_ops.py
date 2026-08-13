"""Operation 10 (tasks/ROTA-T009/brief.md): revalidate / finalize / restore.

Revalidate/finalize never move assignments -- they refresh Deviations and
applied_rule_version_ids in place via T008's replace_working_snapshot, which
is not the "material assignment correction" the owner versioning rule
targets. Restore only moves the T008 current reference.
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
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header
from rota.planning.validator import validate


def _require_current_working(conn, site_id: str, month: date) -> str:
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    header = get_schedule_version_header(conn, current_id)
    if header.status.value.startswith("FINAL"):
        raise ScheduleVersionNotWorking(f"{current_id} is FINAL and cannot be revalidated in place")
    return current_id


def revalidate(conn, *, site_id: str, month: date) -> ScheduleVersion:
    current_id = _require_current_working(conn, site_id, month)
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    report = validate(state, list(state.existing_assignments))
    all_rules = state.site_rules + state.unresolved_site_rules
    deviations = materialize_deviations(report.violation_details, all_rules)
    return lifecycle.replace_working_snapshot(
        conn, version_id=current_id, applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=state.shift_demands, assignments=list(state.existing_assignments), deviations=deviations,
    )


def finalize(
    conn, *, site_id: str, month: date, coordinator_id: str, acknowledged_deviation_ids: set[str],
    acknowledged_at: datetime | None = None, reason: str | None = None,
) -> ScheduleVersion:
    """Finalize always revalidates fresh first. Succeeds only when the
    caller acknowledges the exact current Deviation set -- not more, not
    fewer -- then stamps acknowledged_by/at/reason before delegating to
    T008 finalization."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    revalidated = revalidate(conn, site_id=site_id, month=month)
    snapshot = get_schedule_snapshot(conn, revalidated.version_id)
    current_ids = {d.deviation_id for d in snapshot.deviations}
    if current_ids != set(acknowledged_deviation_ids):
        raise ValueError(
            f"acknowledged_deviation_ids must exactly match the current Deviation set {current_ids}"
        )
    stamp = acknowledged_at or datetime.now()
    acknowledged = [
        replace(d, acknowledged=True, acknowledged_by=coordinator_id, acknowledged_at=stamp, reason=reason)
        for d in snapshot.deviations
    ]
    lifecycle.replace_working_snapshot(
        conn, version_id=revalidated.version_id, applied_rule_version_ids=revalidated.applied_rule_version_ids,
        shift_demands=snapshot.shift_demands, assignments=snapshot.assignments, deviations=acknowledged,
    )
    return lifecycle.finalize_schedule_version(conn, version_id=revalidated.version_id)


def restore(conn, *, site_id: str, month: date, coordinator_id: str, version_id: str) -> None:
    """Moves only the current reference; never deletes later history.
    Editing a restored FINAL naturally creates a new child first via the
    normal manual-correction/REPLAN entry points, which never require the
    current version to be WORKING before starting a child."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    lifecycle.restore_schedule_version(conn, site_id=site_id, month=month, version_id=version_id)
