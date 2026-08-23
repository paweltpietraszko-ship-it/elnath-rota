# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
OWNER_FOLLOW_UP: `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

The owner follow-up is fully consolidated below; there is no separate unresolved frontend/correction contract.

T023b adds exactly two HARD protections to an `OCHRONA` Site:

1. 24h minimum immediate rest after an actual 24h WorkPeriod;
2. 35h uninterrupted rest in every complete seven-day week of the calendar-month settlement period.

No production implementation may start before independent Codex preimplementation PASS on the exact final contract HEAD.

## 1. CLOSED PRODUCT FACTS

The frozen addendum is the semantic authority. Preserve these boundaries:

- `Site` is a planning/service unit, not a physical-object aggregate;
- protection and cleaning at one real location are separate Sites;
- T023b implements protection only; cleaning is not `ORDINARY` by default;
- no T023b aggregation from `state.other_site_assignments` and no inferred external work;
- TRAINEE remains work under frozen T012 REST/LOAD semantics; no training-specific logic;
- weekly windows are only complete 7-day blocks starting on day 1 and wholly inside the month;
- remaining month-end days create no WEEKLY-REST-01 window;
- immediate rest after a concrete 24h duty may cross month end;
- new real Sites receive an explicit regime from their creation flow; no silent ORDINARY creation default;
- ordinary Site editing cannot change regime;
- one deliberate audited regime-correction operation belongs to T023b;
- historical ScheduleVersions and REALIZED Assignments are not rewritten by regime correction;
- existing persisted Sites are test data only, so migration may use `ORDINARY` as compatibility default.

No owner decision remains open.

## 2. SITE REGIME — MINIMAL DATA / WRITE CONTRACT

### Domain

In `rota/domain.py` add:

`SitePlanningRegime = ORDINARY | OCHRONA`

and required:

`Site.planning_regime: SitePlanningRegime`

Do not use a boolean. Do not add CLEANING/SPRZATANIE semantics in this task.

### Schema / repository

Bump LocalStore schema v8 -> v9 and add:

`planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

The SQL default exists only to migrate current test/legacy rows. Every application-created Site supplies the enum explicitly; repository INSERT must write the supplied value rather than rely on the SQL default.

`site_repository` owns the write boundary:

- normal insert/write persists the supplied regime;
- read/list returns `SitePlanningRegime` and fails closed on unsupported stored values;
- normal write of an already-existing Site must reject a regime change before updating other fields;
- add one narrowly named repository primitive used only by the exceptional application correction command to update **only** `planning_regime` in an open transaction.

Do not add a generic regime setter or a second immutability guard in unrelated code.

### Bootstrap / creation

`bootstrap_or_resume_coordinator_context()` keeps the existing Site write path.

Update only its planning-relevant comparison/audit serialization so initial `planning_regime` is included in Site configuration facts.

A missing regime must fail before a new real Site is persisted; `ORDINARY` is never inferred by application code from omission.

### Exceptional correction command

Add one application command in `rota/application/durable_inputs.py`:

`correct_site_planning_regime(conn, *, coordinator_id: str, site_id: str, planning_regime: SitePlanningRegime, note: str | None = None, responds_to_decision_required_id: str | None = None) -> tuple[date, ...]`

Required behaviour:

1. authorize through the existing active coordinator context for `site_id`;
2. load the current Site and no-op without an action if the requested regime already matches;
3. before the write, determine which current schedule months contain at least one non-CANCELLED `PLANNED` Assignment; these are `replan_required_months`;
4. in one transaction: validate any decision-required link, update only the Site regime through the dedicated repository correction primitive, record exactly one existing `CONTEXT_CONFIGURATION_SAVED` action, and invalidate current decision-required pointers for that Site;
5. action before/after state must identify the old/new regime; after-state also records `replan_required_months` as correction impact metadata;
6. return the same ordered `replan_required_months` tuple to the caller;
7. do not create, rewrite, restore, finalize or delete a ScheduleVersion; do not mutate any Assignment;
8. do not add a new CoordinatorActionKind.

The distinctly named command plus the frontend confirmation is the controlled correction path. No generic `set_site_regime`/checkbox path is authorized.

### Existing current plan after correction

Correction is prospective for planning:

- existing ScheduleVersions remain unchanged snapshots;
- REALIZED facts remain unchanged;
- any subsequent PLAN/REPLAN/select/manual-correction/finalize assembles the corrected current Site regime and therefore applies the corrected rules;
- T021 must, after a successful correction, visibly route the coordinator to existing REPLAN for every returned `replan_required_month`; until that replan occurs it must not present the old current plan as a plan produced under the corrected regime.

