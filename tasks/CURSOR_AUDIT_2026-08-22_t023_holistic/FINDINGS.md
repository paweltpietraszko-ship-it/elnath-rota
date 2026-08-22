# Cursor audit — ROTA-T023 holistic (2026-08-22)

DATE: 2026-08-22
SHA: `3d2c2dc` (`origin/main`, T023 Checkpoint C reaudit recorded)
CONTRACT: `tasks/ROTA-T023/brief.md` + `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`
REQUEST: `tasks/CURSOR_AUDIT_2026-08-22_t023_holistic/REQUEST.md`

Three angles, not one narrative. No re-run of the T023/T020/T018 test matrix. No fix proposals. No PASS/FAIL.

Known Checkpoint B assembler fail-closed on `plan_month` / `select_candidate` / `replan` is not re-flagged.

---

## A. IMPLEMENTATION GAPS ACROSS CHECKPOINTS A/B/C

### A1. `plan()` still runs the T018 CalendarDay / flat-8 gate

Frozen addendum §13 / brief §18: the T018 `EXCUSED_ABSENCE_HOURS_PER_DAY` / `excused_absence_days_in_month` path may remain only as the preserved PRE_PLAN_LEAVE source (`absence.py` legacy plus T020 PRE_PLAN decomposition). POST_PLAN hours must not use CalendarDay.

`rota/planning/engine.py:29` imports `IncompleteAbsenceCalendarError` and `excused_absence_days_in_month`. `_plan` at `:76-79` calls `excused_absence_days_in_month(..., kinds=(AvailabilityKind.SICK_LEAVE,), calendar_days=state.calendar_days)` before `solve()`. `plan()` at `:62-63` maps that exception to `TECHNICAL_ERROR`.

This is not PRE_PLAN capture and not T020 decomposition. It is a live PLAN-time consumer of the retired mechanism. It still keys off SICK_LEAVE only (the pre-T023 TARGET carve-out), so a LEAVE_GRANTED-only month does not hit this gate. Assembler already requires a full `CalendarDay` month (`assembler.py` `_assemble_calendar`), so the remaining live effect is mainly conflicting holiday rows → TECHNICAL_ERROR, plus a SICK-only calendar completeness philosophy that T023 no longer uses for hours.

### A2. Checkpoint C reimplements SICK/LEAVE precedence instead of calling the canonical owner

Frozen addendum §13: `rota/planning/absence.py` is the single precedence owner; consumers must not reimplement SICK/LEAVE precedence.

`canonical_daily_hours` (`absence.py:150-171`) already collapses same-date facts with SICK winning.

`schedule_export._winning_days` (`schedule_export.py:324-333`) copies that rule over `(record, snapshot)` pairs. `_absence_pairs_for_employee` (`:380-396`) then branches on `source_mode` itself.

Same snapshot, second owner of “who wins the day”.

### A3. Checkpoint C POST_PLAN hours do not use `DayReference.hours`

Frozen addendum §4 / §13: canonical hours are the bound PRIMARY period durations; WorkBalance/solver/analytics consume `DailyAbsenceFact.hours` decoded from that field (`work_balance_repository.py:47-49`, `balance.py:99`, `solver.py:276-287`).

T020 POST_PLAN (`schedule_export.py:334-336`) ignores `day.hours` and sums `PeriodFact` intervals with `p.site_id == site_id`. PRE_PLAN (`:322-323`) does use `day.hours`.

So Checkpoint B trusts the captured `hours` field (Employee-global). Checkpoint C POST_PLAN treats that field as unused and re-derives a Site-filtered duration from `periods`. A 24h WorkPeriod captured as one grouped duration (`absence_reference_repository.py:339-354`) can still match 12+12 on one Site, but a bound PRIMARY on another Site is in `hours` and not in this PDF row. Frozen §14 allows Site from provenance for print; frozen §13 still says the same canonical result feeds T020. Those two sentences are implemented as two arithmetics.

### A4. `absence.py` module comment is stale vs merged B/C

`absence.py:123-127` still says the T023 canonical API is “Deliberately NOT wired into rota.balance / rota.planning.solver / rota.application.schedule_export yet”. After `3d2c2dc` those three consumers are wired (`balance.py:18-26`, `solver.py:276-287`, `schedule_export.py:275`). The code paths are not this comment; the comment is the contract’s own “one owner” file describing a pre-B world.

### A5. Residual CalendarDay use at PRE_PLAN capture (authorized shape, named for completeness)

