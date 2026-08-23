# ROTA-T023b — ARCHITECT STOP

STATUS: OWNER DECISION REQUIRED — DO NOT IMPLEMENT
DATE: 2026-08-23
CONTRACT_HEAD_BEFORE_STOP: `f86566b229b8dd6e643b3c1cea6efdca4ef85a0d`

## CLOSED OWNER RULING — SITE IDENTITY

`Site` is a planning/service unit, not a unique physical object.

The same real-world location may therefore be represented by more than one independent Site, for example:
- `X — Ochrona`;
- `X — Sprzątanie`.

Those Sites have independent planning scope, memberships, schedules and coordinator associations. The same coordinator may be associated with both, but this does not merge their planning facts or HARD rules.

T023b concerns only the protection-service Site. Cleaning has a different legal/HARD regime and remains a separate future task; T023b must not infer, implement or reuse cleaning rules.

## CLOSED OWNER RULING — REGIME IS NOT A NORMAL EDIT

The Site planning/service regime is a classification of that Site, not an ordinary mutable planning setting.

- the regime is selected when the Site is created and requires explicit confirmation before the initial save;
- ordinary Site editing must not expose a simple regime toggle;
- after creation, the regime is normally immutable;
- correcting an erroneous initial classification is a separate exceptional operation, not a normal edit path;
- T023b does not define a general `ORDINARY <-> OCHRONA` transition workflow and does not need retroactive ScheduleVersion semantics for a routine toggle, because such a toggle is not part of the product.

This closes the previously open question about temporal effects of a normal regime change: there is no normal regime-change command in T023b.

## ARCHITECT CORRECTION — BOOLEAN MODE IS TOO NARROW

The earlier proposal `Site.ochrona_mode: bool` is retracted.

Reason: the known domain contains more than the binary distinction `OCHRONA` vs `ORDINARY`; cleaning is a separate service regime with its own future HARD rules. Therefore `False = ordinary` is not a valid domain model.

The consolidated T023b contract must use an explicit Site planning/service-regime classification rather than a boolean checkbox. T023b must not implement cleaning HARD semantics.

## STILL OPEN — EXISTING-SITE MIGRATION

One product decision remains before the single final consolidation.

Existing persisted Sites predate the new explicit regime classification. They cannot all be truthfully migrated to `ORDINARY`, because some real Sites may represent protection or cleaning services, and current persisted data does not contain a canonical regime fact from which the classification can be reconstructed safely.

The architect will not infer regime from SiteProfile name, shift pattern, coordinator, employees or any other heuristic.

Owner must choose the migration semantics for existing Sites:

1. **Explicit reclassification required** — existing Sites migrate to an `UNCLASSIFIED`/equivalent state and must be explicitly classified before planning under the new regime-aware contract; or
2. another explicit owner-provided migration rule that identifies the correct regime without heuristic inference.

Until this is closed, do not implement schema migration or regime-aware planning. CC remains read-only.
