# TASK_CONTRACT

TASK_ID: ROTA-T008
TITLE: LocalStore + ScheduleVersion lifecycle
STATUS: ARCHITECTURE_APPROVED_FOR_PRE_IMPLEMENTATION_REVIEW
DATE: 2026-08-13
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes

BASE_MAIN_SHA: e010f004e90a1e4f426bb72298e7307045d32b56
OWNER_APPROVED_ROADMAP_SHA: 9c0919100d245262f90b69c08ba13efcb93fadf5
ROADMAP_AUDIT_PASS_COMMIT: 6a237002d51a5225d1573342d4e7f51469b8beee

## STATUS / PROCESS GATE

This contract is ready for Codex pre-implementation review.

CC MUST NOT implement ROTA-T008 until Codex returns:
- PASS / READY_FOR_IMPLEMENTATION; or
- a precise CONTRACT_GAP that is subsequently resolved by the architect/owner as appropriate.

A review finding does not authorize CC to invent semantics.

## PURPOSE / ROADMAP POSITION

ROTA-T008 is the first task in the owner-approved post-T007 sequence:

`T008 LocalStore + ScheduleVersion lifecycle`
`-> T009 Application Layer`
`-> T010 Natural Language Rule Intake`
`-> T011 Backend/Application E2E`
`-> T012 Desktop + Desktop E2E`

T008 establishes the durable operational truth that T009 will consume.

T008 is NOT:
- a parser task;
- an application-workflow task;
- a desktop/bridge task;
- a temporary persistence layer created only to unblock UI.

The product principle for this stage is: reduce scope, not quality. Persistence introduced here is the durable LocalStore foundation of the product.

## SOURCE AUTHORITY

Use, in descending authority for this task:

1. frozen `arch/spec.md`, especially SECTION 1, SECTION 4, SECTION 5 and SECTION 6;
2. `arch/OWNER_APPROVED_ROADMAP_T008_T012.md` at `9c0919100d245262f90b69c08ba13efcb93fadf5`;
3. accepted T004 SiteProfile persistence contract/behavior;
4. accepted T005 SiteMemory + Decision Ledger contract/behavior;
5. accepted T006 REPLAN-MIN-01 and accepted T007 SiteRule execution only insofar as T008 must not regress them;
6. exact accepted main base `e010f004e90a1e4f426bb72298e7307045d32b56` for already-accepted domain shapes and engineering policy.

Do not treat task tests, commit messages, model suggestions or current implementation accidents as new product authority.

## OBJECTIVE

Extend Rota's existing single local SQLite database into the complete operational LocalStore required by the frozen product contract while preserving T004/T005 data and semantics.

After T008, closing and reopening the application database must allow the program to reconstruct exactly the persisted operational facts required by later T009 application assembly:

- Sites;
- Coordinators;
- CoordinatorSiteAssociations;
- Employees;
- SiteMemberships;
- ExternalSupportWindows;
- AvailabilityRecord history/current state;
- reproducible CalendarDay data;
- WorkBalance input needed to reconstruct balances;
- ScheduleVersion history;
- exactly one current ScheduleVersion reference per Site/month once versions exist;
- complete ShiftDemand / Assignment / Deviation content for every ScheduleVersion;
- applied_rule_version_ids for each ScheduleVersion.

SiteProfile and SiteMemory/Decision Ledger remain the existing T004/T005 sources of truth in the SAME database. Do not duplicate or replace them.

## ARCHITECTURE DECISION — ONE LOCALSTORE, ONE SQLITE DATABASE

Rota continues to use exactly one local SQLite database.

T008 MUST extend the existing T004/T005 database. It MUST NOT introduce:
- a second database for schedules;
- a second database for employees;
- an embedded server;
- an ORM/database service requiring another runtime;
- cloud persistence;
- a runtime dependency on Elnath Memory Engine.

The DB path remains caller-supplied. T008 does not hardcode the future desktop data-directory path; that belongs to the desktop/application boundary.

`rota/planning/` remains persistence-free.

## ARCHITECTURE DECISION — SCHEMA VERSIONING STARTS NOW

The accepted base currently initializes schema with `CREATE TABLE IF NOT EXISTS` and has no schema version.

T008 MUST replace that growth model with a small, durable, ordered SQLite migration mechanism.

Required mechanism:
- use SQLite `PRAGMA user_version` as the schema version marker;
- migration steps are ordered and deterministic;
- migration from the existing T004/T005/T007 schema is supported in place without data loss;
- a brand-new empty database reaches the exact same latest schema as a migrated database;
- each migration step is transactional;
- schema version is advanced only after that migration succeeds;
- reconnecting at the latest version is idempotent;
- if database `user_version` is greater than the highest version understood by this binary, fail closed with a dedicated schema/version error; never silently downgrade or rewrite it.

