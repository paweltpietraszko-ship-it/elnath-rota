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

ACCEPTED_LINEAGE PRESENT IN BASE:
- T004: c3c43d176c58a14a70ee0db760d4df96a5c66bae
- T005: b97b762b3dfb4eef9d43a747a064e3b1e1144786
- T006: 6568de1de85a2cb290ebea041c62b00f99f79add
- T007: f50c49edeff92c0ef2c6274359fe4ede9f144f13
- T008: 5dee28d1a692b3fde94c0f1e0add8b27c32c9b3d

## PROCESS GATE

This contract is written against the exact integrated base above.

CC MUST NOT implement T009 on an individual task branch, old main, or the abandoned benchmark branch.

CC starts only after Codex returns `PASS / READY_FOR_IMPLEMENTATION`.

## PURPOSE

T008 made the operational state durable. T009 adds the thin application layer that performs the coordinator's real actions by composing:

- LocalStore repositories;
- SiteProfile;
- SiteMemory / Decision Ledger;
- PlanningEngine.

T009 does NOT parse natural language. That is T010.

T009 does NOT build UI/desktop bridge. That is T012.

## ANTI-BUREAUCRACY RULE

T009 MUST be a thin orchestration layer, not a second system above Rota.

Do NOT introduce:
- command bus / mediator framework;
- event sourcing;
- workflow engine;
- service/facade/repository layers that only forward calls;
- dependency-injection framework;
- permission matrix or role hierarchy;
- new application state machine duplicating ScheduleVersion status;
- generic rule engine;
- generic UNSAT/conflict analyzer;
- application-side solver logic;
- DTO copies of every domain entity;
- a separate use-case class for every button unless it is genuinely useful in code.

One small `rota/application/` package with ordinary Python functions or one small service object is enough.

The test for every abstraction is: does it own a real T009 responsibility? If not, do not add it.

## DEPENDENCY BOUNDARY

Required direction:

```text
future UI / T010
      |
      v
rota/application
   |          |
   v          v
persistence  planning
      \      /
       domain
```

Rules:
- application may call persistence and planning;
- application contains no SQL/table names;
- persistence does not import application or call PlanningEngine;
- planning does not import persistence/application;
- future UI/T010 must not assemble PlanningState or write SQLite directly.

Do not move new orchestration into legacy `backend.py`.

## COORDINATOR CONTEXT

For coordinator-originated writes, require:
- active Coordinator;
- active Site;
- active CoordinatorSiteAssociation for that coordinator/site.

This is only basic context integrity. Do not create a new authorization subsystem.

## ONE CANONICAL PLANNINGSTATE ASSEMBLER

T009 MUST provide one application-side assembler that builds PlanningState from LocalStore for `(site_id, month, schedule_version_id)`.

It loads/derives:
- Site and SiteProfile;
- complete CalendarDay month data;
- SiteMemberships and referenced Employees;
- relevant ExternalSupportWindows;
- current active AvailabilityRecords;
- monthly SiteRules through existing `assemble_monthly_site_rules(conn, site_id, month)` with NO caller rule IDs;
- resolved rules, unresolved rules and T007 applicability separately;
- chosen ScheduleVersion demands/assignments/deviations;
- WorkBalance from persisted targets + current-version facts;
- holiday history from current REALIZED PRIMARY assignments on holidays;
- same-Site boundary assignments;
- relevant current assignments of the same Employees on other Sites;
- exact schedule_version_id.

Assembler is read-only.

For REST/LOAD boundary context use the accepted T008 interval queries with:
- `context_start = first day of month - 6 days`;
- `context_end = first day of next month + 7 days`, exclusive.

Do not duplicate target-version assignments inside boundary context.
Use current ScheduleVersions only for surrounding/cross-Site context.

Missing CalendarDay for any date in the month is incomplete input. Do not guess `holiday=false` and do not call a network calendar.

