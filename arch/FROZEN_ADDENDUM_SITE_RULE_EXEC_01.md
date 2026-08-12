# FROZEN PRODUCT CONTRACT ADDENDUM — SITE-RULE-EXEC-01

ADDENDUM_ID: SITE-RULE-EXEC-01
DATE: 2026-08-12
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_IMPLEMENTATION_SHA: b97b762b3dfb4eef9d43a747a064e3b1e1144786
OWNER_DECISION_SOURCE: direct owner request in architecture session 2026-08-12

## OWNER DECISION

Literal owner request:

`Możesz napisać zadanie by solver korzystał z tych pamięci, bo obecnie z tego co mówił codex nie ma nic co mu karze to zrobić.`

Product meaning:

SiteMemory is not only historical storage. Active, structured SiteRule versions remembered for a Site must become planning input and must affect PlanningEngine according to their frozen rule semantics. A supported active rule must never be silently ignored.

## SOURCE SUPPORT

This addendum closes an extraction/implementation gap already present in the product sources:

- product spec 02, §10.3: the pilot must express at least required shift type, forbidden employee assignment, assignment allowed only in specified time (examples: only nights / only weekends), day-related requirements and time-bound requirements;
- product spec 02, §10.7: an unrecognized requirement remains NEEDS_RESOLUTION and is not automatically interpreted by the solver;
- product spec 02, §11.4: active Site rules applicable to the planning period are recalled automatically; coordinator does not re-enter or manually search for them every month;
- product spec 02, §11.5: SiteMemory remembers rules/history/source/period/status; solver applies active structural rules, detects conflict and assesses feasibility;
- architecture reference 03: RULE-08 profile owns supported rule kinds and interpretation; MEMORY-01..03 separate memory retrieval from PlanningEngine persistence ownership;
- current frozen arch/spec.md already says executable SiteRule must be structured, NEEDS_RESOLUTION must not execute, INFORMATIONAL must not constrain planning, HARD is protected, and PlanningState.site_rules is the executable set.

## SITE-RULE-EXEC-01 — MEMORY MUST REACH PLANNING

For every initial PLAN and every REPLAN of one Site/month:

1. Before PlanningEngine is called, an application/persistence assembly layer MUST automatically retrieve every SiteRule family belonging to the Site.
2. It MUST project the rule state that is actually effective during the planning month, including mid-month supersedes/corrects/rejects and inclusive effective_to semantics.
3. PlanningEngine MUST receive this prepared rule context through PlanningState. PlanningEngine MUST NOT read SQLite, SiteMemory repositories or Decision Ledger directly.
4. Every RESOLVED + supported + HARD rule effective for a demand MUST constrain automatic PRIMARY assignment.
5. A supported active HARD rule MUST NOT be silently ignored to obtain FEASIBLE.
6. NEEDS_RESOLUTION remains display-only and MUST NOT constrain planning.
7. INFORMATIONAL remains non-constraining.
8. A RESOLVED rule that claims to be executable but has an unsupported rule_kind or malformed parameters is a model/capability error and MUST produce TECHNICAL_ERROR rather than being silently ignored.
9. Normal infeasibility caused by valid HARD SiteRules is NOT TECHNICAL_ERROR. It follows the existing DECISION_REQUIRED/feasibility contract and must identify the relevant rule_version_id as a blocker/source reference.

## MONTHLY APPLICABILITY PROJECTION

SiteRuleVersion persistence remains immutable and must not be rewritten merely to derive a planning interval.

Add an ephemeral planning projection:

`SiteRuleApplicability`
- rule_version_id
- applies_from: date (inclusive)
- applies_to: date (inclusive)

PlanningState keeps the exact persisted SiteRuleVersion objects and receives applicability slices separately.

Monthly assembly semantics:

- enumerate all rule families for site_id automatically; caller must not provide a hand-maintained rule_id list;
- for every calendar day in the target month, use T005 effective selection semantics to determine the effective rule for each family;
- NO_ACTIVE_RULE contributes nothing for that day;
- consecutive days selecting the same rule_version_id are coalesced into one SiteRuleApplicability slice;
- a rule version may therefore have an effective planning slice shorter than its persisted effective_to when a later decision supersedes/corrects/rejects it;
- the persisted SiteRuleVersion itself is never modified to encode that derived slice;
- all distinct RESOLVED versions selected for at least one day enter PlanningState.site_rules;
- all distinct NEEDS_RESOLUTION versions selected for at least one day enter PlanningState.unresolved_site_rules;
- applicability slices may reference either set, but only RESOLVED supported executable rules can affect PlanningEngine.

This projection exists because PlanningState covers a full month while T005 history can change state inside that month.

## INITIAL EXECUTABLE RULE CATALOG — PROFILE OCHRONA

Do NOT build a universal rule language.

Initial supported structural rule kinds are deliberately small and correspond to the source product requirements.

### 1. EMPLOYEE_ALLOWED_SHIFT_KINDS

Parameters:
- employee_id: non-empty string
- allowed_shift_kinds: non-empty JSON list containing only `D` and/or `N`

