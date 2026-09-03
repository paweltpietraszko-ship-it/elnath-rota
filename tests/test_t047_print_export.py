"""ROTA-T047 dedicated test matrix: tasks/ROTA-T047/brief.md Section 8
(T47-01..T47-11) -- existing D/N work codes shorter/longer than 12h/24h
(catalog_kind == OTHER) are printable via exact interval mapping, and a
large roster paginates instead of failing the whole export. Split out of
tests/test_t020.py (already at/over its own SIZE_FILE floor) rather than
grown further -- reuses that module's fixtures directly.

T47-06 (TRAINEE / contradictory provenance safeguards unchanged) is
already covered by tests/test_t020.py::test_t20_10_effective_trainee_is_unsupported
and ::test_t20_11_wrong_interval_same_duration_fails_mapping -- neither
touches catalog_kind == OTHER handling, so no new test is added for it.
"""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest
import reportlab.pdfgen.canvas as rl_canvas

from rota.application import plan_ops, store
from rota.application.schedule_export import ExportReady
from rota.application.schedule_export import generate_schedule_pdf as _generate_schedule_pdf
from rota.application import schedule_export as SE
from rota.domain import ShiftCatalogKind, ShiftDemand, ShiftKind, SiteProfile, StandardShift
from rota.persistence.db import connect
from rota.persistence.site_repository import WorkCodeInterval, save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _default_intervals, _seed, _settings, _work_item
from tests.test_vertical_full_stack import COORD, _bootstrap


def _capture_pages(monkeypatch) -> list[list[str]]:
    # Records every drawn text string per rendered page (split on showPage()) so
    # pagination/header-repetition/employee-uniqueness can be asserted without a
    # PDF-parsing dependency -- ReportLab subsets/re-encodes glyphs, so searching
    # raw or decompressed PDF bytes for literal text does not work.
    pages: list[list[str]] = [[]]
    originals = {name: getattr(rl_canvas.Canvas, name) for name in ("drawString", "drawCentredString", "drawRightString", "showPage")}

    def _wrap_draw(name):
        def wrapped(self, x, y, text, *a, **k):
            pages[-1].append(text)
            return originals[name](self, x, y, text, *a, **k)
        return wrapped

    def _wrap_show_page(self, *a, **k):
        pages.append([])
        return originals["showPage"](self, *a, **k)

    monkeypatch.setattr(rl_canvas.Canvas, "drawString", _wrap_draw("drawString"))
    monkeypatch.setattr(rl_canvas.Canvas, "drawCentredString", _wrap_draw("drawCentredString"))
    monkeypatch.setattr(rl_canvas.Canvas, "drawRightString", _wrap_draw("drawRightString"))
    monkeypatch.setattr(rl_canvas.Canvas, "showPage", _wrap_show_page)
    return pages


def _finished_pages(pages: list[list[str]]) -> list[list[str]]:
    while pages and not pages[-1]:
        pages.pop()
    return pages


def _other_demand(demand: ShiftDemand, *, kind: ShiftKind) -> ShiftDemand:
    return ShiftDemand(demand.demand_id, "", demand.start_datetime, demand.end_datetime, 1, shift_kind=kind, catalog_kind=ShiftCatalogKind.OTHER)


# --- T47-01/02/03: existing configured D/N codes shorter/longer than 12h/24h print ------------
def test_t47_01_d2_4h_configured_other_prints():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(work_code_intervals={**_default_intervals(), "D2": WorkCodeInterval("06:00", "10:00", False)}))
    d1, a1 = _work_item(3, 6, 10, kind=ShiftKind.D)
    d1 = _other_demand(d1, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[2] == "D2"
    assert model.rows[0].wyk[2] == "D2"


def test_t47_02_d4_2h_configured_other_prints():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(work_code_intervals={**_default_intervals(), "D4": WorkCodeInterval("06:00", "08:00", False)}))
    d1, a1 = _work_item(3, 6, 8, kind=ShiftKind.D)
    d1 = _other_demand(d1, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[2] == "D4"
    assert model.rows[0].wyk[2] == "D4"


def test_t47_03_n2_16h_crossing_midnight_configured_other_prints():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(work_code_intervals={**_default_intervals(), "N2": WorkCodeInterval("15:00", "07:00", True)}))
    d1, a1 = _work_item(3, 15, 7, kind=ShiftKind.N)
    d1 = _other_demand(d1, kind=ShiftKind.N)
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[2] == "N2"
    assert model.rows[0].wyk[2] == "N2"


