# FROZEN ADDENDUM — OCHRONA REST RULES 01

STATUS: FROZEN ARCHITECT CONTRACT
TASK: ROTA-T023b
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`

This addendum freezes exactly two additional automatic rest protections for Sites operating in the owner-selected ochrona mode. It does not claim general Polish-labour-law compliance and does not change unrelated planning, absence, payroll, print or HR semantics.

Controlling product decisions are the verified legal facts and O1/O2/O3 in `arch/T023b_ochrona_rest_rules_architect_brief.md`.

## 1. PRODUCT BOUNDARY

T023b adds exactly:

1. for an ochrona Site, an effective immediate-rest floor of 24 hours after an actual 24-hour WorkPeriod;
2. for an ochrona Site, a HARD requirement for at least 35 hours of uninterrupted rest in each statutory seven-day week;
3. employee-wide evaluation of those protections across the target Site, other Sites and relevant month boundaries;
4. one explicit audited manual-correction override path using the already-existing REST override precedent.

T023b does not add:
- Sunday-placement enforcement under art. 133 §3-4;
- automatic shortening of weekly rest to 24h under art. 133 §2;
- night-work-window rules;
- monthly/average weekly work-time limits;
- payroll, wage, leave-entitlement or HR settlement rules;
- a new exception workflow, rule ledger or schedule-version model;
- any reuse of `SitePrintSettings.base_regime` as a legal/work-rule mode.

Legal references used to define the selected scope:
- Kodeks pracy art. 128 §3 pkt 2: week = seven consecutive calendar days beginning on the first day of the settlement period;
- art. 133 §1: at least 35h uninterrupted weekly rest;
- art. 136 §2 applied through art. 137: after extended work in the protection/property-guarding equivalent-time system, immediate rest at least equal to hours worked; T023b freezes the selected 24h case only;
- art. 137: up to 24h daily dimension and settlement period not exceeding one month.

The T023b product settlement period is the calendar month (O3).

## 2. PER-SITE MODE

### 2.1 Canonical field

The legal-mode switch is current state owned by `Site`, not `SiteProfile` and not print settings.

Canonical domain field:

`Site.ochrona_mode: bool = False`

Semantics:
- `False` = ordinary mode; all pre-T023b planning/rest behaviour remains unchanged;
- `True` = ochrona mode; the two T023b protections in this addendum are active;
- the mode of the **target PlanningState Site** gates T023b enforcement;
- when that target Site is in ochrona mode, employee work on all Sites participates in the rest calculation;
- an ordinary target Site does not run T023b checks.

Why this ownership is required: the owner's switch is per Site, and multiple Sites may share one SiteProfile. A profile-scoped flag could silently switch unrelated Sites.

### 2.2 Persistence / migration

Schema v8 -> v9 adds one column to `sites`:

`ochrona_mode INTEGER NOT NULL DEFAULT 0 CHECK (ochrona_mode IN (0,1))`

Existing rows therefore migrate deterministically to ordinary mode. No data backfill heuristic is permitted.

`Site` appends the Python field with default `False` for source/test compatibility. `site_repository` reads and writes the column as bool.

The mode is mutable current state. It is not snapshotted into ScheduleVersion and does not create a second Site history table. Existing append-only coordinator actions remain its audit history.

### 2.3 Application write boundary

Initial Site creation/resume may persist the field through the existing `bootstrap_or_resume_coordinator_context()` Site write. Its existing `CONTEXT_CONFIGURATION_SAVED` action must include `ochrona_mode` in Site before/after state.

Later checkbox edits use one named application command:

`set_site_ochrona_mode(conn, *, coordinator_id, site_id, ochrona_mode, note=None, responds_to_decision_required_id=None)`

It must:
- require the existing active coordinator context;
- write only the named Site's mode;
- record exactly one existing `CoordinatorActionKind.CONTEXT_CONFIGURATION_SAVED` row, not add a new action kind;
- use `affected_site_ids=[site_id]`, affected entity `SITE:<site_id>`, source `CURRENT_STATE`;
- carry deterministic before/after `{site_id, ochrona_mode}` facts;
- invalidate current DECISION_REQUIRED pointers for that Site for all months in the same transaction;
- not create or rewrite a ScheduleVersion.

`update_site()` remains the ordinary name/active edit path and must reject an attempted `ochrona_mode` change, exactly as it already rejects profile rebinding; the caller must use `set_site_ochrona_mode()`.

One coordinator command still creates exactly one coordinator-action row (T019b).

## 3. ONE PURE REST-SEMANTICS OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of work-period/rest semantics used by solver, independent validator and manual-override fact reconstruction.

T023b extends that owner; it does not create a parallel `legal_rest.py`, application-local calculation or persistence-owned rule.

At minimum the owner must expose pure equivalents of these semantics (exact helper names may differ mechanically, semantics may not):

1. effective required rest after a WorkPeriod, parameterized by `ochrona_mode`;
2. statutory week-window generation anchored to calendar-month settlement periods;
3. maximum uninterrupted rest inside a supplied statutory week from occupied work intervals;
4. deterministic weekly-rest facts sufficient for independent validator/manual audit.

`work_periods.py` must continue to import no persistence module and no OR-Tools symbol.

## 4. IMMEDIATE REST AFTER A 24H DUTY — REST-01 EXTENSION

T023b does **not** create a second immediate-rest rule code. Existing `REST-01` remains the owner of directional rest between WorkPeriods.

For a resolved WorkPeriod `P`:

- `configured_rest(P)` remains the existing `P.required_rest_after_hours` after legacy normalization;
- `duration(P) = P.end - P.start`;
- if target Site `ochrona_mode=False`, `effective_rest(P) = configured_rest(P)`;
- if target Site `ochrona_mode=True` and `duration(P) == 24h`, `effective_rest(P) = max(configured_rest(P), 24h)`;
- otherwise `effective_rest(P) = configured_rest(P)`.

REST-01 violation remains:

`gap(next.start - P.end) < effective_rest(P)`

Existing overlap/zero-gap/illegal-continuous-pair rules remain unchanged.

### 4.1 Both 24h mechanisms

The floor is based on the resolved WorkPeriod's actual 24h duration, not on trusting only a catalog label or one rest-hours field. Therefore it applies uniformly to:
- normal Catalog H24 periods grouped from two 12h components;
- same-month emergency H12+H12 periods when the emergency pair is selected;
- cross-month emergency H12+H12 periods resolved under the existing shared `work_period_id` machinery.

Malformed work-period provenance remains independently rejected by existing `WORK_PERIOD-01` / `SHIFT-24-PAIR-01` checks; the T023b floor never makes malformed provenance legal.

### 4.2 Do not rewrite persisted rest provenance

T023b must **not** overwrite `ShiftDemand.required_rest_hours`, `ShiftDemand.emergency_24h_rest_hours` or `Assignment.required_rest_after_hours` to 24 merely because the target Site is in ochrona mode.

Those fields remain configured/snapshotted provenance. The 24h legal floor is applied dynamically by the canonical pure owner.

Why: ordinary mode must preserve configured behaviour, including after a Site is switched from ochrona back to ordinary. Persisting the temporary effective floor into schedule provenance would silently change ordinary-mode semantics.

## 5. WEEKLY REST — WEEKLY-REST-01

New built-in HARD code: `WEEKLY-REST-01`.

It is active only when the target `PlanningState.site.ochrona_mode` is true.

For every relevant employee/statutory-week pair:
- required uninterrupted rest = 35h exactly;
- O1: no automatic 24h shortening is inferred;
- O2: no Sunday-placement constraint is checked;
- all non-CANCELLED work intervals count as occupied time, regardless of Site and regardless of PRIMARY/TRAINEE role;
- overlapping/abutting occupied intervals are merged before measuring free gaps;
- occupied intervals are clipped to the half-open statutory window `[week_start, week_end)`;
- the maximum uninterrupted rest is the maximum free interval between `week_start`, merged occupied intervals and `week_end`;
- PASS iff maximum uninterrupted rest >= 35h;
- FAIL iff maximum uninterrupted rest < 35h.

The comparison is exact in elapsed time; no rounding-to-days or rolling-hours substitution is allowed.

LOAD-01 remains a separate soft/decision threshold and is not evidence of weekly-rest compliance.

## 6. STATUTORY WEEK AND TEMPORAL WINDOW

### 6.1 Settlement-month week generation

For any calendar settlement month `M`:
- anchor = first calendar day of `M` at 00:00;
- statutory week starts are `anchor + 7*n days` for every `n >= 0` whose start is before the first day of the next calendar month;
- each week is exactly `[start, start + 7 days)`;
- the final week may extend into the next month/year;
- ISO week numbers and arbitrary rolling seven-day windows are forbidden as substitutes.

Examples:
- a month beginning on any weekday still starts week 1 on day 1;
- a week starting 29 December may continue into January;
- the next calendar month starts its own settlement-period week sequence on its day 1.

### 6.2 Target-touching relevance

T023b must not reject a target plan solely because unrelated historical/current work already violates a T023b rule outside the target plan's influence.

A statutory week is relevant to a validation/solver run only if at least one target-Site target-version work interval overlaps that week.

For validator/manual correction, target intervals are non-CANCELLED Assignments from the candidate/corrected target snapshot.

For solver, relevance is conditional:
- a fixed target Assignment overlapping the week makes the check unconditional;
- otherwise the check is activated only when at least one selected target solver slot overlaps the week.

History/other-Site work participates in the calculation once a week is relevant, but history alone does not activate a new failure.

### 6.3 Which settlement months are considered

Given target work intervals:
1. take the calendar month containing the earliest target interval start;
2. include the immediately preceding calendar settlement month;
3. include every settlement month through the calendar month containing the latest target interval end;
4. generate statutory weeks for those settlement months;
5. retain only target-touching weeks.

This captures:
- the trailing statutory week from the previous settlement month that overlaps early target work;
- every current-month statutory week;
- the current month's final statutory week even when it crosses month/year;
- the next settlement month's first week when a target overnight/cross-boundary interval actually overlaps it.

The minimal logical read window is `min(relevant week_start)` through `max(relevant week_end)`.

Current `assemble_planning_state()` already over-reads employee cross-context through the existing unbounded interval APIs. T023b must reuse that data and filter deterministically; it must not add a second weekly-rest repository query or shrink the existing T012 unbounded REST context.

## 7. SOLVER ENFORCEMENT

Automatic planning in ordinary mode is byte-for-semantics equivalent to pre-T023b for these rules.

In ochrona mode:

### 7.1 REST-01

Existing rest-constraint construction must call the shared effective-rest owner. A prospective/fixed 24h WorkPeriod therefore requires at least 24h immediate rest even when configured/snapshotted rest is 0/11/23.

Same-month emergency pair constraints must apply the 24h floor to the merged selected pair's external edge. Cross-month emergency pairing must apply the same floor to the resolved merged period. No emergency path may retain the lower configured rest once the pair is an actual selected 24h period.

### 7.2 WEEKLY-REST-01 CP-SAT shape

For each employee/relevant statutory week, the solver must encode existence of at least one 35h work-free interval.

A complete finite candidate set may be built from rest-window starts at:
- statutory `week_start`;
- the end time of every fixed or prospective work interval that overlaps the week;
provided `start + 35h <= week_end`.

For each candidate 35h rest window:
- discard it if fixed work overlaps it;
- otherwise create a Boolean witness that can be true only if no selected solver slot overlaps it.

Require at least one witness when the week is target-touched. If there is no fixed target overlap, target-touch activation must be equivalent to OR of selected target slots overlapping that week; history-only failure must not make the model infeasible.

This construction is a mechanical encoding of Section 5, not a second semantic owner. Window generation/overlap facts come from pure helpers in `work_periods.py`.

### 7.3 Planning outcome boundary

A violating candidate is never emitted as FEASIBLE or as a coordinator-acceptable DECISION_REQUIRED candidate.

If HARD constraints make the scheduling problem infeasible, existing Frozen Execution Contract outcome diagnosis remains in force; T023b does not add a fourth PlanningResult status or redefine generic infeasibility/coverage diagnosis.

## 8. INDEPENDENT VALIDATOR

The validator re-derives both protections from `PlanningState + final Assignment list`; it never trusts solver witness literals.

In ordinary mode it reports no T023b-only violations.

In ochrona mode:
- existing `_check_rest` uses effective REST-01 required rest from the shared pure owner;
- `WEEKLY-REST-01` independently constructs relevant statutory weeks, occupied intervals and maximum uninterrupted rest;
- employee-wide input includes target Assignments plus existing `state.boundary_assignments` and `state.other_site_assignments`;
- cancelled assignments do not count as work;
- weekly `ViolationDetail.assignment_ids` names the target Assignment(s) that make the week relevant, never relies on parsing message text;
- message may display week bounds/observed rest, but structured downstream logic may not parse it.

`select_candidate`, `plan()` candidate evaluation, `revalidate`, `finalize` and manual correction inherit the rule through the existing validator call graph. No local reimplementation is authorized in those application modules.

## 9. MANUAL CORRECTION / AUDITED EXCEPTION

O1 allows explicit coordinator manual correction to persist a weekly-rest exception; Section 6 of the architect input requires the same audited precedent for both T023b protections.

T023b generalizes the existing REST override plumbing; it does not create another override table or executable exception rule.

### 9.1 Deviation

- `REST-01` remains `DeviationCategory.LAW`.
- add `WEEKLY-REST-01 -> DeviationCategory.LAW` to the existing static mapping.
- automatic candidate selection still rejects HARD violations;
- `apply_manual_correction` may persist them as materialized deviations exactly like existing REST-01.

### 9.2 One audit record per logical correction

If one manual correction produces any `REST-01` and/or `WEEKLY-REST-01` violation, create exactly one existing-style `CONFIRMED_EXCEPTION / INFORMATIONAL / RESOLVED` rule with:

- `rule_kind = "REST_OVERRIDE_RECORD"`;
- one `rule_id` scoped to the child correction, preserving the existing `REST-OVERRIDE:<child_id>` family shape;
- structured parameters containing all rest-violation facts for that correction.

Do not create one override record per violation or per employee.

### 9.3 Minimum reconstructable fact shape

Top-level structured parameters:
- `child_version_id`;
- `coordinator_action_id` — the one `MANUAL_SCHEDULE_CORRECTION` (or existing named manual action kind used by the caller) action created for this same correction;
- `violations` — deterministic ordered list.

For a REST-01 entry include at minimum:
- `rule = "REST-01"`;
- `employee_id`;
- earlier/later Assignment identities sufficient to distinguish ScheduleVersions;
- actual gap hours;
- configured/resolved provenance rest hours;
- effective required rest hours;
- earlier WorkPeriod duration hours;
- whether the 24h ochrona floor increased the requirement.

For a WEEKLY-REST-01 entry include at minimum:
- `rule = "WEEKLY-REST-01"`;
- `employee_id`;
- `week_start`, `week_end`;
- observed maximum uninterrupted rest hours;
- required rest hours = 35;
- deterministic Assignment identities overlapping the week;
- target Assignment identities that made the week relevant.

The DecisionRecord already contains coordinator identity and recorded time; the structured action id provides direct linkage to the one material coordinator action.

### 9.4 Atomic hook order

The existing `create_schedule_version(... on_success=...)` transaction remains the atomic boundary.

The composed success hook must:
1. record the one material coordinator action and retain its returned `action_id`;
2. if rest override facts exist, write the one `REST_OVERRIDE_RECORD` using that action id;
3. run any existing caller-specific success state in the same transaction.

A failure at any point rolls back child ScheduleVersion content, deviation rows, coordinator action and override DecisionRecord/SiteRuleVersion together.

T019b's one-action rule remains preserved: `record_decision_no_commit` used for the derived REST override does not create another coordinator-action row.

## 10. SITE MODE CHANGE AND EXISTING SCHEDULES

Changing `ochrona_mode` is a current planning-input change:
- it does not mutate historical ScheduleVersions;
- subsequent `plan_month`, `replan`, `select_candidate`, `revalidate`, `finalize` and manual correction read the current mode through the assembled `Site`;
- switching ordinary -> ochrona may therefore make an existing current schedule fail new HARD validation until corrected/overridden;
- switching ochrona -> ordinary removes only the two T023b protections and restores configured pre-T023b rest behaviour;
- no persisted rest field is rewritten by either transition.

## 11. OWNERSHIP / FILE IMPACT

Expected implementation ownership:
- `rota/domain.py` — append Site mode field;
- `rota/persistence/db.py` — schema v9 migration;
- `rota/persistence/site_repository.py` — Site mode I/O;
- `rota/application/bootstrap.py` — bootstrap state/audit includes mode;
- `rota/application/durable_inputs.py` — named checkbox write path + update_site guard;
- `rota/planning/work_periods.py` — pure canonical rest/week semantics;
- `rota/planning/constraints.py` — CP-SAT REST-01 floor + weekly-rest encoding;
- `rota/planning/solver.py` — wire weekly constraints / mode to constraint builder;
- `rota/planning/validator.py` — independent REST-01 floor + WEEKLY-REST-01;
- `rota/application/deviation_mapping.py` — WEEKLY-REST-01 LAW mapping;
- `rota/application/manual_edit.py` — generalized one-record atomic rest override.

Existing `rota/application/assembler.py` read behaviour is reused unchanged unless an independent audit proves a literal data gap. Existing unbounded cross-context is already sufficient.

No modification is expected in `rota/planning/eligibility.py`, `rota/application/plan_ops.py`, `rota/application/lifecycle_ops.py`, `rota/persistence/schedule_repository.py`, `rota/persistence/site_memory.py`, `rota/site_memory_types.py`, T023/T026 absence code or T020 print settings.

## 12. REQUIRED REGRESSION GUARANTEES

Implementation must prove at least:

1. schema v8->v9 preserves every existing Site and sets `ochrona_mode=False`;
2. new Site may be created ordinary or ochrona; shared SiteProfile does not couple the flags;
3. ordinary-mode outputs remain unchanged for all T012/T022 rest and emergency-pair regressions;
4. mode edit is authorized, atomic, one coordinator action, no ScheduleVersion write, and invalidates current questions for that Site;
5. update_site cannot silently change the legal mode;
6. ochrona normal H24 with 23h59 rest fails REST-01; 24h and 24h01 pass;
7. same-month emergency H12+H12 has identical 24h floor;
8. cross-month emergency pair has identical floor and sees the next duty in the following month;
9. configured rest 0/11/23 cannot lower the ochrona 24h floor; configured >24 remains stronger and is preserved;
10. a 12h/16h/non-24h period keeps its configured REST-01 requirement; T023b does not generalize the law rule beyond the selected 24h case;
11. cross-Site next duty participates in REST-01 when target Site is ochrona;
12. statutory week starts on settlement-month day 1, not ISO Monday and not a rolling window;
13. maximum weekly rest 34h59 fails, 35h passes, 35h01 passes;
14. a final statutory week may cross month/year and is validated once for its own settlement-month anchor;
15. previous-settlement trailing week is checked when current target work overlaps it;
16. next settlement month's first week is checked only when target work actually overlaps it;
17. unrelated history-only weekly violation does not block a target run that does not touch that week;
18. employee work on another Site reduces the same employee's weekly rest;
19. O1: automatic 24h weekly-rest exception is never inferred; a 24h-only weekly rest fails automatic planning/validation;
20. O2: no Sunday-placement rule appears anywhere;
21. solver and validator agree on feasible/violating 24h-rest and weekly-rest cases;
22. candidate selection rejects a persisted violating automatic candidate;
23. manual correction can persist the same violation only with LAW deviation plus one `REST_OVERRIDE_RECORD`;
24. the override contains coordinator_action_id and reconstructable 24h/weekly facts;
25. one manual correction with multiple rest violations creates one coordinator action and one override DecisionRecord, not duplicates;
26. fault injection proves child schedule/action/override atomicity;
27. changing mode does not mutate existing ScheduleVersion/rest provenance;
28. LOAD-01 remains unchanged and cannot substitute for WEEKLY-REST-01;
29. absence accounting/T020/T026 regressions remain unchanged;
30. full suite, Ruff, `git diff --check`, frozen/scope/size/function guards pass subject only to already owner-accepted inherited exceptions.

## 13. FINAL STATUS

This addendum resolves the known T023b product questions from the architect input without adding product semantics beyond O1/O2/O3 and the existing frozen execution model.

Implementation is not authorized until the matching `tasks/ROTA-T023b/brief.md` and this exact addendum HEAD receive independent Codex preimplementation PASS.
