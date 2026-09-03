# FINDING 2026-09-03 — no single, app-wide "working month" control; four
screens each pick the current calendar month independently.

STATUS: finding + verified current-state map, NOT a design doc, NOT
frozen. Architect-input material — CC does not author the implementation
brief here. Backlog memory item 7 (2026-09-01, re-raised 2026-09-03).

## Origin / requirement

Paweł, raised twice on two different days with the same complaint, no new
detail the second time:

> mamy w programie kilka miejsc gdzie trzeba zaznaczać jakiego miesiąca
> dotyczą zmiany. Domyślnie jest ustawiony bieżący miesiąc. Potrzebuję by
> w jednym miejscu koordynator mógł ustalić miesiąc na jakim pracuje, np
> październik i żeby nie musiał wszędzie ustawiać go ręcznie. Jedno
> kliknięcie październik ustawia cały program pod pracę na październik.

A UI/UX gap, not a backend defect or a solver question.

## Verified current state (read, not guessed)

Exactly four screens each maintain their own, fully independent month
picker, all defaulting to the current calendar month:

- `frontend/src/screens/MonthlyPlanning.tsx:169-175` —
  `currentYearMonth = todayIso().slice(0, 7)`, own `monthInput` state, own
  local `firstOfMonthIso` helper (duplicated verbatim, see below).
- `frontend/src/screens/Analytics.tsx:72-74` — same pattern, own
  `monthInput` state, own copy of `firstOfMonthIso`.
- `frontend/src/screens/Export.tsx:43-45` — same pattern, own `monthInput`
  state, own copy of `firstOfMonthIso`, plus a derived `periodLabel` state.
- `frontend/src/screens/EmployeeDetail.tsx` — has its own
  `type="month"` picker too (not read in detail this pass).

`firstOfMonthIso` (the `"YYYY-MM"` input → first-of-month ISO date
converter) is a small, identical, hand-copied function defined separately
in `MonthlyPlanning.tsx:9`, `Analytics.tsx:8`, and `Export.tsx:12` — three
independent copies of the same few lines, itself a small duplication
symptom of the same root problem.

`Decisions.tsx` is a different shape and likely NOT part of the same fix:
it lists only the specific months that actually have a pending
`DECISION_REQUIRED` (`api.getDecisionMonths`), as clickable chips — there
is no "current month" default to override there.

## A promising existing shape, not yet a design

`frontend/src/screens/Room.tsx` is the shell that renders every screen
(`MonthlyPlanning`, `Decisions`, `Analytics`, `History`, ...) as children
and already lifts OTHER cross-screen state up to itself precisely this
way — e.g. `activeNav` (line 52), `controlPanelTab` (line 56),
`decisionContext` (line 62) all live in `Room.tsx` and get threaded down
as props. A shared "working month" living in `Room.tsx` and passed to the
four screens above would follow an already-established, precedented
pattern in this codebase rather than inventing a new one — noted as a
promising shape to start from, not a decision to build it that way.

## Explicitly open, not decided here

- Does every one of the four screens ALWAYS defer to the global month, or
  does any of them have a legitimate reason to look at a different month
  temporarily (e.g. comparing two months side by side) that a hard global
  override would break? Not checked — needs a real per-screen
  function-list pass before designing, per the standing rule that UI
  changes get a function list pinned before any mockup/implementation.
- Where does the global month selector itself live in the UI (a new
  top-level control in `Room.tsx`'s header/sidebar? part of an existing
  screen?) — not decided.
- Whether "Wydruk"/Export's separate `periodLabel` (a human label distinct
  from the month itself, e.g. "Sierpień 2026") stays independently
  editable or also derives from the global month.
- Whether this should absorb [[project_screen_consolidation_proposal]]'s
  broader 5-screens-to-2 discussion or ship independently first.

## Scale note

Smaller than backlog items 6/11/12 in this batch: no solver/domain-model
change, no new backend concept — purely a frontend state-lifting exercise
following a pattern this codebase already uses elsewhere. The real open
question is UX design (where the control lives, whether any screen is a
legitimate exception), not engine feasibility.

No brief.md/TASK_SCOPE exists for this finding. Next step is Paweł's
decision on relaying to architect Claude.
