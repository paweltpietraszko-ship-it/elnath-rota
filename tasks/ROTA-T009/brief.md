# TASK_CONTRACT

TASK_ID: ROTA-T009
TITLE: Application Layer / application use cases
STATUS: ARCHITECTURE_APPROVED_FOR_PRE_IMPLEMENTATION_REVIEW
DATE: 2026-08-13
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes

INTEGRATED_BASE_SHA: 81c30912bb24ed70a6cc095916fd2d3b6a2071fb
BASE_BRANCH_AT_FREEZE: main
OWNER_APPROVED_ROADMAP_SHA: 9c0919100d245262f90b69c08ba13efcb93fadf5
ROADMAP_AUDIT_PASS_COMMIT: 6a237002d51a5225d1573342d4e7f51469b8beee

ACCEPTED_LINEAGE_PRESENT_IN_INTEGRATED_BASE:
- ROTA-T004 accepted implementation: c3c43d176c58a14a70ee0db760d4df96a5c66bae
- ROTA-T005 accepted implementation: b97b762b3dfb4eef9d43a747a064e3b1e1144786
- ROTA-T006 accepted implementation: 6568de1de85a2cb290ebea041c62b00f99f79add
- ROTA-T007 accepted implementation: f50c49edeff92c0ef2c6274359fe4ede9f144f13
- ROTA-T008 accepted delivered implementation/test SHA: 5dee28d1a692b3fde94c0f1e0add8b27c32c9b3d

## STATUS / PROCESS GATE

This contract is written against the exact integrated base above.

CC MUST NOT implement ROTA-T009:
- on an individual T004/T005/T006/T007/T008 task branch;
- on an older main;
- on the benchmark branch;
- on any base that does not contain the complete accepted T004-T008 lineage above.

CC MUST NOT begin implementation until Codex returns:
- `PASS / READY_FOR_IMPLEMENTATION`; or
- a precise contract finding that is subsequently resolved by the architect/owner as appropriate.

Codex pre-implementation review is limited to contract conformity, testability, contradictions and genuine contract gaps. A review finding does not authorize the implementer to invent semantics.

## PURPOSE / ROADMAP POSITION

The owner-approved sequence is:

`T008 LocalStore + ScheduleVersion lifecycle`
`-> T009 Application Layer`
`-> T010 Natural Language Rule Intake`
`-> T011 Backend/Application E2E`
`-> T012 Desktop + Desktop E2E`

T008 established durable operational truth. T009 establishes the durable application/use-case boundary that coordinates that truth with SiteProfile, SiteMemory and PlanningEngine.

T009 is the layer that answers:

> "When the coordinator performs one application action, which durable facts are loaded, which planning operation runs, what is validated, and what is written back?"

It MUST NOT answer natural-language interpretation questions. Natural-language rule intake is ROTA-T010.

## SOURCE AUTHORITY

Use, in descending authority for this task:

1. frozen `arch/spec.md` on the integrated base;
2. frozen addenda already accepted for T006 and T007;
3. owner-approved roadmap `arch/OWNER_APPROVED_ROADMAP_T008_T012.md` at `9c0919100d245262f90b69c08ba13efcb93fadf5`;
4. accepted T004-T008 contracts, clarifications and accepted behavior;
5. product/reference architecture documents in `ELNATH_WARD_HANDOFF_FINAL_2026-08-10/` where they do not conflict with later frozen owner decisions;
6. exact integrated code base `81c30912bb24ed70a6cc095916fd2d3b6a2071fb` for existing accepted APIs and shapes.

Do not treat tests, commit messages, model suggestions, legacy `backend.py`, benchmark code, or current implementation accidents as new product authority.

## PRODUCT / QUALITY PRINCIPLE

Rota does not build a throwaway MVP. Scope may be narrower than the final product, but what T009 introduces is the target application boundary, not temporary glue to be replaced by the desktop task.

Reduce scope, not quality.

## ARCHITECTURE DECISION — ONE APPLICATION BOUNDARY

Introduce a target package:

`rota/application/`

This package owns use-case orchestration.

Required dependency direction:

```text
future UI / desktop bridge / T010 parser
                |
                v
        rota/application
          /           \
         v             v
rota/persistence   rota/planning
         \             /
          v           v
             rota/domain
```

Rules:

- `rota/application/` MAY call persistence repositories and planning primitives.
- `rota/application/` MUST NOT contain SQL or know table names.
- `rota/persistence/` MUST NOT import `rota.application` or PlanningEngine workflow.
- `rota/planning/` MUST NOT import `rota.persistence` or `rota.application`.
- future UI/desktop MUST call application use cases; it MUST NOT recreate repository -> PlanningState -> solver -> persistence orchestration itself.
- T010 MUST call a structured application command; it MUST NOT write repositories or SQLite directly.

Do not turn the existing top-level `backend.py` into the architectural application layer. It may remain legacy/inert, but new T009 orchestration belongs under `rota/application/`.