Missing target_hours remains missing. Do not invent zero or a norm; it may be surfaced as a warning and omitted from target-based SOFT context.

## INITIAL SHIFTDEMAND GENERATION

When no ScheduleVersion exists yet, generate month ShiftDemand deterministically from SiteProfile.standard_shifts:
- every calendar day;
- one occurrence per configured StandardShift;
- start/end/end_next_day from profile;
- required_primary_count from profile.

Demand generation MUST NOT depend on roster size, target_hours, absences or X/Y.

This is simple data expansion, not planning.

## APPLICATION OPERATIONS

Exact function/class names are implementation choice. The following behaviors must exist.

### 1. Open Site/month

Read-only.

Return enough existing domain/read-model data for later UI:
- Site/Profile;
- Employees/memberships/current availability;
- active + unresolved rules;
- current ScheduleVersion if any;
- version history;
- available WorkBalance context;
- input warnings.

Opening MUST NOT create a version, call plan(), change current reference or write business data.

### 2. Precheck

Assemble fresh context and run a simple precheck.

The integrated base has no public precheck primitive, so T009 MAY add one small pure planning function.

Precheck:
- returns only `NO_OBVIOUS_SHORTAGE` or `LIKELY_INSUFFICIENT + context`;
- never claims FEASIBLE;
- does not use CP-SAT;
- does not generate a candidate;
- does not access persistence.

If no ScheduleVersion exists, precheck may use ephemeral profile-derived demands without persisting a version.

### 3. PLAN

If no ScheduleVersion exists:
1. validate coordinator context;
2. generate profile-derived month demands;
3. create the first current WORKING ScheduleVersion with those demands and no invented assignments/deviations;
4. set applied_rule_version_ids from the currently assembled RESOLVED monthly rule versions;
5. assemble PlanningState from the durable version;
6. call real `PlanningEngine.plan()`.

If current is WORKING, assemble fresh state and call plan().

If current is FINAL, do not reopen it; caller must use REPLAN for a new child.

Planning result is passed through as FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.
Do not turn technical failure into shortage.
Do not auto-apply any DECISION_REQUIRED suggestion.
Do not auto-save the first FEASIBLE candidate.

### 4. Select one FEASIBLE candidate

Coordinator chooses one candidate.

Before saving:
- target version must still be current WORKING;
- validate the supplied candidate against fresh assembled context using existing independent validator;
- reject if HARD-invalid;
- refresh applied_rule_version_ids;
- persist the complete selected working snapshot through T008 lifecycle.

No in-memory candidate registry is required.

### 5. REPLAN

Explicit REPLAN always creates a NEW WORKING child from the current version before calling PlanningEngine.

Child starts as a complete clone of parent month state.
T008/T006 invariants remain authoritative:
- REALIZED preserved exactly;
- future frozen preserved;
- planned TRAINEE/training decision preserved;
- FINAL parent remains immutable;
- solver ranking remains HARD -> minimum reshuffle -> existing SOFT.

After child creation, assemble fresh context and call real plan().
Do not auto-save a returned candidate.

### 6. Change durable input, then plan again

Application exposes thin commands for existing durable facts needed by coordinator workflow:
- ExternalSupportWindow;
- AvailabilityRecord append/supersede/deactivate;
- Employee current fields;
- SiteMembership/readiness override;
- target_hours;
- SiteProfile configuration.

These commands should normally validate context and delegate to existing repositories. Do not wrap every repository method in a new abstraction unless application behavior is added.

Mandatory flow:
`PLAN -> DECISION_REQUIRED -> coordinator changes one durable input (for example adds X window) -> PLAN again on fresh PlanningState`.

No hidden temporary solver override.

### 7. Structured SiteRule decision seam for T010

Expose one structured application command that calls accepted T005 `record_decision`.

Caller supplies explicit structured values already resolved by somebody else:
- site/coordinator/rule ids;
- exact statement;
- effective_from;
- T005 relation / first-decision semantics;
- NewRuleContent when applicable.

