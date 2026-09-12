"""ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS (brief.md exact SHA 0db122a):
narrow test matrix for the PDF export LAW guard, application-layer only
(generate_schedule_pdf directly) -- proves the fingerprint/one-time-ack
contract itself (brief.md sections 3-6). HTTP round-trip acceptance
(P1-P11) lives in tests/test_t021_export_api.py."""
from __future__ import annotations

import pytest

from datetime import date, datetime

from rota.application import schedule_export as SE
from rota.application.schedule_export import ExportLawBlocked, ExportProblem, ExportReady, generate_schedule_pdf
from rota.domain import ShiftKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings, _work_item


@pytest.fixture
def conn():
    connection = connect(":memory:")
    _seed(connection)
    try:
        yield connection
    finally:
        connection.close()


def _rest01_scenario(conn):
    # REST-01: D 06-18 day1, then N 00-16 day2 -- 6h gap, below the 11h
    # REST_MIN_HOURS fallback (no work_period_id/required_rest_after_hours
    # set on either Assignment).
    save_site_print_settings(conn, _settings())
    demand1, a1 = _work_item(1, 6, 18, kind=ShiftKind.D)
    demand2, a2 = _work_item(2, 0, 16, kind=ShiftKind.N)
    _create_version(conn, [demand1, demand2], [a1, a2])
    return a1, a2


def _export(conn, acknowledged=frozenset()):
    return generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="sierpień 2026", acknowledged_law_fingerprints=acknowledged)


def test_p1_working_without_law_still_prints(conn):
    save_site_print_settings(conn, _settings())
    demand, a = _work_item(1, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [a])
    result = _export(conn)
    assert isinstance(result, ExportReady)


def test_p3_fresh_unacknowledged_law_blocks_export(conn):
    _rest01_scenario(conn)
    result = _export(conn)
    assert isinstance(result, ExportLawBlocked)
    assert len(result.items) == 1
    assert result.items[0].rule == "REST-01"
    assert result.items[0].affected_assignment_or_employee == "EMP-1"
    assert result.items[0].fingerprint


def test_p5_acknowledged_fingerprint_unblocks_export(conn):
    _rest01_scenario(conn)
    blocked = _export(conn)
    assert isinstance(blocked, ExportLawBlocked)
    fingerprint = blocked.items[0].fingerprint
    result = _export(conn, acknowledged=frozenset({fingerprint}))
    assert isinstance(result, ExportReady)


def test_p7_next_export_requires_ack_again(conn):
    _rest01_scenario(conn)
    blocked = _export(conn)
    fingerprint = blocked.items[0].fingerprint
    ready = _export(conn, acknowledged=frozenset({fingerprint}))
    assert isinstance(ready, ExportReady)
    again = _export(conn)
    assert isinstance(again, ExportLawBlocked)


def test_p8_changed_structural_fact_invalidates_old_fingerprint(conn):
    a1, _a2 = _rest01_scenario(conn)
    blocked = _export(conn)
    stale_fingerprint = blocked.items[0].fingerprint

    # Same rule (REST-01), same employee, same assignment_id ("ASG-2") --
    # but a genuinely different structural fact: the second shift's actual
    # start/end moved (still an 8h < 11h gap, still REST-01).
    demand1, _ = _work_item(1, 6, 18, kind=ShiftKind.D)
    _demand2b, a2b = _work_item(2, 2, 18, kind=ShiftKind.N)
    lifecycle.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[],
        shift_demands=[demand1, _demand2b], assignments=[a1, a2b], deviations=[],
    )
    result = _export(conn, acknowledged=frozenset({stale_fingerprint}))
    assert isinstance(result, ExportLawBlocked)
    assert result.items[0].fingerprint != stale_fingerprint


def test_direct_post_without_fingerprints_is_blocked(conn):
    # P4, application-layer half: calling generate_schedule_pdf with no
    # acknowledgement at all (the default) is exactly what a direct POST
    # with no ack fingerprints reaches -- covered again at the HTTP layer
    # in tests/test_t021_export_api.py.
    _rest01_scenario(conn)
    result = generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="sierpień 2026")
    assert isinstance(result, ExportLawBlocked)


def test_non_law_deviation_never_blocks(conn):
    # P2: a real non-LAW HARD violation (COVERAGE-01: demand under-covered)
    # must never appear in the export LAW guard nor block the PDF.
    save_site_print_settings(conn, _settings())
    demand, a = _work_item(1, 6, 18, kind=ShiftKind.D)
    under_covered = demand.__class__(
        demand_id="DEM-1B", schedule_version_id="", start_datetime=demand.start_datetime,
        end_datetime=demand.end_datetime, required_primary_count=2, shift_kind=demand.shift_kind,
        catalog_kind=demand.catalog_kind,
    )
    _create_version(conn, [demand, under_covered], [a])
    result = _export(conn)
    assert isinstance(result, ExportReady)


def test_p9_version_changed_during_render_is_rejected(conn, monkeypatch):
    # brief.md section 6: a coordinator finalize/correction/REPLAN racing
    # this export's own render must never let already-validated-then-stale
    # bytes out the door -- simulated by mutating current mid-render.
    save_site_print_settings(conn, _settings())
    demand, a = _work_item(1, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [a])  # SV-1, no LAW -- would print fine on its own

    original_render = SE._render_pdf

    def _render_and_mutate_current(model, generated_at):
        demand2, a2 = _work_item(1, 6, 18, kind=ShiftKind.D)
        lifecycle.create_schedule_version(
            conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
            created_at=datetime(2026, 7, 26, 8), created_by="COORD-1", applied_rule_version_ids=[],
            shift_demands=[demand2], assignments=[a2], deviations=[], effective_from=date(2026, 7, 26),
        )
        return original_render(model, generated_at)

    monkeypatch.setattr(SE, "_render_pdf", _render_and_mutate_current)
    result = _export(conn)
    assert isinstance(result, ExportProblem)
    assert result.problem_code == "SCHEDULE_VERSION_CHANGED"


if __name__ == "__main__":
    print("test_export_unacknowledged_law module OK")
