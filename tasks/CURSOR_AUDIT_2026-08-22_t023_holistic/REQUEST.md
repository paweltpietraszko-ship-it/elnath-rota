# Cursor audit request — ROTA-T023 holistic review (2026-08-22)

STATUS: request for an independent scan, not yet run. Output goes back
through CC for verification against source (same discipline as
`tasks/CURSOR_AUDIT_2026-08-21/FINDINGS_VERIFIED.md` and
`tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`) before
anything here is trusted or acted on.

## Context

ROTA-T023 ("schedule-based absence hours accounting") just merged to
`main` after three checkpoints (A: provenance/write-time capture, B:
WorkBalance/solver/analytics/REPLAN cutover, C: T020 PDF presentation),
each independently audited round-by-round by a separate Codex instance
against `tasks/ROTA-T023/brief.md` and
`arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`. That
process was narrow and adversarial by design — each round targeted one
or two specific findings. This request is the opposite shape: a single
wide pass looking for anything that narrow process structurally couldn't
catch.

**Do not re-derive or re-run the existing T023 test matrix.** Every
`test_t23_*`/`test_t20_*` id in `tasks/ROTA-T023/brief.md` section 17 and
every file under `tests/test_t023*.py`, `tests/test_t020.py`,
`tests/test_t018.py`, `tests/test_sick_leave.py`,
`tests/test_balance.py`, `tests/test_t019.py`, `tests/test_t019b.py`,
`tests/test_t012.py`,
`tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py`,
`tasks/ROTA-T023/round_01/tests/*.py` is already covered ground — reading
them for context is fine, reporting a gap they already close is not
useful here.

## Task for Cursor

Three independent angles. Report each separately; don't try to unify
them into one narrative.

### A. IMPLEMENTATION GAPS ACROSS CHECKPOINTS A/B/C

Read the full frozen contract (`tasks/ROTA-T023/brief.md` +
`arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`) end to
end, then read the actual implementation:
`rota/planning/absence.py`, `rota/persistence/absence_reference_repository.py`,
`rota/balance.py`, `rota/persistence/work_balance_repository.py`,
`rota/application/analytics_read.py`, `rota/application/balance_read.py`,
`rota/planning/solver.py`, `rota/application/plan_ops.py`,
`rota/application/schedule_export.py`, `rota/application/durable_inputs.py`.

Report:
- Any contract sentence (brief.md or the frozen addendum) that the code
  doesn't actually implement, or implements differently than written.
- Any code path reachable in production that no existing test in the
  files listed above under "do not re-derive" actually exercises —
  name the exact function/branch and why it looks untested.
- Any residual use, anywhere in `rota/`, of the pre-T023 flat-8/
  CalendarDay mechanism (`EXCUSED_ABSENCE_HOURS_PER_DAY`,
  `excused_absence_days_in_month`, `IncompleteAbsenceCalendarError`)
  outside the one place it's explicitly frozen as the preserved
  PRE_PLAN_LEAVE source (`rota/planning/absence.py`'s own legacy
  function plus `rota/application/schedule_export.py`'s PRE_PLAN
  decomposition path). If you find one, name file:line and say which
  frozen-addendum clause it should have been retired under.
