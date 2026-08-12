# ROTA-T008 — PRE-IMPLEMENTATION REVIEW 01 — ARCHITECT CLARIFICATION

DATE: 2026-08-13
STATUS: READY_FOR_RE-REVIEW
ORIGINAL_TASK_CONTRACT_SHA: 49ab1276ae0ee2eeff375a86224a87b57fd3c6a6
ARCHITECT: ChatGPT
IMPLEMENTER: CC
AUDITOR: Codex

## STATUS / PRECEDENCE

Codex pre-implementation review of `tasks/ROTA-T008/brief.md` at `49ab1276ae0ee2eeff375a86224a87b57fd3c6a6` returned `WYMAGA KOREKTY — NOT READY FOR IMPLEMENTATION` with five material contract findings.

This clarification closes exactly those five findings before implementation.

For the five topics below, this file has precedence over conflicting wording in the original `tasks/ROTA-T008/brief.md`. All other T008 scope, invariants, migration rules, transaction rules, acceptance criteria and out-of-scope boundaries remain unchanged.

CC MUST NOT implement from `49ab1276...` alone. Codex must re-review the contract set consisting of the original brief plus this clarification and return PASS / READY_FOR_IMPLEMENTATION or a precise remaining CONTRACT_GAP.

No roadmap change and no new product feature are introduced here. These corrections align T008 with the already-frozen product/architecture behavior.

---

## R1-1 — PRIMARY STORAGE MUST ALLOW MANUAL SPLITS AND TRUTHFUL COVERAGE VIOLATIONS

The original brief incorrectly required:

`Assignment interval equals the covered demand interval`.

That requirement is removed.

Frozen architecture distinguishes solver-generated normal coverage from manually recorded operational reality:
- solver-generated OCHRONA PRIMARY normally covers a full demand;
- manual correction MAY split one ShiftDemand across sequential PRIMARY Assignments;
- coverage gaps or excess PRIMARY overlap MUST be detectable by validation and MUST NOT prevent storing the real operational state.

Therefore T008 LocalStore is a persistence boundary, not a COVERAGE-01 validator.

### Corrected PRIMARY persistence invariants

For `Assignment.role == PRIMARY` T008 storage requires:
- `covers_demand_id` is present;
- `mentor_primary_assignment_id` is absent;
- referenced ShiftDemand exists in the SAME ScheduleVersion;
- Assignment has a valid positive actual interval (`end_datetime > start_datetime`), as already required.

T008 storage MUST NOT require:
- Assignment interval == ShiftDemand interval;
- one PRIMARY per demand;
- complete coverage of the demand;
- no gap inside demand coverage;
- no overlap/excess PRIMARY coverage;
- solver-standard D/N interval shape for a manually persisted Assignment.

Those are validation/planning concerns, not persistence admission rules.

The actual Assignment interval is authoritative and must round-trip exactly.

A WORKING snapshot MAY therefore persist, for one D demand 05:00–17:00:
- valid manual split: A 05:00–13:00 and B 13:00–17:00;
- truthful incomplete state: A 05:00–13:00 with 13:00–17:00 uncovered;
- another manually edited state that later validation classifies as excess/coverage violation.

T008 does not itself create the resulting `Deviation`; T009/validation owns the decision to attach/update Deviations. T008 only guarantees that such truthful WORKING state can be stored and reconstructed.

### Test correction

Replace original matrix item K2 semantics.

Required adversarial tests:
1. two same-version PRIMARY Assignments splitting one demand sequentially are accepted and round-trip;
2. a same-version PRIMARY covering only part of a demand is accepted and round-trips even when the remaining interval is uncovered;
3. storage does not manufacture fake coverage or expand the Assignment interval;
4. dangling/cross-version `covers_demand_id` remains rejected.

---

## R1-2 — CHILD SCHEDULEVERSION MUST PRESERVE PARENT REALIZED WORK

The original brief required REALIZED immutability indirectly through REPLAN regression boundaries but did not make child creation enforce it.

That is insufficient.

Whenever a new ScheduleVersion has `parent_version_id`, every Assignment that is `state == REALIZED` in the parent is an immutable historical fact and MUST be present unchanged in the child snapshot.

