# ROTA-T020 — printable schedule PDF — CHECKPOINT B master brief

STATUS: READY FOR CODEX R5-ONLY REAUDIT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
BASE_BRANCH: main
BASE_SHA: d9c87185e3051aa65df3234c8db2d703fe32c5d8
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
DESIGN_PARENT_HEAD: 55c9b388959a3bb757d2d3e72d61f81d5e3bce88
OWNER_SOURCE: arch/T020_schedule_export_architect_brief.md
FULL_B_CONTRACT: tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md
R5_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_R5_AMENDMENT.md
R5_AUDIT_COMMIT: 891013d3ccecf8fdbe8a5772d17be4fdb21ac111
AUTHORITATIVE_ABSENCE_DECISION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md
ROW_POPULATION_DECISION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_02.md section 1
CHECKPOINT_A_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md
CHECKPOINT_A_ARTIFACT_COMMIT: d88a85b06a2de98eda65617603b12caec0cf5d59

## 1. CURRENT CONTRACT

This file is the backend/master entry point for Checkpoint B.

The former Checkpoint A contract remains preserved in Git history and its accepted result is frozen by `CHECKPOINT_A_ACCEPTANCE.md`. Do not use the old A-only `TASK_SCOPE` for production B.

The normative implementation contract is `tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md` as refined by the later narrow `tasks/ROTA-T020/CHECKPOINT_B_R5_AMENDMENT.md`.

Source precedence for T020 B is:

1. explicit current owner decisions;
2. `arch/T020_schedule_export_architect_brief.md`;
3. `CHECKPOINT_A_ACCEPTANCE.md` and exact accepted PDF artifacts;
4. authoritative correction `CHECKPOINT_B_OWNER_DECISIONS_05.md`;
5. preserved row-population rule in `CHECKPOINT_B_OWNER_DECISIONS_02.md` section 1;
6. `CHECKPOINT_B_R5_AMENDMENT.md` for the exact R5-1..R5-4 refinements;
7. `CHECKPOINT_B_CONTRACT.md` for the remaining technical architecture and testable implementation details.

`CHECKPOINT_B_OWNER_DECISIONS_03.md` and `_04.md` are superseded. The old absence-allocation interpretation in `_01.md` is superseded by `_05.md`. `ARCHITECT_PLANNING_GAP_01.md` is withdrawn as a blocker. Round 4 remains historical implementation evidence only.

Round 5 at commit `891013d3ccecf8fdbe8a5772d17be4fdb21ac111` found exactly R5-1..R5-4. Those four findings are answered by `CHECKPOINT_B_R5_AMENDMENT.md`; they require narrow independent re-audit before CC.

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

Existing files modified are limited to persistence/schema/settings support and the ReportLab dependency, exactly as listed in the final `TASK_SCOPE` below.

No new repository module, no export-history table, no second schedule model and no generic settings subsystem are authorized.

## 5. R5-ONLY PREIMPLEMENTATION REAUDIT GATE

Codex must audit the exact current HEAD before production CC starts.

This next round is deliberately narrow. It checks only:

- T020-B-R5-1: exact work-code settings schema, uniqueness and zero/one/many real-work mapping;
- T020-B-R5-2: start-date anchor for ordinary overnight work across `effective_from`;
- T020-B-R5-3: exact normal/emergency T012 24h structural recognition;
- T020-B-R5-4: mandatory fail-closed/negative evidence supplement;
- exact SHA and confirmation that no production code changed while closing the contract findings.

Sections already PASS in Round 5 are not reopened unless the R5 amendment directly contradicts them.

Codex does not write production code during this gate.

Required verdict:

`PASS — R5-1..R5-4 CLOSED — READY_FOR_IMPLEMENTATION`

or

`FAIL — R5 FINDINGS REMAIN`

Until independent PASS is recorded and accepted by architect:

**PRODUCTION CC MUST NOT START.**

## 6. IMPLEMENTATION BACKEND BASE

After Codex PASS and architect acceptance, the backend implementation `before_sha` is the exact final preimplementation accepted SHA, not `main`.

That keeps owner/architect/audit pipeline artifacts outside the implementation diff and makes NEW_FILES count the actual B implementation only.

## 7. FORBIDDEN IMPLEMENTATION PATHS

The following remain explicitly out of implementation scope:

`rota/planning/**`, `rota/balance.py`, `rota/domain.py`, `rota/persistence/schedule_lifecycle.py`, `arch/spec.md`, `arch/FROZEN.lock`, `Grafiki/**`, Checkpoint A PDFs/renderer.

Any audit-proven need to change one of these requires an architect amendment before CC touches it.

## 8. CANONICAL IMPLEMENTATION TASK_SCOPE

TASK_SCOPE:
- pyproject.toml
- rota/application/schedule_export.py
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/persistence/employee_repository.py
- tests/test_t020.py