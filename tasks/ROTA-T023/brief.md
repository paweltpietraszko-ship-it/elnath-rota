# ROTA-T023 — ABSENCE TIMING / HOURS — CONSOLIDATED IMPLEMENTATION CONTRACT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-22
TASK_ID: ROTA-T023
BASE_BRANCH: main
BASE_SHA: e05dfb7dd4463370bf8174db7ae58a9b984cf99e
TASK_BRANCH: task/ROTA-T023
OWNER_SOURCE: arch/T023_absence_hours_architect_brief.md
OWNER_NIGHT_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_NIGHT_SHIFT_ANCHOR.md
OWNER_TIMING_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_ABSENCE_TIMING_PLAN_WYK.md
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
LAST_AUDIT: tasks/ROTA-T023/round_01/tests/tests_r5.txt

CC_GATE: BLOCKED UNTIL INDEPENDENT CODEX PREIMPLEMENTATION PASS ON THIS EXACT CONTRACT SHA

## 1. CONSOLIDATION / PRECEDENCE

This brief and the frozen addendum are the complete architect implementation contract for T023.

Earlier round documents under `tasks/ROTA-T023/round_01/ARCHITECT_R3_*.md` are historical review artifacts. They do not override this consolidated pair.

This consolidation incorporates the already-closed R3-1/R3-2/R3-4/R3-6 corrections and closes only the outstanding R5-1/R5-2/R5-3 findings. It does not reopen Round-3 PASS foundations.

No new product rule may be introduced merely for architectural tidiness. Where this brief recommends an implementation placement, it states why and which concrete failure it prevents.

## 2. PRODUCT MODEL

There is one consumer-facing absence result but two owner-authorized prospective provenance modes plus one rejected class.

### 2.1 PRE_PLAN_LEAVE

`LEAVE_GRANTED` for a date/block with no mechanically accepted applicable PLAN at Availability write time.

- no prior Employee schedule is required;
- absence is not `MISSING` merely because PLAN does not yet exist;
- HARD eligibility excludes the Employee on leave dates;
- no nominal operational Assignment is created;
- preserve the owner-approved pre-PLAN canonical leave-total path and configured T020 exact-sum decomposition;
- binding 40h example remains PLAN `D1 / D1 / N2` and WYK `U1 / U1 / U2`;
- presentation does not cover ShiftDemand.

This is a timing/provenance exception, not a SiteProfile strategy. The pre-PLAN arithmetic must never be used as fallback for a post-PLAN absence.

### 2.2 POST_PLAN_REFERENCE

A prospective `SICK_LEAVE` or `LEAVE_GRANTED` for a date/block where a mechanically accepted applicable PLAN exists at Availability write time.

- preserve the accepted pre-REPLAN Employee PRIMARY plan as immutable PLAN/accounting provenance;
- exact scheduled period hours are the absence-hour source;
- later REPLAN assigns real coverage to another eligible PRIMARY but cannot erase the bound PLAN fact;
- T020 prints C for sickness or U for granted leave below the preserved period;
- preserved PLAN/U/C presentation is not operational coverage.

### 2.3 RETROACTIVE — REJECTED

A new/expanded active absence may not newly cover an Employee PRIMARY work fact that already started or is REALIZED. The invalid write is rejected before AvailabilityVersion/snapshot/action persistence.

A minioną date alone is not retroactivity. A past known rest day contains no started Employee work fact to rewrite.

## 3. R5-1 — MECHANICAL ACCEPTED PLAN PROOF

### 3.1 What is NOT proof

Do not infer acceptance from:
- CURRENT pointer alone;
- `WORKING`, `WORKING_WITH_DEVIATIONS` or FINAL status alone;
- ScheduleVersion existence;
- non-empty Assignment list.

`plan_month()` creates a technical CURRENT WORKING container before the coordinator selects a candidate, so those signals are insufficient.

### 3.2 Existing durable proof

The mechanical acceptance event is the existing `CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED` recorded by `rota/application/plan_ops.py::select_candidate()` in the same successful transaction as the selected snapshot.

