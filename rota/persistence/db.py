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
from typing import Callable

LATEST_SCHEMA_VERSION = 18


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
        PRIMARY KEY (employee_id, month),
        CHECK (substr(month, 9, 2) = '01')
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
        status TEXT NOT NULL,
        CHECK (substr(month, 9, 2) = '01')
    )""",
    # R3-2: composite unique target so current_schedule_versions can enforce,
    # at the storage boundary, that its declared (site_id, month) actually
    # matches the version_id it points at -- version_id alone is already the
    # PK, but a bare FK on version_id alone cannot also pin site_id/month.
    """CREATE UNIQUE INDEX IF NOT EXISTS schedule_versions_identity
       ON schedule_versions(version_id, site_id, month)""",
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
        version_id TEXT NOT NULL,
        PRIMARY KEY (site_id, month),
        FOREIGN KEY (version_id, site_id, month) REFERENCES schedule_versions(version_id, site_id, month)
    )""",
    """CREATE TABLE IF NOT EXISTS shift_demands (
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        demand_id TEXT NOT NULL,
        start_datetime TEXT NOT NULL,
        end_datetime TEXT NOT NULL,
        required_primary_count INTEGER NOT NULL,
        PRIMARY KEY (schedule_version_id, demand_id)
    )""",
    # R3-2: covers_demand_id and mentor_primary_assignment_id must both
    # belong to the SAME schedule_version_id as the assignment. Both FKs are
    # immediate (not deferred) so a single raw SQL INSERT/UPDATE fails right
    # away at the storage boundary, not only at eventual transaction commit.
    # This requires callers to insert shift_demands before assignments (see
    # schedule_lifecycle._insert_content) and PRIMARY assignments before any
    # TRAINEE assignment that names them as mentor (see
    # schedule_lifecycle._order_assignments_mentor_first).
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
        PRIMARY KEY (schedule_version_id, assignment_id),
        FOREIGN KEY (schedule_version_id, covers_demand_id)
            REFERENCES shift_demands(schedule_version_id, demand_id),
        FOREIGN KEY (schedule_version_id, mentor_primary_assignment_id)
            REFERENCES assignments(schedule_version_id, assignment_id)
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
    # R3-1: UPDATE must reject if EITHER the row's current (OLD) version is
    # FINAL, OR the row's incoming (NEW) version is FINAL -- otherwise an
    # UPDATE that reassigns a row from a WORKING version straight into a
    # FINAL one bypasses the guard entirely (OLD alone is FINAL-free).
    conditions = {
        "INSERT": "(SELECT status FROM schedule_versions WHERE version_id = NEW.{col}) LIKE 'FINAL%'",
        "UPDATE": (
            "(SELECT status FROM schedule_versions WHERE version_id = OLD.{col}) LIKE 'FINAL%' "
            "OR (SELECT status FROM schedule_versions WHERE version_id = NEW.{col}) LIKE 'FINAL%'"
        ),
        "DELETE": "(SELECT status FROM schedule_versions WHERE version_id = OLD.{col}) LIKE 'FINAL%'",
    }
    triggers = []
    for table, version_col in _FINAL_CHILD_TABLES:
        for verb, condition_template in conditions.items():
            condition = condition_template.format(col=version_col)
            triggers.append(f"""
                CREATE TRIGGER IF NOT EXISTS {table}_no_{verb.lower()}_if_final
                BEFORE {verb} ON {table}
                WHEN {condition}
                BEGIN SELECT RAISE(ABORT, '{table}: FINAL ScheduleVersion content is immutable'); END
            """)
    return tuple(triggers)


# ---------------------------------------------------------------------------
# Migration 3 -- ROTA-T009: coordinator-facing "Obowiazuje od" provenance.
# Legacy pre-T009 rows keep effective_from = NULL (genuinely unknown, never
# guessed); every version created going forward supplies it explicitly.
# effective_from is immutable once set, same as created_at -- changing it
# means creating another child version, not rewriting this one.
# ---------------------------------------------------------------------------
_MIGRATION_3: tuple[str, ...] = (
    "ALTER TABLE schedule_versions ADD COLUMN effective_from TEXT",
    """CREATE TRIGGER IF NOT EXISTS schedule_versions_no_effective_from_change
       BEFORE UPDATE ON schedule_versions
       WHEN NEW.effective_from IS NOT OLD.effective_from
       BEGIN SELECT RAISE(ABORT, 'schedule_versions: effective_from is immutable once set'); END""",
)


