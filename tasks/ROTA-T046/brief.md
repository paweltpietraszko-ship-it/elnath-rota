# ROTA-T046 — two small, independent corrective fixes

STATUS: DRAFT — CC READ-ONLY UNTIL PASS
BASE_PRODUCT_SHA: `HEAD` at brief time (confirm exact SHA before implementation)
ORIGIN: findings 1 and 9, `project_small_findings_backlog_2026-08-31` (CC/Paweł
evaluator dry-run session, 2026-08-31/2026-09-01) — no separate arch/ finding
doc exists for either, both are small, code-grounded, single-file fixes found
by direct reading, not by a Wariant A/B generator run.

No production implementation may start before independent PASS on this exact
contract HEAD.

This bundles two unrelated, independent, non-overlapping small fixes into one
Task because both are trivial in scope and neither touches a file the other
does. They are verified and reviewed as two separate checkpoints; either may
land without the other being ready.

---

## Part A — `RetroactiveAbsenceRejected` leaks as an unhandled HTTP 500

### A.0 Origin and root cause (confirmed by reading, not guessed)

`rota/persistence/absence_reference_repository.py:81-84` defines
`RetroactiveAbsenceRejected` — correct, intentional business logic (own unit
tests already pass in `tests/test_t023.py`): a new/expanded active
SICK_LEAVE/LEAVE_GRANTED write that would newly cover a non-CANCELLED PRIMARY
work period that already started, or a REALIZED PRIMARY Assignment, is
rejected before any persistence (raised inside `check_retroactivity`, called
from `capture_reference_if_applicable`, itself called from
`rota.application.durable_inputs.append_availability`).

The shared exception-to-HTTP mapping table, `api/errors.py::_STATUS_BY_EXCEPTION`
(brief.md section 3.2: "one shared helper, never per-router ad-hoc handling"),
simply has no entry for `RetroactiveAbsenceRejected`. Both callers of
`append_availability` — `create_availability` and `update_availability` in
`api/routers/durable_inputs.py` (lines ~228-238, ~249-261) — already route
every exception through `to_http_exception(exc)`, which falls through to the
generic `return HTTPException(status_code=500, detail=f"unexpected error: {exc}")`
for any exception type not in the table. First seen in Wariant A's
`coordinator_report.json` (seed16, seed18,
`tasks/ROTA-T043/round_01/tests/failures/seed16-crash.json`).

### A.1 What must change

Add exactly one entry to `api/errors.py::_STATUS_BY_EXCEPTION`:

- import `RetroactiveAbsenceRejected` from
  `rota.persistence.absence_reference_repository`;
- map it to **409** — matching this file's existing precedent for "this write
  conflicts with already-committed/realized state"
  (`ScheduleVersionNotWorking`, `NonEditableScheduleVersion`,
  `SiteRegimeChangeRejected` are all 409 in the same table), not 400/422.

No other change. `to_http_exception` itself, `check_retroactivity`,
`capture_reference_if_applicable`, and both router endpoints are otherwise
untouched — the shared-helper pattern already routes every exception through
one place, so this is a pure table addition.

### A.2 TASK_SCOPE (Part A)

Production files allowed:
- `api/errors.py`

Test files:
- `tests/test_t023.py` (existing `RetroactiveAbsenceRejected` unit coverage
  lives here — read first, add an HTTP-level test near it or in an existing
  API-level absence test file if one already exercises this endpoint;
  do not create a new test module for one assertion)

Explicitly out of scope:
- `rota/persistence/absence_reference_repository.py` (the domain exception
  and its raising logic are correct and untouched);
- `api/routers/durable_inputs.py` (both endpoints already correctly funnel
  through `to_http_exception`; no per-router handling is added, per
  brief.md section 3.2).

### A.3 Minimum test matrix (Part A)

1. **RETROACTIVE_REJECTED_RETURNS_409** — NEW TEST REQUIRED. Drive
   `POST /api/workspace/employees/{id}/availability` (or the PATCH
   equivalent) through the real FastAPI app with a payload that reproduces
   `RetroactiveAbsenceRejected` (an active SICK_LEAVE/LEAVE_GRANTED write
   newly covering an already-started PLANNED or REALIZED PRIMARY —
   `tests/test_t023.py`'s existing domain-level reproducer shows the exact
   setup). Assert `response.status_code == 409` and the response body's
   `detail` is the exception's own message (not a generic "unexpected
   error" string).
