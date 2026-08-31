# ROTA-T045 — SHIFT-24-PAIR-01 false positive on legal overlapping demands

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `91c5e56`
FINDING: `arch/FINDING_VARIANT_B_SHIFT24_PAIR_2026-08-31.md`
CODEX_INPUT: `arch/CODEX_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md`
ARCHITECT_INPUT: `arch/ARCHITECT_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md`

No production implementation may start before independent PASS on this exact
contract HEAD.

## 0. Origin and verdict (closed, not to be re-litigated)

A controlled 30-object Wariant B batch (`tasks/ROTA-T044/round_01/tests/reports/batch1/`)
showed 20/30 (67%) objects ending `TECHNICAL_ERROR`, all on the same
`SHIFT-24-PAIR-01` violation. Codex and the architect independently confirmed
the same root cause with independent minimal reproducers:

- the Wariant B generator did nothing wrong — the product legally allows
  independent, overlapping catalog occurrences (arch/spec.md:58, 485;
  ROTA-T012), and Wariant B's job is to reproduce coordinator configurations,
  not sanitize them. **The generator is not touched by this task.**
- the solver already enforces the same-person rule correctly during solving
  (`rota/planning/constraints.py::add_same_person_24h_constraints`, called
  from `rota/planning/solver.py`). It reasons per `(demand_id, employee_id)`
  and is not the source of the bug. **`constraints.py`/`solver.py` are not
  touched by this task** unless implementation independently reproduces a
  distinct solver-side defect — if that happens, stop and report, do not
  silently expand scope.
- the actual defect is in the independent post-hoc validator:
  `rota/planning/validator.py::_check_24h_same_person` (lines ~450-478)
  builds `emp1`/`emp2` from **every PRIMARY whose interval merely overlaps**
  each H24 half by raw geometry (lines 470-471), with no attribution to
  which demand that PRIMARY actually belongs to. A PRIMARY legitimately
  covering a different, independently-overlapping demand gets swept into
  the wrong set, producing a false `emp1 != emp2` mismatch and a false
  `TECHNICAL_ERROR`.

Minimal reproducer (Codex, confirmed independently by architect on
`main@c9f2404`): E1 covers both halves of one H24 occurrence; E2 covers a
separate, legally overlapping 10h demand that overlaps only the first half.
Production `validate()` returns `hard_pass=False` /
`SHIFT-24-PAIR-01: ... mismatch ['E1','E2'] vs ['E1']` even though the H24
occurrence itself is correctly, uniformly covered by E1.

Diagnosability of `TECHNICAL_ERROR` (candidates always `[]`, only a text
`error_message`) is explicitly **out of scope** for this task per both Codex
and the architect — it is a separate, user-visible product decision, not
part of this validator fix.

## 1. What must change

`_check_24h_same_person` must stop trusting raw time-overlap alone to decide
which PRIMARY assignments belong to a given H24 component. It must use the
same attribution semantics already frozen for `COVERAGE-01`
(`_check_coverage`, ROTA-T041 OWNER-T041-01 / AUDIT-1 C-03 / T41-A-R2-03):

- a PRIMARY's real covered sub-interval belongs to the demand it's actually
  competing for;
- when the PRIMARY's own `covers_demand_id` tag points to a *different*
  demand that genuinely, concurrently competes (in time) with the H24
  component being checked, the competing sub-interval is attributed to that
  other, tagged demand — not double-counted into the H24 set;
- a missing tag, a tag pointing nowhere among current demands, or a tag
  whose claimed target the assignment doesn't actually overlap, must fall
  back to plain geometry. **A false or absent tag can never hide real H24
  coverage** — this is T022-F2, and it must not regress.
- a non-competing (adjacent, not overlapping) tail/head of a spanning/manual
  PRIMARY still counts by plain geometry exactly as today (T022 requirement).

## 2. How, structurally (architect's recommendation — follow it)

Do not write a second, parallel attribution algorithm for H24. Extract the
existing sub-interval attribution logic already inside `_check_coverage`
(the tag-vs-geometry exclusion computed per PRIMARY per demand, lines
~133-156) into one small shared helper, and have both `_check_coverage` and
`_check_24h_same_person` build their employee/coverage sets from it. One
source of truth for "does this PRIMARY, in this sub-interval, actually
belong to this demand" — reused by both HARD checks.

`_check_24h_same_person`'s existing fail-closed shape checks
(`_is_well_formed_normal_h24_pair`, cardinality-!=2 handling) are unaffected
and must not change behavior.

## 3. Preserve exactly (frozen, do not regress)

- **T022-F2**: employee sets for SHIFT-24-PAIR-01 are derived from actual
  coverage, never solely from `covers_demand_id`; a false/missing/wrong tag
  can never hide real H24 coverage by a spanning or manual PRIMARY.
- **T022-F3**: malformed/wrong-cardinality H24 provenance still fails closed
  (unchanged code paths, sections above `_check_24h_same_person`'s employee-set
  computation).
- **ROTA-T041 / COVERAGE-01 concurrent-demand disambiguation**: two
  independently legal, concurrent demands each correctly covered by one
  person must not produce a false `COVERAGE-01` (this must stay green — this
  task must not reopen AUDIT-1 C-03 / T41-A-R2-03).
- Everything else in `validator.py` is untouched.

## 4. TASK_SCOPE

Production files allowed:

- `rota/planning/validator.py`

No other production file. If implementation genuinely cannot fix this
without touching `constraints.py`/`solver.py`, stop and report — do not
silently widen scope on a "small corrective Task."

