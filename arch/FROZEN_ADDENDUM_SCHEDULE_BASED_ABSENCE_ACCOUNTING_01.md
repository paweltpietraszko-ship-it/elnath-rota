# FROZEN ADDENDUM — T023 ABSENCE TIMING / HOURS — CONSOLIDATED

STATUS: FROZEN PRODUCT ADDENDUM — PREIMPLEMENTATION
DATE: 2026-08-22
TASK_ID: ROTA-T023
OWNER_SOURCE: arch/T023_absence_hours_architect_brief.md
OWNER_NIGHT_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_NIGHT_SHIFT_ANCHOR.md
OWNER_TIMING_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_ABSENCE_TIMING_PLAN_WYK.md
AUDIT_FINDINGS_INCORPORATED: R3-1..R3-6 and R5-1..R5-3

This file and `tasks/ROTA-T023/brief.md` are the only architect implementation contract after this consolidation. Earlier `ARCHITECT_R3_*.md` files remain historical review artifacts and do not override this pair.

## 1. PRESERVED PRODUCT BOUNDARY

Rota owns correct PLAN/WYK facts, D/N/U/C presentation, coordinator-facing absence hours and solver TARGET/fairness inputs. Rota does not own payroll, benefits, leave entitlement, HR settlement or legal advice.

Preserved invariants:
- active `SICK_LEAVE` / `LEAVE_GRANTED` remain HARD availability exclusions;
- absent Employees never receive nominal operational Assignments merely to display U/C;
- real ShiftDemand is covered by an actually eligible PRIMARY Employee;
- WorkBalance remains Employee-global/cross-Site;
- `LEAVE_PLAN` creates no actual absence hours;
- SICK supersedes overlapping granted leave for presentation/accounting: one C, no U+C;
- no SiteProfile absence strategy and no new D/N/U/C legend values.

## 2. TWO AUTHORIZED PROSPECTIVE SOURCES

T023 has one consumer-facing absence result, but two owner-authorized timing/provenance sources.

### 2.1 PRE_PLAN_LEAVE

Applies to `LEAVE_GRANTED` for a date/block for which no mechanically accepted applicable PLAN exists when the leave is recorded.

Rules:
- lack of a prior Employee schedule is not `MISSING` for this path;
- solver keeps the Employee unavailable on leave dates;
- no nominal operational Assignment is created;
- preserve the owner-approved pre-PLAN canonical leave-total + configured T020 decomposition path;
- binding example remains 40h Monday-Friday leave shown as PLAN `D1 / D1 / N2` and WYK `U1 / U1 / U2` in the accepted 12h presentation regime;
- these cells are presentation only and do not cover ShiftDemand;
- this pre-PLAN arithmetic must not leak into POST_PLAN_REFERENCE as a fallback.

### 2.2 POST_PLAN_REFERENCE

Applies to a prospective granted absence when a mechanically accepted applicable PLAN already exists for the affected date/block. It covers:
- sickness learned after PLAN; and
- granted leave added while PLAN is in force for future, not-yet-started work.

Rules:
- capture the Employee's accepted pre-REPLAN PRIMARY plan as immutable presentation/accounting provenance;
- later REPLAN may assign replacement coverage but cannot erase that bound PLAN fact;
- T020 prints matching U or C under the preserved planned period;
- exact scheduled period duration is the absence-hour source;
- no flat-8/workday fallback is allowed for this path.

## 3. MECHANICAL DEFINITION OF ACCEPTED PLAN — R5-1

`CURRENT`, `WORKING`, `FINAL`, non-empty Assignments and ScheduleVersion existence are not acceptance proofs.

The existing durable acceptance fact is `CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED`, written by `select_candidate()` in the same successful transaction that persists the coordinator-chosen snapshot.

For an Availability write at `recorded_at`, an accepted applicable ScheduleVersion for a Site/date is selected mechanically as follows:
1. start from the ScheduleVersion that is CURRENT for that Site/month at the write boundary;
2. walk its lineage toward the root using the existing lineage helper; cycle/missing-parent/context mismatch is an error;
3. consider only versions with real `effective_from <= anchored date`;
4. a version is accepted only if an existing durable `SCHEDULE_CANDIDATE_SELECTED` action names that `schedule_version_id` and has `recorded_at <=` the Availability command's `recorded_at`;
5. choose the deepest applicable accepted version;
6. an unselected technical WORKING child is skipped; its accepted parent remains the latest accepted plan when otherwise applicable.

Why this implementation evidence is recommended: it reuses the durable coordinator action already emitted exactly when a candidate is chosen.

Problem solved: the empty WORKING container created by `plan_month()` cannot be mistaken for an accepted plan, and a valid accepted empty schedule does not depend on Assignment count.

`site_memory.list_coordinator_actions(...)` already exposes the action history. T023 may read it; no new acceptance table/event is authorized.

