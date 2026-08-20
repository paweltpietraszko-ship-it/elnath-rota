# ROTA-T020 — printable schedule PDF — CHECKPOINT B master brief

STATUS: ARCHITECT FINAL GATE ACCEPTED — READY FOR MERGE
DATE: 2026-08-20
TASK_ID: ROTA-T020
BASE_BRANCH: main
BASE_SHA: d9c87185e3051aa65df3234c8db2d703fe32c5d8
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
DESIGN_PARENT_HEAD: 55c9b388959a3bb757d2d3e72d61f81d5e3bce88
OWNER_SOURCE: arch/T020_schedule_export_architect_brief.md
FULL_B_CONTRACT: tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md
R5_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_R5_AMENDMENT.md
R6_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_R6_AMENDMENT.md
R6_LINKAGE_NARROWING: tasks/ROTA-T020/CHECKPOINT_B_R6_LINKAGE_NARROWING_AMENDMENT.md
SCOPE_AMENDMENT_01: tasks/ROTA-T020/CHECKPOINT_B_SCOPE_AMENDMENT_01.md
SCOPE_AMENDMENT_02: tasks/ROTA-T020/CHECKPOINT_B_SCOPE_AMENDMENT_02.md
R5_AUDIT_COMMIT: 891013d3ccecf8fdbe8a5772d17be4fdb21ac111
R6_AUDIT_COMMIT: 501a3c69ee39a1f541a4567aa9c33d3040e83e5a
FINAL_PREIMPLEMENTATION_AUDIT_COMMIT: 1e02f66e00a48cf7b95de41b6d920900e83d036c
FINAL_PREIMPLEMENTATION_AUDIT_REPORT: tasks/ROTA-T020/round_01/tests/tests_r7.txt
ARCHITECT_PREIMPLEMENTATION_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_B_PREIMPLEMENTATION_ACCEPTANCE.md
FINAL_IMPLEMENTATION_PRODUCT_SHA: 6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d
FINAL_IMPLEMENTATION_AUDIT_COMMIT: 0cb6c0e93a9bd0443cf184ea3331a5c272c56570
FINAL_IMPLEMENTATION_AUDIT_REPORT: tasks/ROTA-T020/round_01/tests/tests_r12.txt
ARCHITECT_FINAL_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_B_FINAL_ACCEPTANCE.md
AUTHORITATIVE_ABSENCE_DECISION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md
ROW_POPULATION_DECISION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_02.md section 1
CHECKPOINT_A_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md
CHECKPOINT_A_ARTIFACT_COMMIT: d88a85b06a2de98eda65617603b12caec0cf5d59

## 1. CURRENT CONTRACT

This file is the backend/master entry point for Checkpoint B.

The former Checkpoint A contract remains preserved in Git history and its accepted result is frozen by `CHECKPOINT_A_ACCEPTANCE.md`. Do not use the old A-only `TASK_SCOPE` for production B.

The normative implementation contract is `tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md` as refined by the later narrow amendments. Current precedence is:

1. explicit current owner decisions;
2. `arch/T020_schedule_export_architect_brief.md`;
3. `CHECKPOINT_A_ACCEPTANCE.md` and exact accepted PDF artifacts;
4. authoritative correction `CHECKPOINT_B_OWNER_DECISIONS_05.md`;
5. preserved row-population rule in `CHECKPOINT_B_OWNER_DECISIONS_02.md` section 1;
6. `CHECKPOINT_B_R6_LINKAGE_NARROWING_AMENDMENT.md` solely for the R6 Section 5 emergency cross-month/cross-year responsibility boundary and corrected T20-41 oracle;
7. `CHECKPOINT_B_SCOPE_AMENDMENT_02.md` solely for the second mechanical T019b latest-schema migration-oracle correction;
8. `CHECKPOINT_B_SCOPE_AMENDMENT_01.md` solely for the mechanical schema-version assertion scope extension;
9. `CHECKPOINT_B_R6_AMENDMENT.md` for the Round-6 closure of remaining R5-1/R5-3/R5-4 findings except where narrowed by item 6;
10. `CHECKPOINT_B_R5_AMENDMENT.md` for R5 refinements not superseded by R6/later narrowing;
11. `CHECKPOINT_B_CONTRACT.md` for the remaining technical architecture and testable implementation details.

