# FINDING 2026-09-03 — a computed PLAN candidate has no persisted trace
until accepted; navigate away or reload and it is gone with no way back
except re-running PLAN.

STATUS: finding + verified current-state map, NOT a design doc, NOT
frozen. Architect-input material — CC does not author the implementation
brief here. Backlog memory item 8 (2026-09-01).

## Origin / requirement

Paweł hit this live on site "Royal": ran PLAN, got a result, had not yet
accepted it, wanted to look at it from elsewhere and it was not there.

> miał być podgląd grafiku nie wiem czy jest w planach czy już zrobiony...
> jestem na obiekcie Royal i jeszcze nie zaakceptowałem grafiku więc go
> nie ma na podglądzie. To bez sensu, bo on gdzieś powinien być jako
> zaplanowany nie potwierdzony z możliwością podglądu.

## Two possible sources of confusion, both checked and ruled distinct

- **The existing "Podgląd" (T041, `tasks/ROTA-T041/brief.md`)** is a
  different feature entirely: a PDF preview of an ALREADY-accepted/
  current schedule export, byte-identical to the download. It has nothing
  to do with a pre-acceptance candidate — it cannot show something that
  was never accepted, by design.
- **`frontend/src/screens/MonthlyPlanning.tsx`'s inline candidate
  display** (verified by reading the code, not assumed): a `FEASIBLE` PLAN
  result's candidate(s) render directly from `planResult`, a plain React
  state variable set by the last `api.planMonth`/`api.replanMonth` call
  (lines 339-372, 866-905) — rendered as a `ScheduleGrid` with an
  "Zatwierdź ten grafik"/"Wybierz ten wariant" button
  (`chooseCandidate` → `api.selectCandidate`, line 368-372). This is
  **pure client-side memory, never written to the database.** No
  `ScheduleVersion` row (no `WORKING`-status entry) exists until the
  coordinator actually clicks accept.

## Confirmed consequence

Navigate to another screen, reload the page, or simply come back later
before accepting, and the computed candidate is gone with **no persisted
trace anywhere.** Re-running PLAN is the only way back, and — depending on
the solver's search state/randomness — nothing guarantees it reproduces
the exact same candidate the coordinator was looking at.

`ScheduleStatus` (`rota/domain.py:85-89`) has exactly four values:
`WORKING`, `WORKING_WITH_DEVIATIONS`, `FINAL_NO_DEVIATIONS`,
`FINAL_WITH_DEVIATIONS` — there is no "computed, not yet accepted" state
anywhere in the lifecycle. No mention anywhere in `arch/` of such a state
ever being planned. This looks like a genuine, previously-undocumented
gap, not a rediscovery of existing scope.

## Explicitly open, not decided here

- Whether the fix is a genuinely new, persisted `ScheduleStatus` value
  (e.g. a "PLANNED, not yet confirmed" row that a later accept/discard
  transitions out of) or simply surfacing/persisting the raw PLAN response
  somewhere durable without touching `ScheduleStatus`'s own state machine
  at all — these are very different sizes of change and neither has been
  evaluated.
- If a new persisted state is introduced: how it interacts with REPLAN,
  with multiple coordinators/sessions, with the existing "Historia wersji"
  list, and with `excludeVersionFromHistory`/`restoreVersion`.
- Whether this should support comparing multiple not-yet-accepted
  candidates (today's `planResult.candidates` can already have more than
  one) or only ever the single most recent PLAN result.
- Whether a lighter-weight fix (e.g. only warn the coordinator before
  navigating away with an unaccepted candidate still in memory) would
  address the actual pain point without a persistence-layer change at
  all — not evaluated, worth considering given the scale gap between the
  two options above.

## Scale note

Touches `ScheduleStatus`/`ScheduleVersion` lifecycle semantics — a core,
already-audited state machine (multiple prior Tasks reference its exact
four-value shape) — genuinely architect-level, not a screen tweak, per the
standing rule that lifecycle/contract changes get the full process.

No brief.md/TASK_SCOPE exists for this finding. Next step is Paweł's
decision on relaying to architect Claude.