### Required preservation rule

For every parent REALIZED Assignment, child creation requires a corresponding Assignment with:
- the same `assignment_id`;
- child `schedule_version_id` equal to the new child version id;
- identical `employee_id`;
- identical `start_datetime`;
- identical `end_datetime`;
- identical `role`;
- identical `state == REALIZED`;
- identical `frozen`;
- identical `covers_demand_id`;
- identical `mentor_primary_assignment_id`.

The only field that necessarily differs is `schedule_version_id`, because the Assignment row belongs to the child snapshot.

Child creation MUST fail atomically if any parent REALIZED Assignment is:
- omitted;
- changed;
- changed to PLANNED or CANCELLED;
- moved to another Employee/time/role;
- rebound to another demand or mentor.

This does NOT forbid the child from changing a parent PLANNED Assignment to REALIZED when real work has subsequently occurred. It only protects facts that were already REALIZED in the parent.

This clarification does not make future `frozen=true` permanently immutable across all child versions: freeze/unfreeze is a separate coordinator operation in the frozen UI/application contract. The special cross-version storage invariant here is REALIZED, because ASSIGN-03 makes already-realized work non-negotiable.

### Test correction

Add to lineage/version tests:
1. child preserving all parent REALIZED rows succeeds;
2. child omitting one parent REALIZED row is rejected and current reference remains unchanged;
3. child modifying employee/time/role/state/reference of parent REALIZED is rejected atomically;
4. parent snapshot itself remains unchanged;
5. child may legitimately convert a previously PLANNED parent Assignment to REALIZED if all other applicable snapshot invariants pass.

---

## R1-3 — BOUNDARY CONTEXT IS AN ADJACENT INTERVAL QUERY, NOT MONTH-OVERLAP ONLY

The original `BOUNDARY CONTEXT QUERY` was too narrow because it returned only assignments whose actual interval overlaps the target month.

Frozen TIME-03 / STATE-02 make the month a planning/version scope, not a correctness boundary. Adjacent context must be sufficient for cross-month REST-01 and LOAD-01 evaluation.

A prior Assignment may matter even when it ends before month start and therefore does NOT overlap the target month. Rolling 7-day load also requires work from days preceding the month boundary.

### Corrected persistence capability

T008 MUST provide a focused CURRENT-version assignment query for boundary assembly with inputs equivalent to:
- `site_id`;
- requested `context_start: datetime`;
- requested `context_end: datetime`;
- optional exclusion of the target ScheduleVersion/month if useful to the repository design.

It returns:
- Assignments belonging to CURRENT ScheduleVersions for the Site;
- non-CANCELLED only;
- whose actual interval overlaps the requested context interval;
- deterministic order;
- no non-current/historical-version leakage.

The repository API need not hardcode planning policy into SQL. T009 will choose the exact assembly window. However T008 tests MUST prove the query is capable of supplying at least all context required around a monthly boundary.

### Mandatory monthly-boundary capability test

For a target month starting at `M0`, query an adjacent interval that begins at least six calendar days before `M0` and prove it returns:
- prior-month assignments within those six preceding days needed for a rolling 7-day LOAD-01 window;
- a prior assignment that ends before `M0` and does not overlap the target month but is close enough to matter to REST-01;
- an overnight prior-month Assignment crossing into the target month.

Symmetrically, the generic interval query must be capable of retrieving current assignments after month end when T009 requests forward adjacent context; T008 must not encode "previous month only" as a storage limitation.

The original statement that cross-month ownership follows Assignment.start_datetime remains unchanged.

Cross-Site assignment query remains interval-based as already specified and must continue to support CURRENT-version context for REST-01/LOAD-01.

### Acceptance correction

Original acceptance item 20 is replaced by:

`Cross-month Assignment ownership uses start time; LocalStore exposes current-version adjacent-interval assignment queries sufficient to assemble REST-01/LOAD-01 boundary context, including non-overlapping prior work and rolling-7-day predecessor work.`

---

## R1-4 — HOLIDAY HISTORY IS CURRENT + REALIZED PRIMARY ONLY