`absence_reference_repository._resolve_no_accepted_plan_day` (`:310-325`) still does 8h × weekday × not-holiday via `workday_holiday_map` / `list_calendar_days`. That is the frozen PRE_PLAN source, not a stray consumer. It is the write-time twin of `excused_absence_days_in_month`, not a third runtime hours path.

No additional residual `EXCUSED_ABSENCE_HOURS_PER_DAY` / `excused_absence_days_in_month` / `IncompleteAbsenceCalendarError` call sites in `rota/` beyond `absence.py` (definition), `engine.py` (A1), `absence_reference_repository.py:238` (comment), and `balance.py:19` (supersession comment).

---

## B. LABOR-LAW COMPLIANCE FOR PRIVATE SECURITY (“ochrona”)

Product boundary (frozen addendum §1): Rota does not own payroll, benefits, leave entitlement, HR settlement or legal advice. Findings below compare what the code *encodes as legal/illegal for scheduling* against current KP text. Not a legal opinion.

Law text checked 2026-08-22: Kodeks pracy, t.j. Dz.U. 2025 poz. 277, via lexlege.pl (art. 136 dated 22.08.2026; art. 137 dated 30.06.2026). I did not open ISAP PDF page images; if those pages diverge from the t.j. citation, treat B2 as uncertain.

### B1. Daily rest: art. 132 is the default; art. 137 + 136 §2 after 24h is not enforced

`rota/constants.py:3-4` sets `REST_MIN_HOURS = 11` with an explicit “art. 132 KP” comment. `work_periods.resolve_required_rest` (`work_periods.py:29-32`) uses that only when provenance is missing. Live REST-01 uses per-period `required_rest_hours` / `required_rest_after_hours` (`constraints.py:8-16`, `validator.py` REST-01). `arch/spec.md` T012: coordinator enters `required_rest_hours >= 0`; the program enforces that number and does not derive or validate law.

Art. 132 §1 KP (current t.j.): co najmniej 11 godzin nieprzerwanego odpoczynku w każdej dobie, with the stated exceptions.

Art. 137 KP (current t.j., stan lexlege 30.06.2026): do pracowników zatrudnionych przy pilnowaniu mienia lub ochronie osób może być stosowany system równoważnego czasu pracy z przedłużeniem dobowego wymiaru **do 24 godzin**, okres rozliczeniowy nieprzekraczający 1 miesiąca; **przepisy art. 135 § 2 i 3 oraz art. 136 § 2 stosuje się odpowiednio**.

Art. 136 §2 KP (stan lexlege 22.08.2026): bezpośrednio po okresie pracy w przedłużonym dobowym wymiarze przysługuje odpoczynek przez czas odpowiadający **co najmniej liczbie przepracowanych godzin**, niezależnie od odpoczynku z art. 133.

Secondary commentary (inforlex / czas-pracy.pl) reads that “odpowiednio” for ochrona 24h as rest ≥ 24h after a 24h shift. I am not certain a court would always read art. 137 that way without the commentary; the statutory hook is the “stosuje się odpowiednio” clause itself.

Code allows a 24h catalog WorkPeriod (two 12h components, counted once) followed by `required_rest_hours=11` (T012 legacy default, `spec.md` pre-T012 line). REST-01 will pass an 11h gap after 24h work. There is no check that rest after a 24h period is ≥ 24h. `required_rest_hours=0` is also legal in-product (internal join of two H12 into one 24h period — T012 / T022), which is a different fact: rest *inside* the period, not after it.

### B2. 24h shift length vs art. 137

`FROZEN_WORK_CODE_HOURS` (`site_repository.py:39-41`) is a T020 print legend (D1=12, D2=4, D3=24, D4=2, D5=24, N1=12, N2=16, N3–N5=24), not a legality table. Planning 24h is `ShiftCatalogKind.H24` as two 12h D/N components (`shift_catalog.py` / T012).

Art. 137 (citation above) currently allows extending the daily dimension to 24h for ochrona/pilnowanie. A 24h on-site period is therefore not, by itself, outside that article. The code does not encode the 1-month (extendable) settlement period, art. 130 monthly norm, or art. 131 average 40h week. `target_hours` is a coordinator integer (`MissingTargetHoursError`, `balance.py:37-42`).

### B3. Weekly rest (art. 133) is not encoded; LOAD-01 is a different number

