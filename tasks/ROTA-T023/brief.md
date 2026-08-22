# ROTA-T023 — SCHEDULE-BASED ABSENCE HOURS — ARCHITECT IMPLEMENTATION CONTRACT

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-22
TASK_ID: ROTA-T023
BASE_BRANCH: main
BASE_SHA: e05dfb7dd4463370bf8174db7ae58a9b984cf99e
TASK_BRANCH: task/ROTA-T023
ARCHITECT_INPUT_HEAD: 7483712ce66a42606cb31562bb5f62aa51bc91a8
OWNER_SOURCE: arch/T023_absence_hours_architect_brief.md
OWNER_NIGHT_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_NIGHT_SHIFT_ANCHOR.md
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
SUPERSEDES_IN_PART:
- arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md
- tasks/ROTA-T018/brief.md
- tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md
- tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md

CC_GATE: BLOCKED UNTIL INDEPENDENT CODEX PREIMPLEMENTATION PASS ON THE EXACT ARCHITECT CONTRACT SHA

## 1. GOAL

Replace T018/T020 flat workday absence accounting with one durable schedule-based absence truth:

`absence_hours = hours scheduled for the Employee in the adopted reference schedule during the granted absence`

The implementation must bind the pre-absence schedule fact before absence-driven replacement can erase it, then make solver TARGET, WorkBalance/analytics and T020 PDF consume the same canonical result.

No payroll/HR scope and no new operational absence Assignment layer.

## 2. NON-NEGOTIABLE PRODUCT RULES

1. One algorithm for every Site/profile: scheduled reference hours, never profile-specific flat hours.
2. 8h -> 8h; 12h -> 12h; legal 24h WorkPeriod -> 24h once.
3. Weekend/holiday scheduled work counts; known reference rest = 0.
4. Missing/ambiguous/unreadable reference fails closed.
5. `SICK_LEAVE` and `LEAVE_GRANTED` both consume the canonical hours in WorkBalance and live solver TARGET.
6. `LEAVE_PLAN` contributes 0 actual absence hours.
7. SICK wins overlap with LEAVE_GRANTED: one C, no U+C.
8. N `17:00-05:00` belongs wholly to its start date.
9. Persisted legal 24h WorkPeriod uses the same start-date anchor, including month/year boundaries.
10. Later REPLAN/finalize/restore/restart/CURRENT movement must not change a bound reference.
11. REALIZED work is never rewritten to U/C; overlap is a visible fail-closed conflict.
12. Multi-Site aggregate is Employee-global; Site PDF is a local projection of the same bound facts, with no duplicate membership allocation.
13. Absent Employees remain operationally ineligible and never cover Site demand through nominal U/C data.
14. T023 does not define new D/N/U/C legend values.

## 3. MECHANICAL FINDINGS THAT DRIVE THE DESIGN

Verified at architect input HEAD:

- `AvailabilityRecord` has no schedule reference/capture timestamp.
- availability history is append-only.
- `AVAILABILITY_CHANGED` is written atomically with the availability mutation, but its coordinator-action `schedule_version_id` is currently `None`.
- coordinator-action rows can carry one schedule id, but T023 reference can span multiple Sites/months/versions, so that field is not the canonical provenance surface.
- CURRENT ScheduleVersion is Site/month scoped.
- FINAL ScheduleVersion content is immutable.
- a current WORKING ScheduleVersion can be replaced in place under the same `version_id`; therefore persisting only `schedule_version_id` is insufficient.
- WorkBalance rows are not persisted; only target_hours is stored.
- T020 already reconstructs current lineage by `effective_from`, but its absence path separately recounts flat-8 workdays.
- `PlanningState` carries WorkBalance, so solver can consume canonical `WorkBalance.absence_hours` without adding a second absence calculation to the solver.

## 4. PERSISTENCE — MIGRATION 8

Advance `LATEST_SCHEMA_VERSION` from 7 to 8.

Migration 8 adds exactly one table:

`absence_reference_snapshots`

Required columns:

- `availability_version_id TEXT PRIMARY KEY`
  - references the persisted AvailabilityVersion identity;
- `captured_at TEXT NOT NULL`;
- `reference_status TEXT NOT NULL`
  - exact values `BOUND`, `MISSING`, `AMBIGUOUS`;
