"""ROTA-T010-A tests (tasks/ROTA-T010/part_a_bootstrap_roster.md TESTY
OBOWIAZKOWE): bootstrap/resume, context completeness, month PLAN readiness,
current roster."""
from __future__ import annotations

import calendar
from datetime import date, time
from pathlib import Path

import pytest

from rota.application.bootstrap import (
    bootstrap_or_resume_coordinator_context,
    coordinator_context_completeness,
    current_roster,
    month_plan_readiness,
)
from rota.application.errors import CoordinatorContextAlreadyActive
from rota.domain import (
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
    SitePlanningRegime,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.work_balance_repository import save_work_balance_target
from rota.domain import CalendarDay

COORD = "COORD-A1"
SITE = "SITE-A1"
PROFILE = "PROFILE-A1"
EMP = "EMP-A1"
MONTH_A = date(2026, 9, 1)
MONTH_B = date(2026, 10, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE, display_name="Profile A1", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _site() -> Site:
    return Site(site_id=SITE, profile_id=PROFILE, display_name="Site A1", active=True, planning_regime=SitePlanningRegime.ORDINARY)


def _coordinator() -> Coordinator:
    return Coordinator(coordinator_id=COORD, display_name="Coord A1", active=True)


def _association(active: bool = True) -> CoordinatorSiteAssociation:
    return CoordinatorSiteAssociation(coordinator_id=COORD, site_id=SITE, active=active)


def _fill_calendar(conn, month: date) -> None:
    import calendar as cal
    days = cal.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        save_calendar_day(conn, CalendarDay(date=date(month.year, month.month, d), holiday=False))


def _bootstrap_full(conn) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=_coordinator(), site_profile=_profile(), site=_site(), association=_association(),
    )
    save_employee(conn, Employee(EMP, "Emp A1", date(2020, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership(EMP, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def test_empty_database_reports_full_missing_list(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    result = coordinator_context_completeness(conn, coordinator_id=COORD, site_id=SITE)
    assert not result.complete
    assert any("coordinator" in m for m in result.missing)
    assert any("site" in m for m in result.missing)
    assert any("Association" in m for m in result.missing)
    assert any("LOCAL" in m for m in result.missing)


def test_resume_partial_context_without_duplication(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD, site_id=SITE, coordinator=_coordinator())
    bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD, site_id=SITE, site_profile=_profile())
    bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD, site_id=SITE, site=_site())
    bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD, site_id=SITE, association=_association())
    result = coordinator_context_completeness(conn, coordinator_id=COORD, site_id=SITE)
    assert any("LOCAL" in m for m in result.missing)
    assert len(result.missing) == 1


def test_existing_active_context_requires_authorized_edit(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    with pytest.raises(CoordinatorContextAlreadyActive):
        bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD, site_id=SITE, coordinator=_coordinator())


def test_competing_bootstrap_after_activation_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    with pytest.raises(CoordinatorContextAlreadyActive):
        bootstrap_or_resume_coordinator_context(
            conn, coordinator_id=COORD, site_id=SITE, association=_association(),
        )


def test_complete_context_without_calendar_auto_heals_ready(tmp_path: Path) -> None:
    """ROTA-CALENDAR-AUTO-GENERATE (OWNER 2026-09-21): "ludzie nie będą
    pamiętać, że trzeba wejść w kalendarz i go wygenerować -- nikt tak nie
    robi." month_plan_readiness now silently fills the missing calendar
    instead of reporting it as an incompleteness."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    assert conn.execute("SELECT COUNT(*) FROM calendar_days").fetchone()[0] == 0
    result = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result.ready
    assert not any("CalendarDay" in m for m in result.missing)
    days_in_month = calendar.monthrange(MONTH_A.year, MONTH_A.month)[1]
    assert conn.execute("SELECT COUNT(*) FROM calendar_days").fetchone()[0] == days_in_month


def test_partial_calendar_auto_heals_without_overwriting_manual_entry(tmp_path: Path) -> None:
    """Fill-missing-only: a coordinator's own earlier manual entry (2026-09-01
    is an ordinary Tuesday, not a real PL holiday -- marking it holiday=True
    is a deliberate manual correction) must survive the auto-heal untouched."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    save_calendar_day(conn, CalendarDay(date=date(2026, 9, 1), holiday=True))
    result = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result.ready
    row = conn.execute(
        "SELECT holiday FROM calendar_days WHERE date = ?", (date(2026, 9, 1).isoformat(),),
    ).fetchone()
    assert bool(row[0]) is True
    days_in_month = calendar.monthrange(MONTH_A.year, MONTH_A.month)[1]
    count = conn.execute(
        "SELECT COUNT(*) FROM calendar_days WHERE date >= ? AND date < ?",
        (MONTH_A.isoformat(), MONTH_B.isoformat()),
    ).fetchone()[0]
    assert count == days_in_month


def test_full_calendar_ready(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    _fill_calendar(conn, MONTH_A)
    result = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result.ready
    assert result.missing == ()


def test_missing_target_hours_does_not_block_readiness(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    _fill_calendar(conn, MONTH_A)
    result = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result.ready
    assert any(EMP in w for w in result.target_hours_warnings)
    save_work_balance_target(conn, employee_id=EMP, month=MONTH_A, target_hours=160)
    result2 = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result2.ready
    assert result2.target_hours_warnings == ()


def test_readiness_auto_heals_independently_per_month(tmp_path: Path) -> None:
    """Each month's calendar is filled on its own request -- checking MONTH_A
    must not reach ahead and fill MONTH_B, and MONTH_B's own readiness check
    must still auto-heal it independently."""
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    result_a = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert result_a.ready
    count_b_before = conn.execute(
        "SELECT COUNT(*) FROM calendar_days WHERE date >= ? AND date < ?",
        (MONTH_B.isoformat(), date(2026, 11, 1).isoformat()),
    ).fetchone()[0]
    assert count_b_before == 0

    result_b = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_B)
    assert result_b.ready
    days_in_b = calendar.monthrange(MONTH_B.year, MONTH_B.month)[1]
    count_b_after = conn.execute(
        "SELECT COUNT(*) FROM calendar_days WHERE date >= ? AND date < ?",
        (MONTH_B.isoformat(), date(2026, 11, 1).isoformat()),
    ).fetchone()[0]
    assert count_b_after == days_in_b


def test_disabled_membership_removed_from_roster_but_history_kept(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    assert [e.employee_id for e in current_roster(conn, site_id=SITE)] == [EMP]

    save_site_membership(
        conn,
        SiteMembership(EMP, SITE, MembershipKind.LOCAL, False, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    assert current_roster(conn, site_id=SITE) == ()
    completeness = coordinator_context_completeness(conn, coordinator_id=COORD, site_id=SITE)
    assert any("LOCAL" in m for m in completeness.missing)

    save_site_membership(
        conn,
        SiteMembership(EMP, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    assert [e.employee_id for e in current_roster(conn, site_id=SITE)] == [EMP]
