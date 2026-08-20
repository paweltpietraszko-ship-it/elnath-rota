"""ScheduleVersion write-side lifecycle (tasks/ROTA-T008/brief.md
SCHEDULEVERSION LIFECYCLE OPERATIONS): create, in-place WORKING replacement,
finalize, restore/select-current. All four are single-transaction and
delegate invariant checks to rota.persistence.schedule_validation; SQL
triggers (rota/persistence/db.py) provide the physical FINAL-immutability
backstop underneath.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date, datetime

from rota.domain import Assignment, AssignmentRole, Deviation, ScheduleStatus, ScheduleVersion, ShiftDemand
from rota.persistence import schedule_validation as validation
from rota.persistence.schedule_errors import (
    DuplicateScheduleVersionId,
    InvalidCurrentVersionTarget,
    MalformedScheduleSnapshot,
    NonEditableScheduleVersion,
)
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header


def _order_assignments_mentor_first(assignments: list[Assignment]) -> list[Assignment]:
    """PRIMARY rows before TRAINEE rows, so the immediate (schedule_version_id,
    mentor_primary_assignment_id) FK always finds its mentor row already
    inserted -- caller-supplied order is not guaranteed to be mentor-first."""
    return sorted(assignments, key=lambda a: a.role != AssignmentRole.PRIMARY)


def _insert_content(
    conn: sqlite3.Connection, version_id: str,
    applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand],
    assignments: list[Assignment], deviations: list[Deviation],
) -> None:
    conn.executemany(
        "INSERT INTO schedule_version_applied_rules (version_id, seq, rule_version_id) VALUES (?, ?, ?)",
        [(version_id, seq, rule_version_id) for seq, rule_version_id in enumerate(applied_rule_version_ids)],
    )
    conn.executemany(
        "INSERT INTO shift_demands (schedule_version_id, demand_id, start_datetime, end_datetime, "
        "required_primary_count, shift_kind, catalog_kind, required_rest_hours, work_period_template_id, "
        "work_period_component, emergency_24h_rest_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(version_id, d.demand_id, d.start_datetime.isoformat(), d.end_datetime.isoformat(), d.required_primary_count,
          d.shift_kind.value if d.shift_kind else None, d.catalog_kind.value if d.catalog_kind else None,
          d.required_rest_hours, d.work_period_template_id, d.work_period_component, d.emergency_24h_rest_hours)
         for d in shift_demands],
    )
    conn.executemany(
        "INSERT INTO assignments (schedule_version_id, assignment_id, employee_id, start_datetime, end_datetime, "
        "role, state, frozen, covers_demand_id, mentor_primary_assignment_id, operational_code, work_period_id, "
        "required_rest_after_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(version_id, a.assignment_id, a.employee_id, a.start_datetime.isoformat(), a.end_datetime.isoformat(),
          a.role.value, a.state.value, int(a.frozen), a.covers_demand_id, a.mentor_primary_assignment_id,
          a.operational_code, a.work_period_id, a.required_rest_after_hours)
         for a in _order_assignments_mentor_first(assignments)],
    )
    conn.executemany(
        "INSERT INTO deviations (schedule_version_id, deviation_id, category, source_reference, "
        "affected_assignment_or_employee, acknowledged, acknowledged_by, acknowledged_at, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(version_id, d.deviation_id, d.category.value, d.source_reference, d.affected_assignment_or_employee,
          int(d.acknowledged), d.acknowledged_by, d.acknowledged_at.isoformat() if d.acknowledged_at else None,
          d.reason) for d in deviations],
    )


def _delete_content(conn: sqlite3.Connection, version_id: str) -> None:
    # assignments before shift_demands: assignments.covers_demand_id has an
    # immediate FK into shift_demands, so deleting shift_demands first would
    # (correctly) be rejected while assignments still reference them.
    conn.execute("DELETE FROM schedule_version_applied_rules WHERE version_id = ?", (version_id,))
    conn.execute("DELETE FROM deviations WHERE schedule_version_id = ?", (version_id,))
    conn.execute("DELETE FROM assignments WHERE schedule_version_id = ?", (version_id,))
    conn.execute("DELETE FROM shift_demands WHERE schedule_version_id = ?", (version_id,))


def _set_current_reference(conn: sqlite3.Connection, site_id: str, month: date, version_id: str) -> None:
    conn.execute(
        """INSERT INTO current_schedule_versions (site_id, month, version_id) VALUES (?, ?, ?)
           ON CONFLICT(site_id, month) DO UPDATE SET version_id = excluded.version_id""",
        (site_id, month.isoformat(), version_id),
    )


def _nn_reference_by_id(conn: sqlite3.Connection, reference_version_id: str | None) -> dict[str, Assignment]:
    if reference_version_id is None:
        return {}
    return {a.assignment_id: a for a in get_schedule_snapshot(conn, reference_version_id).assignments}


def _validate_content(
    conn: sqlite3.Connection, *, site_id: str, month: date, parent_version_id: str | None,
    applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand], assignments: list[Assignment],
    deviations: list[Deviation], nn_reference_version_id: str | None, allow_new_nn_from_planned_primary: bool,
) -> ScheduleStatus:
    validation.validate_applied_rules(conn, site_id=site_id, applied_rule_version_ids=applied_rule_version_ids)
    demands_by_id = validation.validate_demands(month, shift_demands)
    assignments_by_id = validation.validate_assignments(conn, month, assignments, demands_by_id)
    validation.validate_deviations(conn, deviations, assignments_by_id, demands_by_id)
    validation.validate_realized_preserved(conn, parent_version_id, assignments_by_id)
    validation.validate_nn_provenance(
        assignments_by_id, _nn_reference_by_id(conn, nn_reference_version_id),
        allow_new_nn_from_planned_primary=allow_new_nn_from_planned_primary,
    )
    return validation.derive_working_status(deviations)


def create_schedule_version(
    conn: sqlite3.Connection, *, version_id: str, site_id: str, month: date, parent_version_id: str | None,
    created_at: datetime, created_by: str, applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand],
    assignments: list[Assignment], deviations: list[Deviation], effective_from: date | None = None,
    on_success: Callable[[sqlite3.Connection], None] | None = None,
) -> ScheduleVersion:
    """Atomically create a new ScheduleVersion header+content and point the
    (site_id, month) current reference at it. If parent_version_id is set,
    every parent REALIZED Assignment must be preserved byte-for-byte (R1-2).

    effective_from (tasks/ROTA-T009/review_01_architect_clarification.md
    SCHEDULEVERSION DATES) is coordinator-supplied provenance, never derived
    by this storage primitive -- callers that omit it get NULL, matching
    legacy pre-T009 rows. The T009 application layer is responsible for
    always supplying a real value on its own coordinator-facing operations;
    this lower-level primitive stays permissive for T008-era callers.

    on_success (tasks/ROTA-T009 R4-1): an optional same-transaction hook for
    a caller that must combine this write with exactly one other write (e.g.
    training.mark_training_realized's readiness update) so both commit or
    roll back together -- nested `with conn:` calls each commit
    independently in Python's sqlite3 module, so composing two already-
    wrapped writes cannot achieve this by nesting alone. Not a general
    workflow mechanism: at most one hook, called only on the success path,
    inside the same transaction as everything above."""
    with conn:
        if conn.execute("SELECT 1 FROM schedule_versions WHERE version_id = ?", (version_id,)).fetchone():
            raise DuplicateScheduleVersionId(version_id)
        validation.validate_month_is_first_of_month(month)
        validation.validate_site_and_coordinator(conn, site_id, created_by)
        validation.validate_lineage(conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=parent_version_id)
        status = _validate_content(
            conn, site_id=site_id, month=month, parent_version_id=parent_version_id,
            applied_rule_version_ids=applied_rule_version_ids, shift_demands=shift_demands,
            assignments=assignments, deviations=deviations, nn_reference_version_id=parent_version_id,
            allow_new_nn_from_planned_primary=parent_version_id is not None,
        )
        conn.execute(
            "INSERT INTO schedule_versions (version_id, site_id, month, parent_version_id, created_at, "
            "created_by, status, effective_from) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version_id, site_id, month.isoformat(), parent_version_id, created_at.isoformat(), created_by,
                status.value, effective_from.isoformat() if effective_from else None,
            ),
        )
        _insert_content(conn, version_id, applied_rule_version_ids, shift_demands, assignments, deviations)
        _set_current_reference(conn, site_id, month, version_id)
        if on_success is not None:
            on_success(conn)
    return get_schedule_version_header(conn, version_id)


def _require_editable_current(conn: sqlite3.Connection, version_id: str) -> ScheduleVersion:
    header = get_schedule_version_header(conn, version_id)
    if get_current_version_id(conn, header.site_id, header.month) != version_id:
        raise NonEditableScheduleVersion(f"{version_id} is not the current version for its Site/month")
    if header.status.value.startswith("FINAL"):
        raise NonEditableScheduleVersion(f"{version_id} is FINAL and cannot be edited")
    return header


def replace_working_snapshot(
    conn: sqlite3.Connection, *, version_id: str, applied_rule_version_ids: list[str],
    shift_demands: list[ShiftDemand], assignments: list[Assignment], deviations: list[Deviation],
    on_success: Callable[[sqlite3.Connection], None] | None = None,
) -> ScheduleVersion:
    """Full in-place snapshot replacement of the current WORKING/
    WORKING_WITH_DEVIATIONS version. FINAL versions and non-current versions
    reject with NonEditableScheduleVersion; use create_schedule_version for a
    new child instead.

    on_success (ROTA-T019b): same same-transaction hook seam as
    create_schedule_version -- default None preserves existing behavior."""
    with conn:
        header = _require_editable_current(conn, version_id)
        status = _validate_content(
            conn, site_id=header.site_id, month=header.month,
            parent_version_id=header.parent_version_id, applied_rule_version_ids=applied_rule_version_ids,
            shift_demands=shift_demands, assignments=assignments, deviations=deviations,
            nn_reference_version_id=version_id, allow_new_nn_from_planned_primary=False,
        )
        _delete_content(conn, version_id)
        _insert_content(conn, version_id, applied_rule_version_ids, shift_demands, assignments, deviations)
        conn.execute("UPDATE schedule_versions SET status = ? WHERE version_id = ?", (status.value, version_id))
        if on_success is not None:
            on_success(conn)
    return get_schedule_version_header(conn, version_id)


def _replace_content_for_finalize(
    conn: sqlite3.Connection, version_id: str, header: ScheduleVersion,
    applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand],
    assignments: list[Assignment], deviations: list[Deviation],
) -> None:
    if any(not d.acknowledged for d in deviations):
        raise MalformedScheduleSnapshot(f"{version_id}: all Deviations must be acknowledged to finalize")
    _validate_content(
        conn, site_id=header.site_id, month=header.month, parent_version_id=header.parent_version_id,
        applied_rule_version_ids=applied_rule_version_ids, shift_demands=shift_demands,
        assignments=assignments, deviations=deviations,
        nn_reference_version_id=version_id, allow_new_nn_from_planned_primary=False,
    )
    _delete_content(conn, version_id)
    _insert_content(conn, version_id, applied_rule_version_ids, shift_demands, assignments, deviations)


def finalize_schedule_version(
    conn: sqlite3.Connection, *, version_id: str,
    applied_rule_version_ids: list[str] | None = None, shift_demands: list[ShiftDemand] | None = None,
    assignments: list[Assignment] | None = None, deviations: list[Deviation] | None = None,
    on_success: Callable[[sqlite3.Connection], None] | None = None,
) -> ScheduleVersion:
    """One-way transition WORKING(_WITH_DEVIATIONS) -> FINAL_*; every
    Deviation on the version must already be acknowledged.

    tasks/ROTA-T009 R4-1: a caller (lifecycle_ops.finalize) that must both
    persist a freshly-revalidated, now-acknowledged snapshot AND flip to
    FINAL cannot do so as two separate committing calls -- the second call's
    failure would leave the first one's acknowledgement persisted with no
    FINAL transition. Supplying shift_demands/assignments/deviations here
    replaces the whole snapshot in the SAME transaction as the status
    transition; omitting them preserves the original single-purpose
    behavior (deviations already acknowledged in storage)."""
    with conn:
        header = _require_editable_current(conn, version_id)
        if shift_demands is not None:
            _replace_content_for_finalize(
                conn, version_id, header, applied_rule_version_ids, shift_demands, assignments, deviations,
            )
            has_deviations = bool(deviations)
        else:
            rows = conn.execute(
                "SELECT acknowledged FROM deviations WHERE schedule_version_id = ?", (version_id,),
            ).fetchall()
            if any(not acknowledged for (acknowledged,) in rows):
                raise MalformedScheduleSnapshot(f"{version_id}: all Deviations must be acknowledged before finalization")
            has_deviations = bool(rows)
        target = ScheduleStatus.FINAL_WITH_DEVIATIONS if has_deviations else ScheduleStatus.FINAL_NO_DEVIATIONS
        conn.execute("UPDATE schedule_versions SET status = ? WHERE version_id = ?", (target.value, version_id))
        if on_success is not None:
            on_success(conn)
    return get_schedule_version_header(conn, version_id)


def restore_schedule_version(
    conn: sqlite3.Connection, *, site_id: str, month: date, version_id: str,
    on_success: Callable[[sqlite3.Connection], None] | None = None,
) -> None:
    """Move the (site_id, month) current reference to version_id (any prior
    version, including a FINAL one already superseded) without deleting or
    altering any ScheduleVersion's content."""
    with conn:
        header = get_schedule_version_header(conn, version_id)
        if header.site_id != site_id or header.month != month:
            raise InvalidCurrentVersionTarget(f"{version_id} does not belong to ({site_id}, {month})")
        _set_current_reference(conn, site_id, month, version_id)
        if on_success is not None:
            on_success(conn)


if __name__ == "__main__":
    print("persistence.schedule_lifecycle module OK")
