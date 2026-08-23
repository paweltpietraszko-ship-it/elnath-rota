# ROTA-T023b — ARCHITECT STOP

STATUS: OWNER DECISION REQUIRED — DO NOT IMPLEMENT
DATE: 2026-08-23
CONTRACT_HEAD_BEFORE_STOP: `f86566b229b8dd6e643b3c1cea6efdca4ef85a0d`

One product question remains after the consolidated owner clarifications.

If a Site already has a current/persisted ScheduleVersion created while `ochrona_mode=False`, and the coordinator later changes the Site to `ochrona_mode=True`, do the new T023b HARD protections apply immediately to that already-existing schedule/version, or only to schedules created/replanned after the switch?

This is not hypothetical: existing `revalidate`, `finalize` and `restore` operate on persisted versions, so the answer determines whether T023b must add lifecycle guards/audit handling or durable regime provenance.

Do not implement until the owner selects the temporal semantics of the mode change. No other T023b product question is open.
