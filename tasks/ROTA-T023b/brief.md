# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

BINDING_OWNER_FOLLOW_UP: `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md`

The owner follow-up was recorded after this draft and requires architect consolidation before CC implementation. Where this brief conflicts with that decision, the owner decision controls.

T023b adds exactly two HARD protections to an `OCHRONA` Site:

1. 24h minimum immediate rest after an actual 24h WorkPeriod;
2. 35h uninterrupted rest in every complete seven-day week of the calendar-month settlement period.

No production implementation may start before independent Codex preimplementation PASS on the exact final contract HEAD.

## 1. CLOSED PRODUCT FACTS

The frozen addendum is the semantic authority. The implementation must preserve these boundaries:

- `Site` is a planning/service unit, not a physical-object aggregate;
- protection and cleaning at one real location are separate Sites;
- T023b implements protection only;
- no T023b aggregation from `state.other_site_assignments` and no inferred external work;
- TRAINEE remains work under existing T012 REST/LOAD semantics; no training-specific logic;
- weekly windows are only complete 7-day blocks starting on day 1 and wholly inside the month;
- remaining month-end days create no WEEKLY-REST-01 window;
- immediate rest after a concrete 24h duty may cross month end;
- Site regime is selected at creation and has no ordinary post-creation edit path;
- existing persisted Sites are test data only, so legacy migration may use `ORDINARY` as compatibility default;
- exceptional correction of a wrongly classified Site is outside T023b.

No owner decision remains open.

## 2. SITE REGIME — MINIMAL DATA CHANGE

### Domain

In `rota/domain.py` add:

`SitePlanningRegime = ORDINARY | OCHRONA`

and required:

`Site.planning_regime: SitePlanningRegime`

Do not use a boolean. Do not add CLEANING/SPRZATANIE semantics in this task.

### Schema / repository

Bump LocalStore schema v8 -> v9 and add:

`planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

The SQL default is only migration compatibility for current test/legacy rows. New `Site` objects carry the enum explicitly.

`site_repository` is the single write-boundary owner of regime immutability:

- insert persists the supplied regime;
- read/list returns `SitePlanningRegime` and rejects unsupported stored values;
- if a Site already exists, a write attempting to change its persisted regime must fail before update;
- ordinary writes changing allowed Site fields continue to work.

Do not add a second regime guard or setter elsewhere. In particular, T023b does not add `set_site_regime`, `set_site_ochrona_mode` or a lifecycle transition workflow.

### Bootstrap

`bootstrap_or_resume_coordinator_context()` continues to use the existing Site write path. Update only its planning-relevant comparison/audit serialization so the initial explicit regime is included in Site configuration facts.

The backend requirement is explicit regime selection plus repository immutability. UI confirmation mechanics remain outside this implementation task.

## 3. ONE PURE REST OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of shared arithmetic.

Add only the reusable semantics needed for:

- effective required rest after one resolved WorkPeriod;
- complete settlement-week windows for one calendar month;
- maximum uninterrupted free interval inside one weekly window.

Required semantics:

- exact 24h WorkPeriod + `OCHRONA` => `max(resolved configured rest, 24h)`;
- otherwise configured/resolved rest is unchanged;
- weekly windows exist only when a full 7-day interval fits inside the month;
- weekly free time clips work to the week, merges overlapping/abutting work and measures the largest free gap including both boundaries.

Do not create another legal-rest module or duplicate this arithmetic in application code.

## 4. SOLVER / VALIDATOR

### Existing REST-01

Keep `REST-01` as the only immediate-rest code.

Solver and validator must apply the shared effective-rest semantics to target-Site WorkPeriods under `OCHRONA`, covering the existing T012 24h shapes:

- Catalog H24;
- same-month emergency H12+H12;
- existing cross-month emergency pair provenance.

The next target-Site duty must respect that rest even across month end.

Do not apply the new T023b floor to `state.other_site_assignments`. Existing T012/T022 cross-Site behaviour is retained, not redesigned.

### WEEKLY-REST-01

Add one HARD solver constraint and one independent validator check.

For `OCHRONA`, per employee and complete weekly window, occupied time is only recorded target-Site non-CANCELLED work. PRIMARY and TRAINEE both count. PASS requires at least one uninterrupted free interval of 35h or more.

For `ORDINARY`, the new weekly check is skipped.

The solver encoding is intentionally not prescribed. It must be logically equivalent to the pure weekly oracle, and the independent validator must re-derive the result from final Assignment facts rather than solver literals.

Do not reuse LOAD-01, ISO weeks or rolling seven-day windows.

No new PlanningResult status.

## 5. MANUAL CORRECTION — REUSE, DO NOT REDESIGN

Keep the current `apply_manual_correction()` transaction and REST override precedent.

Required changes only:

- map `WEEKLY-REST-01` to `DeviationCategory.LAW`;
- extend the existing REST override record so a manual weekly-rest violation is auditable;
- use the shared pure week/rest helpers for any reconstructed facts; do not build a separate weekly audit calculation and do not parse validator messages;
- one logical correction still creates at most one existing-style `REST_OVERRIDE_RECORD`, even if it contains several REST-01/WEEKLY-REST-01 violations.

Minimum weekly fact needed in that existing record:

- employee;
- week start/end;
- observed maximum uninterrupted rest;
- required rest = 35h.

For the 24h REST-01 floor, retain enough fact data to distinguish configured/resolved rest from the effective required rest.

Do not add `coordinator_action_id`, a new action, a new table or a new hook ordering solely for T023b.

Existing atomic manual-correction tests remain the atomicity oracle; T023b does not require a second fault-injection framework when transaction ordering is unchanged.

## 6. TASK SCOPE

Production files allowed:

- `rota/domain.py`
- `rota/persistence/db.py`
- `rota/persistence/site_repository.py`
- `rota/application/bootstrap.py`
- `rota/planning/work_periods.py`
- `rota/planning/constraints.py`
- `rota/planning/solver.py`
- `rota/planning/validator.py`
- `rota/application/deviation_mapping.py`
- `rota/application/manual_edit.py`

Contract/test files:

- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
- `tasks/ROTA-T023b/brief.md`
- `tests/test_t023b.py`
- `tests/test_local_store_schema_migration.py`

Mechanical compatibility exception: existing tests/fixtures under `tests/` may be edited only as needed to provide explicit `planning_regime=ORDINARY` to pre-T023b Site constructors. Such edits may not change assertions or scenario meaning.

No other production modification is authorized unless independent audit proves a literal blocker.

Explicitly out of scope for modification:

- `rota/application/durable_inputs.py` — repository immutability must make a second guard unnecessary;
- `rota/application/assembler.py`;
- plan/lifecycle/export modules;
- `rota/planning/eligibility.py`;
- schedule persistence/lifecycle modules;
- site-memory/action-kind modules;
- SiteProfile and print-setting semantics;
- training/mentor logic;
- cleaning-service HARD rules or physical-object modeling;
- payroll/HR/night/Sunday/general work-time compliance;
- exceptional Site-regime correction workflow;
- `arch/spec.md`, `arch/FROZEN.lock` and the architect input brief.

## 7. MINIMUM TEST MATRIX

The matrix is intentionally limited to distinct product/ownership risks.

### Regime

T23b-01 — v8 test/legacy row migrates to v9 as `ORDINARY`; new explicit `OCHRONA` round-trips through repository.

T23b-02 — repository rejects changing `planning_regime` of an existing Site while ordinary allowed Site updates still work.

T23b-03 — two Sites sharing one SiteProfile may have different regimes without cross-effect; ORDINARY retains pre-T023b REST/LOAD behaviour.

### 24h immediate rest

T23b-10 — Catalog H24 gaps 23h59 / 24h / 24h01 => fail / pass / pass under OCHRONA; configured value >24 remains stronger and persisted provenance is not rewritten.

T23b-11 — emergency H12+H12 gets the same floor, including the existing cross-month pair/next target-Site duty case.

T23b-12 — the new T023b floor does not consume `state.other_site_assignments`.

### Weekly rest

T23b-20 — parameterized month-window oracle proves 31/30/28/leap-February shapes, no cross-month weekly window, and month-end tail days excluded.

T23b-21 — maximum uninterrupted rest 34h59 / 35h / 35h01 => fail / pass / pass.

T23b-22 — non-CANCELLED TRAINEE interrupts weekly rest exactly as existing work; no training-specific rule appears.

T23b-23 — `state.other_site_assignments` do not enter the weekly calculation.

### Integration / manual path

T23b-30 — OCHRONA solver output and independent validator agree for both new protections; an automatic violating candidate is not accepted.

T23b-31 — explicit manual correction of REST-01 and/or WEEKLY-REST-01 uses LAW deviation + at most one existing REST override record with fact-derived rest data.

### Negative scope

T23b-40 — no Sunday rule, automatic 24h weekly exception, CLEANING semantics or LOAD-01 reinterpretation is introduced.

## 8. RETAINED REGRESSIONS / QUALITY GATES

Run relevant existing regressions rather than duplicating their mechanisms:

- T012 REST/emergency/cross-month and TRAINEE REST/LOAD tests;
- T022 cross-Site REST tests;
- existing manual-correction/REST-override and T019b atomic/action tests;
- local-store migration tests;
- full suite;
- Ruff;
- `git diff --check`;
- repository scope/size/function guards with only the explicit mechanical Site-constructor compatibility exception above.

Do not rewrite existing regression outcomes merely to make T023b pass.

T023b is one implementation/review unit. No checkpoint split is required.

## 9. PREIMPLEMENTATION AUDIT

Independent Codex must audit the exact final contract HEAD and answer only material implementation-readiness questions:

1. Can `site_repository` be the single regime-immutability owner without a `durable_inputs` or lifecycle change?
2. Are new Site regime semantics explicit while legacy `ORDINARY` is only test-data migration compatibility?
3. Do both T012 24h mechanisms receive the same target-Site OCHRONA floor without changing persisted rest provenance or cross-Site semantics?
4. Are weekly windows exactly the frozen full-month blocks, with no cross-month/rolling/ISO substitution?
5. Can solver enforce and validator independently verify the same pure weekly/rest semantics without a prescribed unnecessary algorithm?
6. Does manual correction extend the existing REST override minimally, with no second audit engine or transaction redesign?
7. Does any remaining clause require code or a product scenario not necessary for the frozen owner rulings?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered contract defects tied to exact clauses.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: targeted matrix + retained regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.
