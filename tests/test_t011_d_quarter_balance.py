"""ROTA-T011-D (tasks/ROTA-T011-D/brief.md): explicit quarter-balance read
(A-5) and real carry-in in the assembler (B-5/W2). No persistence-import
boundary is required by this brief (unlike T011-A/B/E) -- seeding uses
rota.persistence directly where convenient for precise control of hours.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

from rota.application.assembler import assemble_planning_state
from rota.application.balance_read import quarter_balance
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context, month_plan_readiness
from rota.application.durable_inputs import set_target_hours, update_employee, update_membership
from rota.application.open_month import open_month
from rota.application.plan_ops import plan_month
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
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
from rota.persistence.employee_repository import save_employee
from rota.persistence.work_balance_repository import save_work_balance_target

COORD = "COORD-T011D"
SITE = "SITE-T011D"
PROFILE = "PROFILE-T011D"
EMP_A = "EMP-T011D-A"
EMP_B = "EMP-T011D-B"
JUL = date(2026, 7, 1)
AUG = date(2026, 8, 1)
SEP = date(2026, 9, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE, display_name="Profile T011D", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn, *, employee_ids=(EMP_A,)) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coord T011D", True),
        site_profile=_profile(),
        site=Site(SITE, PROFILE, "Site T011D", True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    for employee_id in employee_ids:
        update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
        update_membership(
            conn, coordinator_id=COORD, site_id=SITE,
            membership=SiteMembership(employee_id, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
        )


def _fill_calendar(conn, month: date) -> None:
    days = calendar.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, d), False))


def _seed_month(conn, *, month: date, entries) -> None:
    """entries: list of (employee_id, day, hours). Builds one current
    ScheduleVersion for `month` with one REALIZED PRIMARY Assignment per
    entry -- direct persistence seeding, allowed by this brief."""
    demands, assignments = [], []
    for i, (employee_id, day, hours) in enumerate(entries):
        demand_id = f"DEM-{month.isoformat()}-{i}"
        start = datetime(month.year, month.month, day, 6, 0)
        end = start + timedelta(hours=hours)
        demands.append(ShiftDemand(demand_id, "", start, end, 1))
        assignments.append(Assignment(
            f"AS-{month.isoformat()}-{i}", "", employee_id, start, end,
            AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demand_id, None,
        ))
    lifecycle.create_schedule_version(
        conn, version_id=f"SV-{month.isoformat()}", site_id=SITE, month=month, parent_version_id=None,
        created_at=datetime(month.year, month.month, 1, 8, 0), created_by=COORD,
        applied_rule_version_ids=[], shift_demands=demands, assignments=assignments, deviations=[], effective_from=month,
    )


def test_1_quarter_balance_accumulates(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    for month in (JUL, AUG, SEP):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=month, target_hours=100)
    _seed_month(conn, month=JUL, entries=[(EMP_A, 1, 120)])
    _seed_month(conn, month=AUG, entries=[(EMP_A, 1, 96)])
    _seed_month(conn, month=SEP, entries=[(EMP_A, 1, 100)])

    balances, warnings = quarter_balance(conn, employee_id=EMP_A, quarter_first_month=JUL)
    assert warnings == []
    assert [b.month for b in balances] == [JUL, AUG, SEP]
    assert balances[1].quarter_balance != balances[1].month_balance
    assert balances[2].quarter_balance != balances[2].month_balance
    # cumulative: Jul +20, Aug -4 (cum 16), Sep 0 (cum 16)
    assert balances[0].quarter_balance == 20
    assert balances[1].quarter_balance == 16
    assert balances[2].quarter_balance == 16


def test_2_quarter_balance_degrades_never_raises(tmp_path) -> None:
    """A gap mid-quarter (or in a future month) must never surface
    MissingTargetHoursError out of this function -- empty result plus a
    warning naming the missing month is intentional, not an oversight."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=JUL, target_hours=100)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    # SEP (a future month relative to the quarter start) has no target_hours.

    balances, warnings = quarter_balance(conn, employee_id=EMP_A, quarter_first_month=JUL)
    assert balances == []
    assert len(warnings) == 1
    assert "2026-09" in warnings[0]


