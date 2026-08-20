# ROTA-T019b — durable memory of material coordinator actions + final DECISION_REQUIRED readback

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T019b
BASE_BRANCH: main
BASE_SHA: 102273b553783b5a083a60d5ee9964e9ec67221a
TASK_BRANCH: task/T019b
OWNER_SOURCE: arch/T019b_decision_guidance_readback_architect_brief.md
PREDESIGN_AUDIT: tasks/ROTA-T019b/operation_audit.md
DEPENDS_ON: T005 + T008 + T009 + T010 + T012 + T013 + T016 + T017 + T018 + T019 merged on main
FOLLOWED_BY: T021 UI

## 1. CEL

Rota ma trwale pamiętać materialne, świadome działania koordynatora wpływające na grafik oraz ostatnie finalne pytanie `DECISION_REQUIRED`, które rzeczywiście zostało pokazane koordynatorowi.

Po restarcie application read ma pozwolić ustalić:
- co koordynator zmienił;
- kto wykonał zmianę;
- kiedy została zapisana;
- od kiedy dana zmiana faktycznie obowiązuje w istniejącym modelu;
- jaki był stan przed i po;
- czego/których pracowników/Site/miesiąca/ScheduleVersion dotyczyła;
- opcjonalną notatkę koordynatora;
- czy działanie było jawnie wskazaną odpowiedzią na zapisany finalny `DECISION_REQUIRED`.

T019b NIE jest logiem technicznym i NIE jest workflow engine.

## 2. FROZEN PRODUCT BOUNDARIES

1. Historia materialnych działań koordynatora jest append-only. Nie nadpisujemy i nie kasujemy dawnych wpisów.
2. Notatka jest zawsze opcjonalna. Brak notatki nie blokuje i nie zmienia działania.
3. Nie zapisujemy prób solvera, T018 retry stages, kolejności fallbacków, surowych wewnętrznych blockerów ani niewybranych wariantów T017.
4. `DECISION_REQUIRED` jest pytaniem do koordynatora, nie jego decyzją. Ma osobny current-readback/provenance context.
5. Związek pytanie -> działanie istnieje wyłącznie, gdy caller jawnie poda `responds_to_decision_required_id`. Nigdy nie inferować związku z czasu, rodzaju zmiany ani kolejnego PLAN.
6. Jeden publiczny materialny command = jeden logical coordinator-action entry.
7. Existing operational/domain data pozostają current truth dla planowania. Action memory jest historyczną projekcją/audytem i NIGDY nie jest wejściem solvera/validatora/WorkBalance.
8. Existing Decision Ledger pozostaje ownerem SiteRule/DecisionRecord. Nie zapisujemy employee flags, targetów, restore lub candidate selection jako fałszywych `(site_id, rule_id)` chains.
9. Brak UI w T019b.
10. Brak obowiązkowego uzasadnienia/rationale.

## 3. BASELINE — POST T019

Na exact BASE_SHA:

- `decision_records` + `site_rule_versions` są append-only i poprawnie przechowują strukturalne decyzje regułowe;
- Availability ma append-only `availability_versions`, lecz bez actor/recorded_at/site context;
- ScheduleVersion lineage przechowuje child history dla REPLAN/manual corrections/training oraz `created_by/created_at/effective_from`;
- `select_candidate` nadpisuje current WORKING snapshot in-place;
- `restore` nadpisuje tylko `current_schedule_versions` pointer;
- `finalize` aktualizuje status bieżącej wersji i zapisuje acknowledgement Deviations;
- Employee, Membership, target_hours, CalendarDay, SiteProfile, Site i ExternalSupportWindow są current-state / UPSERT i nie mają pełnej historii before/after;
- finalny T013 `DecisionRequiredPayload` istnieje tylko w pamięci procesu jako element `PlanningResult`;
- wszystkie coordinator-facing write paths przechodzą przez `rota.application.*`.

Predesign audit dokładnie klasyfikuje każdą publiczną operację mutującą. Nie implementować T019b bez zgodności z `tasks/ROTA-T019b/operation_audit.md`.

## 4. ARCHITECTURE — EXTEND EXISTING SITEMEMORY, NO PARALLEL SUBSYSTEM

Nie tworzyć:
- `coordinator_action_repository.py`;
- `decision_memory_repository.py`;
- nowego query bus;
- event bus;
- command bus;
- audit framework;
- workflow engine;
- per-action files.

T019b rozszerza istniejące:

- `rota/site_memory_types.py` — stabilne typy/kinds pamięci;
- `rota/persistence/site_memory.py` — persistence action index + final DR snapshots/current pointer;
- `rota/application/memory_read.py` — jedyny publiczny application read dla tej pamięci.