No new stale-schedule flag, ScheduleVersion regime snapshot, export rewrite or lifecycle state is introduced by T023b.

## 3. T021 FRONTEND BINDING — NO DUPLICATED BACKEND

This task does not implement T021 UI code, but the later frontend is bound to these product rules:

- separate creation entry points/screens for at least OCHRONA and ORDINARY;
- no generic regime checkbox/toggle/dropdown in Site creation;
- the selected entry point supplies the required regime;
- common fields, validation, components and persistence remain shared implementation;
- Site workspace visibly shows its regime;
- ordinary edit has no regime-change control;
- correction is a visibly separate flow with explicit confirmation and calls only `correct_site_planning_regime`;
- cleaning remains a separate future service flow and must not silently map to ORDINARY.

## 4. ONE PURE REST OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of shared arithmetic.

Add only reusable semantics for:

- effective required rest after one resolved WorkPeriod;
- complete settlement-week windows for one calendar month;
- maximum uninterrupted free interval inside one weekly window.

Required semantics:

- exact 24h WorkPeriod + `OCHRONA` => `max(resolved configured rest, 24h)`;
- otherwise configured/resolved rest is unchanged;
- weekly windows exist only when a full 7-day interval fits inside the month;
- weekly free time clips work to the week, merges overlapping/abutting work and measures the largest free gap including both boundaries.

Do not create another legal-rest module or duplicate this arithmetic in application code.

## 5. SOLVER / VALIDATOR

### Existing REST-01

Keep `REST-01` as the only immediate-rest code.

Solver and validator use the shared effective-rest semantics for target-Site WorkPeriods under `OCHRONA`, covering existing T012 forms:

- Catalog H24;
- same-month emergency H12+H12;
- existing cross-month emergency pair provenance.

The next target-Site duty must respect that rest even across month end.

Do not apply the new T023b floor to `state.other_site_assignments`. Existing T012/T022 cross-Site behaviour is retained, not redesigned.

### WEEKLY-REST-01

Add one HARD solver constraint and one independent validator check.

For `OCHRONA`, per employee and complete weekly window, occupied time is only recorded target-Site non-CANCELLED work. PRIMARY and TRAINEE both count. PASS requires at least one uninterrupted free interval of 35h or more.

For `ORDINARY`, skip the new weekly check.

Solver encoding is intentionally not prescribed. It must be logically equivalent to the pure weekly oracle; validator independently re-derives the result from final Assignment facts.

Do not reuse LOAD-01, ISO weeks or rolling seven-day windows. Add no PlanningResult status.

## 6. MANUAL SCHEDULE CORRECTION — REUSE, DO NOT REDESIGN

Keep the current `apply_manual_correction()` transaction and REST override precedent.

Required changes only:

- map `WEEKLY-REST-01` to `DeviationCategory.LAW`;
- extend the existing REST override record so a manual weekly-rest violation is auditable;
- use shared pure week/rest helpers for reconstructed facts; do not create a second weekly audit calculation or parse validator messages;
- one logical child correction still creates at most one existing-style `REST_OVERRIDE_RECORD`.

Minimum weekly facts: employee, week start/end, observed maximum uninterrupted rest, required rest=35h.

For the 24h REST-01 floor retain enough facts to distinguish configured/resolved rest from effective required rest.

Do not add `coordinator_action_id`, another action/table or new hook ordering solely for T023b. Existing atomic manual-correction tests remain the atomicity oracle.

## 7. TASK SCOPE

Production files allowed:

- `rota/domain.py`
- `rota/persistence/db.py`
- `rota/persistence/site_repository.py`
- `rota/application/bootstrap.py`
- `rota/application/durable_inputs.py`
- `rota/planning/work_periods.py`
- `rota/planning/constraints.py`
- `rota/planning/solver.py`
- `rota/planning/validator.py`
- `rota/application/deviation_mapping.py`
- `rota/application/manual_edit.py`

Existing schedule/site-memory APIs may be read/called; no modification is authorized unless audit proves a literal blocker.

Contract/test files:

- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
- `tasks/ROTA-T023b/brief.md`
- `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md` (read-only owner ruling)
- `tests/test_t023b.py`
- `tests/test_local_store_schema_migration.py`

Mechanical compatibility exception: existing tests/fixtures under `tests/` may be edited only to provide explicit `planning_regime=ORDINARY` to pre-T023b Site constructors/imports. Assertions and scenario meaning must not change.

Explicitly out of scope for modification unless independent audit proves a blocker:

