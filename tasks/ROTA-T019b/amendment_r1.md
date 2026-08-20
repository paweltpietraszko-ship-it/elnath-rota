# ROTA-T019b — architect contract amendment after preimplementation Round 1

STATUS: READY FOR CODEX PREIMPLEMENTATION ROUND 2 — NOT READY FOR CC
DATE: 2026-08-20
BASE_SHA: 102273b553783b5a083a60d5ee9964e9ec67221a
PARENT_CONTRACT_SHA: 8c881f6999711dc00434a83f3ec617f95cb11837
ROUND_01_AUDIT_SHA: 40bc84fecdf7d6773fccef37d5ee4a17f37463c0
ROUND_01_REPORT: tasks/ROTA-T019b/round_01/tests/tests_r1.txt

This document is a NORMATIVE amendment to `tasks/ROTA-T019b/brief.md` and `tasks/ROTA-T019b/operation_audit.md`.

It closes exactly findings T019b-R1-1, T019b-R1-2 and T019b-R1-3. It changes no product decision, no storage architecture, no application semantics beyond the already-frozen explicit `select_candidate` actor requirement, and authorizes no implementation before Round 2 PASS.

## A1. T019b-R1-1 — `training.save_site_membership`

`rota.application.training.save_site_membership(conn, membership)` is explicitly classified as:

- **NO independent coordinator action**;
- internal/derived same-transaction write seam used by `mark_training_realized`;
- existing module-level monkeypatch/test seam MUST be preserved;
- MUST NOT create its own coordinator-action row;
- MUST NOT get a new action kind;
- when readiness changes during `mark_training_realized`, that derived before/after belongs only to the single `TRAINING_REALIZED` action.

`tasks/ROTA-T019b/operation_audit.md` is amended accordingly.

No production behavior is added solely for this finding.

## A2. T019b-R1-2 — literal TASK_SCOPE expansion for explicit candidate actor adaptations

Section 21 `TASK_SCOPE` of `tasks/ROTA-T019b/brief.md` is hereby amended to ADD exactly these existing legacy test files:

- `tests/test_audit_t009_r4.py`
- `tests/test_audit_t009_r5.py`
- `tests/test_t009_lifecycle_memory_backup_boundary.py`
- `tests/test_t009_manual_edit.py`
- `tests/test_t009_plan_select_replan.py`
- `tests/test_t010_nn.py`

Authorization in those six files is **mechanical only**: add the explicit `coordinator_id` already established by each test's fixture/context to the fourteen legacy `select_candidate()` calls enumerated by Round 1:

- `tests/test_audit_t009_r4.py`: current baseline call sites around lines 40, 111, 115, 528;
- `tests/test_audit_t009_r5.py`: around lines 41, 316;
- `tests/test_t009_lifecycle_memory_backup_boundary.py`: around lines 28, 109;
- `tests/test_t009_manual_edit.py`: around line 99;
- `tests/test_t009_plan_select_replan.py`: around lines 21, 55, 58, 107;
- `tests/test_t010_nn.py`: around line 34.

Frozen limits:

1. Do not change candidate contents, ordering, T017 diversity semantics, validation expectations, persistence expectations or status oracles.
2. Do not change fixtures except where strictly necessary to pass the already-existing coordinator id into the call.
3. Do not weaken any assertion.
4. No unrelated cleanup/refactor in these files.
5. If implementation discovers any additional `select_candidate()` legacy caller needing semantic change rather than this explicit-actor argument, STOP and return to architect.

## A3. T019b-R1-3 — literal TASK_SCOPE expansion for schema version 6

Section 21 `TASK_SCOPE` of `tasks/ROTA-T019b/brief.md` is hereby amended to ADD:

- `tests/test_t012.py`

Authorization in this file is **mechanical only**:

- update the existing exact schema assertion around current baseline line 256 from literal `LATEST_SCHEMA_VERSION == 5` to literal `LATEST_SCHEMA_VERSION == 6` after T019b migration 6 is implemented;
- all other T012 oracles remain unchanged and closed.

No other `tests/test_t012.py` edit is authorized by this amendment.

## A4. NORMATIVE AMENDED TASK_SCOPE

For T019b implementation, the literal TASK_SCOPE is the original Section 21 list from `tasks/ROTA-T019b/brief.md` PLUS exactly the following seven existing test files:

- `tests/test_audit_t009_r4.py`
- `tests/test_audit_t009_r5.py`
- `tests/test_t009_lifecycle_memory_backup_boundary.py`
- `tests/test_t009_manual_edit.py`
- `tests/test_t009_plan_select_replan.py`
- `tests/test_t010_nn.py`
- `tests/test_t012.py`

`tasks/ROTA-T019b/**` architect/audit artifacts remain pipeline artifacts and do not expand production implementation scope.

No other file may be edited without STOP + a later architect amendment.

## A5. ROUND 2 SCOPE — ONLY R1-1 / R1-2 / R1-3

Codex Round 2 must audit the exact amendment SHA and check only:

1. `operation_audit.md` now explicitly includes `training.save_site_membership` as internal/derived **NO independent action**, preserving its existing monkeypatch seam;
2. the six files containing the fourteen legacy `select_candidate()` calls are literally authorized by the amended TASK_SCOPE, with adaptation constrained to explicit `coordinator_id` only;
3. `tests/test_t012.py` is literally authorized by the amended TASK_SCOPE, constrained to the one schema-version `5 -> 6` assertion adaptation;
4. no product decision, architecture, production code, tests or unrelated contract clause changed in this amendment.

Round 2 is NOT a second full architecture review unless it finds a direct contradiction introduced by this amendment.

Required Round 2 verdict if all four checks pass:

`PASS — READY_FOR_IMPLEMENTATION`

Until that verdict:

**CC MUST NOT START T019b IMPLEMENTATION.**

After Round 2 PASS, CC may implement only the original contract as narrowed/extended by this amendment and the amended operation audit.