## 4. POST-PLAN REFERENCE ARITHMETIC

For POST_PLAN_REFERENCE:

`absence_hours = exact hours of the Employee's accepted bound PRIMARY work periods whose anchor dates are covered by the granted absence`.

Consequences:
- scheduled 8h -> 8h;
- scheduled 12h D/N -> 12h;
- legal persisted 24h WorkPeriod -> 24h once;
- scheduled weekend/holiday counts its scheduled hours;
- accepted readable plan proving no Employee PRIMARY period on the anchor date -> 0h;
- missing/ambiguous/unreadable accepted reference -> fail closed, never invent 0/8/12/24;
- TRAINEE neither adds hours nor makes a coherent PRIMARY reference ambiguous merely by existing.

CalendarDay remains available to unrelated calendar rules but does not alter POST_PLAN_REFERENCE hours.

## 5. DATE ANCHOR

Every bound work period belongs wholly to its start date.

Owner examples:
- `2027-03-01 17:00 -> 2027-03-02 05:00`, absence starts Mar 2 -> 0 for that N;
- same N, absence includes Mar 1 -> full shift duration on Mar 1.

Do not split at midnight.

A legal 24h WorkPeriod follows the same start-date anchor and is counted once, including cross-month/year linkage.

## 6. DURABLE PROVENANCE

T023 persists one append-only `absence_reference_snapshots` row per AvailabilityVersion. It stores deterministic provenance, including source mode.

Required source modes:
- `PRE_PLAN_LEAVE`;
- `POST_PLAN_REFERENCE`.

Mode is established at the Availability write boundary and must survive later PLAN, REPLAN, restore, restart and CURRENT movement. A pre-PLAN leave must not become post-PLAN merely because a schedule later exists.

POST_PLAN_REFERENCE stores the exact bound schedule-period facts, not just a `schedule_version_id`, because WORKING content may be replaced in place under the same id.

A range may require different provenance blocks where plan acceptance differs by date/month. No user-facing mode selector is added.

No guessed legacy backfill from today's CURRENT is allowed.

## 7. REFERENCE SITE SCOPE — R3-1

An enabled `EXTERNAL_SUPPORT` membership alone does not add a required Site.

Reference Site scope is derived from:
- enabled LOCAL memberships; and
- Sites on which the Employee has actual non-CANCELLED PRIMARY reference work in the accepted effective schedule facts.

Dormant/unused external support cannot create `MISSING`. Real scheduled external-site PRIMARY work participates once in Employee-global accounting.

Multiple LOCAL memberships do not duplicate global hours.

## 8. RETROACTIVITY — R5-2

Rota must not create a new active absence state that retroactively changes a work fact that already started or was realized.

The guard is work-fact based, not calendar-date based.

For newly introduced/expanded active SICK/LEAVE coverage:
- reject if it would cover a non-CANCELLED PRIMARY work period whose `start_datetime < Availability recorded_at`;
- reject if it would cover a REALIZED PRIMARY Assignment;
- apply the same rule to a correction/extension only for newly introduced coverage;
- do not silently clip an invalid requested range.

Do NOT reject merely because `start_date` is before `recorded_at.date()`.

A past date that the accepted plan proves was a rest day contains no started work fact to rewrite and is not rejected for retroactivity; it contributes 0h on POST_PLAN_REFERENCE. A past date with incomplete provenance remains subject to the normal provenance fail-closed rule, not a blanket elapsed-date rejection.

Inactive/deactivation writes that remove coverage are not retroactive creation.

Why this boundary is recommended: it mirrors the owner's exact prohibition—do not alter a shift that already started/took place.

Problem solved: an L4 range may include yesterday's known rest day plus a future planned shift without being rejected only because yesterday is in the range.

## 9. REALIZED / WYK

A valid new T023 write cannot newly place absence over already started/REALIZED work.

Therefore:
- REALIZED remains immutable WYK truth;
- no normal absence arithmetic branch chooses count/exclude/unavailable for the same worked period;
- the write is rejected before AvailabilityVersion/snapshot/action is persisted if it newly creates such overlap.

Existing T020 conflict detection may remain only as a defensive integrity signal for legacy/corrupt data; it does not define normal product arithmetic.

## 10. REPLAN CUTOVER — R5-3

REPLAN changes operational work only prospectively from coordinator acceptance.

The exact cutover is the `recorded_at` used by the successful `SCHEDULE_CANDIDATE_SELECTED` action when `select_candidate()` accepts a candidate on a REPLAN child (`parent_version_id != None`). `ScheduleVersion.effective_from` is date-only and is not the sub-day cutover proof.

