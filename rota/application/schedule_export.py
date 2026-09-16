"""ROTA-T020 Checkpoint B -- printable schedule PDF export (READ/PRESENTATION only; never touches solver/lifecycle write paths). No SQL here -- only existing repositories.

ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 8: the schedule-assembly
logic that used to live here (private, PDF-bound) moved to
rota.application.schedule_projection -- PDF and the external Excel API
now share one projection builder. This file keeps only PDF rendering,
the LAW-deviation entry point, and font resolution. Compatibility
aliases/re-exports below (`_assemble_export_model`, `_reconstruct_
lineage`, `_build_ordinary_rows`, `_build_rows`) exist solely so the
pre-existing tests that call them directly, via the `SE` module alias
or a plain `from ... import` (tests/test_t020.py and 6 siblings, none
in this Task's TASK_SCOPE), keep working unchanged -- OWNER_RULING
2026-09-16: alias over rename.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, Union
import reportlab
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rota.application.lifecycle_ops import fresh_validation
from rota.application.schedule_projection import (
    BLANK,
    DELEGACJA_LABEL,
    PLAN_PRIORITY,
    ExportModel,
    ExportProblemError,
    OrdinaryRowCells,
    build_schedule_projection,
)
from rota.application.schedule_projection import _reconstruct_lineage  # noqa: F401 -- re-export, see module docstring
from rota.application.schedule_projection import _build_ordinary_rows, _build_rows  # noqa: F401 -- re-export, see module docstring
from rota.domain import DeviationCategory
from rota.persistence import schedule_repository, site_repository

# Compatibility aliases (see module docstring) -- never called by new code,
# only by pre-existing tests using the old private names via `SE.`/direct import.
_assemble_export_model = build_schedule_projection

@dataclass(frozen=True)
class ExportReady:
    pdf_bytes: bytes; document_revision: str; schedule_provenance: str  # noqa: E702
@dataclass(frozen=True)
class ExportProblem:
    problem_code: str; message: str  # noqa: E702
@dataclass(frozen=True)
class ExportLawItem:
    # ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS: `rule` is the raw built-in
    # validator code (e.g. "REST-01") -- the api layer, not this one, owns
    # translating it to a Polish label (mirrors the existing
    # api/routers/schedule.py::_deviation_label split).
    fingerprint: str; rule: str; affected_assignment_or_employee: str  # noqa: E702
@dataclass(frozen=True)
class ExportLawBlocked:
    items: tuple[ExportLawItem, ...]
ExportResult = Union[ExportReady, ExportProblem, ExportLawBlocked]
# Entry point
def generate_schedule_pdf(
    conn: sqlite3.Connection, *, site_id: str, month: date, period_label: str, generated_at: Optional[datetime] = None,
    acknowledged_law_fingerprints: frozenset = frozenset(),
) -> ExportResult:
    try:
        # ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS: these two checks mirror
        # _assemble_export_model's own opening two -- kept in the SAME
        # order here so an existing (no settings, no schedule) site keeps
        # its established PRINT_SETTINGS_MISSING precedence over the new
        # NO_CURRENT_SCHEDULE pin below, instead of silently reordering an
        # already-tested problem_code precedence.
        if month.day != 1:
            raise ExportProblemError("PROVENANCE_INCOMPLETE", "month must be the first day of the month")
        if site_repository.get_site_print_settings(conn, site_id) is None:
            raise ExportProblemError("PRINT_SETTINGS_MISSING", f"no print settings saved for {site_id}")
        version_id = schedule_repository.get_current_version_id(conn, site_id, month)
        if version_id is None:
            raise ExportProblemError("NO_CURRENT_SCHEDULE", f"no current ScheduleVersion for ({site_id}, {month})")
        law_items = _fresh_law_items(conn, site_id=site_id, month=month, schedule_version_id=version_id)
        unacknowledged = tuple(item for item in law_items if item.fingerprint not in acknowledged_law_fingerprints)
        if unacknowledged:
            return ExportLawBlocked(items=unacknowledged)
        model = _assemble_export_model(conn, site_id=site_id, month=month, period_label=period_label)
        _assert_same_current(conn, site_id, month, version_id)
        pdf_bytes = _render_pdf(model, generated_at or datetime.now(timezone.utc))
        _assert_same_current(conn, site_id, month, version_id)
    except ExportProblemError as exc:
        return ExportProblem(exc.code, exc.message)
    except site_repository.InvalidSitePrintSettings as exc:
        return ExportProblem("PRINT_SETTINGS_INVALID", str(exc))
    return ExportReady(pdf_bytes=pdf_bytes, document_revision=_document_revision(model), schedule_provenance=model.provenance_text)
def _assert_same_current(conn: sqlite3.Connection, site_id: str, month: date, expected_version_id: str) -> None:
    # brief.md section 6: check -> render must be about the same pinned
    # ScheduleVersion; a coordinator change (finalize/correction/REPLAN)
    # racing this request must never let stale-checked bytes out the door.
    if schedule_repository.get_current_version_id(conn, site_id, month) != expected_version_id:
        raise ExportProblemError("SCHEDULE_VERSION_CHANGED", "current ScheduleVersion changed during export")
def _law_fingerprint(detail, assignment_lookup: dict, planning_regime: str) -> str:
    # brief.md section 5: derived from ViolationDetail + structural
    # Assignment data only, never from human `message` text. Assignment
    # start/end/work_period_id/required_rest_after_hours are all included
    # (not just assignment_id) so a manual correction OR a required-rest
    # change (e.g. an OCHRONA 24h period's effective floor moving 11h->24h,
    # rota.planning.work_periods.effective_required_rest_after_hours) never
    # inherits an old fingerprint's acknowledgement for the same underlying
    # pair (P8, Codex R1 audit finding on b1df489: required_rest_after_hours
    # was previously omitted, so that exact case kept the stale fingerprint
    # valid). planning_regime is included at payload level for the same
    # reason (it gates the ochrona 24h floor bump). REST-01/WEEKLY-REST-01
    # can reference other_site_assignments/boundary_assignments too, not
    # only existing_assignments, hence the merged lookup.
    facts = []
    for assignment_id in detail.assignment_ids:
        assignment = assignment_lookup.get(assignment_id)
        if assignment is None:
            raise ExportProblemError("WORK_PROVENANCE_INCOMPLETE", f"LAW violation references unresolvable assignment {assignment_id}")
        facts.append([
            assignment.assignment_id, assignment.employee_id,
            assignment.start_datetime.isoformat(), assignment.end_datetime.isoformat(),
            assignment.work_period_id, assignment.required_rest_after_hours,
        ])
    payload = {
        "rule": detail.rule, "affected_employee_id": detail.affected_employee_id,
        "planning_regime": planning_regime, "assignments": sorted(facts, key=lambda f: [str(x) for x in f]),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
def _fresh_law_items(conn: sqlite3.Connection, *, site_id: str, month: date, schedule_version_id: str) -> list[ExportLawItem]:
    result = fresh_validation(conn, site_id=site_id, month=month, schedule_version_id=schedule_version_id)
    assignment_lookup = {
        a.assignment_id: a
        for pool in (result.state.existing_assignments, result.state.other_site_assignments, result.state.boundary_assignments)
        for a in pool
    }
    planning_regime = result.state.site.planning_regime.value
    items = []
    for detail, deviation in zip(result.violation_details, result.deviations):
        if deviation.category != DeviationCategory.LAW:
            continue
        items.append(ExportLawItem(
            fingerprint=_law_fingerprint(detail, assignment_lookup, planning_regime),
            rule=detail.rule, affected_assignment_or_employee=deviation.affected_assignment_or_employee,
        ))
    return items
# Document revision (Section 17) -- excludes generated_at/filename/PDF metadata.
def _document_revision(model: ExportModel) -> str:
    payload = {
        "regime": model.regime, "site_id": model.site_id, "month": model.month.isoformat(),
        "date_range": [model.days[0].isoformat(), model.days[-1].isoformat()],
        "period_label": model.period_label, "company_print_name": model.company_print_name, "site_print_name": model.site_print_name,
        "current_version_id": model.current_version_id, "lineage": model.lineage, "adjacent_facts": model.adjacent_facts,
    }
    if model.regime == "ORDINARY":
        payload["ordinary_rows"] = [
            {"employee_id": r.employee_id, "display_name": r.display_name, "position_label": r.position_label,
             "day_cells": r.day_cells, "day_absence_kind": r.day_absence_kind, "total_hours": r.total_hours}
            for r in model.ordinary_rows
        ]
    else:
        payload["base_regime"] = model.base_regime
        payload["work_code_intervals"] = {k: (None if v is None else [v.start_time, v.end_time, v.end_next_day]) for k, v in sorted(model.work_code_intervals.items())}
        payload["extra_work_codes"] = {k: [v.start_time, v.end_time, v.end_next_day] for k, v in sorted(model.extra_work_codes.items())}
        payload["reserve_hours"] = dict(sorted(model.reserve_hours.items()))
        payload["rows"] = [
            {"employee_id": r.employee_id, "display_name": r.display_name, "plan": r.plan, "wyk": r.wyk,
             "plan_hours": r.plan_hours, "wyk_hours": r.wyk_hours, "urlop_hours": r.urlop_hours, "l4_hours": r.l4_hours}
            for r in model.rows
        ]
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
_FILL = {
    "d": HexColor("#dcdcdc"), "n": HexColor("#a6a6a6"), "h24": HexColor("#595959"), "u": white, "c": white,
    "s1": white,
    # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 10: DELEGACJA must not
    # collide with D/N -- its own fill, never the "d" family's.
    "del": HexColor("#f2e2c4"),
}
_TEXT = {
    "d": black, "n": black, "h24": white, "u": black, "c": black, "off": HexColor("#8a8a8a"), "s1": black,
    "del": black,
}
_WEEKEND_BG = HexColor("#e2e2e2")
_DOW = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Ni"]
MARGIN, NAME_W, SUM_W = 24.0, 170.0, 48.0
LEGEND_PAGE_TITLE_H = 24.0
HEADER_H, LEGEND_H, FOOTER_H = 90.0, 150.0, 20.0
def _family(code: str) -> str:
    # ROTA-T052 (R4-02 audit fix): a combined same-day cell ("N1/S1",
    # "24/S1") takes its family from the primary (non-S1) code, so it still
    # renders as that shift's kind, not as an unstyled fallback.
    primary = code.split("/", 1)[0]
    if primary == "24":
        return "h24"
    if primary == "S1":
        return "s1"
    if primary == DELEGACJA_LABEL:
        # ROTA-DELEGACJA-ABSENCE-KIND: checked before the D/N-family
        # fallback below, which would otherwise misclassify "DEL" as the
        # "D" (day-shift) family purely from its first letter.
        return "del"
    if code == BLANK:
        return "off"
    return {"D": "d", "N": "n", "U": "u", "C": "c"}.get(primary[0], "off")
def _row_height(n_rows: int) -> float:
    return max(22.0, min(46.0, (22.0 * 2 * 10) / max(1, 2 * n_rows)))
def _fit_font_size(text: str, font: str, size: float, max_width: float, min_size: float = 6.5) -> float:
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size
def _check_fits(row_h: float) -> int:
    # T047: a large roster no longer fails the whole export -- it is split across as many pages
    # as needed (see _render_pdf). Only the pathological case where not even one employee's
    # PLAN/WYK pair fits at the accepted readability floor remains a real layout failure.
    available = landscape(A3)[1] - 2 * MARGIN - HEADER_H - LEGEND_H - FOOTER_H
    rows_per_page = int(available // (2 * row_h))
    if rows_per_page < 1:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", f"not even one employee's PLAN/WYK pair fits at the {row_h}pt floor")
    return rows_per_page
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
    elif fam == "s1":
        # ROTA-T052: dotted border distinguishes S1 from U (solid) and C
        # (dashed) in black-and-white print, per the legend's own scheme.
        c.setStrokeColor(black); c.setDash(1, 1.5)  # noqa: E702
        c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
        c.setDash()
    elif fam == "del":
        # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 10: its own border
        # pattern (distinct from U/C/S1) plus the "del" fill/text colors and
        # the literal "DEL" text -- unambiguous against D/N even in
        # black-and-white print.
        c.setStrokeColor(black); c.setDash(3, 2)  # noqa: E702
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
def _used_codes(model: ExportModel) -> list[str]:
    """ROTA-T056 brief section 9.4/11 (OWNER ruling): the legend shows only
    codes that actually appear in this rendered document -- never an
    unused, merely-configured D6+/N6+ or reserve slot. Deterministic order:
    standard D/N family order, then any monthly extras (sorted), then U/C,
    then 24/S1."""
    used: set[str] = set()
    for row in model.rows:
        for cells in (row.plan, row.wyk):
            for cell in cells:
                if cell == BLANK or cell.endswith("~"):
                    continue
                used.update(cell.split("/"))
    ordered = [c for c in PLAN_PRIORITY if c in used]
    ordered += sorted(c for c in used if c[0] in "DN" and c not in PLAN_PRIORITY)
    ordered += [c for c in ("U1", "U2", "U3", "U4", "U5") if c in used]
    ordered += [c for c in ("C1", "C2", "C3", "C4", "C5") if c in used]
    ordered += [c for c in ("24", "S1") if c in used]
    ordered += [c for c in (DELEGACJA_LABEL,) if c in used]
    return ordered
def _legend_entry_text(code: str, model: ExportModel) -> str:
    if code == "24":
        return "24 = pełny okres 24h w dniu rozpoczęcia"
    if code == "S1":
        return "S1 = szkolenie okresowe (ręcznie ustalane przez koordynatora, godziny pracy)"
    if code == DELEGACJA_LABEL:
        return "DEL = delegacja (dzień zablokowany dla automatu; godziny wg zapisanego rekordu, liczą się jako praca)"
    if code in site_repository.FROZEN_WORK_CODE_HOURS:
        return f"{code} = {site_repository.FROZEN_WORK_CODE_HOURS[code]}h"
    if code in model.extra_work_codes:  # ROTA-T056: monthly D6+/N6+
        hours = int(site_repository.interval_duration_hours(model.extra_work_codes[code]))
        return f"{code} = {hours}h (dodatkowy kod miesiąca)"
    value = {"U1": 12, "U2": 16, "C1": 12, "C2": 16}.get(code, model.reserve_hours.get(code))
    return f"{code} = {value}h" if value is not None else f"{code} = — (rezerwa)"
_LEGEND_TITLE = "Legenda — użyte w tym wydruku oznaczenia (wartości właściciela, nie normalizowane)"
_LEGEND_FOOTNOTES = (
    "Numer przy literze NIE oznacza wspólnej wartości dla wszystkich liter (np. D4=2h, N4=24h).",
    "Druk czarno-biały: D/N/24 = gęstość wypełnienia, U = obwódka ciągła, C = obwódka przerywana, S1 = obwódka kropkowana, DEL = obwódka kreskowana — czytelne bez koloru.",
)
def _legend_required_height(n_entries: int) -> float:
    # title + ceil(n/2) rows of a 2-column list + fixed footnotes; 0 entries never happens (T56-08 guarantees at least the S1/24/normal work codes if any row exists).
    rows = -(-max(n_entries, 1) // 2)
    return 15 + rows * 12 + len(_LEGEND_FOOTNOTES) * 12 + 6
def _draw_legend(c, model: ExportModel, regular, bold, italic, y: float) -> float:
    entries = _used_codes(model)
    c.setFont(bold, 10); c.drawString(MARGIN, y, _LEGEND_TITLE); y -= 15  # noqa: E702
    col_w = (landscape(A3)[0] - 2 * MARGIN) / 2
    rows = -(-len(entries) // 2)
    for i in range(rows):
        for col, idx in enumerate((i, i + rows)):
            if idx >= len(entries):
                continue
            c.setFont(regular, 9); c.drawString(MARGIN + col * col_w, y, _legend_entry_text(entries[idx], model))  # noqa: E702
        y -= 12
    c.setFont(italic, 8)
    for line in _LEGEND_FOOTNOTES:
        c.drawString(MARGIN, y, line); y -= 12  # noqa: E702
    return y
def _draw_page_header(c, model: ExportModel, day_w, revision: str, generated_at: datetime, regular, bold, page_h) -> float:
    y = page_h - MARGIN
    c.setFont(bold, 16); c.drawString(MARGIN, y, f"{model.company_print_name} — {model.site_print_name}"); y -= 18  # noqa: E702
    c.setFont(regular, 9.5); c.drawString(MARGIN, y, f"Okres: {model.period_label}   Zakres dat: {model.days[0].isoformat()} — {model.days[-1].isoformat()}"); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, model.provenance_display_text); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, f"Rewizja treści: {revision[:10]}   Wygenerowano: {generated_at.isoformat()}"); y -= 16  # noqa: E702
    return _draw_day_headers(c, day_w, model.days, model.holiday_by_date, bold, y)
def _draw_page_footer(c, regular, page_num: int, page_count: int, page_w: float) -> None:
    c.setFont(regular, 7.5); c.drawCentredString(page_w / 2, MARGIN / 2, f"Strona {page_num} z {page_count}")  # noqa: E702
def _draw_legend_only_page(c, model: ExportModel, regular, bold, italic, page_h) -> None:
    # ROTA-T056 brief section 9.4/11 (OWNER ruling): a dedicated legend page
    # only when the used-codes legend does not fit legibly on the grid
    # page's leftover space -- never truncated, hidden, or shrunk past the
    # accepted readable floor (the same fonts/sizes _draw_legend already uses).
    y = page_h - MARGIN
    c.setFont(bold, 14); c.drawString(MARGIN, y, "Legenda — ciąg dalszy (wszystkie użyte oznaczenia)"); y -= LEGEND_PAGE_TITLE_H  # noqa: E702
    _draw_legend(c, model, regular, bold, italic, y)
def _render_pdf(model: ExportModel, generated_at: datetime) -> bytes:
    # ROTA-T065-PRINT-GAP brief section 13: the regime branch is purely a
    # private render-model choice -- one public entry point, one PDF result
    # type, no second document/lifecycle.
    if model.regime == "ORDINARY":
        return _render_ordinary_pdf(model, generated_at)
    return _render_ochrona_pdf(model, generated_at)
def _render_ochrona_pdf(model: ExportModel, generated_at: datetime) -> bytes:
    regular, bold, italic = _resolve_unicode_font()
    page_w, page_h = landscape(A3)
    day_w = (page_w - 2 * MARGIN - NAME_W - 4 * SUM_W) / len(model.days)
    row_h = _row_height(len(model.rows))
    rows_per_page = _check_fits(row_h)
    _check_header_fits(model, regular, bold)
    revision = _document_revision(model)
    pages = [model.rows[i:i + rows_per_page] for i in range(0, len(model.rows), rows_per_page)] or [[]]
    grid_page_count = len(pages)
    legend_h = _legend_required_height(len(_used_codes(model)))
    last_page_rows = len(pages[-1]) if pages else 0
    available_on_grid_page = (page_h - MARGIN - HEADER_H) - (last_page_rows * 2 * row_h) - MARGIN
    legend_needs_own_page = legend_h > available_on_grid_page
    # R8-04 fix: a dedicated legend page is only a valid destination if the
    # legend itself actually fits there -- previously this was assumed
    # unconditionally, and a large enough used-code set (130 in the audit
    # repro) overflowed past the footer, truncated and overlapping it.
    # Brief section 2/11 authorizes exactly one extra page, not an
    # open-ended one, so an oversized legend fails closed instead of
    # silently truncating or inventing a third page.
    available_on_own_page = page_h - 2 * MARGIN - LEGEND_PAGE_TITLE_H
    if legend_needs_own_page and legend_h > available_on_own_page:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", "used-code legend does not fit even on its own dedicated page at the accepted readability floor")
    page_count = grid_page_count + (1 if legend_needs_own_page else 0)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A3))
    for page_num, page_rows in enumerate(pages, start=1):
        y = _draw_page_header(c, model, day_w, revision, generated_at, regular, bold, page_h)
        for row in page_rows:
            for label, cells in (("PLAN", row.plan), ("WYK", row.wyk)):
                _draw_subrow(c, y, row_h, day_w, label, cells, row, regular, bold)
                y -= row_h
        if page_num == grid_page_count and not legend_needs_own_page:  # T047: legend printed at least once, not repeated per page
            _draw_legend(c, model, regular, bold, italic, y - 10)
        _draw_page_footer(c, regular, page_num, page_count, page_w)
        c.showPage()
    if legend_needs_own_page:
        _draw_legend_only_page(c, model, regular, bold, italic, page_h)
        _draw_page_footer(c, regular, page_count, page_count, page_w)
        c.showPage()
    c.save()
    return buf.getvalue()
# ORDINARY rendering (brief section 6/9/10/16 -- T65P-16 "1:1 z OWNER_ACCEPTED prototypem").
ORD_SUM_W = 56.0
ORD_ROW_H = 30.0
ORD_LEGEND_LINES = (
    "Rola pracownika (rzeczywiste stanowisko) jest wypisana raz pod nazwiskiem, nie przy każdej zmianie — nawet gdy ktoś pokrywa dodatkową zmianę, zostaje swoją rolą.",
    "Komórki dni pokazują wyłącznie rzeczywiste godziny (np. 5–12); odcień wypełnienia komórki to podpowiedź tej samej roli.",
    "Kilka niezależnych zmian jednego dnia — osobne linie w tej samej komórce, w kolejności chronologicznej.",
    "Zmiana przechodząca przez północ: godzina końcowa z dopiskiem (+1) oznacza następną dobę (np. 22–6(+1)).",
    "Nieobecność: pogrubiona pełna ramka = Urlop, przerywana ramka = L4, bez wypełnienia. „–” = zwykły dzień bez pracy.",
    "DEL = delegacja (kropkowana ramka): dzień zablokowany dla automatu, ale jego godziny liczą się jak realna praca.",
    "„Godz.” = suma godzin rzeczywistej pracy w miesiącu, wliczając godziny delegacji (bez godzin absencji Urlop/L4).",
)
def _ordinary_position_shades(rows: "tuple[OrdinaryRowCells, ...]") -> dict[str, tuple]:
    # Brief section 5/11: deterministic for however many organizational
    # positions actually appear in this document -- never a hardcoded
    # two-role palette. The fill is only a secondary cue; the position text
    # under the name stays the primary carrier of meaning.
    positions = sorted({r.position_label for r in rows}, key=str.casefold)
    light, dark = 0xE2, 0x50
    shades: dict[str, tuple] = {}
    for index, label in enumerate(positions):
        level = dark if len(positions) <= 1 else round(light - (light - dark) * index / (len(positions) - 1))
        fill = HexColor(f"#{level:02x}{level:02x}{level:02x}")
        shades[label] = (fill, black if level >= 0x90 else white)
    return shades
def _check_ordinary_fits(row_h: float) -> int:
    available = landscape(A3)[1] - 2 * MARGIN - HEADER_H - _ordinary_legend_height() - FOOTER_H
    rows_per_page = int(available // row_h)
    if rows_per_page < 1:
        raise ExportProblemError("ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT", f"not even one employee row fits at the {row_h}pt floor")
    return rows_per_page
def _ordinary_legend_height() -> float:
    return 15 + len(ORD_LEGEND_LINES) * 11 + 6
def _draw_ordinary_day_headers(c, day_w, days, holiday_by_date, bold, y) -> float:
    x = MARGIN + NAME_W
    for d in days:
        if d.weekday() >= 5 or holiday_by_date.get(d, False):
            c.setFillColor(_WEEKEND_BG); c.rect(x, y - 30, day_w, 30, stroke=0, fill=1); c.setFillColor(black)  # noqa: E702
        c.setFont(bold, 6.5); c.drawCentredString(x + day_w / 2, y - 10, _DOW[d.weekday()])  # noqa: E702
        c.setFont(bold, 8); c.drawCentredString(x + day_w / 2, y - 24, str(d.day))  # noqa: E702
        x += day_w
    c.setFont(bold, 6.5); c.drawCentredString(x + ORD_SUM_W / 2, y - 18, "Godz.")  # noqa: E702
    return y - 32
def _draw_ordinary_page_header(c, model: ExportModel, day_w, revision: str, generated_at: datetime, regular, bold, page_h) -> float:
    y = page_h - MARGIN
    c.setFont(bold, 16); c.drawString(MARGIN, y, f"{model.company_print_name} — {model.site_print_name}"); y -= 18  # noqa: E702
    c.setFont(regular, 9.5); c.drawString(MARGIN, y, f"Okres: {model.period_label}   Zakres dat: {model.days[0].isoformat()} — {model.days[-1].isoformat()}"); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, model.provenance_display_text); y -= 12  # noqa: E702
    c.drawString(MARGIN, y, f"Rewizja treści: {revision[:10]}   Wygenerowano: {generated_at.isoformat()}"); y -= 16  # noqa: E702
    return _draw_ordinary_day_headers(c, day_w, model.days, model.holiday_by_date, bold, y)
def _draw_ordinary_row(c, y, row_h, day_w, row: "OrdinaryRowCells", days, regular, bold, shades) -> None:
    x = MARGIN
    c.setFont(regular, _fit_font_size(row.display_name, regular, 7.5, NAME_W - 4)); c.drawString(x + 2, y - row_h / 2 + 4, row.display_name)  # noqa: E702
    c.setFont(regular, 6); c.setFillColor(HexColor("#5c6156"))  # noqa: E702
    c.drawString(x + 2, y - row_h / 2 - 6, row.position_label)
    c.setFillColor(black)
    x += NAME_W
    fill, text_color = shades.get(row.position_label, (None, black))
    for day_index, _ in enumerate(days):
        lines = row.day_cells[day_index]
        absence_kind = row.day_absence_kind[day_index]
        c.setStrokeColor(HexColor("#c8c8c8")); c.setLineWidth(0.4)  # noqa: E702
        c.rect(x, y - row_h, day_w, row_h, stroke=1, fill=0)
        is_blank = lines == [BLANK]
        if absence_kind is None and not is_blank and fill is not None:
            c.setFillColor(fill); c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=0, fill=1)  # noqa: E702
        if absence_kind == "URLOP":
            c.setStrokeColor(black); c.setLineWidth(1.4)  # noqa: E702
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setLineWidth(0.4)
        elif absence_kind == "L4":
            c.setStrokeColor(black); c.setDash(2, 1.5)  # noqa: E702
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setDash(); c.setLineWidth(0.4)  # noqa: E702
        elif absence_kind == "DEL":
            # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 10: a third,
            # visually distinct border -- DELEGACJA counts as real work
            # hours, so it must not read as Urlop (solid) or L4 (dashed).
            c.setStrokeColor(black); c.setDash(1, 1.5)  # noqa: E702
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setDash(); c.setLineWidth(0.4)  # noqa: E702
        if not is_blank:
            fs = 6.5
            while fs > 4.5 and max(pdfmetrics.stringWidth(t, bold, fs) for t in lines) > day_w - 3:
                fs -= 0.5
            line_h = fs + 1.5
            top = y - row_h / 2 + (len(lines) - 1) * line_h / 2
            c.setFillColor(black if absence_kind is not None or fill is None else text_color)
            c.setFont(bold, fs)
            for i, line in enumerate(lines):
                c.drawCentredString(x + day_w / 2, top - i * line_h - fs * 0.35, line)
            c.setFillColor(black)
        x += day_w
    c.setFont(regular, 7); c.drawCentredString(x + ORD_SUM_W / 2, y - row_h / 2 - 3, str(row.total_hours))  # noqa: E702
def _draw_ordinary_legend(c, regular, italic, bold, y: float) -> None:
    c.setFont(bold, 10); c.drawString(MARGIN, y, "Legenda"); y -= 15  # noqa: E702
    c.setFont(regular, 8)
    for line in ORD_LEGEND_LINES:
        c.drawString(MARGIN, y, line); y -= 11  # noqa: E702
def _render_ordinary_pdf(model: ExportModel, generated_at: datetime) -> bytes:
    regular, bold, italic = _resolve_unicode_font()
    page_w, page_h = landscape(A3)
    day_w = (page_w - 2 * MARGIN - NAME_W - ORD_SUM_W) / len(model.days)
    rows_per_page = _check_ordinary_fits(ORD_ROW_H)
    _check_header_fits(model, regular, bold)
    revision = _document_revision(model)
    shades = _ordinary_position_shades(model.ordinary_rows)
    pages = [model.ordinary_rows[i:i + rows_per_page] for i in range(0, len(model.ordinary_rows), rows_per_page)] or [[]]
    page_count = len(pages)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A3))
    for page_num, page_rows in enumerate(pages, start=1):
        y = _draw_ordinary_page_header(c, model, day_w, revision, generated_at, regular, bold, page_h)
        for row in page_rows:
            _draw_ordinary_row(c, y, ORD_ROW_H, day_w, row, model.days, regular, bold, shades)
            y -= ORD_ROW_H
        if page_num == page_count:
            _draw_ordinary_legend(c, regular, italic, bold, y - 10)
        _draw_page_footer(c, regular, page_num, page_count, page_w)
        c.showPage()
    c.save()
    return buf.getvalue()
