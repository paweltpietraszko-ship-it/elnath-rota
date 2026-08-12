# ELNATH ROTA — ARCHITEKTURA v0.3 CANDIDATE

STATUS: CANDIDATE_AFTER_CONTRACT_REVIEW
SOURCE OF PRODUCT BEHAVIOR: ELNATH_ROTA_SPEC_PRODUKTOWA_v0.17_PL_CANDIDATE.md
SCOPE: product architecture
LANGUAGE: model-to-model / normative

OUT_OF_SCOPE:
- implementation plan;
- Elnath Ward tasking;
- solver algorithm;
- database technology/schema;
- desktop framework;
- generic future-industry framework.

PRINCIPLE:
Architecture MUST be precise where ambiguity can change a schedule, lose history, or prevent a required coordinator action.
It MUST NOT formalize implementation details without such a case.

---

## A0. SYSTEM SHAPE

```text
ELNATH ROTA
├── CORE
│   ├── Site
│   ├── Coordinator
│   ├── Employee
│   ├── SiteMembership
│   ├── AvailabilityRecord
│   ├── SiteRule / SiteMemory
│   ├── WorkBalance
│   ├── ScheduleVersion
│   ├── ShiftDemand
│   ├── Assignment
│   └── Deviation
├── SITE PROFILE
│   └── OCHRONA
├── PlanningEngine
├── DesktopUI
└── LocalStore
```

ARCH-01
`Site` is the concrete work object.
No separate SiteInstance layer.

ARCH-02
Pilot:
- 1 Site;
- 1 Coordinator;
- profile OCHRONA.

ARCH-03
Core MUST NOT structurally assume exactly one Site or Coordinator.

ARCH-04
Second Site(profile=OCHRONA) MUST be primarily data/configuration.
No copied OCHRONA planner.

ARCH-05
Future SKLEP MAY add profile-specific coverage/rules/policy.
It MUST NOT require redesign of shared identities/history.

ARCH-06
No Company entity in pilot architecture.

---

## A1. SITE / COORDINATOR / EMPLOYEE

### Site

ENTITY Site

REQUIRED:
- site_id
- profile_id
- display_name
- active

SITE-01
Site.profile_id selects SiteProfile semantics.

---

### Coordinator

ENTITY Coordinator

REQUIRED:
- coordinator_id
- display_name
- active

RELATION CoordinatorSiteAssociation:
- coordinator_id
- site_id
- active

PILOT:
- one Coordinator associated with pilot Site.

NO:
- role hierarchy;
- permission matrix;
- concurrent editing model.

---

### Employee

ENTITY Employee

REQUIRED:
- employee_id
- display_name
- active_from
- active_to optional

EMPLOYEE RESTRICTION:
- DAY_ONLY enabled=true|false

EMP-01
DAY_ONLY is a stable, toggleable Employee restriction.

EMP-02
An Employee is eligible for an Assignment only if the complete Assignment interval lies inside Employee active period.

EMP-03
Employee MUST NOT be structurally owned by exactly one Site.

OPEN-QUALIFICATION
Do not add qualification data unless pilot legal/site audit confirms that qualification changes assignment eligibility.
If required, store only the minimal fact needed for eligibility.

---

## A2. SITE MEMBERSHIP / EXTERNAL SUPPORT

ENTITY SiteMembership

REQUIRED:
- employee_id
- site_id
- membership_kind: LOCAL | EXTERNAL_SUPPORT
- enabled
- readiness_state: NOT_READY | READY_FOR_PRIMARY
- readiness_source: DEFAULT | COORDINATOR_OVERRIDE

MEMBERSHIP-01
LOCAL is eligible when:
- membership enabled;
- Employee active period covers Assignment;
- Employee restrictions allow Assignment;
- AvailabilityRecords allow Assignment;
- active rules allow Assignment.

MEMBERSHIP-02
EXTERNAL_SUPPORT is unavailable unless a confirmed ExternalSupportWindow covers the Assignment.

