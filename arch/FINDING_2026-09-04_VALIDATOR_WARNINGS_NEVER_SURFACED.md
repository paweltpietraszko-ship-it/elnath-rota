# FINDING 2026-09-04 — `validate()`'s independent-validator warnings are computed and then discarded everywhere; no coordinator ever sees them

STATUS: finding + verified current-state map, NOT a design doc, NOT frozen.
Architect-input material — CC does not author the implementation brief
here. Surfaced during ROTA-T052 implementation (S1 periodic training) when
OWNER (2026-09-04) decided a real REST-01/WEEKLY-REST-01 violation around
S1 must produce a SOFT warning, never a HARD block — building that warning
correctly is what exposed this.

## Origin / requirement

Paweł, after seeing the S1 SOFT-warning mechanism explained: "to w takim
razie jest to sprawa do całościowego naprawienia taskiem. nie możemy mieć
martwych ostrzeżeń" (this needs a proper Task to fix comprehensively — we
cannot have dead warnings).

## Verified current state (read, not guessed)

Two entirely separate, unconnected warning mechanisms exist in this
codebase:

**1. Solver-side, narrow, working.** `rota/planning/solver.py::_collect_warnings`
runs once per PLAN/REPLAN, checks exactly one thing (an employee's prior N
carrying them into a day-off until 05:00 -> `DAY_SHIFT_OFF-01 SOFT`), and
its own docstring says the sibling `LEAVE_PLAN-01 SOFT` check was
deliberately *moved out* of this function into the validator "to avoid
duplicating the warning" (R17-4) — implying the intent was for the
independent validator to be the one true source, with this solver-side
list either retired or merged later. That never happened. This list
reaches the coordinator today: `PlanningResultOut.warnings` (built in
`rota/application/plan_ops.py:174,200` as `assembler_warnings +
result.warnings`) is returned to the frontend and rendered as the "Uwaga:"
banner in `MonthlyPlanning.tsx`.

**2. Independent-validator-side, broader, dead.** `rota/planning/validator.py::validate()`
builds its own `warnings: list[str]` from four checks:
- `_check_day_only` → `DAY_ONLY-N-FALLBACK-01 SOFT`
- `_check_day_shift_off` → `DAY_SHIFT_OFF-01 SOFT` (a **second**,
  independent implementation of the same rule #1 above already covers)
- `_check_leave_plan` → `LEAVE_PLAN-01 SOFT`
- `_check_rest` / `_check_weekly_rest` → `REST-01 SOFT` / `WEEKLY-REST-01
  SOFT` (new, added by the T052 OWNER correction, S1-only for now)

`IndependentValidationReport.warnings` carries this list out of `validate()`.
Confirmed by reading every call site:
- `rota/application/plan_ops.py:361` (`select_candidate`) — calls
  `report = validate(state, for_validation)`, then reads only
  `report.hard_pass` / `report.violations`. `report.warnings` is never
  touched again in that function.
- `rota/application/manual_edit.py:310` (`apply_manual_correction`) —
  calls `report = validate(state, corrected_assignments)`, then reads
  `report.violation_details` (via `materialize_deviations`) and
  `report.violation_details` again (via `_rest_override_pairs`/
  `_weekly_rest_override_facts`). `report.warnings` is never read.

No other production caller of `validate()` exists. This list is computed,
in full, on every manual correction and every candidate selection, and
discarded every single time. It reaches no API response, no persisted
record, no UI.

## Why this isn't a one-off gap

The solver-side docstring's own admission ("moved to validator... to avoid
duplicating") shows this was already noticed once and partially addressed
in the wrong direction — logic was consolidated into the validator, but
the validator's output was never wired up, so the *old* solver-side
warning (rule #1) is the only one that actually works, purely because it
was never migrated. A rule added straight to the validator (`_check_leave_plan`,
and now S1's REST-01/WEEKLY-REST-01 SOFT) inherits total silence by
default. This will keep happening to every future SOFT rule unless the
validator's warning channel itself gets wired to a response, not each
rule individually.

## Scale note / what a fix needs to decide

Not decided here, flagged for the architect/OWNER:
- Where should `report.warnings` surface for `select_candidate`
  (`api/routers/schedule.py`) and `apply_manual_correction`
  (`api/routers/manual_edit.py`)? Both currently discard it; both would
  need a new response field.
- Should it also be visible on a plain month reload (`rota/application/open_month.py`
  / `MonthViewOut`), not just transiently in the one response right after
  the write that produced it? That's the harder half — it means either
  re-running `validate()` on every GET, or persisting the last computed
  warning set somewhere.
- Should the solver-side `DAY_SHIFT_OFF-01 SOFT` duplicate in
  `solver.py::_collect_warnings` be retired once the validator's version
  reaches the same UI, per the original R17-4 intent, or is duplication
  now acceptable/harmless?
- Does every existing SOFT warning (`DAY_ONLY-N-FALLBACK-01`,
  `LEAVE_PLAN-01`) get surfaced at once, or does this ship incrementally
  (S1's `REST-01 SOFT`/`WEEKLY-REST-01 SOFT` first, since that's the one
  with an explicit OWNER instruction behind it)?

No brief.md/TASK_SCOPE exists for this finding. Next step is Paweł's
decision on relaying to architect Claude for a dedicated Task.