- `rota/application/assembler.py`;
- plan/lifecycle/export modules;
- schedule persistence/lifecycle modules;
- site-memory/action-kind modules;
- `rota/planning/eligibility.py`;
- SiteProfile and print-setting semantics;
- training/mentor logic;
- cleaning-service HARD rules or physical-object modeling;
- payroll/HR/night/Sunday/general work-time compliance;
- `arch/spec.md`, `arch/FROZEN.lock` and architect input brief.

## 8. MINIMUM TEST MATRIX

### Regime / correction

T23b-01 — v8 test/legacy row migrates as `ORDINARY`; new explicit OCHRONA round-trips and application creation does not rely on SQL default.

T23b-02 — normal repository Site write rejects regime change while allowed ordinary Site updates still work.

T23b-03 — dedicated correction command changes only regime, uses active-context authorization, writes exactly one existing `CONTEXT_CONFIGURATION_SAVED` before/after audit fact, invalidates decision-required pointers and creates no ScheduleVersion/Assignment mutation.

T23b-04 — correction returns months containing current non-CANCELLED PLANNED work; REALIZED/CANCELLED-only history does not require replan. Same-regime request is a no-op with no action.

T23b-05 — two Sites sharing one SiteProfile may have different regimes without cross-effect; ORDINARY retains pre-T023b REST/LOAD behaviour.

### 24h immediate rest

T23b-10 — Catalog H24 gaps 23h59 / 24h / 24h01 => fail / pass / pass under OCHRONA; configured value >24 remains stronger and persisted provenance is not rewritten.

T23b-11 — emergency H12+H12 gets the same floor, including existing cross-month pair/next target-Site duty.

T23b-12 — new T023b floor does not consume `state.other_site_assignments`.

### Weekly rest

T23b-20 — parameterized month-window oracle proves 31/30/28/leap-February shapes, no cross-month weekly window and tail days excluded.

T23b-21 — maximum uninterrupted rest 34h59 / 35h / 35h01 => fail / pass / pass.

T23b-22 — non-CANCELLED TRAINEE interrupts weekly rest under existing T012 semantics; no training-specific rule appears.

T23b-23 — `state.other_site_assignments` do not enter weekly calculation.

### Integration / manual schedule path

T23b-30 — OCHRONA solver output and independent validator agree for both protections; automatic violating candidate is not accepted.

T23b-31 — explicit manual schedule correction of REST-01 and/or WEEKLY-REST-01 uses LAW deviation + at most one existing REST override record with fact-derived data.

### Negative scope

T23b-40 — no Sunday rule, automatic 24h weekly exception, CLEANING semantics, LOAD-01 reinterpretation, stale-schedule state or ScheduleVersion regime snapshot is introduced.

## 9. RETAINED REGRESSIONS / QUALITY GATES

Run relevant existing regressions instead of duplicating mechanisms:

- T012 REST/emergency/cross-month and TRAINEE REST/LOAD tests;
- T022 cross-Site REST tests;
- existing manual-correction/REST-override and T019b atomic/action tests;
- local-store migration tests;
- full suite;
- Ruff;
- `git diff --check`;
- repository scope/size/function guards with only the explicit mechanical Site-constructor compatibility exception.

Do not rewrite existing regression outcomes merely to make T023b pass.

T023b is one implementation/review unit. No checkpoint split is required.

## 10. PREIMPLEMENTATION AUDIT

Independent Codex must audit the exact final contract HEAD and answer material readiness questions:

1. Can normal repository writes enforce regime immutability while one narrowly scoped correction primitive enables only the dedicated application correction command?
2. Does new-Site creation require an explicit regime despite the migration-only SQL `ORDINARY` default?
3. Is correction auditable and prospective without rewriting ScheduleVersions/REALIZED facts or inventing stale/lifecycle state?
4. Can the command derive `replan_required_months` from existing current-schedule reads without modifying schedule repositories/lifecycle?
5. Does the T021 binding prevent checkbox/default mistakes while sharing common implementation?
6. Do both T012 24h mechanisms receive the same target-Site OCHRONA floor without changing persisted rest provenance or cross-Site semantics?
7. Are weekly windows exactly the frozen complete monthly blocks, with no cross-month/rolling/ISO substitution?
8. Can solver and validator share pure semantics without a prescribed unnecessary solver algorithm?
9. Does manual schedule correction minimally extend existing REST override semantics without a second audit engine or transaction redesign?
10. Does any remaining clause require code or a product scenario not necessary for the frozen owner rulings?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered contract defects tied to exact clauses.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: targeted matrix + retained regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.