For an Availability command timestamp `recorded_at`, a ScheduleVersion is accepted only if a durable `SCHEDULE_CANDIDATE_SELECTED` action:
- names that `schedule_version_id`; and
- has `action.recorded_at <= recorded_at`.

Existing `site_memory.list_coordinator_actions(...)` is sufficient to read this fact. No new acceptance table/event is added.

Why recommended: this is the durable fact already emitted exactly when the coordinator chooses a candidate.

Problem solved: a technical empty WORKING root/child cannot be mistaken for accepted PLAN, while a legitimately selected empty schedule remains mechanically accepted because acceptance does not depend on Assignment count.

### 3.3 Accepted applicable version for a Site/date

Use the current Site/month lineage at the Availability write boundary:
1. start at CURRENT and walk parent links to root using the shared lineage helper in `schedule_repository`;
2. reject cycle/missing-parent/site-month mismatch;
3. require real `effective_from` for a version used on the date;
4. filter to `effective_from <= anchored_date`;
5. filter to versions with the durable candidate-selected proof above;
6. choose the deepest remaining version.

An unselected technical REPLAN child is skipped; its accepted applicable parent remains eligible. If no accepted version exists:
- `LEAVE_GRANTED` uses PRE_PLAN_LEAVE for that date/block;
- supported post-PLAN sickness must not silently fall back to PRE_PLAN_LEAVE; absent required accepted provenance is reference-incomplete.

One AvailabilityVersion may contain different date/month provenance blocks if accepted PLAN exists for only part of its range.

## 4. PERSISTENCE — MIGRATION 8

Advance schema 7 -> 8 and add exactly one production table:

`absence_reference_snapshots`
- `availability_version_id TEXT PRIMARY KEY`;
- `captured_at TEXT NOT NULL`;
- `reference_status TEXT NOT NULL` (`BOUND`, `MISSING`, `AMBIGUOUS`);
- `snapshot_json TEXT NOT NULL`.

Add append-only UPDATE/DELETE rejection triggers. Do not add a current pointer, WorkBalance history table, second Assignment table or second absence ledger.

No migration-time guessed historical backfill.

### 4.1 Deterministic snapshot JSON

The JSON is deterministic and contains at minimum:
- persisted `source_mode` per relevant date/month block: `PRE_PLAN_LEAVE` or `POST_PLAN_REFERENCE`;
- captured Site scope/projection provenance;
- accepted source ScheduleVersion id/action proof where POST_PLAN_REFERENCE applies;
- ordered day/period/component facts;
- source assignment/demand ids and exact start/end intervals for bound post-PLAN periods;
- work-period/template/component provenance needed for legal 24h grouping;
- explicit MISSING/AMBIGUOUS diagnostic when applicable.

Do not persist only a derived flat total as the sole truth. PRE_PLAN_LEAVE may persist the canonical pre-PLAN input/provenance needed to reproduce its authorized total without fabricating Assignments. POST_PLAN_REFERENCE must persist exact period facts because WORKING content can later mutate in place under the same version id.

`WorkBalance` gains non-persisted `absence_hours: int = 0` at the end for positional compatibility.

## 5. AVAILABILITY WRITE BOUNDARY

`rota/application/durable_inputs.py::append_availability` is the canonical coordinator command boundary because it already owns coordinator context, `recorded_at`, the Availability transaction and `AVAILABILITY_CHANGED` action/invalidation.

For active SICK/LEAVE:
1. capture one `recorded_at` for the command;
2. obtain/hold the existing SQLite write transaction boundary;
3. validate retroactivity against newly introduced/expanded coverage;
4. determine source mode/accepted-plan provenance using facts that existed before any absence-driven REPLAN;
5. append AvailabilityVersion;
6. persist its immutable absence-reference provenance in the same transaction;
7. record the existing coordinator action/invalidation in that same transaction.

Any validation/persistence failure rolls the whole write back.

`availability_repository.py` remains the append-only chain primitive and does not independently invent coordinator-time policy.