RELATION ExternalSupportWindow

REQUIRED:
- window_id
- employee_id
- site_id
- start_datetime
- end_datetime
- active

OPTIONAL:
- allowed_shift_kind: D | N

WINDOW-01
One EXTERNAL_SUPPORT membership MAY have N windows.

WINDOW-02
Only active windows make X/Y eligible.

WINDOW-03
Pilot does NOT model X/Y home-site HR, balances, or schedule.

---

## A3. CALENDAR / TIME

ENTITY CalendarDay

REQUIRED:
- date
- holiday

DERIVED:
- weekday from date
- weekend from weekday

CAL-01
Holiday information used by planning MUST be reproducible after application restart.

Implementation MAY persist CalendarDay records or derive them from a deterministic local calendar source.

CAL-02
Pilot plant working day:
Monday-Friday AND holiday=false.

CAL-03
Do NOT store `plant_working_day` as a second source of truth.

CAL-04
Holiday data MAY come from persisted CalendarDay records or a deterministic local calendar source, including a bundled structured data file.
PlanningEngine MUST NOT read CSV/JSON/calendar files directly.
Holiday data is resolved before planning and passed through PlanningState.

CAL-05
Historical holiday-load metrics are derived from persisted current-version Assignments joined with CalendarDay where holiday=true.
No manually maintained per-Employee holiday ledger is required.

TIME-01
Assignment uses actual interval:
[start_datetime, end_datetime)

TIME-02
Weekend work = Assignment interval intersects Saturday or Sunday.

TIME-03
Month is planning/version scope, not correctness boundary.

Planning and validation MUST include enough adjacent context to evaluate:
- cross-midnight work;
- rest continuity;
- assignments crossing month boundary;
- boundary availability.

TIME-04
Assignment belongs to the schedule month of its start_datetime.

---

## A4. AVAILABILITY / LEAVE

ENTITY AvailabilityRecord

KINDS:
- DAY_SHIFT_OFF
- UNAVAILABLE_24H
- LEAVE_PLAN
- LEAVE_GRANTED

REQUIRED:
- availability_id
- availability_version_id
- employee_id
- kind
- date_or_range
- active

OPTIONAL:
- supersedes_availability_version_id
- note

AV-01 — LEAVE_PLAN
- MUST NOT make Employee ineligible;
- PlanningEngine SHOULD avoid assigning inside the planned leave when a better solution exists;
- collision MUST produce a visible planning warning;
- MUST NOT be treated as LEAVE_GRANTED or UNAVAILABLE_24H.

AV-02 — LEAVE_GRANTED
- automatic plan MUST NOT create a colliding Assignment;
- manual Coordinator override is allowed;
- manual collision creates Deviation category LEAVE_OR_TIME_OFF.

AV-03 — DAY_SHIFT_OFF
- automatic plan MUST NOT assign D on that date;
- N MAY remain possible;
- manual Coordinator D assignment is allowed;
- manual collision creates Deviation category LEAVE_OR_TIME_OFF.

AV-04 — UNAVAILABLE_24H
- automatic plan MUST NOT create any Assignment whose actual interval collides with the unavailable range;
- manual Coordinator override is allowed;
- manual collision creates Deviation category LEAVE_OR_TIME_OFF.

AV-05
History is preserved by version chain.
A prior record superseded by a newer record is presented as changed.
Explicit withdrawal sets active=false.

No separate stored `CHANGED` state is required.

---

## A5. SITE RULE / SITE MEMORY

ENTITY SiteRule

RULE FAMILY:
- rule_id

RULE VERSION:
- rule_version_id
- site_id
- category: CLIENT_REQUIREMENT | LOCAL_RULE | CONFIRMED_EXCEPTION
- rule_kind optional when unresolved
- structured_parameters optional when unresolved
- enforcement: HARD | SOFT | INFORMATIONAL
- resolution_status: RESOLVED | NEEDS_RESOLUTION
- effective_from
- effective_to optional
- changed_at
- changed_by coordinator_id
- supersedes_rule_version_id optional

