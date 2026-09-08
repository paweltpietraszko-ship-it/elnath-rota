"""ROTA-T019 (tasks/ROTA-T019/brief.md): coordinator analytics read model
dedicated matrix. Direct rota.persistence seeding is used throughout for
precise control, matching tests/test_t011_d_quarter_balance.py convention.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

import pytest

from rota.planning.absence import IncompleteAbsenceCalendarError
from rota.application.analytics_read import (
    AnalyticsDataStatus,
    AnalyticsHoursScope,
    analytics_for_site_month,
)
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import (
    add_external_support_window,
    append_availability,
    set_target_hours,
    update_employee,
    update_membership,
)
from rota.application.open_month import open_month
from rota.application.balance_read import quarter_balance
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.domain import AvailabilityKind

COORD = "COORD-T019"
SITE = "SITE-T019"
SITE2 = "SITE-T019-B"
PROFILE = "PROFILE-T019"
PROFILE2 = "PROFILE-T019-B"
EMP_A = "EMP-T019-A"
EMP_B = "EMP-T019-B"
JUL = date(2026, 7, 1)
AUG = date(2026, 8, 1)
SEP = date(2026, 9, 1)


def _profile(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=True,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap_site(conn, *, site_id: str, profile_id: str) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id,
        coordinator=Coordinator(COORD, "Coord T019", True),
        site_profile=_profile(profile_id),
        site=Site(site_id, profile_id, site_id, True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, site_id, True),
    )


def _member(
    conn, *, site_id: str, employee_id: str, kind: MembershipKind = MembershipKind.LOCAL,
    enabled: bool = True, active_from=date(2020, 1, 1), active_to=None,
) -> None:
    update_employee(
        conn, coordinator_id=COORD, site_id=site_id,
        employee=Employee(employee_id, employee_id, active_from, active_to, False),
    )
    update_membership(
        conn, coordinator_id=COORD, site_id=site_id,
        membership=SiteMembership(employee_id, site_id, kind, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def _fill_calendar(conn, month: date) -> None:
    days = calendar.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, d), False))


def _seed_month(
    conn, *, site_id: str, month: date, entries, parent_version_id=None, version_id=None,
) -> str:
    """entries: (employee_id, day, hours, state). One PRIMARY Assignment per
    entry on a new ScheduleVersion; state defaults REALIZED."""
    version_id = version_id or f"SV-{site_id}-{month.isoformat()}"
    # assignment_id/demand_id are stable per (site, month, index) -- not per
    # version_id -- so a parent/child version pair sharing site+month can
    # preserve/transition the SAME assignment identity (NN provenance,
    # REALIZED preservation).
    demands, assignments = [], []
    for i, entry in enumerate(entries):
        employee_id, day, hours = entry[0], entry[1], entry[2]
        state = entry[3] if len(entry) > 3 else AssignmentState.REALIZED
        op_code = entry[4] if len(entry) > 4 else None
        demand_id = f"DEM-{site_id}-{month.isoformat()}-{i}"
        start = datetime(month.year, month.month, day, 6, 0)
        end = start + timedelta(hours=hours)
        demands.append(ShiftDemand(demand_id, "", start, end, 1))
        assignments.append(Assignment(
            f"AS-{site_id}-{month.isoformat()}-{i}", "", employee_id, start, end,
            AssignmentRole.PRIMARY, state, False, demand_id, None, op_code,
        ))
    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=parent_version_id,
        created_at=datetime(month.year, month.month, 1, 8, 0), created_by=COORD,
        applied_rule_version_ids=[], shift_demands=demands, assignments=assignments, deviations=[], effective_from=month,
    )
    return version_id


def _absence(conn, *, employee_id: str, kind: AvailabilityKind, start: date, end: date) -> None:
    """ROTA-T023 Checkpoint B: routed through the durable_inputs entry point
    (not the raw repository call) so absence_reference capture runs -- the
    canonical DailyAbsenceFact snapshot WorkBalance/analytics now consume is
    populated only via this path, same as production coordinator writes."""
    append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id=f"AV-{employee_id}-{start.isoformat()}",
        employee_id=employee_id, kind=kind, start_date=start, end_date=end, active=True,
    )


def _table_snapshot(conn) -> dict:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    return {t: conn.execute(f"SELECT * FROM {t}").fetchall() for t in tables}


def _setup_one_employee_month(conn, *, target=100, hours=88) -> None:
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=target)
    _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, hours)])
    _fill_calendar(conn, AUG)


def test_1_complete_one_employee_month(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _setup_one_employee_month(conn, target=100, hours=88)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view.hours_scope == AnalyticsHoursScope.ALL_SITES
    row = view.rows[0]
    assert row.employee_id == EMP_A and row.display_name == EMP_A
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    md = row.month_data
    assert md.target_hours == 100 and md.planned_hours == 0 and md.realized_hours == 88
    assert md.month_balance == 88 - 100
    assert md.effective_target_hours == 100
    assert md.quarter_balance is None and md.unresolved_carryover is None


def test_2_complete_quarter_running_balance(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    for month in (JUL, AUG, SEP):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=month, target_hours=100)
        _fill_calendar(conn, month)
    _seed_month(conn, site_id=SITE, month=JUL, entries=[(EMP_A, 1, 120)])
    _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, 96)])
    _seed_month(conn, site_id=SITE, month=SEP, entries=[(EMP_A, 1, 100)])

    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.AVAILABLE
    assert [m.month for m in row.quarter_months] == [JUL, AUG, SEP]
    assert row.quarter_months[0].quarter_balance == 20
    assert row.quarter_months[1].quarter_balance == 16
    assert row.quarter_months[2].quarter_balance == 16
    assert row.month_data == row.quarter_months[1]


def test_3_planned_and_realized_are_separate_no_double_count(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    _seed_month(conn, site_id=SITE, month=AUG, entries=[
        (EMP_A, 1, 40, AssignmentState.REALIZED), (EMP_A, 5, 30, AssignmentState.PLANNED),
    ])
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    md = view.rows[0].month_data
    assert md.realized_hours == 40 and md.planned_hours == 30
    assert md.month_balance == (40 + 30) - 100


def test_4_cancelled_nn_does_not_increase_hours(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    v1 = _seed_month(conn, site_id=SITE, month=AUG, entries=[
        (EMP_A, 1, 40, AssignmentState.REALIZED), (EMP_A, 10, 30, AssignmentState.PLANNED),
    ], version_id="SV-NN-V1")
    _seed_month(conn, site_id=SITE, month=AUG, entries=[
        (EMP_A, 1, 40, AssignmentState.REALIZED), (EMP_A, 10, 30, AssignmentState.CANCELLED, "NN"),
    ], parent_version_id=v1, version_id="SV-NN-V2")
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    md = view.rows[0].month_data
    assert md.realized_hours == 40 and md.planned_hours == 0


def test_5_and_6_historical_version_not_counted_then_restore_switches(tmp_path, monkeypatch) -> None:
    # ROTA-T057 follow-up (2026-09-07): restore_schedule_version now refuses
    # a live month (Przelicz Plan is the only way to change one) -- AUG
    # (2026-08-01) is otherwise already in the past relative to real
    # wall-clock "now", which is incidental here (this test is about
    # restore switching analytics data, not liveness), so "now" is frozen
    # to before AUG.
    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 15)

    monkeypatch.setattr(lifecycle, "datetime", _FixedDateTime)
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    v1 = _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, 50, AssignmentState.PLANNED)], version_id="SV-V1")
    view_v1 = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view_v1.rows[0].month_data.planned_hours == 50

    _seed_month(
        conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, 90, AssignmentState.PLANNED)],
        parent_version_id=v1, version_id="SV-V2",
    )
    view_v2 = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view_v2.rows[0].month_data.planned_hours == 90  # v1's 50h no longer counted

    lifecycle.restore_schedule_version(conn, site_id=SITE, month=AUG, version_id=v1)
    view_restored = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view_restored.rows[0].month_data.planned_hours == 50


def test_7_reopen_restart_identical(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _setup_one_employee_month(conn, target=100, hours=88)
    before = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    conn.close()
    reopened = connect(db_path)
    after = analytics_for_site_month(reopened, site_id=SITE, month=AUG)
    assert before == after


def test_8_requested_month_missing_target(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.UNAVAILABLE
    assert row.month_data is None and row.quarter_months == ()
    assert len(row.warnings) == 1
    assert row.warnings[0] == (
        f"analytics unavailable for employee '{EMP_A}', month {AUG.isoformat()}: missing target_hours"
    )


def test_9_other_quarter_month_missing_target(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    # JUL (earlier quarter month) has no target_hours.
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    assert row.month_data is not None and row.month_data.target_hours == 100
    assert row.quarter_months == ()
    assert row.month_data.quarter_balance is None and row.month_data.unresolved_carryover is None
    assert row.warnings[0] == f"quarter analytics unavailable for employee '{EMP_A}': missing target_hours for {JUL.isoformat()}"


def test_10_requested_month_incomplete_calendar_with_qualifying_absence(tmp_path) -> None:
    """ROTA-T041 OWNER-T041-02 superseded the old T023 "SICK_LEAVE has no
    PRE_PLAN_LEAVE path" rule (see absence_reference_repository.py's
    _resolve_no_accepted_plan_day docstring): a SICK_LEAVE with no accepted
    plan anywhere now resolves the same flat 8h/qualified-workday total as
    pre-plan LEAVE_GRANTED -- which requires a complete CalendarDay for the
    month to know which days are workdays. With no CalendarDay entries for
    AUG at all, recording the absence itself now fails fast at write time
    (IncompleteAbsenceCalendarError), rather than degrading gracefully to
    an UNAVAILABLE analytics row read later -- updated from the superseded
    MISSING-reference expectation accordingly."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    # No CalendarDay entries for AUG at all.
    with pytest.raises(IncompleteAbsenceCalendarError):
        _absence(conn, employee_id=EMP_A, kind=AvailabilityKind.SICK_LEAVE, start=date(2026, 8, 3), end=date(2026, 8, 3))