No external migration framework is required. This is a small repository-owned mechanism, not an invitation to add Alembic or another dependency.

The old T004 statement that idempotent CREATE TABLE initialization was enough for that earlier narrow task does not govern future schema evolution after T008.

## EXISTING DATA MUST SURVIVE MIGRATION

Migration tests MUST start from a non-empty legacy database shaped like accepted T007 persistence and containing at least:
- one SiteProfile with ordered StandardShifts;
- one T005 rule family;
- DecisionRecord history;
- at least one SiteRuleVersion with JSON parameters.

After T008 migration:
- every pre-existing value round-trips unchanged;
- T004 repository behavior remains valid;
- T005 Rule Store / Decision Ledger behavior remains valid;
- T007 monthly rule assembly can still read the same remembered rules.

T008 MUST NOT rewrite immutable T005 history merely to retrofit new foreign keys.

## DOMAIN REPRESENTATION BOUNDARY

T008 persists existing accepted domain fields. It does not add coordinator-facing product fields merely because a normalized database design could contain them.

All date/time/enum/boolean values MUST round-trip without semantic change.

Recommended encoding boundary:
- `date`, `datetime`, `time`: ISO representation compatible with existing repository conventions;
- enums: exact `.value` text;
- booleans: constrained integer 0/1;
- list ordering that is part of a domain field must round-trip deterministically.

Do not invent timezone conversion. Current accepted Rota datetimes are local/naive domain values; T008 stores and restores that existing representation exactly.

## MUTABLE CURRENT-STATE ENTITIES

T008 adds durable current-state persistence for:

### Site
Persist exactly:
- site_id
- profile_id
- display_name
- active

Invariant:
- profile_id must identify an existing SiteProfile.

Operations required:
- save/upsert current Site;
- get by site_id;
- list Sites deterministically.

No hidden Site history is introduced.
No physical delete API is required; `active=false` represents disabling.

### Coordinator
Persist exactly:
- coordinator_id
- display_name
- active

Operations:
- save/upsert;
- get;
- deterministic list.

No physical delete API required.

### CoordinatorSiteAssociation
Persist exactly:
- coordinator_id
- site_id
- active

Identity:
- `(coordinator_id, site_id)`.

Both referenced entities must exist.

Operations:
- save/upsert current association;
- list associations for coordinator and for Site.

No physical delete API required; use active state.

### Employee
Persist exactly current accepted Employee fields:
- employee_id
- display_name
- active_from
- active_to
- day_only

Operations:
- save/upsert;
- get;
- deterministic list.

Invariant:
- if active_to exists, `active_to >= active_from`.

Employee remains cross-Site. Do not add Employee.site_id.

### SiteMembership
Persist exactly:
- employee_id
- site_id
- membership_kind
- enabled
- readiness_state
- readiness_source

Identity:
- `(employee_id, site_id)`.

Both Employee and Site must exist.

Operations:
- save/upsert current membership;
- get/list by Site;
- get/list by Employee.

No membership history beyond the current frozen domain is invented.

### ExternalSupportWindow
Persist exactly:
- window_id
- employee_id
- site_id
- start_datetime
- end_datetime
- active
- allowed_shift_kind

Invariants:
- Employee exists;
- Site exists;
- `end_datetime > start_datetime`;
- if `allowed_shift_kind` exists it is a valid ShiftKind.

Operations:
- save/upsert current window;
- get;
- list by Site / Employee and optionally overlapping interval.

No physical delete API required; removal at later application/UI layer maps to `active=false` unless a later contract says otherwise.

## AVAILABILITYRECORD — APPEND-ONLY HISTORY

The frozen/domain shape already contains:
- availability_id;
- availability_version_id;
- employee_id;
- kind;
- start_date;
- end_date inclusive;
- active;
- supersedes_availability_version_id;
- note.

T008 MUST make the version fields real history rather than repeatedly overwriting one row.

Architecture:
- `availability_id` identifies one logical availability family;
- each `availability_version_id` is immutable after insert;
- first version has no predecessor;
- a later version for the same `availability_id` supersedes the current chain end;
- no branching;
- predecessor must belong to the same availability_id and employee_id;
- historical versions remain readable;
- cancellation/deactivation is a new immutable version with `active=false`, not UPDATE/DELETE of the prior record.

T008 does not invent new AvailabilityKind semantics. It must persist every AvailabilityKind already present in the accepted domain base.

Required API:
- append first availability version;
- append superseding version;
- get full history in deterministic chain order;
- get current chain-end record(s) for employee;
- list current active records overlapping a requested date range.

