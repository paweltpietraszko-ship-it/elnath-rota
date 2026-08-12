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

from rota.domain import Assignment, AssignmentState
from rota.planning.state import PlanningState
from rota.planning.engine_types import (
    BlockingDemand,
    Blocker,
    DecisionRequiredPayload,
    LoadBlocker,
    PlanningResult,
)
from rota.planning.shift_catalog import UnclassifiedShiftError
from rota.planning.site_rules import UnsupportedOrMalformedSiteRule, validate_executable_site_rules
from rota.planning.solver import SolverOutcome, eligible_employees_for_demands, fixed_existing_assignments, solve
from rota.planning.validator import IndependentValidationReport, ViolationDetail, validate


def plan(state: PlanningState) -> PlanningResult:
    """Produce a PlanningResult for one PlanningState.

    plan() has exactly three output statuses (arch/spec.md:339-342); a raw
    exception is never one of them. FINDING R17-3: UnclassifiedShiftError is
    a genuine model error (arch/spec.md:503-507) -- a ShiftDemand that
    matches no StandardShift in the profile -- and must be mapped to
    TECHNICAL_ERROR at this public boundary, not left to propagate to the
    caller. ROTA-T007: UnsupportedOrMalformedSiteRule (a RESOLVED rule that
    claims to be executable but isn't) is the same class of model error.
    """
    try:
        return _plan(state)
    except UnclassifiedShiftError as exc:
        return PlanningResult("TECHNICAL_ERROR", [], None, f"model error: {exc}", [])
    except UnsupportedOrMalformedSiteRule as exc:
        return PlanningResult("TECHNICAL_ERROR", [], None, f"site rule error: {exc}", [])


def _plan(state: PlanningState) -> PlanningResult:
    # ROTA-T007: prevalidate before solve() -- a RESOLVED HARD/SOFT SiteRule
    # that cannot be executed must never be silently ignored just to reach
    # FEASIBLE (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md point 8).
    validate_executable_site_rules(state.site_rules)
    outcome = solve(state, enforce_load_cap=True)

    if outcome.unassignable_demand_ids:
        return _decision_for_unassignable(state, outcome)

    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)

    if outcome.status_name != "INFEASIBLE":
        # Round 14 audit (tests_r14.txt FINDING R14-2): only a proven
        # INFEASIBLE justifies retrying without the LOAD-01 cap to see whether
        # the cap itself was the cause. UNKNOWN (time limit) or MODEL_INVALID
        # is a genuine technical failure, not a constraint conflict; retrying
        # and then guessing a LOAD-01 cause from whatever the uncapped solve
        # happens to return was producing untyped DECISION_REQUIRED payloads
        # (load_blocker=None) with no real trigger.
        return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {outcome.status_name}", [])

    # INFEASIBLE with the LOAD-01 cap enabled is not evidence of a REST-01
    # conflict by itself: the cap constraint is part of what CP-SAT's
    # assumption core can implicate. Round 13 audit (tests_r13.txt FINDING
    # R13-1) found every capped-solve conflict being reported as REST-01 even
    # when removing the cap alone would resolve it (pure LOAD-01 case). The
    # cap must be dropped and re-solved before treating this as a genuine
    # cross-demand conflict.
    return _resolve_without_load_cap(state)


def _resolve_without_load_cap(state: PlanningState) -> PlanningResult:
    fallback = solve(state, enforce_load_cap=False)
    if fallback.unassignable_demand_ids:
        return _decision_for_unassignable(state, fallback)
    if fallback.assignments is not None:
        return _decision_for_load(state, fallback)
    if fallback.conflicting_demand_ids:
        return _decision_for_conflict(state, fallback)
    return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {fallback.status_name}", [])


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
        return PlanningResult("FEASIBLE", [full], None, None, outcome.warnings + report.warnings)
    if _has_non_load_violations(report):
        return _decision_for_conflicts(state, full, report, list(outcome.warnings))
    # FINDING R17-1: a demand already fully covered by existing_assignments
    # never gets a SolverSlot, so the LOAD-01 cap constraint is never added
    # for that employee even though the capped solve reports OPTIMAL. A
    # LOAD-01-only violation surfacing here is a genuine boundary, not a
    # solver/mapping bug, and must not become TECHNICAL_ERROR.
    return _load_decision(state, report, list(outcome.warnings), full, outcome.site_rule_exclusions)


