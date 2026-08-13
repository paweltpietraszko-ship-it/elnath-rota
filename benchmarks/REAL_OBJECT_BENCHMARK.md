# ROTA-REAL-OBJECT-01 — R4 simplified benchmark

Status: architect-authored R4 candidate after owner-directed simplification
Production base: `e010f004e90a1e4f426bb72298e7307045d32b56`

## Purpose

This benchmark is deliberately **not** a second scheduling system.

It answers only:

1. Did production create a complete legal schedule?
2. In a controlled resource shortage, did production avoid false `FEASIBLE`?
3. After adding a concrete resource such as a confirmed X/Y window, does the problem disappear?
4. Does REPLAN preserve the known minimum number of baseline placements?
5. How long did production planning take?

`rota_stress.py` may remain a synthetic stress generator. It is not evidence for the
five-person real object.

## Fixed real-object model

Operational cases use:

- five LOCAL employees: A, B, C, D, E;
- C is `DAY_ONLY`;
- optional X/Y with `EXTERNAL_SUPPORT`;
- one D 05:00–17:00 and one N 17:00–05:00 per day;
- REST-01 = 11h;
- LOAD-01 threshold = 60h in a rolling 7-day window;
- real predecessor and cross-month context where relevant.

X/Y are not hidden sixth/seventh local workers. They become usable only through
the existing production rules for external support.

## What decides PASS

Each frozen scenario states:

- `expected_status`: `FEASIBLE` or `DECISION_REQUIRED`;
- `expectation_kind`;
- one short `expectation_reason`;
- only the small amount of extra data needed for that expectation
  (`expected_demand_ids`, `expected_employee_id`, or `expected_reshuffles`).

For `FEASIBLE`:

- production must return exactly one candidate;
- the independent checker verifies coverage, assignment intervals, DAY_ONLY,
  availability, SiteRules, X/Y window eligibility, REST, LOAD, fixed facts and
  the strict ROTA-REG-001 monthly-hour expectation where applicable;
- REPLAN cases additionally compare baseline `(employee_id, demand_id)` pairs.

For controlled negative cases:

- the fixture itself contains a short local proof;
- production must return `DECISION_REQUIRED`;
- any `FEASIBLE` is a mismatch and its candidate is checked independently.

The benchmark **does not** decide basic PASS from:

- blocker wording;
- `unblocking_options`;
- `EXTERNAL-01` versus `EXTERNAL_SUPPORT_DISABLED`;
- inferred UNSAT cores;
- an independently reimplemented PlanningEngine.

Decision payload details are preserved in JSON for diagnostics only.

## Small ground-truth constructions

R4 permits only simple constructions that can be checked directly from fixture data:

- `SIMPLE_SHORTAGE`: a named demand has zero eligible employees;
- `REST_PAIR_SHORTAGE`: two named demands each have only the same employee and
  those intervals violate REST if both are assigned;
- `EXTERNAL_BEFORE`: current state cannot cover the named demand, while a named
  probe window makes the expected X/Y employee eligible;
- `EXTERNAL_AFTER`: the confirmed X/Y employee is eligible and local workers are not;
- `FORCED_LOAD`: named demands are each forced to one employee and together exceed
  60h in a real rolling 7-day window;
- `FIXED_LOAD`: known fixed/history work is exactly at or above the threshold;
- `REPLAN`: only the declared baseline placement count is evaluated.

There is no generic UNSAT analyser and no reference CP-SAT solver in R4.

## REPLAN

R4 contains three explicit REPLAN cases:

- `replan-min-0` → expected reshuffles: 0;
- `replan-min-1` → expected reshuffles: 1;
- `replan-min-2` → expected reshuffles: 2.

A reshuffle is counted per redistributable baseline pair `(employee_id, demand_id)`.
If the same pair remains in the candidate it is unchanged; otherwise it counts as
one change. New demands do not add a reshuffle.

## Fixture validation

Before production `plan()` is called, fixtures are checked for:

- stable ids and valid intervals;
- legal availability/rule values;
- weekday validation for both weekday-based T007 rule kinds;
- global assignment-id uniqueness across boundary, other-site and fixed facts;
- canonical target-site D/N boundary geometry;
- C not working N in fixed facts;
- complete operative six-day history where required;
- valid hard fixed demand references and intervals;
- REST consistency among fixed facts;
- actual monotonicity of the absence ladder.

A malformed fixture yields `BENCHMARK_INVALID` and production is not blamed.

## Verdict classes

Per case:

- `PRODUCTION_PASS` — production matches the explicit expectation;
- `PRODUCTION_MISMATCH` — wrong production status, illegal candidate, or wrong
  REPLAN reshuffle count;
- `BENCHMARK_INVALID` — malformed fixture or contradictory declared construction;
- `INCONCLUSIVE` — no frozen expected status, so the run is diagnostic only.

## Required mutation coverage

Tests must demonstrate that the benchmark detects:

- missing coverage;
- an ineligible employee;
- REST violation;
- LOAD violation;
- false `FEASIBLE` in a controlled shortage;
- an unnecessary REPLAN reshuffle.

They must also demonstrate that arbitrary decision-payload wording does **not**
control the basic PASS/FAIL result.

## Reproduction and report

Each result keeps:

- `case_id` and seed;
- SHA-256 input fingerprint;
- full scenario input;
- short expected status/kind/reason;
- production status;
- full decision payload as diagnostic data;
- candidate-check metrics;
- reshuffle count where applicable;
- production elapsed time.

Commands:

```bash
pytest -q tests/test_real_object_benchmark.py
python -m benchmarks.real_object --suite core --json real_object_core_r4.json
python -m benchmarks.real_object --suite calendar --json real_object_calendar_r4.json
python -m benchmarks.real_object --suite all --json real_object_all_r4.json
python -m benchmarks.real_object --suite all --case external-before-confirmation --seed 13001
```

## Scope lock

R4 must not change `rota/`.

If a future benchmark requirement again needs a general oracle, generic causal
certificate system, or another scheduling solver, work stops and returns to the
owner instead of growing the benchmark into a duplicate product.
