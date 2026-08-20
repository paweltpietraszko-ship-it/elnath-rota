"""ROTA-T020 Checkpoint B -- printable schedule PDF export.

tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md: a READ/PRESENTATION feature only.
Never changes solver decisions, Assignment coverage, Availability, T018
absence accounting, WorkBalance, or ScheduleVersion lifecycle. U/C print
symbols are a paper convention filled into otherwise-empty qualifying
absence cells; they never become operational Assignments and never reduce
real Site demand.

No SQL lives here -- only calls into existing persistence repositories.
"""
from __future__ import annotations

import hashlib
import io
import json
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
from rota.persistence.availability_repository import list_active_overlapping_for_employees
from rota.persistence.schedule_errors import ScheduleVersionNotFound
from rota.planning.absence import EXCUSED_ABSENCE_HOURS_PER_DAY, IncompleteAbsenceCalendarError, excused_absence_days_in_month
from rota.planning.work_periods import PeriodComponent, group_into_periods

PLAN_PRIORITY = ("D1", "D2", "D3", "D4", "D5", "N1", "N2", "N3", "N4", "N5")
BLANK = "–"  # "-"


class ExportProblemError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class ExportReady:
    pdf_bytes: bytes
    document_revision: str
    schedule_provenance: str


@dataclass(frozen=True)
class ExportProblem:
    problem_code: str
    message: str


ExportResult = Union[ExportReady, ExportProblem]


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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_schedule_pdf(
    conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str, generated_at: Optional[datetime] = None,
) -> ExportResult:
    try:
        model = _assemble_export_model(conn, site_id=site_id, month=month, period_label=period_label)
        pdf_bytes = _render_pdf(model, generated_at or datetime.now(timezone.utc))
    except ExportProblemError as exc:
        return ExportProblem(exc.code, exc.message)
    return ExportReady(
        pdf_bytes=pdf_bytes, document_revision=_document_revision(model), schedule_provenance=model.provenance_text,
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

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

    collected = _collect_real_work_cells(conn, days, daily_version, snapshots, settings)
    seen_employee_ids = collected[2]
    work_cells = _apply_24h_periods(collected, settings)

    roster_ids = set(local_ids) | seen_employee_ids
    employees = employee_repository.list_employees_by_ids(conn, list(roster_ids))
    absence_by_employee = _collect_absence(conn, month, days, local_ids, work_cells, settings)

    rows = _build_rows(roster_ids, employees, days, work_cells, absence_by_employee, settings.reserve_hours)
    provenance = _provenance_text(lineage)
    return ExportModel(
        site_id=site_id, month=month, period_label=period_label,
        company_print_name=settings.company_print_name, site_print_name=settings.site_print_name,
        base_regime=settings.base_regime, work_code_intervals=settings.work_code_intervals,
        reserve_hours=settings.reserve_hours, current_version_id=lineage[-1].version_id,
        lineage=[(h.version_id, h.effective_from.isoformat() if h.effective_from else None) for h in lineage],
        days=days, rows=rows, provenance_text=provenance,
    )


def _month_days(month: date) -> list[date]:
    import calendar as _cal
    n = _cal.monthrange(month.year, month.month)[1]
    return [date(month.year, month.month, d) for d in range(1, n + 1)]


def _reconstruct_lineage(conn: sqlite3.Connection, site_id: str, month: date) -> list:
    current_id = schedule_repository.get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise ExportProblemError("NO_CURRENT_SCHEDULE", f"no current ScheduleVersion for ({site_id}, {month})")
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


def _provenance_text(lineage: list) -> str:
    ordered = [(h.version_id, h.effective_from.isoformat() if h.effective_from else "") for h in lineage]
    digest = hashlib.sha256(json.dumps(ordered, sort_keys=True).encode("utf-8")).hexdigest()
    return f"Schedule provenance: {lineage[-1].version_id} / lineage-sha256:{digest}"


# ---------------------------------------------------------------------------
# Real work cells (Section 10)
# ---------------------------------------------------------------------------

def _collect_real_work_cells(conn, days, daily_version, snapshots, settings):
    """Returns (work_cells: {employee_id: {date: code}}, components: list[PeriodComponent]
    for 24h detection, seen_employee_ids: set[str]). Raises ExportProblemError for any
    TRAINEE/INNY/missing-provenance item -- one bad item fails the whole export."""
    raw_items: dict[tuple[str, date], list] = {}
    components: list[PeriodComponent] = []
    seen_employee_ids: set[str] = set()
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
            if a.role == AssignmentRole.TRAINEE:
                raise ExportProblemError("UNSUPPORTED_TRAINEE_PRINT", f"{a.assignment_id} is an effective TRAINEE assignment")
            demand = demands_by_id.get(a.covers_demand_id) if a.covers_demand_id else None
            if demand is None:
                raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"{a.assignment_id} has no coherent covered demand")
            if demand.catalog_kind == ShiftCatalogKind.OTHER:
                raise ExportProblemError("UNSUPPORTED_SHIFT_KIND", f"{a.assignment_id} covers an INNY demand")
            seen_employee_ids.add(a.employee_id)
            raw_items.setdefault((a.employee_id, day), []).append((a, demand))
            components.append(PeriodComponent(
                a.assignment_id, a.employee_id, a.start_datetime, a.end_datetime,
                a.work_period_id, a.required_rest_after_hours, a.schedule_version_id,
            ))
    return raw_items, components, seen_employee_ids


