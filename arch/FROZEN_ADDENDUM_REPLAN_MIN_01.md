# FROZEN PRODUCT CONTRACT ADDENDUM — REPLAN-MIN-01

ADDENDUM_ID: REPLAN-MIN-01
DATE: 2026-08-12
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
APPLIES_TO: ELNATH ROTA arch/spec.md v0.4 + owner decisions through 2026-08-10
SOURCE_GAP_SHA: 7ac0fd634ee59ed6d0a3d2f1dab2169519fe094e
OWNER_DECISION_SOURCE: direct owner decision in architecture session 2026-08-12

## PRECEDENCE

This addendum is a narrow amendment to the Frozen Product Contract.

For REPLAN behavior only, `REPLAN-MIN-01` below takes precedence over any earlier statement or implementation that allows redistributable PLANNED assignments to be rearranged without a minimal-change preference.

All existing HARD constraints, ASSIGN-03, ASSIGN-04, TARGET-01 and all other frozen rules remain unchanged.

This addendum does not change initial planning from an empty schedule. It applies to every REPLAN of an existing schedule.

## OWNER DECISION

Literal product decision:

"Każdy replan musi kończyć sie minimalnymi zmianami grafiku przy jakich uda sie go ustalić."

Meaning in product terms:

Every REPLAN must preserve the existing schedule as much as possible. The solver may change only as many existing assignments as are necessary to obtain a valid replanned schedule.

## REPLAN-MIN-01 — MINIMAL RESHUFFLE

Priority order for every REPLAN:

1. Satisfy all HARD constraints and existing non-negotiable preservation rules.
2. Among all HARD-valid replanned schedules, minimize the number of changed baseline Assignment placements.
3. Only among schedules with the same minimum reshuffle count apply TARGET-01 and the existing ordinary SOFT ranking.

Therefore:
- no improvement in target_hours, weekend fairness, holiday fairness, D/N preference, DAY_SHIFT_OFF quality or LEAVE_PLAN quality may justify one additional reshuffled baseline assignment;
- minimal reshuffle is not a HARD constraint: if a change is necessary to obtain any HARD-valid complete schedule, that change is allowed;
- minimal reshuffle is not implemented as an arbitrary numeric weight relative to TARGET_DEVIATION_WEIGHT or other SOFT weights;
- the ordering is lexicographic: HARD validity first, reshuffle count second, ordinary SOFT third.

## UNIT OF RESHUFFLE

Reshuffle is counted per baseline demand placement, not per employee.

Baseline for comparison:
- an existing Assignment with role=PRIMARY;
- state=PLANNED;
- frozen=false;
- `covers_demand_id` present;
- the Assignment is otherwise in the redistributable REPLAN set.

For one such baseline Assignment:
- unchanged = the final replanned schedule assigns the same `covers_demand_id` to the same `employee_id`;
- changed = the final replanned schedule assigns that `covers_demand_id` to a different employee, or the baseline placement cannot remain and is replaced;
- internal Assignment identity/row id does not matter if the same employee still covers the same demand.

A baseline Assignment that must move because keeping it would violate HARD still counts as a changed placement, but the change is permitted.

A ShiftDemand that had no baseline redistributable PRIMARY placement is not itself counted as a reshuffle merely because REPLAN assigns it. Any additional movement of existing baseline placements required to cover it is counted normally.

The rule is about preserving people's existing planned shifts, not preserving database row identities.

## SCOPE

REPLAN-MIN-01 applies to every REPLAN, regardless of trigger, including but not limited to:
- sickness/absence;
- new unavailability;
- coordinator change that requires replanning;
- any other supported invocation of REPLAN on an existing schedule.

It does not apply to first-time planning where no existing schedule placement exists to preserve.

## RELATION TO EXISTING RULES

ASSIGN-03 remains stronger: REALIZED work MUST NOT be changed by REPLAN.

ASSIGN-04 remains stronger: future frozen Assignment MUST NOT be changed by REPLAN.

HARD constraints remain stronger than REPLAN-MIN-01.

TARGET-01 remains SOFT and is evaluated only after the minimum reshuffle count has been fixed.

Existing ordinary SOFT ranking remains unchanged and is used only to rank candidates tied on minimum reshuffle count.

## MULTIPLE CANDIDATES

If several FEASIBLE candidates have the same minimum reshuffle count, existing SOFT ranking may distinguish them.

If several candidates remain equivalent after ordinary SOFT ranking, PlanningEngine may return the existing allowed candidate set according to the Frozen Product Contract.

A candidate with a larger reshuffle count must not outrank a candidate with a smaller reshuffle count merely because its ordinary SOFT score is better.

## NON-GOALS

REPLAN-MIN-01 does not:
- freeze all PLANNED Assignments;
- prohibit necessary changes;
- redefine HARD;
- redefine TARGET-01;
- introduce a user-facing approval step;
- change the meaning of REALIZED or frozen;
- change the regression oracle for initial planning merely because REPLAN gained this rule.

## ACCEPTANCE SEMANTICS

A correct implementation must demonstrate at least:
- if one baseline assignment can be replaced while every other baseline assignment remains unchanged and HARD is satisfied, a solution changing two or more baseline placements is not an acceptable REPLAN result;
- when two solutions have the same minimum reshuffle count, existing TARGET/SOFT ranking may choose between them;
- if no HARD-valid schedule exists at reshuffle count N but one exists at N+1, REPLAN may use N+1;
- the minimal-change rule applies for every REPLAN trigger, not only absence;
- REALIZED and frozen assignments remain untouched exactly as before.

## PROCESS / ANTI-DRIFT

This addendum exists because the previous frozen contract specified what REPLAN must not move but did not define a positive minimal-change objective.

No implementer, auditor or model may replace this rule with a different weighting policy or infer an exception by trigger without a new explicit owner decision.
