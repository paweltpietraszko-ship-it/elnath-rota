"""ROTA-T020 Checkpoint B -- printable schedule PDF export (READ/PRESENTATION only; never touches solver/lifecycle write paths). No SQL here -- only existing repositories."""
from __future__ import annotations
import hashlib
import io
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Union
import reportlab
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rota.domain import AssignmentRole, AssignmentState, AvailabilityKind, MembershipKind, ShiftCatalogKind
from rota.persistence import calendar_repository, employee_repository, schedule_repository, site_repository
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.persistence.availability_repository import list_active_overlapping_for_employees
from rota.persistence.schedule_errors import ScheduleVersionNotFound
from rota.planning.absence import DetailedAbsencePeriodFact, DetailedDailyAbsenceFact, IncompleteAbsenceReferenceError, canonical_site_absence_days
from rota.planning.work_periods import PeriodComponent, group_into_periods
PLAN_PRIORITY = ("D1", "D2", "D3", "D4", "D5", "N1", "N2", "N3", "N4", "N5")
BLANK = "–"
class ExportProblemError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message; super().__init__(f"{code}: {message}")  # noqa: E702
@dataclass(frozen=True)
class ExportReady:
    pdf_bytes: bytes; document_revision: str; schedule_provenance: str  # noqa: E702
@dataclass(frozen=True)
class ExportProblem:
    problem_code: str; message: str  # noqa: E702
ExportResult = Union[ExportReady, ExportProblem]
@dataclass(frozen=True)
class RowCells:
    employee_id: str; display_name: str; plan: list[str]; wyk: list[str]  # noqa: E702
    plan_hours: int; wyk_hours: int; urlop_hours: int; l4_hours: int  # noqa: E702
@dataclass(frozen=True)
class ExportModel:
    site_id: str; month: date; period_label: str; company_print_name: str; site_print_name: str  # noqa: E702
    base_regime: str; work_code_intervals: dict; reserve_hours: dict; current_version_id: str  # noqa: E702
    lineage: list[tuple[str, Optional[str]]]; days: list[date]; rows: list[RowCells]  # noqa: E702
    provenance_text: str; holiday_by_date: dict; adjacent_facts: list  # noqa: E702
# Entry point
def generate_schedule_pdf(
    conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str, generated_at: Optional[datetime] = None,
) -> ExportResult:
    try:
        model = _assemble_export_model(conn, site_id=site_id, month=month, period_label=period_label)
        pdf_bytes = _render_pdf(model, generated_at or datetime.now(timezone.utc))
    except ExportProblemError as exc:
        return ExportProblem(exc.code, exc.message)
    except site_repository.InvalidSitePrintSettings as exc:
        return ExportProblem("PRINT_SETTINGS_INVALID", str(exc))
    return ExportReady(pdf_bytes=pdf_bytes, document_revision=_document_revision(model), schedule_provenance=model.provenance_text)
