# ROTA-T020 — CHECKPOINT B SCOPE AMENDMENT 01

STATUS: APPROVED MECHANICAL SCOPE AMENDMENT — CC MAY CONTINUE
DATE: 2026-08-20
TASK_ID: ROTA-T020
PARENT_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_B_PREIMPLEMENTATION_ACCEPTANCE.md
PARENT_ACCEPTANCE_SHA: 2549cb0b5ebbb541777f2b2f02e8ed9b09227b9d

## 1. PURPOSE

Implementation of T020 migration 7 necessarily changes the repository-wide latest schema version from 6 to 7.

Two pre-existing regression tests outside the original T020 TASK_SCOPE assert the repository's current latest schema version literally:

- `tests/test_t012.py`;
- `tests/test_t019b.py`.

Both currently contain the assertion shape:

`LATEST_SCHEMA_VERSION == 6`

Once T020 correctly sets `LATEST_SCHEMA_VERSION = 7`, those assertions must follow the repository-wide schema version. This is a mechanical scope consequence, not a T012 or T019b product change.

## 2. TASK_SCOPE AMENDMENT

Add exactly these existing files to the T020 implementation TASK_SCOPE:

- `tests/test_t012.py`;
- `tests/test_t019b.py`.

Authorization in those two files is restricted to the exact literal assertion update:

FROM:

`LATEST_SCHEMA_VERSION == 6`

TO:

`LATEST_SCHEMA_VERSION == 7`

No other edit in either file is authorized by this amendment.

## 3. SEMANTIC BOUNDARY

This amendment does NOT authorize:

- changing any T012 behavior, fixture, oracle, provenance rule or 24h semantics;
- changing any T019b behavior, fixture, oracle, action-memory semantics or migration-6 history expectations;
- renaming tests;
- refactoring test helpers;
- changing expected table sets or migration-specific assertions;
- weakening or deleting tests;
- modifying production paths beyond the already-frozen T020 TASK_SCOPE.

The two assertions continue to mean exactly what they meant before: a freshly/currently opened database reports the repository's `LATEST_SCHEMA_VERSION`. Only that repository-wide constant advances from 6 to 7 because T020 adds migration 7.

## 4. DIFF ORACLE

For each newly authorized legacy test file, implementation audit must prove the file diff is exactly one semantic token change:

`6 -> 7`

inside the existing `LATEST_SCHEMA_VERSION` assertion.

Any additional changed line in either `tests/test_t012.py` or `tests/test_t019b.py` is outside scope and requires separate architect review.

## 5. GATE EFFECT

This is a purely mechanical scope amendment discovered before the first implementation commit. It does not reopen product architecture, Checkpoint A, the Round-7 preimplementation PASS, or any owner decision.

No additional preimplementation Codex round is required solely for this amendment.

CC MAY CONTINUE T020 Checkpoint B implementation after this amendment is committed.

Because no implementation commit existed before this amendment, the canonical implementation `before_sha` becomes the branch HEAD after this amendment and the corresponding `brief.md` TASK_SCOPE update are committed.

This remains implementation authorization only. It is not final acceptance and not merge authorization.