T009 MUST NOT infer rule_kind, employee, category, enforcement or dates from text.
No parser, LLM or DSL in T009.

### 8. Manual schedule edit + validation

Coordinator may edit the real working schedule, including:
- add/edit/cancel PRIMARY;
- split one demand across sequential PRIMARY assignments;
- repair or create a coverage gap;
- add/edit/cancel TRAINEE;
- freeze/unfreeze assignment.

If current version is FINAL, create a WORKING child first.
If current is WORKING, edit current working snapshot.

Manual state may be saved even when it contains a coordinator-created coverage or protected-rule violation that the solver itself would never create.

Immediately after each material edit:
- run existing validator;
- do NOT call REPLAN automatically;
- materialize current persistent violations as Deviations;
- remove stale Deviations that no longer exist;
- update WORKING vs WORKING_WITH_DEVIATIONS through T008 snapshot lifecycle.

Manual assignment is not frozen automatically.

Deviation.source_reference must be the exact rule_version_id or stable built-in condition code.

Use one small explicit mapping table, not a classifier/rule engine:
- COVERAGE-01 -> COVERAGE;
- DAY_SHIFT_OFF-01 / LEAVE_GRANTED-01 / UNAVAILABLE-01 / SICK_LEAVE-01 -> LEAVE_OR_TIME_OFF;
- LOAD-01 -> HOURS;
- REST-01 / EMP-02 -> LAW;
- CLIENT_REQUIREMENT SiteRule -> CLIENT_REQUIREMENT;
- current known non-law/non-client operational conditions (`DAY_ONLY-01`, `MEMBERSHIP-01`, `EXTERNAL-01`, LOCAL_RULE, CONFIRMED_EXCEPTION) -> PREFERENCE reporting bucket only.

`PREFERENCE` as Deviation category does NOT make a HARD condition soft.
Unknown future source fails closed instead of being guessed.

### 9. Training S readiness

Training remains ordinary Assignment data; no TrainingRecord.

Application supports add/edit/cancel TRAINEE and marking actual training REALIZED.
Existing frozen mentor/weekday/profile rules remain unchanged.

After a qualifying TRAINEE becomes REALIZED:
- if readiness_source == DEFAULT and realized training count reaches the profile threshold, update membership readiness to READY_FOR_PRIMARY;
- if readiness_source == COORDINATOR_OVERRIDE, do not overwrite it.

### 10. Revalidate / finalize / restore

Revalidate current WORKING against fresh rules/availability/windows/context:
- do not move assignments;
- refresh Deviations;
- refresh applied_rule_version_ids;
- persist complete working snapshot.

Finalize always performs fresh revalidation first.

If deviations exist, finalization succeeds only when caller consciously acknowledges the exact current deviation set. Application stamps acknowledged_by/acknowledged_at and optional reason, then delegates to T008 finalization.

Restore/select an earlier ScheduleVersion only moves the T008 current reference. Never delete later history. Editing a restored FINAL creates a new child first.

### 11. SiteMemory read

Expose simple application reads needed by future UI:
- effective/active rules for Site/month;
- unresolved rules;
- rule version history;
- DecisionRecord chain for a rule family.

Do not create a new audit subsystem. This is just access to the memory already stored by T005.

### 12. Backup and diagnostic ZIP

These operations stay behind application boundary so future UI does not implement storage/privacy logic itself.

Backup:
- caller supplies destination;
- use consistent SQLite backup semantics;
- no cloud behavior.

Diagnostic ZIP is opt-in and filtered. It MUST exclude by default:
- employee names;
- medical/absence note text;
- full Assignment schedule content;
- tokens/passwords/secrets;
- full database.

It may contain small technical metadata such as schema version, counts, selected IDs, stable result/condition codes and sanitized exception information.

No telemetry/upload service.

## TRANSACTION / RESTART RULES

