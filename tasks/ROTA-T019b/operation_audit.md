# ROTA-T019b — predesign audit of coordinator-facing application mutations

STATUS: FROZEN INPUT TO T019b ARCHITECT CONTRACT
DATE: 2026-08-20
BASE_SHA: 102273b553783b5a083a60d5ee9964e9ec67221a
OWNER_SOURCE: arch/T019b_decision_guidance_readback_architect_brief.md

## 1. Purpose

This audit enumerates public write-capable `rota.application.*` operations on the post-T019 main baseline and classifies whether one successful invocation is a material coordinator action for schedule memory.

The unit is the application operation, never an individual SQL statement. Derived system side effects and solver internals are not independent coordinator actions.

Columns:
- MATERIAL: whether T019b must create one coordinator-action history entry;
- CURRENT HISTORY: what durable provenance exists before T019b;
- GAP: missing owner-required provenance;
- DR LINK: whether the action may explicitly link to the currently stored final DECISION_REQUIRED question;
- EFFECTIVE FROM: the truthful date T019b records without inventing future-effective semantics.

## 2. Frozen classification matrix

| Application operation | MATERIAL | CURRENT HISTORY | GAP before T019b | DR LINK | EFFECTIVE FROM |
|---|---|---|---|---|---|
| `bootstrap.bootstrap_or_resume_coordinator_context` | CONDITIONAL YES when `site_profile` and/or `site` scheduling configuration is supplied; NO when the call only establishes Coordinator/Association access metadata | Site/Profile are mutable current-state; no action history | actor/time/before-after/note absent | no practical open question is expected before an active context, but optional link is not required for bootstrap | `recorded_at.date()`; bootstrap does not become future-dated configuration |
| `durable_inputs.add_external_support_window` | YES | mutable current-state UPSERT | actor/time/before-after/action note/link absent | YES | `window.start_datetime.date()`; the window already owns its applicability interval |
| `durable_inputs.append_availability` | YES | append-only AvailabilityVersion chain; user `note` already exists | actor, recorded_at, Site context and explicit DR link absent | YES | `start_date` from the AvailabilityRecord; do not add a second applicability date |
| `durable_inputs.update_employee` | YES only when `day_only` changes or an Employee is first created with its initial `day_only`; NO for display name and retired `active_from/active_to` alone | mutable current-state UPSERT | no historical day_only transition, actor/time/before-after/note/link | YES | `recorded_at.date()` because `Employee.day_only` is a current boolean and takes effect immediately in today's model |
| `durable_inputs.update_membership` | YES when any membership planning field changes/row is created: kind, enabled, readiness state/source, `can_work_24h` | mutable current-state UPSERT | no history/actor/time/before-after/note/link | YES | `recorded_at.date()`; SiteMembership is not effective-dated |
| `durable_inputs.set_target_hours` | YES when value is created/changed | mutable current-state `(employee, month)` | no history/actor/time/before-after/note/link | YES | target `month` itself |
| `durable_inputs.set_calendar_day` | YES when holiday flag is created/changed | mutable current-state by date | no history/actor/time/before-after/note/link | YES | `CalendarDay.date` |
| `durable_inputs.update_site_profile` | YES when any planning-relevant profile field/StandardShift/active flag changes; NO for display name alone | profile + full shift list overwritten atomically, no version history | actor/time/before-after/note/link absent | YES | `recorded_at.date()`; profile is current-state, not future-versioned |
| `durable_inputs.update_site` | YES only when `active` changes/row is first established; NO for display name alone; `profile_id` rebinding is already forbidden | mutable current-state | actor/time/before-after/note/link absent | YES | `recorded_at.date()` |
| `durable_inputs.update_coordinator` | NO | mutable access/identity current-state | not a schedule decision | NO | n/a |
| `durable_inputs.update_association` | NO | mutable access current-state | not a schedule-content/planning-input decision | NO | n/a |
| `rule_decisions.record_structured_rule_decision` | YES | append-only DecisionRecord + SiteRuleVersion, actor/recorded_at/effective_from already durable | unified action index, optional action note, explicit DR link absent | YES | existing `effective_from` |
| `plan_ops.plan_month` | NO coordinator-action entry; YES final-question readback side effect | may create technical first WORKING container; PlanningResult itself transient | final DECISION_REQUIRED is lost on restart | n/a as an action | n/a |
| `plan_ops.select_candidate` | YES | chosen candidate replaces current WORKING snapshot in place; unselected candidates intentionally not stored | explicit selecting actor can be missing via legacy fallback; prior selection can be overwritten; note/link absent | YES | current ScheduleVersion `effective_from`; legacy NULL remains genuinely unknown |
| `plan_ops.replan` | YES | creates append-only child ScheduleVersion with actor/time/effective_from and moves current pointer; solver result transient | explicit action kind/note/link absent; final DR transient | YES | existing `effective_from` argument |
| `manual_edit.apply_manual_correction` | YES | append-only child ScheduleVersion, parent link, actor/time/effective_from, derived Deviation | action kind/note/link and compact changed-fact readback absent | YES | existing `effective_from` |
| `manual_edit.freeze_or_unfreeze` | YES; exactly one action, not an extra action plus generic manual-correction action | same child-version mechanism | named intent/note/link absent | YES | existing `effective_from` |
| `manual_edit.mark_not_worked` | YES; exactly one action | same child-version mechanism, NN persisted on child | named intent/note/link absent | YES | existing `effective_from` |
| `training.mark_training_realized` | YES; exactly one action | manual-correction child + derived DEFAULT readiness update in same transaction | named intent/note/link absent; derived readiness must not become a second human action | YES | existing `effective_from` |
| `lifecycle_ops.revalidate` | NO | deterministic in-place refresh of Deviations/applied rules | this is a system recomputation, not a coordinator decision | NO | n/a |
| `lifecycle_ops.finalize` | YES, including the exact Deviation acknowledgements performed by this operation | FINAL status + Deviation `acknowledged_by/at/reason` survive; transition itself has no unified action entry | one action entry/link/filterable provenance absent | YES | ScheduleVersion `effective_from`; `recorded_at` separately says when finalization occurred |
| `lifecycle_ops.restore` | YES | only current pointer changes; ScheduleVersions remain | no durable history of who/when/which pointer transition/note/link | YES | `recorded_at.date()` because restore changes current immediately and does not rewrite the restored version's original `effective_from` |
| `backup.backup_database` | NO | writes external backup file only | not a scheduling decision | NO | n/a |
| `backup.build_diagnostic_zip` | NO | writes diagnostic artifact only | not a scheduling decision | NO | n/a |
| `store.open_store` | NO | may perform schema migration as system maintenance | not a coordinator decision | NO | n/a |