`CHECKPOINT_B_OWNER_DECISIONS_03.md` and `_04.md` are superseded. The old absence-allocation interpretation in `_01.md` is superseded by `_05.md`. `ARCHITECT_PLANNING_GAP_01.md` is withdrawn as a blocker. Round 4 remains historical implementation evidence only.

Round 5 found R5-1..R5-4. Round 6/7 closed them for preimplementation. During implementation review, the architect then narrowed R6 Section 5 because re-validating T012 emergency WorkPeriod legality inside the exporter would duplicate canonical planning/validator logic. The linkage narrowing changes no product behavior: it removes duplicate validation responsibility from T020 and leaves only adjacent persisted `(employee_id, work_period_id)` linkage plus lineage/provenance handling.

After architect acceptance, implementation also discovered two purely mechanical scope consequences of migration 7:

- `CHECKPOINT_B_SCOPE_AMENDMENT_01.md` authorizes the exact `LATEST_SCHEMA_VERSION == 6` -> `== 7` updates in `tests/test_t012.py` and `tests/test_t019b.py`;
- `CHECKPOINT_B_SCOPE_AMENDMENT_02.md` additionally corrects the existing T019b public-`connect()` latest-schema migration oracle so its name no longer claims v6/three tables and its expected post-v5 table delta includes the T020 `site_print_settings` table.

These amendments do not change owner product behavior or reopen the completed preimplementation product gate.

Final implementation audit through Round 12 is complete. Exact product SHA `6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d` is architect-accepted by `CHECKPOINT_B_FINAL_ACCEPTANCE.md`. No further implementation/audit round is required unless the product SHA changes.

## 2. NON-NEGOTIABLE PRODUCT BOUNDARY

T020 does not change solver coverage.

Absent Employees do not receive operational Assignments merely for printing. Real Site demand remains fully covered by Employees actually eligible to work.

T020 reads canonical Rota state and adds U/C as a paper presentation convention in otherwise empty qualifying LOCAL-row cells. Those symbols are not ShiftDemand coverage and are not persisted into ScheduleVersion.

Frozen example remains:

PLAN `D1 / D1 / N2` = 40h

WYK `U1 / U1 / U2` = 40h

No rounding or guessed symbol is allowed.

## 3. CHECKPOINT A VISUAL GATE IS CLOSED

Accepted exact artifact commit:

`d88a85b06a2de98eda65617603b12caec0cf5d59`

Accepted blobs:

- 12h PDF: `91d617c32b96296814debc7696f5a621cde40973`;
- 24h PDF: `2a0f6a706142eaa77f8992c98dd1cc98d2ebf1ba`.

A3 landscape, accepted density/name handling, PLAN/WYK rows, 24h start-date symbol, asymmetric legend, grayscale cues and header/provenance composition are binding as stated in `CHECKPOINT_A_ACCEPTANCE.md`.

## 4. IMPLEMENTATION SHAPE

Checkpoint B uses exactly two new non-pipeline implementation files:

- `rota/application/schedule_export.py`;
- `tests/test_t020.py`.

Existing files modified are limited to persistence/schema/settings support, the ReportLab dependency, and the exact legacy-test maintenance edits explicitly authorized by Scope Amendments 01 and 02, exactly as listed/restricted below.

No new repository module, no export-history table, no second schedule model and no generic settings subsystem are authorized.

### 4.1 No duplicate T012 emergency validator in export

For R6 Section 5 cross-month/cross-year emergency presentation, `schedule_export.py` trusts already-validated persisted WorkPeriod provenance and checks only unambiguous adjacent `(employee_id, work_period_id)` linkage from effective CURRENT truth.

T020 does not duplicate T012 checks for D/N kind, H12 classification, gap/overlap/contiguity, emergency rest snapshot or terminal rest equality, and does not contain an exporter-owned equivalent of `check_emergency_pair_structure()`.

Outgoing exact linkage -> one `24` on the start side. Incoming exact linkage -> continuation suppressed. No match / different work_period_id / different Employee -> no linkage, ordinary work. Ambiguous or referentially incomplete linkage remains fail-closed. Adjacent lineage corruption remains `PROVENANCE_INCOMPLETE`.

Adjacent facts actually used to decide collapse/suppression remain part of revision/provenance because they affect visible content.

