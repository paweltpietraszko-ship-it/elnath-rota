# ROTA-T023 — ARCHITECT R3 TIMING INCORPORATION

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-22
TASK_ID: ROTA-T023
PARENT_OWNER_DECISION_COMMIT: 92542647761eb3a7b7aeb02b3d6c36e82b7fcd4e
OWNER_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_ABSENCE_TIMING_PLAN_WYK.md
PREVIOUS_R3_CLARIFICATION: tasks/ROTA-T023/round_01/ARCHITECT_R3_CLARIFICATION.md

## 1. NARROW PRECEDENCE

This document changes only T023-R3-3, T023-R3-5 and their direct PLAN/WYK, provenance, write-boundary and test consequences.

For those points it has precedence over conflicting wording in:
- `tasks/ROTA-T023/round_01/ARCHITECT_R3_CLARIFICATION.md` sections 5, 7, 9, 10 and 12;
- `tasks/ROTA-T023/brief.md` where that brief assumes every granted absence requires a previously adopted Employee schedule;
- `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md` only where it assumes one schedule-reference mechanism also covers approved leave entered before PLAN;
- T023 test rows that expected REALIZED-overlap arithmetic instead of write-time rejection;
- T023 test rows that removed the accepted pre-PLAN 40h T020 leave presentation.

T023-R3-1, R3-2, R3-4 and R3-6 remain closed exactly as in the previous clarification and are not redesigned here.

Round-3 PASS findings remain closed:
- no nominal U/C operational Assignment;
- no payroll/HR scope;
- durable preservation of post-PLAN reference facts;
- N `17:00-05:00` and legal 24h start-date anchoring;
- SICK-over-LEAVE precedence where both valid prospective absence records overlap;
- operational demand is covered only by actually eligible PRIMARY Employees.

## 2. OWNER TIMING MODEL

T023 no longer uses one schedule-reference mechanism for every absence timing case.

There are two supported prospective sources plus one rejected timing class.

### 2.1 PRE_PLAN_LEAVE

Applies to `LEAVE_GRANTED` for an affected date/range for which no accepted PLAN applicable to that date exists when the leave is recorded.

Product behavior:
- the leave is recorded before PLAN;
- solver eligibility excludes the Employee on those leave dates;
- no nominal operational Assignment is created for the absent Employee;
- no prior Employee PLAN is required and the absence MUST NOT become `MISSING` merely because there is no adopted Employee schedule yet;
- T020 uses the existing owner-approved leave presentation path and Site legend/allocation rules;
- the binding owner example remains 40h Monday-Friday leave represented as PLAN `D1 / D1 / N2` and WYK `U1 / U1 / U2` in the accepted 12h Site presentation regime;
- those symbols remain presentation only and cover no ShiftDemand.

The previous T023 statement "empty readable reference schedule = 0 and old 40h synthetic decomposition is gone" does not apply to this PRE_PLAN_LEAVE path.

### 2.2 POST_PLAN_REFERENCE

Applies when a granted absence is recorded prospectively after an accepted PLAN already contains the Employee's planned work for the affected date.

This includes:
- `SICK_LEAVE` learned after PLAN; and
- `LEAVE_GRANTED` requested/approved while PLAN is already in force for future, not-yet-started work.

Product behavior:
- capture and preserve the Employee's pre-REPLAN planned PRIMARY work as the PLAN/reference presentation fact;
- later REPLAN may replace operational coverage with another eligible Employee but MUST NOT erase that preserved PLAN presentation fact;
- T020 prints `C` for SICK or `U` for granted leave under the preserved planned period;
- the preserved PLAN/U/C fact is not operational coverage;
- actual ShiftDemand remains covered by the replacement PRIMARY Employee;
- accepted REPLAN is prospective and does not alter earlier/completed work.

The post-PLAN reference remains the schedule-based T023 source: exact scheduled 8h/12h/N/24h periods, weekend/holiday scheduled work, known rest=0, start-date anchoring and durable post-bind invariance remain unchanged.

### 2.3 RETROACTIVE — REJECTED

An operation that would newly apply `SICK_LEAVE` or `LEAVE_GRANTED` to already completed/past work is invalid and MUST be rejected before it creates a new active absence state.

A REALIZED Assignment remains REALIZED/WYK and is not an accepted absence-accounting conflict state.

