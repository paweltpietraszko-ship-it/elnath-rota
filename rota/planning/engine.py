"""PlanningEngine.plan(): orchestrate solver + independent validator into a PlanningResult.

Status mapping (arch/spec.md SECTION 3, Frozen Execution Contract v0.4 §6):
- CP-SAT finds a full-coverage solution within the LOAD-01 threshold and the
  independent validator confirms HARD PASS -> FEASIBLE.
- No eligible employee exists for some demand, coverage is only reachable by
  exceeding the LOAD-01 threshold, or a minimal set of demands is jointly
  unsatisfiable (e.g. REST-01 conflict between two demands for the only
  eligible employee) -> DECISION_REQUIRED with the relevant blockers.
- CP-SAT reports OPTIMAL/FEASIBLE but the independent validator finds a HARD
  violation anyway -> this is a solver/mapping bug (anti-drift rule 12), not
  a product outcome, and is reported as TECHNICAL_ERROR rather than silently
  claimed FEASIBLE.
- Any other unresolved CP-SAT status (e.g. UNKNOWN after the time limit) with
  no identifiable staffing or HARD-conflict cause -> TECHNICAL_ERROR. Audit
  round 12 (tests_r12.txt FINDING 3) found that ordinary REST-01 conflicts
  were falling into this branch; solver.solve() now diagnoses the minimal
  conflicting demand set via CP-SAT assumptions so those cases route to
  DECISION_REQUIRED instead.

Known scope limit of this experiment: DecisionRequiredPayload.load_blocker is
a single field (arch/spec.md SECTION 3), so when several employees exceed the
LOAD-01 threshold only the worst offender is reported there; the rest are
still listed in `blockers`, and this is called out in `warnings`, not hidden.
"""
from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime

from rota.domain import Assignment, AssignmentState
from rota.planning.decision_guidance import build_decision_payload
from rota.planning.state import PlanningState
from rota.planning.engine_types import (
    BlockingDemand,
    Blocker,
    LoadBlocker,
    PlanningResult,
)
from rota.planning.replan_reshuffle import redistributable_baseline_assignments
from rota.planning.shift_catalog import UnclassifiedShiftError
from rota.planning.site_rules import UnsupportedOrMalformedSiteRule, validate_executable_site_rules
from rota.planning.solver import (
    PLANNING_OPERATION_BUDGET_SECONDS, REPLAN_SEARCH_BUDGET_SECONDS, SolverOutcome, eligible_employees_for_demands,
    fixed_existing_assignments, solve,
)
from rota.planning.timeutil import intervals_overlap
from rota.planning.validator import IndependentValidationReport, ViolationDetail, validate


def _with_model_error_boundary(fn, *args, **kwargs) -> PlanningResult:
    """The one public model-error boundary every public entry point
    (plan(), plan_requiring_different_result_narrow/_wide) shares.

    FINDING R17-3: UnclassifiedShiftError is a genuine model error
    (arch/spec.md:503-507) -- a ShiftDemand that matches no StandardShift in
    the profile -- and must be mapped to TECHNICAL_ERROR at this public
    boundary, not left to propagate to the caller. ROTA-T007:
    UnsupportedOrMalformedSiteRule (a RESOLVED rule that claims to be
    executable but isn't) is the same class of model error.

    ROTA-T033 audit finding R1-3 (2026-08-26): REPLAN's own entry points
    used to call _plan()/solve() directly, bypassing this boundary entirely
    -- the same model error that plan() maps to a structured TECHNICAL_ERROR
    would surface from REPLAN as a raw exception (an HTTP 500, not
    PlanningResultOut). One shared boundary function, not a copy of this
    except-list pasted into each new entry point."""
    try:
        return fn(*args, **kwargs)
    except UnclassifiedShiftError as exc:
        return PlanningResult("TECHNICAL_ERROR", [], None, f"model error: {exc}", [])
    except UnsupportedOrMalformedSiteRule as exc:
        return PlanningResult("TECHNICAL_ERROR", [], None, f"site rule error: {exc}", [])


def plan(state: PlanningState, search_attempt: int = 0) -> PlanningResult:
    """Produce a PlanningResult for one PlanningState.

    plan() has exactly three output statuses (arch/spec.md:339-342); a raw
    exception is never one of them -- see _with_model_error_boundary.

    ROTA-T032 section 6.1: this is the ONE public entry point that creates
    the shared planning-operation deadline (PLANNING_OPERATION_BUDGET_SECONDS,
    a time.monotonic() absolute instant) -- every internal solve() call below, across every retry stage,
    gets only the time remaining to this same deadline, never a fresh
    per-stage allowance. section 7.2: search_attempt only varies CP-SAT
    search seed/order for "Szukaj dalej" retries, never the model.
    """
    deadline = time.monotonic() + PLANNING_OPERATION_BUDGET_SECONDS
    return _with_model_error_boundary(_plan, state, deadline, search_attempt)


