# FINAL ARCHITECTURAL ACCEPTANCE — ROTA-T007

DATE: 2026-08-12
STATUS: PASS
ARCHITECT: ChatGPT
TASK_ID: ROTA-T007
TITLE: Executable SiteRules — SiteMemory -> PlanningState -> PlanningEngine

## ACCEPTED IMPLEMENTATION SHA

`f50c49edeff92c0ef2c6274359fe4ede9f144f13`

This acceptance is bound to the exact implementation SHA above. Any later executable-code change requires separate architectural review.

The branch may contain later audit-report commits. In particular, `09ad804a2d9072cb6623a3cee0e744e1d23dca8d` is an audit artifact commit and is not the implementation SHA accepted here.

## BASIS

The architect inspected the T007 implementation at `2819fb6e18b055ad2e13bdf1ce44eba795b7d567`, including:

- monthly SiteMemory projection using T005 effective-selection semantics;
- automatic discovery of rule families for a Site;
- explicit `SiteRuleApplicability` slices in PlanningState;
- the frozen initial three-kind executable SiteRule catalog;
- RESOLVED HARD fail-closed validation;
- INFORMATIONAL and NEEDS_RESOLUTION non-execution per R1 clarification;
- solver eligibility enforcement of applicable HARD SiteRules;
- independent validator re-checking the same SiteRule semantics;
- exact `rule_version_id` provenance on SiteRule-related blockers;
- preservation of ROTA-T006 REPLAN-MIN-01 ordering;
- the real SQLite two-month restart integration path proving remembered SiteRules affect `plan()` without re-entry.

Codex round 6 returned PASS on `2819fb6` after closing findings R3-1, R3-2, R4-1, R4-2 and R5-1.

The architect then identified two stale pre-T007 comments that contradicted the implemented contract and therefore created an anti-drift risk. Commit `f50c49e` corrects only those comments/docstrings in `rota/domain.py` and `rota/planning/eligibility.py`.

Codex round 7 confirmed for exact SHA `f50c49e`:

- executable AST is identical to `2819fb6` after removing docstrings/comments;
- full suite 202/202 PASS;
- ROTA-REG-001 7/7 PASS;
- benchmark 100/100 PASS;
- Ruff PASS;
- SIZE_FILE / SIZE_FUNC PASS;
- zero new findings.

## ARCHITECTURAL VERDICT

PASS.

ROTA-T007 satisfies SITE-RULE-EXEC-01 and its R1 clarification. SiteMemory is now operationally authoritative for the supported active HARD SiteRules: persisted decisions are projected into PlanningState and constrain real PLAN/REPLAN execution without giving PlanningEngine persistence ownership.

The accepted implementation preserves the previously accepted ROTA-T006 priority order: HARD validity first, then minimum reshuffle for REPLAN, then ordinary SOFT/TARGET ranking.

## MERGE DECISION

From the architecture side, `f50c49edeff92c0ef2c6274359fe4ede9f144f13` is READY FOR MERGE.

Merge remains the product owner's repository decision.
