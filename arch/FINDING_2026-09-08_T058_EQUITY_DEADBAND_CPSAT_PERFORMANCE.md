# FINDING 2026-09-08 — ROTA-T058's 24h equity deadband breaks CP-SAT's ability
to prove optimality on real objects (verified, root-caused, NOT an encoding bug)

**UPDATE 2026-09-08 (same day, after further owner-directed investigation):
the problem is broader and more fundamental than the deadband encoding
itself -- see "The weighted-dominance chain is fragile to ANY change,
not just the deadband" below. Read that section first.**

STATUS: finding + reproduced root cause, NOT a design document. Input for
the architect (same role as other `arch/FINDING_*` docs) — CC does not
design the solver-engineering solution here; this needs real architect/
Codex judgment on a genuine CP-SAT modeling trade-off, not a brief
correction. Paweł's own words on why this goes here rather than being
quietly worked around: *"zapytaj inne modele bo to jest sedno działania
programu a nie jakaś poboczna sprawa"* (ask other models -- this is the
core of how the program works, not a side matter).

## Where this sits in ROTA-T058

`task/ROTA-T058` (brief @ `c033141`, Codex preimplementation PASS `000daf2`)
implements two independent things per the frozen contract:

1. **HARD ban on a third consecutive PRIMARY service** -- DONE, VERIFIED
   WORKING. `constraints.add_max_two_consecutive_primary_shift_constraint`,
   wired into `solver.py`, an independent validator mirror
   (`validator._check_third_consecutive_shift`), `engine.py`'s new
   non-decision `THIRD_CONSECUTIVE_SHIFT_BLOCKED` status (no automatic
   `DECISION_REQUIRED` override, per owner ruling), `deviation_mapping.py` +
   `api/routers/schedule.py`'s Polish label for the manual-correction
   escape hatch. 17/17 targeted tests pass (`tests/test_t058.py`), covering
   every acceptance criterion T58-01..T58-09/T58-13/T58-14. **This part has
   no known problem and is ready on its own.**
2. **24h SOFT dead zone on the equity/equal-split hours spread** (brief
   section 2.6, `EQUITY_DEADBAND_HOURS = 24`) -- IMPLEMENTED, but discovered
   live (via a real full-suite test run taking far longer than expected,
   Paweł's own instinct that this smelled like the earlier REPLAN-budget
   dual-bound-non-convergence bug) to cause a severe, reproducible CP-SAT
   performance regression on real objects. **This is the subject of this
   finding.**

## Reproduced numbers (same real object, same seed, only the deadband code differs)

Using `tests/support/t009_fixtures.seed_real_object(seed=42, month=2026-08)`
through the real `plan_ops.plan_month` vertical, with `log_search_progress`
confirming the shape each time (found a FEASIBLE incumbent immediately, the
*dual* bound never closes):