T023 therefore has no normal product branch choosing whether REALIZED-overlap hours are counted, excluded or make a balance unavailable. New valid data must not enter that state.

## 3. CURRENT OWNER CLARIFICATION — LEAVE DURING AN ACTIVE PLAN

The owner additionally clarified in the current architect session that leave is usually known before PLAN, but may also be requested for several future days while PLAN is already in force.

Therefore `LEAVE_GRANTED` is timing-sensitive:
- before applicable PLAN -> PRE_PLAN_LEAVE;
- after applicable PLAN, for future not-yet-started work -> POST_PLAN_REFERENCE;
- retroactive over completed/past work -> reject.

Do not infer "LEAVE is always pre-PLAN" from the common workflow.

## 4. ONE CONSUMER-FACING RESULT, TWO AUTHORIZED SOURCES

`rota/planning/absence.py` remains the single consumer-facing absence-accounting owner, but it MUST distinguish source provenance.

This is one public accounting entry point with two authorized source modes, not one universal schedule-reference algorithm.

### PRE_PLAN_LEAVE accounting source

For this mode only, preserve the already accepted pre-T023 canonical leave-total behavior that T020 consumed for the owner-approved 40h example.

The existing T020 owner contract explicitly defined that presentation as consuming the canonical T018 absence-accounting result and then decomposing that exact total through the configured Site legend.

T023 MUST NOT generalize this pre-PLAN fallback to POST_PLAN_REFERENCE.

T023 also MUST NOT silently redesign the legacy pre-PLAN weekday/holiday qualification rules inside this narrow R3 correction. Any future product change to that legacy pre-PLAN arithmetic requires a separate owner decision.

### POST_PLAN_REFERENCE accounting source

Use the bound exact schedule periods from the pre-REPLAN accepted PLAN and the existing schedule-based T023 arithmetic.

No flat 8h/workday fallback is permitted when a POST_PLAN_REFERENCE exists.

### Consumer equality

For either valid source mode, the resulting canonical `absence_hours`, kind and presentation facts feed the same downstream consumers:
- weekly/monthly/quarterly coordinator totals;
- WorkBalance/effective target;
- live solver TARGET/fairness input;
- T020 U/C presentation.

Consumers MUST NOT independently choose PRE_PLAN_LEAVE vs POST_PLAN_REFERENCE.

## 5. WHY THIS TWO-SOURCE SHAPE IS RECOMMENDED

Reason:
- the owner explicitly defined two different timing facts: pre-PLAN approved leave has no prior Employee PLAN, while post-PLAN sickness/late leave does have one and must preserve it.

Problem it solves:
- it prevents a pre-PLAN leave from becoming permanent `MISSING` only because no schedule existed yet;
- it prevents later CURRENT/PLAN creation from retroactively changing that leave into a different accounting mode;
- it preserves the pre-REPLAN PLAN fact for late sickness/leave instead of falling back to synthetic presentation;
- it avoids creating a fake nominal operational Assignment merely to have something to snapshot.

This is not a profile/industry strategy. The branch is selected by timing/provenance of the absence relative to the accepted PLAN.

## 6. DURABLE PROVENANCE MODE

The existing planned `absence_reference_snapshots` persistence remains one table.

Recommended technical shape:
- persist a deterministic `source_mode` in the existing snapshot/provenance JSON for every active `LEAVE_GRANTED` / `SICK_LEAVE` version handled by T023;
- values used by this contract are `PRE_PLAN_LEAVE` and `POST_PLAN_REFERENCE`;
- `POST_PLAN_REFERENCE` stores the already-required immutable schedule-period provenance;
- `PRE_PLAN_LEAVE` stores the mode/provenance needed to prove that the absence was recorded before an applicable PLAN; it does not fabricate Assignment/ShiftDemand rows.

Why this is recommended:
- the timing mode is a historical fact established when the availability version is written and must survive restart, later PLAN creation and REPLAN.

Problem it solves:
- without a durable mode, a read after PLAN creation could reinterpret an old pre-PLAN leave as post-PLAN simply because CURRENT now exists.

No second absence table, workflow engine or nominal Assignment layer is introduced.

## 7. MODE IS DECIDED AT WRITE TIME, NOT READ TIME

For each affected date/block, the Availability write path determines whether an accepted applicable PLAN already exists before any absence-driven REPLAN mutation.

