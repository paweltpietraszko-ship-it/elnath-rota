# T021 implementation pipeline — DRAFT input for architect (2026-08-22)

**UPDATE (2026-08-22, same day)**: `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`
(ROTA-T025) supersedes this draft's "Coordinator identity switcher"
item below — deployment moved to a hosted PWA, real password login is
now required instead of a no-password picker. That item's description
further down is corrected inline. Nothing else in this document changes
— T023 (referenced as NB-3) is UNAFFECTED by T025 (pure domain/solver
logic, no dependency on deployment model or auth), no need to stop or
revise it for this reason.

STATUS: factual input material, NOT a decided implementation contract.
Same role as `arch/T004_T005_architect_brief.md` and
`arch/FINDING_2026-08-22_ABSENCE_HOURS_ACCOUNTING.md` — CC does not
design the contract, sequence rounds authoritatively, or assign final
Task numbers; that's architect Claude's job once Paweł relays this.
Source of every fact below: `arch/T021_spec.md` (already
Codex/Cursor-audited, see that file's own audit sections) — this
document only reorganizes it from per-screen to per-implementation-unit.

## Headline finding: T021 is >90% a FRONTEND-ONLY task
Nearly every backend function T021's UI needs already exists and is
already merged — traced to `rota/application/*.py` module docstrings,
most of which cite "tasks/ROTA-T009/brief.md operation N" as origin
(open_month=op1, precheck=op2, plan_ops=op3/4/5, manual_edit=op8,
training=op9, lifecycle_ops=op10, memory_read=op11), plus later
feature tasks: T010 (roster matrix/availability), T012 (24h shifts),
T013 (DecisionRequiredPayload), T017 (multi-candidate PLAN), T019/T019b
(analytics + action history/decision readback), T020 (PDF export).
Genuinely NEW backend work is small — 3 items, listed below.

## NEW backend work required (not yet built, block or run alongside UI work)

**NB-1. Dry-run preview for manual correction** (Ręczna korekta).
Paweł's explicit decision, called foundational. Shares
`apply_manual_correction`'s steps 1-8 (assemble → validate →
materialize_deviations + `_rest_override_pairs`), stops before
`lifecycle.create_schedule_version`, returns would-be Deviations. Full
shape: `T021_spec.md` §Ręczna korekta "NEW BACKEND FUNCTION NEEDED".
Blocks: the Ręczna korekta screen's core interaction (can be built with
a stub/no-dry-run fallback if sequencing requires, but the "zmiana→
pytanie→zapisz/odrzuć" flow Paweł asked for specifically needs it).

**NB-2. Two missing application-layer wrappers** (Cursor audit
V-C1/V-C2, `tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`):
- `current_decision_required_months_for_site` — exists in
  `rota/persistence/site_memory.py`, no `memory_read.py` wrapper (its
  siblings all have one).
- `SitePrintSettings` save — `save_site_print_settings` exists in
  `rota/persistence/site_repository.py`, no `durable_inputs.py`
  wrapper.
Low-risk, thin wrapper functions — does not block UI work (UI can call
persistence directly short-term the way `schedule_export.py` already
does, or these get added as a small prerequisite round).

**NB-3. Absence-hours accounting — ROTA-T023, already spun off,
currently FAIL/blocked** at the architect, per Codex round 3
(`tasks/ROTA-T023/round_01/tests/tests_r3.txt`). Not part of this
document's scope — tracked separately, Paweł's explicit priority
ordering (T023 before T021) still stands for THAT unit of work; noted
here only because Analityka i bilanse's `month_balance`/
`quarter_balance` figures will change once T023 lands.

**NB-4. Real authentication (T025 F1)** — CORRECTED 2026-08-22, was
listed as a UI-only gap below before the PWA/hosting pivot. No
password/credential-verification layer exists anywhere in `rota/`
today (`context.py`'s check is identity-trust only, not
authentication). This is now foundational, not a simple header
component — it blocks the "workspace shell" build unit (item 1 below)
from being a no-password picker as originally planned. Exact scheme
not decided (see T025 finding) — flag as a real dependency, not a
same-day frontend task.

## UI-only gaps (backend already exists, just never had a screen)
No new backend needed for any of these — purely frontend build items,
can be sequenced freely:
- ~~Coordinator identity switcher (no-password picker)~~ — SUPERSEDED,
  see NB-4 above and `T021_spec.md`'s "CROSS-CUTTING REQUIREMENT"
  section (now marked superseded there too). The underlying scoping
  need (site list scoped to the acting coordinator,
  `active_sites_for_coordinator`) is unchanged — only the mechanism for
  establishing "who is acting" changes from a picker to real login.
