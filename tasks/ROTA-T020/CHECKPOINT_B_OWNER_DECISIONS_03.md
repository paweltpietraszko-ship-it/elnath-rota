# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 03 — PLAN/WYK absence semantics

STATUS: FROZEN OWNER DECISION — SUPERSEDES B-PD-01 INTERPRETATION FROM CHECKPOINT_B_OWNER_DECISIONS_01.md
DATE: 2026-08-20
TASK_ID: ROTA-T020
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
PARENT_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md
SUPERSEDES_IN_PART: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_01.md

This record captures the owner's clarification made after Checkpoint A acceptance. It corrects the earlier interpretation that leave/sickness on the printed Site should be treated as a simple absence of planned work.

## 1. Core owner rule

For a LOCAL employee, leave or sickness does **not** erase the employee's monthly PLAN.

The employee still has a normal monthly PLAN corresponding to the monthly work norm / planned-hours requirement. Absence is represented in WYK against those planned positions.

Binding owner example:

- monthly PLAN / norm: `168h`;
- the employee remains planned for `168h`;
- WYK may contain, for example, `144h` represented as sickness `C`;
- the remaining `24h` may be normal performed work, according to the actual schedule state.

Therefore the product meaning is NOT:

`absence -> remove planned hours`

It is:

`PLAN remains the normal planned schedule; WYK records how those planned positions were actually accounted for/presented, including U/C.`

## 2. Cell-level example

On a 12h Site a sickness position may be represented as:

- PLAN: `D1`
- WYK: `C1`

The PLAN position is not blank merely because the employee was sick.

Analogously, a longer sickness period may occupy many planned positions while the employee still has the full monthly PLAN expected for that month.

The same structural principle applies to leave presentation: PLAN is preserved; WYK carries the appropriate `U` presentation for the corresponding planned positions.

## 3. Consequence for the earlier B-PD-01 closure

The statement in `CHECKPOINT_B_OWNER_DECISIONS_01.md` that T020 should treat leave as simply "no work on this Site" is superseded and MUST NOT be used for Checkpoint B design or implementation.

T020 must not fabricate site-local `8h` absence amounts from T018 WorkBalance accounting, but it also must not erase planned schedule positions because an Availability record exists.

The accepted 40h visual example remains a presentation example of this same PLAN/WYK structure:

- PLAN: `D1 / D1 / N2` = `40h`;
- WYK: `U1 / U1 / U2` = `40h`.

It is not evidence that PLAN should disappear during leave.

## 4. Solver / planning boundary

The owner explicitly states that the planner/solver is expected to preserve the employee's monthly planned-hours requirement even when a large part of the month is represented in WYK as sickness/leave.

T020 itself is an export/read task and MUST NOT silently invent this PLAN if the persisted planning model does not contain enough information to derive it correctly.

Therefore, before the production Checkpoint B contract is frozen, the architect/Codex predesign audit must verify whether the current planner + ScheduleVersion/Availability model already represents this owner rule correctly.

If current planning semantics instead reduce or remove the employee's PLAN because of `LEAVE_GRANTED` / `SICK_LEAVE`, that is a real product-contract mismatch outside the PDF renderer and requires an explicit planning amendment/task. It must not be hidden inside T020 export logic.

## 5. One-day sickness clarification

The owner additionally states that a one-day sickness is atypical in the target protection/security domain and, when such an exceptional case requires planning interpretation, the solver should ask the coordinator rather than guess an automatic treatment.

This is a planning requirement, not authorization for T020 to change solver behavior.

## 6. LOCAL / EXTERNAL row rule remains unchanged

`CHECKPOINT_B_OWNER_DECISIONS_02.md` remains valid:

- enabled LOCAL employee -> always has a row on the Site/month print, even with zero actual Assignment rows;
- EXTERNAL_SUPPORT -> has a row only if actually assigned on that Site/month;
- EXTERNAL_SUPPORT with no Assignment -> no empty row.

For a LOCAL row, a lack of worked Assignment does not by itself imply an empty PLAN if the employee is on leave/sick. PLAN/WYK must follow the owner rule above.

## 7. Implementation hold

This document closes the meaning of PLAN/WYK for absence presentation but deliberately does not claim that the current solver already implements it.

Checkpoint B production CC must not encode a compensating fake PLAN in the renderer. The next architect step is to mechanically inspect current planning behavior against this owner rule and freeze the production B contract only after that boundary is explicit.
