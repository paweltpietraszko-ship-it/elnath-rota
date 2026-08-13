# ROTA-REAL-OBJECT-01 — R3 CONDITION CLARIFICATION

Date: 2026-08-13
Status: ARCHITECTURAL CLARIFICATION
Scope: blocker taxonomy used by ROTA-REAL-OBJECT-01 and public PlanningResult provenance

## Decision

The canonical public condition for an EXTERNAL_SUPPORT employee who cannot be used for the demand is:

`EXTERNAL-01`

This remains true when the immediate internal cause is `SiteProfile.external_support_enabled == false`.

`EXTERNAL_SUPPORT_DISABLED` may describe an internal implementation reason, diagnostic detail, or branch in eligibility code, but it is NOT a second public blocker taxonomy for `DecisionRequiredPayload.blockers[*].condition`.

## Rationale

The accepted planning boundary names the eligibility family as `EXTERNAL-01`. Profile capability, active matching ExternalSupportWindow, employee/Site/interval/shift-kind matching and membership state are gates within that eligibility family. A coordinator-facing decision payload should not change condition taxonomy depending on which internal gate rejected X/Y.

This clarification does not make disabled external support magically unlockable. If the profile disables external support, adding a window is insufficient and the benchmark must not claim an EXTERNAL_SUPPORT_DECISION_REQUIRED class. The case remains a proven shortage unless another valid remedy exists. The blocker condition nevertheless stays `EXTERNAL-01`.

## Benchmark consequence

For `external-window-profile-disabled`:

- reference feasibility remains unchanged;
- the benchmark checker accepts `EXTERNAL-01` as the canonical external blocker condition;
- `EXTERNAL_SUPPORT_DISABLED` in the public `PlanningResult` payload is a mismatch after the benchmark itself is accepted;
- no production code is changed on the benchmark branch.

This clarification closes only the one condition-code ambiguity identified by Codex R2. It does not alter product behavior, ExternalSupportWindow semantics, or the frozen eligibility rules.
