# ROTA-T023b — ARCHITECT INPUT: OCHRONA REST-RULE ENFORCEMENT

DATE: 2026-08-23
BASE: `main@5e8f282c8208441b25f0f0a3e0f44016c7162a6a`
STATUS: INPUT FOR AN ARCHITECT SESSION — NOT AN IMPLEMENTATION CONTRACT

This document supplies verified code facts, official legal sources and the
owner rulings already made. It does not choose field placement, algorithms or
new product semantics. The architect owns the contract/addendum. CC may read
the result only as an implementation-feasibility review; CC does not resolve
the owner questions below, write the architecture contract or implement code
before independent Codex preimplementation PASS.

## 1. Required architect deliverables

Produce, without implementation:

1. a frozen addendum for the two rest protections in Section 7;
2. `tasks/ROTA-T023b/brief.md` with exact scope, named invariants, gates and
   adversarial test matrix;
3. a schema/migration and application-impact list, including the Site-mode
   input, existing-Site compatibility and all planning/validation/manual-edit
   call sites;
4. an explicit temporal data-window contract for cross-Site and
   cross-boundary validation;
5. an impact list for existing frozen/regression oracles requiring deliberate
   supersession;
6. a checkpoint order if this cannot be safely reviewed as one implementation
   unit.

The architect must end with exactly one status:

- `READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS`, or
- `OWNER DECISION REQUIRED`, naming only product questions not resolved in
  this document.

## 2. Why this task exists

T023 replaced flat 8h/day absence accounting with schedule-based hours. It did
not add general work-rest legality rules.

A holistic post-T023 audit
(`tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/FINDINGS.md`, Section B) found
two separate gaps in the current scheduling rules:

- no legal rest floor after a 24h duty in the security equivalent-time
  system;
- no 35h uninterrupted weekly-rest check.

These are not T023 absence-accounting regressions. T023b is a separate task.

OWNER RULING (2026-08-23, Paweł, verbatim intent): the program needs a mode
switch — "checkbox określający tryb pracy programu ochrona/zwykłe zasady" —
so that ochrona-mode Sites receive the new rest protections, while ordinary
Sites retain today's coordinator-configured behaviour.

OWNER RULING (2026-08-23, Paweł, verbatim intent): these protections are legal
minimums, not judgment calls — "jeśli koordynator zechce je ręcznie złamać to
jego sprawa, ale nie budujemy programu łamiącego prawo." Automatic planning
must not propose a violating plan. An explicit manual correction may persist
one only through the existing audited hard-violation/REST-override precedent
described in Section 6.

Do not describe T023b as complete Polish-labour-law compliance. Its closed
candidate scope is only the two protections in Section 7. Night work, payroll,
settlement of wages and other work-time rules remain outside this task.

## 3. Official legal facts (verified 2026-08-23)

Primary source: current codified Kodeks pracy, Dz.U. 2025 poz. 277, ELI text
showing legal state current on 2026-08-18:

https://eli.gov.pl/api/acts/DU/2025/277/text/U/D20250277Lj.pdf

Official explanatory source: Państwowa Inspekcja Pracy, `Czas pracy`:

https://www.pip.gov.pl/dla-pracownikow/porady-prawne/czas-pracy

### 3.1 Rest after extended work — art. 136 §2 with art. 137

Art. 137 allows employees guarding property or protecting persons to work in
an equivalent-time system with a daily dimension extended up to 24 hours and
applies art. 136 §2 accordingly. Art. 136 §2 requires, immediately after work
in the extended daily dimension, uninterrupted rest lasting at least as many
hours as were worked, independently of weekly rest under art. 133.

For the exact T023b case selected by the owner, 24h worked therefore requires
at least 24h immediate rest.

### 3.2 Weekly rest — art. 128 §3 point 2 and art. 133

Art. 133 §1 establishes at least 35 hours of uninterrupted rest in each week,
including at least 11 hours of uninterrupted daily rest.

This rule cannot be specified as an arbitrary rolling seven-day window or ISO
week. Art. 128 §3 point 2 defines `week` for work-time accounting as seven
consecutive calendar days beginning on the first day of the settlement
period. The eventual contract must identify the durable source of that
settlement-period start and must test both sides of month/year boundaries.

The base 35h statement is not the whole statutory rule:

- art. 133 §2 permits weekly rest shorter than 35h, but not shorter than 24h,
  in the cases named there, including a scheduled transition to another
  shift;
- art. 133 §3 says weekly rest should fall on Sunday and defines the Sunday
  interval;
- art. 133 §4 permits another day where Sunday work is allowed.

Section 8 records the owner's deliberately stricter product treatment of
these cases.