`rota/persistence/decision_ledger.py` pozostaje wyspecjalizowanym write ownerem dla SiteRule decisions.

## 5. STORAGE — MIGRATION 6

W `rota/persistence/db.py` dodać dokładnie jeden ordered migration step, podnoszący `LATEST_SCHEMA_VERSION` z 5 do 6.

### 5.1 `coordinator_action_records` — append-only

Minimalne kolumny semantyczne:

- `action_id TEXT PRIMARY KEY`;
- `action_kind TEXT NOT NULL`;
- `origin_site_id TEXT NOT NULL`;
- `affected_site_ids_json TEXT NOT NULL`;
- `coordinator_id TEXT NOT NULL`;
- `recorded_at TEXT NOT NULL`;
- `effective_from TEXT`;
- `month TEXT` nullable;
- `schedule_version_id TEXT` nullable;
- `affected_entities_json TEXT NOT NULL`;
- `before_state_json TEXT` nullable;
- `after_state_json TEXT` nullable;
- `note TEXT` nullable;
- `source_kind TEXT NOT NULL`;
- `source_id TEXT` nullable;
- `responds_to_decision_required_id TEXT` nullable FK to final DR snapshots.

Required FKs for concrete identities that exist as stable rows:
- `origin_site_id -> sites.site_id`;
- `coordinator_id -> coordinators.coordinator_id`;
- `responds_to_decision_required_id -> decision_required_snapshots.decision_required_id`.

Do NOT add generic FKs for polymorphic source/entity IDs.

Add DB triggers forbidding UPDATE and DELETE on `coordinator_action_records`.

### 5.2 `decision_required_snapshots` — append-only final questions only

Minimal columns:

- `decision_required_id TEXT PRIMARY KEY`;
- `site_id TEXT NOT NULL`;
- `month TEXT NOT NULL` first-day;
- `schedule_version_id TEXT` nullable;
- `requested_by TEXT NOT NULL` coordinator id;
- `recorded_at TEXT NOT NULL`;
- `payload_json TEXT NOT NULL`.

Payload is the exact final coordinator-facing T013 `DecisionRequiredPayload` shape:
- blocking shift demands;
- rendered blockers;
- load blocker;
- final dynamic unblocking options.

No raw solver trace columns.

Add UPDATE/DELETE-forbidden triggers.

### 5.3 `current_decision_required` — mutable current pointer only

Columns:

- `site_id TEXT NOT NULL`;
- `month TEXT NOT NULL`;
- `decision_required_id TEXT NOT NULL` FK;
- primary key `(site_id, month)`.

This table is a current pointer analogous in purpose (not schema) to `current_schedule_versions`: it may be replaced/deleted. Snapshot history is never deleted.

### 5.4 Indexes

Add only indexes justified by required reads:
- coordinator action by `recorded_at`;
- coordinator action by `coordinator_id, recorded_at`;
- coordinator action by `action_kind, recorded_at`;
- snapshot by `site_id, month, recorded_at`.

Site/entity filtering may finish in memory from deterministic JSON arrays; do not add JSON-extension dependency or relation tables solely for filtering at pilot scale.

## 6. STABLE ACTION TYPES

In existing `rota/site_memory_types.py` add `CoordinatorActionKind(str, Enum)` with exactly these minimum values:

- `CONTEXT_CONFIGURATION_SAVED`
- `EXTERNAL_SUPPORT_WINDOW_CHANGED`
- `AVAILABILITY_CHANGED`
- `EMPLOYEE_DAY_ONLY_CHANGED`
- `SITE_MEMBERSHIP_CHANGED`
- `TARGET_HOURS_CHANGED`
- `CALENDAR_DAY_CHANGED`
- `SITE_PROFILE_CHANGED`
- `SITE_ACTIVE_CHANGED`
- `RULE_DECISION_RECORDED`
- `SCHEDULE_CANDIDATE_SELECTED`
- `SCHEDULE_REPLAN_CREATED`
- `MANUAL_SCHEDULE_CORRECTION`
- `ASSIGNMENT_FREEZE_CHANGED`
- `ASSIGNMENT_NOT_WORKED`
- `TRAINING_REALIZED`
- `SCHEDULE_FINALIZED`
- `SCHEDULE_RESTORED`

Do not add action kinds for PLAN, REVALIDATE, solver retries, fallback stages, generated readiness or REST_OVERRIDE_RECORD.

Persistence-level stored record may also live in `site_memory_types.py`; do not add these types to frozen `rota/domain.py`.

