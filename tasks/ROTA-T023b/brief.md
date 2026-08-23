# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`

T023b adds exactly two automatic HARD protections for Sites explicitly switched to ochrona mode: a 24h immediate-rest floor after an actual 24h WorkPeriod, and 35h uninterrupted weekly rest in statutory weeks anchored to the calendar-month settlement period.

No implementation may start before independent Codex preimplementation PASS on the exact contract HEAD.

## 1. CONTROLLING FACTS / DECISIONS

Source input: `arch/T023b_ochrona_rest_rules_architect_brief.md`.

Binding decisions already closed before this contract:
- Site has an explicit ochrona/ordinary mode switch;
- new protections are HARD for automatic planning;
- manual override is allowed only through explicit audited manual correction;
- O1: automatic weekly floor is always 35h; no inferred 24h art.133 §2 exception;
- O2: Sunday placement is out of T023b;
- O3: settlement period is the calendar month; statutory week is seven days from settlement-period day 1.

Verified current architecture reused by T023b:
- `work_periods.py` already owns pure REST-01/work-period semantics for solver + validator;
- normal H24 and emergency H12+H12 both resolve into WorkPeriods;
- `assemble_planning_state()` already reads employee cross-Site/cross-month current context through unbounded interval APIs;
- `manual_edit.apply_manual_correction()` already materializes HARD deviations and writes one atomic derived REST override DecisionRecord in the ScheduleVersion transaction;
- T019b requires one material coordinator command -> exactly one coordinator-action row.

No owner decision is open at contract freeze.

## 2. NAMED INVARIANTS

### SITE-MODE-01 — per-Site legal mode

`Site.ochrona_mode` is the only T023b mode input.

- ordinary (`False`) preserves pre-T023b behaviour;
- ochrona (`True`) enables REST-24H-01 semantics through REST-01 and WEEKLY-REST-01;
- SiteProfile sharing cannot propagate the mode;
- print `base_regime` is unrelated.

### REST-24H-01 — ochrona effective REST-01 floor

This is not a new validator code. It is the ochrona-mode effective requirement inside existing `REST-01`:

`effective_rest = max(configured_resolved_rest, 24h)` iff earlier WorkPeriod duration is exactly 24h and target Site is ochrona; otherwise existing rest applies.

The floor is dynamic and is never written back into configured/snapshotted rest provenance.

### WEEKLY-REST-01 — statutory-week uninterrupted rest

In ochrona mode, each relevant employee/statutory-week pair must contain at least 35h uninterrupted work-free time.

- statutory week = exactly seven consecutive days;
- settlement-month anchor = calendar day 1 at 00:00;
- starts repeat every 7 days while the start is still inside that settlement month;
- final week may cross month/year;
- no ISO week / rolling-window substitution;
- no automatic 24h shortening;
- no Sunday-placement rule.

### REST-CROSS-CONTEXT-01 — employee-wide facts

When the target Site is ochrona, target assignments plus boundary and other-Site assignments for the same employee form one rest context. History participates once a target interval makes an edge/week relevant.

Ordinary target Site does not activate T023b checks.

### REST-TARGET-TOUCH-01 — no historical-only blocking

T023b does not reject a target run solely because unrelated history already violates a new rule.

- REST-01 keeps its existing target-touching edge semantics;
- WEEKLY-REST-01 is evaluated only for a statutory week touched by at least one target-version work interval;
- solver activation is conditional on a fixed target interval or selected target slot touching the week.

### REST-OVERRIDE-01 — one manual exception record

A manual correction may persist REST-01/WEEKLY-REST-01 violations only through the existing deviation + `REST_OVERRIDE_RECORD` mechanism.

One logical manual correction -> one material coordinator action + at most one REST override DecisionRecord containing all rest violation facts, atomically with the child ScheduleVersion.

## 3. SITE MODE DATA CONTRACT

### Domain

Append to `Site`:

`ochrona_mode: bool = False`

Default preserves source/test compatibility and ordinary-mode migration behaviour.

### Schema

Bump `LATEST_SCHEMA_VERSION` 8 -> 9.