Invariant:
- `end_date >= start_date`.

Direct UPDATE/DELETE of availability-version rows must be rejected at the storage boundary.

## CALENDARDAY — DURABLE REPRODUCIBILITY CHOICE

CAL-01/CAL-04 permit persisted CalendarDay OR a deterministic bundled local source.

T008 chooses persisted CalendarDay as the LocalStore mechanism.

Persist exactly:
- date
- holiday

Identity:
- date.

Operations:
- save/upsert CalendarDay;
- get exact date;
- list inclusive date range ordered by date.

T008 does NOT decide which dates are public holidays and does not fetch a calendar from the network. It only guarantees that calendar facts supplied to LocalStore survive restart and can later be assembled by T009.

PlanningEngine MUST NOT read the CalendarDay table directly.

## WORKBALANCE — PERSIST INPUT, DERIVE OPERATIONAL OUTPUT

Frozen WorkBalance distinguishes coordinator input from derived values:
- target_hours: coordinator planning input;
- planned_hours: derived from current ScheduleVersions;
- realized_hours: derived from current ScheduleVersions;
- month_balance: derived;
- quarter_balance: aggregate;
- unresolved_carryover: current accepted balance computation remains as in the accepted base; its broader lifecycle remains outside this task unless already frozen elsewhere.

Architecture decision:

T008 MUST NOT create an independently editable/stale second source of truth for derived WorkBalance fields.

Persist authoritative monthly input:
- employee_id;
- month (first day of month);
- target_hours.

The complete WorkBalance returned after restart is reconstructed using:
- stored target_hours;
- current ScheduleVersion assignments across ALL Sites for that Employee/month (EMP-03);
- current AvailabilityRecord state required by accepted balance computation;
- accepted `rota.balance` computation.

Historical/non-current ScheduleVersions MUST NOT contribute to planned_hours, realized_hours, month_balance or quarter_balance.

When current ScheduleVersion reference changes through restore/select, reconstructed WorkBalance must change accordingly without manually synchronizing a second balance-hours table.

Required API/support:
- save/upsert target_hours for `(employee_id, month)`;
- get target_hours;
- list target inputs needed for a calendar quarter;
- repository/query support sufficient to reconstruct month/quarter WorkBalance from current operational data.

Missing target_hours remains missing data; do not silently replace it with zero or a guessed statutory norm.

T008 does not add payroll, salary or HR settlement logic.

## SCHEDULEVERSION — PERSISTED AGGREGATE

A persisted ScheduleVersion is one complete reconstructable snapshot aggregate containing:

Header:
- version_id
- site_id
- month
- parent_version_id optional
- created_at
- created_by
- status
- applied_rule_version_ids

Content:
- complete ShiftDemand set for that version;
- complete Assignment set for that version;
- complete Deviation set for that version.

T008 may introduce a focused persistence DTO such as `ScheduleSnapshot` outside `rota/planning/` to transport this aggregate. Do not add UI/application semantics to that DTO.

## SCHEDULEVERSION IDENTITY / LINEAGE INVARIANTS

- version_id is unique.
- month is the first calendar day of that month.
- Site exists.
- created_by Coordinator exists.
- if parent_version_id exists:
  - parent exists;
  - parent != child;
  - parent.site_id == child.site_id;
  - parent.month == child.month.
- because a new child may only point to an already-existing parent and parent linkage is not editable after creation, cycles are impossible.

The following header identity fields are immutable after first insert:
- version_id;
- site_id;
- month;
- parent_version_id;
- created_at;
- created_by.

A WORKING version may change only its mutable snapshot/status fields through the dedicated working-snapshot operation described below.

## CURRENT VERSION REFERENCE

Persist a separate current-version reference keyed by:
- `(site_id, month)`.

Invariant:
- for every `(site_id, month)` that has one or more ScheduleVersions, exactly one current reference exists after a successful LocalStore operation;
- referenced version exists;
- referenced version belongs to that exact Site/month;
- one Site/month can never have two current references.

Required operations:
- get current version id/snapshot;
- set/select an existing version as current;
- list all versions for Site/month without deleting non-current history.

`set_current` changes only the reference. It MUST NOT mutate the selected or deselected ScheduleVersion.

Physical delete of the current-reference row is not a supported product operation.

## CREATE NEW SCHEDULEVERSION

Creating a new ScheduleVersion MUST be one atomic LocalStore transaction containing:
- new header;
- complete applied_rule_version_ids association;
- complete ShiftDemand content;
- complete Assignment content;
- complete Deviation content;
- update/creation of the current-version reference to the new version.

A newly created version begins in a WORKING status:
- WORKING; or
- WORKING_WITH_DEVIATIONS.

