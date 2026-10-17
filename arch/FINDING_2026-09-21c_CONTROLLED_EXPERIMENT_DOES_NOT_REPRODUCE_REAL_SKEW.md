# FINDING 2026-09-21 (round 3) — the architect-requested controlled experiment does NOT reproduce the Bolf site's 5/0 Saturday split; root cause remains UNPROVEN

STATUS: experiment result + explicit gap statement, NOT a root-cause
declaration and NOT a design document, per the architect's own
instruction in this round's precheck ("jeśli realnego snapshota nie da
się bezpiecznie odtworzyć, napisz wprost, które dane są brakujące — nie
zastępuj go syntetycznym... ani nie deklaruj root cause").

DATA: all data is synthetic and created by the owner; "real object" and
"production" here mean a fully assembled site object and the owner's own
running instance, NOT a customer or real personal data. See
`arch/DATA_STATUS.md`.

## What was run

Exact architect-requested experiment: reconstructed the Bolf site's
stored January 2027 `shift_demands` (all 26 stored demand_id/start/end
timestamps, read read-only from the running instance) and its stored
`calendar_days` (2027-01-01 and
2027-01-06 holidays, matching real PL calendar), OCHRONA regime, 2
LOCAL/no-target/no-absence employees (matching real membership fields
confirmed identical). Ran four solves, capturing real CP-SAT diagnostics
(status, objective, best_objective_bound, wall_time) from every
`_run_solver` call:

| Run | Params | Result | Saturday split | CP-SAT status |
|---|---|---|---|---|
| Baseline | production defaults (30s, 1% gap) | 150h/147h | 27h/18h (3/2) | **OPTIMAL**, objective=best_bound=2613 (zero gap, not just under 1%) |
| Baseline, tighter control | 0% gap, 120s | 150h/147h | 27h/18h (3/2) | OPTIMAL, identical objective/bound |
| Capped (HARD: weekend-hours spread ≤9h) | production defaults | 150h/147h | 27h/18h (3/2) | OPTIMAL, **identical objective=2613** |
| Capped, tighter control | 0% gap, 120s | 150h/147h | 27h/18h (3/2) | OPTIMAL, identical |
| All 3 T017 diversity candidates (baseline) | — | all three | all three 27h/18h | — |

## The actual finding: this reconstruction does not reproduce the real symptom

