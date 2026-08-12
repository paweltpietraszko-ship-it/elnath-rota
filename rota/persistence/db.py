"""Connection + idempotent schema init for Rota's local SQLite store.

ROTA-T004 (tasks/ROTA-T004/brief.md, DATABASE FOUNDATION): path is supplied
by the caller -- this module never hardcodes a desktop data file location.
No migration framework: CREATE TABLE IF NOT EXISTS is enough for the pilot.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS site_profiles (
    profile_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    active INTEGER NOT NULL,
    day_only_blocks_n INTEGER NOT NULL,
    external_support_enabled INTEGER NOT NULL,
    training_s_enabled INTEGER NOT NULL,
    training_s_weekdays_only INTEGER NOT NULL,
    training_s_default_readiness_threshold INTEGER NOT NULL,
    rolling_7d_decision_threshold_hours INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS standard_shifts (
    profile_id TEXT NOT NULL REFERENCES site_profiles(profile_id),
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    end_next_day INTEGER NOT NULL,
    required_primary_count INTEGER NOT NULL,
    PRIMARY KEY (profile_id, seq)
);

-- ROTA-T005: Rule Store (append-only SiteRuleVersion) + Decision Ledger.
-- Triggers below physically forbid UPDATE/DELETE, matching the append-only
-- pattern adapted from Elnath Memory Engine's store/schema.sql.

CREATE TABLE IF NOT EXISTS site_rule_versions (
    rule_version_id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    category TEXT NOT NULL,
    rule_kind TEXT,
    structured_parameters TEXT,
    enforcement TEXT NOT NULL,
    resolution_status TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    supersedes_rule_version_id TEXT REFERENCES site_rule_versions(rule_version_id),
    description TEXT,
    source TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS decision_records (
    decision_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    chain_seq INTEGER NOT NULL,
    statement TEXT NOT NULL,
    coordinator_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    rule_version_id TEXT REFERENCES site_rule_versions(rule_version_id),
    rel TEXT,
    predecessor_decision_id TEXT REFERENCES decision_records(decision_id),
    UNIQUE (site_id, rule_id, chain_seq)
);

CREATE TABLE IF NOT EXISTS decision_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_decision_id TEXT NOT NULL REFERENCES decision_records(decision_id),
    rel TEXT NOT NULL,
    to_decision_id TEXT NOT NULL REFERENCES decision_records(decision_id),
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS site_rule_versions_no_update BEFORE UPDATE ON site_rule_versions
BEGIN SELECT RAISE(ABORT, 'site_rule_versions is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS site_rule_versions_no_delete BEFORE DELETE ON site_rule_versions
BEGIN SELECT RAISE(ABORT, 'site_rule_versions is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS decision_records_no_update BEFORE UPDATE ON decision_records
BEGIN SELECT RAISE(ABORT, 'decision_records is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS decision_records_no_delete BEFORE DELETE ON decision_records
BEGIN SELECT RAISE(ABORT, 'decision_records is append-only: DELETE forbidden'); END;

CREATE TRIGGER IF NOT EXISTS decision_relations_no_update BEFORE UPDATE ON decision_relations
BEGIN SELECT RAISE(ABORT, 'decision_relations is append-only: UPDATE forbidden'); END;
CREATE TRIGGER IF NOT EXISTS decision_relations_no_delete BEFORE DELETE ON decision_relations
BEGIN SELECT RAISE(ABORT, 'decision_relations is append-only: DELETE forbidden'); END;
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the Rota SQLite store at db_path and ensure its schema exists."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA_SQL)


if __name__ == "__main__":
    print("persistence.db module OK")
