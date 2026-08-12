"""Pure validation helpers for ScheduleVersion creation/replacement
(tasks/ROTA-T008/brief.md SCHEDULEVERSION IDENTITY / LINEAGE INVARIANTS,
SHIFTDEMAND/ASSIGNMENT/DEVIATION PERSISTENCE INVARIANTS, R1-1/R1-2/R1-5
clarifications). Read-only SELECTs against an already-open connection; no
writes here.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date

from rota.domain import Assignment, AssignmentRole, AssignmentState, Deviation, ScheduleStatus, ShiftDemand
from rota.persistence.schedule_errors import InvalidScheduleLineage, MalformedScheduleSnapshot, RealizedWorkAltered
from rota.persistence.schedule_repository import ScheduleVersionNotFound, get_schedule_snapshot, get_schedule_version_header


def validate_site_and_coordinator(conn: sqlite3.Connection, site_id: str, coordinator_id: str) -> None:
    if conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (site_id,)).fetchone() is None:
        raise MalformedScheduleSnapshot(f"unknown site {site_id!r}")
    if conn.execute("SELECT 1 FROM coordinators WHERE coordinator_id = ?", (coordinator_id,)).fetchone() is None:
        raise MalformedScheduleSnapshot(f"unknown coordinator {coordinator_id!r}")


def validate_lineage(
    conn: sqlite3.Connection, *, version_id: str, site_id: str, month: date, parent_version_id: str | None
) -> None:
    if parent_version_id is None:
        return
    if parent_version_id == version_id:
        raise InvalidScheduleLineage("parent_version_id cannot equal version_id")
    try:
        parent = get_schedule_version_header(conn, parent_version_id)
    except ScheduleVersionNotFound as exc:
        raise InvalidScheduleLineage(f"parent {parent_version_id!r} does not exist") from exc
    if parent.site_id != site_id or parent.month != month:
        raise InvalidScheduleLineage(
            f"parent {parent_version_id!r} belongs to ({parent.site_id}, {parent.month}), not ({site_id}, {month})"
        )


def validate_applied_rules(conn: sqlite3.Connection, *, site_id: str, applied_rule_version_ids: list[str]) -> None:
    for rule_version_id in applied_rule_version_ids:
        row = conn.execute(
            "SELECT site_id FROM site_rule_versions WHERE rule_version_id = ?", (rule_version_id,)
        ).fetchone()
        if row is None:
            raise MalformedScheduleSnapshot(f"applied rule {rule_version_id!r} does not exist")
        if row[0] != site_id:
            raise MalformedScheduleSnapshot(f"applied rule {rule_version_id!r} belongs to a different Site")


def validate_demands(month: date, shift_demands: list[ShiftDemand]) -> dict[str, ShiftDemand]:
    by_id: dict[str, ShiftDemand] = {}
    for demand in shift_demands:
        if demand.demand_id in by_id:
            raise MalformedScheduleSnapshot(f"duplicate demand_id {demand.demand_id!r}")
        if demand.end_datetime <= demand.start_datetime:
            raise MalformedScheduleSnapshot(f"demand {demand.demand_id!r}: end must be after start")
        if demand.required_primary_count <= 0:
            raise MalformedScheduleSnapshot(f"demand {demand.demand_id!r}: required_primary_count must be > 0")
        start = demand.start_datetime
        if (start.year, start.month) != (month.year, month.month):
            raise MalformedScheduleSnapshot(f"demand {demand.demand_id!r}: start date not in ScheduleVersion.month")
        by_id[demand.demand_id] = demand
    return by_id


def _validate_assignment_shape(
    conn: sqlite3.Connection, month: date, assignment: Assignment, seen: dict[str, Assignment]
) -> None:
    if assignment.assignment_id in seen:
        raise MalformedScheduleSnapshot(f"duplicate assignment_id {assignment.assignment_id!r}")
    if assignment.end_datetime <= assignment.start_datetime:
        raise MalformedScheduleSnapshot(f"assignment {assignment.assignment_id!r}: end must be after start")
    start = assignment.start_datetime
    if (start.year, start.month) != (month.year, month.month):
        raise MalformedScheduleSnapshot(f"assignment {assignment.assignment_id!r}: start date not in ScheduleVersion.month")
    if conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (assignment.employee_id,)).fetchone() is None:
        raise MalformedScheduleSnapshot(f"assignment {assignment.assignment_id!r}: unknown employee {assignment.employee_id!r}")


def _validate_assignment_references(
    assignment: Assignment, demands_by_id: dict[str, ShiftDemand], assignments_by_id: dict[str, Assignment]
) -> None:
    """R1-1 clarification: PRIMARY interval need not equal the demand
    interval -- only that covers_demand_id resolves within the same
    version. Manual splits/gaps are truthful operational state, not a
    persistence-layer COVERAGE-01 violation."""
    if assignment.role == AssignmentRole.PRIMARY:
        if not assignment.covers_demand_id or assignment.mentor_primary_assignment_id:
            raise MalformedScheduleSnapshot(f"PRIMARY {assignment.assignment_id!r}: covers_demand_id required, mentor forbidden")
        if assignment.covers_demand_id not in demands_by_id:
            raise MalformedScheduleSnapshot(f"PRIMARY {assignment.assignment_id!r}: covers_demand_id not in this version")
    elif assignment.role == AssignmentRole.TRAINEE:
        if assignment.covers_demand_id or not assignment.mentor_primary_assignment_id:
            raise MalformedScheduleSnapshot(f"TRAINEE {assignment.assignment_id!r}: mentor required, covers_demand_id forbidden")
        mentor = assignments_by_id.get(assignment.mentor_primary_assignment_id)
        if mentor is None or mentor.role != AssignmentRole.PRIMARY:
            raise MalformedScheduleSnapshot(f"TRAINEE {assignment.assignment_id!r}: mentor not a same-version PRIMARY")


def validate_assignments(conn: sqlite3.Connection, month: date, assignments: list[Assignment], demands_by_id: dict) -> dict[str, Assignment]:
    by_id: dict[str, Assignment] = {}
    for assignment in assignments:
        _validate_assignment_shape(conn, month, assignment, by_id)
        by_id[assignment.assignment_id] = assignment
    for assignment in assignments:
        _validate_assignment_references(assignment, demands_by_id, by_id)
    return by_id


def validate_deviations(
    conn: sqlite3.Connection, deviations: list[Deviation], assignments_by_id: dict[str, Assignment]
) -> None:
    seen: set[str] = set()
    for deviation in deviations:
        if deviation.deviation_id in seen:
            raise MalformedScheduleSnapshot(f"duplicate deviation_id {deviation.deviation_id!r}")
        seen.add(deviation.deviation_id)
        _validate_one_deviation(conn, deviation, assignments_by_id)


def _validate_one_deviation(conn: sqlite3.Connection, deviation: Deviation, assignments_by_id: dict) -> None:
    if not deviation.source_reference:
        raise MalformedScheduleSnapshot(f"deviation {deviation.deviation_id!r}: source_reference required")
    target = deviation.affected_assignment_or_employee
    is_employee = conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (target,)).fetchone() is not None
    if not target or (not is_employee and target not in assignments_by_id):
        raise MalformedScheduleSnapshot(
            f"deviation {deviation.deviation_id!r}: affected_assignment_or_employee must resolve to an "
            "Employee or a same-version Assignment"
        )
    if deviation.acknowledged:
        if not deviation.acknowledged_by or not deviation.acknowledged_at:
            raise MalformedScheduleSnapshot(f"deviation {deviation.deviation_id!r}: acknowledged requires by+at")
        coordinator_row = conn.execute(
            "SELECT 1 FROM coordinators WHERE coordinator_id = ?", (deviation.acknowledged_by,)
        ).fetchone()
        if coordinator_row is None:
            raise MalformedScheduleSnapshot(f"deviation {deviation.deviation_id!r}: unknown acknowledged_by coordinator")


def derive_working_status(deviations: list[Deviation]) -> ScheduleStatus:
    """R1-5 clarification: WORKING status is always derived from persisted
    Deviation count, never independently caller-supplied."""
    return ScheduleStatus.WORKING_WITH_DEVIATIONS if deviations else ScheduleStatus.WORKING


def validate_realized_preserved(
    conn: sqlite3.Connection, parent_version_id: str | None, assignments_by_id: dict[str, Assignment]
) -> None:
    """R1-2 clarification: every parent REALIZED Assignment must be present
    in the child unchanged except for schedule_version_id. schedule_version_id
    is excluded from both sides of the comparison -- storage always derives it
    from the enclosing version, so a caller-supplied Assignment's own
    schedule_version_id field (whatever value it happens to carry) must never
    by itself cause a false RealizedWorkAltered rejection."""
    if parent_version_id is None:
        return
    parent_snapshot = get_schedule_snapshot(conn, parent_version_id)
    for parent_assignment in parent_snapshot.assignments:
        if parent_assignment.state != AssignmentState.REALIZED:
            continue
        child_assignment = assignments_by_id.get(parent_assignment.assignment_id)
        if child_assignment is None:
            raise RealizedWorkAltered(f"missing parent REALIZED assignment {parent_assignment.assignment_id!r}")
        expected = replace(parent_assignment, schedule_version_id=None)
        actual = replace(child_assignment, schedule_version_id=None)
        if actual != expected:
            raise RealizedWorkAltered(f"parent REALIZED assignment {parent_assignment.assignment_id!r} was altered")


if __name__ == "__main__":
    print("persistence.schedule_validation module OK")