T008 does not create a brand-new ScheduleVersion directly in FINAL status.

If creation fails at any point, reopening the database must show:
- no partially created new version/content; and
- the previous current reference unchanged.

## EDITING A WORKING VERSION

Working-state editing is allowed because frozen immutability applies to FINAL.

Required LocalStore operation:
- atomically replace the complete mutable snapshot of the CURRENT working version.

It may replace, as one transaction:
- status between WORKING / WORKING_WITH_DEVIATIONS as appropriate;
- applied_rule_version_ids;
- ShiftDemands;
- Assignments;
- Deviations.

It MUST NOT change immutable header identity fields.

Only a current WORKING/WORKING_WITH_DEVIATIONS version may be edited in place.
A non-current version is treated as historical snapshot and is not edited until explicitly selected as current.
A FINAL version is never editable.

If replacement fails partway, the prior complete working snapshot remains visible after reopen.

## FINALIZATION

Finalization changes only a current WORKING version into the matching FINAL state and then freezes the complete snapshot.

Required mapping:
- zero Deviations -> FINAL_NO_DEVIATIONS;
- one or more Deviations -> FINAL_WITH_DEVIATIONS.

For FINAL_WITH_DEVIATIONS:
- every persisted Deviation must have `acknowledged=true` before finalization;
- acknowledged_by and acknowledged_at must be present for every acknowledged Deviation;
- T008 does not require a free-text reason if the current frozen product contract does not require one.

T008 does not decide HOW the coordinator is asked to confirm. That is T009/T012. Persistence only refuses to manufacture a FINAL_WITH_DEVIATIONS snapshot whose stored acknowledgements do not prove the required conscious confirmation happened.

After finalization, the following are immutable:
- ScheduleVersion header/status;
- applied_rule_version_ids;
- all ShiftDemands;
- all Assignments;
- all Deviations and their acknowledgement fields.

Final immutability MUST be enforced at the storage boundary, not merely by UI convention. Direct SQL attempts to mutate/delete/add content under a FINAL version must fail.

## MATERIAL CHANGE AFTER FINAL

A FINAL ScheduleVersion is never reopened or rewritten.

A material change after FINAL requires a NEW WORKING child:
- new version_id;
- same Site/month;
- parent_version_id = the version from which the change starts;
- new created_at / created_by;
- complete working snapshot supplied by the caller;
- new version becomes current atomically.

T008 persistence does not decide what constitutes a material business change; T009 commands will decide when to create the child. T008 only provides the safe persistence primitive and rejects mutation of FINAL.

## RESTORE / SELECT EARLIER VERSION

Restore/select is reference movement, not history deletion.

Required behavior:
- select any existing ScheduleVersion belonging to the same Site/month as current;
- atomically point current reference at it;
- do not delete descendants or later versions;
- do not change selected version content;
- all current-version-derived queries (WorkBalance, holiday/current assignment queries) immediately use the newly selected current version.

T008 does not add a separate "restored" status.

## APPLIED RULE VERSION IDS

`ScheduleVersion.applied_rule_version_ids` MUST round-trip as the exact list supplied for that snapshot, in deterministic order.

For every referenced rule_version_id:
- SiteRuleVersion must exist;
- its site_id must equal ScheduleVersion.site_id.

T008 does not recalculate which rules SHOULD have been applied. T007/T009 assembly owns that semantic decision. T008 preserves the provenance supplied for the saved version and validates only existence/Site coherence.

## SHIFTDEMAND PERSISTENCE INVARIANTS

Persist exactly:
- demand_id
- schedule_version_id
- start_datetime
- end_datetime
- required_primary_count

Required:
- demand belongs to exactly one snapshot row identified by `(schedule_version_id, demand_id)`;
- `end_datetime > start_datetime`;
- required_primary_count > 0;
- demand start date belongs to ScheduleVersion.month.

A demand may end in the next month.

Demand logical IDs MAY repeat in another ScheduleVersion because identity in LocalStore is scoped by schedule_version_id. This allows reconstructable snapshots without forcing artificial global ID regeneration merely because a version changed.

## ASSIGNMENT PERSISTENCE INVARIANTS

Persist exactly current accepted Assignment fields.

LocalStore identity is `(schedule_version_id, assignment_id)`.

Required:
- Employee exists;
- `end_datetime > start_datetime`;
- Assignment start date belongs to ScheduleVersion.month (cross-month ownership by start time);
- PRIMARY:
  - covers_demand_id is present;
  - mentor_primary_assignment_id is absent;
  - covered demand exists in the SAME ScheduleVersion;
  - Assignment interval equals the covered demand interval;
- TRAINEE:
  - covers_demand_id is absent;
  - mentor_primary_assignment_id is present;
  - referenced mentor Assignment exists in the SAME ScheduleVersion and has role PRIMARY.