A public facade such as `RotaApplication` is RECOMMENDED and may be split internally into focused modules. Exact internal file layout is an implementation choice as long as the public use-case boundary and dependency rules remain testable.

## APPLICATION CONSTRUCTION / NO HIDDEN BUSINESS SESSION

The application boundary MUST be constructed from:
- caller-supplied local DB path, or a caller-supplied LocalStore connection factory;
- injectable clock for timestamps;
- injectable ID factory for new ScheduleVersion/Assignment/Deviation identifiers where deterministic tests require it.

The application layer MUST NOT hardcode the future desktop data-directory path.

The application layer MUST NOT keep authoritative business state only in memory.

In particular it MUST NOT make correctness depend on an in-memory:
- selected Site;
- selected month;
- current ScheduleVersion;
- candidate schedule;
- coordinator session object.

Site/month/coordinator are explicit use-case inputs. LocalStore current references are authoritative after restart.

## COORDINATOR CONTEXT — VALIDATION, NOT A NEW PERMISSION SYSTEM

T009 does not invent roles, permissions or authorization hierarchy.

For coordinator-originated write actions, application context validation MUST require:
- Coordinator exists and is active;
- Site exists and is active;
- active `CoordinatorSiteAssociation(coordinator_id, site_id)` exists.

Failure is an application-context error and performs no write.

This check is not a new permission matrix and does not introduce role levels.

Read-only technical/admin setup helpers used to bootstrap tests MAY be separate, but future coordinator UI commands must enter through validated application context.

## CENTRAL RESPONSIBILITY — PERSISTENCE -> PLANNINGSTATE ASSEMBLY

T009 MUST establish one canonical application-side assembler for PlanningState.

No future caller may be required to manually gather rule IDs, boundary assignments, cross-Site work, holiday history or balance data before calling PlanningEngine.

Given `(site_id, month)` and a specific current/working ScheduleVersion context, assembly MUST load/derive:

1. `Site`;
2. its `SiteProfile`;
3. the complete persisted `CalendarDay` set for the planning month;
4. relevant `SiteMemberships`;
5. referenced Employees;
6. current active `ExternalSupportWindows` relevant to the planning context;
7. current active AvailabilityRecords relevant to planning;
8. SiteRules using `assemble_monthly_site_rules(conn, site_id, month)` — no caller-supplied rule IDs;
9. `resolved SiteRules`, `unresolved SiteRules`, and T007 `SiteRuleApplicability` separately;
10. current ScheduleVersion `ShiftDemand`, `Assignment` and `Deviation` content;
11. WorkBalance values reconstructed from current LocalStore facts, never from historical schedule versions;
12. holiday history from current persisted REALIZED PRIMARY assignments joined to persisted holiday calendar data;
13. same-Site adjacent/boundary assignments sufficient for REST-01 and LOAD-01;
14. relevant current assignments for the same Employees on other Sites;
15. exact schedule_version_id used for this planning operation.

The assembler MUST NOT mutate persistence.

### Context interval

For the one-month planning context, use an interval wide enough to include every fact that can affect cross-boundary REST-01/LOAD-01:

- `context_start = first_day_of_month - 6 calendar days`;
- `context_end = first_day_of_next_month + 7 calendar days`, exclusive.

The application MUST use T008 interval-based current-version queries, not "previous month row" heuristics.

Same-Site boundary/context assignments MUST not be duplicated with the current ScheduleVersion's own assignment set when constructing PlanningState.

Cross-Site context MUST use current ScheduleVersions only and exclude the target Site.

### Calendar completeness

T008 chose persisted `CalendarDay` as the reproducible mechanism.

T009 MUST NOT guess missing holiday values and MUST NOT call a network calendar.

A PlanningState for a month is planning-ready only if a `CalendarDay` exists for every calendar date in that month. Missing dates are an application input/context error, not silently `holiday=false`.

### Missing target hours

Missing WorkBalance `target_hours` remains missing data. T009 MUST NOT replace it with zero or an invented statutory norm.

Because target_hours is SOFT and coverage demand must not be generated from it, missing target data MUST NOT be transformed into a fake HARD shortage. The application may surface a `MISSING_TARGET_HOURS` input warning and omit that WorkBalance from target-based soft context; it MUST NOT invent the value.

## SHIFTDEMAND GENERATION — SITEPROFILE, NOT EMPLOYEE TARGETS

When a Site/month has no ScheduleVersion yet, the application must be able to construct the first planning context.

For an initial OCHRONA/current-profile month, generate ShiftDemand from the active SiteProfile `standard_shifts`:
- every calendar day in the month;
- one demand occurrence per configured StandardShift;
- actual start/end interval from `start_time`, `end_time`, `end_next_day`;
- `required_primary_count` exactly from profile configuration;
- demand belongs to the month by start_datetime.

Demand generation MUST NOT depend on:
- Employee count;
- target_hours;
- availability;
- solver witness;
- X/Y availability.

This generator is deterministic application/domain assembly. It is not a second solver.