- `snapshot_json TEXT NOT NULL`
  - deterministic canonical JSON described below.

Add append-only triggers rejecting UPDATE and DELETE.

No historical backfill is performed.

No current-pointer table is added. No WorkBalance history table is added. No second Assignment table is added.

### 4.1 Snapshot JSON contract

The JSON is deterministic (`sort_keys=True` plus deterministic list ordering) and contains:

- `scope_site_ids`: sorted unique Site ids considered at capture;
- `months`: sorted by Site id then calendar month;
- each Site/month block:
  - `site_id`;
  - `month`;
  - `status` = `BOUND` / `MISSING` / `AMBIGUOUS`;
  - `days`, sorted by date;
- each day:
  - `date`;
  - `status`;
  - selected source ScheduleVersion id when one coherent version owns that day;
  - zero or more normalized reference periods anchored on that date;
  - an explicit diagnostic reason when not BOUND;
- each reference period:
  - `site_id`;
  - `anchor_date`;
  - ordered component facts;
- each component fact preserves at least:
  - source `schedule_version_id`;
  - source `assignment_id`;
  - source `demand_id`;
  - start/end datetime;
  - Assignment state;
  - ShiftDemand `shift_kind`;
  - ShiftDemand `catalog_kind`;
  - `work_period_id`;
  - `work_period_template_id`;
  - `work_period_component`.

The snapshot may retain ids whose mutable WORKING child rows later disappear. They are historical provenance labels, not pointers that must be re-read to recompute hours.

Do not persist a derived flat `absence_hours` as the only source fact. Canonical hours are recalculated deterministically from the immutable captured period intervals/components.

### 4.2 Shared value types

The narrow immutable DTO/enums required to represent a decoded snapshot belong in `rota/domain.py`; they must contain no repository/service behavior.

`WorkBalance` gains `absence_hours: int = 0` as a non-persisted computed field. Existing positional callers must remain mechanically compatible by adding the field at the end with a default.

## 5. REFERENCE CAPTURE BOUNDARY

`rota/persistence/absence_reference_repository.py` is the one new production repository module.

It owns:
- deterministic snapshot encode/decode;
- batch reads by AvailabilityVersion id;
- reference capture from schedule history/current pointers;
- same-chain inheritance/overlap reuse;
- no accounting arithmetic.

`rota/persistence/availability_repository.py` remains the owner of AvailabilityVersion append.

For active `SICK_LEAVE` / `LEAVE_GRANTED`:
1. append the AvailabilityVersion inside the existing open transaction;
2. the write obtains the SQLite write lock before reference capture;
3. capture the reference snapshot in the same transaction;
4. persist the immutable snapshot row;
5. the existing application-level coordinator action/invalidation completes in that same outer transaction where applicable.

Missing/ambiguous schedule truth is encoded as `MISSING`/`AMBIGUOUS`; it is not converted to 0 and does not cause the availability fact itself to be omitted.

Unexpected persistence failure rolls the transaction back normally.

For inactive versions and other AvailabilityKind values, no reference snapshot is required.

The existing coordinator-action `schedule_version_id` MUST remain `None` for `AVAILABILITY_CHANGED`; do not stuff one arbitrary version id into a fact that can span several Sites/versions. The canonical linkage is `absence_reference_snapshots`.

## 6. REFERENCE SCOPE AND READABILITY

### 6.1 Site scope at capture

For the Employee, reference scope is the deterministic union of:
- all currently enabled Site memberships, regardless of LOCAL/EXTERNAL_SUPPORT kind; and
- Sites owning any current non-CANCELLED Assignment for that Employee overlapping the captured month range/boundary context.

If the union is empty for an active granted absence, global reference status is `MISSING`, not known 0h.

This scope is captured and does not change when memberships change later.

### 6.2 Month horizon

For every active granted AvailabilityVersion, capture complete reference Site/month blocks for every calendar month intersecting its inclusive range.

Capturing the full intersecting month, not only currently absent dates, is required so a later correction/extension in the same Availability chain cannot rebind newly included days to a post-absence REPLAN.

Adjacent date/month facts required to prove a 24h WorkPeriod are captured with the anchored period even when a component is outside the absence range.

### 6.3 Effective schedule selection