OPTIONAL:
- description
- source
- reason/note

RULE-01
Executable rule MUST be structured.

RULE-02
NEEDS_RESOLUTION:
- remains stored and visible;
- MUST NOT be executed by PlanningEngine.

RULE-03
INFORMATIONAL MUST NOT constrain planning.

RULE-04
HARD is protected from automatic violation.

RULE-05
SOFT MAY be traded according to active profile planning policy.

RULE-06
Rule version history is immutable.

RULE-07
Each SiteRule belongs to exactly one Site.

RULE-08
SiteProfile owns supported profile rule kinds and their interpretation.

RULE-09
Free text alone MUST NOT become executable planning logic.

MEMORY-01
SiteMemory = responsibility to remember SiteRule versions/history and retrieve applicable rules.

MEMORY-02
SiteMemory does NOT plan schedules.

MEMORY-03
PlanningEngine does NOT persist Site knowledge.

MEMORY-04
SiteMemory is NOT required to be a separate database, service, LLM system, or semantic search system.

---

## A6. BUILT-IN CONSTRAINT REFERENCES

Purpose:
Coordinator must be able to receive a concrete explanation even when a condition is not a SiteRule.

BUILT_IN_CONDITION_CODE examples:
- COVERAGE
- DAY_ONLY
- EMPLOYEE_ACTIVE_PERIOD
- DAY_SHIFT_OFF
- UNAVAILABLE_24H
- LEAVE_GRANTED
- CROSS_MONTH_REST
- WORK_TIME_RULE

COND-01
Every validation result that may become a Deviation MUST reference either:
- SiteRule.rule_version_id;
or
- a stable built-in condition code.

COND-02
This is an identifier convention, NOT a separate rule-engine component.

---

## A7. SITE PROFILE

CONCEPT SiteProfile

MUST define:
- coverage generation;
- standard shift semantics;
- profile-specific rule kinds;
- profile-specific planning policy;
- interpretation of relevant Employee restrictions.

MUST NOT own:
- Employee identity;
- Coordinator identity;
- ScheduleVersion history;
- WorkBalance identity.

---

## A8. PROFILE OCHRONA

PROFILE_ID: OCHRONA

STANDARD DEMAND:

D:
- 05:00–17:00
- required_primary_count=1

N:
- 17:00–05:00 next day
- required_primary_count=1

OCHRONA-01
Automatic planner generates only standard D/N demand.

OCHRONA-02
Demand comes from Site coverage requirement, never from Employee target hours.

OCHRONA-03
Employee.DAY_ONLY=true:
- automatic planner MUST NOT assign N;
- Coordinator MAY disable DAY_ONLY;
- Coordinator MAY manually override and accept resulting Deviation.

### Training S

OCHRONA-04
S = Assignment(role=TRAINEE).
S is NOT a third normal shift.

OCHRONA-05
TRAINEE:
- Monday-Friday only;
- exact interval chosen by Coordinator;
- counts toward trainee work hours;
- does NOT satisfy PRIMARY coverage;
- references mentor PRIMARY Assignment.

OCHRONA-06
Training history comes only from TRAINEE Assignments.
No TrainingRecord entity.

OCHRONA-07
Default readiness:
2 TRAINEE Assignments with state=REALIZED
-> READY_FOR_PRIMARY
only when readiness_source=DEFAULT.

OCHRONA-08
Coordinator MAY override readiness manually.
Override MUST persist.

---

## A9. SHIFT DEMAND / ASSIGNMENT / COVERAGE

### ShiftDemand

ENTITY ShiftDemand

REQUIRED:
- demand_id
- schedule_version_id
- start_datetime
- end_datetime
- required_primary_count

DEMAND-01
ShiftDemand is persisted as part of ScheduleVersion.