def _plan(
    state: PlanningState, deadline: float | None = None, search_attempt: int = 0, search_variants: bool = True,
    quality_required: bool = True,
) -> PlanningResult:
    # ROTA-T007: prevalidate before solve() -- a RESOLVED HARD/SOFT SiteRule
    # that cannot be executed must never be silently ignored just to reach
    # FEASIBLE (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md point 8).
    validate_executable_site_rules(state.site_rules)
    # T018 B6/DAY-ONLY-N-FALLBACK-01: literal 4-stage retry order (see
    # module docstring). A capped stage's candidate is always terminal;
    # only a proven INFEASIBLE or a pre-model coverage shortage advances to
    # the next stage -- COMPLETE-GRAPH FAILURE INCLUDES PRE-MODEL SHORTAGE:
    # normal `unassignable` must not end the plan early while a further
    # fallback stage remains, so stages 1-2 never dispatch it (round 14
    # audit); only stage 3 finally treats it as the terminal shortage, since
    # no uncapped solve can repair a missing eligible slot.
    #
    # ROTA-T033 (Codex audit finding, UNAUTHORIZED, 2026-08-26): deadline is
    # None for ordinary plan()/PLAN -- unaffected, original fixed per-call
    # budget. plan_requiring_different_result_narrow passes its OWN 45s
    # REPLAN_SEARCH_BUDGET_SECONDS deadline here too, so this baseline check
    # and the diversity solve that follows it share ONE budget, never
    # baseline-unbounded-time-plus-45s.
    for allow_day_only_n_fallback, allow_emergency_24h in ((False, False), (True, False)):
        outcome = solve(
            state, enforce_load_cap=True, allow_day_only_n_fallback=allow_day_only_n_fallback,
            allow_emergency_24h=allow_emergency_24h, deadline=deadline, search_attempt=search_attempt,
            search_variants=search_variants, quality_required=quality_required,
        )
        result = _dispatch_or_continue(state, outcome)
        if result is not None:
            return result

    outcome_3 = solve(
        state, enforce_load_cap=True, allow_day_only_n_fallback=True, allow_emergency_24h=True,
        deadline=deadline, search_attempt=search_attempt, search_variants=search_variants,
        quality_required=quality_required,
    )
    result = _dispatch_stage3(state, outcome_3)
    if result is not None:
        return result
    # INFEASIBLE with the LOAD-01 cap enabled is not evidence of a REST-01
    # conflict by itself (round 13 FINDING R13-1) -- drop the cap before
    # treating this as a genuine cross-demand conflict, both fallbacks still
    # ON (part_c_emergency_24h.md section 9 point 9: same boundary context).
    return _resolve_without_load_cap(
        state, deadline, search_attempt, allow_emergency_24h=True, allow_day_only_n_fallback=True,
    )


def _dispatch_or_continue(state: PlanningState, outcome: SolverOutcome) -> PlanningResult | None:
    """Stage 1/2 only: a found candidate is always terminal (delegated to
    _evaluate_candidate's own FEASIBLE/conflict/load disposition). A proven
    INFEASIBLE or a pre-model coverage shortage (NO_ELIGIBLE_EMPLOYEE) means
    None -- the caller must still try the next fallback stage. Any other
    status (UNKNOWN/MODEL_INVALID) is a genuine technical failure, never
    masked by a further retry (round 14 audit tests_r14.txt FINDING R14-2).
    ROTA-T032 section 6.3: a technical failure caused by the shared deadline
    running out with no candidate proven anywhere carries
    optimization_complete=False through to the final PlanningResult."""
    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)
    if outcome.unassignable_demand_ids or outcome.status_name == "INFEASIBLE":
        return None
    return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {outcome.status_name}", [], outcome.optimization_complete)


def _dispatch_stage3(state: PlanningState, outcome: SolverOutcome) -> PlanningResult | None:
    """Stage 3 only: unlike stages 1/2, an unassignable shortage here IS
    terminal (no uncapped solve can repair a missing eligible slot). None
    means a proven INFEASIBLE -- the caller must still try Stage 4."""
    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)
    if outcome.unassignable_demand_ids:
        return _decision_for_unassignable(state, outcome)
    if outcome.status_name != "INFEASIBLE":
        return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {outcome.status_name}", [], outcome.optimization_complete)
    return None


def _resolve_without_load_cap(
    state: PlanningState, deadline: float | None = None, search_attempt: int = 0,
    allow_emergency_24h: bool = False, allow_day_only_n_fallback: bool = False,
) -> PlanningResult:
    fallback = solve(
        state, enforce_load_cap=False, allow_emergency_24h=allow_emergency_24h,
        allow_day_only_n_fallback=allow_day_only_n_fallback, deadline=deadline, search_attempt=search_attempt,
    )
    if fallback.unassignable_demand_ids:
        return _decision_for_unassignable(state, fallback)
    if fallback.assignments is not None:
        return _decision_for_load(state, fallback)
    if fallback.night_streak_conflicts:
        return _decision_for_night_streak(state, fallback)
    if fallback.conflicting_demand_ids:
        return _decision_for_conflict(state, fallback)
    return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {fallback.status_name}", [], fallback.optimization_complete)


def _full_assignments(state: PlanningState, solved: list[Assignment]) -> list[Assignment]:
    """REPLAN: only REALIZED/frozen/TRAINEE existing Assignments are fixed
    facts (rota.planning.solver.fixed_existing_assignments); a redistributable
    PRIMARY is intentionally NOT included here even though it is still in
    state.existing_assignments -- solve() already excluded it from coverage
    counting, so the demand it used to cover is re-solved into `solved`
    instead. Including both would double-count that demand's coverage."""
    return fixed_existing_assignments(state) + list(solved)


