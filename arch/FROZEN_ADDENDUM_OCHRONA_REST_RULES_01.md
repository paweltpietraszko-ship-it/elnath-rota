# FROZEN ADDENDUM — OCHRONA REST RULES 01

STATUS: FROZEN ARCHITECT CONTRACT
TASK: ROTA-T023b
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

This is the consolidated T023b contract after owner clarification on 2026-08-23. It freezes exactly two additional automatic rest protections for a Site explicitly operating in ochrona mode. It does not claim general Polish-labour-law compliance and it does not invent work facts that Rota does not store.

## 1. PRODUCT BOUNDARY

T023b adds exactly:

1. in ochrona mode, a minimum 24h immediate rest after an actual 24h WorkPeriod;
2. in ochrona mode, at least 35h uninterrupted rest in each **full seven-day week** of the calendar-month settlement period;
3. identical HARD enforcement in automatic planning and independent validation;
4. the existing explicit audited manual-correction override precedent for those violations;
5. ordinary-mode compatibility.

T023b does not add:

- Sunday-placement enforcement under art. 133 §3-4;
- automatic shortening of the weekly floor to 24h under art. 133 §2;
- night-work-window rules;
- monthly/average weekly work-time limits;
- payroll, wage, leave-entitlement or HR rules;
- external time tracking or inference about work not stored in the considered Rota;
- aggregation of T023b work time from other Sites/objects;
- a new training rule;
- a new exception workflow;
- reuse of `SitePrintSettings.base_regime` as the ochrona/ordinary switch.

## 2. CONTROLLING LEGAL / OWNER DECISIONS

The product settlement period for T023b is the calendar month.

Verified statutory basis:

- Kodeks pracy art. 128 §3 pkt 2 defines a week as seven consecutive calendar days beginning on the first day of the settlement period;
- art. 130 §1 separately distinguishes the number of weeks in the settlement period from days remaining to its end;
- art. 133 §1 requires at least 35h uninterrupted rest in each week;
- art. 136 §2, applied through art. 137, requires immediate rest after extended work at least equal to the hours worked;
- art. 137 permits the selected ochrona equivalent-time system up to 24h with a settlement period not exceeding one month.

Official sources used for the contract:

- ELI current Kodeks pracy text: `https://eli.gov.pl/api/acts/DU/2025/277/text/U/D20250277Lj.pdf`;
- PIP monthly-period example: `https://www.pip.gov.pl/dla-pracodawcow/pytania-i-odpowiedzi/jaki-wplyw-maja-swieta-przypadajace-w-maju-na-wymiar-czasu-pracy`.

Owner decisions already binding:

- O1: automatic weekly floor is always 35h; T023b does not infer the statutory 24h shortening;
- O2: Sunday placement is outside T023b;
- O3: settlement period is the calendar month;
- O4: only complete seven-day weeks wholly contained in that month are WEEKLY-REST-01 windows; remaining 0-3 calendar days are tail days outside that weekly rule;
- O5: T023b validates only work facts actually recorded for the target Site in the considered Rota; it does not aggregate other-Site schedules or infer external work;
- O6: TRAINEE is not a T023b special case. Frozen T012 semantics remain: a non-CANCELLED TRAINEE Assignment is work for REST/LOAD and therefore can interrupt weekly rest.

## 3. PER-SITE MODE

The switch is current state owned by `Site`, not `SiteProfile` and not print settings.

Canonical field:

`Site.ochrona_mode: bool = False`

Semantics:

- `False` = ordinary mode; T023b adds no new restriction;
- `True` = ochrona mode; the two protections in this addendum apply to that Site;
- Sites sharing one SiteProfile may have different values;
- no T023b rule reads another Site's mode.

Persistence:

- schema v8 -> v9 adds `sites.ochrona_mode INTEGER NOT NULL DEFAULT 0 CHECK (ochrona_mode IN (0,1))`;
- existing Sites therefore migrate to ordinary mode;
- no backfill heuristic and no new table;
- `Site` appends the Python field with default `False`;
- `site_repository` reads/writes it as bool.

Write boundary:

- bootstrap/create may persist the field through the existing Site write and `CONTEXT_CONFIGURATION_SAVED` action;
- later edits use one named application command `set_site_ochrona_mode(...)` under the existing active coordinator context;
- one successful material edit creates exactly one existing `CONTEXT_CONFIGURATION_SAVED` coordinator action and invalidates current decision-required pointers for that Site in the same transaction;
- no new CoordinatorActionKind and no ScheduleVersion are created by changing the mode.

## 4. CANONICAL REST OWNER

`rota/planning/work_periods.py` remains the pure persistence-free owner of WorkPeriod/rest semantics shared by solver, independent validator and manual-override fact reconstruction.

T023b may extend it with pure helpers for:

- effective required rest after one WorkPeriod;
- full settlement-month week windows;
- maximum uninterrupted free interval inside one supplied week.

Do not create a second planning/legal-rest module or persistence-owned calculation.

## 5. 24H IMMEDIATE REST — NARROW REST-01 EXTENSION

Existing `REST-01` remains the rule code.

For a resolved WorkPeriod `P` on the target Site:

- `configured_rest(P)` = existing resolved `required_rest_after_hours`;
- `duration(P) = P.end - P.start`;
- ordinary mode: effective rest remains `configured_rest(P)`;
- ochrona mode + exact 24h duration: `effective_rest(P) = max(configured_rest(P), 24h)`;
- any other duration: effective rest remains `configured_rest(P)`.

The floor is based on the resolved actual WorkPeriod span, not on trusting only a catalog label or one rest field. It therefore covers both existing 24h mechanisms:

- Catalog H24;
- emergency H12+H12, including the existing cross-month emergency pair representation.

The 24h floor is a **target-Site T023b rule**. It must not be applied to `state.other_site_assignments` or used to create any new cross-Site T023b semantics. Existing pre-T023b T012/T022 cross-Site REST behaviour remains unchanged.

Persisted configured/snapshotted rest provenance is not rewritten to 24h. The legal floor is evaluated dynamically.

### Cross-month boundary

Unlike WEEKLY-REST-01, immediate rest after a concrete 24h duty does not stop at month end.

Example: if a target-Site 24h duty ends on 31 March, its required immediate rest may extend into April. Existing same-Site boundary context is used to compare that duty with the next recorded target-Site work period. No external or other-Site work is inferred.

## 6. WEEKLY-REST-01

New built-in HARD code: `WEEKLY-REST-01`.

It is active only for target Site `ochrona_mode=True`.

### 6.1 Full-week windows only

For settlement month `M`:

1. `month_start` = day 1 at 00:00;
2. `month_end` = day 1 of the next month at 00:00;
3. create `[month_start + 7*n days, month_start + 7*(n+1) days)` only while the whole interval ends `<= month_end`;
4. do not create a partial or cross-month final week.

Human-date example for a 31-day month:

- days 1-7;
- days 8-14;
- days 15-21;
- days 22-28;
- days 29-31 are tail days and create no WEEKLY-REST-01 window;
- day 1 of the next month begins week 1 of the new settlement period.

There is no week 29 March -> April. Weekly windows never overlap across settlement months.

### 6.2 Work facts inside a week

For one employee and one full week:

- use only non-CANCELLED Assignments actually recorded for the target Site in the considered Rota;
- current target Assignments and same-Site boundary Assignments may contribute only to the extent their interval overlaps the week;
- do not include `state.other_site_assignments`;
- do not invent work performed outside Rota;
- PRIMARY and TRAINEE both count as occupied time because T012 already freezes TRAINEE as work for REST/LOAD;
- there is no additional training-specific branch or rule.

Clip occupied intervals to the half-open week, merge overlapping/abutting occupied intervals, then measure free gaps including the week boundaries.

PASS iff the maximum uninterrupted free interval is `>= 35h`.

FAIL iff it is `< 35h`.

The comparison is exact elapsed time. LOAD-01 is unrelated and cannot prove WEEKLY-REST-01 compliance.

Tail days outside full weeks do not create a weekly-rest requirement. Work in tail days may still be relevant to ordinary REST-01 or the 24h immediate-rest rule.

## 7. SOLVER / VALIDATOR PARITY

