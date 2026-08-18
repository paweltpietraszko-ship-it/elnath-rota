"""ScheduleVersion read queries (tasks/ROTA-T008/brief.md SCHEDULEVERSION,
CURRENT VERSION REFERENCE, BOUNDARY CONTEXT QUERY, CURRENT CROSS-SITE
ASSIGNMENT QUERY, HOLIDAY HISTORY SUPPORT). Write/lifecycle operations live
in rota/persistence/schedule_lifecycle.py.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Optional

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Deviation,
    DeviationCategory,
    ScheduleStatus,
    ScheduleVersion,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
)
from rota.persistence.schedule_errors import ScheduleVersionNotFound
from rota.persistence.schedule_types import ScheduleSnapshot


def _row_to_demand(row: tuple) -> ShiftDemand:
    (schedule_version_id, demand_id, start_dt, end_dt, count,
     shift_kind, catalog_kind, required_rest_hours, template_id, component, emergency_rest) = row
    return ShiftDemand(
        demand_id, schedule_version_id, datetime.fromisoformat(start_dt), datetime.fromisoformat(end_dt), count,
        shift_kind=ShiftKind(shift_kind) if shift_kind else None,
        catalog_kind=ShiftCatalogKind(catalog_kind) if catalog_kind else None,
        required_rest_hours=required_rest_hours,
        work_period_template_id=template_id, work_period_component=component,
        emergency_24h_rest_hours=emergency_rest,
    )


def _row_to_assignment(row: tuple) -> Assignment:
    (schedule_version_id, assignment_id, employee_id, start_dt, end_dt, role, state,
     frozen, covers_demand_id, mentor_id, operational_code, work_period_id, required_rest_after_hours) = row
    return Assignment(
        assignment_id, schedule_version_id, employee_id, datetime.fromisoformat(start_dt), datetime.fromisoformat(end_dt),
        AssignmentRole(role), AssignmentState(state), bool(frozen), covers_demand_id, mentor_id, operational_code,
        work_period_id=work_period_id, required_rest_after_hours=required_rest_after_hours,
    )


def _row_to_deviation(row: tuple) -> Deviation:
    (schedule_version_id, deviation_id, category, source_reference, affected,
     acknowledged, acknowledged_by, acknowledged_at, reason) = row
    return Deviation(
        deviation_id, schedule_version_id, DeviationCategory(category), source_reference, affected, bool(acknowledged),
        acknowledged_by, datetime.fromisoformat(acknowledged_at) if acknowledged_at else None, reason,
    )


def get_schedule_version_header(conn: sqlite3.Connection, version_id: str) -> ScheduleVersion:
    row = conn.execute(
        "SELECT version_id, site_id, month, parent_version_id, created_at, created_by, status, effective_from "
        "FROM schedule_versions WHERE version_id = ?",
        (version_id,),
    ).fetchone()
    if row is None:
        raise ScheduleVersionNotFound(version_id)
    version_id_, site_id, month, parent_id, created_at, created_by, status, effective_from = row
    applied_rules = [
        r[0] for r in conn.execute(
            "SELECT rule_version_id FROM schedule_version_applied_rules WHERE version_id = ? ORDER BY seq",
            (version_id,),
        ).fetchall()
    ]
    return ScheduleVersion(
        version_id=version_id_, site_id=site_id, month=date.fromisoformat(month), parent_version_id=parent_id,
        created_at=datetime.fromisoformat(created_at), created_by=created_by, status=ScheduleStatus(status),
        applied_rule_version_ids=applied_rules,
        effective_from=date.fromisoformat(effective_from) if effective_from else None,
    )


def get_schedule_snapshot(conn: sqlite3.Connection, version_id: str) -> ScheduleSnapshot:
    header = get_schedule_version_header(conn, version_id)
    demands = [
        _row_to_demand(r) for r in conn.execute(
            "SELECT schedule_version_id, demand_id, start_datetime, end_datetime, required_primary_count, "
            "shift_kind, catalog_kind, required_rest_hours, work_period_template_id, work_period_component, "
            "emergency_24h_rest_hours FROM shift_demands WHERE schedule_version_id = ? ORDER BY demand_id",
            (version_id,),
        ).fetchall()
    ]
    assignments = [
        _row_to_assignment(r) for r in conn.execute(
            "SELECT schedule_version_id, assignment_id, employee_id, start_datetime, end_datetime, role, state, "
            "frozen, covers_demand_id, mentor_primary_assignment_id, operational_code, work_period_id, "
            "required_rest_after_hours FROM assignments "
            "WHERE schedule_version_id = ? ORDER BY assignment_id",
            (version_id,),
        ).fetchall()
    ]
    deviations = [
        _row_to_deviation(r) for r in conn.execute(
            "SELECT schedule_version_id, deviation_id, category, source_reference, "
            "affected_assignment_or_employee, acknowledged, acknowledged_by, acknowledged_at, reason "
            "FROM deviations WHERE schedule_version_id = ? ORDER BY deviation_id",
            (version_id,),
        ).fetchall()
    ]
    return ScheduleSnapshot(header.status, header.applied_rule_version_ids, demands, assignments, deviations)


def get_shift_demands_by_ids(conn: sqlite3.Connection, version_demand_ids: list[tuple[str, str]]) -> list[ShiftDemand]:
    """ROTA-T012 Part C: batch-fetch ShiftDemand rows by (schedule_version_id,
    demand_id) pairs, grouped per version -- used to reconstruct cross-month
    emergency boundary demand provenance from an OLDER persisted CURRENT
    ScheduleVersion, never from the current SiteProfile."""
    by_version: dict[str, list[str]] = {}
    for version_id, demand_id in version_demand_ids:
        by_version.setdefault(version_id, []).append(demand_id)
    demands: list[ShiftDemand] = []
    for version_id, demand_ids in by_version.items():
        placeholders = ",".join("?" for _ in demand_ids)
        rows = conn.execute(
            "SELECT schedule_version_id, demand_id, start_datetime, end_datetime, required_primary_count, "
            "shift_kind, catalog_kind, required_rest_hours, work_period_template_id, work_period_component, "
            f"emergency_24h_rest_hours FROM shift_demands WHERE schedule_version_id = ? AND demand_id IN ({placeholders})",
            (version_id, *demand_ids),
        ).fetchall()
        demands.extend(_row_to_demand(r) for r in rows)
    return demands


def list_schedule_versions(conn: sqlite3.Connection, site_id: str, month: date) -> list[ScheduleVersion]:
    rows = conn.execute(
        "SELECT version_id FROM schedule_versions WHERE site_id = ? AND month = ? ORDER BY created_at, version_id",
        (site_id, month.isoformat()),
    ).fetchall()
    return [get_schedule_version_header(conn, row[0]) for row in rows]


def get_current_version_id(conn: sqlite3.Connection, site_id: str, month: date) -> Optional[str]:
    row = conn.execute(
        "SELECT version_id FROM current_schedule_versions WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    return row[0] if row else None


def get_current_schedule_snapshot(conn: sqlite3.Connection, site_id: str, month: date) -> Optional[tuple]:
    version_id = get_current_version_id(conn, site_id, month)
    if version_id is None:
        return None
    return get_schedule_version_header(conn, version_id), get_schedule_snapshot(conn, version_id)


def get_current_assignments_in_interval(
    conn: sqlite3.Connection, site_id: str, context_start: datetime, context_end: datetime,
) -> list[Assignment]:
    """ROTA-T008 BOUNDARY CONTEXT QUERY (R1-3 clarification): every
    non-CANCELLED Assignment from a CURRENT ScheduleVersion of site_id whose
    actual interval overlaps [context_start, context_end), regardless of
    which month owns the ScheduleVersion. Interval-based, not month-overlap
    only -- capable of supplying rolling-7d LOAD-01 predecessor context and
    non-overlapping-but-relevant REST-01 context alike."""
    rows = conn.execute(
        """SELECT a.schedule_version_id, a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime,
                  a.role, a.state, a.frozen, a.covers_demand_id, a.mentor_primary_assignment_id, a.operational_code,
                  a.work_period_id, a.required_rest_after_hours
           FROM assignments a
           JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
           WHERE c.site_id = ? AND a.state != ? AND a.start_datetime < ? AND a.end_datetime > ?
           ORDER BY a.start_datetime, a.assignment_id""",
        (site_id, AssignmentState.CANCELLED.value, context_end.isoformat(), context_start.isoformat()),
    ).fetchall()
    return [_row_to_assignment(row) for row in rows]


def get_current_assignments_for_employees(
    conn: sqlite3.Connection, employee_ids: list[str], interval_start: datetime, interval_end: datetime,
    exclude_site_id: Optional[str] = None,
) -> list[Assignment]:
    """ROTA-T008 CURRENT CROSS-SITE ASSIGNMENT QUERY: non-CANCELLED
    Assignments for the given employees from CURRENT ScheduleVersions of
    any Site (optionally excluding one), overlapping the requested
    interval. Used by T009 for REST-01/LOAD-01/WorkBalance assembly across
    Sites (EMP-03: Employee is not owned by one Site)."""
    if not employee_ids:
        return []
    placeholders = ",".join("?" for _ in employee_ids)
    params: list = [*employee_ids, AssignmentState.CANCELLED.value, interval_end.isoformat(), interval_start.isoformat()]
    site_clause = ""
    if exclude_site_id is not None:
        site_clause = "AND c.site_id != ?"
        params.append(exclude_site_id)
    rows = conn.execute(
        f"""SELECT a.schedule_version_id, a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime,
                   a.role, a.state, a.frozen, a.covers_demand_id, a.mentor_primary_assignment_id, a.operational_code,
                  a.work_period_id, a.required_rest_after_hours
            FROM assignments a
            JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
            WHERE a.employee_id IN ({placeholders}) AND a.state != ? AND a.start_datetime < ? AND a.end_datetime > ?
            {site_clause}
            ORDER BY a.start_datetime, a.assignment_id""",
        params,
    ).fetchall()
    return [_row_to_assignment(row) for row in rows]


def list_months_with_assignments(conn: sqlite3.Connection, site_id: str) -> list[date]:
    """ROTA-T011-B (B-6=W1+filtr obsady): a month qualifies only when its
    CURRENT version has at least one Assignment row -- state is irrelevant
    (a CANCELLED+NN Assignment still counts, per part_d_nn.md: the parent
    plan is preserved, not erased). A month whose current version has a
    current-version pointer but zero Assignments (the empty root
    plan_month creates before ever calling the solver) does not qualify --
    that pointer alone is not evidence of a schedule to navigate to."""
    rows = conn.execute(
        """SELECT DISTINCT c.month
           FROM current_schedule_versions c
           JOIN assignments a ON a.schedule_version_id = c.version_id
           WHERE c.site_id = ?
           ORDER BY c.month""",
        (site_id,),
    ).fetchall()
    return [date.fromisoformat(row[0]) for row in rows]


def get_current_realized_primary_on_holidays(conn: sqlite3.Connection, site_id: str) -> list[Assignment]:
    """ROTA-T008 HOLIDAY HISTORY SUPPORT (R1-4 clarification): CURRENT
    ScheduleVersions only, Assignment.state == REALIZED only,
    Assignment.role == PRIMARY only, on a stored CalendarDay(holiday=true)."""
    rows = conn.execute(
        """SELECT a.schedule_version_id, a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime,
                  a.role, a.state, a.frozen, a.covers_demand_id, a.mentor_primary_assignment_id, a.operational_code,
                  a.work_period_id, a.required_rest_after_hours
           FROM assignments a
           JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
           JOIN calendar_days cd ON cd.date = date(a.start_datetime)
           WHERE c.site_id = ? AND a.role = ? AND a.state = ? AND cd.holiday = 1
           ORDER BY a.start_datetime, a.assignment_id""",
        (site_id, AssignmentRole.PRIMARY.value, AssignmentState.REALIZED.value),
    ).fetchall()
    return [_row_to_assignment(row) for row in rows]


if __name__ == "__main__":
    print("persistence.schedule_repository module OK")