HARD semantics:
For automatic PRIMARY assignment of this employee, the ShiftDemand classification MUST be one of allowed_shift_kinds.

Example:
`allowed_shift_kinds=["N"]` means the employee may be automatically assigned only to N.

### 2. EMPLOYEE_ALLOWED_WEEKDAYS

Parameters:
- employee_id: non-empty string
- allowed_weekdays: non-empty JSON list of ISO weekdays 1..7 (Monday=1, Sunday=7)

HARD semantics:
For automatic PRIMARY assignment of this employee, the start date of the ShiftDemand MUST have an ISO weekday contained in allowed_weekdays.

Example:
`allowed_weekdays=[6,7]` means only shifts STARTING on Saturday or Sunday are allowed.

### 3. EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS

Parameters:
- employee_id: non-empty string
- weekdays: non-empty JSON list of ISO weekdays 1..7
- forbidden_shift_kinds: non-empty JSON list containing only `D` and/or `N`

HARD semantics:
For automatic PRIMARY assignment of this employee, assignment is forbidden when BOTH:
- demand.start_datetime.date().isoweekday() is in weekdays; and
- classified ShiftKind is in forbidden_shift_kinds.

Example:
`weekdays=[5], forbidden_shift_kinds=["D"]` means no Friday D for that employee, while Friday N remains allowed.

## DAY ANCHOR

For the initial weekday-based SiteRule kinds, the relevant day is the calendar date on which the ShiftDemand starts.

Therefore:
- N Thursday 17:00 -> Friday 05:00 belongs to Thursday for these rule kinds;
- N Friday 17:00 -> Saturday 05:00 belongs to Friday.

This follows the existing Rota convention used by day-start restrictions such as DAY_SHIFT_OFF and gives one deterministic interpretation for overnight shifts.

## PARAMETER TYPE / JSON BOUNDARY

T007 closes the RuleParameters CONTRACT_GAP only for the initial catalog above.

Use an explicit typed union (TypedDict or equivalent typed structures) for the three supported parameter shapes while preserving T005's JSON persistence boundary.

Persistence still stores JSON-compatible values; it does not interpret rule semantics.

Execution layer validates exact shape and values before solve. Unknown keys, missing keys, invalid weekdays, empty lists, invalid ShiftKind values or wrong value types are malformed executable rules.

Do not infer parameters from free text in this addendum/task.

## ENFORCEMENT SCOPE FOR THIS ADDENDUM

The first executable catalog is frozen for HARD execution.

- HARD: execute exactly as defined above.
- INFORMATIONAL: never constrains planning.
- SOFT SiteRule ranking is NOT defined by this addendum. Do not invent a numeric weight. Until a separate profile SOFT policy is frozen, a RESOLVED SOFT SiteRule must not be silently treated as HARD or ignored; if it reaches the executable PlanningState set, PlanningEngine returns TECHNICAL_ERROR identifying rule_version_id.

This is intentionally narrow because the source pilot treats client requirements as HARD and the current product contract does not freeze relative ranking weights for arbitrary SOFT SiteRules.

## MULTIPLE RULES

All applicable HARD SiteRules combine by conjunction: every applicable HARD rule must pass.

If multiple valid HARD rules make coverage impossible, the result follows the existing DECISION_REQUIRED contract. Solver MUST NOT drop one of the rules automatically.

When a SiteRule is the reason an employee cannot cover a demand, blocker/source reference is its `rule_version_id`, not a newly invented generic condition code.

## REPLAN / EXISTING ASSIGNMENTS

SITE-RULE-EXEC-01 applies to both PLAN and REPLAN.

- REALIZED remains untouched by REPLAN and is not retroactively invalidated solely because a later SiteRule would have blocked that historical automatic assignment.
- future frozen Assignment remains untouchable. If it conflicts with an applicable HARD SiteRule, the conflict is an autonomy boundary and must surface as DECISION_REQUIRED with the relevant rule_version_id, not be silently moved and not be mislabeled TECHNICAL_ERROR.
- redistributable PLANNED PRIMARY assignments may move according to the active REPLAN contract, including REPLAN-MIN-01 when that addendum is present on the implementation base.

## NO DIRECT PERSISTENCE COUPLING

PlanningEngine, solver, eligibility and validator MUST NOT:
- import sqlite3;
- import rota.persistence;
- open the Rota database;
- query Decision Ledger.

They consume only PlanningState and pure executable rule types/projections.

## INDEPENDENT VALIDATION

Every generated candidate must be independently validated against all applicable HARD SiteRules after solving.

The validator must re-check rule semantics against candidate Assignments and rule applicability; it must not assume that CP-SAT eligibility already guaranteed correctness.

A violation must carry/reference the exact `rule_version_id`.

## NON-GOALS

This addendum does not implement:
- natural-language parsing;
- LLM rule interpretation;
- UI;
- arbitrary client-specific DSL;
- generic boolean rule composition;
- automatic creation of new rule_kind;
- SOFT SiteRule weighting;
- persistence inside PlanningEngine.
