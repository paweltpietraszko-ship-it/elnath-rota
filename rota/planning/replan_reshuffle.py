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
    existing Assignments (same `redistributable` predicate, mirrored,
    including the ROTA-T057 state.cutover_at already-live exclusion)."""
    mentor_linked_ids = _mentor_linked_ids(state)
    return [
        a for a in state.existing_assignments
        if a.state != AssignmentState.CANCELLED
        and a.role == AssignmentRole.PRIMARY
        and a.covers_demand_id is not None
        and a.state == AssignmentState.PLANNED
        and not a.frozen
        and a.assignment_id not in mentor_linked_ids
        and not (state.cutover_at is not None and a.start_datetime < state.cutover_at)
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


def build_any_difference_expr(x: dict, baseline_pairs: set[tuple[str, str]]):
    """ROTA-T033 audit finding R1-1 (2026-08-26): the coordinator-facing
    "must differ from what's currently there" requirement (solver.solve's
    require_different_from_baseline) is NOT the same question
    build_reshuffle_count_expr answers. That function only asks "did an
    ALREADY-COVERED demand's placement change" -- it has no term at all for
    a demand that was genuinely open (no redistributable coverage yet, e.g.
    a partially-saved schedule) suddenly getting filled. Filling one is just
    as much a different, better schedule as reassigning an already-covered
    one, and must count the same way.

    baseline_pairs is the FULL (employee_id, covers_demand_id) signature of
    every redistributable baseline placement in scope (both past-pinned and
    future -- past ones are separately forced via model.add(x[key]==1), so
    their own term here always evaluates to 0, correctly "unchanged"; never
    pass only the future subset, or a pinned past placement would wrongly
    slip into the "new pair" half below and count as a difference it can
    never actually be).

    Every key in baseline_pairs contributes 1 if it's no longer selected (or
    no longer even a valid slot -- same constant-1 treatment as
    build_reshuffle_count_expr). Every OTHER key in x -- any pairing that
    was NOT part of the baseline -- contributes its own selected value: a
    previously-nonexistent placement appearing in the candidate is exactly
    as much a difference as an existing one disappearing or changing hands."""
    terms = [1 - x[key] if key in x else 1 for key in baseline_pairs]
    terms.extend(var for key, var in x.items() if key not in baseline_pairs)
    return cp_model.LinearExpr.sum(terms) if terms else cp_model.LinearExpr.constant(0)


if __name__ == "__main__":
    print("planning.replan_reshuffle module OK")
