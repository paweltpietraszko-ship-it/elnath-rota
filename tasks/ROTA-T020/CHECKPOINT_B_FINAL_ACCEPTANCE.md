# ROTA-T020 — CHECKPOINT B ARCHITECT FINAL ACCEPTANCE

STATUS: PASS — READY FOR MERGE
DATE: 2026-08-20
TASK_ID: ROTA-T020
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
IMPLEMENTATION_BEFORE_SHA: c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2
ACCEPTED_PRODUCT_SHA: 6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d
FINAL_AUDIT_COMMIT: 0cb6c0e93a9bd0443cf184ea3331a5c272c56570
FINAL_AUDIT_REPORT: tasks/ROTA-T020/round_01/tests/tests_r12.txt

## 1. ARCHITECT VERDICT

ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T020 CHECKPOINT B: PASS — READY FOR MERGE.

I accept exact product SHA:

`6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d`

against the frozen T020 contract hierarchy and the implementation-time architect amendments.

The final independent Round 12 audit is accepted:

`PASS — R11-1 CLOSED — CHECKPOINT B READY FOR ARCHITECT FINAL GATE`.

This document is architectural/product acceptance of Checkpoint B. It is NOT authorization for the assistant to merge to `main`; merge remains an explicit owner action.

## 2. FINAL EVIDENCE

Accepted final evidence on exact product SHA `6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d`:

- Round 12 R11 reproducer: 2/2 PASS;
- Round 10 regression matrix with the owner-accepted font item excluded from reopening: 4/4 PASS;
- full repository suite: 888/888 PASS;
- Ruff: PASS;
- `guard.py check arch/spec.md`: PASS;
- `git diff --check`: PASS;
- `rota/application/schedule_export.py`: exactly 600 lines;
- Round 11 had exactly one remaining implementation finding, R11-1;
- Round 12 closes exactly R11-1 without reopening any earlier accepted section.

The branch HEAD immediately before this acceptance was exactly final audit commit:

`0cb6c0e93a9bd0443cf184ea3331a5c272c56570`.

## 3. ARCHITECTURE ACCEPTED

The implementation preserves the frozen architecture boundary:

- T020 is read/presentation logic, not a second planning system;
- solver coverage is unchanged;
- U/C symbols are presentation-only and do not create Assignment or cover ShiftDemand;
- no T020 production changes exist in `rota/planning/**`, `rota/balance.py`, `rota/domain.py`, or `rota/persistence/schedule_lifecycle.py`;
- no changes exist in `arch/spec.md`, `arch/FROZEN.lock`, `Grafiki/**`, or accepted Checkpoint A artifacts;
- no second schedule model, PDF history table, generic workflow/event system, or generic settings subsystem was introduced;
- normal catalog-H24 presentation is validated under the T020 normal-H24 contract, including exact `{1,2}` component identity and exactly 12h per component;
- emergency cross-month/cross-year presentation does NOT duplicate T012 emergency legality validation: T020 uses persisted adjacent `(employee_id, work_period_id)` linkage and effective lineage only;
- adjacent facts actually used for collapse/suppression affect document revision/provenance;
- real work code mapping remains exact interval-based, not duration-only guessing;
- accepted Checkpoint A visual composition remains the production baseline.

## 4. OWNER-ACCEPTED FONT ITEM — CLOSED, NOT A BLOCKER

The font-resolution item previously discussed in implementation audit is CLOSED by explicit owner acceptance of the current rendered behavior.

It is not reopened by this final gate and is not a blocker for T020 acceptance.

This acceptance does not create a new general font architecture rule for unrelated future tasks.

## 5. TASK_SCOPE / FORBIDDEN-PATH CHECK

Implementation diff is measured from:

`c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2`

to accepted product SHA:

`6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d`.

Authorized implementation paths are respected:

- `pyproject.toml`;
- `rota/application/schedule_export.py`;
- `rota/persistence/db.py`;
- `rota/persistence/site_repository.py`;
- `rota/persistence/employee_repository.py`;
- `tests/test_t020.py`;
- `tests/test_t012.py` under Scope Amendment 01 restriction;
- `tests/test_t019b.py` under Scope Amendments 01/02 restrictions.

Pipeline/task documents and audit evidence under `tasks/ROTA-T020/**` are not production implementation paths.

The two legacy-test restrictions are satisfied:

- `tests/test_t012.py`: only `LATEST_SCHEMA_VERSION == 6` -> `== 7`;
- `tests/test_t019b.py`: schema assertion `6 -> 7`, test rename to latest/expected-tables wording, and addition of `site_print_settings` to the expected latest-schema table delta; no semantic rewrite of T019b behavior.

## 6. MECHANICAL SIZE / DIFF EXCEPTIONS — ACCEPTED FOR THIS SHA ONLY

The backend size/diff gate produces mechanical review items that do not represent product or architecture defects. They are accepted narrowly for this exact T020 implementation and create no precedent.

### 6.1 `tests/test_t012.py` — 1701 lines

Accepted because this is inherited T012 test size. T020 changes one existing assertion token only (`6 -> 7`) with zero net line growth and no semantic expansion.

No refactor/split of T012 tests is required by T020.

### 6.2 `tests/test_t019b.py` — 899 lines

Accepted because T019b already had a dedicated prior size allowance up to 900 lines, and T020 performs only the exact latest-schema oracle maintenance authorized by Scope Amendments 01/02.

No unrelated T019b refactor is required by T020.

### 6.3 `tests/test_t020.py` — 689 lines

Accepted as a one-time exact T020 dedicated-test exception.

Reason: the frozen T020 contract requires a broad single dedicated matrix across migration/settings, lineage/effective_from, row population, D/N mapping, normal/emergency 24h presentation, U/C decomposition, provenance/revision, fail-closed cases, layout, static PDF and the later linkage responsibility matrix. Splitting this file solely to satisfy a mechanical line ceiling would add another test artifact without improving ownership or behavior.

This exception is exact to 689 lines at accepted product SHA and is non-precedential.

### 6.4 Implementation diff arithmetic

For non-pipeline authorized implementation files, the exact GitHub diff from implementation `before_sha` to accepted product SHA is append-heavy:

- additions: 1515;
- deletions: 6;
- total changed lines: 1521;
- additions/deletions ratio: 252.5:1.

The high ratio is expected for this task because it introduces the new 600-line export module, the new 689-line dedicated test matrix, migration 7/settings persistence support, and only narrow edits to existing code/tests.

`TOTAL_LINES=1521` and `RATIO=252.5:1` are accepted for exact ROTA-T020 product SHA only. They are not permission for future tasks to exceed backend thresholds.

## 7. DUPLICATION CHECK

The implementation-time R6 Linkage Narrowing Amendment is satisfied architecturally.

T020 does not own a second emergency-24h validator. The exporter distinguishes normal H24 according to its own presentation contract, while emergency cross-boundary linkage trusts persisted WorkPeriod identity and adjacent effective truth rather than rechecking T012 D/N/rest/gap/H12 legality.

This separation is intentional and accepted.

## 8. FINAL STATUS

Checkpoint A: ACCEPTED / frozen.

Checkpoint B contract: ACCEPTED.

Checkpoint B implementation at `6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d`: ACCEPTED.

Independent implementation audit through Round 12: PASS.

ROTA-T020: PASS — READY FOR MERGE.

No further implementation or audit round is required for the accepted scope unless the product SHA changes.

No merge to `main` is performed or authorized by this record alone.
