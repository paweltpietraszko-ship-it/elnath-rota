# ROTA-T009 — ARCHITECT CLARIFICATION R2

STATUS: PRE_IMPLEMENTATION_CONTRACT_CLARIFICATION
DATE: 2026-08-13
BASE_BRIEF_SHA: 85bc18547c78c74bcc080486ed6a27ceed15b433
R1_CLARIFICATION_SHA: 0d5fdfa31844b0932a2c23654b7b8ced8c4edc50
INTEGRATED_BASE_SHA: 81c30912bb24ed70a6cc095916fd2d3b6a2071fb

This clarification resolves only Codex R2 finding R2-1 (manual-correction atomicity).
It supersedes only the ordering in `review_01_architect_clarification.md` section `T009 MANUAL CORRECTION FLOW`.
No product semantics, solver semantics, coverage semantics, versioning rules or scope are otherwise changed.

## ATOMIC MANUAL CORRECTION FLOW

A material coordinator correction is one application action and MUST NOT expose a partially prepared child as the current ScheduleVersion.

Required order:

1. Read the current parent ScheduleVersion and its complete snapshot.
2. Require the coordinator-supplied `effective_from` (`Obowiązuje od`) for the new version.
3. Allocate the new child/version identifiers needed for the prepared snapshot.
4. In memory, clone the complete parent month snapshot into the proposed child representation.
5. In memory, apply only the requested real assignment correction(s).
6. Build a fresh PlanningState for validation from current durable Site/Profile/rules/calendar/availability/windows/balance/boundary/cross-Site facts plus the prepared in-memory child snapshot. The child does NOT need to be current or persisted in order to validate it.
7. Run the independent validator against the prepared corrected assignments, using the interval-based COVERAGE-01 semantics frozen in R1.
8. In memory, materialize the complete current Deviation set for that prepared child, including same-version ShiftDemand targets for coverage deviations as frozen in R1.
9. Only after steps 1-8 succeed, call the T008 ScheduleVersion creation lifecycle once with the complete child content: header including `effective_from`, complete ShiftDemands, corrected Assignments, applied_rule_version_ids and complete Deviations.
10. That one lifecycle transaction writes the complete child and switches `(site_id, month)` current reference to it atomically.
11. Do NOT call REPLAN automatically.

If any error occurs before the lifecycle call, persistence is unchanged.
If the lifecycle transaction fails, T008 rollback semantics leave the parent/current reference unchanged.
There is no valid intermediate state in which an incomplete child is current.

Implementation MAY add the smallest application-side helper needed to assemble/validate a PlanningState around a prepared in-memory ScheduleVersion snapshot. It MUST NOT add a workflow engine, staging database state, pending-version status, event log, second transaction protocol or new persistence subsystem.

## FOCUSED TEST

Add one focused failure-path integration test in addition to the R1 tests:

- arrange a current parent;
- prepare a material correction;
- force validation/deviation preparation to fail before ScheduleVersion creation;
- assert no child exists and current still points to the unchanged parent.

Existing T008 transaction tests continue to prove that a failure during `create_schedule_version()` itself also leaves the previous durable state/current reference intact.

## STATUS FOR CODEX

Re-review only R2-1 against the brief + R1 + this R2 clarification.
Expected result: PASS / READY_FOR_IMPLEMENTATION, or a finding that the remaining contract is still internally impossible.
Do not reopen general task design in this re-review.
