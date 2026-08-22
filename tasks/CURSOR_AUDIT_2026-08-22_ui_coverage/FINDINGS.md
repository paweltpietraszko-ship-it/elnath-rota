# Cursor audit — T021 UI coverage vs `rota/application`

DATE: 2026-08-22
SHA: `e05dfb7`
SPEC: uploaded `T021_spec.md` (copied here; not on `origin/main`)
REQUEST: seven already-in-spec items — confirmed present in COMPLETENESS AUDIT / later notes. Not re-listed below.

Sanity check: the seven REQUEST items are the same file. Scan did **not** stop at those seven.

No fix proposals. No PASS/FAIL.

---

## A. OMISSIONS

Public `rota/application/` functions with no name and no clear paraphrase in `T021_spec.md`. Known-seven and functions the spec already names as gaps (`update_site`, `mark_training_realized`, identity-switcher reads) are excluded.

### A1. `bootstrap_or_resume_coordinator_context`

- `rota/application/bootstrap.py:188`
- First write / resume of Coordinator → SiteProfile → Site → Association. Raises `CoordinatorContextAlreadyActive` once the ordinary edit path works.
- Natural fit: Workspace / first-run, or Panel before any Site exists. Spec Workspace assumes `list_sites` / `active_sites_for_coordinator` already have rows.

### A2. `all_sites_for_coordinator`

- `rota/application/bootstrap.py:383`
- Every association for a coordinator, including inactive Site / inactive association.
- Natural fit: identity switcher / admin “co istnieje” (T011-B W3 pair). Spec names `active_sites_for_coordinator` and persistence `list_sites`, not this.

### A3. `availability_history`

- `rota/application/availability_matrix.py:75`
- Full append-only chain for one `availability_id` family.
- Natural fit: EmployeeDetail absence log (spec only describes current `AvailabilityKind` rows, not the version chain).

### A4. `quarter_balance`

- `rota/application/balance_read.py:15`
- Fail-closed quarter reconstruct: empty list + warning if any of the three calendar-quarter months lacks `target_hours` (including future months).
- Natural fit: Analityka i bilanse. Spec’s only read is `analytics_for_site_month` (different degrade rules).

### A5. `decision_chain_for_rule_family`

- `rota/application/memory_read.py:32`
- `rule_history` for one `(site_id, rule_id)`.
- Natural fit: Historia i audyt → Historia reguł. Spec lists `rules_history_for_site` / `provenance_for_rule_version` / `decision_for_rule`, not this sibling.

### A6. `generate_profile_demands`

- `rota/application/assembler.py:60`
- Builds `ShiftDemand`s from `SiteProfile.standard_shifts` for a month.
- Natural fit: none (assembler). Panel Obiekt katalog zmian is described without this function.

### A7. `resolved_rule_version_ids`

- `rota/application/assembler.py:48`
- Rule version ids stamped onto a new `ScheduleVersion`.
- Natural fit: none (called by plan/lifecycle, not a screen).

### A8. `category_for_rule`

- `rota/application/deviation_mapping.py:37`
- Maps validator rule code → `DeviationCategory`.
- Natural fit: none (used when materializing Deviations after korekta / revalidate).

### A9. `save_site_membership`

- `rota/application/training.py:24`
- Unguarded membership write for the training `on_success` hook / tests.
- Natural fit: none. Not `update_membership`.

### A10. `require_real_date`

- `rota/application/errors.py:61`
- Rejects `datetime` where a calendar `date` is required (`effective_from`).
- Natural fit: none (guard used by PLAN/REPLAN/korekta).

---

## B. INACCURACIES

### B1. Write signatures drop required `coordinator_id`

Spec Planowanie (`T021_spec.md` ~376–423):

- claims `plan_month(site_id, month, effective_from=None)`
- claims `select_candidate(site_id, month, candidate, note=, responds_to_decision_required_id=)`
- claims `replan(site_id, month, effective_from, note=, responds_to_decision_required_id=)`
- claims `finalize(site_id, month, acknowledged_deviation_ids, reason=)`
- claims `restore(site_id, month, version_id)`
- claims `revalidate(site_id, month)`

Code (all keyword-only after `conn`):

