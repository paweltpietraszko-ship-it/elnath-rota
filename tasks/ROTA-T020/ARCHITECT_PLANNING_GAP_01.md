# ROTA-T020 — ARCHITECT PLANNING GAP 01

STATUS: WITHDRAWN / NOT A T020 BLOCKER
DATE: 2026-08-20
TASK_ID: ROTA-T020
AUDIT_COMMIT: a99d8d2848e10e70f47388125e00cfd557f06c55
AUDITED_HEAD: 38b30539955f5793a8a59a274ca3f98c003825dc
REPORT: tasks/ROTA-T020/round_01/tests/tests_r4.txt
SUPERSEDED_BY: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md

## 1. WITHDRAWAL

The earlier architect conclusion `ACCEPTED BLOCKING FINDING — CHECKPOINT B HELD` is withdrawn.

Codex Round 4 correctly established a factual property of the current planning model: absent Employees do not receive a second nominal Assignment layer that mirrors U/C presentation. The audit itself remains valid evidence about the implementation.

The architectural blocker was created because the architect incorrectly inferred that T020 required such a nominal planning layer.

The owner has now corrected that premise.

## 2. AUTHORITATIVE OWNER CORRECTION

For T020:

- the operational solver continues to assign real Site coverage only to Employees eligible to work;
- U/C does not reduce the Site demand that must actually be covered;
- the absent Employee does not need a second operational or nominal Assignment merely for printing;
- T020 fills the LOCAL Employee's otherwise empty qualifying print cells using the frozen absence presentation decomposition;
- PLAN D/N and WYK U/C pairs created for absence are print symbols, not evidence of a real ShiftDemand Assignment;
- actual work cells still come from real Assignment/work-period provenance;
- T020 must not change WorkBalance, Assignment, ScheduleVersion, solver eligibility, or coverage accounting merely to create those symbols.

The authoritative source is `CHECKPOINT_B_OWNER_DECISIONS_05.md` and the original owner brief section `Urlop i chorobowe na wydruku`.

## 3. EFFECT ON ROUND 4

Round 4 is not deleted or declared technically wrong. Its finding answers the question it was asked: the current model does not persist the nominal absence PLAN layer that the architect had incorrectly required.

That missing layer is no longer a required product behavior for T020.

Therefore:

- `FAIL — PLANNING CONTRACT GAP` is NOT a current T020 blocker;
- no separate planning task is required merely to enable T020 U/C printing;
- no change to solver coverage semantics is authorized by T020;
- no second Assignment/history layer should be introduced for this purpose.

## 4. CHECKPOINT STATUS

- Checkpoint A: ACCEPTED / FROZEN.
- B-PD row-population decision: CLOSED.
- U/C presentation semantics: CLOSED by owner correction 05.
- T020 Checkpoint B architecture: OPEN FOR FULL CONTRACT DESIGN.
- Production CC: NOT YET AUTHORIZED until that full B contract is frozen and independently audited.
