"""PRECHECK (tasks/ROTA-T009/brief.md operation 2): a fast, non-CP-SAT
heuristic over an already-assembled PlanningState -- the caller assembles
context first (that touches persistence); this function itself does not.
Reuses the solver's own eligibility slot-building so eligibility rules are
never duplicated, but never calls solve() and never produces a candidate.
"""
from __future__ import annotations

from dataclasses import dataclass

from rota.planning.solver import eligible_employees_for_demands
from rota.planning.state import PlanningState


@dataclass(frozen=True)
class PrecheckResult:
    status: str  # "NO_OBVIOUS_SHORTAGE" or "LIKELY_INSUFFICIENT"
    under_covered_demand_ids: tuple[str, ...]


def precheck(state: PlanningState) -> PrecheckResult:
    shortfalls = tuple(
        demand.demand_id for demand in state.shift_demands
        if len(eligible_employees_for_demands(state, [demand.demand_id])) < demand.required_primary_count
    )
    if shortfalls:
        return PrecheckResult("LIKELY_INSUFFICIENT", shortfalls)
    return PrecheckResult("NO_OBVIOUS_SHORTAGE", ())