- SiteProfile toggles on Panel sterowania → Obiekt (`day_only_blocks_n`,
  `external_support_enabled`, `training_s_enabled`,
  `training_s_weekdays_only`, `training_s_default_readiness_threshold`)
  — `update_site_profile` already exists and writes all of these.
- `set_calendar_day` (holiday/calendar config) — function exists, no
  screen. Placement not yet decided (candidate: a small section on
  Panel sterowania → Obiekt, not yet proposed to Paweł).
- Coordinator account management (`update_coordinator`/
  `update_association`, `active_coordinators`/`all_coordinators`) —
  explicitly out of scope per `T021_spec.md`'s completeness audit;
  confirm with Paweł whether this stays out of T021 entirely or gets a
  minimal screen.
- Readiness override (`update_membership`'s
  `readiness_source=COORDINATOR_OVERRIDE`) and `membership_kind`
  editing (LOCAL↔EXTERNAL_SUPPORT via the same function) — both
  documented, both need a small control added to the EmployeeDetail
  screen's existing matrix card, not a new screen.
- "+ Nowy obiekt" — DECIDED and mocked (workspace inline form), backend
  is `bootstrap_or_resume_coordinator_context`, already exists.

## Per-screen build units (suggested grouping, not a final round plan)
Every screen's full data/action spec is in `arch/T021_spec.md` — not
repeated here. Grouping by shared surface area only:

1. **Workspace shell**: `Main.dc.html` equivalent — site list
   (`active_sites_for_coordinator`), filter chips, search, "+ Nowy
   obiekt" form, backup/diagnostyka card, **login screen (NB-4)**
   instead of the originally-planned no-password picker — shared
   header/session state used by every other screen too, build this
   once, early. Depends on NB-4's auth scheme being decided first.
2. **Panel sterowania**: Obiekt tab (site fields, shift catalog,
   D1-D5/N1-N5 print codes, U3-C5 reserve hours, SiteProfile toggles) +
   Obsada tab (roster matrix, 24h plain-toggle vs. date-ranged columns
   — mechanism distinction in spec is load-bearing, not cosmetic) +
   per-employee detail screen (matrix row, day_only, S status +
   override, absence log via
   `get_current_availability_for_employee`, target_hours,
   membership_kind edit, support-window list for EXTERNAL_SUPPORT).
3. **Przegląd**: composed dashboard (decision preview, version-status
   tile, headcount, "wróć do pracy" resume link, quick actions) — build
   after Panel sterowania + Planowanie miesiąca exist, since it links
   into both.
4. **Planowanie miesiąca**: plan/select/replan/finalize/restore flow,
   PLAN/WYK grid matching the real paper document
   (`Grafiki/7442.jpg`) — non-negotiable visual fidelity requirement,
   see spec's "Correction same day" note.
5. **Decyzje koordynatora**: month list + blocker/unblocking-option
   display — string-matched links into screens 2 and 4 (spec's V-C3
   caveat: fragile prefix matching, not ID-based — implementer should
   know this going in).
6. **Ręczna korekta**: depends on NB-1 (dry-run) for its core flow;
   freeze/unfreeze and NN can ship first as simpler entry points if
   sequencing needs to decouple from NB-1.
7. **Historia i audyt**: two independent read streams, no
   interdependency with other screens beyond linking INTO them
   (`responds_to` cross-link to Decyzje koordynatora).
8. **Analityka i bilanse**: single existing entry point, straightforward
   — but note `month_balance`/`quarter_balance` values will shift once
   T023 lands; sequence-independent otherwise.
9. **Wydruk Grafiku**: single existing entry point
   (`generate_schedule_pdf`), ~17 problem codes each need a Polish
   message — the largest single "just translate/wire it up" chunk of
   work in T021.

## Cross-cutting, applies to every unit above
- No anglicisms in any UI-facing text (`T021_spec.md`'s rule, with the
  specific known internal codes needing translation, including the
  `DAY_SHIFT_OFF-01` backend gap that needs its OWN fix in
  `decision_guidance.py`, separate from T021's UI work).
- Every screen that mutates state must pass `responds_to_decision_required_id`
  through when reached via a Decyzje koordynatora link.
- Light/dark toggle: dropped, do not resurrect without new instruction.

## Explicitly NOT decided here (architect's call)
- Actual Task numbering/branch structure (one T021 branch vs. several
  sub-tasks vs. the numbered-round convention used elsewhere).
- Build order beyond the loose grouping above.
- Whether NB-1/NB-2 become their own preceding Tasks or land inside
  T021's own branch.
- `set_calendar_day` and coordinator-account-management placement
  (flagged, not proposed).
