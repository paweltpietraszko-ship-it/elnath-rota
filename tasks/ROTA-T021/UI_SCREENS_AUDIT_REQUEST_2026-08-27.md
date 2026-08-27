# Codex audit request — T021 screens: does the frontend actually click through what the backend audit assumed?

STATUS: request for an independent audit, not yet run. Plain findings back
to Paweł/CC, same discipline as every other round on this repo — file:line
evidence, no fix proposals, PASS/WYMAGA_DECYZJI/FAIL verdict only if that's
useful, otherwise a plain findings list for us to triage.

## Why this round exists

Five new nav screens were implemented today on `task/ROTA-T021-analityka`
(exact HEAD `c7656dcdb00309d5f0b8766264ef2aca96c87cac` — verify against
`git log -1 task/ROTA-T021-analityka` before starting, in case it moved):
Przegląd, Decyzje koordynatora, Historia i audyt, Analityka i bilanse,
Wydruk Grafiku. Each has its own backend router
(`api/routers/{overview,decisions,history,analytics,export}.py`) and its
own React screen (`frontend/src/screens/{Overview,Decisions,History,
Analytics,Export}.tsx`), wired into `frontend/src/screens/Room.tsx`'s nav.

Every backend endpoint was individually tested (`tests/test_t021_*.py`,
21+ tests, all green) and smoke-tested live against the real dev DB. What
has NOT been independently checked: whether the **frontend code that
actually renders and calls these endpoints** matches what those backend
tests assumed — field names, enum values, required vs optional params,
what a button actually sends versus what the screen's spec says it should
send. A backend-only audit can pass while the two sides have quietly
drifted (e.g. a frontend field renamed after the backend test was written,
an enum value spelled differently client-side, a button wired to the wrong
endpoint, a response field the UI silently ignores).

## Task for Codex

For each of the 5 screens, do BOTH of the following:

**A. Static wiring trace (always do this part).** For every clickable
action, form field, and rendered data field in the screen's `.tsx` file:
1. Trace it forward through `frontend/src/api/client.ts` to the exact
   backend endpoint (method + path) it calls, and the exact request body
   shape it sends.
2. Compare that against the endpoint's actual Pydantic request/response
   models in the matching `api/routers/*.py` file — field names, types,
   optionality, enum value spellings must match exactly on both sides.
3. Cross-check the screen's full set of displayed fields/actions against
   `arch/T021_spec.md`'s function list for that screen (§Przegląd,
   §Decyzje koordynatora, §Historia i audyt, §Analityka i bilanse,
   §Wydruk Grafiku) — flag anything the screen shows/does that isn't in
   spec (invented), and anything spec requires that the screen doesn't
   actually wire up (missing), even if it's visually present but a dead
   button.

**B. Real click-through, if you have that capability.** If you can drive
a real browser (Playwright/similar) against a running instance, do it —
report explicitly whether you did or didn't have this capability, don't
just silently skip it. If you can:
1. Start/use the backend (`uvicorn api.main:app`) and frontend (`npm run
   dev`, Vite) dev servers against a real or seeded SQLite DB.
2. For each of the 5 screens, actually click through its primary actions
   (open the screen, change the month/filter where applicable, trigger at
   least one write action where one exists — e.g. save print settings,
   export a PDF, expand a quarter breakdown, expand an action's detail)
   and report what actually rendered/happened versus what the code and
   spec claim should happen.
3. Specifically compare your own findings from part A (the static
   contract you traced) against what you observe really happening at
   runtime — report any place where the two disagree (this is the
   category that matters most this round: static trace says X, but the
   browser shows Y).

## Known context, don't re-derive

- `arch/T021_spec.md` sections for these 5 screens are the frozen,
  current source of truth (§Przegląd, §Decyzje koordynatora, §Historia i
  audyt, §Analityka i bilanse, §Wydruk Grafiku).
- No new backend business logic was added except one small application
  wrapper, `durable_inputs.save_print_settings` (Wydruk Grafiku's save
  side) — everything else composes pre-existing, unchanged application
  functions.
- Per spec's own anglicism rule, all 18 `CoordinatorActionKind` values and
  the 3 `rel` values have hand-written Polish labels in `History.tsx`
  (`ACTION_KIND_LABEL`/`REL_LABEL`) since no server-side Polish text
  exists for them — check these are complete (all 18 present) and that no
  raw English enum value can leak to the screen unmapped.
- `Decisions.tsx`'s `unblocking_options` → screen navigation mapping is
  explicitly fragile prefix-matching on free-text strings (see the
  function's own comment) — check it fails safely (falls back to plain
  text) rather than crashing or mislinking when the backend's wording
  doesn't match a known prefix.

## Scope

Include: `frontend/src/screens/{Overview,Decisions,History,Analytics,
Export}.tsx`, `frontend/src/screens/Room.tsx` (nav wiring only),
`frontend/src/api/client.ts` (the parts touching these 5 screens),
`api/routers/{overview,decisions,history,analytics,export}.py`,
`arch/T021_spec.md` (the 5 relevant sections), `tests/test_t021_*.py` (as
evidence only, not to be re-run wholesale — these already pass).

Exclude: the already-built Panel sterowania / Planowanie miesiąca screens
and their routers (out of scope, unchanged today); `rota/application/**`
and `rota/persistence/**` internals beyond the one new wrapper named
above (already unit-tested, not this round's concern); Ręczna korekta
(not built yet, separate future task).

## Output format

Plain findings, file:line evidence on both the frontend and backend side
for each. State explicitly, at the top, whether part B (real click-
through) was performed or not and why. No fix proposals — that's for
Paweł + CC after this comes back.
