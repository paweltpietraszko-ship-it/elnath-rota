# ROTA-T022 — planning integrity repair after independent cross-cutting audit

STATUS: DRAFT FOR INDEPENDENT CC/CURSOR IMPACT ANALYSIS — NOT READY FOR IMPLEMENTATION

BASE_SHA: `d50a9aa4dfb35ed479470bb7fb83ffca18ecc346` (`main`, after merged ROTA-T020)

This is a corrective task, not a redesign of the planning architecture. It
collects defects mechanically reproduced against the current code and two
explicit owner decisions dated 2026-08-21. CC and Cursor must first review the
impact and completeness of the proposed scope. They must not implement while
this status remains DRAFT.

## 1. Sources of truth

Existing frozen/product contracts remain authoritative:

- `arch/spec.md`, especially HARD validation, COVERAGE-01, LOAD-01,
  ASSIGN-03/04, DAY_ONLY-01 and DAY_SHIFT_OFF-01;
- `arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md`, especially `DAY ANCHOR`:
  weekday SiteRules use the calendar date on which the `ShiftDemand` starts;
- `tasks/ROTA-T012/brief.md`;
- `tasks/ROTA-T012/part_b_work_period_rest.md`;
- `tasks/ROTA-T012/part_c_emergency_24h.md`;
- accepted R20-3/R22/R23 behavior recorded by the T003 audit and regression
  tests: an active TRAINEE pins the referenced PRIMARY during REPLAN.

The external Cursor scan and CC's uncommitted verification note were audit
inputs, not contract sources. This brief is self-contained and does not depend
on either uncommitted file being present on another machine.

This task-local brief records the following owner decisions verbatim in
product meaning:

### OWNER-T022-01 — full-hour work granularity

There is no partial-hour work in this protection-scheduling product. A work
shift may start and end only on a full clock hour. The program must not accept,
persist, solve or report FEASIBLE for a work interval containing minutes,
seconds or microseconds other than zero. A positive duration is therefore an
integer number of hours.

This rule applies to:

- configured `StandardShift.start_time/end_time`;
- persisted/generated `ShiftDemand.start_datetime/end_datetime`;
- persisted/solver/manual `Assignment.start_datetime/end_datetime`.

It does not apply to audit/metadata timestamps such as `created_at`,
`changed_at`, `recorded_at`, nor to date-only absence records. T022 does not
change those fields.

### OWNER-T022-02 — two consecutive H12 are 24h work

Two directly consecutive 12-hour work intervals assigned to the same employee
constitute 24 hours of continuous work. On a mixed profile, automatic use of
that employee is illegal when `SiteMembership.can_work_24h=false`.

The existing T012 emergency mechanism remains the only automatic route for
joining ordinary H12 demands into a 24h work period. A normal pass must not
silently create the same 24h result as two independent work periods merely
because their configured rest is `0`. Emergency use still requires:

- an existing, unambiguous Site 24h capability/provenance;
- the existing fallback order;
- `can_work_24h=true` on a mixed profile;
- all other HARD gates.

`required_rest_hours=0` remains a legal configuration. It does not authorize a
hidden 24h assignment and does not bypass `can_work_24h`.

## 2. Mechanically reproduced defects

Every output below was reproduced in-memory on `main@d50a9aa`; no diagnostic
test or code change was committed while producing this brief.

### T022-F1 — demand-sensitive HARD checks can be skipped or anchored wrongly

Current code:

- `validator._assignment_kind()` uses explicit covering-demand kind when
  present, but for a legacy demand falls back to the Assignment start time;
- `_check_day_only()` skips when that returns `None`;
- `_check_site_rules()` also skips and uses `assignment.start_datetime.date()`
  instead of the frozen ShiftDemand day anchor;
- `_check_external()` consumes the same single-kind helper;
- COVERAGE-01 independently derives coverage from actual intervals, not from
  the single `covers_demand_id` tag, because a manual PRIMARY may span or split
  demand intervals.

Reproduced current results:

1. legacy N demand 17:00–05:00, DAY_ONLY employee, frozen PRIMARY
   16:00–05:00 tagged to that demand -> `plan() == FEASIBLE`, no DAY_ONLY-01;
2. Monday demand, PRIMARY starts Sunday and covers the Monday interval,
   `EMPLOYEE_ALLOWED_WEEKDAYS=[Sunday]` -> `plan() == FEASIBLE`, no SiteRule
   violation.

Required behavior:

- for every demand-kind/day-dependent HARD check, `ShiftDemand.shift_kind`
  is authoritative when present and `classify_demand(the demand, profile)` is
  the only legacy fallback;
- weekday SiteRules use each relevant ShiftDemand start date, never an
  Assignment start-date substitute;
- a manual/spanning PRIMARY cannot hide actually covered N/H24/weekday demand
  segments behind a different `covers_demand_id` tag;
