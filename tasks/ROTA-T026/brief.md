# ROTA-T026 — ABSENCE CANONICALIZATION OWNERSHIP REPAIR

STATUS: READY FOR INDEPENDENT CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
BASE_PRODUCT_SHA: `3d2c2dce52af9e48f28d86b8160249f2040d405c`
ARCHITECT_INPUT_SHA: `64774715ecb1cfb56dc7cd69a2192761e0eba335`
CONTROLLING_CONTRACT: `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md` + preserved T023 decisions in `tasks/ROTA-T023/brief.md`

This task repairs two post-T023 ownership/canonicalization gaps without changing product semantics. It does not reopen T023 absence-hour rules, T020 presentation rules, payroll/HR, labor-law modeling, or coordinator UX error policy.

## 1. SOURCE / FACT CLASSIFICATION

Confirmed source material:
- `arch/T026_absence_canonicalization_gaps_architect_brief.md`;
- `tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/REQUEST.md`;
- `tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/FINDINGS.md`;
- current product `main@3d2c2dc`.

Facts confirmed against current code:
1. `rota/planning/engine.py::_plan()` still calls the retired T018 SICK-only `excused_absence_days_in_month(..., calendar_days=...)` gate before solving, although T023 solver TARGET now consumes only `PlanningState.work_balances[].absence_hours`.
2. `rota/application/schedule_export.py` independently chooses SICK over LEAVE on a date and independently derives POST_PLAN Site hours from bound periods, despite frozen T023 assigning precedence/accounting/Site filtering to one pure canonical owner in `rota/planning/absence.py`.
3. `rota/planning/absence.py` still contains stale pre-B/C ownership comments.

These are implementation/ownership gaps under an already-decided product contract. No new owner/product decision is required for the repair below.

## 2. DISPOSITION

### T026-1 — stale engine CalendarDay/SICK gate

DISPOSITION: **AUTHORIZED IN T026 — REMOVE THE STALE GATE.**

Architect decision:
- `plan(PlanningState)` is a public planning-engine boundary over an already constructed `PlanningState`.
- For absence-hour accounting specifically, `PlanningState.work_balances` is authoritative input.
- `plan()` / `_plan()` must not reconstruct, recount, or independently completeness-check SICK/LEAVE absence hours from `availability_records`, `CalendarDay`, source mode, or the T018 flat-8 helper.
- Raw `availability_records` remain valid planning input for their existing HARD eligibility/validator responsibilities; this decision is only about absence-hour accounting/TARGET provenance.
- `plan()` continues to own its existing planning-model validation/orchestration/status mapping (SiteRule execution validation, solver orchestration, independent validator, three PlanningResult statuses). T026 does not redefine those boundaries.

Supported production planning path:
- `plan_month()` assembles state through `assemble_planning_state()` before calling `plan()`.
- `replan()` assembles state through `assemble_planning_state()` before calling `plan()`.
- `select_candidate()` validates a supplied candidate and does not call `plan()`.
- `assemble_planning_state()` builds `work_balances` through `reconstruct_month_balance()`, which is the existing fail-closed canonical absence-reference path.

Therefore:
- remove the `engine.py` import/use of `excused_absence_days_in_month` and `IncompleteAbsenceCalendarError` that exists solely for the old SICK CalendarDay gate;
- remove the obsolete `_sick_adjusted_targets()` explanatory comment;
- do **not** replace it with a new raw-Availability/CalendarDay guard or a new invented WorkBalance completeness invariant.

Why recommended: T023 already moved TARGET accounting to canonical WorkBalance. A second SICK-only T018 gate validates a retired representation rather than the value the solver actually consumes.

Concrete problem solved: a hand-built or otherwise valid canonical `PlanningState` can currently become `TECHNICAL_ERROR` solely because its raw CalendarDay/SICK legacy representation is incomplete/conflicting, even when its canonical WorkBalance is already the authoritative target input.

### T026-2 — T020 duplicate precedence / Site POST_PLAN arithmetic

DISPOSITION: **AUTHORIZED IN T026 — KEEP `rota/planning/absence.py` AS THE SINGLE PURE OWNER AND EXTEND ITS PURE PROJECTION API.**

No frozen amendment is authorized. The existing single-owner contract remains controlling.

Layering decision:
- `rota/planning/absence.py` remains pure and persistence-free.
- It must not import `rota.persistence.*`.
- `rota/application/schedule_export.py` may mechanically decode/map persisted `AbsenceReferenceSnapshot` / `DayReference` / `PeriodFact` fields into pure input dataclasses owned by `rota/planning/absence.py`.
- Persistence remains provenance/I/O; presentation remains code/symbol rendering; accounting/precedence/range/Site projection remains in the pure canonical owner.