The Bolf site's stored data (round 2 finding, `FINDING_2026-09-
21b_...md`) showed a **5/0** Saturday split (all 5 Saturdays, 45h, to one
employee) three separate times. This controlled experiment, built from
the same demands/calendar/regime/employee-eligibility facts, instead
proves **3/2 (27h/18h) is the unique OPTIMAL solution** — proven with
zero gap (objective exactly equals best_objective_bound), not merely
"under the 1% tolerance." Forcing an explicit HARD cap that would also
have allowed 3/2 changed nothing, because the model was already
choosing 3/2 without it. All 3 T017 diversity-search candidates agree.

This directly means: **the 5/0 result cannot be a tied/arbitrary CP-SAT
optimum being resolved unluckily** — under this reconstruction's model,
5/0 is strictly WORSE than 3/2 (a larger weekend-fairness spread at
equal committed-hours cost is never cheaper), so a solver proving 3/2
optimal would never legitimately return 5/0 for the same inputs. Since
the Bolf site DID produce 5/0 three times, **something about the real solve
differs from this reconstruction** in a way not yet identified.

## What is confirmed identical (ruled out as the explanation)

- Shift catalog (both StandardShift rows, exact times/weekdays) —
  read directly from the running instance.
- `shift_demands` for the real month — all 26 rows used verbatim.
- `calendar_days`/holidays for the real month — read directly.
- Site `planning_regime` (OCHRONA) — read directly.
- Both employees' `site_memberships` (`enabled`, `can_work_24h`,
  `allowed_roles`, `position_role_id` all identical) and `employees`
  rows (`active_from`, `active_to`, `day_only` all identical) — read
  directly.
- Zero `availability_versions` rows for either employee (no absences) —
  read directly, and independently confirmed by Pawel before this round
  started.
- Zero `work_balance_targets` rows for either (expected for OCHRONA).
- Empty `site_roles`, `role_coverage_authorizations`, and
  `schedule_version_employee_positions` for this site/version — no
  role-based eligibility mechanism of any kind is in play (also directly
  addresses Pawel's confirmation that both employees have identical
  permissions).
- **Pawel's own hypothesis, tested and RULED OUT**: real `shift_demands`
  carry `catalog_kind='INNY'` (Polish for OTHER) for the Saturday-only
  shift and `catalog_kind='12h'` for every weekday shift — a genuinely
  different, non-standard classification from the ordinary 12h shifts,
  automatically assigned by duration (`rota.planning.shift_catalog.
  normalized_catalog_kind`), not something manually configured. `catalog_
  kind` DOES change solver/validator behavior in several places
  (`rota/planning/constraints.py`, `eligibility.py`, `work_periods.py` —
  24h emergency-pairing eligibility, rest-period grouping). Re-ran the
  experiment using `rota.application.assembler.generate_profile_demands`
  (the real production code path, confirmed to correctly tag Saturdays
  `ShiftCatalogKind.OTHER` / weekdays `ShiftCatalogKind.H12`, matching
  production exactly) instead of hand-built `ShiftDemand` objects with
  `catalog_kind=None` — result unchanged: still the fair 3/2 split
  (27h/18h), not 5/0. The non-standard/INNY classification itself does
  not explain the discrepancy in this reconstruction.

## What is NOT yet confirmed — the actual gap (named explicitly, per the architect's instruction)

- **Real `search_attempt`/invocation path**: this experiment always used
  `search_attempt=0` (the ordinary `plan()` default). Whether the real
  January solves that produced 5/0 were genuinely all `search_attempt=0`
  first-time PLANs, or whether one or more went through a "Szukaj dalej"
  retry (`search_attempt>0`, which does randomize CP-SAT's search) was
  NOT verified this round — `schedule_versions.created_by`/
  `coordinator_action_records` were not read for this level of detail.
- **Which candidate was actually accepted**: `plan()` returns up to 3
  T017-diversity candidates; this experiment confirmed all 3 give 3/2
  in the clean reconstruction, but did NOT verify whether the real
  accepted January version came from `select_candidate` choosing
  candidate 0 vs. a later diversity variant, nor whether the real
  solve's OWN diversity search behaved the same way as this
  reconstruction's.
- **Whether the Bolf site's actual January PLAN calls used `search_attempt=0`
  three times in a row, or included at least one non-zero attempt** —
  the three real `schedule_versions` rows only show `created_at`
  timestamps a few minutes apart; nothing in the schema read so far
  distinguishes an ordinary PLAN click from a "Szukaj dalej" retry.
- Real employee_id values are UUIDs, not `"A"`/`"B"` — CP-SAT's
  tie-break behavior when MULTIPLE tied optima exist (not established
  here, since 3/2 was proven UNIQUE for this reconstruction) could in
  principle depend on variable creation order, but since this
  reconstruction proved 3/2 uniquely optimal (not tied with 5/0), that
  channel doesn't explain the discrepancy either UNLESS the real
  model's tie structure differs from this reconstruction's for a reason
  not yet identified.

## CC's assessment, not a decision

The controlled experiment the architect asked for was run faithfully and
gives a clean, decisive, but negative result: it does not reproduce the
real symptom, which means the round-2 finding's real-data observation
(5/0 splits) and this round's clean reconstruction (provably-optimal
3/2) are currently IN TENSION, and CC does not have enough information
to resolve which one reflects what actually runs in production for a
real coordinator's PLAN click. Declaring `add_weekend_fairness`
underweighted would be premature: this experiment shows it working
correctly (selecting the cheaper, more balanced option) whenever a
cheaper option exists and the model matches this reconstruction.

Two ways to close this gap, either read-only, neither attempted yet
because they were outside this round's specific ask:

1. Read `coordinator_action_records`/whatever field distinguishes an
   ordinary PLAN from a "Szukaj dalej" retry for the 3 real January
   `schedule_versions`, to check if `search_attempt` varied.
2. Re-run `plan()` on this EXACT reconstruction with `search_attempt=1`
   and `search_attempt=2` (randomized search) to see whether a
   randomized attempt can reach a 5/0-shaped result at all under this
   model, and if so, whether it's still labeled OPTIMAL/tied-cost or a
   worse, only-reachable-because-randomized-and-stopped-early result.

## Reproduction

Same as round 2's finding, plus: monkeypatch `rota.planning.solver.
_run_solver` to capture `(status_name, objective_value,
best_objective_bound, wall_time)` per call; monkeypatch
`rota.planning.fairness.add_weekend_fairness` (referenced from both
`rota.planning.fairness` and `rota.planning.solver` module namespaces)
to additionally add `model.add(max_weekend - min_weekend <= 9)` after
calling the original. Compare `plan(state)` before/after, and again with
`solver_module.SOLVER_RELATIVE_GAP_LIMIT = 0.0` /
`SOLVER_TIME_LIMIT_SECONDS = 120.0` monkeypatched for the tighter
control. No DB writes, no production access needed to re-run this exact
experiment.