# Assembly
def _assemble_export_model(conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str) -> ExportModel:
    if month.day != 1:
        raise ExportProblemError("PROVENANCE_INCOMPLETE", "month must be the first day of the month")
    settings = site_repository.get_site_print_settings(conn, site_id)
    if settings is None:
        raise ExportProblemError("PRINT_SETTINGS_MISSING", f"no print settings saved for {site_id}")
    lineage = _reconstruct_lineage(conn, site_id, month)
    days = _month_days(month)
    snapshots: dict[str, "schedule_repository.ScheduleSnapshot"] = {}
    daily_version = {d: _version_for_date(lineage, d) for d in days}
    memberships = employee_repository.list_memberships_for_site(conn, site_id)
    local_ids = {m.employee_id for m in memberships if m.membership_kind == MembershipKind.LOCAL and m.enabled}
    collected = _collect_real_work_cells(conn, site_id, days, daily_version, snapshots, settings)
    seen_employee_ids = collected[2]
    work_cells, adjacent_facts = _apply_24h_periods(collected, settings, days)
    calendar_days = calendar_repository.list_calendar_days(conn, days[0], days[-1])
    holiday_by_date = {c.date: c.holiday for c in calendar_days}
    absence_by_employee = _collect_absence(conn, days, local_ids, work_cells, settings, site_id)
    roster_ids = local_ids | seen_employee_ids | set(absence_by_employee)  # C-R15-3: a bound Site period keeps an Employee here after REPLAN
    employees = employee_repository.list_employees_by_ids(conn, list(roster_ids))
    rows = _build_rows(roster_ids, employees, days, work_cells, absence_by_employee, settings.reserve_hours)
    provenance = _provenance_text(lineage, adjacent_facts)
    return ExportModel(
        site_id=site_id, month=month, period_label=period_label,
        company_print_name=settings.company_print_name, site_print_name=settings.site_print_name,
        base_regime=settings.base_regime, work_code_intervals=settings.work_code_intervals,
        reserve_hours=settings.reserve_hours, current_version_id=lineage[-1].version_id,
        lineage=[(h.version_id, h.effective_from.isoformat() if h.effective_from else None) for h in lineage],
        days=days, rows=rows, provenance_text=provenance, holiday_by_date=holiday_by_date, adjacent_facts=adjacent_facts,
    )
def _month_days(month: date) -> list[date]:
    import calendar as _cal
    n = _cal.monthrange(month.year, month.month)[1]; return [date(month.year, month.month, d) for d in range(1, n + 1)]  # noqa: E702
def _reconstruct_lineage(conn: sqlite3.Connection, site_id: str, month: date) -> list:
    current_id = schedule_repository.get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise ExportProblemError("NO_CURRENT_SCHEDULE", f"no current ScheduleVersion for ({site_id}, {month})")
    # ROTA-T023b (frozen addendum section 4, presentation/export enforcement):
    # one pre-render gate using the shared schedule-repository predicate --
    # never reimplemented here. A missing/corrupt current_id falls through
    # to the existing lineage walk below, which already raises its own
    # PROVENANCE_INCOMPLETE for that case.
    try:
        requires_regime_replan = schedule_repository.version_requires_regime_replan(conn, current_id)
    except ScheduleVersionNotFound:
        requires_regime_replan = False
    if requires_regime_replan:
        raise ExportProblemError("REGIME_REPLAN_REQUIRED", f"{current_id}: regime replan required before export")
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
def _provenance_text(lineage: list, adjacent_facts: list) -> str:
    # Adjacent facts actually used for collapse/suppression must affect displayed provenance, not only document_revision (R6 Section 7 / R10-3).
    ordered = [(h.version_id, h.effective_from.isoformat() if h.effective_from else "") for h in lineage]
    digest = hashlib.sha256(json.dumps([ordered, adjacent_facts], sort_keys=True).encode("utf-8")).hexdigest()
    return f"Schedule provenance: {lineage[-1].version_id} / lineage-sha256:{digest}"
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
def _validate_item(a, demand) -> None:
    if a.role == AssignmentRole.TRAINEE:
        raise ExportProblemError("UNSUPPORTED_TRAINEE_PRINT", f"{a.assignment_id} is an effective TRAINEE assignment")
    if demand is None:
        raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{a.assignment_id} has no coherent covered demand")
    if a.start_datetime != demand.start_datetime or a.end_datetime != demand.end_datetime:
        raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{a.assignment_id}: actual interval contradicts its covered demand")
    if demand.catalog_kind == ShiftCatalogKind.OTHER:
        raise ExportProblemError("UNSUPPORTED_SHIFT_KIND", f"{a.assignment_id} covers an INNY demand")
def _ckey(a) -> str:
    return f"{a.schedule_version_id}::{a.assignment_id}"  # identity is (schedule_version_id, assignment_id) -- a bare local id may repeat across ScheduleVersions (R10-2)
def _component(a) -> PeriodComponent:
    return PeriodComponent(_ckey(a), a.employee_id, a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id)
