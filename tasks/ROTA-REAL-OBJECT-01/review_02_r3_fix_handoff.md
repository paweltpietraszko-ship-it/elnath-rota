# ROTA-REAL-OBJECT-01 — R3 FIX HANDOFF

Date: 2026-08-13
Previous audited SHA: `e2ed1a9be999780e941e8df12de55bc630f8fab6`
Codex verdict: FAIL benchmarku, not PlanningEngine

This handoff records the R3 correction set. It does not declare PASS.

## R2-1 — complete DECISION_REQUIRED validation

Closed by `benchmarks/real_object_decisions.py`.

R3 validates every reported element rather than accepting one correct fragment:

- every blocking demand id and interval;
- every blocker employee/condition;
- exact LOAD employee/window/hours certificate;
- absence of stray load_blocker in non-LOAD classes;
- semantic unblocking options, including required X/Y option for external support;
- rejection of additional fictional blockers and unrelated options.

Durable regressions are in `tests/test_real_object_benchmark_r3.py`.

## R2-2 — collective HARD shortage / REST

Closed by `collective_shortage_evidence()` in `real_object_checker.py`.

The checker now has two independent proof modes:

1. per-demand zero individually eligible employee;
2. independent uncapped CP-SAT for the exact reported demand set, enforcing coverage, eligibility, fixed facts and pairwise REST.

REST blockers are accepted only for employees independently eligible for a conflicting pair in a collectively INFEASIBLE reported set.

A dedicated regression creates D and N that are each individually coverable only by A but cannot both be covered by A under REST.

## R2-3 — full fixed/boundary validation

Closed in `real_object_input.py`.

One global fixed-fact family now validates:

- assignment_id uniqueness across target boundary, cross-site context and fixed-demand collections;
- known employee and operative state;
- CANCELLED cannot masquerade as fixed work/history;
- positive intervals;
- target Site boundary/fixed facts must use canonical D/N geometry;
- fixed demands must match the real demand interval;
- target-site DAY_ONLY;
- hard fixed availability/SiteRule/external-window coherence;
- REST across all fixed/context facts;
- required six-day history counts only REALIZED target-site D/N.

R3 adds explicit `ScenarioSpec.other_site_assignments` for legitimate cross-site REST/LOAD context. This is not a loophole for malformed target-site boundary geometry.

## R2-4 — monotonic absence ladder

Closed in `real_object_scenarios.py` and guarded by the runner.

Levels are now cumulative:

- L0: no added absence;
- L1: B UNAVAILABLE_24H;
- L2: L1 + A DAY_SHIFT_OFF;
- L3: L2 + D DAY_SHIFT_OFF + E DAY_SHIFT_OFF.

`run_matrix()` independently checks that each level's availability facts are a subset of the next level. Non-monotonic series produce top-level `benchmark_errors` and cannot PASS even if case-level statuses happen to be green.

## Condition decision — external support disabled

Architectural clarification:

`arch/BENCHMARK_REAL_OBJECT_R3_CONDITION_CLARIFICATION_2026-08-13.md`

Canonical public blocker condition is `EXTERNAL-01`, including when profile capability is disabled. `EXTERNAL_SUPPORT_DISABLED` may remain internal diagnostic detail but is not a second public `DecisionRequiredPayload.blockers[*].condition` taxonomy.

This decision changes no production code on the benchmark branch.

## REST exactly 11 h without illegal local geometry

R2 correctly rejected local boundary facts such as 06:00–18:00 because target Site shifts are D 05–17 and N 17–05.

R3 tests the exact 11 h threshold using explicit `other_site_assignments`: cross-site work may have a different shift geometry but still constrains the employee's target-Site REST/LOAD. The below-11 case uses the same mechanism. Target-site boundary remains canonical D/N.

## Hygiene

- removed the unused `datetime.date` import from checker;
- rewrote `benchmarks/REAL_OBJECT_BENCHMARK.md` without trailing whitespace.

## Scope boundary

R3 changes benchmark/test/architecture clarification files only. It does not modify `rota/`, PlanningEngine, frozen product semantics, or ROTA-REG-001.

## Required R3 audit

Codex should:

1. rerun the official benchmark tests plus `tests/test_real_object_benchmark_r3.py`;
2. rerun its R2 adversarial test unchanged where compatible with public benchmark APIs;
3. run core/calendar/all JSON suites and exact replay;
4. run Ruff and `git diff --check`;
5. first decide whether benchmark infrastructure is sound;
6. only after benchmark PASS classify any remaining red production case as a separate PlanningEngine finding.

In particular, do not normalize `EXTERNAL_SUPPORT_DISABLED` to green in the benchmark. Test it against the architectural clarification above.