@pytest.mark.skip(
    reason="ROTA-TEST-CLEANUP (2026-09-08): this test's scenario is no longer "
    "constructible. ROTA-T041 OWNER-T041-02 made a SICK_LEAVE-no-accepted-plan "
    "capture require a complete CalendarDay for its own month (see "
    "test_10/test_12, fixed in this same cleanup) -- so JUL's absence with "
    "JUL's calendar left incomplete (the whole premise here) now fails fast "
    "at _absence()/write time with IncompleteAbsenceCalendarError, never "
    "reaching analytics_for_site_month to produce the "
    "MONTH_AVAILABLE_QUARTER_UNAVAILABLE-via-incomplete-calendar-in-another-"
    "month shape this test asserts. Filling JUL's calendar too makes the "
    "absence fully resolvable (verified: status becomes plain AVAILABLE, "
    "quarter fully available) -- a different, no-longer-interesting scenario. "
    "Needs an owner/architect decision: is there still a real product path "
    "to MONTH_AVAILABLE_QUARTER_UNAVAILABLE for a different reason (e.g. a "
    "genuine multi-site resolution ambiguity), or should this test be "
    "deleted as testing dead ground? Flagged, not decided here.",
)
def test_11_other_quarter_month_incomplete_reference_blocks_quarter_only(tmp_path) -> None:
    """ROTA-T023 Checkpoint B: JUL's qualifying SICK_LEAVE has no accepted
    plan anywhere -- MISSING POST_PLAN_REFERENCE, discovered lazily at read
    time (capture itself needs no CalendarDay for this branch), same
    month-available/quarter-unavailable shape as the superseded
    CalendarDay-completeness oracle this replaces (brief.md section 18)."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    for month in (JUL, AUG, SEP):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=month, target_hours=100)
    _fill_calendar(conn, AUG)
    _absence(conn, employee_id=EMP_A, kind=AvailabilityKind.SICK_LEAVE, start=date(2026, 7, 3), end=date(2026, 7, 3))
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    assert row.month_data is not None
    assert row.quarter_months == ()
    assert row.warnings[0].startswith(f"quarter analytics unavailable for employee '{EMP_A}', month {JUL.isoformat()}: ")


def test_12_sick_leave_with_no_accepted_plan_uses_weekday_holiday_exclusion(tmp_path) -> None:
    """ROTA-T041 OWNER-T041-02 superseded the T023 Checkpoint B rule this
    test originally locked in (brief.md section 18: "SICK_LEAVE has no
    PRE_PLAN_LEAVE path, reference is MISSING regardless of CalendarDay
    completeness"). A SICK_LEAVE with no accepted plan anywhere now resolves
    via the same flat 8h/qualified-workday arithmetic as pre-plan
    LEAVE_GRANTED (_resolve_no_accepted_plan_day), so a complete calendar
    produces a real weekday/holiday-derived effective_target instead of
    MISSING/UNAVAILABLE. Aug 1-9 2026 with day 3 (Monday) a holiday: 4
    genuine workdays (4, 5, 6, 7) x 8h = 32h excluded from the 100h target."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    for d in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(2026, 8, d), holiday=(d == 3)))
    _absence(conn, employee_id=EMP_A, kind=AvailabilityKind.SICK_LEAVE, start=date(2026, 8, 1), end=date(2026, 8, 9))
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    assert row.month_data is not None
    assert row.month_data.effective_target_hours == 68
    assert row.warnings[0] == f"quarter analytics unavailable for employee '{EMP_A}': missing target_hours for {date(2026, 7, 1).isoformat()}"


def test_13_leave_granted_weekend_holiday_same_semantics(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    # Same weekday-holiday-inside-absence oracle as test_12, for LEAVE_GRANTED.
    for d in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(2026, 8, d), holiday=(d == 3)))
    _absence(conn, employee_id=EMP_A, kind=AvailabilityKind.LEAVE_GRANTED, start=date(2026, 8, 1), end=date(2026, 8, 9))
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    md = view.rows[0].month_data
    assert md.effective_target_hours == 100 - 8 * 4


