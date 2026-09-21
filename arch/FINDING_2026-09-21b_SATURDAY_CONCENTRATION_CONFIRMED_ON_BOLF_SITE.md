# FINDING 2026-09-21 (correction/confirmation, round 2) — Saturday-shift concentration confirmed on the Bolf site object, in the ACTUAL regime (OCHRONA) and ACTUAL mechanism (add_ochrona_hours_fairness), superseding the original synthetic-only finding

STATUS: finding + reproduced root cause on a fully assembled site
object, NOT a design
document. Input for the architect (same role as other `arch/FINDING_*`
docs) — CC does not design the solver-engineering fix here.

DATA: all data is synthetic and created by the owner; "real object" and
"production" here mean a fully assembled site object and the owner's own
running instance, NOT a customer or real personal data. See
`arch/DATA_STATUS.md`.

Supersedes `arch/FINDING_2026-09-21_RARE_WEEKLY_SLOT_PINNED_TO_ONE_
EMPLOYEE.md` after the architect's own precheck (BOARD.md,
`ROTA-RARE-WEEKLY-SLOT-PINNED`) correctly flagged that finding's
synthetic repro (ORDINARY regime, one Saturday/month, cross-month
rotation framing) as unverified against the Bolf site's observed
symptom. This round re-investigated directly against the Bolf site's
stored data (read-only queries against the owner's own running
instance) and the original repro's regime
assumption was WRONG — corrected and reproduced below.

## Correction: the Bolf site is OCHRONA, not ORDINARY

