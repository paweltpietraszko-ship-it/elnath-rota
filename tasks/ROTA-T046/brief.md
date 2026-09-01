# ROTA-T046 — PRE_PLAN sick leave prints under the wrong column

STATUS: R2 — OWNER_CORRECTED APPLIED, READY FOR NARROW REAUDIT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `ed6d1efb73b2089d951fb0f188b3b16c00a52fe0`
CODEX_R1_AUDIT: `tasks/ROTA-T046/round_01/tests/tests_r1.txt` @ `4aa04e5`
ORIGIN: finding 9, `project_small_findings_backlog_2026-08-31` (CC/Paweł
evaluator dry-run session, 2026-08-31/2026-09-01) — no separate arch/ finding
doc exists, a small, code-grounded, single-file fix found by direct reading
and by reading the actual rendered PDF, not by a Wariant A/B generator run.

No production implementation may start before independent PASS on this exact
contract HEAD.

## 0. R2 change (OWNER_CORRECTED, do not re-litigate)

R1 bundled a second, unrelated fix ("Part A": mapping
`RetroactiveAbsenceRejected` to HTTP 409 in `api/errors.py`). Codex R1 audit
(`tests_r1.txt` @ `4aa04e5`) returned FAIL for that part after an OWNER
correction on 2026-09-01: retroactively appending SICK_LEAVE/LEAVE_GRANTED
over an already-started or already-realized PRIMARY work period is an HR/
payroll-adjacent scenario this scheduling program does not aim to support,
and swapping one technical status code (500) for another (409) does not by
itself produce a human-friendly message anyway. **Part A is removed from
this Task entirely** — not fixed, not softened, removed. The underlying
domain safeguard (`RetroactiveAbsenceRejected`,
`rota/persistence/absence_reference_repository.py`) is correct and stays
exactly as it is; this Task does not touch it, does not extend its handling,
and does not change its current HTTP behavior.

This brief now covers only the original R1 "Part B" fix, renumbered as the
Task's sole scope below.

## 1. Origin and root cause (confirmed by reading the code AND the actual
rendered PDF, not just computed data)

`rota/application/schedule_export.py::_decompose_pre_plan` (lines 321-323):

```python
def _decompose_pre_plan(employee_id, pre_plan_days, settings) -> list[tuple]:
    span, qualifying = [d for d, _ in pre_plan_days], [(d, day.canonical_hours) for d, day in pre_plan_days if day.canonical_hours]
    return _decompose(employee_id, "U", span, [d for d, _ in qualifying], sum(h for _, h in qualifying), settings)
```

The print letter is hardcoded to `"U"` for every `PRE_PLAN_LEAVE` day,
regardless of the real `AvailabilityKind` (SICK_LEAVE or LEAVE_GRANTED)
carried on each day (`CanonicalSiteAbsenceDay.kind`,
`rota/planning/absence.py:144`). Compare `_post_plan_pair`
(schedule_export.py:339-342, days recorded AFTER the first PLAN, e.g. via
REPLAN), which correctly branches:

```python
letter = "C" if day.kind == AvailabilityKind.SICK_LEAVE else "U"
```

`PRE_PLAN_LEAVE` is real, common territory for SICK_LEAVE specifically by
OWNER decision — `rota/persistence/absence_reference_repository.py`'s
`_resolve_no_accepted_plan_day` docstring: "this is legitimate PRE_PLAN
territory for BOTH LEAVE_GRANTED and SICK_LEAVE — known sick leave entered
before the first accepted plan now counts the same 8h/qualified-workday
total as pre-plan LEAVE_GRANTED, never MISSING" (OWNER-T041-02 / AUDIT-1
C-02, superseding the old "SICK has no pre-PLAN path" restriction). So a
coordinator marking someone sick BEFORE running the month's first PLAN — a
normal, common sequence — hits exactly this path.

**Confirmed visually**, not just in computed data: printed a real object
(Wariant A seed 6, July 2026) and read the actual rendered PDF. The monthly
TOTAL column ("Wyk. g.") is correct and NOT affected by this bug — it sums
all codes regardless of letter, so it is not a totals/fairness problem. The
real damage is that the row's "Urlop g." / "L4 g." summary columns
misattribute the hours: the affected employee's PRE_PLAN sick leave shows
entirely under "Urlop g." with "L4 g." = 0.

## 2. What must change

`_decompose_pre_plan` must group its `pre_plan_days` by `day.kind`
(preserving date order within each group) instead of treating them as one
undifferentiated span, and call `_decompose(...)` once per kind-group with
the correct letter — `"C"` for `AvailabilityKind.SICK_LEAVE`, `"U"` for
`AvailabilityKind.LEAVE_GRANTED` — exactly the same letter rule
`_post_plan_pair` already uses, each group with its own `span`, `qualifying`
dates, and summed `total_hours`. Concatenate the resulting pairs (order
within the month does not need to be re-sorted by the caller — confirm
`_absence_pairs_for_employee`'s existing assembly does not assume a single
contiguous block; if it does, preserve overall date order across groups).

A single employee's PRE_PLAN days for one month may legitimately contain
BOTH kinds in different date ranges (e.g., an early-month LEAVE_GRANTED
period and a later, separate SICK_LEAVE period, both before the first
PLAN) — the fix must handle this correctly, not just the common one-kind
case.

## 3. Preserve exactly (frozen, do not regress)

