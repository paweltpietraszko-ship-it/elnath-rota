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

from rota.domain import Assignment
from rota.planning.state import PlanningState
from rota.planning.engine_types import (
    BlockingDemand,
    Blocker,
    DecisionRequiredPayload,
    LoadBlocker,
    PlanningResult,
)
from rota.planning.solver import SolverOutcome, eligible_employees_for_demands, solve
from rota.planning.validator import IndependentValidationReport, validate


def plan(state: PlanningState) -> PlanningResult:
    """Produce a PlanningResult for one PlanningState."""
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
    return list(state.existing_assignments) + list(solved)


def _evaluate_candidate(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    full = _full_assignments(state, outcome.assignments)
    report = validate(state, full)
    if not report.hard_pass:
        return PlanningResult(
            "TECHNICAL_ERROR", [], None,
            "independent validator found HARD violations in a CP-SAT-OPTIMAL candidate: "
            + "; ".join(report.violations),
            [],
        )
    return PlanningResult("FEASIBLE", [full], None, None, outcome.warnings + report.warnings)


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
    threshold = state.profile.rolling_7d_decision_threshold_hours
    over_threshold = {e: h for e, h in report.maximum_rolling_7d_hours.items() if h > threshold}
    if not over_threshold:
        # Defensive: this path is only reached because the capped solve was
        # INFEASIBLE and the uncapped retry then succeeded, which should mean
        # the cap was the cause. If independent validation finds nobody
        # actually over threshold, that expectation was wrong -- do not
        # return an untyped DECISION_REQUIRED (load_blocker=None, empty
        # blockers); surface it as TECHNICAL_ERROR instead (round 14 audit,
        # tests_r14.txt FINDING R14-2).
        return PlanningResult(
            "TECHNICAL_ERROR", [], None,
            "uncapped solve succeeded but no employee is over the LOAD-01 threshold; "
            "cannot attribute the capped INFEASIBLE to LOAD-01",
            [],
        )
    warnings = list(outcome.warnings) + list(report.warnings)
    load_blocker, blockers = _rank_load_blockers(report, over_threshold, warnings)
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
