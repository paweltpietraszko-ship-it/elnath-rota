# ARCHITECTURAL ACCEPTANCE — ROTA-T005

STATUS: PASS
DATE: 2026-08-12
ARCHITECT: ChatGPT architect
IMPLEMENTER: CC
AUDITOR: Codex
ACCEPTED_IMPLEMENTATION_SHA: b97b762b3dfb4eef9d43a747a064e3b1e1144786
TASK_BASE_SHA: c17491cbde7311bf31ca0164093d71cbe0cf3d67
CONTRACT: tasks/ROTA-T005/brief.md
AUDIT_REPORT_DECLARED: tasks/ROTA-T005/round_01/tests/tests_r2.txt

## SCOPE OF FINAL REVIEW

Final architectural acceptance was performed against the exact pushed implementation commit `b97b762b3dfb4eef9d43a747a064e3b1e1144786`, not only against the auditor verdict.

Verified architecturally:
- task provenance matches `tasks/ROTA-T005/repo_before.hash` at base `c17491cbde7311bf31ca0164093d71cbe0cf3d67`;
- the full T005 implementation is exactly two commits above that base: initial implementation plus the R1 correction commit;
- production changes stay within the T005 boundary: SiteMemory types, Rota persistence/Decision Ledger, and the minimal RuleParameters comment/type-boundary correction;
- `arch/spec.md` and `rota/planning/` are unchanged by T005;
- SiteRuleVersion persistence is append-only and DecisionRecord/DecisionRelation history is append-only;
- one rule_id is mechanically bound to one site_id through the shared rule-family invariant;
- supersedes_rule_version_id is checked to stay inside the same site_id/rule_id family;
- Decision Record + SiteRuleVersion + relation are created inside one transaction on the decision write path;
- decision history is a single linear chain with no caller-selected arbitrary predecessor;
- `supersedes`, `corrects`, and `rejects` preserve provenance; `rejects` does not create a fake disabled SiteRuleVersion;
- effective selection is based on chain order after filtering decisions whose effective_from has arrived, with SiteRuleVersion.effective_to interpreted inclusively;
- expired/rejected rules do not resurrect older versions automatically;
- provenance can map a rule_version_id back to its creating decision and earlier chain;
- `structured_parameters` uses JSON only as a persistence representation, rejects lossy/non-JSON round trips, and does not freeze the future RuleParameters type or rule_kind catalog;
- RESOLVED and NEEDS_RESOLUTION are projected separately for PlanningState assembly;
- PlanningEngine has no persistence/Decision Ledger I/O coupling;
- full Elnath Memory Engine runtime, archive/evidence workflow, semantic retrieval, and EME role machinery were not introduced.

## AUDIT EVIDENCE

Codex verdict supplied for the same implementation SHA reports:
- author suite: 147/147 PASS;
- independent matrix: 20/20 PASS;
- both R1 findings fixed;
- Ruff, size limits and PlanningEngine isolation: PASS;
- 0 new errors;
- 0 `WYMAGA_DECYZJI`.

The R1 correction commit itself documents and fixes the two previously identified classes:
- rule-family integrity across both Decision Ledger and direct SiteRuleVersion write paths;
- strict JSON-compatible, meaning-preserving persistence boundary.

## FINAL VERDICT

PASS.

ROTA-T005 satisfies its Task Contract and is accepted architecturally on exactly:

`b97b762b3dfb4eef9d43a747a064e3b1e1144786`

Any later commit requires separate review; this acceptance must not be transferred to a different SHA by implication.

This acceptance closes persistence/history only. It does NOT approve or define executable `rule_kind` semantics, the future typed RuleParameters union, natural-language interpretation, solver execution of SiteRule, or the later SiteMemory -> PlanningState -> plan() integration benchmark.
