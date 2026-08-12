"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r23.txt.

R23-1: holiday fairness compared only new-slot hours against historical
hours, ignoring current-run fixed (frozen/mentor-linked) holiday work --
so it picked an observably more unequal candidate even when a perfectly
equal one was achievable. Non-blocking SOFT (owner confirmed 2026-08-12:
"holiday fairness to miękkie wymaganie ... nie przepisy prawa"), fixed
anyway since it was cheap and legitimate.

R23-2: frozen-conflict violation classification matched assignment_id as a
substring of the violation message text, so short/common IDs ("a",
"mentor", "missing") could coincidentally match unrelated violation text
and mask an independent dangling TRAINEE reference.

R23-3: the validator accepted a TRAINEE whose mentor_primary_assignment_id
resolved to a real PRIMARY, without checking the TRAINEE's own interval
fell inside that PRIMARY's interval -- a mentor from a different day, or
one that didn't cover the full training interval, passed HARD validation.
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R23-1 -----------------------------------------------------------


def test_r23_1_holiday_fairness_counts_current_fixed_holiday_work():
    days = [5, 6, 7, 8]  # Mon-Thu 2026-10: plain weekdays, isolates holiday fairness from weekend fairness
    demands = tuple(
        ShiftDemand(f"2026-10-0{d}-D", "test-v1", datetime(2026, 10, d, 5, 0), datetime(2026, 10, d, 17, 0), 1)
        for d in days
    )
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    frozen = tuple(
        Assignment(f"f{d}", "test-v1", "A", demands[i].start_datetime, demands[i].end_datetime,
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demands[i].demand_id, None)
        for i, d in enumerate(days[:2])
    )
    calendar_days = tuple(CalendarDay(date(2026, 10, d), True) for d in days)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=demands, existing_assignments=frozen, calendar_days=calendar_days,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    counts: dict[str, int] = {}
    for a in result.candidates[0]:
        counts[a.employee_id] = counts.get(a.employee_id, 0) + 1
    assert counts == {"A": 2, "B": 2}


# FINDING R23-2 -------------------------------------------------------------


def test_r23_2_short_frozen_id_does_not_mask_dangling_trainee():
    empA = Employee("A", "A", date(2026, 9, 1), None, False)
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    for frozen_id in ("a", "mentor", "missing"):
        frozen = Assignment(
            frozen_id, "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
        )
        dangling = Assignment(
            "dangling-t", "test-v1", "MENTEE", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "missing-mentor",
        )
        state = base_state(
            employees=(empA, mentee), memberships=(_local_membership("A"), _local_membership("MENTEE")),
            shift_demands=(DEMAND_D,), existing_assignments=(frozen, dangling), availability_records=(sick,),
        )
        result = plan(state)
        assert result.status == "TECHNICAL_ERROR", f"frozen_id={frozen_id!r} masked the dangling reference"


# FINDING R23-3 -------------------------------------------------------------


def test_r23_3_trainee_must_be_temporally_inside_mentor_interval():
    mentor = Assignment(
        "mentor-1", "test-v1", "A", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    different_day = Assignment(
        "t-a", "test-v1", "M", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-1",
    )
    starts_before = Assignment(
        "t-b", "test-v1", "M", datetime(2026, 10, 1, 4, 0), datetime(2026, 10, 1, 17, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-1",
    )
    ends_after = Assignment(
        "t-c", "test-v1", "M", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 18, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-1",
    )
    inside = Assignment(
        "t-ok", "test-v1", "M", datetime(2026, 10, 1, 9, 0), datetime(2026, 10, 1, 13, 0),
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-1",
    )
    state = base_state()
    for trainee, should_flag in ((different_day, True), (starts_before, True), (ends_after, True), (inside, False)):
        report = validate(state, [mentor, trainee])
        has_assign_violation = any(v.startswith("ASSIGN:") for v in report.violations)
        assert has_assign_violation == should_flag, trainee.assignment_id


if __name__ == "__main__":
    print("test_audit_r23_findings module OK")
