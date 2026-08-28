# ARCHITECT BRIEF — Employee silently omitted from the whole fairness objective when target_hours is missing for the planned month

Author: CC (implementer role). Origin: live reproduction on Paweł's own dev
object (Test1, `SITE-af2c7186283e4a4cbc3fb84b99fa1792`, September 2026),
during unrelated manual testing of ROTA-T040. Not requested as a task —
raised per CLAUDE.md "flag, don't fix" duty. No product code changed while
investigating; every claim below is reproduced against `rota_dev.db` and/or
a fresh `plan_month()` call, not inferred from reading code alone.

## 1. Symptom as reported by the owner

On a 5-person OCHRONA object (D_N_12H, all `target_hours=176` for
September), after adding then reverting an absence and running both REPLAN
and a full PLAN (Przelicz PLAN), the resulting schedule consistently gives
4 employees 168h each and 1 employee 48h. All 3 returned candidates (T017
diversity search) show the same aggregate split, though the actual
day-by-day assignments differ substantially between them (confirmed: 20%,
73%, 87% of (demand, employee) pairs differ pairwise — the T017 diversity
mechanism itself is working correctly, ruled out as a cause).

Owner's framing, verbatim and correct: "jaki grafik jest legalny jeśli
pracownik dostaje 48 godzin" and "trzeba spojrzeć na całość, jak solver
wybiera zasady, według czego je priorytetyzuje."

## 2. What was ruled out (tested directly, not assumed)

- **Not a stale/cached WORKING version** (unlike the earlier
  `ARCHITECT_BRIEF_SHIFT_CATALOG_STALE_WORKING_VERSION_2026-08-28.md`
  finding): a fresh, direct `plan_month()` call outside the UI, on the same
  DB, reproduces the exact same 168/168/168/168/48 split independently.
- **Not a broken diversity search**: the 3 candidates genuinely differ in
  who covers which day (20-87% of pairs), just not in the aggregate
  per-employee hour total.
- **Not an active absence**: the affected employee (`88bf7a0a-...`,
  "TestC") has *zero* `availability_versions` rows, ever — nothing
  restricts them.
- **Not a HARD load/rest cap specific to this employee**: `add_load_constraints`
  applies the same rolling-window `threshold` to every employee uniformly;
  it cannot explain why one specific person alone is capped while 4 others
  reach 168h.
- **Not a weighting/priority problem between SOFT terms** — this was my
  own first (wrong) hypothesis, tested and falsified directly:
  monkeypatching `solver.TARGET_EQUITY_WEIGHT` from 1 up to 2000 (a
  1000-2000x change) produced **zero change** in the outcome. If this were
  a rhythm-vs-equity weight competition, scaling equity's weight that hard
  would have flipped it. It didn't, which is what led to the real cause
  below instead of stopping at a plausible-looking wrong answer.

## 3. Root cause, confirmed by direct instrumentation of a live solve

Traced by wrapping `add_target_equity_fairness` and printing the
`effective_targets` dict it actually receives during a real `plan_month()`
call on the live object:

```
effective_targets: {'0ebac8ff-...': 176, '27fb44ba-...': 176,
                     '7661c3a4-...': 176, '86691eda-...': 176}
```

Only 4 of the 5 roster members are present. `88bf7a0a-...` ("TestC") is
missing entirely — not target 0, not target None-but-present, simply
absent from the dict.

Chain, file by file:

1. **`work_balance_targets` table**: TestC has a row for `month='2026-08-01'`
   but none for `month='2026-09-01'`. The other 4 roster members have rows
   for both months. A data gap for this one employee/month, not a code bug
   at this layer.

2. **`rota/application/assembler.py::_assemble_work_balances`** (decision
   tag `R3-11-D` in the existing comment): when
   `get_work_balance_target(conn, employee_id, month) is None` for the
   *exact planned month*, the employee is **deliberately, by design,
   omitted from `state.work_balances` entirely** — the comment states this
   is intentional so "missing target_hours must never block PLAN". A
   warning string is appended: `"missing target_hours for employee
   {id!r}: omitted from WorkBalance context"`.

