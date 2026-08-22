# ROTA-T023 — ARCHITECT INPUT: SCHEDULE-BASED ABSENCE HOURS

STATUS: INPUT FOR A NEW ARCHITECT SESSION — NOT AN IMPLEMENTATION CONTRACT
PRIORITY: T023 before T021
BASE: `main@e05dfb7dd4463370bf8174db7ae58a9b984cf99e`

## 1. Architect deliverables

Produce, without implementation:

1. a frozen addendum superseding `arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md`;
2. `tasks/ROTA-T023/brief.md` with exact `TASK_SCOPE`, gates and test matrix;
3. an impact list for existing frozen/regression oracles requiring deliberate supersession;
4. a checkpoint order if the change cannot be safely reviewed as one implementation unit.

CC must not implement before independent Codex preimplementation PASS.

## 2. Product boundary

Rota owns:

- correct PLAN/WYK schedule facts;
- D/N/U/C presentation;
- planned, realized and absence hours for coordinator-facing weekly/monthly/quarterly totals;
- solver TARGET/fairness inputs consistent with those operational hours.

Rota does not own:

- payroll or wages;
- sickness-benefit calculations;
- leave entitlement/pool;
- HR settlement or legal advice.

Do not introduce HR/payroll features.

## 3. Binding accounting rule

Use one rule for every Site/profile/industry:

`absence_hours = hours scheduled for the employee in the adopted reference schedule during the granted absence`.

Consequences:

- ordinary 8h schedule naturally yields 8h;
- equivalent 12h/24h schedule yields its scheduled 12h/24h;
- a scheduled Saturday/Sunday/holiday counts its scheduled hours;
- a known rest day in a valid reference schedule yields 0h;
- no Mon–Fri/nonholiday filter remains in this calculation;
- no `FLAT_HOURS_PER_QUALIFIED_WORKDAY` alternative and no SiteProfile strategy toggle;
- no flat-8 fallback when a schedule exists.

The earlier direction proposing two SiteProfile-scoped strategies is rejected. Security differs in schedule shape, not in the governing absence-hours algorithm.

## 4. Reference schedule invariant

The hours source is the adopted employee schedule applicable before absence-driven replacement/replan.

- A replacement worker covering demand does not erase the absent employee's nominal PLAN U/C hours.
- Later REPLAN, restore, restart or current-pointer movement must not silently change already established absence hours.
- A readable reference schedule proving no shift means 0h.
- A missing, ambiguous or unreadable reference schedule is not a rest day: fail closed; never invent 0/8/12/24.
- The architect must define durable provenance/linkage and its atomic write/read boundary. Do not rely on CURRENT-only lookup if it loses the pre-replan fact.

Current mechanical fact: `AvailabilityRecord` and its persisted row do not carry `schedule_version_id`; `AVAILABILITY_CHANGED` action currently records `schedule_version_id=None`.

## 5. SICK / LEAVE semantics

- `SICK_LEAVE` and `LEAVE_GRANTED` use the same canonical scheduled-hour calculation.
- If live solver TARGET is absence-adjusted, both granted kinds consume that same result. TARGET remains SOFT and cannot override HARD coverage/eligibility.
- `LEAVE_PLAN` does not create actual absence hours until granted.
- On overlapping `SICK_LEAVE` and `LEAVE_GRANTED`, sickness interrupts/supersedes leave for the overlap: count once and present C, not U+C.
- Existing solver SICK-only arithmetic and T020 `ABSENCE_KIND_CONFLICT` are intentional supersession candidates, not immutable compatibility oracles.
- Solver eligibility remains correct: absent employees receive no operational Assignment. T023 must not create nominal coverage Assignments or duplicate demand coverage.

## 6. Binding owner decision — overnight anchor

For T023 accounting and U/C presentation, a shift `17:00–05:00` belongs wholly to its start date.

- Do not split at midnight.
- Absence covers it only when the inclusive absence range contains the shift start date.
- Example: `2027-03-01 17:00 → 2027-03-02 05:00`, absence starts `2027-03-02`: no U/C conversion and 0 absence hours for that shift.
- Same shift, absence includes `2027-03-01`: whole scheduled duration becomes the U/C absence amount on `2027-03-01`.
- No partial symbols for the two calendar dates.

The existing start-date presentation rule for a persisted 24h WorkPeriod must remain consistent; do not create a second date-anchor rule.

## 7. REALIZED facts

- A later or retroactive absence record must not rewrite a `REALIZED` Assignment into U/C.
- Actual worked facts remain WYK.
- An overlap between REALIZED work and later absence data is surfaced for coordinator resolution; it is not silently converted or erased.

## 8. Multi-Site semantics