R6 T20-41 is superseded by the exporter-linkage responsibility matrix in `CHECKPOINT_B_R6_LINKAGE_NARROWING_AMENDMENT.md`. T20-39/T20-40 remain without re-testing T012 structural legality.

## 5. PREIMPLEMENTATION GATE — CLOSED

Independent preimplementation audit sequence is complete.

Final independent preimplementation audit:

- audited contract HEAD: `71383665d06aed02ce32e452b7a9f85ad9c9559b`;
- audit commit: `1e02f66e00a48cf7b95de41b6d920900e83d036c`;
- report: `tasks/ROTA-T020/round_01/tests/tests_r7.txt`;
- verdict: `PASS — REMAINING R5 FINDINGS CLOSED — READY_FOR_IMPLEMENTATION`;
- exact-SHA/no-production-diff sanity: PASS;
- committed T012 cross-boundary mechanics: 5/5 PASS;
- full-suite evidence on the unchanged preimplementation product/test tree: 845/845 PASS from Round 5.

Architect preimplementation acceptance is recorded in `CHECKPOINT_B_PREIMPLEMENTATION_ACCEPTANCE.md`.

## 6. IMPLEMENTATION FINAL GATE — CLOSED

Accepted exact product SHA:

`6ea9e09b01d66a9b2837571e4f3d67dd4ec47f9d`

Final independent audit:

- audit commit: `0cb6c0e93a9bd0443cf184ea3331a5c272c56570`;
- report: `tasks/ROTA-T020/round_01/tests/tests_r12.txt`;
- verdict: `PASS — R11-1 CLOSED — CHECKPOINT B READY FOR ARCHITECT FINAL GATE`;
- R11 reproducer: 2/2 PASS;
- full suite: 888/888 PASS;
- Ruff / guard / `git diff --check`: PASS;
- `schedule_export.py`: exactly 600 lines.

The owner-accepted font item is CLOSED and is not reopened by final acceptance.

Architect final acceptance is recorded in `CHECKPOINT_B_FINAL_ACCEPTANCE.md`, including exact mechanical size/diff exceptions for this SHA only.

**ROTA-T020 CHECKPOINT B: PASS — READY FOR MERGE.**

No merge is performed or implied by this brief. Merge to `main` remains an explicit owner action.

## 7. IMPLEMENTATION BACKEND BASE

The implementation backend/diff base remains the exact amended preimplementation/scope HEAD recorded before the first production implementation commit:

`c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2`

The later R6 linkage narrowing was recorded after implementation had begun and therefore does NOT reset or replace this mechanical `before_sha`.

Implementation and audit diffs are measured from `c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2`.

## 8. FORBIDDEN IMPLEMENTATION PATHS

The following remain explicitly out of scope:

`rota/planning/**`, `rota/balance.py`, `rota/domain.py`, `rota/persistence/schedule_lifecycle.py`, `arch/spec.md`, `arch/FROZEN.lock`, `Grafiki/**`, Checkpoint A PDFs/renderer.

In particular, T020 does not modify T012/planning production code merely to support export linkage. The existing planning validator remains canonical.

## 9. CANONICAL IMPLEMENTATION TASK_SCOPE

TASK_SCOPE:
- pyproject.toml
- rota/application/schedule_export.py
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/persistence/employee_repository.py
- tests/test_t020.py
- tests/test_t012.py
- tests/test_t019b.py

### `tests/test_t012.py` restriction

The only authorized T020 edit is:

`LATEST_SCHEMA_VERSION == 6` -> `LATEST_SCHEMA_VERSION == 7`.

No other change in `tests/test_t012.py` is permitted.

### `tests/test_t019b.py` restriction

Exactly these T020 edits are authorized, and no others:

1. `LATEST_SCHEMA_VERSION == 6` -> `LATEST_SCHEMA_VERSION == 7`;
2. rename `test_a1_real_v5_to_v6_migration_preserves_data_and_adds_exactly_three_tables` to `test_a1_real_v5_to_latest_migration_preserves_data_and_adds_expected_tables`;
3. add exactly `site_print_settings` to that test's expected `tables_after - tables_before` set, leaving the three existing T019b tables unchanged.

No fixture/helper, seed procedure, public `connect()` call, preserved-data assertion, migration-loop behavior, action-memory behavior, or any other test/oracle may change under T020.