def _evaluate_candidate(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    full = _full_assignments(state, outcome.assignments)
    report = validate(state, full)
    if report.hard_pass:
        return _feasible_result(
            state, full, list(outcome.warnings) + list(report.warnings), outcome.alternatives, outcome.optimization_complete,
        )
    if _has_non_load_violations(report):
        return _decision_for_conflicts(state, full, report, list(outcome.warnings))
    # FINDING R17-1: a demand already fully covered by existing_assignments
    # never gets a SolverSlot, so the LOAD-01 cap constraint is never added
    # for that employee even though the capped solve reports OPTIMAL. A
    # LOAD-01-only violation surfacing here is a genuine boundary, not a
    # solver/mapping bug, and must not become TECHNICAL_ERROR.
    return _load_decision(state, report, list(outcome.warnings), full, outcome.site_rule_exclusions)


def _feasible_result(
    state: PlanningState, first_full: list[Assignment], first_warnings: list[str],
    alternatives: list[tuple[list[Assignment], list[str]]], optimization_complete: bool = True,
) -> PlanningResult:
    """T017: a single candidate keeps the exact legacy unprefixed warning
    shape. 2-3 candidates each get independently HARD-validated; any
    additional candidate failing validation fails the WHOLE result closed
    (anti-drift rule 12, brief.md H2) -- never a silent partial success.
    ROTA-T032 section 6.4: optimization_complete carries through unchanged
    from the solver outcome that produced first_full/alternatives in EVERY
    branch below, including the multi-candidate one -- audit R7-1
    (tests_r7.txt, 2026-08-25): the shared deadline can now run out while
    searching for a THIRD variant after already finding a second one, which
    keeps both candidates (solver.py) but must still mark the result
    incomplete; `alternatives` non-empty no longer implies True."""
    if not alternatives:
        return PlanningResult("FEASIBLE", [first_full], None, None, first_warnings, optimization_complete)
    candidates = [first_full]
    per_candidate_warnings = [first_warnings]
    for solved, solver_warnings in alternatives:
        full = _full_assignments(state, solved)
        report = validate(state, full)
        if not report.hard_pass:
            return PlanningResult(
                "TECHNICAL_ERROR", [], None,
                "independent validator rejected an additional T017 variant candidate", [],
            )
        candidates.append(full)
        per_candidate_warnings.append(list(solver_warnings) + list(report.warnings))
    warnings = [
        f"candidate={index} | {warning}"
        for index, candidate_warnings in enumerate(per_candidate_warnings, start=1)
        for warning in candidate_warnings
    ]
    return PlanningResult("FEASIBLE", candidates, None, None, warnings, optimization_complete)


def _is_timeout_technical_error(result: PlanningResult) -> bool:
    """ROTA-T033 audit finding R1-2 (2026-08-26): _plan()'s own dispatch
    (_dispatch_or_continue/_dispatch_stage3/_resolve_without_load_cap) maps
    ANY non-INFEASIBLE, non-assignments solver status -- including UNKNOWN,
    a plain shared-deadline timeout, not a real failure -- to a generic
    TECHNICAL_ERROR carrying f"solver status: {status_name}". That is the
    right call for ordinary PLAN (no SEARCH_INCOMPLETE concept exists
    there), but REPLAN's own baseline check shares the SAME deadline as its
    diversity search, so a timeout can just as easily land here as in the
    diversity solve -- and must get the identical, retryable
    SEARCH_INCOMPLETE treatment, never TECHNICAL_ERROR. MODEL_INVALID and
    every other genuine failure still doesn't match this string and stays a
    real TECHNICAL_ERROR."""
    return result.status == "TECHNICAL_ERROR" and result.error_message is not None and "UNKNOWN" in result.error_message


def _already_differs_from_baseline(state: PlanningState, candidate: list[Assignment]) -> bool:
    """Integration audit finding INT-R3-1 (2026-08-26, round 3): the baseline
    check's own _plan() call can already produce a genuinely different
    schedule -- e.g. the baseline was empty/partial (a prior DECISION_REQUIRED
    that a newly-declared external support window just resolved), so ANY
    full candidate is trivially different from it. Reuses
    replan_reshuffle.redistributable_baseline_assignments (the exact same
    predicate solve()'s own diversity constraint is built from) against a
    stand-in state whose existing_assignments is the candidate itself, so
    this never drifts from the solver's own definition of "the pairs that
    count"."""
    baseline_pairs = {(a.employee_id, a.covers_demand_id) for a in redistributable_baseline_assignments(state)}
    candidate_state = replace(state, existing_assignments=tuple(candidate))
    candidate_pairs = {(a.employee_id, a.covers_demand_id) for a in redistributable_baseline_assignments(candidate_state)}
    return candidate_pairs != baseline_pairs


def plan_requiring_different_result_narrow(
    state: PlanningState, cutover_at: datetime, search_attempt: int = 0,
    prior_variant_signatures: tuple[frozenset[tuple[str, str]], ...] = (),
) -> PlanningResult:
    return _with_model_error_boundary(
        _plan_requiring_different_result_narrow, state, cutover_at, search_attempt, prior_variant_signatures,
    )


def _plan_requiring_different_result_narrow(
    state: PlanningState, cutover_at: datetime, search_attempt: int = 0,
    prior_variant_signatures: tuple[frozenset[tuple[str, str]], ...] = (),
) -> PlanningResult:
    """Owner decision 2026-08-26, then OWNER_CORRECTED same day after a Codex
    audit question: REPLAN, by definition, must never hand the coordinator
    back the schedule they already have. This is step 1 ("wąskie
    wyszukiwanie") of the agreed two-step flow: ordinary rules only, no
    fallback exceptions, budgeted at REPLAN_SEARCH_BUDGET_SECONDS. Used only
    by plan_ops.replan(), now offered alongside "Przelicz (PLAN)" even
    before finalize (not gated behind isFinal on the frontend), so a
    coordinator can choose either a minimal recompute (PLAN, unaffected by
    this function -- keeps the original protective minimize-reshuffle
    behavior, e.g. for a newly reported L4) or a genuinely different
    alternative (REPLAN) at the same point in the flow.

    The caller cannot assume the state's existing content is actually
    coverage-valid -- nothing stops REPLAN from being invoked (directly via
    the API, if not through the gated frontend) on a version whose content
    never solved cleanly. That must still get the full existing diagnosis
    (DECISION_REQUIRED/TECHNICAL_ERROR), not a diversity verdict about a
    schedule that never validly existed in the first place. So this runs
    _plan()'s ordinary, unmodified diagnosis FIRST; only once that confirms
    a real FEASIBLE baseline does a second, diversity-only solve ask the
    actual new question.

    Codex audit finding (UNAUTHORIZED, 2026-08-26): the baseline check and
    the diversity solve MUST share ONE REPLAN_SEARCH_BUDGET_SECONDS budget,
    not the baseline check running unbounded and then a fresh 45s starting
    only for the diversity search -- a coordinator could otherwise wait far
    longer than the agreed budget for one click. Both calls below share the
    same `deadline` for exactly this reason.

    Four outcomes, per the agreed contract -- "nie wolno pisać 'nie istnieje
    inny grafik' po samym kroku 1" (never claim no-alternative from step 1
    alone; only a step-2 proof earns that):
    - FEASIBLE: a genuinely different HARD-valid schedule exists, here it is.
    - DECISION_REQUIRED / TECHNICAL_ERROR: the baseline itself never solved
      cleanly (see above) -- unrelated to diversity, passed through as-is.
    - NARROW_SEARCH_EXHAUSTED: PROVEN (CP-SAT INFEASIBLE, not a guess) that
      no different schedule exists under ordinary rules alone. The
      coordinator is offered a choice: keep the current schedule, or widen
      the search to exceptions (plan_requiring_different_result_wide).
    - SEARCH_INCOMPLETE: the budget ran out before proving anything either
      way -- an unproven "maybe", never reported as NARROW_SEARCH_EXHAUSTED
      or NO_ALTERNATIVE.

    cutover_at mirrors plan_ops._enforce_replan_cutover's own "now" (same
    invariant: an already-past PRIMARY Assignment is never moved) -- the
    caller computes it once, at the same point in its own flow, so the
    solver never even considers a placement select_candidate would reject
    later on cutover grounds alone.

    OWNER_CORRECTED 2026-09-08: this baseline check only ever looks at
    baseline_check.candidates[0] (_already_differs_from_baseline) when it
    ends up FEASIBLE. T017's own up-to-2-additional-candidate search has no
    purpose here and, on a large enough state, can burn nearly the entire
    shared REPLAN_SEARCH_BUDGET_SECONDS budget on two candidates that are
    never inspected either way (search_variants=False, safe unconditionally).

    CODEX AUDIT FAIL 2026-09-08 (round 1, exact SHA 6cba91e): the earlier
    version of this docstring also claimed baseline_check's FEASIBLE content
    is "discarded outright" and applied quality_required=False
    unconditionally on that basis -- false. When prior_variant_signatures is
    empty (a podejscie's very first REPLAN call) and the baseline already
    differs from the pre-REPLAN state, the early return a few lines below
    hands baseline_check itself back to the coordinator as the shown
    result -- quality_required=False there let REPLAN stop at the first
    HARD-valid schedule instead of the normal quality bar, a real,
    reproduced regression (repro: first REPLAN on a fresh state returned
    36/168/180/180/180h instead of PLAN's own 144/144/144/156/156h on an
    otherwise identical state). quality_required is only safe to relax when
    prior_variant_signatures is non-empty: only then is the early-return
    branch below (gated on `not prior_variant_signatures`) provably
    unreachable, so baseline_check is guaranteed discarded and the
    SOLVER_RELATIVE_GAP_LIMIT non-convergence budget fix (owner finding
    2026-09-08) can still apply safely."""
    deadline = time.monotonic() + REPLAN_SEARCH_BUDGET_SECONDS
    baseline_check = _plan(
        state, deadline, search_attempt, search_variants=False,
        quality_required=not prior_variant_signatures,
    )
    if baseline_check.status != "FEASIBLE":
        if _is_timeout_technical_error(baseline_check):
            return PlanningResult("SEARCH_INCOMPLETE", [], None, None, [], optimization_complete=False)
        return baseline_check
    # T57-04 (architect FAIL 2026-09-07): this shortcut's baseline is always
    # empty pre-acceptance (nothing accepted yet), so "differs from it" was
    # trivially true for any non-empty candidate and this fired on every
    # call once REPLAN became pre-acceptance-only -- silently skipping the
    # dedicated diversity solve below, and with it the only place that can
    # ever enforce >=15% against this podejscie's stored history. Only take
    # the shortcut when there is no history yet to enforce against (the
    # podejscie's very first REPLAN call).
    if not prior_variant_signatures and _already_differs_from_baseline(state, baseline_check.candidates[0]):
        # INT-R3-1: the baseline check's own candidate already satisfies
        # "must differ" (e.g. baseline was empty/partial) -- a second,
        # diversity-only solve would be redundant and, on timeout, would
        # wrongly discard this already-valid, already-different candidate.
        # optimization_complete is forced False: the normal REPLAN diversity
        # pass (which could still have found an even better arrangement) was
        # deliberately skipped, not proven unnecessary.
        return replace(baseline_check, optimization_complete=False)
    # OWNER_CORRECTED 2026-09-08: same reasoning as the baseline check above
    # -- T017's up-to-2-additional-candidate search is never required by
    # T057's own REPLAN contract (each "kolejny wariant" is its own REPLAN
    # call, see execution_e2.md) and, combined with the new
    # prior_variant_signatures HARD constraints (T57-04), made this solve
    # itself burn most of the shared budget hunting for extra candidates
    # nobody asked for on a large state. search_variants=False here trades
    # "up to 3 candidates from one click" (never exercised or required) for
    # "reliably returns its one candidate within budget."
    outcome = solve(
        state, enforce_load_cap=True, require_different_from_baseline=True, cutover_at=cutover_at, deadline=deadline,
        search_attempt=search_attempt, prior_variant_signatures=prior_variant_signatures, search_variants=False,
    )
    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)
    if outcome.status_name == "INFEASIBLE":
        return PlanningResult("NARROW_SEARCH_EXHAUSTED", [], None, None, [])
    if outcome.status_name == "UNKNOWN":
        return PlanningResult("SEARCH_INCOMPLETE", [], None, None, [], optimization_complete=False)
    return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {outcome.status_name}", [])


