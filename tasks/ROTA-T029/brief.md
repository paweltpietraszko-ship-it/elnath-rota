# ROTA-T029 — direct checkbox toggle for the employee matrix

Status: **IMPLEMENTED**

Base branch/SHA: `task/ROTA-T029` from `37973b5` (main, post-T027)

## 1. Owner intent (Paweł, 2026-08-24, live-tested T021 Screen 2)

Checkboxes in the employee matrix (Dniówka/Nocka/dni tygodnia) ARE the
instruction to the solver — click = immediate, permanent decision, no date
required. Dated "restrictions" were meant only for temporary EXCEPTIONS to
that instruction (owner's example: 24h is off by default; coordinator checks
it and optionally says "for 10 days"). The separate "Ograniczenia: Dniówka /
Nocka / dni tygodnia" add-form (forcing both a start AND end date on every
restriction, even a permanent one) was a design error introduced in T021b —
it made every permanent decision look like it needed a remembered date.

## 2. Verified before touching anything (per owner instruction)

Traced every use of `effective_to` end-to-end: `SiteRuleVersion.effective_to`,
`NewRuleContent.effective_to`, `site_rule_repository`'s read/write, and
`effective_rule_on`/`assemble_monthly_site_rules` (the solver-facing
projection) already treat `effective_to=None` as "in effect indefinitely" —
this is pre-existing, working behavior, not something T029 adds.
`end_employee_matrix_rule_early` already branches on `version.effective_to is
None`. Only T021b's own wrapper functions in `rota/application/
rule_decisions.py` and their API bodies artificially required both dates.
No T021b test asserts the date is required. Full trace in delivery notes.

## 3. Fix

- `rota/application/rule_decisions.py`: `create_employee_shift_unavailability`,
  `create_employee_weekday_unavailability`, `create_day_only_n_exception`,
  `update_employee_matrix_rule_period` — `effective_to: Optional[date]`;
  skip the `effective_from > effective_to` guard when `None`; statement
  generators gain a None-safe "bezterminowo" phrasing.
- `api/routers/rule_decisions.py` — matching 4 Pydantic bodies:
  `effective_to: str | None = None`.
- `frontend/src/api/client.ts` — matching type widening.
- `frontend/src/screens/EmployeeDetail.tsx` — the matrix's Dniówka/Nocka/
  weekday cells become directly clickable: click toggles the underlying rule
  immediately (create with no end date, or end-early to restore), no form.
  Nocka for a `day_only` employee is the one genuine temporary-exception case
  (owner's own model) — its click opens a small dated form
  (`create_day_only_n_exception`) instead of a plain permanent toggle.
  Removed the "+ Nowe ograniczenie" always-dated add form for Dniówka/Nocka/
  weekday (superseded by direct click). Kept the restriction list's own
  date-correction/early-end actions for existing periods.

## 4. Scope

`rota/application/rule_decisions.py`, `api/routers/rule_decisions.py`,
`frontend/src/api/client.ts`, `frontend/src/screens/EmployeeDetail.tsx`. No
schema change (the nullable column already existed).

## 5. Verification

- Full Python regression.
- New backend tests covering open-ended create/update.
- Frontend build; manual verification via the live dev server.