- all applicable SiteRules remain AND;
- DAY_SHIFT_OFF HARD continues to mean the actual day on which work starts;
  T022 does not redefine it as an overlap rule;
- valid solver-generated ordinary assignments retain their current results.

Impact reviewers must enumerate every live consumer of `_assignment_kind()` or
equivalent demand-kind reconstruction, including DAY_ONLY, SiteRules,
EXTERNAL and 24h qualification. If one consumer has a contractually different
anchor, it must be listed explicitly rather than silently normalized.

### T022-F2 — normal H24 same-person validation can be bypassed by tags

Current COVERAGE-01 counts PRIMARY interval coverage. Current
`_check_24h_same_person()` groups only Assignments whose `covers_demand_id`
points directly at an H24 component. Both facts are individually intentional,
but their combination creates a hole.

Reproducer:

- normal H24 components H1/H2 share one template;
- employee A covers H1 and is tagged H1;
- employee B covers H2 by actual interval but is tagged to a following demand
  that the same spanning Assignment also covers;
- all demand intervals have exact PRIMARY coverage;
- employees on H1 and H2 differ.

Current result: `IndependentValidationReport.hard_pass == True`, without
`SHIFT-24-PAIR-01`.

Required behavior:

- employee sets for each normal H24 component are derived consistently with
  the interval-based COVERAGE-01 truth;
- the final employee set on component 1 equals the set on component 2,
  including fixed/REALIZED/frozen/manual/spanning PRIMARY facts;
- `covers_demand_id` remains required lineage but cannot hide actual H24
  coverage;
- a valid normal H24 pair continues to pass and keeps its T012 provenance.

### T022-F3 — malformed normal-H24 template cardinality is skipped

`constraints.add_same_person_24h_constraints()` and
`validator._check_24h_same_person()` both skip templates whose distinct H24
demand set is not exactly two. Generation normally creates two, but persisted
or directly assembled malformed provenance is not consistently rejected.

Required behavior:

- explicit normal H24 provenance is fail-closed unless it contains exactly
  components 1 and 2, each exactly 12h, directly consecutive, opposite D/N,
  with matching template id, rest and required count;
- persistence/write validation rejects malformed snapshot input using the
  existing malformed-snapshot boundary;
- independent validation never reports HARD PASS for malformed normal-H24
  provenance;
- structural candidate violations use the existing `SHIFT-24-PAIR-01`; no new
  condition code is created;
- legacy demands with no explicit T012 H24 provenance are not retroactively
  guessed into malformed H24.

### T022-F4 — normal pass can silently create 24h from H12 with rest=0

Reproducer on a mixed H12/H24 profile:

- two directly consecutive H12 D/N demands;
- both have `required_rest_hours=0`;
- one available employee with `can_work_24h=false`;
- normal `plan()` pass.

Current result: `FEASIBLE`; the employee receives both H12 Assignments under
two standalone `work_period_id` values, with no SHIFT-24 blocker.

Required behavior follows OWNER-T022-02:

- the normal pass cannot assign both directly consecutive H12 periods to one
  employee as two unrelated periods;
- a second/emergency pass may join them only through existing valid emergency
  provenance and eligibility;
- `can_work_24h=false` on a mixed profile yields the existing `SHIFT-24-01`
  qualification failure when that employee would be needed for the 24h pair;
- manually supplied/persisted two-H12 continuous work without valid emergency
  work-period provenance fails independent validation using existing T012
  structural/qualification codes, never ordinary FEASIBLE;
- same-month, month boundary and year boundary siblings are covered;
- no third automatic retry and no new override are introduced;
- existing all-24h profile semantics remain unchanged.

Cross-Site REST remains unchanged. Impact reviewers must report, without
inventing policy, whether any current cross-Site data path can create the same
continuous-H12 shape but lacks enough persisted qualification provenance. If
so, that is a scope/contract question before implementation, not permission
for CC to guess.

### T022-F5 — independent REPLAN validator omits mentor-linked PRIMARY

Solver fixed partition and reshuffle baseline treat a non-CANCELLED PRIMARY
referenced by an active TRAINEE as fixed. `_check_replan_preserves_fixed()`
preserves REALIZED, frozen and TRAINEE rows, but not their referenced PRIMARY.

Reproducer changes only the mentor PRIMARY employee while retaining the same
assignment id and interval. The TRAINEE reference still resolves. Current
validator result: `hard_pass == True`.

Required behavior:

- the independent validator re-derives the same fixed-set invariant as solver
  and reshuffle logic;
- every field change, removal or replacement of a mentor-linked PRIMARY is
  rejected during REPLAN;
- a CANCELLED TRAINEE does not pin its former PRIMARY;
- no change to ASSIGN-03 REALIZED or ASSIGN-04 frozen semantics;
- validation remains independent of CP-SAT bookkeeping.

