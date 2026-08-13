# ROTA-REAL-OBJECT-01 — R4 simplification handoff

Status: READY_FOR_CODEX_R4_AUDIT  
Architect candidate: to be bound to branch head after this file is committed.

## Owner correction

R3 was over-engineered: the benchmark had started duplicating the planner through
a second CP-SAT model and a generic DECISION_REQUIRED certificate subsystem.

R4 deliberately removes that architecture.

## R4 scope

Preserved:

- A–E real-object model, C DAY_ONLY, optional X/Y;
- core/calendar scenarios;
- real production `PlanningEngine.plan()`;
- independent HARD candidate checker;
- fixture validation;
- replay by `case_id + seed`;
- JSON input/result report;
- performance timing.

Removed:

- `benchmarks/real_object_decisions.py`;
- `benchmarks/real_object_oracle.py`;
- generic blocker/unblocking-option certification;
- generic collective UNSAT analysis;
- R3 certificate-specific test suite.

## Acceptance semantics

Per scenario the frozen truth is now small and explicit:

- expected production status;
- short human-readable reason;
- only the concrete demand/employee/reshuffle fields needed by that case.

Negative scenarios are accepted only when their fixture construction itself is
directly checkable:

- zero eligible employee for a named demand;
- two demands restricted to one employee and conflicting on REST;
- X unavailable before a window and eligible after it;
- named forced shifts exceeding LOAD;
- fixed/history load boundary.

No generic solver is used to prove those claims.

`DECISION_REQUIRED` payload contents remain in JSON but do not control basic
benchmark PASS. In particular `EXTERNAL-01` vs `EXTERNAL_SUPPORT_DISABLED` and
the wording of `unblocking_options` are diagnostic differences, not benchmark
correctness gates.

## R3 findings handled

- R3-1: generic causal proof replaced by scenario-local expectations.
- R3-2: no SiteRule blocker-id inference remains; payload blockers are not judged.
- R3-3: weekday validation now covers both weekday-based rule kinds.
- R3-4: REPLAN has explicit expected minima 0/1/2 and a baseline-pair counter.
- R3-5: old certificate-message tests were removed with the subsystem; R4 tests
  contain no unused certificate imports.

## Required audit

Run at exact R4 head:

```bash
pytest -q tests/test_real_object_benchmark.py
pytest -q
ruff check benchmarks tests/test_real_object_benchmark.py
git diff --check e010f004e90a1e4f426bb72298e7307045d32b56..HEAD

python -m benchmarks.real_object --suite core --json real_object_core_r4.json
python -m benchmarks.real_object --suite calendar --json real_object_calendar_r4.json
python -m benchmarks.real_object --suite all --json real_object_all_r4.json
python -m benchmarks.real_object --suite all --case external-before-confirmation --seed 13001
```

Audit the benchmark first. If a controlled case is red after the benchmark
itself is PASS, report the production mismatch separately. Do not add a new
oracle or certificate subsystem to make the benchmark decide harder cases.