Migration 9:

`ALTER TABLE sites ADD COLUMN ochrona_mode INTEGER NOT NULL DEFAULT 0 CHECK (ochrona_mode IN (0,1))`

Migration must be transactional under the existing migration runner. No new table.

### Repository

`site_repository.write_site_in_open_transaction`, `get_site`, `list_sites` read/write the field.

### Creation path

`bootstrap_or_resume_coordinator_context()` persists the supplied Site mode. Existing `CONTEXT_CONFIGURATION_SAVED` before/after Site state includes the field. Existing Sites or caller-created `Site(...)` without explicit mode remain ordinary.

### Edit path

Add public application command:

`set_site_ochrona_mode(conn, *, coordinator_id: str, site_id: str, ochrona_mode: bool, note: str | None = None, responds_to_decision_required_id: str | None = None) -> None`

Requirements:
- active coordinator context required;
- no-op write produces no action;
- changed write uses same transaction for Site row, current-question invalidation and exactly one `CONTEXT_CONFIGURATION_SAVED` action;
- affected Sites = target Site only;
- action state is only the changed mode fact;
- all current DECISION_REQUIRED months for that Site are invalidated;
- no ScheduleVersion is created.

`update_site()` must reject a changed `ochrona_mode` and name `set_site_ochrona_mode` as the supported edit boundary. Existing active/name semantics remain unchanged.

No new CoordinatorActionKind is authorized.

## 4. PURE OWNER / WORK-PERIOD CONTRACT

`rota/planning/work_periods.py` owns the semantics. It remains pure, OR-Tools-free and persistence-free.

Required reusable operations (names are suggested; CC may choose equivalent names only if semantics stay literal):

### `effective_required_rest_hours(period, *, ochrona_mode)`

- starts from already-resolved `WorkPeriod.required_rest_after_hours`;
- exact 24h duration + ochrona -> max(current,24);
- otherwise unchanged.

### `statutory_week_windows(settlement_month)`

Returns ordered half-open `[start,end)` seven-day windows with starts `month_start + 7*n` while start < next-month start.

### `relevant_statutory_week_windows(target_intervals)`

- derive earliest target-start month;
- include prior calendar settlement month;
- include settlement months through latest target-end month;
- generate statutory windows;
- retain windows that overlap at least one target interval.

No target intervals -> no relevant weekly check.

### `maximum_uninterrupted_rest_hours(work_intervals, week_start, week_end)`

- clip work intervals to week;
- merge overlapping/abutting occupied intervals;
- return maximum free gap including window boundaries;
- exact elapsed-time arithmetic, no rounding.

Pure helpers must be directly testable at 23h59/24h/24h01 and 34h59/35h/35h01 boundaries independent of FULL_HOUR integration constraints.

## 5. SOLVER CONTRACT

### Existing REST-01

`constraints.py` must use the pure effective-rest requirement for every relevant WorkPeriod comparison when `state.site.ochrona_mode` is true.

Both existing 24h paths are mandatory:
- normal H24 grouped period;
- same-month selected emergency pair merged period;
- cross-month emergency pair resolved from boundary + current half.

No solver path may compare a selected 24h period using a lower 0/11/23 configured rest in ochrona mode.

Ordinary mode must execute current behaviour.

### WEEKLY-REST-01

Add one CP-SAT builder in `constraints.py`, wired once from `solver.solve()`.

For each employee/relevant week:
- fixed occupied intervals: fixed target + boundary + other-Site non-CANCELLED assignments;
- prospective occupied intervals: that employee's target solver slots;
- all roles in fixed work count; prospective solver slots are PRIMARY because solver creates PRIMARY only.

Complete witness construction:
1. candidate 35h rest-window starts are statutory week start plus end times of all fixed/prospective intervals overlapping that week;
2. discard starts whose 35h window exceeds statutory week end;
3. discard candidate rest windows overlapped by fixed work;
4. for each remaining candidate, a Boolean witness may be true only if all overlapping selected slot vars are false;
5. define target-touch activation: fixed target work touching week OR OR(selected target slot vars touching week);
6. when activated, require at least one rest witness.