T008 persists frozen/state exactly. It does not reinterpret REPLAN semantics.

## DEVIATION PERSISTENCE INVARIANTS

Persist exactly:
- deviation_id
- schedule_version_id
- category
- source_reference
- affected_assignment_or_employee
- acknowledged
- acknowledged_by
- acknowledged_at
- reason

LocalStore identity is `(schedule_version_id, deviation_id)`.

Required:
- source_reference is non-empty;
- affected_assignment_or_employee is non-empty and must resolve either to an Employee or an Assignment in the same ScheduleVersion;
- if acknowledged=false, acknowledged_by / acknowledged_at may be absent;
- if acknowledged=true, acknowledged_by and acknowledged_at are required and acknowledged_by must identify an existing Coordinator;
- reason remains optional unless a later frozen contract makes it mandatory.

T008 does not decide whether a Deviation SHOULD exist. Planning/application validation owns that. T008 preserves and validates the persisted fact.

## BOUNDARY CONTEXT QUERY

Frozen contract: an Assignment crossing the month boundary belongs to the ScheduleVersion of its START time and is read by the adjacent month as boundary context.

T008 MUST provide persistence query support that, for `(site_id, target_month)`, returns non-CANCELLED Assignments from CURRENT ScheduleVersions of the same Site whose actual interval overlaps the target month but whose owning ScheduleVersion.month differs from target_month.

At minimum this must correctly return a prior-month N shift that starts on the last day of the prior month and ends in target_month.

Historical/non-current versions MUST NOT leak into boundary context.

## CURRENT CROSS-SITE ASSIGNMENT QUERY

Because Employee is not owned by one Site, T009 will need current assignments from other Sites for REST-01 / LOAD-01 and WorkBalance assembly.

T008 MUST provide query support for:
- selected employee ids;
- requested datetime/date interval;
- CURRENT ScheduleVersions only;
- optionally excluding one Site;
- non-CANCELLED assignments;
- deterministic ordering.

Do not make PlanningEngine query this repository. T009 later assembles the result into PlanningState.

## HOLIDAY HISTORY SUPPORT

CAL-05 history uses persisted CURRENT-version Assignments joined with CalendarDay where holiday=true.

T008 MUST provide either one focused repository query or composable LocalStore queries sufficient to retrieve current-version historical PRIMARY Assignments on stored holiday dates.

Historical/non-current ScheduleVersions MUST NOT contribute.

PlanningEngine still receives ready holiday_history through PlanningState; no database I/O moves into planning.

## NO DUPLICATE SOURCE OF TRUTH

T008 MUST NOT create competing copies of:
- SiteProfile data already owned by T004;
- SiteRuleVersion / Decision Ledger data already owned by T005;
- PlanningState (never persisted);
- PlanningEngine results as an unrelated cache;
- derived WorkBalance hours independent of current ScheduleVersions.

One database may contain multiple normalized tables; "one source of truth" means each business fact has one authoritative persisted representation.

## STORAGE-LEVEL INTEGRITY

Use SQLite constraints/foreign keys/triggers where they materially protect frozen invariants and prevent bypass through another repository later.

At minimum storage boundary must protect:
- foreign_keys ON;
- append-only AvailabilityRecord versions;
- no physical deletion of ScheduleVersion history;
- FINAL ScheduleVersion immutability including child content and applied rules;
- child rows belonging to an existing ScheduleVersion;
- exact one-row key for current `(site_id, month)` reference;
- impossible cross-Site/month current reference;
- impossible cross-version covered-demand / mentor references;
- impossible mutation of immutable T005 rows remains as already accepted.

Repository-level validation may supplement constraints where SQLite cannot express an invariant cleanly.

Do not move product interpretation into SQL triggers; triggers protect persistence invariants only.

## TRANSACTION BOUNDARIES

The following MUST be atomic:

1. one schema migration step + version increment;
2. append AvailabilityRecord successor;
3. create new ScheduleVersion aggregate + set current reference;
4. replace current WORKING snapshot;
5. finalize current ScheduleVersion;
6. restore/select current version reference;
7. existing T004 profile+shifts save remains atomic;
8. existing T005 Decision Ledger + SiteRuleVersion write remains atomic.

A process/database exception at any intermediate statement must not expose a partially successful business operation after reopen.

## ERROR MODEL

Use focused persistence/domain errors, not raw sqlite3 exceptions as the public repository contract for expected invariant failures.

Examples of dedicated error classes or equivalent explicit typed failures:
- entity not found;
- duplicate immutable version id;
- invalid availability chain;
- invalid schedule lineage;
- non-current/non-working edit attempt;
- FINAL immutable violation;
- invalid current-version target;
- malformed schedule snapshot;
- unsupported future schema version.

