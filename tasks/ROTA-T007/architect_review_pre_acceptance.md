# ROTA-T007 — ARCHITECT REVIEW BEFORE FINAL ACCEPTANCE

DATE: 2026-08-12
STATUS: HOLD_FOR_DOCUMENTATION_DRIFT_FIX
ARCHITECT: ChatGPT
AUDITED_IMPLEMENTATION_SHA: 2819fb6e18b055ad2e13bdf1ce44eba795b7d567
CODEX_PASS_REPORT_COMMIT: cef176da13a671e32e7849fc8757d12cbcd437da

## RESULT

Functional/behavioral architecture review: PASS.
Final architectural acceptance / owner merge recommendation: HOLD pending one narrow anti-drift cleanup.

No product decision is required. No solver, persistence, rule semantics, test expectation, objective, status mapping, or public behavior may change as part of this cleanup.

## CONFIRMED

The implementation correctly establishes the T007 vertical path:

Decision Ledger / SQLite -> monthly SiteMemory projection -> PlanningState applicability -> executable HARD SiteRules -> solver eligibility -> independent validator -> PlanningResult with rule_version_id provenance.

It preserves T005 effective-selection semantics and T006 REPLAN-MIN-01 ordering. INFORMATIONAL remains non-executable; unsupported/malformed RESOLVED HARD fails closed; RESOLVED SOFT remains explicitly unsupported. The two-month SQLite integration scenario exercises persistence restart and real plan().

Codex round 6 reports PASS on exact implementation SHA 2819fb6 with 202/202 full suite, all 13 T007 audit tests, unchanged ROTA-REG-001, benchmark PASS, Ruff/size PASS, and all R3-R5 findings closed.

## BLOCKER — STALE CANON COMMENTS

Two implementation comments still assert the pre-T007 state and contradict the code and frozen T007 contract:

1. `rota/planning/eligibility.py` module docstring still says SiteRuleVersion is intentionally not interpreted and the rule_kind catalog is CONTRACT_GAP/out of scope.
2. `rota/domain.py` still contains `# rule_kind catalog: CONTRACT_GAP — osobny task` directly on `SiteRuleVersion.rule_kind`, even though T007 now freezes an initial executable three-kind catalog. Only future rule kinds beyond that initial catalog remain a separate contract gap.

These are not runtime bugs, but they are an architecture/provenance anti-drift blocker: a future model or implementer could incorrectly treat the stale statements as current contract authority.

## REQUIRED FIX

CC should make a documentation-only commit that:

- updates/removes the stale `eligibility.py` module wording so it states that T007 executes the frozen initial SiteRule catalog supplied through PlanningState, while PlanningEngine still performs no persistence I/O;
- replaces the stale `domain.py` comment with wording that the INITIAL three-kind catalog is frozen by T007 and only catalog extension remains a separate contract gap;
- changes no executable behavior.

Codex need only verify the exact follow-up SHA is documentation/comment-only relative to 2819fb6 and that it introduces no semantic change. Full behavioral re-audit is unnecessary unless the diff contains executable changes.

After that exact SHA is visible on origin/task/ROTA-T007, return it to the architect for final acceptance. Merge to main remains owner decision.