def _apply_24h_periods(raw_items_and_components, settings):
    raw_items, components, seen_employee_ids = raw_items_and_components
    work_cells: dict[str, dict[date, str]] = {}
    consumed: set[str] = set()
    for period in group_into_periods(components):
        if len(period.component_ids) != 2:
            continue
        total_hours = (period.end - period.start).total_seconds() / 3600
        if total_hours != 24:
            continue
        consumed.update(period.component_ids)
        work_cells.setdefault(period.employee_id, {})[period.start.date()] = "24"

    for (employee_id, day), items in raw_items.items():
        remaining = [(a, d) for a, d in items if a.assignment_id not in consumed]
        if not remaining:
            continue
        if len(remaining) > 1:
            raise ExportProblemError("MULTIPLE_WORK_ITEMS_PER_CELL", f"{employee_id}/{day} has {len(remaining)} independent work items")
        assignment, demand = remaining[0]
        code = _map_work_code(assignment, demand, settings)
        work_cells.setdefault(employee_id, {})[day] = code
    return work_cells


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
        if (
            interval.start_time == assignment.start_datetime.strftime("%H:%M")
            and interval.end_time == assignment.end_datetime.strftime("%H:%M")
            and interval.end_next_day == crosses_midnight
        ):
            candidates.append(code)
    if not candidates:
        raise ExportProblemError("WORK_CODE_MAPPING_REQUIRED", f"{assignment.assignment_id}: no configured code matches its interval")
    if len(candidates) > 1:
        raise ExportProblemError("WORK_CODE_MAPPING_AMBIGUOUS", f"{assignment.assignment_id}: {len(candidates)} candidate codes")
    return candidates[0]


# ---------------------------------------------------------------------------
# Absence presentation (Sections 12-15) -- print symbols only, never Assignment.
# ---------------------------------------------------------------------------

def _span_dates(records, kind, month_start, month_end) -> list[date]:
    dates: set[date] = set()
    for r in records:
        if not r.active or r.kind != kind:
            continue
        d = max(r.start_date, month_start)
        end = min(r.end_date, month_end)
        while d <= end:
            dates.add(d)
            d += timedelta(days=1)
    return sorted(dates)


def _qualifying_subset(span: list[date], holiday_by_date: dict) -> list[date]:
    return [d for d in span if d.isoweekday() <= 5 and not holiday_by_date.get(d, False)]


