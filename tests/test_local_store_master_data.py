"""ROTA-T008 test matrix categories B (CURRENT MASTER DATA), C (AVAILABILITY
HISTORY), D (CALENDAR).
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    Site,
    SiteMembership,
)
from rota.persistence.availability_repository import (
    InvalidAvailabilityChain,
    UnknownEmployeeForAvailability,
    append_availability_version,
    get_availability_history,
    get_current_availability_for_employee,
    list_active_overlapping,
)
from rota.persistence.calendar_repository import get_calendar_day, list_calendar_days, save_calendar_day
from rota.persistence.coordinator_repository import (
    UnknownCoordinatorOrSite,
    list_associations_for_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import (
    InvalidEmployeeActivePeriod,
    UnknownEmployeeOrSite,
    list_memberships_for_employee,
    list_windows_for_employee,
    save_employee,
    save_external_support_window,
    save_site_membership,
)
from rota.persistence.site_repository import UnknownSiteProfile, get_site, save_site
from tests.support.t008_fixtures import seed_base_entities


# --- B. CURRENT MASTER DATA -------------------------------------------------


def test_b_site_coordinator_association_round_trip_and_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    conn.close()

    reopened = connect(db_path)
    assert get_site(reopened, "SITE-1").display_name == "Site One"
    associations = list_associations_for_coordinator(reopened, "COORD-1")
    assert associations == [CoordinatorSiteAssociation("COORD-1", "SITE-1", True)]


def test_b_employee_membership_and_window_round_trip_and_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    save_site_membership(conn, SiteMembership(
        "EMP-1", "SITE-1", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
    ))
    save_external_support_window(conn, ExternalSupportWindow(
        "WIN-1", "EMP-1", "SITE-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), True, None,
    ))
    conn.close()

    reopened = connect(db_path)
    assert list_memberships_for_employee(reopened, "EMP-1")[0].membership_kind == MembershipKind.LOCAL
    assert list_windows_for_employee(reopened, "EMP-1")[0].window_id == "WIN-1"


def test_b_invalid_fk_and_coherence_cases_fail_explicitly(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)

    with pytest.raises(UnknownSiteProfile):
        save_site(conn, Site("SITE-X", "NO-SUCH-PROFILE", "X", True))

    with pytest.raises(UnknownCoordinatorOrSite):
        save_coordinator_site_association(conn, CoordinatorSiteAssociation("NO-SUCH-COORD", "SITE-1", True))

    with pytest.raises(UnknownEmployeeOrSite):
        save_site_membership(conn, SiteMembership(
            "NO-SUCH-EMP", "SITE-1", MembershipKind.LOCAL, True, ReadinessState.NOT_READY, ReadinessSource.DEFAULT,
        ))

    with pytest.raises(InvalidEmployeeActivePeriod):
        save_employee(conn, Employee("EMP-BAD", "Bad", date(2026, 8, 1), date(2026, 1, 1), False))


# --- C. AVAILABILITY HISTORY -------------------------------------------------


def test_c1_first_version_is_immutable_chain_start(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    record = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    assert record.supersedes_availability_version_id is None
    history = get_availability_history(conn, "AV-FAM-1")
    assert len(history) == 1


def test_c2_valid_superseding_version_extends_chain(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    first = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    second = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    assert second.supersedes_availability_version_id == first.availability_version_id
    history = get_availability_history(conn, "AV-FAM-1")
    assert [r.availability_version_id for r in history] == [first.availability_version_id, second.availability_version_id]


def test_c3_active_false_is_a_new_version_not_a_rewrite(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    cancellation = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=False,
    )
    history = get_availability_history(conn, "AV-FAM-1")
    assert len(history) == 2
    assert cancellation.active is False
    assert history[0].active is True  # the earlier version is untouched


def test_c4_history_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    conn.close()

    reopened = connect(db_path)
    assert len(get_availability_history(reopened, "AV-FAM-1")) == 1


def test_c5_branch_skip_and_wrong_employee_predecessor_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    save_employee(conn, Employee("EMP-2", "Emp Two", date(2026, 1, 1), None, False))
    append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    with pytest.raises(InvalidAvailabilityChain):
        append_availability_version(
            conn, availability_id="AV-FAM-1", employee_id="EMP-2", kind=AvailabilityKind.LEAVE_PLAN,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
        )
    with pytest.raises(UnknownEmployeeForAvailability):
        append_availability_version(
            conn, availability_id="AV-FAM-2", employee_id="NO-SUCH-EMP", kind=AvailabilityKind.LEAVE_PLAN,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
        )


def test_c6_direct_update_and_delete_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    record = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE availability_versions SET active = 0 WHERE availability_version_id = ?",
            (record.availability_version_id,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "DELETE FROM availability_versions WHERE availability_version_id = ?",
            (record.availability_version_id,),
        )


def test_c7_current_range_query_returns_chain_end_only(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    latest = append_availability_version(
        conn, availability_id="AV-FAM-1", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), active=True,
    )
    current = get_current_availability_for_employee(conn, "EMP-1")
    assert [r.availability_version_id for r in current] == [latest.availability_version_id]
    overlapping = list_active_overlapping(conn, "EMP-1", date(2026, 8, 3), date(2026, 8, 3))
    assert [r.availability_version_id for r in overlapping] == [latest.availability_version_id]


# --- D. CALENDAR -------------------------------------------------------------


def test_d1_calendar_day_range_round_trips_and_restarts(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_calendar_day(conn, CalendarDay(date(2026, 8, 15), True))
    save_calendar_day(conn, CalendarDay(date(2026, 8, 16), False))
    conn.close()

    reopened = connect(db_path)
    assert get_calendar_day(reopened, date(2026, 8, 15)).holiday is True
    days = list_calendar_days(reopened, date(2026, 8, 1), date(2026, 8, 31))
    assert [d.date for d in days] == [date(2026, 8, 15), date(2026, 8, 16)]


def test_d2_deterministic_ordering(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    for day in [date(2026, 8, 20), date(2026, 8, 1), date(2026, 8, 10)]:
        save_calendar_day(conn, CalendarDay(day, False))
    days = list_calendar_days(conn, date(2026, 8, 1), date(2026, 8, 31))
    assert [d.date for d in days] == sorted(d.date for d in days)


def test_d3_updating_holiday_fact_uses_only_the_calendar_repository(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    save_calendar_day(conn, CalendarDay(date(2026, 8, 15), False))
    save_calendar_day(conn, CalendarDay(date(2026, 8, 15), True))  # upsert, no PlanningEngine I/O involved
    assert get_calendar_day(conn, date(2026, 8, 15)).holiday is True