# ---------------------------------------------------------------------------
# Migration 4 -- ROTA-T010-D: operational_code on Assignment. In T010 the
# only value is "NN" (a previously PLANNED PRIMARY the employee did not
# work, recorded as state=CANCELLED + operational_code="NN" on the child
# version -- never a new table, never a synthetic REALIZED).
# ---------------------------------------------------------------------------
_MIGRATION_4: tuple[str, ...] = (
    "ALTER TABLE assignments ADD COLUMN operational_code TEXT",
)


# ---------------------------------------------------------------------------
# Migration 5 -- ROTA-T012 Part A: shift catalog (24h/12h/INNY) + work-period
# rest provenance. Every new column is nullable/has a legacy-compatible
# default; existing rows are read back with catalog_kind/required_rest_hours/
# active_weekdays/can_work_24h/work_period_id normalized at the repository
# layer (rota.planning.shift_catalog.normalized_catalog_kind and friends),
# never rewritten here. No FINAL history row is touched.
# ---------------------------------------------------------------------------
_MIGRATION_5: tuple[str, ...] = (
    "ALTER TABLE standard_shifts ADD COLUMN catalog_kind TEXT",
    "ALTER TABLE standard_shifts ADD COLUMN required_rest_hours INTEGER",
    "ALTER TABLE standard_shifts ADD COLUMN active_weekdays TEXT",
    "ALTER TABLE site_memberships ADD COLUMN can_work_24h INTEGER",
    "ALTER TABLE shift_demands ADD COLUMN shift_kind TEXT",
    "ALTER TABLE shift_demands ADD COLUMN catalog_kind TEXT",
    "ALTER TABLE shift_demands ADD COLUMN required_rest_hours INTEGER",
    "ALTER TABLE shift_demands ADD COLUMN work_period_template_id TEXT",
    "ALTER TABLE shift_demands ADD COLUMN work_period_component INTEGER",
    "ALTER TABLE shift_demands ADD COLUMN emergency_24h_rest_hours INTEGER",
    "ALTER TABLE assignments ADD COLUMN work_period_id TEXT",
    "ALTER TABLE assignments ADD COLUMN required_rest_after_hours INTEGER",
)