Test files:

- `tasks/ROTA-T045/brief.md`
- `tests/test_t022_planning_integrity.py`
- `tests/test_t040_h24_rhythm_occupancy.py`
- `tests/test_t012.py` (read-only unless an existing SHIFT-24-PAIR-01/T022-F2
  fixture there needs a genuinely new assertion for this fix; do not touch
  unrelated assertions)

Explicitly out of scope:

- `rota/planning/constraints.py`, `rota/planning/solver.py` (see section 0);
- `tests/property/coordinator_simulator.py` and any Wariant A/B generator
  code (no filtering, no new sanity rule — architect's explicit finding: the
  67% batch result is an argument for keeping the generator wide, not for
  narrowing it);
- `PlanningResult`/API-visible diagnostics for `TECHNICAL_ERROR` (candidates
  discarded on TECHNICAL_ERROR) — separate OWNER decision, not this task;
- any change to `COVERAGE-01`'s own violation semantics/message format
  beyond factoring out the shared helper.

## 5. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `rota/planning/validator.py` (`_check_coverage`, `_check_24h_same_person`)
- REASON: this task changes the owner of a HARD rule's employee-set
  attribution and shares logic between two independent HARD checks
  (`COVERAGE-01`, `SHIFT-24-PAIR-01`); confirmed via `where.py` before this
  brief that both functions currently have exactly one production call site
  each (`validator.py:660`/`:671`, both inside the same module's public
  `validate()` orchestration) — the map must confirm this is still true
  after refactor and that no other module reimplements this attribution.

## 6. Minimum test matrix (architect's matrix, verbatim)

1. **LEGAL_OVERLAP_PASS** — E1 covers both components of one H24 occurrence;
   E2 covers an independent, legal demand overlapping only the first half.
   `SHIFT-24-PAIR-01` does not fire.
2. **REAL_MISMATCH_FAIL** — the first and second halves of one H24 occurrence
   are genuinely covered by different people. `SHIFT-24-PAIR-01` fires.
3. **T022_TAG_BYPASS_STILL_FAILS** — a spanning/manual PRIMARY genuinely
   covers an H24 component but its `covers_demand_id` tag points to a
   different, non-competing/adjacent demand. The tag must not hide real
   coverage — T022-F2 protection preserved.
4. **T041_CONCURRENT_DISAMBIGUATION_STAYS_GREEN** — existing legal-concurrent-
   demand `COVERAGE-01` disambiguation (T041/AUDIT-1 C-03) is unaffected by
   the refactor; existing regression for this must stay green.
5. **MALFORMED_H24_STILL_FAILS_CLOSED** — T022-F3 cardinality/provenance
   fail-closed behavior is unchanged.
6. **MULTI_PRIMARY_H24** — when `required_primary_count > 1`, the correct
   matching multi-person set on both halves still passes.

Add these as new test cases in `tests/test_t022_planning_integrity.py`
(or `tests/test_t040_h24_rhythm_occupancy.py` if that file already owns
comparable H24 fixtures — implementer's judgment, keep it in whichever file
already has the closest existing fixture helpers, do not create a third
home for H24 tests).

The Wariant B batch's seed 0
(`tasks/ROTA-T044/round_01/tests/reports/batch1/seed0.json`,
reproduction command inside that file) is kept as an integration-level
confirmation that this specific real object now returns `FEASIBLE`/
`DECISION_REQUIRED` instead of a false `TECHNICAL_ERROR` — it is not a
substitute for the unit matrix above.

## 7. Retained regressions / quality gates

- Full `tests/test_t022_planning_integrity.py`, `tests/test_t040_h24_rhythm_occupancy.py`;
- `tests/test_t041_checkpoint_a.py` (COVERAGE-01 concurrent-demand tests —
  must stay green, this is the exact regression the shared-helper refactor
  must not break);
- `tests/test_t012.py` (existing H24/emergency-pair regressions);
- full suite;
- Ruff;
- `git diff --check`.

## 8. Process

Small corrective Task, one implementation/review unit, no checkpoint split.
After PASS on this brief: implementation, then targeted matrix + retained
regressions + quality gates + independent exact-SHA implementation audit
(Codex) + architect exact-SHA review. Merge remains an explicit owner
action — never on CC's own initiative even after green backend + Codex.

## 9. Final preimplementation verification

Independent verification of this exact HEAD should answer:

1. Does the fix reuse `_check_coverage`'s existing tag/geometry attribution
   rather than adding a second, parallel algorithm?
2. Does the minimal test matrix (section 6) cover both the false-positive
   fix and every T022-F2/F3/T041 regression this change could plausibly
   break?
3. Is the fix contained entirely inside `rota/planning/validator.py`, with
   no solver/generator/API change?
4. Does the fix leave `TECHNICAL_ERROR`'s diagnostics gap untouched, as a
   separate, undecided product question?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` only for a concrete contradiction in this contract.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

## 10. EXACT TASK_SCOPE

Mechanical restatement of section 4 for backend.py's parser (bare paths, no
formatting).

TASK_SCOPE:
- arch/FINDING_VARIANT_B_SHIFT24_PAIR_2026-08-31.md
- arch/CODEX_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md
- arch/ARCHITECT_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md
- tasks/ROTA-T045/brief.md
- rota/planning/validator.py
- tests/test_t022_planning_integrity.py
- tests/test_t040_h24_rhythm_occupancy.py
- tests/test_t012.py
