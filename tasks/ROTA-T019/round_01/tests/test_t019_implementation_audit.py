"""Independent implementation-audit evidence for ROTA-T019 Round 3."""
from __future__ import annotations

import ast
import calendar
import inspect
from datetime import date, time

import rota.application.analytics_read as analytics_module
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import append_availability, set_target_hours, update_employee, update_membership
from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    ShiftKind,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect


MONTH = date(2026, 8, 1)
SITE = "SITE-T019-AUDIT"
COORD = "COORD-T019-AUDIT"
EMP = "EMP-T019-AUDIT"


def _seed_context(conn, membership_kind: MembershipKind) -> None:
    profile = SiteProfile(
        "PROFILE-T019-AUDIT", "Audit", True,
        [StandardShift(ShiftKind.D, time(6), time(18), False, 1)],
        False, True, False, False, 1, 999,
    )
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Audit", True),
        site_profile=profile,
        site=Site(SITE, profile.profile_id, "Audit", True),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    update_employee(
        conn, coordinator_id=COORD, site_id=SITE,
        employee=Employee(EMP, "Audit employee", date(2020, 1, 1), None, False),
    )
    update_membership(
        conn, coordinator_id=COORD, site_id=SITE,
        membership=SiteMembership(
            EMP, SITE, membership_kind, True,
            ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        ),
    )


def test_external_support_without_window_has_no_analytics_row(tmp_path) -> None:
    conn = connect(tmp_path / "external-no-window.db")
    _seed_context(conn, MembershipKind.EXTERNAL_SUPPORT)
    set_target_hours(
        conn, coordinator_id=COORD, site_id=SITE,
        employee_id=EMP, month=MONTH, target_hours=160,
    )
    assert analytics_module.analytics_for_site_month(conn, site_id=SITE, month=MONTH).rows == ()


def test_weekday_holiday_inside_absence_does_not_reduce_effective_target(tmp_path) -> None:
    conn = connect(tmp_path / "weekday-holiday.db")
    _seed_context(conn, MembershipKind.LOCAL)
    set_target_hours(
        conn, coordinator_id=COORD, site_id=SITE,
        employee_id=EMP, month=MONTH, target_hours=160,
    )
    for day_number in range(1, calendar.monthrange(2026, 8)[1] + 1):
        day = date(2026, 8, day_number)
        save_calendar_day(conn, CalendarDay(day, holiday=(day == date(2026, 8, 3))))
    append_availability(
        conn, coordinator_id=COORD, site_id=SITE,
        availability_id="AV-T019-AUDIT-HOLIDAY", employee_id=EMP,
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2026, 8, 3), end_date=date(2026, 8, 3), active=True,
    )
    row = analytics_module.analytics_for_site_month(conn, site_id=SITE, month=MONTH).rows[0]
    assert row.month_data.effective_target_hours == 160


def test_full_quarter_uses_canonical_compute_quarter_balance_owner() -> None:
    tree = ast.parse(inspect.getsource(analytics_module))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name) and node.func.id == "compute_quarter_balance"
            or isinstance(node.func, ast.Attribute) and node.func.attr == "compute_quarter_balance"
        )
    ]
    assert calls, "analytics full-quarter path bypasses canonical compute_quarter_balance()"