## 7. ACTION ENTRY SEMANTICS

### 7.1 One action

One successful coordinator command listed MATERIAL in the operation audit creates exactly one action row.

Nested implementation calls do not create extra action rows.

### 7.2 `origin_site_id` vs affected Sites

`origin_site_id` = active Site context under which coordinator performed the command.

`affected_site_ids` = sorted unique snapshot of currently modeled Sites whose planning input/current schedule can be affected by the changed fact.

Frozen examples:
- Site-specific membership/rule/window/schedule action -> that Site;
- Employee day_only / availability / target -> enabled membership Sites for that Employee at action time; if this set is empty include origin Site so the action remains discoverable;
- CalendarDay -> all currently stored Sites;
- SiteProfile -> all Sites currently bound to that profile;
- shared Employee -> one action with multiple affected Site IDs, never duplicate action rows per Site.

Site filtering in the read API tests membership in `affected_site_ids`, not only `origin_site_id`.

### 7.3 affected entities

Store a deterministic JSON array of objects with at minimum:

`{"entity_kind": <stable string>, "entity_id": <stable id>}`

Sort by `(entity_kind, entity_id)` and deduplicate.

Required entity kinds used by T019b include as applicable:
- `EMPLOYEE`;
- `SITE_MEMBERSHIP`;
- `SITE_PROFILE`;
- `SITE`;
- `CALENDAR_DAY`;
- `AVAILABILITY`;
- `EXTERNAL_SUPPORT_WINDOW`;
- `WORK_BALANCE_TARGET`;
- `SITE_RULE`;
- `SCHEDULE_VERSION`;
- `ASSIGNMENT`;
- `DEVIATION`.

No generic user-defined entity system.

### 7.4 structured before/after

`before_state_json` / `after_state_json` are historical structured snapshots of the facts changed by this one action, not copies of the entire database.

They are never used to reconstruct PlanningState.

Canonical rules:
- JSON object keys sorted during serialization;
- Enum values stored as `.value`;
- dates/datetimes ISO-8601;
- tuples/lists represented in deterministic order;
- no Python repr;
- no technical object memory addresses.

Current-state commands store the relevant current fact before and after.

Schedule commands store compact change data:
- candidate selection: changed/added/removed selected Assignment facts only; never unselected candidates;
- manual/freeze/NN/training: supplied/derived changed Assignment facts and, for training, derived membership readiness when it actually changes;
- REPLAN: current ScheduleVersion pointer parent -> child, not solver attempts/candidates;
- restore: current pointer before -> restored version;
- finalize: status before/after plus acknowledged Deviation ids/states.

### 7.5 no-op current-state updates

For mutable current-state operations, if no schedule-material field actually changes:
- perform existing nonmaterial write if the caller requested it;
- create no material action row;
- do not invalidate a stored final DR solely because of display-name/retired metadata/no-op changes.

Examples:
- Employee display-name-only update: no T019b action;
- `active_from/active_to` only: no action (T016 EMP-02 retired);
- Site display-name-only: no action;
- SiteProfile display-name-only: no action.

## 8. EFFECTIVE_FROM — TRUTHFUL EXISTING SEMANTICS ONLY

T019b does NOT create future-effective versions of current-state entities.

Use:
- SiteRule decision -> existing decision `effective_from`;
- Availability -> `start_date`;
- target -> target `month`;
- CalendarDay -> its date;
- ExternalSupportWindow -> `start_datetime.date()`;
- REPLAN/manual/freeze/NN/training -> existing command `effective_from`;
- candidate selection/finalize -> current ScheduleVersion `effective_from` (legacy NULL stays NULL);
- current-state day_only/membership/profile/Site.active/bootstrap -> `recorded_at.date()` because the persisted current value becomes operative immediately;
- restore -> `recorded_at.date()`; restoring does not rewrite the old ScheduleVersion's original effective_from.

No audit row may claim a future effective date for a current-state boolean while planning already uses that value today.

## 9. OPTIONAL NOTE

Every material public command that does not already carry an equivalent optional note gets:

`note: str | None = None`

Existing fields reused:
- `append_availability.note` is both the AvailabilityRecord note and action note;
- `lifecycle_ops.finalize.reason` remains optional Deviation reason and is also exposed as the action note for that one finalize action.

No note is required, validated as rationale, or generated by the program.

Empty/whitespace-only note may normalize to `None`; nonempty content is preserved as entered after outer whitespace trim.

## 10. EXPLICIT DECISION_REQUIRED LINK

Material commands except bootstrap may accept:

`responds_to_decision_required_id: str | None = None`

If non-None, before mutating:
1. referenced snapshot must exist;
2. it must be the current pointer for its `(site_id, month)`;
3. snapshot `site_id` must equal the command `origin_site_id`;
4. otherwise fail before business mutation.

No inference from:
- action kind;
- employee;
- time proximity;
- the fact that PLAN later becomes FEASIBLE.

The action row references the immutable snapshot. Later replacement/clearing of the current pointer never destroys this provenance.

An action does not assert that the question is solved merely because it links to it.

## 11. FINAL DECISION_REQUIRED SNAPSHOT / CURRENT POINTER

Only application `plan_ops.plan_month()` and `plan_ops.replan()` may update current final-question readback.

After the existing `plan(state)` returns its FINAL public `PlanningResult`:

### DECISION_REQUIRED
- persist exactly the already-rendered `decision_payload`;
- never persist internal retry stages;
- atomically insert immutable snapshot and set `(site_id, month)` current pointer;
- if current pointer already references a byte/canonically identical payload for the same schedule_version_id, reuse that snapshot rather than creating duplicate rows from repeated identical PLAN clicks.

### FEASIBLE
- clear current pointer for that site/month;
- do not delete any immutable snapshots;
- do not persist candidates in question memory.

### TECHNICAL_ERROR
- preserve the previous current pointer; a technical failure is not evidence that an earlier coordinator question was resolved.

Fail closed:
- do not return coordinator-facing DECISION_REQUIRED if its snapshot/current pointer failed to persist;
- do not return FEASIBLE while a persistence failure prevented clearing a now-stale pointer;
- such persistence failure becomes the application result `TECHNICAL_ERROR` with `candidates=[]` and no `decision_payload`, without changing engine/fallback semantics.

## 12. STALE QUESTION INVALIDATION BY MATERIAL INPUT CHANGE

A final question is current only for the input/current-schedule context that produced it.

The same transaction that commits a material coordinator action must clear current DR pointers whose context the action can affect. This is staleness invalidation, NOT inferred question->action linkage.

Required granularity:
- target -> affected Site(s), that target month;
- CalendarDay -> all Sites, that calendar month;
- Availability / ExternalSupportWindow -> affected Site(s), every month overlapped by its date interval;
- schedule action -> action Site/month;
- day_only / membership / SiteProfile / Site.active / context configuration -> all current questions for affected Sites;
- SiteRule -> months of currently stored pointers intersecting the rule's effective interval; open-ended rule invalidates matching months on/after effective_from.

If the action explicitly links to the current question, validate/capture the link first, append the action, then clear affected current pointer(s) in the same transaction. Immutable snapshot remains available through action detail.

## 13. ATOMICITY — HISTORY MUST NOT LAG A SUCCESSFUL HUMAN WRITE

For every MATERIAL command:

`business mutation + coordinator_action_records INSERT + stale-current-question invalidation`

must commit or roll back as one transaction.

No post-commit best-effort audit write.

### 13.1 Mutable repositories

Where a current repository wraps its own `with conn:`, add the same narrow transaction-neutral sibling pattern already used elsewhere:
- employee write;
- ExternalSupportWindow write;
- Availability append;
- target write;
- CalendarDay write.

Existing public repository functions keep their behavior and wrap the new transaction-neutral primitive.

Do not move SQL into application modules.

### 13.2 Existing transaction-neutral owners reused

Reuse current no-commit primitives for:
- SiteProfile;
- Site;
- Coordinator;
- CoordinatorSiteAssociation;
- Decision Ledger.

Bootstrap may be refactored so one invocation's supplied pieces and its one conditional material action are one transaction, while preserving the existing ability to resume a partial context across separate calls. No onboarding state/step is introduced.

### 13.3 Schedule lifecycle

Extend existing `schedule_lifecycle` same-transaction hook pattern minimally to the write operations that currently lack it:
- `replace_working_snapshot`;
- `finalize_schedule_version`;
- `restore_schedule_version`.

Default `on_success=None`; existing callers preserve behavior.

`create_schedule_version` already has the accepted one-hook transaction boundary.

This hook is ONLY a transaction-composition seam; do not generalize it into events/middleware/workflow.

## 14. SELECT_CANDIDATE ACTOR MUST BECOME EXPLICIT

T019b history may not guess who selected a candidate from `ScheduleVersion.created_by`.

`plan_ops.select_candidate` must require an explicit `coordinator_id` for the material selection write. Remove the semantic fallback to version creator for selection.

This is the only intentionally tightened coordinator-actor requirement in T019b.

