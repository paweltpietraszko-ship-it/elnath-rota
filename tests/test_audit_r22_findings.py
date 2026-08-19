"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r22.txt.

R22-1: long/multi-year holiday history exceeded the hardcoded 0..744 CP-SAT
variable domain in the holiday fairness term, making the whole model
INFEASIBLE/invalid on a SOFT term even though the current demand had a
perfectly HARD-valid solution.

R22-2: the frozen-conflict DECISION_REQUIRED path assumed any diagnosed
frozen conflict explained the entire report, silently dropping a
co-occurring LOAD-01 violation (missing load_blocker) or an unrelated
inconsistency (dangling TRAINEE reference).

R22-3: the independent validator accepted a TRAINEE's
mentor_primary_assignment_id resolving to another TRAINEE instead of
requiring it to resolve to a PRIMARY.
"""
from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime, timedelta

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


def _full_month_calendar(month: date) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


# FINDING R22-1 -----------------------------------------------------------


def test_r22_1_long_holiday_history_does_not_break_the_model():
    employee_a = Employee("A", "A", date(2020, 1, 1), None, False)
    employee_b = Employee("B", "B", date(2020, 1, 1), None, False)
    # 63 historical 12h holiday shifts = 756h, over the old hardcoded 744h domain.
    history = tuple(
        Assignment(f"h{i}", "prev-v1", "A", datetime(2020, 1, 1) + timedelta(days=i), datetime(2020, 1, 1) + timedelta(days=i, hours=12),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None)
        for i in range(63)
    )
    calendar_days = (CalendarDay(date(2026, 10, 1), True),)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(DEMAND_D,), holiday_history=history, calendar_days=calendar_days,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0][0].employee_id == "B"


# FINDING R22-2 -------------------------------------------------------------


def test_r22_2a_frozen_conflict_with_concurrent_load01_includes_load_blocker():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    boundary = tuple(
        Assignment(f"f{d}", "test-v1", "A", datetime(2026, 9, d, 5, 0), datetime(2026, 9, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None)
        for d in range(25, 31)
    )
    frozen_demand = Assignment(
        "f-demand", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,),
        existing_assignments=boundary + (frozen_demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z tygodniowym czasem pracy" in conditions
    assert "Koliduje z zapisem: Chorobowe" in conditions


def test_r22_2b_frozen_conflict_with_dangling_reference_is_technical_error():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    mentee = Employee("MENTEE", "MENTEE", date(2026, 9, 1), None, False)
    frozen_conflict = Assignment(
        "frozen-1", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    dangling_trainee = Assignment(
        "dangling-t", "test-v1", "MENTEE", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "does-not-exist",
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee, mentee), memberships=(_local_membership("A"), _local_membership("MENTEE")),
        shift_demands=(DEMAND_D,), existing_assignments=(frozen_conflict, dangling_trainee),
        availability_records=(sick,), calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert "does-not-exist" in result.error_message


# FINDING R22-3 -------------------------------------------------------------


def test_r22_3_validator_rejects_trainee_referencing_trainee():
    real_primary = Assignment(
        "real-primary", "test-v1", "A", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    first_trainee = Assignment(
        "first-trainee", "test-v1", "MENTEE1", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "real-primary",
    )
    wrong_reference = Assignment(
        "wrong-reference", "test-v1", "MENTEE2", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "first-trainee",
    )
    state = base_state(shift_demands=(DEMAND_D,))
    report = validate(state, [real_primary, first_trainee, wrong_reference])
    assert not report.hard_pass
    assert any("wrong-reference" in v and "first-trainee" in v and "not PRIMARY" in v for v in report.violations)


if __name__ == "__main__":
    print("test_audit_r22_findings module OK")