`AVAILABILITY_CHANGED.schedule_version_id` remains `None`; one absence may span multiple Site/version provenance facts, which belong in the snapshot JSON.

Why this placement is recommended: the command already has the timestamp and atomic mutation boundary.

Problem solved: no partial Availability/snapshot/action and no duplicate clock/policy in persistence.

## 6. R5-2 — RETROACTIVITY GUARD

For a new/superseding active SICK/LEAVE, inspect only coverage newly introduced/expanded by that version.

Reject when newly covered range would include:
- a non-CANCELLED PRIMARY work period for the Employee with `start_datetime < recorded_at`; or
- a REALIZED PRIMARY Assignment for the Employee.

Do not reject solely because `start_date < recorded_at.date()`.

A past date proven by accepted plan to contain no Employee PRIMARY work is allowed and contributes 0h on POST_PLAN_REFERENCE. A past date with incomplete provenance is handled by normal reference-completeness rules, not elapsed-date rejection.

Do not silently clip invalid input to future dates.

A same-day future period may remain prospective if no covered Employee work fact on that date/range has already started; if newly requested date coverage would also cover an earlier started Employee PRIMARY fact, the write is rejected rather than rewriting it.

Inactive/deactivation operations removing coverage are not retroactive creation.

Why recommended: it matches the owner rule at the level of the work fact that must not be rewritten.

Problem solved: L4 may include yesterday's known rest day plus a future planned shift without false rejection merely because yesterday elapsed.

## 7. POST_PLAN REFERENCE CAPTURE

### 7.1 Site scope — R3-1

Reference Site scope is the deterministic union of:
- enabled LOCAL Site memberships; and
- Sites on which the Employee has actual non-CANCELLED PRIMARY work in the accepted effective schedule facts.

An EXTERNAL_SUPPORT membership alone never adds a required Site and cannot create MISSING. Real accepted external-site PRIMARY work enters the Employee-global reference once.

### 7.2 Accepted readable day

A POST_PLAN_REFERENCE day is BOUND only if the accepted selected schedule facts can prove the Employee's PRIMARY plan/rest.

Coverage completeness must reuse the canonical coverage algorithm from `planning.validator`; structural Assignment/Demand checks stay with existing schedule validation; 24h grouping/legality reuses `planning.work_periods`.

A BOUND accepted day with zero Employee PRIMARY periods is known 0h.

TRAINEE is not counted as PRIMARY and does not itself make the day ambiguous.

Contradictory/overlapping Employee PRIMARY periods are ambiguous. Disjoint periods may sum exact duration.

### 7.3 Same-chain / overlap invariance

Bound post-PLAN facts are immutable across same Availability chain correction/extension, later WORKING replacement, REPLAN, FINAL, restore, restart and CURRENT movement.

A later sickness overlapping already-bound leave must reuse compatible original facts; disagreement between bound candidates is ambiguous rather than choosing today's CURRENT.

## 8. POST_PLAN CANONICAL ARITHMETIC

`rota/planning/absence.py` is pure/persistence-free and remains the single accounting/precedence owner.

For POST_PLAN_REFERENCE:
- 8h period -> 8h;
- 12h D/N -> 12h;
- legal persisted 24h WorkPeriod -> 24h once;
- scheduled weekend/holiday -> scheduled hours;
- accepted known rest -> 0h;
- no weekday/nonholiday filter;
- missing/ambiguous accepted reference -> explicit failure, never guessed 0/8/12/24.

N `17:00-05:00` belongs wholly to start date. Owner examples remain binding. Legal 24h uses the same start-date anchor including cross-month/year.

SICK wins overlap with LEAVE_GRANTED; count once and present C. LEAVE_PLAN contributes no actual absence hours.

The canonical API supports explicit inclusive date-range projection for weekly totals and month/Site projections. T023 does not invent a separate weekly arithmetic or week-boundary convention.

## 9. PRE_PLAN_LEAVE CANONICAL PATH

