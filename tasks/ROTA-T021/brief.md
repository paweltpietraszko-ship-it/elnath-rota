# ROTA-T021 — FRONTEND IMPLEMENTATION CONTRACT

STATUS: LIVE — screens added incrementally, one at a time
BASE_PRODUCT_SHA: `7349ae6` (main, post-T023b merge) — **branch corrected
2026-08-23 to actually descend from this SHA (round-2 audit A1: the
branch had diverged before T023b merged); verified
`git merge-base --is-ancestor 7349ae6 HEAD` now succeeds.**
ROUND-2 CORRECTIONS (2026-08-23, `tasks/ROTA-T021/round_01/tests/tests_r2.txt`):
A1 branch ancestry (above), A2 dropped `month_plan_readiness` from
Screen 1 (§4 Reads), A3 complete Site-creation field mapping (§4
Writes), A4 three-state calendar UI + bulk-generate action (§4
Calendar/holidays).
OWNER_PROCESS: resolved live with Paweł, no architect design round-trip
(makieta already exists; architect would only be re-designing from it —
Paweł's explicit ruling, 2026-08-23). Codex still audits each screen for
CONTRACT COMPLETENESS (Tor 1 below) — this replaces the architect round,
it does not remove verification entirely.

This document consolidates decisions already made across several
documents into one place Codex can audit against. It does not restate
their reasoning — see the source docs for that.

## 1. AUTHORITATIVE SOURCES (read these, this brief only indexes them)

- `arch/T021_spec.md` — per-screen backend function/DTO facts. Authoritative
  for WHAT each screen must show and call.
- `arch/T021_owner_decisions_2026-08-22.md` — D1 (calendar in scope,
  global), D2 (SiteProfile toggles permanently out of UI), D3 (Site
  editing in scope), frontend stack (React+TS+Vite).
- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md` §2-3, 5 +
  `tasks/ROTA-T023b/brief.md` §5 — **supersedes D4** below.
- Design Canvas artifact "Elnath Rota UI Makieta" (private, owned by
  Paweł) — visual reference. Tor 2 (Paweł's own review) checks fidelity
  to this; Codex does not have access to it and does not audit visual
  match, only backend-contract completeness.
- `arch/FINDING_2026-08-23_RODO_INTERNAL_NETWORK_BASELINE.md` — auth (F1)
  and SQLCipher are NOT T021 blockers (ruled 2026-08-23), but §1 below
  still requires real login now per T025's original F1 finding — see
  note in §2.

## 2. WORKING METHOD (two tracks, both required before a screen is "done")

**Tor 1 — contract completeness (Codex, mechanical).** For each screen:
does the frontend call exactly the backend functions named in
`T021_spec.md` for that screen, with every required field, no invented
fields, no silently-dropped required fields? Codex audits source only —
it cannot and does not judge visual/UX correctness.

**Tor 2 — product fit (Paweł, sensory).** Does the running screen actually
serve a coordinator the way it's meant to, matching the mockup's intent?
Only Paweł can answer this. CC runs the screen in a real browser before
handing it over, to catch obvious breakage first, but that is not a
substitute for Tor 2.

A screen is done only when both tracks pass. Neither track blocks CC from
starting the next screen while the other is pending on a finished one.

## 3. GLOBAL ARCHITECTURE DECISIONS

### 3.1 Frontend stack (D1-D4 doc, unchanged)
React + TypeScript + Vite. No Next.js. Reasoning already recorded, not
reopened here.

### 3.2 API layer (NEW DECISION, 2026-08-23 — was open as T025 finding F2)

`rota/application/*.py` is a plain Python function library taking an
already-open `sqlite3.Connection` — no HTTP layer exists. The React
frontend cannot call Python functions directly. Decision: **FastAPI**,
thin pass-through only.

Reasoning: Python-native (no second language for the API layer), trivial
to wrap existing `rota/application/*` functions 1:1, automatic OpenAPI
schema generation gives Codex a second, independent source to diff
frontend calls against (not just reading TypeScript source), works
identically for the eventual Railway/PWA path (T025) and for a
client-hosted internal-network path (this is the same decision either
way — only the deployment target changes, not the API shape).

Required shape:
- one FastAPI router module per `rota/application/*.py` module it wraps
  (e.g. `api/routers/bootstrap.py` wraps `rota.application.bootstrap`);
- a router function does argument marshalling (JSON <-> Python
  dataclass/enum) and calls the existing application function directly —
  it must not reimplement or duplicate any business logic, validation, or
  branching that already lives in `rota/application/*.py`. If a screen
  seems to need logic that doesn't exist as an application function yet,
  that is a gap to flag, not something to invent in the API layer;
  exception construction (`SiteNotFound`, `InvalidCoordinatorContext`,
  etc.) maps to HTTP status codes in one shared error-mapping helper, not
  per-router ad-hoc handling;
- `sqlite3.Connection` lifecycle (open per request, close after) is the
  API layer's own concern, not exposed to the frontend;
- authentication (T025 F1) is a real, separate, still-undesigned
  requirement layered on top of this API — not solved by this brief.
  Until it exists, the API must not be exposed on any network the
  coordinator's own machine doesn't already trust (dev-local only for
  now). This does not block screen-building (per the RODO finding's
  ruling), but no build of this API may ship to a client before F1 is
  real.

### 3.3 Interim coordinator_id, pending real login (GAP FOUND 2026-08-23)

`T021_spec.md:118-165`'s "coordinator identity switcher" (a no-password
name-picker in the header, using `active_coordinators`/
`all_coordinators`) is explicitly marked SUPERSEDED by T025's real-login
requirement — it is not the design to build. But real login (F1) does
not exist yet either, and every screen needs SOME `coordinator_id` to
call anything. Interim decision, dev-only, until F1 lands: the API layer
reads `coordinator_id` from a single hardcoded dev-config value (an env
var or a one-line config file), never from a UI control. No login
screen, no identity-picker UI gets built as if it were real — that would
misrepresent an already-superseded design as current. When F1 (real
login) is designed, this interim mechanism is deleted outright, not
extended.

### 3.4 D4 superseded — Site creation is per-service, not one generic form

`T021_spec.md:393-407`'s "one inline form, Nazwa obiektu / Nazwa profilu /
Próg decyzyjny" is STALE. Per `FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md`
§3/§5 (T023b, owner-ruled 2026-08-23):

- separate, unambiguous creation entry points for OCHRONA and ORDINARY —
  no generic regime checkbox/toggle/dropdown;
- the chosen entry point supplies `Site.planning_regime` explicitly to
  `bootstrap_or_resume_coordinator_context`;
- common fields/validation/components stay shared (one underlying form
  component, parameterized by regime, not two independent forms);
- ordinary Site editing must expose no regime-change control;
- a mistaken initial classification is corrected only via
  `durable_inputs.correct_site_planning_regime` (separate, explicit,
  confirmed action — not a field in the ordinary edit form).

Everything else in `T021_spec.md`'s Workspace/Przedpokój section (backup
placement, completeness filters, search) is unchanged and current.

## 4. SCREEN 1 — Workspace / Przedpokój (IN PROGRESS)

Source: `T021_spec.md:344-407` (Site-creation subsection superseded by
§3.4 above; rest current).

### Reads (no mutation)
- `bootstrap.active_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]`
- `site_memory.current_decision_required_months_for_site(conn, *, site_id: str) -> list[date]`
  — per site, for the "Wymaga decyzji" filter chip
- `bootstrap.coordinator_context_completeness(conn, *, coordinator_id: str, site_id: str) -> ContextCompleteness(complete: bool, missing: tuple[str, ...])`
  — per site, for the "Konfiguracja niepełna" filter chip. **CORRECTED
  2026-08-23 (round-2 audit A2)**: this is the ONLY completeness read
  Screen 1 uses. `month_plan_readiness` is dropped from this screen — it
  requires a `month` param Workspace has no reason to own (it lists
  Sites, not one month), and it already calls
  `coordinator_context_completeness` internally and folds its `missing`
  list in (`bootstrap.py:330`), so calling both here would be one
  completeness calculation done twice with no month owner for the
  second one. `month_plan_readiness` belongs to Planowanie miesiąca,
  where a specific month is already selected — wire it there when that
  screen is reached, not here.
- `site_repository.get_site_print_settings(conn, site_id: str) -> Optional[SitePrintSettings]`
  — `None` is an additional "Konfiguracja niepełna" signal (`PRINT_SETTINGS_MISSING`)
- Search: client-side filter over `active_sites_for_coordinator`'s result
  by `display_name`/`site_id` — no backend call.

### Writes
- **Create OCHRONA Site** / **Create ORDINARY Site** (two entry points,
  shared form component per §3.4): `bootstrap.bootstrap_or_resume_coordinator_context(conn, *, coordinator_id, site_id, coordinator=None, site_profile=SiteProfile(...), site=Site(...), association=CoordinatorSiteAssociation(...))`.

  **CORRECTED 2026-08-23 (round-2 audit A3)** — complete field mapping,
  UI inputs are exactly three (Nazwa obiektu, Nazwa profilu zmianowego,
  Próg decyzyjny 7-dniowy); every other constructor field is either a
  generated ID or a fixed constant, named explicitly here so no
  implementation invents its own values:

  - `site_id: str` — **generated by the API layer**, never UI input:
    `f"SITE-{uuid.uuid4().hex}"`.
  - `profile_id: str` — **generated by the API layer**, same pattern:
    `f"PROF-{uuid.uuid4().hex}"`. Same value used for both
    `SiteProfile.profile_id` and `Site.profile_id`.
  - `SiteProfile.display_name` — UI input: Nazwa profilu zmianowego.
  - `SiteProfile.active` — constant `True`.
  - `SiteProfile.standard_shifts` — constant `[]` (empty on purpose: the
    catalog is filled incrementally in Panel Sterowania afterward, per
    `bootstrap_or_resume_coordinator_context`'s own "resume a partial
    context" design — an empty catalog is exactly why the new Site
    correctly appears under "Konfiguracja niepełna," not a bug to fix
    here).
  - `SiteProfile.day_only_blocks_n` — constant `True` (D2).
  - `SiteProfile.external_support_enabled` — constant `True` (D2).
  - `SiteProfile.training_s_enabled` — constant `False` (D2).
  - `SiteProfile.training_s_weekdays_only` — constant `False`. Moot per
    D2 (never read once `training_s_enabled=False`), but the constructor
    has no default, so a value must still be supplied.
  - `SiteProfile.training_s_default_readiness_threshold` — constant `1`.
    Same moot-but-mandatory reasoning.
  - `SiteProfile.rolling_7d_decision_threshold_hours` — UI input: Próg
    decyzyjny 7-dniowy.
  - `Site.display_name` — UI input: Nazwa obiektu.
  - `Site.active` — constant `True`.
  - `Site.planning_regime` — supplied by the chosen entry point
    (`SitePlanningRegime.OCHRONA` or `.ORDINARY`), not a form field.
  - `CoordinatorSiteAssociation.coordinator_id` — the interim
    dev-config `coordinator_id` (§3.3).
  - `CoordinatorSiteAssociation.site_id` — the same generated `site_id`.
  - `CoordinatorSiteAssociation.active` — constant `True`.
  - `coordinator=None` — the dev-config coordinator is created once as a
    separate, one-time dev-setup step (outside this per-Site-creation
    call, not part of Screen 1); ordinary Site creation never re-creates
    or re-supplies the `Coordinator` row.
- `backup.backup_database(conn, destination: str) -> None`
- `backup.build_diagnostic_zip(conn, destination: str) -> None`
  (destination: a path the API layer resolves server-side; the frontend
  triggers a download, it does not choose a filesystem path itself)

### Calendar/holidays (GAP FOUND 2026-08-23 — never placed on any screen)

D1 (`arch/T021_owner_decisions_2026-08-22.md`) ruled calendar editing
in scope, global/whole-UI — `CalendarDay` has no `site_id` at all. No
document ever assigned it to a screen (`T021_spec.md:42` only lists it
as an unplaced gap). Workspace/Przedpokój is the only screen with
matching (cross-Site, global) scope — decided here, now, not deferred
again:

- Read: `calendar_repository.list_calendar_days(conn, range_start: date, range_end: date) -> list[CalendarDay]`
  (persistence-layer, no application wrapper exists for reads — call
  directly, same already-accepted pattern as other missing-wrapper
  reads noted in `T021_spec.md`)
- Write: `durable_inputs.set_calendar_day(conn, *, coordinator_id: str, site_id: str, day: CalendarDay, note=None, responds_to_decision_required_id=None) -> None`
  — `site_id` here is a pure authorization technicality (any active
  `CoordinatorSiteAssociation` works; the write itself is never
  site-scoped or persisted per-site). The frontend must pass any one of
  the coordinator's own associated site_ids for this call — it must
  never be shown to the user as "which obiekt," since that would imply a
  scoping that doesn't exist.

  **CORRECTED 2026-08-23 (round-2 audit A4)**: `list_calendar_days`
  returns only persisted rows. A missing row is not the same fact as a
  persisted `holiday=False` — `month_plan_readiness` (used by Planowanie
  miesiąca, and by extension anything depending on a Site being
  plan-ready) treats every missing date as incomplete configuration.
  The UI must therefore show three distinct states per date, not two:

  1. **niekonfigurowany** (no row for that date) — visually distinct
     from state 2, never silently rendered as an unchecked "roboczy" box;
  2. **roboczy** (persisted `holiday=False`) — an explicit saved fact;
  3. **święto** (persisted `holiday=True`).

  Toggling a single date only ever writes that one date. To move a whole
  displayed range out of state 1, the screen offers a bulk action
  ("Wygeneruj kalendarz na rok/miesiąc YYYY") that calls
  `set_calendar_day` once per date in range for every date NOT already
  present, each with `holiday=False` — this is the only way a Site's
  calendar reaches "complete" for `month_plan_readiness`'s purposes.
  Individual dates are then toggled to `holiday=True` as needed. The
  bulk action must skip (not overwrite) dates that already have a row.

### Out of scope for this screen
- Site regime correction (`correct_site_planning_regime`) — belongs to
  Panel Sterowania's per-Site editing, not Workspace.
- Anything inside a Site's "room" (all other screens).

## 5. SCREENS 2-9 — not yet detailed

`T021_spec.md` sections for Przegląd, Planowanie miesiąca, Panel
sterowania (Obiekt/Obsada), Decyzje koordynatora, Ręczna korekta,
Historia i audyt, Analityka i bilanse, Wydruk Grafiku remain the
authoritative source. Each gets its own §-numbered expansion in this
brief when CC starts building it — not written speculatively ahead of
need, matching Paweł's established per-screen method
([[feedback_screen_function_list_before_mockup]]). Panel Sterowania's
expansion must additionally cover the T023b regime-correction UI (§3.4)
when it's reached.

**Known open items from `T021_spec.md`'s own completeness audit
(lines 30-198) that must not get silently dropped when their screen is
reached** — carried forward explicitly so re-verifying each screen
doesn't depend on re-reading the whole spec file from scratch every
time:

- **Panel Sterowania**: `durable_inputs.update_site_profile` (only
  `rolling_7d_decision_threshold_hours` may ever be editable per D2 —
  the other SiteProfile toggles stay permanently non-coordinator-facing);
  `durable_inputs.update_site` (D3, display_name/active editing);
  `update_membership`'s `readiness_source=COORDINATOR_OVERRIDE` path for
  S/szkolenie (currently read-only badge only, per
  `T021_spec.md:92-98` — confirm with Paweł whether T021 makes this
  editable or keeps it read-only); `membership_kind` is not editable
  anywhere today (`T021_spec.md:100-102`) — confirm in/out of scope
  before building, don't assume.
- **EmployeeDetail (Panel Sterowania → per-employee)**: absence log's
  real source is `availability_repository.get_current_availability_for_employee`
  (persistence-layer, no application wrapper — same missing-wrapper
  pattern as calendar reads above), not
  `availability_matrix.employee_availability_matrix` (that function
  covers only 3 of 5 `AvailabilityKind` values and 2 of 4 relevant rule
  kinds — confirmed insufficient for the absence log,
  `T021_spec.md:71-90`).
- **Ręczna korekta**: the dry-run preview function this screen's Krok 2
  needs does not exist in `rota/application/*` yet
  (`T021_spec.md:186-187`) — flag back, do not invent it in the API
  layer.
- **Planowanie miesiąca**: "Historia wersji"/`restore` source
  (`open_month.months_with_schedule`/`list_schedule_versions`?) was
  never confirmed (`T021_spec.md:111-113`) — verify before building, not
  guessed.
- **Cross-cutting**: one raw/untranslated backend code,
  `DAY_SHIFT_OFF-01` in `rota/planning/decision_guidance.py`
  (`_render_condition`), returns unmapped — violates the no-anglicisms
  rule; whichever screen renders it (Decyzje koordynatora) needs either
  a backend fix (out of this task's scope per §6) or a frontend-side
  translation table as a stopgap — decide when that screen is reached,
  don't ship the raw code to a coordinator.

## 6. TASK_SCOPE

New directories, this task owns them entirely (greenfield):
- `frontend/` — React + TypeScript + Vite app
- `api/` — FastAPI thin pass-through layer

Existing `rota/**` files may be READ (existing application functions) but
this task does not modify `rota/**` — a gap found while wiring a screen
(a function that doesn't exist yet) is flagged back, not silently
patched into the API layer.

## 7. NEGATIVE SCOPE

- No authentication implementation yet (§3.2 — separate, still-open
  requirement).
- No SQLCipher/encryption-at-rest work (ruled non-blocking, separate finding).
- No Railway/PWA deployment config yet (T025, separate).
- No redesign of `T021_spec.md`'s per-screen facts — this brief indexes
  them, it does not re-derive or override them except where explicitly
  marked superseded (§3.4).