- If `LEAVE_GRANTED` has no applicable accepted PLAN -> PRE_PLAN_LEAVE.
- If `LEAVE_GRANTED` has an applicable accepted PLAN and affected work is still prospective -> POST_PLAN_REFERENCE.
- `SICK_LEAVE` in the supported owner path uses POST_PLAN_REFERENCE.
- SICK must not be silently routed through PRE_PLAN_LEAVE merely because a schedule lookup failed.

If one AvailabilityVersion spans a boundary where some affected dates already have an accepted PLAN and other dates do not, the persisted provenance must be able to represent the source mode per affected date/month block rather than misclassifying the entire range.

Why this per-block capability is recommended:
- T023 already supports cross-month ranges, and one long leave may cross from a currently planned month into a not-yet-planned month.

Problem it solves:
- it avoids forcing a real post-PLAN date through synthetic pre-PLAN accounting or forcing a genuinely pre-PLAN future month into false `MISSING`.

No new user-facing mode selector is authorized.

## 8. R3-3 — MISSING LIFECYCLE IS CLOSED

The prior open R3-3 question is closed by the owner timing decision.

A granted leave entered before PLAN is not a failed schedule capture and does not wait for later CURRENT to "heal" it.

It is durably classified as PRE_PLAN_LEAVE and remains on that authorized path after PLAN is later created.

Therefore:
- no automatic later-CURRENT backfill is needed;
- no permanent `MISSING` is created for the ordinary approved-leave-before-PLAN case;
- BOUND POST_PLAN_REFERENCE schedule facts remain immutable;
- genuine POST_PLAN_REFERENCE capture failure remains fail-closed and cannot become 0h;
- legacy active granted absence with no T023 provenance is still not reconstructed from today's CURRENT.

The former R3-3 owner question is removed from the gate.

## 9. R3-5 — RETROACTIVE REALIZED CONFLICT IS CLOSED BY WRITE REJECTION

The prior open R3-5 arithmetic question is removed.

The canonical product behavior is prevention, not later numerical interpretation.

### 9.1 Canonical command boundary

`rota/application/durable_inputs.py::append_availability` is the current coordinator command that:
- establishes `recorded_at`;
- validates coordinator context;
- opens the atomic transaction;
- appends AvailabilityVersion;
- records `AVAILABILITY_CHANGED` and invalidation.

T023 retroactivity validation belongs on this existing command/write boundary before the new active absence version is persisted.

`rota/persistence/availability_repository.py` remains the append-only chain primitive and must not independently invent coordinator-time policy.

Why this placement is recommended:
- `durable_inputs.append_availability` already owns the atomic coordinator write and already has the effective `recorded_at` timestamp.

Problem it solves:
- it prevents a repository-only clock/policy duplicate and guarantees rejected retroactive input leaves no partial AvailabilityVersion, snapshot or coordinator action.

### 9.2 What must be rejected

For an active new/superseding `SICK_LEAVE` or `LEAVE_GRANTED`, T023 must reject newly introduced absence coverage that is retroactive relative to the command's `recorded_at`/existing schedule truth.

At minimum the guard must reject:
- a new absence family whose requested coverage starts in an already elapsed calendar date;
- newly added coverage over an affected shift that has already started before `recorded_at`;
- newly added coverage over a REALIZED Assignment;
- a range extension/correction that newly introduces any such past/started/REALIZED coverage.

Do not silently clip the coordinator's requested range to future dates. Reject the invalid write so the stored fact equals what the coordinator actually approved.

### 9.3 Same-day future absence remains possible

A leave/L4 entered today for a shift that has not yet started is not retroactive merely because `start_date == recorded_at.date()`.

If an accepted PLAN already contains that future shift, use POST_PLAN_REFERENCE and prospective REPLAN.

Why this distinction is recommended:
- the owner said REPLAN is prospective from acceptance, not "only from tomorrow".

Problem it solves:
- a date-only `start_date <= today` ban would incorrectly reject legitimate same-day future sickness/leave, while a date-only allowance could incorrectly rewrite an already-started same-day shift.

### 9.4 Existing chain history is not re-created by a superseding version

Availability is append-only versioned history. A later version may preserve already-established historical coverage while changing only future dates or metadata.

The retroactivity guard therefore evaluates newly introduced/expanded active coverage, not every historical date repeated in the superseding record.