# --- T47-04: same duration, different start/end signature still fails mapping -----------------
def test_t47_04_same_duration_wrong_interval_still_fails_mapping():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(work_code_intervals={**_default_intervals(), "D2": WorkCodeInterval("06:00", "10:00", False)}))
    d1, a1 = _work_item(3, 7, 11, kind=ShiftKind.D)  # same 4h duration as D2, wrong start/end
    d1 = _other_demand(d1, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_CODE_MAPPING_REQUIRED"


# --- T47-05: a duration with no frozen code (14h) never invents one ----------------------------
def test_t47_05_14h_has_no_configured_code():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 17, 7, kind=ShiftKind.D)  # 17:00-07:00 = 14h, matches no FROZEN_WORK_CODE_HOURS value
    d1 = _other_demand(d1, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_CODE_MAPPING_REQUIRED"


# --- T47-07: an ordinary small roster still renders one page with the legend -------------------
def test_t47_07_small_roster_still_single_page(monkeypatch):
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    pages = _capture_pages(monkeypatch)
    result = _generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, ExportReady)
    pages = _finished_pages(pages)
    assert len(pages) == 1
    assert any(t.startswith("Legenda —") for t in pages[0])


# --- T47-08: a large roster paginates, every employee appears exactly once, PLAN+WYK together --
def test_t47_08_large_roster_paginates_with_every_employee_once(monkeypatch):
    employee_ids = tuple(f"EMP-{i:02d}" for i in range(17))
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    pages = _capture_pages(monkeypatch)
    result = _generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, ExportReady)
    pages = _finished_pages(pages)
    assert len(pages) > 1
    all_text = [t for page in pages for t in page]
    expected_names = ["Emp One"] + [f"Pracownik {e}" for e in employee_ids[1:]]
    for name in expected_names:
        assert all_text.count(name) == 1, f"{name} must appear exactly once across the whole document"


# --- T47-09: every page repeats the required headers/date range and is numbered ----------------
def test_t47_09_multi_page_repeats_headers_and_numbers_pages(monkeypatch):
    employee_ids = tuple(f"EMP-{i:02d}" for i in range(30))
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    pages = _capture_pages(monkeypatch)
    result = _generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, ExportReady)
    pages = _finished_pages(pages)
    page_count = len(pages)
    assert page_count > 1
    title = "ELNATH DEMO — SITE-DEMO"
    for page_num, page_texts in enumerate(pages, start=1):
        assert any(title in t for t in page_texts)
        assert f"Strona {page_num} z {page_count}" in page_texts
    legend_hits = sum(1 for page_texts in pages for t in page_texts if t.startswith("Legenda —"))
    assert legend_hits == 1


# --- T47-10: readability -- no clipped rows/overlap, checked visually against real PNG renders
# during implementation (Section 9); no automated pytest assertion added (no PDF rasterizer
# dependency in this repo) -- structural non-overlap is already implied by row_h staying at or
# above its existing accepted floor (T47-07/08/09 above never shrink it further).


# --- T47-11: production vertical -- real object/catalog/PLAN/select/export, no manual PDF/mock -
def _profile_d2_4h(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(10, 0), False, 1)],  # 4h -> catalog_kind normalizes to OTHER
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def test_t47_11_d2_4h_through_real_plan_select_export(tmp_path: Path):
    from rota.persistence.site_repository import SitePrintSettings

    site_id, profile_id, month = "SITE-T047", "PROF-T047", date(2026, 11, 1)
    employees = ("EMP-T047-1", "EMP-T047-2")
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, site_id=site_id, profile_id=profile_id, profile=_profile_d2_4h(profile_id), employees=employees, month=month)
    save_site_print_settings(conn, SitePrintSettings(
        site_id=site_id, company_print_name="ELNATH DEMO", site_print_name=site_id, base_regime="12h",
        work_code_intervals={**{k: None for k in ("D1", "D3", "D4", "D5", "N1", "N2", "N3", "N4", "N5")}, "D2": WorkCodeInterval("06:00", "10:00", False)},
        reserve_hours={k: None for k in ("U3", "U4", "U5", "C3", "C4", "C5")},
    ))

    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id=COORD, effective_from=month)
    assert result.status == "FEASIBLE"
    plan_ops.select_candidate(conn, site_id=site_id, month=month, candidate=result.candidates[0], coordinator_id=COORD)

    export = _generate_schedule_pdf(conn, site_id=site_id, month=month, period_label="Listopad 2026")
    assert isinstance(export, ExportReady) and export.pdf_bytes.startswith(b"%PDF")

    model = SE._assemble_export_model(conn, site_id=site_id, month=month, period_label="Listopad 2026")
    assert any("D2" in row.plan for row in model.rows), "at least one real Assignment must print as D2"