DEMAND-02
OCHRONA standard required_primary_count=1.

---

### Assignment

ENTITY Assignment

REQUIRED:
- assignment_id
- schedule_version_id
- employee_id
- start_datetime
- end_datetime
- role: PRIMARY | TRAINEE
- state: PLANNED | REALIZED | CANCELLED
- frozen

PRIMARY:
- covers_demand_id required

TRAINEE:
- mentor_primary_assignment_id required
- covers_demand_id absent

ASSIGN-01
Site is derived through ScheduleVersion.
No Assignment.site_id.

ASSIGN-02
No Assignment.source is required.

ASSIGN-03
REALIZED work MUST NOT be changed by REPLAN.

ASSIGN-04
future frozen Assignment MUST NOT be changed by REPLAN.

ASSIGN-05
Manual Assignment is NOT automatically frozen.

ASSIGN-06
Solver-generated OCHRONA PRIMARY normally covers one full D/N demand.

ASSIGN-07
Manual intra-month correction MAY split one ShiftDemand across N sequential PRIMARY Assignments.

Example VALID coverage:
- A 05:00–13:00
- B 13:00–17:00

ASSIGN-08
Coverage gaps or excess PRIMARY overlap MUST be detectable by validate().
They MUST NOT prevent storing the real operational state.

Coverage violation may create Deviation category COVERAGE.

ASSIGN-09
Actual interval is authoritative.
No `is_standard_shift` flag required.

ASSIGN-10
TRAINEE mentor PRIMARY:
- same ScheduleVersion;
- same Site via ScheduleVersion;
- overlaps trainee interval;
- role=PRIMARY.

ASSIGN-11
Planned TRAINEE Assignment is a Coordinator-fixed training decision.
REPLAN MUST NOT move or delete it automatically.

If REPLAN cannot preserve a valid mentor PRIMARY relationship:
- preserve training decision;
- report conflict;
- Coordinator decides.

---

## A10. WORK BALANCE

ENTITY WorkBalance

KEY:
- employee_id
- month

FIELDS:
- target_hours: Coordinator planning input
- planned_hours: derived from current ScheduleVersions
- realized_hours: derived from current ScheduleVersions
- month_balance
- unresolved_carryover: operational value; exact lifecycle OPEN

AGGREGATE:
- quarter_balance from monthly balances

WB-01
target_hours != planned_hours != realized_hours.

WB-02
target_hours is not an obligation frozen into one schedule revision.

WB-03
planned_hours MAY change after REPLAN.

WB-04
realized_hours MUST reflect actual recorded work.

WB-05
Hour calculations MUST use only current ScheduleVersion for each relevant (site_id, month).
Historical ScheduleVersions MUST NOT be summed into operational hour totals.

WB-06
If Employee works on multiple Sites, current versions across those Sites contribute to Employee totals.

WB-07
Exact legal/company settlement and unresolved carryover lifecycle remain OPEN pending audit.

---

## A11. PLANNING STATE

CONCEPT PlanningState
NOT a persisted domain entity.

SCOPE:
- one Site;
- one month;
- one current ScheduleVersion context.

INCLUDES:
- Site + SiteProfile;
- calendar + boundary context;
- eligible Employees/SiteMemberships;
- Employee active periods/restrictions/readiness;
- ExternalSupportWindows;
- applicable resolved SiteRules;
- unresolved SiteRules for display only;
- AvailabilityRecords;
- WorkBalance context;
- current ScheduleVersion content;
- adjacent boundary assignments;
- relevant assignments of same Employees on other Sites when such data exists.
- derived holiday-work history for eligible Employees, based on persisted Assignments and CalendarDay(holiday=true).

STATE-01
NEEDS_RESOLUTION SiteRule MUST NOT enter executable rule set.

STATE-02
Boundary context MUST be sufficient for cross-month validation.

---

## A12. PLANNING ENGINE