## USE CASE 1 — OPEN SITE / MONTH

Provide a read-only `open_site_month` use case.

It MUST return an application view/model sufficient for future T012 UI to display:
- Site + SiteProfile;
- coordinator-visible employee/membership/current availability context;
- active/resolved and unresolved SiteRules;
- current ScheduleVersion header/content when one exists;
- available version history for Site/month;
- reconstructed WorkBalance context where targets exist;
- current warnings/context completeness information.

Opening a Site/month MUST NOT:
- create ScheduleVersion;
- change current reference;
- call plan();
- modify rules;
- acknowledge deviations;
- change any durable fact.

If no ScheduleVersion exists, return `current_version=None`. Do not create an empty schedule merely by opening the screen.

## USE CASE 2 — PRECHECK

The frozen architecture requires a simple precheck before full planning:
- `NO_OBVIOUS_SHORTAGE`; or
- `LIKELY_INSUFFICIENT + context`.

PRECHECK MUST NOT claim FEASIBLE.

The accepted integrated base has no public precheck primitive. T009 MAY add exactly one pure, persistence-free planning primitive such as `rota/planning/precheck.py::precheck(state)` to satisfy the already-frozen contract.

It MUST be deliberately conservative and simple:
- no CP-SAT;
- no second scheduling engine;
- no general UNSAT analysis;
- no persistence access;
- no schedule candidate generation.

It may detect only obvious structural shortage and may return `NO_OBVIOUS_SHORTAGE` when the full solver later finds DECISION_REQUIRED. That is valid.

The application `precheck` use case must assemble fresh input and call this primitive. It performs no persistence write.

If no ScheduleVersion exists yet, precheck uses an ephemeral non-persisted planning context with deterministic ShiftDemand generated from SiteProfile. It MUST NOT create the first durable version merely to perform precheck.

## USE CASE 3 — INITIAL PLAN

Provide `plan_site_month` for ordinary planning.

Behavior:

### No ScheduleVersion exists

1. validate coordinator context;
2. generate deterministic month ShiftDemands;
3. assemble current Site/Profile/rules/people/calendar/context facts;
4. create the first current WORKING ScheduleVersion with:
   - generated complete ShiftDemand set;
   - no invented Assignments;
   - no invented Deviations;
   - applied_rule_version_ids equal to the currently assembled RESOLVED rule versions that apply on at least one day of the month;
5. rebuild PlanningState from the durable version and fresh facts;
6. call the real `PlanningEngine.plan(state)`.

The first durable version is created only because planning has actually begun, not on screen open.

### Current version is WORKING / WORKING_WITH_DEVIATIONS

- assemble fresh PlanningState from that current version;
- call real `plan(state)`.

### Current version is FINAL

`plan_site_month` MUST NOT reopen or mutate FINAL.
Return an application result that directs the caller to explicit REPLAN. Do not silently turn PLAN into an in-place edit of FINAL.

### Planning result handling

- `TECHNICAL_ERROR`: pass through as technical failure; do not rewrite it as shortage.
- `DECISION_REQUIRED`: return the decision package; do not auto-apply any relief action.
- `FEASIBLE`: return complete candidate AssignmentSets to the caller.

A FEASIBLE candidate is NOT automatically selected or persisted merely because the solver returned it.

PlanningEngine remains prohibited from choosing the final business schedule for the coordinator.

## USE CASE 4 — SELECT / SAVE ONE FEASIBLE CANDIDATE

Provide an application command that accepts:
- Site/month;
- coordinator context;
- target current working version id;
- one exact candidate AssignmentSet returned by planning.

The application MUST NOT depend on an in-memory candidate cache.

Before persistence:
1. confirm target version is still current and WORKING;
2. assemble a fresh PlanningState from current LocalStore facts;
3. run the independent `rota.planning.validator.validate` against the supplied candidate;
4. reject the candidate if the fresh validator reports any HARD violation;
5. refresh applied_rule_version_ids from the fresh assembled RESOLVED monthly rule set;
6. persist the selected complete snapshot through T008 `replace_working_snapshot`.

A stale candidate that became invalid because rules, availability, windows or cross-Site context changed MUST be rejected, not silently saved.

Soft warnings may be returned to the caller. Do not invent a hard Deviation merely because the solver has a SOFT quality warning.

## USE CASE 5 — REPLAN

Provide explicit `replan_site_month`.

Every REPLAN creates a NEW WORKING child ScheduleVersion derived from the current version before invoking PlanningEngine.

This is true whether the current parent is WORKING or FINAL.

Steps:
1. validate coordinator context;
2. read the exact current parent snapshot;
3. create a new child with complete cloned parent month state as initial baseline;
4. preserve every parent REALIZED Assignment exactly;
5. preserve future frozen Assignments and planned TRAINEE training decisions in the baseline passed to PlanningEngine;
6. make child current atomically through T008 lifecycle;
7. assemble fresh rules/availability/windows/boundary/cross-Site context into PlanningState for the child;
8. call real PlanningEngine.plan();
9. return FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR without auto-selecting a candidate.

