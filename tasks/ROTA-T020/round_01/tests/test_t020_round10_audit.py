"""Narrow independent re-audit for product 2ba338b."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import reportlab

from rota.application import schedule_export as export
from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftCatalogKind, ShiftDemand, ShiftKind
from rota.persistence import schedule_lifecycle
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings


def _leg(assignment_id: str, start: datetime, end: datetime, demand_id: str, period_id: str) -> Assignment:
    return Assignment(
        assignment_id,
        "",
        "EMP-1",
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.REALIZED,
        False,
        demand_id,
        None,
        work_period_id=period_id,
        required_rest_after_hours=24,
    )


def _create_adjacent_version(conn, month: date, version_id: str, demand: ShiftDemand, assignment: Assignment) -> None:
    schedule_lifecycle.create_schedule_version(
        conn,
        version_id=version_id,
        site_id="SITE-1",
        month=month,
        parent_version_id=None,
        created_at=datetime.combine(month, datetime.min.time()),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[demand],
        assignments=[assignment],
        deviations=[],
        effective_from=month,
    )


def test_round10_normal_h24_repeated_component_number_is_malformed() -> None:
    start = datetime(2026, 8, 5, 6)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    first = ShiftDemand(
        "D",
        "",
        start,
        middle,
        1,
        shift_kind=ShiftKind.D,
        catalog_kind=ShiftCatalogKind.H24,
        work_period_template_id="TPL",
        work_period_component=1,
    )
    second = ShiftDemand(
        "N",
        "",
        middle,
        end,
        1,
        shift_kind=ShiftKind.N,
        catalog_kind=ShiftCatalogKind.H24,
        work_period_template_id="TPL",
        work_period_component=1,
    )

    assert export._is_legitimate_normal_24h(first, second, 24) is False


def test_round10_cross_month_linkage_allows_reused_local_assignment_id() -> None:
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demand_a = ShiftDemand("N-A", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    _create_version(conn, [demand_a], [_leg("SAME-LOCAL-ID", start, middle, "N-A", "WP")])
    demand_b = ShiftDemand("D-B", "", middle, end, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    _create_adjacent_version(conn, date(2026, 9, 1), "SV-SEP", demand_b, _leg("SAME-LOCAL-ID", middle, end, "D-B", "WP"))

    model = export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August")

    assert model.rows[0].plan[30] == "24"


def test_round10_displayed_provenance_changes_when_adjacent_link_is_used() -> None:
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demand_a = ShiftDemand("N-A", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    _create_version(conn, [demand_a], [_leg("A-AUG", start, middle, "N-A", "WP")])
    before = export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August")
    demand_b = ShiftDemand("D-B", "", middle, end, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    _create_adjacent_version(conn, date(2026, 9, 1), "SV-SEP", demand_b, _leg("A-SEP", middle, end, "D-B", "WP"))
    after = export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August")

    assert before.provenance_text != after.provenance_text
    assert export._document_revision(before) != export._document_revision(after)


def test_round10_font_resolution_has_no_machine_specific_os_paths() -> None:
    reportlab_root = Path(reportlab.__file__).resolve().parent
    candidates = export._font_candidates()
    outside_reportlab = [path for triple in candidates for path in triple if not path.is_relative_to(reportlab_root)]

    assert outside_reportlab == []


def test_round10_long_header_content_fails_before_clipping() -> None:
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(
        conn,
        _settings(company_print_name="F" * 500, site_print_name="S" * 500),
    )
    _create_version(conn, [], [])

    result = export.generate_schedule_pdf(
        conn,
        site_id="SITE-1",
        month=MONTH,
        period_label="P" * 500,
    )

    assert isinstance(result, export.ExportProblem)
    assert result.problem_code == "ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT"