Unexpected storage/system failures may propagate/wrap as technical persistence errors for T009 to map later. T008 does not introduce PlanningResult status mapping.

## PERSISTENCE API BOUNDARY

Exact Python file names/classes are architecturally flexible provided responsibilities remain separated and size policy passes.

Expected focused areas may include:
- `rota/persistence/db.py` / migrations;
- Site/Coordinator/Employee repositories;
- availability repository;
- calendar repository;
- schedule repository;
- WorkBalance target/query adapter;
- focused persistence DTO/types.

Do NOT build a generic Repository base class, UnitOfWork framework, event bus or service locator.

The persistence API must be usable by later T009 without T009 issuing raw SQL.

## PLANNING BOUNDARY

T008 MUST NOT change PlanningEngine behavior.

Forbidden inside `rota/planning/`:
- sqlite3 import;
- `rota.persistence` import;
- opening LocalStore;
- current-version lookup;
- WorkBalance database query;
- CalendarDay database query.

No solver objective, constraint, status mapping, SiteRule execution or REPLAN semantics may change in T008.

ROTA-REG-001 remains unchanged.

## REQUIRED INTEGRATION SCENARIO — VERSION / RESTART / RESTORE

Create a real SQLite-backed integration test using one database file.

Scenario:

1. migrate/open database from current accepted persistence foundation;
2. save SiteProfile (existing T004 path), Site, Coordinator, Employee/membership and CalendarDay facts;
3. save WorkBalance target_hours;
4. create WORKING ScheduleVersion V1 with:
   - complete ShiftDemands;
   - Assignments including one overnight Assignment crossing into the next month;
   - applied_rule_version_ids from a real T005 SiteRuleVersion;
   - no Deviations;
5. finalize V1 as FINAL_NO_DEVIATIONS;
6. create complete WORKING child V2 with parent_version_id=V1, materially changing at least one future PLANNED Assignment;
7. verify V2 becomes current while V1 remains byte/field-equivalent and immutable;
8. close database and reopen it;
9. reconstruct V2 exactly and verify current reference points to V2;
10. select/restore V1 as current;
11. verify V2 still exists unchanged in history;
12. verify current-only assignment/boundary/WorkBalance queries now reflect V1 rather than V2 without manual rewrite of derived balance rows;
13. close/reopen again and verify the restored current reference persists.

This scenario proves durable version history, current pointer semantics, restart reconstruction and no duplicate balance truth.

## REQUIRED CRASH-CONSISTENCY SCENARIO

Using a real SQLite database, force an exception/abort AFTER some statements of a multi-row schedule operation have executed but BEFORE the operation would normally complete.

Must prove after connection close/reopen:
- no partial new ScheduleVersion aggregate is visible;
- no orphaned child content is visible;
- prior current version still points to the exact prior version;
- existing T004/T005 data remains intact.

Repeat equivalent fault injection for replacement of a current WORKING snapshot: after reopen either the entire old snapshot or entire new snapshot is visible, never a mixed set.

No production-only "test mode" or debug API is required to create the failure; tests may use a controlled SQLite trigger/monkeypatch at repository boundary.

## REQUIRED LEGACY MIGRATION SCENARIO

Construct a non-empty database using the accepted pre-T008 schema and accepted T004/T005 data paths/fixtures.

Then open with T008 `connect()`.

Assertions:
- migration completes to latest known `PRAGMA user_version`;
- pre-existing SiteProfile + ordered shifts are unchanged;
- pre-existing SiteRuleVersions and DecisionRecords are unchanged;
- T005 effective selection still returns the same result;
- T007 monthly assembly returns the same remembered rules;
- reopening again performs no destructive/repeated migration;
- setting `PRAGMA user_version` to a future unsupported value fails closed and leaves DB untouched.

## REQUIRED TEST MATRIX

### A. SCHEMA / MIGRATION
A1. empty DB -> latest schema.
A2. accepted legacy non-empty DB -> latest schema without data loss.
A3. connect latest DB again -> idempotent.
A4. future user_version -> dedicated fail-closed error; no downgrade.
A5. migration failure -> schema version and data rollback for that step.

### B. CURRENT MASTER DATA
Round-trip + restart for Site, Coordinator, CoordinatorSiteAssociation, Employee, SiteMembership, ExternalSupportWindow.
Check invalid FK/coherence cases fail explicitly.

### C. AVAILABILITY HISTORY
C1. first immutable version.
C2. valid superseding version.
C3. active=false cancellation as new version.
C4. history survives restart.
C5. branch/skip/wrong employee predecessor rejected.
C6. direct UPDATE/DELETE rejected.
C7. current-range query returns chain end only.

