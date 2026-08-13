"""PRECHECK (tasks/ROTA-T009/brief.md operation 2): a fast, non-CP-SAT
heuristic over an already-assembled PlanningState -- the caller assembles
context first (that touches persistence); this function itself does not.
Reuses the solver's own eligibility slot-building and fixed-assignment
logic so eligibility/coverage rules are never duplicated, but never calls
solve() and never produces a candidate.
"""
from __future__ import annotations

from dataclasses import dataclass

from rota.domain import AssignmentRole
from rota.planning.solver import eligible_employees_for_demands, fixed_existing_assignments
from rota.planning.state import PlanningState


@dataclass(frozen=True)
class PrecheckResult:
    status: str  # "NO_OBVIOUS_SHORTAGE" or "LIKELY_INSUFFICIENT"
    under_covered_demand_ids: tuple[str, ...]


def _fixed_primary_coverage_counts(state: PlanningState) -> dict[str, int]:
    """R4-7: eligible_employees_for_demands already returns only the slots
    remaining after fixed (REALIZED/frozen/TRAINEE/no-covers_demand_id)
    PRIMARY coverage is subtracted -- comparing that remaining pool against
    the demand's full required_primary_count, instead of against what is
    still actually needed, misreports a fully- or partially-covered demand
    as a shortage."""
    counts: dict[str, int] = {}
    for assignment in fixed_existing_assignments(state):
        if assignment.role == AssignmentRole.PRIMARY and assignment.covers_demand_id:
            counts[assignment.covers_demand_id] = counts.get(assignment.covers_demand_id, 0) + 1
    return counts


def precheck(state: PlanningState) -> PrecheckResult:
    fixed_counts = _fixed_primary_coverage_counts(state)
    shortfalls = []
    for demand in state.shift_demands:
        remaining_need = demand.required_primary_count - fixed_counts.get(demand.demand_id, 0)
        if remaining_need <= 0:
            continue
        eligible = eligible_employees_for_demands(state, [demand.demand_id])
        if len(eligible) < remaining_need:
            shortfalls.append(demand.demand_id)
    if shortfalls:
        return PrecheckResult("LIKELY_INSUFFICIENT", tuple(shortfalls))
    return PrecheckResult("NO_OBVIOUS_SHORTAGE", ())
