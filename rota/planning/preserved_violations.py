"""ROTA-PRESERVED-FACTS-REPLAN section 3B: the single owner of "this HARD
violation is a preserved input fact, not a new solver decision" -- shared
by the engine's candidate gates and plan_ops.select_candidate's acceptance
gate, so both draw the same line. It never edits the validator report:
the violation stays visible to reads, memory, finalization and export.

Exactly three classes, nothing broader:
1. THIRD-CONSECUTIVE-SHIFT-01 among unchanged fixed/boundary facts
   (the pre-existing engine._is_fully_historical_third_shift semantics);
2. NIGHT-STREAK-01 among unchanged fixed/boundary facts (the same line);
3. COVERAGE-01 whose shortage is exactly the coverage of already-started
   PRIMARY+CANCELLED+NN facts the candidate carries unchanged -- NN is the
   proven cause of the gap, never real coverage.

Fixedness and NN facts come from the solver's own owners
(fixed_existing_assignments/_historical_nn_facts); the solver never
imports this module."""
from __future__ import annotations

from dataclasses import replace

from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.solver import _historical_nn_facts, fixed_existing_assignments
from rota.planning.state import PlanningState
from rota.planning.validator_shared import ViolationDetail, _attributed_overlap_intervals, coverage_segments

_FIXED_FACT_RULES = frozenset({"THIRD-CONSECUTIVE-SHIFT-01", "NIGHT-STREAK-01"})


def _unchanged_in(candidate: list[Assignment], facts: list[Assignment]) -> list[Assignment]:
    """The input facts the candidate still carries field-for-field (an id
    alone never qualifies; schedule_version_id is the only field a
    persisted preview may legitimately restamp)."""
    by_id = {a.assignment_id: a for a in candidate}
    kept = []
    for fact in facts:
        other = by_id.get(fact.assignment_id)
        if other is not None and replace(other, schedule_version_id=fact.schedule_version_id) == fact:
            kept.append(fact)
    return kept


def _is_fixed_fact_violation(state: PlanningState, detail: ViolationDetail, candidate: list[Assignment]) -> bool:
    # A window wholly inside state.boundary_assignments gets no ids at all
    # (validator only records current-month ids) -- every date predates
    # this solve. Otherwise every named id must be an unchanged fixed fact.
    if not detail.assignment_ids:
        return True
    fixed_ids = {a.assignment_id for a in _unchanged_in(candidate, fixed_existing_assignments(state))}
    return set(detail.assignment_ids) <= fixed_ids


def _is_historical_nn_shortage(state: PlanningState, detail: ViolationDetail, candidate: list[Assignment]) -> bool:
    if len(detail.demand_ids) != 1 or detail.assignment_ids:
        return False
    demand = next((d for d in state.shift_demands if d.demand_id == detail.demand_ids[0]), None)
    nn_facts = _unchanged_in(candidate, _historical_nn_facts(state))
    if demand is None or not nn_facts:
        return False
    demand_by_id = {d.demand_id: d for d in state.shift_demands}
    working = [a for a in candidate if a.role == AssignmentRole.PRIMARY and a.state != AssignmentState.CANCELLED]
    nn_intervals = []
    for a in nn_facts:
        nn_intervals.extend(_attributed_overlap_intervals(replace(a, state=AssignmentState.PLANNED), demand, demand_by_id))
    if not nn_intervals:
        return False  # no NN on this demand: nothing here is explained by NN
    overlapping = list(nn_intervals)
    for a in working:
        overlapping.extend(_attributed_overlap_intervals(a, demand, demand_by_id))
    segments = coverage_segments(demand.start_datetime, demand.end_datetime, overlapping)
    # Every segment must be exact once the NN facts are counted back in:
    # any leftover gap or any excess is not explained by NN.
    return all(count == demand.required_primary_count for _, _, count in segments)


def is_preserved_violation(state: PlanningState, detail: ViolationDetail, candidate: list[Assignment]) -> bool:
    if detail.rule in _FIXED_FACT_RULES:
        return _is_fixed_fact_violation(state, detail, candidate)
    if detail.rule == "COVERAGE-01":
        return _is_historical_nn_shortage(state, detail, candidate)
    return False


def gating_hard_pass(state: PlanningState, report, candidate: list[Assignment]) -> bool:
    """report.hard_pass, except that preserved violations alone never fail
    it. hard_pass=False with an empty detail list stays False (an empty
    all() must not swallow it)."""
    if report.hard_pass:
        return True
    return bool(report.violation_details) and all(
        is_preserved_violation(state, d, candidate) for d in report.violation_details
    )
