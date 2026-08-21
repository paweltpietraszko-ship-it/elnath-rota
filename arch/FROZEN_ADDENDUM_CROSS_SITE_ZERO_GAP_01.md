# FROZEN PRODUCT CONTRACT ADDENDUM — CROSS-SITE-ZERO-GAP-01

ADDENDUM_ID: CROSS-SITE-ZERO-GAP-01
DATE: 2026-08-21
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_SHA: d50a9aa4dfb35ed479470bb7fb83ffca18ecc346
OWNER_DECISION_SOURCE: tasks/ROTA-T022/brief.md OWNER-T022-03 (HEAD 810c6fa0355f12a0895260cb11aa19dd869253d5)
APPLIES_TO: ELNATH ROTA arch/spec.md REST-01 / SHIFT-24 / T012 work-period pairing

## SUPERSESSION — EXACT SCOPE

This addendum is a narrow amendment to the Frozen Product Contract.

It supersedes only the REST-01 statements in `arch/spec.md` that currently
read, in product meaning:

- the same directional rest semantics apply same-site, cross-month and
  cross-site;
- a persisted earlier `required_rest_after_hours` snapshot of `0` is a legal
  rest wall, including across Sites.

Those statements remain true for every **positive** gap. They do **not**
authorize zero-time continuation of work from Site A onto a different Site B.

This addendum does not change `arch/spec.md` text or `arch/FROZEN.lock`.
Later T022 implementation must still not modify those files.

It does not introduce distances, travel-time configuration, a routing engine,
`Assignment.site_id`, or a new public DTO. ASSIGN-01 remains: Site is derived
through ScheduleVersion.

## OWNER DECISION

Literal product decision (OWNER-T022-03):

The 24h mechanism applies only to two consecutive H12 components performed on
the same Site. An Assignment ending on Site A and another Assignment starting
at exactly the same time on a different Site B cannot form one normal or
emergency 24h WorkPeriod: the employee cannot move between Sites with zero
time.

Automatic planning must reject that immediate cross-Site continuation even
when the earlier persisted `required_rest_after_hours=0` and even when the
employee has `can_work_24h=true` on either Site. Those values do not authorize
zero-time travel and the two Assignments must never be joined under one 24h
`work_period_id`.

A positive gap continues to be governed by the existing directional cross-Site
REST contract. Existing explicit manual REST-deviation recording/finalization
semantics are not reopened.

## CROSS-SITE-ZERO-GAP-01

For one employee, two work intervals on **different Sites** that abut
(`later.start == earlier.end`) are illegal automatic work.

Enforcement:

1. Automatic `plan()` / REPLAN / CP-SAT must not assign a current-Site demand
   that starts at the exact end of an `other_site_assignments` interval, nor
   the reverse (current-Site work ending at the exact start of other-Site
   work).
2. Independent HARD validation of a candidate must fail that same abutment.
3. The two intervals must never share a 24h `work_period_id`. Existing T012
   grouping by `work_period_id` must not merge them into one WorkPeriod.
4. `can_work_24h=true` and persisted rest `0` do not create an exception.
5. A **positive** cross-Site gap (`later.start > earlier.end`) keeps REST-01
   as already frozen: `gap >= earlier.required_rest_after_hours`, directional,
   using persisted provenance, not the current foreign SiteProfile.
6. Same-Site zero-gap remains the T012 / OWNER-T022-02 24h question. This
   addendum does not reopen same-Site pairing, emergency fallback order, or
   cross-month same-Site extension.
7. Missing other-Site CURRENT data still does not invent a warning or
   DECISION_REQUIRED (STATE-T012-01). The prohibition applies only to
   persisted/assembled other-Site facts that are actually present.

## CONDITION CODES — NO NEW STABLE CODE

Use existing codes only:

- zero-gap across different Sites → `REST-01`, even when
  `earlier.required_rest_after_hours == 0`;
- an attempt to treat that pair as normal/emergency 24h, or to write one
  shared 24h `work_period_id` onto those two Assignments → fail-closed with
  existing `WORK_PERIOD-01` / `SHIFT-24-PAIR-01` / `SHIFT-24-01` as the
  structural or qualification fact already requires; never a successful 24h
  pair;
- do **not** create a new condition code, travel code, or public DTO.

Manual correction that knowingly writes this REST-01 still follows the
existing T012 MAY-record path (Deviation + finalize confirmation +
`REST_OVERRIDE_RECORD` when REST-01 is present). T022 does not reopen that
path or invent a second override.

## SITE IDENTITY WITHOUT A NEW DTO

`Assignment` has no `site_id` (ASSIGN-01). Planning already distinguishes
Sites by collection:

- current `PlanningState` assignments and `boundary_assignments` are the
  planning Site (boundary is same-Site, other-month);
- `other_site_assignments` are other-Site CURRENT facts.

Zero-gap between a current/boundary period and an `other_site_assignments`
period is this addendum. Zero-gap between current and boundary remains
same-Site T012-C. Do not add `assembler.py`, `other_site_shift_demands`, or
persistence lookup inside the validator to recover a foreign Site id.

Two already-persisted other-Site rows that happen to abut each other are
outside this Site's solver. The current Site must not join them into a 24h
WorkPeriod of its own. It does not need a travel model to classify them.

## IMPLEMENTATION TASK_SCOPE FOR THIS BOUNDARY

This addendum does not expand T022 into a new architecture. The zero-gap
rule is enforced only in files already in the T022 candidate TASK_SCOPE:

- `rota/planning/work_periods.py` — grouping must not merge current-Site and
  other-Site components into one 24h period;
- `rota/planning/constraints.py` — REST edges against
  `other_site_assignments`; emergency pair literals stay same-Site demands;
- `rota/planning/validator.py` — independent `_check_rest` / malformed period
  checks;
- `rota/planning/solver.py` — `_solved_work_period_id` remains site-scoped;
  solver must not emit a shared 24h id across Sites;
- `rota/planning/eligibility.py` / `rota/planning/engine.py` only as already
  required for T022-F4 same-Site 24h; they do not grow a travel predicate;
- `tests/test_t022_planning_integrity.py` — the already-required zero-gap
  cross-Site oracles.

Do not add `rota/application/assembler.py` or a domain/schema change.

`rota/application/manual_edit.py` is not added. It already calls
`validator.validate()` and materializes REST-01 Deviations. The REST override
DecisionRecord continues to re-derive pairs from validator REST-01; T022
must keep that existing path able to see this REST-01 case by placing the
zero-gap predicate where `_check_rest` already decides REST-01, not by
opening a new manual-edit contract.

## OUT OF SCOPE

- changing positive-gap directional REST, ASSIGN-T012-01 provenance, or
  STATE-T012-01 missing-data silence;
- same-Site H12+H12 24h (OWNER-T022-02 / T012 Part C);
- LOAD-01 arithmetic, T013 raw conflict labels, T018 fallback order;
- distances, maps, or configurable travel time.
