# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

T023b implements exactly two new HARD protections for a protection-service Site:

1. at least 24h immediate rest after an actual 24h WorkPeriod;
2. at least 35h uninterrupted rest in each complete seven-day week of the calendar-month settlement period.

No production implementation may start before independent Codex preimplementation PASS on the exact final contract HEAD.

## 1. CONTROLLING PRODUCT FACTS

The following are closed owner decisions:

- `Site` is one planning/service unit, not a unique physical object;
- one real-world location may therefore have separate Sites, e.g. protection and cleaning;
- those Sites have independent schedules, memberships and HARD semantics even if the same coordinator manages both;
- T023b concerns protection only; cleaning HARD rules are a separate task;
- T023b does not aggregate work from other Sites and does not infer unobserved/external work;
- TRAINEE remains work exactly under frozen T012 REST/LOAD semantics; no new training logic;
- settlement period = calendar month;
- WEEKLY-REST-01 uses only complete seven-day blocks starting at day 1; the final 0-3 days are tail days and do not form another week;
- no weekly window crosses into the next month;
- immediate rest after a concrete 24h duty may cross month end;
- Site regime is selected at creation and is normally immutable;
- ordinary Site editing cannot change the regime;
- correcting a mistaken initial classification is a separate exceptional product operation outside T023b;
- currently persisted Sites are test data only, so migration requires no real-world reclassification workflow.

No owner decision remains open for this task.

## 2. NAMED INVARIANTS

### SITE-REGIME-01 — explicit planning/service regime

Add:

`SitePlanningRegime = ORDINARY | OCHRONA`

and required Site field:

`planning_regime: SitePlanningRegime`

This is deliberately an enum, not a boolean. `False = ORDINARY` is not a valid long-term domain model because other service regimes exist conceptually. T023b implements no cleaning enum value or cleaning semantics.

- `ORDINARY` preserves pre-T023b behaviour;
- `OCHRONA` enables the two T023b protections;
- regime belongs to Site, not SiteProfile and not print settings;
- Site regime has no normal post-creation edit path.

### REST-24H-01 — effective floor inside existing REST-01

This is not a new validator code.

For a resolved target-Site WorkPeriod `P`:

`effective_rest = max(configured_resolved_rest, 24h)` iff:

- `state.site.planning_regime == OCHRONA`, and
- `P` lasts exactly 24h.

Otherwise existing configured/resolved rest applies.

Do not rewrite persisted rest provenance.

### WEEKLY-REST-01 — complete settlement-week rest

For OCHRONA, every complete seven-day week wholly inside `state.month` must contain at least 35h uninterrupted target-Site work-free time for each employee with recorded target-Site work in that week.

- exact elapsed time;
- no ISO week;
- no rolling-window substitution;
- no Sunday placement;
- no automatic 24h shortening;
- PRIMARY and TRAINEE both count as work;
- CANCELLED does not count;
- `state.other_site_assignments` do not count.

### TAIL-DAYS-01

Days left after the final complete seven-day block are outside WEEKLY-REST-01.

They may still participate in REST-01 and in immediate rest after a concrete 24h duty.

### REGIME-IMMUTABLE-01

After Site creation, ordinary application editing cannot change `planning_regime`.

T023b adds no setter/toggle command for regime change. A future exceptional correction flow must have its own contract and is not implemented here.

### REST-OVERRIDE-01

Automatic planning never persists a violating candidate.

An explicit manual schedule correction may persist REST-01/WEEKLY-REST-01 deviations only through the existing atomic REST override precedent, producing at most one `REST_OVERRIDE_RECORD` for one logical child correction.

## 3. DOMAIN / SCHEMA / SITE WRITE CONTRACT

### Domain

In `rota/domain.py`:

- add `SitePlanningRegime(str, Enum)` with exactly `ORDINARY`, `OCHRONA`;
- add required `Site.planning_regime: SitePlanningRegime` with **no product default**.

Existing test constructors must be updated explicitly. Do not hide the choice behind `False`, `None` or an implicit application default.

### Schema v9

In `rota/persistence/db.py`:

`ALTER TABLE sites ADD COLUMN planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

The schema default exists only because every currently persisted Site is test/legacy data. It is a migration compatibility value, not the product's new-Site selection rule.

No `UNCLASSIFIED`, no heuristic backfill, no new table.

### Repository

`site_repository` must:

- persist the supplied regime explicitly on writes;
- return `SitePlanningRegime` on reads/lists;
- fail closed on unsupported stored values.

### Creation/bootstrap

`bootstrap_or_resume_coordinator_context()` keeps the existing Site object write boundary.

Required changes:

- a newly created Site carries an explicit required `planning_regime`;
- `_planning_fields(Site)` includes regime;
- `_site_state(Site)` includes regime;
- existing `CONTEXT_CONFIGURATION_SAVED` therefore records the initial regime as planning-relevant configuration;
- no new CoordinatorActionKind.

### Ordinary edit

`durable_inputs.update_site()` keeps existing name/active behaviour but must reject any attempted `planning_regime` change.

Do not add:

- `set_site_ochrona_mode`;
- `set_site_regime`;
- generic regime-transition command;
- lifecycle handling for a routine regime toggle.

There is no routine regime toggle in this product contract.

## 4. PURE REST OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of shared WorkPeriod/rest calculations.

Add only pure equivalents of:

### `effective_required_rest_hours(period, *, planning_regime)`

- starts from resolved WorkPeriod rest;
- exact 24h + OCHRONA => max(current, 24h);
- otherwise unchanged.

### `complete_settlement_week_windows(month)`

For `[month_start, next_month_start)` return ordered windows:

`[month_start + 7*n days, month_start + 7*(n+1) days)`

only while window end `<= next_month_start`.

No partial final window.

### `maximum_uninterrupted_rest_hours(work_intervals, week_start, week_end)`

- clip intervals to week;
- merge overlapping/abutting occupied time;
- measure free gaps including both week boundaries;
- return exact maximum free duration.

Do not create another legal-rest module or duplicate the arithmetic in manual/application code.

## 5. IMMEDIATE 24H REST — SOLVER + VALIDATOR

Existing `REST-01` remains the only immediate-rest code.

The effective floor applies to target-Site resolved WorkPeriods under OCHRONA and must cover the existing T012 shapes:

- normal Catalog H24;
- same-month emergency H12+H12 selected as one WorkPeriod;
- cross-month emergency H12+H12 represented by existing work-period provenance.

The next recorded target-Site duty must respect the effective rest even across month end.

Do not apply the new floor to `state.other_site_assignments`. Preserve existing T012/T022 cross-Site REST semantics exactly as they are.

Malformed WorkPeriod provenance remains handled by existing structural rules; T023b does not create alternative grouping semantics.

## 6. WEEKLY-REST-01 — SOLVER

Wire one new HARD weekly-rest builder in `constraints.py`, called from the existing solver only for OCHRONA.

For one employee/full week, occupied time is target-Site work only:

- fixed target assignments from the existing target/fixed context;
- same-Site boundary assignments that overlap the week;
- prospective selected target solver slots.

Do not use `state.other_site_assignments`.

Non-CANCELLED TRAINEE fixed work counts as occupied time under existing T012 semantics. No training branch is added.

The CP-SAT constraint must be equivalent to the pure 35h oracle. A valid simple encoding may enumerate candidate 35h rest windows starting at:

- `week_start`;
- end times of fixed/prospective target-Site work in that week;

and require at least one such window with no fixed/selected overlap.

Equivalent implementation is allowed if audit can prove parity with the pure oracle.

No LOAD-01 variable or rolling window may satisfy WEEKLY-REST-01.

## 7. INDEPENDENT VALIDATOR

`validator.validate()` independently re-derives both T023b rules from final facts.

### REST-01

For target-Site WorkPeriod edges use the shared effective-rest helper. Do not infer 24h from a label alone.

### WEEKLY-REST-01

For ORDINARY: skip.

For OCHRONA:

- generate every complete week wholly inside `state.month`;
- work = non-CANCELLED target candidate/current Assignments + same-Site boundary Assignments overlapping the week;
- exclude `state.other_site_assignments`;
- PRIMARY and TRAINEE both occupy time;
- `<35h` maximum uninterrupted free time emits `ViolationDetail(rule="WEEKLY-REST-01", ...)`;
- structured assignment ids identify target-Site Assignment facts; downstream must not parse message text.

Tail days create no weekly check.

Existing candidate-selection/revalidation/finalization callers inherit validator semantics; do not copy WEEKLY-REST-01 into those application modules.

## 8. MANUAL CORRECTION

Keep the existing `apply_manual_correction()` transaction and REST override precedent.

Required T023b changes:

- `WEEKLY-REST-01 -> DeviationCategory.LAW`;
- `REST-01 -> LAW` unchanged;
- generalize existing rest-override fact reconstruction for WEEKLY-REST-01;
- one logical child correction with any REST-01/WEEKLY-REST-01 deviations creates at most one existing-style `REST_OVERRIDE_RECORD`.

Minimum weekly structured facts:

- employee id;
- full-week start/end;
- observed maximum uninterrupted rest;
- required = 35h;
- target-Site Assignment identities overlapping the week.

For a 24h REST-01 exception record:

- actual gap;
- configured/resolved rest;
- effective required rest.

Do not add `coordinator_action_id`, another action, another override table or reordered action semantics solely for T023b.

## 9. TASK SCOPE

Functional production scope:

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

Contract/test scope:

- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
- `tasks/ROTA-T023b/brief.md`
- `tests/test_t023b.py`
- `tests/test_local_store_schema_migration.py`

Mechanical compatibility exception:

- existing tests/fixtures anywhere under `tests/` may be changed **only** to add explicit `planning_regime=SitePlanningRegime.ORDINARY` to pre-T023b Site constructors/imports;
- such mechanical edits may not change assertions, expected outcomes, fixture meaning or any other product semantic;
- OCHRONA may be used outside `tests/test_t023b.py` only where an existing retained regression deliberately needs an OCHRONA Site to prove parity/integration.

No other production modification is authorized absent a concrete independent-audit finding proving a blocker.

Explicitly out of scope for modification:

- `arch/spec.md`, `arch/FROZEN.lock`;
- architect input brief;
- `rota/application/assembler.py`;
- lifecycle/plan/export modules;
- `rota/planning/eligibility.py`;
- schedule persistence/lifecycle modules;
- site-memory/action-kind modules;
- T023/T026 absence modules;
- SiteProfile schema/semantics;
- SitePrintSettings/base_regime;
- training/mentor logic;
- UI visual design;
- cleaning-service model/HARD rules;
- physical-object/address aggregation;
- payroll/HR/night/Sunday/general work-time compliance;
- exceptional correction of an erroneous Site regime.

## 10. REQUIRED TEST MATRIX

### Site regime / migration

T23b-01 — v8 existing test rows migrate to v9 as `ORDINARY`.

T23b-02 — new persisted Site has explicit `planning_regime`; unsupported stored values fail closed.

T23b-03 — two Sites sharing one SiteProfile can have different regimes without cross-effect.

T23b-04 — `update_site()` rejects regime change while preserving its current supported edits.

T23b-05 — no public normal regime-change command exists.

T23b-06 — ORDINARY preserves pre-T023b REST/LOAD results for equivalent facts.

### Immediate 24h rest

T23b-10 — Catalog H24 pure gaps 23h59 / 24h / 24h01 => fail / pass / pass under OCHRONA.

T23b-11 — same-month emergency H12+H12 has the same effective floor.

T23b-12 — configured rest 0/11/23 cannot lower OCHRONA floor below 24h; configured value >24 remains stronger.

T23b-13 — cross-month emergency/24h duty still enforces immediate rest against next recorded target-Site duty in M+1.

T23b-14 — persisted configured rest provenance is unchanged by the OCHRONA floor.

T23b-15 — T023b does not apply its new 24h floor to `state.other_site_assignments`.

### Complete weekly windows

T23b-20 — 31-day month => exactly 1-7, 8-14, 15-21, 22-28; days 29-31 are tail days.

T23b-21 — 30-day month => four full weeks + two tail days; 28-day month => exactly four weeks; leap February => four weeks + one tail day.

T23b-22 — no weekly window crosses into the next month; next month starts its own sequence on day 1.

T23b-23 — maximum uninterrupted rest 34h59 / 35h / 35h01 => fail / pass / pass.

T23b-24 — non-CANCELLED TRAINEE interrupts weekly rest exactly as recorded work, with no training-specific rule/result.

T23b-25 — work only in tail days does not create WEEKLY-REST-01 solely because of those tail days.

T23b-26 — `state.other_site_assignments` do not enter weekly calculation; no surrogate external work is created.

### Parity / manual override

T23b-30 — solver does not return an OCHRONA candidate that independent validator rejects for either T023b rule.

T23b-31 — manual correction with 24h REST-01 violation persists LAW deviation + existing atomic REST override with reconstructable effective-rest facts.

T23b-32 — manual correction with WEEKLY-REST-01 violation uses the same single-record override precedent with week/rest facts.

T23b-33 — one correction with multiple rest violations creates no duplicate REST override record.

T23b-34 — fault in existing atomic success path leaves no partial child/deviation/override write.

### Negative scope

T23b-40 — no Sunday-placement rule.

T23b-41 — no automatic 24h weekly-rest exception.

T23b-42 — LOAD-01 remains existing rolling-7d decision-threshold behaviour.

T23b-43 — existing T012 TRAINEE and T012/T022 cross-Site regressions remain unchanged.

T23b-44 — no CLEANING/SPRZATANIE regime, disabled-person HARD rule, physical-object aggregate or regime-correction workflow appears in T023b implementation.

## 11. RETAINED REGRESSIONS / QUALITY GATES

Run at minimum:

- `tests/test_t012.py`;
- existing T012 emergency/cross-month tests;
- existing training tests covering TRAINEE REST/LOAD;
- T022 cross-Site REST regressions;
- T019b coordinator action/audit regressions;
- local-store migration tests;
- full suite;
- Ruff;
- `git diff --check`;
- repository size/function/scope guards, with only already accepted inherited exceptions plus the explicit mechanical Site-constructor compatibility exception above.

Do not rewrite an existing oracle merely to make T023b pass.

## 12. IMPLEMENTATION UNIT

T023b is one implementation/review unit. No A/B/C split is required.

Expected shape:

1. one required Site regime enum/field + v9 migration/repository round-trip;
2. bootstrap audit inclusion + immutable ordinary edit guard;
3. small pure additions in `work_periods.py`;
4. existing REST-01 target-Site effective floor for actual 24h periods;
5. one WEEKLY-REST-01 solver builder + independent validator check;
6. one deviation-map entry + minimal generalization of existing REST override facts;
7. targeted and retained regressions.

No new repository module, audit store, planning status, training logic, cleaning logic, external-time model or regime-transition workflow.

## 13. PREIMPLEMENTATION AUDIT

Independent Codex must audit the exact final contract HEAD.

Required questions:

1. Does the contract model Site as planning/service unit rather than physical object?
2. Is the boolean `ochrona_mode` fully removed in favour of an explicit regime value?
3. Does T023b implement only `ORDINARY` and `OCHRONA`, with cleaning explicitly deferred?
4. Is legacy migration default `ORDINARY` clearly test-data compatibility only, with no `UNCLASSIFIED` or heuristic inference?
5. Is regime required at new Site creation and blocked from ordinary edits?
6. Is there no normal regime-transition command or retroactive lifecycle requirement?
7. Are T023b work facts target-Site only, with no `other_site_assignments` aggregation or inferred external work?
8. Is TRAINEE inherited solely from T012 with no new training branch?
9. Are weekly windows complete seven-day blocks wholly inside the month, with tail days excluded and no overlap across months?
10. Does cross-month behaviour remain only where needed for immediate rest after a concrete 24h duty/existing work-period provenance?
11. Do solver and validator share pure arithmetic while remaining independently enforcing?
12. Does manual correction reuse existing REST override/audit semantics without the previously invented `coordinator_action_id` requirement or hook reordering?
13. Is scope sufficient without assembler/lifecycle/site-memory changes?
14. Does any clause introduce a scenario not required by the frozen owner rulings?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered contract defects tied to exact clauses.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: targeted matrix + retained regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.