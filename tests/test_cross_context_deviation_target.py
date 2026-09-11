"""ROTA-CROSS-CONTEXT-DEVIATION-TARGET (brief 6b9d64f, Codex preimplementation
PASS fabd835): a LAW-category Deviation may legally target an Assignment
from a cross-context source (same-Site adjacent month, or another Site)
that the validator itself compares against -- REST-01/WEEKLY-REST-01/
THIRD-CONSECUTIVE-SHIFT-01 all do this. `_validate_one_deviation` used to
accept only a same-version Assignment (or, for COVERAGE, a same-version
ShiftDemand), so any such cross-context target raised
MalformedScheduleSnapshot at persistence.

Since ROTA-T036, REST-01/WEEKLY-REST-01 no longer trigger this at all --
they always persist an Employee target (deviation_mapping._EMPLOYEE_TARGETED_
SOURCES), never the cross-context Assignment. THIRD-CONSECUTIVE-SHIFT-01
(ROTA-T058, also DeviationCategory.LAW) is NOT in that employee-targeted set,
but -- confirmed by direct code reading and A6 below -- it *also* cannot
reach this branch today: _check_third_consecutive_shift only ever collects
assignment_ids from validate()'s own `assignments` argument (the target
version's content); state.boundary_assignments contribute a DATE to the
streak, never an id. A boundary-only date is simply missing from
assignment_ids, never a foreign one.

CONCLUSION (a real finding, not an assumption): no currently-shipped LAW
rule can reach the new cross-context-Assignment branch today. This fix is
therefore defensive/forward-looking, matching the brief's abstract
Acceptance A1-A5 exactly (proven here via direct Deviation construction,
same technique the brief's own proposed SQL targets), while A6 documents
why THIRD-CONSECUTIVE-SHIFT-01 specifically does not exercise it. The
original historical crash (pre-ROTA-T036 REST-01) stays proven fixed by its
own unrelated mechanism in test_t036_rest_deviation_target.py's T36-11,
unaffected by this change (same-version/Employee-target code paths).
"""
from __future__ import annotations

from datetime import date, datetime, time

from rota.application import bootstrap
from rota.application.assembler import assemble_planning_state
from rota.application.deviation_mapping import materialize_deviations
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Deviation,
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
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.validator import validate

COORD = "COORD-XCTX"
SITE_A = "SITE-XCTX-A"
SITE_B = "SITE-XCTX-B"
PROFILE = "PROF-XCTX"
EMPLOYEE = "EMP-XCTX"
AUGUST = date(2026, 8, 1)
SEPTEMBER = date(2026, 9, 1)


