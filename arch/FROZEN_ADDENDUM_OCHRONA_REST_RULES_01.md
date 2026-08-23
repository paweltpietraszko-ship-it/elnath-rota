# FROZEN ADDENDUM — OCHRONA REST RULES 01

STATUS: FROZEN ARCHITECT CONTRACT
TASK: ROTA-T023b
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

This addendum freezes only the product semantics needed for ROTA-T023b. Implementation ownership, file scope and test gates are in `tasks/ROTA-T023b/brief.md`.

## 1. PRODUCT BOUNDARY

T023b adds exactly two automatic HARD protections for a protection-service Site:

1. after an actual 24-hour WorkPeriod, immediate rest is at least 24 hours;
2. in every complete seven-day week of the calendar-month settlement period, uninterrupted rest is at least 35 hours.

T023b does not claim general Polish-labour-law compliance and does not add rules for cleaning, night work, Sunday placement, payroll/HR, average weekly/monthly work time or any other work-time regime.

## 2. SITE MEANS A PLANNING/SERVICE UNIT

`Site` is a planning/service unit, not a unique physical object.

The same real-world location may therefore have separate Sites, for example protection and cleaning. Those Sites have independent schedules, memberships and HARD semantics even when managed by the same coordinator.

T023b concerns only protection. Cleaning has its own future HARD rules and is not modeled by this task.

## 3. SITE PLANNING REGIME

The Site has an explicit planning/service regime:

`SitePlanningRegime = ORDINARY | OCHRONA`

with required Site field:

`planning_regime: SitePlanningRegime`

This is an enum rather than a boolean because `not OCHRONA` is not a durable synonym for `ORDINARY` once other service regimes exist.

Semantics:

- `ORDINARY` preserves pre-T023b behaviour;
- `OCHRONA` enables the two T023b protections;
- regime belongs to Site, not SiteProfile and not print settings;
- regime is selected explicitly when the Site is created;
- ordinary Site editing cannot change it;
- correcting an erroneous initial classification is a separate exceptional product operation outside T023b.

Currently persisted Sites are test data only. Migration may assign those legacy/test rows `ORDINARY`; this is compatibility, not a product default for new real Sites.

## 4. WORK FACTS USED BY T023b

T023b validates only work actually recorded for the target Site in the considered Rota.

It must not:

- aggregate T023b time from another Site;
- infer another employer/site schedule;
- invent external work that Rota does not store.

Existing pre-T023b T012/T022 cross-Site REST behaviour remains unchanged; T023b adds no new cross-Site semantics.

A non-CANCELLED `TRAINEE` Assignment remains work exactly under frozen T012 REST/LOAD semantics. It may therefore interrupt weekly rest. T023b adds no training-specific branch or rule.

## 5. IMMEDIATE REST AFTER 24H

Existing `REST-01` remains the immediate-rest rule code.

For a resolved target-Site WorkPeriod `P`:

- `configured_rest(P)` is the already-resolved persisted/configured rest provenance;
- if the Site regime is `OCHRONA` and `P` lasts exactly 24 hours, `effective_rest(P) = max(configured_rest(P), 24h)`;
- otherwise `effective_rest(P) = configured_rest(P)`.

The rule is based on the resolved actual WorkPeriod span, not merely a catalog label. It therefore covers both existing T012 24h mechanisms:

- Catalog H24;
- emergency H12+H12, including the existing cross-month pair representation.

Persisted rest provenance is not rewritten to 24h.

Immediate rest after a concrete 24h duty may cross a month boundary. The month boundary does not cancel the rest owed after that duty.

## 6. WEEKLY REST

New HARD code: `WEEKLY-REST-01`.

It applies only when the target Site regime is `OCHRONA`.

The settlement period is the calendar month. Weekly windows are only complete seven-day blocks beginning at day 1 of that month:

`[month_start + 7*n days, month_start + 7*(n+1) days)`

and a window exists only if its end is still inside the same settlement month.

Therefore, for a 31-day month the weekly windows are days 1-7, 8-14, 15-21 and 22-28. Days 29-31 are remaining days outside `WEEKLY-REST-01`. No weekly window crosses into the next month; day 1 of the next month begins that month's own sequence.

For one employee and one weekly window:

- count non-CANCELLED target-Site work only;
- PRIMARY and TRAINEE both occupy time;
- clip occupied intervals to the weekly window;
- merge overlapping/abutting occupied intervals;
- measure the maximum uninterrupted free interval, including gaps at both week boundaries.

PASS iff maximum uninterrupted rest is at least 35 hours.

The comparison uses exact elapsed time. LOAD-01 is a separate rolling-hours rule and cannot substitute for this check.

Owner decisions retained:

- no automatic shortening of the 35h floor to 24h;
- no Sunday-placement rule in T023b.

## 7. AUTOMATIC VS MANUAL PATH

Automatic planning must never return/persist a candidate violating either T023b HARD rule. Independent validation must derive the same result from final Assignment facts rather than trusting solver internals.

An explicit manual schedule correction may persist such a HARD violation only through the existing audited REST-override precedent. T023b reuses that mechanism; it does not create another exception workflow, audit store or planning result status.

The manual audit record must remain fact-derived and sufficient to identify the violated rest requirement. It must reuse the same canonical rest/week arithmetic used by planning rather than creating a second semantic calculation.

## 8. LEGAL / OWNER BASIS

The product settlement period for this task is the calendar month.

Relevant verified sources:

- Kodeks pracy art. 128 §3 pkt 2 — week definition;
- art. 130 §1 — full weeks and days remaining in the settlement period;
- art. 133 §1 — at least 35h uninterrupted weekly rest;
- art. 136 §2 applied through art. 137 — immediate rest after extended work.

Official text: `https://eli.gov.pl/api/acts/DU/2025/277/text/U/D20250277Lj.pdf`

PIP monthly-period example: `https://www.pip.gov.pl/dla-pracodawcow/pytania-i-odpowiedzi/jaki-wplyw-maja-swieta-przypadajace-w-maju-na-wymiar-czasu-pracy`

No other product semantics are authorized by this addendum.
