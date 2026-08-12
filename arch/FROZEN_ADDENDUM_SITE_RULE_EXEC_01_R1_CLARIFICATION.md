# FROZEN CONTRACT CLARIFICATION — SITE-RULE-EXEC-01 R1

CLARIFICATION_ID: SITE-RULE-EXEC-01-R1
DATE: 2026-08-12
STATUS: FROZEN_CONTRACT_CLARIFICATION
APPLIES_TO: arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md
REVIEWED_TASK_CONTRACT_SHA: 6289146447afc3b62b6fe18a3a058b201216cdde

## PURPOSE

Pre-implementation review of ROTA-T007 identified two material ambiguities in the original addendum/brief. This clarification closes them before CC implementation.

For the two topics below, this file has precedence over ambiguous wording in the original addendum and `tasks/ROTA-T007/brief.md`. All other T007 semantics remain unchanged.

## CLARIFICATION 1 — PROFILE SCOPE

RULE-08 says supported rule kinds belong to SiteProfile semantics. The current `SiteProfile` model, however, has no structural profile-family discriminator, and `profile_id` is an identifier rather than a semantic inheritance mechanism.

For T007:

- the initial executable catalog applies to **every SiteProfile used inside the current protection (OCHRONA) pilot scope**;
- execution MUST NOT depend on literal `profile_id == "OCHRONA"`;
- execution MUST NOT infer profile family from prefixes/suffixes such as `OCHRONA-*`, display_name text, or other naming conventions;
- therefore a protection-profile variant with another arbitrary `profile_id` uses the same T007 catalog while it remains inside the current protection pilot;
- T007 does not introduce a new coordinator-facing profile-family field or configuration step.

Future profiles outside the protection pilot (for example shop/bakery profiles) MUST NOT inherit the T007 catalog merely because of naming or because the code has no discriminator. Before such profiles are enabled, a separate contract must define their supported rule kinds and, if needed, a structural capability/profile-family mechanism.

This is a pilot-scope decision, not permission to make the catalog globally universal across future industries.

## CLARIFICATION 2 — INFORMATIONAL UNKNOWN / MALFORMED

`INFORMATIONAL` means non-executable and non-constraining.

Therefore for a `RESOLVED` SiteRule with `enforcement == INFORMATIONAL`:

- PlanningEngine MUST NOT execute its rule semantics;
- PlanningEngine MUST NOT require its `rule_kind` to belong to the executable T007 registry;
- PlanningEngine MUST NOT validate its `structured_parameters` against executable T007 parameter schemas merely to permit planning;
- unknown `rule_kind`, missing execution parameters or malformed execution parameters in an INFORMATIONAL rule MUST NOT produce `TECHNICAL_ERROR`;
- the record remains available as remembered/displayable information and has zero planning effect.

The fail-closed executable-rule rule is narrowed explicitly:

- `RESOLVED + HARD`: supported kind and valid parameters are required; unknown/malformed -> `TECHNICAL_ERROR` with `rule_version_id`;
- `RESOLVED + SOFT`: T007 has no ranking semantics; if present in executable planning context -> `TECHNICAL_ERROR` with `rule_version_id`, as already frozen;
- `RESOLVED + INFORMATIONAL`: never executable; unknown/malformed execution shape is ignored by the planning engine and does not block planning;
- `NEEDS_RESOLUTION`: never executable and does not fail planning merely because structure is absent/unknown.

This clarification does not authorize persistence to rewrite or repair INFORMATIONAL data and does not change the T005 Decision Ledger/history semantics.

## TEST CONSEQUENCES

Codex must add adversarial coverage proving:

1. two protection-pilot SiteProfiles with different arbitrary `profile_id` values execute the same T007 HARD catalog without prefix/name matching;
2. an INFORMATIONAL rule with an unknown `rule_kind` does not constrain planning and does not cause TECHNICAL_ERROR;
3. an INFORMATIONAL rule with malformed/missing executable parameters does not constrain planning and does not cause TECHNICAL_ERROR;
4. the same unknown/malformed shape under RESOLVED HARD still fails closed to TECHNICAL_ERROR with exact `rule_version_id`;
5. no implementation introduces profile-id string heuristics.