COMPONENT PlanningEngine
NO persistent business-state ownership.

### precheck(PlanningState)

OUTPUT:
- NO_OBVIOUS_SHORTAGE
- LIKELY_INSUFFICIENT + context

PRECHECK-01
MUST NOT claim FEASIBLE.

---

### plan(PlanningState)

OUTPUT STATUS:
- FEASIBLE
- DECISION_REQUIRED
- TECHNICAL_ERROR

FEASIBLE OUTPUT:
- candidate_schedules: 1..3 complete AssignmentSets
- per-candidate soft-quality summary
- warnings
- deviations

PLAN-01
FEASIBLE means all automatic HARD constraints are respected and no unacknowledged critical-load gate is exceeded.

PLAN-02
Each FEASIBLE candidate MAY contain:
- SOFT deviations;
- preference compromises;
- hour-target deviation;
- warnings.

PLAN-03
PlanningEngine MAY return up to 3 complete FEASIBLE candidates. It MUST NOT select the final business schedule for Coordinator. UI presents candidates and Coordinator selects one.

PLAN-04
Weekend fairness is SOFT and monotonic: candidate closer to ideal equal weekend distribution among relevant eligible Employees receives no worse weekend-fairness score than a more unequal candidate.

PLAN-04A
Holiday fairness is SOFT and historical.
Among HARD-valid candidates, PlanningEngine SHOULD prefer variants that reduce disparity in historical holiday-work load among Employees eligible for the relevant holiday Assignments.
Holiday fairness MUST NOT override HARD constraints.
Historical holiday load MUST be derived from persisted Assignment history joined with CalendarDay(holiday=true), not from a separately hand-maintained holiday roster.

PLAN-05
Critical-load gate:
- evaluate every rolling window of 7 consecutive days for every Employee;
- sum actual Assignment hours overlapping that window;
- more than 60 hours in any such window requires Coordinator decision;
- such candidate MUST NOT be returned as ordinary FEASIBLE until Coordinator explicitly accepts that critical load.

PLAN-06
DECISION_REQUIRED means automatic planner cannot produce an acceptable complete schedule with current inputs without either:
- violating/unlocking at least one protected HARD condition; or
- requiring unacknowledged critical load >60 h in a rolling 7-day window.

DECISION_REQUIRED MUST include where determinable:
- problematic ShiftDemands / periods;
- blocking Employees / conditions / rules;
- critical-load Employee + 7-day window + hours, if relevant;
- explicit available relief actions / HARD unlock options;
- needed external-support range, if relevant.

PLAN-07
DECISION_REQUIRED is not terminal planning failure. PlanningEngine MUST stop autonomous assignment, return the decision package, and wait for Coordinator to change/authorize an input. After that decision, planning runs again.

PLAN-08
PlanningEngine MUST NOT itself:
- create or activate X/Y support;
- recall Employee from LEAVE_GRANTED / time off;
- disable DAY_ONLY or another protected rule;
- accept critical load on Coordinator's behalf.

PLAN-09
PlanningEngine MUST NOT silently use X/Y outside active ExternalSupportWindow.

PLAN-10
Coverage demand remains 100%: every required D/N ShiftDemand must be covered by exactly one PRIMARY in a selected complete schedule. Partial coverage is not FEASIBLE.

---

### validate(PlanningState, AssignmentSet | CandidateAssignment)

OUTPUT:
- findings
- deviations
- source references
- explanations

VALIDATE-01
validate MUST NOT regenerate or modify Assignments.

VALIDATE-02
Manual edit triggers validation, not implicit REPLAN.

VALIDATE-03
Finding = non-persisted validation observation.

VALIDATE-04
If an issue must remain attached to a saved ScheduleVersion and/or be consciously accepted at finalization, it is materialized as Deviation.

VALIDATE-05
"Why?" MUST resolve to:
- rule_version_id;
or
- built-in condition code.

---

## A13. REPLAN