def test_14_effective_target_algebra_holds(tmp_path) -> None:
    """ROTA-T023 Checkpoint B: uses LEAVE_GRANTED (PRE_PLAN_LEAVE), since
    SICK_LEAVE has no accepted plan in this fixture and would degrade the row
    to UNAVAILABLE (test_12) rather than exercising the algebra identity."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    _absence(conn, employee_id=EMP_A, kind=AvailabilityKind.LEAVE_GRANTED, start=date(2026, 8, 3), end=date(2026, 8, 3))
    _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 4, 40)])
    md = analytics_for_site_month(conn, site_id=SITE, month=AUG).rows[0].month_data
    assert md.effective_target_hours == md.planned_hours + md.realized_hours - md.month_balance


def test_15_cross_site_hours_are_global(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _bootstrap_site(conn, site_id=SITE2, profile_id=PROFILE2)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, 40)])
    _seed_month(conn, site_id=SITE2, month=AUG, entries=[(EMP_A, 2, 30)], version_id="SV-SITE2-AUG")
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert len(view.rows) == 1
    assert view.rows[0].month_data.realized_hours == 70
    assert view.hours_scope == AnalyticsHoursScope.ALL_SITES


def test_16_no_local_membership_on_requested_site_no_row(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _bootstrap_site(conn, site_id=SITE2, profile_id=PROFILE2)
    _member(conn, site_id=SITE2, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE2, employee_id=EMP_A, month=AUG, target_hours=100)
    _seed_month(conn, site_id=SITE2, month=AUG, entries=[(EMP_A, 1, 40)])
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view.rows == ()


def test_17_disabled_local_membership_no_row(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A, enabled=False)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view.rows == ()


def test_18_external_support_never_gets_a_row(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A, kind=MembershipKind.EXTERNAL_SUPPORT)
    _seed_month(conn, site_id=SITE, month=AUG, entries=[(EMP_A, 1, 40)])

    # T019-R3-3: the no-window variant must actually run, not just the
    # with-window one -- assert it BEFORE any ExternalSupportWindow exists.
    view_no_window = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view_no_window.rows == ()

    add_external_support_window(
        conn, coordinator_id=COORD, site_id=SITE,
        window=ExternalSupportWindow("WIN-1", EMP_A, SITE, datetime(2026, 8, 1), datetime(2026, 8, 31), True, None),
    )
    view_no_local = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view_no_local.rows == ()

    _member(conn, site_id=SITE, employee_id=EMP_B, kind=MembershipKind.LOCAL)
    _member(conn, site_id=SITE, employee_id=EMP_A, kind=MembershipKind.EXTERNAL_SUPPORT)  # unchanged, still X-Y
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_B, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    view_mixed = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert [r.employee_id for r in view_mixed.rows] == [EMP_B]


def test_18b_same_employee_local_and_external_gets_exactly_one_row(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _bootstrap_site(conn, site_id=SITE2, profile_id=PROFILE2)
    _member(conn, site_id=SITE, employee_id=EMP_A, kind=MembershipKind.LOCAL)
    _member(conn, site_id=SITE2, employee_id=EMP_A, kind=MembershipKind.EXTERNAL_SUPPORT)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert len(view.rows) == 1 and view.rows[0].employee_id == EMP_A


def test_19_emp02_active_period_ignored(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A, active_from=date(2099, 1, 1), active_to=None)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert len(view.rows) == 1 and view.rows[0].employee_id == EMP_A


def test_20_deterministic_ordering(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id="EMP-Z")
    _member(conn, site_id=SITE, employee_id="EMP-A")
    for emp in ("EMP-Z", "EMP-A"):
        for month in (JUL, AUG, SEP):
            set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=emp, month=month, target_hours=100)
        _fill_calendar(conn, JUL)
    _fill_calendar(conn, AUG)
    _fill_calendar(conn, SEP)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert [r.employee_id for r in view.rows] == ["EMP-A", "EMP-Z"]
    assert [m.month for m in view.rows[0].quarter_months] == [JUL, AUG, SEP]


def test_21_empty_local_roster(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    assert view.rows == () and view.site_id == SITE and view.month == AUG


def test_22_read_only_no_side_effects(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _setup_one_employee_month(conn)
    before = _table_snapshot(conn)
    analytics_for_site_month(conn, site_id=SITE, month=AUG)
    after = _table_snapshot(conn)
    assert before == after


def test_23_n_plus_1_oracle(tmp_path) -> None:
    conn_small = connect(tmp_path / "small.db")
    _bootstrap_site(conn_small, site_id=SITE, profile_id=PROFILE)
    _member(conn_small, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn_small, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn_small, AUG)
    queries_small = []
    conn_small.set_trace_callback(lambda sql: queries_small.append(sql))
    analytics_for_site_month(conn_small, site_id=SITE, month=AUG)
    conn_small.set_trace_callback(None)

    conn_big = connect(tmp_path / "big.db")
    _bootstrap_site(conn_big, site_id=SITE, profile_id=PROFILE)
    many = [f"EMP-{i}" for i in range(8)]
    for emp in many:
        _member(conn_big, site_id=SITE, employee_id=emp)
        set_target_hours(conn_big, coordinator_id=COORD, site_id=SITE, employee_id=emp, month=AUG, target_hours=100)
    _fill_calendar(conn_big, AUG)
    queries_big = []
    conn_big.set_trace_callback(lambda sql: queries_big.append(sql))
    analytics_for_site_month(conn_big, site_id=SITE, month=AUG)
    conn_big.set_trace_callback(None)

    assert len(queries_big) == len(queries_small)


def test_24_no_overtime_or_payroll_language(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _setup_one_employee_month(conn, target=50, hours=88)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    text = " ".join(row.warnings) + repr(row.month_data)
    for banned in ("nadgodziny", "overtime", "wynagrodzenie", "payroll", "ZUS"):
        assert banned not in text


def test_25_open_month_regression_unaffected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _setup_one_employee_month(conn)
    view = open_month(conn, site_id=SITE, month=AUG)
    assert any(b.employee_id == EMP_A for b in view.work_balances)


def test_26_quarter_balance_regression_unaffected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    balances, warnings = quarter_balance(conn, employee_id=EMP_A, quarter_first_month=JUL)
    assert balances == [] and len(warnings) == 1


def test_27_legal_zero_is_not_missing_data(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    assert row.month_data.planned_hours == 0 and row.month_data.realized_hours == 0


def test_28_no_blanket_calendar_requirement_without_qualifying_absence(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_site(conn, site_id=SITE, profile_id=PROFILE)
    _member(conn, site_id=SITE, employee_id=EMP_A)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    # No CalendarDay entries at all, and no absence records -- must not fail.
    view = analytics_for_site_month(conn, site_id=SITE, month=AUG)
    row = view.rows[0]
    assert row.status == AnalyticsDataStatus.MONTH_AVAILABLE_QUARTER_UNAVAILABLE
    assert row.month_data.target_hours == 100