def _decision_for_unassignable(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    by_id = {d.demand_id: d for d in state.shift_demands}
    demand_ids = outcome.unassignable_demand_ids
    blocking = [
        BlockingDemand(demand_id, by_id[demand_id].start_datetime, by_id[demand_id].end_datetime)
        for demand_id in demand_ids
        if demand_id in by_id
    ]
    blockers = [
        Blocker(employee_id, reason)
        for demand_id in demand_ids
        for employee_id, reason in outcome.unassignable_reasons.get(demand_id, [])
    ]
    payload = DecisionRequiredPayload(
        blocking_shift_demands=blocking,
        blockers=blockers,
        load_blocker=None,
        unblocking_options=[
            "potwierdzenie X/Y",
            "świadome ściągnięcie pracownika z wolnego",
            "świadome odwołanie/override urlopu zgodnie z kontraktem",
            "świadome wyłączenie DAY_ONLY",
        ],
    )
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
    blockers = [Blocker(employee_id, "REST-01") for employee_id in involved_employees]
    # ROTA-T007 (audit round 3 FINDING R3-2): a SiteRule can be the necessary
    # cause of this REST-01 conflict (it removed an alternative employee for
    # one of these demands) even though neither demand was unassignable on
    # its own -- its rule_version_id must stay visible here too, not only on
    # the simple single-demand shortage path.
    blockers += _site_rule_blockers_for(outcome.site_rule_exclusions, demand_ids)
    payload = DecisionRequiredPayload(
        blocking_shift_demands=blocking,
        blockers=blockers,
        load_blocker=None,
        unblocking_options=["świadoma ręczna korekta zgodnie z kontraktem"],
    )
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
    "MEMBERSHIP-01", "EMP-02", "DAY_ONLY-01", "DAY_SHIFT_OFF-01",
    "UNAVAILABLE-01", "SICK_LEAVE-01", "LEAVE_GRANTED-01", "EXTERNAL-01", "REST-01",
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
    unblocking_options = [
        "świadome odmrożenie Assignment i ponowne planowanie",
        "świadoma ręczna korekta frozen Assignment zgodnie z kontraktem",
    ]
    load_blocker, load_blockers = (None, [])
    if over_threshold:
        load_blocker, load_blockers = _rank_load_blockers(report, over_threshold, warnings)
        unblocking_options.append("świadoma akceptacja >" + str(threshold) + "h / 7 kolejnych dni")

    frozen_blockers, blocking = _frozen_blockers_and_demands(state, full, frozen_details)
    payload = DecisionRequiredPayload(
        blocking_shift_demands=blocking,
        blockers=frozen_blockers + load_blockers,
        load_blocker=load_blocker,
        unblocking_options=unblocking_options,
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
    load_blocker, blockers = _rank_load_blockers(report, over_threshold, warnings)
    # ROTA-T007 (audit round 3 FINDING R3-2): a SiteRule that excluded other
    # employees from demands the over-threshold employee(s) ended up
    # covering can be the necessary cause of this LOAD-01 breach -- surface
    # its rule_version_id too, not just LOAD-01.
    over_threshold_demand_ids = {
        a.covers_demand_id for a in full if a.employee_id in over_threshold and a.covers_demand_id
    }
    blockers = blockers + _site_rule_blockers_for(site_rule_exclusions, over_threshold_demand_ids)
    payload = DecisionRequiredPayload(
        blocking_shift_demands=[],
        blockers=blockers,
        load_blocker=load_blocker,
        unblocking_options=["świadoma akceptacja >" + str(threshold) + "h / 7 kolejnych dni"],
    )
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
