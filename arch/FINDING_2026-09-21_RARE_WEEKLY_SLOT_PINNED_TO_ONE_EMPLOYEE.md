# FINDING 2026-09-21 — a rare, weekly-recurring demand (e.g. the only Saturday shift in the month) is deterministically pinned to the same employee every month, even when all eligible employees are fully interchangeable

STATUS: finding + reproduced root cause, NOT a design document. Input for
the architect (same role as other `arch/FINDING_*` docs) — CC does not
design the solver-engineering fix here.

DATA: all data is synthetic and created by the owner; "real object" and
"production" here mean a fully assembled site object and the owner's own
running instance, NOT a customer or real personal data. See
`arch/DATA_STATUS.md`.

## The live symptom

Real object "Bolf" (day-shifts-only ORDINARY site): the shift catalog has
a Saturday-only D shift, 9h (`active_weekdays` restricted to Saturday).
Paweł's own report: "program ładnie jej używa ale przypisuje ją na sztywno
do jednego pracownika. Więc jeden pracownik pracuje wszystkie soboty a
drugi w żadną" (the program uses it fine, but pins it to one employee —
one works every Saturday, the other never does). Confirmed with Paweł
directly: both employees have identical roles/eligibility for this shift
— this is not a `required_role_id` restriction or any other legitimate
eligibility gate.

## Reproduced root cause: deterministic CP-SAT tie-break, not a rotation mechanism

Minimal synthetic `PlanningState` (`tests/support/minimal_state.base_state`),
no DB: 2 fully interchangeable LOCAL employees (A, B), identical
`target_hours`, two 12h D demands per month — one on that month's Saturday,
one on an ordinary weekday, both otherwise unconstrained (no HARD rule
distinguishes them; either employee can legally take either demand). Ran
`rota.planning.engine.plan(state)` for 6 consecutive months
(2026-08 .. 2027-01), rebuilding a fresh, independent `PlanningState` each
time (no shared state, no persisted history):

```
2026-08: Saturday demand went to employee B
2026-09: Saturday demand went to employee B
2026-10: Saturday demand went to employee B
2026-11: Saturday demand went to employee B
2026-12: Saturday demand went to employee B
2027-01: Saturday demand went to employee B
```

Employee B, every single month, with zero variation. This exactly
reproduces the live symptom in isolation.

**Why**: `rota/planning/solver.py`'s first-attempt solve always uses
`solver.parameters.random_seed = 0` and `randomize_search = False`
(`search_attempt=0` — only "Szukaj dalej" retries vary this). Each month's
model is built fresh and is *structurally symmetric* between A and B for
this pair of demands — nothing in the objective distinguishes "give
Saturday to A, weekday to B" from "give Saturday to B, weekday to A"; both
cost exactly the same under every fairness term:

- `add_target_equity_fairness`/TARGET-01: identical total hours either way
  (both employees end at `target_hours`).
- `add_weekend_fairness` (`rota/planning/fairness.py`): computes
  `max(weekend_hours) - min(weekend_hours)` **within one month**. With
  only one weekend demand that month, exactly one employee gets weekend
  hours no matter which one — the spread is the same (12h vs 0h) either
  way. This term cannot express "but not the *same* employee as every
  other month" — it has no memory of prior months at all, and by design
  (SOFT, monthly) isn't meant to.

With the model genuinely tied on every term, CP-SAT's deterministic
default (fixed seed, no randomization) resolves the tie the same way
every time — almost certainly driven by variable/branching order tied to
`employee_id` iteration order, not intentional load-bearing logic. Because
each month's model has the same structure and the same employee set, the
same tie gets broken the same way every month, forever.

## What this does NOT affect

- `add_weekend_fairness` and `add_target_equity_fairness` themselves are
  not wrong — they correctly minimize their own declared, single-month
  objectives. There is currently **no term at all** whose job is
  cross-month rotation of *which specific employee* covers a rare,
  calendar-pinned recurring slot (as opposed to aggregate hours).
- This is not a `required_role_id`/eligibility bug — confirmed directly
  with Paweł that both employees are equally eligible.
- Not specific to Saturdays or to 9h shifts — reproduced with a generic
  12h D demand. Any demand shape that recurs on a fixed weekly cadence
  with only one eligible slot per month, in an otherwise-symmetric
  employee pool, will exhibit the same pinning.

## Open question for the architect (CC does not design this)

There is no existing state or term in the model that looks across months
at "who covered this recurring slot last time" — `add_weekend_fairness`
is explicitly monthly/SOFT and was never meant to do this. Candidate
directions, none evaluated/chosen here:

- A genuine cross-month rotation term/constraint: something needs to read
  *which employee* (not just how many hours) covered comparable slots in
  recent prior months and penalize repeating the same one, when multiple
  employees are otherwise equally eligible. This is a new kind of input
  (identity-level history, not just hours) that today's `WorkBalance`/
  historical-hours plumbing doesn't carry.
- Alternatively, break the CP-SAT symmetry deliberately (e.g. rotate
  employee iteration order per month, or seed from month) so at least the
  outcome isn't *permanently* pinned — weaker than real rotation (still no
  guarantee of an even spread over time) but far cheaper than adding
  identity-aware history.
- Scope question for the architect/owner: is this worth solving generally
  for any rare recurring slot, or narrowly for weekend-shaped demands
  (`add_weekend_fairness`'s own domain)?

CC's recommendation, stated plainly (not a decision): the reproduction
above is small, deterministic, and DB-free — an architect/Codex round can
iterate directly against it without needing to reconstruct Bolf's real
data.

## Reproduction

Script (not committed — throwaway, scratchpad-only): 2 employees via
`tests/support/minimal_state.base_state`, identical `target_hours`, two D
demands per month (one on that month's first Saturday, one on an ordinary
weekday), `rota.planning.engine.plan(state)` called independently per
month across 6 consecutive months. No DB writes, no persisted state
shared between runs — trivially rebuildable as a proper test if the
architect wants it committed.
