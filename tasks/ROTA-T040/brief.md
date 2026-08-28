# ROTA-T040 — H24 false infeasibility caused by SOFT occupancy encoding

Status: **IMPLEMENTACJA ZAKOŃCZONA (autor: CC), do audytu**

Preimplementation audit: PASS — READY_FOR_IMPLEMENTATION
(`tasks/ROTA-T040/round_01/tests/tests_r1.txt`, exact SHA `9ff2c69`).

## Implementacja

`rota/planning/fairness.py`: nowy helper `_occupied_bool(model, term, name)`
(analogiczny do istniejącego `_exactly_one`) — ciasna konwersja
`occupied <=> term >= 1`. `add_dn_rhythm_reward()` używa go zamiast
surowego `any2`/`any3` w obu implikacjach "wolne", z lokalnym cache
`occupied_cache: dict[(employee_id, date), BoolVar]` per wywołanie
(reużycie między zachodzącymi na siebie oknami rytmu, bez eager
booleanizacji całego miesiąca — zgodnie z PREIMPLEMENTATION_REDUCTION_GATE
punkty 1-3).

Żadne inne pliki nie zmienione — `solver.py::_build_day_kind_terms`, H24
pairing, NIGHT-STREAK-01, REST-01, validator, engine bez zmian, dokładnie
jak wymaga sekcja 3 briefu.

## Weryfikacja

- `ruff check` czyste.
- Nowy `tests/test_t040_h24_rhythm_occupancy.py` — T40-01..T40-06, 6/6
  PASS (2.12s, bez ciężkiego solvera poza T40-04/05 które i tak są małe:
  1 zmiana/dzień, 5 osób).
- T40-07 (regresja T034): `test_t034_third_consecutive_shift_soft.py` +
  `test_t032_soft_ranking.py` (NIGHT-STREAK-01 pełne macierze) — 24/24
  PASS, zero regresji.
- `tests/test_vertical_full_stack.py` (w tym scenario 2, H24) — 4/4 PASS.
- backend.py gate (SHA `c981c32`): FAIL `SIZE_FUNC: add_third_consecutive_shift_penalty
  ma 102 linie` — potwierdzone jako pre-istniejące (T034, nie dotknięte w
  T040, ta sama długość na `BASE_SHA` przed zmianą) — plus WYMAGA_DECYZJI
  `RATIO`/`TOTAL_LINES` (nowy plik testowy). **OWNER_ACCEPTED oba, Paweł,
  2026-08-28.**
- **Niezależny dowód na prawdziwym obiekcie Pawła** (`rota_dev.db`,
  site `SITE-af2c7186...`, "Test1", 5 LOCAL, OCHRONA, H24 06:00-06:00):
  `plan_month()` teraz zwraca `FEASIBLE`, 3 kandydatów, kandydat[0]
  niezależnie zwalidowany: `hard_pass=True, violations=0`. To dokładnie
  ten sam obiekt, który wcześniej dawał fałszywe `DECISION_REQUIRED`.

BASE_MAIN_SHA: `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`
SOURCE_FINDING_SHA: `fb562a7e7878e97b944cfc5ef816e6c588fdcbb9`
SOURCE_FINDING: `arch/ARCHITECT_BRIEF_NIGHT_STREAK_24H_FALSE_POSITIVE_2026-08-28.md`
ARCHITECT_DECISION_DATE: 2026-08-28

## 1. Defect class

A normal catalog H24 occurrence is expanded into a D component and an N component of the same work period. Both components start on the same calendar date and `SHIFT-24-PAIR-01` requires the same employee on both components.

`solver._build_day_kind_terms()` deliberately builds, per employee/date:

`(d_term, n_term, any_term, n_demand_id)`

where `any_term` is a raw non-negative count/sum of all non-CANCELLED starts on that date, not a Boolean.

For a normal H24 decision assigned to employee E on date d:

- `d_term = x_D`;
- `n_term = x_N`;
- `x_D == x_N` through `SHIFT-24-PAIR-01`;
- therefore `any_term = x_D + x_N = 2*x`.

This representation is valid and must not be changed.

The defect is in `fairness.add_dn_rhythm_reward()`. Its `wolne` encoding currently uses raw `any_term` directly in constraints equivalent to:

`match + any_term <= 1`.

That inequality is correct only if `any_term` is already Boolean. For H24, when `any_term = 2*x`, even `match = 0` implies `2*x <= 1`, hence `x = 0`.

Across overlapping D→N→wolne→wolne windows this SOFT helper therefore hard-forbids legal H24 assignments and can make the whole CP-SAT model INFEASIBLE.

This exactly explains the observed class:

- a manually constructed H24 round-robin candidate passes the independent validator with `hard_pass=True`;
- PLAN still returns `DECISION_REQUIRED`/INFEASIBLE;
- disabling `NIGHT-STREAK-01` only changes which HARD assumption/core is reported next; it does not remove the malformed fairness constraint.

The reported `NIGHT-STREAK-01` / later `REST-01` labels are not root-cause proof. `engine._decision_for_night_streak()` reports a night assumption present in the UNSAT core; the generic `_decision_for_conflict()` labels ordinary conflicting demand cores as `REST-01`. Neither path audits whether an unrelated SOFT helper accidentally added a hard restriction.

## 2. Frozen architectural correction

Do **not** special-case H24.

The general invariant is:

> `any_term` is a non-negative occupancy count. Before a SOFT rule asks whether a date is `wolne`, it must convert that count to the Boolean predicate `occupied := (any_term >= 1)` (or equivalently `free := (any_term == 0)`).

`add_dn_rhythm_reward()` must use a Boolean occupancy/free literal in its `wolne` implications, never the raw count.

### 2.1 Constant cases stay cheap

Preserve the current cheap skips:

- integer `any_term == 0` => date is proven free;
- integer `any_term > 0` => date is proven occupied, so the window cannot match and may be skipped.

No BoolVar is needed for a constant.

### 2.2 Decision-expression case

For a non-constant raw occupancy expression create a tight Boolean equivalence, canonical meaning:

`occupied <=> any_term >= 1`

using the existing CP-SAT model, e.g. equivalent constraints:

- `any_term >= 1` only if `occupied`;
- `any_term == 0` only if `not occupied`.

Then the reward match may require `occupied == 0`, e.g. `match + occupied <= 1`.

Because `any_term` is built only from non-negative 0/1 assignment terms plus non-negative fixed constants, this equivalence is complete and does not need a generic integer-sign abstraction.

### 2.3 Reuse within overlapping windows

A date appears in multiple 4-day rhythm windows. Reuse one lazily-created occupancy literal per `(employee_id, date)` within one call to `add_dn_rhythm_reward()`.

A small local cache is authorized. Do not eagerly booleanize every date in `solver._build_day_kind_terms()`.

This preserves the earlier T032 performance correction: reification is created only for windows that actually survive the cheap skips and need the SOFT reward.

## 3. What remains unchanged

### `solver._build_day_kind_terms`

Unchanged. `any_term` remains a raw count/sum and may legitimately exceed 1.

Do not force it to Boolean globally. Other users of `day_kind_terms` retain their current semantics.

### D/N literals

`d_term` and `n_term` handling in `add_dn_rhythm_reward()` remains the existing `exactly one` semantics through `_exactly_one()` where needed.

T040 changes only the `wolne` occupancy predicate.

### H24 HARD semantics

Unchanged:

- normal H24 D/N components remain one work period;
- same employee remains required across both components;
- OCHRONA exact-24h rest floor remains 24h;
- `NIGHT-STREAK-01` remains max two consecutive N start dates;
- `WEEKLY-REST-01`, LOAD, coverage and eligibility remain unchanged.

### Diagnostics

Do not change `engine._decision_for_night_streak()` or `_decision_for_conflict()` in T040.

Once the malformed SOFT constraint is removed, the known legal H24 case should no longer reach those conflict paths. A broader redesign of UNSAT attribution is not required by this defect.

### T034

`add_third_consecutive_shift_penalty()` is unchanged. It uses D/N literals but does not use raw `any_term` as a Boolean `wolne` gate.

## 4. TASK_SCOPE

TASK_SCOPE:
- rota/planning/fairness.py
- tests/test_t040_h24_rhythm_occupancy.py

(machine-readable block above, added for backend.py's parser — CC,
2026-08-28; prose below is the architect's own frozen scope statement,
unchanged.)

Production — exactly:

- `rota/planning/fairness.py`.

Tests — one focused module, e.g.:

- `tests/test_t040_h24_rhythm_occupancy.py`.

Do not modify:

- `rota/planning/solver.py`;
- `rota/planning/constraints.py`;
- `rota/planning/validator.py`;
- `rota/planning/work_periods.py`;
- `rota/planning/engine.py` / `engine_types.py`;
- shift catalog generation;
- application/API/frontend/persistence/domain;
- T034 logic;
- the separate stale-WORKING shift-catalog finding.

If implementation appears to require any production file outside `fairness.py`, stop and report the concrete blocker rather than widening the task.

## 5. Required acceptance matrix

### T40-01 — minimal mechanical reproducer of the defect