# ---------------------------------------------------------------------------
# Migration 6 -- ROTA-T019b: durable memory of material coordinator actions
# (append-only index) + immutable final DECISION_REQUIRED snapshots + a
# mutable current-question pointer. Historical/readback only -- never read
# by PlanningState assembly, the solver, the validator or WorkBalance.
# ---------------------------------------------------------------------------
_MIGRATION_6: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS coordinator_action_records (
        action_id TEXT PRIMARY KEY,
        action_kind TEXT NOT NULL,
        origin_site_id TEXT NOT NULL REFERENCES sites(site_id),
        affected_site_ids_json TEXT NOT NULL,
        coordinator_id TEXT NOT NULL REFERENCES coordinators(coordinator_id),
        recorded_at TEXT NOT NULL,
        effective_from TEXT,
        month TEXT,
        schedule_version_id TEXT,
        affected_entities_json TEXT NOT NULL,
        before_state_json TEXT,
        after_state_json TEXT,
        note TEXT,
        source_kind TEXT NOT NULL,
        source_id TEXT,
        responds_to_decision_required_id TEXT REFERENCES decision_required_snapshots(decision_required_id)
    )""",
    """CREATE TRIGGER IF NOT EXISTS coordinator_action_records_no_update
       BEFORE UPDATE ON coordinator_action_records
       BEGIN SELECT RAISE(ABORT, 'coordinator_action_records is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS coordinator_action_records_no_delete
       BEFORE DELETE ON coordinator_action_records
       BEGIN SELECT RAISE(ABORT, 'coordinator_action_records is append-only: DELETE forbidden'); END""",
    """CREATE TABLE IF NOT EXISTS decision_required_snapshots (
        decision_required_id TEXT PRIMARY KEY,
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        schedule_version_id TEXT,
        requested_by TEXT NOT NULL REFERENCES coordinators(coordinator_id),
        recorded_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        CHECK (substr(month, 9, 2) = '01')
    )""",
    """CREATE TRIGGER IF NOT EXISTS decision_required_snapshots_no_update
       BEFORE UPDATE ON decision_required_snapshots
       BEGIN SELECT RAISE(ABORT, 'decision_required_snapshots is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS decision_required_snapshots_no_delete
       BEFORE DELETE ON decision_required_snapshots
       BEGIN SELECT RAISE(ABORT, 'decision_required_snapshots is append-only: DELETE forbidden'); END""",
    """CREATE TABLE IF NOT EXISTS current_decision_required (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        decision_required_id TEXT NOT NULL REFERENCES decision_required_snapshots(decision_required_id),
        PRIMARY KEY (site_id, month)
    )""",
    """CREATE INDEX IF NOT EXISTS coordinator_action_records_by_recorded_at
       ON coordinator_action_records(recorded_at)""",
    """CREATE INDEX IF NOT EXISTS coordinator_action_records_by_coordinator
       ON coordinator_action_records(coordinator_id, recorded_at)""",
    """CREATE INDEX IF NOT EXISTS coordinator_action_records_by_kind
       ON coordinator_action_records(action_kind, recorded_at)""",
    """CREATE INDEX IF NOT EXISTS decision_required_snapshots_by_site_month
       ON decision_required_snapshots(site_id, month, recorded_at)""",
)


# ---------------------------------------------------------------------------
# Migration 7 -- ROTA-T020 Checkpoint B: Site print settings only (current
# mutable state, no history table). Saving this never creates a
# ScheduleVersion and never records a T019b material coordinator action --
# it changes print presentation, not schedule truth.
# ---------------------------------------------------------------------------
_MIGRATION_7: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS site_print_settings (
        site_id TEXT PRIMARY KEY REFERENCES sites(site_id),
        company_print_name TEXT NOT NULL,
        site_print_name TEXT NOT NULL,
        base_regime TEXT NOT NULL CHECK(base_regime IN ('12h','24h')),
        work_code_intervals_json TEXT NOT NULL,
        reserve_hours_json TEXT NOT NULL
    )""",
)


# ---------------------------------------------------------------------------
# Migration 8 -- ROTA-T023: durable absence-reference provenance. One
# append-only row per AvailabilityVersion that actually requires captured
# reference facts (active SICK_LEAVE/LEAVE_GRANTED writes only -- see
# rota/persistence/absence_reference_repository.py). No current pointer, no
# WorkBalance history table, no second Assignment table, no second ledger.
# ---------------------------------------------------------------------------
_MIGRATION_8: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS absence_reference_snapshots (
        availability_version_id TEXT PRIMARY KEY REFERENCES availability_versions(availability_version_id),
        captured_at TEXT NOT NULL,
        reference_status TEXT NOT NULL CHECK (reference_status IN ('BOUND', 'MISSING', 'AMBIGUOUS')),
        snapshot_json TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS absence_reference_snapshots_no_update
       BEFORE UPDATE ON absence_reference_snapshots
       BEGIN SELECT RAISE(ABORT, 'absence_reference_snapshots is append-only: UPDATE forbidden'); END""",
    """CREATE TRIGGER IF NOT EXISTS absence_reference_snapshots_no_delete
       BEFORE DELETE ON absence_reference_snapshots
       BEGIN SELECT RAISE(ABORT, 'absence_reference_snapshots is append-only: DELETE forbidden'); END""",
)


# ---------------------------------------------------------------------------
# Migration 9 -- ROTA-T023b: Site classification (ORDINARY|OCHRONA) and its
# ScheduleVersion provenance. SQL defaults exist only for current test/legacy
# rows -- new Site creation and new ScheduleVersion writes must persist an
# explicit/derived value at the application layer, never rely on this
# default (frozen addendum section 3).
# ---------------------------------------------------------------------------
_MIGRATION_9: tuple[str, ...] = (
    "ALTER TABLE sites ADD COLUMN planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' "
    "CHECK (planning_regime IN ('ORDINARY','OCHRONA'))",
    "ALTER TABLE schedule_versions ADD COLUMN planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' "
    "CHECK (planning_regime IN ('ORDINARY','OCHRONA'))",
)


# ---------------------------------------------------------------------------
# Migration 10: excluded_from_history on ScheduleVersion (2026-08-26,
# owner decision) -- a WORKING/WORKING_WITH_DEVIATIONS version the
# coordinator has discarded (e.g. an unwanted REPLAN attempt) can be hidden
# from the Historia panel and analytics without touching the physical-delete
# trigger above: schedule_versions_no_delete stays a hard, unconditional
# backstop, this is a visibility flag only. FINAL versions must never be
# excluded (schedule_versions_no_update_if_final already refuses any UPDATE
# once status is FINAL, this column included) -- they are the real audit
# trail, not a discardable draft.
# ---------------------------------------------------------------------------
_MIGRATION_10: tuple[str, ...] = (
    "ALTER TABLE schedule_versions ADD COLUMN excluded_from_history INTEGER NOT NULL DEFAULT 0",
)


# ---------------------------------------------------------------------------
# Migration 11: ROTA-T052 -- S1 (periodic training) default print interval.
# Nullable, purely a UI default/config value for MonthlyPlanning/PrintSettings
# (brief section 4/9) -- NOT a WORK_CODE_KEYS entry, no fixed-duration
# constraint. assignments.role stays plain TEXT (brief section 3: no CHECK
# exists today, so no migration is needed there for the new
# AssignmentRole.PERIODIC_TRAINING value).
# ---------------------------------------------------------------------------
_MIGRATION_11: tuple[str, ...] = (
    "ALTER TABLE site_print_settings ADD COLUMN s1_default_interval_json TEXT",
)


# ---------------------------------------------------------------------------
# Migration 12: ROTA-T054 -- persisted PLAN/REPLAN preview. At most one
# current row per (site_id, month); NOT a ScheduleVersion, NOT a history --
# candidates_json/warnings_json are a snapshot of one FEASIBLE
# PlanningResult, overwritten by the next one and deleted on accept/reject
# (brief section 4). schedule_version_id names the exact WORKING version
# the preview was computed against, so a reader can tell a stale preview
# (current version has since changed) apart without a second table.
# ---------------------------------------------------------------------------
_MIGRATION_12: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS plan_previews (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        schedule_version_id TEXT NOT NULL REFERENCES schedule_versions(version_id),
        candidates_json TEXT NOT NULL,
        warnings_json TEXT NOT NULL,
        optimization_complete INTEGER NOT NULL,
        -- R2-03/A-F2 audit fixes (pre-merge, folded into this migration
        -- rather than follow-ups): which operation stage produced this
        -- preview, so a reload can tell which continuation a further
        -- "Szukaj dalej" should retry -- replan's narrow (replan()/
        -- replan_retry_narrow()) and wide (replan_wider_search()) stages
        -- dispatch to different endpoints and must not be conflated.
        operation_kind TEXT NOT NULL CHECK (operation_kind IN ('plan', 'replan_narrow', 'replan_wide')),
        PRIMARY KEY (site_id, month),
        CHECK (substr(month, 9, 2) = '01')
    )""",
)


# ---------------------------------------------------------------------------
# Migration 13: ROTA-T056 -- monthly additional D6+/N6+ work-code intervals.
# Current-state, no history: one row per (site_id, month), overwritten
# whole on save. Keyed by (site_id, month) so one month's definitions never
# affect another month's read/export (brief section 4 -- OWNER decision 3:
# per (site_id, month), never per-site-permanent). codes_json maps
# code -> WorkCodeInterval (same shape as site_print_settings'
# work_code_intervals); the frozen standard D1-5/N1-5 table is untouched
# and lives only in site_print_settings.
# ---------------------------------------------------------------------------
_MIGRATION_13: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS site_monthly_extra_work_codes (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        codes_json TEXT NOT NULL,
        PRIMARY KEY (site_id, month),
        CHECK (substr(month, 9, 2) = '01')
    )""",
)


# ---------------------------------------------------------------------------
# Migration 14: ROTA-T057 -- pre-acceptance REPLAN "podejscie" (attempt)
# memory. Every candidate signature shown since the last fresh PLAN or
# explicit "Odrzuc wynik" for a (site_id, month), so the >=15%-different-
# from-EVERY-previous-variant rule (not just the last one) survives a
# reload -- a separate table, not a column on plan_previews, because it is
# a growing list per attempt, not a single current snapshot.
# ---------------------------------------------------------------------------
_MIGRATION_14: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS plan_attempt_signatures (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        seq INTEGER NOT NULL,
        signature_json TEXT NOT NULL,
        PRIMARY KEY (site_id, month, seq),
        CHECK (substr(month, 9, 2) = '01')
    )""",
)