Extract the existing T020 lineage/date-selection mechanics into reusable read helpers in `rota/persistence/schedule_repository.py`; both T020 real-work reconstruction and T023 reference capture must use the same helper rather than two drifting lineage algorithms.

For each Site/date:
- follow CURRENT lineage to root;
- reject cycle/missing parent/context mismatch;
- every used version needs real `effective_from`;
- select the deepest lineage version with `effective_from <= date`.

No CURRENT schedule / no applicable version is `MISSING`.

### 6.4 Readable adopted day

A selected Site/day is BOUND only if persisted operational schedule truth is coherent enough to prove that day's plan:
- ShiftDemand/PRIMARY coverage for the selected day is complete;
- assignment-to-demand provenance is coherent;
- the Employee's non-CANCELLED PRIMARY reference items are unambiguous;
- a referenced 24h WorkPeriod has coherent linked components.

An unfinished/unselected schedule with uncovered demand is not evidence that the Employee rests.

A BOUND day with zero reference periods for the Employee is known 0h.

An effective TRAINEE item for the absent Employee has no frozen T023 absence-accounting presentation semantics and therefore makes that reference day `AMBIGUOUS`; do not count it as PRIMARY and do not silently ignore it.

Disjoint independent PRIMARY periods anchored on the same date may contribute their exact summed hours to accounting; overlapping/contradictory periods are `AMBIGUOUS`. T020 may still fail its existing one-cell presentation boundary if more than one period must occupy one cell.

## 7. INHERITANCE / OVERLAP RULES

### 7.1 Same Availability chain

When appending a new active version of an existing `availability_id`:
- copy every already-captured Site/month block from the latest predecessor snapshot when that Site/month remains relevant;
- do not recapture that month from CURRENT;
- capture only newly required Site/month blocks not present in the predecessor baseline.

This preserves the original pre-absence month schedule across date corrections/extensions.

### 7.2 Different granted-absence chains

When capturing a day that overlaps another currently active granted absence for the same Employee:
- reuse compatible already-bound day facts from the other active granted record;
- if more than one candidate bound reference disagrees, persist `AMBIGUOUS`;
- never choose the newest CURRENT snapshot merely because it is available.

This is mandatory for SICK-over-LEAVE after a leave-driven REPLAN.

## 8. CANONICAL ACCOUNTING API

`rota/planning/absence.py` remains pure and persistence-free.

Remove the governing use of:
- `EXCUSED_ABSENCE_HOURS_PER_DAY`;
- `excused_absence_days_in_month`;
- weekday/nonholiday filtering;
- `IncompleteAbsenceCalendarError` as an absence-accounting error.

Provide one canonical reference-period calculation that accepts:
- active AvailabilityRecords;
- decoded AbsenceReferenceSnapshots;
- requested month/date scope;
- optional `site_id` projection;
- current REALIZED assignments when the consumer has them for conflict detection.

Required result contains at least:
- total `absence_hours`;
- `leave_hours`;
- `sick_hours`;
- ordered period-level facts used for presentation;
- kind (U/C) after precedence.

Required fail-closed errors:
- incomplete reference;
- ambiguous reference;
- REALIZED-vs-absence conflict.

No consumer reimplements precedence, anchoring, period duration or Site filtering.

### 8.1 Kind precedence

For each anchored reference period:
1. if any active SICK_LEAVE covers the anchor date -> C/SICK;
2. else if any active LEAVE_GRANTED covers the anchor date -> U/LEAVE;
3. else it is not an absence period.

Multiple active records of the selected kind must resolve to the same bound reference fact; disagreement is ambiguous.

LEAVE_PLAN is ignored by actual-hours accounting.

### 8.2 Period duration and anchors

Duration is exact persisted scheduled interval duration from bound reference components.

A linked legal 24h WorkPeriod is one 24h period anchored at the WorkPeriod start.

An ordinary overnight N `17:00-05:00` is one period anchored at its start date.

No midnight splitting.

## 9. WORKBALANCE / ANALYTICS

`rota/balance.py` calls only the canonical T023 absence primitive.

`compute_month_balance`:
- keeps PRIMARY PLANNED/REALIZED operational Assignment sums unchanged;
- computes canonical Employee-global absence hours from bound references;
- sets `WorkBalance.absence_hours`;
- uses `effective_target_hours = target_hours - absence_hours`;
- keeps `month_balance = realized_hours + planned_hours - effective_target_hours`.

