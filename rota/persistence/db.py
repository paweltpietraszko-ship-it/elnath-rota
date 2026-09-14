"""Connection + ordered SQLite migration for Rota's local LocalStore.

ROTA-T004 (tasks/ROTA-T004/brief.md, DATABASE FOUNDATION): path is supplied
by the caller -- this module never hardcodes a desktop data file location.

ROTA-T008 (tasks/ROTA-T008/brief.md, ARCHITECTURE DECISION -- SCHEMA
VERSIONING STARTS NOW): replaces unversioned CREATE-only schema growth with
an ordered `PRAGMA user_version` migration mechanism. Each migration step
is a tuple of individual DDL statements (not one script blob) executed via
plain conn.execute() inside an explicit BEGIN/COMMIT/ROLLBACK -- SQLite's
DDL is genuinely transactional this way, unlike executescript(), which
issues an implicit COMMIT before running and would not roll back a partial
step on failure. Note `with conn:` alone is NOT sufficient here: Python's
sqlite3 module only auto-wraps DML in an implicit transaction, not DDL, so
CREATE TABLE/TRIGGER statements would commit immediately regardless of a
later exception in the same `with conn:` block.

2026-09 oversized-file refactor (owner-authorized, mechanical-only, zero
product-behavior change): the individual _MIGRATION_N tuples now live in
db_migrations_1_2.py / db_migrations_3_9.py / db_migrations_10_17.py /
db_migrations_18_21.py, grouped by era. Every name is re-imported here so
`rota.persistence.db._MIGRATION_1` etc. keep resolving as module attributes
exactly as before (tests/test_local_store_schema_migration.py accesses
several of them directly)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from rota.persistence.db_migrations_1_2 import _MIGRATION_1, _MIGRATION_2, _final_guard_triggers
from rota.persistence.db_migrations_3_9 import (
    _MIGRATION_3,
    _MIGRATION_4,
    _MIGRATION_5,
    _MIGRATION_6,
    _MIGRATION_7,
    _MIGRATION_8,
    _MIGRATION_9,
)
from rota.persistence.db_migrations_10_17 import (
    _MIGRATION_10,
    _MIGRATION_11,
    _MIGRATION_12,
    _MIGRATION_13,
    _MIGRATION_14,
    _MIGRATION_15,
    _MIGRATION_16,
    _MIGRATION_17,
)
from rota.persistence.db_migrations_18_21 import (
    _MIGRATION_19,
    _MIGRATION_20,
    _MIGRATION_21,
    _migration_18_encrypt_existing_persisted_names,
)

LATEST_SCHEMA_VERSION = 21


class UnsupportedSchemaVersion(Exception):
    """Raised when a database's PRAGMA user_version is newer than this
    binary understands. Never silently downgrades or rewrites it."""


MIGRATIONS: tuple[tuple[int, tuple[str, ...] | Callable[[sqlite3.Connection], None]], ...] = (
    (1, _MIGRATION_1),
    (2, _MIGRATION_2 + _final_guard_triggers()),
    (3, _MIGRATION_3),
    (4, _MIGRATION_4),
    (5, _MIGRATION_5),
    (6, _MIGRATION_6),
    (7, _MIGRATION_7),
    (8, _MIGRATION_8),
    (9, _MIGRATION_9),
    (10, _MIGRATION_10),
    (11, _MIGRATION_11),
    (12, _MIGRATION_12),
    (13, _MIGRATION_13),
    (14, _MIGRATION_14),
    (15, _MIGRATION_15),
    (16, _MIGRATION_16),
    (17, _MIGRATION_17),
    # ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE: a data
    # migration (a Python callable, not a tuple of DDL/DML strings) --
    # see migrate()'s loop below for how the two kinds are dispatched.
    (18, _migration_18_encrypt_existing_persisted_names),
    (19, _MIGRATION_19),
    (20, _MIGRATION_20),
    (21, _MIGRATION_21),
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the Rota SQLite store at db_path, migrate
    it to the latest schema, and return the connection.

    ROTA-T027: check_same_thread=False. api/deps.py::get_conn() is a
    FastAPI sync-generator dependency; FastAPI dispatches its open
    (__enter__) and close (__exit__) as two *separate*
    anyio.to_thread.run_sync calls with no guarantee both land on the
    same worker thread, and under concurrent request load they often
    don't -- sqlite3's default check_same_thread=True then raises
    ProgrammingError on close. Each connection here is still used
    strictly sequentially (open, then request handling, then close --
    never concurrently by more than one thread at once), which is
    exactly the usage pattern check_same_thread=False is for; it only
    disables sqlite3's own same-thread assertion, not any real
    thread-safety."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply every migration step newer than the database's current
    PRAGMA user_version, in order, each as its own atomic transaction.
    Fails closed (UnsupportedSchemaVersion) without any mutation if the
    database's version is newer than this binary understands."""
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    if current_version > LATEST_SCHEMA_VERSION:
        raise UnsupportedSchemaVersion(
            f"database schema version {current_version} is newer than this binary's "
            f"latest known version {LATEST_SCHEMA_VERSION}; refusing to open"
        )
    for version, statements in MIGRATIONS:
        if version <= current_version:
            continue
        # `with conn:` only auto-wraps DML in an implicit transaction --
        # Python's sqlite3 module does not precede DDL (CREATE TABLE/TRIGGER)
        # with an implicit BEGIN, so CREATE statements commit immediately
        # and survive a later exception in the same `with conn:` block. An
        # explicit BEGIN/COMMIT/ROLLBACK is required for real DDL atomicity.
        conn.execute("BEGIN")
        try:
            if callable(statements):
                statements(conn)
            else:
                for statement in statements:
                    conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {version}")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")


def init_schema(conn: sqlite3.Connection) -> None:
    """Backward-compatible alias for the pre-T008 name; now migrates."""
    migrate(conn)


if __name__ == "__main__":
    print("persistence.db module OK")
