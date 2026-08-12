"""REPLAN-MIN-01 (arch/FROZEN_ADDENDUM_REPLAN_MIN_01.md, tasks/ROTA-T006/brief.md):
minimal-reshuffle objective for REPLAN, ranked strictly BEFORE the ordinary
TARGET/SOFT objective -- not an arbitrary weight relative to it.

UNIT OF RESHUFFLE (brief.md): counted per baseline demand placement, not per
employee and not per Assignment row id. A baseline placement is UNCHANGED
iff the same employee still covers the same demand in the final candidate.
"""
from __future__ import annotations

from ortools.sat.python import cp_model

from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.state import PlanningState


def _mentor_linked_ids(state: PlanningState) -> set:
    """Mirrors solver.fixed_existing_assignments's own mentor_linked_ids
    computation -- duplicated (not imported) so this module stays a pure
    reader of PlanningState and doesn't force a signature change on the
    widely-used fixed_existing_assignments; kept in sync by
    tests/test_replan_reshuffle.py's baseline/fixed partition test."""
    return {
        assignment.mentor_primary_assignment_id
        for assignment in state.existing_assignments
        if assignment.role == AssignmentRole.TRAINEE
        and assignment.state != AssignmentState.CANCELLED
        and assignment.mentor_primary_assignment_id
    }


def redistributable_baseline_assignments(state: PlanningState) -> list[Assignment]:
    """The baseline placements REPLAN-MIN-01 is measured against: the exact
    complement of solver.fixed_existing_assignments among non-CANCELLED
    existing Assignments (same `redistributable` predicate, mirrored)."""
    mentor_linked_ids = _mentor_linked_ids(state)
    return [
        a for a in state.existing_assignments
        if a.state != AssignmentState.CANCELLED
        and a.role == AssignmentRole.PRIMARY
        and a.covers_demand_id is not None
        and a.state == AssignmentState.PLANNED
        and not a.frozen
        and a.assignment_id not in mentor_linked_ids
    ]


def build_reshuffle_count_expr(x: dict, baseline: list[Assignment]):
    """One 'changed' term per baseline placement. A baseline employee who is
    no longer an eligible (employee, demand) slot at all -- e.g. a new
    absence removed them from `x` entirely -- has no variable to check: that
    placement is definitionally changed, contributed as a constant 1."""
    changed_terms = []
    for assignment in baseline:
        key = (assignment.employee_id, assignment.covers_demand_id)
        changed_terms.append(1 - x[key] if key in x else 1)
    return cp_model.LinearExpr.sum(changed_terms) if changed_terms else cp_model.LinearExpr.constant(0)


if __name__ == "__main__":
    print("planning.replan_reshuffle module OK")
