# FROZEN ADDENDUM — SCHEDULE-BASED ABSENCE ACCOUNTING 01

STATUS: FROZEN PRODUCT ADDENDUM — PREIMPLEMENTATION
DATE: 2026-08-22
TASK_ID: ROTA-T023
OWNER_SOURCE: arch/T023_absence_hours_architect_brief.md
OWNER_NIGHT_DECISION: tasks/ROTA-T023/round_01/OWNER_DECISION_NIGHT_SHIFT_ANCHOR.md
SUPERSEDES_FOR_ABSENCE_HOURS: arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md

## 1. PRECEDENCE AND PRESERVED BEHAVIOR

This addendum supersedes `arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md` only where that addendum defines absence-hour arithmetic from calendar workdays.

Superseded:
- flat `8 h` per qualifying Monday-Friday/nonholiday day;
- `CalendarDay.holiday` / weekday filtering as the source of absence hours;
- `EXCUSED_ABSENCE_HOURS_PER_DAY=8` as the governing accounting rule;
- solver SICK-only target arithmetic;
- T020's independent flat-8 absence total, SICK+LEAVE overlap rejection, membership-count attribution rule and monthly aggregate coin-change placement.

Preserved:
- active `SICK_LEAVE` and `LEAVE_GRANTED` remain HARD availability exclusions for operational Assignment eligibility;
- absence date ranges remain inclusive calendar ranges for the HARD collision check;
- absent Employees never receive nominal operational coverage Assignments merely to represent U/C;
- real Site demand remains covered by operationally eligible PRIMARY Employees;
- WorkBalance remains Employee-global/cross-Site;
- ScheduleVersion history/lifecycle, T012 work-period legality and all unrelated frozen rules remain unchanged.

## 2. ONE CANONICAL ACCOUNTING RULE

For every Site, SiteProfile and industry:

`absence_hours = hours scheduled for the Employee in the adopted reference schedule during the granted absence`

There is no per-profile accounting strategy and no flat-hours fallback.

Consequences:
- an 8h scheduled work period contributes 8h;
- a 12h scheduled D or N period contributes 12h;
- a legal persisted 24h WorkPeriod contributes 24h once;
- a scheduled Saturday, Sunday or holiday contributes its scheduled hours;
- a readable adopted reference schedule proving no work period on the anchored date contributes 0h;
- weekday and `CalendarDay.holiday` values do not alter this arithmetic;
- missing, ambiguous or unreadable reference truth is not a rest day and must fail closed.

## 3. ADOPTED REFERENCE SCHEDULE

The adopted reference schedule is the durable schedule truth applicable before an absence-driven replacement/replan can remove or replace the absent Employee's operational Assignment.

A reference Site/day is readable only when:
1. the Site/month has a coherent CURRENT ScheduleVersion lineage;
2. every lineage header used for date selection belongs to the same Site/month and has real `effective_from`;
3. the deepest lineage version with `effective_from <= anchored date` is deterministically selectable;
4. persisted ShiftDemand/PRIMARY coverage for that selected day is structurally complete enough to distinguish a known rest day from an unfinished/unadopted schedule;
5. every reference work item needed for the Employee has coherent persisted Assignment/ShiftDemand provenance;
6. a persisted 24h WorkPeriod needed by the reference has coherent linked components, including an adjacent-month/year component when applicable.

A readable selected day with no reference work item for the Employee is a known 0h day.

A missing CURRENT schedule, incomplete/unadopted coverage, broken lineage, missing effective date, dangling provenance, contradictory work items, malformed 24h linkage or another state that cannot prove one schedule fact is `MISSING`/`AMBIGUOUS`, never 0h.

## 4. DURABLE BINDING INVARIANT

Reference facts are bound when an active `SICK_LEAVE` or `LEAVE_GRANTED` AvailabilityVersion is appended, before any later absence-driven schedule mutation.

The bound reference is immutable historical input for absence accounting. Later:
- candidate selection that replaces a WORKING snapshot in place;
- REPLAN child creation;
- FINAL transition;
- restore to an older ScheduleVersion;
- restart;
- CURRENT pointer movement;
- replacement-worker assignment

must not alter already-bound reference hours.

A mere `schedule_version_id` pointer is insufficient because a current WORKING ScheduleVersion may be replaced in place under the same id. The durable binding therefore preserves the exact reference work-period facts used for accounting together with source ScheduleVersion/Assignment/ShiftDemand identifiers.

No historical backfill may infer old reference facts from today's CURRENT state. An active legacy granted absence without a T023 reference snapshot is reference-incomplete and fails closed.

## 5. CORRECTIONS, EXTENSIONS AND OVERLAPPING GRANTED ABSENCE

An Availability `availability_id` is one version chain. A later active version in the same chain must preserve already-bound reference month facts from the predecessor; changing dates must not rebind an already-captured month to a post-absence replacement schedule.

For a different active granted-absence chain overlapping the same Employee/Site/anchored date:
- existing compatible bound reference facts are reused for the overlapping date;
- if candidate bound facts disagree, the reference is `AMBIGUOUS`;
- CURRENT is not chosen arbitrarily to resolve disagreement.

This rule exists so a later `SICK_LEAVE` overlapping an already-bound `LEAVE_GRANTED` cannot lose the pre-leave nominal schedule after REPLAN.

## 6. DATE ANCHOR

Every reference work period belongs wholly to the calendar date on which that work period starts.

