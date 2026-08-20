# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 02

STATUS: B-PD-02 CLOSED — CHECKPOINT B PRODUCT QUESTIONS FROM CHECKPOINT A CLOSED — NOT YET A PRODUCTION IMPLEMENTATION CONTRACT
DATE: 2026-08-20
TASK_ID: ROTA-T020
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
PARENT_ACCEPTANCE_HEAD: 9c10b14fba223f400f517f9dcd62306ea1765cbf
OWNER_DECISION_SOURCE: explicit owner clarification in conversation on 2026-08-20

This document records the owner's closure of B-PD-02 and clarifies how LOCAL roster presence relates to existing absence information. It changes no production code and does not by itself authorize CC implementation.

## 1. B-PD-02 — employee row population — CLOSED

For a printed Site/month:

1. An enabled `LOCAL` employee of the printed Site gets a row on the schedule even if that employee has zero Assignment rows in the printed month.
2. An `EXTERNAL_SUPPORT` employee gets a row only if that employee actually has an effective Assignment on the printed Site/month.
3. An `EXTERNAL_SUPPORT` employee with no effective Assignment on the printed Site/month does **not** get an empty row.
4. A real Assignment on the printed Site/month is sufficient to include the Employee row regardless of membership kind, because the printed schedule may not omit a person who actually appears in that Site's schedule.

This closes B-PD-02.

## 2. LOCAL employee with zero Assignment

A LOCAL employee remains visible even when no shift is assigned in the month because the printed roster represents the Site's local staff, not merely the set of Assignment rows.

Where the employee has recorded absence information, the print may show the corresponding presentation family:

- `LEAVE_GRANTED` -> leave presentation (`U` family);
- `SICK_LEAVE` -> sickness presentation (`C` family).

This must reuse the existing Availability truth. T020 must not invent a second absence status field and must not introduce `U` or `C` as new solver/domain enums merely for printing.

If a LOCAL employee has no Assignment and no applicable recorded leave/sickness fact, the row remains present without fabricating an absence reason.

## 3. Solver / planning clarification

The owner additionally clarified that the planner must know whether an otherwise unassigned local employee is unavailable because of leave or sickness. In the current architecture that information is represented by existing Availability records (`LEAVE_GRANTED` / `SICK_LEAVE`) and is already planning input.

T020 Checkpoint B is an export/read task and must not create a parallel solver status for `U` / `C`.

The separately recorded owner rule that an exceptional one-day sickness case should ask the coordinator remains a planning-semantic requirement outside T020 implementation scope. T020 must not silently implement or reinterpret that solver behavior as part of PDF export.

## 4. Consequence for Checkpoint B contract design

The two owner decisions identified before production B are now closed:

- B-PD-01: closed by `CHECKPOINT_B_OWNER_DECISIONS_01.md` — no synthetic Site-local 8h leave allocation in T020;
- B-PD-02: closed by this document — LOCAL always gets a row; EXTERNAL_SUPPORT only when actually assigned.

The architect may now design the full Checkpoint B implementation contract against these owner decisions and the frozen Checkpoint A visual acceptance.

Production CC must still wait for the explicit Checkpoint B implementation contract and its required preimplementation audit gate.