def _validate_calendar_coverage(records, kind, month, calendar_days) -> None:
    try:
        excused_absence_days_in_month(records, month, kinds=(kind,), calendar_days=tuple(calendar_days))
    except IncompleteAbsenceCalendarError as exc:
        raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", str(exc)) from exc


def _legal_uc_value(code: str, reserve_hours: dict) -> Optional[int]:
    base = {"U1": 12, "U2": 16, "C1": 12, "C2": 16}
    return base.get(code, reserve_hours.get(code))


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


def _decompose(employee_id: str, letter: str, span: list[date], qualifying: list[date], settings) -> list[tuple]:
    pairs_by_value = _pair_values(letter, settings.base_regime, settings.reserve_hours)
    if not qualifying:
        return [(d, f"{letter}~", f"{letter}~") for d in span]
    values_by_rank = sorted(pairs_by_value, key=lambda v: PLAN_PRIORITY.index(pairs_by_value[v][0]))
    total_hours = len(qualifying) * EXCUSED_ABSENCE_HOURS_PER_DAY
    sequence = _minimal_sequence(total_hours, values_by_rank, employee_id, letter)
    if len(sequence) > len(qualifying):
        raise ExportProblemError("ABSENCE_DECOMPOSITION_REQUIRED", f"{employee_id}: decomposition needs more cells than available")
    symbol_dates = qualifying[: len(sequence)]
    pairs = [(symbol_dates[i], *pairs_by_value[v]) for i, v in enumerate(sequence)]
    pairs += [(d, f"{letter}~", f"{letter}~") for d in span if d not in symbol_dates]
    return pairs


def _collect_absence(conn, month, days, local_ids, work_cells, settings) -> dict[str, list[tuple]]:
    if not local_ids:
        return {}
    month_start, month_end = days[0], days[-1]
    calendar_days = calendar_repository.list_calendar_days(conn, month_start, month_end)
    holiday_by_date = {c.date: c.holiday for c in calendar_days}
    records = list_active_overlapping_for_employees(conn, sorted(local_ids), month_start, month_end)
    by_employee: dict[str, list] = {}
    for r in records:
        by_employee.setdefault(r.employee_id, []).append(r)

    result: dict[str, list[tuple]] = {}
    for employee_id in sorted(local_ids):
        emp_records = by_employee.get(employee_id, [])
        if not emp_records:
            continue
        result_pairs = _absence_pairs_for_employee(
            conn, employee_id, emp_records, month, month_start, month_end, calendar_days, holiday_by_date,
            work_cells, settings,
        )
        if result_pairs:
            result[employee_id] = result_pairs
    return result


def _absence_pairs_for_employee(conn, employee_id, emp_records, month, month_start, month_end, calendar_days, holiday_by_date, work_cells, settings):
    _validate_calendar_coverage(emp_records, AvailabilityKind.LEAVE_GRANTED, month, calendar_days)
    _validate_calendar_coverage(emp_records, AvailabilityKind.SICK_LEAVE, month, calendar_days)
    leave_span = _span_dates(emp_records, AvailabilityKind.LEAVE_GRANTED, month_start, month_end)
    sick_span = _span_dates(emp_records, AvailabilityKind.SICK_LEAVE, month_start, month_end)
    if set(leave_span) & set(sick_span):
        raise ExportProblemError("ABSENCE_KIND_CONFLICT", f"{employee_id}: LEAVE_GRANTED/SICK_LEAVE overlap")
    for d in (*leave_span, *sick_span):
        if d in work_cells.get(employee_id, {}):
            raise ExportProblemError("ASSIGNMENT_ABSENCE_CONFLICT", f"{employee_id}/{d}: real Assignment on an active absence day")
    if not leave_span and not sick_span:
        return []
    memberships_all = employee_repository.list_memberships_for_employee(conn, employee_id)
    enabled_local = sum(1 for m in memberships_all if m.membership_kind == MembershipKind.LOCAL and m.enabled)
    if enabled_local > 1:
        raise ExportProblemError("ABSENCE_SITE_AMBIGUOUS", f"{employee_id} has {enabled_local} enabled LOCAL memberships")
    pairs = []
    if leave_span:
        pairs += _decompose(employee_id, "U", leave_span, _qualifying_subset(leave_span, holiday_by_date), settings)
    if sick_span:
        pairs += _decompose(employee_id, "C", sick_span, _qualifying_subset(sick_span, holiday_by_date), settings)
    return pairs