def _wide_try_diversity_at_stage(
    state: PlanningState, cutover_at: datetime, deadline: float, *,
    enforce_load_cap: bool, allow_day_only_n_fallback: bool, allow_emergency_24h: bool, search_attempt: int = 0,
    prior_variant_signatures: tuple[frozenset[tuple[str, str]], ...] = (),
) -> PlanningResult | None:
    """Only called once the ORDINARY (non-diversity) solve at these exact
    stage flags already came back cleanly FEASIBLE (see
    plan_requiring_different_result_wide) -- so any INFEASIBLE here is
    provably attributable to the diversity requirement alone at THIS
    permissiveness level (coverage/rest are already known solvable without
    it), never a real conflict. Returns None to mean "not diverse at this
    stage, try the next one".

    OWNER_CORRECTED 2026-09-08: search_variants=False for the same reason
    as the narrow search's own diversity solve -- never required, and
    burns shared budget on discarded extra candidates (see engine._plan
    /solve()'s search_variants docstring)."""
    outcome = solve(
        state, enforce_load_cap=enforce_load_cap, allow_day_only_n_fallback=allow_day_only_n_fallback,
        allow_emergency_24h=allow_emergency_24h, require_different_from_baseline=True, cutover_at=cutover_at,
        deadline=deadline, search_attempt=search_attempt, prior_variant_signatures=prior_variant_signatures,
        search_variants=False,
    )
    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)
    if outcome.status_name == "INFEASIBLE":
        return None
    if outcome.status_name == "UNKNOWN":
        return PlanningResult("SEARCH_INCOMPLETE", [], None, None, [], optimization_complete=False)
    return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {outcome.status_name}", [])


