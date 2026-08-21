# ROTA-T022 — CC independent preimplementation analysis

STATUS: ANALYSIS ONLY — NO PRODUCT CODE CHANGED. Answers brief.md SECTION 7.
Reviewed against brief.md @ HEAD `0d50713` on this branch.

Per Paweł's 2026-08-21 verbal instruction: the collision test named in
brief.md SECTION 7 (`05:00–05:01`, `expected_complete=True`) is judged
nonsense and is to be removed as part of this task. SECTION "Known
collision — resolved" below records that decision and its exact,
line-bounded amendment. Cursor still reviews this analysis independently
before any owner freeze; CC has not written or changed test/product code.

## 1. Traceability

Every required behavior in SECTION 2 (T022-F1 through F5) and SECTION 3
(whole-hour boundary) traces to either an existing frozen contract citation
already present in the brief, or to OWNER-T022-01/02/03. No requirement in
those sections was found that lacks a named source. The two nonblocking
notes (C3, C6) are correctly excluded from blocking scope with their own
justification (SECTION 5).

## 2. Call sites that write or validate StandardShift/ShiftDemand/Assignment boundaries

- `rota/planning/shift_catalog.py:95-118` `validate_standard_shift_shape` /
  `validate_standard_shift` — the only StandardShift shape gate. Currently
  checks `required_rest_hours >= 0`, `active_weekdays`, and
  `catalog_kind`-vs-duration. **Does not check `start_time`/`end_time`
  minute/second/microsecond == 0.** This is the single insertion point for
  OWNER-T022-01's StandardShift half.
- `rota/persistence/schedule_validation.py:99-109` `validate_demands` —
  checks duplicate id, `end > start`, `required_primary_count > 0`, month
  membership. **No whole-hour check.**
- `rota/persistence/schedule_validation.py:138-150`
  `_validate_assignment_shape` — checks duplicate id, `end > start`, month
  crossing, known employee, operational_code. **No whole-hour check.**
  This function and `validate_demands` are called from every schedule
  write path that goes through `MalformedScheduleSnapshot`-guarded
  persistence (`schedule_lifecycle`, `manual_edit`, `plan_ops`, `training`,
  `lifecycle_ops` all route writes through
  `rota.persistence.schedule_validation`), so this is confirmed as the
  single shared choke point for ShiftDemand/Assignment content, not one of
  several parallel gates.
- `rota/application/bootstrap.py:59-67` `_is_valid_standard_shift` — a
  DELIBERATELY narrower bootstrap-readiness gate (documented R3-1,
  `tests/test_audit_t010_r3.py`), not full shape validation. **Currently
  has no whole-hour check either**, and is NOT in the candidate
  TASK_SCOPE. See "Known collision — resolved" below: this is the
  mechanically-unavoidable-contradiction case SECTION 5's non-goal list
  anticipates, so it must be added to TASK_SCOPE.

## 3. Live consumers of `_assignment_kind()` / `classify_demand()`

- `rota/planning/validator.py:215` (`_check_day_only`)
- `rota/planning/validator.py:379` (`_check_external`)
- `rota/planning/validator.py:404` (`_check_site_rules`)
- `rota/planning/validator.py:241` (definition of `_assignment_kind` itself)
- `rota/planning/solver.py:147` (`classify_demand`, solver-side, demand-only — never assignment-based, so it is not subject to the F1 anchor bug; only the three validator call sites above are)
- `rota/planning/shift_catalog.py:49` (definition of `classify_demand`)

Confirms brief's own enumeration (DAY_ONLY, SiteRules, EXTERNAL) is
complete for `_assignment_kind()`. No fourth consumer exists.

## 4. H24/H12 pairing predicates across the codebase

- `rota/planning/constraints.py:363-397` `add_same_person_24h_constraints`
  — solver, normal H24, by `work_period_template_id` + exactly-2-demand_id.
