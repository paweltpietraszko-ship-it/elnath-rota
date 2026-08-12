"""PlanningEngine.plan(): orchestrate solver + independent validator into a PlanningResult.

Status mapping (arch/spec.md SECTION 3, Frozen Execution Contract v0.4 §6):
- CP-SAT finds a full-coverage solution within the LOAD-01 threshold and the
  independent validator confirms HARD PASS -> FEASIBLE.
- No eligible employee exists for some demand, or coverage is only reachable
  by exceeding the LOAD-01 threshold -> DECISION_REQUIRED with the relevant
  blockers.
- CP-SAT reports OPTIMAL/FEASIBLE but the independent validator finds a HARD
  violation anyway -> this is a solver/mapping bug (anti-drift rule 12), not
  a product outcome, and is reported as TECHNICAL_ERROR rather than silently
  claimed FEASIBLE.
- Any other unresolved CP-SAT status (e.g. UNKNOWN after the time limit) with
  no identifiable staffing cause -> TECHNICAL_ERROR.

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
from rota.planning.solver import SolverOutcome, solve
from rota.planning.validator import IndependentValidationReport, validate


def plan(state: PlanningState) -> PlanningResult:
    """Produce a PlanningResult for one PlanningState."""
    outcome = solve(state, enforce_load_cap=True)

    if outcome.unassignable_demand_ids:
        return _decision_for_unassignable(state, outcome.unassignable_demand_ids)

    if outcome.assignments is not None:
        return _evaluate_candidate(state, outcome)

    return _resolve_without_load_cap(state)


def _resolve_without_load_cap(state: PlanningState) -> PlanningResult:
    fallback = solve(state, enforce_load_cap=False)
    if fallback.unassignable_demand_ids:
        return _decision_for_unassignable(state, fallback.unassignable_demand_ids)
    if fallback.assignments is None:
        return PlanningResult("TECHNICAL_ERROR", [], None, f"solver status: {fallback.status_name}", [])
    return _decision_for_load(state, fallback)


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


def _decision_for_unassignable(state: PlanningState, demand_ids: list[str]) -> PlanningResult:
    by_id = {d.demand_id: d for d in state.shift_demands}
    blocking = [
        BlockingDemand(demand_id, by_id[demand_id].start_datetime, by_id[demand_id].end_datetime)
        for demand_id in demand_ids
        if demand_id in by_id
    ]
    payload = DecisionRequiredPayload(
        blocking_shift_demands=blocking,
        blockers=[],
        load_blocker=None,
        unblocking_options=[
            "potwierdzenie X/Y",
            "świadome ściągnięcie pracownika z wolnego",
            "świadome odwołanie/override urlopu zgodnie z kontraktem",
            "świadome wyłączenie DAY_ONLY",
        ],
    )
    return PlanningResult("DECISION_REQUIRED", [], payload, None, [])


def _decision_for_load(state: PlanningState, outcome: SolverOutcome) -> PlanningResult:
    full = _full_assignments(state, outcome.assignments)
    report = validate(state, full)
    threshold = state.profile.rolling_7d_decision_threshold_hours
    over_threshold = {e: h for e, h in report.maximum_rolling_7d_hours.items() if h > threshold}
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
