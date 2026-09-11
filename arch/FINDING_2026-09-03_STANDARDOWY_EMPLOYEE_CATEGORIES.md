# FINDING 2026-09-03 — "Standardowy" regime needs independent employee
categories (kierownicy/załoga/uczniowie); print export needs category
grouping too.

STATUS: finding + verified scope estimate, NOT a design doc, NOT frozen.
Architect-input material (same role as `arch/T004_T005_architect_brief.md`
and other `arch/FINDING_*` docs) — CC does not author the implementation
brief here; that is architect Claude's job once Paweł relays this. No
TASK_SCOPE/WHERE_MAP/acceptance-matrix contract exists yet on purpose.

Related: backlog memory item 11 ("Standardowy" site regime is Ochrona's
model reused unchanged) and item 7 (single global working-month control,
unrelated but re-raised the same day).

## Origin / requirement

Paweł's own words describing the first concrete "Standardowy" target — his
wife's retail shop:

> dla żony musimy mieć zmiany 5-12 i 12-19 od poniedziałku do piątku i w
> soboty od 5 do 14. ale nie ma sensu robić wersji sklepowej dokladnie pod
> jej sklep bo to szkoda roboty. W sklepie muszą być 3 warstwy załogi
> rotujące niezależnie: kierownicy, zaloga i uczniowie. ewentualnie ekipa
> sprzątająca.

Explicit constraint: do not hand-build a one-off shop-specific version —
this must land as a general "Standardowy" capability (part of the same
feature-basket approach already agreed for other business types: handel,
magazyn, produkcja, gastronomia, transport, etc. — see the small-findings
backlog for the fuller cross-industry table). "Ekipa sprzątająca" is
explicitly tentative ("ewentualnie"), not a confirmed fourth category.

Later, reviewing this finding: "na pewno to będzie też nowy wydruk" — the
printed schedule must also change (see "Print/export impact" below), this
is not backend-only work.

## Verification method (important — do not re-derive from scratch)

