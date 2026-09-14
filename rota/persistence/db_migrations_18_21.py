"""Migrations 18-21: RODO display-name-at-rest encryption (a one-time data
migration, not DDL), the ROTA-T065 store-roles TEXT-column era (superseded
but left in place), the per-Site configurable role catalog
(ROTA-T065-CONFIGURABLE-ROLES), and the ORDINARY hourly-availability window
columns (ROTA-T065-ORDINARY-TIME-AVAILABILITY).

Split out of rota/persistence/db.py (2026-09 oversized-file refactor,
mechanical-only, zero behavior change)."""
from __future__ import annotations

import sqlite3


def _migration_18_encrypt_existing_persisted_names(conn: sqlite3.Connection) -> None:
    """ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE brief.md
    (exact SHA 5683bac) section 4: one-time, deterministic encryption of
    any existing plaintext plan_previews.warnings_json /
    decision_required_snapshots.payload_json, so this fix protects
    already-persisted records too, not only new writes after this
    version. A local import (not top-of-file) keeps this module's
    normal import graph free of a hard dependency on pii_crypto for
    every caller that never needs this one-time migration path.

    decision_required_snapshots is append-only via its own
    BEFORE UPDATE/DELETE triggers (created in _MIGRATION_2). Those
    are dropped and recreated byte-identical to their original
    definition WITHIN this same migration transaction (migrate() wraps
    every step in one BEGIN/COMMIT/ROLLBACK) -- a failure here rolls
    back both the data and the trigger state together, so the
    append-only invariant is never actually weakened for ordinary
    runtime; only this one versioned migration step can touch it at
    all, exactly as the brief requires."""
    from rota.persistence import pii_crypto

    rows = conn.execute("SELECT site_id, month, warnings_json FROM plan_previews").fetchall()
    if rows:
        key = pii_crypto.resolve_key(conn)
        for site_id, month, warnings_json in rows:
            if isinstance(warnings_json, (bytes, bytearray)):
                continue  # already encrypted -- re-running this migration is a no-op
            aad = pii_crypto.bind_aad("PLAN_PREVIEW_WARNINGS", site_id, month)
            conn.execute(
                "UPDATE plan_previews SET warnings_json = ? WHERE site_id = ? AND month = ?",
                (pii_crypto.encrypt_text(key, warnings_json, aad), site_id, month),
            )

    conn.execute("DROP TRIGGER IF EXISTS decision_required_snapshots_no_update")
    conn.execute("DROP TRIGGER IF EXISTS decision_required_snapshots_no_delete")
    try:
        rows = conn.execute("SELECT decision_required_id, payload_json FROM decision_required_snapshots").fetchall()
        if rows:
            key = pii_crypto.resolve_key(conn)
            for decision_required_id, payload_json in rows:
                if isinstance(payload_json, (bytes, bytearray)):
                    continue
                aad = pii_crypto.bind_aad("DECISION_REQUIRED_PAYLOAD", decision_required_id)
                conn.execute(
                    "UPDATE decision_required_snapshots SET payload_json = ? WHERE decision_required_id = ?",
                    (pii_crypto.encrypt_text(key, payload_json, aad), decision_required_id),
                )
    finally:
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS decision_required_snapshots_no_update
               BEFORE UPDATE ON decision_required_snapshots
               BEGIN SELECT RAISE(ABORT, 'decision_required_snapshots is append-only: UPDATE forbidden'); END"""
        )
        conn.execute(
            """CREATE TRIGGER IF NOT EXISTS decision_required_snapshots_no_delete
               BEFORE DELETE ON decision_required_snapshots
               BEGIN SELECT RAISE(ABORT, 'decision_required_snapshots is append-only: DELETE forbidden'); END"""
        )


# ---------------------------------------------------------------------------
# Migration 19 -- ROTA-T065: ORDINARY store roles. `allowed_roles` on
# site_memberships is a comma-joined EmployeeRole.value list (empty/NULL =
# no roles, the correct default for every OCHRONA/legacy membership, which
# never has a role-bearing demand to consult it). `required_role` on
# standard_shifts/shift_demands is a single EmployeeRole.value or NULL
# (OCHRONA/legacy never sets it). Every new column is nullable/empty-
# default; no existing row's meaning changes.
# ---------------------------------------------------------------------------
_MIGRATION_19: tuple[str, ...] = (
    "ALTER TABLE site_memberships ADD COLUMN allowed_roles TEXT",
    "ALTER TABLE standard_shifts ADD COLUMN required_role TEXT",
    "ALTER TABLE shift_demands ADD COLUMN required_role TEXT",
)


# ---------------------------------------------------------------------------
# Migration 20 -- ROTA-T065-CONFIGURABLE-ROLES: replaces the fixed 2-value
# EmployeeRole enum (migration 19) with a per-Site role catalog. The old
# allowed_roles/required_role TEXT columns from migration 19 are left in
# place, unused (brief.md section 10: existing ORDINARY data is test-only,
# no migration of it is required) -- new columns/tables only, no destructive
# ALTER. `site_roles`/`role_coverage_authorizations` are the one owner
# (rota/persistence/site_role_repository.py); `schedule_version_employee_
# positions` is a write-once-per-version historical snapshot for print,
# owned for reads by schedule_repository.py.
# ---------------------------------------------------------------------------
_MIGRATION_20: tuple[str, ...] = (
    "ALTER TABLE site_memberships ADD COLUMN position_role_id TEXT",
    "ALTER TABLE standard_shifts ADD COLUMN required_role_id TEXT",
    "ALTER TABLE shift_demands ADD COLUMN required_role_id TEXT",
    "ALTER TABLE shift_demands ADD COLUMN required_role_name TEXT",
    """CREATE TABLE IF NOT EXISTS site_roles (
        role_id TEXT PRIMARY KEY,
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        display_name TEXT NOT NULL,
        active INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS role_coverage_authorizations (
        authorization_id TEXT PRIMARY KEY,
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        covered_role_id TEXT NOT NULL REFERENCES site_roles(role_id),
        start_datetime TEXT NOT NULL,
        end_datetime TEXT NOT NULL,
        active INTEGER NOT NULL
    )""",
    # One row per (version, employee) -- the ONLY historical source for
    # printed position labels (brief.md section 6); never re-derived from
    # today's site_memberships.position_role_id.
    """CREATE TABLE IF NOT EXISTS schedule_version_employee_positions (
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        employee_id TEXT NOT NULL REFERENCES employees(employee_id),
        role_id TEXT NOT NULL,
        role_name TEXT NOT NULL,
        PRIMARY KEY (schedule_version_id, employee_id)
    )""",
)


# ---------------------------------------------------------------------------
# Migration 21 -- ROTA-T065-ORDINARY-TIME-AVAILABILITY brief.md section
# 2/10: the one new AvailabilityKind (UNAVAILABLE_TIME_WINDOW) stores its
# daily [start_time, end_time) window on the SAME append-only
# availability_versions row -- both columns stay NULL for every existing
# kind, no behavior change to them. New columns only, no destructive ALTER.
# ---------------------------------------------------------------------------
_MIGRATION_21: tuple[str, ...] = (
    "ALTER TABLE availability_versions ADD COLUMN start_time TEXT",
    "ALTER TABLE availability_versions ADD COLUMN end_time TEXT",
)


if __name__ == "__main__":
    print("persistence.db_migrations_18_21 module OK")
