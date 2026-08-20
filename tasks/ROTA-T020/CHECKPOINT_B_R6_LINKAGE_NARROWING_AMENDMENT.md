# ROTA-T020 — CHECKPOINT B R6 LINKAGE NARROWING AMENDMENT

STATUS: ARCHITECT AMENDMENT — BINDING FOR IMPLEMENTATION CORRECTION — CC MAY CONTINUE AFTER THIS RECORD
DATE: 2026-08-20
TASK_ID: ROTA-T020
PARENT_CONTRACT: tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md
PARENT_R6_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_R6_AMENDMENT.md
SCOPE: R6 Section 5 emergency cross-month/cross-year recognition only

## 1. PURPOSE

This amendment narrows R6 Section 5 so T020 does not duplicate canonical T012 emergency-work-period validation.

The planning/validation layer already owns whether an emergency-shaped persisted WorkPeriod is structurally legal. In particular, T012 validator/work-period logic owns rules such as opposite D/N kind, direct contiguity, emergency-rest snapshot, terminal required-rest match and the internal legitimacy of the emergency pair.

T020 is a read/presentation use case. Its responsibility is only to identify whether persisted schedule truth says that work on one side of a month boundary is linked to the same WorkPeriod on the adjacent month, so the accepted one-symbol `24` presentation can be collapsed/suppressed correctly.

Duplicating the T012 structural rules in `rota/application/schedule_export.py` is an architectural error: it creates a second validator whose behavior can drift from the planning validator.

This amendment changes no product behavior, solver behavior, Assignment meaning, T012 behavior, Checkpoint A visuals, U/C rules, TASK_SCOPE, schema or persistence model.

Where this amendment conflicts with R6 Section 5.4/5.5 or the R6 T20-41 oracle, this amendment controls.

## 2. CANONICAL RESPONSIBILITY BOUNDARY

### 2.1 T012 / planning-validator owns legitimacy

T020 MUST NOT independently re-derive whether a persisted emergency WorkPeriod is legal.

The exporter MUST NOT implement or duplicate checks equivalent to:

- opposite D/N shift-kind validation;
- 12h/H12 emergency-component classification;
- direct temporal contiguity / gap / overlap validation;
- first-demand `emergency_24h_rest_hours` validation;
- second Assignment `required_rest_after_hours` equality with the emergency snapshot;
- any function semantically corresponding to `check_emergency_pair_structure()`;
- any second emergency-pair validator maintained in the export layer.

T020 trusts canonical persisted planning truth produced through the planning/validator path.

This is not permission to weaken T012. It is a prohibition on duplicating T012 in T020.

### 2.2 T020 owns linkage for presentation

For emergency cross-month/cross-year presentation, T020 checks only the persisted linkage required to decide collapse/suppression.

The canonical identity is:

`(employee_id, work_period_id)`

with `work_period_id` required to be non-null.

The adjacent item must come from the effective CURRENT truth of the immediately adjacent month of the same Site, reconstructed under the already-frozen lineage/effective_from rules.

No unrelated adjacent-month work enters the requested grid, roster, U/C calculation or summaries.

## 3. OUTGOING BOUNDARY PRESENTATION

Let A be work visible in requested month M whose persisted provenance has non-null `work_period_id`.

Inspect only the effective boundary truth of M+1.

Results:

1. Exactly one adjacent Assignment has the same `(employee_id, work_period_id)`:
   - treat A and that adjacent Assignment as the same already-validated persisted WorkPeriod for T020 presentation;
   - render one `24` on A's WorkPeriod/start-side date in M;
   - suppress A's ordinary D/N presentation;
   - do not import the adjacent Assignment as a separate M cell;
   - count the accepted `24` once in M summaries.

2. No adjacent Assignment has that exact identity:
   - no cross-month linkage is proven;
   - A remains ordinary work and is rendered through the normal D/N mapping.

3. Adjacent work has a different `work_period_id`:
   - it is not linked;
   - A remains ordinary work.

4. Adjacent work has the same `work_period_id` but a different Employee:
   - it is not the same canonical identity;
   - it does not create linkage.

T020 does not ask again whether the matching persisted pair has the correct D/N/rest/gap/H12 structure.

## 4. INCOMING BOUNDARY PRESENTATION

Let B be effective work in requested month M with non-null `work_period_id` and inspect only the effective boundary truth of M-1.

If exactly one prior Assignment has the same `(employee_id, work_period_id)`, B is the continuation of the already-validated persisted WorkPeriod whose paper symbol belongs to the prior month/start side.

Therefore:

- B emits no ordinary D/N symbol in M;
- B emits no second `24` symbol;
- B contributes zero additional visible PLAN/WYK hours to M summaries;
- no prior-month work is imported into M as a visible cell.

If no exact identity match exists, B remains ordinary work.

Different `work_period_id` or different Employee does not create linkage.

## 5. FAIL-CLOSED CONDITIONS OWNED BY T020

