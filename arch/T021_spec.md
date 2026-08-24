# T021 SPEC — condensed, per-screen. Read this, not T021_ui_facts.md.

## DEPLOYMENT PIVOT (2026-08-22): read `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md` (ROTA-T025) first
Deployment moved from local desktop app to hosted PWA (Railway), moved
up from "after testing" to "now" — real password login now required.
This supersedes the "coordinator identity switcher" section further
below (kept for its reasoning trail, not as a live decision). Screen
content/backend-function mapping in the rest of this file is
UNAFFECTED — it never assumed a specific delivery shell.

## SECOND AUDIT PASS (2026-08-22): independent Cursor cross-check
After CC's own completeness audit below, Paweł had Cursor independently
cross-reference every `rota/application/*.py` function against this
file. Raw output verified by CC against source before trusting it (same
discipline as `tasks/CURSOR_AUDIT_2026-08-21/`); full write-up
`tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`. All
confirmed fixes already applied inline below (search "2026-08-22" /
"Cursor audit" for the specific corrections: 5 function signatures
missing `coordinator_id`, a self-contradicting STATUS line, a stale
`list_sites` citation, a wrong 17-vs-18 count, the 24h column's actual
mechanism, a narrowed availability-matrix claim, a second untranslated
backend code, 2 missing application-layer wrappers, and 2 corrections
to the Decyzje koordynatora option-mapping). One NEW unbuilt item surfaced this pass:
`bootstrap_or_resume_coordinator_context` (no "+ Nowy obiekt" flow
exists anywhere) — needs Paweł's placement call before it's mocked up.
The absence log's read source, initially left open, is now resolved
(`get_current_availability_for_employee`) — no mockup change needed,
EmployeeDetail's absence log UI was already correct.

## COMPLETENESS AUDIT (2026-08-22, post mockup-pass) — read before pipelining
Paweł asked directly whether all program logic is represented and
screen dependencies are correct. Ran `grep -n "^def [a-z]" rota/application/*.py`
against every screen in this spec — first time this was done exhaustively
rather than function-by-function as each screen was built. Findings:

**Retracted error**: see the "Konfiguracja niepełna" entry under
Workspace/Przedpokój below — `coordinator_context_completeness` already
existed; I wrongly said it didn't.

**Real gaps, never represented on any screen — need Paweł's call on
priority/placement, not silently built**:
- `durable_inputs.set_calendar_day` — holiday/calendar config. Flagged
  by the ORIGINAL Codex audit (§7 in facts doc) and never resolved.
- `durable_inputs.update_site_profile` — SiteProfile-level toggles
  never shown anywhere: `day_only_blocks_n`, `external_support_enabled`,
  `training_s_enabled`, `training_s_weekdays_only`,
  `training_s_default_readiness_threshold`,
  `rolling_7d_decision_threshold_hours` (this last one IS shown, read-only,
  on Obiekt tab — the rest are not, and none are editable in the mockup).
- `durable_inputs.update_site` — Site display_name/active editing, not
  represented.
- Coordinator account management — `bootstrap.active_coordinators`/
  `all_coordinators`, `durable_inputs.update_coordinator`/
  `update_association` — ZERO screen anywhere touches coordinator
  accounts or their site associations. Entirely outside current scope.
- `training.mark_training_realized` / SiteProfile training_s_* toggles
  — see mechanism correction below.

**Mechanism correction (EmployeeDetail screen)**: didn't check
`rota/application/availability_matrix.py` (`employee_availability_matrix`)
before designing the per-employee matrix — the purpose-built T010-B
read-model for exactly this screen. Correction: only "Ogólna
dostępność" and the absence log are `AvailabilityRecord`-based
(durable_inputs.append_availability) — CORRECT as built. The
Nocka/weekday-forbidden columns and the day_only temp-N-exception go
through `SiteRuleVersion` decisions, the SAME decision-ledger mechanism
as Historia i audyt's "Historia reguł obiektu" — a per-employee matrix
edit should be traceable in that same rule-history view, which the
mockup doesn't currently imply. Not re-mocked yet.

**NARROWED 2026-08-22 (Cursor audit V-B7)**: the above overclaimed which
kinds `employee_availability_matrix` actually covers.
`_RELEVANT_AVAILABILITY_KINDS = (SICK_LEAVE, LEAVE_GRANTED,
UNAVAILABLE_24H)` only — excludes `DAY_SHIFT_OFF`/`LEAVE_PLAN`.
`_RELEVANT_RULE_KINDS = (EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
EMPLOYEE_DAY_ONLY_N_EXCEPTION)` only — excludes
`EMPLOYEE_ALLOWED_SHIFT_KINDS`/`EMPLOYEE_ALLOWED_WEEKDAYS` even though
both are real rule kinds. Consequence: this function alone cannot power
the EmployeeDetail absence log (which needs all 5 `AvailabilityKind`
values, since `append_availability` writes any of them).

**RESOLVED (2026-08-22)**: correct source is
`rota/persistence/availability_repository.py::get_current_availability_for_employee(conn, employee_id) -> list[AvailabilityRecord]`
— unfiltered by kind (returns every `availability_id` family's current
chain-end, active or not), the exact same call `availability_matrix.py`
itself makes internally before narrowing it down. No mockup change
needed — EmployeeDetail's absence log UI was already correct; only the
backend citation was missing. Persistence-layer, no confirmed
application wrapper (same missing-wrapper pattern as V-C1/V-C2) — flag
for implementation.

**"S/szkolenie" oversimplified**: not a settable toggle — it's DERIVED
from real TRAINEE `Assignment` history via `training.mark_training_realized`
(gated by the SiteProfile training_s_* toggles above), but
`durable_inputs.update_membership` ALSO accepts a direct
`readiness_source=COORDINATOR_OVERRIDE` write — so a manual override
path exists and isn't surfaced as an editable control on EmployeeDetail
(shown as a read-only badge only).

