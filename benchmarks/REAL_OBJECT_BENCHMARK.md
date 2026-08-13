# ROTA-REAL-OBJECT-01 — benchmark against production code

Status: architect-authored test infrastructure  
Base production SHA: `e010f004e90a1e4f426bb72298e7307045d32b56`

## Why this exists

The historical `benchmarks/rota_stress.py` is a synthetic-feasible stress
generator. It creates a known witness first and then constructs a larger
employee pool around that witness. It is useful as a solver stress tool, but
its `100/100` result is **not** evidence that Rota works for the real
five-person object.

ROTA-REAL-OBJECT-01 asks a different question: what does the current
production `PlanningEngine` do when the input keeps the real local roster
fixed and the environment becomes difficult?

## Non-negotiable roster

Every operational case uses exactly five LOCAL employees:

- A
- B
- C — `DAY_ONLY`
- D
- E

X and Y are separate `EXTERNAL_SUPPORT` employees. They are never a hidden
sixth/seventh local reserve. They can be assigned only when the scenario
contains a matching active `ExternalSupportWindow` and the profile has
external support enabled.

The benchmark uses one PRIMARY D 05:00–17:00 and one PRIMARY N
17:00–05:00 every day, REST-01 = 11h, and LOAD-01 decision threshold = 60h
in every rolling seven-day window.

## Independence from production planning logic

The reference oracle in `real_object_oracle.py` uses OR-Tools, but builds its
own small CP-SAT existence model.

It does **not** import or call:

- `rota.planning.engine.plan`;
- the production solver;
- production eligibility/constraint builders;
- the production validator.

The independent checker in `real_object_checker.py` also does not call the
production validator.

Only `real_object_production.py` translates a benchmark scenario into the
real `PlanningState`. Then `real_object.py` calls production `plan()` and
compares the result with the already-computed reference class.

## Reference classes

A case is independently classified as one of:

- `KNOWN_FEASIBLE`
- `LOAD_DECISION_REQUIRED`
- `EXTERNAL_SUPPORT_DECISION_REQUIRED`
- `KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT`
- `PROVEN_STAFFING_SHORTAGE`
- `INCONCLUSIVE`

`UNKNOWN` from the reference solver becomes `INCONCLUSIVE`; it is never
counted as proof that production is right.

For external support, the benchmark contains paired before/after cases. The
before state has no confirmed window and must not use X/Y. The after state
contains the explicit window. The reference oracle additionally proves that
the corresponding local-only state is infeasible when the case claims that
external support was actually necessary.

## Correctness is not performance

The JSON report has separate `correctness` and `performance` sections.

A fast wrong status is a correctness failure. A slow correct result is
reported as slow, but is not called semantically wrong because this benchmark
does not define an SLA.

## Run

Core matrix:

```bash
python -m benchmarks.real_object --suite core
```

Core + 24-month calendar sweep:

```bash
python -m benchmarks.real_object --suite all
```

Replay one exact case:

```bash
python -m benchmarks.real_object --suite all --case external-before-confirmation
```

Write an audit artifact:

```bash
python -m benchmarks.real_object --suite all --json real_object_report.json
```

Exit code is zero only when every selected case passes correctness and every
declared benchmark scenario is classified by the reference oracle as intended.

## Audit rule

If this benchmark produces a reproducible red case against production code,
do **not** weaken the scenario, enlarge the LOCAL roster, silently add an
external window, or rewrite the expected class to make the report green.

First classify whether the error is:

1. a bug in benchmark construction/oracle/checker; or
2. a production PlanningEngine defect.

Those are separate changes and must not be repaired in the same commit merely
to restore a green benchmark.