Confirmed via read-only query: `sites.planning_regime = 'OCHRONA'` for
Bolf. Shift catalog (`standard_shifts`, read-only): one D shift
05:00-17:00 (12h) active Mon-Fri, one SEPARATE D shift 05:00-14:00 (9h)
active Saturday-only. 2 LOCAL employees, both `enabled=1`,
`can_work_24h=1`, no role restriction (`position_role_id`/
`allowed_roles` both NULL for both — matches Paweł's own confirmation
that both employees have identical eligibility), no `work_balance_
targets` rows for either (expected: OCHRONA doesn't require a target).
This means the ACTUAL mechanism in play is `add_ochrona_hours_fairness`
(equalizing each employee's total committed hours, weighted to dominate
rhythm+weekend+holiday combined) plus `add_weekend_fairness` as a
SUBORDINATE tie-break term — not `add_target_equity_fairness` as the
original finding assumed.

## Stored site data (read-only, 3 independently-planned months, zero absences confirmed by Paweł for January)

| Month | Employee A hours | Employee B hours | Saturday split |
|---|---|---|---|
| 2026-09 (4 Saturdays, even month) | 144 | 156 | Employee 2: all 4 Saturdays (36h) |
| 2026-10 (5 Saturdays) | 156 | 168 | Employee 2: all Saturdays (60h) |
| 2027-01, attempt 1 (5 Saturdays, fresh PLAN, `parent_version_id=NULL`) | 153 | 144 | Employee 1: all 5 Saturdays (45h) |
| 2027-01, attempt 2 (re-ran PLAN on the SAME unchanged input) | 144 | 153 | Employee 2: all 5 Saturdays (45h) |
| 2027-01, attempt 3 (re-ran PLAN again, same input) | 144 | 153 | Employee 2: all 5 Saturdays (45h) |

Confirmed no `availability_versions` rows at all for either employee
(zero absence/leave records) and identical `employees` rows
(`active_from`, `active_to`, `day_only` all equal) — the two employees
are genuinely, verifiably symmetric inputs. Paweł independently
confirmed January had zero absences from his own side before this
table was shown to him.

**The January flip between attempt 1 and attempts 2/3 is itself
important**: re-running PLAN on the exact same unchanged input flipped
WHICH employee got all the Saturdays. This rules out a fixed,
input-independent bias (e.g. lexicographic employee_id ordering always
winning) and points at CP-SAT's search order/internal state varying
between separate solver invocations even at `search_attempt=0`,
converging on *some* Saturday-concentrated solution each time rather
than a Saturday-spread one — not always the *same* one.

## Confirmed independently: a clean, minimal, matching synthetic reconstruction reproduces it too

Built the exact real shape (same two-StandardShift catalog, OCHRONA
regime, 2 fully symmetric employees, no absences, no targets) via
`tests.support.minimal_state.base_state` + `rota.application.assembler.
generate_profile_demands` + `rota.planning.engine.plan`:

- **2026-09 (30 days, 4 Saturdays — an even month)**: perfectly even
  result, 150h/150h total, 18h/18h Saturday (2 Saturdays each). This is
  why the FIRST reconstruction attempt (done before re-checking against
  the stored data) looked "fine" and seemed to contradict the original
  finding — September's arithmetic happens to admit a perfectly
  symmetric optimum, masking the issue.
- **2027-01 (31 days, 5 Saturdays — the Bolf site's actually-reported month)**:
  reproduced the same qualitative defect: 150h/147h total (a mere 3h
  gap — near the theoretical minimum, since exact equality is
  impossible with 12h/9h shift granularity), but Saturdays split 2/3
  instead of evenly-as-possible, in a clean, fully symmetric, absence-free
  synthetic run with no site-specific stored data involved at all.

## What this establishes

- Not a fixed pin to one specific employee (contradicts the original
  finding's framing) — it's a per-solve tendency to CONCENTRATE Saturday
  coverage onto fewer employees than necessary, even when total-hours
  cost is already at (or extremely near) its achievable minimum spread,
  and even when spreading Saturdays more evenly would cost nothing extra
  in total-hours terms.
- `add_ochrona_hours_fairness` is doing its declared job correctly
  (minimizing total committed-hours spread) — the gap is specifically in
  `add_weekend_fairness`, whose job is exactly to break ties among
  total-hours-equal solutions toward the more Saturday-balanced one, and
  which is not achieving that in practice for this shape (small
  employee pool, an odd/awkward number of Saturdays, two different
  shift durations).
- Reproducible in isolation, at full shape, without touching the running
  instance or needing the Bolf site's stored data again — see
  Reproduction below.

## Owner input, plain language (2026-09-21, offered to the architect as a candidate direction, not a decision)

Paweł's own proposal after reading this finding: "Nie można tego załatwić
prostym IF? Solver sprawdza, że pracownik miał poprzednią sobotę/niedzielę
pracującą i mu nie przydziela następnej?" (a simple rotation rule: don't
assign an employee this Saturday if they worked the previous one).

CC's honest assessment, not a decision: this is a more targeted, more
predictable direction than raising `WEEKEND_FAIRNESS_WEIGHT` alone --
for exactly Bolf's shape (2 eligible employees), "not the same
person as last Saturday" mechanically forces alternation, which IS an
even split in the 2-employee case. Three caveats before this becomes a
design, all standard territory for a solver-contract change (CC does not
resolve these, flagging for the architect):

1. **Month boundary**: the first Saturday of a month needs to know who
   worked the LAST Saturday of the PREVIOUS month -- technically
   available (same class of lookback `boundary_assignments`/
   `holiday_history` already do for other facts), but needs to actually
   be wired to a "last Saturday worked" fact, which doesn't exist today.
2. **Generalizes weakly beyond 2 employees**: "not the same as
   immediately previous" only forbids direct repetition -- with 3+
   employees it does not by itself guarantee even rotation over time
   (e.g. two employees could still alternate with each other while a
   third never gets picked). Bolf's case is 2 employees, where this
   reduces to exactly the fix needed, but the general mechanism the
   architect designs should account for larger rosters too.
3. **Must be SOFT with a fallback, not an unconditional HARD block** --
   direct, hard-won precedent in this project: `arch/` and BOARD.md
   history show T058's HARD third-consecutive-shift rule needed real
   OWNER-calibrated tuning after it silently produced infeasible plans
   in real edge cases (e.g. the only available employee this Saturday
   is exactly the one who worked last Saturday, everyone else genuinely
   unavailable). An unconditional HARD "never repeat" constraint risks
   the exact same failure mode -- this needs to be a preference that
   yields when there is no other feasible option, not a rule that can
   make a real month unsolvable.

## Open question for the architect (CC does not design this)

Same class of question as the original finding, now confirmed against
the fully assembled site object and its actual mechanism:

- Is `WEEKEND_FAIRNESS_WEIGHT` (currently 1, the smallest unit in the
  penalty hierarchy) simply too weak to reliably win the tie-break
  against CP-SAT's default search order, the same class of issue as
  `arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_
  SHORTFALL.md` diagnosed for `TARGET_EQUITY_WEIGHT`? That finding's own
  experiment technique (force a HARD cap on the relevant spread, check
  whether it's still trivially FEASIBLE at low cost) would directly
  test this here too — not run in this round, left for the architect/
  Codex iteration per CC's role.
- Does raising `WEEKEND_FAIRNESS_WEIGHT` (or restructuring its
  dominance relative to `ochrona_fairness_weight`, which currently
  already folds `WEEKEND_FAIRNESS_WEIGHT * weekend_bound` INTO the
  dominant term's own size — worth checking whether that construction
  itself is part of the problem, since it makes weekend_fairness's
  raw weight shrink in relative importance as the dominant term grows)
  fix this without the CP-SAT performance regression T058/T059 already
  documented for a different weight?
- Small pool size (2 employees) may make this qualitatively worse than
  it would be on a larger roster — worth checking whether the same
  effect appears with more employees before deciding this needs a
  targeted fix versus being an edge case of very small OCHRONA rosters.

CC's recommendation, stated plainly (not a decision): both reproductions
above (the Bolf site's own stored January data, and the clean synthetic
reconstruction of the same shape) are small, reproducible, and directly
actionable — an architect/Codex round can iterate against either without
needing further access to the running instance.

## Reproduction

Synthetic (no DB, no running-instance access): `SiteProfile` with two
`StandardShift(ShiftKind.D, ...)` entries — 05:00-17:00 `active_weekdays=
(1,2,3,4,5)` and 05:00-14:00 `active_weekdays=(6,)` — `Site.planning_
regime = SitePlanningRegime.OCHRONA`, 2 `LOCAL` `Employee`/
`SiteMembership` pairs with no target_hours, `rota.application.
assembler.generate_profile_demands(profile, date(2027,1,1))` for the
demand set, `rota.planning.engine.plan(state)`. Compare Saturday-hours
distribution across employees in the FEASIBLE candidate. Re-run for
`date(2026,9,1)` to see the contrasting even-month case.

Assembled-site comparison (if the architect wants to re-verify against
the Bolf site directly): site_id `SITE-c9aebae1ba32428f8ae9f7a90dc2dfed`,
`schedule_versions` for months 2026-09/2026-10/2027-01, `assignments`
joined on `schedule_version_id`, aggregate hours by `employee_id` and by
`start_datetime`'s weekday. Read-only, was reviewed live with Paweł's
explicit approval for this round; no data was modified.