Build a tiny CP-SAT model around real `add_dn_rhythm_reward()` semantics where a candidate `wolne` date has raw occupancy `any_term = 2*x` (the normal H24 shape), force `x == 1`, and make the surrounding D/N literals sufficient for the rhythm window to be considered.

Before T040 the model must reproduce the false infeasibility caused by `match + 2*x <= 1`.

After T040 the same model must be FEASIBLE; the occupied date simply prevents that rhythm match/reward. It must **not** force `x` to zero.

This is the primary root-cause oracle.

### T40-02 — ordinary one-start occupancy remains unchanged

With `any_term = x` (ordinary D/N day), `x == 1` prevents the `wolne` match but remains itself legal. With `x == 0`, the date may satisfy `wolne`.

### T40-03 — ordinary D→N→wolne→wolne reward still works

A canonical ordinary 12h D/N four-date window with exactly D, exactly N, free, free still produces the existing reward. T040 must not silently disable or change T032 rhythm ranking.

### T40-04 — real H24 vertical through solver/validator

Create a deterministic synthetic PlanningState with:

- regime `OCHRONA`;
- a normal catalog H24 occurrence represented as D/N components sharing one `work_period_template_id` per day;
- at least four consecutive daily H24 occurrences (enough to exercise the rhythm windows);
- enough ordinary LOCAL employees for a legal alternating/round-robin schedule;
- no availability/SiteRule/day_only noise;
- load threshold or solve mode chosen so LOAD is not the test subject.

Run the real solver/plan path. A full candidate must exist and the independent `validate()` on the returned candidate must have `hard_pass=True`.

The test must fail on `BASE_MAIN_SHA` because of the T040 defect and pass after the fairness correction.

Do not use the owner's `rota_dev.db` as the automated oracle.

### T40-05 — H24 work-period semantics unchanged

The vertical candidate must still prove both H24 components of each occurrence go to the same employee and share the canonical work-period identity/rest provenance. T040 must not obtain FEASIBLE by weakening H24 HARD.

### T40-06 — NIGHT-STREAK and REST remain active

Include focused sibling checks (reuse existing tests where sufficient; do not duplicate their full matrices) proving:

- three genuine consecutive N start dates for one employee are still illegal;
- assigning adjacent 24h work periods to the same employee without the required 24h rest remains illegal.

The fix is not allowed to make the reproducer green by bypassing those HARD rules.

### T40-07 — T034 regressions remain green

Run the focused T034 third-consecutive-shift tests. No T034 production change is authorized.

### T40-08 — simulator evidence is supporting only

`tests/property/test_coordinator_simulator.py` / seed exercising `SINGLE_24H` may be used as supporting evidence if runtime is acceptable, but it is not the primary deterministic acceptance oracle and must not be edited merely to make T040 pass.

## 6. PREIMPLEMENTATION REDUCTION GATE

Necessary production change after reduction:

1. one tight Boolean occupancy/free conversion for a non-constant `any_term` inside `add_dn_rhythm_reward()`;
2. reuse that Boolean in the two existing `wolne` implications;
3. local per-employee/date cache to avoid duplicate reification across overlapping windows.

Explicitly unnecessary and removed from consideration:

- H24 special-case;
- change to `_build_day_kind_terms`;
- change to normal H24 pairing/rest;
- change to NIGHT-STREAK;
- change to validator;
- change to engine conflict attribution;
- new solver phase;
- DTO/status/persistence/UI work;
- second day-kind builder or second D/N classifier.

## 7. Separate stale-WORKING finding

`arch/ARCHITECT_BRIEF_SHIFT_CATALOG_STALE_WORKING_VERSION_2026-08-28.md` is a separate application/persistence question and is explicitly outside T040.

T040 must not regenerate persisted `shift_demands`, reset current ScheduleVersion pointers, or alter PLAN lifecycle behavior.

## 8. Codex preimplementation audit

Audit this exact contract and answer only:

1. Does the root-cause derivation correctly follow from `any_term` being a count and H24 producing `2*x` on one start date?
2. Does the proposed Boolean occupancy equivalence remove the accidental HARD restriction without weakening the intended `wolne` meaning?
3. Is changing only `fairness.py` sufficient?
4. Does leaving `_build_day_kind_terms`, H24 HARD, REST, NIGHT-STREAK, validator and engine unchanged preserve existing ownership boundaries?
5. Is T40-01 a deterministic before/after reproducer of the exact malformed inequality?
6. Does T40-04 prove the real vertical defect without depending on `rota_dev.db` or simulator randomness?
7. Are the sibling regressions sufficient to prove no HARD rule was bypassed?
8. Is there any smaller correction that preserves the same semantics without duplicating logic?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered contract defects.

Until PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.