Before replacing that WORKING child snapshot, selection must prove:
- every existing non-CANCELLED PRIMARY Assignment with `start_datetime < cutover_at` is present in the candidate unchanged;
- the candidate contains no added/replaced non-CANCELLED PRIMARY Assignment whose `start_datetime < cutover_at`;
- equality is against the current child snapshot cloned from the previously accepted schedule; normal child `schedule_version_id` identity is already shared by that current snapshot and its candidate.

This cutover preservation check belongs in the existing atomic `select_candidate()` / `replace_working_snapshot(pre_check=...)` path. It is a selection-time lifecycle invariant, not a new solver HARD rule.

Why this location is recommended: only candidate selection has the real acceptance timestamp and the final snapshot being committed.

Problem solved: solver may propose redistribution of earlier PLANNED non-frozen work, but the coordinator cannot accept a REPLAN candidate that rewrites any PRIMARY work already started before acceptance.

No new versioning model and no timestamp field on ScheduleVersion are introduced.

## 11. VALIDATION OWNERSHIP — R3-6

`absence_reference_repository.py` is I/O/provenance only. It must not reimplement COVERAGE-01, Assignment/Demand structure, trainee/mentor rules or 24h legality.

Capture reuses:
- the existing canonical coverage predicate from `rota/planning/validator.py` (refactor the current private calculation into a shared pure helper if needed; both validator and capture call the same helper);
- existing `rota/planning/work_periods.py` grouping/24h functions without duplicating them.

Why recommended: one invariant has one owner.

Problem solved: absence capture cannot drift from normal planning validation.

## 12. WEEKLY / MONTHLY / QUARTERLY — R3-2

The canonical absence API accepts an explicit inclusive date range. Weekly output is the same canonical result over the caller-supplied seven-day range; T023 does not invent a separate week convention, analytics subsystem or persisted weekly row.

Monthly and quarterly consumers aggregate the same canonical facts.

## 13. CONSUMERS

`rota/planning/absence.py` is the single pure consumer-facing accounting/precedence owner. It receives decoded persisted provenance and returns canonical total/leave/sick hours plus ordered presentation facts.

The same result feeds:
- WorkBalance and analytics;
- solver TARGET/fairness;
- T020 U/C presentation.

WorkBalance exposes `absence_hours`; effective target is `max(0, target_hours - absence_hours)`. TARGET remains SOFT.

Consumers do not choose source mode from CURRENT and do not reimplement SICK/LEAVE precedence, anchor rules or Site filtering.

## 14. T020

PRE_PLAN_LEAVE:
- preserve owner-approved deterministic exact-sum Site legend allocation/decomposition;
- 40h example remains `D1/D1/N2` + `U1/U1/U2`;
- no nominal Assignment/demand provenance is fabricated;
- no rounding or invented symbols;
- where global pre-PLAN leave has no schedule provenance to allocate across multiple LOCAL Sites, preserve the existing fail-closed Site-attribution boundary rather than duplicate it.

POST_PLAN_REFERENCE:
- place PLAN at the exact preserved period anchor;
- place equal-hour U/C below it;
- Site comes from bound schedule provenance;
- multiple memberships alone are not ambiguity;
- no monthly coin-change relocation for bound post-PLAN periods.

## 15. NON-GOALS

No payroll/HR, leave pool, SiteProfile strategy, nominal absence Assignment layer, duplicate ledger, workflow engine, WorkBalance history, guessed historical backfill, new legend or new schedule-version system.

## 16. REQUIRED REGRESSION GUARANTEES

Implementation must prove at least:
1. PRE_PLAN_LEAVE owner 40h example remains valid.
2. Root WORKING created by `plan_month()` without candidate selection is not accepted PLAN.
3. Successful `SCHEDULE_CANDIDATE_SELECTED` is accepted-plan proof, including a valid accepted empty schedule.
4. Unselected REPLAN child does not hide an accepted applicable parent.
5. POST_PLAN 8/12/N/24/rest/weekend/holiday arithmetic follows exact bound schedule.
6. Both owner N 17:00-05:00 examples and cross-month/year 24h anchor once.
7. Dormant EXTERNAL_SUPPORT cannot create MISSING; real external-site PRIMARY work counts once.
8. TRAINEE does not add hours or create T023-only ambiguity.
9. Explicit seven-day range gives weekly canonical total.
10. Past known rest day in a new absence range is not rejected solely because the date elapsed.
11. New coverage over started/REALIZED PRIMARY is rejected atomically.
12. REPLAN selection cannot remove/change/add any non-CANCELLED PRIMARY started before acceptance cutover.
13. Later WORKING replacement/REPLAN/finalize/restore/restart cannot alter bound post-PLAN reference facts.
14. SICK-over-LEAVE produces one C.
15. Solver, WorkBalance/analytics and T020 consume the same canonical result.
16. Absent Employee never operationally covers ShiftDemand.
17. Existing unrelated T012/HARD/calendar rules remain unchanged.