### D. CALENDAR
D1. CalendarDay range round-trip/restart.
D2. deterministic ordering.
D3. update current holiday fact does not require PlanningEngine I/O.

### E. SCHEDULE SNAPSHOT ROUND-TRIP
Complete version reconstructs exact header, ordered applied_rule_version_ids, ShiftDemand, Assignment and Deviation values after restart.

### F. CURRENT REFERENCE
F1. first successful create creates exactly one current reference.
F2. child creation switches it atomically.
F3. restore/select switches it without deleting later history.
F4. wrong Site/month target rejected.
F5. current reference survives restart.

### G. FINAL IMMUTABILITY
G1. finalize no-deviation -> FINAL_NO_DEVIATIONS.
G2. deviations -> FINAL_WITH_DEVIATIONS only when acknowledged.
G3. direct/repository header mutation after FINAL rejected.
G4. child INSERT/UPDATE/DELETE under FINAL rejected.
G5. applied-rule mutation under FINAL rejected.
G6. physical delete FINAL/history rejected.

### H. WORKING EDIT
H1. current working aggregate can be completely replaced atomically.
H2. immutable header fields cannot change.
H3. non-current version edit rejected.
H4. mixed old/new snapshot impossible on injected failure.

### I. LINEAGE
I1. child parent same Site/month accepted.
I2. cross-Site/cross-month/missing/self parent rejected.
I3. FINAL parent is not mutated when child created.

### J. APPLIED RULE PROVENANCE
J1. real T005 rule_version_id round-trips.
J2. missing rule id rejected.
J3. rule from other Site rejected.
J4. list order deterministic and preserved.

### K. SHIFTDEMAND / ASSIGNMENT REFERENCES
K1. cross-month overnight demand/assignment owned by start month.
K2. PRIMARY must cover same-version demand with matching interval.
K3. TRAINEE must reference same-version PRIMARY mentor.
K4. dangling/cross-version demand or mentor rejected.
K5. invalid interval/count rejected.

### L. DEVIATION
L1. round-trip all categories/fields.
L2. acknowledged requires coordinator + timestamp.
L3. affected reference resolves to employee or same-version assignment.
L4. final-with-deviations rejects unacknowledged deviation.

### M. CURRENT-ONLY OPERATIONAL QUERIES
M1. boundary context uses current versions only.
M2. cross-Site employee assignments use current versions only.
M3. holiday history uses current versions only + stored CalendarDay.
M4. CANCELLED excluded where query contract says non-CANCELLED.
M5. restore current pointer changes query results immediately.

### N. WORKBALANCE
N1. target_hours persists/restarts.
N2. missing target is not guessed as zero.
N3. planned/realized derive from current versions only.
N4. historical versions are not double-counted.
N5. cross-Site current assignments for same Employee are included.
N6. restore/select changes reconstructed balance without writing derived hours.
N7. accepted `rota.balance` behavior remains unchanged.

### O. CRASH CONSISTENCY
O1. failed create leaves no partial version and old current unchanged.
O2. failed working replacement leaves one complete snapshot, never mixed.
O3. failed migration leaves previous schema/data/version coherent.

### P. EXISTING PERSISTENCE REGRESSIONS
P1. T004 profile persistence suite stays green.
P2. T005 Decision Ledger/Rule Store suite stays green.
P3. T007 two-month remembered-rule integration stays green.

### Q. PLANNING ISOLATION
Static/import check: `rota/planning/` still imports neither sqlite3 nor rota.persistence; ROTA-REG-001 unchanged and green.

## TASK_SCOPE

Allowed production changes:
- `rota/persistence/db.py` and focused migration helpers;
- new/updated focused persistence modules for entities listed in this contract;
- focused persistence aggregate/DTO types outside `rota/planning/`;
- `rota/domain.py` ONLY if a strictly necessary type annotation/import correction is required to persist existing fields without changing product shape;
- `rota/balance.py` ONLY if a persistence-neutral adapter seam is strictly required and computation semantics remain identical;
- tests/support builders for persistence fixtures;
- dedicated T008 tests.

Existing T004/T005 persistence modules may be minimally refactored to participate in the migration foundation, but their accepted public behavior and immutable-history semantics MUST remain unchanged.

## OUT_OF_SCOPE

Do NOT implement in T008:
- T009 application commands/orchestration;
- PlanningState assembly from LocalStore;
- natural-language parser / LLM / rule intake;
- desktop bridge;
- React/Tauri UI;
- print;
- backup UX or diagnostic ZIP;
- PWA;
- Excel/XLSX import;
- new SiteRule kinds;
- SiteRule SOFT weighting;
- new REPLAN behavior;
- payroll/HR settlement;
- cloud sync;
- event sourcing;
- generic repository framework;
- physical deletion workflows for business history;
- new product fields not already frozen.

