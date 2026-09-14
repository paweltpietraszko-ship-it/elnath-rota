# ROTA-FILES-REFACTOR-L1 — validator.py split (oversized-file repair, Level 1)

SOURCE: BOARD.md findings `ROTA-EMPLOYEE-DETAIL-SIZE-LIMIT` and
`ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT`; owner conversation 2026-09-14
("pliki o takim rozmiarze nawet ty trudno czytasz ze zrozumieniem" /
"rdzenia nie ruszamy ale dodatkowe logiki muszą lądować w innych
plikach"). No architect-authored brief -- this is CC's own proposal
(three risk tiers presented to owner), owner-authorized directly in chat
("Ok, zróbmy poziom 1" / "Dokończ teraz"), scoped to the single lowest-risk
file in Tier 1.

## 1. Cel

Split `rota/planning/validator.py` (988 lines before this Task) into
topic-grouped sibling modules for readability, with **zero
product-behavior change**. Not a rewrite -- every check function's body
is moved verbatim; only its file location changes.

Explicitly NOT in scope: `rota/planning/solver.py`, `engine.py`,
`constraints.py`, `work_periods.py` (Tier 3, core solver, needs architect
involvement per owner's own "rdzenia nie ruszamy" ruling) and every other
Tier 1/2 file from the refactor plan (`db.py`, `EmployeeDetail.tsx`,
`MonthlyPlanning.tsx`, `client.ts`, application-layer files) -- each is
its own separate Task.

## 2. Shape of the split

`validator.py` was already structurally ready for this: ~35 independent
`_check_*` functions (each taking `state`/`assignments`/`details` and
appending `ViolationDetail`s) plus one `validate()` orchestrator calling
them in a fixed order. The split:

- `rota/planning/validator_shared.py` -- `ViolationDetail`,
  `IndependentValidationReport` dataclasses, and every pure helper used
  by more than one check group (`coverage_segments`,
  `_attributed_overlap_intervals`, `_covering_demand`, `_covered_demands`,
  `_demand_kind`, `_is_well_formed_normal_h24_pair`, `_is_full_hour`,
  `_monthly_hours`, `_by_employee`, `_not_cancelled`,
  `_coverage_violation_detail`).
- `rota/planning/validator_checks_integrity.py` -- FULL_HOUR-01, ASSIGN
  (trainee/mentor), ASSIGN-03/04 (REPLAN preserves fixed), COVERAGE-01.
- `rota/planning/validator_checks_availability.py` -- MEMBERSHIP-01,
  ROLE-01, DAY_ONLY-01, DAY_SHIFT_OFF-01, UNAVAILABLE-01/SICK_LEAVE-01/
  LEAVE_GRANTED-01, UNAVAILABLE_TIME-01, LEAVE_PLAN-01, EXTERNAL-01,
  SITE_RULE-01.
- `rota/planning/validator_checks_patterns.py` -- NIGHT-STREAK-01,
  THIRD-CONSECUTIVE-SHIFT-01, SHIFT-24-PAIR-01, SHIFT-24-01 (via the
  emergency-pair path).
- `rota/planning/validator_checks_rest_and_load.py` -- WORK_PERIOD-01,
  REST-01, WEEKLY-REST-01, LOAD-01.
- `rota/planning/validator.py` -- thin orchestrator: imports every check
  from the sibling modules, defines `validate()` calling them in the
  exact original order, re-exports `ViolationDetail`,
  `IndependentValidationReport`, `coverage_segments` (via `__all__`) so
  every existing `from rota.planning.validator import ...` external
  caller keeps working unchanged.

Import graph is a simple DAG: `validator_shared.py` depends on nothing
project-internal beyond `rota.domain`/`rota.planning.state`/
`rota.planning.shift_catalog`; each `validator_checks_*.py` depends only
on `validator_shared.py` (never on `validator.py` or a sibling check
module); `validator.py` depends on all of the above. No circular imports.

## 3. Frozen contract preserved

`tests/test_t023.py::test_t23_55_shared_coverage_helper_used_by_validator_and_t023_capture`
asserts the literal source string
`"from rota.planning.validator import coverage_segments"` inside
`rota/persistence/absence_reference_repository.py`. `coverage_segments`'s
real implementation now lives in `validator_shared.py`, but `validator.py`
re-exports it under the same name at the same import path -- this test is
untouched and still passes.

## 4. Verification performed

- `ruff check` on all 6 touched/new files: clean.
- Every test file in the repo that imports anything from
  `rota.planning.validator` (28 files, found via
  `grep -rn "from rota.planning.validator import" tests/`): run together.
  23 failed / 542 passed. All 23 independently reproduced on a clean
  `origin/main` worktree (pre-existing, unrelated to this split) --
  5 of the 23 were not previously catalogued pre-existing failures
  (found while verifying this Task) and are flagged separately to
  BOARD.md, not fixed here (out of this Task's scope).
- Manual line-count check: `validator.py` 109, `validator_shared.py` 213,
  `validator_checks_integrity.py` 97, `validator_checks_availability.py`
  303, `validator_checks_patterns.py` 216,
  `validator_checks_rest_and_load.py` 193 -- all comfortably under the
  600-line limit.
- No `backend.py` run: the mechanical gate is the subject of the separate
  `ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT` repair Task and is not currently
  trustworthy for SIZE_FILE/RUFF/DIFF_SCOPE. Owner explicitly authorized
  proceeding without it for this one Task rather than waiting.

## 5. Acceptance

RL1-01 -- every existing test that passed on `main` before this Task
still passes after it (no new failures beyond the 23 independently
confirmed pre-existing on clean `main`).

RL1-02 -- `validate()`'s return value (violations, violation_details,
warnings, monthly_hours, rest/load figures) is byte-for-byte identical
to before the split for every exercised scenario -- this is a pure code
move, not a rewrite.

RL1-03 -- every external import of `rota.planning.validator`
(`ViolationDetail`, `IndependentValidationReport`, `coverage_segments`,
`validate`) keeps resolving at the same path, unchanged.

RL1-04 -- no file in the split exceeds 600 lines.

## 6. TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-FILES-REFACTOR-L1/**
- rota/planning/validator.py
- rota/planning/validator_shared.py
- rota/planning/validator_checks_integrity.py
- rota/planning/validator_checks_availability.py
- rota/planning/validator_checks_patterns.py
- rota/planning/validator_checks_rest_and_load.py