### 3.3 Night work — out of scope by owner ruling

OWNER RULING (2026-08-23): T023b does not model the night-work window from
art. 151⁷, night-work compensation or protected-group HR eligibility. This is
outside product scope, not deferred into the T023b contract.

## 4. Confirmed current-code gap

### 4.1 Current REST-01 does not derive a legal floor

`REST_MIN_HOURS = 11` (`rota/constants.py`) is the general legacy-compatible
default. `work_periods.resolve_required_rest` uses it only for legacy
provenance. Normal T012 paths use persisted rest provenance derived from a
coordinator-configured `StandardShift.required_rest_hours` value. The field's
own comment in `rota/domain.py` states that its default is not a
program-enforced legal minimum.

Consequently an explicit 24h WorkPeriod with `required_rest_after_hours=11`
can pass current REST-01. No check raises the effective minimum to 24h in an
ochrona mode.

### 4.2 Both existing 24h mechanisms must be covered

A contract limited to one of these paths would leave the same bug class open:

1. **Catalog H24** — two 12h D/N components share one `work_period_id`.
   Terminal rest is carried by `Assignment.required_rest_after_hours` and
   checked through `work_periods.py`/REST-01.
2. **Emergency 24h pair** — two ordinary H12 demands are joined through the
   T012-C rescue path. The earlier demand carries the separate snapshot
   `ShiftDemand.emergency_24h_rest_hours`; independent validation cross-checks
   that provenance in `work_periods.py`/`SHIFT-24-PAIR-01`.

The architect must produce one invariant covering both, including same-month
and cross-month emergency pairing. The implementation must not trust only a
catalog label or only one rest-hours field.

### 4.3 LOAD-01 is not weekly rest

LOAD-01 computes hours worked in a rolling seven-day window against
`SiteProfile.rolling_7d_decision_threshold_hours` and reports
`DECISION_REQUIRED`. It neither finds an uninterrupted rest interval nor uses
the statutory week boundary. It remains a separate current feature and must
not be renamed or reused as proof of art. 133 compliance unless the frozen
contract explicitly supersedes its semantics.

### 4.4 No hidden prior implementation

At the audited base there is no frozen addendum or `rota/` symbol implementing
the two T023b protections. The existing 11h/rest-provenance and LOAD-01 paths
are the only adjacent mechanisms.

## 5. Site-mode ownership and compatibility boundary

The owner's language makes the behaviour a fact about a **Site**: an ochrona
Site receives the new protections; an ordinary Site does not. Do not infer
that `SiteProfile` is automatically a per-Site owner. In the current model a
`Site` references a `SiteProfile` by `profile_id`, and the model does not
guarantee that a profile is bound to only one Site.

Current adjacent fields are not reusable without an explicit contract:

- `SiteProfile.rolling_7d_decision_threshold_hours` is per profile and owns a
  soft LOAD-01 threshold, not a legal regime;
- `SitePrintSettings.base_regime` is keyed by `site_id` but is print/export
  configuration (`"12h"|"24h"`), not solver input.

The architect chooses storage/API mechanics, but the resulting semantics must
remain per-Site and must not silently switch other Sites merely because they
share a profile. Reusing `base_regime` is not authorized: 12h/24h print shape
and ochrona/ordinary legal mode are independent facts.

Compatibility consequences already fixed by the owner wording:

- existing Sites migrate/default to ordinary mode so their current planning
  behaviour does not change merely because T023b is deployed;
- ordinary mode skips only the new T023b checks; it is not a second redesigned
  ruleset;
- the requested mode is coordinator-visible and editable as a checkbox in
  Site creation/editing. The architect must name the write/read boundary and
  authorization path; visual design belongs to T021, not this addendum.

## 6. HARD classification and existing manual-override precedent

Both selected protections are HARD for automatic planning in ochrona mode:

- the solver must never propose a violating candidate;
- independent validation must report the same HARD violation from persisted
  facts rather than trusting solver literals;
- `plan()`/candidate selection/`replan()` cannot turn the violation into
  `DECISION_REQUIRED` or silently accept it.

An explicit coordinator manual correction may persist a HARD violation. This
is not authorization for a second override system. The existing precedent is
REST-01 in `rota/application/manual_edit.py`:

- `apply_manual_correction` validates the corrected snapshot and materializes
  HARD deviations instead of treating them as automatic candidates;
- `_rest_override_pairs`, `_rest_override_rule_content` and
  `_with_rest_override_hook` independently reconstruct REST-01 facts;
- the successful write records an audited `CONFIRMED_EXCEPTION` rule with
  `INFORMATIONAL` enforcement and `RESOLVED` status.

