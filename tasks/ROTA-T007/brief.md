# TASK_CONTRACT

TASK_ID: ROTA-T007
TITLE: Executable SiteRules — SiteMemory -> PlanningState -> PlanningEngine
STATUS: ARCHITECTURE_APPROVED_FOR_IMPLEMENTATION
DATE: 2026-08-12
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes

FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md
BASE_REQUIRED: accepted ROTA-T005 implementation SHA b97b762b3dfb4eef9d43a747a064e3b1e1144786 or a later accepted integration base containing it

## SEQUENCING WITH ROTA-T006

ROTA-T006 (REPLAN minimal reshuffle) and ROTA-T007 both touch PlanningEngine/solver behavior.

Do not implement them in parallel on divergent solver bases.

If T006 is implemented/accepted first, T007 task_init MUST use the accepted T006 SHA as its base.
If T007 is implemented/accepted first, T006 must later rebase/review against the accepted T007 SHA.

No semantic dependency requires T006 to exist for initial PLAN, but an implementation base containing REPLAN-MIN-01 must preserve it.

## OBJECTIVE

Make SiteMemory operationally authoritative for supported active SiteRules.

A rule saved and remembered by T005 must be capable of changing the result of `PlanningEngine.plan()` without PlanningEngine reading the database.

Required vertical path:

`Decision Ledger / SiteRuleVersion in SQLite`
`-> monthly SiteMemory projection`
`-> PlanningState`
`-> executable rule validation`
`-> solver eligibility/constraints`
`-> independent validator`
`-> FEASIBLE or DECISION_REQUIRED with rule_version_id provenance`

T007 is NOT PASS if rules are merely loaded into PlanningState but ignored by the solver.

## CURRENT GAP CONFIRMED IN BASE

At accepted T005 SHA:

- PlanningState already has `site_rules` described as RESOLVED/executable and `unresolved_site_rules` as display-only;
- T005 can persist/history/retrieve rules and assemble effective rules;
- `rota/planning/eligibility.py` explicitly says SiteRuleVersion is intentionally not interpreted because `rule_kind` catalog is CONTRACT_GAP;
- solver therefore has no constraint that uses `PlanningState.site_rules`.

T007 closes exactly that gap.

## SOURCE AUTHORITY

Use:
- frozen arch/spec.md RULE-01..RULE-05, STATE-01, PlanningEngine no-persistence boundary;
- `arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md`;
- product source 02 §10.3, §10.7, §11.4, §11.5;
- architecture reference 03 RULE-08 and MEMORY-01..03;
- accepted T005 behavior for effective selection/history.

Do not infer additional product rule kinds.

## DOMAIN / EXECUTION TYPES

### RuleParameters

Replace the placeholder `RuleParameters = object` with a typed union covering only the three initial supported parameter shapes.

The persisted representation must remain JSON-compatible and round-trip through T005 unchanged.

Recommended technical shape: TypedDict-based union using plain JSON scalar/list values.

Required parameter schemas:

### EMPLOYEE_ALLOWED_SHIFT_KINDS

- employee_id: str, non-empty
- allowed_shift_kinds: list of `D|N`, non-empty

### EMPLOYEE_ALLOWED_WEEKDAYS

- employee_id: str, non-empty
- allowed_weekdays: list[int], non-empty, every value 1..7 ISO weekday

### EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS

- employee_id: str, non-empty
- weekdays: list[int], non-empty, every value 1..7
- forbidden_shift_kinds: list of `D|N`, non-empty

Execution parser/validator must reject malformed values before solve.

Do not make persistence understand these schemas. Persistence remains generic JSON transport.

## RULE KIND REGISTRY

Profile OCHRONA supports exactly these executable T007 kinds:

- `EMPLOYEE_ALLOWED_SHIFT_KINDS`
- `EMPLOYEE_ALLOWED_WEEKDAYS`
- `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`

No prefix matching, free-text matching or fallback interpretation.

Unknown RESOLVED HARD rule_kind = TECHNICAL_ERROR with rule_version_id.
Unknown NEEDS_RESOLUTION rule_kind remains non-executable and must not cause TECHNICAL_ERROR merely because it is stored/displayed.

## MONTHLY SITEMEMORY PROJECTION

T005's single-date `effective_rule_on()` is the source of truth for effective selection.

Add a monthly assembly operation outside `rota/planning/` that:

1. discovers all rule_id families belonging to `site_id` from persistence; caller does not supply a manually curated list;
2. walks every date in the target month;
3. for each `(rule_id, date)` calls/reuses T005 effective-selection semantics;
4. omits NO_ACTIVE_RULE days;
5. collects exact persisted SiteRuleVersion objects selected during the month;
6. coalesces consecutive dates selecting the same rule_version_id into applicability slices;
7. returns RESOLVED and NEEDS_RESOLUTION versions separately plus applicability slices.

Introduce ephemeral non-persisted type:

`SiteRuleApplicability`
- rule_version_id: str
- applies_from: date inclusive
- applies_to: date inclusive

Do not mutate stored SiteRuleVersion.effective_to to encode supersession/rejection-derived ends.

## PLANNINGSTATE CHANGE

PlanningState retains:
- `site_rules`: distinct RESOLVED SiteRuleVersion objects applicable for at least one day in the month;
- `unresolved_site_rules`: distinct NEEDS_RESOLUTION SiteRuleVersion objects applicable for at least one day in the month.

Add:
- `site_rule_applicability: tuple[SiteRuleApplicability, ...]`

PlanningEngine receives only this in-memory context.

All test/state builders must provide the new field explicitly; no hidden database access or global singleton.

## APPLICABILITY TO A DEMAND

A SiteRuleVersion constrains a ShiftDemand only when there is a `SiteRuleApplicability` slice for that rule_version_id satisfying:

`applies_from <= demand.start_datetime.date() <= applies_to`

For weekday-based rules, the day is `demand.start_datetime.date()`.

Overnight examples:
- Thursday N 17:00 -> Friday 05:00 is Thursday for weekday rule evaluation;
- Friday N 17:00 -> Saturday 05:00 is Friday.

## HARD EXECUTION SEMANTICS

T007 executes the initial catalog only when `enforcement == HARD` and `resolution_status == RESOLVED`.

### EMPLOYEE_ALLOWED_SHIFT_KINDS

For matching employee_id, automatic PRIMARY Assignment is eligible only if classified ShiftKind is in allowed_shift_kinds.

### EMPLOYEE_ALLOWED_WEEKDAYS

For matching employee_id, automatic PRIMARY Assignment is eligible only if demand start date ISO weekday is in allowed_weekdays.

### EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS

For matching employee_id, automatic PRIMARY Assignment is ineligible when both:
- demand start ISO weekday is in weekdays; and
- classified ShiftKind is in forbidden_shift_kinds.

Rules for another employee do not affect the current employee.

Multiple applicable HARD rules combine with logical AND. Every applicable rule must pass.

## INFORMATIONAL / UNRESOLVED / SOFT

### NEEDS_RESOLUTION

Never execute. It remains in `unresolved_site_rules` only.

### INFORMATIONAL

Never constrains planning.

### SOFT

T007 does not define arbitrary SiteRule SOFT weighting.

Do NOT:
- silently ignore a RESOLVED SOFT executable rule;
- treat it as HARD;
- invent `SITE_RULE_WEIGHT`;
- map it to TARGET_DEVIATION_WEIGHT by guess.

If a RESOLVED SOFT SiteRule reaches executable `site_rules` before a later SOFT-policy task freezes its ranking semantics, PlanningEngine returns TECHNICAL_ERROR identifying rule_version_id.

## SOLVER INTEGRATION

SiteRule execution must be part of slot eligibility/constraint construction, not a post-hoc warning only.

For an applicable HARD rule violation:
- the employee/demand slot is not eligible;
- blocker condition/source is the exact `rule_version_id`;
- solver must not create that Assignment merely because doing so improves target/fairness/coverage objective.

Valid SiteRule-induced staffing infeasibility remains normal domain infeasibility:
- not TECHNICAL_ERROR;
- use existing DECISION_REQUIRED path;
- include concrete blocking demand and blocker with `condition = rule_version_id`.

Do not introduce generic condition code like `SITE_RULE_BLOCK`; provenance must identify the actual version.

## VALIDATION

Independent validator must re-check every applicable HARD SiteRule against every generated automatic PRIMARY Assignment.

It must not trust solver slot filtering as proof.

Any violation is HARD FAIL and references the exact rule_version_id.

T007 is FAIL if deleting/bypassing solver rule filtering could allow a candidate through validator.

## REPLAN EXISTING ASSIGNMENTS

Preserve existing REPLAN semantics.

- REALIZED work is untouched and is not retroactively made invalid solely by a later SiteRule.
- future frozen Assignment cannot be moved. If it conflicts with an applicable HARD SiteRule, surface DECISION_REQUIRED/autonomy boundary with rule_version_id.
- PLANNED non-frozen redistributable PRIMARY may be reassigned to satisfy active SiteRules.
- if implementation base contains REPLAN-MIN-01, the minimal-reshuffle objective remains mandatory after HARD validity; SiteRules are HARD and therefore outrank reshuffle minimization.

