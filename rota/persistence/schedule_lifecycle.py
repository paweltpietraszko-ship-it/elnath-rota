"""ScheduleVersion write-side lifecycle (tasks/ROTA-T008/brief.md
SCHEDULEVERSION LIFECYCLE OPERATIONS): create, in-place WORKING replacement,
finalize, restore/select-current. All four are single-transaction and
delegate invariant checks to rota.persistence.schedule_validation; SQL
triggers (rota/persistence/db.py) provide the physical FINAL-immutability
backstop underneath.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from rota.domain import Assignment, AssignmentRole, Deviation, ScheduleStatus, ScheduleVersion, ShiftDemand
from rota.persistence import schedule_validation as validation
from rota.persistence.schedule_errors import (
    DuplicateScheduleVersionId,
    InvalidCurrentVersionTarget,
    MalformedScheduleSnapshot,
    NonEditableScheduleVersion,
)
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_version_header


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
        "required_primary_count) VALUES (?, ?, ?, ?, ?)",
        [(version_id, d.demand_id, d.start_datetime.isoformat(), d.end_datetime.isoformat(), d.required_primary_count)
         for d in shift_demands],
    )
    conn.executemany(
        "INSERT INTO assignments (schedule_version_id, assignment_id, employee_id, start_datetime, end_datetime, "
        "role, state, frozen, covers_demand_id, mentor_primary_assignment_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(version_id, a.assignment_id, a.employee_id, a.start_datetime.isoformat(), a.end_datetime.isoformat(),
          a.role.value, a.state.value, int(a.frozen), a.covers_demand_id, a.mentor_primary_assignment_id)
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


def _validate_content(
    conn: sqlite3.Connection, *, site_id: str, month: date, parent_version_id: str | None,
    applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand], assignments: list[Assignment],
    deviations: list[Deviation],
) -> ScheduleStatus:
    validation.validate_applied_rules(conn, site_id=site_id, applied_rule_version_ids=applied_rule_version_ids)
    demands_by_id = validation.validate_demands(month, shift_demands)
    assignments_by_id = validation.validate_assignments(conn, month, assignments, demands_by_id)
    validation.validate_deviations(conn, deviations, assignments_by_id, demands_by_id)
    validation.validate_realized_preserved(conn, parent_version_id, assignments_by_id)
    return validation.derive_working_status(deviations)


def create_schedule_version(
    conn: sqlite3.Connection, *, version_id: str, site_id: str, month: date, parent_version_id: str | None,
    created_at: datetime, created_by: str, applied_rule_version_ids: list[str], shift_demands: list[ShiftDemand],
    assignments: list[Assignment], deviations: list[Deviation], effective_from: date | None = None,
) -> ScheduleVersion:
    """Atomically create a new ScheduleVersion header+content and point the
    (site_id, month) current reference at it. If parent_version_id is set,
    every parent REALIZED Assignment must be preserved byte-for-byte (R1-2).

    effective_from (tasks/ROTA-T009/review_01_architect_clarification.md
    SCHEDULEVERSION DATES) is coordinator-supplied provenance, never derived
    by this storage primitive -- callers that omit it get NULL, matching
    legacy pre-T009 rows. The T009 application layer is responsible for
    always supplying a real value on its own coordinator-facing operations;
    this lower-level primitive stays permissive for T008-era callers."""
    with conn:
        if conn.execute("SELECT 1 FROM schedule_versions WHERE version_id = ?", (version_id,)).fetchone():
            raise DuplicateScheduleVersionId(version_id)
        validation.validate_month_is_first_of_month(month)
        validation.validate_site_and_coordinator(conn, site_id, created_by)
        validation.validate_lineage(conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=parent_version_id)
        status = _validate_content(
            conn, site_id=site_id, month=month, parent_version_id=parent_version_id,
            applied_rule_version_ids=applied_rule_version_ids, shift_demands=shift_demands,
            assignments=assignments, deviations=deviations,
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
) -> ScheduleVersion:
    """Full in-place snapshot replacement of the current WORKING/
    WORKING_WITH_DEVIATIONS version. FINAL versions and non-current versions
    reject with NonEditableScheduleVersion; use create_schedule_version for a
    new child instead."""
    with conn:
        header = _require_editable_current(conn, version_id)
        status = _validate_content(
            conn, site_id=header.site_id, month=header.month,
            parent_version_id=header.parent_version_id, applied_rule_version_ids=applied_rule_version_ids,
            shift_demands=shift_demands, assignments=assignments, deviations=deviations,
        )
        _delete_content(conn, version_id)
        _insert_content(conn, version_id, applied_rule_version_ids, shift_demands, assignments, deviations)
        conn.execute("UPDATE schedule_versions SET status = ? WHERE version_id = ?", (status.value, version_id))
    return get_schedule_version_header(conn, version_id)


def finalize_schedule_version(conn: sqlite3.Connection, *, version_id: str) -> ScheduleVersion:
    """One-way transition WORKING(_WITH_DEVIATIONS) -> FINAL_*; every
    Deviation on the version must already be acknowledged."""
    with conn:
        _require_editable_current(conn, version_id)
        rows = conn.execute("SELECT acknowledged FROM deviations WHERE schedule_version_id = ?", (version_id,)).fetchall()
        if any(not acknowledged for (acknowledged,) in rows):
            raise MalformedScheduleSnapshot(f"{version_id}: all Deviations must be acknowledged before finalization")
        target = ScheduleStatus.FINAL_WITH_DEVIATIONS if rows else ScheduleStatus.FINAL_NO_DEVIATIONS
        conn.execute("UPDATE schedule_versions SET status = ? WHERE version_id = ?", (target.value, version_id))
    return get_schedule_version_header(conn, version_id)


def restore_schedule_version(conn: sqlite3.Connection, *, site_id: str, month: date, version_id: str) -> None:
    """Move the (site_id, month) current reference to version_id (any prior
    version, including a FINAL one already superseded) without deleting or
    altering any ScheduleVersion's content."""
    with conn:
        header = get_schedule_version_header(conn, version_id)
        if header.site_id != site_id or header.month != month:
            raise InvalidCurrentVersionTarget(f"{version_id} does not belong to ({site_id}, {month})")
        _set_current_reference(conn, site_id, month, version_id)


if __name__ == "__main__":
    print("persistence.schedule_lifecycle module OK")