Preimplementation audit must enumerate all existing tests/callers that require the mechanical new argument before CC edits them.

No change to T017 candidate selection semantics otherwise.

## 15. APPLICATION ACTION MAPPING

Implement exactly the classification frozen in `operation_audit.md`.

Important non-duplication rules:
- `freeze_or_unfreeze` passes a specific action kind through the existing manual-correction path; generic manual action is not additionally inserted;
- `mark_not_worked` same;
- `mark_training_realized` same; readiness update remains derived;
- manual REST override DecisionRecord remains existing rule provenance, not a second action;
- `finalize` produces one action regardless of Deviation count;
- `revalidate` produces zero actions;
- `plan_month` produces zero actions and only manages final-question readback;
- `replan` produces exactly one REPLAN action plus separately manages the returned final-question pointer;
- first technical WORKING container created by PLAN is not a human action.

## 16. ACTION SOURCE REFERENCES

Stable minimum `source_kind` values:
- `CURRENT_STATE`;
- `AVAILABILITY_VERSION`;
- `DECISION_RECORD`;
- `SCHEDULE_VERSION`;
- `CURRENT_SCHEDULE_POINTER`.

`source_id`:
- Availability -> `availability_version_id`;
- rule decision -> `decision_id`;
- manual/replan/training/freeze/NN/finalize -> relevant `ScheduleVersion.version_id`;
- candidate selection -> current version id;
- restore -> restored version id;
- current-state facts may use their stable entity key or NULL where composite identity is represented in before/after.

Source references are provenance only; action memory never becomes operational current truth.

## 17. APPLICATION READ — EXTEND `memory_read.py`

No UI imports persistence.

### 17.1 Action summary DTO

Define application-local frozen DTOs in `rota/application/memory_read.py` (not `domain.py`) with enough data for T021 list/detail.

`MaterialActionSummary` minimum:
- `action_id`;
- `action_kind`;
- `origin_site_id`;
- `affected_site_ids`;
- `coordinator_id`;
- `recorded_at`;
- `effective_from`;
- `month`;
- `schedule_version_id`;
- `affected_entities`;
- `note`;
- `responds_to_decision_required_id`.

`MaterialActionDetail` adds:
- `before_state` structured object/None;
- `after_state` structured object/None;
- `source_kind`;
- `source_id`;
- `responds_to` stored final-question readback or None.

Do not create human-language Polish summary strings in T019b; T021 owns presentation labels. Structured kind/entities/states are sufficient.

### 17.2 History read

Public read:

`material_action_history(conn, *, site_id=None, affected_entity_kind=None, affected_entity_id=None, action_kind=None, coordinator_id=None, recorded_from=None, recorded_to=None) -> tuple[MaterialActionSummary, ...]`

Semantics:
- every filter optional and AND-composed;
- `site_id` matches `affected_site_ids`, not only origin site;
- entity kind/id pair filters affected entity array; if only one of the pair supplied -> ValueError;
- recorded range inclusive at both ends;
- deterministic newest-first: `(recorded_at DESC, action_id DESC)`;
- no hidden hard limit/pagination in T019b.

### 17.3 Detail read

`material_action_detail(conn, *, action_id: str) -> MaterialActionDetail`

Unknown id -> explicit existing-style not-found exception owned by SiteMemory, not empty fake record.

### 17.4 Current final question readback

`current_decision_required(conn, *, site_id: str, month: date) -> DecisionRequiredReadback | None`

DTO minimum:
- `decision_required_id`;
- `site_id`;
- `month`;
- `schedule_version_id`;
- `requested_by`;
- `recorded_at`;
- `payload: DecisionRequiredPayload`;
- `linked_action_ids: tuple[str, ...]` deterministic.

Month must be first day; no silent normalization.

This returns only current pointer target. Historical snapshots are exposed when linked from action detail; T019b does not add a raw list of every old system question.

## 18. DECISION_REQUIRED SERIALIZATION

Round-trip must preserve all final T013 payload data exactly except normal deterministic JSON representation:
- `BlockingDemand` ids/start/end;
- Blocker employee id + already-rendered `condition`;
- optional LoadBlocker employee/window/hours;
- ordered final `unblocking_options`.

Do not re-run `decision_guidance.py` during readback. Readback is what was shown then, not a re-render against today's names/rules.

Serialization/deserialization helper may live in `site_memory_types.py` or `memory_read.py`; only one canonical mapping in production. Do not duplicate it in persistence and application separately.

## 19. BEFORE/AFTER MINIMUM CONTENT BY ACTION FAMILY

