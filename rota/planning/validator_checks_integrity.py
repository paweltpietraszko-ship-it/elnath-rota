"""Structural-integrity HARD checks split out of validator.py (2026-09
oversized-file refactor, mechanical-only, zero behavior change):
FULL_HOUR-01, ASSIGN (trainee/mentor reference), ASSIGN-03/04 (REPLAN
preserves fixed), COVERAGE-01."""
from __future__ import annotations

from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.state import PlanningState
from rota.planning.validator_shared import (
    ViolationDetail,
    _attributed_overlap_intervals,
    _coverage_violation_detail,
    _is_full_hour,
    coverage_segments,
)


def _check_coverage(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """COVERAGE-01: derived from each PRIMARY's actual interval overlap, via
    the shared attribution owner `_attributed_overlap_intervals` (ROTA-T045)."""
    primary = [a for a in assignments if a.role == AssignmentRole.PRIMARY]
    demand_by_id = {d.demand_id: d for d in state.shift_demands}
    for demand in state.shift_demands:
        overlapping = []
        for a in primary:
            overlapping.extend(_attributed_overlap_intervals(a, demand, demand_by_id))
        segments = coverage_segments(demand.start_datetime, demand.end_datetime, overlapping)
        bad_segments = [s for s in segments if s[2] != demand.required_primary_count]
        if bad_segments:
            details.append(_coverage_violation_detail(demand, bad_segments))


def _check_trainee_mentor_reference(assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """TRAINEE.mentor_primary_assignment_id must resolve to a same-candidate PRIMARY whose interval contains it (SECTION 8)."""
    by_id = {a.assignment_id: a for a in assignments}
    for assignment in assignments:
        if assignment.role != AssignmentRole.TRAINEE:
            continue
        mentor_id = assignment.mentor_primary_assignment_id
        if not mentor_id:
            continue
        target = by_id.get(mentor_id)
        ids = (assignment.assignment_id, mentor_id)
        if target is None:
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) references missing mentor_primary_assignment_id {mentor_id}"))
        elif target.role != AssignmentRole.PRIMARY:
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) mentor_primary_assignment_id {mentor_id} is not PRIMARY (role={target.role.value})"))
        elif assignment.start_datetime < target.start_datetime or assignment.end_datetime > target.end_datetime:
            details.append(ViolationDetail("ASSIGN", ids, f"ASSIGN: {assignment.assignment_id} (TRAINEE) interval is not inside mentor {mentor_id}'s interval ({target.start_datetime}-{target.end_datetime})"))


def _check_replan_preserves_fixed(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """REPLAN (SECTION 7, ASSIGN-03/04): REALIZED, frozen, TRAINEE, PERIODIC_TRAINING (T52-11: S1 is a manual
    coordinator fact, never solver-moved) and any mentor-linked PRIMARY must not change -- mirrors
    solver.fixed_existing_assignments/replan_reshuffle's mentor-linked-PRIMARY protection (T022-F5)."""
    by_id = {a.assignment_id: a for a in assignments}
    mentor_linked_ids = {
        a.mentor_primary_assignment_id
        for a in state.existing_assignments
        if a.role == AssignmentRole.TRAINEE and a.state != AssignmentState.CANCELLED and a.mentor_primary_assignment_id
    }
    for existing in state.existing_assignments:
        if existing.state == AssignmentState.CANCELLED:
            continue
        must_preserve = (
            existing.state == AssignmentState.REALIZED or existing.frozen
            or existing.role in (AssignmentRole.TRAINEE, AssignmentRole.PERIODIC_TRAINING)
            or existing.assignment_id in mentor_linked_ids
        )
        if not must_preserve:
            continue
        candidate = by_id.get(existing.assignment_id)
        ids = (existing.assignment_id,)
        if candidate is None:
            details.append(ViolationDetail("ASSIGN-03/04", ids, f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE/mentor-linked) missing from candidate"))
        elif candidate != existing:
            details.append(ViolationDetail("ASSIGN-03/04", ids, f"ASSIGN-03/04: {existing.assignment_id} (REALIZED/frozen/TRAINEE/mentor-linked) was modified"))


def _check_full_hour(state: PlanningState, assignments: list[Assignment], details: list[ViolationDetail]) -> None:
    """OWNER-T022-01: no partial-hour work anywhere. Defense-in-depth for malformed in-memory/legacy state reaching
    plan()/validate() without having passed the persistence-layer write-time guard. Covers every work boundary named
    by the contract -- current/boundary demands, current/boundary/other-Site Assignments (incl. REALIZED, since a
    pre-T022 fractional-hour historical row is still invalid) and the profile catalog itself (T022-R1-1)."""
    for demand in (*state.shift_demands, *state.boundary_shift_demands):
        if not _is_full_hour(demand.start_datetime) or not _is_full_hour(demand.end_datetime):
            details.append(ViolationDetail("FULL_HOUR-01", (), f"FULL_HOUR-01: demand {demand.demand_id} start/end is not a full clock hour", demand_ids=(demand.demand_id,)))
    for assignment in (*assignments, *state.existing_assignments, *state.boundary_assignments, *state.other_site_assignments, *state.holiday_history):
        if not _is_full_hour(assignment.start_datetime) or not _is_full_hour(assignment.end_datetime):
            details.append(ViolationDetail("FULL_HOUR-01", (assignment.assignment_id,), f"FULL_HOUR-01: assignment {assignment.assignment_id} start/end is not a full clock hour"))
    for shift in state.profile.standard_shifts:
        if not _is_full_hour(shift.start_time) or not _is_full_hour(shift.end_time):
            details.append(ViolationDetail("FULL_HOUR-01", (), f"FULL_HOUR-01: profile StandardShift kind={shift.kind.value} start/end is not a full clock hour"))


if __name__ == "__main__":
    print("planning.validator_checks_integrity module OK")