## PLANNINGENGINE PERSISTENCE BOUNDARY

Forbidden imports/behavior inside `rota/planning/`:
- sqlite3;
- `rota.persistence`;
- DB path;
- Decision Ledger query;
- SiteMemory repository query.

PlanningEngine must remain deterministic from PlanningState input.

## REQUIRED INTEGRATION SCENARIO — TWO MONTHS

Create a real SQLite-backed integration test proving the complete path, not a fixture that inserts SiteRuleVersion directly into PlanningState.

Scenario:

1. Save through T005 Decision Ledger a RESOLVED HARD rule for employee A:
   - rule_kind = `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`
   - weekdays = [5]
   - forbidden_shift_kinds = ["D"]
   - effective period spans two consecutive planning months.
2. Close and reopen the database before at least one month to prove persistence is used.
3. For month 1, assemble monthly SiteRule context from SiteMemory and construct PlanningState from that projection.
4. Run real `PlanningEngine.plan()`.
5. Repeat for month 2 using the same remembered rule without re-entering it.

Assertions:
- A is never automatically assigned Friday D in either month;
- Friday N is still allowed by this rule;
- the test must contain a case where A is otherwise eligible/needed for Friday N so "N allowed" is actually demonstrated, not merely untested;
- no caller manually injects rule_id into the month assembler;
- PlanningEngine performs no persistence I/O.

This test represents the product promise: coordinator records a durable local rule once; later schedules automatically remember and apply it.

## REQUIRED TEST MATRIX

### A. BASELINE NO RULES
Same PlanningState with no applicable SiteRules retains pre-T007 solver behavior.

### B. ONLY N
HARD `EMPLOYEE_ALLOWED_SHIFT_KINDS {A,[N]}` blocks A from D and allows A on N.

### C. ONLY WEEKENDS
HARD `EMPLOYEE_ALLOWED_WEEKDAYS {A,[6,7]}` blocks starts Monday-Friday and allows Saturday/Sunday starts.

### D. FRIDAY D BLOCKED / N ALLOWED
HARD `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS {A,[5],[D]}` blocks Friday D but allows Friday N.

### E. OVERNIGHT DAY ANCHOR
Thursday N ending Friday is evaluated as Thursday; Friday N ending Saturday is evaluated as Friday.

### F. MID-MONTH SUPERSESSION
Two versions in one family change during a month. Monthly projection yields correct non-overlapping applicability slices and solver behavior changes on the exact effective date.

### G. MID-MONTH REJECT
Rule active early month, rejected later. No rule applies after reject date; stored old SiteRuleVersion remains immutable.

### H. NEEDS_RESOLUTION
Persisted active NEEDS_RESOLUTION version appears in unresolved context and has zero planning effect.

### I. INFORMATIONAL
RESOLVED INFORMATIONAL rule has zero planning constraint effect.

### J. UNKNOWN/MALFORMED EXECUTABLE
Unknown RESOLVED HARD rule_kind and malformed supported parameters each produce TECHNICAL_ERROR containing rule_version_id. Neither is silently ignored.

### K. CONFLICT / DECISION_REQUIRED
Valid HARD SiteRule makes a required demand impossible with available staffing. Result is DECISION_REQUIRED, not TECHNICAL_ERROR, and blocker condition includes rule_version_id.

### L. MULTIPLE RULES
Two applicable HARD rules for one employee combine by AND; solver cannot satisfy one while ignoring the other.

### M. INDEPENDENT VALIDATOR
Construct/corrupt a candidate containing an Assignment forbidden by an active HARD SiteRule. Validator must fail it independently with rule_version_id.

### N. PERSISTENCE RESTART / TWO MONTHS
Required two-month integration scenario above.

### O. NO PLANNING I/O
Static/import test confirms `rota/planning/` imports neither sqlite3 nor rota.persistence.

### P. REPLAN FROZEN CONFLICT
Applicable HARD SiteRule conflicts with future frozen Assignment. Frozen assignment is not moved; result follows DECISION_REQUIRED/autonomy-boundary semantics and identifies rule_version_id.

### Q. REALIZED HISTORY
A later SiteRule does not retroactively invalidate already REALIZED historical work.

## TASK_SCOPE