If parent is FINAL, it remains immutable history.

If PlanningEngine returns DECISION_REQUIRED, the child remains the current WORKING decision context containing its cloned baseline; do not erase it and do not rewrite the parent.

If PlanningEngine returns FEASIBLE, candidate selection is a separate coordinator action and persists through the candidate-selection use case.

T006 ordering remains unchanged:
1. HARD;
2. minimum reshuffle count relative to the REPLAN baseline;
3. existing ordinary SOFT/TARGET ranking.

T009 MUST NOT introduce a new reshuffle weighting scheme.

## USE CASE 6 — COORDINATOR DECISION CHANGES INPUT, THEN PLAN AGAIN

DECISION_REQUIRED is not terminal failure.

T009 provides structured application commands to change existing durable inputs and then lets the coordinator call PLAN again.

At minimum the application boundary must support these structured actions:
- add/update/deactivate ExternalSupportWindow;
- append/supersede/deactivate AvailabilityRecord;
- save target_hours;
- save/update Employee current fields;
- save/update SiteMembership current fields;
- explicit readiness override through SiteMembership;
- save SiteProfile configuration;
- structured SiteRule/DecisionLedger command described separately below.

The application MUST NOT itself decide which relief action to take.

Example mandatory flow:
1. PLAN -> DECISION_REQUIRED because X/Y are unavailable;
2. coordinator command creates a confirmed ExternalSupportWindow;
3. PLAN runs again on fresh PlanningState;
4. X/Y are eligible only inside the persisted confirmed window.

No hidden "temporary solver override" is allowed. Coordinator decisions change durable input facts.

## STRUCTURED SITE RULE COMMAND — T010 INTEGRATION POINT, NOT A PARSER

T009 MUST expose a structured application command that writes one already-resolved rule decision through the accepted T005 Decision Ledger.

The command accepts explicit structured values, including:
- site_id;
- coordinator_id;
- rule_id;
- exact statement text supplied by caller;
- effective_from;
- relation (`supersedes` / `corrects` / `rejects` as accepted by T005, or first decision semantics);
- explicit `NewRuleContent` when the decision establishes/changes a rule.

It MUST call the accepted T005 `record_decision` write path.

It MUST NOT:
- parse natural language;
- infer rule_kind;
- infer employee identity from text;
- infer category/enforcement/effective dates;
- create a universal DSL;
- call an LLM;
- bypass Decision Ledger with direct SiteRule inserts.

This command is the application seam that ROTA-T010 will call after T010 has performed its separately frozen interpretation step.

## USE CASE 7 — MANUAL SCHEDULE CORRECTION + IMMEDIATE VALIDATION

Manual correction is not REPLAN.

Provide application commands that can modify the current operational schedule, including:
- add PRIMARY assignment;
- edit PRIMARY employee/interval;
- cancel assignment;
- split one ShiftDemand across sequential PRIMARY assignments;
- repair a coverage gap;
- add/edit/cancel TRAINEE through the training use case below.

### FINAL -> child first

If the current version is FINAL and a coordinator starts a material manual edit, the application MUST create a new WORKING child first, clone the complete parent snapshot, and apply the edit to the child.

The FINAL parent is never reopened.

### WORKING -> edit current working snapshot

If current is WORKING/WORKING_WITH_DEVIATIONS, edit that working snapshot atomically.

### Manual state must be storable

Persistence is not a validator.

The application MUST allow the real operational state to be stored even when manual edits create:
- a coverage gap;
- split coverage;
- an explicit coordinator override of a protected condition.

The command must run `validator.validate` immediately after the edit. It MUST NOT silently call REPLAN and undo the coordinator's edit.

Manual assignment is NOT automatically frozen.

### Deviation materialization

Validation findings remain non-persisted observations until the application materializes issues that must remain attached to the ScheduleVersion as Deviations.

Every persisted Deviation MUST retain the exact source reference:
- exact SiteRule `rule_version_id`; or
- exact stable built-in condition code.

The following deterministic category mapping is frozen for T009 reporting/storage only; it MUST NOT weaken HARD enforcement:

- `COVERAGE-01` -> `DeviationCategory.COVERAGE`;
- `DAY_SHIFT_OFF-01`, `LEAVE_GRANTED-01`, `UNAVAILABLE-01`, `SICK_LEAVE-01` -> `LEAVE_OR_TIME_OFF`;
- `LOAD-01` -> `HOURS`;
- `REST-01`, `EMP-02` -> `LAW`;
- exact SiteRule whose `RuleCategory == CLIENT_REQUIREMENT` -> `CLIENT_REQUIREMENT`;
- `DAY_ONLY-01`, `MEMBERSHIP-01`, `EXTERNAL-01`, and exact SiteRule with `RuleCategory` LOCAL_RULE or CONFIRMED_EXCEPTION -> `PREFERENCE` as the existing broad non-law/non-client reporting bucket.