### NONBLOCKING REVIEW NOTE — DAY_SHIFT_OFF SOFT warning duplication

For one solved N that ends at 05:00 on a DAY_SHIFT_OFF date, `plan()` currently
returns two differently formatted warnings: one from solver and one from the
independent validator. The validator also warns for any overnight Assignment,
although the frozen SOFT exception specifically describes N started the
previous day.

The frozen contract requires the N-entering-day-off condition to remain visible
as SOFT, but does not currently freeze warning cardinality or one canonical
text. Therefore T022 does not classify duplication as a blocking defect and
does not authorize a code change for it. CC/Cursor may mention one bounded
proposal in `ARCHITECTURE_PROPOSALS`; it must not affect their PASS/FAIL.

## 3. Whole-hour validation boundary

OWNER-T022-01 is a blocking correction, not a reason to redesign LOAD-01.

Required enforcement:

1. create/update of `StandardShift` rejects any non-zero minute, second or
   microsecond on start/end;
2. every schedule-content write path rejects non-full-hour ShiftDemand and
   Assignment boundaries before mutation/child creation where atomicity is
   currently guaranteed;
3. direct planning/validation of malformed legacy/in-memory state fails closed
   and can never return FEASIBLE/HARD PASS;
4. valid historical whole-hour data remains readable;
5. metadata timestamps are unaffected;
6. no schema migration, new field, rounding mode or fractional-hours UI is
   introduced;
7. LOAD-01 retains its integer threshold and is regression-tested at exact
   whole-hour boundaries (60 passes; 61 requires decision for threshold 60).

Use existing dedicated error boundaries where they already own the input:
`InvalidStandardShift` for catalog shape and `MalformedScheduleSnapshot` for
schedule snapshot writes. Public PLAN must map malformed in-memory/catalog
state to its existing fail-closed technical/configuration outcome. Do not
invent a coordinator override for malformed time data.

## 4. Required equivalence-class test matrix

The original reproducer remains in every class, plus these siblings.

### A. Full-hour boundary

- StandardShift start `05:30`; end `17:30`; seconds/microseconds non-zero;
- 30-minute and 12h30 INNY;
- ShiftDemand start/end at `:30` through root and child schedule writes;
- Assignment start/end at `:30` through create child, replace working
  snapshot, finalize-in-place and manual correction paths that share content
  validation;
- failure is atomic: no partial child/content/action/memory write;
- direct `plan()` malformed state never FEASIBLE;
- positive whole-hour INNY remains legal;
- ordinary D/N/H24 generation remains unchanged;
- LOAD exact 60/61 and a cross-month whole-hour window remain correct.

### B. Demand anchor and kind

- legacy N demand plus earlier-starting spanning PRIMARY -> DAY_ONLY-01;
- explicit N demand remains authoritative despite current profile changes;
- Monday demand covered by Sunday-starting PRIMARY checks Monday SiteRules;
- reverse weekday sibling does not false-block;
- assignment spanning actual D and N demand segments cannot hide N behind a D
  tag for DAY_ONLY or allowed-shift-kind SiteRules;
- EXTERNAL allowed kind cannot be bypassed by a different tag;
- every applicable SiteRule remains AND.

### C. Normal H24

- tagged component mismatch (existing happy negative);
- interval-covered component hidden behind other tag (original reproducer);
- required_primary_count=2 with one hidden mismatch;
- fixed/REALIZED/frozen/manual siblings;
- valid spanning representation, if accepted by existing persistence
  contract, produces identical actual employee sets and does not false-fail;
- malformed one component, duplicate component, components 1+3, three
  components, wrong duration, gap/overlap, same kind, rest/count mismatch;
- valid generated D->N and N->D pairs pass;
- last-day month/year crossing remains valid.

### D. H12+H12 continuous 24h

- rest=0 and `can_work_24h=false` cannot yield FEASIBLE;
- rest=0 and flag true still uses only legal configured emergency capability;
- no Site 24h capability means no automatic same-person 24h join;
- ordinary normal pass with different employees remains legal;
- fallback produces one shared emergency work_period_id/rest snapshot;
- same-month, cross-month and cross-year;
- DAY_ONLY, availability, SiteRules, EXTERNAL, REST and LOAD remain AND.

### E. REPLAN mentor pinning

- remove mentor PRIMARY;
- change employee, interval, covers_demand_id, state, frozen or provenance;
- same unchanged mentor PRIMARY passes;
- multiple TRAINEEs pointing to one PRIMARY;
- CANCELLED TRAINEE does not pin;
- solver fixed partition, reshuffle baseline and validator agree on the full
  parameterized matrix.

### F. Regression

- every FEASIBLE candidate passes independent HARD validation;
- ROTA-REG-001;
- March 2027 owner scenario;
- T012 normal/emergency/cross-month matrices;
- T017 multi-candidate validation;
- T018 fallback ordering;
- full suite, Ruff, frozen guard and `git diff --check`.