def test_3_quarter_balance_needs_no_coordinator_context(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    save_employee(conn, Employee(EMP_A, EMP_A, date(2020, 1, 1), None, False))
    save_work_balance_target(conn, employee_id=EMP_A, month=JUL, target_hours=100)
    save_work_balance_target(conn, employee_id=EMP_A, month=AUG, target_hours=100)
    save_work_balance_target(conn, employee_id=EMP_A, month=SEP, target_hours=100)

    balances, warnings = quarter_balance(conn, employee_id=EMP_A, quarter_first_month=JUL)
    assert warnings == []
    assert [b.month for b in balances] == [JUL, AUG, SEP]


def test_4_open_month_no_longer_lies(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=JUL, target_hours=100)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _seed_month(conn, month=JUL, entries=[(EMP_A, 1, 120)])
    _fill_calendar(conn, AUG)

    view = open_month(conn, site_id=SITE, month=AUG)
    wb = next(b for b in view.work_balances if b.employee_id == EMP_A)
    assert wb.quarter_balance != wb.month_balance


def test_5_first_month_of_quarter_has_zero_carry_in(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=JUL, target_hours=100)
    _seed_month(conn, month=JUL, entries=[(EMP_A, 1, 120)])
    _fill_calendar(conn, JUL)

    view = open_month(conn, site_id=SITE, month=JUL)
    wb = next(b for b in view.work_balances if b.employee_id == EMP_A)
    assert wb.quarter_balance == wb.month_balance


def test_6_missing_earlier_norm_does_not_block_plan(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    # ROTA-T058 (owner-authorized fixture fix, 2026-09-08): a single employee
    # covering every day of AUG now genuinely trips the new HARD
    # max-two-consecutive-PRIMARY-shifts rule -- this test is about the
    # missing-earlier-quarter-norm warning not blocking PLAN, not staffing
    # tightness, so a second employee restores real slack.
    _bootstrap(conn, employee_ids=(EMP_A, EMP_B))
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    # JUL (earlier month of the same quarter) has no target_hours.
    _fill_calendar(conn, AUG)

    readiness = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=AUG)
    assert readiness.ready

    state, warnings = assemble_planning_state(conn, site_id=SITE, month=AUG)
    assert any("2026-07" in w for w in warnings)

    result = plan_month(conn, site_id=SITE, month=AUG, coordinator_id=COORD, effective_from=AUG)
    assert result.status == "FEASIBLE"


def test_7_zero_carry_in_preserves_solver_input(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    _fill_calendar(conn, AUG)

    state, warnings = assemble_planning_state(conn, site_id=SITE, month=AUG)
    wb = next(b for b in state.work_balances if b.employee_id == EMP_A)
    assert wb.target_hours == 100
    assert wb.quarter_balance == wb.month_balance
    assert wb.unresolved_carryover == wb.month_balance
    assert any("2026-07" in w for w in warnings)


def test_8_target01_membership_unaffected_by_earlier_gap(tmp_path) -> None:
    """Direct evidence for FINDING D-1: the SET of (employee_id, target_hours)
    feeding TARGET-01 must be identical whether or not an earlier month's
    norm is missing -- only balance/warning fields may differ."""
    gap_conn = connect(tmp_path / "gap.db")
    _bootstrap(gap_conn, employee_ids=(EMP_A, EMP_B))
    set_target_hours(gap_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    set_target_hours(gap_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_B, month=JUL, target_hours=90)
    set_target_hours(gap_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_B, month=AUG, target_hours=90)
    _fill_calendar(gap_conn, AUG)
    gap_state, _ = assemble_planning_state(gap_conn, site_id=SITE, month=AUG)

    full_conn = connect(tmp_path / "full.db")
    _bootstrap(full_conn, employee_ids=(EMP_A, EMP_B))
    set_target_hours(full_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=JUL, target_hours=100)
    set_target_hours(full_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=AUG, target_hours=100)
    set_target_hours(full_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_B, month=JUL, target_hours=90)
    set_target_hours(full_conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_B, month=AUG, target_hours=90)
    _fill_calendar(full_conn, AUG)
    full_state, _ = assemble_planning_state(full_conn, site_id=SITE, month=AUG)

    gap_set = {(b.employee_id, b.target_hours) for b in gap_state.work_balances}
    full_set = {(b.employee_id, b.target_hours) for b in full_state.work_balances}
    assert gap_set == full_set == {(EMP_A, 100), (EMP_B, 90)}


def test_9_restart_yields_the_same_numbers(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _bootstrap(conn)
    for month in (JUL, AUG):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id=EMP_A, month=month, target_hours=100)
    _seed_month(conn, month=JUL, entries=[(EMP_A, 1, 120)])
    _fill_calendar(conn, AUG)
    before_quarter, _ = quarter_balance(conn, employee_id=EMP_A, quarter_first_month=JUL)
    before_view = open_month(conn, site_id=SITE, month=AUG)
    conn.close()

    reopened = connect(db_path)
    after_quarter, _ = quarter_balance(reopened, employee_id=EMP_A, quarter_first_month=JUL)
    after_view = open_month(reopened, site_id=SITE, month=AUG)
    assert before_quarter == after_quarter
    assert before_view.work_balances == after_view.work_balances