`calendar_days` may remain temporarily accepted as a compatibility argument, but it MUST NOT influence T023 absence hours.

`rota/persistence/work_balance_repository.py`:
- loads current assignments exactly as today;
- loads current active availability;
- loads their reference snapshots in batch;
- does not load CalendarDay for absence arithmetic;
- never persists computed balance rows.

`rota/application/analytics_read.py`:
- uses the same canonical snapshots/arithmetic;
- adds `absence_hours` to `AnalyticsMonthData`;
- derives `effective_target_hours` directly as `target_hours - absence_hours`;
- replaces CalendarDay-specific absence warnings with stable reference-incomplete/reference-ambiguous/REALIZED-conflict degradation;
- keeps `AnalyticsHoursScope.ALL_SITES`.

`rota/application/balance_read.py` must degrade expected T023 reference errors to an explicit unavailable warning rather than returning a guessed/partial quarter.

No new analytics screen or payroll field is added.

## 10. SOLVER TARGET

Rename/replace the SICK-only helper with absence-generic target adjustment.

The solver MUST consume the `absence_hours` already present on the assembled WorkBalance for that Employee/month. It MUST NOT:
- recount AvailabilityRecords;
- read CalendarDay;
- call a separate flat-8 helper;
- treat LEAVE_GRANTED differently from SICK_LEAVE.

Adjusted target:

`max(0, work_balance.target_hours - work_balance.absence_hours)`

Use the same lower-bound behavior the current solver uses for SICK adjustment; do not create a negative TARGET.

TARGET remains SOFT. No HARD eligibility rule changes.

`rota/planning/engine.py` removes T018's eager CalendarDay-based absence validation. Reference incompleteness is detected before/while WorkBalance is assembled and through the canonical T023 errors, not by checking a holiday calendar.

Public PLAN/REPLAN application boundaries must return/fail closed as TECHNICAL_ERROR for a reference-accounting failure; they must not continue with `absence_hours=0`.

## 11. T020 PDF

T020 remains a presentation feature and never creates operational Assignments.

Replace `_collect_absence` flat-day/month-total logic with canonical site-projected reference periods.

For each printed LOCAL Employee:
- ask canonical T023 accounting for the printed Site/month;
- only reference periods with `period.site_id == printed site_id` may produce U/C;
- a Site absent from the bound scope contributes 0h to that Site;
- more than one LOCAL membership is not `ABSENCE_SITE_AMBIGUOUS`.

Placement is 1:1 with reference periods:
- anchor at reference period start date;
- PLAN code maps the exact bound reference period interval/kind or existing 24h rule;
- WYK code is U/C of exactly equal hours;
- no monthly total coin-change movement to unrelated dates.

SICK+LEAVE overlap prints one C.

`ASSIGNMENT_ABSENCE_CONFLICT` remains the explicit T020 problem for actual REALIZED/current work overlapping granted absence. A planned nominal reference period is not itself this conflict.

Add/make available stable provenance problems:
- `ABSENCE_REFERENCE_INCOMPLETE`;
- `ABSENCE_REFERENCE_AMBIGUOUS`.

The old `ABSENCE_SITE_AMBIGUOUS` and SICK+LEAVE `ABSENCE_KIND_CONFLICT` behavior is superseded and must not be triggered for those old conditions.

Existing exact print-code fail-closed rules remain:
- no rounding;
- no invented D/N/U/C code;
- no combining unrelated reference days to manufacture a representable total;
- if an exact reference period has no legal PLAN/WYK presentation pair, return the existing explicit presentation problem.

Real-work lineage/24h behavior unrelated to absence remains unchanged.

`schedule_export.py` must stay within the repository size gate by deleting/replacing the superseded flat-8/coin-change absence path, not by layering a second path on top.

## 12. REALIZED CONFLICT

Canonical accounting must detect both:
- a bound reference component already REALIZED when the later/retroactive absence is recorded; and
- a current REALIZED PRIMARY Assignment whose start-date anchor overlaps an active granted absence.

