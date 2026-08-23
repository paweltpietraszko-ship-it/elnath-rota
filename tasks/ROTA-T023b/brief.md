# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
OWNER_FOLLOW_UP: `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md`
R3_AUDIT: `tasks/ROTA-T023b/round_01/tests/tests_r3.txt`
SUPERSEDES_CONTRACT_HEAD: `f42549d493f7a6bc330bf44a53dc10c8a8085c6c`

R3-1 is resolved structurally below. The frontend return value is no longer the owner of the replan obligation; persisted Site + ScheduleVersion provenance are.

T023b adds exactly two HARD protections to an `OCHRONA` Site:

1. 24h minimum immediate rest after an actual 24h WorkPeriod;
2. 35h uninterrupted rest in every complete seven-day week of the calendar-month settlement period.

No production implementation may start before independent PASS on this exact consolidated contract HEAD.

## 1. CLOSED PRODUCT FACTS

The frozen addendum is semantic authority. Preserve these boundaries:

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
- existing persisted data is test data only, so migration may use `ORDINARY` compatibility defaults.

No owner decision remains open.

## 2. SITE REGIME + DURABLE SCHEDULE PROVENANCE

### Domain

In `rota/domain.py` add:

`SitePlanningRegime = ORDINARY | OCHRONA`

Required Site field:

`Site.planning_regime: SitePlanningRegime`

Required ScheduleVersion field:

`ScheduleVersion.planning_regime: SitePlanningRegime`

The ScheduleVersion field is provenance of its persisted planning content, not a second mutable Site setting.

Do not add CLEANING/SPRZATANIE semantics in this task.

### Schema v9

Bump LocalStore schema v8 -> v9 and add both:

`sites.planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

`schedule_versions.planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

Both SQL defaults exist only for current test/legacy rows. New Site creation and new ScheduleVersion writes must persist an explicit/derived value and must not rely on the SQL default.

### Site repository

`site_repository` owns Site-regime writes:

- normal insert/write persists the supplied regime;
- read/list returns `SitePlanningRegime` and fails closed on unsupported stored values;
- normal write of an existing Site rejects a regime change before updating other fields;
- one narrowly named open-transaction primitive may update **only** `planning_regime`, and only the dedicated correction command uses it.

No generic regime setter/toggle.

### Schedule repository — single durable replan read owner

`schedule_repository` reads/writes ScheduleVersion regime provenance and owns two derived reads:

`version_requires_regime_replan(conn, version_id) -> bool`

returns `True` exactly when:

1. that ScheduleVersion contains at least one `Assignment.state == PLANNED`, and
2. `ScheduleVersion.planning_regime != current Site.planning_regime`.

No PLANNED Assignment => `False`; REALIZED/CANCELLED-only history is not blocked.

`list_regime_replan_required_months(conn, site_id) -> tuple[date, ...]`

returns sorted months whose **current** ScheduleVersion satisfies the same predicate.

These reads are the persistent owner after restart. Do not derive the obligation from an in-memory command result or by parsing coordinator-action JSON.

## 3. CREATION + EXCEPTIONAL REGIME CORRECTION

### Bootstrap / creation

`bootstrap_or_resume_coordinator_context()` keeps the existing Site write path.

Update only its planning-relevant comparison/audit serialization so initial `planning_regime` is included in Site configuration facts.

A missing regime must fail before a new real Site is persisted; application code never infers ORDINARY from omission.

### Correction command

Add in `rota/application/durable_inputs.py`:

`correct_site_planning_regime(conn, *, coordinator_id: str, site_id: str, planning_regime: SitePlanningRegime, note: str | None = None, responds_to_decision_required_id: str | None = None) -> tuple[date, ...]`

Required behaviour:

1. authorize with existing active coordinator context;
2. same-regime request is a no-op with no coordinator action;
3. in one transaction: validate the decision-required link, update only Site regime through the dedicated repository primitive, record exactly one existing `CONTEXT_CONFIGURATION_SAVED` action with old/new regime, and invalidate current decision-required pointers for that Site;
4. do not create/rewrite/finalize/restore a ScheduleVersion and do not mutate Assignments;
5. after the Site update, return `list_regime_replan_required_months(...)` as a UI convenience;
6. action metadata may include that derived month list, but it is not the enforcement source;
7. add no CoordinatorActionKind.