- `plan_month` — `rota/application/plan_ops.py:90` — required `coordinator_id`
- `select_candidate` — `plan_ops.py:185` — required `coordinator_id`; `None` raises `MissingCoordinatorActor` (`plan_ops.py:29`, `:198-199`)
- `replan` — `plan_ops.py:250` — required `coordinator_id`
- `finalize` — `lifecycle_ops.py:91` — required `coordinator_id`; also `responds_to_decision_required_id`
- `restore` — `lifecycle_ops.py:132` — required `coordinator_id`; also `note`, `responds_to_decision_required_id`
- `revalidate` — `lifecycle_ops.py:45` — `coordinator_id` optional; if omitted, actor is `header.created_by` (`:50-51`)

Omitting `conn` is consistent style in the spec. Omitting the acting coordinator is not: every write except the `revalidate` fallback goes through `require_active_coordinator_context`.

### B2. Workspace site list vs later decision

- Spec Workspace (`T021_spec.md` ~282–289): source is `rota/persistence/site_repository.py::list_sites` — all Site rows, no coordinator.
- Spec COMPLETENESS / switcher (`T021_spec.md` ~59–65, ~105–110): `Main.dc.html` uses `bootstrap.active_sites_for_coordinator(coordinator_id)` (`bootstrap.py:373`).

Those are different sets. `active_sites_for_coordinator` keeps `association.active` and `Site.active` and does **not** check `Coordinator.active` (`bootstrap.py:373-377`). `list_sites` is every site in the store.

### B3. `analytics_for_site_month` “never throws”

- Spec Analityka (`T021_spec.md` ~586–588): degrades, never throws.
- Code `rota/application/analytics_read.py:171-173`: `ValueError` if `month.day != 1`.
- Same `day == 1` raise: `current_decision_required` `memory_read.py:144-145`, `month_plan_readiness` `bootstrap.py:322-323`. Spec does not mention it. `open_month` (`open_month.py:45`) does not check the day; version lookup uses the `date` as stored.

### B4. `CoordinatorActionKind` count

- Spec Historia (`T021_spec.md` ~556–565): “17” values, then lists 18 names.
- Code `rota/site_memory_types.py:71-93`: those 18 members, no more.

### B5. STATUS still asks for a completeness function the audit retracted

- Spec STATUS (`T021_spec.md` ~131–132): work item (2) “site-configuration-completeness backend function — NEW”.
- Spec Workspace (`T021_spec.md` ~294–310): retracted; use `coordinator_context_completeness` / `month_plan_readiness`.

### B6. Panel matrix treats `can_work_24h` like a dated HARD checkbox

- Spec Panel Obsada (`T021_spec.md` ~425–430): columns include `24h (can_work_24h)`; “Unchecking = od–do date range = HARD, auto-reverts after do”.
- Code: `can_work_24h` is `SiteMembership` (`rota/domain.py:178-182`), written by `update_membership` (`durable_inputs.py:224-238`). Boolean, no od–do. `SHIFT-24-01` reads that flag (`eligibility.py:172-173`).
- `employee_availability_matrix` (`availability_matrix.py:53-71`) does not return membership or `can_work_24h`.

### B7. COMPLETENESS correction vs what `employee_availability_matrix` actually returns

Known finding #5 is that this function exists. The spec’s correction (`T021_spec.md` ~32–45) then states D/N/weekday are `EMPLOYEE_ALLOWED_SHIFT_KINDS` / `EMPLOYEE_ALLOWED_WEEKDAYS` / `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` / `EMPLOYEE_DAY_ONLY_N_EXCEPTION`.

Code `availability_matrix.py:30-33, 58-68`:

- availability kinds loaded: `SICK_LEAVE`, `LEAVE_GRANTED`, `UNAVAILABLE_24H` only — not `DAY_SHIFT_OFF`, not `LEAVE_PLAN` (both are on the spec’s “Zgłoś nieobecność” picker, `T021_spec.md` ~444–448, and exist on `AvailabilityKind` `domain.py:27-41`).
- rule kinds loaded: `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` and `EMPLOYEE_DAY_ONLY_N_EXCEPTION` only — not the two `ALLOWED_*` kinds.

Using this read-model as the EmployeeDetail source does not populate the screen the spec describes.

### B8. Decyzje: not every blocker is ready-made Polish

