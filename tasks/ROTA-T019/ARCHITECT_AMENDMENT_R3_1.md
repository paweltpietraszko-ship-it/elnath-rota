# ROTA-T019 — ARCHITECT AMENDMENT T019-R3-1

DATE: 2026-08-20
STATUS: FROZEN MECHANICAL GATE AMENDMENT
BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2
CONTRACT_SHA: 08879e9af837dbedf37a6cefbb9384bab2f58c7a
AUDITED_PRODUCT_SHA: 62e2d55ec97f057d2a3f82fa4747efa2a13ae4c7
ROUND_4_AUDIT_HEAD: 66e54a9342c92dca64d6f8f5eaa3fd01d2916abd
FINDING: T019-R3-1

## 1. PURPOSE

Round 4 closed T019-R3-2, T019-R3-3 and T019-R3-4 and left exactly one blocker: the full `BASE_SHA -> PRODUCT_SHA` backend gate reports `NEW_FILES: 3 new files (max 2)`.

This amendment closes only that mechanical mismatch. It does not change product behavior, TASK_SCOPE, implementation, tests, frozen product semantics, or any repository-wide backend threshold.

## 2. WHY BACKEND STILL REPORTS FAIL

`backend.py` has repository-wide `MAX_NEW_FILES = 2` and excludes `tasks/*` pipeline artifacts from NEW_FILES counting.

For T019, the full BASE diff contains exactly three non-pipeline added files:

1. `arch/T019_coordinator_analytics_architect_brief.md` — owner/architect source document created before implementation;
2. `rota/application/analytics_read.py` — the one new production application read module required by T019;
3. `tests/test_t019.py` — the one dedicated implementation test file required by T019.

The third file is therefore not scope expansion by CC. It is the owner brief that is necessarily visible only when the final gate correctly uses the full BASE_SHA diff rather than contract-stage -> product diff.

`tasks/ROTA-T019/brief.md` and all `tasks/ROTA-T019/round_01/**` files are pipeline artifacts and are excluded by backend.py from NEW_FILES and TOTAL_LINES.

## 3. EXACT TASK-SPECIFIC WAIVER

For ROTA-T019 only, and only for a final branch state whose non-pipeline BASE diff has exactly the three added files listed in section 2:

`NEW_FILES = 3 — ARCHITECT ACCEPTED`

This supersedes the repository-wide `MAX_NEW_FILES = 2` result only for the T019 final gate. It does not modify `backend.py`, does not raise the global limit, and is not precedent for another task or another set of files.

Any fourth non-pipeline added file, or replacement of one of the three listed files by another file, invalidates this waiver and requires a new architect decision.

## 4. TOTAL_LINES

The same required full BASE diff reports:

`TOTAL_LINES = 1106`

The 1106 lines are exactly the non-pipeline TASK_SCOPE diff:

- `arch/T019_coordinator_analytics_architect_brief.md`: +292;
- `rota/application/analytics_read.py`: +224;
- `rota/persistence/availability_repository.py`: +25;
- `rota/persistence/work_balance_repository.py`: +21;
- `tests/test_t019.py`: +544;

Total: `292 + 224 + 25 + 21 + 544 = 1106`.

This is the correct final-gate metric. The earlier shorter contract-stage -> product number is not the final BASE metric.

For the exact final branch state created by this amendment, provided the non-pipeline diff remains exactly the five files above and Round 4 semantic/quality findings remain closed:

`TOTAL_LINES = 1106 — ARCHITECT ACCEPTED`

This is an exact-SHA-only mechanical waiver. It does not change `TOTAL_LINES_THRESHOLD = 150` in backend.py and creates no precedent.

## 5. CLOSED / NOT REOPENED

This amendment does not reopen:

- T019-R3-2 canonical quarter owner;
- T019-R3-3 EXTERNAL_SUPPORT no-row siblings;
- T019-R3-4 weekday-holiday absence oracle;
- WINDOW-03;
- LOCAL-only analytics roster;
- effective target semantics;
- read-only/no-second-truth boundary;
- N+1 batching contract;
- missing-data statuses/warnings;
- full test, benchmark, Ruff, guard, or git-diff evidence already accepted by Round 4.

CC has no implementation work to perform for T019-R3-1.

## 6. FINAL GATE INTERPRETATION

At final architect review, the backend output may remain mechanically `STATUS: FAIL` solely because the repository-wide NEW_FILES constant is 2, and may continue to list `TOTAL_LINES: 1106` under WYMAGA_DECYZJI.

Those two exact findings are accepted by this amendment if and only if the final SHA has the unchanged non-pipeline BASE diff described above. Any other backend REASON or WYMAGA_DECYZJI remains unwaived.