REPLAN operates on one Site + one month.

REPLAN-01
REPLAN creates a new WORKING ScheduleVersion derived from current version.

REPLAN-02
The new version contains complete month state.

REPLAN-03
Preserve unchanged:
- all REALIZED Assignments;
- all future frozen Assignments;
- planned TRAINEE Assignments and their training decision.

REPLAN-04
May redistribute:
- future unfrozen PRIMARY Assignments inside current month.

REPLAN-05
MUST NOT:
- alter realized work;
- alter frozen work;
- move/cancel TRAINEE automatically;
- add X/Y outside active support windows;
- modify SiteRules;
- modify next month's version.

REPLAN-06
Planned TRAINEE is attached to an existing mentor PRIMARY Assignment selected by Coordinator.
While that TRAINEE remains planned, REPLAN MUST preserve the referenced mentor PRIMARY needed to realize the training decision.
If another newly introduced HARD condition makes that impossible:
- report DECISION_REQUIRED / conflict;
- preserve the training decision;
- Coordinator resolves it.

---

## A14. SCHEDULE VERSION

ENTITY ScheduleVersion

REQUIRED:
- version_id
- site_id
- month
- parent_version_id optional
- created_at
- created_by coordinator_id
- status:
  - WORKING
  - WORKING_WITH_DEVIATIONS
  - FINAL_NO_DEVIATIONS
  - FINAL_WITH_DEVIATIONS
- applied_rule_version_ids

VERSION CONTENT:
- complete ShiftDemand set for month;
- complete Assignment state for month;
- Deviations belonging to version.

VER-01
A ScheduleVersion represents a complete reconstructable state of one Site/month.

VER-02
When new version is created, REALIZED Assignments from parent are copied semantically unchanged into child version.
Historical versions remain untouched.

VER-03
Exactly one current version reference exists for each (site_id, month).

VER-04
FINAL ScheduleVersion is immutable.

VER-05
If current version is FINAL and Coordinator starts material edit or REPLAN:
- create new WORKING child first;
- old FINAL remains history.

VER-06
A WORKING version MAY be edited during the current editing session.
Finalization freezes it as immutable FINAL.

VER-07
Restoring/selecting an earlier version changes current-version reference without deleting later history.

VER-08
applied_rule_version_ids describe the rule set used for current validation of that version.

For WORKING version:
- explicit validation under changed rules MAY replace this set and regenerate corresponding Deviations.

For FINAL version:
- set is immutable;
- changed rules require a new WORKING child.

VER-09
Assignment crossing month boundary belongs to version by Assignment.start_datetime.
Adjacent month reads it as boundary context.

---

## A15. DEVIATION

ENTITY Deviation

REQUIRED:
- deviation_id
- schedule_version_id
- category:
  - LAW
  - CLIENT_REQUIREMENT
  - LEAVE_OR_TIME_OFF
  - HOURS
  - PREFERENCE
  - COVERAGE
- source_reference
- affected_assignment_or_employee
- acknowledged

OPTIONAL UNTIL ACKNOWLEDGED:
- acknowledged_by
- acknowledged_at
- reason

DEV-01
source_reference =
- SiteRule.rule_version_id;
or
- built-in condition code.

DEV-02
Finalization with deviations requires conscious confirmation.

DEV-03
After confirmation:
- acknowledged=true;
- acknowledged_by required;
- acknowledged_at required.

DEV-04
reason remains optional.

DEV-05
Printed schedule MUST NOT show deviation history/categories/reasons.

---

## A16. DESKTOP UI BOUNDARY

PILOT MUST SUPPORT:
- open Site/month;
- manage Employees, availability, targets;
- show active and unresolved SiteRules;
- add/remove X/Y availability windows;
- add/edit/cancel S training + mentor;
- precheck;
- plan;
- REPLAN;
- manual edit;
- validate after edit;
- freeze/unfreeze;
- show warnings/deviations/explanations;
- finalize;
- restore/select earlier version;
- print;
- local backup;
- diagnostic ZIP.