def _collect_real_work_cells(conn, site_id, days, daily_version, snapshots, settings):
    # raw_items/components/seen_ids/demand_by_assignment/assignment_by_id/boundary_ids/adjacent_versions. Raises on TRAINEE/INNY/bad provenance.
    raw_items: dict[tuple[str, date], list] = {}
    components: list[PeriodComponent] = []
    demand_by_assignment: dict = {}; assignment_by_id: dict = {}; seen_employee_ids: set[str] = set()  # noqa: E702
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
            demand = demands_by_id.get(a.covers_demand_id) if a.covers_demand_id else None
            _validate_item(a, demand)
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
    return raw_items, components, seen_employee_ids, demand_by_assignment, assignment_by_id, boundary_ids, adjacent_versions
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
def _apply_24h_periods(collected, settings, days: list[date]):
    raw_items, components, seen_employee_ids, demand_by_assignment, assignment_by_id, boundary_ids, adjacent_versions = collected
    work_cells: dict[str, dict[date, str]] = {}; consumed: set[str] = set(); adjacent_facts: list[tuple] = []  # noqa: E702
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
        work_cells.setdefault(employee_id, {})[day] = _map_work_code(assignment, demand, settings)
    return work_cells, sorted(adjacent_facts)
def _map_work_code(assignment, demand, settings) -> str:
    duration_hours = (assignment.end_datetime - assignment.start_datetime).total_seconds() / 3600
    family = demand.shift_kind.value if demand.shift_kind else None
    crosses_midnight = assignment.end_datetime.date() > assignment.start_datetime.date()
    candidates = []
    for code, interval in settings.work_code_intervals.items():
        if interval is None or family is None or not code.startswith(family):
            continue
        if site_repository.FROZEN_WORK_CODE_HOURS[code] != duration_hours:
            continue
        if interval.start_time == assignment.start_datetime.strftime("%H:%M") and interval.end_time == assignment.end_datetime.strftime("%H:%M") and interval.end_next_day == crosses_midnight:
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
    span, qualifying = [d for d, _ in pre_plan_days], [(d, day.canonical_hours) for d, day in pre_plan_days if day.canonical_hours]
    return _decompose(employee_id, "U", span, [d for d, _ in qualifying], sum(h for _, h in qualifying), settings)
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
def _hours_of(code: str, reserve_hours: dict) -> int:
    if code == "24":
        return 24
    if code == BLANK or code.endswith("~"):
        return 0
    if code in site_repository.FROZEN_WORK_CODE_HOURS:
        return site_repository.FROZEN_WORK_CODE_HOURS[code]
    return _legal_uc_value(code, reserve_hours) or 0
def _build_rows(roster_ids, employees, days, work_cells, absence_by_employee, reserve_hours) -> list[RowCells]:
    rows = []
    for employee_id in roster_ids:
        employee = employees[employee_id]
        absence_by_date = {d: (p, u) for d, p, u in absence_by_employee.get(employee_id, [])}
        emp_work = work_cells.get(employee_id, {})
        plan, wyk = [], []
        for day in days:
            if day in emp_work:
                plan.append(emp_work[day]); wyk.append(emp_work[day])  # noqa: E702
            elif day in absence_by_date:
                plan_code, uc_code = absence_by_date[day]
                plan.append(plan_code); wyk.append(uc_code)  # noqa: E702
            else:
                plan.append(BLANK); wyk.append(BLANK)  # noqa: E702
        rows.append(RowCells(
            employee_id=employee_id, display_name=employee.display_name, plan=plan, wyk=wyk,
            plan_hours=sum(_hours_of(c, reserve_hours) for c in plan), wyk_hours=sum(_hours_of(c, reserve_hours) for c in wyk),
            urlop_hours=sum(_hours_of(c, reserve_hours) for c in wyk if c.startswith("U")), l4_hours=sum(_hours_of(c, reserve_hours) for c in wyk if c.startswith("C")),
        ))
    rows.sort(key=lambda r: (r.display_name.casefold(), r.employee_id))
    return rows
