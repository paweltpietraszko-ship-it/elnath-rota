"""ROTA-T036 (contract SHA 8b2519c, Codex preimplementation PASS on 6e202f8):
REST-01/WEEKLY-REST-01 persist an Employee target, never one of the
(possibly cross-context) assignment_ids -- rota/planning/validator.py gains
an explicit ViolationDetail.affected_employee_id seam;
rota/application/deviation_mapping.py routes exactly these two source
references through it. No persistence change, no HARD semantics change.

T36-01..T36-10 are focused unit-level proofs against ViolationDetail/
_affected_target directly. T36-11 is the mandatory real vertical: a genuine
cross-month REST-01 finding (August's persisted N-shift boundary Assignment
into September) materialized into a Deviation and persisted through the
real rota.persistence.schedule_lifecycle.create_schedule_version -- this
exact pipeline raised MalformedScheduleSnapshot before T036 (the ROTA-T034
round-2/3 audit finding) because deviation_mapping picked the cross-context
assignment_id as target; after T036 it must succeed with an Employee
target. T36-12 (WEEKLY-REST-01) stays at the mapper/validator level, no
duplicate full lifecycle proof needed per the frozen contract."""
from __future__ import annotations

from datetime import date, datetime, time

import pytest

from rota.application import bootstrap
from rota.application.assembler import assemble_planning_state
from rota.application.deviation_mapping import _BUILTIN_RULE_CATEGORY, _EMPLOYEE_TARGETED_SOURCES, _affected_target, materialize_deviations
from rota.application.errors import UnknownDeviationSource
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    DeviationCategory,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.validator import ViolationDetail, validate
from tests.support.minimal_state import PROFILE_ID as _MINIMAL_PROFILE_ID, SITE_ID as _MINIMAL_SITE_ID, base_state

SITE = "SITE-T036"
PROFILE = "PROF-T036"
COORD = "COORD-T036"
EMPLOYEE = "EMP-T036"
AUGUST = date(2026, 8, 1)
SEPTEMBER = date(2026, 9, 1)


# --- T36-01/T36-02: pure mapping picks the employee, ignoring assignment_ids[0] ---


def test_t36_01_rest01_targets_employee_even_with_cross_context_assignment_first():
    detail = ViolationDetail(
        "REST-01", ("cross-context-assignment", "target-version-assignment"),
        "REST-01: E1 ...", affected_employee_id="E1",
    )
    assert _affected_target(detail) == "E1"


def test_t36_02_weekly_rest01_targets_employee():
    detail = ViolationDetail("WEEKLY-REST-01", ("a1",), "WEEKLY-REST-01: E1 ...", affected_employee_id="E1")
    assert _affected_target(detail) == "E1"


# --- T36-03: fail closed without affected_employee_id, no message parsing ---


def test_t36_03_rest01_without_employee_id_fails_closed():
    detail = ViolationDetail("REST-01", ("a1", "a2"), "REST-01: E1 overlapping assignments")
    with pytest.raises(UnknownDeviationSource):
        _affected_target(detail)


def test_t36_03b_weekly_rest01_without_employee_id_fails_closed():
    detail = ViolationDetail("WEEKLY-REST-01", ("a1",), "WEEKLY-REST-01: E1 only 10.0h ...")
    with pytest.raises(UnknownDeviationSource):
        _affected_target(detail)


# --- T36-07/T36-08/T36-09: other rules are unaffected ---


def test_t36_07_other_assignment_rule_keeps_assignment_target():
    detail = ViolationDetail("LOAD-01", ("a1", "a2"), "LOAD-01: E1 over cap")
    assert _affected_target(detail) == "a1"


def test_t36_08_coverage_keeps_demand_target():
    detail = ViolationDetail("COVERAGE-01", (), "COVERAGE-01: gap", demand_ids=("D-1",))
    assert _affected_target(detail) == "D-1"


def test_t36_09_law_category_gate_is_by_exact_source_not_category():
    """WEEKLY-REST-01 and REST-01 both map to DeviationCategory.LAW (see
    _BUILTIN_RULE_CATEGORY), but the employee-target seam is gated on the
    exact source_reference string, never on category -- a hypothetical
    future LAW rule with a different name must not silently inherit this."""
    assert _BUILTIN_RULE_CATEGORY["REST-01"] == DeviationCategory.LAW
    assert _BUILTIN_RULE_CATEGORY["WEEKLY-REST-01"] == DeviationCategory.LAW
    assert _EMPLOYEE_TARGETED_SOURCES == frozenset({"REST-01", "WEEKLY-REST-01"})
    # A rule with no affected_employee_id and no assignment/demand ids must
    # still fail closed, not silently succeed just because it happens to
    # map to LAW.
    detail = ViolationDetail("SOME-FUTURE-LAW-RULE", (), "...")
    with pytest.raises(UnknownDeviationSource):
        _affected_target(detail)


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, _MINIMAL_SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# --- T36-05: real cross-Site REST pair -- validator names the Employee,
# no cross-context Assignment persistence lookup is ever needed ------------


