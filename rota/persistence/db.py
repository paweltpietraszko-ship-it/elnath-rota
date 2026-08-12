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
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

LATEST_SCHEMA_VERSION = 2


class UnsupportedSchemaVersion(Exception):
    """Raised when a database's PRAGMA user_version is newer than this
    binary understands. Never silently downgrades or rewrites it."""


# ---------------------------------------------------------------------------
# Migration 1 -- baseline: exactly the pre-T008 T004/T005 schema, unchanged.
# CREATE-IF-NOT-EXISTS statements so a legacy database that already has these
# objects (created by the old unversioned init_schema()) converges cleanly.
# ---------------------------------------------------------------------------
_MIGRATION_1: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS site_profiles (
        profile_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        active INTEGER NOT NULL,
        day_only_blocks_n INTEGER NOT NULL,
        external_support_enabled INTEGER NOT NULL,
        training_s_enabled INTEGER NOT NULL,
        training_s_weekdays_only INTEGER NOT NULL,
        training_s_default_readiness_threshold INTEGER NOT NULL,
        rolling_7d_decision_threshold_hours INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS standard_shifts (
        profile_id TEXT NOT NULL REFERENCES site_profiles(profile_id),
        seq INTEGER NOT NULL,
        kind TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        end_next_day INTEGER NOT NULL,
        required_primary_count INTEGER NOT NULL,
        PRIMARY KEY (profile_id, seq)
    )""",
    """CREATE TABLE IF NOT EXISTS rule_families (
        rule_id TEXT PRIMARY KEY,
        site_id TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS site_rule_versions (
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
    )""",
    """CREATE TABLE IF NOT EXISTS decision_records (
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
    )""",
    """CREATE TABLE IF NOT EXISTS decision_relations (
        relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_decision_id TEXT NOT NULL REFERENCES decision_records(decision_id),
        rel TEXT NOT NULL,
        to_decision_id TEXT NOT NULL REFERENCES decision_records(decision_id),
        created_at TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS rule_families_no_update BEFORE UPDATE ON rule_families
       BEGIN SELECT RAISE(ABORT, 'rule_families is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS rule_families_no_delete BEFORE DELETE ON rule_families
       BEGIN SELECT RAISE(ABORT, 'rule_families is append-only: DELETE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS site_rule_versions_no_update BEFORE UPDATE ON site_rule_versions
       BEGIN SELECT RAISE(ABORT, 'site_rule_versions is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS site_rule_versions_no_delete BEFORE DELETE ON site_rule_versions
       BEGIN SELECT RAISE(ABORT, 'site_rule_versions is append-only: DELETE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS decision_records_no_update BEFORE UPDATE ON decision_records
       BEGIN SELECT RAISE(ABORT, 'decision_records is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS decision_records_no_delete BEFORE DELETE ON decision_records
       BEGIN SELECT RAISE(ABORT, 'decision_records is append-only: DELETE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS decision_relations_no_update BEFORE UPDATE ON decision_relations
       BEGIN SELECT RAISE(ABORT, 'decision_relations is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS decision_relations_no_delete BEFORE DELETE ON decision_relations
       BEGIN SELECT RAISE(ABORT, 'decision_relations is append-only: DELETE forbidden'); END""",
)


# ---------------------------------------------------------------------------
# Migration 2 -- ROTA-T008: the full operational LocalStore.
# ---------------------------------------------------------------------------
_MIGRATION_2: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS sites (
        site_id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL REFERENCES site_profiles(profile_id),
        display_name TEXT NOT NULL,
        active INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS coordinators (
        coordinator_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        active INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS coordinator_site_associations (
        coordinator_id TEXT NOT NULL REFERENCES coordinators(coordinator_id),
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        active INTEGER NOT NULL,
        PRIMARY KEY (coordinator_id, site_id)
    )""",
    """CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        active_from TEXT NOT NULL,
        active_to TEXT,
        day_only INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS site_memberships (
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        membership_kind TEXT NOT NULL,
        enabled INTEGER NOT NULL,
        readiness_state TEXT NOT NULL,
        readiness_source TEXT NOT NULL,
        PRIMARY KEY (employee_id, site_id)
    )""",
    """CREATE TABLE IF NOT EXISTS external_support_windows (
        window_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        start_datetime TEXT NOT NULL,
        end_datetime TEXT NOT NULL,
        active INTEGER NOT NULL,
        allowed_shift_kind TEXT
    )""",
    # ROTA-T008 AVAILABILITYRECORD -- APPEND-ONLY HISTORY: availability_id
    # names one logical family; chain_seq mirrors decision_ledger's linear
    # chain pattern (MAX+1, current end = MAX(chain_seq) per family).
    """CREATE TABLE IF NOT EXISTS availability_versions (
        availability_version_id TEXT PRIMARY KEY,
        availability_id TEXT NOT NULL,
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        chain_seq INTEGER NOT NULL,
        kind TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        active INTEGER NOT NULL,
        supersedes_availability_version_id TEXT REFERENCES availability_versions(availability_version_id),
        note TEXT,
        UNIQUE (availability_id, chain_seq)
    )""",
    """CREATE TRIGGER IF NOT EXISTS availability_versions_no_update BEFORE UPDATE ON availability_versions
       BEGIN SELECT RAISE(ABORT, 'availability_versions is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS availability_versions_no_delete BEFORE DELETE ON availability_versions
       BEGIN SELECT RAISE(ABORT, 'availability_versions is append-only: DELETE forbidden'); END""",
    """CREATE TABLE IF NOT EXISTS calendar_days (
        date TEXT PRIMARY KEY,
        holiday INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS work_balance_targets (
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        month TEXT NOT NULL,
        target_hours INTEGER NOT NULL,
        PRIMARY KEY (employee_id, month)
    )""",
    # ScheduleVersion aggregate. status/lineage semantics are enforced by
    # rota/persistence/schedule_repository.py; the triggers below only
    # protect the two invariants SQL can express cleanly and that no
    # repository bug should ever be able to bypass: FINAL is physically
    # immutable, and identity/lineage header fields never change once set.
    """CREATE TABLE IF NOT EXISTS schedule_versions (
        version_id TEXT PRIMARY KEY,
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        parent_version_id TEXT REFERENCES schedule_versions(version_id),
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL REFERENCES coordinators(coordinator_id),
        status TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS schedule_versions_no_update_if_final
       BEFORE UPDATE ON schedule_versions
       WHEN OLD.status LIKE 'FINAL%'
       BEGIN SELECT RAISE(ABORT, 'schedule_versions: FINAL header is immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS schedule_versions_no_identity_change
       BEFORE UPDATE ON schedule_versions
       WHEN NEW.version_id IS NOT OLD.version_id
         OR NEW.site_id IS NOT OLD.site_id
         OR NEW.month IS NOT OLD.month
         OR NEW.parent_version_id IS NOT OLD.parent_version_id
         OR NEW.created_at IS NOT OLD.created_at
         OR NEW.created_by IS NOT OLD.created_by
       BEGIN SELECT RAISE(ABORT, 'schedule_versions: identity/lineage fields are immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS schedule_versions_no_delete
       BEFORE DELETE ON schedule_versions
       BEGIN SELECT RAISE(ABORT, 'schedule_versions: physical delete is not a supported operation'); END""",
    """CREATE TABLE IF NOT EXISTS schedule_version_applied_rules (
        version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        seq INTEGER NOT NULL,
        rule_version_id TEXT NOT NULL REFERENCES site_rule_versions(rule_version_id),
        PRIMARY KEY (version_id, seq)
    )""",
    """CREATE TABLE IF NOT EXISTS current_schedule_versions (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        PRIMARY KEY (site_id, month)
    )""",
    """CREATE TABLE IF NOT EXISTS shift_demands (
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        demand_id TEXT NOT NULL,
        start_datetime TEXT NOT NULL,
        end_datetime TEXT NOT NULL,
        required_primary_count INTEGER NOT NULL,
        PRIMARY KEY (schedule_version_id, demand_id)
    )""",
    """CREATE TABLE IF NOT EXISTS assignments (
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        assignment_id TEXT NOT NULL,
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        start_datetime TEXT NOT NULL,
        end_datetime TEXT NOT NULL,
        role TEXT NOT NULL,
        state TEXT NOT NULL,
        frozen INTEGER NOT NULL,
        covers_demand_id TEXT,
        mentor_primary_assignment_id TEXT,
        PRIMARY KEY (schedule_version_id, assignment_id)
    )""",
    """CREATE TABLE IF NOT EXISTS deviations (
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        deviation_id TEXT NOT NULL,
        category TEXT NOT NULL,
        source_reference TEXT NOT NULL,
        affected_assignment_or_employee TEXT NOT NULL,
        acknowledged INTEGER NOT NULL,
        acknowledged_by TEXT REFERENCES coordinators(coordinator_id),
        acknowledged_at TEXT,
        reason TEXT,
        PRIMARY KEY (schedule_version_id, deviation_id)
    )""",
)

# BEFORE INSERT/UPDATE/DELETE guards for FINAL immutability of child content,
# generated once per (table, version-fk-column) instead of hand-duplicated.
_FINAL_CHILD_TABLES = (
    ("shift_demands", "schedule_version_id"),
    ("assignments", "schedule_version_id"),
    ("deviations", "schedule_version_id"),
    ("schedule_version_applied_rules", "version_id"),
)


def _final_guard_triggers() -> tuple[str, ...]:
    triggers = []
    for table, version_col in _FINAL_CHILD_TABLES:
        for verb, ref in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
            triggers.append(f"""
                CREATE TRIGGER IF NOT EXISTS {table}_no_{verb.lower()}_if_final
                BEFORE {verb} ON {table}
                WHEN (SELECT status FROM schedule_versions WHERE version_id = {ref}.{version_col}) LIKE 'FINAL%'
                BEGIN SELECT RAISE(ABORT, '{table}: FINAL ScheduleVersion content is immutable'); END
            """)
    return tuple(triggers)


MIGRATIONS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (1, _MIGRATION_1),
    (2, _MIGRATION_2 + _final_guard_triggers()),
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the Rota SQLite store at db_path, migrate
    it to the latest schema, and return the connection."""
    conn = sqlite3.connect(db_path)
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