- Absence accounting follows the employee's reference schedule across Sites without double counting.
- WorkBalance remains employee-global/cross-Site as frozen by EMP-03/WB-05.
- A Site PDF counts and displays only reference shifts belonging to that Site.
- A global absence with no reference shift at that Site contributes 0 absence hours to that Site's PDF.
- Do not add a per-Site accounting mode. Do not duplicate the same absence hours on every membership.

## 9. Existing model facts to verify mechanically

- `rota/planning/absence.py`: flat `EXCUSED_ABSENCE_HOURS_PER_DAY=8` and calendar-day counting.
- `rota/planning/solver.py::_sick_adjusted_targets`: SICK-only consumer.
- `rota/balance.py`: SICK+LEAVE; WorkBalance reconstructed from current assignments.
- `rota/application/schedule_export.py`: separately synthesizes U/C from flat 8h and currently rejects SICK+LEAVE overlap.
- `rota/persistence/work_balance_repository.py`: only targets are stored; computed WorkBalance rows do not exist, so no balance-row backfill is required.
- `rota/domain.py::AvailabilityRecord`: no schedule reference or recorded timestamp.
- ScheduleVersion lineage/history exists and current assignments are Site-scoped; architect must identify the smallest correct provenance surface.

Canonical ownership requirement: solver, WorkBalance/analytics and T020 export must consume one absence-hour truth. T020 may present the result but must not invent parallel eligibility or accounting semantics.

## 10. Required contract oracles

At minimum:

1. basic 8h scheduled shift -> 8h;
2. equivalent 12h D and N -> 12h;
3. persisted legal 24h WorkPeriod -> 24h once on start date;
4. valid reference rest day -> 0h;
5. scheduled weekend and scheduled holiday -> scheduled hours count;
6. N `17:00–05:00` owner examples from Section 6;
7. missing/ambiguous reference -> fail closed, never treated as known 0h;
8. absence entered after PLAN, replacement REPLAN, finalize and restart -> nominal hours unchanged;
9. restore/current-pointer movement cannot rewrite the reference;
10. cross-month and cross-year N/24h ownership without double counting;
11. SICK+LEAVE overlap -> one C result;
12. LEAVE_PLAN -> no actual absence hours;
13. REALIZED overlap -> worked fact preserved and conflict visible;
14. employee on two Sites -> employee aggregate correct, each Site export local, no duplication;
15. solver TARGET, WorkBalance/analytics and PDF consume equal canonical hours for the same reference facts;
16. absent employee never covers ShiftDemand; another operational PRIMARY must cover it;
17. current T018 HARD availability and calendar-range collision behavior remains intact unless the new addendum explicitly supersedes a named oracle;
18. old flat-8, Mon–Fri-only, SICK-only solver and PDF conflict tests are enumerated before implementation and changed only when the new contract directly supersedes them.

## 11. Official sources

- Current consolidated Polish Labour Code, Dz.U. 2025 poz. 277: art. 130 §3, art. 154² §1, art. 128 §3 pkt 1:
  https://eli.gov.pl/eli/DU/1974/141
- MRPiPS — work-time systems, schedules and settlement:
  https://www.gov.pl/web/rodzina/ustalanie-i-rozliczanie-czasu-pracy
- PIP — equivalent-system example, 12h + 4h leave = 16h; employee-workday anchor; sickness interrupts leave:
  https://www.pip.gov.pl/aktualnosci/odpoczynek-rzecz-swieta-urlopy-wypoczynkowe-od-a-do-z
- PIP — sickness reduces dimension only where work was scheduled:
  https://www.pip.gov.pl/dla-pracodawcow/pytania-i-odpowiedzi/czy-w-sytuacji-gdy-pracownik-przebywal-na-zwolnieniu-chorobowym-w-dniu-wyznaczonym-przez-pracodawce-jako-dzien-wolny-za-swieto-przypadajace-w-sobote-przysluguje-mu-inny-dzien-wolny-np-w-kolejnym-okresie-rozliczeniowym
- Supreme Court II PK 116/10 — employee workday/start of night-shift leave:
  https://www.sn.pl/sites/orzecznictwo/Orzeczenia2/II%20PK%20116-10-1.pdf
- Supreme Court I PSK 79/22 — actual work is not factual absence merely because of a later sickness certificate:
  https://www.sn.pl/sites/orzecznictwo/OrzeczeniaHTML/i%20psk%2079-22.docx.html

## 12. Required architect output status

The architect must end with exactly one status:

- `READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC`, or
- `OWNER DECISION REQUIRED`, naming only product questions not resolved above.

Do not write code. Do not silently reinstate flat 8h, weekday filtering, a per-Site mode, nominal coverage Assignments, or HR/payroll scope.