On conflict:
- underlying Assignment state remains REALIZED;
- WorkBalance/analytics numerical absence result for the affected scope is unavailable/fail-closed;
- solver planning does not silently reduce TARGET from an unresolved conflicting absence;
- T020 surfaces `ASSIGNMENT_ABSENCE_CONFLICT` and does not replace the worked cell with U/C.

No automatic correction is authorized.

## 13. MULTI-SITE

Global WorkBalance/analytics:
- use all Site reference periods in the captured scope;
- deduplicate by canonical bound period identity;
- require complete/consistent global reference scope.

T020:
- projects only the printed Site;
- does not duplicate global hours on every membership;
- does not infer Site ownership from readiness/target/current distribution.

A reference Site not present in the captured scope contributes 0 to that Site projection; a Site present in scope but MISSING/AMBIGUOUS fails that Site projection.

## 14. NO LEGACY BACKFILL

Migration 8 MUST NOT create guessed snapshots for pre-T023 AvailabilityVersions.

For an active pre-migration SICK_LEAVE/LEAVE_GRANTED with no snapshot:
- canonical accounting raises reference-incomplete;
- WorkBalance/analytics/PDF/solver target do not substitute old flat 8;
- CURRENT is not used as a historical reconstruction fallback.

A future explicit remediation feature is outside T023.

## 15. EXACT TASK_SCOPE

TASK_SCOPE:
- arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
- tasks/ROTA-T023/brief.md
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/absence_reference_repository.py
- rota/persistence/availability_repository.py
- rota/persistence/schedule_repository.py
- rota/planning/absence.py
- rota/planning/solver.py
- rota/planning/engine.py
- rota/balance.py
- rota/persistence/work_balance_repository.py
- rota/application/analytics_read.py
- rota/application/balance_read.py
- rota/application/schedule_export.py
- rota/application/plan_ops.py
- tests/test_t023.py
- tests/test_t018.py
- tests/test_sick_leave.py
- tests/test_balance.py
- tests/test_t019.py
- tests/test_t020.py
- tests/test_t019b.py
- tests/test_t012.py
- tests/test_audit_r20_r21_findings.py
- tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py

NEW_FILES:
- arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md
- tasks/ROTA-T023/brief.md
- rota/persistence/absence_reference_repository.py
- tests/test_t023.py

No other file may change without STOP + architect scope amendment based on a concrete compiler/test/audit finding.

Explicitly OUT OF SCOPE:
- arch/spec.md
- arch/FROZEN.lock
- rota/planning/eligibility.py
- rota/planning/validator.py
- rota/planning/constraints.py
- rota/planning/work_periods.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/site_memory.py
- SiteProfile absence strategy/configuration
- T020 print-settings schema/legend values
- payroll/HR modules

## 16. CHECKPOINT ORDER

T023 is too cross-cutting to review safely as one undifferentiated implementation diff. Use one task branch and three ordered implementation checkpoints; do not merge an intermediate checkpoint to main.

### Checkpoint A — provenance + canonical core

Allowed production subset:
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/absence_reference_repository.py
- rota/persistence/availability_repository.py
- rota/persistence/schedule_repository.py
- rota/planning/absence.py
- dedicated/migration tests needed for A

Must prove:
- migration 8;
- append-only snapshot;
- atomic AvailabilityVersion + snapshot;
- same-chain inheritance;
- WORKING in-place mutation cannot change bound facts;
- REPLAN/restore/restart invariants;
- 8/12/N/24/rest/weekend/holiday/start-date/missing/ambiguous/multi-Site canonical core.

No solver/balance/export behavior switch before A passes targeted audit.

### Checkpoint B — WorkBalance + solver + analytics

Allowed production subset:
- rota/balance.py
- rota/persistence/work_balance_repository.py
- rota/planning/solver.py
- rota/planning/engine.py
- rota/application/analytics_read.py
- rota/application/balance_read.py
- rota/application/plan_ops.py
- related tests

Must prove one canonical `absence_hours` reaches:
- WorkBalance;
- analytics;
- both SICK and LEAVE_GRANTED live TARGET;
- quarter reads;
- reference failures remain fail-closed.

HARD availability behavior must stay unchanged.

### Checkpoint C — T020 presentation + regression closure

Allowed production subset:
- rota/application/schedule_export.py
- related T020/T018/regression tests