UI MUST NOT own:
- solver policy;
- rule evaluation;
- legal work-time logic;
- work-hour calculation.

---

## A17. LOCAL STORE

MUST persist:
- Sites
- Coordinators
- CoordinatorSiteAssociations
- Employees
- SiteMemberships
- ExternalSupportWindows
- AvailabilityRecords/history
- SiteRules/versions
- WorkBalances
- ScheduleVersions
- ShiftDemands
- Assignments
- Deviations
- current-version references
- holiday/calendar data if not deterministically regenerated locally

STORE-01
Local durable persistence.

STORE-02
No cloud runtime required.

STORE-03
One physical local store is sufficient.

STORE-04
Application supports local backup.
Format OPEN.

STORE-05
Application creates opt-in diagnostic ZIP.

Diagnostic ZIP MUST exclude by default:
- employee names;
- medical details;
- full schedule content;
- passwords/tokens;
- full database.

Implementation ownership of filtering = OPEN.
UI MUST NOT bypass filtering.

---

## A18. KNOWN EXTENSION TESTS

TEST-EXT-01
Add second Site(profile=OCHRONA):
- new Site/config/memberships/rules/schedules;
- no copied planner.

TEST-EXT-02
Add additional Coordinators:
- add Coordinator + associations;
- no Site/ScheduleVersion redesign.

TEST-EXT-03
Future SKLEP:
MAY add different profile coverage/rules/policy;
MUST reuse shared identities/history/storage concepts.

No SKLEP functionality is implemented now.

---

## A19. CONTRACT BREAK TESTS

CB-01
LEAVE_PLAN overlaps planned Assignment:
- Employee remains eligible;
- visible warning exists.

CB-02
LEAVE_GRANTED overlaps automatic Assignment:
- automatic planner refuses;
- manual Coordinator override may be saved as Deviation.

CB-03
DAY_SHIFT_OFF:
- automatic D forbidden;
- N possible;
- manual D override may be saved.

CB-04
Current FINAL month -> REPLAN:
- new WORKING child;
- old FINAL reconstructable;
- realized work unchanged.

CB-05
v1/v2/v3 contain copied realized state:
- operational realized_hours counts current version only;
- no multiplication by version count.

CB-06
FEASIBLE candidate containing N,N or hour-target deviation:
- plan may return it among 1..3 complete candidates;
- deviations/warnings visible;
- status is FEASIBLE if all HARD and critical-load gate are respected.

CB-07
Manual real state:
A 05:00–13:00, then no coverage.
- state can be saved;
- validate reports COVERAGE issue/deviation;
- no fake full coverage.

CB-08
Manual split:
A 05:00–13:00
B 13:00–17:00
- one D demand fully covered.

CB-09
Two planned S trainings do NOT make Employee ready.
Two REALIZED S trainings do, unless Coordinator override exists.

CB-10
REPLAN with future S attached to mentor PRIMARY:
- training time/trainee preserved;
- referenced mentor PRIMARY is preserved while S remains planned;
- if a new HARD makes this impossible, return DECISION_REQUIRED/conflict, never silently move/delete training.

CB-11
Employee active_to before proposed shift:
- Employee ineligible.

CB-12
X has two separate confirmed windows:
- both can coexist;
- X eligible only inside active windows.

CB-13
SiteRule changes after FINAL:
- FINAL explanation remains tied to old rule versions;
- new rules require new WORKING child for revalidation/editing.

CB-14
Restart application:
- holidays used by planning remain reproducible;
- persisted schedule/version/availability/support data remains available.

CB-15
Second OCHRONA Site:
- no core/planner copy.

CB-16
Employee has 60 h in every rolling 7-day window:
- critical-load gate not triggered solely by this threshold.