For PRE_PLAN_LEAVE only, preserve the previously owner-approved canonical leave-total behavior consumed by T020 before an Employee PLAN exists. Do not silently redesign its legacy weekday/holiday qualification inside T023 timing consolidation.

The binding 40h owner example remains an oracle.

No post-PLAN consumer may use this source as fallback when accepted schedule provenance is missing.

## 10. R5-3 — REPLAN ACCEPTANCE CUTOVER

Owner rule: accepted REPLAN applies prospectively from coordinator acceptance; earlier work facts remain unchanged.

### 10.1 Mechanical cutover timestamp

For candidate selection on a REPLAN child (`header.parent_version_id != None`), `select_candidate()` captures one `cutover_at` immediately before the final cutover-preservation check and snapshot replacement. The successful `SCHEDULE_CANDIDATE_SELECTED.recorded_at` MUST use that same timestamp.

`ScheduleVersion.effective_from` is date-only and is not used as the sub-day cutover proof.

### 10.2 Required preservation invariant

Inside the existing atomic `replace_working_snapshot(pre_check=...)` selection boundary, compare the candidate with the current REPLAN-child snapshot cloned from the previous schedule.

Require exact set preservation of every non-CANCELLED PRIMARY Assignment whose `start_datetime < cutover_at`:
- no removal;
- no employee/interval/demand/role/state/frozen/work-period/operational-code mutation;
- no newly added replacement PRIMARY starting before cutover.

The candidate and current child snapshot already share the child `schedule_version_id`; comparison does not need a new cross-version identity model.

This is a selection-time lifecycle invariant. Do not add it as a solver HARD constraint merely to make generated candidates pretty: the solver may propose redistribution, but selection cannot commit a candidate that rewrites pre-cutover work.

Why this location is recommended: only `select_candidate()` has both the real acceptance timestamp and the exact snapshot about to be committed.

Problem solved: earlier PLANNED non-frozen PRIMARY shifts cannot be redistributed as collateral damage of a future-absence REPLAN.

No new ScheduleVersion timestamp/effective-from model is introduced.

## 11. WORKBALANCE / ANALYTICS / SOLVER

Canonical result for the persisted source mode feeds every consumer.

`compute_month_balance`:
- planned/realized PRIMARY work sums remain operational facts;
- sets `WorkBalance.absence_hours`;
- `effective_target = max(0, target_hours - absence_hours)`;
- month/quarter balances continue from that effective target.

Analytics exposes the same absence/effective-target values and keeps Employee-global ALL_SITES semantics. Explicit weekly range uses the same canonical API. Quarter reads do not return guessed partial numeric results when required provenance is incomplete.

Solver consumes `WorkBalance.absence_hours`; it does not recount Availability, CalendarDay or source mode. SICK and granted leave reduce live TARGET through the same canonical result. TARGET stays SOFT; HARD eligibility remains authoritative.

## 12. T020 PRESENTATION

T020 never creates operational Assignments.

PRE_PLAN_LEAVE:
- retain deterministic configured exact-sum allocation/decomposition;
- preserve 40h `D1/D1/N2` + `U1/U1/U2`;
- no rounding/invented legend;
- where no schedule provenance exists to allocate one global pre-PLAN leave across multiple LOCAL Sites, preserve the existing fail-closed Site-attribution boundary rather than duplicate the global total.

POST_PLAN_REFERENCE:
- place PLAN at exact preserved period anchor;
- WYK U/C has equal exact hours;
- Site ownership comes from bound period provenance;
- multiple memberships alone are not ambiguity;
- no aggregate monthly coin-change relocation.

SICK+LEAVE overlap prints one C. Existing real-work/24h presentation behavior unrelated to absence stays unchanged.

The existing `ASSIGNMENT_ABSENCE_CONFLICT` may remain only as defensive detection for legacy/corrupt data; T023 valid writes must prevent creating that state.

## 13. VALIDATION OWNERSHIP — R3-6

