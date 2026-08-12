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
