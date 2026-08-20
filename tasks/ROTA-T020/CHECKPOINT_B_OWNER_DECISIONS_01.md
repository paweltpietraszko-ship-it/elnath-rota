# ROTA-T020 — CHECKPOINT B OWNER DECISIONS 01

STATUS: B-PD-01 CLOSED — B-PD-02 STILL OPEN — CHECKPOINT B NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
PARENT_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md
OWNER_DECISION_SOURCE: explicit owner statement in conversation on 2026-08-20

This document records a narrow owner clarification for Checkpoint B. It does not change Checkpoint A visuals, does not authorize production implementation, and does not amend T018 WorkBalance semantics.

## 1. B-PD-01 — CLOSED

The previously open question was whether T020 must allocate the T018 `8h per qualified workday` LEAVE_GRANTED / SICK_LEAVE accounting amount to one particular Site when an Employee is modeled across multiple Sites.

Owner decision:

> `8h urlopu nie występuje, bo pracownik dostaje po prostu dzień bez pracy`

Normative T020 interpretation:

1. T020 MUST NOT treat the T018 `8h` accounting unit as a Site-local leave duration.
2. T020 MUST NOT allocate, split, duplicate, or infer that `8h` amount between Sites for print purposes.
3. A leave day on the printable schedule means that the employee has no work on the printed Site for that day; the export does not manufacture a synthetic `8h` Site assignment or Site-local leave-hours fact.
4. Site-local PLAN/WYK totals continue to come only from the effective schedule state for that Site.
5. T020 may present leave/sickness using the accepted print-symbol convention, but the presentation must not claim that T018's accounting `8h` is the duration worked/absent on the Site.
6. The same Employee being modeled on another Site does not cause the T018 accounting `8h` to be copied into this Site's printable totals.

Therefore the cross-Site allocation problem identified as B-PD-01 no longer exists in T020: the print read model does not consume that global `8h` amount as Site-local time.

## 2. T018 IS NOT CHANGED BY T020

This decision is deliberately scoped to the printable schedule.

T020 does not alter `rota.balance`, `rota.planning.absence`, TARGET semantics, or the frozen T018 WorkBalance convention. If those accounting rules are to be changed globally, that requires a separate product task/amendment.

In particular, T020 must not rewrite T018 merely because its printable representation uses different semantics.

## 3. ONE-DAY SICKNESS — OWNER REQUIREMENT FOR PLANNING, NOT T020 IMPLEMENTATION

Owner additionally stated:

> `przy jednodniowej chorobie, nie zdarza sie w ochronie, solver ma zapytać koordynatora`

This is recorded as product truth:

- a one-day sickness case is exceptional in the target security-domain workflow;
- when such a case requires planning resolution, the planner must not silently invent the operational interpretation;
- the final planning outcome must ask the coordinator for a decision rather than guessing.

However, T020 remains a read/export task and MUST NOT modify the solver, retry sequence, T013 decision guidance, T018 fallback logic, or PlanningResult semantics.

The solver-side behavior must be implemented/audited in its own planning task or explicit planning amendment. T020 Checkpoint B may only consume the final resolved Rota state; it cannot implement this requirement inside the PDF/read model.

## 4. EFFECT ON CHECKPOINT A VISUALS

Checkpoint A remains visually accepted at commit `d88a85b06a2de98eda65617603b12caec0cf5d59`.

This owner clarification does not revoke the accepted layout, PLAN/WYK rows, legend appearance, grayscale treatment, or A3-landscape baseline.

The accepted 40h example remains a visual/legend decomposition example. It must not be interpreted in Checkpoint B as proof that T020 owns or allocates T018's global `8h per qualified workday` accounting amount to a Site.

## 5. REMAINING PRODUCT BLOCKER

B-PD-02 remains open:

- whether an enabled EXTERNAL_SUPPORT employee with no effective Assignment on the printed Site/month receives an empty row.

Until B-PD-02 is explicitly closed and the architect publishes the full Checkpoint B implementation contract:

**PRODUCTION CC MUST NOT START T020 CHECKPOINT B.**