Why this is recommended:
- otherwise any legitimate absence chain would become impossible to correct/deactivate once its first day passed.

Problem it solves:
- it enforces "do not create new retroactive absence" without making existing append-only history unmaintainable.

Inactive/deactivation operations that remove coverage are not retroactive creation and are not rejected merely because the historical record being deactivated contains past dates.

## 10. REALIZED / WYK CONSEQUENCES

For valid new T023 writes:
- no active absence is created over already completed/REALIZED work;
- REALIZED Assignment remains unchanged;
- no solver/WorkBalance/T020 arithmetic branch is needed to decide whether that same period is simultaneously work and absence;
- no automatic U/C replacement of WYK occurs.

The existing T020 `ASSIGNMENT_ABSENCE_CONFLICT` may remain as a defensive integrity signal for legacy/corrupt/unexpected data, but it is not a normal product state produced by the T023 write path and does not authorize a new arithmetic rule.

Why retaining the defensive signal is recommended:
- T023 cannot guarantee that every historical/pre-migration database is pristine, and deleting an existing integrity check provides no owner benefit.

Problem it solves:
- unexpected legacy inconsistency can still be surfaced without turning it into supported business semantics.

## 11. T020 CONSEQUENCES

T020 now has two absence presentation paths selected by persisted provenance mode.

### PRE_PLAN_LEAVE

- preserve the owner-approved deterministic configured allocation/decomposition behavior;
- binding 40h example remains `D1 / D1 / N2` over `U1 / U1 / U2`;
- no schedule Assignment provenance is fabricated;
- exact-sum/no-rounding/no-invented-legend rules remain;
- the absence symbols do not cover demand.

For PRE_PLAN_LEAVE only, the previous T020 owner fail-closed Site attribution rule remains applicable when there is no schedule provenance capable of allocating the global leave presentation across multiple LOCAL Sites. Do not duplicate the same global pre-PLAN leave total across Sites and do not invent origin-Site ownership.

### POST_PLAN_REFERENCE

- print the preserved planned period in PLAN;
- print matching exact-hour `U` or `C` in WYK under that period;
- Site ownership comes from the bound schedule period;
- multiple memberships alone do not create ambiguity;
- no aggregate monthly coin-change is used for these bound post-PLAN periods.

Why two T020 paths are required:
- the owner explicitly preserved synthetic/configured presentation for leave known before PLAN and explicitly required the earlier PLAN shift to remain visible for sickness/late leave after PLAN.

Problem it solves:
- forcing both through one exporter mechanism would either erase the 40h pre-PLAN owner example or fabricate a pre-PLAN schedule that never existed.

## 12. SOLVER / WORKBALANCE / ANALYTICS CONSEQUENCES

Eligibility remains HARD and timing-independent:
- valid active SICK/LEAVE blocks the absent Employee from operational coverage on covered dates;
- another eligible PRIMARY covers the demand.

Numerical TARGET/WorkBalance/analytics use the canonical absence result from the persisted source mode:
- PRE_PLAN_LEAVE -> preserved canonical pre-PLAN leave total;
- POST_PLAN_REFERENCE -> exact bound schedule-period total.

No consumer may inspect CURRENT and decide its own source mode.

Weekly explicit-range, monthly and quarterly totals use the same mode-specific canonical result and must agree with T020 totals for the same source facts.

## 13. TASK_SCOPE DELTA

Add to T023 TASK_SCOPE:
- `rota/application/durable_inputs.py`

Reason:
- it is the existing atomic coordinator Availability command and already owns `recorded_at`, coordinator context, Availability write and action/invalidation transaction.

Problem solved:
- retroactive rejection can occur before any durable partial state is created without duplicating write policy in persistence.

No other new production module is required by R3-3/R3-5.

The R3-6 scope amendment for `rota/planning/validator.py` remains unchanged.

## 14. TEST MATRIX DELTAS

These deltas supersede only R3-3/R3-5 and directly conflicting old T23 rows.

### Timing / provenance

T23-R3-3A — approved `LEAVE_GRANTED` entered before applicable PLAN is PRE_PLAN_LEAVE, does not become MISSING, solver excludes the Employee, and no nominal Assignment is created.

T23-R3-3B — binding 40h pre-PLAN owner example remains exact T020 PLAN `D1/D1/N2`, WYK `U1/U1/U2`; presentation does not cover demand.