| Path exercised | Without deadband | With deadband | Ratio |
|---|---|---|---|
| `add_equal_split_fairness` fallback (incomplete target vector -- this seed's natural shape) | 0.41s, OPTIMAL | **45.0s, budget exhausted, `optimization_complete=False`, never proves anything** | unbounded |
| `add_target_equity_fairness` (same object, target_hours filled in for every employee to force this branch instead) | 0.43s, OPTIMAL | 13.75s, OPTIMAL (still proves it, just much slower) | ~32x |

`PLANNING_OPERATION_BUDGET_SECONDS` is 45s (owner-set 2026-08-25) -- the
equal_split path does not merely get slower, it silently stops proving
anything at all within budget, every time, for this ordinarily-trivial
object.

## Root cause (isolated experimentally, not guessed)

Four different CP-SAT encodings of the SAME 24h ReLU/dead-zone semantics
were tried on `add_equal_split_fairness`, all reproducing the 45s+
non-convergence identically:

1. `model.add(relu_var >= expr)` (one-sided inequality, minimization
   pressure pulls it to `max(0, expr)`).
2. `model.add_max_equality(relu_var, [expr, 0])` (CP-SAT's native,
   supposedly-tighter max-with-constant primitive).
3. Same as (2) with `relu_var`'s domain tightened to
   `[0, MAX_MONTHLY_HOURS - EQUITY_DEADBAND_HOURS]` instead of the full
   `[0, MAX_MONTHLY_HOURS]`.
4. A boolean-gated equality (`over_deadband` indicator +
   `only_enforce_if`), the exact shape already used for
   `add_target_equity_fairness`'s own deadband.

All four failed identically. A fifth, isolating experiment ruled out "extra
variables/constraints in the model" as the cause on its own: declaring the
exact same auxiliary ReLU variable and its `add_max_equality` constraint,
but leaving the ORIGINAL `weight * (max_hours - min_hours)` term in the
objective (i.e. computing but never actually using the deadbanded value),
solved in 0.49s -- fully unaffected. **The regression appears only once the
deadbanded/gated expression itself, not the plain linear spread, is what
gets multiplied by the large "must strictly dominate every other
coexisting SOFT term" weight already established as this codebase's
pattern (`solver._add_combined_objective`, OWNER_CORRECTED 2026-08-25) and
put into `model.minimize(...)`.**

This matches a documented, known CP-SAT phenomenon, not a one-off bug in
this codebase:

- "CP-SAT can find optimal solutions quickly but then take considerable
  time to prove optimality... particularly when working with complex
  variable structures and bounds" and "reified constraints... can
  negatively impact CP-SAT's performance by modifying its boolean
  structure" -- [or-tools-discuss: CP-SAT poor
  performance](https://groups.google.com/g/or-tools-discuss/c/tmF6DmQBYU4),
  [or-tools-discuss: limits on objective variable make the solver
  slower](https://groups.google.com/g/or-tools-discuss/c/nZclS8C5MKk).
- The CP-SAT Primer's own advanced-modeling guidance on piecewise-linear
  objective terms specifically calls out that "tightening the big-M
  parameters can help eliminate some non-well-behaved piecewise linear
  solutions" and ships a dedicated `PiecewiseLinearFunction` helper
  (`cpsat-utils`) precisely because naive encodings of exactly this shape
  (a flat region + a linear region, i.e. our dead zone) are known to hurt
  bound propagation -- [CP-SAT Primer: Advanced
  Modeling](https://d-krupke.github.io/cpsat-primer/advanced_modelling.html),
  [CP-SAT Primer: Understanding the
  Log](https://d-krupke.github.io/cpsat-primer/understanding_the_log.html).

In short: this is a real, externally-documented CP-SAT weak spot
(piecewise-linear/dead-zone terms at large objective weight), not a
mistake CC made in wiring it up four different ways.

## What this does NOT affect

- The HARD third-consecutive-shift ban (part 1 above) -- fully independent
  code path, verified fast and correct on its own, zero interaction with
  the equity deadband.
- TARGET-01 itself -- unchanged, still dominant, still fast on its own
  (the 0.43s/0.41s "without deadband" baselines above already include
  TARGET-01 running normally).
- Any REPLAN-only mechanism (`quality_required`/`stop_at_first_solution`,
  ROTA-REPLAN-BUDGET-FIX 2026-09-08) -- that fix applies only to an
  internal, always-discarded REPLAN baseline check, never to ordinary
  PLAN/Przelicz Plan, which is exactly the vertical this regression hits.
  It cannot be reused here without genuinely degrading the quality the
  coordinator actually sees, which the T058 brief explicitly forbids
  changing.

## The weighted-dominance chain is fragile to ANY change, not just the deadband

Paweł's own challenge, correctly aimed: if the deadband costs more than it
buys, is asking "how do we encode the deadband better" even the right
question? CC proposed a candidate alternative -- skip the deadband
entirely, and instead simply give `DN_RHYTHM_REWARD_WEIGHT` a value that
outright dominates `TARGET_EQUITY_WEIGHT`'s max swing, so rhythm always
wins ties against equity instead of the reverse (today's accidental
ordering, since both nominally have weight=1 but equity's raw magnitude --
percentage points, 0..74400 -- dwarfs rhythm's raw magnitude -- a small
match count). This is a PURE CONSTANT change: no new variable, no
reification, no piecewise structure, the same "size a weight to strictly
dominate" pattern already used four times elsewhere in this exact codebase
(`TARGET_DEVIATION_WEIGHT`, `equal_split_weight`, `prefer_local_weight`,
and T058's own `target_weight`/`equal_split_weight` extensions).

**This candidate also fails, and fails immediately -- not just at an
extreme value:**

Using the same real object (seed=42, equal_split-fallback branch) with
BOTH equity paths reverted to their original, confirmed-fast form (0.75s
baseline, matching the "HARD ban alone" numbers above), only
`DN_RHYTHM_REWARD_WEIGHT` was varied:

| `DN_RHYTHM_REWARD_WEIGHT` | Result |
|---|---|
| 1 (today's value) | 0.95s, OPTIMAL |
| 10 | **45.0s, budget exhausted, never proves anything** |
| 100 | 45.0s, budget exhausted |
| 1,000 | 45.0s, budget exhausted |
| 10,000 | 45.0s, budget exhausted |
| 74,401 (the exact "dominates equity's max swing" threshold) | 45.0s, budget exhausted |
| 100,000 | 45.0s, budget exhausted |

**A 10x bump in one existing constant -- no new model structure whatsoever
-- is enough to break it.** The achieved rhythm-match count did not even
improve across any of these (112 in every run, including weight=1), so
this was pure cost with zero observed benefit at every tested weight.

Root cause (plausible, not yet fully proven): `DN_RHYTHM_REWARD_WEIGHT`
does not stay isolated -- in the equal_split-fallback branch it is
multiplied by `rhythm_match_count` (~112 on this object) INSIDE
`equal_split_weight`'s own formula
(`solver._add_combined_objective`), and `equal_split_weight` is then
ITSELF multiplied again by `(MAX_MONTHLY_HOURS + 1)` = 745 to produce
`prefer_local_weight`. A change to one base constant cascades through two
further multiplications already present in the existing, shipped
"strictly dominate" chain. Whether that cascade is the full explanation or
CP-SAT's B&B/LP-relaxation is simply this sensitive to coefficient scale
changes in this specific model shape either way, the practical conclusion
is the same: **this weighted-objective architecture appears to already be
running close to whatever limit lets CP-SAT prove optimality for this
object in reasonable time, and it is NOT specific to the equity deadband
or to CC's proposed alternative -- both hit the same wall.**

This reframes the open question below: it is no longer only "how do we
encode a 24h dead zone efficiently", but "is this cascading-weight-
dominance architecture itself safe to extend further at all, by any
means, without a real solver-engineering pass" -- exactly Paweł's
instinct that this is core, not a side matter.

## Open question for the architect (CC does not design this)

How should ROTA-T058's owner-mandated 24h equity dead zone actually be
encoded so it does not cost 32x-to-unbounded solve time on real objects?
Candidate directions found in research above, none evaluated or chosen
here:

- A genuinely tighter piecewise-linear formulation (e.g. the `cpsat-utils`
  `PiecewiseLinearFunction` pattern, or hand-tightened big-M bounds per the
  Primer's own advice) rather than the four ad-hoc encodings already ruled
  out.
- Scoping the deadband's *weight* separately from the "must strictly
  dominate" sizing pattern, if that guarantee can be preserved a different
  way for a piecewise term specifically.
- Accepting a relaxed `relative_gap_limit`/time budget for ONLY this term's
  presence, if that is judged an acceptable trade-off (owner decision, not
  CC's).
- Deciding the deadband is not worth this cost at all, and shipping T058's
  HARD ban alone for now while this is investigated separately.
- Given the reweight experiment above: investigating whether the existing
  "strictly dominate" weight-chain architecture itself
  (`_add_combined_objective`'s `target_weight`/`equal_split_weight`/
  `prefer_local_weight` cascade) needs to be restructured so a single
  constant change stops cascading into fragile coefficient blowups -- a
  question about the existing, already-shipped design, not only about
  T058's new addition to it.

CC's recommendation, stated plainly (not a decision): part 1 (the HARD
ban) is fully working, tested, and has no dependency on part 2 -- it could
ship on its own while this is resolved, if Paweł/architect agree that
split is acceptable. Not acted on without an explicit instruction.

## Reproduction

`tests/support/t009_fixtures.seed_real_object(conn, case_id=..., month=date(2026,8,1), seed=42)`
then `plan_ops.plan_month(...)` through the real DB-backed vertical,
timed with `time.monotonic()`; `log_search_progress=True` on the solver
confirms a FEASIBLE incumbent is found almost immediately while
`best_bound` stays far away for the remainder of the budget. All five
isolating experiments above were done by monkeypatching
`rota.planning.solver.add_equal_split_fairness` /
`add_target_equity_fairness` with alternate implementations against this
exact same seeded state, so every number in the table is a controlled,
apples-to-apples comparison, not different objects.

## OWNER_ACCEPTED 2026-09-08 — podział T058/T059

Paweł jawnie zaakceptował rozdzielenie zakresu po przedstawieniu skutku
widocznego dla użytkownika:

- T058 kończy i audytuje wyłącznie zakaz trzeciej kolejnej służby PRIMARY;
- zaakceptowana tolerancja 24 h nie została anulowana — przechodzi do
  osobnego zadania solver-engineering T059;
- do czasu wdrożenia T059 istniejące wyrównywanie godzin pozostaje bez zmian
  i może nadal preferować różnicę mniejszą niż 24 h kosztem rytmu D/N/W/W.

Ta decyzja zamyka `OWNER_EXPLANATION_GATE` dla delivery T058
`76b3b57e9eb7307904c4e03806cbd1dc41f311e9`.
