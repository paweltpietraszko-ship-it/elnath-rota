# FINAL ARCHITECTURAL ACCEPTANCE — ROTA-T006

DATE: 2026-08-12
TASK_ID: ROTA-T006
TITLE: REPLAN minimal reshuffle
VERDICT: PASS
ARCHITECT: ChatGPT architect

## ACCEPTED IMPLEMENTATION

Accepted implementation SHA:

`6568de1de85a2cb290ebea041c62b00f99f79add`

This acceptance applies only to the exact implementation SHA above. A later code change does not inherit this PASS automatically.

Audit-report commit visible on `task/ROTA-T006`:

`f495d0b6d2898f0e09014ea5528228c797e2d07b`

The audit-report commit is not the implementation SHA. It records Codex round-3 PASS for `6568de1`.

## ARCHITECTURAL CHECK

The accepted implementation satisfies REPLAN-MIN-01:

1. REPLAN minimizes changed redistributable baseline placements before ordinary SOFT/TARGET ranking.
2. The priority is lexicographic, not represented by an arbitrary dominating numeric weight.
3. Phase 1 may establish `min_reshuffle_count` only after CP-SAT returns `OPTIMAL`.
4. `FEASIBLE`, `UNKNOWN`, and `MODEL_INVALID` from phase 1 fail closed rather than being presented as a proven minimum.
5. Proven `INFEASIBLE` remains on the existing conflict/DECISION_REQUIRED boundary.
6. Phase 2 fixes the proven minimum reshuffle count and then applies the existing ordinary SOFT objective.
7. Reshuffle identity is employee + demand, not Assignment row/object id.
8. A baseline placement whose old employee/demand slot becomes impossible contributes one required reshuffle.
9. A newly uncovered demand without a baseline placement does not itself count as a reshuffle.
10. Initial planning without baseline placements retains the previous single-phase behavior.
11. Existing REALIZED/frozen protections and other HARD rules remain above reshuffle minimization.
12. Scope remains inside the permitted planning/T006 areas; no persistence, SiteMemory, arch/spec or regression-oracle semantic drift was introduced by the implementation.

## AUDIT EVIDENCE

Codex round 3 audited exact implementation SHA `6568de1de85a2cb290ebea041c62b00f99f79add` and reported:

- author suite: 163/163 PASS;
- independent matrix: 6/6 PASS;
- total: 169/169 PASS;
- production stress benchmark: 100/100 PASS;
- both previous R2 findings closed;
- Ruff PASS;
- SIZE_FILE / SIZE_FUNC PASS;
- 0 new findings;
- 0 WYMAGA_DECYZJI.

## RESULT

ROTA-T006 is architecturally closed with PASS on `6568de1de85a2cb290ebea041c62b00f99f79add`.

Merge to `main` remains an owner decision.