Paweł explicitly distrusted a first, grep-based CC pass on this exact
question ("już parę razy twierdziłeś że czegoś nie ma w kodzie bo nie
sprawdziłeś na poważnie") and authorized a one-time investigation agent to
re-verify by reading full files, not grepping and assuming. That agent's
findings were then spot-checked by CC with `where.py` (mechanical raw-hit
tool) plus a direct read of the two files the agent had flagged as
unverified (`fairness.py`, `constraints.py` — zero category/role-related
hits found in either). The verdicts below are the result of that two-pass
verification, not a single quick read.

## Verified findings

**1. Arbitrary shift start/end times per weekday — COMPATIBLE TODAY, no
code change needed.** `StandardShift` (`rota/domain.py:117-130`) has
free-form `start_time`/`end_time`; `validate_standard_shift_shape`
(`rota/planning/shift_catalog.py:95-123`) only enforces non-negative rest,
valid `active_weekdays`, and full-clock-hour start/end — it does not force
12h/24h duration when `catalog_kind` is left `None` (the normal case),
`normalized_catalog_kind` auto-classifies any other duration into `OTHER`.
`active_weekdays` genuinely filters demand generation per calendar day
(`_all_components`, `shift_catalog.py:195-210`), traced end-to-end through
`generate_catalog_demands` (`shift_catalog.py:246-256`) →
`rota/application/assembler.py:71`. Three `StandardShift` rows (Mon-Fri
5:00-12:00, Mon-Fri 12:00-19:00, Sat-only 5:00-14:00) already express the
target case as-is.

**2. Closed Sunday — COMPATIBLE TODAY, but via a different mechanism than
expected.** `CalendarDay.holiday` is never consulted by demand generation
at all — it only feeds fairness scoring (`rota/planning/fairness.py`) and
print-header styling (`schedule_export.py`), confirmed by tracing every
reference. The actual "no work happens" mechanism is simply never
including weekday `7` in any `StandardShift.active_weekdays` — already
sufficient, no `holiday` flag needed for this purpose.

**3. Independent, non-interchangeable employee categories — CONFIRMED
MISSING, needs new domain-model logic.** Full reads of `rota/domain.py`,
`rota/planning/eligibility.py` (244 lines), and the relevant sections of
`rota/planning/solver.py`, cross-checked with `where.py` on `MembershipKind`
across the whole repo history (including archived task diffs): `MembershipKind`
has only ever had `LOCAL`/`EXTERNAL_SUPPORT`; `AssignmentRole.TRAINEE` is a
solo-vs-mentored distinction for the onboarding program, not a job-category
partition; `ShiftDemand` carries nothing that could tag a required
category. No partial, deprecated, or half-built category mechanism exists
anywhere in `rota/`, `fairness.py`, or `constraints.py`.

## Touch-point map (factual, not a design)

If a category concept is added:

- `rota/domain.py` — a category value needs to live somewhere (`Employee`
  or `SiteMembership`; `SiteMembership` is more consistent with how
  `membership_kind`/`can_work_24h` are already modeled per-site) and a
  required-category field needs to land on `StandardShift`/`ShiftDemand`.
- `rota/planning/shift_catalog.py` — `_Component`/`_components_for_shift`
  (139-164) and `_components_to_demands` (213-243) need to carry the
  category from `StandardShift` through to each generated `ShiftDemand`;
  `validate_standard_shift_shape` needs category-aware validation.
- `rota/planning/eligibility.py` — one new HARD gate comparing
  employee/membership category against the demand's required category,
  analogous to the existing `MEMBERSHIP_DISABLED`/`SHIFT-24-01`/
  `DAY_ONLY-01` gates in `_common_hard_gate` (151-192).
- `rota/planning/solver.py` — likely **no structural change** to
  `_add_coverage_constraints` (301-316): it already builds one constraint
  per `demand_id`; two overlapping demands at the same time slot (one
  tagged "kierownik", one tagged "załoga") already get independent
  coverage once eligibility filters slots per-demand by category. The new
  eligibility gate alone should be sufficient for the solver side.
- `rota/planning/fairness.py`, `rota/planning/constraints.py` — read in
  full during verification, zero category-relevant content found; flagged
  as needing review only if fairness/rest scoring is ever meant to differ
  per category (not requested so far).

## Print/export impact (new, from Paweł's own follow-up)

`rota/application/schedule_export.py::_build_rows` (roster assembly) and
its row ordering (`rows.sort(key=lambda r: (r.display_name.casefold(),
r.employee_id))`, currently pure alphabetical) produce one flat table of
every site employee with no grouping. Paweł: "na pewno to będzie też nowy
wydruk." A category-aware printed schedule would need to group/section
rows by category (e.g. kierownicy first, then załoga, then uczniowie) —
this is real, additional scope beyond the backend/solver work above, not
automatically covered by it. Not investigated in detail this pass
(`schedule_export.py`'s current single-table, single-legend layout was
only confirmed to lack grouping, not redesigned).

## Scale assessment

Genuinely architect-scale (touches the core domain model, the eligibility
gate, and shift-catalog generation — three separate files needing a new
concept threaded consistently), but narrower than "rewrite the solver":
the two new pieces (a category value on the employee/membership side, a
category requirement on the demand side) are additive fields following an
existing, well-worn pattern in this codebase (`can_work_24h`,
`membership_kind`, `catalog_kind`), not unprecedented architecture. The
solver's core constraint-building machinery likely does not need
restructuring. Print/export grouping is a genuinely separate, additional
piece of scope on top of the backend change.

## Explicitly open, not decided here

- Where the category value lives (`Employee` vs `SiteMembership`).
- Whether "ekipa sprzątająca" is in scope now or genuinely tentative.
- How a category interacts with `EXTERNAL_SUPPORT`/`can_work_24h`/existing
  `SiteRule`s (e.g., can an EXTERNAL_SUPPORT employee cover any category,
  or only "załoga"?).
- Exact print layout/grouping/labels for the category-aware schedule.
- Whether this is scoped as one Task or split (domain+solver work vs.
  print work) — Paweł has not been asked this yet.

No brief.md/TASK_SCOPE exists for this finding. Next step is Paweł's
decision on whether/when to relay this to architect Claude.
