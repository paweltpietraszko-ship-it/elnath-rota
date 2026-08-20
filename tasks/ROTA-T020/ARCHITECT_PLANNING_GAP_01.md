# ROTA-T020 — ARCHITECT PLANNING GAP 01

STATUS: ACCEPTED BLOCKING FINDING — CHECKPOINT B HELD
DATE: 2026-08-20
TASK_ID: ROTA-T020
AUDIT_COMMIT: a99d8d2848e10e70f47388125e00cfd557f06c55
AUDITED_HEAD: 38b30539955f5793a8a59a274ca3f98c003825dc
REPORT: tasks/ROTA-T020/round_01/tests/tests_r4.txt

## 1. ARCHITECT DECISION

Codex Round 4 finding `FAIL — PLANNING CONTRACT GAP` is ACCEPTED.

The finding is product/architecture blocking, not a renderer defect.

T020 Checkpoint B MUST NOT be frozen for production implementation until the planning gap below is closed by a separate planning contract and implementation.

Checkpoint A remains accepted and frozen. No accepted visual artifact is invalidated by this finding.

## 2. FROZEN OWNER SEMANTICS THAT CURRENT PLANNING DOES NOT REPRESENT

For a LOCAL Employee, excused absence does not erase the nominal monthly PLAN.

Example owner semantics:

- monthly PLAN / norm: 168h;
- WYK may contain 144h represented as sickness `C`;
- the remaining 24h may be ordinary realized work;
- PLAN remains 168h rather than collapsing to 24h or 0h;
- for a 12h Site an ordinary absence position can therefore be visually represented as `PLAN D1 / WYK C1` when that is the nominal planned position.

The same structural rule applies to granted leave using `U` in WYK.

`U/C` describe execution/presentation of nominal planned positions. They are not permission to delete those positions from the employee's monthly PLAN.

## 3. VERIFIED CURRENT-MODEL GAP

Round 4 established that the current model cannot generally produce or persist that truth:

1. `SICK_LEAVE` and `LEAVE_GRANTED` are HARD availability blockers for Assignment eligibility.
2. A blocked Employee therefore receives no Assignment for the affected demand.
3. `SICK_LEAVE` additionally reduces the solver TARGET used by the objective; a full-month 168h case can reduce that effective target to 0.
4. `LEAVE_GRANTED` leaves the live target number intact but still blocks Assignment creation, so nominal PLAN positions are still absent.
5. REPLAN can redistribute an earlier PLANNED Assignment to another Employee, so an old parent snapshot is not a canonical current nominal PLAN layer.
6. Availability stores absence kind/range but not the missing nominal demand/shift/intervall or D/N position.
7. When absence is known before the first PLAN there is no historical ScheduleVersion from which a renderer could recover the missing nominal position.

Therefore the current ScheduleVersion + Assignment + Availability model has no canonical general source for `PLAN D1 / WYK C1` or `PLAN D1 / WYK U1`.

## 4. FORBIDDEN T020 WORKAROUNDS

T020 Checkpoint B MUST NOT close this gap by:

- inventing nominal PLAN rows in the export read model;
- deriving a D/N position only from target_hours;
- selecting an arbitrary historical parent Assignment as the PLAN source;
- treating `current parent = PLAN` and `current child = WYK`;
- fabricating demand ids or intervals from Availability;
- changing accepted PDF symbols to hide the missing planning truth;
- recomputing a second solver inside the exporter.

The exporter must read canonical planning truth after the planning contract is fixed.

## 5. REQUIRED PLANNING CONTRACT BEFORE T020-B

A separate planning contract must define and test the smallest canonical representation that supports all of the following without creating a second scheduling system:

P1. Full nominal monthly PLAN remains representable for LOCAL Employees despite SICK_LEAVE / LEAVE_GRANTED.

P2. Absence known before the first PLAN still produces deterministic nominal PLAN positions up to the applicable monthly planning target/norm.

P3. Absence added after an existing plan does not destroy the nominal position needed for later PLAN/WYK presentation.

P4. Actual coverage may still be assigned to another eligible Employee; nominal employee PLAN and actual Site coverage must not be conflated.

P5. WYK can deterministically associate U/C with the corresponding nominal planned position, including its real interval/work-period provenance.

P6. Full-month absence is representable without collapsing the owner's nominal PLAN to zero.

P7. REPLAN preserves the required nominal-plan semantics while still allowing operational coverage to change.

P8. Existing HARD rule meaning remains explicit: an absent Employee must not be treated as actually eligible to perform the operational shift merely so that a PLAN row can be printed.

P9. WorkBalance/accounting and T018 semantics are not silently redefined as a side effect. Any required change must be explicit in the planning contract.

P10. A one-day sickness case identified by the owner as exceptional must not be guessed automatically; the planning contract must surface the required coordinator decision rather than inventing a normal absence decomposition.

## 6. ARCHITECTURE BOUNDARY

The planning fix must be designed before choosing implementation details for T020-B.

It must not become:

- a second solver;
- a second ScheduleVersion history;
- an export-only planning table;
- an HR/payroll subsystem;
- a generic workflow/event framework;
- a PDF-owned source of scheduling truth.

The minimal representation may extend existing planning/schedule persistence if necessary, but the exact representation is NOT frozen by this finding.

## 7. CHECKPOINT STATUS

- Checkpoint A: ACCEPTED / FROZEN.
- B-PD-02 row-population decision: CLOSED by owner.
- T020 visual B work: BLOCKED by planning gap.
- Production CC for T020-B: NOT AUTHORIZED.
- Next required step: architect planning contract + independent preimplementation audit.

Only after that planning contract is implemented and independently accepted may the architect freeze the full T020 Checkpoint B production contract.