- `rota/planning/validator.py:420-435` `_check_24h_same_person` — same
  criterion, independently re-derived (by design, not drift).
- `rota/planning/work_periods.py:177-197`
  `find_same_month_pair_candidates` — structural emergency-pair detection,
  plain H12 only (`_is_plain_12h`), excludes H24.
- `rota/planning/work_periods.py:208-243`
  `find_cross_month_pair_candidates` — same, cross-month boundary variant.
- `rota/planning/work_periods.py:253-286`
  `check_emergency_pair_structure` — independent structural re-check,
  called only from `validator._check_emergency_pairs`
  (`validator.py:438-468`), which explicitly skips any demand with
  `catalog_kind == H24` (`validator.py:457-458`).
- `rota/planning/constraints.py:251-282`
  `build_emergency_pair_context` — filters candidates by slot-eligibility
  and `can_work_24h`, gated by `is_all_24h_profile` short-circuit
  (`constraints.py:256-257`).

None of these predicates currently carry a Site identity comparison for
F4/OWNER-T022-03 — see Q8 below.

## 5. Test enumeration (non-full-hour work boundaries) — PARTIAL, not exhaustive

Confirmed found:

- `tests/test_audit_t010_r4_a.py:97-106` (id
  `smallest_representative_positive_same_day_interval`,
  `StandardShift(ShiftKind.D, time(5), time(5, 1), False, 1)`,
  `expected_complete=True`) — **the named collision, resolved below.**
- `tests/test_site_rules_execution.py` — flagged by an initial broad grep,
  now checked line-by-line: the only matches are
  `datetime(2026, 10, day, 5, 0)` / `datetime(2026, 10, day, 17, 0)` (05:00
  and 17:00, both whole-hour) and one `changed_at` metadata timestamp. This
  was a grep false positive (the pattern loosely matched the `day, 5`
  arguments); no amendment needed here.

This is not a claim of completeness. A dedicated `time(` /
`datetime(...,` minute-argument sweep across `tests/**` was not run to
exhaustion in this pass — the implementer must run one before relying on
"only these two files" for the amendment list.

### Known collision — resolved (owner instruction, 2026-08-21)

`tests/test_audit_t010_r4_a.py:97-106`, case id
`smallest_representative_positive_same_day_interval`, asserts that a
1-minute StandardShift makes `coordinator_context_completeness()` report
`complete=True`. Paweł's explicit ruling: this premise is wrong and the
case is to be removed, not preserved as a "deliberately narrower bootstrap
observation."

Reasoning that supports the ruling, not just the instruction: once
OWNER-T022-01 is enforced, a StandardShift with a fractional-hour
interval can never be legally written or planned. A bootstrap check that
still reports the site "ready" for such a shift is not a narrower
observation — it is an active false positive that would let a coordinator
believe the site is plannable when every subsequent write/plan call would
reject it. This is exactly the "mechanically unavoidable contradiction"
SECTION 5 reserves as the one legitimate reason to touch bootstrap's gate.

Required amendment (not yet made — awaiting owner freeze):

1. `rota/application/bootstrap.py:59-67` `_is_valid_standard_shift` gains
   a whole-hour check on `start_time`/`end_time` alongside its existing
   `required_primary_count > 0` and `end_next_day or end_time > start_time`
   checks.
2. `tests/test_audit_t010_r4_a.py:97-106` — replace this case. The
   1-minute shift must now assert `expected_complete=False`, and (`any(...
   "shift" in item.lower())`) `is True`. Recommended id:
   `sub_hour_interval_is_not_complete`. This is a same-file, same-function,
   line-bounded change to one `pytest.param(...)` entry — no other case in
   the parametrize list is touched.
3. Add `rota/application/bootstrap.py` to TASK_SCOPE (currently absent —
   see Q6).

## 6. TASK_SCOPE completeness

Candidate list in brief.md SECTION 6 is missing one file:

- `rota/application/bootstrap.py` — required by the resolved collision
  above (Q5/known collision). Exact call path:
  `coordinator_context_completeness` (`bootstrap.py:257`) →
  `_is_valid_standard_shift` (`bootstrap.py:59`).

All other candidate files were confirmed as necessary and sufficient for
F1–F5 and the whole-hour boundary by the call-site enumeration in Q2–Q4.
No other missing file was found.

## 7. Schema / new condition code

No requirement in the brief needs a schema or public-DTO change. Existing
error boundaries cover every case:

- `InvalidStandardShift` — StandardShift shape (whole-hour, F-series).
- `MalformedScheduleSnapshot` — ShiftDemand/Assignment write-time shape.
- `SHIFT-24-01`, `SHIFT-24-PAIR-01`, `DAY_ONLY-01`, rule_version_id-based
  SiteRule codes, `ASSIGN-03/04` — all existing HARD condition codes,
  reusable as-is for F1, F2, F3, F5.

For OWNER-T022-03 (cross-Site zero-gap), no new code is required either:
the natural implementation is a REST-01-family gap floor specific to a
Site change (see Q8) — it is still a rest-boundary violation, just with an
enforced minimum gap greater than a configured `0` when the two periods'
Sites differ. This keeps the "no new stable condition code" constraint
satisfied. If Codex's review disagrees and judges this needs its own code,
that is a `WYMAGA_DECYZJI`, not something CC should decide unilaterally.

## 8. OWNER-T022-03 (cross-Site 24h/zero-gap) enforcement paths

Structural point already true, not requiring a fix: `WorkPeriod` grouping
already keys same-Site normal-24h and emergency periods by a `site_id`
inclusive `period_id`/`period_key` (`constraints.py:95`:
`f"{site_id}:{s.demand.work_period_template_id}"`;
`constraints.py:301`: emergency `work_period_id` also embeds `site_id`).
Two different-Site periods therefore never collapse into ONE WorkPeriod
today — `group_into_periods` cannot merge across a Site boundary because
their period keys differ. **OWNER-T022-03's "never merge into one
WorkPeriod" clause is already satisfied by existing code.**

The actual gap is narrower than "merging": the **zero-gap rest check**
between two already-separate, adjacent periods on different Sites. Today,
`violates_rest`/`_check_rest`/`add_rest_constraints`'s edge checks use
`gap_hours < earlier.required_rest_after_hours` uniformly, regardless of
Site. If the earlier period's persisted/configured rest is `0`, a
zero-gap cross-Site continuation currently passes REST-01 cleanly on both
the solver side and the independent validator side, because neither knows
or cares that the two periods are on different Sites.

Enumerated paths that need this specific new floor:

- `rota/planning/constraints.py` `_add_ordinary_fixed_edges` /
  `_add_ordinary_period_edges` / `_add_merged_pair_edges` (solver side,
  fixed cross-Site edges specifically — same-Site edges are unaffected);
- `rota/planning/validator.py:_check_rest` (independent re-check, all
  `(target, other)` pairs where `other` comes from
  `state.other_site_assignments`).

Both sides already have Site identity available at the point they build
`PeriodComponent`/`WorkPeriod` inputs (the boundary/other-site Assignment
carries its own `site_id` implicitly via which state list it came from);
no missing file beyond the existing TASK_SCOPE (`constraints.py`,
`validator.py`) was found for this enforcement. Positive-gap directional
REST and manual-deviation semantics are untouched by this — only the
`gap == 0 and Sites differ` edge needs the floor.

## 9. New test file size estimate

