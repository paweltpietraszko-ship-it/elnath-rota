from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as repository
from rota.persistence.db import MIGRATIONS, connect
from rota.persistence.schedule_errors import InvalidCurrentVersionTarget, NonEditableScheduleVersion
from tests.support.t008_fixtures import seed_base_entities
from tests.support.t009_fixtures import seed_real_object


MONTH = date(2026, 8, 1)


def _create_version(conn, version_id: str, parent_version_id: str | None, day: int):
    return lifecycle.create_schedule_version(
        conn,
        version_id=version_id,
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=parent_version_id,
        created_at=datetime(2026, 8, day, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[],
        assignments=[],
        deviations=[],
        effective_from=MONTH,
    )


def test_migration_9_to_10_preserves_existing_version_and_guards(tmp_path):
    db_path = tmp_path / "old-v9.db"
    old = sqlite3.connect(db_path)
    old.execute("PRAGMA foreign_keys = ON")
    for version, statements in MIGRATIONS:
        if version > 9:
            break
        old.execute("BEGIN")
        for statement in statements:
            old.execute(statement)
        old.execute(f"PRAGMA user_version = {version}")
        old.execute("COMMIT")
    seed_base_entities(old)
    old.execute(
        "INSERT INTO schedule_versions "
        "(version_id, site_id, month, parent_version_id, created_at, created_by, status, effective_from, planning_regime) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("SV-OLD", "SITE-1", MONTH.isoformat(), None, datetime(2026, 8, 1, 8).isoformat(),
         "COORD-1", "WORKING", MONTH.isoformat(), "ORDINARY"),
    )
    old.commit()
    old.close()

    migrated = connect(db_path)
    assert migrated.execute("PRAGMA user_version").fetchone()[0] == 10
    assert repository.get_schedule_version_header(migrated, "SV-OLD").excluded_from_history is False
    assert migrated.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError, match="physical delete"):
        migrated.execute("DELETE FROM schedule_versions WHERE version_id = 'SV-OLD'")


def test_exclusion_only_hides_noncurrent_draft_and_keeps_snapshot_and_pointer(tmp_path):
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_version(conn, "SV-1", None, 1)
    _create_version(conn, "SV-2", "SV-1", 2)
    counts_before = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("schedule_versions", "shift_demands", "assignments", "deviations")
    }

    lifecycle.exclude_version_from_history(
        conn, site_id="SITE-1", month=MONTH, version_id="SV-1"
    )

    assert repository.get_current_version_id(conn, "SITE-1", MONTH) == "SV-2"
    assert [v.version_id for v in repository.list_schedule_versions(conn, "SITE-1", MONTH)] == ["SV-2"]
    all_versions = repository.list_schedule_versions(conn, "SITE-1", MONTH, include_excluded=True)
    assert [v.version_id for v in all_versions] == ["SV-1", "SV-2"]
    assert all_versions[0].excluded_from_history is True
    repository.get_schedule_snapshot(conn, "SV-1")
    counts_after = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("schedule_versions", "shift_demands", "assignments", "deviations")
    }
    assert counts_after == counts_before
    with pytest.raises(sqlite3.IntegrityError, match="physical delete"):
        conn.execute("DELETE FROM schedule_versions WHERE version_id = 'SV-1'")


def test_exclusion_rejects_current_final_and_cross_month_targets(tmp_path):
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_version(conn, "SV-1", None, 1)
    with pytest.raises(NonEditableScheduleVersion, match="current"):
        lifecycle.exclude_version_from_history(conn, site_id="SITE-1", month=MONTH, version_id="SV-1")

    lifecycle.finalize_schedule_version(conn, version_id="SV-1")
    _create_version(conn, "SV-2", "SV-1", 2)
    with pytest.raises(NonEditableScheduleVersion, match="FINAL"):
        lifecycle.exclude_version_from_history(conn, site_id="SITE-1", month=MONTH, version_id="SV-1")
    with pytest.raises(InvalidCurrentVersionTarget):
        lifecycle.exclude_version_from_history(
            conn, site_id="SITE-1", month=date(2026, 9, 1), version_id="SV-1"
        )
    assert repository.get_schedule_version_header(conn, "SV-1").excluded_from_history is False


def test_vertical_api_hides_old_draft_but_keeps_row_and_surfaces_target_warning():
    conn = connect(":memory:")
    state = seed_real_object(
        conn, case_id="audit-hide", month=MONTH, seed=77, coordinator_id=DEV_COORDINATOR_ID
    )
    site_id = state.site.site_id
    lifecycle.create_schedule_version(
        conn, version_id="SV-1", site_id=site_id, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8), created_by=DEV_COORDINATOR_ID,
        applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[], effective_from=MONTH,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-2", site_id=site_id, month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8), created_by=DEV_COORDINATOR_ID,
        applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[], effective_from=MONTH,
    )
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        with TestClient(app) as client:
            before = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}")
            assert before.status_code == 200
            assert {v["version_id"] for v in before.json()["version_history"]} == {"SV-1", "SV-2"}
            assert any("missing target_hours" in warning for warning in before.json()["warnings"])

            hidden = client.post(
                f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/exclude-from-history",
                json={"version_id": "SV-1"},
            )
            assert hidden.status_code == 204
            after = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}")
            assert [v["version_id"] for v in after.json()["version_history"]] == ["SV-2"]
            assert conn.execute(
                "SELECT excluded_from_history FROM schedule_versions WHERE version_id = 'SV-1'"
            ).fetchone() == (1,)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()