Automatic planning in ordinary mode preserves pre-T023b semantics.

In ochrona mode:

- solver must prevent a selected target-Site candidate that violates the 24h effective REST-01 floor;
- solver must enforce existence of at least one 35h work-free interval in each full weekly window for every employee whose target-Site work is modeled in that week;
- fixed target-Site work, including TRAINEE, participates as occupied time;
- prospective solver slots are the existing PRIMARY candidate work;
- no `other_site_assignments` participate in either new T023b protection;
- independent validator re-derives both rules from final Assignment facts and does not trust solver literals;
- no new PlanningResult status is introduced.

For CP-SAT, a minimal complete encoding of weekly rest may enumerate possible 35h rest-window starts at the week start and at ends of fixed/prospective target-Site intervals, then require at least one candidate window not overlapped by fixed or selected work. An equivalent simpler encoding is allowed if it has the same exact oracle.

## 8. MANUAL CORRECTION / AUDIT

`apply_manual_correction()` remains the only supported explicit override path.

- `REST-01` remains `DeviationCategory.LAW`;
- add `WEEKLY-REST-01 -> DeviationCategory.LAW`;
- automatic planning never invokes the override path;
- a manual correction may persist the HARD deviation only with the existing atomic `REST_OVERRIDE_RECORD` precedent.

Generalize the existing rest-override reconstruction, without parsing validator message text, so one logical manual correction creates at most one `REST_OVERRIDE_RECORD` containing all REST-01/WEEKLY-REST-01 facts for that child ScheduleVersion.

Minimum additional WEEKLY fact shape:

- employee id;
- full-week start/end;
- observed maximum uninterrupted rest;
- required rest = 35h;
- target-Site Assignment identities overlapping the week.

For a REST-01 override after an exact 24h period, the record must expose actual gap, configured/resolved rest and effective required rest so the applied 24h floor is reconstructable.

Keep the existing transaction structure: child ScheduleVersion, deviations, REST override DecisionRecord and the one existing coordinator action commit or roll back together. Do not introduce a second audit store or a second coordinator action for the derived override record.

## 9. PRESERVED CONTRACTS

T023b preserves without reinterpretation:

- T012 WorkPeriod identity, configured-rest provenance, emergency 24h mechanics and TRAINEE-as-work semantics;
- existing T012/T022 cross-Site REST behaviour; T023b does not expand it;
- LOAD-01 rolling-7d threshold and its current meaning;
- T019b one material command -> one coordinator-action rule;
- T023/T026 absence accounting;
- SitePrintSettings/base_regime;
- ordinary-mode results after migration.

T023b does not modify `arch/spec.md` or `arch/FROZEN.lock`.

## 10. REQUIRED ORACLES

The implementation tests must prove at minimum:

1. existing Site migration defaults `ochrona_mode=False`;
2. two Sites sharing one SiteProfile can hold different mode values;
3. ordinary mode preserves pre-T023b rest behaviour;
4. Catalog H24: 23h59 fails, 24h passes, 24h01 passes under the ochrona floor;
5. same-month emergency H12+H12 has the same floor;
6. cross-month emergency pair and a next target-Site duty enforce the same immediate floor across month end;
7. configured rest 0/11/23 cannot lower the ochrona 24h floor;
8. a 31-day month produces only weeks 1-7, 8-14, 15-21, 22-28; days 29-31 create no weekly window;
9. a 30-day month has two tail days; a 28-day month has none; leap-February has one;
10. 34h59 weekly rest fails, 35h passes, 35h01 passes;
11. a non-CANCELLED TRAINEE interval can interrupt the 35h rest exactly like other recorded work; no training-specific logic is added;
12. work only in tail days does not create WEEKLY-REST-01;
13. T023b weekly calculation ignores `state.other_site_assignments` and does not infer external work;
14. solver and independent validator agree on the same target-Site facts;
15. automatic violating candidate is rejected; equivalent explicit manual correction persists only with deviation + one atomic auditable REST override record;
16. no Sunday-placement rule and no automatic 24h weekly exception are introduced;
17. LOAD-01 regression semantics remain unchanged.

No other product scenarios are authorized by this addendum.