The correction command is deliberate/audited backend support for the separate T021 correction flow. It is not an ordinary edit control.

## 4. SCHEDULEVERSION PROVENANCE / LIFECYCLE GATE

This section is the structural R3-1 closure.

### Provenance on creation

`create_schedule_version()` persists planning-regime provenance as follows:

- root version (`parent_version_id is None`) starts with the current Site regime;
- child version inherits the parent ScheduleVersion regime because its initial persisted planning content derives from that parent;
- no child becomes current-regime merely because it was created after a Site correction.

This inheritance is intentionally conservative: cloning old planning content does not prove that content was accepted under the new regime.

### Provenance adoption on selected candidate

A successful `select_candidate()` already validates the candidate against the freshly assembled current Site.

When that validated candidate is atomically persisted into the current WORKING ScheduleVersion, the same transaction also sets that ScheduleVersion's `planning_regime` provenance to `state.site.planning_regime`.

Only this fresh accepted candidate write may promote an old-regime WORKING plan through the normal automatic planning path.

`revalidate()`, `finalize()`, `restore()` and plain navigation do **not** change ScheduleVersion regime provenance.

Manual child corrections inherit their parent provenance. Therefore regime correction cannot be bypassed by an unrelated manual edit; T021 still routes a mismatched planned month through REPLAN/candidate selection.

### Persistence lifecycle enforcement

`schedule_lifecycle` is the enforcement boundary for finalize/restore:

- `finalize_schedule_version()` must reject before mutation when `version_requires_regime_replan(version_id)` is true;
- `restore_schedule_version()` must reject before moving CURRENT when the target version requires regime replan;
- failed gates write no lifecycle/action side effects;
- an existing REST override does not waive this regime-provenance mismatch; regime correction itself is not a REST exception.

This gives `lifecycle_ops.finalize()` and `lifecycle_ops.restore()` durable protection without duplicating the predicate in application code.

### Presentation/export enforcement

`schedule_export.generate_schedule_pdf()` must fail closed with a stable problem code such as `REGIME_REPLAN_REQUIRED` when the current ScheduleVersion requires regime replan.

Do not redesign PDF semantics. This is one pre-render gate using the schedule-repository predicate.

T021 may call `list_regime_replan_required_months()` on navigation/restart and route those months to existing REPLAN. The UI is therefore recoverable after restart, but backend correctness does not depend on that routing.

No new stale-schedule table, lifecycle status, regime-correction history table or action kind is introduced.

## 5. T021 FRONTEND BINDING — SHARED IMPLEMENTATION

T021 UI code is not implemented by this task, but it is bound to:

- separate creation entry points/screens for at least OCHRONA and ORDINARY;
- no generic regime checkbox/toggle/dropdown in Site creation;
- selected entry point supplies the required regime;
- common fields, validation, components and persistence stay shared;
- Site workspace visibly shows regime;
- ordinary edit has no regime-change control;
- correction is visibly separate, explicitly confirmed and calls only `correct_site_planning_regime`;
- after correction/navigation, persisted `list_regime_replan_required_months()` drives REPLAN prompts;
- cleaning remains a separate future service flow and never silently maps to ORDINARY.

## 6. ONE PURE REST OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of shared arithmetic.

Add only reusable semantics for:

- effective required rest after one resolved WorkPeriod;
- complete settlement-week windows for one calendar month;
- maximum uninterrupted free interval inside one weekly window.

Required semantics:

- exact 24h WorkPeriod + `OCHRONA` => `max(resolved configured rest, 24h)`;
- otherwise configured/resolved rest unchanged;
- weekly windows exist only when a full 7-day interval fits inside the month;
- weekly free time clips work to the week, merges overlapping/abutting work and measures the largest free gap including both boundaries.

Do not create another legal-rest module or duplicate this arithmetic in application code.