T020 still fails closed for failures inside ITS own read/linkage responsibility.

### 5.1 Adjacent lineage failure

If an adjacent CURRENT month exists and the exact boundary truth that must be inspected cannot be reconstructed because of missing parent, cycle, Site/month mismatch or required `effective_from=None`, return:

`PROVENANCE_INCOMPLETE`

with no partial PDF.

### 5.2 Ambiguous or referentially incomplete linkage

If the effective adjacent boundary truth yields more than one candidate for the same canonical `(employee_id, work_period_id)`, or the exporter cannot unambiguously resolve the persisted identity needed for collapse/suppression, return:

`WORK_PROVENANCE_INCOMPLETE`

with no partial PDF.

This is linkage/referential integrity only. It MUST NOT become a second validation of D/N, duration, contiguity, rest or emergency-demand structure.

### 5.3 No match is not corruption

Absence of an exact adjacent identity match is not itself an error.

It means no cross-month WorkPeriod linkage is proven for T020 and the requested work remains ordinary 12h/D-N presentation, as already frozen by R6.

## 6. NORMAL CATALOG-H24 IS NOT REOPENED HERE

This amendment is intentionally narrow to R6 Section 5 emergency cross-month/cross-year linkage.

R6 Section 4 normal catalog-H24 presentation remains unchanged by this amendment.

No broader redesign of normal 24h recognition is authorized by this document.

## 7. REVISION / PROVENANCE REMAINS CONTENT-SENSITIVE

The R6 revision rule remains binding.

When adjacent data is actually consulted and used to decide collapse/suppression, document revision/provenance MUST include the exact adjacent data that influenced that decision.

At minimum this includes:

- ordered adjacent current-lineage `(version_id, effective_from)` metadata actually used;
- the persisted adjacent Assignment identity/provenance facts actually used for the linkage decision, including `employee_id`, non-null `work_period_id`, schedule-version identity and assignment identity;
- any other adjacent field actually consumed by the linkage implementation.

Fields not consulted for linkage must not be added merely to recreate T012 validation in the revision model.

`generated_at` remains excluded.

Unrelated adjacent work remains excluded.

A later adjacent PLAN/REPLAN that changes whether an outgoing/incoming link exists may therefore change the earlier/later document revision because it changes visible content or suppression provenance. No ScheduleVersion mutation or export-history table is introduced.

## 8. TEST MATRIX CORRECTION

### 8.1 T20-39 / T20-40 remain

T20-39 and T20-40 remain required for outgoing/incoming month/year boundary behavior, revision change, suppression and isolation of unrelated adjacent work.

They MUST NOT re-test T012 internal structural legality in T020.

### 8.2 T20-41 is superseded

The R6 malformed-emergency structural matrix in T20-41 is REMOVED from T020 responsibility.

Replace T20-41 with an exporter-linkage responsibility matrix covering at least:

1. outgoing exact unique `(employee_id, work_period_id)` match -> one `24` on start side;
2. incoming exact unique match -> continuation suppressed, zero duplicate visible hours;
3. no adjacent match -> ordinary work;
4. same Employee + different `work_period_id` -> ordinary work;
5. same `work_period_id` + different Employee -> no linkage;
6. unrelated adjacent work -> ignored;
7. multiple adjacent candidates for one exact canonical identity -> `WORK_PROVENANCE_INCOMPLETE`, no PDF;
8. adjacent CURRENT lineage corruption -> `PROVENANCE_INCOMPLETE`, no PDF;
9. month and year boundaries are both represented.

Do NOT add T020 tests for same-D/N, malformed emergency rest, gap/overlap, INNY/H12 classification or other conditions already owned by T012 emergency validation.

Existing T012 tests remain the proof of those rules.

## 9. IMPLEMENTATION CONSTRAINT

`rota/application/schedule_export.py` may contain only the minimal adjacent-month read and canonical identity-linkage logic required by this amendment.

It MUST NOT contain an exporter-owned emergency structural validator.

If current implementation contains such duplicate logic, CC is authorized and required to remove/simplify it and update `tests/test_t020.py` to the corrected responsibility matrix.

Both files are already inside the accepted TASK_SCOPE; no new production path is authorized.

## 10. GATE CONSEQUENCE

This is an architect correction to avoid duplicated business-rule logic discovered during implementation.

It does not reopen the completed preimplementation product gate and does not change the original implementation `before_sha` used to measure the implementation diff.

The existing implementation `before_sha` remains:

`c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2`

CC may continue only after this amendment is present on the task branch.

The next independent implementation audit must verify:

- no duplicate T012 emergency structural validator in `schedule_export.py`;
- cross-month linkage is based only on unambiguous persisted `(employee_id, work_period_id)` identity plus adjacent effective lineage;
- T20-39/T20-40 remain;
- T20-41 is the exporter-linkage matrix above;
- adjacent facts actually used still affect document revision/provenance;
- no solver/planning/T012 production code was changed by T020.

No merge authorization is granted by this amendment.