Must prove:
- exact reference-period placement;
- one C for SICK-over-LEAVE;
- Site-local projection/no duplication;
- REALIZED conflict;
- no aggregate coin-change;
- no new legend;
- real-work/T012 presentation regressions unchanged.

### Final gate

After C:
- full suite;
- Ruff/format/lint guards used by repository;
- `git diff --check`;
- size/function guards;
- independent Codex implementation audit against the final product SHA;
- architect final acceptance before merge.

## 17. REQUIRED T023 TEST MATRIX

### Persistence / invariance

T23-01 — v7 -> v8 migration preserves all prior data and adds exactly `absence_reference_snapshots`.

T23-02 — snapshot UPDATE/DELETE rejected; deterministic encode/decode survives restart.

T23-03 — active SICK/LEAVE append writes AvailabilityVersion + reference snapshot atomically; forced snapshot insert failure leaves neither partial reference nor partial availability write.

T23-04 — `AVAILABILITY_CHANGED` action remains one logical action and keeps `schedule_version_id=None`; snapshot contains actual multi-version provenance.

T23-05 — reference captured from a WORKING schedule remains unchanged after `replace_working_snapshot()` mutates the same `version_id`.

T23-06 — bind after PLAN, replacement REPLAN, finalize, restart: canonical periods/hours identical.

T23-07 — restore CURRENT to older version after bind: canonical periods/hours identical.

T23-08 — same Availability chain extension within an already-captured month reuses predecessor month facts; new month is captured separately.

T23-09 — SICK added after LEAVE-driven REPLAN reuses the pre-leave overlapping reference; disagreement between candidate inherited references is AMBIGUOUS.

### Canonical arithmetic

T23-10 — scheduled 8h -> 8 absence_hours.

T23-11 — 12h D -> 12; equivalent 12h N -> 12.

T23-12 — `2027-03-01 17:00 -> 2027-03-02 05:00`, absence starts Mar 2 -> 0.

T23-13 — same N, absence includes Mar 1 -> full 12 on Mar 1.

T23-14 — legal persisted 24h WorkPeriod -> 24 once on start date.

T23-15 — 24h cross-month and cross-year component -> 24 once, no second-month double count.

T23-16 — BOUND readable day with no Employee period -> 0.

T23-17 — scheduled Saturday/Sunday and `CalendarDay.holiday=True` -> scheduled hours unchanged.

T23-18 — MISSING/AMBIGUOUS reference -> explicit fail-closed error, never 0/8.

T23-19 — LEAVE_PLAN -> 0 actual absence.

T23-20 — SICK+LEAVE overlap -> one period, SICK/C classification, no double hours.

T23-21 — disjoint same-day PRIMARY periods sum exact non-overlapping duration; overlapping contradictory periods -> AMBIGUOUS.

T23-22 — effective TRAINEE reference -> AMBIGUOUS/fail closed, not silently counted/ignored.

T23-23 — REALIZED-at-bind or current REALIZED overlap -> explicit conflict; Assignment remains REALIZED.

### Multi-Site

T23-24 — Employee has schedules on Site A and B: global total = A+B once.

T23-25 — Site A projection = only A; Site B projection = only B; membership count causes no duplication.

T23-26 — printed Site absent from captured reference scope -> 0 local absence.

T23-27 — Site in captured scope with missing reference -> Site projection fails; global projection also fails.

### Consumer equality

T23-30 — WorkBalance.absence_hours equals canonical global result and effective target is target-absence.

T23-31 — SICK and LEAVE_GRANTED with equal reference schedule reduce solver TARGET identically.

T23-32 — solver uses WorkBalance.absence_hours and does not call a CalendarDay/flat-day counter.

T23-33 — AnalyticsMonthData.absence_hours and effective_target_hours equal WorkBalance.

T23-34 — quarter analytics/read uses the same month canonical results; one bad reference month degrades quarter without partial numeric guess.

T23-35 — T020 `urlop_hours` / `l4_hours` equals canonical Site projection for same bound periods.

### T020 presentation

T23-40 — reference 12h D/N appears on exact anchored PLAN date with equal U/C WYK code.

T23-41 — reference 24h period prints once on start date when existing legal equal-hour U/C code is configured.

T23-42 — no-reference rest day creates no synthetic U/C symbol.

