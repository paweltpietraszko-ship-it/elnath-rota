"""Migrations 3-9: coordinator-facing "Obowiazuje od" provenance (T009),
operational_code on Assignment (T010-D), shift-catalog + work-period rest
provenance (T012 Part A), durable coordinator-action/decision-required
memory (T019b), Site print settings (T020 Checkpoint B), absence-reference
provenance (T023), and Site planning_regime classification (T023b).

Split out of rota/persistence/db.py (2026-09 oversized-file refactor,
mechanical-only, zero behavior change)."""
from __future__ import annotations

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


if __name__ == "__main__":
    print("persistence.db_migrations_3_9 module OK")