Important: category `PREFERENCE` here is only the frozen Deviation reporting bucket available in the current domain. It does NOT convert a HARD rule into SOFT and does NOT allow PlanningEngine to violate it automatically.

If validator produces a persistent violation source that is not covered by the frozen mapping above, T009 MUST fail closed with an explicit unmapped-deviation error rather than guess a category.

For each revalidation pass, persisted Deviations for the working snapshot are regenerated from current validation state; stale deviations that no longer exist are removed from the working snapshot. Deviation identity may be regenerated for a new validation pass; source_reference + affected target are the semantic provenance.

The resulting T008 working status is derived from actual deviation count:
- 0 -> WORKING;
- >=1 -> WORKING_WITH_DEVIATIONS.

## USE CASE 8 — FREEZE / UNFREEZE ASSIGNMENT

Provide explicit freeze and unfreeze commands for an Assignment.

- Manual edit does not freeze automatically.
- Toggle only the requested current Assignment's `frozen` value.
- Revalidate the resulting current working snapshot.
- Do not run REPLAN automatically.
- If current version is FINAL and a material freeze-state change is requested, create a WORKING child first and change the child.

Future REPLAN must then observe accepted ASSIGN-04/T006 behavior for frozen future Assignments.

## USE CASE 9 — TRAINING S / TRAINEE

Provide structured application commands for:
- add TRAINEE Assignment;
- edit TRAINEE interval / employee / mentor;
- cancel TRAINEE Assignment;
- mark TRAINEE REALIZED when recording actual work.

Rules remain those already frozen:
- only when SiteProfile.training_s_enabled=true;
- weekdays only when profile flag requires it;
- exact interval chosen by coordinator;
- TRAINEE does not cover PRIMARY demand;
- mentor_primary_assignment_id required;
- mentor PRIMARY must belong to same ScheduleVersion/Site and contain the trainee interval;
- planned TRAINEE is a coordinator-fixed training decision preserved by REPLAN.

### Default readiness update

After a TRAINEE changes to REALIZED, application must recompute training history from current persisted TRAINEE Assignments.

When:
- membership.readiness_source == DEFAULT; and
- count of qualifying REALIZED TRAINEE assignments reaches `SiteProfile.training_s_default_readiness_threshold`,

application updates SiteMembership readiness_state to READY_FOR_PRIMARY.

If readiness_source == COORDINATOR_OVERRIDE, application MUST NOT overwrite the coordinator's readiness decision automatically.

No TrainingRecord entity is introduced.

## USE CASE 10 — REVALIDATE CURRENT WORKING VERSION

Provide an explicit revalidation use case.

Purpose:
- current rules/availability/windows/context may change after a WORKING version was last validated;
- manual edits require immediate validation;
- finalization must never depend on stale validation.

Behavior:
1. require current version is WORKING/WORKING_WITH_DEVIATIONS;
2. assemble fresh PlanningState with current durable facts;
3. call independent validator against the stored current assignments;
4. regenerate working Deviations using the frozen mapping;
5. replace `applied_rule_version_ids` with the current assembled RESOLVED monthly rule versions;
6. persist complete current working snapshot atomically.

Revalidation MUST NOT regenerate or move Assignments.

FINAL versions are never revalidated/mutated in place. Changed rules after FINAL require a new WORKING child.

## USE CASE 11 — FINALIZE

Provide an application finalization command.

Finalization MUST use fresh validation, never stale stored Deviations.

Required flow:
1. validate coordinator context;
2. require current version is WORKING/WORKING_WITH_DEVIATIONS;
3. perform fresh revalidation as above;
4. return the complete current Deviation list to the caller if acknowledgement is still required;
5. finalization request may include the exact deviation IDs the coordinator consciously acknowledges plus optional per-deviation reason;
6. application stamps `acknowledged=true`, `acknowledged_by=coordinator_id`, `acknowledged_at=clock.now()` for exactly those current deviations;
7. if the submitted acknowledgement set is not exactly the current required deviation set, do not finalize;
8. persist acknowledgements atomically in the working snapshot;
9. call T008 `finalize_schedule_version`.

Zero deviations -> FINAL_NO_DEVIATIONS.
One or more acknowledged deviations -> FINAL_WITH_DEVIATIONS.

Reason remains optional.

No UI confirmation dialog is implemented in T009. T009 only establishes the application command that future UI uses after showing the deviations.

## USE CASE 12 — RESTORE / SELECT EARLIER SCHEDULEVERSION

Provide application use case to select an existing version as current.

It MUST delegate to T008 restore/current-reference semantics:
- move only current reference;
- do not delete later versions;
- do not edit selected version;
- preserve complete history.

Opening a restored FINAL version is read-only. A later manual edit or REPLAN creates a new WORKING child first.

## USE CASE 13 — SITE MEMORY / DECISION HISTORY READ MODEL

Future UI must be able to answer operational memory questions without querying persistence itself.