def test_t36_05_cross_site_rest_targets_employee_without_assignment_lookup():
    employee = Employee("E1", "E1", date(2020, 1, 1), None, False)
    # A real, complete Assignment at a DIFFERENT Site, ending too close to
    # this Site's own assignment start -- state.other_site_assignments is
    # exactly the second cross-context source _check_rest folds into
    # all_assignments (alongside state.boundary_assignments, covered by
    # T36-11's cross-month case).
    other_site_assignment = Assignment(
        "OTHER-SITE-ASSIGN-1", "SV-OTHER-SITE", "E1", datetime(2026, 10, 1, 18, 0), datetime(2026, 10, 2, 6, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    target_demand = ShiftDemand("TARGET-D-1", "", datetime(2026, 10, 2, 8, 0), datetime(2026, 10, 2, 20, 0), 1, shift_kind=ShiftKind.D)
    target_assignment = Assignment(
        "TARGET-ASSIGN-1", "", "E1", target_demand.start_datetime, target_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, target_demand.demand_id, None,
    )
    state = base_state(
        employees=(employee,), memberships=(_membership("E1"),), shift_demands=(target_demand,),
        other_site_assignments=(other_site_assignment,),
    )
    report = validate(state, [target_assignment])
    rest_details = [d for d in report.violation_details if d.rule == "REST-01"]
    assert rest_details, "test setup invalid: no cross-Site REST-01 violation was raised"
    finding = rest_details[0]
    assert finding.affected_employee_id == "E1"
    # Diagnostic assignment_ids must still name both real Assignments --
    # T036 only changes the PERSISTED target, not validator diagnostics.
    assert set(finding.assignment_ids) == {"OTHER-SITE-ASSIGN-1", "TARGET-ASSIGN-1"}

    deviations = materialize_deviations(report.violation_details, site_rules=())
    rest_deviation = next(d for d in deviations if d.source_reference == "REST-01")
    assert rest_deviation.affected_assignment_or_employee == "E1"


# --- T36-06: WEEKLY-REST-01 boundary-dependent finding carries the employee ---


def _weekly_rest_state(*, with_boundary: bool):
    employee = Employee("E1", "E1", date(2020, 1, 1), None, False)
    site = Site(_MINIMAL_SITE_ID, _MINIMAL_PROFILE_ID, "Site X", True, planning_regime=SitePlanningRegime.OCHRONA)
    # One long current-month occupation leaves only the window's opening
    # stretch (month_start .. this assignment's start) free -- exactly the
    # stretch a same-Site boundary Assignment (previous month spilling into
    # day 1) shrinks. Every other gap in the 7-day window is already well
    # under WEEKLY_REST_REQUIRED_HOURS (35h) regardless of the boundary.
    long_assignment = Assignment(
        "WEEKLY-LONG-1", "", "E1", datetime(2026, 10, 2, 12, 0), datetime(2026, 10, 7, 20, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    boundary_assignments = ()
    if with_boundary:
        # Previous-month (September) work spilling into October 1 -- ends
        # 24h before long_assignment starts, so the opening free stretch
        # shrinks from 36h (month_start..Oct 2 12:00, PASSES) to 24h (FAILS).
        boundary_assignments = (
            Assignment(
                "SEPT-BOUNDARY-1", "SV-SEPTEMBER", "E1", datetime(2026, 9, 30, 4, 0), datetime(2026, 10, 1, 12, 0),
                AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
            ),
        )
    state = base_state(
        employees=(employee,), memberships=(_membership("E1"),), site=site,
        boundary_assignments=boundary_assignments,
    )
    return state, long_assignment


def test_t36_06a_control_without_boundary_has_no_weekly_rest_violation():
    """Control for T36-06: the exact same current-month content, with no
    boundary Assignment, must NOT trigger WEEKLY-REST-01 (opening stretch
    is 36h, at/above the 35h floor) -- proves the boundary Assignment is
    what actually decides the finding below, not the current-month content."""
    state, long_assignment = _weekly_rest_state(with_boundary=False)
    report = validate(state, [long_assignment])
    assert not any(d.rule == "WEEKLY-REST-01" for d in report.violation_details)


def test_t36_06b_boundary_dependent_weekly_rest_targets_employee():
    state, long_assignment = _weekly_rest_state(with_boundary=True)
    report = validate(state, [long_assignment])
    weekly_details = [d for d in report.violation_details if d.rule == "WEEKLY-REST-01"]
    assert weekly_details, "test setup invalid: boundary Assignment did not tip the window into violation"
    finding = weekly_details[0]
    assert finding.affected_employee_id == "E1"

    deviations = materialize_deviations(report.violation_details, site_rules=())
    weekly_deviation = next(d for d in deviations if d.source_reference == "WEEKLY-REST-01")
    assert weekly_deviation.category == DeviationCategory.LAW
    assert weekly_deviation.affected_assignment_or_employee == "E1"


# --- T36-11: real cross-month vertical: repro the exact T034-audit failure,
# now succeeding end to end through real persistence -----------------------


def _bootstrap_site(conn) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coord", True),
        site_profile=SiteProfile(
            PROFILE, "Profile", True,
            [StandardShift(ShiftKind.D, time(8, 0), time(20, 0), False, 1)],
            True, True, False, False, 1, 40,
        ),
        site=Site(SITE, PROFILE, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    from rota.persistence.employee_repository import save_employee, save_site_membership
    save_employee(conn, Employee(EMPLOYEE, "Employee One", date(2020, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership(EMPLOYEE, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def _seed_month_calendar(conn, month: date) -> None:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = month
    while day < next_month:
        save_calendar_day(conn, CalendarDay(day, False))
        day = date.fromordinal(day.toordinal() + 1)


def test_t36_11_cross_month_rest01_persists_with_employee_target_not_cross_context_assignment():
    conn = connect(":memory:")
    _bootstrap_site(conn)
    _seed_month_calendar(conn, SEPTEMBER)

    # August: one root ScheduleVersion with a single N-shift ending Sept 1
    # 06:00 -- this becomes September's boundary Assignment (cross-context).
    august_demand = ShiftDemand(
        "AUG-N-1", "", datetime(2026, 8, 31, 18, 0), datetime(2026, 9, 1, 6, 0), 1, shift_kind=ShiftKind.N,
    )
    august_assignment = Assignment(
        "AUG-ASSIGN-1", "", EMPLOYEE, august_demand.start_datetime, august_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, august_demand.demand_id, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-AUGUST", site_id=SITE, month=AUGUST, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[august_demand], assignments=[august_assignment], deviations=[],
        effective_from=AUGUST,
    )

    september_demand = ShiftDemand(
        "SEP-D-1", "", datetime(2026, 9, 1, 8, 0), datetime(2026, 9, 1, 20, 0), 1, shift_kind=ShiftKind.D,
    )
    september_assignment = Assignment(
        "SEP-ASSIGN-1", "", EMPLOYEE, september_demand.start_datetime, september_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, september_demand.demand_id, None,
    )

    # September: real PlanningState assembly must pick up August's PRIMARY
    # as a boundary Assignment (no exclusion applies -- SV-AUGUST is not the
    # target version and is currently the (SITE, AUGUST) current version).
    # shift_demands is pinned to just this one demand -- no current
    # September version exists yet, so leaving it unset would fall back to
    # a full profile-generated month of demands, producing unrelated
    # COVERAGE-01 noise this test has no interest in.
    state, _warnings = assemble_planning_state(conn, site_id=SITE, month=SEPTEMBER, shift_demands=[september_demand])
    assert any(a.assignment_id == "AUG-ASSIGN-1" for a in state.boundary_assignments), (
        "test setup invalid: August's Assignment did not become a boundary fact"
    )
    # Real HARD re-check: August's 06:00 end + September's 08:00 start is a
    # 2h gap, far under the legacy-default 11h REST-01 floor.
    report = validate(state, [september_assignment])
    rest_details = [d for d in report.violation_details if d.rule == "REST-01"]
    assert rest_details, "test setup invalid: no REST-01 violation was raised at all"
    finding = rest_details[0]
    assert finding.affected_employee_id == EMPLOYEE
    # T36-11 point 2/3/4: both diagnostic assignment_ids survive unchanged,
    # and the cross-context one (August's) is genuinely absent from the
    # target (September) content -- this is the exact precondition that
    # made the pre-T036 pipeline fail with MalformedScheduleSnapshot.
    assert finding.assignment_ids == ("AUG-ASSIGN-1", "SEP-ASSIGN-1")
    assert "AUG-ASSIGN-1" not in {a.assignment_id for a in [september_assignment]}

    deviations = materialize_deviations(report.violation_details, site_rules=())
    rest_deviation = next(d for d in deviations if d.source_reference == "REST-01")
    assert rest_deviation.category == DeviationCategory.LAW
    assert rest_deviation.affected_assignment_or_employee == EMPLOYEE

    # The real persistence write -- this exact call raised
    # MalformedScheduleSnapshot before T036 (target = "AUG-ASSIGN-1", not
    # resolvable in September's own assignments_by_id). After T036 it must
    # succeed, unchanged persistence code.
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEPTEMBER", site_id=SITE, month=SEPTEMBER, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[september_demand], assignments=[september_assignment], deviations=deviations,
        effective_from=SEPTEMBER,
    )

    snapshot = get_schedule_snapshot(conn, "SV-SEPTEMBER")
    saved = next(d for d in snapshot.deviations if d.source_reference == "REST-01")
    assert saved.affected_assignment_or_employee == EMPLOYEE

    conn.close()


if __name__ == "__main__":
    print("test_t036_rest_deviation_target module OK")