# ---------------------------------------------------------------------------
# Migration 15: ARCHITECT_DECISION 2026-09-06 (BOARD.md ROTA-T057) -- one
# PlanPreview, no second subsystem. schedule_version_id becomes optional/
# NULL: a preview may now exist BEFORE the very first ScheduleVersion for a
# (site_id, month) is ever created (T57-01, "pierwszy PLAN nie tworzy
# ScheduleVersion przed akceptacja"). SQLite cannot ALTER a column's
# NULL-ability in place -- rebuild via the standard create/copy/drop/rename
# sequence, same shape as the original migration 12 table otherwise.
# ---------------------------------------------------------------------------
_MIGRATION_15: tuple[str, ...] = (
    """CREATE TABLE plan_previews_v15 (
        site_id TEXT NOT NULL REFERENCES sites(site_id),
        month TEXT NOT NULL,
        schedule_version_id TEXT REFERENCES schedule_versions(version_id),
        candidates_json TEXT NOT NULL,
        warnings_json TEXT NOT NULL,
        optimization_complete INTEGER NOT NULL,
        operation_kind TEXT NOT NULL CHECK (operation_kind IN ('plan', 'replan_narrow', 'replan_wide')),
        PRIMARY KEY (site_id, month),
        CHECK (substr(month, 9, 2) = '01')
    )""",
    """INSERT INTO plan_previews_v15 (site_id, month, schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind)
       SELECT site_id, month, schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind FROM plan_previews""",
    "DROP TABLE plan_previews",
    "ALTER TABLE plan_previews_v15 RENAME TO plan_previews",
)


