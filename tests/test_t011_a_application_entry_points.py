"""ROTA-T011-A (tasks/ROTA-T011-A/brief.md): CalendarDay write, store
open/migrate, and availability-chain history -- the three application-layer
entry points that close Z-1/Z-3/Z-7b. This file must never import anything
from rota.persistence -- that is the actual subject of the task (test 9).
"""
from __future__ import annotations

import calendar
from datetime import date, time

import pytest

from rota.application import store
from rota.application.availability_matrix import availability_history
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context, month_plan_readiness
from rota.application.durable_inputs import append_availability, set_calendar_day, update_employee, update_membership
from rota.application.errors import IncompleteCalendarData, InvalidCoordinatorContext
from rota.application.open_month import open_month
from rota.domain import (
    AvailabilityKind,
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

COORD = "COORD-T011A"
SITE = "SITE-T011A"
PROFILE = "PROFILE-T011A"
EMP = "EMP-T011A"
MONTH = date(2026, 9, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE, display_name="Profile T011A", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap_context(conn) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coord T011A", True),
        site_profile=_profile(),
        site=Site(SITE, PROFILE, "Site T011A", True),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee(EMP, "Emp T011A", date(2020, 1, 1), None, False))
    update_membership(
        conn, coordinator_id=COORD, site_id=SITE,
        membership=SiteMembership(EMP, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def _fill_calendar(conn, month: date) -> None:
    days = calendar.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(month.year, month.month, d), False))


def test_1_calendar_flips_month_readiness(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_context(conn)
    before = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert not before.ready
    assert any("missing CalendarDay for" in m for m in before.missing)

    _fill_calendar(conn, MONTH)
    after = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert after.ready


def test_2_open_month_stops_raising_after_calendar_is_filled(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_context(conn)
    with pytest.raises(IncompleteCalendarData):
        open_month(conn, site_id=SITE, month=MONTH)

    _fill_calendar(conn, MONTH)
    view = open_month(conn, site_id=SITE, month=MONTH)
    assert view.site.site_id == SITE


def test_3_set_calendar_day_upserts_not_duplicates(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_context(conn)
    target = date(2026, 9, 1)
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(target, False))
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(target, True))

    rows = conn.execute("SELECT COUNT(*) FROM calendar_days WHERE date = ?", (target.isoformat(),)).fetchall()
    assert rows[0][0] == 1
    holiday = conn.execute("SELECT holiday FROM calendar_days WHERE date = ?", (target.isoformat(),)).fetchone()
    assert bool(holiday[0]) is True


def test_4_set_calendar_day_requires_active_context(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    with pytest.raises(InvalidCoordinatorContext):
        set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(2026, 9, 1), False))
    rows = conn.execute("SELECT COUNT(*) FROM calendar_days").fetchall()
    assert rows[0][0] == 0


def test_5_open_store_on_fresh_path_yields_a_working_current_schema(tmp_path) -> None:
    db_path = tmp_path / "fresh.db"
    assert not db_path.exists()
    conn = store.open_store(db_path)
    assert db_path.exists()

    _bootstrap_context(conn)
    _fill_calendar(conn, MONTH)
    readiness = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert readiness.ready


def test_6_open_store_is_observably_idempotent(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap_context(conn)
    _fill_calendar(conn, MONTH)
    conn.close()

    reopened = store.open_store(db_path)
    readiness = month_plan_readiness(reopened, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert readiness.ready
    reopened.close()

    reopened_again = store.open_store(db_path)
    readiness_again = month_plan_readiness(reopened_again, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert readiness_again.ready


def test_7_restart_without_touching_persistence(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap_context(conn)
    _fill_calendar(conn, MONTH)
    conn.close()

    reopened = store.open_store(db_path)
    readiness = month_plan_readiness(reopened, coordinator_id=COORD, site_id=SITE, month=MONTH)
    assert readiness.ready


def test_8_availability_history_returns_full_chain_in_order(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_context(conn)

    first = append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-CHAIN-1", employee_id=EMP,
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 9, 10), end_date=date(2026, 9, 12),
        active=True,
    )
    second = append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-CHAIN-1", employee_id=EMP,
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 9, 10), end_date=date(2026, 9, 11),
        active=True,
    )

    history = availability_history(conn, availability_id="AV-CHAIN-1")
    assert [r.availability_version_id for r in history] == [first.availability_version_id, second.availability_version_id]
    assert second.supersedes_availability_version_id == first.availability_version_id

    assert availability_history(conn, availability_id="AV-UNKNOWN-FAMILY") == []


def test_9_this_file_never_imports_rota_persistence() -> None:
    import ast
    from pathlib import Path

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("rota.persistence"), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("rota.persistence"), node.module