def plan_requiring_different_result_wide(
    state: PlanningState, cutover_at: datetime, search_attempt: int = 0,
    prior_variant_signatures: tuple[frozenset[tuple[str, str]], ...] = (),
) -> PlanningResult:
    return _with_model_error_boundary(
        _plan_requiring_different_result_wide, state, cutover_at, search_attempt, prior_variant_signatures,
    )


def _plan_requiring_different_result_wide(
    state: PlanningState, cutover_at: datetime, search_attempt: int = 0,
    prior_variant_signatures: tuple[frozenset[tuple[str, str]], ...] = (),
) -> PlanningResult:
    """Step 2 ("Szukaj szerzej") of the agreed two-step REPLAN flow -- called
    only after plan_requiring_different_result_narrow returns
    NARROW_SEARCH_EXHAUSTED and the coordinator explicitly chooses to widen
    the search, never automatically. Reuses _plan()'s exact 4-stage
    fallback ladder (day-only-N exception, emergency 24h, dropping the
    LOAD-01 cap) for its ORDINARY (non-diversity) dispatch, unchanged --
    exactly _dispatch_or_continue/_dispatch_stage3/_resolve_without_load_cap's
    own logic, so a genuine coverage/rest conflict is diagnosed exactly like
    ordinary PLAN would, completely independent of diversity.

    Only once a stage's ORDINARY solve comes back cleanly FEASIBLE does this
    ask the actual new question at that SAME permissiveness level: is there
    also a genuinely different arrangement? A first attempt (round 1 of this
    task) tried to read that off the diversity-required solve's own
    INFEASIBLE core (conflicting_demand_ids) -- WRONG when a demand has
    exactly one eligible employee: requiring "differ from baseline" then
    directly contradicts that demand's OWN coverage assumption, so the
    minimal unsat core includes it even though the true, only cause is the
    diversity floor, not a real conflict (tests/test_t033_replan_must_differ.py
    caught this). Solving twice per stage -- once ordinary, once diverse --
    at the SAME flags sidesteps the ambiguity entirely: an ordinary-FEASIBLE
    stage that goes INFEASIBLE only once diversity is added can only be the
    floor's doing, by construction (_wide_try_diversity_at_stage).

    NO_ALTERNATIVE is returned only after every stage's ordinary solve was
    confirmed FEASIBLE somewhere (guaranteed by the caller: this function is
    only reached after plan_requiring_different_result_narrow's own baseline
    _plan() check already proved the state solves cleanly) yet no stage ever
    produced a diverse one -- an exhaustive, proven fact. Any UNKNOWN
    (budget ran out before a stage could prove anything) is SEARCH_INCOMPLETE
    instead, never conflated with either NARROW_SEARCH_EXHAUSTED or
    NO_ALTERNATIVE."""
    deadline = time.monotonic() + REPLAN_SEARCH_BUDGET_SECONDS
    stages = (
        (True, False, False),
        (True, True, False),
        (True, True, True),
        (False, True, True),
    )
    # Tracks whether ANY earlier stage's ORDINARY (non-diversity) solve
    # already proved coverage achievable -- stage 4 (uncapped) is only a
    # genuine LOAD-01 decision point (_decision_for_load, exactly like
    # ordinary PLAN) when it is the FIRST stage to succeed; if an earlier,
    # capped stage already succeeded, dropping the cap was never actually
    # necessary and stage 4 must be treated like any other diversity
    # candidate instead of manufacturing a LOAD-01 decision that doesn't
    # reflect reality.
    found_ordinary_feasible = False
    for enforce_load_cap, allow_day_only_n_fallback, allow_emergency_24h in stages:
        # OWNER_CORRECTED 2026-09-08: search_variants=False -- this ordinary,
        # per-stage solve only ever needs to know "does coverage work at
        # this permissiveness level", never its extra T017 candidates (see
        # solve()'s search_variants docstring).
        ordinary = solve(
            state, enforce_load_cap=enforce_load_cap, allow_day_only_n_fallback=allow_day_only_n_fallback,
            allow_emergency_24h=allow_emergency_24h, deadline=deadline, search_attempt=search_attempt,
            search_variants=False,
        )
        if ordinary.status_name == "UNKNOWN":
            return PlanningResult("SEARCH_INCOMPLETE", [], None, None, [], optimization_complete=False)
        if ordinary.assignments is not None:
            if not enforce_load_cap and not found_ordinary_feasible:
                return _decision_for_load(state, ordinary)
            found_ordinary_feasible = True
            ordinary_result = _evaluate_candidate(state, ordinary)
            if ordinary_result.status != "FEASIBLE":
                return ordinary_result  # a real decision/error, exactly like ordinary PLAN
            diverse_result = _wide_try_diversity_at_stage(
                state, cutover_at, deadline, enforce_load_cap=enforce_load_cap,
                allow_day_only_n_fallback=allow_day_only_n_fallback, allow_emergency_24h=allow_emergency_24h,
                search_attempt=search_attempt, prior_variant_signatures=prior_variant_signatures,
            )
            if diverse_result is not None:
                return diverse_result
            continue  # ordinary-FEASIBLE but not diverse at this stage -- try a more permissive one
        if ordinary.unassignable_demand_ids:
            # Stage 3 (fallback=True, emergency=True, still capped) is
            # terminal for a shortage exactly like _dispatch_stage3: dropping
            # the LOAD-01 cap next cannot repair a missing eligible slot
            # either. An earlier stage having already proven feasible would
            # contradict eligibility only ever growing with more fallback
            # flags -- guarded defensively anyway.
            if enforce_load_cap and allow_day_only_n_fallback and allow_emergency_24h and not found_ordinary_feasible:
                return _decision_for_unassignable(state, ordinary)
            continue
        if ordinary.status_name == "INFEASIBLE":
            # Mirrors _resolve_without_load_cap's own ordering exactly:
            # night-streak conflicts checked before plain coverage/rest ones,
            # and both only diagnosed at the final, uncapped stage when no
            # earlier stage already proved feasible -- same as ordinary
            # _plan()'s _dispatch_or_continue/_dispatch_stage3, which never
            # attempt this diagnosis before the last stage either.
            if not enforce_load_cap and not found_ordinary_feasible:
                if ordinary.night_streak_conflicts:
                    return _decision_for_night_streak(state, ordinary)
                if ordinary.conflicting_demand_ids:
                    return _decision_for_conflict(state, ordinary)
            continue  # a genuine ordinary conflict at this permissiveness -- a later stage may still rescue it
        return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {ordinary.status_name}", [])

    if found_ordinary_feasible:
        # Every stage that could ever cover this month was tried; none ever
        # produced a schedule different from the baseline -- an exhaustive,
        # proven fact, not a guess.
        return PlanningResult("NO_ALTERNATIVE", [], None, None, [])
    # plan_requiring_different_result_narrow's own baseline _plan() check
    # already proved this state solves cleanly somewhere -- reaching here
    # with no stage ever ordinarily feasible contradicts that guarantee;
    # fail closed rather than claim a proof this function cannot have.
    return PlanningResult(
        "TECHNICAL_ERROR", [], None, "wide search: no stage proved feasible, contradicting the narrow step's own precondition", [],
    )