## 3. Read-only / pure application modules checked

The following current modules expose no coordinator-facing business mutation and therefore do not get action instrumentation:

- `analytics_read.py`;
- `assembler.py`;
- `availability_matrix.py`;
- `balance_read.py`;
- `context.py`;
- `deviation_mapping.py`;
- `errors.py`;
- `memory_read.py` (will be extended only with reads in T019b);
- `open_month.py`;
- `precheck.py`.

## 4. Existing history boundaries

### 4.1 Decision Ledger — keep as-is semantically

`decision_records` is append-only and linear by `(site_id, rule_id)`. It correctly owns structured SiteRule decisions and REST_OVERRIDE_RECORD provenance. It must NOT become the generic store for employee flags, target hours, schedule selection or restore.

T019b adds a cross-cutting human-action index entry when the public `record_structured_rule_decision` operation succeeds. The action entry references the resulting DecisionRecord and does not duplicate or replace SiteRule execution truth.

A REST_OVERRIDE_RECORD created internally by a manual correction is NOT an additional coordinator action entry. The manual correction is the one human operation.

### 4.2 Availability history

Availability is already append-only by logical `availability_id`, but versions do not record coordinator, recorded_at or Site context. T019b preserves the AvailabilityVersion chain and adds one action entry referencing the new version.

### 4.3 Schedule history

Child ScheduleVersions already preserve manual-correction/REPLAN/training history well. T019b does not replace that lineage. It adds the missing human-action classification, optional note and explicit DECISION_REQUIRED link.

Two lifecycle gaps require historical before/after in the action index:
- candidate selection overwrites the same WORKING snapshot;
- restore overwrites only the current pointer.

Finalize also gets one action entry so Deviation acknowledgement + FINAL transition can be found as a coordinator action.

### 4.4 Mutable current-state inputs

Employee.day_only, membership, target hours, CalendarDay, SiteProfile, Site.active and ExternalSupportWindow currently overwrite current rows. Their action entry therefore stores the changed fact's structured before/after snapshot; it is historical evidence only and is never read by planning as current truth.

## 5. Effective-from boundary

T019b must never invent delayed applicability that the existing model cannot enforce.

Existing effective-dated facts keep their existing date:
- SiteRule: DecisionRecord/SiteRuleVersion `effective_from`;
- Availability: `start_date`;
- target hours: target month;
- CalendarDay: its date;
- ExternalSupportWindow: window start date;
- ScheduleVersion child actions: existing ScheduleVersion `effective_from`.

