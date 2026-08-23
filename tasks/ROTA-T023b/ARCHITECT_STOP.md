# ROTA-T023b — ARCHITECT STOP

STATUS: OWNER DECISION REQUIRED — DO NOT IMPLEMENT
DATE: 2026-08-23

The previously committed T023b architect contract is retracted as implementation-ready.

Reason: architect review identified product semantics that were not closed by the input brief but were nevertheless inferred in the first contract draft. In particular:

1. settlement-month tail / statutory-week boundary behavior was invented rather than owner-resolved;
2. mixed-mode cross-Site semantics (ochrona Site vs ordinary Site for the same employee) were inferred from separate brief statements and are not explicitly resolved;
3. assignment-role treatment for the new rest protections, including TRAINEE/training, was inferred from adjacent implementation rather than from product scope;
4. T023b must never infer unobserved work outside Rota. Only work facts actually represented by the product may participate.

Until the owner answers the open questions and the architect produces one consolidated replacement contract, do not use:
- `arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md` as a frozen implementation authority;
- `tasks/ROTA-T023b/brief.md` as an implementation-ready brief.

CC remains READ-ONLY. Do not implement. Do not run a preimplementation PASS against the retracted draft.
