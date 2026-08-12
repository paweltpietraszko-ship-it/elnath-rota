"""ROTA-T008 test matrix category A (SCHEMA / MIGRATION), REQUIRED LEGACY
MIGRATION SCENARIO, and category Q (PLANNING ISOLATION).
"""
from __future__ import annotations

import ast
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from rota.persistence.db import LATEST_SCHEMA_VERSION, UnsupportedSchemaVersion, connect, migrate
from rota.persistence.site_memory import effective_rule_on
from rota.persistence.site_profile_repository import get_site_profile, save_site_profile
from rota.persistence.site_rule_assembly import assemble_site_rules
from rota.persistence.site_rule_repository import insert_site_rule_version
from tests.support.t008_fixtures import make_profile, make_rule_version, seed_rule_decision


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def test_a1_empty_db_migrates_to_latest_schema(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    assert "schedule_versions" in _table_names(conn)
    assert "site_profiles" in _table_names(conn)


def test_a2_legacy_nonempty_db_migrates_without_data_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)  # simulate the pre-T008 world stopping at migration 1's tables
    save_site_profile(conn, make_profile("LEGACY-PROF"))
    insert_site_rule_version(conn, make_rule_version(rule_version_id="RV-LEGACY", site_id="LEGACY-SITE"))
    conn.close()

    reopened = connect(db_path)
    assert reopened.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    assert get_site_profile(reopened, "LEGACY-PROF").profile_id == "LEGACY-PROF"
    assert "sites" in _table_names(reopened)


def test_a3_reconnect_to_latest_db_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    connect(db_path).close()
    conn = connect(db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    save_site_profile(conn, make_profile())
    assert get_site_profile(conn, "PROF-1").profile_id == "PROF-1"


def test_a4_future_schema_version_fails_closed_without_mutation(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    connect(db_path).close()
    conn = sqlite3.connect(db_path)
    conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION + 1}")
    conn.close()

    reopened = sqlite3.connect(db_path)
    with pytest.raises(UnsupportedSchemaVersion):
        migrate(reopened)
    assert reopened.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION + 1


def test_a5_failed_migration_step_rolls_back_schema_version_and_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import rota.persistence.db as db_module

    db_path = tmp_path / "rota.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    broken_migration_2 = db_module._MIGRATION_2 + ("SELECT this_is_not_valid_sql_and_will_fail",)
    monkeypatch.setattr(db_module, "MIGRATIONS", ((1, db_module._MIGRATION_1), (2, broken_migration_2)))

    with pytest.raises(sqlite3.OperationalError):
        db_module.migrate(conn)

    # migration 1 already committed as its own atomic step before migration
    # 2 was attempted; only the failed step (2) rolls back, not step 1.
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    assert "sites" not in _table_names(conn)
    assert "site_profiles" in _table_names(conn)


def test_legacy_migration_scenario_preserves_t005_effective_selection_and_t007_assembly(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    save_site_profile(conn, make_profile("PROF-1"))
    decision = seed_rule_decision(conn, rule_id="RULE-1", site_id="SITE-1")
    conn.close()

    reopened = connect(db_path)
    assert reopened.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    effective = effective_rule_on(reopened, "SITE-1", "RULE-1", date(2026, 8, 15))
    assert effective.rule_version.rule_version_id == decision.rule_version_id
    resolved, needs_resolution = assemble_site_rules(reopened, "SITE-1", ["RULE-1"], date(2026, 8, 15))
    assert any(r.rule_version_id == decision.rule_version_id for r in resolved)
    assert needs_resolution == ()

    reopened.close()
    twice_reopened = connect(db_path)
    assert twice_reopened.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION


def test_q_planning_module_has_no_persistence_coupling() -> None:
    planning_dir = Path(__file__).resolve().parents[1] / "rota" / "planning"
    for path in planning_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith("sqlite3"), f"{path}: forbidden sqlite3 import"
                assert not name.startswith("rota.persistence"), f"{path}: forbidden rota.persistence import"
