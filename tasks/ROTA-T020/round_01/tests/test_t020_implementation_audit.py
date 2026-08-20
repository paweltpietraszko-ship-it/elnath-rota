"""Independent implementation audit matrix for ROTA-T020 Checkpoint B.

Each test is a contract oracle that is expected to pass before Checkpoint B
can receive an implementation PASS.  The matrix deliberately targets omitted
equivalence classes rather than repeating tests/test_t020.py happy paths.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from rota.application import schedule_export as export
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
)
from rota.persistence import employee_repository
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings


def _assignment(
    assignment_id: str,
    employee_id: str,
    start: datetime,
    end: datetime,
    demand_id: str,
    *,
    work_period_id: str | None = None,
) -> Assignment:
    return Assignment(
        assignment_id,
        "",
        employee_id,
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.REALIZED,
        False,
        demand_id,
        None,
        work_period_id=work_period_id,
        required_rest_after_hours=24 if work_period_id else None,
    )


def test_audit_malformed_h12_pair_is_not_collapsed_as_t012_24h() -> None:
    """R5 4.3/T20-35: an emergency pair needs the first-demand marker."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 5, 6)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demands = [
        ShiftDemand("D", "", start, middle, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12),
        ShiftDemand("N", "", middle, end, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12),
    ]
    assignments = [
        _assignment("A-D", "EMP-1", start, middle, "D", work_period_id="WP"),
        _assignment("A-N", "EMP-1", middle, end, "N", work_period_id="WP"),
    ]
    _create_version(conn, demands, assignments)

    with pytest.raises(export.ExportProblemError) as exc:
        export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")
    assert exc.value.code == "WORK_PROVENANCE_INCOMPLETE"


def test_audit_normal_h24_cross_month_is_owned_by_start_month() -> None:
    """R6 3/T20-38: the second half may start outside the requested month."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demands = [
        ShiftDemand(
            "N", "", start, middle, 1, shift_kind=ShiftKind.N,
            catalog_kind=ShiftCatalogKind.H24, work_period_template_id="TPL", work_period_component=1,
        ),
        ShiftDemand(
            "D", "", middle, end, 1, shift_kind=ShiftKind.D,
            catalog_kind=ShiftCatalogKind.H24, work_period_template_id="TPL", work_period_component=2,
        ),
    ]
    assignments = [
        _assignment("A-N", "EMP-1", start, middle, "N", work_period_id="WP"),
        _assignment("A-D", "EMP-1", middle, end, "D", work_period_id="WP"),
    ]
    _create_version(conn, demands, assignments)

    model = export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")

    assert model.rows[0].plan[30] == "24"
    assert model.rows[0].plan_hours == 24


def test_audit_assignment_interval_must_equal_covered_demand_interval() -> None:
    """R5 4.1/T20-33: demand identity alone is insufficient provenance."""
    conn = connect(":memory:")
    _seed(conn)
    intervals = _settings().work_code_intervals
    intervals["D1"] = type(intervals["D1"])("07:00", "19:00", False)
    save_site_print_settings(conn, _settings(work_code_intervals=intervals))
    demand_start = datetime(2026, 8, 5, 6)
    demand_end = demand_start + timedelta(hours=12)
    assignment_start = datetime(2026, 8, 5, 7)
    assignment_end = assignment_start + timedelta(hours=12)
    demand = ShiftDemand(
        "D", "", demand_start, demand_end, 1,
        shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12,
    )
    _create_version(conn, [demand], [_assignment("A", "EMP-1", assignment_start, assignment_end, "D")])

    with pytest.raises(export.ExportProblemError) as exc:
        export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")
    assert exc.value.code == "WORK_PROVENANCE_INCOMPLETE"


def test_audit_corrupt_persisted_settings_return_stable_problem() -> None:
    """R6 2/T20-30: corrupt persisted settings cannot escape as exceptions."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    conn.execute(
        "UPDATE site_print_settings SET work_code_intervals_json = ? WHERE site_id = ?",
        ('["not", "an", "object"]', "SITE-1"),
    )

    result = export.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")

    assert isinstance(result, export.ExportProblem)
    assert result.problem_code == "PRINT_SETTINGS_INVALID"


def test_audit_large_roster_fails_before_clipping_single_sheet(monkeypatch: pytest.MonkeyPatch) -> None:
    """T20-25/T20-36: content below the page is not a valid READY PDF."""
    employee_ids = tuple(f"EMP-{index:02d}" for index in range(30))
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    monkeypatch.setattr(export, "_resolve_unicode_font", lambda: ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"))

    result = export.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")

    assert isinstance(result, export.ExportProblem)
    assert result.problem_code == "ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT"


def test_audit_pinned_production_reportlab_can_render_ready_pdf() -> None:
    """T20-03/04: the installed production dependency must render the PDF."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])

    result = export.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="Sierpien 2026")

    assert isinstance(result, export.ExportReady)
    assert result.pdf_bytes.startswith(b"%PDF")


def test_audit_membership_ambiguity_check_is_batched(monkeypatch: pytest.MonkeyPatch) -> None:
    """Section 20 regression matrix: absence export must not issue N reads."""
    employee_ids = ("EMP-1", "EMP-2", "EMP-3")
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    for index, employee_id in enumerate(employee_ids):
        append_availability_version(
            conn,
            availability_id=f"AV-{index}",
            employee_id=employee_id,
            kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2026, 8, 19),
            end_date=date(2026, 8, 25),
            active=True,
        )
    calls = 0
    original = employee_repository.list_memberships_for_employee

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(employee_repository, "list_memberships_for_employee", counted)
    export._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="August 2026")

    assert calls <= 1, "membership ambiguity must use one batch read, not one query per absent employee"