The original `HOLIDAY HISTORY SUPPORT` correctly required current ScheduleVersions and stored CalendarDay facts but failed to constrain history to REALIZED work.

Corrected semantics for the `PlanningState.holiday_history` persistence source:
- CURRENT ScheduleVersions only;
- `Assignment.state == REALIZED` only;
- `Assignment.role == PRIMARY` only;
- Assignment belongs to a stored `CalendarDay` with `holiday == true` according to the accepted holiday-history day semantics already used by Rota;
- deterministic ordering;
- historical/non-current, PLANNED, CANCELLED and TRAINEE assignments do not enter this holiday-history result.

This is historical workload, not future planned holiday load.

T008 still does not maintain a separate per-Employee holiday ledger.

### Test correction

Matrix M3 must prove in one fixture that:
- current REALIZED PRIMARY on holiday is returned;
- current PLANNED PRIMARY on holiday is not returned;
- current CANCELLED PRIMARY on holiday is not returned;
- current REALIZED TRAINEE on holiday is not returned;
- non-current REALIZED PRIMARY on holiday is not returned;
- REALIZED PRIMARY on a non-holiday CalendarDay is not returned.

---

## R1-5 — WORKING STATUS MUST MATCH DEVIATION PRESENCE

The original brief froze FINAL status mapping but left `WORKING` versus `WORKING_WITH_DEVIATIONS` as "as appropriate".

That ambiguity is closed.

For every successfully persisted WORKING snapshot:
- zero persisted Deviations => status MUST be `WORKING`;
- one or more persisted Deviations => status MUST be `WORKING_WITH_DEVIATIONS`.

This applies both to:
- initial ScheduleVersion creation;
- atomic replacement of the current working snapshot.

A caller MUST NOT be able to persist:
- `WORKING` with one or more Deviations;
- `WORKING_WITH_DEVIATIONS` with zero Deviations.

Repository may derive the status from Deviation count or validate an explicitly supplied status; either implementation is acceptable, but incoherent persisted state is not.

Acknowledgement state does not change this working-status rule: a WORKING snapshot containing acknowledged Deviations remains `WORKING_WITH_DEVIATIONS` until finalization.

FINAL mapping remains unchanged:
- zero Deviations => `FINAL_NO_DEVIATIONS`;
- one or more Deviations => `FINAL_WITH_DEVIATIONS`, with all required acknowledgements present.

### Test correction

Add tests proving:
1. create with zero deviations produces/accepts only WORKING;
2. create with deviations produces/accepts only WORKING_WITH_DEVIATIONS;
3. working replacement that removes the last deviation changes status to WORKING atomically;
4. working replacement that adds first deviation changes status to WORKING_WITH_DEVIATIONS atomically;
5. explicit mismatched status/deviation count is rejected if API exposes status input.

---

## UPDATED REQUIRED INTEGRATION SCENARIO DELTAS

The original `VERSION / RESTART / RESTORE` scenario remains required, with these additions:

1. V1 contains at least one Assignment already marked REALIZED before V2 child creation.
2. V2 MUST preserve that REALIZED Assignment exactly under R1-2.
3. V2 also demonstrates a manual split or truthful partial PRIMARY state under R1-1 in a WORKING snapshot.
4. Boundary query after restart is exercised with predecessor work that does not overlap the target month but is inside requested adjacent context, plus six-day predecessor load context.
5. Holiday-history assertion distinguishes current REALIZED PRIMARY from current PLANNED work.
6. At least one working-snapshot replacement changes Deviation count across zero/non-zero and proves matching WORKING status transition.

These additions remain persistence/application-boundary tests. T008 does not implement T009 validation/orchestration.

---

## UPDATED AUDIT FOCUS

Codex re-review must confirm all five findings are closed without reopening unrelated T008 decisions:

1. storage no longer forbids manual split/coverage-gap truth;
2. child creation structurally protects parent REALIZED history;
3. boundary persistence capability is interval-based and sufficient for 7-day/REST adjacent context rather than month-overlap-only;
4. holiday history is current REALIZED PRIMARY only;
5. WORKING status is coherent with persisted Deviation count.

If these are closed and no new material contract gap exists, return `PASS / READY_FOR_IMPLEMENTATION`.