def _bootstrap_site(conn, site_id: str) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id,
        coordinator=Coordinator(COORD, "Coord", True),
        site_profile=SiteProfile(
            PROFILE, "Profile", True,
            [StandardShift(ShiftKind.D, time(8, 0), time(20, 0), False, 1)],
            True, True, False, False, 1, 40,
        ),
        site=Site(site_id, PROFILE, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, site_id, True),
    )
    save_employee(conn, Employee(EMPLOYEE, "Employee One", date(2020, 1, 1), None, False))
    save_site_membership(
        conn, SiteMembership(EMPLOYEE, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def _seed_month_calendar(conn, month: date) -> None:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = month
    while day < next_month:
        save_calendar_day(conn, CalendarDay(day, False))
        day = date.fromordinal(day.toordinal() + 1)


def _create_current_version(conn, *, version_id: str, site_id: str, month: date, assignment: Assignment, demand: ShiftDemand) -> None:
    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=None,
        created_at=datetime(month.year, month.month, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[assignment], deviations=[], effective_from=month,
    )


def _fresh_conn():
    conn = connect(":memory:")
    _bootstrap_site(conn, SITE_A)
    _bootstrap_site(conn, SITE_B)
    _seed_month_calendar(conn, AUGUST)
    _seed_month_calendar(conn, SEPTEMBER)
    return conn


def _september_demand_and_assignment() -> tuple[ShiftDemand, Assignment]:
    demand = ShiftDemand("SEP-D-1", "", datetime(2026, 9, 1, 8, 0), datetime(2026, 9, 1, 20, 0), 1, shift_kind=ShiftKind.D)
    assignment = Assignment(
        "SEP-ASSIGN-1", "", EMPLOYEE, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    return demand, assignment


# --- A1: current cross-month (same Site) Assignment is a legal LAW target ---


def test_a1_current_adjacent_month_assignment_is_legal_law_target():
    conn = _fresh_conn()
    august_demand = ShiftDemand("AUG-D-1", "", datetime(2026, 8, 31, 8, 0), datetime(2026, 8, 31, 20, 0), 1, shift_kind=ShiftKind.D)
    august_assignment = Assignment(
        "AUG-ASSIGN-1", "", EMPLOYEE, august_demand.start_datetime, august_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, august_demand.demand_id, None,
    )
    _create_current_version(conn, version_id="SV-AUG", site_id=SITE_A, month=AUGUST, assignment=august_assignment, demand=august_demand)

    september_demand, september_assignment = _september_demand_and_assignment()
    deviation = Deviation(
        "DEV-0-THIRD-CONSECUTIVE-SHIFT-01", "", DeviationCategory.LAW, "THIRD-CONSECUTIVE-SHIFT-01",
        "AUG-ASSIGN-1", False, None, None, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[september_demand], assignments=[september_assignment], deviations=[deviation],
        effective_from=SEPTEMBER,
    )
    snapshot = get_schedule_snapshot(conn, "SV-SEP")
    assert snapshot.deviations[0].affected_assignment_or_employee == "AUG-ASSIGN-1"
    conn.close()


# --- A2: current cross-Site Assignment is a legal LAW target ---------------


def test_a2_current_other_site_assignment_is_legal_law_target():
    conn = _fresh_conn()
    other_site_demand = ShiftDemand("OTH-D-1", "", datetime(2026, 9, 1, 6, 0), datetime(2026, 9, 1, 18, 0), 1, shift_kind=ShiftKind.D)
    other_site_assignment = Assignment(
        "OTH-ASSIGN-1", "", EMPLOYEE, other_site_demand.start_datetime, other_site_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, other_site_demand.demand_id, None,
    )
    _create_current_version(conn, version_id="SV-OTH", site_id=SITE_B, month=SEPTEMBER, assignment=other_site_assignment, demand=other_site_demand)

    september_demand, september_assignment = _september_demand_and_assignment()
    deviation = Deviation(
        "DEV-0-REST-01-CROSS-SITE", "", DeviationCategory.LAW, "THIRD-CONSECUTIVE-SHIFT-01",
        "OTH-ASSIGN-1", False, None, None, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[september_demand], assignments=[september_assignment], deviations=[deviation],
        effective_from=SEPTEMBER,
    )
    snapshot = get_schedule_snapshot(conn, "SV-SEP")
    assert snapshot.deviations[0].affected_assignment_or_employee == "OTH-ASSIGN-1"
    conn.close()


# --- A3: a NON-current (superseded) version's Assignment stays rejected ----


def test_a3_noncurrent_version_assignment_is_still_rejected():
    conn = _fresh_conn()
    august_demand = ShiftDemand("AUG-D-1", "", datetime(2026, 8, 31, 8, 0), datetime(2026, 8, 31, 20, 0), 1, shift_kind=ShiftKind.D)
    august_assignment = Assignment(
        "AUG-ASSIGN-1", "", EMPLOYEE, august_demand.start_datetime, august_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, august_demand.demand_id, None,
    )
    _create_current_version(conn, version_id="SV-AUG-1", site_id=SITE_A, month=AUGUST, assignment=august_assignment, demand=august_demand)
    # Supersede August's version with an empty child -- SV-AUG-1 is no longer current.
    lifecycle.create_schedule_version(
        conn, version_id="SV-AUG-2", site_id=SITE_A, month=AUGUST, parent_version_id="SV-AUG-1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[], assignments=[], deviations=[], effective_from=date(2026, 8, 2),
    )

    september_demand, september_assignment = _september_demand_and_assignment()
    deviation = Deviation(
        "DEV-0-THIRD-CONSECUTIVE-SHIFT-01", "", DeviationCategory.LAW, "THIRD-CONSECUTIVE-SHIFT-01",
        "AUG-ASSIGN-1", False, None, None, None,
    )
    try:
        lifecycle.create_schedule_version(
            conn, version_id="SV-SEP", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
            created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
            shift_demands=[september_demand], assignments=[september_assignment], deviations=[deviation],
            effective_from=SEPTEMBER,
        )
        raised = False
    except MalformedScheduleSnapshot:
        raised = True
    assert raised, "a Deviation targeting a no-longer-current Assignment must still be rejected"
    conn.close()


# --- A4: a non-LAW category gets no cross-context Assignment exception ----


def test_a4_non_law_category_does_not_gain_cross_context_target():
    conn = _fresh_conn()
    august_demand = ShiftDemand("AUG-D-1", "", datetime(2026, 8, 31, 8, 0), datetime(2026, 8, 31, 20, 0), 1, shift_kind=ShiftKind.D)
    august_assignment = Assignment(
        "AUG-ASSIGN-1", "", EMPLOYEE, august_demand.start_datetime, august_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, august_demand.demand_id, None,
    )
    _create_current_version(conn, version_id="SV-AUG", site_id=SITE_A, month=AUGUST, assignment=august_assignment, demand=august_demand)

    september_demand, september_assignment = _september_demand_and_assignment()
    deviation = Deviation(
        "DEV-0-DAY_ONLY-01", "", DeviationCategory.PREFERENCE, "DAY_ONLY-01",
        "AUG-ASSIGN-1", False, None, None, None,
    )
    try:
        lifecycle.create_schedule_version(
            conn, version_id="SV-SEP", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
            created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
            shift_demands=[september_demand], assignments=[september_assignment], deviations=[deviation],
            effective_from=SEPTEMBER,
        )
        raised = False
    except MalformedScheduleSnapshot:
        raised = True
    assert raised, "only category=LAW may target a cross-context Assignment"
    conn.close()


# --- A5: existing COVERAGE same-version ShiftDemand exception is untouched -


def test_a5_coverage_same_version_demand_target_still_works():
    conn = _fresh_conn()
    september_demand, september_assignment = _september_demand_and_assignment()
    gap_demand = ShiftDemand("SEP-D-GAP", "", datetime(2026, 9, 2, 8, 0), datetime(2026, 9, 2, 20, 0), 1, shift_kind=ShiftKind.D)
    deviation = Deviation(
        "DEV-0-COVERAGE-01", "", DeviationCategory.COVERAGE, "COVERAGE-01",
        "SEP-D-GAP", False, None, None, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[september_demand, gap_demand], assignments=[september_assignment], deviations=[deviation],
        effective_from=SEPTEMBER,
    )
    snapshot = get_schedule_snapshot(conn, "SV-SEP")
    assert snapshot.deviations[0].affected_assignment_or_employee == "SEP-D-GAP"
    conn.close()


# --- A6: THIRD-CONSECUTIVE-SHIFT-01 (ROTA-T058) does NOT currently reach ---
# this branch -- documented here as a finding, not assumed. Unlike the
# pre-T036 REST-01 shape, _check_third_consecutive_shift only ever collects
# assignment_ids from the `assignments` argument passed to validate() (the
# target version's own content) -- state.boundary_assignments contribute a
# DATE to the streak, never an id to `ids`. A boundary-only date in the
# streak is therefore simply missing from assignment_ids, never a foreign
# one. This means no currently-shipped LAW rule can reach the new
# cross-context branch today; it is a defensive/forward-looking fix for the
# next rule (or reproduced historical fact) that names a real cross-context
# Assignment, exactly as REST-01/WEEKLY-REST-01 did before ROTA-T036.


def test_a6_third_consecutive_shift_never_emits_a_foreign_boundary_assignment_id():
    conn = _fresh_conn()
    aug31_demand = ShiftDemand("AUG-D-31", "", datetime(2026, 8, 31, 8, 0), datetime(2026, 8, 31, 20, 0), 1, shift_kind=ShiftKind.D)
    aug31_assignment = Assignment(
        "AUG-ASSIGN-31", "", EMPLOYEE, aug31_demand.start_datetime, aug31_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, aug31_demand.demand_id, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-AUGUST", site_id=SITE_A, month=AUGUST, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[aug31_demand], assignments=[aug31_assignment], deviations=[], effective_from=AUGUST,
    )

    sep1_demand = ShiftDemand("SEP-D-1", "", datetime(2026, 9, 1, 8, 0), datetime(2026, 9, 1, 20, 0), 1, shift_kind=ShiftKind.D)
    sep1_assignment = Assignment(
        "SEP-ASSIGN-1", "", EMPLOYEE, sep1_demand.start_datetime, sep1_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, sep1_demand.demand_id, None,
    )
    sep2_demand = ShiftDemand("SEP-D-2", "", datetime(2026, 9, 2, 8, 0), datetime(2026, 9, 2, 20, 0), 1, shift_kind=ShiftKind.D)
    sep2_assignment = Assignment(
        "SEP-ASSIGN-2", "", EMPLOYEE, sep2_demand.start_datetime, sep2_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, sep2_demand.demand_id, None,
    )
    state, _warnings = assemble_planning_state(conn, site_id=SITE_A, month=SEPTEMBER, shift_demands=[sep1_demand, sep2_demand])
    assert any(a.assignment_id == "AUG-ASSIGN-31" for a in state.boundary_assignments), (
        "test setup invalid: August 31 did not become a boundary fact"
    )
    report = validate(state, [sep1_assignment, sep2_assignment])
    details = [d for d in report.violation_details if d.rule == "THIRD-CONSECUTIVE-SHIFT-01"]
    assert details, "test setup invalid: no THIRD-CONSECUTIVE-SHIFT-01 violation was raised across Aug 31/Sep 1/Sep 2"
    # The boundary-only date (Aug 31) contributes no id at all -- ids never
    # names a cross-context Assignment for this rule as currently written.
    assert "AUG-ASSIGN-31" not in details[0].assignment_ids
    assert set(details[0].assignment_ids) == {"SEP-ASSIGN-1", "SEP-ASSIGN-2"}

    # Still persists cleanly either way -- both ids are same-version.
    deviations = materialize_deviations(report.violation_details, site_rules=())
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEPTEMBER", site_id=SITE_A, month=SEPTEMBER, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8, 0), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[sep1_demand, sep2_demand], assignments=[sep1_assignment, sep2_assignment],
        deviations=deviations, effective_from=SEPTEMBER,
    )
    conn.close()


if __name__ == "__main__":
    print("test_cross_context_deviation_target module OK")