T23-43 — old 40h empty-schedule synthetic `D1/D1/N2` allocation is gone: empty BOUND reference = 0.

T23-44 — one-day correct 8h accounting with no legal existing PLAN/WYK 8h pair remains explicit presentation failure; no invented code.

T23-45 — SICK+LEAVE overlap prints C only; no `ABSENCE_KIND_CONFLICT`.

T23-46 — two LOCAL memberships do not cause `ABSENCE_SITE_AMBIGUOUS`; each Site sees only its bound periods.

T23-47 — REALIZED overlap returns `ASSIGNMENT_ABSENCE_CONFLICT`; actual work fact is untouched.

### HARD / coverage regression

T23-50 — SICK_LEAVE still HARD-blocks operational Assignment on every calendar date in its inclusive range.

T23-51 — LEAVE_GRANTED still HARD-blocks operational Assignment; outside range remains eligible.

T23-52 — absent Employee never covers ShiftDemand; another eligible PRIMARY covers it or existing DECISION_REQUIRED remains.

T23-53 — CalendarDay holiday/weekend no longer changes absence hours but still affects unrelated frozen rules that consume CalendarDay.

T23-54 — T012 emergency/normal 24h legality and rest semantics unchanged.

## 18. DELIBERATE SUPERSESSION / IMPACT LIST

Historical documents are not rewritten. The following oracles are deliberately superseded only in the named sense.

### 18.1 T018 frozen addendum / direct T018 tests

`arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md`
- superseded: Monday-Friday/nonholiday + 8h arithmetic and calendar-completeness requirement as absence-hour source;
- preserved: HARD SICK/LEAVE blocking and unrelated T018 DAY_ONLY fallback.

`tests/test_t018.py`
- `test_a7_1_sick_leave_across_two_weekends_counts_only_weekdays` — superseded.
- `test_a7_2_leave_granted_gets_identical_workday_filter_in_workbalance` — superseded.
- `test_a7_3_weekday_holiday_excluded_from_workday_count` — superseded; scheduled holiday now counts.
- `test_a7_4_weekend_holiday_still_zero_no_double_effect` — superseded as an accounting oracle; reference schedule decides 0 vs scheduled hours.
- `test_a7_5_overlapping_sick_and_leave_dedup_before_workday_filter` — superseded by reference-period dedup + SICK precedence.
- `test_a7_6_cross_month_range_clips_and_filters_workdays` — superseded by start-date anchored periods.
- `test_a7_7_weekend_absence_still_hard_blocks_assignment` — PRESERVED.
- `test_a7_8_incomplete_calendar_with_qualifying_absence_fails_closed` — superseded by reference-completeness fail-closed; missing CalendarDay alone is no longer the absence error.
- `test_a7_9_direct_plan_with_incomplete_calendar_and_sick_absence_is_technical_error` — superseded only where CalendarDay absence validation caused the status.
- `test_a7_10_legacy_balance_call_without_absence_or_calendar_keeps_result` — PRESERVED.
- `test_a7_11a_round23_solver_l4_march_2027_reduces_target_to_56` — superseded numeric oracle.
- `test_a7_11b_round23_quarter_balance_leave_march_2027_reduces_target_to_56` — superseded numeric oracle.
- `test_a7_11c_round23_solver_l4_excludes_weekday_public_holiday` — superseded.
- `test_a7_12_march_2027_workbalance_target_56_at_target_168` — superseded numeric oracle.
- all Checkpoint-B DAY_ONLY fallback tests are outside the T023 semantic change and must remain unchanged.

`tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py`
- all three flat workday/public-holiday arithmetic oracles are superseded.

`tests/test_audit_r20_r21_findings.py`
- R21-1 direct flat-workday absence-helper expectation is superseded;
- unrelated R20/R21 conflict/status oracles remain unchanged.

### 18.2 SICK/WorkBalance

`tests/test_sick_leave.py`
- module flat-8 accounting statement is superseded;
- `test_sick_leave_reduces_target_by_8h_per_day_not_shift_length` — superseded;
- `test_leave_granted_does_not_reduce_solver_target_unlike_sick_leave` — explicitly superseded: LEAVE_GRANTED now consumes canonical absence_hours in live TARGET too;
- HARD blocking, outside-range eligibility and REPLAN redistribution meaning remain preserved, with new reference fixtures where required.