Current-state booleans/configuration (`day_only`, membership, profile, Site.active) take effect in the program immediately after their successful write. Their historical `effective_from` is therefore `recorded_at.date()`.

T019b does NOT introduce future-effective Employee/SiteMembership/SiteProfile versions. A future requirement such as entering `day_only=True` on 12 March but making planning apply it only from 1 April is a separate product capability, not an audit-field trick.

## 6. One operation = one action entry

The following wrappers MUST NOT double-log:

- `freeze_or_unfreeze` -> one `ASSIGNMENT_FREEZE_CHANGED`, not also `MANUAL_SCHEDULE_CORRECTION`;
- `mark_not_worked` -> one `ASSIGNMENT_NOT_WORKED`;
- `mark_training_realized` -> one `TRAINING_REALIZED`; derived readiness is part of its after-state when it changes;
- manual correction that also writes REST_OVERRIDE_RECORD -> one `MANUAL_SCHEDULE_CORRECTION`; the rule audit record remains in Decision Ledger but is not a second human action;
- finalize with N acknowledged Deviations -> one `SCHEDULE_FINALIZED`, not N action entries.

PLAN/solver retries/T018 fallback attempts never create action entries.

## 7. Required action kinds

Frozen minimum stable kinds:

- `CONTEXT_CONFIGURATION_SAVED`;
- `EXTERNAL_SUPPORT_WINDOW_CHANGED`;
- `AVAILABILITY_CHANGED`;
- `EMPLOYEE_DAY_ONLY_CHANGED`;
- `SITE_MEMBERSHIP_CHANGED`;
- `TARGET_HOURS_CHANGED`;
- `CALENDAR_DAY_CHANGED`;
- `SITE_PROFILE_CHANGED`;
- `SITE_ACTIVE_CHANGED`;
- `RULE_DECISION_RECORDED`;
- `SCHEDULE_CANDIDATE_SELECTED`;
- `SCHEDULE_REPLAN_CREATED`;
- `MANUAL_SCHEDULE_CORRECTION`;
- `ASSIGNMENT_FREEZE_CHANGED`;
- `ASSIGNMENT_NOT_WORKED`;
- `TRAINING_REALIZED`;
- `SCHEDULE_FINALIZED`;
- `SCHEDULE_RESTORED`.

No `PLAN_ATTEMPT`, `SOLVER_RETRY`, `FALLBACK_STAGE`, `REVALIDATE` or derived-readiness action kind.

## 8. Site and affected-entity semantics

Every action stores:
- `origin_site_id`: the active coordinator context in which the action was performed;
- `affected_site_ids`: a sorted snapshot of Sites whose currently modeled planning input can be affected by this action;
- structured affected entities (at minimum `entity_kind` + `entity_id`).

This avoids pretending that a cross-Site Employee/Calendar fact belongs to exactly one Site while still preserving where the coordinator performed the action.

Examples:
- day_only / availability / target: affected Sites are the Employee's enabled membership Sites at write time; if none, preserve `origin_site_id` so the action is still discoverable;
- CalendarDay: all currently stored Sites are affected;
- SiteProfile: all Sites currently bound to that profile;
- membership/rule/window/schedule action: the named Site;
- a shared Employee action is one action with several affected Site ids, never duplicated per Site.

Site filtering in the T019b read model means `site_id in affected_site_ids`. Detail also exposes `origin_site_id`.

## 9. DECISION_REQUIRED classification

A final coordinator-facing DECISION_REQUIRED is a question/context, not a human action.

T019b stores only the final `DecisionRequiredPayload` returned by `plan_month`/`replan`, after all existing T018 retries and T013 rendering. No internal solver blocker trace, failed stage or unselected candidate is stored.

A successful material action may carry an optional explicit `responds_to_decision_required_id`. Temporal proximity alone never creates a link.

## 10. Predesign result

The existing rule Decision Ledger is necessary but insufficient. The smallest coherent T019b solution is:

1. keep Decision Ledger and all existing domain histories as their current owners;
2. add one append-only coordinator-action index inside existing SiteMemory persistence;
3. add immutable final DECISION_REQUIRED snapshots plus a mutable current pointer;
4. extend existing application mutators so the relevant domain write and one human-action index insert commit atomically;
5. extend existing `memory_read.py` with structured history/current-question reads for T021;
6. never let the new memory tables influence PlanningState, solver, validator, WorkBalance or current operational truth.
