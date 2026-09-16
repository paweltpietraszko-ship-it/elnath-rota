# FINDING 2026-09-16 — Excel/VBA adapter direction decided (owner
conversation, not yet a Task). Confirms and narrows
`proposals/ELNATH-ROTA-ENGINE-INTEGRATION-OPTIONS.md` (branch
`proposal/engine-excel-integration-options`, EXPLORATION ONLY doc,
Variants A-F).

STATUS: finding + owner decisions from a direct conversation, NOT a
design doc, NOT frozen, NOT a TASK_SCOPE. Routed for Codex to confirm
the factual/technical claims below against current repo state, then
for the architect to turn into a real brief. CC has not designed the
API/auth/template shape here.

## Origin

Target user profile (owner's own framing): retired law-enforcement
officers, established Excel workflow, a pendrive is already "the new
thing" for them. Explicit adoption-risk framing: **the software's own
UI is the actual barrier**, not solver quality — "nie ucz użytkownika
Elnath — naucz Elnath jego Excela" (proposals doc, section 2). Owner's
own words on why this matters: without this direction, Rota risks being
"tylko moim programem do szuflady" regardless of how good the solver is.

## Decisions made in this conversation (owner-confirmed, in order)

1. **Direction: proposals doc's Variant D** (Excel remains the user-
   facing surface; Rota is a hidden engine behind it) is the one to
   pursue, not Variant B/A/E/F as the primary path. Matches the
   proposals doc's own section 13 assessment for this user profile.
2. **Technology: VBA, not Office Script.** Confirmed the real target
   machine is classic desktop Excel (a local `.xlsx`/`.xlsm` file, not
   Microsoft 365/Excel Online/OneDrive-SharePoint) — Office Script
   requires the cloud/365 surface and does not fit this profile. This
   was a genuine fork the owner had conflated as "one option"; resolved
   explicitly in-session.
3. **Full functionality, not read-only.** The VBA adapter should both
   read the computed schedule back into the sheet AND be able to
   trigger PLAN/REPLAN against Rota (a "Przelicz" button), not just
   pull a finished result (proposals doc's Poziom 3, not Poziom 2).
4. **Hosting: Rota-as-SaaS on a cloud engine (Railway), reachable from
   the target machine.** Confirmed the target machines have real
   internet/network access (it's a company network, not an air-gapped
   post) — this was checked explicitly because the user profile
   plausibly suggested an offline workstation; it does not apply here,
   so the cloud-engine premise of Variant D/F holds.
5. **Auth: a static access key/token embedded in the workbook, not an
   interactive login flow per use.** The owner did not understand what
   "authenticate" meant operationally; the resolved plain-language
   framing is: Rota issues one key once, the VBA macro sends it silently
   with every request, no username/password prompt on each use.
6. **Template ownership / business-model split.** The owner's own
   company schedule file (referenced in this repo's `Grafiki/`
   directory) is confirmed as the reference for Rota's ONE standardized
   Excel output template — Rota-as-SaaS ships this one template, it does
   not attempt to auto-adapt to an arbitrary pre-existing client file.
   Matching a *different* client's own existing, idiosyncratic
   spreadsheet layout is explicitly scoped as a **separate, billable
   custom-development service**, not part of the core SaaS product.
   This resolves proposals doc section 12, question 7 ("czy integracja
   ma wspierać dowolny arkusz klienta, czy jeden uzgodniony szablon")
   in favor of "jeden uzgodniony szablon" for the SaaS core.

## Facts CC verified against current repo state during this
conversation (Codex: please re-verify independently, exact SHA below)

Verified at `main@63f469f`:

- **Real multi-tenant authentication already exists** for
  `IS_CENTRAL_SERVICE` mode: `api/deps.py` branches on it;
  `api/auth/context.py::get_authenticated_context` resolves a
  server-side `AccountMapping` (per authenticated fastapi-users
  account) to a `db_path` + `coordinator_id`, never trusting a
  caller-supplied identity. This is the T024/T025 Railway-PWA auth
  layer already built — it is a real foundation for "Excel as another
  authenticated client," not a green-field problem. **What does NOT
  exist yet**: a static API-key credential type for this auth layer —
  today's `current_active_user` dependency is fastapi-users' own
  session/cookie-or-bearer-token user model, built for a browser login
  flow, not obviously an issue-once-embed-in-a-workbook key. This gap
  needs explicit architect design, not an assumption that "auth already
  exists" trivially covers decision 5 above.
- **The existing API contract (`api/routers/schedule.py` and friends)
  already returns everything Variant D/F's flow needs as structured
  JSON**: `PlanningResultOut`/`MonthViewOut` with `FEASIBLE`,
  `DECISION_REQUIRED`, `TARGET_HOURS_REQUIRED`, `THIRD_CONSECUTIVE_
  SHIFT_BLOCKED` etc., plus (as of this session) `employees`/
  `delegation_days` roster projection. A VBA client calling PLAN/REPLAN
  would need to handle this same state machine that the React frontend
  already handles — this is real integration surface, not a new one to
  invent.
- **No `.xlsx` export exists today.** `rota/application/
  schedule_export.py` (T020) only produces a PDF via `reportlab`; it
  does contain the reusable logic for decomposing a schedule into the
  printable grid (work codes, absence decomposition, DELEGACJA
  handling) that a `.xlsx` writer could share, rather than
  reimplementing that decomposition a second time.

## Explicitly NOT decided here

- The API-key/credential scheme itself (issuance, storage, revocation,
  how it maps onto the existing fastapi-users `AccountMapping` model).
- The exact `.xlsx` template layout (rows/columns/cells) — the owner's
  `Grafiki/` file is the reference to design FROM, not yet transcribed
  into a frozen cell-by-cell spec.
- Whether the VBA adapter gets a purpose-built, stable "external
  client" API surface, or calls the same internal contract the React
  frontend uses (versioning/stability implications differ materially).
- How VBA should present `DECISION_REQUIRED`/blocker states to the user
  inside Excel (a dialog box? a written cell? this needs its own small
  UX decision).
- Timeline/priority relative to any other in-flight Task.

## Next step

This is architecture-decision scale (new external client class, new
credential type, new export format) — needs Codex to confirm the
"Facts CC verified" section against actual current code (not take it on
faith), then real architect engagement for an actual brief. Not
implemented, not designed in detail, here.
