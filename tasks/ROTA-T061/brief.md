# ROTA-T061 — RETIRED / DO NOT IMPLEMENT

STATUS: **RETIRED — OWNER REJECTED 2026-09-10**

This task is intentionally closed and must not be revived, implemented, or used as a requirement by future instances unless OWNER explicitly reopens it.

## Why T061 was retired

The proposed T061 required creating the first monthly schedule manually when no `current ScheduleVersion` exists. After inspection of the real product flow, OWNER rejected that direction because it would require a new whole-month manual scheduling capability rather than a correction of an existing schedule.

The product boundary is now explicit:

1. The first schedule for a month is created only by `PLAN`.
2. If PLAN cannot create a schedule, the program should give the coordinator practical next actions through ROTA-T062, for example change staffing, availability or leave data, and then run `PLAN` again.
3. If, after permissible input changes, PLAN still cannot create a schedule, **having no schedule is a correct business outcome**. The system must not manufacture a `current ScheduleVersion` or a manual root merely to avoid that outcome.
4. Existing `Korekta ręczna` remains a correction of a schedule that already exists. It is not a whole-month schedule builder and must not be extended into one under T061.
5. Solver constraints remain constraints of automatic planning. This retirement does not change the existing manual-correction rules for an already existing schedule.
6. The previously proposed mechanism `no current -> first manual root` is explicitly rejected.
7. Source tests such as `test_t011_e...::test_2` and `::test_3` must not be treated as authority to recreate the rejected product behavior. Tests do not create contract.
8. Earlier T061 briefs, reports, PASS results and implementation proposals that assume a first manual root are obsolete.

## Successor

The next product task is **ROTA-T062 — explainable blocked PLAN / practical next actions**.

T062 must not depend on T061 and must not offer a first-manual-root path. Its job is to prevent the coordinator from being left with an unexplained dead end while preserving the correct possibility that, with the current admissible inputs, no schedule can be produced.