Required pure shapes in `rota/planning/absence.py` (exact names may be mechanically adjusted by CC only if a collision exists; semantics may not change):

`DetailedAbsencePeriodFact`
- `assignment_id: str`
- `schedule_version_id: str`
- `site_id: str`
- `covers_demand_id: Optional[str]`
- `work_period_id: Optional[str]`
- `start_datetime: datetime`
- `end_datetime: datetime`
- `shift_kind: Optional[str]`
- `catalog_kind: Optional[str]`
- `required_rest_hours: Optional[int]`
- `work_period_template_id: Optional[str]`
- `work_period_component: Optional[int]`

`DetailedDailyAbsenceFact`
- `the_date: date`
- `kind: AvailabilityKind`
- `source_mode: str`
- `status: str`
- `hours: Optional[int]`
- `periods: tuple[DetailedAbsencePeriodFact, ...]`

`CanonicalSiteAbsenceDay`
- `the_date: date`
- `kind: AvailabilityKind`
- `source_mode: str`
- `canonical_hours: int` — the same Employee-global winning-day canonical hours represented by `DailyAbsenceFact.hours`;
- `site_hours: Optional[int]` — `None` for PRE_PLAN_LEAVE because it has no schedule Site provenance; for POST_PLAN_REFERENCE, exact hours belonging to the requested Site from bound period provenance, including 0 for accepted rest;
- `site_periods: tuple[DetailedAbsencePeriodFact, ...]` — POST_PLAN bound periods for the requested Site, preserving the immutable D/N/24h provenance T020 needs; empty for PRE_PLAN_LEAVE.

Required pure function:

`canonical_site_absence_days(facts, *, range_start, range_end, site_id) -> tuple[CanonicalSiteAbsenceDay, ...]`

Required behavior:
1. clip facts to the explicit inclusive `[range_start, range_end]` before winner/status evaluation;
2. apply the same one-owner SICK-over-LEAVE_GRANTED winner rule as `canonical_daily_hours`;
3. fail closed with `IncompleteAbsenceReferenceError` when the winning fact is MISSING/AMBIGUOUS; never guess 0/8/12/24;
4. PRE_PLAN_LEAVE: preserve the captured canonical `hours`; return `site_hours=None` and no site periods — Site attribution remains T020's already-frozen presentation boundary;
5. POST_PLAN_REFERENCE: preserve captured Employee-global `canonical_hours`, filter bound periods by `site_id`, and derive `site_hours` from those immutable period intervals exactly as T020 already does today; accepted rest therefore yields `site_hours=0`;
6. preserve bound period `shift_kind` and other captured period provenance so T020 can map D/N/24h symbols without re-reading CURRENT;
7. no source-mode choice from CURRENT and no new fallback/backfill.

Implementation ownership inside `absence.py`:
- `canonical_daily_hours` and `canonical_site_absence_days` must share one internal winner/status path; two independent SICK/LEAVE precedence implementations inside the same module are not acceptable.

Required `schedule_export.py` boundary after T026:
- it may load current Availability records and captured snapshots and mechanically construct `DetailedDailyAbsenceFact` values;
- it may enforce its existing presentation-only concerns: real-work/absence conflict, PRE_PLAN multi-LOCAL fail-closed attribution, exact legend/code availability, exact PRE_PLAN decomposition, D/N code selection from canonical `site_periods`;
- it must **not** contain its own SICK-vs-LEAVE winner implementation;
- it must **not** sum POST_PLAN Site period durations itself;
- it must consume `canonical_site_absence_days(...)` for winner/range/status/Site-hour projection.

Why recommended: this preserves the frozen T023 single-owner contract while keeping the pure domain layer free of persistence imports.

Concrete problem solved: T020 currently owns a second implementation of two rules already assigned to the canonical absence owner, so later changes/fixes can make WorkBalance/analytics and the PDF disagree even while both read the same persisted snapshot.

### T026-3 — stale comments

DISPOSITION: **AUTHORIZED CLEANUP, NO BEHAVIOR CHANGE.**

Within `rota/planning/absence.py`, remove/update stale comments/docstrings that claim solver/schedule_export are not yet wired or that live solver TARGET still uses the pre-T023 SICK-only flat-8 carve-out. Preserve historical T018 helper documentation where it still correctly describes the retained PRE_PLAN_LEAVE source.

Why recommended: the canonical owner should not document a superseded architecture as current behavior.

Concrete problem solved: stale comments can mislead a later maintainer into restoring a path T023 deliberately retired.