`absence_reference_repository.py` owns deterministic encode/decode, immutable snapshot persistence/batch reads and provenance assembly only. It must not implement its own COVERAGE-01, Assignment/Demand, trainee/mentor or 24h legality algorithms.

Implementation may refactor the existing private coverage calculation in `rota/planning/validator.py` into a reusable pure helper; the main validator and T023 capture must call the same helper.

T023 calls existing `rota/planning/work_periods.py` functions for grouping/24h semantics without modifying that module unless a concrete compile/test/audit finding proves a callable gap.

Why recommended: one existing invariant has one code owner.

Problem solved: no validator drift between planning and absence capture.

## 14. NO LEGACY BACKFILL

Migration 8 does not synthesize provenance for pre-T023 active AvailabilityVersions from today's CURRENT. Such legacy records without T023 provenance are reference-incomplete until a separately authorized remediation exists.

## 15. EXACT TASK_SCOPE

TASK_SCOPE:
- arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
- tasks/ROTA-T023/brief.md
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/absence_reference_repository.py
- rota/persistence/availability_repository.py
- rota/persistence/schedule_repository.py
- rota/planning/absence.py
- rota/planning/solver.py
- rota/planning/engine.py
- rota/planning/validator.py
- rota/balance.py
- rota/persistence/work_balance_repository.py
- rota/application/analytics_read.py
- rota/application/balance_read.py
- rota/application/schedule_export.py
- rota/application/plan_ops.py
- rota/application/durable_inputs.py
- tests/test_t023.py
- tests/test_t018.py
- tests/test_sick_leave.py
- tests/test_balance.py
- tests/test_t019.py
- tests/test_t020.py
- tests/test_t019b.py
- tests/test_t012.py
- tests/test_audit_r20_r21_findings.py
- tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py
- tests/test_t011_a_application_entry_points.py
- tests/test_audit_t009_r6.py
- tests/test_t023_checkpoint_b.py

