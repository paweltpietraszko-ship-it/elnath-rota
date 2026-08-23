# ROTA-T021 — ARCHITECT INPUT AFTER ROUND-1 UI FACT AUDIT

STATUS: INPUT FOR OWNER/ARCHITECT DECISIONS — NOT AN IMPLEMENTATION CONTRACT
MATERIAL_HEAD: `task/ROTA-T021@7a4aaa3479433596819ebeff0be536693afda8a1`
BASE: `main@5e8f282c8208441b25f0f0a3e0f44016c7162a6a`

## 1. Purpose and authority boundary

T021 needs a consolidated implementation contract, but the current material is not ready to become one by simple copy/paste. Round-1's six mockup blockers have factual answers, while four later completeness items still require explicit owner/architect decisions. The material also contains one direct contradiction about `+ Nowy obiekt` and an unresolved dependency boundary with T025/PWA.

The architect must resolve those items without implementation. If an item requires a product choice, request/record Paweł's ruling rather than infer it from a plausible screen placement.

Controlling product truth remains:

1. frozen owner/spec decisions already present in `arch/` and the implemented application/domain contracts on `main@5e8f282`;
2. explicit owner rulings recorded in `arch/T021_ui_facts_2026-08-21.md`;
3. the new owner rulings requested by this brief;
4. only then a consolidated `tasks/ROTA-T021/brief.md`.

Supporting material, not independently controlling:

- `arch/T021_spec.md` — detailed per-screen fact map, but not frozen and internally inconsistent in the places named below;
- `arch/T021_implementation_pipeline_DRAFT.md` — suggested grouping only, explicitly not a decided sequence;
- `arch/T021_round1_audit_response_2026-08-22.md` — verified disposition of the Round-1 blockers;
- both Cursor audit folders — factual audit inputs, not task contracts;
- `Grafiki/Zrzut ekranu (630).png` — historical PDF/reference screenshot;
- `Grafiki/Zrzut ekranu (631).png` — historical Round-1 mockup screenshot, not the corrected contract and not an editable mockup artifact.

Do not import the unrelated C1-C7 findings from `tasks/CURSOR_AUDIT_2026-08-21/FINDINGS_VERIFIED.md` into T021 merely because that audit is present on the branch. They require their own task/owner classification. Only T021 facts explicitly adopted into the current UI material participate here.

## 2. Round-1 blockers already factually closed

The architect should record these as preserved facts, not reopen them as product questions.

### R1-1 — backup and diagnostics placement

`backup.backup_database` and `build_diagnostic_zip` operate on the whole SQLite database, not one Site. Their confirmed UI home is Workspace/Przedpokój, outside a Site room (`T021_spec.md:383-391`).

### R1-2 — training surface

There is no standalone training screen. `training.mark_training_realized` is a side effect of marking a TRAINEE Assignment REALIZED through the existing manual-correction flow. The per-employee screen shows derived `ReadinessState` as the S/szkolenie badge. Editing the SiteProfile training policy is a separate open decision in section 3; it must not be conflated with inventing a training nav item.

### R1-3 — candidate count

`PlanningResult.candidates` contains 1, 2 or 3 `list[Assignment]` candidates. UI must render the returned count rather than assume exactly two.

### R1-4 — candidate labels and deviation counts

The backend supplies no strategy/name field and no per-candidate deviation count. Candidates are generic numbered choices (`Wariant 1..3`); invented labels such as “Równomierne obciążenie” and candidate-specific deviation summaries are not backend facts.

### R1-5 — complete SitePrintSettings shape

The editable print configuration must represent the complete frozen DTO:

- `company_print_name`, `site_print_name`;
- `base_regime` (`12h` or `24h`);
- optional intervals for exactly `D1..D5,N1..N5`, with frozen code durations not editable by the coordinator;
- optional integer reserve hours for exactly `U3,U4,U5,C3,C4,C5`.

### R1-6 — formerly nav-only screens

All five formerly nav-only screens now have source-backed content sections in `T021_spec.md`:

- Decyzje koordynatora (`memory_read` + `decision_guidance`);
- Ręczna korekta (`manual_edit` plus the owner-required preview gap);
- Historia i audyt (`memory_read`, two distinct streams);
- Analityka i bilanse (`analytics_read`);
- Wydruk Grafiku (`schedule_export`).

Round-1's FAIL must not be carried forward as if these six items were still unanswered. Corrected behavior must still be visible in the accepted editable mockup and later regression/interaction criteria.

## 3. Product decisions still open

The architect must obtain or record an explicit disposition for every item below: authorize in T021 with exact placement/fields, defer to a named task, or exclude with a traceable owner reason. “The backend already has a function” is not itself authorization to expose a control.

### D1 — calendar/holiday editing (`set_calendar_day`)

