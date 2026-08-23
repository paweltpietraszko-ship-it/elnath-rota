# T023b — ochrona rest-rule enforcement: architect input material

DATE: 2026-08-23
STATUS: fact + direction, NOT a design doc, NOT frozen. Same role as
`arch/T004_T005_architect_brief.md` and the original
`arch/T023_absence_hours_architect_brief.md` served for their tasks — CC
does not author the implementation brief or any new FROZEN_ADDENDUM here;
that is architect Claude's job once Paweł relays this over.

AUTHORITY BOUNDARY: this document states what current code does and what
current law text says. It does not decide field names, enforcement
mechanism, or scope boundaries beyond what Paweł has explicitly ruled
below.

## 1. Why this task exists

T023 (merged to `main`) correctly replaced flat 8h/day absence accounting
with schedule-based hours (actual scheduled shift length: 12h D/N, 24h
once for a legal 24h period). That was the accounting-side fix.

Paweł's original request for T023 also included verifying general KP
(Kodeks pracy) compliance for ochrona's równoważny system (12/24h shifts).
A holistic post-T023 audit (`tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/FINDINGS.md`,
section B, 2026-08-22) found that several *rest-rule* requirements — not
absence-hour accounting — are not enforced anywhere in the codebase. T023
never claimed to cover these; they were simply never implemented. T023b
is the follow-up task to close that gap.

OWNER RULING (2026-08-23, Paweł, verbatim intent): the program needs a
mode switch — "checkbox określający tryb pracy programu ochrona/zwykłe
zasady" — so that ochrona-mode Sites get the real KP rest rules for
równoważny czas pracy enforced, while normal Sites keep today's
coordinator-configured behavior unchanged.

## 2. What current code does NOT enforce (confirmed against source, 2026-08-23)

### 2.1 Rest after a 24h shift (art. 136 §2 w zw. z art. 137 KP)

Law text (checked against lexlege.pl, t.j. Dz.U. 2025 poz. 277 — the
same source citation as the holistic audit; article numbers not
independently re-verified beyond that source today):
- Art. 137 KP: pracownicy zatrudnieni przy pilnowaniu mienia lub ochronie
  osób mogą pracować w systemie równoważnego czasu pracy z przedłużeniem
  dobowego wymiaru czasu pracy do 24 godzin, w okresie rozliczeniowym
  nieprzekraczającym 1 miesiąca; stosuje się odpowiednio art. 135 §2-3
  oraz art. 136 §2.
- Art. 136 §2 KP: bezpośrednio po okresie pracy w przedłużonym dobowym
  wymiarze pracownikowi przysługuje odpoczynek odpowiadający co najmniej
  liczbie przepracowanych godzin (tj. po 24h służby — co najmniej 24h
  odpoczynku), niezależnie od odpoczynku z art. 133.

