"""Independent R3 reproducer for the export-LAW fingerprint contract."""
from dataclasses import replace

from rota.application.schedule_export import ExportLawBlocked, ExportReady, generate_schedule_pdf
from rota.domain import ShiftKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings, _work_item


def test_changed_required_rest_fact_does_not_inherit_old_export_ack():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand1, assignment1 = _work_item(1, 6, 18, kind=ShiftKind.D)
    demand2, assignment2 = _work_item(2, 0, 16, kind=ShiftKind.N)
    _create_version(conn, [demand1, demand2], [assignment1, assignment2])

    first = generate_schedule_pdf(
        conn, site_id="SITE-1", month=MONTH, period_label="sierpień 2026",
    )
    assert isinstance(first, ExportLawBlocked)
    old_fingerprint = first.items[0].fingerprint

    # Same rule/index/employee/assignment IDs and same timestamps.  Only the
    # structural legal fact changes: the first work period now requires 24h
    # rest instead of the legacy 11h fallback.  REST-01 still exists, but it
    # describes a different shortfall and must require a new confirmation.
    stricter_assignment1 = replace(assignment1, required_rest_after_hours=24)
    lifecycle.replace_working_snapshot(
        conn,
        version_id="SV-1",
        applied_rule_version_ids=[],
        shift_demands=[demand1, demand2],
        assignments=[stricter_assignment1, assignment2],
        deviations=[],
    )

    second = generate_schedule_pdf(
        conn,
        site_id="SITE-1",
        month=MONTH,
        period_label="sierpień 2026",
        acknowledged_law_fingerprints=frozenset({old_fingerprint}),
    )
    assert isinstance(second, ExportLawBlocked)
    assert second.items[0].fingerprint != old_fingerprint


def test_successful_export_ack_does_not_persist_or_change_lifecycle():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand1, assignment1 = _work_item(1, 6, 18, kind=ShiftKind.D)
    demand2, assignment2 = _work_item(2, 0, 16, kind=ShiftKind.N)
    _create_version(conn, [demand1, demand2], [assignment1, assignment2])

    before_version = conn.execute(
        "SELECT status FROM schedule_versions WHERE version_id = 'SV-1'",
    ).fetchone()
    before_deviations = conn.execute(
        "SELECT COUNT(*) FROM deviations WHERE schedule_version_id = 'SV-1'",
    ).fetchone()
    before_actions = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()

    blocked = generate_schedule_pdf(
        conn, site_id="SITE-1", month=MONTH, period_label="sierpień 2026",
    )
    assert isinstance(blocked, ExportLawBlocked)
    ready = generate_schedule_pdf(
        conn,
        site_id="SITE-1",
        month=MONTH,
        period_label="sierpień 2026",
        acknowledged_law_fingerprints=frozenset({blocked.items[0].fingerprint}),
    )
    assert isinstance(ready, ExportReady)

    assert conn.execute(
        "SELECT status FROM schedule_versions WHERE version_id = 'SV-1'",
    ).fetchone() == before_version
    assert conn.execute(
        "SELECT COUNT(*) FROM deviations WHERE schedule_version_id = 'SV-1'",
    ).fetchone() == before_deviations
    assert conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone() == before_actions