Art. 133 §1 KP: w każdym tygodniu co najmniej 35 godzin nieprzerwanego odpoczynku, obejmującego 11 godzin dobowego; §2 can shorten to 24h in listed cases (including shift-change). §3: that rest should fall on Sunday unless Sunday work is allowed.

No `rota/planning` symbol implements a 35h consecutive weekly rest. LOAD-01 (`validator.py:479-496`, `constraints.py`, `engine.py:374+`) is a rolling 7-day *hours-worked* window against `SiteProfile.rolling_7d_decision_threshold_hours` (example default 60 in `shift_catalog.py:275`). Exceeding it is DECISION_REQUIRED (`decision_guidance.py:29`, “Koliduje z tygodniowym czasem pracy”), not a HARD 35h rest gap. Two 24h duties with an 11h gap can satisfy REST-01 and still have no 35h weekly block.

Sunday-off-at-least-once-per-4-weeks (art. 151¹¹ / related Sunday rules — I did not re-fetch the exact numbered article in this pass) is also not encoded. `CalendarDay.holiday` affects PRE_PLAN 8h qualification (`absence_reference_repository.py:323-324`: ISO weekday ≤5 and not holiday) and does not create a Sunday-off HARD rule.

### B4. Night work

Art. 151⁷ KP (not re-opened as full text here; standard current rule): pora nocna is 8 hours chosen by the employer between 21:00 and 7:00. Code has `ShiftKind.N` and typical 17:00–05:00 N (`Grafiki/` / T012 examples). There is no encoded 8-hour night-period cap, no “pracownik pracujący w nocy” extra limits, no night-work allowance. Uncertain without the full current 151⁷–151⁸ text in front of me whether a 12h N is treated as night work for the whole interval or only the overlap with the employer’s 8h night window — the product does not model that window at all.

### B5. T023 absence hours vs L4 and urlop in KP

Brief §11 / frozen §13: SICK_LEAVE and LEAVE_GRANTED both reduce live TARGET through `max(0, target_hours - absence_hours)` (`solver.py:287`, `balance.py:99-100`). HARD exclusion of the absent employee is unchanged (`eligibility.py`).

Polish law treats them as distinct:
- choroba / L4 — remuneration/zasiłek under art. 92 KP and the zasiłek chorobowy regime (ZUS), not a reduction of a scheduling quota;
- urlop wypoczynkowy — art. 172 KP: za czas urlopu pracownik zachowuje prawo do wynagrodzenia jak za pracę.

Rota applies the same hour-quota subtraction to both and presents C vs U only in T020 letters (`schedule_export.py:339`). That matches the owner scheduling/fairness model and frozen §1 (not payroll). It does **not** match legal settlement: L4 is not “hours off the monthly norm” in KP, and urlop is paid as work, not as a smaller target. PRE_PLAN leave still uses 8h × qualified workday (`_PRE_PLAN_HOURS_PER_WORKDAY = 8`, `absence_reference_repository.py:78, 323-325`), which is the owner T018 convention, not art. 130 daily dimension (8h in basic system) applied as HR settlement.

I am not asserting a compliance verdict for a security firm’s timesheet vs ZUS. The encoding is: one fairness number, two legally different absences.

---

## C. VERTICAL INTEGRATION

Canonical write: `durable_inputs.append_availability` (`durable_inputs.py:169-210`) → `capture_and_check_in_open_transaction` (`absence_reference_repository.py:547-575`) for active SICK/LEAVE only → snapshot row. Reconstruct: `work_balance_repository.absence_facts_for_employee` (`:23-50`) → `balance.compute_month_balance` → `assembler._assemble_work_balances` (`assembler.py:138-155`) → `PlanningState.work_balances` → `solver._effective_targets` (`solver.py:276-287`) on `plan_month`/`replan` after `assemble_planning_state` (`plan_ops.py:129, 347`). Analytics: `analytics_read.py:193` via `absence_facts_for_employees`. PDF: `schedule_export._collect_absence` (`:352-378`) reads the same snapshot table, then A2/A3.

R5-3 cutover sits on `select_candidate` (`plan_ops.py:185-237, 287-300`), not on the snapshot. Bound POST_PLAN facts are not rewritten by later CURRENT movement (`_prior_bound_post_plan_facts`, `absence_reference_repository.py:287-307`).

### C1. Parallel Availability reads that skip snapshots

Application functions that load SICK/LEAVE (or all availability) as `AvailabilityRecord` and never decode `absence_reference_snapshots`:

- `assembler._assemble_windows_and_availability` (`assembler.py:92-105`) → `PlanningState.availability_records` → eligibility/validator HARD block. Intentional second channel (presence vs hours).
- `open_month` (`open_month.py:45-58`) surfaces those records beside `work_balances` (canonical hours). Two facts on one view: dates from CURRENT availability, hours from snapshots.
- `availability_matrix.employee_availability_matrix` (`availability_matrix.py:30-32, 53-60`) returns current SICK/LEAVE/UNAVAILABLE_24H records only. No `source_mode`, no `hours`, no snapshot. T021 EmployeeDetail “absence log” (`T021_spec.md` Panel per-employee, uploaded copy used in the T021 audit — not on `origin/main`) is this function, not `analytics_for_site_month`.

`analytics_for_site_month` (`analytics_read.py:171+`) is the T021 Analityka path and does use the canonical chain. `balance_read.quarter_balance` also uses reconstruct and degrades on `IncompleteAbsenceReferenceError` (`balance_read.py:13-30`).

Production write bypass: `availability_repository.append_availability_version` still exists (`availability_repository.py:81`) and does not capture. Callers in `rota/` production application code go through `durable_inputs.append_availability`. Test files still call the persistence function directly (out of REQUEST “do not re-derive” test list except as context). Not a second application entry point.

### C2. `IncompleteAbsenceReferenceError` outside PLAN — different surfaces, same assembler

Not re-stating the Checkpoint B ruling that fail-closed on `plan_month`/`replan`/`select_candidate` is required.

`IncompleteAbsenceReferenceError` is caught only in `analytics_read.py` (`:96, :114, :143`) and `balance_read.py` (`:30`). It is not caught in:

- `open_month` → `assemble_planning_state` → `_assemble_work_balances` → `reconstruct_month_balance` (`assembler.py:153`)
- `manual_edit.apply_manual_correction` (`manual_edit.py:234`)
- `lifecycle_ops.revalidate` / `finalize` (`lifecycle_ops.py:38`)

Those are coordinator-facing month/korekta/finalize paths, not the analytics degrade-to-UNAVAILABLE path. A legacy active SICK/LEAVE without a snapshot (`work_balance_repository.py:39-46`) makes Analityka show a warning row and makes Przegląd/korekta/finalize raise through assembler instead. PDF has its own `ABSENCE_REFERENCE_INCOMPLETE` (`schedule_export.py:372-374`). Three coordinator-visible behaviors for one missing snapshot.

`_carry_in_before` (`assembler.py:128`) catches `MissingTargetHoursError` only, not `IncompleteAbsenceReferenceError` from an earlier quarter month. Same exception class, earlier month, still uncaught on those screens. Not the “missing target never blocks PLAN” catch.

### C3. T021 would not show stale snapshot hours on Analityka; it would show hour-less absences on EmployeeDetail

T021 Analityka is `analytics_for_site_month` — canonical, ALL_SITES, LOCAL rows. Not stale vs WorkBalance.

T021 absence log / matrix is `employee_availability_matrix` / `append_availability` records. After a T023 write, the log has the new dates (same transaction as capture) but never the captured PRE_PLAN vs POST_PLAN hours. A coordinator comparing EmployeeDetail (ranges) with Analityka (`absence_hours` inside effective target) is looking at two projections of the same write. PDF U/C (A3) is a third, Site-filtered.

No T021 UI package is on `origin/main` (`arch/T021_spec.md` absent). Wiring is from the uploaded spec used in the 2026-08-22 UI audit.

### C4. Solver TARGET now follows WorkBalance, including LEAVE_GRANTED

`solver._effective_targets` (`solver.py:276-287`) uses `wb.absence_hours` for both kinds. The old SICK-only live TARGET carve-out is gone from solver and remains only as the engine.py calendar probe (A1). `plan_month` / `replan` reach this through `assemble_planning_state` work_balances. Chain holds for hours once assembler returns.

---

## Not reported (in scope of the request to skip)

- Assembler fail-closed blocking PLAN on incomplete reference (Checkpoint B owner/Codex ruling).
- Anything already closed by `tests/test_t023*.py`, `test_t020.py`, `test_t018.py`, `test_balance.py`, `test_t019.py`, `test_t012.py`, or `tasks/ROTA-T023/round_01/tests/*`.
- PRE_PLAN 8h/workday capture itself (frozen §2.1 / §14).
- R5-3 implementation sitting on `select_candidate` (matches frozen §10).
