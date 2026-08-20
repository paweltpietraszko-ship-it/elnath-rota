# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 04

STATUS: OWNER PRODUCT DECISION — SUPERSEDES INCOMPLETE ABSENCE-PLANNING INTERPRETATIONS
DATE: 2026-08-20
TASK_ID: ROTA-T020
PREVIOUS_ARCHITECT_GAP: tasks/ROTA-T020/ARCHITECT_PLANNING_GAP_01.md

## 1. OWNER RULE — U/C DO NOT REMOVE NOMINAL PLANNED HOURS

For a LOCAL Employee, granted leave (`LEAVE_GRANTED`) and sickness (`SICK_LEAVE`) do not remove the Employee's nominal planned hours.

The solver must still assign nominal PLAN positions corresponding to the amount of the Employee's U/C absence.

Examples supplied by the owner:

- full-month U/C with monthly norm 168h -> solver still plans 168h for that Employee; WYK marks the corresponding positions as U or C;
- 40h U/C -> solver plans 40h of nominal positions corresponding to that absence; WYK marks those planned positions as U or C;
- the remainder of the Employee's monthly PLAN, if any, is planned normally so that the Employee's total nominal PLAN follows the applicable monthly planning norm/contract.

Absence therefore changes the execution/result presentation of the relevant nominal positions, not their existence in PLAN.

## 2. PLAN/WYK RELATION

For each planned position covered by U/C:

- PLAN retains the real nominal D/N position and its real interval/work-period provenance;
- WYK shows the corresponding U/C code according to the frozen T020 legend/decomposition rules;
- the U/C code must correspond to the value of the planned nominal position being replaced in WYK.

Example for a 12h Site when the nominal planned position is a 12h day shift:

- PLAN: `D1`
- WYK: `C1` for sickness, or `U1` for granted leave.

The exact D/N position must come from planning truth. It must not be invented by the exporter.

## 3. FULL-MONTH AND PARTIAL ABSENCE

Full-month absence is not a special case that collapses planning target or assignments to zero.

If the Employee's applicable monthly nominal PLAN is 168h and the entire month is U/C, the nominal PLAN remains 168h and WYK represents those 168h as U/C positions.

If only 40h are U/C, the solver must create/preserve nominal planned positions totaling 40h for the U/C portion, while the remainder of the Employee's nominal monthly PLAN is planned as ordinary work according to the normal planning rules.

## 4. OPERATIONAL COVERAGE REMAINS SEPARATE

An Employee on U/C must not become operationally eligible to perform the shift merely because the nominal PLAN position exists.

The Site still needs actual eligible coverage for the demand. Another Employee may therefore be assigned to perform the operational shift while the absent Employee retains the corresponding nominal PLAN position represented as U/C in WYK.

Nominal Employee PLAN and actual Site coverage are distinct planning truths and must not be conflated.

## 5. CURRENT IMPLEMENTATION IS NON-CONFORMING

The Codex Round 4 audit correctly established that the current model does not implement this owner rule:

- `SICK_LEAVE` / `LEAVE_GRANTED` currently HARD-block Assignment eligibility;
- full-month `SICK_LEAVE` can reduce the objective target from 168h to 0;
- full-month `LEAVE_GRANTED` can leave target=168h but still produce 0 Assignment positions;
- Availability alone does not preserve the missing nominal D/N position or its provenance.

Therefore the current implementation must change in planning before T020-B may rely on it.

## 6. NO EXPORT WORKAROUND

T020 renderer/export code must not fabricate the missing PLAN, infer D/N from target hours, or reconstruct a nominal schedule from arbitrary historical ScheduleVersion parents.

The planning layer must first persist/read canonical nominal positions for U/C.

## 7. OWNER COMMUNICATION RULE FOR UNDEFINED CASES

The architect and implementers must not infer missing product semantics from current code when the owner rule is not explicit.

When a case affects real scheduling behavior and the frozen owner material does not define it unambiguously, it must be surfaced as a product question to the owner before the behavior is frozen.

Technical implementation choices that do not change product behavior remain architect-owned and do not require owner questions.

## 8. RELATION TO PRIOR DECISIONS

This document supersedes any earlier wording that could be read as:

- U/C simply removing work from PLAN;
- U/C being represented only as an absence record with no nominal planned position;
- full-month sickness reducing the Employee's nominal monthly PLAN to zero.

`ARCHITECT_PLANNING_GAP_01.md` remains valid as a diagnosis that the current model is missing the required representation, but the present document is the authoritative owner semantics for the planning fix.

Checkpoint A remains accepted/frozen. T020 Checkpoint B remains blocked until the planning gap is implemented and independently accepted.