- `_post_plan_pair`'s existing correct `"C"`/`"U"` branching is untouched.
- The `ABSENCE_DECOMPOSITION_REQUIRED` fail-closed behavior in `_decompose`
  (raised when a decomposition needs more cells than available) is
  unchanged and must still fire per kind-group exactly as it would have
  fired for the combined span before this fix — do not silently swallow it.
- Total hours reported for PRE_PLAN days (sum across both letters) must
  equal what the combined pre-fix calculation would have summed — this fix
  changes attribution (which column/letter), not the total.
- `RetroactiveAbsenceRejected` and its current HTTP behavior
  (`api/errors.py`) are untouched by this Task — see section 0.

## 4. TASK_SCOPE

Production files allowed:
- `rota/application/schedule_export.py`

No other production file — `rota/planning/absence.py` and
`rota/persistence/absence_reference_repository.py` already carry `kind`
correctly through to this point; nothing there needs to change. `api/errors.py`
is explicitly out of scope per section 0.

Test files:
- `tasks/ROTA-T046/brief.md`
- `tests/test_t020.py` (existing PRE_PLAN/absence print tests live here —
  see `test_t20_19_overlapping_leave_and_sick_prints_c_only` and neighboring
  cases for the file's existing fixture helpers; reuse them)

Explicitly out of scope:
- `api/errors.py`, `rota/persistence/absence_reference_repository.py`,
  `api/routers/durable_inputs.py` (Part A, removed — see section 0);
- Any change to `_post_plan_pair`'s own logic (already correct);
- Any change to how `source_mode`/`kind` are resolved upstream
  (`rota/planning/absence.py`, `rota/persistence/absence_reference_repository.py`)
  — this is a print-layer attribution fix only.

## 5. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `rota/application/schedule_export.py`
  (`_decompose_pre_plan`, `_absence_pairs_for_employee`)
- REASON: confirm before implementation that `_decompose_pre_plan` has
  exactly one caller (`_absence_pairs_for_employee`) so the grouping change
  cannot silently affect an unrelated call path. Codex R1 audit already ran
  this and confirmed it (`tests_r1.txt`); reconfirm on this exact HEAD if the
  file changed since.

## 6. Minimum test matrix

1. **PRE_PLAN_SICK_LEAVE_PRINTS_C** — NEW TEST REQUIRED. An employee with a
   PRE_PLAN SICK_LEAVE span (recorded before the first accepted plan) must
   show `C1`/`C2`/`C~`-family codes in `wyk`, and the row's `l4_hours` must
   be `> 0` while the incorrect `urlop_hours` for that span is `0`.
2. **PRE_PLAN_LEAVE_GRANTED_STILL_PRINTS_U** — existing behavior for
   LEAVE_GRANTED PRE_PLAN days must be unchanged (regression guard) —
   reuse/confirm the existing PRE_PLAN LEAVE_GRANTED fixture
   (`test_t020.py`, the test using `_grant_leave` with default
   `kind=LEAVE_GRANTED`) stays green with `U`-family codes.
3. **PRE_PLAN_MIXED_KINDS_SAME_EMPLOYEE** — NEW TEST REQUIRED. One employee
   with both a PRE_PLAN LEAVE_GRANTED period and a separate PRE_PLAN
   SICK_LEAVE period in the same month: LEAVE_GRANTED days print `U`-family,
   SICK_LEAVE days print `C`-family, `urlop_hours` and `l4_hours` both
   reflect their own correct portion, and the employee's total `wyk_hours`
   for the month is unchanged versus before this fix (attribution changes,
   total does not).
4. **PRE_PLAN_DECOMPOSITION_STILL_FAILS_CLOSED_PER_KIND** — a PRE_PLAN span
   for one kind that cannot be decomposed into available codes still raises
   `ABSENCE_DECOMPOSITION_REQUIRED` (confirm existing coverage of this error
   path in `test_t020.py` still passes; add one case scoped to a single kind
   group if no existing case is easily adaptable).

Codex R1 confirmed all four items above as the correct, still-needed matrix
(three real classes: pure L4, pure urlop, mixed; plus the existing
fail-closed case) — unchanged from R1, reproduced here as the Task's sole
matrix.

## 7. Retained regressions / quality gates

- `tests/test_t020.py` full file green (all existing PRE_PLAN/POST_PLAN
  print cases); new tests green.
- `ruff check rota/application/schedule_export.py tests/test_t020.py`
- `git diff --check`

Full suite is optional, not a default gate for this narrow corrective fix.

## 8. Process

One small corrective fix, one implementation/review unit, no checkpoint
split. After PASS on this brief: implementation, then targeted matrix +
retained regressions + quality gates + independent exact-SHA implementation
audit (Codex) + architect exact-SHA review. Merge remains an explicit owner
action — never on CC's own initiative even after green backend + Codex.

## 9. Final preimplementation verification

Independent verification of this exact HEAD should answer:

1. Is Part A (the `api/errors.py`/`RetroactiveAbsenceRejected` change)
   fully absent from this contract — no production file, no test, no scope
   entry referencing it?
2. Does the fix preserve the correct monthly TOTAL (only the Urlop/L4
   attribution changes), and does it correctly handle an employee with both
   kinds of PRE_PLAN absence in the same month?
3. Does the fix stay entirely inside `rota/application/schedule_export.py`,
   with no solver/domain/persistence-layer change?

Required verdict:
- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` only for a concrete contradiction in this contract.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

## 10. EXACT TASK_SCOPE

Mechanical restatement of section 4 for backend.py's parser (bare paths, no
formatting).

TASK_SCOPE:
- tasks/ROTA-T046/brief.md
- rota/application/schedule_export.py
- tests/test_t020.py