Owner-authorized narrow amendment (2026-08-22, Checkpoint B own test matrix):
tests/test_t023_checkpoint_b.py is a new file, in scope ONLY for T23-30..34,
T23-R5-3A..F and T23-50..54 (brief.md section 17). Checkpoint A tests in
tests/test_t023.py must not be moved, removed or duplicated here. T23-35
("T020 totals equal canonical source-mode projection") is explicitly
DEFERRED TO CHECKPOINT C per section 16 (schedule_export.py is Checkpoint
C's own allowed production subset and is not yet rewired) -- not tested in
Checkpoint B, not a Checkpoint B gap or FAIL. This is a one-time,
exact-SHA exception to backend.py's global MAX_NEW_FILES=2: the mechanical
gate is expected to report NEW_FILES: 3 new files (max 2) for this task,
and that specific finding is pre-accepted by the owner for this SHA --
backend.py's global constant is unchanged.

Owner-authorized narrow amendment (2026-08-22, Round 8 A-R8-1 fallout):
tests/test_t011_a_application_entry_points.py is in scope only for
test_8_availability_history_returns_full_chain_in_order -- fixture-only
CalendarDay seeding, no change to the tested Availability chain or its
assertions.

Owner-authorized narrow amendment (2026-08-22, Checkpoint B R5-3 fallout):
tests/test_audit_t009_r6.py is in scope only for the "trainee" parametrization
of test_r6_replan_candidate_with_fixed_facts_can_be_selected. Its month
(2026-08, already elapsed relative to real wall-clock capture of
select_candidate's cutover_at) puts every shift in that month before
cutover_at, so the new R5-3 guard blocks the solver's ordinary
redistribution of a non-fixed PRIMARY it was never meant to protect there.
Allowed change: move only this parametrization's scenario to a deterministic
future month, and shift its manual-correction/REPLAN effective_from
accordingly, so the guard is not spuriously triggered by wall-clock elapse.
Must keep TRAINEE creation, the real solver, selecting its candidate, and the
existing absence of CandidateRejected. No change to frozen/realized
parametrizations, assertions, or any other test in the file.

NEW_FILES relative to task base:
- arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
- tasks/ROTA-T023/brief.md
- rota/persistence/absence_reference_repository.py
- tests/test_t023.py

Explicitly OUT OF SCOPE for modification unless a concrete implementation/audit finding requires an architect scope amendment:
- arch/spec.md
- arch/FROZEN.lock
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/work_periods.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/site_memory.py
- rota/site_memory_types.py
- SiteProfile absence strategy/configuration
- T020 legend/settings schema
- payroll/HR modules

Reading/calling existing out-of-scope APIs is allowed; modifying them is not.

## 16. CHECKPOINT ORDER

### A — provenance + write-time timing core
Allowed production subset: domain, db, absence_reference_repository, availability_repository, schedule_repository, durable_inputs, planning.absence, planning.validator, targeted tests.

Must prove migration/immutability/atomicity, accepted-plan action proof, PRE_PLAN vs POST_PLAN provenance, R5-2 work-fact retro guard, shared coverage owner, reference invariance and canonical core.

### B — WorkBalance + solver + analytics + REPLAN cutover
Allowed production subset: balance, work_balance_repository, solver, engine, analytics_read, balance_read, plan_ops, related tests.

Must prove consumer equality, both SICK/LEAVE target adjustment, weekly/month/quarter consistency and R5-3 selection cutover preservation.

### C — T020 + regression closure
Allowed production subset: schedule_export plus related T020/T018/regression tests.

Must prove both presentation paths, one C, Site attribution/no duplication, no nominal coverage, no invented legend and unchanged real-work/T012 behavior.

No intermediate checkpoint is merged to main.

## 17. REQUIRED TEST MATRIX

### Persistence / timing provenance
T23-01 — v7->v8 preserves data and adds exactly `absence_reference_snapshots`.
T23-02 — snapshot UPDATE/DELETE rejected; deterministic restart round-trip.
T23-03 — AvailabilityVersion + provenance + coordinator action are atomic; forced failure leaves no partial write.
T23-04 — `AVAILABILITY_CHANGED.schedule_version_id` remains None; snapshot carries multi-version provenance.
T23-05 — POST_PLAN bound facts survive in-place WORKING replacement under same version id.
T23-06 — bind -> replacement REPLAN -> finalize -> restart preserves post-PLAN reference.
T23-07 — restore/current movement after bind does not change bound hours.
T23-08 — same Availability chain preserves already-bound blocks; new blocks use authorized timing provenance.
T23-09 — later SICK overlapping bound leave reuses compatible original facts; disagreement is ambiguous.

### R5-1 accepted PLAN
T23-R5-1A — `plan_month()` technical CURRENT WORKING before `select_candidate()` is NOT accepted PLAN.
T23-R5-1B — successful `SCHEDULE_CANDIDATE_SELECTED` is accepted proof even if selected schedule has zero Employee periods / valid empty schedule.
T23-R5-1C — unselected REPLAN child does not hide an accepted applicable parent.
T23-R5-1D — acceptance action after Availability `recorded_at` cannot be used retroactively to choose POST_PLAN_REFERENCE.
T23-R5-1E — leave before accepted PLAN -> PRE_PLAN_LEAVE; same future leave after accepted PLAN -> POST_PLAN_REFERENCE.

### PRE_PLAN_LEAVE
T23-PRE-01 — binding 40h leave preserves exact `D1/D1/N2` + `U1/U1/U2` presentation and no demand coverage.
T23-PRE-02 — later PLAN creation does not reclassify persisted PRE_PLAN_LEAVE.
T23-PRE-03 — PRE_PLAN source is never used as fallback for missing POST_PLAN_REFERENCE.

### POST_PLAN arithmetic
T23-10 — scheduled 8h -> 8.
T23-11 — 12h D/N -> 12.
T23-12 — Mar1 17:00-Mar2 05:00 + absence starts Mar2 -> 0 for that shift.
T23-13 — same N + absence includes Mar1 -> full 12 on Mar1.
T23-14 — legal persisted 24h -> 24 once on start date.
T23-15 — 24h cross-month/year -> once, no double count.
T23-16 — accepted readable rest -> 0.
T23-17 — scheduled weekend/holiday -> scheduled hours unchanged.
T23-18 — missing/ambiguous accepted reference -> explicit failure, never guessed 0/8.
T23-19 — LEAVE_PLAN -> 0 actual absence.
T23-20 — SICK+LEAVE -> one SICK/C period, no double hours.
T23-21 — disjoint same-day PRIMARY periods sum exact; contradictory overlap ambiguous.
T23-22 — valid TRAINEE does not change PRIMARY absence hours and is not an extra period.

### R5-2 retroactivity
T23-R5-2A — requested range begins yesterday on accepted known rest and includes future shift: write accepted; rest contributes 0.
T23-R5-2B — new coverage over PRIMARY with start before command `recorded_at` is rejected atomically even if Assignment still PLANNED.
T23-R5-2C — new coverage over REALIZED PRIMARY rejected atomically; REALIZED remains WYK.
T23-R5-2D — elapsed calendar date alone with no started Employee work fact is not rejection reason.
T23-R5-2E — range extension rejects only when newly introduced coverage adds started/REALIZED work; deactivation/removal is not retroactive creation.

### Multi-Site / weekly
T23-24 — actual accepted schedules on A+B -> global A+B once.
T23-25 — Site projection contains only that Site's bound post-PLAN periods.
T23-26 — dormant EXTERNAL_SUPPORT membership cannot create MISSING.
T23-27 — actual external-support Site PRIMARY reference work enters global total once.
T23-28 — explicit seven-day caller range equals sum of canonical anchored facts; month partition reproduces monthly total.

### Consumer equality
T23-30 — WorkBalance.absence_hours equals canonical result; effective target target-absence.
T23-31 — equal canonical SICK/LEAVE results reduce live solver TARGET equally.
T23-32 — solver consumes WorkBalance field; no CalendarDay/flat recount/source-mode choice.
T23-33 — analytics absence/effective target equal WorkBalance.
T23-34 — quarter uses same month results and does not guess around incomplete required provenance.
T23-35 — T020 totals equal canonical source-mode projection.

### R5-3 REPLAN cutover
T23-R5-3A — REPLAN candidate may change future PRIMARY starting at/after cutover.
T23-R5-3B — candidate removing an existing non-CANCELLED PRIMARY started before cutover is rejected.
T23-R5-3C — candidate changing employee/interval/demand/state/frozen/work-period/code of pre-cutover PRIMARY is rejected.
T23-R5-3D — candidate adding a replacement PRIMARY starting before cutover is rejected.
T23-R5-3E — the same timestamp is used for cutover validation and successful `SCHEDULE_CANDIDATE_SELECTED.recorded_at`.
T23-R5-3F — ordinary initial PLAN candidate selection is not subjected to REPLAN-child cutover preservation.

### T020
T23-40 — POST_PLAN 12h D/N appears on exact anchored PLAN date with equal U/C WYK.
T23-41 — POST_PLAN legal 24h prints once when existing equal-hour U/C code exists.
T23-42 — POST_PLAN accepted rest produces no synthetic U/C.
T23-43 — PRE_PLAN 40h owner allocation remains valid; POST_PLAN does not use that coin-change path.
T23-44 — exact unrepresentable post-PLAN period returns presentation problem; no invented code.
T23-45 — SICK+LEAVE prints C only.
T23-46 — multiple LOCAL memberships alone do not make POST_PLAN reference ambiguous; PRE_PLAN without Site provenance keeps existing fail-closed attribution.
T23-47 — defensive legacy work/absence conflict leaves actual work untouched and surfaces integrity problem.

### HARD / regressions
T23-50 — valid SICK remains HARD unavailable across inclusive range.
T23-51 — valid LEAVE_GRANTED remains HARD unavailable; outside range eligible.
T23-52 — absent Employee never covers ShiftDemand; replacement eligible PRIMARY covers it or normal DECISION_REQUIRED remains.
T23-53 — CalendarDay no longer changes POST_PLAN absence hours but unrelated calendar rules unchanged.
T23-54 — T012 normal/emergency 24h legality/rest semantics unchanged.
T23-55 — shared coverage helper is used by validator and T023 capture; no duplicate coverage algorithm in persistence.

## 18. DELIBERATE SUPERSESSION / PRESERVATION

Historical docs/tests are not rewritten merely for cleanliness. Only these meanings change:

- T018 flat weekday/nonholiday arithmetic is no longer universal. It may remain only as the preserved PRE_PLAN_LEAVE source; sickness/post-PLAN leave tests that assert flat-8 regardless of accepted schedule are superseded.
- T018 HARD SICK/LEAVE blocking and DAY_ONLY behavior remain preserved.
- `tests/test_sick_leave.py` SICK flat-8 target oracle and "LEAVE does not reduce live TARGET" are superseded for POST_PLAN canonical behavior; HARD/outside/replan eligibility meaning remains.
- `tests/test_balance.py` flat-8 granted-leave expectation is superseded except where an explicit PRE_PLAN_LEAVE fixture intentionally exercises the preserved pre-PLAN source.
- T019 CalendarDay-specific absence degradation and weekend/holiday flat-workday oracles are superseded by source-mode/provenance semantics; unrelated analytics/current/restore/cross-Site behavior remains.
- T020 owner decision that U/C is presentation only, row population, exact legend/fail-closed and real-work lineage remain preserved.
- `test_t20_14_frozen_40h_leave_decomposition` is PRESERVED for PRE_PLAN_LEAVE and must not be deleted as an obsolete synthetic example.
- `test_t20_19_overlapping_leave_and_sick_conflict` is superseded by SICK/C precedence.
- old multi-LOCAL ambiguity is superseded for POST_PLAN_REFERENCE, but PRE_PLAN_LEAVE without schedule Site provenance preserves the existing fail-closed attribution rather than duplicating global hours.
- Schema literal expectations move latest 7 -> 8 and add exactly `absence_reference_snapshots`; migration-7 T020 settings behavior remains.
- R21-1 and old task-level R23 flat workday assertions are superseded only where they claim the flat rule is universal.

No unrelated oracle may be weakened to make implementation pass.

## 19. PREIMPLEMENTATION AUDIT — NEXT ROUND ONLY R5-1..R5-3

The next independent Codex audit must inspect this exact consolidated HEAD and answer only:

R5-1:
- Is `SCHEDULE_CANDIDATE_SELECTED` the sole mechanical accepted-PLAN proof?
- Can a technical unselected root/child be mistaken for accepted?
- Can an unselected child hide its accepted applicable parent?

R5-2:
- Is elapsed date alone NOT a rejection reason?
- Are newly covered started/REALIZED PRIMARY facts rejected atomically?
- Does known past rest remain allowed/0 without weakening provenance checks?

R5-3:
- Is successful REPLAN candidate acceptance cut over at the exact candidate-selection timestamp?
- Can any non-CANCELLED PRIMARY started before cutover be removed/changed/replaced/added by the accepted candidate?
- Is the check placed on the existing selection/write boundary without inventing a new version system?

R3-1/R3-2/R3-4/R3-6 and Round-3 PASS foundations are not to be reopened unless an R5 finding directly proves a contradiction.

Required verdict:
`PASS — READY_FOR_IMPLEMENTATION`
or concrete R5-1..R5-3 findings.

Until PASS: `NOT READY FOR CC`.

## 20. IMPLEMENTATION / FINAL GATES

After preimplementation PASS:
1. CC implements only current checkpoint scope.
2. Targeted checkpoint tests pass.
3. Architect reviews exact checkpoint SHA/diff.
4. After C: full suite, Ruff/repository guards, `git diff --check`, size/function guards.
5. Independent Codex implementation audit on exact final SHA.
6. Architect final acceptance.
7. Merge remains explicit owner action.

## 21. ARCHITECT OUTPUT STATUS

READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
