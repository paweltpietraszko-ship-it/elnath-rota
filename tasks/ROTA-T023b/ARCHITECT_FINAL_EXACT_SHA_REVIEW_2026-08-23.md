# ROTA-T023b — ARCHITECT FINAL EXACT-SHA REVIEW

DATE: 2026-08-23
IMPLEMENTATION_SHA_REVIEWED: `cbd5c16d5d5232ebed44bfbd3c9bc1c082c3c666`
EVIDENCE_HEAD_BEFORE_THIS_REVIEW: `34e991dc4db9022abebd157f78ecca67a478a7e9`
CONTRACT_HEAD: `50ac0cb1c6b09661dbd16d15c3bad8228f995507`
R9_REPORT: `tasks/ROTA-T023b/round_01/tests/tests_r9.txt`
PREVIOUS_ARCHITECT_FINDING: `tasks/ROTA-T023b/ARCHITECT_IMPLEMENTATION_REVIEW_2026-08-23.md`

## REVIEW MODE

This is the architect's own final technical + substantive exact-SHA review. CC/Codex tests and gates were **not rerun**. Their R9 execution results are treated as independent evidence; product semantics, ownership and the A1 correction were independently reviewed in source.

## EXECUTION EVIDENCE ACCEPTED

R9 reports on exact implementation SHA `cbd5c16d5d5232ebed44bfbd3c9bc1c082c3c666`:

- T023b + adversarial audit matrix: 38 passed;
- relevant vertical/regression set: 113 passed;
- full repository behavioural suite: 1052 passed;
- Ruff: PASS;
- `git diff --check`: PASS.

The sole old T023 Checkpoint-B source-diff proof remains formally excluded by owner decision because T023b deliberately modifies the previously frozen source-shape of `constraints.py` / `work_periods.py`. This exclusion does not waive behavioural T023 regressions.

The owner-accepted backend NEW_FILES / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES exceptions remain delivery exceptions, not product defects. No further shrinking or source reshaping is required solely to make those historical structural gates green.

## SUBSTANTIVE REVIEW

### 1. Site planning regime and product boundary — PASS

- `Site` remains the planning/service unit, not a physical-object aggregate.
- `SitePlanningRegime` is explicit and non-boolean (`ORDINARY | OCHRONA`).
- ordinary Site writes cannot mutate regime;
- deliberate correction is a separate audited application operation;
- no CLEANING semantics, cross-Site T023b aggregation or inferred external work was introduced.

### 2. Durable regime correction / R5-3 — PASS

R5-3 remains structurally closed:

- ScheduleVersion persists planning-regime provenance;
- `version_requires_regime_replan()` derives mismatch from persisted Site + ScheduleVersion facts after restart;
- FINALIZE and RESTORE fail closed for regime-stale PLANNED content;
- PDF presentation fails closed;
- child creation conservatively inherits parent provenance;
- only successful selected-candidate persistence after fresh validation adopts current Site regime provenance;
- no extra lifecycle status/table/action kind is needed.

### 3. Immediate rest after exact 24h work — PASS

- existing `REST-01` remains the rule code;
- exact 24h target-Site WorkPeriod under OCHRONA gets `max(configured/resolved rest, 24h)` at read/enforcement time;
- configured stronger values remain stronger;
- persisted rest provenance is not rewritten;
- normal H24 and emergency H12+H12 use the same WorkPeriod owner;
- the T023b floor is not applied to other-Site work;
- month boundary does not cancel immediate rest owed after a concrete 24h period.

### 4. Weekly rest semantics — PASS

- only complete seven-day settlement windows starting at month day 1 exist;
- trailing month-end days do not create another WEEKLY-REST-01 window;
- no weekly window crosses settlement-month boundary;
- target-Site non-CANCELLED PRIMARY and TRAINEE work occupies time;
- shared `work_periods.py` arithmetic clips intervals, merges overlapping/abutting work and measures the maximum uninterrupted free interval;
- threshold is exactly >=35h;
- LOAD-01, ISO weeks, rolling windows and automatic 24h weekly exception were not substituted.

### 5. Architect finding A1 — CLOSED / PASS

The previous architect finding concerned same-Site month-boundary work entering day 1.

The correction is semantically correct and narrow:

- solver was already correct and remains unchanged: WEEKLY target fixed facts include `fixed_existing_assignments + state.boundary_assignments`, excluding `state.other_site_assignments`;
- validator `_check_weekly_rest()` now evaluates current/candidate non-CANCELLED target Assignments plus non-CANCELLED same-Site `state.boundary_assignments`;
- manual `_weekly_rest_override_facts()` reconstructs from the same boundary-inclusive target-Site fact set;
- both continue to use the same pure weekly oracle rather than reimplementing clipping/merging arithmetic;
- canonical assembler excludes the target/current ScheduleVersion from boundary context, so this does not double-count the current plan;
- focused regression proves both direct validator behaviour and persistence -> assembler -> `apply_manual_correction()` behaviour for previous-month work overlapping day 1.

Therefore solver, independent validator and manual audit are now aligned on the reachable same-Site boundary class that caused A1.

### 6. Manual exception path — PASS

- T023b reuses the existing REST override precedent rather than creating another exception subsystem;
- `WEEKLY-REST-01` maps to LAW deviation;
- manual weekly facts are fact-derived through the shared pure owner;
- one logical manual correction creates at most one existing-style `REST_OVERRIDE_RECORD` for REST-01 / WEEKLY-REST-01 facts;
- no new coordinator action kind, audit table or hook-order redesign was introduced solely for T023b.

### 7. Architecture / scope discipline — PASS

No remaining T023b implementation mechanism appears to exist only for hypothetical future scenarios. The implementation reuses existing Site persistence, ScheduleVersion lifecycle, canonical assembler, work-period owner, independent validator and REST override path. The final A1 correction added only the missing reachable same-Site boundary facts and did not widen product semantics.

## FINAL VERDICT

**PASS — ARCHITECT EXACT-SHA ACCEPTED.**

Exact product implementation accepted:

`cbd5c16d5d5232ebed44bfbd3c9bc1c082c3c666`

No known product or architecture blocker remains for ROTA-T023b.

Delivery is accepted with the owner's already-recorded backend structural exceptions and exclusion of the obsolete T023 Checkpoint-B source-diff proof. Those exceptions do not waive behavioural regressions.

No further product-code changes are requested by the architect.

Merge remains an explicit owner action; this review does not perform or authorize the merge on the owner's behalf.
