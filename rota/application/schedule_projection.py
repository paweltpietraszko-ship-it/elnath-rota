"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 8: the shared, format-
independent schedule projection -- extracted verbatim (mechanical move,
no behavior change) from rota/application/schedule_export.py's own
assembly logic, which used to be private and PDF-bound. PDF rendering
and the external Excel API both build on `build_schedule_projection`;
neither reimplements work-code mapping, absence decomposition, or
DELEGACJA hour arithmetic a second time.

This module owns projection ONLY -- it never imports reportlab and
knows nothing about Excel cells or PDF canvases. Exceptions
(`ExportProblemError`) are shared vocabulary between projection and
rendering: many `problem_code`s (WORK_PROVENANCE_INCOMPLETE, ABSENCE_
DECOMPOSITION_REQUIRED, etc.) originate here.

schedule_export.py keeps a compatibility alias,
`_assemble_export_model = build_schedule_projection` (plus a re-export
of `_reconstruct_lineage`), so the many existing tests calling
`SE._assemble_export_model(...)`/`SE._reconstruct_lineage(...)` directly
(tests/test_t020.py, test_t023b.py, test_t023_checkpoint_c.py,
test_t056.py, test_t047_print_export.py, test_t065_manual_middle_
shift.py -- none of them in this Task's TASK_SCOPE) keep working
unchanged. OWNER_RULING 2026-09-16: alias over rename, to avoid
touching 5 test files outside TASK_SCOPE for a pure rename.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from rota.domain import Assignment, AssignmentRole, AssignmentState, AvailabilityKind, MembershipKind, ShiftCatalogKind, SitePlanningRegime
from rota.persistence import calendar_repository, employee_repository, schedule_repository, site_repository
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.persistence.availability_repository import list_active_overlapping_for_employees
from rota.persistence.schedule_errors import ScheduleVersionNotFound
from rota.planning.absence import (
    DetailedAbsencePeriodFact,
    DetailedDailyAbsenceFact,
    IncompleteAbsenceReferenceError,
    IncompleteDelegationHoursError,
    canonical_site_absence_days,
    delegation_hours_in_range,
)
from rota.planning.work_periods import PeriodComponent, group_into_periods

PLAN_PRIORITY = ("D1", "D2", "D3", "D4", "D5", "N1", "N2", "N3", "N4", "N5")
BLANK = "–"
# ROTA-DELEGACJA-ABSENCE-KIND brief.md section 10: frozen label for both
# regimes -- never "D" (already OCHRONA's day-shift code).
DELEGACJA_LABEL = "DEL"


class ExportProblemError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class RowCells:
    employee_id: str
    display_name: str
    plan: list[str]
    wyk: list[str]
    plan_hours: int
    wyk_hours: int
    urlop_hours: int
    l4_hours: int


@dataclass(frozen=True)
class OrdinaryRowCells:
    # ROTA-T065-PRINT-GAP brief section 5/9: one row per employee (no
    # PLAN/WYK duet), one fixed historical position label under the name
    # (never per-shift), day cells are real hour-range lines or absence
    # words -- never D/N codes. day_absence_kind drives border style only
    # ("URLOP"=solid, "L4"=dashed, None=plain work/blank cell).
    employee_id: str
    display_name: str
    position_label: str
    day_cells: list[list[str]]
    day_absence_kind: list[Optional[str]]
    total_hours: int


@dataclass(frozen=True)
class ExportModel:
    site_id: str
    month: date
    period_label: str
    company_print_name: str
    site_print_name: str
    base_regime: str
    work_code_intervals: dict
    reserve_hours: dict
    current_version_id: str
    lineage: list[tuple[str, Optional[str]]]
    days: list[date]
    rows: list[RowCells]
    provenance_text: str
    provenance_display_text: str
    holiday_by_date: dict
    adjacent_facts: list
    extra_work_codes: dict  # ROTA-T056: this exact (site_id, month)'s D6+/N6+ definitions
    # ROTA-T065-PRINT-GAP: regime branch is presentation-only (brief section
    # 13) -- "OCHRONA" keeps every field above populated as before,
    # "ORDINARY" leaves them at inert placeholder values and uses
    # ordinary_rows instead of rows.
    regime: str = "OCHRONA"
    ordinary_rows: tuple[OrdinaryRowCells, ...] = ()


# Assembly
def build_schedule_projection(conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str) -> ExportModel:
    if month.day != 1:
        raise ExportProblemError("PROVENANCE_INCOMPLETE", "month must be the first day of the month")
    settings = site_repository.get_site_print_settings(conn, site_id)
    if settings is None:
        raise ExportProblemError("PRINT_SETTINGS_MISSING", f"no print settings saved for {site_id}")
    site = site_repository.get_site(conn, site_id)
    lineage = _reconstruct_lineage(conn, site_id, month)
    days = _month_days(month)
    calendar_days = calendar_repository.list_calendar_days(conn, days[0], days[-1])
    holiday_by_date = {c.date: c.holiday for c in calendar_days}
    if site.planning_regime == SitePlanningRegime.ORDINARY:
        return _assemble_ordinary_export_model(
            conn, site_id=site_id, month=month, period_label=period_label,
            settings=settings, lineage=lineage, days=days, holiday_by_date=holiday_by_date,
        )
    snapshots: dict[str, "schedule_repository.ScheduleSnapshot"] = {}
    daily_version = {d: _version_for_date(lineage, d) for d in days}
    extra_codes = site_repository.get_site_monthly_extra_work_codes(conn, site_id, month)
    extra_hours = {code: int(site_repository.interval_duration_hours(iv)) for code, iv in extra_codes.items()}
    memberships = employee_repository.list_memberships_for_site(conn, site_id)
    local_ids = {m.employee_id for m in memberships if m.membership_kind == MembershipKind.LOCAL and m.enabled}
    collected = _collect_real_work_cells(conn, site_id, days, daily_version, snapshots, settings, extra_codes)
    seen_employee_ids = collected[2]
    work_cells, adjacent_facts = _apply_24h_periods(collected, settings, days, extra_codes)
    absence_by_employee = _collect_absence(conn, days, local_ids, work_cells, settings, site_id)
    delegation_by_employee = _collect_delegation_records(conn, days, local_ids)
    roster_ids = (
        local_ids | seen_employee_ids | set(absence_by_employee) | set(delegation_by_employee)
    )  # C-R15-3: a bound Site period keeps an Employee here after REPLAN
    employees = employee_repository.list_employees_by_ids(conn, list(roster_ids))
    rows = _build_rows(
        roster_ids, employees, days, work_cells, absence_by_employee, delegation_by_employee,
        settings.reserve_hours, extra_hours,
    )
    provenance = _provenance_text(lineage, adjacent_facts)
    provenance_display = _provenance_display_text(lineage, adjacent_facts)
    return ExportModel(
        site_id=site_id, month=month, period_label=period_label,
        company_print_name=settings.company_print_name, site_print_name=settings.site_print_name,
        base_regime=settings.base_regime, work_code_intervals=settings.work_code_intervals,
        reserve_hours=settings.reserve_hours, current_version_id=lineage[-1].version_id,
        lineage=[(h.version_id, h.effective_from.isoformat() if h.effective_from else None) for h in lineage],
        days=days, rows=rows, provenance_text=provenance, provenance_display_text=provenance_display,
        holiday_by_date=holiday_by_date, adjacent_facts=adjacent_facts, extra_work_codes=extra_codes,
    )
def _month_days(month: date) -> list[date]:
    import calendar as _cal
    n = _cal.monthrange(month.year, month.month)[1]; return [date(month.year, month.month, d) for d in range(1, n + 1)]  # noqa: E702
def _reconstruct_lineage(conn: sqlite3.Connection, site_id: str, month: date) -> list:
    current_id = schedule_repository.get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise ExportProblemError("NO_CURRENT_SCHEDULE", f"no current ScheduleVersion for ({site_id}, {month})")
    try:  # ROTA-T023b sec.4: pre-render gate; missing/corrupt current_id falls through to PROVENANCE_INCOMPLETE below.
        if schedule_repository.version_requires_regime_replan(conn, current_id):
            raise ExportProblemError("REGIME_REPLAN_REQUIRED", f"{current_id}: regime replan required before export")
    except ScheduleVersionNotFound: pass  # noqa: E701
    chain, seen, version_id = [], set(), current_id
    while version_id is not None:
        if version_id in seen:
            raise ExportProblemError("PROVENANCE_INCOMPLETE", "cyclic ScheduleVersion lineage")
        seen.add(version_id)
        try:
            header = schedule_repository.get_schedule_version_header(conn, version_id)
        except ScheduleVersionNotFound:
            raise ExportProblemError("PROVENANCE_INCOMPLETE", f"missing lineage version {version_id}")
        if header.site_id != site_id or header.month != month:
            raise ExportProblemError("PROVENANCE_INCOMPLETE", f"{version_id} does not belong to ({site_id}, {month})")
        if header.effective_from is None:
            raise ExportProblemError("PROVENANCE_INCOMPLETE", f"{version_id} has no effective_from")
        chain.append(header)
        version_id = header.parent_version_id
    chain.reverse()
    return chain
def _version_for_date(lineage: list, target: date) -> Optional[str]:
    selected = None
    for header in lineage:
        if header.effective_from <= target:
            selected = header.version_id
    return selected
# ORDINARY assembly (brief section 6/7/9/10) -- no D/N mapping, no 24h
# collapse, no PLAN/WYK duet, one fixed historical position label per
# employee. Absence still comes from the same canonical facts as OCHRONA
# (canonical_site_absence_days), only the presentation is simpler: a plain
# "Urlop"/"L4" word per active day, never an hour-code decomposition.
def _assemble_ordinary_export_model(
    conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str,
    settings, lineage: list, days: list[date], holiday_by_date: dict,
) -> "ExportModel":
    snapshots: dict[str, "schedule_repository.ScheduleSnapshot"] = {}
    daily_version = {d: _version_for_date(lineage, d) for d in days}
    memberships = employee_repository.list_memberships_for_site(conn, site_id)
    local_ids = {m.employee_id for m in memberships if m.membership_kind == MembershipKind.LOCAL and m.enabled}
    work_items, seen_employee_ids = _collect_ordinary_work_items(conn, days, daily_version, snapshots)
    absence_by_employee = _collect_ordinary_absence(conn, days, local_ids, work_items, site_id)
    delegation_by_employee = _collect_delegation_records(conn, days, local_ids)
    roster_ids = local_ids | seen_employee_ids | set(absence_by_employee) | set(delegation_by_employee)
    employees = employee_repository.list_employees_by_ids(conn, list(roster_ids))
    current_version_id = lineage[-1].version_id
    positions = schedule_repository.get_schedule_version_employee_positions(conn, current_version_id)
    rows = _build_ordinary_rows(roster_ids, employees, days, work_items, absence_by_employee, delegation_by_employee, positions)
    provenance = _provenance_text(lineage, [])
    provenance_display = _provenance_display_text(lineage, [])
    return ExportModel(
        site_id=site_id, month=month, period_label=period_label,
        company_print_name=settings.company_print_name, site_print_name=settings.site_print_name,
        base_regime="", work_code_intervals={}, reserve_hours={}, current_version_id=current_version_id,
        lineage=[(h.version_id, h.effective_from.isoformat() if h.effective_from else None) for h in lineage],
        days=days, rows=[], provenance_text=provenance, provenance_display_text=provenance_display,
        holiday_by_date=holiday_by_date, adjacent_facts=[], extra_work_codes={},
        regime="ORDINARY", ordinary_rows=tuple(rows),
    )
def _collect_ordinary_work_items(conn, days: list[date], daily_version: dict, snapshots: dict):
    """Brief section 6/7: every non-cancelled PRIMARY Assignment for the day
    is a real interval; ORDINARY never collapses a pair into "24", never
    maps to a D/N code and never raises MULTIPLE_WORK_ITEMS_PER_CELL -- all
    non-overlapping real items of a day share one cell as separate
    chronological lines instead."""
    items: dict[str, dict[date, list[tuple[datetime, datetime, str]]]] = {}
    seen_employee_ids: set[str] = set()
    for day in days:
        version_id = daily_version[day]
        if version_id is None:
            continue
        if version_id not in snapshots:
            snapshots[version_id] = schedule_repository.get_schedule_snapshot(conn, version_id)
        snapshot = snapshots[version_id]
        for a in snapshot.assignments:
            if a.start_datetime.date() != day or a.state == AssignmentState.CANCELLED:
                continue
            if a.role == AssignmentRole.TRAINEE:
                raise ExportProblemError("UNSUPPORTED_TRAINEE_PRINT", f"{a.assignment_id} is an effective TRAINEE assignment")
            if a.role != AssignmentRole.PRIMARY:
                continue
            seen_employee_ids.add(a.employee_id)
            items.setdefault(a.employee_id, {}).setdefault(day, []).append((a.start_datetime, a.end_datetime, a.assignment_id))
    for by_day in items.values():
        for day_items in by_day.values():
            day_items.sort(key=lambda t: (t[0], t[1], t[2]))
    return items, seen_employee_ids
def _format_ordinary_hour(dt: datetime) -> str:
    return str(dt.hour) if dt.minute == 0 else f"{dt.hour}:{dt.minute:02d}"
def _format_ordinary_piece(start: datetime, end: datetime) -> str:
    # Brief section 5/6/8: literal hours, no leading zeros, "(+1)" when the
    # shift ends on a later calendar date than it started; always anchored
    # on the start date's cell.
    suffix = "(+1)" if end.date() > start.date() else ""
    return f"{_format_ordinary_hour(start)}–{_format_ordinary_hour(end)}{suffix}"
def _ordinary_absence_word(kind: AvailabilityKind) -> str:
    return "Urlop" if kind == AvailabilityKind.LEAVE_GRANTED else "L4"
def _collect_delegation_records(conn, days: list[date], local_ids: set) -> dict[str, list]:
    """ROTA-DELEGACJA-ABSENCE-KIND brief.md section 10: DELEGACJA is not
    excused absence and carries no absence_reference_snapshot (unlike
    SICK_LEAVE/LEAVE_GRANTED). Returns each LOCAL employee's active
    DELEGACJA AvailabilityRecords overlapping the month -- shared by both
    regime renderers. Callers use the one canonical
    rota.planning.absence.delegation_hours_in_range for any hours
    arithmetic (brief section 7: this module must never repeat it)."""
    month_start, month_end = days[0], days[-1]
    all_employee_ids = [e.employee_id for e in employee_repository.list_employees(conn)]
    records = list_active_overlapping_for_employees(conn, all_employee_ids, month_start, month_end)
    result: dict[str, list] = {}
    for r in records:
        if r.kind == AvailabilityKind.DELEGACJA and r.employee_id in local_ids:
            result.setdefault(r.employee_id, []).append(r)
    return result
def _delegation_days(records: list, month_start: date, month_end: date) -> set:
    """Calendar-membership only (which days a cell must show DEL for) --
    never an hours computation; see _collect_delegation_records' note."""
    covered: set = set()
    for r in records:
        d = max(r.start_date, month_start)
        end = min(r.end_date, month_end)
        while d <= end:
            covered.add(d)
            d += timedelta(days=1)
    return covered
def _collect_ordinary_absence(conn, days: list[date], local_ids: set, work_days: dict, site_id: str) -> dict[str, list[tuple[date, str]]]:
    # Same canonical source and site-attribution/fail-closed rules as
    # OCHRONA's _collect_absence -- only the per-day presentation differs
    # (a plain word, never an hour-code decomposition).
    month_start, month_end = days[0], days[-1]
    all_employee_ids = [e.employee_id for e in employee_repository.list_employees(conn)]
    records = list_active_overlapping_for_employees(conn, all_employee_ids, month_start, month_end)
    by_employee: dict[str, list] = {}
    for r in records:
        by_employee.setdefault(r.employee_id, []).append(r)
    memberships_by_employee = employee_repository.list_memberships_for_employees(conn, sorted(by_employee))
    result: dict[str, list[tuple[date, str]]] = {}
    for employee_id in sorted(by_employee):
        emp_records = [r for r in by_employee[employee_id] if r.kind in (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)]
        if not emp_records:
            continue
        snapshots = [(r, get_absence_reference_snapshot(conn, r.availability_version_id)) for r in emp_records]
        bound_here = any(p.site_id == site_id for _, snap in snapshots if snap for day in snap.days for p in day.periods)
        if employee_id not in local_ids and not bound_here:
            continue
        for r, snapshot in snapshots:
            if snapshot is None:
                raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", f"{employee_id}: legacy active {r.kind.value} has no captured reference snapshot")
        enabled_local = sum(1 for m in memberships_by_employee.get(employee_id, []) if m.membership_kind == MembershipKind.LOCAL and m.enabled)
        try:
            canonical_days = canonical_site_absence_days(_detailed_facts(snapshots), range_start=month_start, range_end=month_end, site_id=site_id)
        except IncompleteAbsenceReferenceError as exc:
            raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", f"{employee_id}: {exc}") from exc
        pairs = _ordinary_absence_days_for_employee(employee_id, canonical_days, work_days, enabled_local)
        if pairs:
            result[employee_id] = pairs
    return result
def _ordinary_absence_days_for_employee(employee_id: str, canonical_days, work_days: dict, enabled_local: int) -> list[tuple[date, str]]:
    for day in canonical_days:
        if day.the_date in work_days.get(employee_id, {}):
            raise ExportProblemError("ASSIGNMENT_ABSENCE_CONFLICT", f"{employee_id}/{day.the_date}: real Assignment on an active absence day")
    pre_plan_days = [d for d in canonical_days if d.source_mode == "PRE_PLAN_LEAVE"]
    post_plan_days = [d for d in canonical_days if d.source_mode != "PRE_PLAN_LEAVE"]
    pairs: list[tuple[date, str]] = []
    if pre_plan_days:
        if enabled_local > 1:  # T23-46: keeps the existing fail-closed Site-attribution boundary
            raise ExportProblemError("ABSENCE_SITE_AMBIGUOUS", f"{employee_id} has {enabled_local} enabled LOCAL memberships")
        for day in pre_plan_days:
            pairs.append((day.the_date, _ordinary_absence_word(day.kind)))
    for day in post_plan_days:
        if day.site_hours == 0:
            continue  # accepted rest, or no bound period at this Site -- no synthetic absence word (T23-42)
        pairs.append((day.the_date, _ordinary_absence_word(day.kind)))
    return pairs
def _build_ordinary_rows(
    roster_ids, employees, days: list[date], work_items: dict, absence_by_employee: dict,
    delegation_by_employee: dict, positions: dict,
) -> list[OrdinaryRowCells]:
    rows = []
    for employee_id in roster_ids:
        employee = employees[employee_id]
        # rota.persistence.schedule_lifecycle._insert_employee_positions
        # (ROTA-T065-CONFIGURABLE-ROLES section 6, owner contract): an
        # employee with no snapshotted row -- OCHRONA-only external
        # support, or an ORDINARY employee never assigned a position --
        # gets no row, and the read side prints "no position", never an
        # error; PRINT-GAP must not invent a stricter contract here.
        position = positions.get(employee_id)
        position_label = position.role_name if position is not None else ""
        absence_by_date = dict(absence_by_employee.get(employee_id, []))
        delegation_records = delegation_by_employee.get(employee_id, [])
        delegation_days = _delegation_days(delegation_records, days[0], days[-1])
        emp_items = work_items.get(employee_id, {})
        day_cells: list[list[str]] = []
        day_absence_kind: list[Optional[str]] = []
        total_hours = 0
        for day in days:
            pieces = emp_items.get(day)
            if pieces:
                # ROTA-DELEGACJA-ABSENCE-KIND audit R2 (tests_r2.txt R2-01):
                # a coordinator's manual correction may legally place a real
                # Assignment on an active DELEGACJA day -- the write path
                # already materializes this as a DELEGACJA-01 Deviation
                # (warning), never a hard block. The print renderer must
                # not turn a saved decision back into an export-time
                # exception; show the real worked hours, exactly as any
                # other real Assignment day.
                day_cells.append([_format_ordinary_piece(start, end) for start, end, _ in pieces])
                day_absence_kind.append(None)
                total_hours += sum(round((end - start).total_seconds() / 3600) for start, end, _ in pieces)
            elif day in delegation_days:
                day_cells.append([DELEGACJA_LABEL])
                day_absence_kind.append("DEL")
            elif day in absence_by_date:
                word = absence_by_date[day]
                day_cells.append([word])
                day_absence_kind.append("URLOP" if word == "Urlop" else "L4")
            else:
                day_cells.append([BLANK])
                day_absence_kind.append(None)
        try:
            total_hours += delegation_hours_in_range(delegation_records, employee_id, days[0], days[-1])
        except IncompleteDelegationHoursError as exc:
            raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", str(exc)) from exc
        rows.append(OrdinaryRowCells(
            employee_id=employee_id, display_name=employee.display_name, position_label=position_label,
            day_cells=day_cells, day_absence_kind=day_absence_kind, total_hours=total_hours,
        ))
    rows.sort(key=lambda r: (r.display_name.casefold(), r.employee_id))
    return rows
def _lineage_digest(lineage: list, adjacent_facts: list) -> str:
    ordered = [(h.version_id, h.effective_from.isoformat() if h.effective_from else "") for h in lineage]
    return hashlib.sha256(json.dumps([ordered, adjacent_facts], sort_keys=True).encode("utf-8")).hexdigest()
def _provenance_text(lineage: list, adjacent_facts: list) -> str:
    # Adjacent facts actually used for collapse/suppression must affect displayed provenance, not only document_revision (R6 Section 7 / R10-3).
    # Full technical value -- feeds ExportReady.schedule_provenance (API-only field, never rendered) and must stay unchanged (T051 R4).
    digest = _lineage_digest(lineage, adjacent_facts)
    return f"Schedule provenance: {lineage[-1].version_id} / lineage-sha256:{digest}"
def _provenance_display_text(lineage: list, adjacent_facts: list) -> str:
    # T051 (OWNER_CORRECTED): short, human-facing text drawn on the PDF only -- no SV-..., no English label.
    return f"Kod weryfikacyjny grafiku: {_lineage_digest(lineage, adjacent_facts)[:10]}"
# Real work cells (Section 10)
def _adjacent_day_items(conn, site_id: str, target_day: date) -> list:
    # Adjacent-month leg for linkage detection only, never its own cell; a broken adjacent lineage fails PROVENANCE_INCOMPLETE (R6 Amendment 2.2).
    other_month = date(target_day.year, target_day.month, 1)
    if schedule_repository.get_current_version_id(conn, site_id, other_month) is None:
        return []
    lineage = _reconstruct_lineage(conn, site_id, other_month)
    version_id = _version_for_date(lineage, target_day)
    if version_id is None:
        return []
    effective_from = next(h.effective_from for h in lineage if h.version_id == version_id)
    snapshot = schedule_repository.get_schedule_snapshot(conn, version_id)
    demands_by_id = {d.demand_id: d for d in snapshot.shift_demands}
    items = []
    for a in snapshot.assignments:
        if a.start_datetime.date() != target_day or a.state == AssignmentState.CANCELLED or a.role != AssignmentRole.PRIMARY:
            continue
        demand = demands_by_id.get(a.covers_demand_id)
        if demand is not None:
            items.append((a, demand, version_id, effective_from))
    return items
def _interval_bounds(anchor: date, interval) -> tuple[datetime, datetime]:
    """R8-02 fix: the ONE exact-match arithmetic shared by _extra_code_matches
    and _map_work_code. Computes the full expected start/end datetime an
    interval means when anchored on a given date -- comparing these two full
    datetimes (not HH:MM strings plus a crosses-midnight bool) is required
    because `end_datetime.date() > start_datetime.date()` is true for ANY
    later day, not only exactly one day later: a 65h Assignment was
    previously accepted as matching a 41h (end_next_day=True) definition
    because both merely "crossed midnight"."""
    start = datetime.combine(anchor, datetime.strptime(interval.start_time, "%H:%M").time())
    end_date = anchor + timedelta(days=1) if interval.end_next_day else anchor
    end = datetime.combine(end_date, datetime.strptime(interval.end_time, "%H:%M").time())
    return start, end
def _extra_code_matches(a, demand, extra_codes: dict) -> bool:
    """ROTA-T056 brief section 9.1 -- the ONE narrow exception to the
    provenance invariant below. A manually-corrected Assignment may differ
    from its covered demand's interval ONLY when it is anchored on the
    demand's own date and exactly matches (full start/end datetime, not
    merely the same duration) a saved monthly D6+/N6+ definition of the same
    family for this exact (site, month). Any other discrepancy -- no
    configured extra code, wrong family, wrong date, same-duration-
    different-clock, or any other manual divergence -- stays fail-closed
    (T56-08)."""
    if demand.shift_kind is None or a.start_datetime.date() != demand.start_datetime.date():
        return False
    family = demand.shift_kind.value
    for code, interval in extra_codes.items():
        if not code.startswith(family):
            continue
        start, end = _interval_bounds(demand.start_datetime.date(), interval)
        if a.start_datetime == start and a.end_datetime == end:
            return True
    return False
def _validate_item(a, demand, extra_codes: dict) -> None:
    if a.role == AssignmentRole.TRAINEE:
        raise ExportProblemError("UNSUPPORTED_TRAINEE_PRINT", f"{a.assignment_id} is an effective TRAINEE assignment")
    if demand is None:
        raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{a.assignment_id} has no coherent covered demand")
    if a.start_datetime != demand.start_datetime or a.end_datetime != demand.end_datetime:
        if not _extra_code_matches(a, demand, extra_codes):
            raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{a.assignment_id}: actual interval contradicts its covered demand")
    # T047: catalog_kind == OTHER only means "duration other than 12h/24h" (rota.planning.shift_catalog);
    # it is not a third unsupported work kind, so it is no longer rejected here. Printability of a
    # D/N item is decided solely by _map_work_code's exact interval match, which fails closed
    # (WORK_CODE_MAPPING_REQUIRED) on its own when no configured code matches.
def _ckey(a) -> str:
    return f"{a.schedule_version_id}::{a.assignment_id}"  # identity is (schedule_version_id, assignment_id) -- a bare local id may repeat across ScheduleVersions (R10-2)
def _component(a) -> PeriodComponent:
    return PeriodComponent(_ckey(a), a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id)
def _collect_real_work_cells(conn, site_id, days, daily_version, snapshots, settings, extra_codes):
    # raw_items/components/seen_ids/demand_by_assignment/assignment_by_id/boundary_ids/adjacent_versions/s1_cells. Raises on TRAINEE/INNY/bad provenance.
    raw_items: dict[tuple[str, date], list] = {}
    components: list[PeriodComponent] = []
    demand_by_assignment: dict = {}; assignment_by_id: dict = {}; seen_employee_ids: set[str] = set()  # noqa: E702
    # ROTA-T052 (brief section 7): S1 never covers a demand and never
    # participates in 24h-period/demand-coverage validation -- collected
    # separately (keyed by its own real interval, not a bare code string, so
    # the merge below can tell real overlap from mere same-day co-occurrence
    # -- R4-02 audit fix), merged into work_cells afterward.
    s1_cells: dict[str, dict[date, tuple[datetime, datetime]]] = {}
    for day in days:
        version_id = daily_version[day]
        if version_id is None:
            continue
        if version_id not in snapshots:
            snapshots[version_id] = schedule_repository.get_schedule_snapshot(conn, version_id)
        snapshot = snapshots[version_id]
        demands_by_id = {d.demand_id: d for d in snapshot.shift_demands}
        for a in snapshot.assignments:
            if a.start_datetime.date() != day or a.state == AssignmentState.CANCELLED:
                continue
            if a.role == AssignmentRole.PERIODIC_TRAINING:
                seen_employee_ids.add(a.employee_id)
                s1_cells.setdefault(a.employee_id, {})[day] = (a.start_datetime, a.end_datetime)
                continue
            demand = demands_by_id.get(a.covers_demand_id) if a.covers_demand_id else None
            _validate_item(a, demand, extra_codes)
            seen_employee_ids.add(a.employee_id)
            raw_items.setdefault((a.employee_id, day), []).append((a, demand))
            demand_by_assignment[_ckey(a)] = demand
            assignment_by_id[_ckey(a)] = a
            components.append(_component(a))
    boundary_days = (days[0] - timedelta(days=1), days[-1] + timedelta(days=1))
    boundary_items = []
    for snapshot in snapshots.values():  # a boundary component can already sit in an in-month version
        demands_by_id = {d.demand_id: d for d in snapshot.shift_demands}
        for a in snapshot.assignments:
            if a.start_datetime.date() in boundary_days and a.role == AssignmentRole.PRIMARY and a.state != AssignmentState.CANCELLED:
                demand = demands_by_id.get(a.covers_demand_id)
                if demand is not None:
                    boundary_items.append((a, demand, a.schedule_version_id, None))
    for boundary_day in boundary_days:  # or it may live in a genuinely different month's own ScheduleVersion
        boundary_items.extend(_adjacent_day_items(conn, site_id, boundary_day))
    boundary_ids: set[str] = set(); adjacent_versions: dict = {}  # noqa: E702
    for a, demand, version_id, effective_from in boundary_items:
        if a.work_period_id is None or _ckey(a) in demand_by_assignment:
            continue
        demand_by_assignment[_ckey(a)] = demand; assignment_by_id[_ckey(a)] = a; boundary_ids.add(_ckey(a))  # noqa: E702
        adjacent_versions[_ckey(a)] = (version_id, effective_from.isoformat() if effective_from else None)
        components.append(_component(a))
    return raw_items, components, seen_employee_ids, demand_by_assignment, assignment_by_id, boundary_ids, adjacent_versions, s1_cells
def _is_legitimate_normal_24h(d0, d1, total_hours: float) -> bool:
    # R5 Amendment Section 4.2 -- unchanged, still owned/re-derived by T020.
    if total_hours != 24 or d0.catalog_kind != ShiftCatalogKind.H24 or d1.catalog_kind != ShiftCatalogKind.H24:
        return False
    if d0.shift_kind is None or d0.shift_kind == d1.shift_kind:
        return False
    if not (d0.work_period_template_id) or d0.work_period_template_id != d1.work_period_template_id:
        return False
    if {d0.work_period_component, d1.work_period_component} != {1, 2}:
        return False
    hours0, hours1 = (d0.end_datetime - d0.start_datetime).total_seconds() / 3600, (d1.end_datetime - d1.start_datetime).total_seconds() / 3600
    return hours0 == 12 and hours1 == 12
def _classify_period(period, demand_by_assignment: dict, boundary_ids: set) -> Optional[str]:
    # 'normal' (R5 4.2, re-derived) or 'linked' (cross-boundary pair -- trusts persisted (employee_id, work_period_id) only, per R6 Linkage Narrowing). None -> caller fails closed if asserted.
    if len(period.component_ids) != 2:
        return None
    d0, d1 = demand_by_assignment.get(period.component_ids[0]), demand_by_assignment.get(period.component_ids[1])
    if d0 is None or d1 is None:
        return None
    total_hours = (period.end - period.start).total_seconds() / 3600
    if _is_legitimate_normal_24h(d0, d1, total_hours):
        return "normal"
    crosses_boundary = any(cid in boundary_ids for cid in period.component_ids)
    if crosses_boundary and d0.catalog_kind != ShiftCatalogKind.H24 and d1.catalog_kind != ShiftCatalogKind.H24:
        return "linked"
    return None
def _intervals_overlap(a: tuple[datetime, datetime], b: tuple[datetime, datetime]) -> bool:
    return a[0] < b[1] and b[0] < a[1]
def _apply_24h_periods(collected, settings, days: list[date], extra_codes):
    raw_items, components, seen_employee_ids, demand_by_assignment, assignment_by_id, boundary_ids, adjacent_versions, s1_cells = collected
    work_cells: dict[str, dict[date, str]] = {}; consumed: set[str] = set(); adjacent_facts: list[tuple] = []  # noqa: E702
    # ROTA-T052 (R4-02 audit fix): the real interval behind whatever code
    # currently occupies a cell, so a later S1 sharing that day can tell
    # genuine time overlap from mere same-day co-occurrence.
    work_intervals: dict[str, dict[date, tuple[datetime, datetime]]] = {}
    for period in group_into_periods(components):
        if len(period.component_ids) < 2:
            continue
        kind = _classify_period(period, demand_by_assignment, boundary_ids)
        if kind is None:
            if [cid for cid in period.component_ids if cid in demand_by_assignment]:
                raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{period.employee_id}: malformed shared work_period {period.period_key}")
            continue
        consumed.update(period.component_ids)
        if period.start.date() in days:
            work_cells.setdefault(period.employee_id, {})[period.start.date()] = "24"
            work_intervals.setdefault(period.employee_id, {})[period.start.date()] = (period.start, period.end)
        if kind == "linked":
            boundary_cid = next(cid for cid in period.component_ids if cid in boundary_ids)
            a = assignment_by_id[boundary_cid]
            version_id, effective_from = adjacent_versions[boundary_cid]
            adjacent_facts.append((a.employee_id, a.work_period_id, version_id, a.assignment_id, effective_from))
    for (employee_id, day), items in raw_items.items():
        remaining = [(a, d) for a, d in items if _ckey(a) not in consumed]
        if not remaining:
            continue
        if len(remaining) > 1:
            raise ExportProblemError("MULTIPLE_WORK_ITEMS_PER_CELL", f"{employee_id}/{day} has {len(remaining)} independent work items")
        assignment, demand = remaining[0]
        work_cells.setdefault(employee_id, {})[day] = _map_work_code(assignment, demand, settings, extra_codes)
        work_intervals.setdefault(employee_id, {})[day] = (assignment.start_datetime, assignment.end_datetime)
    # ROTA-T052 (T52-06/T52-08/T52-12, R4-02 audit fix): S1 sharing a
    # calendar day with another work item is only a real problem when their
    # intervals actually overlap -- a HARD violation the validator would
    # already have flagged, but T037 never blocks a save on a HARD
    # violation, so a forced-through overlap can still reach export and
    # must still be rejected here. A legal, non-overlapping same-day pair
    # (e.g. S1 10-14 + N 18-06) combines into one cell instead.
    for employee_id, by_day in s1_cells.items():
        for day, s1_interval in by_day.items():
            existing_codes = work_cells.setdefault(employee_id, {})
            existing_intervals = work_intervals.setdefault(employee_id, {})
            other_interval = existing_intervals.get(day)
            if other_interval is not None and _intervals_overlap(s1_interval, other_interval):
                raise ExportProblemError("MULTIPLE_WORK_ITEMS_PER_CELL", f"{employee_id}/{day} has both S1 and an overlapping work item")
            if day in existing_codes:
                existing_codes[day] = f"{existing_codes[day]}/S1"
            else:
                existing_codes[day] = "S1"
            existing_intervals[day] = s1_interval
    return work_cells, sorted(adjacent_facts)
def _map_work_code(assignment, demand, settings, extra_codes: dict) -> str:
    duration_hours = (assignment.end_datetime - assignment.start_datetime).total_seconds() / 3600
    family = demand.shift_kind.value if demand.shift_kind else None
    anchor = demand.start_datetime.date()
    candidates = []
    for code, interval in settings.work_code_intervals.items():
        if interval is None or family is None or not code.startswith(family):
            continue
        if site_repository.FROZEN_WORK_CODE_HOURS[code] != duration_hours:
            continue
        start, end = _interval_bounds(anchor, interval)
        if assignment.start_datetime == start and assignment.end_datetime == end:
            candidates.append(code)
    # ROTA-T056 section 9.2: monthly D6+/N6+ extra codes -- same exact-match
    # rule (R8-02 fix: full datetime, not HH:MM + crosses-midnight bool), no
    # FROZEN_WORK_CODE_HOURS lookup (duration is derived from the interval).
    for code, interval in extra_codes.items():
        if family is None or not code.startswith(family):
            continue
        start, end = _interval_bounds(anchor, interval)
        if assignment.start_datetime == start and assignment.end_datetime == end:
            candidates.append(code)
    if not candidates:
        raise ExportProblemError("WORK_CODE_MAPPING_REQUIRED", f"{assignment.assignment_id}: no configured code matches its interval")
    return candidates[0]
# Absence presentation (Sections 12-15) -- print symbols only, never Assignment.
# T23-35: reads the same canonical absence_reference_snapshots WorkBalance/analytics/solver already consume, never its own recount.
def _legal_uc_value(code: str, reserve_hours: dict) -> Optional[int]:
    return {"U1": 12, "U2": 16, "C1": 12, "C2": 16}.get(code, reserve_hours.get(code))
def _pair_values(letter: str, base_regime: str, reserve_hours: dict) -> dict:
    plan_by_value: dict[int, str] = {}
    for code in PLAN_PRIORITY:
        value = site_repository.FROZEN_WORK_CODE_HOURS[code]
        if base_regime == "12h" and value == 24:
            continue
        plan_by_value.setdefault(value, code)
    uc_by_value: dict[int, str] = {}
    for i in range(1, 6):
        code = f"{letter}{i}"
        value = _legal_uc_value(code, reserve_hours)
        if value is not None:
            uc_by_value.setdefault(value, code)
    return {v: (plan_by_value[v], uc_by_value[v]) for v in plan_by_value if v in uc_by_value}
def _minimal_sequence(total_hours: int, values_by_rank: list[int], employee_id: str, letter: str) -> list[int]:
    INF = float("inf")
    best = [0] + [INF] * total_hours
    for amount in range(1, total_hours + 1):
        for v in values_by_rank:
            if v <= amount and best[amount - v] + 1 < best[amount]:
                best[amount] = best[amount - v] + 1
    if best[total_hours] == INF:
        raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", f"{employee_id}: no exact {letter} decomposition for {total_hours}h")
    sequence, remaining = [], total_hours
    while remaining > 0:
        for v in values_by_rank:
            if v <= remaining and best[remaining - v] == best[remaining] - 1:
                sequence.append(v)
                remaining -= v
                break
    return sequence
def _decompose(employee_id: str, letter: str, span: list[date], qualifying: list[date], total_hours: int, settings) -> list[tuple]:
    pairs_by_value = _pair_values(letter, settings.base_regime, settings.reserve_hours)  # PRE_PLAN_LEAVE only (T23-43), coin-change unchanged
    if not qualifying:
        return [(d, f"{letter}~", f"{letter}~") for d in span]
    values_by_rank = sorted(pairs_by_value, key=lambda v: PLAN_PRIORITY.index(pairs_by_value[v][0]))
    sequence = _minimal_sequence(total_hours, values_by_rank, employee_id, letter)
    if len(sequence) > len(qualifying):
        raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", f"{employee_id}: decomposition needs more cells than available")
    symbol_dates = qualifying[: len(sequence)]
    pairs = [(symbol_dates[i], *pairs_by_value[v]) for i, v in enumerate(sequence)]
    pairs += [(d, f"{letter}~", f"{letter}~") for d in span if d not in symbol_dates]
    return pairs
def _decompose_pre_plan(employee_id, pre_plan_days, settings) -> list[tuple]:
    pairs: list[tuple] = []  # T046: letter follows each day's real kind (C=SICK_LEAVE, U=LEAVE_GRANTED), mirrors _post_plan_pair
    for kind, letter in ((AvailabilityKind.SICK_LEAVE, "C"), (AvailabilityKind.LEAVE_GRANTED, "U")):
        span, qualifying = [d for d, day in pre_plan_days if day.kind == kind], [(d, day.canonical_hours) for d, day in pre_plan_days if day.kind == kind and day.canonical_hours]  # noqa: E501
        pairs += _decompose(employee_id, letter, span, [d for d, _ in qualifying], sum(h for _, h in qualifying), settings)
    return pairs
def _detailed_facts(snapshots) -> list[DetailedDailyAbsenceFact]:
    # T026-2: mechanical persisted-to-pure mapping only -- no precedence/range/arithmetic; canonical_site_absence_days owns that.
    facts = []
    for record, snapshot in snapshots:
        for day in snapshot.days:
            periods = tuple(
                DetailedAbsencePeriodFact(
                    p.assignment_id, p.schedule_version_id, p.site_id, p.covers_demand_id, p.work_period_id,
                    p.start_datetime, p.end_datetime, p.shift_kind, p.catalog_kind, p.required_rest_hours,
                    p.work_period_template_id, p.work_period_component,
                )
                for p in day.periods
            )
            facts.append(DetailedDailyAbsenceFact(day.the_date, record.kind, day.source_mode, day.status, day.hours, periods))
    return facts
def _post_plan_pair(employee_id, day, settings) -> list[tuple]:
    if day.site_hours == 0:
        return []  # accepted rest, or no bound period at this Site -- no synthetic U/C (T23-42)
    letter = "C" if day.kind == AvailabilityKind.SICK_LEAVE else "U"
    pairs_by_value = _pair_values(letter, settings.base_regime, settings.reserve_hours)
    if day.site_hours not in pairs_by_value:
        raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", f"{employee_id}/{day.the_date}: no exact {day.site_hours}h POST_PLAN code")
    plan_code, uc_code = pairs_by_value[day.site_hours]
    shift_kinds = {p.shift_kind for p in day.site_periods if p.shift_kind}
    if len(shift_kinds) == 1:  # C-R15-2: the immutable bound shift_kind owns D/N presentation, not duration alone
        kind_letter = next(iter(shift_kinds))
        family_codes = [c for c in PLAN_PRIORITY if c.startswith(kind_letter) and site_repository.FROZEN_WORK_CODE_HOURS[c] == day.site_hours and not (settings.base_regime == "12h" and day.site_hours == 24)]
        if not family_codes:
            raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", f"{employee_id}/{day.the_date}: no exact {day.site_hours}h {kind_letter}-family POST_PLAN code")
        plan_code = family_codes[0]
    return [(day.the_date, plan_code, uc_code)]
def _collect_absence(conn, days, local_ids, work_cells, settings, site_id) -> dict[str, list[tuple]]:
    # C-R15-3: discovery is never gated on currently-enabled Site membership -- a bound period keeps an Employee here even after that membership is later disabled; local_ids only decides PRE_PLAN's own fail-closed attribution below.
    month_start, month_end = days[0], days[-1]
    all_employee_ids = [e.employee_id for e in employee_repository.list_employees(conn)]
    records = list_active_overlapping_for_employees(conn, all_employee_ids, month_start, month_end)
    by_employee: dict[str, list] = {}
    for r in records:
        by_employee.setdefault(r.employee_id, []).append(r)
    memberships_by_employee = employee_repository.list_memberships_for_employees(conn, sorted(by_employee))
    result: dict[str, list[tuple]] = {}
    for employee_id in sorted(by_employee):
        emp_records = [r for r in by_employee[employee_id] if r.kind in (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)]
        if not emp_records:
            continue
        snapshots = [(r, get_absence_reference_snapshot(conn, r.availability_version_id)) for r in emp_records]
        bound_here = any(p.site_id == site_id for _, snap in snapshots if snap for day in snap.days for p in day.periods)
        if employee_id not in local_ids and not bound_here:
            continue  # dormant/unrelated: not this Site's business, never creates a row or MISSING
        for r, snapshot in snapshots:  # brief.md section 14 (NO LEGACY BACKFILL), same as WorkBalance/analytics (B-R12-1)
            if snapshot is None:
                raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", f"{employee_id}: legacy active {r.kind.value} has no captured reference snapshot")
        enabled_local = sum(1 for m in memberships_by_employee.get(employee_id, []) if m.membership_kind == MembershipKind.LOCAL and m.enabled)
        try:
            canonical_days = canonical_site_absence_days(_detailed_facts(snapshots), range_start=month_start, range_end=month_end, site_id=site_id)
        except IncompleteAbsenceReferenceError as exc:
            raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", f"{employee_id}: {exc}") from exc
        pairs = _absence_pairs_for_employee(employee_id, canonical_days, work_cells, settings, enabled_local)
        if pairs:
            result[employee_id] = pairs
    return result
def _absence_pairs_for_employee(employee_id, canonical_days, work_cells, settings, enabled_local) -> list[tuple]:
    for day in canonical_days:
        if day.the_date in work_cells.get(employee_id, {}):
            raise ExportProblemError("ASSIGNMENT_ABSENCE_CONFLICT", f"{employee_id}/{day.the_date}: real Assignment on an active absence day")
    pre_plan_days = [(d.the_date, d) for d in canonical_days if d.source_mode == "PRE_PLAN_LEAVE"]
    post_plan_days = [d for d in canonical_days if d.source_mode != "PRE_PLAN_LEAVE"]
    pairs = []
    if pre_plan_days:
        if enabled_local > 1:  # T23-46: keeps the existing fail-closed Site-attribution boundary, else duplicates the global total
            raise ExportProblemError("ABSENCE_SITE_AMBIGUOUS", f"{employee_id} has {enabled_local} enabled LOCAL memberships")
        pairs += _decompose_pre_plan(employee_id, pre_plan_days, settings)
    for day in post_plan_days:
        pairs += _post_plan_pair(employee_id, day, settings)
    return pairs
# Row assembly (Section 11/16)
def _hours_of(code: str, reserve_hours: dict, extra_hours: dict) -> int:
    # ROTA-T052: a combined same-day cell (e.g. "N1/S1", R4-02 audit fix)
    # sums its parts -- S1 itself has no fixed duration and contributes 0
    # here (WorkBalance, not this printed column, owns S1's real hours).
    if "/" in code:
        return sum(_hours_of(part, reserve_hours, extra_hours) for part in code.split("/"))
    if code == "S1":
        return 0
    if code == "24":
        return 24
    if code == BLANK or code.endswith("~"):
        return 0
    if code in site_repository.FROZEN_WORK_CODE_HOURS:
        return site_repository.FROZEN_WORK_CODE_HOURS[code]
    if code in extra_hours:
        # ROTA-T056 section 9.3: a monthly D6+/N6+ code must never silently
        # sum as 0h -- its duration comes from the validated monthly
        # extra-code configuration, never guessed.
        return extra_hours[code]
    if code == DELEGACJA_LABEL:
        # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 7: DELEGACJA's hours
        # are a per-record rate, never a fixed per-code value like the
        # FROZEN_WORK_CODE_HOURS table above -- _build_rows adds the real
        # total once via delegation_hours_in_range, not through this lookup.
        return 0
    return _legal_uc_value(code, reserve_hours) or 0
def _build_rows(
    roster_ids, employees, days, work_cells, absence_by_employee, delegation_by_employee,
    reserve_hours, extra_hours,
) -> list[RowCells]:
    rows = []
    for employee_id in roster_ids:
        employee = employees[employee_id]
        absence_by_date = {d: (p, u) for d, p, u in absence_by_employee.get(employee_id, [])}
        delegation_records = delegation_by_employee.get(employee_id, [])
        delegation_days = _delegation_days(delegation_records, days[0], days[-1])
        emp_work = work_cells.get(employee_id, {})
        plan, wyk = [], []
        for day in days:
            if day in emp_work:
                # ROTA-DELEGACJA-ABSENCE-KIND audit R2 (tests_r2.txt R2-01):
                # same reasoning as _build_ordinary_rows above -- a saved
                # manual-correction decision must not become a hard export
                # block; show the real work code as usual.
                plan.append(emp_work[day]); wyk.append(emp_work[day])  # noqa: E702
            elif day in delegation_days:
                plan.append(DELEGACJA_LABEL); wyk.append(DELEGACJA_LABEL)  # noqa: E702
            elif day in absence_by_date:
                plan_code, uc_code = absence_by_date[day]
                plan.append(plan_code); wyk.append(uc_code)  # noqa: E702
            else:
                plan.append(BLANK); wyk.append(BLANK)  # noqa: E702
        try:
            delegation_hours = delegation_hours_in_range(delegation_records, employee_id, days[0], days[-1])
        except IncompleteDelegationHoursError as exc:
            raise ExportProblemError("ABSENCE_REFERENCE_INCOMPLETE", str(exc)) from exc
        rows.append(RowCells(
            employee_id=employee_id, display_name=employee.display_name, plan=plan, wyk=wyk,
            plan_hours=sum(_hours_of(c, reserve_hours, extra_hours) for c in plan) + delegation_hours,
            wyk_hours=sum(_hours_of(c, reserve_hours, extra_hours) for c in wyk) + delegation_hours,
            urlop_hours=sum(_hours_of(c, reserve_hours, extra_hours) for c in wyk if c.startswith("U")),
            l4_hours=sum(_hours_of(c, reserve_hours, extra_hours) for c in wyk if c.startswith("C")),
        ))
    rows.sort(key=lambda r: (r.display_name.casefold(), r.employee_id))
    return rows


# --- ROTA-EXCEL-VBA-ENGINE-ADAPTER Codex R5-01 fix: shared day-grid for an
# Assignment list that is NOT (yet) a persisted ScheduleVersion -- a PLAN/
# REPLAN candidate, or the currently accepted version's own assignments
# read back for the external Excel API. brief.md section 8/XL-12: one
# shared projection owner for PDF and Excel, never a second classification
# in a router. Unlike build_schedule_projection (which reads a real,
# possibly multi-version ScheduleVersion lineage and collapses D+N pairs
# into a persisted "24" via work_period_id bookkeeping), this works from a
# bare in-memory Assignment list with no lineage/24h-period concept --
# multiple legal, non-overlapping same-day PRIMARY pieces for one employee
# join with "/", matching MonthlyPlanning.tsx's own display convention,
# and every piece's hours count toward the total (Codex R5-01: the
# earlier per-router implementation kept only the LAST same-day
# Assignment, silently discarding real worked hours).


def build_ad_hoc_day_grid(
    assignments: list[Assignment], demands_by_id: dict, days: list[date],
    delegation_by_employee: dict[str, list],
) -> dict[str, tuple[list[str], int]]:
    by_employee_day: dict[str, dict[date, list[Assignment]]] = {}
    for a in assignments:
        if a.state == AssignmentState.CANCELLED:
            continue
        by_employee_day.setdefault(a.employee_id, {}).setdefault(a.start_datetime.date(), []).append(a)

    result: dict[str, tuple[list[str], int]] = {}
    employee_ids = set(by_employee_day) | set(delegation_by_employee)
    for employee_id in employee_ids:
        emp_days = by_employee_day.get(employee_id, {})
        records = [r for r in delegation_by_employee.get(employee_id, []) if r.kind == AvailabilityKind.DELEGACJA]
        covered_delegation_days = _delegation_days(records, days[0], days[-1])
        cells: list[str] = []
        total_hours = 0
        for day in days:
            pieces = emp_days.get(day)
            if pieces:
                codes = []
                for a in pieces:
                    if a.operational_code:
                        codes.append(a.operational_code)
                    elif a.role == AssignmentRole.PERIODIC_TRAINING:
                        codes.append("S1")
                    else:
                        demand = demands_by_id.get(a.covers_demand_id) if a.covers_demand_id else None
                        codes.append(demand.shift_kind.value if demand and demand.shift_kind else "?")
                    if a.role in (AssignmentRole.PRIMARY, AssignmentRole.PERIODIC_TRAINING):
                        total_hours += round((a.end_datetime - a.start_datetime).total_seconds() / 3600)
                cells.append("/".join(codes))
            elif day in covered_delegation_days:
                cells.append(DELEGACJA_LABEL)
            else:
                cells.append("")
        total_hours += delegation_hours_in_range(records, employee_id, days[0], days[-1])
        result[employee_id] = (cells, total_hours)
    return result