- Spec Decyzje (`T021_spec.md` ~468–472): reasons from `_BUILT_IN_CONDITION_TEXT`.
- Code `decision_guidance.py:23-33, 64-65`: `DAY_SHIFT_OFF-01` is not in that dict; `_render_condition` returns the raw code `"DAY_SHIFT_OFF-01"`.
- Spec’s option→screen list (`T021_spec.md` ~479–485) also omits the real extra options from `build_unblocking_options` (`decision_guidance.py:104-135`): `"Skonfiguruj Wsparcie zewnętrzne: …"` and `"Brak automatycznego rozwiązania…"`.

### B9. NAV line vs later “DONE”

- Spec NAV (`T021_spec.md` ~274–275): Planowanie “mockup exists but is FAIL vs. code, needs revision”.
- Spec later (`T021_spec.md` ~160–177): Planowanie — DONE.

---

## C. DEPENDENCY / SEQUENCING

Links claimed in the spec, checked against functions on `e05dfb7`. Same-ID / same-scope only. No invented glue.

### C1. Identity switcher → site list

- Claimed: selected coordinator → `active_sites_for_coordinator` → every screen’s site scope (`T021_spec.md` ~105–110).
- Functions exist: `active_coordinators` `bootstrap.py:362`, `all_coordinators` `:367`, `active_sites_for_coordinator` `:373`.
- Does not hold if Workspace is implemented as written (`list_sites`, no `coordinator_id`). See B2.
- `active_sites_for_coordinator` does not filter a deactivated coordinator; the switcher must compose `active_coordinators` first.

### C2. Przegląd “Ostatnia akcja” → Planowanie miesiąca

- Claimed: current WORKING `ScheduleVersion` for `(site_id, month)` opens Planowanie on that draft (`T021_spec.md` ~355–364).
- Application read that actually returns the header: `open_month` → `OpenMonthView.current_version` (`open_month.py:45-58`). Spec names persistence `get_current_version_id` + `get_schedule_version_header` instead.
- `get_current_version_id` is the current pointer, any status. WORKING filter is UI-side on `ScheduleVersion.status`.
- Same `(site_id, month)` is what `plan_month` / `select_candidate` / `replan` take. No extra glue. Holds if the tile passes that pair and ignores FINAL.

### C3. Przegląd decyzje tile / Workspace “Wymaga decyzji” / Decyzje sidebar

- Claimed: `site_memory.current_decision_required_months_for_site` for the month list / badge; `memory_read.current_decision_required` per month (`T021_spec.md` ~290–292, ~335–340, ~463–465).
- `current_decision_required` exists (`memory_read.py:143`). Persistence `current_decision_required_months_for_site` (`rota/persistence/site_memory.py:420`) has **no** `rota/application` wrapper.
- Per-month payload is the same object PLAN persists (`plan_ops.py:35-54`). IDs match. The **list of months** is not an application function.

### C4. Decyzje `unblocking_options` → other screens

Options are plain `list[str]` (`engine_types.py:36`, `decision_guidance.py:104-135`). No screen id, no function name. Mapping is string prefix only.

| Spec mapping | Actual string (code) | Backend end | Holds? |
|---|---|---|---|
| Zmień Ogólna/Nocka/24 → Obsada | `Zmień Ogólna dostępność: …` / `Zmień Nocka: …` / `Zmień 24: …` (`decision_guidance.py:37-39`) | `append_availability` `:146`; `record_structured_rule_decision` `rule_decisions.py:41`; `update_membership.can_work_24h` `:224` | Same employee names in the string, not ids. 24 is membership bool (B6), not the dated matrix. |
| Ręczna korekta mimo zapisu → Ręczna korekta | `Ręczna korekta mimo zapisu Chorobowe/Urlop…` / `Ręczna korekta z uwzględnieniem odpoczynku…` (`:40-42`) | `apply_manual_correction` `manual_edit.py:213` + `responds_to_decision_required_id` | Holds if UI passes that id (spec ~486–487). |
| Zmień zapisaną regułę → Panel → Obiekt | `Zmień zapisaną regułę: {description}` (`:128`) | `record_structured_rule_decision` | Function exists. Spec has **no Obiekt function list**; print-code table on Obiekt is `SitePrintSettings`, not SiteRule. |
| Odmroź → Ręczna korekta unfreeze | `Odmroź zapisane przypisania i uruchom planowanie ponownie` (`:45`) | `freeze_or_unfreeze` `manual_edit.py:264` **and** `replan` `plan_ops.py:250` | One string, two operations. Spec maps only unfreeze. |
| Świadomie zaakceptuj przekroczenie → home TBD | `Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy` (`:46`) | no application write | Spec already TBD. Confirmed: no function. |
| *(not in spec)* | `Skonfiguruj Wsparcie zewnętrzne: …` (`:120`) | `add_external_support_window` `durable_inputs.py:103` | Option exists; spec mapping omits it. Placement elsewhere (EmployeeDetail) is confirmed. |
| *(not in spec)* | `Brak automatycznego rozwiązania…` (`:47`) | none | Dead-end string. |