No LOAD-01 variable/window can satisfy WEEKLY-REST-01.

### Outcome semantics

Do not add a new PlanningResult status.

- solver never emits a candidate that violates a T023b HARD;
- validator never accepts such candidate;
- candidate selection rejects it;
- if legal constraints make the model infeasible, existing Frozen Execution Contract infeasibility diagnosis remains unchanged.

This is not permission to persist a violating automatic candidate as DECISION_REQUIRED.

## 6. INDEPENDENT VALIDATOR CONTRACT

`validator.validate()` must independently re-derive the rules from final Assignment facts.

### REST-01

Use the shared `effective_required_rest_hours(..., ochrona_mode=state.site.ochrona_mode)` logic. Do not parse demand labels to infer 24h. Resolved WorkPeriod duration owns the floor.

### WEEKLY-REST-01

For target Site ordinary: skip.

For target Site ochrona:
- target intervals = non-CANCELLED target Assignments;
- relevant weeks = pure owner calculation from target intervals;
- work intervals = non-CANCELLED target + boundary + other-Site Assignments for same employee;
- calculate exact maximum uninterrupted free interval;
- `<35h` -> one `ViolationDetail(rule="WEEKLY-REST-01", ...)` per employee/week;
- `assignment_ids` contains deterministic target Assignment ids touching that week so downstream deviation materialization has a target fact;
- message is display-only; downstream logic must not parse it.

No Sunday-placement check.

## 7. TEMPORAL DATA WINDOW CONTRACT

Persistence read shape stays unchanged.

`assemble_planning_state()` currently reads current same-Site boundary and other-Site assignments using the existing unbounded context window. T023b reuses it.

The logical minimum needed by T023b is the union of relevant statutory windows, from earliest relevant `week_start` through latest relevant `week_end`.

Do not:
- add a new weekly-rest repository read API;
- narrow `_context_window()` to a guessed fixed margin;
- read only current month;
- ignore cross-month work-period halves or other-Site assignments.

Checkpoint audits must explicitly verify that no T023b implementation change to assembler/query ownership was needed. If implementation proves a literal missing fact, stop and return an architect finding before expanding scope.

## 8. MANUAL OVERRIDE CONTRACT

`apply_manual_correction()` remains the only supported explicit override path.

### Deviations

Add static mapping:

`WEEKLY-REST-01 -> DeviationCategory.LAW`

Existing `REST-01 -> LAW` stays.

### Reconstructable facts

Generalize current `_rest_override_pairs` / `_rest_override_rule_content` plumbing to derive structured facts for both rule families without parsing messages.

REST-01 fact minimum:
- employee id;
- earlier/later assignment identity including ScheduleVersion scope;
- actual gap;
- configured/resolved rest;
- effective required rest;
- earlier period duration;
- `ochrona_24h_floor_applied` bool.

WEEKLY fact minimum:
- employee id;
- statutory `week_start/week_end`;
- observed maximum uninterrupted rest;
- required 35h;
- all work assignment identities overlapping the week;
- target assignment identities that make it relevant.

### One derived record

If either rule family is violated, write one:
- category `CONFIRMED_EXCEPTION`;
- enforcement `INFORMATIONAL`;
- resolution `RESOLVED`;
- rule kind `REST_OVERRIDE_RECORD`;
- rule id `REST-OVERRIDE:<child_id>`.

Structured top-level payload includes `child_version_id`, `coordinator_action_id`, ordered `violations`.

### Atomic ordering

Refactor the existing composed success hook so the same `create_schedule_version` transaction:
1. writes the one material coordinator action and obtains its returned action id;
2. writes the derived REST override record using that action id;
3. performs existing caller-specific success effects.

No second coordinator action is created for the derived record. `record_decision_no_commit` stays the transaction-neutral persistence primitive.

Fault at any step -> no child schedule, no action, no override.

## 9. DELIBERATE PRESERVATION / SUPERSESSION

