"""Migrations 10-17: ScheduleVersion history-visibility flag, S1 print
default, persisted PLAN/REPLAN preview + its NULLable-schedule_version_id
rebuild, monthly extra work codes, REPLAN attempt-signature memory, and two
small plan_previews column additions.

Split out of rota/persistence/db.py (2026-09 oversized-file refactor,
mechanical-only, zero behavior change)."""
from __future__ import annotations

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


if __name__ == "__main__":
    print("persistence.db_migrations_10_17 module OK")