Allowed production areas:
- typed SiteRule parameter/execution types in `rota/`;
- `rota/domain.py` only to replace/point the RuleParameters placeholder to the typed union;
- `rota/persistence/site_rule_repository.py` for automatic family listing if needed;
- `rota/persistence/site_rule_assembly.py` for monthly projection;
- `rota/planning/state.py` for SiteRuleApplicability context;
- a focused `rota/planning/site_rules.py` or equivalent pure rule evaluator/parser;
- `rota/planning/eligibility.py`;
- `rota/planning/solver.py` only as necessary to pass rule context/reasons;
- `rota/planning/validator.py`;
- `rota/planning/engine.py` only for executable-rule prevalidation/status mapping;
- tests/support builders affected by PlanningState shape;
- dedicated T007 tests.

Keep modules within existing SIZE_FILE/SIZE_FUNC policy.

## OUT_OF_SCOPE

Do not implement:
- natural language parser / LLM interpreter;
- UI rule editor;
- automatic question asking;
- arbitrary DSL;
- arbitrary boolean conditions;
- new SiteRule categories;
- new persistence service/database;
- EME runtime dependency;
- SOFT SiteRule weighting;
- ScheduleVersion persistence changes;
- applied_rule_version_ids persistence lifecycle;
- calendar/holiday changes unrelated to weekday evaluation;
- new REPLAN semantics beyond preserving already-frozen T006 behavior if present.

## ACCEPTANCE CONTRACT

PASS requires all of the following:

1. SiteMemory rule families are discovered automatically for site_id; monthly caller does not supply rule_ids manually.
2. Monthly projection correctly handles effective_from, inclusive effective_to, supersedes, corrects, rejects and mid-month changes using T005 selection semantics.
3. Persisted SiteRuleVersion history remains immutable; derived applicability does not rewrite it.
4. PlanningState receives exact resolved/unresolved versions plus explicit applicability slices.
5. PlanningEngine performs zero persistence I/O.
6. RuleParameters is typed for exactly the three initial catalog kinds and remains JSON-compatible at persistence boundary.
7. Unknown/malformed RESOLVED HARD rules cannot be silently ignored.
8. NEEDS_RESOLUTION never constrains planning.
9. INFORMATIONAL never constrains planning.
10. T007 does not invent SOFT weight; unsupported RESOLVED SOFT fails explicitly rather than changing behavior silently.
11. Applicable HARD SiteRules constrain solver eligibility before search result is accepted.
12. Multiple HARD SiteRules combine by AND.
13. Weekday-based semantics use demand start date exactly.
14. HARD SiteRule blocker/source references exact rule_version_id.
15. Valid SiteRule-caused shortage/conflict maps to DECISION_REQUIRED, not TECHNICAL_ERROR.
16. Independent validator catches SiteRule HARD violations after solve.
17. REALIZED/frozen REPLAN protections remain intact.
18. REPLAN-MIN-01 remains intact on any base containing T006; HARD SiteRules outrank reshuffle minimization.
19. Two-month SQLite integration proves a remembered rule automatically affects real plan() after restart without re-entry.
20. Friday-D-block / Friday-N-allowed semantics are both positively demonstrated.
21. Existing regression suite remains green except tests intentionally updated for the new PlanningState field/previously missing SiteRule execution.
22. ROTA-REG-001 initial-planning oracle remains valid unless a direct conflict with an explicitly inserted SiteRule is part of the test; T007 must not rewrite the oracle to fit implementation.
23. Ruff, SIZE_FILE, SIZE_FUNC and git diff --check PASS.
24. No new product semantics are invented outside this Task Contract/addendum.

## AUDIT INSTRUCTIONS FOR CODEX

Codex must test behavior, not mere presence of code.

Required adversarial checks include:
- remove/bypass rule application and prove independent validator catches it;
- prove rule stored in SQLite and automatically projected, not manually injected into PlanningState;
- prove rule persists across restart and second month;
- prove a better TARGET/SOFT outcome cannot override HARD SiteRule;
- prove unknown RESOLVED rule cannot disappear silently;
- prove a reject gap really removes execution after its effective date;
- prove blockers/explanations use actual rule_version_id.

A PASS based only on unit-testing parser functions or checking that `state.site_rules` is non-empty is insufficient.

## PROCESS

1. Select one accepted integration base respecting the T006 sequencing note.
2. Run `task_init.py ROTA-T007` on that exact base.
3. CC implements only this Task Contract.
4. Codex audits exact implementation SHA with independent matrix.
5. Result returns to architect for final architectural PASS/FAIL.
6. Merge to main remains owner decision.
