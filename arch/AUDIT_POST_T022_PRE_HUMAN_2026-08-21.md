# AUDIT — po merge ROTA-T022, przed testami ręcznymi

DATE: 2026-08-21
PRODUCT_SHA: `27850f059d2bb9de35849a1c71435c5bbccf1fd4` (`main`, merge T022)
AUDITOR: Cursor (independent, no product-code changes)
VERDICT: **READY FOR HUMAN TESTS** with one non-blocking ledger gap

This audit executed the agreed pre-human sequence. Dead-code inventory is
not a gate. Travel/routing is not a product concept and was not tested.

## Official regression (pytest)

| Matrix | Result |
|---|---|
| `tests/test_t022_planning_integrity.py` | PASS (in the 153-pack below) |
| T011-E happy-path e2e | PASS |
| T018 absence workday accounting | PASS |
| T019 analytics | PASS |
| T020 PDF | PASS |
| Pack of the above | **153 passed** |
| T017 except env-bound `test_m13_*` | **26 passed** |

`tests/test_t017.py::test_m13_first_candidate_matches_pre_t017_deterministic_result`
fails on this Linux ortools `9.15.6755` **and on pre-T022 `main@d50a9aa`**.
It is not a T022 regression. Do not treat it as a human-test blocker.

## 1. T022 reaudit

In-memory reproducers on the merged SHA:

- cross-Site zero-gap, rest snapshot `0`, `can_work_24h=true` → not FEASIBLE, independent validation REST-01
- same-Site H12+H12, rest `0`, `can_work_24h=false` → not FEASIBLE
- fractional other-Site assignment → fail-closed (not rounded)

PASS.

## 2. Lifecycle + database restart

Public application path only (`store.open_store` → bootstrap → `plan_month` /
`select_candidate` / `replan` / `mark_not_worked` / `finalize` / PDF).

After each of PLAN+select, REPLAN+select, manual NN, and finalize: close the
SQLite file and reopen. `open_month`, current-version pointer, Deviation set,
and PDF `current_version_id` stayed identical. PDF remained `ExportReady`.

PASS.

## 3. Two-Site isolation

One store, SITE-A and SITE-B, disjoint extras + shared employee.

- A schedule/PDF/T019 roster does not list B-only employees (and reverse)
- SHARED work from A appears in B `other_site_assignments` (REST/LOAD facts)
- REPLAN+select on A does not move B's current version pointer

Calendar is **store-global** (`calendar_days` keyed by date, not Site). That is
existing T011-A contract, not a T022 defect. Human testers should not expect
independent per-Site holiday tables.

PASS (with that calendar note).

## 4. Manual REST-01 vs validator

Ordinary insufficient-rest pair: validator REST-01 and
`manual_edit._rest_override_pairs` see the same pair. PASS.

**FINDING PH-1 (non-blocking):** T022 zero-gap REST-01 is decided in
`validator._check_rest` (`zero-gap continuous work is not permitted` /
cross-Site abutment) **before** `gap < required_rest`.
`manual_edit._employee_violating_pairs` still uses only
`work_periods.violates_rest` (`gap < rest`). For rest snapshot `0` and gap `0`
that predicate is false, so `_rest_override_pairs` returns empty while
`validate()` reports REST-01.

Consequence: `apply_manual_correction` still materializes a REST-01
Deviation from validator details (HARD does not block the save). The extra
T012 `REST_OVERRIDE_RECORD` DecisionRecord is skipped when the pair list is
empty.

This does not reopen T022 TASK_SCOPE. It is post-merge completeness of the
manual ledger for the new REST-01 shape. Humans can still test planning and
finalize; coordinators who manually write a zero-gap REST deviation may miss
the DecisionRecord row.

## 5. Old snapshots

Write-time `create_schedule_version` rejects a fractional-minute demand
(`MalformedScheduleSnapshot`). In-memory legacy `shift_kind=None` spanning
DAY_ONLY coverage is not FEASIBLE+hard_pass.

PASS. No migration.

## 6. Absences, PDF, T019

- PLAN did not start PRIMARY work for the sick employee on sick dates
- PDF L4 (`C*` WYK family) hours for 2026-11-06..09 were in `(0, 16]` —
  weekend 7–8 Nov not converted to 8h×4
- T019 `planned_hours` (interval work, `hours_scope=ALL_SITES`) is **not**
  the same number as PDF `plan_hours` (frozen work-code table + absence
  letters on the PLAN row). Observed 216 vs 232 on this seed; the +16 matches
  two weekday L4 presentation cells at 8h. That is T019 vs T020 accounting,
  not a T022 fail.

PASS for the agreed product rules. Do not ask human testers to equate T019
planned hours with PDF plan_hours.

## 7. T017 through PDF

This seed produced ≥2 FEASIBLE candidates. Select first → REPLAN on that
version → select → close/reopen. Current pointer, PDF version, and persisted
PRIMARY signature were the selected lineage, not the rejected candidate.

PASS.

## 8. T013 (proven-false REST-01 only)

Probe: two consecutive H12, rest `0`, `can_work_24h=false`.

- `plan()` → `DECISION_REQUIRED`
- coordinator-facing blocker: `Koliduje z odpoczynkiem dobowym` (T013 wording)
- independent validate of both placements: REST-01 `zero-gap continuous work is not permitted`

Gap is 0 and configured rest is 0, so classic `gap < rest` is false, but the
frozen OWNER-T022-02/03 rule **names that shape REST-01**. The label is not a
proven false REST-01 (rest is not “innocent”; the new zero-gap rule is the
cause and is coded REST-01).

No T013 finding filed.

## Human-test notes

1. One SQLite calendar for all Sites.
2. PDF hours ≠ T019 planned hours.
3. T017 `m13` CP-SAT signature is environment-sensitive.
4. If a coordinator manually creates zero-gap REST, check whether
   `REST_OVERRIDE_RECORD` appears (PH-1).

## Out of gate

Dead helpers / `_check_rest` vs `violates_rest` duplication (C3): register
only. PH-1 is the live instance of that duplication on the new zero-gap
predicate.