Preserved:
- ordinary REST-01 configured rest semantics;
- REST_MIN_HOURS legacy fallback where it already applies;
- T012 normal H24 and emergency 24h pairing shape/eligibility/provenance;
- T022 cross-Site zero-gap / illegal continuous H12+H12 rules;
- LOAD-01 rolling-7d threshold and DECISION_REQUIRED meaning;
- SiteProfile sharing semantics;
- T019b one-action rule and stable action-kind catalog;
- current ScheduleVersion/versioning semantics;
- T023/T026 absence accounting;
- T020 print settings and `base_regime`;
- all ordinary Sites after migration.

Superseded/narrowly extended:
- only in target ochrona mode, an exact 24h WorkPeriod's effective REST-01 requirement may no longer be lower than 24h;
- a new independent `WEEKLY-REST-01` HARD applies in target ochrona mode.

No existing test asserting `required_rest_after_hours=11` after a 24h duty is universally sufficient may remain an oracle for ochrona mode. It remains valid for ordinary mode.

No existing rolling-7d LOAD-01 test may be rewritten to claim it proves weekly uninterrupted rest.

## 10. TASK SCOPE

TASK_SCOPE:
- arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md
- tasks/ROTA-T023b/brief.md
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/application/bootstrap.py
- rota/application/durable_inputs.py
- rota/planning/work_periods.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/application/deviation_mapping.py
- rota/application/manual_edit.py
- tests/test_t023b.py
- tests/test_local_store_schema_migration.py

CC may modify only production/test files in this list. Architect contract files may receive only mechanical audit/backend formatting corrections that do not change semantics; semantic contract changes return to architect.

Reading/calling existing out-of-scope APIs is allowed.

## 11. EXPLICIT OUT OF SCOPE MODIFICATION

Do not modify unless an independent audit proves a literal blocking defect:
- `arch/spec.md`;
- `arch/FROZEN.lock`;
- `arch/T023b_ochrona_rest_rules_architect_brief.md`;
- `rota/application/assembler.py`;
- `rota/application/plan_ops.py`;
- `rota/application/lifecycle_ops.py`;
- `rota/application/schedule_export.py`;
- `rota/planning/eligibility.py`;
- `rota/persistence/schedule_repository.py`;
- `rota/persistence/schedule_lifecycle.py`;
- `rota/persistence/site_memory.py`;
- `rota/site_memory_types.py`;
- T023/T026 absence provenance/accounting modules;
- SitePrintSettings/base_regime;
- SiteProfile schema for the legal mode;
- UI visual design/T021 layouts;
- payroll/HR/legal-entitlement modules;
- night-work, Sunday-placement, average weekly/monthly work-time rules.

## 12. CHECKPOINT ORDER

T023b is reviewed in three implementation checkpoints. No intermediate merge to main.

### Checkpoint A — mode + canonical semantics + validator

Allowed functional files:
- `rota/domain.py`
- `rota/persistence/db.py`
- `rota/persistence/site_repository.py`
- `rota/application/bootstrap.py`
- `rota/application/durable_inputs.py`
- `rota/planning/work_periods.py`
- `rota/planning/validator.py`
- `rota/application/deviation_mapping.py`
- tests in TASK_SCOPE.

Closure:
- v9 migration/default ordinary;
- per-Site write/audit boundary;
- pure 24h effective-rest and statutory-week helpers;
- validator REST-01/weekly enforcement;
- ordinary compatibility.

### Checkpoint B — solver parity

Allowed additional functional files:
- `rota/planning/constraints.py`
- `rota/planning/solver.py`
- tests in TASK_SCOPE.

Closure:
- normal/emergency/cross-month 24h floor in CP-SAT;
- WEEKLY-REST-01 witness encoding;
- target-touch conditionality;
- solver/validator sibling parity.

### Checkpoint C — manual override + atomic audit

Allowed additional functional file:
- `rota/application/manual_edit.py`
- tests in TASK_SCOPE.

Closure:
- LAW deviation mapping already present from A;
- one generalized REST override record;
- direct coordinator-action linkage;
- atomicity/no duplicate;
- full retained regression.

After each checkpoint: targeted tests + architect exact-SHA review + independent Codex implementation audit before moving to next checkpoint. Final full suite/audit only after C.