Facts:

- `durable_inputs.set_calendar_day(coordinator_id, site_id, day, note, responds_to_decision_required_id)` exists;
- `CalendarDay` is keyed by date globally, not by Site;
- `site_id` authorizes the write but is not persisted on the calendar fact;
- changing one day records `CALENDAR_DAY_CHANGED` and invalidates that month across all affected Sites.

Required decision:

- whether calendar editing is in T021 at all;
- exact screen placement and who can reach it;
- whether the UI must explicitly warn that the holiday value is global and may invalidate schedules for multiple Sites;
- required month/range interaction and confirmation behavior;
- whether a response reached from Decyzje koordynatora must thread `responds_to_decision_required_id` through this action.

Do not silently place a global calendar toggle inside one Site's settings without this ruling.

### D2 — SiteProfile policy controls

Open fields named by the completeness audit:

- `day_only_blocks_n`;
- `external_support_enabled`;
- `training_s_enabled`;
- `training_s_weekdays_only`;
- `training_s_default_readiness_threshold`.

Facts:

- `durable_inputs.update_site_profile` writes the complete `SiteProfile`, not an isolated toggle command;
- a profile also carries `active`, `standard_shifts` and `rolling_7d_decision_threshold_hours`;
- a material profile change invalidates all Sites bound to that profile, so the control cannot pretend it is necessarily local to the currently open Site;
- the current material shows `rolling_7d_decision_threshold_hours` read-only; this brief does not reopen that separate presentation choice unless the owner does.

Required decision for each of the five fields: editable now, read-only now, or deferred. For fields authorized as editable, name the screen, describe the shared-profile impact that must be visible to the coordinator, and require preservation of every unedited SiteProfile field during the aggregate write.

Training policy controls are not the same thing as the derived per-employee S/szkolenie badge or the existing manual readiness override path.

### D3 — Site editing (`update_site`)

Facts:

- the mutable fields are `display_name` and `active`;
- `site_id` remains identity and `profile_id` may not be rebound through this operation;
- only active-state change is currently recorded as `SITE_ACTIVE_CHANGED` and causes invalidation; an ordinary display-name update is a current-state write without that material action.

Required decision:

- whether name editing and/or active-state editing belongs in T021;
- exact placement;
- whether deactivation requires an explicit confirmation and where the user returns after the currently open Site becomes inactive;
- whether the current audit behavior for display-name-only changes is accepted as-is or belongs to a separate backend/audit task. Do not change it implicitly inside UI work.

### D4 — `+ Nowy obiekt` / bootstrap flow

The source material currently contradicts itself:

- `T021_round1_audit_response_2026-08-22.md` and the current handoff classify placement/flow as still open;
- `T021_spec.md:393-406` says `DECIDED + BUILT`: Workspace inline form;
- `T021_implementation_pipeline_DRAFT.md` also says “DECIDED and mocked.”

This must receive a fresh explicit owner ruling. The later “DECIDED” prose is not sufficient evidence by itself while the handoff source says the decision was never authorized.

Backend constraints the ruling must respect:

- `bootstrap_or_resume_coordinator_context` accepts optional complete `Coordinator`, `SiteProfile`, `Site` and `CoordinatorSiteAssociation` domain objects and can resume partial context over several calls;
- it does not define a frontend create-site DTO or defaults for a partially specified SiteProfile;
- `SiteProfile` requires active state, standard shifts, all policy toggles and both threshold values;
- the proposed three-field form (site name, profile name, 7-day threshold) therefore needs explicit defaults/staging rules for every omitted required field rather than inventing them in CC implementation;
- an already complete active coordinator/Site context is rejected and must use authorized edit operations instead;
- under T025 the acting coordinator comes from real authentication, not the superseded no-password identity picker.

Required decision:

- include/defer/exclude;
- Workspace inline form vs. another explicitly named flow;
- exact minimum input DTO and owner-approved defaults, or a defined multi-step partial bootstrap;
- how IDs are generated/entered;
- what is created atomically on the first submission;
- expected post-create destination and how `Konfiguracja niepełna` guides completion.

## 4. Additional scope classifications the final contract must make explicit

These are not reopened Round-1 blockers, but leaving them implicit would produce an untestable implementation scope.

### 4.1 Per-employee edits

Current code permits `readiness_source=COORDINATOR_OVERRIDE` and changing `membership_kind` between LOCAL and EXTERNAL_SUPPORT. Current material suggests controls on the existing per-employee screen but does not identify a separate owner ruling. The architect must either trace those controls to an accepted decision and include them, or mark them deferred/read-only. Do not infer authorization solely from writable backend fields.

The absence log itself is factually resolved: its complete current source is `get_current_availability_for_employee`; `employee_availability_matrix` is narrower and cannot replace it.

