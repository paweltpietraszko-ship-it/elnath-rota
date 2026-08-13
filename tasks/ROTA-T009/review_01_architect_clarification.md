# ROTA-T009 — ARCHITECT CLARIFICATION R1

STATUS: PRE_IMPLEMENTATION_CONTRACT_CLARIFICATION
DATE: 2026-08-13
BASE_BRIEF_SHA: 85bc18547c78c74bcc080486ed6a27ceed15b433
INTEGRATED_BASE_SHA: 81c30912bb24ed70a6cc095916fd2d3b6a2071fb

This clarification resolves Codex R1 findings about manual split coverage and coverage-gap provenance, and freezes the owner's real operational requirements supplied after that audit.

It supersedes only conflicting T009 brief clauses below. The rest of `tasks/ROTA-T009/brief.md` remains unchanged.

## OWNER REAL-WORLD CASE

A scheduled D 05:00-17:00 employee did not arrive.

Actual work was covered by:
- P: 05:00-13:00 after staying beyond the preceding night shift;
- B: starting at 13:00, four hours before B's scheduled N 17:00-05:00, then continuing through that night.

The product must let the coordinator record the real state without replanning the whole month.

The monthly schedule cell may later be presented by T012 compactly as `P/B`, with detail/history available on hover or inspection. Exact UI rendering remains T012 scope.

These extra worked hours are actual worked hours. Rota MUST NOT automatically label them "overtime". WorkBalance continues to compare actual/planned hours with target_hours; an employee may still have a negative balance after such additional work.

## OWNER VERSIONING RULE

Every material change to who is assigned to a day/night, or to the actual work interval used to represent that assignment, creates a NEW ScheduleVersion child.

The previous version remains immutable history and the changed child becomes current.

Changing the schedule field `Obowiązuje od` also creates a new ScheduleVersion child.

Pure presentation/cosmetic changes such as legend/layout/colour changes do NOT create ScheduleVersion history. They belong to the future presentation layer, not T009 schedule state.

T009 therefore MUST NOT use T008 in-place working-snapshot replacement for a coordinator material assignment correction. The application command creates a child and applies the correction to that child as one application action. T008's in-place primitive may remain available internally for lifecycle operations that do not violate this owner rule.

REPLAN keeps its already accepted parent -> new WORKING child semantics.

## SCHEDULEVERSION DATES

Every ScheduleVersion already has system `created_at`; it remains automatic provenance and MUST NOT be coordinator-edited.

Add one schedule-version field:

- `effective_from: date` — coordinator-facing label: `Obowiązuje od`.

Rules:
- coordinator enters `effective_from` manually when a new schedule version is created;
- Rota MUST NOT derive it from `created_at`, month, current date or the changed assignment date;
- changing `effective_from` means creating another child version, not rewriting historical metadata;
- parent/child + created_at/created_by + effective_from are sufficient T009 provenance for later UI to explain that a cell changed; do not add a second cell-history/audit subsystem.

T009 may add the smallest LocalStore/domain migration needed to persist this one field. Existing pre-T009 rows must not be assigned a guessed historical `effective_from`; migration may preserve it as unknown/NULL for legacy rows, while every newly created T009 version requires the coordinator-supplied value.

## COVERAGE — REAL INTERVALS ARE AUTHORITATIVE

Codex R1 correctly found that the accepted validator currently counts PRIMARY records per `covers_demand_id`. That is insufficient for the owner's real case.

For coverage validation, use actual PRIMARY work intervals.

For each ShiftDemand interval, validator must evaluate the overlapping PRIMARY intervals geometrically over `[start_datetime, end_datetime)`:
- every instant of the demand must have exactly `required_primary_count` PRIMARY coverage;
- a gap is COVERAGE-01;
- coverage above required_primary_count is COVERAGE-01;
- sequential pieces are valid when their union covers the demand exactly with the required multiplicity.

Therefore for required_primary_count=1:
- P 05:00-13:00 + B 13:00-17:00 = valid complete D coverage;
- P 05:00-17:00 + B 05:00-17:00 = excess coverage;
- P 05:00-13:00 only = uncovered 13:00-17:00 gap.

Coverage calculation MUST use actual PRIMARY interval overlap, not merely the count of assignments whose `covers_demand_id` equals the demand.

This is a narrow correction to independent coverage validation. It does NOT change PlanningEngine's standard D/N generation, solver objective, T006 reshuffle priority, HARD/SOFT policy, or introduce another solver.

`Assignment.start_datetime/end_datetime` remain the authoritative actual work interval. A manually corrected PRIMARY may extend across more than one standard demand; coverage is derived from its actual interval. This permits B's truthful continuous 13:00-05:00 work interval to contribute to the end of D and to N without inventing two fake work periods merely for accounting.

## COVERAGE GAP DEVIATION TARGET

Codex R1 also correctly found that an empty coverage gap has no truthful Employee/Assignment target.

A coverage violation about a demand must be able to target that ShiftDemand.

Use the smallest durable extension to Deviation necessary to represent this truth. Required semantic result:
- COVERAGE-01 gap/excess may reference the exact same-version `demand_id` as its affected target;
- do NOT invent an employee as responsible when no employee assignment exists;
- source_reference remains the stable built-in `COVERAGE-01`;
- category remains `DeviationCategory.COVERAGE`.

Implementation may extend the existing affected-target representation rather than invent a separate deviation subsystem. The representation must be unambiguous and persistence-validated against the same ScheduleVersion.

## T009 MANUAL CORRECTION FLOW

For a material coordinator correction:

1. read current ScheduleVersion;
2. require coordinator-supplied `Obowiązuje od` for the new version;
3. create one complete child snapshot;
4. apply only the requested real assignment change(s) to the child;
5. make child current; parent remains history;
6. run the existing independent validator with the corrected interval-based COVERAGE-01 logic;
7. materialize any real Deviations;
8. do NOT call REPLAN automatically.

The rest of the month is copied unchanged. This operation is not a month-wide reschedule.

## TESTS REQUIRED BY THIS CLARIFICATION

Add focused tests only:

1. D 05:00-17:00 split P 05:00-13:00 + B 13:00-17:00 is complete coverage.
2. P 05:00-13:00 alone reports the exact uncovered demand interval as COVERAGE-01.
3. Two full PRIMARY 05:00-17:00 assignments report excess coverage.
4. A truthful B 13:00-05:00 PRIMARY interval can contribute coverage to the tail of D and the following N through actual overlap; its worked hours are not double-counted.
5. Material assignment correction creates one child, leaves parent readable/unchanged, and child becomes current.
6. New child stores automatic created_at and coordinator-entered effective_from; system does not derive effective_from.
7. Changing effective_from creates another child rather than editing history.
8. Coverage-gap Deviation points to the exact ShiftDemand, not an invented Employee.

No new test framework, solver, workflow engine, event log, or cell-audit subsystem is authorized.

## STATUS FOR CODEX

Audit `brief.md` together with this clarification. R1-1 and R1-2 are resolved by owner-backed product semantics rather than by removing real operational functionality.