Exact field serialization may use private helpers, but tests freeze semantic content:

- `EMPLOYEE_DAY_ONLY_CHANGED`: employee id + day_only before/after;
- `SITE_MEMBERSHIP_CHANGED`: all planning fields of membership;
- `TARGET_HOURS_CHANGED`: employee, month, target before/after;
- `CALENDAR_DAY_CHANGED`: date, holiday before/after;
- `SITE_PROFILE_CHANGED`: all planning-relevant profile flags + complete StandardShift catalog before/after;
- `SITE_ACTIVE_CHANGED`: site id + active;
- `EXTERNAL_SUPPORT_WINDOW_CHANGED`: window business fields;
- `AVAILABILITY_CHANGED`: previous chain-end record or null -> new AvailabilityRecord;
- `RULE_DECISION_RECORDED`: predecessor decision/rule reference -> new decision/rule reference/content;
- `SCHEDULE_CANDIDATE_SELECTED`: changed/added/removed selected Assignment facts only;
- `SCHEDULE_REPLAN_CREATED`: old current version -> child version;
- manual/freeze/NN/training: parent/child ids + changed Assignment facts; training additionally includes readiness before/after if derived value changes;
- `SCHEDULE_FINALIZED`: status before/after + affected Deviation acknowledgement state;
- `SCHEDULE_RESTORED`: current version id before/after;
- `CONTEXT_CONFIGURATION_SAVED`: supplied planning-relevant Site/Profile state before/after.

Canonical Assignment snapshot contains business/provenance fields already persisted on Assignment; no candidate score/objective/internal solver data.

## 20. NO SECOND TRUTH / NO PLANNING COUPLING

Forbidden:
- importing coordinator action memory from `rota.planning.*`;
- reading `coordinator_action_records` or DR snapshot tables while assembling PlanningState;
- using action history to infer current day_only/membership/target/rules/current version;
- restoring a schedule from action JSON;
- adding `audit_id`/action fields to Domain entities;
- adding a new generic event system.

Current operational repositories remain authoritative.

## 21. TASK_SCOPE

TASK_SCOPE:
- arch/T019b_decision_guidance_readback_architect_brief.md
- tasks/ROTA-T019b/operation_audit.md
- tasks/ROTA-T019b/brief.md
- rota/site_memory_types.py
- rota/persistence/db.py
- rota/persistence/site_memory.py
- rota/persistence/employee_repository.py
- rota/persistence/availability_repository.py
- rota/persistence/work_balance_repository.py
- rota/persistence/calendar_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/application/memory_read.py
- rota/application/bootstrap.py
- rota/application/durable_inputs.py
- rota/application/rule_decisions.py
- rota/application/plan_ops.py
- rota/application/manual_edit.py
- rota/application/training.py
- rota/application/lifecycle_ops.py
- tests/test_audit_t009_r4.py
- tests/test_audit_t009_r5.py
- tests/test_t009_lifecycle_memory_backup_boundary.py
- tests/test_t009_manual_edit.py
- tests/test_t009_plan_select_replan.py
- tests/test_t010_nn.py
- tests/test_t012.py
- tests/test_t019b.py

No other file without STOP + architect amendment after preimplementation audit.

## 22. NEW_FILES / BACKEND BOUNDARY

Full BASE_SHA diff is deliberately designed to stay within repository `MAX_NEW_FILES=2` for non-pipeline artifacts.

Allowed new non-pipeline files:
1. `arch/T019b_decision_guidance_readback_architect_brief.md` — already present owner source;
2. `tests/test_t019b.py` — dedicated implementation matrix.

`tasks/ROTA-T019b/**` are pipeline artifacts excluded by backend.py.

**No new production module is allowed.**

If implementation claims another new production file is necessary, STOP before creating it.

## 23. EXPLICITLY OUT OF SCOPE

Without amendment do NOT change:
- `arch/spec.md`;
- `arch/FROZEN.lock`;
- `rota/domain.py`;
- `rota/planning/*` including engine, decision_guidance, solver, validator;
- `rota/application/analytics_read.py`;
- `rota/application/open_month.py`;
- `rota/application/assembler.py`;
- `rota/application/balance_read.py`;
- T019 analytics semantics;
- T013 rendered texts/options;
- T017 candidate generation/diversity;
- T018 retry/fallback order;
- UI/T021 files;
- backup format;
- generic permissions/login model.

No future-effective day_only/profile/membership model in T019b.

## 24. PREIMPLEMENTATION LEGACY ENUMERATION — REQUIRED

