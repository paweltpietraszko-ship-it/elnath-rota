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

## ARCHITECT CORRECTION — BOOLEAN MODE IS TOO NARROW

The earlier proposal `Site.ochrona_mode: bool` is retracted.

Reason: the known domain now contains at least three distinct service regimes conceptually (`OCHRONA`, `ORDINARY`, `SPRZATANIE`). Therefore `False = ordinary` is not a valid long-term domain statement.

The consolidated T023b contract will use an explicit Site planning/service-regime value rather than a boolean checkbox. T023b will implement only the regimes actually required by this task; adding cleaning HARD semantics is forbidden here and belongs to its own task.

This is an architect-owned representation correction. It does not create a cleaning feature.

## STILL OPEN — CHANGE OF AN EXISTING SITE REGIME

One product decision remains.

If an existing Site is deliberately changed from `ORDINARY` to `OCHRONA`, what is the temporal effect on already-persisted/current ScheduleVersions?

Choose one product semantics:

1. **Immediate** — after the regime change, existing/current schedules are subject to the OCHRONA HARD rules on the next validation/finalize/restore path; or
2. **Prospective** — the new regime applies only to schedules created/replanned after the change, so persisted ScheduleVersions must retain the regime under which they were created.

This is not about accidental clicks. The separate UI/write-path question (double confirmation / blocking ordinary edit) can be frozen once the temporal semantics is selected.

Do not implement until this final owner decision is closed and the architect emits one consolidated replacement contract. CC remains read-only.
