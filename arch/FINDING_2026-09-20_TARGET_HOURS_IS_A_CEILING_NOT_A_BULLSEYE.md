# FINDING 2026-09-20 — target_hours must be a ceiling, never a bullseye to chase from below: root cause of the equity weakness, owner-confirmed

STATUS: finding + owner-confirmed product/domain ruling, NOT a design
document. Supersedes the "just raise TARGET_EQUITY_WEIGHT" framing in
`arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_SHORTFALL.md`
and `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/` (both still valid as evidence,
read them first) -- this doc explains WHY that weight lever didn't work
and what the actual fix needs to do instead. CC does not design the
CP-SAT encoding here.

## The real-world rule (OWNER, 2026-09-20, verbatim reasoning)

"W życiu gdy koordynatorowi brakuje godzin do rozdysponowania uzupełnia
grafik urlopami. Solver nie może traktować limitu jako celu. Zawsze
będzie ten problem, bo na obiektach jest nadwyżka obsady na czasy gdy
trzeba wydać urlopy albo gdy ktoś jest na chorobowym."

In plain terms: `target_hours` is a CEILING (never exceed it), not a
number the solver should try to *reach* by piling on real shifts. When
there isn't enough real shift-work to bring everyone up to their
ceiling -- a NORMAL, CONSTANT condition on every real object (staffing
is sized assuming some people are on leave/sick at any time) -- the
coordinator fills the remaining gap with leave (urlop), a separate
manual action. The solver distributing that unavoidable shortfall
unevenly across people, in an attempt to get individuals closer to a
ceiling that was never meant to be chased, is the actual bug.

## How this explains everything found so far

- `arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_SHORTFALL.md`
  proved TARGET-01 is mathematically invariant across "nobody exceeds
  target" distributions, and that a near-even split is trivially
  feasible -- but the shipped objective doesn't reliably pick it.
- `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/round_01/tests/weight_experiment.py`
  (this same Task, phase 2) then tried the obvious lever -- raise
  `TARGET_EQUITY_WEIGHT` -- across 4 values x 2 real objects x 2 repeats
  each. Result: spread did NOT improve monotonically; on the 10-employee
  ORDINARY object it got WORSE at every higher weight tested (70 -> 72 ->
  79 -> 79 hours of spread as weight went 1 -> 3 -> 10 -> 30).
- **Why that lever couldn't have worked**: `solver.py::
  _add_combined_objective` computes `target_weight = TARGET_DEVIATION_WEIGHT
  + TARGET_EQUITY_WEIGHT * MAX_COMPLETION_PCT + DN_RHYTHM_REWARD_WEIGHT *
  rhythm_match_count` -- TARGET-01's own weight is DELIBERATELY sized to
  scale together with `TARGET_EQUITY_WEIGHT` (so equity can never outrank
  TARGET-01, per the 2026-08-25 owner-corrected dominance guarantee).
  Raising `TARGET_EQUITY_WEIGHT` therefore raises the "chase the target
  from below" pressure (`neg` in `pos - neg = worked - target`) by the
  SAME stroke, canceling out any gain from strengthening equity. The two
  forces are coupled by construction; turning up equity's dial turns up
  its opposing force too. No value of that one constant could have fixed
  this.
- Real Royal data itself supports this: all 6 employees' `target_hours`
  came from a single bulk "ustaw wszystkim" apply-to-all action on
  2026-09-18 (`coordinator_action_records`, `TARGET_HOURS_CHANGED`,
  `changed_employee_ids` covering 5 of the 6 seconds after the 6th was
  set individually) -- a blanket 176h (the standard full-time monthly
  norm) applied to everyone on an object that structurally cannot give
  6 people 176h of real D/N shift work each. This is realistic test data
  for exactly the "everyone's ceiling exceeds available real work"
  condition this finding describes, not a data-entry mistake to correct
  -- the OWNER confirms this condition is normal and constant on real
  objects, so the fix must handle it as the common case, not a corner one.

## What must change (direction only, not an encoding -- architect+Codex decide the mechanism)

TARGET-01's `neg` term (`target - worked`, when worked < target) must
stop creating pressure to close that gap through shift-assignment
concentration on specific individuals. The `pos` term (`worked - target`,
overshooting the ceiling) should very likely be kept as today's strong/
near-HARD deterrent -- the ceiling itself is still real and must not be
exceeded. Once `neg` no longer feeds a chase-the-target pressure, the
CURRENT, UNCHANGED `add_target_equity_fairness` mechanism (minimize
spread of completion_pct) has nothing coupled to fight against and
should naturally become the dominant, correct driver of how the
available real hours get spread -- likely with NO weight changes needed
at all, since the coupling identified above (not the raw magnitude of
`TARGET_EQUITY_WEIGHT`) was the actual defect.

This is NOT proposed as "revert to the pre-2026-09-15 equal-split
fallback" -- that mechanism had its own real, confirmed bug (owner,
2026-09-20): it ignored `absence_hours` entirely, so an employee already
on 80h of granted leave this month would ALSO get a full ~100h of new
shift work piled on top (180h total) instead of the intended ~100h,
because it split raw available demand hours equally among "available"
employees with no accounting for hours they'd already been credited via
leave. `task/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE`'s own name and
its `_effective_targets = target_hours - absence_hours - delegation_hours`
mechanism (unchanged since 2026-09-15, still correct) is the right fix
for THAT bug and must be preserved. The NEW fix is specifically about
how TARGET-01 treats the remaining, still-positive `_effective_targets`
shortfall once absence/delegation are already subtracted -- a ceiling to
respect, not a number to chase via uneven shift-stacking.

## Open question for the architect (CC does not design this)

How should `pos - neg = worked - target` (or `_effective_targets`'s
result) be encoded so that:
1. `pos` (exceeding the ceiling) keeps its strong deterrent -- unchanged
   behavior when someone would be overworked past target.
2. `neg` (falling short of the ceiling) contributes NO pressure to close
   the gap via uneven shift concentration -- the existing, unmodified
   `add_target_equity_fairness` term should then organically produce the
   most-even split of whatever real hours are actually available,
   without any weight retuning.
3. The genuine remaining shortfall (ceiling minus actual real hours
   given) still surfaces to the coordinator as information -- most
   likely via the EXISTING `DecisionRequiredPayloadOut`/`Analityka i
   bilanse` "bilans miesiąca" negative-hours display (already shows
   `-176`-style deficits per owner's own screenshots earlier this
   session) so they know to fill it with urlop -- this finding does not
   ask for a NEW notification mechanism, just confirmation the existing
   display path still works once TARGET-01 stops chasing the gap itself.

Candidate directions, none evaluated/chosen here: drop the `neg` penalty
from TARGET-01's sum entirely (keep `pos` only) and re-verify TARGET-01
still dominates rhythm/weekend/holiday via the existing sizing formula;
or keep a much smaller, decoupled `neg` weight that does NOT scale with
`TARGET_EQUITY_WEIGHT`, sized only to gently prefer using up available
real demand before leaving anyone below a reachable ceiling (still
subordinate to equity). Either way, `target_weight`'s formula in
`_add_combined_objective` needs to stop coupling equity's weight to the
under-target penalty's own weight -- that coupling is the confirmed
defect, independent of which of the two above (or another) direction is
chosen.

## Reproduction

Same real objects/method as `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/`
(`report.md`, `reproducer.py`, `weight_experiment.py`) -- no DB writes,
no PII. A follow-up experiment isolating `pos`-only vs `pos+neg` TARGET-01
encoding, on the same two objects with the same stability-repeat method,
would directly confirm this finding's predicted mechanism before any
production change.