Before CC edits code, Codex must mechanically enumerate existing tests/callers affected by:
- `select_candidate` explicit coordinator actor requirement;
- optional `note`/explicit DR-link parameters if exact signature assertions exist;
- bootstrap transaction composition if tests assert partial commit within one invocation;
- `LATEST_SCHEMA_VERSION=6` / exact migration lists;
- schedule lifecycle optional `on_success` signatures/monkeypatch fakes;
- repository refactor to transaction-neutral sibling helpers;
- exact `memory_read.py` public surface/import expectations.

Required output:
- exact existing file list;
- exact tests/call sites;
- mechanical adaptation vs semantic conflict.

Do not authorize broad legacy rewrites. Any required test file must be added literally to TASK_SCOPE by architect before CC.

## 25. MINIMUM T019b TEST MATRIX

Dedicated `tests/test_t019b.py` must remain <=600 lines using fixtures/parameterization where sensible and prove at minimum:

### A. Schema / append-only / restart
1. migration 5 -> 6 preserves existing data and creates exactly the three T019b tables;
2. action UPDATE rejected;
3. action DELETE rejected;
4. DR snapshot UPDATE rejected;
5. DR snapshot DELETE rejected;
6. current DR pointer may replace/clear;
7. restart preserves action history, current question and explicit links.

### B. Current-state material history
8. day_only false->true records actor/time/effective=today-equivalent, before/after, optional note;
9. employee display-name/legacy active-date-only change creates no material action;
10. membership planning change records before/after;
11. target create/change records old/new and target month effective_from;
12. CalendarDay change records old/new and global affected Sites;
13. SiteProfile catalog/flag change records complete planning profile before/after; display-name-only no action;
14. Site.active change records; display-name-only no action;
15. ExternalSupportWindow change records before/after and its date range;
16. availability append records exactly one action referencing new AvailabilityVersion; existing chain remains intact;
17. no-op current-state material value produces no action row.

### C. Existing histories / one logical action
18. structured SiteRule decision still creates normal DecisionRecord/SiteRuleVersion and exactly one RULE_DECISION_RECORDED action;
19. REST_OVERRIDE_RECORD side effect of one manual correction does not create a second coordinator action;
20. generic manual correction -> one action;
21. freeze -> one ASSIGNMENT_FREEZE_CHANGED only;
22. NN -> one ASSIGNMENT_NOT_WORKED only;
23. training realized -> one TRAINING_REALIZED only; derived readiness before/after included when changed, no separate membership action;
24. finalize N deviations -> one SCHEDULE_FINALIZED with ack details;
25. restore -> one action with pointer before/after;
26. REPLAN -> one action parent->child, no solver attempt entries;
27. candidate selection -> one action and stores only selected candidate delta; unselected T017 candidates never appear.

### D. Actor / dates / notes
28. select_candidate without explicit coordinator actor is rejected before write/history;
29. candidate selection with actor records actual acting coordinator, not version creator fallback;
30. every action note may be None and operation still succeeds;
31. nonempty note round-trips exactly after normalization;
32. current-state immediate facts never claim caller-supplied future effective date;
33. rule/availability/target/ScheduleVersion actions preserve their existing effective dates.

### E. Final DECISION_REQUIRED readback
34. final PLAN DECISION_REQUIRED survives restart with exact T013 rendered payload round-trip;
35. repeated identical PLAN against same schedule context reuses current snapshot, no duplicate question row;
36. a changed final DR creates a new immutable snapshot and moves current pointer;
37. FEASIBLE clears current pointer but not historical snapshots;
38. TECHNICAL_ERROR preserves previous current pointer;
39. no intermediate retry/fallback/raw solver state is stored;
40. persistence failure while storing final DR fails closed to public TECHNICAL_ERROR, never returns unpersisted DR;
41. persistence failure while clearing stale question prevents returning FEASIBLE as if current readback were coherent.

### F. Explicit link / staleness
42. action with no link remains unlinked even when a current DR exists immediately before it;
43. explicit link to current same-Site question succeeds and action detail returns exact historical question after pointer is cleared/replaced;
44. link to noncurrent/unknown/wrong-Site question fails before business mutation;
45. material action invalidates affected current question in same transaction without claiming it solved the question;
46. target invalidates only affected month/Sites;
47. availability/window invalidates overlapped months;
48. global/current employee or profile change invalidates current questions for all affected Sites;
49. rule decision invalidates only currently stored question months intersecting its effective interval.