# ---------------------------------------------------------------------------
# Migration 16: ROTA-T057 -- plan_previews.effective_from, nullable. Only
# meaningful while schedule_version_id IS NULL: the coordinator-supplied
# effective_from for a month's very first ScheduleVersion, captured at PLAN
# time and carried forward so select_candidate can create that first
# version at acceptance without the caller resupplying it after a reload.
# ---------------------------------------------------------------------------
_MIGRATION_16: tuple[str, ...] = (
    "ALTER TABLE plan_previews ADD COLUMN effective_from TEXT",
)


# ---------------------------------------------------------------------------
# Migration 17: ROTA-T057 -- plan_previews.shift_demands_json. The demands a
# preview's candidates were solved against, so the coordinator-facing grid
# can show D/N labels for a not-yet-accepted candidate even when no
# ScheduleVersion exists yet to source demands from (a real click-through
# found this: "?" instead of D/N with no current_version, 2026-09-06).
# ---------------------------------------------------------------------------
_MIGRATION_17: tuple[str, ...] = (
    "ALTER TABLE plan_previews ADD COLUMN shift_demands_json TEXT NOT NULL DEFAULT '[]'",
)


def _migration_18_encrypt_existing_persisted_names(conn: sqlite3.Connection) -> None:
    """ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE brief.md
    (exact SHA 5683bac) section 4: one-time, deterministic encryption of
    any existing plaintext plan_previews.warnings_json /
    decision_required_snapshots.payload_json, so this fix protects
    already-persisted records too, not only new writes after this
    version. A local import (not top-of-file) keeps db.py's normal
    import graph free of a hard dependency on pii_crypto for every
    caller that never needs this one-time migration path.

    decision_required_snapshots is append-only via its own
    BEFORE UPDATE/DELETE triggers (created in _MIGRATION_2 below). Those
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