## 5. Explicit non-goals

T022 must not include:

- a new planning architecture, solver, workflow engine, schema or domain DTO;
- a fractional/minute-based work model or changes to coordinator-facing hour
  presentation;
- changes to absence accounting, T019 analytics, T019b memory or T020 PDF;
- reopening T012 rest directionality or T018 fallback order;
- changing T013 coordinator wording/raw conflict heuristics;
- changing bootstrap's intentionally narrower completeness gate unless a
  mechanically unavoidable contradiction is reported before implementation;
- removing dead functions or refactoring duplication merely for cleanup;
- changing ExternalSupportWindow granularity when it does not create a work
  interval;
- silently adapting legacy test expectations outside an enumerated amendment.

The Cursor claim about fractional LOAD is not closed by ignoring malformed
input. It is closed only when malformed partial-hour work cannot enter or pass
the planning pipeline and valid whole-hour LOAD boundaries remain correct.

## 6. Candidate TASK_SCOPE for impact review

This list is not authorized for implementation until CC/Cursor complete the
mechanical call-site review below:

- `tasks/ROTA-T022/brief.md`
- `rota/planning/shift_catalog.py`
- `rota/planning/eligibility.py`
- `rota/planning/solver.py`
- `rota/planning/constraints.py`
- `rota/planning/work_periods.py`
- `rota/planning/validator.py`
- `rota/planning/engine.py`
- `rota/persistence/schedule_validation.py`
- `tests/test_t022_planning_integrity.py` (new)

Expected limits:

- `MAX_NEW_FILES=1`, exactly the consolidated T022 regression file;
- no deletion;
- no migration;
- no `arch/spec.md` or `arch/FROZEN.lock` change;
- no production file outside the reviewed final TASK_SCOPE;
- no existing test oracle change without a named, line-bounded amendment;
- engineering metrics are not pre-accepted by this draft.

## 7. Required CC/Cursor preimplementation analysis

CC and Cursor analyze independently. Neither edits product code.

Each report must answer:

1. Does every required behavior above trace to an existing contract or the two
   owner decisions, without an invented requirement?
2. Enumerate all live call sites that write or validate StandardShift,
   ShiftDemand and Assignment work boundaries.
3. Enumerate all live consumers of demand kind/date or `_assignment_kind()`.
4. Enumerate all H24/H12 pairing predicates across solver, validator,
   persistence, replan/manual edit and boundary context.
5. Enumerate every existing test containing non-full-hour work boundaries,
   distinguishing work times from irrelevant metadata timestamps. Identify
   exact tests that would require an amendment; do not edit them.
6. Verify candidate TASK_SCOPE is complete and minimal. Name any missing file
   with the exact unavoidable call path.
7. Verify no requested outcome requires a schema/public-DTO change or a new
   stable condition code. If it does, report `WYMAGA_DECYZJI`; do not design it.
8. Analyze the cross-Site continuous-H12 question noted in F4 and state whether
   existing persisted provenance is sufficient. Do not infer a policy.
9. Check whether one new test file can remain <=600 lines without deleting
   required oracles. If not, report the exact estimated matrix size before any
   implementation.

Required verdict from each reviewer:

- `PASS — REPAIR CONTRACT COMPLETE / READY FOR OWNER FREEZE`,
  or
- `FAIL — CONTRACT/SCOPE FINDINGS`, with exact file/function/contract evidence,
  or
- `WYMAGA_DECYZJI`, only for a genuine unresolved owner/product question.

More general cleanup suggestions must be placed once in a separate,
  non-blocking `ARCHITECTURE_PROPOSALS` section. They must not expand T022.

One collision is already known and must appear in both analyses:

- `tests/test_audit_t010_r4_a.py::test_r4_a_standard_shift_validity_boundaries`
  contains the case `05:00–05:01` with `expected_complete=True`, documenting
  the older bootstrap-only positive-interval boundary. OWNER-T022-01 now says
  such a work shift is invalid. This draft does not silently authorize editing
  that oracle. Reviewers must state whether the test needs a narrow amendment,
  can remain a deliberately narrower bootstrap observation while writes/PLAN
  fail closed, or exposes a genuine contradiction requiring owner confirmation.

## 8. Implementation and review chain after analysis

1. Owner receives both independent analyses.
2. Any mechanical scope amendment is recorded before implementation.
3. The owner freezes the final scope after reviewing both analyses. Codex does
   not self-approve the draft it prepared.
4. Only the owner's `READY_FOR_IMPLEMENTATION` opens CC implementation.
5. CC runs backend gates and full verification on an exact product SHA.
6. Codex performs implementation audit with committed adversarial
   tests against the classes above.
7. Merge requires the owner's explicit instruction after all gates pass.
