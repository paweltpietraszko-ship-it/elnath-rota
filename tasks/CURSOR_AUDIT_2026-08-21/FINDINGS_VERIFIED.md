# Cursor cross-cutting audit — verified findings (2026-08-21)

STATUS: INPUT FOR CODEX OPINION — not a task brief, not an implementation
instruction. No fix has been made. Scope/priority/PASS-FAIL belongs to
Codex + the architect, per CLAUDE.md.

## Origin

Paweł asked Cursor to scan the repo (outside the normal Codex/architect
pipeline) for three things: (1) duplicated/redundant logic, (2) dead
ends/unreachable structure, (3) whether the solver can produce a false
result. Cursor's raw output was NOT trusted as-is — every claim below was
re-checked by CC directly against the current source (file reads + grep),
following the same "verify before reacting" discipline used for Codex
audits. Claims that did not hold up on inspection are listed separately as
rejected, with the evidence that rejects them.

Scope of the scan: `rota/planning/**`, `rota/application/**`,
`rota/persistence/**`, `rota/balance.py`, `rota/domain.py`,
`rota/constants.py`, `rota/site_memory_types.py`. Excluded: `arch/**`,
`tasks/**`, `Grafiki/**`, `tests/**`.

## CONFIRMED — real findings

### C1. `validator._check_site_rules` uses the wrong date anchor
`rota/planning/validator.py:407-408` uses `assignment.start_datetime.date()`.
`rota/planning/validator.py:220-222` (`_check_day_only`) was explicitly
fixed to use the covering demand's start date instead, per comment
"B-R11-1: COVERAGE-01 permits a spanning manual PRIMARY, so the date
anchor must be the covering ShiftDemand's start, not the Assignment's."
That fix was never applied to `_check_site_rules`, right below it in the
same file. A spanning manual PRIMARY whose own start falls on a different
weekday than the demand it covers can pass a HARD `EMPLOYEE_ALLOWED_WEEKDAYS`
/`EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` check it should fail (or vice
versa).

