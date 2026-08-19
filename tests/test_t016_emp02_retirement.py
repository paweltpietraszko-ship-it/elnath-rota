"""ROTA-T016 (owner decision 2026-08-16): EMP-02 is retired. The program does
not decide whether an Employee may work; it plans for whoever the
coordinator has entered into the current SiteMembership roster. This module
proves, through public behavior (not grep/absence-of-function), that
Employee.active_from/active_to no longer gate eligibility, the independent
validator, DECISION_REQUIRED, or deviation categorization, while every other
still-active HARD rule (MEMBERSHIP-01, Availability, DAY_ONLY-01) continues
to block exactly as before.

Scenario 10 (persistence round-trip of legacy active_from/active_to) is not
duplicated here: tests/test_local_store_master_data.py::
test_b_employee_membership_and_window_round_trip_and_restart already proves
Employee (including active_from/active_to) round-trips through save/restart.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.application import plan_ops, training
from rota.application.deviation_mapping import category_for_rule
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_employee, save_site_membership
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.planning.eligibility import check_eligibility
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import SITE_ID, base_state
from tests.support.t009_fixtures import seed_real_object

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)

# Deliberately outside every DEMAND_D/assignment interval used below, on
# both sides, so every scenario genuinely exercises the retired gate rather
# than happening to satisfy it by accident.
FUTURE_ACTIVE_FROM = date(2026, 12, 1)
PAST_ACTIVE_TO = date(2026, 9, 1)


def _local_membership(employee_id: str, enabled: bool = True) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _external_membership(employee_id: str, enabled: bool = True) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.EXTERNAL_SUPPORT, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _external_window(employee_id: str) -> ExternalSupportWindow:
    return ExternalSupportWindow(
        f"win-{employee_id}", employee_id, SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None,
    )


# Scenario 1 -------------------------------------------------------------


def test_local_assignment_before_active_from_is_eligible():
    employee = Employee("A", "A", FUTURE_ACTIVE_FROM, None, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "FEASIBLE"


# Scenario 2 -------------------------------------------------------------


def test_local_assignment_after_active_to_is_eligible():
    employee = Employee("B", "B", date(2026, 1, 1), PAST_ACTIVE_TO, False)
    state = base_state(employees=(employee,), memberships=(_local_membership("B"),), shift_demands=(DEMAND_D,))
    result = plan(state)
    assert result.status == "FEASIBLE"


# Scenario 3 -------------------------------------------------------------


def test_external_support_assignment_outside_active_period_is_eligible():
    employee = Employee("C", "C", FUTURE_ACTIVE_FROM, None, False)
    result = check_eligibility(
        employee, _external_membership("C"), DEMAND_D, ShiftKind.D, base_state().profile,
        [], [_external_window("C")], SITE_ID,
    )
    assert result.eligible


# Scenario 4 -------------------------------------------------------------


def test_validator_does_not_flag_assignment_outside_active_period():
    employee = Employee("D", "D", FUTURE_ACTIVE_FROM, None, False)
    assignment = Assignment(
        "a-d1", "test-v1", "D", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    state = base_state(employees=(employee,), memberships=(_local_membership("D"),), shift_demands=(DEMAND_D,))
    report = validate(state, [assignment])
    assert report.hard_pass
    assert not any("EMP-02" in v for v in report.violations)


# Scenario 5 -------------------------------------------------------------


def test_disabled_membership_still_blocks_regardless_of_active_period():
    """T016 does not touch MEMBERSHIP-01 -- it remains the sole source of
    truth for roster membership. An employee squarely inside their active
    period is still rejected when membership.enabled is False."""
    employee = Employee("E", "E", date(2026, 1, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("E", enabled=False),), shift_demands=(DEMAND_D,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    # T013: MEMBERSHIP_DISABLED is coordinator-invisible (section E) -- the
    # planning outcome (still blocked) is what T016 guarantees, not the
    # visibility of the raw code.
    assert result.decision_payload.blocking_shift_demands
    assert not any(b.employee_id == "E" for b in result.decision_payload.blockers)


# Scenario 6 -------------------------------------------------------------


def test_availability_hard_still_blocks_employee_outside_active_period():
    """T016 does not touch Availability HARD gates -- an employee outside
    their (now inert) active period is still blocked by LEAVE_GRANTED, not
    let through because EMP-02 no longer applies."""
    employee = Employee("F", "F", FUTURE_ACTIVE_FROM, None, False)
    leave = AvailabilityRecord(
        "av-f", "av-f-v1", "F", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 1), date(2026, 10, 1), True, None, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("F"),), shift_demands=(DEMAND_D,),
        availability_records=(leave,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisem: Urlop" for b in result.decision_payload.blockers)


# Scenario 7 -------------------------------------------------------------


def test_frozen_future_assignment_outside_active_period_does_not_trigger_decision_required():
    employee = Employee("G", "G", FUTURE_ACTIVE_FROM, None, False)
    frozen = Assignment(
        "existing-g", "test-v1", "G", DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, DEMAND_D.demand_id, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_local_membership("G"),), shift_demands=(DEMAND_D,),
        existing_assignments=(frozen,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"


# Scenario 8 -------------------------------------------------------------


def test_category_for_rule_treats_emp02_as_unknown_inactive_source():
    try:
        category_for_rule("EMP-02", {})
    except Exception as exc:
        assert type(exc).__name__ == "UnknownDeviationSource"
    else:
        raise AssertionError("category_for_rule('EMP-02', {}) must not resolve to a known category")


# Scenario 9 -------------------------------------------------------------


def _seed_training_scenario(conn, month: date):
    """Plans+selects a real-object month, enables training with threshold=1,
    and returns (state, mentor, trainee_id) for a training-readiness test."""
    state = seed_real_object(conn, case_id="t016-training-readiness", month=month, seed=1601)
    plan_result = plan_ops.plan_month(conn, site_id=state.site.site_id, month=month, coordinator_id="COORD-1", effective_from=month)
    assert plan_result.status == "FEASIBLE"
    version = plan_ops.select_candidate(
        conn, site_id=state.site.site_id, month=month, coordinator_id="COORD-1", candidate=plan_result.candidates[0],
    )
    save_site_profile(conn, replace(
        state.profile, training_s_enabled=True, training_s_weekdays_only=False, training_s_default_readiness_threshold=1,
    ))
    assignments = get_schedule_snapshot(conn, version.version_id).assignments
    mentor = next(a for a in assignments if a.role == AssignmentRole.PRIMARY)
    trainee_id = next(e.employee_id for e in state.employees if e.employee_id != mentor.employee_id)
    return state, mentor, trainee_id


def test_training_readiness_counts_realized_trainee_before_active_from(tmp_path):
    """Moving Employee.active_from to AFTER training already happened must
    not change the historical readiness count or block promotion -- T016
    forbids active_from from becoming a back door into the same gate it
    retired."""
    month = date(2026, 8, 1)
    conn = connect(tmp_path / "rota.db")
    state, mentor, trainee_id = _seed_training_scenario(conn, month)
    trainee_employee = next(e for e in state.employees if e.employee_id == trainee_id)

    # Push active_from to well after the training assignment being recorded.
    save_employee(conn, replace(trainee_employee, active_from=date(2026, 12, 1)))
    membership = next(m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id)
    save_site_membership(conn, replace(
        membership, readiness_state=ReadinessState.NOT_READY, readiness_source=ReadinessSource.DEFAULT,
    ))

    training.mark_training_realized(
        conn, site_id=state.site.site_id, month=month, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        trainee_assignment=Assignment(
            "t016-trainee-1", "", trainee_id, mentor.start_datetime, mentor.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor.assignment_id,
        ),
    )

    promoted = next(m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id)
    assert promoted.readiness_state == ReadinessState.READY_FOR_PRIMARY