Provide application read/query support for:
- active/effective SiteRules for Site/month;
- unresolved NEEDS_RESOLUTION rules;
- immutable rule version history;
- DecisionRecord chain/history for a rule family;
- exact statement, coordinator, recorded_at, effective period, relation and resulting rule_version_id where present.

This is factual memory/read-model behavior, not an audit bureaucracy and not natural-language interpretation.

Application read model MUST NOT rewrite history.

## USE CASE 14 — LOCAL BACKUP

Backup belongs on the application side of the UI boundary.

Provide an application operation that creates a consistent local backup at a caller-supplied destination.

Requirements:
- use SQLite-supported consistent backup semantics; do not copy an open DB file byte-by-byte and hope for consistency;
- source store remains usable after backup;
- backup must be openable by Rota and contain the same durable LocalStore state at the backup point;
- no cloud upload;
- no hardcoded desktop destination.

T012 will choose the destination through UI/desktop APIs; it will not implement backup semantics itself.

## USE CASE 15 — OPT-IN DIAGNOSTIC ZIP

Diagnostic export also belongs behind the application boundary so UI cannot bypass filtering.

Provide an opt-in application command that writes a ZIP to a caller-supplied destination.

By default it MUST NOT contain:
- employee display names;
- medical/absence note text;
- full schedule Assignment content;
- passwords/tokens/secrets;
- full SQLite database.

T009 diagnostic ZIP may contain only filtered technical metadata needed for support, such as:
- schema version;
- application/domain version identifiers available locally;
- counts of Sites/Employees/ScheduleVersions without names;
- selected Site/month/version IDs when explicitly supplied for diagnostics;
- PlanningResult status / stable condition identifiers;
- sanitized exception type/message with obvious secret values excluded.

Do not invent telemetry or network upload.

Tests MUST inspect ZIP members/content and prove prohibited data is absent.

## APPLICATION RESULT TYPES

T009 MAY introduce application-specific DTOs/result types outside `rota/planning/` for:
- open Site/month view;
- context warnings/errors;
- precheck result;
- plan/replan result wrapper;
- candidate selection result;
- revalidation result;
- finalization acknowledgement-required result;
- backup/diagnostic result.

These types MUST NOT duplicate persistent domain entities as a second source of truth.

PlanningResult remains the source for solver status/candidates/decision payload.

Application failures must distinguish at least:
- invalid application/context input;
- missing/incomplete durable data;
- stale/non-current version target;
- technical PlanningEngine failure;
- validation rejection of a FEASIBLE candidate;
- acknowledgement required;
- unmapped Deviation category.

Do not present technical error as staffing shortage or vice versa.

## TRANSACTION BOUNDARIES

Persistence repositories already own atomic storage invariants. T009 must orchestrate them without weakening atomicity.

Requirements:
- one coordinator command that modifies one aggregate/input family must either complete or leave prior durable state intact;
- FINAL->child creation must complete before child mutation; if child creation itself fails, current reference remains parent;
- no application method may partially write a ScheduleVersion directly around T008 lifecycle helpers;
- no direct SQL from application;
- no cross-repository transaction choreography that bypasses repository invariants.

Where an application use case needs several durable writes to be one business action, it MAY add a focused persistence transaction helper below application, but that helper must remain storage/invariant-focused and MUST NOT call PlanningEngine or own workflow semantics.

## RESTART BEHAVIOR

Application restart must not require re-entering remembered operational facts.

After closing and reopening the DB, `open_site_month`, PRECHECK, PLAN and REPLAN must reconstruct their inputs from LocalStore:
- SiteProfile;
- Employees/memberships/readiness;
- availability;
- ExternalSupportWindows;
- SiteMemory rule history/effective rules;
- current ScheduleVersion;
- calendar;
- WorkBalance targets/current-version derived balances;
- boundary/cross-Site context.

No rule_id injection and no hidden in-memory setup from a prior process is allowed.

## REQUIRED PUBLIC USE-CASE SURFACE

Exact class/function names may vary, but the implementation MUST expose testable operations equivalent to:

- `open_site_month(site_id, month, coordinator_id)`
- `precheck_site_month(site_id, month, coordinator_id)`
- `plan_site_month(site_id, month, coordinator_id)`
- `select_plan_candidate(site_id, month, coordinator_id, version_id, assignments)`
- `replan_site_month(site_id, month, coordinator_id)`
- `revalidate_current(site_id, month, coordinator_id)`
- `manual_edit_schedule(...)`
- `set_assignment_frozen(...)`
- `add_or_edit_training(...)`
- `cancel_training(...)`
- `record_training_realized(...)`
- `finalize_current(..., acknowledged_deviation_ids, optional_reasons)`
- `restore_version(site_id, month, coordinator_id, version_id)`
- structured current-fact mutation commands for Employee/SiteMembership/Availability/target/ExternalSupportWindow/SiteProfile;
- `record_structured_rule_decision(...)`
- SiteMemory/history read operations;
- `backup_local_store(destination)`
- `create_diagnostic_zip(destination, ...)`.

