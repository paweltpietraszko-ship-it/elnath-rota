# ROTA-T007 — PRE-IMPLEMENTATION REVIEW 01 — ARCHITECT CLARIFICATION

DATE: 2026-08-12
STATUS: READY_FOR_RE-REVIEW
ORIGINAL_TASK_CONTRACT_COMMIT: 6289146447afc3b62b6fe18a3a058b201216cdde
MANDATORY_CLARIFICATION: arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01_R1_CLARIFICATION.md
ARCHITECT: ChatGPT
IMPLEMENTER: CC
AUDITOR: Codex

## REVIEW RESULT RECEIVED

Pre-implementation review returned `WYMAGA_DECYZJI` with exactly two material ambiguities:

1. which SiteProfiles support the T007 executable rule catalog;
2. whether unknown/malformed INFORMATIONAL rules stop planning.

Both are resolved by the architect before implementation. No CC implementation may begin from the original 6289146 contract without this clarification.

## RESOLUTION 1 — PROFILE SCOPE

T007 catalog applies to all SiteProfiles used in the current protection/OCHRONA pilot scope, regardless of the literal value of `profile_id`.

Forbidden implementation shortcuts:
- `profile_id == "OCHRONA"` as semantic gate;
- `profile_id.startswith("OCHRONA")`;
- display-name parsing;
- any other string naming convention pretending to be profile-family metadata.

T007 does not generalize this catalog to future shop/bakery/other-industry profiles. Those require a later explicit profile-capability/catalog contract.

## RESOLUTION 2 — INFORMATIONAL

INFORMATIONAL is never executable.

Unknown or malformed execution structure in a RESOLVED INFORMATIONAL rule:
- has zero planning effect;
- does not produce TECHNICAL_ERROR;
- remains available for memory/display/provenance.

Fail-closed parsing/validation remains mandatory for RESOLVED HARD. RESOLVED SOFT remains unsupported by T007 ranking and fails explicitly as already specified. NEEDS_RESOLUTION remains non-executable.

## UPDATED SEQUENCING AFTER T006 ACCEPTANCE

ROTA-T006 has received final architectural PASS on implementation SHA:

`6568de1de85a2cb290ebea041c62b00f99f79add`

Therefore T007 implementation MUST use an integration base containing:
- accepted T005 implementation `b97b762b3dfb4eef9d43a747a064e3b1e1144786`;
- accepted T006 implementation `6568de1de85a2cb290ebea041c62b00f99f79add` / REPLAN-MIN-01;
- the T007 frozen addendum, original brief, and this R1 clarification.

T007 must preserve REPLAN-MIN-01. Applicable HARD SiteRules rank above minimal-reshuffle; minimal-reshuffle ranks above ordinary SOFT.

## REQUIRED RE-REVIEW CHECK

Before handing T007 to CC, Codex should re-review the contract set and return either:
- PASS / READY_FOR_IMPLEMENTATION; or
- a precise remaining CONTRACT_GAP.

The re-review must treat the R1 clarification as authoritative for the two resolved topics and must not reopen them merely because the original brief contains the earlier shorthand `Profile OCHRONA` or the broader wording from the initial addendum.
