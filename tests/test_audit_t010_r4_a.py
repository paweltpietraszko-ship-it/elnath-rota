"""ROTA-T010 implementation re-audit round 4: Part A only.

Sibling and boundary coverage for the R3-1/R3-2 fixes.  Parts B and D are
deliberately outside this file and outside the round-4 verdict.
"""
from __future__ import annotations

import calendar
import threading
from datetime import date, time

import pytest

import rota.application.bootstrap as bootstrap_module
from rota.application.bootstrap import (
    bootstrap_or_resume_coordinator_context,
    coordinator_context_completeness,
    month_plan_readiness,
)
from rota.application.errors import CoordinatorContextAlreadyActive
from rota.domain import (
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
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import (
    save_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site


COORDINATOR_ID = "COORD-T010-R4-A"
EMPLOYEE_ID = "EMP-T010-R4-A"
MONTH = date(2026, 10, 1)


def _profile(profile_id: str, shift: StandardShift) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id,
        display_name=profile_id,
        active=True,
        standard_shifts=[shift],
        day_only_blocks_n=True,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=60,
    )


def _seed_complete_context(
    conn, *, site_id: str, profile_id: str, shift: StandardShift, association_active: bool = True
) -> None:
    save_coordinator(conn, Coordinator(COORDINATOR_ID, "Coordinator", True))
    save_site_profile(conn, _profile(profile_id, shift))
    save_site(conn, Site(site_id, profile_id, site_id, True))
    save_coordinator_site_association(
        conn, CoordinatorSiteAssociation(COORDINATOR_ID, site_id, association_active)
    )
    save_employee(conn, Employee(EMPLOYEE_ID, "Employee", date(2020, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership(
            EMPLOYEE_ID,
            site_id,
            MembershipKind.LOCAL,
            True,
            ReadinessState.READY_FOR_PRIMARY,
            ReadinessSource.DEFAULT,
        ),
    )


@pytest.mark.parametrize(
    ("shift", "expected_complete"),
    [
        pytest.param(
            StandardShift(ShiftKind.D, time(5), time(17), False, -1),
            False,
            id="negative_primary_count",
        ),
        pytest.param(
            StandardShift(ShiftKind.D, time(17), time(5), False, 1),
            False,
            id="same_day_end_before_start",
        ),
        pytest.param(
            StandardShift(ShiftKind.D, time(5), time(5, 1), False, 1),
            True,
            id="smallest_representative_positive_same_day_interval",
        ),
        pytest.param(
            StandardShift(ShiftKind.N, time(5), time(5), True, 1),
            True,
            id="equal_clock_times_are_positive_when_end_is_next_day",
        ),
    ],
)
def test_r4_a_standard_shift_validity_boundaries(tmp_path, shift, expected_complete) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_complete_context(conn, site_id="SITE-BOUNDARY", profile_id="PROFILE-BOUNDARY", shift=shift)

    result = coordinator_context_completeness(
        conn, coordinator_id=COORDINATOR_ID, site_id="SITE-BOUNDARY"
    )

    assert result.complete is expected_complete
    assert any("shift" in item.lower() for item in result.missing) is (not expected_complete)


def test_r4_a_invalid_shift_keeps_a_calendar_complete_month_not_ready(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_complete_context(
        conn,
        site_id="SITE-MONTH",
        profile_id="PROFILE-MONTH",
        shift=StandardShift(ShiftKind.D, time(5), time(17), False, 0),
    )
    for day in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(MONTH.year, MONTH.month, day), False))

    result = month_plan_readiness(
        conn, coordinator_id=COORDINATOR_ID, site_id="SITE-MONTH", month=MONTH
    )

    assert not result.ready
    assert any("shift" in item.lower() for item in result.missing)


def test_r4_a_concurrent_reactivation_of_one_inactive_association_has_one_winner(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "rota.db"
    initial = connect(db_path)
    _seed_complete_context(
        initial,
        site_id="SITE-REACTIVATE",
        profile_id="PROFILE-REACTIVATE",
        shift=StandardShift(ShiftKind.D, time(5), time(17), False, 1),
        association_active=False,
    )
    initial.close()

    barrier = threading.Barrier(2)
    original_check = bootstrap_module._has_full_active_context  # C-R4-1: was _has_active_association, stale since C-R3-1

    def synchronized_check(conn, *, coordinator_id: str, site_id: str) -> bool:
        result = original_check(conn, coordinator_id=coordinator_id, site_id=site_id)
        barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(bootstrap_module, "_has_full_active_context", synchronized_check)
    outcomes: list[str] = []

    def worker() -> None:
        conn = connect(db_path)
        try:
            bootstrap_or_resume_coordinator_context(
                conn, coordinator_id=COORDINATOR_ID, site_id="SITE-REACTIVATE",
                association=CoordinatorSiteAssociation(COORDINATOR_ID, "SITE-REACTIVATE", True),
            )
        except CoordinatorContextAlreadyActive:
            outcomes.append("rejected")
        else:
            outcomes.append("success")
        finally:
            conn.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == ["rejected", "success"]


def test_r4_a_concurrent_bootstrap_of_two_different_sites_both_succeeds(
    tmp_path, monkeypatch
) -> None:
    """The CAS is pair-scoped and must not introduce a one-Site-per-coordinator limit."""
    db_path = tmp_path / "rota.db"
    initial = connect(db_path)
    save_coordinator(initial, Coordinator(COORDINATOR_ID, "Coordinator", True))
    initial.close()

    barrier = threading.Barrier(2)
    original_check = bootstrap_module._has_full_active_context  # C-R4-1: was _has_active_association, stale since C-R3-1

    def synchronized_check(conn, *, coordinator_id: str, site_id: str) -> bool:
        result = original_check(conn, coordinator_id=coordinator_id, site_id=site_id)
        barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(bootstrap_module, "_has_full_active_context", synchronized_check)
    outcomes: list[tuple[str, str]] = []

    def worker(site_id: str) -> None:
        profile_id = f"PROFILE-{site_id}"
        conn = connect(db_path)
        try:
            bootstrap_or_resume_coordinator_context(
                conn,
                coordinator_id=COORDINATOR_ID,
                site_id=site_id,
                site_profile=_profile(
                    profile_id, StandardShift(ShiftKind.D, time(5), time(17), False, 1)
                ),
                site=Site(site_id, profile_id, site_id, True),
                association=CoordinatorSiteAssociation(COORDINATOR_ID, site_id, True),
            )
        except Exception as exc:
            outcomes.append((site_id, type(exc).__name__))
        else:
            outcomes.append((site_id, "success"))
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(site_id,)) for site_id in ("SITE-A", "SITE-B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == [("SITE-A", "success"), ("SITE-B", "success")]
