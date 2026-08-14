"""ROTA-T011-E (tasks/ROTA-T011-E/brief.md) TEST 1: one continuous scenario
from an empty database file to a finalized, restarted schedule, through
rota.application.* only -- no rota.persistence import anywhere in this file
(checked mechanically by the auditor, e.g. `rg "rota.persistence"` on this
file returns zero hits; DEPENDENCY BOUNDARY makes this a FAIL condition, not
a style preference).
"""
from __future__ import annotations

import calendar as _calendar
from datetime import date, time
from pathlib import Path

from rota.application import bootstrap, durable_inputs, lifecycle_ops, manual_edit, open_month, plan_ops, store
from rota.application.assembler import assemble_planning_state
from rota.domain import (
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
)

COORD = "COORD-E1"
SITE_ID = "SITE-E1"
PROFILE_ID = "PROFILE-E1"
EMPLOYEES = ("EMP-E1-1", "EMP-E1-2")
MONTH = date(2026, 11, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID, display_name="E1 Profile", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _site() -> Site:
    return Site(site_id=SITE_ID, profile_id=PROFILE_ID, display_name="Site E1", active=True)


def _coordinator() -> Coordinator:
    return Coordinator(coordinator_id=COORD, display_name="Coord E1", active=True)


def _association() -> CoordinatorSiteAssociation:
    return CoordinatorSiteAssociation(coordinator_id=COORD, site_id=SITE_ID, active=True)


def test_1_full_happy_path_zero_edge_cases(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"

    # step 1: open a nonexistent store -- creates and migrates it.
    conn = store.open_store(db_path)

    # step 2: bootstrap in two partial calls, proving resume (not just a
    # first save).
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID, coordinator=_coordinator(), site_profile=_profile(),
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID, site=_site(), association=_association(),
    )

    # step 3: a several-person LOCAL roster.
    for employee_id in EMPLOYEES:
        durable_inputs.update_employee(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False),
        )
        durable_inputs.update_membership(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            membership=SiteMembership(
                employee_id, SITE_ID, MembershipKind.LOCAL, True,
                ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            ),
        )

    # step 4: target_hours for every employee.
    for employee_id in EMPLOYEES:
        durable_inputs.set_target_hours(
            conn, coordinator_id=COORD, site_id=SITE_ID, employee_id=employee_id, month=MONTH, target_hours=80,
        )

    # step 5: full CalendarDay coverage for the planned month.
    days_in_month = _calendar.monthrange(MONTH.year, MONTH.month)[1]
    for day in range(1, days_in_month + 1):
        durable_inputs.set_calendar_day(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            day=CalendarDay(date=date(MONTH.year, MONTH.month, day), holiday=False),
        )

    # step 6: readiness must be true BEFORE PLAN is attempted -- proves the
    # readiness read reflects exactly what plan_month is about to accept.
    readiness = bootstrap.month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE_ID, month=MONTH)
    assert readiness.ready is True
    assert readiness.missing == ()

    # step 7: PLAN.
    result = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]

    # step 8: persist the coordinator's chosen candidate.
    version = plan_ops.select_candidate(
        conn, site_id=SITE_ID, month=MONTH, candidate=candidate, coordinator_id=COORD,
    )

    # step 9: read back -- confirms the current version and inputs.
    view = open_month.open_month(conn, site_id=SITE_ID, month=MONTH)
    assert view.current_version is not None
    assert view.current_version.version_id == version.version_id
    assert {e.employee_id for e in view.employees} == set(EMPLOYEES)

    # step 10: one legal manual correction -- a PLANNED PRIMARY the employee
    # did not actually work becomes NN.
    target = next(a for a in candidate if a.role == AssignmentRole.PRIMARY and a.state == AssignmentState.PLANNED)
    manual_edit.mark_not_worked(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
        assignment_id=target.assignment_id,
    )

    # step 11: revalidate, then finalize with the exact acknowledged
    # Deviation set read from the application layer (not fabricated here).
    lifecycle_ops.revalidate(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD)
    state, _warnings = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    acknowledged_ids = {d.deviation_id for d in state.deviations}
    assert acknowledged_ids  # the NN correction leaves a real coverage gap to acknowledge
    final_version = lifecycle_ops.finalize(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, acknowledged_deviation_ids=acknowledged_ids,
    )
    assert final_version.status.value.startswith("FINAL")

    # step 12: restart -- close and reopen the same file, compare state.
    view_before_restart = open_month.open_month(conn, site_id=SITE_ID, month=MONTH)
    conn.close()

    reopened = store.open_store(db_path)
    view_after_restart = open_month.open_month(reopened, site_id=SITE_ID, month=MONTH)

    assert view_after_restart.current_version is not None
    assert view_after_restart.current_version.version_id == view_before_restart.current_version.version_id
    assert view_after_restart.current_version.status == view_before_restart.current_version.status
    assert view_after_restart.current_version.status.value.startswith("FINAL")
    assert {e.employee_id for e in view_after_restart.employees} == {e.employee_id for e in view_before_restart.employees}
    assert view_after_restart.site.site_id == view_before_restart.site.site_id
    reopened.close()