SECTION 4 classes A–F, with the new sub-hour StandardShift/ShiftDemand/
Assignment write-path siblings (class A), the two new demand-anchor
reproducers (class B), the malformed-H24 matrix (class C), the H12+H12
and cross-Site siblings (class D), and the REPLAN mentor matrix (class E),
is a wide equivalence-class matrix comparable in shape to T020's own
689-line dedicated file (accepted as a one-time exception). A single new
file at `<=600` lines is unlikely to fit without dropping required
oracles — recommend either a narrow, named line-ceiling exception (T020
precedent) or splitting by class (e.g. one file for A+B, one for C+D+E) if
Codex/the owner prefer to avoid another exception. This is a scope
finding for the owner freeze, not a decision CC is making now.

## 10. LOAD-01 full-hour-alignment proof

`rota/planning/timeutil.py:43-61` `rolling_windows` builds every window
from `month_start_dt` (midnight, i.e. hour-aligned) plus whole-day
`timedelta` offsets — every window boundary is hour-aligned unconditionally,
independent of T022.

Inputs consumed by `overlap_hours` inside LOAD-01: solver `slot.demand.*`
(ShiftDemand, gated by SECTION 3 item 2 once implemented), `fixed`
intervals built in `constraints.build_fixed_intervals` from
`fixed_assignments`/`boundary_assignments`/`other_site_assignments`
(all `Assignment`, gated by the same write-path guard), and
`validator._check_load`'s `all_assignments` (same three Assignment
sources). Every one of these sources is a persisted or in-solver
Assignment/ShiftDemand whose boundaries are subject to the same
`MalformedScheduleSnapshot`/`InvalidStandardShift` gates once SECTION 3 is
implemented — **provided** the write-path guard in Q2 is actually wired
into every path listed there (schedule_lifecycle, manual_edit, plan_ops,
training, lifecycle_ops all route through
`rota.persistence.schedule_validation`, confirmed by import). No direct
construction of `Assignment`/`ShiftDemand` bypassing that module was found
in the application layer.

Residual risk: `state.py`'s assembly of `PlanningState.boundary_assignments`/
`other_site_assignments` reads directly from persistence
(`schedule_repository`), not through `schedule_validation`'s write gate —
but since data reaching there was already validated at write time (it is
read-back of previously-persisted, already-guarded rows), this is not a
bypass, only worth the implementer re-confirming no legacy pre-T022 row
can still be read back with fractional hours (SECTION 3 item 4 already
requires legacy data stay readable — such legacy rows, if they exist,
would still be able to feed a truncated LOAD-01 result). This is the one
open question for question 10: **does any pre-T022 legacy fractional-hour
Assignment currently exist in any persisted database this system reads?**
CC cannot answer that from source code alone; it is an operational/data
question, not a code question, and should be asked explicitly at owner
freeze rather than assumed away.

## 11. C3 / C6 acknowledgement

Acknowledged as instructed: C3 (`validator._check_rest` not calling
`work_periods.violates_rest`) and C6 (`engine._decision_for_conflict`'s
fixed `"REST-01"` blocker label) are confirmed real, both already
mechanically verified by CC in the original cross-cutting audit input, and
both are correctly out of scope for T022 per SECTION 5. Neither is
converted into a finding here.

## Verdict

`WYMAGA_DECYZJI` — not `FAIL`, not `PASS`. The contract itself is sound
and traceable (Q1, Q7, Q11 all clean). Three concrete items need an owner
decision or a small scope amendment before freeze, not a redesign:

1. Add `rota/application/bootstrap.py` to TASK_SCOPE and adopt the
   SECTION "Known collision — resolved" amendment verbatim (owner already
   ruled on the substance; this is recording it formally).
2. Q9's file-size estimate: decide narrow exception vs. split-by-class
   before implementation starts, so CC does not have to make that call
   mid-implementation.

`tests/test_site_rules_execution.py` was checked and cleared (Q5) — no
open item remains there.

A repo-wide sweep for non-full-hour work boundaries beyond the two files
checked here (Q5) should still be run once, mechanically, before
implementation — this analysis checked what a grep surfaced, not every
test file individually.

No other gap was found. Cursor should review this analysis independently
before the owner freeze, per brief.md SECTION 8.