# Document revision (Section 17) -- excludes generated_at/filename/PDF metadata.
def _document_revision(model: ExportModel) -> str:
    payload = {
        "site_id": model.site_id, "month": model.month.isoformat(),
        "date_range": [model.days[0].isoformat(), model.days[-1].isoformat()],
        "period_label": model.period_label, "company_print_name": model.company_print_name, "site_print_name": model.site_print_name,
        "base_regime": model.base_regime,
        "work_code_intervals": {k: (None if v is None else [v.start_time, v.end_time, v.end_next_day]) for k, v in sorted(model.work_code_intervals.items())},
        "reserve_hours": dict(sorted(model.reserve_hours.items())),
        "current_version_id": model.current_version_id, "lineage": model.lineage, "adjacent_facts": model.adjacent_facts,
        "rows": [
            {"employee_id": r.employee_id, "display_name": r.display_name, "plan": r.plan, "wyk": r.wyk,
             "plan_hours": r.plan_hours, "wyk_hours": r.wyk_hours, "urlop_hours": r.urlop_hours, "l4_hours": r.l4_hours}
            for r in model.rows
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
# Font resolution (Section 4) -- no hardcoded machine path; env-driven OS search + ReportLab fallback, first candidate covering Polish wins, else fail closed.
_REQUIRED_POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
_FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC = "T020-Regular", "T020-Bold", "T020-Italic"
def _font_candidates() -> list[tuple[Path, Path, Path]]:
    win = Path(os.environ.get("SystemRoot", os.environ.get("WINDIR", "C:\\Windows"))) / "Fonts"
    rl = Path(reportlab.__file__).resolve().parent / "fonts"
    dejavu, liberation, mac = Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/truetype/liberation"), Path("/Library/Fonts")
    return [
        (win / "arial.ttf", win / "arialbd.ttf", win / "ariali.ttf"),
        (win / "segoeui.ttf", win / "segoeuib.ttf", win / "segoeuii.ttf"),
        (win / "tahoma.ttf", win / "tahomabd.ttf", win / "tahoma.ttf"),
        (dejavu / "DejaVuSans.ttf", dejavu / "DejaVuSans-Bold.ttf", dejavu / "DejaVuSans-Oblique.ttf"),
        (liberation / "LiberationSans-Regular.ttf", liberation / "LiberationSans-Bold.ttf", liberation / "LiberationSans-Italic.ttf"),
        (mac / "Arial.ttf", mac / "Arial Bold.ttf", mac / "Arial Italic.ttf"),
        (rl / "Vera.ttf", rl / "VeraBd.ttf", rl / "VeraIt.ttf"),
    ]
def _covers_polish(font_name: str) -> bool:
    face = pdfmetrics.getFont(font_name).face
    return all(face.charToGlyph.get(ord(ch)) is not None for ch in _REQUIRED_POLISH_CHARS)
def _resolve_unicode_font() -> tuple[str, str, str]:
    if _FONT_REGULAR in pdfmetrics.getRegisteredFontNames() and _covers_polish(_FONT_REGULAR):
        return _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC
    for regular, bold, italic in _font_candidates():
        if not (regular.exists() and bold.exists() and italic.exists()):
            continue
        try:
            for name, path in zip((_FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC), (regular, bold, italic)):
                pdfmetrics.registerFont(TTFont(name, str(path)))
        except Exception:
            continue
        if _covers_polish(_FONT_REGULAR):
            return _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC
    raise ExportProblemError("PRINT_FONT_UNAVAILABLE", "no runtime-resolvable font covers the required Polish glyph set")
# PDF rendering (Section 18) -- accepted Checkpoint A visual baseline: A3 landscape, headers, grid, weekend cue, full legend.
_FILL = {"d": HexColor("#dcdcdc"), "n": HexColor("#a6a6a6"), "h24": HexColor("#595959"), "u": white, "c": white}
_TEXT = {"d": black, "n": black, "h24": white, "u": black, "c": black, "off": HexColor("#8a8a8a")}
_WEEKEND_BG = HexColor("#e2e2e2")
_DOW = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Ni"]
MARGIN, NAME_W, SUM_W = 24.0, 170.0, 48.0
HEADER_H, LEGEND_H, FOOTER_H = 90.0, 150.0, 20.0
def _family(code: str) -> str:
    if code == "24":
        return "h24"
    if code == BLANK:
        return "off"
    return {"D": "d", "N": "n", "U": "u", "C": "c"}.get(code[0], "off")
def _row_height(n_rows: int) -> float:
    return max(22.0, min(46.0, (22.0 * 2 * 10) / max(1, 2 * n_rows)))
def _fit_font_size(text: str, font: str, size: float, max_width: float, min_size: float = 6.5) -> float:
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size
def _check_fits(n_rows: int, row_h: float) -> None:
    available = landscape(A3)[1] - 2 * MARGIN - HEADER_H - LEGEND_H - FOOTER_H
    if n_rows * 2 * row_h > available:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", f"{n_rows} rows do not fit the accepted single sheet at the {row_h}pt floor")
def _check_header_fits(model: ExportModel, regular: str, bold: str) -> None:
    # T20-36 -- header/period text must fit at a readable floor size or fail closed, never draw clipped/overflowing text (R10-5).
    available = landscape(A3)[0] - 2 * MARGIN
    title = f"{model.company_print_name} — {model.site_print_name}"
    period = f"Okres: {model.period_label}   Zakres dat: {model.days[0].isoformat()} — {model.days[-1].isoformat()}"
    if pdfmetrics.stringWidth(title, bold, 10.0) > available:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", "company/site header exceeds the accepted readability floor")
    if pdfmetrics.stringWidth(period, regular, 7.0) > available:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", "period label exceeds the accepted readability floor")
def _draw_day_headers(c, day_w, days, holiday_by_date, bold, y) -> float:
    x = MARGIN + NAME_W
    for d in days:
        if d.weekday() >= 5 or holiday_by_date.get(d, False):
            c.setFillColor(_WEEKEND_BG); c.rect(x, y - 30, day_w, 30, stroke=0, fill=1); c.setFillColor(black)  # noqa: E702
        c.setFont(bold, 6.5); c.drawCentredString(x + day_w / 2, y - 10, _DOW[d.weekday()])  # noqa: E702
        c.setFont(bold, 8); c.drawCentredString(x + day_w / 2, y - 24, str(d.day))  # noqa: E702
        x += day_w
    for label in ("Plan g.", "Wyk. g.", "Urlop g.", "L4 g."):
        c.setFont(bold, 6.5); c.drawCentredString(x + SUM_W / 2, y - 18, label)  # noqa: E702
        x += SUM_W
    return y - 32
def _draw_cell(c, x, y, row_h, day_w, code, bold) -> None:
    fam = _family(code)
    c.setStrokeColor(HexColor("#c8c8c8")); c.setLineWidth(0.4)  # noqa: E702
    c.rect(x, y - row_h, day_w, row_h, stroke=1, fill=0)
    fill = _FILL.get(fam)
    if fill is not None:
        c.setFillColor(fill)
        c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=0, fill=1)
    if fam == "u":
        c.setStrokeColor(black); c.setLineWidth(1.0)  # noqa: E702
        c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
    elif fam == "c":
        c.setStrokeColor(black); c.setDash(2, 1.5)  # noqa: E702
        c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
        c.setDash()
    c.setFillColor(_TEXT.get(fam, black)); c.setFont(bold, 6.5)  # noqa: E702
    c.drawCentredString(x + day_w / 2, y - row_h + 5, "" if code == BLANK or code.endswith("~") else code)
    c.setFillColor(black)
def _draw_subrow(c, y, row_h, day_w, label, cells, row, regular, bold) -> None:
    x = MARGIN
    if label == "PLAN":
        c.setFont(regular, _fit_font_size(row.display_name, regular, 7, NAME_W - 40)); c.drawString(x + 2, y - row_h + 5, row.display_name)  # noqa: E702
    c.setFont(regular, 6.5); c.drawRightString(x + NAME_W - 2, y - row_h + 5, label)  # noqa: E702
    x += NAME_W
    for code in cells:
        _draw_cell(c, x, y, row_h, day_w, code, bold)
        x += day_w
    for value in (row.plan_hours if label == "PLAN" else row.wyk_hours, "", row.urlop_hours, row.l4_hours):
        c.setFont(regular, 7); c.drawCentredString(x + SUM_W / 2, y - row_h + 5, "" if value == "" else str(value))  # noqa: E702
        x += SUM_W
def _legend_line(letter: str, slot: int, value, demo: bool) -> str:
    code = f"{letter}{slot}"
    return f"{code} = — (rezerwa)" if value is None else f"{code} = {value}h" + (" (konfiguracja demo)" if demo else "")
def _legend_value(letter: str, slot: int, reserve_hours: dict) -> tuple:
    if letter in "DN":
        return site_repository.FROZEN_WORK_CODE_HOURS[f"{letter}{slot}"], False
    base = {"U1": 12, "U2": 16, "C1": 12, "C2": 16}.get(f"{letter}{slot}")
    value = base if base is not None else reserve_hours.get(f"{letter}{slot}")
    return value, base is None and value is not None
def _draw_legend(c, model: ExportModel, regular, bold, italic, y: float) -> float:
    c.setFont(bold, 10); c.drawString(MARGIN, y, "Legenda — tabela wartości godzinowych (wartości właściciela, nie normalizowane)"); y -= 15  # noqa: E702
    col_w = (landscape(A3)[0] - 2 * MARGIN) / 2
    sub_w = col_w / 2
    for slot in range(1, 6):
        for j, letter in enumerate("DNUC"):
            value, demo = _legend_value(letter, slot, model.reserve_hours)
            c.setFont(regular, 9); c.drawString(MARGIN + (j // 2) * col_w + (j % 2) * sub_w, y, _legend_line(letter, slot, value, demo))  # noqa: E702
        y -= 12
    c.setFont(regular, 9); c.drawString(MARGIN, y, "24 = pełny okres 24h w dniu rozpoczęcia"); y -= 14  # noqa: E702
    c.setFont(italic, 8); c.drawString(MARGIN, y, "Rezerwa = zdefiniowany slot bez wartości. Numer NIE oznacza wspólnej wartości dla wszystkich liter (np. D4=2h, N4=24h)."); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, "Druk czarno-biały: D/N/24 = gęstość wypełnienia, U = obwódka ciągła, C = obwódka przerywana — czytelne bez koloru.")
    return y - 12
def _render_pdf(model: ExportModel, generated_at: datetime) -> bytes:
    regular, bold, italic = _resolve_unicode_font()
    page_w, page_h = landscape(A3)
    day_w = (page_w - 2 * MARGIN - NAME_W - 4 * SUM_W) / len(model.days)
    row_h = _row_height(len(model.rows))
    _check_fits(len(model.rows), row_h)
    _check_header_fits(model, regular, bold)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A3))
    y = page_h - MARGIN
    c.setFont(bold, 16); c.drawString(MARGIN, y, f"{model.company_print_name} — {model.site_print_name}"); y -= 18  # noqa: E702
    c.setFont(regular, 9.5); c.drawString(MARGIN, y, f"Okres: {model.period_label}   Zakres dat: {model.days[0].isoformat()} — {model.days[-1].isoformat()}"); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, model.provenance_text); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, f"Revision: {_document_revision(model)}   Wygenerowano: {generated_at.isoformat()}"); y -= 16  # noqa: E702
    y = _draw_day_headers(c, day_w, model.days, model.holiday_by_date, bold, y)
    for row in model.rows:
        for label, cells in (("PLAN", row.plan), ("WYK", row.wyk)):
            _draw_subrow(c, y, row_h, day_w, label, cells, row, regular, bold)
            y -= row_h
    y -= 10
    _draw_legend(c, model, regular, bold, italic, y)
    c.showPage()
    c.save()
    return buf.getvalue()