- Any inconsistency between how Checkpoint A (capture), Checkpoint B
  (WorkBalance/solver/analytics) and Checkpoint C (T020) each read or
  interpret the same `DailyAbsenceFact`/`DayReference`/`PeriodFact`
  shape — e.g. one consumer trusting a field another consumer treats as
  untrustworthy, or duplicate precedence/decomposition logic that
  should have stayed in one owner module (frozen addendum section 11:
  "Consumers do not choose source mode from CURRENT and do not
  reimplement SICK/LEAVE precedence, anchor rules or Site filtering").

### B. LABOR-LAW COMPLIANCE FOR PRIVATE SECURITY GUARDS ("ochrona")

The product's real users are Polish private security firms
(`Grafiki/` contains real ROYALPACK/APEXIM guard schedules — 12h and
24h shifts are the norm, not the exception). Compare what the code
actually encodes as legal/illegal against **current** Polish labor law
for this sector — Kodeks pracy (rest periods: 11h dobowy, 35h
tygodniowy, night-work definition and limits, work on Sundays/holidays)
and any sector-specific provisions for private security under ustawa o
ochronie osób i mienia and związane rozporządzenia.

Ground every claim in the actual code, not just the brief:
- `rota/planning/eligibility.py`, `rota/planning/constraints.py`,
  `rota/planning/work_periods.py` (24h/rest/legality rules — T012's own
  domain, out of T023's own TASK_SCOPE, so this is genuinely
  independent territory).
- The frozen 24h legend in `rota/persistence/site_repository.py`
  (`FROZEN_WORK_CODE_HOURS`) and whether the hour values it treats as
  legal shift lengths and the rest-hour assumptions elsewhere in the
  codebase are still accurate against current law (cite the specific
  provision and its current text/date, not a remembered summary — law
  changes; say plainly if you can't verify currency).
- T023's own absence-hours model itself: does treating SICK_LEAVE/
  LEAVE_GRANTED as reducing live TARGET the way brief.md section 11
  specifies match how Polish law actually treats sick leave (L4) and
  granted leave (urlop) for compensation/scheduling purposes, or does
  it conflate two legally distinct absence categories?

Where you're not certain current law text, say so explicitly rather
than asserting a compliance verdict — a flagged uncertainty is more
useful here than a confident guess.

### C. VERTICAL INTEGRATION WITH THE REST OF THE PROGRAM

Trace one absence end to end, from the coordinator's actual write
through every downstream consumer, and report any place the chain is
broken, bypassed, or duplicated:

`rota/application/durable_inputs.py::append_availability` →
`rota/persistence/absence_reference_repository.py` (capture) →
`rota/persistence/work_balance_repository.py` (WorkBalance) →
`rota/application/analytics_read.py` (coordinator analytics screen) →
`rota/planning/solver.py` (TARGET-01 objective) →
`rota/application/schedule_export.py` (printed PDF) →
and back upstream into `rota/application/plan_ops.py::select_candidate`/
`replan` (R5-3 cutover) and `rota/application/assembler.py`
(`_assemble_work_balances`, `assemble_planning_state` — how
`PlanningState.work_balances` actually reaches the solver in a real
`plan_month()`/`replan()` call).

Report:
- Any application-layer entry point (`rota/application/*.py`) that
  reads Availability, WorkBalance, or absence data but does NOT go
  through the canonical path above — i.e. a second, parallel read of
  the same facts.
- Any place `assemble_planning_state`/`_assemble_work_balances` could
  raise `IncompleteAbsenceReferenceError` (or `MissingTargetHoursError`)
  uncaught and block `plan_month()`/`select_candidate()`/`replan()`
  entirely for a whole Site/month — this was flagged once already
  during T023 Checkpoint B (see `tasks/ROTA-T023/brief.md` DELIVERY
  history / owner ruling section, "assembler.py note") and explicitly
  ruled NOT A FINDING by Codex under T023 (fail-closed is required
  behavior) — don't re-flag that same conclusion, but DO check whether
  there's a *different*, not-yet-considered call site with the same
  shape that only a whole-program trace would surface.
- Any UI/coordinator-facing read path (if one exists yet — check
  `arch/T021_spec.md` and whatever of `rota/application/` it actually
  wires to) that would show stale or wrong absence data because it
  reads WorkBalance/Availability some other way than the canonical
  chain above.

## Scope

Include: `rota/**`, `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`,
`tasks/ROTA-T023/brief.md`, `arch/T021_spec.md` (context only, for part
C), `Grafiki/` (context only, for part B — real shift patterns).
Exclude: everything already listed under "do not re-derive" above,
`benchmarks/**`, `tasks/**` other than the one brief.md named.

## Output format

Same shape as the two prior Cursor audits: plain findings with
file:line evidence, one paragraph each, no fix proposals, no PASS/FAIL
or priority verdict — that's Paweł + architect's call after CC verifies
each finding against source.