### 4.2 New backend work already owner-required

The manual-correction dry-run is authorized and foundational. The final contract must define its exact application API/result and no-write invariant, shared validation path with the real save, preview invalidation after any pending edit, and coverage of generic correction/freeze/NN flows. It may not be replaced by “save, then show deviations.”

Two thin application wrappers are known gaps and need an explicit task disposition:

- `current_decision_required_months_for_site` wrapper in `memory_read.py`;
- save/read boundary for `SitePrintSettings` in `durable_inputs.py` (persistence functions already exist).

The EmployeeDetail availability read has the same persistence-without-application-wrapper shape. State whether T021 adds a wrapper or authorizes the UI/application layer to use the existing repository read; do not leave the dependency unnamed.

### 4.3 T023/T026 status correction

The DRAFT pipeline's NB-3 statement that T023 is still blocked is stale at this material base. T023 and the post-T023 T026 canonical ownership repair are already present on `main@5e8f282`. The final T021 contract must treat their current APIs/behavior as the baseline, not as future pending work.

### 4.4 Backend text gap

The no-anglicisms UI rule is preserved. `DAY_SHIFT_OFF-01` currently lacks a Polish backend rendering. The architect must name whether its backend correction is an allowed T021 prerequisite/file or a separate task dependency; UI code must not display the raw code.

## 5. T025/PWA dependency boundary

T025 changes the delivery shell but does not invalidate T021's screen data/action mapping:

- hosted responsive PWA on Railway replaces the local Tauri/no-password-picker assumption;
- real authentication, hosted API/transport and database deployment strategy are T025 architecture work and are not decided by T021;
- no T021 screen may implement the superseded coordinator identity picker;
- every coordinator-scoped T021 action still requires a verified acting `coordinator_id` and Site association.

Required architect output: a sequencing/interface ruling that says which T021 work may proceed against an abstract authenticated-session/API boundary, which parts are blocked by T025, and which files/tasks own the adapter. Do not copy F1-F4 design into T021 or leave the workspace shell dependent on an undefined login mechanism.

## 6. Mockup gate and reference images

Paweł's preserved process decision requires an editable mockup before UI implementation. The branch currently contains only reference PNGs, not the editable canvas/source.

- `Zrzut ekranu (631).png` is historical Round-1 evidence and still visibly shows exactly two named candidates; it cannot prove the corrected 1..3 generic selector.
- `Zrzut ekranu (630).png` is a PDF rendering reference, not an implementation-ready screen artifact.

Before authorizing frontend code, the architect must name the exact accessible editable mockup artifact/revision, its owner, and the acceptance record showing all Round-1 corrections plus every newly decided D1-D4 control. Updated screenshots alone may be audit evidence but do not satisfy the owner's “editable mockup” requirement.

## 7. Required architect deliverables

Produce, without implementation:

1. an owner-decision record for D1-D4, with one explicit disposition per item and no inferred defaults;
2. a contradiction-resolution note stating which T021 source statements are superseded, especially the `+ Nowy obiekt` and “zero open decisions” claims;
3. a T025/T021 dependency and sequencing boundary;
4. an explicit disposition for section 4.1, the three wrapper/read-boundary gaps, the dry-run API and `DAY_SHIFT_OFF-01` translation;
5. an editable-mockup gate naming the exact artifact/revision that must pass before frontend implementation;
6. only after the required owner rulings, `tasks/ROTA-T021/brief.md` with:
   - controlling-source precedence and exact base SHA;
   - exact TASK_SCOPE and OUT_OF_SCOPE;
   - backend prerequisites versus frontend screen units;
   - checkpoint/build ordering and dependency gates;
   - per-screen input/output/action/error contracts;
   - `responds_to_decision_required_id` threading rules;
   - Polish UI text/error mapping requirements;
   - regression/interaction/visual acceptance matrix;
   - full-suite, Ruff, frozen, scope/size and visual-review final gates.

If D1-D4 or the T025 boundary remain undecided, do not label an implementation brief READY. Produce the decision request first and stop at the missing authority.

CC must not implement T021 before an independent Codex preimplementation PASS on the exact consolidated contract SHA and acceptance of the exact editable mockup revision.

## 8. Explicit non-goals for this architect pass

- no implementation or migration;
- no redesign of the frozen flat eight-item Site nav without a new owner instruction;
- no new payroll/HR/legal settlement behavior;
- no reopening T023/T026 absence accounting;
- no T025 authentication/API/database design inside T021;
- no coordinator-account administration screen unless the owner explicitly expands scope;
- no light/dark toggle;
- no adoption of unrelated Cursor C1-C7 findings as T021 work;
- no invented UI fields, candidate metadata, defaults or backend guarantees.