## 7. SOLVER / VALIDATOR

### Existing REST-01

Keep `REST-01` as the only immediate-rest code.

Solver and validator use shared effective-rest semantics for target-Site WorkPeriods under OCHRONA, covering existing T012 forms:

- Catalog H24;
- same-month emergency H12+H12;
- existing cross-month emergency pair provenance.

The next target-Site duty must respect that rest even across month end.

Do not apply the new T023b floor to `state.other_site_assignments`. Existing T012/T022 cross-Site behaviour is retained, not redesigned.

### WEEKLY-REST-01

Add one HARD solver constraint and one independent validator check.

For OCHRONA, per employee and complete weekly window, occupied time is only recorded target-Site non-CANCELLED work. PRIMARY and TRAINEE both count. PASS requires at least one uninterrupted free interval of 35h or more.

For ORDINARY, skip the new weekly check.

Solver encoding is intentionally not prescribed. It must be logically equivalent to the pure weekly oracle; validator independently re-derives the result from final Assignment facts.

Do not reuse LOAD-01, ISO weeks or rolling seven-day windows. Add no PlanningResult status.

## 8. MANUAL SCHEDULE CORRECTION — REUSE, DO NOT REDESIGN

Keep current `apply_manual_correction()` transaction and REST override precedent.

Required changes only:

- map `WEEKLY-REST-01` to `DeviationCategory.LAW`;
- extend existing REST override record so a manual weekly-rest violation is auditable;
- use shared pure week/rest helpers for reconstructed facts; no second weekly audit calculation and no message parsing;
- one logical child correction still creates at most one existing-style `REST_OVERRIDE_RECORD`.

Minimum weekly facts: employee, week start/end, observed maximum uninterrupted rest, required rest=35h.

For 24h REST-01 retain enough facts to distinguish configured/resolved rest from effective required rest.

Do not add `coordinator_action_id`, another action/table or new hook ordering solely for T023b. Existing atomic manual-correction tests remain the atomicity oracle.

Manual child ScheduleVersions inherit parent planning-regime provenance per Section 4; an unrelated manual edit is not a substitute for required replan after regime correction.

## 9. TASK SCOPE

Production files allowed:

- `rota/domain.py`
- `rota/persistence/db.py`
- `rota/persistence/site_repository.py`
- `rota/persistence/schedule_repository.py`
- `rota/persistence/schedule_lifecycle.py`
- `rota/application/bootstrap.py`
- `rota/application/durable_inputs.py`
- `rota/application/plan_ops.py`
- `rota/application/manual_edit.py`
- `rota/application/deviation_mapping.py`
- `rota/planning/work_periods.py`
- `rota/planning/constraints.py`
- `rota/planning/solver.py`
- `rota/planning/validator.py`
- `rota/application/schedule_export.py`

No `lifecycle_ops.py` semantic duplicate is required: finalize/restore inherit the persistence lifecycle gate.

Contract/test files:

- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
- `tasks/ROTA-T023b/brief.md`
- `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md` (read-only owner ruling)
- `tasks/ROTA-T023b/round_01/tests/tests_r3.txt` (read-only audit evidence)
- `tests/test_t023b.py`
- `tests/test_local_store_schema_migration.py`

Mechanical compatibility exception: existing tests/fixtures under `tests/` may be edited only to provide explicit/compatible `planning_regime=ORDINARY` for pre-T023b Site/ScheduleVersion constructors. Assertions and scenario meaning must not change.

Explicitly out of scope:

- `rota/application/assembler.py`;
- `rota/application/lifecycle_ops.py` unless implementation proves a literal error-surface blocker;
- site-memory/action-kind modules;
- `rota/planning/eligibility.py`;
- SiteProfile and print-setting semantics;
- training/mentor logic;
- cleaning-service HARD rules or physical-object modeling;
- payroll/HR/night/Sunday/general work-time compliance;
- `arch/spec.md`, `arch/FROZEN.lock` and architect input brief.

## 10. MINIMUM TEST MATRIX

### Regime / migration / correction