## 13. REQUIRED ADVERSARIAL TEST MATRIX

### Site mode / migration

T23b-01 — v8->v9 preserves data; every existing Site reads `ochrona_mode=False`.
T23b-02 — new Site ordinary/ochrona round-trips through repository/restart.
T23b-03 — two Sites sharing one profile may have different modes without cross-change.
T23b-04 — bootstrap action captures selected initial mode.
T23b-05 — `set_site_ochrona_mode` changed write is atomic, one CONTEXT_CONFIGURATION_SAVED action, no ScheduleVersion, invalidates current questions.
T23b-06 — no-op mode write creates no action.
T23b-07 — `update_site` cannot alter mode indirectly.

### 24h immediate rest / REST-01

T23b-10 — pure helper: exact 24h period + 23h59 gap fails; 24h passes; 24h01 passes.
T23b-11 — Catalog H24 in ochrona has effective min 24 despite configured 0/11/23.
T23b-12 — configured 30h after H24 remains 30h, not lowered to 24.
T23b-13 — same Catalog H24 facts in ordinary mode retain configured rest.
T23b-14 — same-month emergency H12+H12 uses identical floor after pair selection.
T23b-15 — cross-month emergency pair uses identical floor against next-month duty.
T23b-16 — employee's next duty on another Site participates in ochrona REST-01.
T23b-17 — non-24h 12h/16h/other valid period is not raised to 24 by T023b.
T23b-18 — persisted required_rest_after_hours remains configured provenance; toggling ochrona off restores configured behaviour.

### Statutory weekly rest

T23b-20 — pure helper: 34h59 max gap fails; 35h passes; 35h01 passes.
T23b-21 — month day 1 is anchor regardless of weekday; ISO Monday gives a deliberately different result and is not used.
T23b-22 — final week starting late in month crosses into next month/year correctly.
T23b-23 — prior settlement month's trailing week is evaluated when current target work overlaps it.
T23b-24 — current target overnight work into next month activates next month's first statutory week.
T23b-25 — next-month first week with no target overlap does not block current run on history alone.
T23b-26 — cross-Site work reduces same Employee's maximum uninterrupted rest.
T23b-27 — overlapping/abutting work intervals merge before free-gap measurement.
T23b-28 — CANCELLED work does not consume weekly rest; TRAINEE work does.
T23b-29 — automatic 24h weekly-rest shortening is never inferred; 24h max rest fails WEEKLY-REST-01.
T23b-30 — no Sunday-placement check is present; changing weekday/Sunday location alone cannot create T023b violation when uninterrupted duration is identical.

### Solver / validator parity

T23b-40 — solver cannot select normal-H24 + next duty at 23h gap in ochrona; validator reports REST-01 for equivalent persisted candidate.
T23b-41 — same-month emergency pair sibling parity.
T23b-42 — cross-month emergency sibling parity.
T23b-43 — weekly 34h case blocked by solver and reported by independent validator.
T23b-44 — weekly exactly 35h feasible/pass.
T23b-45 — ordinary versions of T23b-40..44 reproduce pre-T023b behaviour.
T23b-46 — history-only weekly violation with no target touch does not make solver/validator fail.
T23b-47 — violating hand-built candidate passed to select_candidate is rejected.
T23b-48 — no T023b HARD is represented as a soft penalty or LOAD-01 threshold.

### Manual override / audit

T23b-50 — manual correction may persist REST-01 24h-floor violation with LAW deviation + one REST_OVERRIDE_RECORD.
T23b-51 — manual correction may persist WEEKLY-REST-01 violation with LAW deviation + one REST_OVERRIDE_RECORD.
T23b-52 — one correction violating both creates one material coordinator action and one combined override record.
T23b-53 — weekly record includes employee/week/observed max rest/35h + target/work assignment identities + coordinator_action_id.
T23b-54 — 24h record includes actual gap/configured rest/effective rest/period duration/floor-applied + coordinator_action_id.
T23b-55 — record facts are reconstructed from assignments/pure semantics, never parsed from ViolationDetail.message.
T23b-56 — injected coordinator-action failure rolls back child/deviations/override.
T23b-57 — injected override-decision failure rolls back child/deviations/action.
T23b-58 — repeated internal hook composition cannot create duplicate override record for one correction.

