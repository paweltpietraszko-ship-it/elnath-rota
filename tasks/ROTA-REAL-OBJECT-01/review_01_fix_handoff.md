# ROTA-REAL-OBJECT-01 — R1 FIX HANDOFF

DATE: 2026-08-13
AUTHOR: ChatGPT architect / benchmark author
STATUS: R2_CANDIDATE_FOR_CODEX_REAUDIT
R1_REJECTED_SHA: `54d3bb91841461efa4c121f42308a462381286c9`
PRODUCTION_BASE_SHA: `e010f004e90a1e4f426bb72298e7307045d32b56`

## SCOPE

Codex R1 rejected the benchmark itself. No PlanningEngine finding was issued.
This repair therefore changes benchmark/test infrastructure only. It does not
change production planning, domain, persistence or frozen product contracts.

The original Codex report and adversarial test existed only in the auditor's
local checkout when this repair was authored. The seven finding classes below
are taken from the exact verdict relayed by the owner. Codex must re-run its
original adversarial test unchanged against the R2 exact SHA; this handoff does
not substitute for that re-run.

## R1 FINDING -> R2 REPAIR

### R1-1 — external X/Y pair was internally infeasible

R1 problem: `UNAVAILABLE_24H` on 12 May overlapped the N starting 11 May, so
adding an X window on 12 May did not produce the intended paired state.

R2:
- local shortage uses `DAY_SHIFT_OFF` anchored to the demand start date on
  12 May for A/B/D/E;
- the preceding N is no longer accidentally blocked;
- before/after cases share the same local shortage facts;
- before = no current X window + explicit probe;
- after = the matching current X window;
- negative window matrix covers wrong employee, Site, inactive, partial
  interval, wrong shift kind and profile-disabled.

### R1-2 — fictitious DECISION_REQUIRED certificates were accepted

R2:
- common payload checks reject unknown demand ids / employee ids;
- shortage payload must name a demand independently proven to have zero
  eligible employees and every reported blocker must match an independently
  derived reason for an evidenced demand;
- external-support payload must name a demand independently unlocked by the
  explicit probe window and contain the corresponding X/Y `EXTERNAL-01`
  evidence;
- LOAD payload is not trusted: `verify_load_claim()` performs a fresh,
  independent uncapped CP-SAT solve constrained to the exact reported
  employee/window/hours and the reference must also prove capped INFEASIBLE
  and uncapped FEASIBLE.

### R1-3 — oracle witness was not checked independently

R2:
- every FEASIBLE reference witness is run through
  `check_reference_witness()`;
- COVERAGE, eligibility, REST, LOAD and fixed facts are checked independently;
- checker failure changes the reference solve to
  `UNKNOWN / WITNESS_CHECK_FAILED`;
- such a witness cannot classify production as right or wrong.

### R1-4 — illegal fixed/boundary inputs reached production

R2 adds `real_object_input.py` and validates before oracle and production:
- ids/types/ranges;
- duplicate ids;
- DAY_ONLY C on N;
- boundary overlap / REST structural conflicts;
- fixed demand references, intervals and duplicate hard coverage;
- fixed PLANNED forward eligibility;
- required six-day predecessor shape where the ladder requires it.

Invalid benchmark input returns a benchmark failure with `production.skipped`
and is never used to judge PlanningEngine.

### R1-5 — mandatory ladder 1–14 incomplete

R2 core scenarios explicitly cover all 14 required steps:
1. ROTA-REG-001;
2. 28/29/30/31-day months;
3. six-day predecessor history incl. N ending day 1;
4. PLAN/REPLAN with REALIZED/frozen/redistributable baseline;
5. escalating absences;
6. C absence and flexible-worker absence separately;
7. difficult but <=60h feasible reshuffle;
8. only-uncapped (>60h) feasibility;
9. simple no-eligible shift;
10. REST exactly 11h / below 11h;
11. LOAD exactly 60h / >60h across boundary;
12. month-end N vs known next-month D;
13. X/Y before/after coordinator confirmation;
14. ExternalSupportWindow negative boundary matrix.

The self-test requires `set(ladder_steps) == {1..14}`; Codex should audit that
each labelled scenario really proves its class, not merely trust metadata.

### R1-6 — report/reproduction contract incomplete

R2 report contains:
- stable case_id and seed;
- SHA-256 input fingerprint;
- month, full perturbation description and ladder steps;
- fixed LOCAL roster / DAY_ONLY / external memberships;
- current and probe windows;
- boundary/fixed facts;
- capped/uncapped/no-external/probe reference solves with status, witness,
  checker errors and timeouts;
- production status, full blockers/load blocker/unblocking options, warnings,
  time and independent candidate/certificate evidence;
- correctness separately from performance;
- mean/p50/p95/max and timeout counts per reference class;
- series transition evidence for the escalating absence ladder.

CLI supports exact `--case` plus `--seed` replay.

### R1-7 — JSON TypeError

R2 serializes dataclasses, enums, date/datetime values and nested containers
through `_json_value()` before JSON output. A dedicated test serializes a real
DECISION_REQUIRED report.

## REQUIRED R2 RE-AUDIT

Codex should run, on the exact R2 SHA:

```bash
pytest -q tests/test_real_object_benchmark.py
pytest -q
python -m benchmarks.real_object --suite core --json real_object_core_r2.json
python -m benchmarks.real_object --suite calendar --json real_object_calendar_r2.json
python -m benchmarks.real_object --suite all --json real_object_all_r2.json
python -m benchmarks.real_object --suite all --case external-before-confirmation --seed 13001
```

Additionally:
- run the original R1 adversarial test unchanged;
- verify all generated JSON files parse successfully;
- verify R2 diff contains no `rota/` production changes;
- attack oracle witnesses independently;
- attack DECISION_REQUIRED payloads with fabricated demand/blocker/load data;
- inspect actual ladder semantics rather than only `ladder_steps` metadata.

If the benchmark itself passes but the production matrix contains reproducible
red cases, report those separately as PlanningEngine findings. Do not modify
benchmark expectations merely to make production green.

No PASS is claimed by this handoff. Only Codex re-audit can establish that R2
is a trustworthy benchmark.