T009/T010/T011/T012 remain separate roadmap tasks.

## ACCEPTANCE CONTRACT

PASS requires ALL of the following:

1. One SQLite LocalStore remains the only Rota persistence database.
2. Ordered `PRAGMA user_version` migration mechanism replaces schema growth by unversioned CREATE-only evolution.
3. Empty DB and accepted non-empty pre-T008 DB converge to the same latest schema.
4. Legacy T004/T005 data survives migration exactly and T007 remembered-rule retrieval still works.
5. Unsupported future schema version fails closed without mutation.
6. Site, Coordinator, CoordinatorSiteAssociation, Employee, SiteMembership and ExternalSupportWindow persist/restart with exact accepted fields.
7. AvailabilityRecord history is append-only, linear, non-branching and survives restart; active=false is a new version, not history rewrite.
8. CalendarDay is persisted locally and reproducible after restart; PlanningEngine does not read it directly.
9. WorkBalance target_hours is durable; derived hours/balances are reconstructed from authoritative current operational facts, not stored as a second mutable truth.
10. ScheduleVersion round-trips as a complete reconstructable Site/month snapshot.
11. Exactly one current reference exists after successful version operations for any Site/month with versions.
12. New version creation + full content + current reference is one atomic transaction.
13. Current WORKING snapshot replacement is complete and atomic; non-current or FINAL edit is rejected.
14. FINAL status mapping matches deviation presence and FINAL_WITH_DEVIATIONS requires stored acknowledgements.
15. FINAL header, applied rules and all child content are immutable at storage boundary.
16. Material change after FINAL is represented by a new WORKING child; FINAL is never reopened.
17. Restore/select moves only current reference and preserves all later history unchanged.
18. applied_rule_version_ids preserve order, exist, and belong to the ScheduleVersion Site.
19. ShiftDemand/Assignment/Deviation same-version referential invariants are enforced.
20. Cross-month Assignment ownership uses start time; boundary query returns correct current prior-context after restart.
21. Cross-Site/current assignment queries use current versions only and support multi-Site Employee context.
22. Historical/non-current ScheduleVersions never contribute to current WorkBalance or holiday-history operational queries.
23. Required restart/restore integration scenario passes on a real SQLite file.
24. Required crash-consistency scenarios prove no partial aggregate/current-reference state after forced failure.
25. Existing T004/T005/T007 persistence behavior and tests remain green.
26. PlanningEngine/solver/validator behavior is unchanged; `rota/planning/` has zero persistence I/O/import coupling.
27. ROTA-REG-001 remains unchanged and green.
28. Ruff, SIZE_FILE, SIZE_FUNC and `git diff --check` pass for T008 changes (immutable prior audit artifacts are evaluated according to their existing provenance, not rewritten).
29. No new product semantics are invented outside this contract/source authority.
30. No temporary/throwaway persistence layer, second database, cloud service or generic framework is introduced.

## AUDIT INSTRUCTIONS FOR CODEX

Codex must audit behavior and storage invariants, not merely table existence.

Required adversarial checks include:
- create a real pre-T008 non-empty DB and migrate it;
- inject a failure in the middle of schedule creation and prove old current survives;
- attempt direct SQL mutation of FINAL child content and prove storage rejects it;
- restore an earlier version and prove current-only WorkBalance/boundary/history queries switch without deleting later versions;
- attempt cross-Site current reference, parent, applied-rule and same-version child references;
- attempt AvailabilityRecord branching and direct UPDATE/DELETE;
- prove non-current history is not counted into operational hours;
- inspect imports to prove PlanningEngine still has zero LocalStore coupling;
- compare ROTA-REG-001 unchanged.

A PASS based only on repository round-trip unit tests is insufficient.

If a material product ambiguity is found, return `CONTRACT_GAP / OWNER_DECISION_REQUIRED` rather than inventing behavior.

## PROCESS

1. Codex pre-reviews this exact Task Contract plus frozen sources/owner-approved roadmap.
2. If PASS, implementation branch MUST start from accepted main `e010f004e90a1e4f426bb72298e7307045d32b56` or a later owner-approved main that contains the same accepted T004–T007 lineage.
3. Run repository task-init workflow for `ROTA-T008` without overwriting this architect-authored brief; preserve exact base provenance.
4. CC implements only this Task Contract.
5. Codex audits the exact implementation SHA with independent adversarial tests.
6. Result returns to architect for final architectural PASS/FAIL bound to exact SHA.
7. Merge to main remains owner decision.
