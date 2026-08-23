# ROTA-T021 — FRONTEND IMPLEMENTATION CONTRACT

STATUS: LIVE — screens added incrementally, one at a time
BASE_PRODUCT_SHA: `7349ae6` (main, post-T023b merge)
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

### 3.3 D4 superseded — Site creation is per-service, not one generic form

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
§3.3 above; rest current).

### Reads (no mutation)
- `bootstrap.active_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]`
- `site_memory.current_decision_required_months_for_site(conn, *, site_id: str) -> list[date]`
  — per site, for the "Wymaga decyzji" filter chip
- `bootstrap.coordinator_context_completeness(conn, *, coordinator_id: str, site_id: str) -> ContextCompleteness(complete: bool, missing: tuple[str, ...])`
  — per site, for the "Konfiguracja niepełna" filter chip
- `bootstrap.month_plan_readiness(conn, *, coordinator_id: str, site_id: str, month: date) -> MonthPlanReadiness(ready, missing, target_hours_warnings)`
  — combine with the above per §T021_spec.md:370-377
- `site_repository.get_site_print_settings(conn, site_id: str) -> Optional[SitePrintSettings]`
  — `None` is an additional "Konfiguracja niepełna" signal (`PRINT_SETTINGS_MISSING`)
- Search: client-side filter over `active_sites_for_coordinator`'s result
  by `display_name`/`site_id` — no backend call.

### Writes
- **Create OCHRONA Site** / **Create ORDINARY Site** (two entry points,
  shared form component per §3.3): `bootstrap.bootstrap_or_resume_coordinator_context(conn, *, coordinator_id, site_id, coordinator=None, site_profile=SiteProfile(...), site=Site(..., planning_regime=SitePlanningRegime.OCHRONA|ORDINARY), association=CoordinatorSiteAssociation(...))`.
  Minimal fields per the (superseded but still field-accurate) form spec:
  Nazwa obiektu, Nazwa profilu zmianowego, Próg decyzyjny 7-dniowy
  (`rolling_7d_decision_threshold_hours`). D2's three fixed SiteProfile
  constants (`training_s_enabled=False`, `external_support_enabled=True`,
  `day_only_blocks_n=True`) are hardcoded in this call, never
  coordinator-facing fields.
- `backup.backup_database(conn, destination: str) -> None`
- `backup.build_diagnostic_zip(conn, destination: str) -> None`
  (destination: a path the API layer resolves server-side; the frontend
  triggers a download, it does not choose a filesystem path itself)

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
expansion must additionally cover the T023b regime-correction UI (§3.3)
when it's reached.

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
  marked superseded (§3.3).