T23-R3-3C — later PLAN creation/restart does not reinterpret that PRE_PLAN_LEAVE as POST_PLAN_REFERENCE.

T23-R3-3D — SICK after accepted PLAN captures the Employee's previous planned period; replacement REPLAN preserves that PLAN fact and T020 writes matching C while another Employee covers demand.

T23-R3-3E — `LEAVE_GRANTED` added while PLAN is active for a future not-yet-started shift follows the same POST_PLAN_REFERENCE preservation/replan path and prints U.

T23-R3-3F — a cross-month leave whose affected blocks straddle an existing-PLAN/no-PLAN boundary preserves the correct source mode per block; no entire-range recapture from later CURRENT.

### Retroactivity

T23-R3-5A — new SICK/LEAVE whose newly introduced coverage is wholly retroactive is rejected atomically: no AvailabilityVersion, no absence provenance row, no coordinator action/invalidation side effect.

T23-R3-5B — same-day absence over an already-started or REALIZED planned shift is rejected; WYK remains unchanged.

T23-R3-5C — same-day absence for a future not-yet-started planned shift is accepted as POST_PLAN_REFERENCE and may trigger prospective REPLAN.

T23-R3-5D — a superseding AvailabilityVersion may preserve previously established historical coverage while changing only future coverage; the guard checks newly introduced retroactive coverage rather than banning the whole chain after time passes.

T23-R3-5E — extension/correction that newly adds past/started/REALIZED coverage is rejected as one write; no silent clipping.

T23-R3-5F — defensive legacy `ASSIGNMENT_ABSENCE_CONFLICT` may still surface inconsistent old data, but new valid T023 write paths cannot create that condition and no REALIZED-overlap absence arithmetic oracle is required.

### Replaced old rows

- old T23-23 `REALIZED-at-bind/current REALIZED overlap -> canonical numerical fail-closed` is withdrawn for new writes and replaced by R3-5A..F.
- old T23-43 `old 40h empty-schedule synthetic allocation is gone` is no longer globally true: it remains gone for POST_PLAN_REFERENCE, but the owner-approved 40h configured decomposition is PRESERVED for PRE_PLAN_LEAVE.
- old T23-47 expected conflict remains only as defensive legacy/integrity coverage; the supported new-write oracle is rejection before the conflicting state is created.

All unrelated T023 arithmetic/anchoring/multi-Site/HARD/no-nominal-assignment tests remain unchanged.

## 15. AUDIT QUESTIONS FOR THE NEXT NARROW ROUND

The next independent Codex preimplementation audit must inspect only R3-1 through R3-6 and the direct consequences of this timing decision.

For R3-3/R3-5 specifically verify:
1. Does pre-PLAN approved leave avoid false MISSING without fabricating a schedule?
2. Is the owner-approved 40h `U1/U1/U2` path preserved only where the owner authorized it?
3. Can a later PLAN/restart accidentally reinterpret PRE_PLAN_LEAVE as POST_PLAN_REFERENCE?
4. Does SICK after PLAN preserve the prior PLAN fact and use replacement operational coverage?
5. Does late `LEAVE_GRANTED` during an active PLAN use the same prospective reference/replan path for future shifts?
6. Can any new active absence be created retroactively over an elapsed/started/REALIZED shift?
7. Can a same-day future unstarted shift still receive a valid prospective absence?
8. Is retroactive rejection atomic at the existing coordinator command boundary?
9. Is no REALIZED-overlap numerical business rule invented?
10. Are R3-1/R3-2/R3-4/R3-6 unchanged except where this owner timing decision necessarily interacts with them?

The next audit MUST NOT reopen the Round-3 PASS findings unless this owner decision creates a direct contradiction.

## 16. DELIVERY MECHANICS

This incorporation is documentation-only.

It adds exactly one file:
`tasks/ROTA-T023/round_01/ARCHITECT_R3_TIMING_INCORPORATION.md`

It does not modify production code, tests, `arch/spec.md`, `arch/FROZEN.lock`, the owner decision, the prior Codex report or the previous architect clarification.

## 17. ARCHITECT OUTPUT STATUS

READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC

R3-3: CLOSED by PRE_PLAN_LEAVE vs POST_PLAN_REFERENCE timing provenance.

R3-5: CLOSED by atomic rejection of newly retroactive absence state; no REALIZED-overlap arithmetic choice remains.