3. **That warning never reaches anyone.** Every single call site of
   `assemble_planning_state()` in `rota/application/plan_ops.py` (checked
   all of them — lines ~134, 148, 308, 375, 426, 449) discards the second
   return value: `state, _ = assemble_planning_state(...)`. The warning is
   generated and then thrown away before it can reach `PlanResult.warnings`
   or any UI surface. The coordinator has **no way to learn** that an
   employee's data is incomplete for this month.

4. **`rota/planning/solver.py`** builds the *entire* fairness/target
   apparatus from `state.work_balances` only:
   - `_effective_targets(state)` — dict comprehension over
     `state.work_balances`, so an omitted employee is absent from the
     result, not present with value 0.
   - `_worked_hours_by_employee(...)` iterates `for employee_id in
     target_by_employee` — an omitted employee gets no `worked` expression
     built for them at all.
   - `add_target_equity_fairness` and the per-employee TARGET-01 deviation
     loop in `_add_combined_objective` both iterate over
     `target_by_employee`/`effective_targets` — an omitted employee
     contributes **zero** to either term, in either direction.

5. **Net effect**: the omitted employee remains fully eligible for real
   shift assignment (`site_memberships` is a completely separate
   eligibility path, unaffected by WorkBalance), but is **invisible to
   every fairness signal the objective has**. The solver is not
   "choosing" to be unfair to them — it mathematically cannot perceive
   that they exist as someone to balance hours for. It only assigns them
   real coverage when structurally forced to by HARD constraints
   (coverage, rest, night-streak), which is exactly the 48h residue
   observed. This is a **proven-OPTIMAL** result under the objective as
   actually constructed (`optimization_complete=True` on every run,
   including at inflated equity weights) — the model is doing precisely
   what it was told to do; what it was told to do has an unannounced gap.

## 4. Owner's UX point (2026-08-28, verbatim in substance)

"Masz rację ale UX jest słaby, koordynator będzie popełniać takie błędy a
solver je przemilczy." This is the sharper half of the finding and should
not be lost under the technical trace above: a missing `target_hours` row
for one employee/month is an easy, ordinary data-entry gap (forgetting to
roll it forward when a new month opens, or when an employee is added
mid-month) — not a rare edge case. As implemented, the *only* signal this
condition produces is a warning string that is architecturally guaranteed
to be discarded (every caller does `_`), so a coordinator has zero chance
of noticing before the schedule already looks unfair. The R3-11-D design
intent ("missing target must never block PLAN") is reasonable on its own,
but its downstream interaction with the fairness objective — total
invisibility, not graceful degradation — does not appear to have been
evaluated when that decision was made.

## 5. Scope note (why this needs the architect, not a quick CC fix)

This touches:
- `rota/application/assembler.py`'s WorkBalance assembly contract (R3-11-D).
- `rota/application/plan_ops.py` — 5+ call sites all discarding the same
  warning; fixing surfacing means deciding a plumbing shape once, not
  patching one call site.
- `rota/planning/solver.py`'s combined objective (`_effective_targets`,
  `_worked_hours_by_employee`, `add_target_equity_fairness`,
  `_add_combined_objective`) — whether an employee with a data gap should
  (a) still block PLAN after all, (b) get a synthesized/fallback target
  (and what value), or (c) stay excluded from WorkBalance but be forced
  into TARGET-01/equity some other way, is a product decision, not
  something to guess at implementation time.

Per the standing "when architect is needed" rule: this touches the
solver's objective construction and a frozen owner decision (R3-11-D) —
full process, not a quick patch.

## 6. Not yet done

No code changed. No fix proposed here beyond naming the exact mechanism.
`rota_dev.db`'s Test1/September object still has this data gap for TestC —
left as-is since it is the live reproducer for this brief; adding a
September `work_balance_targets` row for TestC would mask the very
condition this brief is about.
