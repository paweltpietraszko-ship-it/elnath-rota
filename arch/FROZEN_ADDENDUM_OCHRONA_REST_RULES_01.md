# FROZEN ADDENDUM — OCHRONA REST RULES 01

STATUS: FROZEN ARCHITECT CONTRACT
TASK: ROTA-T023b
BASE_PRODUCT_SHA: `5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
ARCHITECT_INPUT_SHA: `4b046be4300480d39320159ae507b32b18f80910`
SUPERSEDES_DRAFT_HEAD: `b1e585979bb6f98d66920181705dcd7c075327fd`

This is the single consolidated T023b contract after the owner clarifications of 2026-08-23. It freezes only the protection-service rest rules required by this task. It must not be read as a general labour-law model or as a contract for cleaning or any other service.

## 1. SITE IDENTITY / PRODUCT BOUNDARY

`Site` is a planning/service unit, not a unique physical object.

The same real-world location may therefore be represented by several independent Sites, for example a protection Site and a cleaning Site. They have independent memberships, schedules, coordinator associations and HARD rules. The same coordinator may be associated with more than one of them; that does not merge their planning facts.

T023b concerns only the protection-service regime.

T023b adds exactly two automatic HARD protections for a protection Site:

1. at least 24h immediate rest after an actual 24h WorkPeriod;
2. at least 35h uninterrupted rest in each complete seven-day week of the calendar-month settlement period.

T023b does not add or infer:

- cleaning HARD rules;
- any disabled-person employment rule;
- Sunday-placement enforcement;
- automatic shortening of weekly rest to 24h;
- night-work-window rules;
- monthly/average weekly work-time limits;
- payroll, wage, leave-entitlement or HR rules;
- external time tracking;
- work performed outside the target Site's recorded Rota;
- a new training rule;
- a new exception workflow;
- a physical-object/address aggregate entity.

## 2. CONTROLLING OWNER DECISIONS

The following owner rulings control this addendum:

- O1: automatic weekly rest is always at least 35h; T023b does not infer the statutory 24h shortening;
- O2: Sunday placement is outside T023b;
- O3: the settlement period is the calendar month;
- O4: only complete seven-day weeks wholly contained in that month are WEEKLY-REST-01 windows; the remaining 0-3 days are tail days outside that weekly rule;
- O5: T023b uses only work facts actually recorded for the target Site; it does not aggregate `other_site_assignments` and does not infer unobserved work;
- O6: TRAINEE is not a new T023b case. Frozen T012 semantics remain: non-CANCELLED TRAINEE is work for REST/LOAD and may interrupt weekly rest;
- O7: `Site` is a planning/service unit, not a unique physical object; a protection Site and a cleaning Site at one real-world location are separate Sites;
- O8: the Site planning/service regime is selected at creation and is normally immutable. Ordinary Site editing cannot change it. Correction of an erroneous initial classification is a separate exceptional product operation and is not implemented by T023b;
- O9: all currently persisted Sites are test data. Migration therefore needs no real-world reclassification workflow.

Legal references used only for the selected rules:

- Kodeks pracy art. 128 §3 pkt 2 — seven consecutive calendar days from the first day of the settlement period;
- art. 130 §1 — full weeks are distinguished from days remaining to the end of the period;
- art. 133 §1 — at least 35h uninterrupted weekly rest;
- art. 136 §2 applied through art. 137 — immediate rest after extended work at least equal to hours worked;
- art. 137 — equivalent-time protection work may reach 24h, with settlement period not exceeding one month.

## 3. EXPLICIT SITE PLANNING REGIME

The earlier boolean proposal `Site.ochrona_mode: bool` is retracted.

Reason: `False` cannot truthfully mean `ORDINARY` once the product can contain other service regimes such as cleaning. T023b must not encode a false binary product model.

Add an explicit enum/value object:

`SitePlanningRegime`

Supported by T023b:

- `ORDINARY`
- `OCHRONA`

Add to `Site`:

`planning_regime: SitePlanningRegime`

`SPRZATANIE` is intentionally **not** added by T023b. Its HARD semantics belong to a separate future task, which may extend the enum/schema deliberately.

Semantics:

- `ORDINARY` preserves pre-T023b behaviour;
- `OCHRONA` enables the two T023b protections for that Site;
- `planning_regime` is owned by Site, not SiteProfile and not SitePrintSettings;
- two Sites may share one SiteProfile and still have different planning regimes;
- no T023b rule reads another Site's regime.

## 4. PERSISTENCE / CREATION / IMMUTABILITY

Schema v8 -> v9 adds one Site column:

`planning_regime TEXT NOT NULL DEFAULT 'ORDINARY' CHECK (planning_regime IN ('ORDINARY','OCHRONA'))`

The default exists **only** for migration of the repository's existing test/legacy rows. It is not a product default for creating a real Site.

Required persistence behaviour:

- existing rows migrate to `ORDINARY` because they are test data;
- no `UNCLASSIFIED` state;
- no heuristic inference from SiteProfile, display name, shift pattern, employees or coordinator;
- `site_repository` round-trips the enum and rejects unsupported persisted values;
- new Site creation through the application bootstrap must provide an explicit `planning_regime` value;
- tests/fixtures that construct Site directly must set `ORDINARY` unless the test intentionally exercises `OCHRONA`.

Creation audit:

- `bootstrap_or_resume_coordinator_context()` persists the selected regime with the Site;
- regime is included in `_planning_fields(Site)` and `_site_state(Site)` so the existing `CONTEXT_CONFIGURATION_SAVED` action records it as planning-relevant configuration.

Immutability:

- `update_site()` may continue its current name/active semantics but must reject a changed `planning_regime`;
- T023b adds no `set_site_regime`, `set_site_ochrona_mode` or equivalent normal edit command;
- T023b adds no regime-transition lifecycle semantics;
- correction of a mistaken initial regime is explicitly outside T023b and requires its own product contract before implementation.

This removes any need for T023b to define retroactive `ORDINARY -> OCHRONA` behaviour for already-persisted ScheduleVersions: there is no normal regime-change operation in this task.

UI visual design and the exact confirmation presentation are outside T023b. The backend contract is that creation receives an explicit regime and normal edit cannot change it.

## 5. ONE CANONICAL REST OWNER

`rota/planning/work_periods.py` remains the single pure, persistence-free owner of WorkPeriod/rest semantics shared by solver and independent validator.

T023b may add pure helpers only for:

1. effective required rest after one resolved WorkPeriod under a supplied planning regime;
2. complete seven-day week windows for one calendar month;
3. maximum uninterrupted free interval inside one supplied week.

Do not create a second legal-rest module, persistence calculation or application-local copy of these semantics.

## 6. IMMEDIATE REST AFTER AN ACTUAL 24H WORK PERIOD

Existing validator code `REST-01` remains the rule code. T023b does not add a second immediate-rest violation code.

For a resolved target-Site WorkPeriod `P`:

- `configured_rest(P)` = existing resolved `required_rest_after_hours`;
- `duration(P) = P.end - P.start`;
- if `state.site.planning_regime == ORDINARY`, effective rest remains `configured_rest(P)`;
- if `state.site.planning_regime == OCHRONA` and `duration(P) == 24h`, `effective_rest(P) = max(configured_rest(P), 24h)`;
- otherwise effective rest remains `configured_rest(P)`.

The rule remains directional:

`next.start - P.end >= effective_rest(P)`.

The 24h floor is based on the resolved actual WorkPeriod span, not a label. It therefore covers existing T012 mechanisms:

- Catalog H24;
- same-month emergency H12+H12 when selected as one WorkPeriod;
- existing cross-month emergency H12+H12 work-period provenance.

Persisted configured/snapshotted rest provenance is not rewritten to 24h.

### Month boundary

Immediate rest after a concrete 24h duty may cross a month boundary.

If a target-Site 24h duty ends on the final day of month M, its required immediate rest still applies against the next recorded target-Site work period in M+1. Existing same-Site boundary context is reused.

Do not apply the new T023b floor to `state.other_site_assignments`. Existing pre-T023b T012/T022 cross-Site REST behaviour is preserved unchanged.

## 7. WEEKLY-REST-01

Add one built-in HARD code:

`WEEKLY-REST-01`.

It is active only for `state.site.planning_regime == OCHRONA`.

### 7.1 Full week windows

For settlement month M:

1. `month_start` = day 1 at 00:00;
2. `month_end` = day 1 of the next month at 00:00;
3. create `[month_start + 7*n days, month_start + 7*(n+1) days)` only while the whole interval ends `<= month_end`;
4. create no partial final week and no cross-month weekly window.

For a 31-day month:

- days 1-7;
- days 8-14;
- days 15-21;
- days 22-28;
- days 29-31 are tail days and create no WEEKLY-REST-01 window;
- day 1 of the next month starts the first week of the new settlement period.

Weekly windows never overlap settlement months.

### 7.2 Occupied work

For one employee and one full week, occupied time consists only of non-CANCELLED target-Site Assignments actually represented in the considered Rota:

- final/candidate target Assignments;
- same-Site boundary Assignments only to the extent they overlap the week;
- fixed target-Site TRAINEE as ordinary recorded work under frozen T012 semantics.

Do not include `state.other_site_assignments` and do not infer external work.

PRIMARY and TRAINEE both occupy time. No additional training branch, exception or eligibility logic is authorized.

Clip occupied intervals to the half-open week, merge overlapping/abutting occupied intervals, and measure free gaps including week boundaries.

PASS iff maximum uninterrupted free interval `>= 35h`.

FAIL iff `< 35h`.

Use exact elapsed time. LOAD-01 is separate and cannot establish WEEKLY-REST-01 compliance.

Tail days create no weekly-rest window, although work in those days may still matter to REST-01/immediate rest.

## 8. SOLVER / INDEPENDENT VALIDATOR

Automatic planning under `ORDINARY` must preserve pre-T023b behaviour.

Under `OCHRONA`:

- solver prevents target-Site candidates violating the effective 24h REST-01 floor;
- solver enforces at least one 35h work-free interval in each complete weekly window for each employee with target-Site work in that window;
- fixed target-Site work, including TRAINEE, is occupied time;
- prospective solver work uses existing PRIMARY slot variables;
- `state.other_site_assignments` do not participate in either new T023b protection;
- independent validator re-derives the same two rules from final Assignment facts and never trusts solver witness literals;
- no new PlanningResult status is introduced.

For weekly CP-SAT encoding, implementation may enumerate candidate 35h rest-window starts at week start and at end times of fixed/prospective target-Site intervals, then require at least one candidate window not overlapped by fixed or selected work. Equivalent encoding is allowed if it is provably equivalent to the pure oracle.

## 9. MANUAL CORRECTION / AUDIT

`apply_manual_correction()` remains the explicit manual schedule-correction path.

- `REST-01` remains `DeviationCategory.LAW`;
- add `WEEKLY-REST-01 -> DeviationCategory.LAW`;
- automatic planning does not use an override path;
- a manual correction may persist those HARD deviations only through the existing atomic REST override precedent.

Generalize current rest-override fact reconstruction without parsing `ViolationDetail.message` so one logical correction creates at most one existing-style `REST_OVERRIDE_RECORD` containing all REST-01/WEEKLY-REST-01 facts for that child ScheduleVersion.

Minimum WEEKLY facts:

- employee id;
- full-week start/end;
- observed maximum uninterrupted rest;
- required rest = 35h;
- target-Site Assignment identities overlapping the week.

For an OCHRONA 24h REST-01 exception, the record exposes actual gap, configured/resolved rest and effective required rest.

Do not add `coordinator_action_id`, a second coordinator action, a new override table or another audit store solely for T023b. Preserve the existing transaction structure and caller-specific action semantics.

## 10. PRESERVED CONTRACTS

T023b preserves without reinterpretation:

- T012 WorkPeriod identity, configured-rest provenance, emergency 24h mechanics and TRAINEE-as-work semantics;
- existing T012/T022 cross-Site REST behaviour;
- LOAD-01 rolling-7d threshold and its current meaning;
- T019b one material command -> one coordinator action;
- current ScheduleVersion lifecycle semantics;
- T023/T026 absence accounting;
- SitePrintSettings/base_regime;
- SiteProfile planning semantics unrelated to the new Site regime field.

T023b does not modify `arch/spec.md` or `arch/FROZEN.lock`.

## 11. MINIMUM REQUIRED ORACLES

Implementation must prove at minimum:

1. v8 test/legacy Site rows migrate to `planning_regime=ORDINARY`;
2. new persisted Site requires an explicit supported regime;
3. two Sites sharing a SiteProfile may have different regimes;
4. `update_site()` rejects regime change;
5. no normal regime-change command exists;
6. ORDINARY preserves pre-T023b rest behaviour;
7. Catalog H24 gaps 23h59 / 24h / 24h01 => fail / pass / pass under OCHRONA;
8. same-month emergency H12+H12 has the same 24h floor;
9. cross-month emergency/24h duty still enforces immediate rest against the next recorded target-Site duty in the next month;
10. configured rest 0/11/23 cannot lower the OCHRONA 24h floor;
11. 31-day month => exactly weeks 1-7, 8-14, 15-21, 22-28; 29-31 are tail days;
12. 30-day month => four full weeks + two tail days; 28-day month => four full weeks; leap February => four full weeks + one tail day;
13. no weekly window crosses a month boundary;
14. weekly maximum rest 34h59 / 35h / 35h01 => fail / pass / pass;
15. non-CANCELLED TRAINEE can interrupt weekly rest without any training-specific rule;
16. work only in tail days creates no WEEKLY-REST-01 solely because of those tail days;
17. `state.other_site_assignments` do not enter either new T023b protection;
18. solver and independent validator agree on the same target-Site facts;
19. manual correction reuses one atomic REST override record with reconstructable facts;
20. no Sunday-placement rule, automatic 24h weekly exception, cleaning rule or external-time surrogate is introduced.

No additional product scenarios are authorized by this addendum.