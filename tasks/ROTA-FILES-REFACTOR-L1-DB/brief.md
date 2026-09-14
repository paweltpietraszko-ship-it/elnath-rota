# ROTA-FILES-REFACTOR-L1-DB — db.py split (oversized-file repair, Level 1)

SOURCE: same owner-authorized Level 1 refactor plan as
`ROTA-FILES-REFACTOR-L1` (validator.py, Codex PASS R1 on `8a9a6df`) --
each Tier 1 file gets its own Task, per that brief's own stated scope
boundary. No architect-authored brief.

## 1. Cel

Split `rota/persistence/db.py` (877 lines before this Task) into
era-grouped migration modules, with **zero product-behavior change**.
Pure code move -- every `_MIGRATION_N` tuple and the one Python-callable
migration are copied verbatim; only their file location changes.

Explicitly NOT in scope: any other Tier 1/2/3 file from the refactor
plan.

## 2. Shape of the split

`db.py` is ~90% migration DDL/DML string tuples (21 migrations,
`_MIGRATION_1`..`_MIGRATION_21` plus one Python-callable data migration,
`_migration_18_encrypt_existing_persisted_names`) and ~10% real logic
(`connect`, `migrate`, `init_schema`, the `MIGRATIONS` tuple assembly).
Split by era into four sibling modules:

- `rota/persistence/db_migrations_1_2.py` -- the pre-T008 baseline
  (`_MIGRATION_1`) and the full T008 operational LocalStore
  (`_MIGRATION_2`), plus `_final_guard_triggers()` (used by `db.py` to
  build migration 2's full statement tuple).
- `rota/persistence/db_migrations_3_9.py` -- `_MIGRATION_3`..`_MIGRATION_9`
  (T009 through T023b).
- `rota/persistence/db_migrations_10_17.py` -- `_MIGRATION_10`..`_MIGRATION_17`
  (schedule-version visibility flag through T057's plan-preview columns).
- `rota/persistence/db_migrations_18_21.py` -- `_migration_18_encrypt_existing_persisted_names`,
  `_MIGRATION_19`, `_MIGRATION_20`, `_MIGRATION_21` (RODO encryption,
  the two role-model eras, ORDINARY hourly availability).
- `rota/persistence/db.py` -- thin orchestrator: imports every migration
  name from the four sibling modules, assembles `MIGRATIONS`, and keeps
  `connect()`/`migrate()`/`init_schema()`/`LATEST_SCHEMA_VERSION`/
  `UnsupportedSchemaVersion` unchanged.

Import graph is a simple DAG: each `db_migrations_*.py` depends on
nothing project-internal except (for migration 18) a local, in-function
import of `rota.persistence.pii_crypto`, exactly as in the original;
`db.py` depends on all four.

## 3. Frozen contract preserved

`tests/test_local_store_schema_migration.py` accesses `_MIGRATION_1` and
`_MIGRATION_2` directly as `rota.persistence.db` module attributes
(`db_module._MIGRATION_1`, `db_module._MIGRATION_2`) and monkeypatches
`db_module.MIGRATIONS`. `db.py` re-imports both names with
`from rota.persistence.db_migrations_1_2 import _MIGRATION_1, _MIGRATION_2, ...`,
which binds them in `db.py`'s own namespace -- `db_module._MIGRATION_1`
resolves exactly as before, and `MIGRATIONS` is still a plain module-level
tuple that monkeypatch can replace.

## 4. Verification performed

- `ruff check` on all 5 touched/new files: clean.
- Direct sanity check: fresh `:memory:` `connect()` reaches
  `PRAGMA user_version == 21 == LATEST_SCHEMA_VERSION`; `db_module._MIGRATION_1`/
  `_MIGRATION_2` resolve and contain the expected first statement.
- Full repo test suite (`pytest tests/ --ignore=tests/property`, 1439
  tests): 64 failed / 1374 passed / 1 skipped, on this branch. The exact
  same 64 tests fail identically on a clean `origin/main` worktree with
  no code changes at all -- confirmed via `diff` on the sorted FAILED
  lists (byte-identical). Zero new regressions from this split.
- This full-suite run also revealed the true scope of pre-existing
  failures is larger than previously tracked in BOARD.md's
  `ROTA-NEWLY-FOUND-PREEXISTING-FAILURES` finding (which undercounted at
  5) -- a corrected finding follows separately, not fixed in this Task.

## 5. Acceptance

RL1DB-01 -- every test that passes on `origin/main` before this Task
still passes after it; the failing set is byte-identical to `main`'s own
(64 tests, independently confirmed pre-existing).

RL1DB-02 -- `migrate()`'s behavior (schema reached, table/column shapes,
data migration 18's encryption pass) is unchanged for every exercised
scenario -- this is a pure code move, not a rewrite.

RL1DB-03 -- `rota.persistence.db._MIGRATION_1` and `_MIGRATION_2` (and
every other `_MIGRATION_N`) keep resolving as module attributes at the
same import path.

RL1DB-04 -- no file in the split exceeds 600 lines.

## 6. TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-FILES-REFACTOR-L1-DB/**
- rota/persistence/db.py
- rota/persistence/db_migrations_1_2.py
- rota/persistence/db_migrations_3_9.py
- rota/persistence/db_migrations_10_17.py
- rota/persistence/db_migrations_18_21.py