def _decision_for_unassignable(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    by_id = {d.demand_id: d for d in state.shift_demands}
    demand_ids = outcome.unassignable_demand_ids
    blocking = [
        BlockingDemand(demand_id, by_id[demand_id].start_datetime, by_id[demand_id].end_datetime)
        for demand_id in demand_ids
        if demand_id in by_id
    ]
    raw_blockers = [
        Blocker(employee_id, reason)
        for demand_id in demand_ids
        for employee_id, reason in outcome.unassignable_reasons.get(demand_id, [])
    ]
    payload = build_decision_payload(state, blocking, raw_blockers, None)
    return PlanningResult("DECISION_REQUIRED", [], payload, None, [])


def _site_rule_blockers_for(
    site_rule_exclusions: dict[str, list[tuple[str, str]]], demand_ids
) -> list[Blocker]:
    """ROTA-T007: dedup (employee_id, rule_version_id) pairs across the given
    demand_ids from site_rule_exclusions, in stable order."""
    seen: set = set()
    blockers: list[Blocker] = []
    for demand_id in demand_ids:
        for employee_id, rule_version_id in site_rule_exclusions.get(demand_id, []):
            key = (employee_id, rule_version_id)
            if key in seen:
                continue
            seen.add(key)
            blockers.append(Blocker(employee_id, rule_version_id))
    return blockers


def _decision_for_night_streak(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    """ROTA-T032 section 3.5: an INFEASIBLE whose minimal unsat core includes
    a NIGHT-STREAK-01 assumption is the same class of autonomy boundary
    REST-01 conflicts already are -- DECISION_REQUIRED, never REST-01 and
    never TECHNICAL_ERROR."""
    by_id = {d.demand_id: d for d in state.shift_demands}
    demand_ids = sorted({demand_id for ids in outcome.night_streak_conflicts.values() for demand_id in ids})
    blocking = [
        BlockingDemand(demand_id, by_id[demand_id].start_datetime, by_id[demand_id].end_datetime)
        for demand_id in demand_ids
        if demand_id in by_id
    ]
    employee_ids = sorted({employee_id for employee_id, _ in outcome.night_streak_conflicts})
    raw_blockers = [Blocker(employee_id, "NIGHT-STREAK-01") for employee_id in employee_ids]
    payload = build_decision_payload(state, blocking, raw_blockers, None)
    warnings = [
        "NIGHT-STREAK-01: demands "
        f"{demand_ids} cannot be jointly covered without exceeding the max-two-consecutive-N limit; "
        "blockers list every employee involved in a conflicting window, not a proven minimal cause"
    ]
    return PlanningResult("DECISION_REQUIRED", [], payload, None, warnings)


def _decision_for_conflict(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    """Audit round 12 FINDING 3: a minimal set of demands that cannot be jointly
    satisfied (typically a REST-01 conflict) is a normal autonomy boundary, not a
    technical failure (arch/spec.md:503-512)."""
    by_id = {d.demand_id: d for d in state.shift_demands}
    demand_ids = outcome.conflicting_demand_ids
    blocking = [
        BlockingDemand(demand_id, by_id[demand_id].start_datetime, by_id[demand_id].end_datetime)
        for demand_id in demand_ids
        if demand_id in by_id
    ]
    involved_employees = eligible_employees_for_demands(state, demand_ids)
    raw_blockers = [Blocker(employee_id, "REST-01") for employee_id in involved_employees]
    # ROTA-T007 (audit round 3 FINDING R3-2): a SiteRule can be the necessary
    # cause of this REST-01 conflict (it removed an alternative employee for
    # one of these demands) even though neither demand was unassignable on
    # its own -- its rule_version_id must stay visible here too, not only on
    # the simple single-demand shortage path.
    raw_blockers += _site_rule_blockers_for(outcome.site_rule_exclusions, demand_ids)
    payload = build_decision_payload(state, blocking, raw_blockers, None)
    warnings = [
        "REST-01: demands "
        f"{sorted(demand_ids)} cannot be jointly covered by eligible employees; "
        "blockers list every employee eligible for any of them, not a proven minimal cause"
    ]
    return PlanningResult("DECISION_REQUIRED", [], payload, None, warnings)


def _decision_for_load(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    full = _full_assignments(state, outcome.assignments)
    report = validate(state, full)
    if _has_non_load_violations(report):
        # Round 15 audit (tests_r15.txt FINDING R15-2): the uncapped fallback
        # candidate is still a candidate and must pass full independent HARD
        # validation (anti-drift rule 12), not just the LOAD-01 slice of it.
        # A LOAD-01 trigger does not authorize silently accepting a
        # co-occurring HARD violation via the DECISION_REQUIRED payload.
        return _decision_for_conflicts(state, full, report, list(outcome.warnings))
    return _load_decision(state, report, list(outcome.warnings), full, outcome.site_rule_exclusions)


def _has_non_load_violations(report: IndependentValidationReport) -> bool:
    return any(d.rule != "LOAD-01" for d in report.violation_details)


def _fixed_non_realized_ids(state: PlanningState) -> set:
    """Assignments REPLAN cannot move (frozen/mentor-linked/no-demand) and
    that are not REALIZED historical fact -- a violation attached to one of
    these is a normal autonomy boundary the coordinator must resolve, not a
    technical failure (ASSIGN-04)."""
    return {a.assignment_id for a in fixed_existing_assignments(state) if a.state != AssignmentState.REALIZED}


# Rules that represent "this fixed Assignment's employee is no longer
# eligible" or "this fixed Assignment conflicts with another Assignment" --
# a genuine, resolvable autonomy boundary (arch/spec.md:463-501). ASSIGN and
# ASSIGN-03/04 are deliberately excluded: those mean the candidate itself is
# structurally inconsistent (e.g. a dangling TRAINEE reference, or a
# REALIZED/frozen Assignment that was altered) -- TRAINEE Assignments are
# always in the fixed set (solver.fixed_existing_assignments), so a dangling
# reference naturally names its own assignment_id and would otherwise look
# "explained" by nothing more than matching its own id. That is corruption,
# not a coordinator decision point, and must stay TECHNICAL_ERROR.
_FROZEN_BOUNDARY_RULES = frozenset({
    "MEMBERSHIP-01", "DAY_ONLY-01", "DAY_SHIFT_OFF-01",
    "UNAVAILABLE-01", "SICK_LEAVE-01", "LEAVE_GRANTED-01", "EXTERNAL-01", "REST-01",
    # ROTA-T032: a NIGHT-STREAK-01 violation entirely among already-fixed
    # (REALIZED/frozen/mentor-linked) Assignments is the same kind of
    # coordinator autonomy boundary REST-01 already is -- never a solver bug.
    "NIGHT-STREAK-01",
})


def _split_frozen_violations(
    state: PlanningState, report: IndependentValidationReport
) -> tuple[list[ViolationDetail], list[ViolationDetail]]:
    """FINDING R25-1 (tests_r25.txt): matching only by assignment_id let one
    diagnosed rule "explain away" an independent violation of a DIFFERENT
    rule on the same Assignment (e.g. a frozen Assignment's DAY_ONLY-01
    masking its own co-occurring SICK_LEAVE-01, or SICK_LEAVE-01 masking its
    own REST-01). Every non-LOAD-01 ViolationDetail whose rule is a known
    autonomy-boundary rule AND whose assignment_ids intersect a fixed
    (non-REALIZED) Assignment is its own frozen-boundary blocker, taken
    directly from the validator's own exhaustive per-rule checks -- no
    separate eligibility re-derivation (which stops at the first failing
    rule) is used to decide what counts as "explained" anymore."""
    fixed_ids = _fixed_non_realized_ids(state)
    # ROTA-T007: a SiteRule-caused ViolationDetail.rule IS the exact
    # rule_version_id (rota.planning.site_rules), never a fixed code, so it
    # can never appear in the static _FROZEN_BOUNDARY_RULES whitelist -- it
    # is instead recognized by membership in this state's own rule set
    # (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md: a frozen conflict with an
    # applicable HARD SiteRule is an autonomy boundary, not a technical
    # failure).
    site_rule_version_ids = {r.rule_version_id for r in state.site_rules}

    def _is_frozen_boundary(detail: ViolationDetail) -> bool:
        # FINDING R26-3 (tests_r26.txt): a rule matching on the whitelist plus
        # *any* one of its assignment_ids being fixed was enough to call a
        # violation "explained" -- so REST-01 between one fixed Assignment and
        # one newly solver-created (movable) Assignment was misclassified as
        # a coordinator autonomy boundary. That is a solver/mapping bug (the
        # candidate itself violates HARD), not a frozen-fact conflict; only
        # when EVERY assignment_id the rule names is itself fixed does this
        # violation describe a conflict between preserved facts the
        # coordinator, not the solver, must resolve.
        return (
            (detail.rule in _FROZEN_BOUNDARY_RULES or detail.rule in site_rule_version_ids)
            and bool(detail.assignment_ids)
            and set(detail.assignment_ids) <= fixed_ids
        )

    non_load_details = [d for d in report.violation_details if d.rule != "LOAD-01"]
    frozen_details = [d for d in non_load_details if _is_frozen_boundary(d)]
    unexplained = [d for d in non_load_details if not _is_frozen_boundary(d)]
    return frozen_details, unexplained


def _decision_for_conflicts(
    state: PlanningState, full: list[Assignment], report: IndependentValidationReport, extra_warnings: list[str]
) -> PlanningResult:
    """FINDING R22-2 (tests_r22.txt): a diagnosed frozen conflict (FINDING
    R20-2) must not silently swallow a co-occurring LOAD-01 violation or any
    other violation it does not explain (e.g. a dangling TRAINEE reference,
    FINDING R20-3/R22-3) -- combine every explainable cause into one
    DECISION_REQUIRED payload, and if anything is left unexplained, fall back
    to TECHNICAL_ERROR (anti-drift rule 12) rather than presenting an
    incomplete decision."""
    frozen_details, unexplained = _split_frozen_violations(state, report)
    if not frozen_details or unexplained:
        message_source = report.violations if not frozen_details else [d.message for d in unexplained]
        return PlanningResult(
            "TECHNICAL_ERROR", [], None,
            "independent validator found HARD violations that cannot be attributed to a known "
            "autonomy boundary: " + "; ".join(message_source),
            [],
        )

    threshold = state.profile.rolling_7d_decision_threshold_hours
    over_threshold = {e: h for e, h in report.maximum_rolling_7d_hours.items() if h > threshold}
    warnings = list(extra_warnings) + list(report.warnings)
    load_blocker, load_raw_blockers = (None, [])
    if over_threshold:
        load_blocker, load_raw_blockers = _rank_load_blockers(report, over_threshold, warnings)

    frozen_raw_blockers, blocking = _frozen_blockers_and_demands(state, full, frozen_details)
    payload = build_decision_payload(
        state, blocking, frozen_raw_blockers + load_raw_blockers, load_blocker, frozen_boundary=True
    )
    return PlanningResult("DECISION_REQUIRED", [], payload, None, warnings)


def _frozen_blockers_and_demands(
    state: PlanningState, full: list[Assignment], frozen_details: list[ViolationDetail]
) -> tuple[list[Blocker], list[BlockingDemand]]:
    assignments_by_id = {a.assignment_id: a for a in full}
    by_demand_id = {d.demand_id: d for d in state.shift_demands}
    blockers = []
    blocking_demand_ids: set = set()
    for detail in frozen_details:
        for assignment_id in detail.assignment_ids:
            assignment = assignments_by_id.get(assignment_id)
            if assignment is None:
                continue
            blockers.append(Blocker(assignment.employee_id, detail.rule))
            if assignment.covers_demand_id:
                blocking_demand_ids.add(assignment.covers_demand_id)
    blocking = [
        BlockingDemand(demand_id, by_demand_id[demand_id].start_datetime, by_demand_id[demand_id].end_datetime)
        for demand_id in blocking_demand_ids
        if demand_id in by_demand_id
    ]
    return blockers, blocking


def _demand_ids_in_worst_windows(
    report: IndependentValidationReport, full: list[Assignment], over_threshold: dict[str, float]
) -> set:
    """ROTA-T007 (audit round 3 FINDING R3-2, narrowed by round 4 FINDING
    R4-1, then round 5 FINDING R5-1): demand_ids relevant to a LOAD-01
    breach are those overlapping, in HOURS, the over-threshold employee's
    own worst rolling-7d window (the same overlap semantics LOAD-01 itself
    uses) -- not merely demands whose start date falls inside the window's
    calendar-date range (an overnight shift starting the day before the
    window can still contribute hours to it), and not every demand that
    employee covers anywhere in the month (which would attribute an
    unrelated SiteRule from a different week to this breach)."""
    demand_ids: set = set()
    for employee_id in over_threshold:
        window = report.maximum_rolling_7d_window_datetimes.get(employee_id)
        if window is None:
            continue
        window_start, window_end = window
        demand_ids |= {
            a.covers_demand_id for a in full
            if a.employee_id == employee_id and a.covers_demand_id
            and intervals_overlap(a.start_datetime, a.end_datetime, window_start, window_end)
        }
    return demand_ids


def _load_decision(
    state: PlanningState, report: IndependentValidationReport, extra_warnings: list[str],
    full: list[Assignment], site_rule_exclusions: dict[str, list[tuple[str, str]]],
) -> PlanningResult:
    """Build a typed LOAD-01 DECISION_REQUIRED from a report already known to
    have no non-LOAD-01 violations. Shared by the existing-assignments-only
    path (_evaluate_candidate, FINDING R17-1) and the uncapped-retry path
    (_decision_for_load)."""
    threshold = state.profile.rolling_7d_decision_threshold_hours
    over_threshold = {e: h for e, h in report.maximum_rolling_7d_hours.items() if h > threshold}
    if not over_threshold:
        # Defensive: report.hard_pass was False but nobody is over threshold
        # after all -- that expectation was wrong; do not return an untyped
        # DECISION_REQUIRED (load_blocker=None, empty blockers) (round 14
        # audit, tests_r14.txt FINDING R14-2).
        return PlanningResult(
            "TECHNICAL_ERROR", [], None,
            "a LOAD-01 violation was reported but no employee is over threshold; cannot classify", [],
        )
    warnings = list(extra_warnings) + list(report.warnings)
    load_blocker, raw_blockers = _rank_load_blockers(report, over_threshold, warnings)
    relevant_demand_ids = _demand_ids_in_worst_windows(report, full, over_threshold)
    raw_blockers = raw_blockers + _site_rule_blockers_for(site_rule_exclusions, relevant_demand_ids)
    payload = build_decision_payload(state, [], raw_blockers, load_blocker)
    return PlanningResult("DECISION_REQUIRED", [], payload, None, warnings)


def _rank_load_blockers(
    report: IndependentValidationReport, over_threshold: dict[str, float], warnings: list[str]
) -> tuple[LoadBlocker | None, list[Blocker]]:
    if not over_threshold:
        return None, []
    worst_employee = max(over_threshold, key=over_threshold.get)
    window_start, window_end = report.maximum_rolling_7d_window[worst_employee]
    load_blocker = LoadBlocker(worst_employee, window_start, window_end, int(over_threshold[worst_employee]))
    blockers = [Blocker(e, "LOAD-01") for e in over_threshold]
    if len(over_threshold) > 1:
        warnings.append(
            "LOAD-01: multiple employees exceed threshold; only worst offender is in load_blocker, "
            f"see blockers for the rest: {sorted(over_threshold)}"
        )
    return load_blocker, blockers


if __name__ == "__main__":
    print("engine module OK")
