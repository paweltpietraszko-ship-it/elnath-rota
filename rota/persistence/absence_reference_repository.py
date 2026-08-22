"""ROTA-T023: durable absence-reference provenance -- I/O and provenance
assembly only (frozen addendum section 11 / brief.md section 13, R3-6).
Does not reimplement COVERAGE-01, Assignment/Demand structure, trainee/
mentor rules or 24h legality:
- overlap/ambiguity detection reuses rota.planning.validator.coverage_segments
  (the same sweep-line algorithm COVERAGE-01 uses, made public for this);
- 24h/period grouping reuses rota.planning.work_periods.group_into_periods.

Two responsibilities live here, both called from
rota.application.durable_inputs.append_availability inside its existing
open write transaction, via capture_and_check_in_open_transaction:

1. R5-2 retroactivity guard: reject before any persistence if newly
   introduced/expanded active SICK_LEAVE/LEAVE_GRANTED coverage would cover
   a non-CANCELLED PRIMARY work period that already started, or a REALIZED
   PRIMARY Assignment.
2. R5-1/section 2 provenance capture: for an active SICK_LEAVE/LEAVE_GRANTED
   write, resolve per-date source_mode (PRE_PLAN_LEAVE vs
   POST_PLAN_REFERENCE) using the durable SCHEDULE_CANDIDATE_SELECTED
   acceptance proof, capture the Employee's accepted bound PRIMARY periods,
   and persist one append-only absence_reference_snapshots row.

Deliberately not persisted here: the exact SCHEDULE_CANDIDATE_SELECTED
action_id used as acceptance proof. The resolution rule (accepted iff a
matching action with recorded_at <= this write's recorded_at exists) is
re-derivable at read time from immutable, already-append-only
coordinator_action_records; persisting the action_id here would be a
second, redundant proof of the same already-durable fact.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from rota.domain import AssignmentRole, AssignmentState, AvailabilityKind, MembershipKind
from rota.persistence import site_memory
from rota.persistence.employee_repository import list_memberships_for_employee
from rota.persistence.schedule_repository import (
    InvalidScheduleVersionLineage,
    get_current_assignments_for_employees,
    get_schedule_snapshot,
    reconstruct_lineage,
)
from rota.planning.validator import coverage_segments
from rota.planning.work_periods import PeriodComponent, group_into_periods
from rota.site_memory_types import CoordinatorActionKind

SOURCE_PRE_PLAN_LEAVE = "PRE_PLAN_LEAVE"
SOURCE_POST_PLAN_REFERENCE = "POST_PLAN_REFERENCE"

STATUS_BOUND = "BOUND"
STATUS_MISSING = "MISSING"
STATUS_AMBIGUOUS = "AMBIGUOUS"

_RETROACTIVITY_KINDS = (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)


class RetroactiveAbsenceRejected(Exception):
    """R5-2: a new/expanded active SICK_LEAVE/LEAVE_GRANTED write would
    newly cover a non-CANCELLED PRIMARY work period that already started,
    or a REALIZED PRIMARY Assignment. Raised before any persistence."""


@dataclass(frozen=True)
class PeriodFact:
    assignment_id: str
    schedule_version_id: str
    site_id: str
    covers_demand_id: Optional[str]
    work_period_id: Optional[str]
    start_datetime: datetime
    end_datetime: datetime


@dataclass(frozen=True)
class DayReference:
    the_date: date
    source_mode: str  # SOURCE_PRE_PLAN_LEAVE | SOURCE_POST_PLAN_REFERENCE
    status: str  # STATUS_BOUND | STATUS_MISSING | STATUS_AMBIGUOUS
    hours: Optional[int]  # None when status != BOUND
    periods: tuple[PeriodFact, ...] = ()


@dataclass(frozen=True)
class AbsenceReferenceSnapshot:
    availability_version_id: str
    captured_at: datetime
    reference_status: str
    reference_site_scope: tuple[str, ...]
    days: tuple[DayReference, ...]


# ---------------------------------------------------------------------------
# R5-2 retroactivity guard
# ---------------------------------------------------------------------------


def _date_range(start_date: date, end_date: date) -> set[date]:
    dates: set[date] = set()
    current = start_date
    while current <= end_date:
        dates.add(current)
        current += timedelta(days=1)
    return dates


def check_retroactivity(
    conn: sqlite3.Connection, *, employee_id: str, kind: AvailabilityKind, start_date: date, end_date: date,
    active: bool, recorded_at: datetime, previous_active_range: Optional[tuple[date, date]],
) -> None:
    """Frozen addendum section 8 / brief.md section 6. `previous_active_range`
    is the (start_date, end_date) of the immediately-previous version in the
    SAME availability_id chain, only when that previous version was itself
    active and of the same kind -- otherwise pass None (its prior coverage
    counts as empty, so the whole new range is "newly introduced"). A
    deactivation (active=False) never rejects: it removes coverage rather
    than introducing it."""
    if not active or kind not in _RETROACTIVITY_KINDS:
        return
    new_dates = _date_range(start_date, end_date)
    previous_dates: set[date] = _date_range(*previous_active_range) if previous_active_range else set()
    newly_introduced = new_dates - previous_dates
    if not newly_introduced:
        return
    window_start = datetime.combine(min(newly_introduced), time.min)
    window_end = datetime.combine(max(newly_introduced) + timedelta(days=1), time.min)
    assignments = get_current_assignments_for_employees(conn, [employee_id], window_start, window_end)
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        anchor = assignment.start_datetime.date()
        if anchor not in newly_introduced:
            continue
        if assignment.state == AssignmentState.REALIZED or assignment.start_datetime < recorded_at:
            raise RetroactiveAbsenceRejected(
                f"{employee_id}: {kind.value} covering {anchor} would newly cover PRIMARY assignment "
                f"{assignment.assignment_id} (state={assignment.state.value}, start={assignment.start_datetime})"
            )


# ---------------------------------------------------------------------------
# R5-1 accepted-plan resolution + reference capture
# ---------------------------------------------------------------------------


def _reference_site_scope(conn: sqlite3.Connection, employee_id: str) -> list[str]:
    """Frozen addendum section 7 / brief.md section 7.1: enabled LOCAL
    memberships, union Sites with actual non-CANCELLED PRIMARY reference
    work. A dormant EXTERNAL_SUPPORT membership alone never adds a Site."""
    local_sites = {
        m.site_id for m in list_memberships_for_employee(conn, employee_id)
        if m.enabled and m.membership_kind == MembershipKind.LOCAL
    }
    rows = conn.execute(
        """SELECT DISTINCT c.site_id FROM assignments a
           JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
           WHERE a.employee_id = ? AND a.role = ? AND a.state != ?""",
        (employee_id, AssignmentRole.PRIMARY.value, AssignmentState.CANCELLED.value),
    ).fetchall()
    work_sites = {row[0] for row in rows}
    return sorted(local_sites | work_sites)


def _overall_status(days: list[DayReference]) -> str:
    if any(d.status == STATUS_AMBIGUOUS for d in days):
        return STATUS_AMBIGUOUS
    if any(d.status == STATUS_MISSING for d in days):
        return STATUS_MISSING
    return STATUS_BOUND


def _collect_primary_periods(
    conn: sqlite3.Connection, *, employee_id: str, site_versions: dict[str, str], snapshot_cache: dict[str, object],
) -> list[PeriodFact]:
    periods: list[PeriodFact] = []
    for site_id, version_id in site_versions.items():
        if version_id not in snapshot_cache:
            snapshot_cache[version_id] = get_schedule_snapshot(conn, version_id)
        snapshot = snapshot_cache[version_id]
        for assignment in snapshot.assignments:
            if (
                assignment.employee_id != employee_id
                or assignment.role != AssignmentRole.PRIMARY
                or assignment.state == AssignmentState.CANCELLED
            ):
                continue
            periods.append(PeriodFact(
                assignment.assignment_id, version_id, site_id, assignment.covers_demand_id,
                assignment.work_period_id, assignment.start_datetime, assignment.end_datetime,
            ))
    return periods


def _resolve_day(
    conn: sqlite3.Connection, *, employee_id: str, kind: AvailabilityKind, the_date: date,
    site_versions: dict[str, str], snapshot_cache: dict[str, object],
) -> DayReference:
    if not site_versions:
        if kind == AvailabilityKind.LEAVE_GRANTED:
            # Frozen addendum section 2.1: lack of a prior Employee schedule
            # is not MISSING for a granted-leave request made before PLAN.
            return DayReference(the_date, SOURCE_PRE_PLAN_LEAVE, STATUS_BOUND, 0, ())
        # SICK_LEAVE has no pre-PLAN path (frozen addendum section 2): with
        # no accepted plan anywhere in scope, the reference is incomplete.
        return DayReference(the_date, SOURCE_POST_PLAN_REFERENCE, STATUS_MISSING, None, ())

    periods = _collect_primary_periods(conn, employee_id=employee_id, site_versions=site_versions, snapshot_cache=snapshot_cache)
    by_id = {p.assignment_id: p for p in periods}
    grouped = group_into_periods([
        PeriodComponent(p.assignment_id, employee_id, p.start_datetime, p.end_datetime, p.work_period_id, None, p.schedule_version_id)
        for p in periods
    ])
    # Owner decision (NIGHT_SHIFT_ANCHOR): every work period belongs wholly
    # to its start date -- never split at midnight.
    anchored = [wp for wp in grouped if wp.start.date() == the_date]
    if not anchored:
        return DayReference(the_date, SOURCE_POST_PLAN_REFERENCE, STATUS_BOUND, 0, ())

    starts_ends = [(wp.start, wp.end) for wp in anchored]
    window_start = min(s for s, _ in starts_ends)
    window_end = max(e for _, e in starts_ends)
    segments = coverage_segments(window_start, window_end, starts_ends)
    ambiguous = any(count > 1 for _, _, count in segments)
    facts = tuple(by_id[cid] for wp in anchored for cid in wp.component_ids)
    if ambiguous:
        return DayReference(the_date, SOURCE_POST_PLAN_REFERENCE, STATUS_AMBIGUOUS, None, facts)
    hours = sum(int((wp.end - wp.start).total_seconds() // 3600) for wp in anchored)
    return DayReference(the_date, SOURCE_POST_PLAN_REFERENCE, STATUS_BOUND, hours, facts)


def _fetch_accepted_version_ids(conn: sqlite3.Connection, recorded_at: datetime) -> set[str]:
    return {
        action.schedule_version_id
        for action in site_memory.list_coordinator_actions(
            conn, action_kind=CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED, recorded_to=recorded_at,
        )
        if action.schedule_version_id
    }


def _accepted_version_for(
    conn: sqlite3.Connection, *, site_id: str, anchor_date: date, accepted_version_ids: set[str],
    lineage_cache: dict[tuple[str, date], list],
) -> Optional[str]:
    month = date(anchor_date.year, anchor_date.month, 1)
    key = (site_id, month)
    if key not in lineage_cache:
        try:
            lineage_cache[key] = reconstruct_lineage(conn, site_id, month)
        except InvalidScheduleVersionLineage:
            lineage_cache[key] = []
    lineage = lineage_cache[key]
    applicable = [
        header for header in lineage
        if header.effective_from is not None
        and header.effective_from <= anchor_date
        and header.version_id in accepted_version_ids
    ]
    if not applicable:
        return None
    # Lineage is root..CURRENT (oldest first); the deepest applicable entry
    # is the one with the highest index -- an unselected technical child is
    # simply absent from `applicable` and does not hide it.
    return max(applicable, key=lineage.index).version_id


def capture_reference(
    conn: sqlite3.Connection, *, availability_version_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, recorded_at: datetime, captured_at: datetime,
) -> AbsenceReferenceSnapshot:
    """Frozen addendum section 3 / brief.md section 3.3: per date, resolve
    the deepest accepted applicable ScheduleVersion (SCHEDULE_CANDIDATE_
    SELECTED proof, recorded_at <= this write's recorded_at) for every Site
    in the Employee's reference scope, then capture bound PRIMARY periods."""
    reference_sites = _reference_site_scope(conn, employee_id)
    accepted_version_ids = _fetch_accepted_version_ids(conn, recorded_at)
    lineage_cache: dict[tuple[str, date], list] = {}
    snapshot_cache: dict[str, object] = {}
    days: list[DayReference] = []
    current = start_date
    while current <= end_date:
        site_versions = {
            site_id: version_id
            for site_id in reference_sites
            if (version_id := _accepted_version_for(
                conn, site_id=site_id, anchor_date=current,
                accepted_version_ids=accepted_version_ids, lineage_cache=lineage_cache,
            )) is not None
        }
        days.append(_resolve_day(
            conn, employee_id=employee_id, kind=kind, the_date=current,
            site_versions=site_versions, snapshot_cache=snapshot_cache,
        ))
        current += timedelta(days=1)

    return AbsenceReferenceSnapshot(
        availability_version_id=availability_version_id, captured_at=captured_at,
        reference_status=_overall_status(days), reference_site_scope=tuple(reference_sites), days=tuple(days),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _encode(snapshot: AbsenceReferenceSnapshot) -> str:
    return json.dumps({
        "reference_site_scope": list(snapshot.reference_site_scope),
        "days": [
            {
                "date": d.the_date.isoformat(),
                "source_mode": d.source_mode,
                "status": d.status,
                "hours": d.hours,
                "periods": [
                    {
                        "assignment_id": p.assignment_id,
                        "schedule_version_id": p.schedule_version_id,
                        "site_id": p.site_id,
                        "covers_demand_id": p.covers_demand_id,
                        "work_period_id": p.work_period_id,
                        "start_datetime": p.start_datetime.isoformat(),
                        "end_datetime": p.end_datetime.isoformat(),
                    }
                    for p in d.periods
                ],
            }
            for d in snapshot.days
        ],
    }, sort_keys=True)


def _decode(availability_version_id: str, captured_at: datetime, reference_status: str, snapshot_json: str) -> AbsenceReferenceSnapshot:
    raw = json.loads(snapshot_json)
    days = tuple(
        DayReference(
            the_date=date.fromisoformat(d["date"]), source_mode=d["source_mode"], status=d["status"],
            hours=d["hours"],
            periods=tuple(
                PeriodFact(
                    assignment_id=p["assignment_id"], schedule_version_id=p["schedule_version_id"],
                    site_id=p["site_id"], covers_demand_id=p["covers_demand_id"], work_period_id=p["work_period_id"],
                    start_datetime=datetime.fromisoformat(p["start_datetime"]),
                    end_datetime=datetime.fromisoformat(p["end_datetime"]),
                )
                for p in d["periods"]
            ),
        )
        for d in raw["days"]
    )
    return AbsenceReferenceSnapshot(
        availability_version_id=availability_version_id, captured_at=captured_at, reference_status=reference_status,
        reference_site_scope=tuple(raw["reference_site_scope"]), days=days,
    )


def save_absence_reference_snapshot_in_open_transaction(conn: sqlite3.Connection, snapshot: AbsenceReferenceSnapshot) -> None:
    conn.execute(
        "INSERT INTO absence_reference_snapshots (availability_version_id, captured_at, reference_status, snapshot_json) "
        "VALUES (?, ?, ?, ?)",
        (snapshot.availability_version_id, snapshot.captured_at.isoformat(), snapshot.reference_status, _encode(snapshot)),
    )


def get_absence_reference_snapshot(conn: sqlite3.Connection, availability_version_id: str) -> Optional[AbsenceReferenceSnapshot]:
    row = conn.execute(
        "SELECT captured_at, reference_status, snapshot_json FROM absence_reference_snapshots WHERE availability_version_id = ?",
        (availability_version_id,),
    ).fetchone()
    if row is None:
        return None
    captured_at, reference_status, snapshot_json = row
    return _decode(availability_version_id, datetime.fromisoformat(captured_at), reference_status, snapshot_json)


def capture_and_check_in_open_transaction(
    conn: sqlite3.Connection, *, availability_version_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, active: bool, recorded_at: datetime,
    previous_active_range: Optional[tuple[date, date]],
) -> Optional[AbsenceReferenceSnapshot]:
    """Single entry point for rota.application.durable_inputs.
    append_availability, called inside its existing open write transaction
    after the new AvailabilityVersion row exists (FK target of
    absence_reference_snapshots) but before commit.

    Raises RetroactiveAbsenceRejected (R5-2) before persisting anything --
    the caller's `with conn:` then rolls the whole write back. Returns None
    (no row persisted) for every kind other than active SICK_LEAVE/
    LEAVE_GRANTED; only those require a captured reference (frozen addendum
    section 6)."""
    if kind not in _RETROACTIVITY_KINDS:
        return None
    check_retroactivity(
        conn, employee_id=employee_id, kind=kind, start_date=start_date, end_date=end_date,
        active=active, recorded_at=recorded_at, previous_active_range=previous_active_range,
    )
    if not active:
        return None
    snapshot = capture_reference(
        conn, availability_version_id=availability_version_id, employee_id=employee_id, kind=kind,
        start_date=start_date, end_date=end_date, recorded_at=recorded_at, captured_at=recorded_at,
    )
    save_absence_reference_snapshot_in_open_transaction(conn, snapshot)
    return snapshot


if __name__ == "__main__":
    print("persistence.absence_reference_repository module OK")