**Membership_kind (LOCAL↔EXTERNAL_SUPPORT) not editable anywhere**:
`update_membership` allows changing it; the mockup treats it as fixed
at "+ Dodaj osobę" time.

**Data-source questions, not yet resolved**:
- **RESOLVED (2026-08-22)**: `Main.dc.html`'s site list — confirmed:
  use `bootstrap.active_sites_for_coordinator(coordinator_id)`, scoped
  to whichever coordinator identity is currently selected, NOT
  `list_sites` (all sites in the DB). See new "Coordinator identity
  switcher" cross-cutting requirement below for how that identity gets
  chosen.
- "Historia wersji"/`restore` on Planowanie miesiąca: never grounded
  against `open_month.months_with_schedule`/`list_schedule_versions` —
  plausible source, not confirmed.
- Month picker on Przegląd/Panel sterowania: hardcoded "Sierpień 2026"
  in the mockup — `open_month.months_with_schedule` likely the real
  source for which months are navigable, not checked.

## CROSS-CUTTING REQUIREMENT (2026-08-22): coordinator identity switcher — SUPERSEDED
**SUPERSEDED same day by `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`
(ROTA-T025)**: the deployment model this section assumed (local desktop
app) and its no-password conclusion are both reversed — Paweł moved the
planned PWA (Railway-hosted) up from "after testing" to "now," driven
by a mobile-access requirement (coordinator away from the office needs
to make urgent plan changes from their phone). Real password-based
login is now required. Read T025's finding doc, not the reasoning
below, for the current direction. Section kept for its historical
reasoning trail, not as a live decision.
Surfaced answering Paweł's "did we miss anything" question, then
resolved over several turns. Real-world constraint: each coordinator
has their own computer; they substitute for each other during absences.
Decisions made, in order:
1. **Deployment stays local desktop app** (Continuity AI Tauri reuse,
   `arch/spec.md` §"REUSE/ADAPT: Continuity AI desktop shell"), one
   local SQLite file per install (`rota/application/store.py` —
   "local SQLite store", no network concept anywhere in the backend
   today). NOT changing this now.
2. **No password/login subsystem exists or is being added now** —
   `rota/application/context.py`'s own docstring: "basic active-triple
   check, not a new authorization subsystem." Confirmed as the standing
   principle, not contradicted by what follows.
3. **DECIDED: build a coordinator IDENTITY SWITCHER now** — a
   name-picker (no password) that sets which `Coordinator` is currently
   acting, using data that already fully exists
   (`Coordinator`/`CoordinatorSiteAssociation`,
   `bootstrap.active_coordinators`/`all_coordinators`). Explicitly
   future-ready: doesn't require solving cross-computer data sharing to
   be worth building now, and today (single computer, no network) a
   given local database will typically only ever contain the
   coordinators actually entered on that machine.
4. **EXPLICITLY DEFERRED, separate question, NOT decided**: how data
   actually gets shared between coordinators' separate computers so
   that switching identity reveals another coordinator's real site
   data (network file share / small local office server / manual
   backup-restore substitution — see chat, three options sketched, none
   chosen). Paweł: "nie tworzymy punktu dostępowego do sieci" right
   now. This blocks the identity switcher from being USEFUL for actual
   substitution today, but not from being BUILT.

**UI implication, not yet applied to the mockup**: every screen's
header currently shows a static "PP / Paweł P." avatar block — this
needs to become the coordinator switcher (click → list from
`active_coordinators`/`all_coordinators` → select → `Main.dc.html`'s
site list and every screen's data scope follows the selected
identity). Cross-cutting across all 9 artboards, not yet built —
flag before the next mockup pass, don't build silently mid-answer.

**Lower-priority, noted only**: `precheck.precheck(state)` — a fast
pre-solve heuristic ("likely insufficient coverage") distinct from the
Ręczna korekta dry-run function (confirmed NOT overlapping, that finding
still stands) — could preface "Zaplanuj miesiąc" with an early warning,
never placed anywhere. `open_month.open_month` is a single richer
read-model several composed-from-smaller-calls screens could have used
instead (Przegląd, Panel sterowania) — not wrong as built, just not the
most-authoritative source in every case.


Rationale/evidence/audit trail lives in `T021_ui_facts_2026-08-21.md` —
only open that file when a decision below needs justifying. This file is
the thing to code from. Format: bullets, code refs, no prose. Nav layout
is FROZEN as the existing flat 8 items — no IA redesign without new
instruction.

STATUS (2026-08-22): all 8 nav screens + Przegląd + the workspace/
Przedpokój screen fully settled, zero open DECISIONS remaining in this
file. Remaining WORK items before this feeds a real implementation
contract (not decisions — actual build items): (1) dry-run preview
backend function (Ręczna korekta section); (2) anglicism sweep
(cross-cutting rule below) — applied screen-by-screen as built, one
backend-owned raw-code gap (`DAY_SHIFT_OFF-01`) found on Cursor's
2026-08-22 pass, see below; (3) two missing application-layer wrappers
found on the same pass (V-C1/V-C2 in
`tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`).
Site-configuration-completeness does NOT need a new function — retracted
same day, see COMPLETENESS AUDIT above. Separately, ROTA-T023 (absence-hours accounting) is
priority-ordered BEFORE T021 per Paweł — see
`arch/FINDING_2026-08-22_ABSENCE_HOURS_ACCOUNTING.md`, unrelated to
this file's content. All screens in the flat nav + workspace level have
now had a first pass — no more unreviewed screens remain.