No HTTP server is required. No UI framework is required.

## EXPLICITLY OUT OF SCOPE

T009 MUST NOT implement:
- natural-language parsing;
- LLM runtime calls;
- inference of rule_kind/category/enforcement/effective dates from coordinator text;
- universal rule language / DSL;
- T010 clarification dialogue;
- React or desktop UI;
- desktop bridge/webview IPC;
- printing UI;
- SaaS/cloud sync;
- event bus/plugin architecture;
- future SKLEP behavior;
- additional SiteRule catalog beyond T007;
- new solver objective or HARD/SOFT semantics;
- new persistence database;
- benchmark redesign.

T009 does not reopen the abandoned real-object benchmark work and does not depend on its branch.

## REQUIRED INTEGRATION TEST MATRIX

The implementation MUST include deterministic integration tests against a real temporary SQLite LocalStore and the real PlanningEngine.

### A. Base / dependency gates

A1. `repo_before.hash` or equivalent records exact implementation base:
`81c30912bb24ed70a6cc095916fd2d3b6a2071fb`.

A2. T004-T008 accepted features are available from that base; implementation does not cherry-pick individual task branches during T009.

A3. `rota/planning/` has no persistence/application imports.

A4. `rota/persistence/` has no application imports and no PlanningEngine calls.

A5. `rota/application/` contains no SQL/table-name access and no UI imports.

A6. no new orchestration is added to legacy `backend.py`.

### B. Open / initial planning

B1. Seed SiteProfile/Site/Coordinator/association/Employees/memberships/calendar/targets and rules; call `open_site_month`; database has zero ScheduleVersions before and after.

B2. First PLAN creates exactly one current WORKING version with full profile-derived month ShiftDemands, then calls real plan().

B3. Demand count and intervals come from SiteProfile and calendar days, not employee target_hours or roster size.

B4. Closing/reopening DB and PLAN again reconstructs same rule/employee/calendar inputs without caller rule IDs.

### C. SiteMemory -> PlanningEngine integration

C1. Through real T005 Decision Ledger store a supported T007 HARD rule.

C2. Close DB, reopen application, call PLAN with no rule_id injection.

C3. Application monthly assembly passes exact active rule/applicability into PlanningState and real solver obeys it.

C4. NEEDS_RESOLUTION remains visible in open/read model but is not executable.

### D. Context correctness

D1. Missing one CalendarDay makes planning context incomplete; application does not assume `holiday=false`.

D2. Boundary query includes required predecessor context from the six prior calendar days and successor context relevant after month end.

D3. Same employee's current Assignment on another Site enters `other_site_assignments` and affects REST/LOAD planning.

D4. Non-current historical versions do not enter boundary/cross-Site/WorkBalance context.

D5. Missing target_hours is surfaced as missing/warning, never converted to zero and never used to create/remove ShiftDemand.

### E. PLAN candidate selection

E1. FEASIBLE from plan() does not change current working Assignments until coordinator selects a candidate.

E2. Selecting one real candidate persists complete selected snapshot through T008 lifecycle.

E3. Mutate durable input after plan but before candidate selection so candidate becomes HARD-invalid; fresh validator rejects it and storage remains unchanged.

E4. TECHNICAL_ERROR is not converted to DECISION_REQUIRED.

### F. DECISION_REQUIRED -> coordinator input -> plan again

F1. Real case returns DECISION_REQUIRED with no confirmed X/Y window.

F2. Add exact ExternalSupportWindow through application command.

F3. Rerun PLAN; real solver may use X/Y only inside confirmed window and returns FEASIBLE when that resource resolves the controlled shortage.

F4. No application method auto-creates window merely because PlanningResult suggested external support.

### G. REPLAN / version lineage

G1. Replan current WORKING -> NEW WORKING child, parent history preserved.

G2. Replan current FINAL -> NEW WORKING child, FINAL unchanged and reconstructable.

G3. REALIZED parent assignments preserved exactly in child.

G4. future frozen and planned TRAINEE decisions remain protected.

G5. controlled T006 scenario proves minimum reshuffle result is preserved through the application path; no new application weighting.

G6. DECISION_REQUIRED during REPLAN leaves child current with baseline complete snapshot; parent untouched.

### H. Manual correction / validation / Deviation

H1. Manual coverage gap is saved as real working state, validator reports COVERAGE and persisted version becomes WORKING_WITH_DEVIATIONS.

H2. Manual split A 05:00-13:00 / B 13:00-17:00 can be stored and validates full demand coverage according to accepted manual-split semantics.

H3. Manual LEAVE_GRANTED override creates exact source reference and LEAVE_OR_TIME_OFF Deviation.

H4. Manual REST violation creates LAW Deviation with REST-01 source.

H5. Manual T007 CLIENT_REQUIREMENT rule override preserves exact rule_version_id and CLIENT_REQUIREMENT category.

H6. an unmapped future validator source fails closed rather than receiving guessed category.

