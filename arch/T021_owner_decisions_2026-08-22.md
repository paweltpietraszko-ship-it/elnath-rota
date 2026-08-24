# T021 — owner rulings, 2026-08-22 (post-brief conversation with Paweł)

Resolves D1-D4 from `arch/T021_post_round1_architect_brief_2026-08-22.md`
section 3, plus the frontend stack choice. Recorded verbatim from the
conversation, not inferred.

## D1 — calendar/holiday editing

RULING: in scope, whole UI (applies to all Sites). Confirmed against
code: `CalendarDay(date, holiday)` has no `site_id` field at all,
`set_calendar_day` already invalidates every Site when a holiday
changes — this matches a national/public holiday calendar, not a
per-Site concept. Paweł confirmed this is the intended meaning (not
asking for per-Site closures, which don't exist in the domain today).
No further backend work needed here; just needs a screen (placement
still TBD by whoever writes the consolidated contract).

## D2 — SiteProfile policy toggles: REMOVED FROM SCOPE, not deferred

RULING: none of the four remaining toggles become a coordinator-facing
control in T021 or ever. Reasoning given directly by Paweł:

- **`training_s_enabled`/`training_s_weekdays_only`/
  `training_s_default_readiness_threshold`** — "To nie program decyduje
  czy, kiedy i ile szkoleń ma przejść pracownik, tylko koordynator...
  program ma to lekceważyć." (The program does not decide whether/when/
  how many trainings an employee needs — only the coordinator does; the
  program should disregard this.) Confirmed compatible with existing
  code: `mark_training_realized`'s auto-promotion hook
  (`rota/application/training.py:99`) only runs while
  `readiness_source == DEFAULT`; the moment a coordinator sets
  `readiness_source=COORDINATOR_OVERRIDE` (already-existing
  `update_membership` capability), the automatic counter never touches
  that membership again. **Implementation consequence**: the
  per-employee S/szkolenie control in T021 must always write through
  `COORDINATOR_OVERRIDE`, never rely on the automatic counting path.
  **Fixed constant at Site-creation time: `training_s_enabled = False`**
  (turns the automatic mechanism off entirely; makes
  `training_s_weekdays_only`/`training_s_default_readiness_threshold`
  moot — no UI needed for either).
- **`external_support_enabled`** — "Na każdym obiekcie, przy złym
  obrocie sprawy może być potrzebne wsparcie zewnętrzne, więc przycisk
  jest niepotrzebny." (Every Site might need external support in a bad
  situation, so the toggle is unnecessary.) **Fixed constant:
  `external_support_enabled = True`** always — never blocks.
- **`day_only_blocks_n`** — "Blokowanie day_only_blocks_n też jest bez
  sensu." **Fixed constant: `day_only_blocks_n = True`** always — this
  one must stay `True` (not `False`) because it is what makes the
  existing per-employee `day_only`/"Nocka" checkbox actually mean
  something; `False` would silently make that checkbox a no-op.

All four values get set once, hardcoded, wherever `SiteProfile` is
constructed (the "+ Nowy obiekt" bootstrap flow, `T021_spec.md:393-407`)
and never exposed as a coordinator-facing control anywhere. This closes
D2 completely — it is not a "read-only for now" deferral, it is
permanently out of the UI.

## D3 — Site editing (display_name/active)

RULING: in scope, now. No further discussion needed — confirmed
directly.

## D4 — "+ Nowy obiekt" flow

RULING: confirmed, matches `T021_spec.md:393-407`'s "DECIDED + BUILT"
description (workspace inline form, 3-field minimal creation). The
contradiction flagged by the architect brief (one doc said open, one
said decided) is resolved in favor of "decided" — proceed on that
basis.

## Frontend stack

RULING: **React + TypeScript + Vite**, not Next.js. Reasoning from the
conversation (all confirmed against T025's actual constraints):

- This is an internal, login-gated coordinator tool, not a public/SEO
  surface — Next.js's core value proposition (SSR/SEO/ISR) buys
  nothing here.
- Real business logic (`rota/planning`, `rota/application`) stays in
  Python on the server regardless of frontend framework — Next.js
  "API routes"/server components would only be a thin proxy to that,
  not real work done in JS.
- Next.js needs a live Node server process in production (SSR); Vite
  produces a static bundle, simpler/cheaper to host on Railway.
- Vite's PWA plugin (`vite-plugin-pwa`) is mature; Next.js PWA support
  is comparatively rough, especially under the App Router.
- Matches the Continuity AI reuse pattern (`arch/spec.md`'s REUSE/ADAPT
  section already assumed Vite+React+TS; only the Tauri-specific bridge
  IPC layer is dropped for the web target).

**Distribution-protection tangent, resolved**: Paweł asked whether the
Railway/PWA move (whose whole point per T025 is "don't hand the tester
my code, hand them a running program") is undermined by either
framework choice. Answer given and accepted: neither Vite nor Next.js
solves that — a shipped client-side JS bundle is inspectable via
browser devtools in ANY web framework, no exception. The actual
protection is architectural, not a framework pick: the valuable logic
(solver, eligibility, validators) never leaves the Python server at
all; the browser only ever gets a thin UI/API-calling shell. Real
protection stays what T024 already named: NDA (L1), gated
login/invitation before a tester ever reaches a URL, server-side
account expiry (L3), minified production build (both frameworks do
this by default) — not a frontend-framework decision.

## Net status

D1-D4 all closed. Frontend stack decided. Nothing here is a "wait for
architect" item anymore — these were resolved directly with Paweł in
conversation, live, per his stated preference over the multi-round
architect handoff for this specific batch of decisions. The
`tasks/ROTA-T021/brief.md` consolidated implementation contract can now
be written incorporating these rulings as settled fact, not open
questions.