### G. Atomicity
50. injected action insert failure rolls back day_only/current-state business mutation;
51. same for Availability append;
52. same for DecisionRecord/SiteRuleVersion operation;
53. same for candidate selection in-place snapshot;
54. same for manual child creation;
55. same for training child + readiness;
56. same for finalize acknowledgements/status;
57. same for restore pointer;
58. same for REPLAN child/current pointer.

### H. Read API / filters / determinism
59. history sorted recorded_at desc + action_id desc tie-break;
60. Site filter uses affected_site_ids and shared Employee action appears once in each affected Site filter result, not duplicated in storage;
61. entity filter kind+id works; half-specified entity filter rejects;
62. action_kind filter;
63. coordinator filter;
64. inclusive recorded date/time range;
65. detail returns before/after/source/note/link;
66. unknown action id raises explicit not-found;
67. current_decision_required validates first-day month;
68. no raw list API exposing unlinked historical system questions is added.

### I. Non-regression
69. existing Decision Ledger chain/effective selection PASS;
70. existing availability history PASS;
71. T013 DECISION_REQUIRED communication oracles PASS unchanged;
72. T017 multi-candidate generation/selection semantics PASS except explicit actor adaptation;
73. T018 fallback order/pass behavior PASS;
74. schedule manual/finalize/restore lifecycle regressions PASS;
75. T016 EMP-02 retirement PASS;
76. T019 analytics PASS;
77. planning module remains free of persistence imports;
78. action/DR memory tables are absent from PlanningState assembly/solver reads.

## 26. PREIMPLEMENTATION CODEX AUDIT

Codex audits exact contract SHA and answers:

1. Is `operation_audit.md` exhaustive for every public write-capable `rota.application.*` operation on BASE_SHA?
2. Are MATERIAL/NO classifications consistent with owner intent and frozen product boundaries?
3. Does the architecture keep Decision Ledger rule-specific rather than overload it?
4. Is one append-only action index + immutable final DR snapshots + current pointer the smallest coherent storage model?
5. Do new memory tables remain historical/readback only and never become planning truth?
6. Is effective_from truthful and does T019b avoid fake future-effective current-state behavior?
7. Is one operation = one action enforced for manual wrappers/training/REST override/finalize?
8. Is select_candidate's actor made explicit without changing T017 candidate semantics?
9. Are domain write + action + stale-question invalidation atomic for every MATERIAL operation?
10. Is final DR capture strictly after existing T018/T013 final rendering, with no retry trace?
11. Are FEASIBLE/TECHNICAL_ERROR pointer semantics fail-closed and coherent?
12. Is explicit question->action linking impossible to infer automatically?
13. Do affected_site_ids correctly handle shared Employee/global Calendar/Profile facts without duplicating action rows?
14. Can T021 meet required history/detail/filter/readback UX using only application reads?
15. Does full BASE design truly add no new production module and stay at exactly two non-pipeline new files (owner brief + dedicated test)?
16. Which exact legacy tests/callers need mechanical adaptation?
17. Does any clause require a new owner product decision? If yes, FAIL with exact clause; do not guess.

Required verdict:

`PASS — READY_FOR_IMPLEMENTATION`

Until that PASS:

**CC MUST NOT START T019b IMPLEMENTATION.**

## 27. IMPLEMENTATION RULES FOR CC

After preimplementation PASS:
- edit only amended literal TASK_SCOPE;
- do not introduce another storage/read module;
- do not write SQL in application modules;
- do not change planning code;
- do not log internal solver events;
- do not require note/rationale;
- do not create duplicate action rows from nested calls;
- preserve existing operational source of truth;
- each atomicity blocker -> STOP to architect before workaround.

## 28. FINAL IMPLEMENTATION GATE

Codex audits exact PRODUCT SHA and full `BASE_SHA -> PRODUCT_SHA` diff.

Required:
- dedicated T019b matrix PASS;
- all architect-authorized legacy adaptations PASS;
- full `tests/` PASS;
- Decision Ledger/T005 regressions PASS;
- schedule lifecycle/manual/training/finalize/restore regressions PASS;
- T013/T017/T018/T019 regressions PASS;
- schema migration tests PASS including legacy upgrade and v5->v6;
- restart/readback/link tests PASS;
- atomicity fault-injection tests PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS;
- `git diff --check` PASS;
- `arch/spec.md` and `arch/FROZEN.lock` unchanged;
- backend.py full BASE gate; every REASON/WYMAGA_DECYZJI returns to architect with exact PRODUCT SHA;
- NEW_FILES full-base count <=2 with exactly the allowed non-pipeline new files;
- no UI files;
- no planning module change/import to persistence/action memory.

Only after Codex implementation PASS + architect review:

`ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T019b: PASS — READY FOR MERGE`
