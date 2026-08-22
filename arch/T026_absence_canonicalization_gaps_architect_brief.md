# ROTA-T026 — ARCHITECT INPUT: POST-T023 CANONICALIZATION GAPS

STATUS: INPUT FOR A NEW ARCHITECT SESSION — NOT AN IMPLEMENTATION CONTRACT
BASE: `main@3d2c2dc` (ROTA-T023 Checkpoints A/B/C merged)
SOURCE: independent Cursor holistic audit, [PR #7](https://github.com/paweltpietraszko-ship-it/elnath-rota/pull/7), exact audit HEAD `6368ec0eae04733b4acd094247352724dd6c0901` (`cursor/t023-holistic-audit-4a06`). The PR contains `tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/FINDINGS.md`; that file is not present in this local workspace, so the PR+SHA above — not a nonexistent local path or an unavailable transcript — is the source citation. CC directly confirmed A2/A3/A4 against `main@3d2c2dc`; Codex directly confirmed A1, checked the same A2/A3 source paths and performed the final scope classification below.

HANDOFF CLASSIFICATION: A1 is a confirmed legacy-gate/contract gap; A2+A3 are one confirmed canonical-ownership gap, not two independent numerical defects; A4 is a stale-comment cleanup with no functional effect. The audit's labor-law items and C1/C2 observations are explicitly excluded in section 5. This classification is complete for the architect handoff and does not depend on either review transcript.

## 1. Architect deliverables

Produce, without implementation:

1. a separate, explicit disposition for **each** of items 1 and 2 below: authorize it in T026, defer it with a named reason/future decision boundary, or reject it as not a defect with trace to the controlling contract; neither item may be left implicit merely because the other is authorized;
2. for item 1, a definition of the public `plan(PlanningState)` trust/validation boundary, followed by the gate decision: remove the stale gate and supersede its oracle, replace it with an exactly named canonical-model invariant, or confirm it as intentional defense-in-depth and state how it remains compatible with T023;
3. for item 2, a layering decision: does the canonical Site-aware projection move into `rota/planning/absence.py`, taking the richer decoded facts with it or by reference, or does it live in another named pure owner? The decision must preserve or explicitly amend the frozen single-owner contract; this module's current ownership comment states that it imports nothing from persistence by design;
4. if either item is authorized, `tasks/ROTA-T026/brief.md` with exact `TASK_SCOPE`, allowed production/test files, superseded-or-preserved historical oracles, and closure criteria for **all** authorized items;
5. explicit confirmation of what stays OUT of scope — this brief deliberately excludes the labor-law and C1/C2 items from the same Cursor audit (see section 5).

CC must not implement before independent Codex preimplementation PASS, per the same pipeline T023 used.

## 2. Item 1 — `rota/planning/engine.py` still gates on the retired SICK-only workday-calendar path

`engine.py:29` imports `IncompleteAbsenceCalendarError, excused_absence_days_in_month` from `rota.planning.absence`. `_plan()` at `engine.py:76-79` calls:

```python
excused_absence_days_in_month(
    state.availability_records, state.month, kinds=(AvailabilityKind.SICK_LEAVE,),
    calendar_days=state.calendar_days,
)
```

before `solve()`. `plan()` at `engine.py:62-63` maps `IncompleteAbsenceCalendarError` to `TECHNICAL_ERROR`. The comment immediately above the call (`engine.py:71-75`) justifies this as a pre-model shortage check because "a pre-model shortage ... never reaches `_sick_adjusted_targets()`" — **that function no longer exists**; it was renamed to `_effective_targets` during ROTA-T023 Checkpoint B (`rota/planning/solver.py:276`), and its body no longer recomputes anything from `calendar_days`/`availability_records` at all — it reads `wb.absence_hours` directly off `PlanningState.work_balances` (already resolved upstream). The comment describes a pre-Checkpoint-B world.

Frozen addendum section 2 (ROTA-T023): SICK_LEAVE has no PRE_PLAN path at all — its hours only ever come from an accepted schedule (POST_PLAN_REFERENCE) or are MISSING. `excused_absence_days_in_month`/`CalendarDay` is not part of how SICK_LEAVE hours are computed anywhere after T023. This engine.py call's actual current effect is a completeness gate unrelated to what the solver now consumes.

**Observed production-path redundancy, not yet confirmed as total:** in the `plan_month()`/`replan()` application paths, `assemble_planning_state()` runs before `plan()` and already calls `_assemble_work_balances()` → `reconstruct_month_balance()`, which raises `IncompleteAbsenceReferenceError` uncaught if a required SICK/LEAVE reference is incomplete. If those are the exhaustive supported entry paths, `engine.py`'s own gate is subsumed before a real caller reaches it. Direct `plan(PlanningState)` remains a public code boundary and is used directly by tests, so T026 must decide whether that boundary accepts only an already assembled/trusted state or owns an independent completeness check; this brief does not infer that answer from current tests.

**Known retained test dependency:** `tests/test_t018.py::test_a7_9_direct_plan_with_incomplete_calendar_and_sick_absence_is_technical_error` (lines 186-198) asserts `plan()` returns `TECHNICAL_ERROR` for a hand-built `PlanningState` carrying a SICK_LEAVE record and no `calendar_days`. It records the old T018 boundary but does not by itself prove that this remains the correct post-T023 oracle.

**Required architect ruling for a testable contract:**

- If `PlanningState` is trusted/assembled input, say so explicitly, identify the supported assembly entry paths, and state whether the old direct-plan oracle is superseded while unrelated uses of the T018 helper remain preserved.
- If `plan()` still owns an independent guard, name the exact canonical field/invariant it checks and its `PlanningResult` error mapping. The guard must not silently restore CalendarDay/raw-Availability recounting that T023 superseded for solver TARGET (`T23-32`).
- State the regression boundary for direct `plan()`, `plan_month()` and `replan()` so a fix cannot close only the observed call path.

## 3. Item 2 — `rota/application/schedule_export.py` re-derives SICK/LEAVE precedence and POST_PLAN hours instead of consuming one canonical result

Frozen addendum section 13: "`rota/planning/absence.py` is the single pure consumer-facing accounting/precedence owner ... Consumers do not choose source mode from CURRENT and do not reimplement SICK/LEAVE precedence, anchor rules or Site filtering."

`rota/planning/absence.py::canonical_daily_hours` (lines 150-171) already implements SICK-wins-over-LEAVE_GRANTED precedence and returns `dict[date, int]` hours. `rota/balance.py` and `rota/application/analytics_read.py` consume decoded `DailyAbsenceFact`; the solver consumes the resulting `WorkBalance.absence_hours` indirectly rather than reading `DailyAbsenceFact` itself. The canonical shape is Employee-global and Site-agnostic, with no `PeriodFact`/shift-kind detail.

`rota/application/schedule_export.py` needs Site-filtered hours (T20 prints one Site's own sheet; frozen addendum: "Site comes from bound schedule provenance") and the bound period's `shift_kind` (to print a D or N code rather than pick by duration alone — this was itself a closed Checkpoint C finding, C-R15-2). `DailyAbsenceFact` cannot supply either. So Checkpoint C built a second reader directly against the richer `AbsenceReferenceSnapshot`/`DayReference`/`PeriodFact` shape (`rota/persistence/absence_reference_repository.py`) and reimplemented both concerns locally:

- `schedule_export.py::_winning_days` (lines 324-333) — its own SICK-wins-LEAVE precedence over `(AvailabilityRecord, AbsenceReferenceSnapshot)` pairs, duplicating `canonical_daily_hours`'s own rule.
- `schedule_export.py::_post_plan_pair` (lines 334-351) — sums `PeriodFact` interval durations filtered by `site_id`, **never reads `DayReference.hours`** for POST_PLAN dates. `_decompose_pre_plan` (lines 321-323), by contrast, reads `day.hours` for PRE_PLAN dates. The two provenance modes legitimately require different projections; the gap is that T020 owns the POST_PLAN Site arithmetic and precedence locally even though frozen section 13 assigns those concerns to one canonical owner.

A same-value substitution is not available by construction: `DailyAbsenceFact` is deliberately simplified and Site-agnostic, so `schedule_export.py` cannot just consume it without losing the Site filtering required by C-R15-3/T23-25. Closing this needs either (a) a canonical Site-aware presentation projection in the existing or another named pure owner, called by `schedule_export.py` instead of its own `_winning_days`/`_post_plan_pair`, or (b) a formal T026 owner amendment authorizing a narrower second owner. Option (b) may not be expressed as a reinterpretation: it must explicitly supersede the conflicting text in frozen addendum section 13, section 16 guarantee 15 and the corresponding `T23-35` consumer-equality requirement, while stating what equality remains required. `rota/planning/absence.py`'s module comment (lines 118-121) currently says it imports nothing from persistence to avoid a layering cycle with `absence_reference_repository.py`, which already imports `rota.planning.validator`/`work_periods`; option (a) must resolve that layering boundary explicitly, not silently.

For either authorized design, the T026 implementation contract must name the pure input and output shapes and preserve the already-frozen behavior for explicit range clipping, SICK-over-LEAVE precedence, PRE_PLAN exact-sum presentation, POST_PLAN Site provenance and D/N/24h/rest facts, and fail-closed MISSING/AMBIGUOUS handling. These are inherited T023 guarantees, not new T026 product rules.

## 4. Item 3 — stale comment, no functional effect

`rota/planning/absence.py:123-127` still reads: "Deliberately NOT wired into rota.balance / rota.planning.solver / rota.application.schedule_export yet -- those are Checkpoint B/C's own allowed-file scope ... until that checkpoint switches them over." All three are wired as of `main@3d2c2dc`. This is a trivial documentation correction: include it if T026 authorizes either implementation item; if neither is authorized, give it an explicit cleanup disposition rather than silently leaving the stale statement in place.

## 5. Explicitly out of scope for this brief

The same Cursor audit raised labor-law questions (Kodeks pracy art. 132/136 §2/137 rest-after-24h-shift, art. 133 35h weekly rest, night-work window) about what `rota/planning/eligibility.py`/`constraints.py`/`work_periods.py` treat as legal today (`REST_MIN_HOURS = 11`, coordinator-entered `required_rest_hours`, no encoded weekly-rest or 24h-aftermath rule). Codex's review of that section confirmed the KP citations on their own terms but held that it is a distinct scope question from T023's canonicalization work — today's product spec treats coordinator-configured `required_rest_hours` as authoritative and does not derive legality from statute anywhere. Paweł has not yet decided whether/when to open that as its own task. Do not fold it into T026.

Also out of scope (Cursor findings C1/C2, reviewed and not reopened): T021's absence log reading raw `AvailabilityRecord` beside `open_month`'s canonical `work_balances` is an intentional split (presence/dates vs. canonical hours are different questions with different owners), and `IncompleteAbsenceReferenceError` propagating uncaught through `manual_edit.apply_manual_correction`/`lifecycle_ops.revalidate`/`finalize`/`open_month` (beyond the `plan_month`/`select_candidate`/`replan` path already ruled fail-closed-required during T023 Checkpoint B) is the same required fail-closed behavior on new call sites, not a new requirement — any push toward degrade-to-warning UX consistency across those coordinator screens is a distinct owner decision, not a T023/T026 defect.