`responds_to_decision_required_id` is on the write functions named above. Link is explicit, not inferred from time order (`plan_ops.py` / `durable_inputs.py` / `manual_edit.py` all call `validate_decision_required_link_no_commit`).

### C5. `target_hours` EmployeeDetail → Analityka

- Claimed: set on per-employee screen, read by Analityka (`T021_spec.md` ~459–460, ~592–598).
- Write: `set_target_hours` `durable_inputs.py:266` — `(employee_id, month)` integer, authorized via `site_id`, stored without site (employee-global).
- Read: `analytics_for_site_month` `analytics_read.py:171` — `hours_scope=ALL_SITES` (`:31-32`, `:218-219`), rows = enabled LOCAL on that site (`:180-182`).
- Same `employee_id` + month (must be day-1). Holds. Numbers are all-sites hours, not hours on the open Site (spec says this).

### C6. Historia action → Decyzje

- Claimed: `material_action_detail.responds_to` is a full `DecisionRequiredReadback` (`T021_spec.md` ~551–555).
- Code `memory_read.py:119-140`: loads snapshot by `responds_to_decision_required_id`, fills `linked_action_ids`.
- Holds when the write passed that id. No automatic join.

### C7. Przegląd “Zaplanuj miesiąc” / “Wygeneruj PDF”

- `plan_month` `plan_ops.py:90` and `generate_schedule_pdf` `schedule_export.py:51` exist.
- PDF also needs `period_label`. First `plan_month` (no current version) needs `effective_from` (`plan_ops.py:113-114`).
- Same `(site_id, month)`. Holds.

### C8. Wydruk ← Obiekt print settings

- Claimed: `SitePrintSettings` already saved on Panel → Obiekt; this screen only passes month + `period_label` (`T021_spec.md` ~604–622).
- Read happens inside `generate_schedule_pdf` (`schedule_export.py:66-68`) via persistence `get_site_print_settings`.
- No `rota/application` get/save for print settings. `update_site` (`durable_inputs.py:390`) writes `Site.display_name` / `active`, not `company_print_name` / `site_print_name` / `base_regime` / intervals / reserve.
- Application-layer write end of this link does not exist.

### C9. Przegląd headcount vs Analityka roster

- Claimed: Przegląd counts enabled LOCAL+EXTERNAL; Analityka LOCAL only (`T021_spec.md` ~347–354, ~576–578).
- Analityka: confirmed `analytics_read.py:180-182`.
- Przegląd: spec cites `list_memberships_for_site` (persistence). Application `current_roster` (`bootstrap.py:353`) is enabled LOCAL+EXTERNAL employees — same membership filter, different return shape (no kind on the tuple).
- Scopes match the claim if Przegląd counts enabled memberships. Not the same function the spec named.

### C10. Backup on Workspace

- Claimed: `backup_database` / `build_diagnostic_zip` are store-global (`T021_spec.md` ~315–323).
- Code `backup.py:17-24`: `conn` only, no `site_id`. Holds.

---

## Already in spec (not new)

REQUEST seven, plus already written in COMPLETENESS and not repeated as A: `update_site`; `mark_training_realized` / `training_s_*`; `update_membership` membership_kind and `readiness_source=COORDINATOR_OVERRIDE`; identity switcher using `active_coordinators`/`all_coordinators`; `precheck` unplaced; `open_month` / `months_with_schedule` unused as the composed-screen source; `set_calendar_day`; SiteProfile toggles except read-only `rolling_7d_decision_threshold_hours`.
