# FINDING 2026-09-03 — periodic/recurring training needs its own print
symbol ("S1"), distinct from initial/onboarding training, and must be
selectable in month planning itself, not only in print-settings config.

STATUS: finding + settled requirement shape, NOT a design doc, NOT frozen.
Architect-input material — CC does not author the implementation brief
here. Backlog memory item 6 (2026-09-01).

## Origin / requirement

Paweł, planning a month, tried to select "S" (szkolenie/training) and
could not:

> nie można w planowaniu miesiąca wybrać S... szkolenie nie jest tylko na
> początku pracy ale są też szkolenia okresowe. Możemy to rozdzielić...
> drugie szkolenie żeby nie mieszać ze szkoleniem początkowym.

Confirmed as two genuinely separate concepts, not one gap:

**1. Initial/onboarding training — existing, unchanged, not touched by
this finding.** `role=TRAINEE` Assignments (`rota/application/training.py`),
counts toward `training_s_default_readiness_threshold` → promotes an
employee to `READY_FOR_PRIMARY`. Print export already explicitly refuses
to render an effective TRAINEE assignment (`UNSUPPORTED_TRAINEE_PRINT`,
checked at `rota/application/schedule_export.py::_validate_item`). Out of
scope here.

**2. Periodic/recurring training ("S1") — new, this finding.** Paweł's
precise spec, refined over two rounds of CC asking rather than guessing:

> to ma być tylko symbol jak D1... nazwać S1... nie przypisujesz mu
> sztywnej liczby godzin tylko w rubryce Kody zmian dokładasz S1 z
> możliwością określenia godzin przez koordynatora

then, after CC asked whether the existing reserve slot "N5" could just be
renamed for this purpose:

> S1 może być z interwałem.

Final, settled shape: S1 lives in "Kody zmian" alongside D/N with its own
start/end-time-interval fields (structurally like D1/N1), but **without**
a fixed, code-enforced duration — the coordinator sets S1's start/end
freely each time, duration follows from that, no min/max enforced in code.

## Why S1 cannot reuse an existing slot (verified in code)

- `work_code_intervals` (`rota/persistence/site_repository.py`) must have
  **exactly** the keys in `WORK_CODE_KEYS` (= `FROZEN_WORK_CODE_HOURS`'s
  keys: D1-D5/N1-N5, 10 fixed keys) — `_validate_work_code_intervals`
  (lines 91-104) rejects any other key set outright, and for every
  present key it hard-enforces the interval's duration to equal that
  code's `FROZEN_WORK_CODE_HOURS` value exactly (line 98). There is no
  "no fixed duration" case anywhere in this validator today — every
  existing work code has one.
- `reserve_hours` (same file) is validated separately against
  `RESERVE_SLOT_KEYS` (U3-U5/C3-C5) — a plain hours-number, no interval
  fields at all. S1 needs interval fields (like D/N) but not a fixed
  duration (like reserve) — it fits neither existing bucket cleanly.
- Renaming/reusing "N5" specifically was checked and rejected: N5's
  interval is hard-locked to exactly 24h by the same validator, and the
  letter "N" carries real solver/validator semantics unrelated to
  training (22:00-6:00 night-differential extraction; `DAY_ONLY-01`'s
  block on N-classified demands) that would misfire if training were
  coded as "N". **S1 must be its own letter family**, not classified as D
  or N for solver/validator purposes, even though its UI shape (start/end
  time fields) now matches D/N's.

## Second, explicitly separate piece of scope

Paweł's own addition, easy to accidentally do only half of:

> [architekt] musi pamiętać by w planowaniu miesiąca S1 się pojawiło

Defining the S1 code in print-settings ("Kody zmian") and being able to
actually place S1 on a specific employee/day in month planning
(`frontend/src/screens/MonthlyPlanning.tsx`) are two different pieces of
work. A design/implementation that only adds the config-side definition
without also making S1 assignable in the planning screen itself would not
satisfy the requirement.

## Touch points (factual, not a design)

- `rota/persistence/site_repository.py` — a third settings structure
  (alongside `work_code_intervals`/`reserve_hours`) or an extension of the
  existing dataclass shape to carry S1's interval without a fixed-duration
  constraint; `_validate_work_code_intervals`'s exact-key-set and
  fixed-duration checks would need a genuinely new code path for S codes,
  not a bolt-on to the existing one (see "why it cannot reuse" above).
- Solver/validator layer — wherever `ShiftKind`/`catalog_kind`/night-
  differential extraction/`DAY_ONLY-01` reason about D/N letters
  (`rota/planning/eligibility.py`, `rota/planning/solver.py`,
  `rota/planning/shift_catalog.py`) needs to definitively NOT treat an S1
  occurrence as D or N — not investigated in detail this pass what "an S1
  occurrence" even IS at the domain level (a `ShiftDemand`? something
  else entirely, since training may not need solver coverage-matching the
  same way work does — open question below).
- `frontend/src/screens/PrintSettings.tsx` — the "Kody zmian" config
  screen, to add the S1 row with interval fields but no duration
  constraint.
- `frontend/src/screens/MonthlyPlanning.tsx` — must gain the ability to
  place S1 on a day, per Paweł's explicit addition above.
- `rota/application/schedule_export.py` — printing S1 once it exists
  (legend text, cell rendering) — not investigated this pass.

## Explicitly open, not decided here

- What IS an S1 occurrence at the domain level — a `ShiftDemand` the
  solver must cover like work (with eligibility/rest implications), or a
  simpler recorded fact that never competes with work coverage at all?
  This determines almost everything about scope and is not yet answered.
- Whether S1 interacts with REST-01/LOAD-01/NIGHT-STREAK-01 or is
  entirely outside those HARD/SOFT rules.
- Exact persistence shape (new table/columns vs. extending
  `SitePrintSettings`).
- Whether S1 has its own legend colour/fill convention on the printed
  schedule.

No brief.md/TASK_SCOPE exists for this finding. Next step is Paweł's
decision on relaying to architect Claude.