MOCKUP REVISION PROGRESS (screen by screen, per Paweł's explicit
pacing choice 2026-08-22): **Panel sterowania — DONE.**
`ControlPanel.dc.html` updated: 24h matrix column added (all example
rows corrected to match the real 11-column header — the original mockup
rows were short by 1 cell even before this pass), employee names are
now click-affordanced into a new `EmployeeDetail.dc.html` artboard
(§8.3 per-employee screen: matrix row, ONLY D toggle, S/szkolenie
status, target_hours, absence log, dimmed "wsparcie zewnętrzne" preview
section), one EXTERNAL_SUPPORT example row added to the matrix, Obiekt
tab now has the real D1-D5/N1-N5 print-code table (kept separate from
the existing, correct Katalog zmian/StandardShift table — these are two
genuinely different mechanisms, do not merge them) and all 6
U3-C5 reserve-hour values, `site_print_name` added alongside
`company_print_name`. Anglicism sweep NOT yet done on this screen
(check on a later pass).

**Planowanie miesiąca — DONE.** `Planning.dc.html` updated: dropped
invented candidate names/deviation counts, plain "Wariant 1"/"Wariant 2"
+ a note that the count is 1-3, not fixed; "FEASIBLE" → "Wykonalny",
"REPLAN" → "Przeplanuj", "Uruchom PLAN" → "Zaplanuj miesiąc" (matches
Przegląd's quick-action name); added a "Historia wersji" control
(`restore`, confirmed placement here); finalize button/footer now notes
the exact-acknowledgment requirement instead of implying a single click
closes the month.

**Correction same day**: the schedule grid used simplified D/N/24
letters and 10 numbered day columns — did NOT match the real, accepted
target layout (`Grafiki/7442.jpg`, the actual APEXIM/ROYALPACK paper
document T020 was built from). Paweł caught this; confirmed decision:
the working grid must use the SAME visual language as the real document
— D1-D5/N1-N5/U1-U5/C1-C5 codes (matching Panel sterowania → Obiekt's
print-code table), PLAN+WYK per day (stacked two-line cell, not a
doubled column count), full month via horizontal scroll, and per-
employee totals split into Godz. plan / Godz. wyk / Urlopy / Chorobowe
(was a single generic "Godz." column). Rebuilt accordingly.

**Decyzje koordynatora — DONE (new artboard `Decisions.dc.html`).**
Blocking demands table, blockers table (ready-made Polish reason text),
load-blocker table, unblocking-options list styled as links to other
screens (matches §9.1's option→screen mapping) — the "Świadomie
zaakceptuj przekroczenie..." option shown dimmed/"miejsce nieustalone"
since its screen-home is still genuinely undecided, not guessed. Month
list in sidebar (2 pending months, matches nav badge).

**Ręczna korekta — DONE (new artboard `ManualEdit.dc.html`).**
Illustrates the new zmiana→pytanie(ostrzeżenie)→zapisz/odrzuć flow as
two stacked steps: Krok 1 (change fields: who's reassigned, note) →
Krok 2 (dry-run result: warning box naming the specific violation,
"Zapisz mimo to"/"Odrzuć zmianę", note that acceptance auto-records the
exception and never triggers an automatic REPLAN). Freeze/unfreeze and
mark-not-worked (NN) shown as smaller dimmed "dla poglądu" examples
below — same mechanism, not built out as full interactions to keep
scope reasonable.

**Historia i audyt — DONE (new artboard `History.dc.html`).** Two
sections matching the two backend streams: "Działania koordynatora"
(filterable table, Polish labels for the action-kind pills, one example
row links back to a Decyzje koordynatora entry via "→ Decyzja: Sierpień
2026") and "Historia reguł obiektu" (one example rule's version chain,
v1→v2 with a "zastępuje" relation badge, who/when/why per version).

**Analityka i bilanse — DONE (new artboard `Analytics.dc.html`).**
Table per LOCAL employee: target/effective target/planned/realized
hours, month + quarter balance, status pill (dostępne/kwartał
niedostępny/niedostępne matching AVAILABLE/MONTH_AVAILABLE_QUARTER_
UNAVAILABLE/UNAVAILABLE). Two degraded examples with real warning text
below the table (incomplete calendar, missing target_hours — links back
to where target_hours actually gets set, the per-employee screen). Note
up top that this table deliberately excludes wsparcie zewnętrzne,
unlike Przegląd's headcount tile.

**Wydruk Grafiku — DONE (new artboard `Export.dc.html`).** Form
(month + period_label) → precondition check → ready state (download
button + version/provenance) → 4 representative problem-code examples
with specific Polish messages, dimmed "dla poglądu" with a note that
~17 total exist and none collapse to a generic error.

**Workspace/Przedpokój — DONE (`Main.dc.html` revised, already
existed).** Filter row honest about its limit ("Konfiguracja niepełna"
today only detects missing print settings, not every gap — matches the
NEW BACKEND REQUIREMENT note above); the incomplete-config example card
now says "Brak ustawień wydruku" (the one confirmed signal) instead of
an invented "Brak katalogu zmian"; added a backup/diagnostyka card at
page bottom, explicitly labeled as covering the whole database, not one
site.

**MOCKUP REVISION PASS COMPLETE (2026-08-22)**: all 9 screens (8 nav +
workspace) now reflect this spec. 3 things remain genuinely outside the
mockup's reach: the two new backend functions (dry-run preview,
site-config-completeness) and the backend-owned "checkbox" anglicism in
`decision_guidance.py`. Anglicism sweep was applied as each screen was
(re)built, not as a separate final pass — worth a last skim before
handing this to implementation.

## CROSS-CUTTING RULE (2026-08-22): no anglicisms in UI-facing text
Paweł: all English loanwords in the program must be Polish. Applies to
every user-visible string — labels, buttons, statuses, warnings. Does
NOT apply to internal code identifiers (enum names, field names) — only
to what the coordinator sees.
- Known internal English codes needing a Polish rendering, never shown
  raw: `PlanningResult.status` (`FEASIBLE`/`DECISION_REQUIRED`/
  `TECHNICAL_ERROR`), `AssignmentState` (`PLANNED`/`REALIZED`/
  `CANCELLED`), `AvailabilityKind`, `MembershipKind`
  (`LOCAL`/`EXTERNAL_SUPPORT`), `ReadinessState`
  (`NOT_READY`/`READY_FOR_PRIMARY`), all 18 `CoordinatorActionKind`
  values, `rel` (`supersedes`/`corrects`/`rejects`), operation names
  PLAN/REPLAN (`plan_ops.plan_month`/replan — buttons need Polish verbs,
  e.g. not literally "PLAN"/"REPLAN").
- **Found existing violation, not yet fixed**: the mockup already used
  raw "FEASIBLE" status and "Uruchom PLAN"/"REPLAN" as literal button
  labels (§7 in facts doc) — needs correcting in the next mockup
  revision pass.
- **Backend-side finding, flagged not fixed**: `decision_guidance.py`'s
  own "ready-made Polish" blocker text (§Decyzje koordynatora above)
  literally contains the English word "checkbox" — e.g. "Koliduje z
  checkbox: Ogólna dostępność". This text is generated server-side, not
  owned by T021's UI layer — flagging for Paweł, not silently
  reproducing it if he wants it fixed at the source instead.
- **Second backend-side finding, found 2026-08-22 (Cursor audit
  V-B8)**: the SAME file's `_render_condition` returns the raw code
  `"DAY_SHIFT_OFF-01"` UNTRANSLATED for that one specific blocker
  (checked before `_BUILT_IN_CONDITION_TEXT`, which has no entry for it
  either) — a coordinator hitting this blocker sees the bare code, not
  Polish text. Same backend-ownership caveat as "checkbox" above.
- **FIXED (2026-08-22)**: nav item "Eksport PDF" renamed to
  **"Wydruk Grafiku"** everywhere (Paweł: the old name was unclear —
  "tajemniczy i nie wiadomo co znaczy"). Applied across all 7 mockup
  screens that carry the sidebar nav (`ControlPanel`/`Planning`/
  `Decisions`/`ManualEdit`/`History`/`Analytics`/`Room`) plus this spec
  file. `EmployeeDetail.dc.html` and `Main.dc.html` have no sidebar nav,
  unaffected. Backend function name (`generate_schedule_pdf`) stays
  English — the rule is about UI-facing text only.

## NAV (frozen, flat)
1. Przegląd — spec below
2. Panel sterowania — Obiekt + Obsada tabs, see below
3. Planowanie miesiąca — spec below (mockup exists but is FAIL vs. code,
   needs revision)
4. Decyzje koordynatora — spec below
5. Ręczna korekta — spec below
6. Historia i audyt — spec below
7. Analityka i bilanse — spec below
8. Wydruk Grafiku — spec below

## Workspace / Przedpokój (Main.dc.html, outside any Site)
Top-level screen before entering a Site's room. Source:
**`bootstrap.active_sites_for_coordinator(conn, coordinator_id) ->
tuple[Site, ...]`** — CORRECTED (2026-08-22, Cursor audit V-B2): earlier
text here cited `site_repository.list_sites` (ALL sites in the DB);
confirmed decision is coordinator-scoped, matching "Twoje obiekty" and
the coordinator identity switcher below. `list_sites`/
`bootstrap.all_sites_for_coordinator` remain available if an
unscoped "every site" admin view is ever wanted — not needed today.
Like Przegląd, **no dedicated backend module** — composed from per-site
reads, one call per site for the filter chips:

- **"Wszystkie"**: `active_sites_for_coordinator` as-is.
- **"Wymaga decyzji"**: sites where
  `site_memory.current_decision_required_months_for_site(site_id)` is
  non-empty — same source as §Decyzje koordynatora, applied per site
  instead of within one.
- **"Konfiguracja niepełna" — RETRACTED "new function needed" claim
  (2026-08-22)**: earlier same-day I wrongly claimed no completeness
  check exists — I had not checked `rota/application/bootstrap.py`.
  It already exists: **`coordinator_context_completeness(conn,
  coordinator_id, site_id) -> ContextCompleteness(complete: bool,
  missing: tuple[str, ...])`** — checks coordinator active/exists, site
  active/exists, site profile active + has ≥1 valid standard shift,
  an active CoordinatorSiteAssociation, and ≥1 active LOCAL
  SiteMembership with a real Employee — each a specific, named string,
  exactly what Paweł required ("nie może się domyślać"). Extended
  per-month by **`month_plan_readiness(conn, coordinator_id, site_id,
  month) -> MonthPlanReadiness(ready, missing, target_hours_warnings)`**
  — adds missing `CalendarDay` entries for the month + non-blocking
  target_hours warnings. **No new backend function needed here** — use
  this. `get_site_print_settings(site_id) == None` (Wydruk Grafiku's
  `PRINT_SETTINGS_MISSING`) is a separate, additional signal not
  covered by `coordinator_context_completeness` — combine both.
- Search box: filters `active_sites_for_coordinator` by
  `display_name`/`site_id` — no
  search-specific backend function, plain client-side or SQL LIKE
  filter over the same list.

**Backup / diagnostyka — placement question from the original Codex
audit (§7A "WYMAGA_DECYZJI"), belongs here if anywhere**:
`backup.backup_database()`/`build_diagnostic_zip()` operate on the
WHOLE SQLite connection (confirmed earlier this session:
`backup_to` uses `conn.backup(dest_conn)`, `diagnostics_payload` counts
rows across every table via `sqlite_master`) — not scoped to one site.
That makes this workspace screen the only structurally correct home for
it, not any per-site screen. **CONFIRMED (2026-08-22): backup lives on
this workspace screen.**

**"+ Nowy obiekt" flow — MISSING, found via Cursor audit V-A1
(2026-08-22)**: `bootstrap.bootstrap_or_resume_coordinator_context` is
the actual function that creates a brand-new Coordinator/SiteProfile/
Site/Association (onboarding a Site for the first time) — never
mentioned anywhere in this spec, no screen represents it. `Main.dc.html`
only ever lists existing sites. **DECIDED + BUILT (2026-08-22)**: button on this workspace screen,
opens an inline form in place (not a separate screen) —
`Main.dc.html` updated. Form is deliberately minimal: Nazwa
obiektu/Nazwa profilu zmianowego/Próg decyzyjny 7-dniowy →
"Utwórz obiekt" → creates just enough (Site + SiteProfile +
CoordinatorSiteAssociation to the current identity) for the new site to
appear under "Konfiguracja niepełna", then the coordinator fills in the
rest (shift catalog, roster, print settings) incrementally in Panel
sterowania — matches `bootstrap_or_resume_coordinator_context`'s own
documented design ("resume a partial context over several calls").

## Przegląd
Per-site landing screen, first item inside a Site's room (NOT the
workspace-level Site grid — that's `Main.dc.html`, outside any Site,
listing ~20-some Sites, a separate concern with no function list yet).

**No dedicated backend module exists for this screen** — unlike every
other screen so far (Decyzje/Historia/Analityka/Eksport each had one
clean entry point built explicitly for T021), Przegląd is a composition
of reads already covered under OTHER screens' sections above. Every
tile's real source:
- **Liczba oczekujących decyzji** (badge/tile) + **lista oczekujących
  decyzji** (the mockup's 2 example rows with "Rozwiąż" link) —
  `site_memory.current_decision_required_months_for_site` (count) +
  `memory_read.current_decision_required` per month (list content).
  Identical source to §Decyzje koordynatora — this tile is a preview
  of that screen, "Rozwiąż" navigates there.
- **Wersja grafiku** (status tile: roboczy/z odchyleniami/finalny) —
  `schedule_repository.get_current_version_id` +
  `get_schedule_version_header(...).status` (`ScheduleStatus`:
  `WORKING`/`WORKING_WITH_DEVIATIONS`/`FINAL_NO_DEVIATIONS`/
  `FINAL_WITH_DEVIATIONS` — anglicism rule applies, Polish rendering
  needed).
- **Liczba osób w obsadzie** — `employee_repository.list_memberships_for_site`,
  count enabled rows. **DECIDED (2026-08-22): LOCAL + EXTERNAL_SUPPORT**
  (if support is in use that month) — this tile shows actual current
  crew size, not the Analityka-style LOCAL-only roster. Deliberately
  DIFFERENT scope from §Analityka i bilanse's headcount (which excludes
  EXTERNAL_SUPPORT) — not an inconsistency, the two tiles answer
  different questions ("who's actually working this month" vs. "whose
  hours are we tracking against a target").
- **Ostatnia akcja — CHANGED (2026-08-22)**: not a log-entry text line —
  it's a "wróć do pracy" pointer straight into the grafik currently
  being worked on. Source: current WORKING `ScheduleVersion` for this
  (site_id, month) — same `get_current_version_id` +
  `get_schedule_version_header` call as the version-status tile above,
  reused here as a clickable resume link into §Planowanie miesiąca
  (opens that screen on the in-progress draft, not a fresh blank
  state). Resolves the earlier open question about whether the full
  day-by-day grid belongs on Przegląd too — it doesn't; this tile is
  the shortcut back into it instead of duplicating it inline.
  `memory_read.material_action_history` (the actual action-log stream)
  is NOT used for this tile — it stays purely §Historia i audyt's.
- **Szybkie akcje**: "Zaplanuj miesiąc" → `plan_ops.plan_month`
  (§Planowanie miesiąca below); "Wygeneruj PDF" →
  `schedule_export.generate_schedule_pdf` (§Wydruk Grafiku); "Otwórz panel
  sterowania" → plain navigation, no backend call.

## Planowanie miesiąca
Source: `rota/application/plan_ops.py` (PLAN/select/REPLAN) +
`rota/application/lifecycle_ops.py` (revalidate/finalize/restore).

**`plan_month(site_id, month, coordinator_id, effective_from=None)`**
→ `PlanningResult` (`coordinator_id` REQUIRED — corrected 2026-08-22,
Cursor audit V-B3, dropped from every signature below too):
- `status`: `FEASIBLE` | `DECISION_REQUIRED` | `TECHNICAL_ERROR` (needs
  Polish rendering per the anglicism rule above).
- `candidates: list[list[Assignment]]` — **CONFIRMED BY CODEX (round_01,
  B1): 1 to 3 candidates, never a fixed count.** No candidate
  name/strategy field and no per-candidate deviation-count field exist
  anywhere in the backend — `PlanningResult` has exactly the 5 fields
  listed here, nothing else.
  - **DECIDED (2026-08-22)**: mockup's invented names/deviation counts
    are dropped. Render however many candidates come back (1-3) as
    plain numbered options ("Wariant 1"/"Wariant 2"/"Wariant 3"), no
    names, no per-candidate deviation summary. No new backend function
    needed for this.
  - Coordinator picks one candidate and calls `select_candidate(...,
    candidate=<the chosen list[Assignment]>)` — passed back WHOLESALE,
    not by index/id.
  - When `status=DECISION_REQUIRED`: `decision_payload` is exactly
    §Decyzje koordynatora's `DecisionRequiredPayload` — same data,
    shown inline here too (or linked there).
- `warnings: list[str]`, `error_message: Optional[str]` (only set on
  TECHNICAL_ERROR).

**`select_candidate(site_id, month, candidate, coordinator_id, note=, responds_to_decision_required_id=)`**
→ persists the chosen candidate as the current `ScheduleVersion`.
`coordinator_id` is not just required but load-bearing: omitting an
explicit actor raises `MissingCoordinatorActor` (ROTA-T019b removed the
old fallback to the version's own `created_by`) — UI must always know
who is currently acting before this call, not defer it.

**`replan(site_id, month, coordinator_id, effective_from, note=, responds_to_decision_required_id=)`**
→ `PlanningResult`, same shape as plan_month. Always clones current
version into a new WORKING child first; never auto-saves the returned
candidate — same select_candidate step after.

**`finalize(site_id, month, coordinator_id, acknowledged_deviation_ids, acknowledged_at=, reason=, responds_to_decision_required_id=)`** →
locks the month. MUST re-derive the fresh Deviation set first and the
caller's `acknowledged_deviation_ids` must match it EXACTLY (not a
subset) or it's rejected — UI must show the current deviations and
require explicit acknowledgment of all of them, not a silent "finalize"
button. Produces status `FINAL_WITH_DEVIATIONS` or `FINAL_NO_DEVIATIONS`.
A FINAL version can't be revalidated/REPLAN'd in place — editing it
starts a fresh child via manual correction or REPLAN.

**`restore(site_id, month, coordinator_id, version_id, note=, responds_to_decision_required_id=)`**
— moves only the current pointer back to an earlier `ScheduleVersion`;
never deletes history (`note`/`responds_to_decision_required_id` were
missing from this entry too, corrected 2026-08-22). **DECIDED
(2026-08-22): lives on Planowanie miesiąca**, not Historia i audyt.

**`revalidate(site_id, month)`** — re-derives Deviations in place on
the current WORKING version without creating a new version (used to
refresh after e.g. an availability change elsewhere invalidated the
current draft). Cannot run on a FINAL version.

## Panel sterowania → Obsada (roster matrix)
- One row per `SiteMembership` (LOCAL or EXTERNAL_SUPPORT kind).
- Matrix columns: Ogólna dostępność, Dniówka (D), Nocka (N), 24h
  (`can_work_24h`), 7× weekday. Default: all checked.
- ✓ = solver may use; ☐ = may not.
  - Ogólna dostępność / Dniówka / Nocka / weekday: unchecking = od–do
    date range = HARD constraint, auto-reverts after "do", no separate
    restore action.
  - **24h is DIFFERENT — corrected 2026-08-22 (Cursor audit V-B6)**:
    `SiteMembership.can_work_24h` is a plain persistent `bool`
    (`update_membership`), no date range, no auto-revert — toggling it
    off stays off until explicitly toggled back on. Do not build a
    date-range picker for this column.
- `day_only` = per-employee flag next to name, not a matrix column.
  Temp Nocka exception frozen separately
  (`FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`).
- S/szkolenie (`ReadinessState`) — NOT a matrix column, lives on
  per-employee screen (below).
- U/C (T020 export symbols) — NEVER matrix columns, unrelated mechanism
  ([[project_t020_legend_symbol_mechanism]] equivalent note in facts
  doc).
- EXTERNAL_SUPPORT row: added via same "+ Dodaj osobę" as LOCAL, same
  matrix. ADDITIONALLY requires ≥1 active `ExternalSupportWindow`
  (date range + optional D/N restriction) or blocked regardless of
  checkboxes (`EXTERNAL-01`, fail-closed — opposite default of LOCAL).
  Window list lives on per-employee screen (below), not in the matrix.
- "Zgłoś nieobecność" action (separate from matrix): reason picker over
  `AvailabilityKind` (`DAY_SHIFT_OFF`/`UNAVAILABLE_24H`/`LEAVE_PLAN`/
  `LEAVE_GRANTED`/`SICK_LEAVE`) + date range.
  `UNAVAILABLE_24H`/`LEAVE_GRANTED`/`SICK_LEAVE` hard-block;
  `DAY_SHIFT_OFF` blocks only that day; `LEAVE_PLAN` is soft-only.
  Backend: `durable_inputs.append_availability`.

## Panel sterowania → Obsada → per-employee ("Nazwisko Imię") screen
One screen per roster row, contains together:
- eligibility matrix for that one employee (same columns as above)
- `day_only` flag
- S/szkolenie status (`ReadinessState`)
- absence log: list of `AvailabilityKind` entries (date range + reason)
- IF `membership_kind == EXTERNAL_SUPPORT`: support-window list
  (`ExternalSupportWindow` entries — date range + optional D/N)
- target_hours per month (`durable_inputs.set_target_hours`) — closes
  §7A gap, read by Analityka i bilanse, set here

## Decyzje koordynatora
- List source: months with active decision for this site
  (`site_memory.current_decision_required_months_for_site`) → nav badge
  count.
- Per month (`memory_read.current_decision_required`):
  - blocking demands (id + time range)
  - blockers: (employee, reason) — reason text is READY-MADE Polish from
    `decision_guidance.py._BUILT_IN_CONDITION_TEXT` (e.g. "Koliduje z
    checkbox: Ogólna dostępność", "Koliduje z zapisem: Urlop", "Koliduje
    z odpoczynkiem dobowym", "Koliduje z tygodniowym czasem pracy",
    "Wsparcie zewnętrzne", or a site rule's own description)
  - load_blocker (optional): employee + week + hours over
  - unblocking_options: ready-made Polish suggestion strings
    (`decision_guidance.build_unblocking_options`) — each one links to
    ANOTHER screen/action (see mapping below), never an inline control
    here
  - requested_by / recorded_at / linked_action_ids
- Option→screen mapping — **CAVEAT added 2026-08-22 (Cursor audit
  V-C3)**: `unblocking_options` are bare Polish strings, no structured
  action/screen id anywhere in the backend. This mapping is UI-side
  prefix matching on that text, not an ID-based link — fragile if the
  backend wording ever changes, flag this to whoever implements it:
  - "Zmień Ogólna dostępność/Nocka/24" → Obsada matrix
  - "Ręczna korekta mimo zapisu..." → Ręczna korekta
  - "Zmień zapisaną regułę" → Panel sterowania → Obiekt
  - "Odmroź zapisane przypisania i uruchom planowanie ponownie" →
    **TWO steps, corrected 2026-08-22 (Cursor audit V-C4)**: Ręczna
    korekta (unfreeze) THEN Planowanie miesiąca (replan) — the option
    text itself says "i uruchom planowanie ponownie", not unfreeze
    alone.
  - "Skonfiguruj Wsparcie zewnętrzne: ⟨names⟩" — **ADDED 2026-08-22
    (Cursor audit V-C5), was missing from this mapping entirely** →
    Obsada → per-employee screen → support-window list (§9.2).
  - "Świadomie zaakceptuj przekroczenie..." → home TBD, candidate:
    inline on Planowanie miesiąca
- Every response action MUST pass `responds_to_decision_required_id`
  back to link the action to this decision.
- **Two missing application-layer wrappers, found 2026-08-22 (Cursor
  audit V-C1/V-C2)**: `current_decision_required_months_for_site` lives
  in `rota/persistence/site_memory.py` with no `memory_read.py` wrapper
  (unlike its sibling functions there); `get_site_print_settings`/
  `save_site_print_settings` (persistence layer, confirmed both exist
  in `site_repository.py`) have no `durable_inputs.py`-equivalent
  application wrapper for the save side either. Not a UI decision —
  flagging for whoever implements the application layer.

## Ręczna korekta
Three backend entry points (`rota/application/manual_edit.py`), all
site+month+coordinator+effective_from scoped, act on current
`ScheduleVersion`, all optionally take `responds_to_decision_required_id`:
1. `apply_manual_correction(upsert_assignments)` — generic add/edit/
   cancel PRIMARY or TRAINEE, split coverage (shared `covers_demand_id`),
   coverage-gap repair. Assignment fields coordinator can set:
   employee_id, start/end, role, state, frozen, covers_demand_id,
   mentor_primary_assignment_id (TRAINEE only), note.
2. `freeze_or_unfreeze(assignment_id, frozen)` — single toggle.
3. `mark_not_worked(assignment_id)` — only legal on PLANNED+PRIMARY →
   CANCELLED + operational_code="NN". Leaves coverage gap.

Behavior: HARD violations NEVER block save (become Deviations, shown
after, not a hard stop). REST-01 violation auto-writes a
`CONFIRMED_EXCEPTION`/`INFORMATIONAL` audit record
(`REST_OVERRIDE_RECORD`) by itself. Never auto-REPLAN. Every correction
= new child `ScheduleVersion`, parent untouched.

### NEW BACKEND FUNCTION NEEDED — dry-run preview (not built yet)
Paweł's decision 2026-08-22: foundational, must build. Flow changes from
zmiana→zapisz to **zmiana→pytanie(ostrzeżenie)→zapisz/odrzuć**.
- Confirmed gap: no `preview`/`dry_run` function exists in
  `rota/application/` today — `apply_manual_correction` validates AND
  persists in one atomic call.
- New function shares steps 1-8 of `apply_manual_correction`
  (`assemble_planning_state` → `validate` → `materialize_deviations` +
  `_rest_override_pairs`) but STOPS before
  `lifecycle.create_schedule_version` — returns would-be Deviations,
  no persistence.
- Covers all 3 entry points above (`freeze_or_unfreeze`/
  `mark_not_worked` already route through `apply_manual_correction`).
- UI: "zapisz" enabled only after a dry-run ran for the current pending
  edit; any further edit invalidates the prior dry-run.
- Needs its own line item in the T021 implementation contract (20-task
  pipeline). NOT implemented yet, not handed to architect/Codex yet.

## Historia i audyt
Source: `rota/application/memory_read.py` — module docstring explicitly
names this T021's data source ("T021 owns human-language labels; this is
structured data only"). Two independent streams:

**1. Rule decision history** (per site rule, e.g. a SiteRuleVersion
change) — append-only Decision Ledger:
- `effective_rules_for_month(site_id, month)` → currently-active
  (resolved, unresolved, applicability) — same source PlanningState uses.
- `rules_history_for_site(site_id)` → dict rule_id → full chain of
  `DecisionRecord`s for every rule at this site.
- `provenance_for_rule_version(rule_version_id)` → the `DecisionRecord`
  that created one specific rule version.
- `decision_for_rule(rule_version_id)` → alias/lookup, same record.
- `decision_chain_for_rule_family(site_id, rule_id)` → alias for
  `rules_history_for_site`'s per-family chain, framed as one rule
  family instead of the whole site's dict — added 2026-08-22, was
  investigated earlier but never written down (Cursor audit V-A3/A4).
- `DecisionRecord` fields: decision_id, site_id, rule_id, chain_seq,
  statement (free text), coordinator_id, recorded_at, effective_from,
  rule_version_id, `rel` (one of `supersedes`/`corrects`/`rejects`,
  nullable), predecessor_decision_id — i.e. every rule change links to
  what it replaced/fixed/voided, never a bare overwrite.

**2. Coordinator material-action history** — every concrete operational
action across the whole program, one unified stream:
- `material_action_history(site_id=, affected_entity_kind=,
  affected_entity_id=, action_kind=, coordinator_id=, recorded_from=,
  recorded_to=)` → filterable list of `MaterialActionSummary`.
- `material_action_detail(action_id)` → `MaterialActionDetail`, adds
  `before_state`/`after_state` (raw changed-fact snapshots, not full
  ScheduleVersion diffs) + `source_kind`/`source_id` + `responds_to`
  (full `DecisionRequiredReadback` when this action answered a §9.1
  decision — cross-links Historia back to Decyzje koordynatora).
- `action_kind` is one of the 18 `CoordinatorActionKind` values
  (recounted 2026-08-22, spec.md previously said 17 while listing all
  18 — Cursor audit V-B5) —
  this enum is the complete list of "things that can happen" across
  every T021 screen, useful as the master action-kind filter/legend for
  this screen: CONTEXT_CONFIGURATION_SAVED, EXTERNAL_SUPPORT_WINDOW_CHANGED,
  AVAILABILITY_CHANGED, EMPLOYEE_DAY_ONLY_CHANGED, SITE_MEMBERSHIP_CHANGED,
  TARGET_HOURS_CHANGED, CALENDAR_DAY_CHANGED, SITE_PROFILE_CHANGED,
  SITE_ACTIVE_CHANGED, RULE_DECISION_RECORDED, SCHEDULE_CANDIDATE_SELECTED,
  SCHEDULE_REPLAN_CREATED, MANUAL_SCHEDULE_CORRECTION,
  ASSIGNMENT_FREEZE_CHANGED, ASSIGNMENT_NOT_WORKED, TRAINING_REALIZED,
  SCHEDULE_FINALIZED, SCHEDULE_RESTORED.
- No Polish presentation strings exist yet for these two streams (unlike
  §Decyzje koordynatora's ready-made text) — T021 UI must supply its own
  human-language labels for `action_kind`/`rel`/field names.

## Analityka i bilanse
Source: `rota/application/analytics_read.py` — module docstring says
literally "Single application-level entry point for the future
'Analityka' screen." One call: `analytics_for_site_month(site_id, month)`
→ `CoordinatorAnalyticsView(site_id, month, quarter_first_month,
hours_scope=ALL_SITES, rows)`.
- One `EmployeeAnalyticsRow` per **LOCAL** roster member only —
  EXTERNAL_SUPPORT never gets a row here (explicit exclusion,
  `MembershipKind.LOCAL` filter).
- Per row: `status` (AVAILABLE / MONTH_AVAILABLE_QUARTER_UNAVAILABLE /
  UNAVAILABLE), `month_data`, `quarter_months` (3 months), `warnings`
  (plain-text reasons when degraded, e.g. missing target_hours or an
  incomplete absence calendar for some month).
- `AnalyticsMonthData` fields: target_hours, effective_target_hours
  (back-computed = planned+realized-balance), planned_hours,
  realized_hours, month_balance, quarter_balance, unresolved_carryover.
- Degrades gracefully for DATA gaps — missing `target_hours` for the
  employee/month, or an incomplete calendar, produces a `warnings` entry
  and a smaller `status`, not an error screen. Does still raise
  `ValueError` for a malformed INPUT (`month.day != 1`) — corrected
  2026-08-22, "never throws" was too absolute (Cursor audit V-B4).
- `hours_scope` is currently always `ALL_SITES` (single enum value) —
  no per-site breakdown exists today.

**Target hours — closes a §7A flagged gap**: `target_hours` is set via
`durable_inputs.set_target_hours(coordinator_id, site_id, employee_id,
month, target_hours)` — per employee, per month, one integer. No
screen owns this today. Belongs on the per-employee ("Nazwisko Imię")
screen (same place as matrix/absence log/support windows) since it's
per-employee+month config, not analytics itself — analytics only READS
it. Add to that screen's field list.

## Wydruk Grafiku
Source: `rota/application/schedule_export.py` (T020 Checkpoint B,
read/presentation only, never touches solver/lifecycle write paths).

**Entry point**: `generate_schedule_pdf(site_id, month, period_label,
generated_at=None)` → `ExportReady(pdf_bytes, document_revision,
schedule_provenance)` or `ExportProblem(problem_code, message)`. Only
two inputs the coordinator supplies: month + `period_label` (free-text
label printed on the document, e.g. a date-range string).

**Hard precondition**: `SitePrintSettings` must already be saved for
the site (`PRINT_SETTINGS_MISSING` otherwise) — that's Panel sterowania
→ Obiekt tab's job, not this screen's. Fields (frozen shape,
`site_repository.py`):
- `company_print_name`, `site_print_name` — free text.
- `base_regime`: `"12h"` | `"24h"`.
- `work_code_intervals`: exactly the 10 keys D1-D5/N1-N5, each an
  optional start/end time interval, duration constrained to a FROZEN
  fixed hour value per code (D1=12h, D2=4h, D3=24h, D4=2h, D5=24h,
  N1=12h, N2=16h, N3=24h, N4=24h, N5=24h — `FROZEN_WORK_CODE_HOURS`,
  never editable).
- `reserve_hours`: exactly the 6 keys U3/U4/U5/C3/C4/C5, each an
  optional plain integer (hours), not a time interval.

**Result is fail-closed with ~17 distinct problem codes** (not a single
generic error) — e.g. `NO_CURRENT_SCHEDULE`, `PROVENANCE_INCOMPLETE`,
`UNSUPPORTED_TRAINEE_PRINT`, `WORK_CODE_MAPPING_REQUIRED`,
`ABSENCE_DECOMPOSITION_REQUIRED`, `ABSENCE_KIND_CONFLICT`,
`ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`, `PRINT_FONT_UNAVAILABLE`, more —
full list in `schedule_export.py` (`ExportProblemError(...)` call
sites). Per the anglicism rule above, EVERY code needs its own Polish
message, not a raw code shown to the coordinator, and not one generic
"export failed" catch-all — each names a specific, actionable data
problem (e.g. "brakuje ustawień wydruku dla obiektu", "za dużo osób w
obsadzie na jedną stronę").

## Wsparcie zewnętrzne — placement CONFIRMED
Not a separate nav item. Lives in Obsada (roster row) + per-employee
screen (support-window list). See above, both sections.

## Light/dark toggle — DROPPED
Cosmetic, not needed. Mockup stays single dark theme. Do not revisit
without new instruction.