H7. manual edit never implicitly calls REPLAN.

### I. Freeze / unfreeze

I1. Manual assignment starts unfrozen unless caller explicitly sets otherwise through freeze command.

I2. Freeze current assignment, then REPLAN; frozen assignment is preserved.

I3. Unfreeze on WORKING, then REPLAN may redistribute subject to T006.

I4. Freeze-state change requested on FINAL first creates child; FINAL content unchanged.

### J. Training S

J1. add TRAINEE with valid same-version PRIMARY mentor and allowed weekday; persists without covering demand.

J2. invalid mentor or interval rejected by accepted validation/storage rules.

J3. planned TRAINEE survives REPLAN with mentor requirement.

J4. after two qualifying REALIZED TRAINEE assignments (or configured threshold) and readiness_source=DEFAULT, application updates readiness to READY_FOR_PRIMARY.

J5. readiness_source=COORDINATOR_OVERRIDE is never overwritten by automatic threshold update.

### K. Fresh revalidation / finalization

K1. change active rule after a WORKING version was last validated; revalidate updates applied_rule_version_ids and current Deviations without moving Assignments.

K2. finalize always performs fresh revalidation first.

K3. zero deviations -> FINAL_NO_DEVIATIONS.

K4. deviations present and acknowledgement set incomplete -> not finalized.

K5. exact current deviation set acknowledged -> acknowledged_by/at stamped and FINAL_WITH_DEVIATIONS.

K6. after FINAL, later SiteRule change does not mutate final applied_rule_version_ids or deviations.

### L. Restore/select

L1. create v1 -> v2 -> v3, restore v1; only current reference moves.

L2. v2/v3 remain readable unchanged.

L3. material edit after restoring FINAL v1 creates a new child; v1 remains immutable.

### M. Restart

M1. Perform rules + availability + X/Y + selected schedule + target + version history, close DB, reopen new application instance.

M2. open/PLAN reconstruct facts without in-memory session restoration or re-entry.

### N. Backup / diagnostics

N1. application backup creates independently openable DB with matching durable state at backup point.

N2. diagnostic ZIP contains no full DB file.

N3. diagnostic ZIP does not contain seeded employee display names, medical/absence note text, full Assignment schedule rows, or seeded fake token/password strings.

N4. diagnostic ZIP still contains useful sanitized technical metadata.

### O. T010 boundary protection

O1. `record_structured_rule_decision` calls accepted Decision Ledger and preserves exact structured input.

O2. no parser/LLM/text-to-rule inference exists in T009.

O3. a test or dependency scan proves T010 future caller can invoke structured application command without importing persistence repository modules.

## REGRESSION / ENGINEERING GATES

Required before Codex implementation audit:
- complete existing test suite PASS;
- all new T009 tests PASS;
- ROTA-REG-001 unchanged;
- T004-T008 accepted tests/invariants unchanged;
- Ruff PASS for touched/new Python;
- `git diff --check` PASS;
- existing repository file/function size gates remain satisfied;
- no persistence import in `rota/planning/`;
- no application import in `rota/persistence/`;
- no raw SQL in `rota/application/`;
- no UI/React/desktop dependency in T009;
- no NLP/LLM dependency in T009.

Do NOT use the abandoned real-object benchmark as an acceptance gate for T009.

## ACCEPTANCE DEFINITION

ROTA-T009 is complete only when a caller that knows nothing about SQLite or PlanningState assembly can:

1. open Site/month;
2. precheck;
3. PLAN;
4. receive FEASIBLE or DECISION_REQUIRED;
5. change a structured coordinator input such as X/Y availability;
6. plan again;
7. select a candidate;
8. make a manual correction and receive fresh validation/deviations;
9. freeze/unfreeze;
10. REPLAN into a new child with T006 minimal reshuffle semantics;
11. manage S training/readiness;
12. revalidate and finalize with conscious deviation acknowledgement;
13. restore an earlier version;
14. reopen the application and reconstruct the same durable context;
15. invoke backup and filtered diagnostics;

while:
- LocalStore remains the durable source of truth;
- SiteMemory remembers but does not plan;
- PlanningEngine plans but does not persist;
- application orchestrates but does not evaluate SQL or invent solver semantics;
- future UI does not need to orchestrate repositories;
- future T010 parser does not need repository/SQLite knowledge.

## REVIEW REQUEST TO CODEX

Pre-implementation review should answer only:

1. Is every required T009 behavior objectively testable?
2. Does any clause contradict the frozen architecture or accepted T004-T008 behavior?
3. Is any application workflow still ambiguous enough that CC would have to invent product/architecture semantics?
4. Does the contract accidentally pull T010 natural-language interpretation or T012 UI into T009?
5. Do transaction/restart/version-lineage tests sufficiently prevent orchestration drift into repositories or PlanningEngine?

Expected verdict:
- `PASS / READY_FOR_IMPLEMENTATION`; or
- precise findings tied to contract clauses.

Do not implement while reviewing.