T23b-01 — v8 Site and ScheduleVersion test/legacy rows migrate with ORDINARY provenance; new OCHRONA Site round-trips and application creation never relies on SQL default.

T23b-02 — normal Site repository write rejects regime change; dedicated correction changes only Site regime, uses active-context authorization, records exactly one existing `CONTEXT_CONFIGURATION_SAVED`, invalidates decision-required pointers and mutates no ScheduleVersion/Assignment.

T23b-03 — same-regime correction is no-op; correction return and `list_regime_replan_required_months()` agree.

### Durable R3 lifecycle gate

T23b-04 — after ORDINARY -> OCHRONA correction, a current version with PLANNED work and ORDINARY provenance remains `version_requires_regime_replan=True` after reopening/re-reading the LocalStore; REALIZED/CANCELLED-only version is false.

T23b-05 — stale-regime PLANNED version cannot be finalized even when caller acknowledges freshly derived deviations; no finalization/action side effect occurs.

T23b-06 — stale-regime PLANNED prior version cannot be restored as CURRENT; REALIZED/CANCELLED-only history is not blocked solely by regime mismatch.

T23b-07 — PDF/current-plan presentation fails with `REGIME_REPLAN_REQUIRED` while mismatch exists.

T23b-08 — REPLAN child initially inherits parent provenance; mere replan/revalidate does not clear mismatch. Successful `select_candidate()` validated under current regime atomically adopts current provenance, after which lifecycle/export gate clears.

T23b-09 — unrelated manual child correction inherits parent provenance and cannot clear a regime-replan obligation.

### 24h immediate rest

T23b-10 — Catalog H24 gaps 23h59 / 24h / 24h01 => fail / pass / pass under OCHRONA; configured value >24 remains stronger and persisted rest provenance is not rewritten.

T23b-11 — emergency H12+H12 gets the same floor, including existing cross-month pair/next target-Site duty.

T23b-12 — new T023b floor does not consume `state.other_site_assignments`.

### Weekly rest

T23b-20 — parameterized month-window oracle proves 31/30/28/leap-February shapes, no cross-month weekly window and tail days excluded.

T23b-21 — maximum uninterrupted rest 34h59 / 35h / 35h01 => fail / pass / pass.

T23b-22 — non-CANCELLED TRAINEE interrupts weekly rest under existing T012 semantics; no training-specific rule appears.

T23b-23 — `state.other_site_assignments` do not enter weekly calculation.

### Solver/manual path

T23b-30 — OCHRONA solver output and independent validator agree for both protections; automatic violating candidate is not accepted.

T23b-31 — explicit manual schedule correction of REST-01 and/or WEEKLY-REST-01 uses LAW deviation + at most one existing REST override record with fact-derived data.

### Negative scope

T23b-40 — no Sunday rule, automatic 24h weekly exception, CLEANING semantics, LOAD-01 reinterpretation, new stale table/status or new CoordinatorActionKind is introduced.

## 11. RETAINED REGRESSIONS / QUALITY GATES

Run relevant existing regressions instead of duplicating mechanisms:

- T008/T009 schedule create/select/finalize/restore/export lifecycle regressions;
- T012 REST/emergency/cross-month and TRAINEE REST/LOAD tests;
- T022 cross-Site REST tests;
- existing manual-correction/REST-override and T019b atomic/action tests;
- local-store migration tests;
- full suite;
- Ruff;
- `git diff --check`;
- repository scope/size/function guards with only the explicit mechanical constructor compatibility exception.

Do not rewrite existing regression outcomes merely to make T023b pass.

T023b remains one implementation/review unit. No checkpoint split is required.

## 12. FINAL PREIMPLEMENTATION VERIFICATION

R3 found one structural blocker only: ephemeral ownership of the replan requirement. This contract replaces it with persisted Site + ScheduleVersion provenance and one shared repository predicate enforced by lifecycle/export.

Independent verification of this exact HEAD should answer:

1. Does ScheduleVersion provenance make the regime mismatch durable across restart without a new stale table/status?
2. Do finalize and restore both fail through the same persistence-owned predicate before mutation?
3. Does export fail closed for the same persisted mismatch?
4. Can a freshly validated selected candidate atomically adopt current Site regime while revalidate/restore/finalize/manual child creation cannot silently do so?
5. Are REALIZED/CANCELLED-only historical versions preserved and not blocked solely by a later Site correction?
6. Does the correction command remain a small Site/audit mutation with the returned month list now only a convenience?
7. Does this structural fix avoid introducing product scenarios beyond the owner ruling and R3-1 reproducer?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` only for a concrete contradiction in this consolidated R3 closure.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: targeted matrix + retained regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.

## 13. EXACT TASK_SCOPE

Mechanical restatement of section 9 for backend.py's parser (bare paths,
no formatting) -- same precedent as T023 brief.md section 15/T026's own
fix. Not a scope change; section 9 is the authoritative prose.

TASK_SCOPE:
- arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md
- arch/T023b_ochrona_rest_rules_architect_brief.md
- tasks/ROTA-T023b/brief.md
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/application/bootstrap.py
- rota/application/durable_inputs.py
- rota/application/plan_ops.py
- rota/application/manual_edit.py
- rota/application/deviation_mapping.py
- rota/planning/work_periods.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/application/schedule_export.py
- tests/test_t023b.py
- tests/test_t012.py
- tests/test_t019b.py
- tests/test_t020.py
- benchmarks/real_object_production.py
- benchmarks/rota_stress.py
- tests/support/minimal_state.py
- tests/support/state_builder.py
- tests/support/t008_fixtures.py
- tests/test_audit_t010_r3.py
- tests/test_audit_t010_r4_a.py
- tests/test_audit_t010_r5_b.py
- tests/test_audit_t010_r6_d.py
- tests/test_local_store_master_data.py
- tests/test_local_store_operational_queries.py
- tests/test_t010_bootstrap_roster.py
- tests/test_t010_day_only_n_exception.py
- tests/test_t010_nn.py
- tests/test_t011_a_application_entry_points.py
- tests/test_t011_b_context_discovery.py
- tests/test_t011_c_site_coordinator_lifecycle.py
- tests/test_t011_d_quarter_balance.py
- tests/test_t011_e_pipeline_e2e_happy_path.py
- tests/test_t011_e_pipeline_e2e_hard_stop.py
- tests/test_t017.py
- tests/test_t018.py
- tests/test_t019.py
- tests/test_t023.py
- tests/test_vertical_full_stack.py

Owner-authorized narrow amendment (2026-08-23, round-5 audit R5-3 fix):
the above `tests/*` and `benchmarks/*` files are in scope ONLY to add
an explicit `planning_regime=SitePlanningRegime.ORDINARY` keyword
argument (plus the matching import) to their existing `Site(...)`
constructor call(s), forced by removing `Site.planning_regime`'s
dataclass default per R5-3 (frozen addendum section 3: omission must
never silently become ORDINARY). No assertion or scenario meaning
changes. `benchmarks/*.py` is not literally under `tests/`, but its two
`Site()` call sites are imported by in-scope test files
(test_real_object_benchmark.py, test_manual_audits.py,
test_rota_stress_benchmark.py) and needed the same mechanical fix for
those tests to run at all.

Owner-authorized narrow amendment (2026-08-23, mechanical schema-bump
fallout): tests/test_t012.py, tests/test_t019b.py, tests/test_t020.py
are in scope ONLY for the LATEST_SCHEMA_VERSION literal (8 -> 9) forced
by this task's own required db.py schema bump (section 2), plus
tests/test_t020.py's test_t20_01b migration-replay test, which cannot
safely reuse its "roll back an already-fully-migrated connection's
pragma" technique against a non-idempotent ALTER TABLE ADD COLUMN
migration (as migrations 3/4/5 already are) the way it could against
migrations 7/8 (both CREATE TABLE IF NOT EXISTS) -- rewritten to build
a genuine schema-6-only connection instead. No other assertion or
scenario meaning in any of the three files changes. Same one-time
exact-SHA exception pattern as T023's own Checkpoint B/C amendments;
backend.py's global MAX_NEW_FILES is unchanged.