CB-17
Employee has 72 h in at least one rolling 7-day window:
- ordinary FEASIBLE not allowed before Coordinator acknowledgement;
- DECISION_REQUIRED identifies Employee, exact 7-day window and hours.

CB-18
Five-person Site, temporary crisis leaves only two locally available Employees and full coverage is possible only with >60 h/7d:
- planner does not declare ordinary FEASIBLE;
- planner does not auto-add X/Y or recall leave/time-off Employee;
- DECISION_REQUIRED offers explicit relief choices.

CB-19
DECISION_REQUIRED followed by Coordinator activation of X support window:
- replanning uses X only inside confirmed window;
- if complete acceptable candidates now exist, returns FEASIBLE candidates.

CB-20
Multiple legal candidates:
- planner may return up to 3 complete candidates;
- Coordinator selects final candidate;
- no hidden automatic final-business-choice requirement.

---

## A20. NON-GOALS

DO NOT ADD without concrete product requirement:
- Company entity;
- multi-company SaaS;
- plugin ecosystem;
- microservices;
- event bus;
- cloud sync;
- distributed storage;
- universal rule DSL;
- universal industry solver;
- generic profile key-value bag;
- enterprise permission hierarchy;
- concurrent editing;
- API gateway;
- automated contract interpretation;
- LLM runtime dependency;
- full HR/payroll model;
- speculative qualification module;
- separate constraint/rule engine solely for metadata.

---

## A21. OPEN

OPEN-01
Exact remaining legal work-time rules for pilot Site beyond the confirmed operational contract (including 11 h minimum rest and allowed N,N); only rules that materially change Assignment eligibility belong here.

OPEN-02
Exact company settlement / unresolved carryover lifecycle.

OPEN-03
Whether pilot Site requires qualification-based eligibility.

CLOSED-04
Planner compares acceptable candidates using SOFT quality; it may return up to 3 complete candidates and Coordinator makes the final selection. HARD is never automatically traded for SOFT.

CLOSED-05
Weekend fairness = monotonic closeness to ideal equal weekend distribution among relevant eligible Employees.

OPEN-06
Planning algorithm / implementation technique.

OPEN-07
Persistence technology/schema.

OPEN-08
Desktop framework.

OPEN-09
Exact print format.

OPEN-10
Backup format.

OPEN-11
Implementation ownership of diagnostic filtering.

---

## A22. COMPACT CONTRACT

1. Site = concrete object; SiteProfile = planning semantics.
2. OCHRONA creates fixed D/N demand; hours target never creates demand.
3. Employee eligibility depends on active period, membership, restrictions, availability, rules, readiness, and external-support windows where relevant.
4. LEAVE_PLAN warns; LEAVE_GRANTED and UNAVAILABLE_24H block automatic assignment.
5. Coordinator may consciously override protected conditions; override becomes visible Deviation.
6. ScheduleVersion is a complete month state.
7. FINAL versions are immutable.
8. REPLAN creates a new WORKING child and preserves realized/frozen/training decisions.
9. Operational hour totals use current versions only, never sum historical revisions.
10. `plan()` may return 1..3 complete FEASIBLE candidates; Coordinator selects the final business schedule.
11. More than 60 h in any rolling 7 consecutive days is a critical-load decision gate, not ordinary FEASIBLE until Coordinator accepts it.
12. When normal planning cannot continue, return DECISION_REQUIRED with blockers and explicit HARD-unlock / relief options; do not terminally fail or auto-unlock them.
13. X/Y, recall from granted leave/time off, protected-rule override and critical-load acceptance are Coordinator decisions only.
14. Weekend fairness is SOFT: closer to ideal equal distribution is better.
15. Planned S is attached to an existing mentor PRIMARY and REPLAN preserves that relationship unless a new HARD makes it impossible.
16. Manual real-world gaps may be stored; validation reports them instead of preventing truthful recording.
17. SiteMemory remembers rules; PlanningEngine applies them.
18. No new architectural level is introduced by v0.3.
