# ROTA-T020 — CHECKPOINT B SCOPE AMENDMENT 02

STATUS: ACCEPTED MECHANICAL SCOPE AMENDMENT — CC MAY CONTINUE
DATE: 2026-08-20
TASK_ID: ROTA-T020
PARENT_SCOPE_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_SCOPE_AMENDMENT_01.md
PARENT_HEAD: 2f24dc192c4b19d6465d2b7f04f4fb607a0f84c5

## 1. PURPOSE

This is a second, independent mechanical scope amendment discovered during implementation.

It does not change product behavior, migration semantics, solver behavior, T019b behavior, T020 behavior, or the meaning of the existing migration test.

`tests/test_t019b.py` is already inside the canonical TASK_SCOPE due to Scope Amendment 01. This amendment changes only the exact diff permitted inside that file.

## 2. WHY THE EXISTING ORACLE MUST MOVE WITH THE LATEST SCHEMA

The existing T019b test exercises the public `connect()` path from a real v5 database.

The contract of public `connect()` is migration to the repository's current `LATEST_SCHEMA_VERSION`, not migration to the historical version that happened to be current when T019b was implemented.

ROTA-T020 migration 7 adds exactly one new table, `site_print_settings`. Therefore leaving the T019b test's name and table-delta oracle frozen at v6/three tables would no longer describe the behavior actually exercised by the test.

This is a maintenance correction to an existing latest-schema migration oracle, not a semantic change to T019b.

## 3. EXACT AUTHORIZED CHANGES IN `tests/test_t019b.py`

In addition to the Scope Amendment 01 authorization changing:

`LATEST_SCHEMA_VERSION == 6`

to:

`LATEST_SCHEMA_VERSION == 7`

CC is authorized to make exactly these two further edits in `tests/test_t019b.py`:

### 3.1 Test name

Change exactly:

`test_a1_real_v5_to_v6_migration_preserves_data_and_adds_exactly_three_tables`

to:

`test_a1_real_v5_to_latest_migration_preserves_data_and_adds_expected_tables`

### 3.2 Expected table set

Change the existing expected newly-added table set from:

`{"coordinator_action_records", "decision_required_snapshots", "current_decision_required"}`

to the same set plus:

`"site_print_settings"`

so the expected delta contains exactly four tables:

- `coordinator_action_records`;
- `decision_required_snapshots`;
- `current_decision_required`;
- `site_print_settings`.

## 4. NOTHING ELSE IS AUTHORIZED IN THIS FILE

No other line in `tests/test_t019b.py` may change under this amendment.

In particular, CC must not change:

- the v5 seed/setup procedure;
- the public `connect()` call;
- preserved-data assertion;
- migration loop semantics;
- fixtures/helpers;
- T019b action-memory behavior;
- any other test name, assertion or oracle.

The test must continue proving the same invariant: a real v5 database opened through public `connect()` migrates to the current latest schema, preserves prior data, and adds exactly the tables introduced after v5.

## 5. `tests/test_t012.py`

Scope Amendment 01 remains unchanged for `tests/test_t012.py`.

The only authorized T020 edit there remains:

`LATEST_SCHEMA_VERSION == 6` -> `LATEST_SCHEMA_VERSION == 7`.

No further T012 test change is authorized.

## 6. GATE EFFECT

This amendment is mechanical and does not reopen the accepted preimplementation architecture/product gate.

CC may apply:

1. the two already-authorized `6 -> 7` schema assertions from Scope Amendment 01;
2. the exact T019b test-name change in Section 3.1;
3. the exact addition of `site_print_settings` to the expected table delta in Section 3.2;
4. no other changes to `tests/test_t012.py` or `tests/test_t019b.py`.

Implementation audit must compare those files against the architect baseline and prove their diff is limited exactly to the authorized lines above.

No merge authorization is granted by this amendment.
