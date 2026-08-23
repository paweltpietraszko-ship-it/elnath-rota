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

## 5.1 SCREEN 2 — Panel sterowania → Obsada → per-employee (IN PROGRESS)

Source: `T021_spec.md:516-559` (roster matrix + per-employee screen),
`arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §5 (frozen
matrix decision).

**BLOCKED ON A SEPARATE BACKEND TASK, NOT PART OF T021**: 3 of the
5 matrix column-groups (Dniówka, Nocka, 7× weekday) have no ready
application-layer function — only the raw `rule_decisions.
record_structured_rule_decision` primitive exists, and choosing how to
wrap it (rule_id continuity, statement text, function shape) is a real
design decision, not an implementation detail. Facts handed to the
architect: `arch/T021_screen2_rule_wrapper_architect_brief_2026-08-23.md`.
**Do not build those 3 column-groups until that task lands and this
brief is updated with the real function names/signatures** — per
Paweł's explicit ruling 2026-08-23: no half-working screens shipped for
review, the small backend piece comes first.

### What CAN be built now (real functions exist, verified against source)

**Scope boundary, corrected 2026-08-23 (round-7 audit R7-1)**: this
increment covers **LOCAL** memberships only, in full (including
remove/re-add). EXTERNAL_SUPPORT is entirely out of this increment —
not created, not listed, not shown on any row — because its required
per-employee detail (support-window list) isn't designed yet, and a
roster surface may not silently hide existing product data it lists.
`list_memberships_for_site` is filtered to `membership_kind == LOCAL`
everywhere below; do together with support-window management as one
follow-up, not partially now.

- **Employee list** (Obsada tab, v1 — a plain list, not the full
  scanning matrix; the matrix-overview is deferred, see Out of scope):
  `employee_repository.list_memberships_for_site(conn, site_id) ->
  list[SiteMembership]`, filtered to `membership_kind == LOCAL`, +
  `employee_repository.list_employees_by_ids` for display names. Shows
  BOTH `enabled=True` ("na obsadzie") and `enabled=False` ("usunięty z
  obsady") rows — the list is the current+historical LOCAL roster, not
  only the active subset; the UI marks disabled rows distinctly and
  offers a re-add action (below) instead of hiding them. Each row links
  to the per-employee screen below.
- **Remove from roster** (per-employee screen action) — **NEW,
  round-7 R7-1**: `durable_inputs.update_membership(conn, *,
  coordinator_id, site_id, membership: SiteMembership, ...)` with the
  employee's CURRENT membership object, only `enabled` flipped to
  `False`; every other field (`membership_kind`, `readiness_state`,
  `readiness_source`, `can_work_24h`) carried over unchanged, read fresh
  from `list_memberships_for_site` immediately before the call, never
  reconstructed from stale UI state. No DELETE, no parallel record —
  this is the same upsert `update_membership` already uses for every
  other membership edit.
- **"+ Dodaj osobę"**: picker over two paths, LOCAL only per the scope
  boundary above:
  - *Nowy pracownik*: form (display_name, day_only checkbox) →
    complete `Employee` construction, corrected 2026-08-23 (round-7
    R7-2, `employee_id` generation corrected again round-9 R9-1) — all
    5 constructor fields, only 2 are coordinator inputs:
    - `employee_id` — **generated once by the frontend**
      (`crypto.randomUUID()`), the moment "+ Dodaj osobę" opens, NOT by
      the API layer. Corrected 2026-08-23 (round-9 R9-1): `Employee`
      uniqueness is `employee_id` only (`display_name` has no UNIQUE
      constraint, `db.py:141-146`) — a server-generated ID returned in a
      lost HTTP response left no way to retry step 1 without risking a
      second Employee row for the same person. A client-generated ID
      makes step 1 itself idempotent: retrying it with the SAME id hits
      the same upsert row, no duplicate possible. The id is held in
      component/form state (and `sessionStorage`, so a reload mid-flow
      doesn't lose it) until step 2 below succeeds, then discarded — it
      is never regenerated on re-render or on a "Ponów" click. Backend
      still validates format and coordinator authorization; the id
      itself carries no privilege.
    - `display_name` — coordinator input.
    - `active_from` — generated by the API layer as today's date
      (`date.today()`). Legacy/informational metadata only (T016: "nie
      oznacza pola, które przyszły Panel musi pytać koordynatora jako
      warunek planowania") — never a form field, never read as an
      eligibility signal.
    - `active_to` — always `None` on creation. Same legacy-metadata
      status as `active_from`; not a form field.
    - `day_only` — coordinator input (checkbox).

      Then `durable_inputs.update_membership(conn, *, coordinator_id,
      site_id, membership: SiteMembership, ...)` with `membership_kind=
      LOCAL, enabled=True, readiness_state=NOT_READY, readiness_source=
      DEFAULT, can_work_24h=True`.

      **Sequencing, corrected 2026-08-23 (round-8 R8-2, id source
      corrected round-9 R9-1)**: two separate, independently-callable
      API endpoints, the frontend orchestrates, matching *istniejący
      pracownik* below:
      1. `POST` employee-creation endpoint → calls `update_employee`
         with the frontend-supplied `employee_id`. Idempotent: calling
         it twice with the same id and the same field values is a safe
         no-op (`update_employee`'s own `before == ...` check).
      2. `POST` roster-attach endpoint (site-scoped) → calls
         `update_membership` only, given the same `employee_id` (from
         step 1, or picked directly in the *istniejący pracownik* path)
         — `enabled=True, membership_kind=LOCAL, ...`. **Same endpoint
         for both paths.**

      *Nowy pracownik* calls (1) then (2), both addressed by the one
      frontend-held id. Any failure at either step is retried by
      re-calling that same step with the same id — never generates a
      new id for the same in-progress attempt.
  - *Istniejący pracownik* — **narrowed 2026-08-23 (round-8 R8-1)**:
    `site_memberships` has ONE row per `(employee_id, site_id)`
    regardless of kind (`db.py:148-155`) — `update_membership` upserts
    on that same pair, so blindly reusing it on an employee who already
    has an EXTERNAL_SUPPORT row here would silently convert that row to
    LOCAL. The picker therefore reads `list_memberships_for_site`
    **unfiltered by kind** and offers only:
    - employees with **no membership row at all** at this site → step
      (2) above creates a fresh LOCAL row;
    - employees with an existing row where `membership_kind == LOCAL
      and enabled == False` → step (2) above, same row, `enabled=True`,
      every other field (`can_work_24h` etc.) carried over from that
      row unchanged (re-add, not a fresh row).

    Employees whose existing row has `membership_kind ==
    EXTERNAL_SUPPORT` (enabled or not) are **not shown in this picker at
    all** — out of scope per the boundary above, this flow must never
    read or write their row.
- **Per-employee screen — "Ogólna dostępność" — UNBLOCKED, corrected
  2026-08-23 (architect resolution on
  `arch/T021_screen2_availability_singularity_architect_brief_2026-08-23.md`,
  replaces every round-8/round-9 text on this control)**: no
  single-family invariant exists or is wanted. An employee may have
  multiple independent `UNAVAILABLE_24H` periods at once; nothing merges
  or deduplicates them. This makes "Ogólna dostępność" work exactly like
  the other 4 `AvailabilityKind` values below — same list, same form, no
  special case:
  - **Checked/unchecked for a given day `d`** is a pure display
    computation, never written or read as its own field:
    `not any(r.active and r.kind == UNAVAILABLE_24H and r.start_date <=
    d <= r.end_date for r in records)`. The per-employee screen's own
    "current status" indicator uses today's date; the deferred
    roster-overview matrix (Out of scope) would use whichever day it's
    scanning.
  - **New period**: fresh `availability_id` (`uuid.uuid4().hex`),
    `durable_inputs.append_availability(conn, *, coordinator_id,
    site_id, availability_id, employee_id, kind, start_date, end_date,
    active=True, ...)`. Always a new family — never looks for an
    existing one to reuse.
  - **Edit an existing period** (shown in the log below): the SAME
    `availability_id` as that specific log entry, new `start_date`/
    `end_date`, `active=True` — a new version in that one family. The
    coordinator picks WHICH period to edit directly from the list (each
    entry is its own row with its own edit action); there is no
    lookup/selection logic anywhere in `api/` or `rota/**` — the
    frontend already has the full list loaded for display and the
    coordinator's click supplies the `availability_id` directly.
  - **End a period early**: same `availability_id`, `active=False`.
  - `AvailabilityRecord.active=True` on an already-past `end_date` is
    normal and permanent (no auto-expiry) — the day-`d` computation
    above already treats it as not-blocking once `d > end_date`; nothing
    needs to change `active` for that.
- **Per-employee screen — "24h" toggle**: same `update_membership` call
  as remove-from-roster, flipping only `can_work_24h`, every other field
  carried over unchanged. Plain persistent bool, no date range, no
  auto-revert (`T021_spec.md:524-529` — do not build a date picker for
  this one).
- **Per-employee screen — "Zgłoś nieobecność"** — **corrected 2026-08-23
  (architect resolution above removes the round-9 R9-2 restriction)**:
  one form, all 5 `AvailabilityKind` values
  (`DAY_SHIFT_OFF`/`UNAVAILABLE_24H`/`LEAVE_PLAN`/`LEAVE_GRANTED`/
  `SICK_LEAVE`) + date range — this IS "Ogólna dostępność"'s own
  mechanism for `UNAVAILABLE_24H` (not a separate path): new entry =
  fresh `availability_id`; editing/ending an entry already in the log
  reuses that entry's own `availability_id`. Shown as a log of every
  family's current state, all 5 kinds together:
  `availability_repository.get_current_availability_for_employee(conn,
  employee_id) -> list[AvailabilityRecord]` (persistence-layer, no
  application wrapper, call directly per the same already-accepted
  missing-wrapper pattern as Screen 1's calendar read) — includes
  `active=False` chain-ends, shown as past/ended entries, not filtered
  out.
- **Per-employee screen — godziny docelowe/miesiąc** — corrected
  2026-08-23 (round-7 R7-4, owner ruling): plain month selector, no
  restriction to months with an existing schedule — defaults to the
  current calendar month, coordinator may pick any month (including
  future months, ahead of any schedule). `durable_inputs.set_target_hours(
  conn, *, coordinator_id, site_id, employee_id, month, target_hours,
  ...)` (`month` always the first of the month). Read side:
  `work_balance_repository.get_work_balance_target(conn, employee_id,
  month) -> Optional[int]` (persistence-layer, no wrapper — call
  directly). `None` is a real, distinct state — "brak ustawionej
  wartości" — never displayed or submitted as `0`; the UI must not
  collapse "never set" into a saved zero.
- **Per-employee screen — day_only flag**: same `update_employee` call
  as employee creation, reading the employee's CURRENT full record first
  (`employee_repository.get_employee`) and resubmitting all 5 fields with
  only `day_only` changed — corrected 2026-08-23 (round-7 R7-2), a
  day_only edit must never blank or guess `display_name`/`active_from`/
  `active_to`.
- **Per-employee screen — S/szkolenie**: read-only badge only
  (`SiteMembership.readiness_state`) — per `T021_spec.md:92-98`, NOT
  editable in this increment (confirm with Paweł before making it
  editable; `readiness_source=COORDINATOR_OVERRIDE` override path
  exists in `update_membership` but has no UI yet).

### Out of scope for this increment

- Dniówka/Nocka/weekday matrix columns — blocked, see above.
- The full roster-overview matrix (all employees, all columns at a
  glance) — the per-employee screen is the primary surface for now; the
  scanning grid is a later addition once the blocked columns exist too
  (building it now would show mostly non-functional columns).
- EXTERNAL_SUPPORT entirely — membership creation, listing, and
  support-window management — moved from "listed but incomplete" to
  fully out of scope 2026-08-23 (round-7 R7-1); do together as one
  follow-up once the per-employee support-window UI is designed.
- `membership_kind` editing (LOCAL↔EXTERNAL_SUPPORT after creation) —
  `T021_spec.md:100-102` confirms this isn't editable anywhere in the
  mockup either; out of scope until asked for.

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