### Retained regressions

T23b-60 — T012 normal H24/rest matrix remains green in ordinary mode.
T23b-61 — T012 emergency same/cross-month pairing matrix remains green in ordinary mode.
T23b-62 — T022 cross-Site zero-gap/continuous-pair matrix remains green.
T23b-63 — T019b one-action semantics remain green.
T23b-64 — T023/T026 absence and T020 export regressions remain green.
T23b-65 — full configured suite, Ruff, frozen/scope guards, size/function guards and `git diff --check` pass subject only to pre-existing owner-accepted exceptions.

## 14. REQUIRED RETAINED TEST FILES TO RUN UNMODIFIED

At minimum run, without weakening their unrelated oracles:
- `tests/test_t012.py`;
- `tests/test_t022_planning_integrity.py`;
- `tests/test_t019b.py`;
- `tests/test_local_store_integration_scenarios.py`;
- `tests/test_local_store_master_data.py`;
- `tests/test_local_store_schedule_version_lifecycle.py`;
- `tests/test_t023.py`;
- `tests/test_t023_checkpoint_b.py`;
- `tests/test_t023_checkpoint_c.py`;
- `tests/test_t026.py`;
- `tests/test_t020.py`;
- full configured `tests/` collection.

If an existing retained test contradicts the explicit ochrona-only extension, supersede only that exact meaning and add its ordinary-mode sibling. Do not relax unrelated HARD oracles.

## 15. PREIMPLEMENTATION AUDIT — REQUIRED QUESTIONS

Audit exact contract HEAD. Do not implement.

### A. Site mode / compatibility

1. Is mode unambiguously per Site and default ordinary on migration?
2. Does the proposed write path preserve T019b one-action semantics and avoid a new action kind?
3. Can shared SiteProfile or print settings accidentally switch legal mode? Required answer: no.

### B. Immediate 24h rest

4. Does extending existing REST-01 through resolved WorkPeriod duration cover Catalog H24 + same-month emergency + cross-month emergency?
5. Is configured rest provenance preserved rather than rewritten to 24?
6. Is ordinary mode unchanged?

### C. Weekly rest / temporal scope

7. Does the week definition exactly follow calendar-month day-1 + successive seven-day windows, including cross-month/year final weeks?
8. Does the relevance rule catch previous-month trailing and next-month-first-week target overlap without blocking on unrelated history?
9. Is employee work from other Sites included from existing assembler context?
10. Does the solver witness construction encode existence of a continuous 35h gap rather than hours-worked/LOAD-01?
11. Does validator independently re-derive the same rule without trusting solver literals?

### D. Manual override

12. Are both rule families LAW deviations under manual correction only?
13. Is there exactly one material coordinator action and at most one combined REST override record per logical correction?
14. Does the record carry direct coordinator_action_id plus reconstructable facts?
15. Does one transaction roll back schedule/action/override together?

### E. Scope

16. Are O1/O2/O3 preserved with no new legal interpretation?
17. Are Sunday/night/payroll/general work-time compliance and LOAD-01 redesign still out of scope?
18. Is there any required modification outside TASK_SCOPE? If yes, name the literal contradiction; do not widen scope speculatively.

Required verdict:

`PASS — READY_FOR_IMPLEMENTATION_A`

or concrete numbered contract findings.

Until PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

## 16. IMPLEMENTATION / FINAL GATES

After preimplementation PASS:
1. CC implements Checkpoint A only.
2. targeted A matrix passes.
3. architect reviews exact A SHA/diff.
4. independent Codex implementation audit PASS for A.
5. repeat for B, then C; no intermediate merge.
6. after C run full configured suite, Ruff, repository guards and `git diff --check`.
7. independent Codex final implementation audit on exact final product SHA.
8. architect final acceptance on exact product SHA + audit delivery HEAD.
9. merge remains explicit owner action.

## 17. ARCHITECT OUTPUT STATUS

READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