### C2. `validator._check_replan_preserves_fixed` omits mentor-linked PRIMARY
`rota/planning/validator.py:172`: `must_preserve = existing.state ==
REALIZED or existing.frozen or existing.role == TRAINEE`. Both
`rota/planning/solver.py:84-90` (`fixed_existing_assignments`) and
`rota/planning/replan_reshuffle.py:17-29` (`_mentor_linked_ids`, explicitly
documented as a deliberate mirror of the solver's own set) additionally
treat a PLANNED, non-frozen PRIMARY referenced by an active TRAINEE's
`mentor_primary_assignment_id` as fixed/unmovable. The independent
validator's ASSIGN-03/04 re-check does not enforce this same rule, so it
would not catch a REPLAN that moved a mentor-linked PRIMARY it should not
have moved.

### C3. `validator._check_rest` reimplements `work_periods.violates_rest` instead of calling it
`rota/planning/validator.py:487-496` inlines the overlap+gap check by hand.
`rota/planning/constraints.py` and `rota/application/manual_edit.py:56`
both correctly call `violates_rest()`. A future change to that function
(epsilon, rounding, direction) would silently not propagate to the
validator's own copy.

### C4. `timeutil.overlap_hours` truncates to whole hours — shared blind spot, not solver-vs-validator drift
`rota/planning/timeutil.py:16-19`: `int(seconds // 3600)`. Both
`constraints.add_load_constraints` (solver) and `validator._check_load`
(`validator.py:523-524`, independent re-check) call the SAME function. A
window containing several intervals each contributing a sub-hour remainder
below the 3600s boundary loses that fractional time on both sides — the
independent validator cannot catch this because it re-derives from the
same truncating primitive, not an independent one. Real actual worked
hours in a rolling 7-day window can exceed `rolling_7d_decision_threshold_hours`
by up to just under 1h per contributing interval without triggering
LOAD-01.

### C5. `required_rest_hours=0` on plain H12 demands bypasses SHIFT-24-01 entirely — needs an owner/architect ruling, not obviously a bug
`SHIFT-24-01` (`rota/planning/eligibility.py:172`) only fires when
`demand.catalog_kind == ShiftCatalogKind.H24`. Two ordinary contiguous H12
demands (opposite D/N) are never subject to it. `validate_standard_shift_shape`
(`rota/planning/shift_catalog.py:102`) only rejects `required_rest_hours < 0`,
so `== 0` is a legal StandardShift configuration. An employee with
`can_work_24h=False` on a mixed profile can be assigned two such H12
demands back-to-back (0h gap, REST-01's `gap < required_rest_after_hours`
is `0 < 0` = false) for a full 24h, without going through the emergency
same-person pairing machinery (`work_periods.check_emergency_pair_structure`)
at all, since that requires a shared `work_period_id`, which is only
assigned when the pairing mechanism actually engages. Whether this is
intended (rest=0 is a valid config choice the owner accepted) or a gap
(SHIFT-24-01 was meant to also gate two-H12 back-to-back-to-24h) is a
product question, not a code defect CC can resolve unilaterally.

### C6. `engine._decision_for_conflict` always labels the blocker `"REST-01"` regardless of actual cause
`rota/planning/engine.py:252`: `Blocker(employee_id, "REST-01")`,
unconditional, for every employee eligible for any of the conflicting
demands. The function's own docstring admits this is only "typically" a
REST-01 conflict (`engine.py:241-243`). If the real cause of the joint
infeasibility is e.g. SHIFT-24-PAIR-01 same-person forcing
(`constraints.add_same_person_24h_constraints`), the coordinator still
sees a REST-01 label and REST-01-flavored `unblocking_options`. The demand
itself is not silently dropped (it still reaches DECISION_REQUIRED), but
the stated reason can be wrong.

### C7. Seven confirmed-dead functions (grep-verified, no callers outside their own definition/`__main__`/a comment)
1. `rota/planning/solver.py:75-76` `_not_cancelled` — never called in solver.py; `fixed_existing_assignments` does its own inline filtering.
2. `rota/planning/engine_types.py:40` `ValidationResult` — no references anywhere in `rota/**`.
3. `rota/planning/shift_catalog.py:67-72` `standard_shift_for` — no callers in `rota/**`.
4. `rota/planning/site_rules.py:187` `day_only_n_exception_applies` — only mentioned in comments (`site_rules.py:23,156`), never called; live path is `day_only_n_exception_authorizing_rule_version_id`.
5. `rota/planning/timeutil.py:34-40` `rest_hours` — only used in the module's own `__main__` block.
6. `rota/persistence/site_rule_assembly.py:22-39` `assemble_site_rules` — no callers; production path is `assemble_monthly_site_rules`.
7. `IndependentValidationReport.monthly_hours` / `.minimum_rest_hours` (`validator.py:64-65`, populated at `validator.py:591-592`) — no read site found anywhere in `rota/**` outside their own definition/population.

## REJECTED — Cursor claims that did not hold up on inspection

### R1. "SHIFT-24-PAIR-01 solver (constraints.py) vs validator disagree" — false
Both `constraints.add_same_person_24h_constraints` and
`validator._check_24h_same_person` use the identical criterion (shared
`work_period_template_id`, exactly 2 distinct `demand_id`s). This is the
same rule independently re-derived on both sides (anti-drift rule 12 by
design), not divergent logic.

### R2. "manual_edit.py:60 uses the wrong component for rest resolution vs group_into_periods" — false
`earlier_a = by_synthetic_id[earlier.component_ids[-1]]` — `component_ids`
is ordered by start ascending (see `group_into_periods`,
`work_periods.py:96-103`), so `[-1]` is exactly the latest component of
that period, i.e. the same component `group_into_periods` itself uses to
resolve `required_rest_after_hours`. No mismatch.

### R3. "bootstrap._is_valid_standard_shift duplicates/conflicts with shift_catalog.validate_standard_shift_shape" — false, intentional and documented
`rota/application/bootstrap.py:59-67`'s docstring (R3-1) and
`rota/planning/shift_catalog.py:95-101`'s docstring both explicitly state
this is a deliberately narrower "is this shift usable enough to bootstrap"
readiness gate, distinct from write-time shape validation, citing
`tests/test_audit_t010_r3.py` as the owner decision record. Not a bug.

### R4. "solver.py / replan_reshuffle.py mentor-linked-id duplication is an unmanaged drift risk" — overstated
It IS a duplication (two independent computations of the same set), but it
is explicitly acknowledged in code: `replan_reshuffle.py:17-22` states
"Mirrors solver.fixed_existing_assignments's own mentor_linked_ids
computation -- duplicated (not imported)... kept in sync by
tests/test_replan_reshuffle.py's baseline/fixed partition test." This is a
known, tested tradeoff, not an unmanaged one. (The validator-side gap, C2
above, is the real, undocumented version of this problem.)

## Not yet independently verified by CC
Cursor's CHECK 3 items #6 and #7 ("solver cannot silently leave a demand
unfilled" / "no bare except swallowing violations") were reviewed and
appear correct (coverage is an exact `==` CP-SAT constraint; no bare
except found in constraint evaluation), but were not exhaustively
stress-tested against every code path.
