# FINDING 2026-09-20 — target equity is too weak to pick an even split when target_hours is structurally unachievable for everyone (verified, root-caused, not a hard-constraint limit)

STATUS: finding + reproduced root cause, NOT a design document. Input for
the architect (same role as other `arch/FINDING_*` docs) — CC does not
design the solver-engineering fix here.

Paweł's own framing of the stakes: "bez prawie równego podziału Rota jest
do wyrzucenia" (without a near-equal split, Rota is worthless) — this is
core product correctness, not a side matter, same category as the T058
equity finding below it in this same directory.

## The live symptom

Real object "Royal" (`SITE-f28eb4dea28047e98821e6b0167b9eb2`), October 2026,
6 LOCAL employees, all with an EQUAL `target_hours = 176` and zero
absence/DELEGACJA this month. `Planowanie miesiąca` produced a candidate
with per-employee totals ranging from 84h to 157h (one employee's total
included a separate, already-fixed +1h DST display bug, unrelated to this
finding — real shift hours were 84h to 156h, a 72h/6-shift spread).

## First hypothesis, tested and DISPROVED: the 2026-09-15 EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE change

Owner's initial hypothesis: this regressed when `task/ROTA-EQUAL-SPLIT-
FALLBACK-IGNORES-ABSENCE` (merged `main@e77b9d3`, 2026-09-15) removed the
old incomplete-target-vector fallback (`add_equal_split_fairness`,
formerly in `rota/planning/fairness.py`) and made `target_hours`
mandatory for every active LOCAL membership before PLAN/REPLAN can run.

**Disproved by reading the removed function's own docstring** (git history,
`5965ef8^:rota/planning/fairness.py`): "fallback used only for a solve
whose target vector is incomplete (at least one available LOCAL employee
has no target_hours for the month)". Royal's target vector was already
COMPLETE (176h × 6) — this fallback would never have activated for this
scenario even before 2026-09-15. Reverting that change would have zero
effect here.

Further: the old fallback and the current `add_target_equity_fairness`
use the mathematically identical mechanism (minimize `max - min` of a
per-employee CP-SAT int var via `add_max_equality`/`add_min_equality`) —
raw hours for the old one, `floor(100*worked/target)` for the current
one. With every target equal, these are equivalent up to a constant
scale factor. There is no reason to expect the deleted function would
have behaved differently here.

## Second hypothesis, tested and CONFIRMED: `TARGET_EQUITY_WEIGHT` is real but not effective at picking the most-even tie

`rota/planning/solver.py::_add_combined_objective`'s TARGET-01 term is
`target_weight * (pos + neg)` where `worked - target = pos - neg` per
employee. Because ShiftDemand coverage is HARD (every demand slot must be
filled), **total worked hours across all employees is a fixed constant**
regardless of how the total is distributed among them. Where nobody
exceeds target (true for all 6 here), `sum(target - worked)` is therefore
also a fixed constant, independent of distribution — TARGET-01 is provably
INVARIANT across the entire space of "nobody overworked" distributions.
`add_target_equity_fairness` (weight `TARGET_EQUITY_WEIGHT = 1`) is the
only term meant to break this tie in favor of the most even split.

**Reproduced directly against the real object** (`assemble_planning_state`
+ `rota.planning.engine.plan`, `rota_dev.db`, no DB writes) by monkey-
patching `add_target_equity_fairness` to ALSO add a hard
`completion_pct_max - completion_pct_min <= N` constraint at several
values of N, everything else in the model untouched:

| Forced max spread (completion_pct points) | Result | Hours per employee (sorted) |
|---|---|---|
| none (today's shipped code) | FEASIBLE, `optimization_complete=True` | 48, 60, 144, 156, 168, 168 |
| ≤ 50 | FEASIBLE, `optimization_complete=True` | 72, 72, 144, 144, 156, 156 |
| ≤ 30 | FEASIBLE, `optimization_complete=True` | 96, 96, 120, 144, 144, 144 |
| ≤ 15 | FEASIBLE, `optimization_complete=True` | 108, 108, 132, 132, 132, 132 |
| ≤ 8  | FEASIBLE, `optimization_complete=True` | 120, 120, 120, 120, 132, 132 |

Every one of these solved quickly and was proven optimal by CP-SAT — a
near-perfectly even split (spread of one 12h shift) is trivially FEASIBLE
on this real calendar. No HARD constraint (rest rules, no-3-consecutive,
D/N rotation, weekly rest) is what's blocking an even split. The shipped,
uncapped objective simply doesn't select it, even though it's sitting
right there with an identical TARGET-01 cost.

This is a genuine weighting/tie-break weakness in the shipped
`add_target_equity_fairness`, not a hard-constraint limitation, and not a
regression from the 2026-09-15 change — most likely a **pre-existing**
weakness that had never been exercised this visibly before, because it
only bites when `target_hours` is structurally unachievable for everyone
(a real understaffing scenario) — previously-tested real objects may
simply not have hit this shape until Royal did.

## What this does NOT affect

- TARGET-01 itself and its "absolute priority over equity/rhythm"
  guarantee (2026-08-25 owner correction) — unaffected, still holds; this
  finding is entirely about the tie-break happening *within* the set of
  TARGET-01-optimal solutions, which was always meant to be equity's job.
- The 2026-09-15 `require_complete_target_hours` gate itself — confirmed
  above to be unrelated to this symptom.
- Hard rules (REST-01, third-consecutive-shift ban, D/N rotation) — all
  independently verified compatible with a near-even split at every
  tested spread cap.

## Open question for the architect (CC does not design this)

How should `add_target_equity_fairness`'s effective strength be raised so
it reliably selects the most-even tie among TARGET-01-optimal solutions,
without repeating T058/T059's CP-SAT performance regression (see
`arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md` in
this same directory)? Candidate directions, none evaluated/chosen here:

- Raise `TARGET_EQUITY_WEIGHT` itself (still a plain linear term, no new
  variable/reification shape) — T058's finding showed raising
  `DN_RHYTHM_REWARD_WEIGHT` 10x broke CP-SAT's ability to prove optimality
  on a DIFFERENT real object, via a weight cascading through
  `equal_split_weight`/`prefer_local_weight` multiplications that no
  longer exist post-2026-09-15 (that whole cascade was deleted with
  `add_equal_split_fairness`) — worth re-testing empirically now that the
  cascade is gone, this may no longer be fragile the same way.
- Add a genuine HARD cap on completion_pct spread (a plain `<=`
  inequality, the same shape tested above, not a deadband/ReLU/piecewise
  structure) — every tested cap level in this experiment solved fast on
  this real object; T058/T059's documented performance regression was
  specifically about a piecewise dead-zone encoding on a DIFFERENT
  object, not a plain linear inequality like this. Needs its own
  performance verification across multiple real objects before shipping,
  not assumed safe from this one experiment alone.
- Some other reweighting of the target_weight-dominance chain now that
  `equal_split_weight`/`prefer_local_weight` no longer exist in it
  (`_add_combined_objective` is simpler post-2026-09-15 than when T058
  was investigated).

CC's recommendation, stated plainly (not a decision): this is now a
well-isolated, reproducible experiment (see Reproduction below) — an
architect/Codex round can iterate on a fix directly against it without
needing to re-discover the root cause.

## Reproduction

`rota.application.assembler.assemble_planning_state(conn, site_id=
"SITE-f28eb4dea28047e98821e6b0167b9eb2", month=date(2026,10,1))` against
`rota_dev.db`, then `rota.planning.engine.plan(state)`, monkeypatching
`rota.planning.fairness.add_target_equity_fairness` (and
`rota.planning.solver.add_target_equity_fairness`, same reference) to
additionally enforce a hard spread cap as shown above. No DB writes
involved — safe to re-run repeatedly.
