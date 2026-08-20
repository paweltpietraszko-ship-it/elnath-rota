# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 04

STATUS: SUPERSEDED — DO NOT USE AS CURRENT PRODUCT CONTRACT
DATE: 2026-08-20
TASK_ID: ROTA-T020
SUPERSEDED_BY: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md

This document previously recorded an incorrect architect interpretation that required the operational solver to create/preserve nominal U/C PLAN Assignments for printing.

The owner corrected that interpretation.

Current authoritative semantics are in `CHECKPOINT_B_OWNER_DECISIONS_05.md`:

- solver keeps operational Site coverage semantics and does not need a second nominal absence Assignment layer;
- U/C does not reduce the Site demand that must actually be covered;
- T020 fills otherwise empty qualifying LOCAL employee print cells using the frozen absence presentation decomposition;
- the paired PLAN D/N and WYK U/C absence symbols are a paper/export convention, not operational Assignment truth;
- actual work cells still map from real Assignment/work-period provenance;
- T020 does not change WorkBalance, Assignment, ScheduleVersion, solver eligibility, or coverage accounting merely to print U/C.

The earlier content remains available in Git history only as audit trail and MUST NOT be used to implement or audit current T020 behavior.