`tests/test_balance.py`
- `test_leave_granted_reduces_effective_target_by_8h_per_day_for_balance` — superseded by reference-schedule hours;
- non-absence PLANNED/REALIZED/quarter tests preserved.

### 18.3 T019 analytics

`tests/test_t019.py`
- `test_10_requested_month_incomplete_calendar_with_qualifying_absence` — CalendarDay-specific failure reason superseded by reference status.
- `test_11_other_quarter_month_incomplete_calendar_blocks_quarter_only` — same.
- `test_12_sick_leave_weekend_holiday_workday_only` — superseded.
- `test_13_leave_granted_weekend_holiday_same_semantics` — superseded.
- non-absence analytics/current/restore/cross-Site row oracles preserved.

### 18.4 T020

`tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md` and `CHECKPOINT_B_CONTRACT.md`
- superseded only for flat T018 hours, monthly synthetic absence decomposition, multi-LOCAL `ABSENCE_SITE_AMBIGUOUS`, and SICK+LEAVE `ABSENCE_KIND_CONFLICT`;
- preserved: U/C is presentation not operational coverage, row population, exact legend mapping/fail-closed, real work lineage, 24h real-work presentation, no duplicate demand.

`tests/test_t020.py`
- `test_t20_14_frozen_40h_leave_decomposition` — superseded: an empty readable reference schedule is 0h, not synthetic 40h.
- `test_t20_19_overlapping_leave_and_sick_conflict` — superseded by one C.
- `test_t20_21_multi_site_local_employee_absence_is_ambiguous` — superseded by reference Site projection/no duplication.
- one-day/non-decomposable exact-code tests remain valid where they assert no invented legend; their accounting setup must use a real reference period rather than flat-day synthesis.
- `ASSIGNMENT_ABSENCE_CONFLICT` remains for actual REALIZED/current-work conflict, not for a planned nominal reference period.
- all real-work, roster, font, revision, lineage and T012 linkage oracles remain unchanged unless a mechanical fixture must provide T023 reference provenance.

### 18.5 Schema literals

Mechanical only:
- `tests/test_t012.py::test_a_current_schema_reconnect_is_idempotent`: latest schema literal 7 -> 8.
- `tests/test_t019b.py::test_a1_real_v5_to_latest_migration_preserves_data_and_adds_expected_tables`: latest 7 -> 8 and expected delta adds exactly `absence_reference_snapshots`.
- T020 migration tests that assert latest schema 7 must assert latest 8 while still proving migration-7 `site_print_settings` behavior.

No other historical oracle may be weakened merely to make the suite pass.

## 19. PREIMPLEMENTATION AUDIT GATE

Independent Codex must audit the exact architect contract HEAD before CC writes production code.

Audit questions:
1. Does the contract implement every owner rule in `arch/T023_absence_hours_architect_brief.md`, including 17:00-05:00?
2. Can any later WORKING in-place replacement/REPLAN/restore/restart alter bound hours?
3. Can a missing schedule become false 0h?
4. Can SICK-over-LEAVE after prior REPLAN accidentally capture replacement-worker/current truth?
5. Can multi-Site hours duplicate through memberships?
6. Do solver, WorkBalance/analytics and T020 have exactly one arithmetic/precedence owner?
7. Is REALIZED work preserved and conflict surfaced?
8. Does T020 still avoid nominal operational Assignments and invented legend values?
9. Are all known superseded oracles explicitly enumerated?
10. Does TASK_SCOPE contain every required implementation/test file and no unrelated redesign?

Required audit verdict:
`PASS — READY_FOR_IMPLEMENTATION`
or a concrete finding list.

Until PASS:
`NOT READY FOR CC`.

## 20. IMPLEMENTATION / FINAL GATES

After preimplementation PASS:
1. CC implements only the current checkpoint scope.
2. Targeted tests for that checkpoint pass.
3. Architect reviews exact product SHA/diff before advancing checkpoint.
4. After Checkpoint C, independent Codex audits final implementation SHA.
5. Full suite + repository guards pass.
6. Architect issues final acceptance or concrete findings.
7. Merge remains an explicit owner action.

No implementation commit is authorized by this architect-document commit itself.

## 21. ARCHITECT OUTPUT STATUS

READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