Code today: `REST_MIN_HOURS = 11` (`rota/constants.py:3-4`, explicit "art.
132 KP" comment — that is the GENERAL 11h daily rest default, not the
after-24h rule). `work_periods.resolve_required_rest` falls back to this
11h only when provenance is missing; live REST-01 otherwise uses a
per-period `required_rest_hours` value that the COORDINATOR types in
(`arch/spec.md` T012: "coordinator enters required_rest_hours >= 0; the
program enforces that number and does not derive or validate law"). A
coordinator can today set `required_rest_hours=11` after a 24h shift and
the program will accept it — nothing checks that a 24h shift's follow-up
rest is ≥24h.

### 2.2 Weekly rest (art. 133 KP)

Law text: co najmniej 35 godzin nieprzerwanego odpoczynku w każdym
tygodniu (obejmujące 11h dobowego odpoczynku); §2 allows shortening to
24h in specific listed cases; §3 ties it to Sunday absent an authorized
exception.

Code today: no symbol implements a 35h consecutive weekly rest check at
all. The only weekly-scale mechanism is LOAD-01
(`rota/planning/validator.py:479-496`, `constraints.py`,
`engine.py:374+`) — a rolling 7-day *worked-hours* ceiling against
`SiteProfile.rolling_7d_decision_threshold_hours` (example default 60h).
Exceeding it produces a coordinator-facing `DECISION_REQUIRED` ("Koliduje
z tygodniowym czasem pracy") — a soft flag the coordinator can override,
not a hard block, and it counts hours worked, not consecutive rest hours.
Two 24h duties with only an 11h gap between them can pass REST-01 today
and still contain no 35h uninterrupted rest block anywhere in that week.

### 2.3 Night work (art. 151⁷ KP) — correction from prior message

Art. 151⁷ §1 KP: pora nocna obejmuje 8 godzin między godzinami 21:00 a
7:00 — the employer fixes ONE specific 8-hour window inside that wider
21:00-7:00 (10h) span; the 8h is the length of "pora nocna" itself, not
the boundary span (I stated this ambiguously in the prior message — the
21:00-7:00 span is 10 hours, the chosen night period within it is 8).
Related provisions (not re-verified in full text this pass) generally
give night workers extra protections and cap night work at 8h in a
24h period for certain categories.

Code today: `ShiftKind.N` exists with a typical example start-time of
17:00 (per `Grafiki/`/T012 examples), but there is no modeled 8h night
window, no per-shift split between "night portion" and "day portion" of
an N shift, and no night-specific hour cap. Whether this needs
scheduling-time enforcement at all (vs. being purely a payroll/HR
concern out of this program's stated boundary — `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md` §1: "Rota does not own payroll,
benefits, leave entitlement, HR settlement") is an open question, not
answered here — see section 4.

## 3. Existing precedent for a Site-level mode field

`SiteProfile` (`rota/domain.py:126`) already carries several structural,
non-coordinator-facing fields describing what KIND of Site this is:
`rolling_7d_decision_threshold_hours` (a number the coordinator sets, but
structurally per-Site). `SitePrintSettings.base_regime` (`rota/persistence/site_repository.py:60`, `"12h"|"24h"`) is a DIFFERENT, already-existing
per-Site field — but it is print/export-only (controls how
`schedule_export.py` pairs work-code values for the PDF legend); it does
not feed the solver, eligibility, or REST-01/LOAD-01 at all. It is not a
usable hook for legal enforcement as-is, but is worth the architect
knowing it exists so a new field is not confused with it or duplicated.

This is a different kind of field than the four toggles Paweł removed
from UI scope on 2026-08-22 (`arch/T021_owner_decisions_2026-08-22.md`
D2): those were about the coordinator's own judgment calls (training
timing, external-support availability, night-shift eligibility per
employee) which he ruled the program must not gate. A
ochrona/zwykłe-zasady mode is not a coordinator judgment call — it is a
structural, legal-regime fact about the Site (does KP's równoważny system
for pilnowanie mienia/ochrona apply here or not), analogous to why
`base_regime` and the (not-yet-built) absence-accounting-strategy
distinction from the earlier finding are Site-level facts, not
coordinator overrides.

## 4. Explicitly NOT decided here

- Exact field name/type/values on `SiteProfile` (or whether it reuses/
  replaces `SitePrintSettings.base_regime` — architect must confirm
  these should stay separate, since one is print-only today).
- Whether "zwykłe zasady" mode changes any code path at all, or is simply
  the absence of the new ochrona-only hard checks (i.e., is it a real
  second ruleset, or just "ochrona checks are skipped when off").
- Exact mechanism/placement for the ≥24h-rest-after-24h-shift check (new
  REST-01 variant vs. a new constraint class).
- Exact mechanism for weekly 35h consecutive rest — this is a genuinely
  new constraint shape (a rest window, not an hours-worked ceiling) with
  no existing analog in `rota/planning/constraints.py` today.
- Whether night-work window modeling (2.3) is in scope for T023b at all,
  is deferred as a separate task, or is ruled out-of-scope as an HR/
  payroll concern per the existing product boundary — Paweł has not yet
  ruled on this specific sub-point; the rest-after-24h (2.1) and weekly
  rest (2.2) points are the ones he explicitly named.
- Interaction with existing coordinator-entered `required_rest_hours`:
  does a new hard ochrona rule override a coordinator's smaller manual
  entry, or does it validate/reject it?
- HARD vs DECISION_REQUIRED (soft) classification for the new checks —
  today's LOAD-01 precedent is soft; Paweł's phrasing ("program ma to
  wymuszać" in the surrounding conversation) suggests HARD is intended
  for at least 2.1, but this needs explicit confirmation, not inference.

## 5. Open question for Paweł (not for architect)

Is night-work window modeling (2.3) part of T023b's scope, or should
T023b cover only 2.1 (rest after 24h shift) and 2.2 (weekly 35h rest) —
the two points explicitly named — with 2.3 tracked separately or ruled
out of scope?