## 3. T026 DOES NOT CHANGE PRODUCT SEMANTICS

The following T023/T020 behavior remains frozen:
- SICK_LEAVE and LEAVE_GRANTED remain HARD unavailable.
- SICK wins same-date overlap and presents C once.
- PRE_PLAN_LEAVE remains owner-approved 8h per qualified weekday/nonholiday source captured at write time.
- SICK has no PRE_PLAN flat-8 fallback.
- POST_PLAN_REFERENCE hours come from accepted bound schedule periods, anchored wholly to work-period start date.
- 8/12/N/24/rest/weekend/holiday behavior remains unchanged.
- global WorkBalance is Employee-wide/cross-Site once; T020 prints only the requested Site's bound post-PLAN periods.
- PRE_PLAN multi-LOCAL no-provenance attribution remains fail-closed rather than duplicated.
- T020 U/C is presentation only and never demand coverage.
- no guessed historical backfill.
- TARGET remains SOFT and uses `max(0, target_hours - absence_hours)`.

T026 fixes ownership, not values.

## 4. TASK_SCOPE — FILES CC MAY MODIFY

Production:
- `rota/planning/engine.py`
- `rota/planning/absence.py`
- `rota/application/schedule_export.py`

Tests:
- `tests/test_t018.py` — only the exact superseded direct-plan CalendarDay/SICK oracle and mechanical imports/fixture edits required by that replacement;
- `tests/test_t026.py` — new T026 closure matrix.

Contract/process:
- `tasks/ROTA-T026/brief.md`

No other product/test file may be modified without a concrete independent-audit finding proving it is required to close this contract.

Inherited owner-accepted legacy SIZE_FILE exceptions in pre-existing large test files are not reopened merely because `tests/test_t018.py` receives the narrow oracle replacement above.

## 5. EXPLICIT OUT OF SCOPE

Do not modify or reinterpret in T026:
- `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`;
- `arch/spec.md`, `arch/FROZEN.lock`;
- DB schema/migrations;
- `rota/persistence/absence_reference_repository.py` capture/provenance rules;
- `rota/persistence/work_balance_repository.py` or `rota/balance.py`;
- `rota/application/assembler.py`, `durable_inputs.py`, `plan_ops.py`;
- eligibility/HARD absence rules;
- T012/T022 work-period/rest legality;
- labor-law findings/questions from Cursor section B, including 24h-after-rest, weekly rest and night-work window;
- Cursor C1 raw Availability UI/read split;
- Cursor C2 coordinator-screen error/degrade UX consistency;
- payroll, HR, leave entitlement, benefits or legal settlement;
- new absence ledger/history/versioning/backfill;
- new SiteProfile strategy/configuration.

Reading/calling existing out-of-scope APIs is allowed; modifying them is not.

## 6. DELIBERATE SUPERSESSION / PRESERVATION

Superseded exactly:
- `tests/test_t018.py::test_a7_9_direct_plan_with_incomplete_calendar_and_sick_absence_is_technical_error` as an oracle for the public `plan(PlanningState)` boundary. Its old meaning depended on pre-T023 SICK TARGET recounting from raw CalendarDay/Availability.

Replacement meaning:
- direct `plan()` with canonical `work_balances` must not become TECHNICAL_ERROR merely because raw SICK/CalendarDay data cannot support the retired flat-8 recount; the planning outcome is determined by the canonical state plus existing solver/validator rules.

Preserved:
- T018 helper tests that directly verify the retained qualified-workday/holiday function where it is still used as PRE_PLAN_LEAVE source;
- T23-32: solver consumes WorkBalance, no CalendarDay/flat recount/source-mode choice;
- T23-35: T020 is a projection of the same canonical absence facts;
- all T023/T020 range, precedence, Site, D/N, 24h, rest, MISSING/AMBIGUOUS and PRE_PLAN decomposition regressions;
- unrelated CalendarDay uses and planning rules.

No unrelated oracle may be weakened to make T026 pass.

## 7. REQUIRED TEST / AUDIT MATRIX

### Item 1 — engine trust boundary

T26-01 — direct `plan()` with a SICK record, canonical WorkBalance and no CalendarDay absence-accounting support does not fail with the retired `calendar error`; result follows normal solver/validator semantics.

T26-02 — for otherwise identical direct PlanningStates with the same canonical WorkBalance, changing only CalendarDay values cannot change absence TARGET arithmetic.

T26-03 — direct plan still uses raw SICK/LEAVE Availability for existing HARD eligibility semantics; removing the legacy hours gate must not make an absent Employee eligible.

