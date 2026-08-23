# FROZEN ADDENDUM — OCHRONA REST RULES 01

STATUS: FROZEN ARCHITECT CONTRACT
TASK: ROTA-T023b
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
OWNER_FOLLOW_UP: `tasks/ROTA-T023b/OWNER_FRONTEND_DECISION_2026-08-23.md`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

This addendum freezes only product semantics. Implementation ownership, file scope and test gates are in `tasks/ROTA-T023b/brief.md`.

## 1. PRODUCT BOUNDARY

T023b adds exactly two automatic HARD protections for a protection-service Site:

1. after an actual 24-hour WorkPeriod, immediate rest is at least 24 hours;
2. in every complete seven-day week of the calendar-month settlement period, uninterrupted rest is at least 35 hours.

T023b does not claim general Polish-labour-law compliance and does not add rules for cleaning, night work, Sunday placement, payroll/HR, average weekly/monthly work time or any other work-time regime.

## 2. SITE IS A PLANNING/SERVICE UNIT

`Site` is a planning/service unit, not a unique physical object.

One real location may therefore have separate Sites for protection, cleaning or another service. Those Sites have independent schedules, memberships and HARD semantics even when managed by the same coordinator.

T023b concerns protection only. Cleaning has separate future HARD rules and must not be represented as `ORDINARY` merely because T023b does not implement cleaning yet.

## 3. SITE PLANNING REGIME

The Site has an explicit planning/service regime:

`SitePlanningRegime = ORDINARY | OCHRONA`

with required Site field:

`planning_regime: SitePlanningRegime`

This is an enum, not a boolean.

Semantics:

- `ORDINARY` preserves pre-T023b behaviour;
- `OCHRONA` enables the two T023b protections;
- regime belongs to Site, not SiteProfile and not print settings;
- a new real Site receives its regime explicitly from its creation flow; omission must never silently become `ORDINARY`;
- ordinary Site editing cannot change the regime;
- a mistaken initial classification may be corrected only by a separate deliberate and audited correction operation.

Currently persisted Sites are test data only. Migration may assign those legacy/test rows `ORDINARY`; this is migration compatibility only, not a creation default.

### Creation and frontend contract

T021 must expose separate, unambiguous creation entry points/screens for at least OCHRONA and ORDINARY. There is no generic creation checkbox/toggle/dropdown that silently chooses the legal regime.

Separate user flows must share common Site form/application/persistence implementation. The selected flow supplies the regime. The Site workspace shows the classification, while ordinary editing exposes no regime-change control.

### Correction semantics

Regime correction is prospective for planning and must not rewrite historical ScheduleVersions or REALIZED Assignments.

After correction:

- persisted ScheduleVersions and Assignment facts remain byte-for-byte historical facts unless changed later through their existing lifecycle operations;
- every fresh PLAN/REPLAN/candidate validation/manual correction/finalize uses the corrected current Site regime;
- an existing current plan is not silently rewritten into a corrected-regime plan;
- if the current plan contains not-yet-realized work, the correction UX must visibly route the coordinator to the existing REPLAN flow before presenting that plan as a plan under the corrected regime.

No new stale-schedule state, regime snapshot on ScheduleVersion or retroactive rewrite is introduced by T023b.

## 4. WORK FACTS USED BY T023b

T023b validates only work actually recorded for the target Site in the considered Rota.

It must not aggregate T023b time from another Site or infer work that Rota does not store.

Existing pre-T023b T012/T022 cross-Site REST behaviour remains unchanged; T023b adds no new cross-Site semantics.

A non-CANCELLED `TRAINEE` Assignment remains work exactly under frozen T012 REST/LOAD semantics and may interrupt weekly rest. T023b adds no training-specific branch.

## 5. IMMEDIATE REST AFTER 24H

Existing `REST-01` remains the immediate-rest rule code.

For a resolved target-Site WorkPeriod `P`:

- `configured_rest(P)` is the already-resolved persisted/configured rest provenance;
- if Site regime is `OCHRONA` and `P` lasts exactly 24 hours, `effective_rest(P) = max(configured_rest(P), 24h)`;
- otherwise `effective_rest(P) = configured_rest(P)`.

The rule is based on the resolved actual WorkPeriod span and covers both existing T012 24h mechanisms: Catalog H24 and emergency H12+H12, including the existing cross-month pair representation.

Persisted rest provenance is not rewritten. Immediate rest after a concrete 24h duty may cross a month boundary.

## 6. WEEKLY REST

New HARD code: `WEEKLY-REST-01`.

It applies only for target Site regime `OCHRONA`.

The settlement period is the calendar month. Weekly windows are only complete seven-day blocks beginning at day 1:

`[month_start + 7*n days, month_start + 7*(n+1) days)`

A window exists only when its end is still inside the same month. For a 31-day month this gives days 1-7, 8-14, 15-21 and 22-28; days 29-31 create no weekly window. No weekly window crosses into the next month.

For one employee and one weekly window:

- count non-CANCELLED target-Site work only;
- PRIMARY and TRAINEE both occupy time;
- clip work to the week, merge overlapping/abutting occupied intervals and measure the largest free gap including both boundaries.

PASS iff maximum uninterrupted rest is at least 35 hours.

LOAD-01 is separate and cannot substitute for this rule. T023b adds neither automatic shortening of the 35h floor to 24h nor Sunday-placement enforcement.

## 7. AUTOMATIC VS MANUAL PATH

Automatic planning must never return/persist a candidate violating either T023b HARD rule. Independent validation derives the same result from final Assignment facts rather than trusting solver internals.

An explicit manual schedule correction may persist such a HARD violation only through the existing audited REST-override precedent. T023b reuses that mechanism and the same canonical rest/week arithmetic; it creates no second exception workflow, audit store or planning result status.

## 8. LEGAL / OWNER BASIS

Relevant basis for the selected product scope:

- Kodeks pracy art. 128 §3 pkt 2 — week definition;
- art. 130 §1 — full weeks and remaining days in the settlement period;
- art. 133 §1 — at least 35h uninterrupted weekly rest;
- art. 136 §2 applied through art. 137 — immediate rest after extended work.

Official text: `https://eli.gov.pl/api/acts/DU/2025/277/text/U/D20250277Lj.pdf`

PIP monthly-period example: `https://www.pip.gov.pl/dla-pracodawcow/pytania-i-odpowiedzi/jaki-wplyw-maja-swieta-przypadajace-w-maju-na-wymiar-czasu-pracy`

No other product semantics are authorized by this addendum.
