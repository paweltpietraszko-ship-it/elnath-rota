"""ROTA-T064 (tasks/ROTA-T064/brief.md section 10): minimal backend tests
for the fill-missing-only calendar month generator.
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, time

import pytest

from rota.application import store
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import generate_calendar_month, generate_calendar_years, set_calendar_day
from rota.application.errors import InvalidCoordinatorContext
from rota.domain import (
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Site,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
    ShiftKind,
)
from rota.persistence.calendar_repository import get_calendar_day, list_calendar_days

COORD = "COORD-T064"
SITE = "SITE-T064"
PROFILE = "PROFILE-T064"


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE, display_name="Profile T064", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coord T064", True),
        site_profile=_profile(),
        site=Site(SITE, PROFILE, "Site T064", True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )


def test_1_generate_future_month_creates_all_dates(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    month = date(2026, 11, 1)
    created = generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=month)
    days_in_month = _cal.monthrange(month.year, month.month)[1]
    assert created == days_in_month
    rows = list_calendar_days(conn, month, date(2026, 11, days_in_month))
    assert len(rows) == days_in_month
    assert {r.date.day for r in rows} == set(range(1, days_in_month + 1))


def test_2_pl_public_holiday_is_true_ordinary_day_is_false(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=date(2026, 11, 1))
    # 2026-11-11 is Narodowe Swieto Niepodleglosci (Independence Day), a
    # real PL public holiday; 2026-11-10 is an ordinary Tuesday.
    assert get_calendar_day(conn, date(2026, 11, 11)).holiday is True
    assert get_calendar_day(conn, date(2026, 11, 10)).holiday is False


def test_3_existing_manual_day_survives_regenerate_unchanged(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    # Coordinator manually marks an ordinary day (2026-11-10, real PL
    # holiday library says False) as a holiday BEFORE generating -- the
    # generator must never overwrite this fill-missing-only.
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(2026, 11, 10), True))
    generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=date(2026, 11, 1))
    assert get_calendar_day(conn, date(2026, 11, 10)).holiday is True


def test_4_second_generation_is_idempotent(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    month = date(2026, 11, 1)
    first = generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=month)
    second = generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=month)
    assert first > 0
    assert second == 0
    days_in_month = _cal.monthrange(month.year, month.month)[1]
    rows = list_calendar_days(conn, month, date(2026, 11, days_in_month))
    assert len(rows) == days_in_month


def test_5_requires_active_coordinator_context(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    with pytest.raises(InvalidCoordinatorContext):
        generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=date(2026, 11, 1))
    rows = conn.execute("SELECT COUNT(*) FROM calendar_days").fetchall()
    assert rows[0][0] == 0


def test_6_rejects_non_first_of_month(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    with pytest.raises(ValueError):
        generate_calendar_month(conn, coordinator_id=COORD, site_id=SITE, month=date(2026, 11, 15))


# --- ROTA-CALENDAR-MULTI-YEAR-GENERATE (OWNER 2026-09-21) -------------------


def test_7_generate_years_fills_every_month_in_range(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    start = date(2026, 11, 1)
    created = generate_calendar_years(conn, coordinator_id=COORD, site_id=SITE, start_month=start, years=2)
    end_exclusive = date(2028, 11, 1)
    days_in_range = (end_exclusive - start).days
    assert created == days_in_range
    # Spot-check the first and last months of the range are both complete.
    assert get_calendar_day(conn, date(2026, 11, 1)) is not None
    assert get_calendar_day(conn, date(2028, 10, 31)) is not None


def test_8_generate_years_never_overwrites_a_manual_correction(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    # A coordinator manually marks a real workday as a holiday (e.g. a
    # company-specific day off) BEFORE the bulk generate runs.
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(2026, 11, 10), True))
    generate_calendar_years(conn, coordinator_id=COORD, site_id=SITE, start_month=date(2026, 11, 1), years=1)
    assert get_calendar_day(conn, date(2026, 11, 10)).holiday is True


def test_9_generate_years_rejects_non_first_of_month(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn)
    with pytest.raises(ValueError):
        generate_calendar_years(conn, coordinator_id=COORD, site_id=SITE, start_month=date(2026, 11, 15), years=1)