The new checks must have equally explicit, atomic and fact-derived audit
records when manually overridden. The architect decides whether the existing
plumbing is generalized or extended; CC must not duplicate it by local
convention. Automatic planning never invokes this override path.

## 7. Product scope (closed)

T023b covers exactly:

1. in ochrona mode, immediate rest of at least 24h after an actual 24h duty,
   across both Catalog H24 and emergency-pair mechanisms;
2. in ochrona mode, an automatic HARD floor of 35h uninterrupted weekly rest,
   anchored to the week definition in art. 128 §3 point 2 and the
   calendar-month settlement period fixed in Section 8;
3. identical independent-validation results for automatically generated and
   persisted/manual snapshots;
4. employee-wide evaluation across all Sites and across the temporal boundary
   needed to prove the applicable rest interval;
5. audited explicit manual override through the precedent in Section 6;
6. ordinary-mode compatibility described in Section 5.

The following remain outside T023b:

- absence accounting from T023/T026;
- payroll, benefits, wage settlement and HR entitlement;
- night-work-window modeling;
- general monthly/average weekly work-time limits;
- a redesign of LOAD-01 or print settings;
- new coordinator policy toggles unrelated to the ochrona/ordinary mode.

## 8. Binding decisions closing art. 133 scope (2026-08-23)

O1 and O2 are owner rulings (confirmed directly by Paweł, 2026-08-23,
outside this document). O3 is Codex's own legal-provenance finding
(derived from the already-established art. 137 fact that ochrona's
equivalent-time settlement period is capped at 1 month), not a product
decision Paweł originated — confirmed/accepted by Paweł as correct
after CC flagged the ambiguous attribution.

### O1 — automatic floor is always 35h

In ochrona mode the automatic solver and independent validator always apply a
35h uninterrupted weekly-rest HARD floor. T023b does not automatically model
the art. 133 §2 shortening to 24h, even where such shortening could be lawful.

A coordinator who needs to apply a statutory 24h exception must do so through
an explicit manual correction. The correction remains a HARD deviation and
must produce the audited `CONFIRMED_EXCEPTION` record required by Section 6;
it must never become an inferred solver exception or `DECISION_REQUIRED`.
The audit record must identify the affected employee, weekly interval,
observed rest duration and coordinator action. The architect defines the
smallest fact shape consistent with the existing manual-override precedent.

### O2 — Sunday placement is outside T023b

Art. 133 §3-4 Sunday placement is not enforced by T023b. The weekly rule in
this task concerns uninterrupted duration only. Do not add employer-defined
Sunday boundaries, Sunday-work authorization data or Sunday-placement
constraints.

### O3 — settlement period is the calendar month (Codex finding, owner-confirmed)

For T023b the applicable settlement period is the calendar month. Its first
day is the statutory week anchor; successive seven-day intervals are derived
from that first day, not from ISO weeks and not from arbitrary rolling
windows. The architect must specify the exact trailing/boundary read window
and ensure that work from adjacent months and other Sites cannot disappear
from validation.

These three decisions close the known product questions. The architect may
return `OWNER DECISION REQUIRED` only for a newly demonstrated contradiction
that cannot be resolved from this document or current frozen contracts.

## 9. Minimum required contract oracles

The frozen addendum/test matrix must include at least:

1. Catalog H24 followed by gaps of 23h59m, 24h and 24h01m;
2. same-month emergency H12+H12 pair with the same three boundaries;
3. cross-month emergency pair and a next duty in the following month;
4. a 24h duty whose configured rest is 0/11/23 but whose effective ochrona
   floor remains 24h;
5. the same facts in ordinary mode retaining current configured behaviour;
6. employee assignments split across two Sites, including a violating next
   duty on another Site;
7. weekly-rest windows immediately below, exactly at and above the selected
   floor;
8. a statutory week spanning a month/year boundary and anchored by the
   settlement-period start;
9. an automatic candidate with only 24h weekly rest is rejected even in a
   fact pattern where a statutory shortening may exist; the equivalent
   explicit manual correction persists only with the required audited
   exception record;
10. automatic solver, independent validator and persisted-snapshot parity;
11. manual correction persists only with deviation plus one atomic audited
    override record containing reconstructable facts;
12. failure/fault injection proving that schedule-version persistence and the
    override audit record cannot commit separately;
13. no duplicate override record for one logical manual correction;
14. ordinary Sites and existing migrated Sites preserve pre-T023b results;
15. no Sunday-placement rule is introduced by solver, validator or manual
    correction;
16. malformed/missing mode or settlement-boundary data fails according to an
    explicitly frozen rule, never by accidental fallback.

Do not write code from this document. First freeze the architect contract and
obtain independent Codex preimplementation PASS.