Binding owner example:
- `2027-03-01 17:00 -> 2027-03-02 05:00`, absence starts `2027-03-02`: 0h absence for that shift;
- the same shift, absence includes `2027-03-01`: full scheduled duration is absence on `2027-03-01`.

Do not split at midnight and do not emit partial U/C for the two dates.

A legal persisted 24h WorkPeriod follows the same start-date anchor: count its full 24h exactly once on the WorkPeriod start date, including cross-month/cross-year linkage.

Monthly, quarterly and Site projections use this same anchor. No second date-ownership rule is allowed.

## 7. SICK_LEAVE / LEAVE_GRANTED / LEAVE_PLAN

`SICK_LEAVE` and `LEAVE_GRANTED` consume the same reference-schedule accounting primitive.

When both cover the same anchored reference period:
- count the scheduled period once;
- classify the overlap as `SICK_LEAVE`;
- present C, not U+C.

`LEAVE_PLAN` creates no actual absence hours and does not adjust live TARGET until a granted absence exists.

## 8. REALIZED WORK CONFLICT

A REALIZED operational Assignment is historical worked truth.

A later or retroactive granted absence that overlaps actual REALIZED work:
- does not rewrite, cancel or replace the REALIZED Assignment;
- does not silently convert that worked period to U/C;
- raises a visible absence-vs-realized conflict for coordinator resolution;
- makes numerical absence accounting for the conflicting scope fail closed rather than guessing whether to count work, absence or both.

The actual worked fact remains WYK/realized truth in storage.

## 9. MULTI-SITE

Reference accounting is Employee-global and follows the Employee's adopted reference schedule across Sites.

Global accounting:
- sums bound reference periods across the reference Site scope once;
- never duplicates hours because the Employee has multiple memberships;
- fails closed if a required reference Site/date in the global scope is missing/ambiguous.

Site PDF projection:
- includes only bound reference periods whose `site_id` is the printed Site;
- if the printed Site was not part of the bound reference scope, that absence contributes 0h to that Site;
- multiple LOCAL memberships are not by themselves an ambiguity and must not duplicate global hours.

There is no per-Site accounting mode.

## 10. CANONICAL CONSUMERS

`rota/planning/absence.py` remains the one pure accounting owner. Its T018 flat-day primitive is replaced by a reference-period primitive.

The same canonical result feeds:
- WorkBalance and coordinator analytics;
- solver TARGET/fairness adjustment;
- T020 U/C export.

No consumer may recount weekdays, multiply days by 8, infer a reference from current Assignments after the fact, or maintain a parallel SICK/LEAVE precedence rule.

WorkBalance exposes canonical `absence_hours` for the month. `effective_target_hours = target_hours - absence_hours`. TARGET remains SOFT.

Both `SICK_LEAVE` and `LEAVE_GRANTED` reduce the live solver TARGET through this same `absence_hours`. HARD eligibility remains authoritative.

## 11. U/C PRESENTATION

U/C presentation follows the bound reference schedule period-by-period; it is not a monthly coin-change allocation.

For each bound reference period on the printed Site:
- PLAN position is the original anchored schedule position;
- WYK uses U for `LEAVE_GRANTED` or C for `SICK_LEAVE`;
- displayed U/C hours equal that one scheduled reference period exactly;
- no operational Assignment or ShiftDemand is fabricated.

T020's existing exact presentation-code rules remain fail-closed. T023 does not invent new D/N/U/C legend values.

Therefore a correct canonical 8h absence may still be unprintable under a Site's currently configured legend. In that case PDF generation returns the existing explicit presentation problem; it must not combine unrelated days, round the value or invent a new symbol.

For a legal 24h reference WorkPeriod, PLAN remains the existing 24h start-date presentation and WYK requires an existing legal equal-hour U/C presentation value.

## 12. CALENDAR DATA

`CalendarDay` remains canonical for rules that actually depend on holidays/calendar data.

It is no longer an absence-hour filter.

Missing CalendarDay data alone is not a reason to change a known bound reference period from 8/12/24h or to turn scheduled weekend/holiday work into 0h.

## 13. NON-GOALS

T023 does not add:
- payroll, wage or benefit calculations;
- leave entitlement/pool management;
- HR settlement;
- legal-advice logic;
- a SiteProfile absence strategy;
- nominal operational absence Assignments;
- duplicate Site-local absence ledgers;
- an event bus/workflow engine;
- historical WorkBalance rows;
- guessed legacy reference backfill;
- new D/N/U/C legend values.

## 14. REQUIRED REGRESSION GUARANTEES

The implementation must prove at least:
1. 8h reference -> 8h;
2. 12h D -> 12h and 12h N -> 12h;
3. legal 24h WorkPeriod -> 24h once on start date;
4. readable rest day -> 0h;
5. scheduled weekend/holiday -> scheduled hours;
6. both `17:00-05:00` owner examples;
7. missing/ambiguous reference -> fail closed;
8. PLAN -> absence bind -> replacement REPLAN -> finalize -> restart preserves reference;
9. restore/current pointer change preserves reference;
10. cross-month/year N/24h is anchored once;
11. SICK+LEAVE overlap -> one C;
12. LEAVE_PLAN -> no absence hours;
13. REALIZED overlap preserves work and surfaces conflict;
14. two Sites -> one global sum and Site-local projections without duplication;
15. solver TARGET, WorkBalance/analytics and PDF use equal canonical hours for equal reference facts;
16. absent Employee does not cover operational demand;
17. existing HARD availability/collision behavior stays intact;
18. all directly superseded flat-8/weekday/SICK-only/T020-conflict oracles are explicitly amended, not silently weakened.
