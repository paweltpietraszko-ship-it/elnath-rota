# ROTA-T023b — OCHRONA REST-RULE ENFORCEMENT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
FROZEN_CONTRACT: `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

T023b implements exactly two new HARD protections for a Site whose checkbox is set to ochrona:

1. at least 24h immediate rest after an actual 24h WorkPeriod;
2. at least 35h uninterrupted rest in each complete seven-day week of the calendar-month settlement period.

No implementation may start before independent Codex preimplementation PASS on the exact contract HEAD.

## 1. OWNER CLARIFICATIONS THAT CONTROL THIS CONTRACT

The 2026-08-23 owner clarification supersedes the architect input's broader cross-Site wording.

### C1 — no T023b cross-Site aggregation

T023b validates only work facts actually stored for the **target Site** in the considered Rota.

- do not add work from `state.other_site_assignments` to the new 24h floor or WEEKLY-REST-01;
- do not infer a second employer/site schedule that Rota does not observe;
- do not add warnings, placeholders or integrations for unknown external work;
- preserve existing pre-T023b T012/T022 cross-Site REST behaviour unchanged.

### C2 — TRAINEE is inherited T012 work, not a new case

Frozen T012 already states: non-CANCELLED TRAINEE remains work for REST/LOAD.

Therefore:

- a TRAINEE interval can interrupt the 35h uninterrupted weekly rest;
- do not add any new training-specific rule, exception, qualification or state;
- existing training/mentor constraints remain outside T023b.

### C3 — only full seven-day weeks exist for WEEKLY-REST-01

The monthly settlement period is divided from day 1 into complete seven-day weeks.

For a 31-day month the weekly windows are human dates:

- 1-7;
- 8-14;
- 15-21;
- 22-28.

Days 29-31 are tail days. They do not form another weekly-rest window. There is no week beginning on day 29 and extending into the next month. Day 1 of the next month begins week 1 of the new settlement period.

This weekly boundary does **not** truncate immediate rest after a concrete 24h duty. A 24h duty ending on the last day of a month may require rest extending into the next month.

No owner decision remains open.

## 2. NAMED INVARIANTS

### SITE-MODE-01

`Site.ochrona_mode: bool = False` is the sole T023b mode input.

- ordinary preserves pre-T023b behaviour;
- ochrona enables the two T023b protections for that Site;
- mode is per Site, not per SiteProfile and not print `base_regime`.

### OCHRONA-24H-REST-01

This is the ochrona-mode effective floor inside existing `REST-01`, not a second validator code.

For a target-Site resolved WorkPeriod `P`:

`effective_rest(P) = max(configured_resolved_rest(P), 24h)` iff `P` lasts exactly 24h and target Site is ochrona.

Otherwise use existing configured/resolved rest.

The floor applies to Catalog H24 and emergency H12+H12 because the actual resolved WorkPeriod span is the criterion.

### WEEKLY-REST-01

For target Site ochrona, every complete seven-day week wholly inside the calendar month must contain at least 35h uninterrupted free time for each employee's recorded target-Site work.

- no rolling-window replacement;
- no ISO week;
- no Sunday-placement test;
- no automatic 24h shortening;
- no cross-Site aggregation;
- PRIMARY and TRAINEE are both recorded work;
- CANCELLED is not work.

### TAIL-DAYS-01

The 0-3 days after the final complete seven-day week are outside WEEKLY-REST-01.

They remain ordinary calendar time and can still participate in existing REST-01 or in immediate rest after a 24h duty.

### MANUAL-REST-OVERRIDE-01

Automatic planning never persists a violating candidate.

An explicit manual correction may persist the HARD deviation only through the existing atomic REST override precedent: materialized deviation + at most one `REST_OVERRIDE_RECORD` for that logical child correction.

## 3. SITE MODE DATA / WRITE BOUNDARY

### Domain and schema

Append:

`Site.ochrona_mode: bool = False`

Bump LocalStore schema v8 -> v9 with:

`ALTER TABLE sites ADD COLUMN ochrona_mode INTEGER NOT NULL DEFAULT 0 CHECK (ochrona_mode IN (0,1))`

Existing rows migrate to ordinary mode. No new table and no heuristic backfill.

`site_repository.write_site_in_open_transaction`, `get_site`, `list_sites` round-trip the field.

### Bootstrap/create

`bootstrap_or_resume_coordinator_context()` may persist the supplied Site mode. Its existing `CONTEXT_CONFIGURATION_SAVED` before/after Site facts must include `ochrona_mode` when Site configuration is recorded.

### Later edit

Add one public application command:

`set_site_ochrona_mode(conn, *, coordinator_id: str, site_id: str, ochrona_mode: bool, note: str | None = None, responds_to_decision_required_id: str | None = None) -> None`

It must:

- use existing active coordinator-context authorization;
- update only the named Site's mode;
- no-op without a material change;
- on change, write the Site field + invalidate current decision-required state for that Site + record exactly one existing `CONTEXT_CONFIGURATION_SAVED` action in one transaction;
- create no ScheduleVersion and no new CoordinatorActionKind.

`update_site()` must not silently change the mode; mode edits go through the named command.

## 4. PURE REST SEMANTICS

`rota/planning/work_periods.py` stays the one pure owner for T012/T023b WorkPeriod/rest calculations.

Add only the pure helpers needed for:

1. target-Site effective required rest after a resolved WorkPeriod;
2. complete week windows for one calendar month;
3. maximum uninterrupted free interval inside one supplied week.

Planning code must not import persistence into this module and must not duplicate the calculations in validator/manual_edit.

### Complete week generation

For `month_start` and `next_month_start`, create:

`[month_start + 7*n days, month_start + 7*(n+1) days)`

only while the end is `<= next_month_start`.

No partial final window.

### Weekly free-time calculation

Given target-Site work intervals:

- clip each interval to `[week_start, week_end)`;
- discard no-overlap intervals;
- merge overlapping or abutting occupied intervals;
- measure free gaps from `week_start` to first occupied interval, between occupied intervals, and from last occupied interval to `week_end`;
- maximum gap `>=35h` passes.

Exact elapsed time; no day rounding.

## 5. 24H IMMEDIATE REST IMPLEMENTATION BOUNDARY

Do not rewrite persisted `required_rest_after_hours` to 24h. Existing configured/snapshot provenance remains intact.

Solver and validator use the shared effective-rest helper only for a **target-Site REST edge** under ochrona mode.

Coverage required:

- normal Catalog H24;
- same-month emergency H12+H12 selected as one WorkPeriod;
- cross-month emergency H12+H12 using existing work-period provenance;
- same-Site next recorded work after the 24h period, including across month end.

Do not apply the new 24h floor to `state.other_site_assignments`. Existing T012/T022 behavior for those facts is not part of T023b and must not change.

## 6. WEEKLY-REST-01 SOLVER

Wire one new HARD weekly-rest constraint builder into the existing solver path only when `state.site.ochrona_mode=True`.

Per employee/full week, occupied time consists only of target-Site facts:

- fixed target assignments from `fixed_existing_assignments(state)`;
- same-Site `state.boundary_assignments` to the extent they overlap the week;
- prospective target solver slots selected for that employee.

Do **not** use `state.other_site_assignments`.

Fixed non-CANCELLED TRAINEE counts as occupied time exactly as T012 already requires. No training branch is added.

The CP-SAT encoding must be equivalent to the pure 35h oracle. A minimal complete construction may enumerate candidate 35h rest starts at:

- `week_start`;
- end times of fixed/prospective target-Site intervals in that week;

and require at least one 35h candidate window with no fixed or selected work overlap. Equivalent simpler encoding is allowed.

No LOAD-01 variable or rolling window may satisfy this rule.

## 7. INDEPENDENT VALIDATOR

`validator.validate()` independently re-derives the rules from final facts.

### REST-01

For target-Site work-period edges, use shared effective rest. Do not infer 24h from a label alone.

### WEEKLY-REST-01

In ordinary mode: skip.

In ochrona mode:

- generate every complete week for `state.month`, whether or not it begins on Monday;
- work = non-CANCELLED target candidate Assignments + same-Site boundary Assignments overlapping the week;
- explicitly exclude `state.other_site_assignments`;
- PRIMARY and TRAINEE both occupy time;
- `<35h` maximum uninterrupted free interval emits `ViolationDetail(rule="WEEKLY-REST-01", ...)`;
- `assignment_ids` must identify target-Site Assignment facts, not message-parsed data.

Tail days create no WEEKLY-REST-01 check.

No application caller may implement its own copy of the rule; existing candidate selection/revalidation/finalization inherit it through validator/solver.

## 8. MANUAL CORRECTION

Keep `apply_manual_correction()` and the current atomic success-hook/DecisionRecord precedent.

Add static deviation mapping:

`WEEKLY-REST-01 -> DeviationCategory.LAW`

Existing `REST-01 -> LAW` remains.

Generalize current rest-override fact reconstruction so one logical correction with any REST-01/WEEKLY-REST-01 deviations produces at most one existing-style:

- category `CONFIRMED_EXCEPTION`;
- enforcement `INFORMATIONAL`;
- resolution `RESOLVED`;
- `rule_kind="REST_OVERRIDE_RECORD"`;
- `rule_id="REST-OVERRIDE:<child_id>"`.

Do not parse `ViolationDetail.message`.

Minimum WEEKLY structured facts:

- employee id;
- week start/end;
- observed maximum uninterrupted rest;
- required = 35h;
- target-Site Assignment identities overlapping that week.

For an ochrona 24h REST-01 exception record configured/resolved rest, effective required rest and actual gap so the applied floor is reconstructable.

Do not add `coordinator_action_id` or another linkage solely for T023b. Existing ScheduleVersion/child id + DecisionRecord coordinator provenance + the existing coordinator action already give the audit trail. Keep all writes atomic exactly as the current manual-correction flow does.

## 9. TASK SCOPE

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

No other production/test modification is authorized absent a concrete independent-audit finding that proves the task cannot be implemented within this scope.

Explicitly out of scope for modification:

- `arch/spec.md`, `arch/FROZEN.lock`;
- architect input brief;
- `rota/application/assembler.py`;
- `rota/application/plan_ops.py`, lifecycle/export modules;
- `rota/planning/eligibility.py`;
- persistence schedule/site-memory/decision-ledger modules;
- `rota/site_memory_types.py`;
- T023/T026 absence modules;
- SiteProfile schema;
- SitePrintSettings/base_regime;
- training/mentor logic;
- UI visual design;
- payroll/HR/night-work/Sunday-placement/general work-time compliance.

Reading/calling existing out-of-scope APIs is allowed.

## 10. REQUIRED ADVERSARIAL TEST MATRIX

### Mode / migration

T23b-01 — v8 database migrates to v9 and every existing Site has `ochrona_mode=False`.

T23b-02 — two Sites sharing the same SiteProfile can have different modes; changing one does not change the other.

T23b-03 — ordinary mode preserves existing REST/LOAD result for the same facts.

### Immediate 24h rest

T23b-10 — Catalog H24 with pure gaps 23h59 / 24h / 24h01 gives fail / pass / pass under ochrona.

T23b-11 — same-month emergency H12+H12 has identical floor.

T23b-12 — configured rest 0/11/23 never lowers the ochrona effective floor below 24h.

T23b-13 — cross-month emergency/24h duty ending in month M still enforces its immediate rest against the next recorded target-Site duty in M+1.

T23b-14 — ordinary mode keeps configured rest; T023b does not mutate persisted rest provenance.

### Full weekly windows

T23b-20 — 31-day month returns exactly four windows: days 1-7, 8-14, 15-21, 22-28; days 29-31 have no weekly window.

T23b-21 — 30-day month has four full weeks + two tail days; 28-day month exactly four weeks; leap February four weeks + one tail day.

T23b-22 — no generated weekly window crosses into the next month and next month's day 1 starts its own sequence.

T23b-23 — maximum uninterrupted rest 34h59 / 35h / 35h01 gives fail / pass / pass in pure calculation.

T23b-24 — non-CANCELLED TRAINEE interval interrupts weekly rest exactly as recorded work; no training-specific result or rule is produced.

T23b-25 — work occurring only on tail days creates no WEEKLY-REST-01 violation solely because of those tail days.

### Parity / manual override

T23b-30 — solver cannot return an ochrona candidate that independent validator rejects for either T023b protection.

T23b-31 — manual correction can persist a 24h-rest violation only with LAW deviation + atomic `REST_OVERRIDE_RECORD` carrying reconstructable effective-rest facts.

T23b-32 — manual correction can persist a WEEKLY-REST-01 violation only with LAW deviation + the same single-record override precedent carrying week/observed-rest facts.

T23b-33 — one correction containing multiple rest violations creates no duplicate REST override record.

T23b-34 — injected failure in the existing atomic schedule-version success path leaves no partial child/deviation/override write.

### Negative scope

T23b-40 — no Sunday-placement rule.

T23b-41 — no automatic 24h weekly-rest exception.

T23b-42 — LOAD-01 regression remains its existing rolling-7d decision-threshold behavior and is not reused as WEEKLY-REST-01.

T23b-43 — existing T012 TRAINEE REST/LOAD and existing T012/T022 cross-Site regressions remain unchanged; T023b adds no new cross-Site semantics.

## 11. RETAINED REGRESSIONS / QUALITY GATES

Run at minimum:

- `tests/test_t012.py`;
- T012 emergency/cross-month tests already present in the suite;
- training tests covering TRAINEE REST/LOAD;
- T022 cross-Site REST regressions;
- T019b manual action/audit tests;
- full suite;
- Ruff;
- `git diff --check`;
- repo scope/size/function guards with only already accepted inherited exceptions.

Do not rewrite existing regression oracles merely to make T023b pass. Any genuine semantic supersession must be named by this contract; otherwise it is a defect.

## 12. IMPLEMENTATION SHAPE / REVIEW UNIT

This task is narrow enough to review as **one implementation unit**. No A/B/C checkpoint split is required.

Expected production shape:

1. one Site bool + v9 migration/repository round-trip;
2. one authorized mode-edit application command;
3. small pure additions in `work_periods.py`;
4. one 24h-floor integration into existing REST solver/validator edges for target Site only;
5. one WEEKLY-REST-01 solver builder + independent validator check;
6. one deviation-map entry and minimal generalization of existing manual REST override facts.

No new repository module, no new audit store, no new planning status, no new training logic, no external-time model.

## 13. PREIMPLEMENTATION AUDIT / FINAL GATES

Independent Codex must audit the exact final architect contract HEAD before CC writes production code.

Audit questions:

1. Does any clause still imply cross-Site/external aggregation for T023b?
2. Are weekly windows restricted to complete 7-day blocks wholly inside the month, with tail days excluded?
3. Is cross-month behavior retained only where needed for immediate rest after a concrete 24h duty / existing work-period provenance, not by extending weekly windows?
4. Is TRAINEE only inherited T012 work with no new training branch?
5. Does ordinary mode preserve current behavior?
6. Can solver and validator share pure semantics without creating a second owner?
7. Does manual correction reuse the existing atomic REST override precedent without new audit plumbing?
8. Is TASK_SCOPE sufficient and no broader product feature is implied?

Required preimplementation verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered contract defects tied to exact clauses.

After implementation:

1. target matrix + retained regressions pass;
2. full suite / Ruff / diff-check / repo guards pass;
3. independent Codex implementation audit is bound to exact implementation SHA;
4. architect reviews exact final SHA and audit;
5. merge remains an explicit owner action.