T26-04 — production `plan_month()` and `replan()` retain existing upstream fail-closed behavior when required canonical absence reference/WorkBalance reconstruction is incomplete. T026 does not add a degrade-to-zero fallback.

T26-05 — retained direct tests for SiteRule/model/solver TECHNICAL_ERROR mapping remain unchanged.

### Item 2 — canonical Site projection

T26-10 — canonical Site projection clips to caller range before precedence/status checks; adjacent out-of-range MISSING/AMBIGUOUS cannot poison the requested range.

T26-11 — same-date SICK+LEAVE yields one SICK winner in both `canonical_daily_hours` and `canonical_site_absence_days`.

T26-12 — single-Site POST_PLAN projection has `site_hours == canonical_hours` and preserves shift-kind provenance.

T26-13 — multi-Site POST_PLAN projection preserves Employee-global `canonical_hours` but returns only requested Site's exact bound `site_hours`/periods; no membership-based duplication.

T26-14 — accepted POST_PLAN rest yields canonical/site 0 for that Site and T020 emits no synthetic U/C.

T26-15 — legal 24h and D/N period provenance survives the pure projection and produces the same T020 PLAN/WYK symbols as before.

T26-16 — PRE_PLAN_LEAVE keeps captured canonical hours with `site_hours=None`; T020 exact decomposition and existing multi-LOCAL fail-closed attribution remain unchanged.

T26-17 — winning MISSING/AMBIGUOUS raises canonical `IncompleteAbsenceReferenceError`; T020 maps it to its existing presentation integrity failure and never guesses hours.

T26-18 — `schedule_export.py` consumes the canonical Site projection; no local SICK/LEAVE winner function and no local POST_PLAN Site-duration sum remains.

T26-19 — `rota/planning/absence.py` imports no persistence module.

### Retained regressions

Must run and remain green at minimum:
- `tests/test_t020.py`;
- `tests/test_t023.py`;
- `tests/test_t023_checkpoint_b.py`;
- `tests/test_t023_checkpoint_c.py`;
- `tests/test_t018.py` after the exact oracle replacement;
- full configured repository suite;
- Ruff;
- `git diff --check`;
- repository scope/size/function guards, with only already owner-accepted inherited exceptions.

## 8. IMPLEMENTATION SHAPE

One implementation checkpoint only. Do not split T026 into independent feature checkpoints because both authorized fixes are small ownership repairs over one frozen absence model.

Expected production delta:
1. `engine.py`: delete retired SICK CalendarDay gate/import/catch path only.
2. `absence.py`: add detailed pure input/output projection types + one canonical Site projection reusing the same winner/status owner; clean stale current-architecture comments.
3. `schedule_export.py`: mechanical snapshot-to-pure-fact mapping; consume canonical projection; retain presentation/code mapping only.

No persistence/schema migration and no new runtime configuration.

## 9. INDEPENDENT CODEX PREIMPLEMENTATION GATE

Audit the exact contract HEAD before CC writes product code.

The audit must answer only:

T026-1:
- Does the contract correctly make canonical `work_balances` authoritative for absence TARGET at the `plan(PlanningState)` boundary?
- Does it remove only the retired SICK CalendarDay accounting gate without weakening raw Availability HARD exclusion or other engine validation?
- Is the old direct-plan T018 oracle superseded narrowly and explicitly?

T026-2:
- Does `rota/planning/absence.py` remain the one pure, persistence-free precedence/accounting/Site-projection owner?
- Is T020 allowed only mechanical persistence-to-pure mapping plus presentation/code mapping, not its own precedence or Site-hours arithmetic?
- Does the proposed projection preserve global canonical hours while exposing the exact Site slice and immutable D/N/24h provenance needed by T020?
- Are PRE_PLAN attribution, MISSING/AMBIGUOUS fail-closed, range clipping and existing T023/T020 outputs preserved?

Scope:
- confirm labor-law and Cursor C1/C2 items remain out of T026;
- do not invent a new product rule or new completeness invariant.

Required verdict:
`PASS — READY_FOR_IMPLEMENTATION`
or concrete T026-1/T026-2 contract findings.

Until that PASS: **NOT READY FOR CC**.

## 10. FINAL GATES

After preimplementation PASS:
1. CC implements only TASK_SCOPE.
2. T26 matrix + retained T018/T020/T023 regressions pass.
3. Full suite, Ruff, repository guards and `git diff --check` pass.
4. Independent Codex implementation audit runs on the exact final implementation SHA.
5. Architect reviews exact final SHA/diff and audit report.
6. Merge remains an explicit owner action.