2. **Existing `tests/test_t023.py` `RetroactiveAbsenceRejected` unit tests**
   stay green, unchanged — confirms the domain exception itself is untouched.

---

## Part B — PRE_PLAN SICK_LEAVE prints as "U" (urlop) instead of "C" (chorobowe)

### B.0 Origin and root cause (confirmed by reading the code AND the actual
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

### B.1 What must change

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

### B.2 Preserve exactly (frozen, do not regress)

- `_post_plan_pair`'s existing correct `"C"`/`"U"` branching is untouched.
- The `ABSENCE_DECOMPOSITION_REQUIRED` fail-closed behavior in `_decompose`
  (raised when a decomposition needs more cells than available) is
  unchanged and must still fire per kind-group exactly as it would have
  fired for the combined span before this fix — do not silently swallow it.
- Total hours reported for PRE_PLAN days (sum across both letters) must
  equal what the combined pre-fix calculation would have summed — this fix
  changes attribution (which column/letter), not the total.

### B.3 TASK_SCOPE (Part B)

Production files allowed:
- `rota/application/schedule_export.py`

No other production file — `rota/planning/absence.py` and
`rota/persistence/absence_reference_repository.py` already carry `kind`
correctly through to this point; nothing there needs to change.

Test files:
- `tests/test_t020.py` (existing PRE_PLAN/absence print tests live here —
  see `test_t20_19_overlapping_leave_and_sick_prints_c_only` and neighboring
  cases for the file's existing fixture helpers; reuse them)

Explicitly out of scope:
- Any change to `_post_plan_pair`'s own logic (already correct);
- Any change to how `source_mode`/`kind` are resolved upstream
  (`rota/planning/absence.py`, `rota/persistence/absence_reference_repository.py`)
  — this is a print-layer attribution fix only.

### B.4 Minimum test matrix (Part B)

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

---

## WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS (Part A): `api/errors.py` (`_STATUS_BY_EXCEPTION`, `to_http_exception`)
- TARGETS (Part B): `rota/application/schedule_export.py`
  (`_decompose_pre_plan`, `_absence_pairs_for_employee`)
- REASON: confirm before implementation that `to_http_exception` genuinely
  has exactly one call site pattern (both `durable_inputs.py` endpoints
  already route through it — no other router reimplements its own mapping
  for `RetroactiveAbsenceRejected`), and that `_decompose_pre_plan` has
  exactly one caller (`_absence_pairs_for_employee`) so the grouping change
  cannot silently affect an unrelated call path.

## Retained regressions / quality gates

- Part A: `tests/test_t023.py` full file green; new HTTP-level test green.
- Part B: `tests/test_t020.py` full file green (all existing PRE_PLAN/
  POST_PLAN print cases); new tests green.
- `ruff check api/errors.py rota/application/schedule_export.py tests/test_t023.py tests/test_t020.py`
- `git diff --check`

Full suite is optional, not a default gate for these two narrow corrective
fixes.

## Process

Two independent small corrective fixes, one implementation/review unit each,
no checkpoint split beyond the Part A / Part B separation above (they may be
implemented and verified in either order, or in parallel, since they touch
disjoint files). After PASS on this brief: implementation, then targeted
matrix + retained regressions + quality gates + independent exact-SHA
implementation audit (Codex) + architect exact-SHA review. Merge remains an
explicit owner action — never on CC's own initiative even after green
backend + Codex.

## Final preimplementation verification

Independent verification of this exact HEAD should answer:

1. Part A: does the fix add exactly one table entry (no per-router
   exception handling introduced), and is 409 the right status code by this
   file's own existing precedent?
2. Part B: does the fix preserve the correct monthly TOTAL (only the
   Urlop/L4 attribution changes), and does it correctly handle an employee
   with both kinds of PRE_PLAN absence in the same month?
3. Do both parts stay entirely inside their one allowed production file each,
   with no solver/domain/persistence-layer change?

Required verdict:
- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` only for a concrete contradiction in this contract.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

## EXACT TASK_SCOPE

Mechanical restatement for backend.py's parser (bare paths, no formatting).

TASK_SCOPE:
- tasks/ROTA-T046/brief.md
- api/errors.py
- rota/application/schedule_export.py
- tests/test_t023.py
- tests/test_t020.py
