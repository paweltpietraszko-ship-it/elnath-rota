# ROTA-T023 — OWNER DECISION: ABSENCE TIMING AND PLAN/WYK

DATE: 2026-08-22
STATUS: ACCEPTED OWNER DECISION — ARCHITECT MUST INCORPORATE
SCOPE: T023-R3-3, T023-R3-5 and their direct PLAN/WYK consequences

## 1. No retroactive schedule mutation

- Rota does not modify the schedule retroactively.
- An absence cannot be applied to a shift that has already taken place.
- A `REALIZED` shift remains immutable WYK truth.
- Saving L4/leave over an already completed/REALIZED shift is not an accepted conflict state requiring numerical interpretation; the operation must not create that state.
- REPLAN changes the schedule only from the moment the coordinator accepts it. Earlier days and shifts remain unchanged.

## 2. Planned leave known before PLAN

- When the coordinator already knows about approved leave, the coordinator records the leave in the control panel before PLAN.
- The solver treats the Employee as unavailable on the leave dates and does not use that Employee for operational demand coverage on those dates.
- T020 presents the leave in WYK using the existing configured Site legend/allocation rules.
- Binding example: approved leave Monday through Friday inclusive is presented in the selected days as `U1`, `U1`, `U2`, consistently with the previously accepted 40-hour example and the Site's 12-hour regime.
- These presentation entries are not operational Assignments and do not cover ShiftDemand.

## 3. Sickness learned after an accepted PLAN

- Sickness is not planned in advance.
- When the Employee later provides L4, the coordinator records the absence and starts REPLAN.
- REPLAN must preserve the Employee's previously planned shift as the PLAN/reference presentation fact.
- T020 writes `C` in WYK under the shift the Employee was supposed to work.
- Operational demand must be covered by another eligible Employee; the absent Employee's preserved PLAN/C presentation is not operational coverage.
- The accepted REPLAN takes effect prospectively; it does not change completed days.

## 4. Contract impact

- The architect must distinguish the pre-PLAN approved-leave path from the post-PLAN sickness/replan path.
- A single rule requiring a previously adopted Employee schedule for every absence does not describe the approved-leave-before-PLAN case.
- A REALIZED-overlap arithmetic choice is not required: Rota must prevent creation of the retroactive conflicting state.
- This document records product behavior only. It does not select schema, DTO, repository or UI architecture.

## 5. Gate

CC remains blocked until the architect incorporates these decisions into the T023 contract and a narrow Codex audit passes their direct consequences.
