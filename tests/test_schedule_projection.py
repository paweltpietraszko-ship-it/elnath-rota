"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 8: narrow tests for the
new rota.application.schedule_projection module -- the projection
extracted (mechanically, byte-identical) out of schedule_export.py so
PDF and the external Excel API share one builder. Reuses
tests/test_t020.py's own fixtures, same pattern as
tests/test_t047_print_export.py.
"""
from __future__ import annotations

from datetime import date

from rota.application import schedule_export as SE
from rota.application import schedule_projection
from rota.application.durable_inputs import append_availability
from rota.domain import AvailabilityKind, ShiftKind
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings, _work_item


def test_module_never_imports_reportlab():
    # brief.md section 8: "Nowy projection owner nie importuje reportlab
    # i nie zna komórek Excela."
    source = open("rota/application/schedule_projection.py", encoding="utf-8").read()
    assert "import reportlab" not in source
    assert "from reportlab" not in source


def test_build_schedule_projection_matches_compatibility_alias():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand, assignment = _work_item(1, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])

    via_projection = schedule_projection.build_schedule_projection(conn, site_id="SITE-1", month=MONTH, period_label="x")
    via_alias = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert SE._document_revision(via_projection) == SE._document_revision(via_alias)
    assert via_projection.rows == via_alias.rows


def test_delegation_day_shows_del_and_contributes_hours():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand, assignment = _work_item(1, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])

    append_availability(
        conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DEL", employee_id="EMP-1",
        kind=AvailabilityKind.DELEGACJA, start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True,
        delegation_hours=8,
    )

    model = schedule_projection.build_schedule_projection(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "EMP-1")
    del_index = date(2026, 8, 5).day - 1
    assert row.plan[del_index] == schedule_projection.DELEGACJA_LABEL
    assert row.plan_hours >= 8