# ---------------------------------------------------------------------------
# Row assembly (Section 11/16)
# ---------------------------------------------------------------------------

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
                plan.append(emp_work[day])
                wyk.append(emp_work[day])
            elif day in absence_by_date:
                plan_code, uc_code = absence_by_date[day]
                plan.append(plan_code)
                wyk.append(uc_code)
            else:
                plan.append(BLANK)
                wyk.append(BLANK)
        rows.append(RowCells(
            employee_id=employee_id, display_name=employee.display_name, plan=plan, wyk=wyk,
            plan_hours=sum(_hours_of(c, reserve_hours) for c in plan),
            wyk_hours=sum(_hours_of(c, reserve_hours) for c in wyk),
            urlop_hours=sum(_hours_of(c, reserve_hours) for c in wyk if c.startswith("U")),
            l4_hours=sum(_hours_of(c, reserve_hours) for c in wyk if c.startswith("C")),
        ))
    rows.sort(key=lambda r: (r.display_name.casefold(), r.employee_id))
    return rows


# ---------------------------------------------------------------------------
# Document revision (Section 17) -- excludes generated_at/filename/PDF metadata.
# ---------------------------------------------------------------------------

def _document_revision(model: ExportModel) -> str:
    payload = {
        "site_id": model.site_id,
        "month": model.month.isoformat(),
        "date_range": [model.days[0].isoformat(), model.days[-1].isoformat()],
        "period_label": model.period_label,
        "company_print_name": model.company_print_name,
        "site_print_name": model.site_print_name,
        "base_regime": model.base_regime,
        "work_code_intervals": {
            k: (None if v is None else [v.start_time, v.end_time, v.end_next_day])
            for k, v in sorted(model.work_code_intervals.items())
        },
        "reserve_hours": dict(sorted(model.reserve_hours.items())),
        "current_version_id": model.current_version_id,
        "lineage": model.lineage,
        "rows": [
            {
                "employee_id": r.employee_id, "display_name": r.display_name, "plan": r.plan, "wyk": r.wyk,
                "plan_hours": r.plan_hours, "wyk_hours": r.wyk_hours, "urlop_hours": r.urlop_hours, "l4_hours": r.l4_hours,
            }
            for r in model.rows
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Font resolution -- path-independent (Section 4): resolved from the
# installed ReportLab package itself, never an OS-specific path. Fails
# closed rather than silently rendering missing Polish glyphs.
# ---------------------------------------------------------------------------

_REQUIRED_POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
_FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC = "T020-Regular", "T020-Bold", "T020-Italic"


def _resolve_unicode_font() -> tuple[str, str, str]:
    font_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    regular, bold, italic = font_dir / "Vera.ttf", font_dir / "VeraBd.ttf", font_dir / "VeraIt.ttf"
    if not (regular.exists() and bold.exists() and italic.exists()):
        raise ExportProblemError("PRINT_FONT_UNAVAILABLE", "no bundled ReportLab Unicode font found")
    if _FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_FONT_REGULAR, str(regular)))
        pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(bold)))
        pdfmetrics.registerFont(TTFont(_FONT_ITALIC, str(italic)))
    face = pdfmetrics.getFont(_FONT_REGULAR).face
    missing = sorted({ch for ch in _REQUIRED_POLISH_CHARS if face.charToGlyph.get(ord(ch)) is None})
    if missing:
        raise ExportProblemError("PRINT_FONT_UNAVAILABLE", f"resolved font is missing Polish glyphs: {''.join(missing)}")
    return _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC


# ---------------------------------------------------------------------------
# PDF rendering (Section 18) -- accepted Checkpoint A visual baseline:
# A3 landscape, grayscale-safe fill-density/border cues, ~170pt name area,
# row height floor 22pt scaling up for smaller rosters, no color-only cues.
# ---------------------------------------------------------------------------

_FILL = {"d": HexColor("#dcdcdc"), "n": HexColor("#a6a6a6"), "h24": HexColor("#595959"), "u": white, "c": white}
_TEXT = {"d": black, "n": black, "h24": white, "u": black, "c": black, "off": HexColor("#8a8a8a")}


def _family(code: str) -> str:
    if code == "24":
        return "h24"
    if code == BLANK:
        return "off"
    return {"D": "d", "N": "n", "U": "u", "C": "c"}.get(code[0], "off")


def _row_height(n_rows: int) -> float:
    return max(22.0, min(46.0, (22.0 * 2 * 10) / max(1, 2 * n_rows)))


def _draw_subrow(c, margin, y, row_h, day_w, name_w, sum_w, label, cells, row, regular, bold) -> None:
    x = margin
    c.setFont(regular, 7)
    if label == "PLAN":
        c.drawString(x + 2, y - row_h + 5, row.display_name[:32])
    c.drawRightString(x + name_w - 2, y - row_h + 5, label)
    x += name_w
    for code in cells:
        fam = _family(code)
        fill = _FILL.get(fam)
        if fill is not None:
            c.setFillColor(fill)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=0, fill=1)
        if fam == "u":
            c.setStrokeColor(black)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
        elif fam == "c":
            c.setDash(2, 1.5)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setDash()
        c.setFillColor(_TEXT.get(fam, black))
        c.setFont(bold, 6.5)
        label_text = "" if code == BLANK or code.endswith("~") else code
        c.drawCentredString(x + day_w / 2, y - row_h + 5, label_text)
        c.setFillColor(black)
        x += day_w
    for value in (row.plan_hours if label == "PLAN" else row.wyk_hours, "", row.urlop_hours, row.l4_hours):
        c.setFont(regular, 7)
        c.drawCentredString(x + sum_w / 2, y - row_h + 5, "" if value == "" else str(value))
        x += sum_w


def _render_pdf(model: ExportModel, generated_at: datetime) -> bytes:
    regular, bold, italic = _resolve_unicode_font()
    page_w, page_h = landscape(A3)
    margin, name_w, sum_w = 24.0, 170.0, 48.0
    day_w = (page_w - 2 * margin - name_w - 4 * sum_w) / len(model.days)
    row_h = _row_height(len(model.rows))
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A3))
    y = page_h - margin
    c.setFont(bold, 16)
    c.drawString(margin, y, f"{model.company_print_name} — {model.site_print_name}")
    y -= 18
    c.setFont(regular, 9.5)
    c.drawString(margin, y, f"Okres: {model.period_label}   Zakres dat: {model.days[0].isoformat()} — {model.days[-1].isoformat()}")
    y -= 12
    c.drawString(margin, y, model.provenance_text)
    y -= 12
    c.drawString(margin, y, f"Revision: {_document_revision(model)}   Wygenerowano: {generated_at.isoformat()}")
    y -= 16
    for row in model.rows:
        for label, cells in (("PLAN", row.plan), ("WYK", row.wyk)):
            _draw_subrow(c, margin, y, row_h, day_w, name_w, sum_w, label, cells, row, regular, bold)
            y -= row_h
    y -= 10
    c.setFont(bold, 10)
    c.drawString(margin, y, "Legenda: D=dniówka N=nocka U=urlop (obwódka ciągła) C=chorobowe (obwódka przerywana) 24=pełny okres 24h")
    c.showPage()
    c.save()
    return buf.getvalue()
