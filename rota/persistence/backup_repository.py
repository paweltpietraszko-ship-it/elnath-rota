"""Backup + diagnostic-metadata primitives (tasks/ROTA-T009/brief.md
operation 12). Lives in persistence, not application, per DEPENDENCY
BOUNDARY: application contains no SQL/table names (R4-11-B).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def backup_to(conn: sqlite3.Connection, destination: str) -> None:
    """Consistent SQLite backup semantics via the sqlite3 backup API."""
    dest_conn = sqlite3.connect(destination)
    try:
        conn.backup(dest_conn)
    finally:
        dest_conn.close()


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return sorted(row[0] for row in rows)


def diagnostics_payload(conn: sqlite3.Connection) -> dict:
    """Only technical metadata: schema version and per-table row counts.
    Deliberately excludes anything that could carry employee names,
    absence/medical note text, full schedule content, or secrets -- no row
    content is ever read here, only COUNT(*)."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": conn.execute("PRAGMA user_version").fetchone()[0],
        "table_row_counts": {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 -- table names from sqlite_master, not user input
            for table in _table_names(conn)
        },
    }