Do not bypass T008 atomic lifecycle helpers with application SQL.

One application write either succeeds through repository/lifecycle operations or leaves the prior durable aggregate intact.

After DB close/reopen, application must reconstruct planning context from LocalStore. No correctness may depend on an in-memory selected Site/month/version/candidate session.

## OUT OF SCOPE

T009 does NOT implement:
- natural-language parsing or clarification dialogue;
- LLM runtime;
- rule inference;
- universal DSL;
- React/desktop UI/IPC;
- printing;
- cloud/SaaS sync;
- event bus/plugin framework;
- future industries;
- new SiteRule kinds;
- new solver objectives/HARD semantics;
- new persistence database;
- benchmark redesign.

## REQUIRED TESTS — SMALL INTEGRATION MATRIX

Use real temporary SQLite LocalStore and real PlanningEngine where planning is involved.

The implementation must prove at least:

1. implementation base is exactly `81c30912bb24ed70a6cc095916fd2d3b6a2071fb` and accepted T004-T008 lineage is present;
2. opening a month performs no write;
3. first PLAN creates one full profile-derived WORKING version and uses remembered SiteRules without caller rule IDs;
4. restart reconstructs the same rule/employee/calendar/current-version context;
5. missing calendar day is rejected as incomplete input; missing target_hours is not invented and does not change demand count;
6. boundary and cross-Site current assignments enter PlanningState; non-current historical versions do not;
7. FEASIBLE candidate is not persisted until selected; a HARD-invalid supplied candidate is rejected;
8. DECISION_REQUIRED + persisted X/Y window + PLAN again uses X/Y only inside that window;
9. REPLAN creates a child, preserves parent history/REALIZED/frozen/TRAINEE and preserves T006 minimal-reshuffle behavior;
10. manual coverage gap can be stored, immediately validates to COVERAGE Deviation, and does not trigger implicit REPLAN;
11. manual split coverage is storable and validates correctly;
12. freeze/unfreeze affects later REPLAN as already frozen by T006;
13. REALIZED training updates default readiness at configured threshold but never overwrites COORDINATOR_OVERRIDE;
14. finalization revalidates fresh, requires exact current deviation acknowledgement, and freezes FINAL;
15. restoring an older version only moves current reference; later history remains readable;
16. structured rule command reaches T005 Decision Ledger without parser/persistence exposure to future T010;
17. backup is openable and diagnostic ZIP proves prohibited data is absent;
18. dependency scan proves: no persistence import from planning, no application import from persistence, no SQL/UI/NLP in application.

Do not create a separate test framework for T009. Ordinary pytest integration tests are enough.

## ENGINEERING GATES

Before Codex implementation audit:
- existing suite PASS;
- new T009 tests PASS;
- ROTA-REG-001 unchanged;
- Ruff PASS;
- `git diff --check` PASS;
- existing file/function size guards PASS;
- zero dependency-boundary violations above.

The abandoned real-object benchmark is NOT an acceptance gate.

## ACCEPTANCE

T009 is complete when a future UI/T010 caller can use one thin application boundary to:

- open Site/month;
- precheck/PLAN/select candidate;
- change durable coordinator inputs and plan again;
- REPLAN;
- manually edit/validate/freeze/train;
- revalidate/finalize/restore;
- read SiteMemory;
- backup/export filtered diagnostics;

without knowing SQLite or assembling PlanningState itself.

LocalStore stores. SiteMemory remembers. PlanningEngine plans/validates. Application only coordinates them.

## REVIEW REQUEST TO CODEX

Audit this contract only for:
1. contradiction with frozen architecture / accepted T004-T008;
2. genuine ambiguity that would force CC to invent behavior;
3. testability;
4. accidental scope leakage into T010 or T012;
5. accidental bureaucracy/architecture that is not needed to perform the use cases.

Expected result: `PASS / READY_FOR_IMPLEMENTATION` or precise contract findings.
Do not implement while reviewing.
