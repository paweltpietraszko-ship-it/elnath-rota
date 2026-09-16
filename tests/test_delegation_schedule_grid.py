"""ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID (brief.md
section 6, DG-01..DG-09): a presentational-only roster + DELEGACJA
projection in api/routers/schedule.py so a LOCAL employee with an active
DELEGACJA and zero Assignments still shows up in the "Planowanie miesiąca"
grid, with a DEL cell on every day the record covers. Narrow -- exercises
the router's new projection fields, not a full PLAN/REPLAN regression
(already covered elsewhere).
"""
from __future__ import annotations

import calendar
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap, durable_inputs, plan_ops
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
    SitePlanningRegime,
    SiteProfile,
    SiteRoleDefinition,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id

COORD = DEV_COORDINATOR_ID
SITE_ID = "SITE-DG"
PROFILE_ID = "PROFILE-DG"
MONTH = date(2026, 11, 1)
MONTH_STR = MONTH.isoformat()


def _profile(*, regime: SitePlanningRegime = SitePlanningRegime.OCHRONA) -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID, display_name="DG profile", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn, *, regime: SitePlanningRegime = SitePlanningRegime.OCHRONA) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        coordinator=Coordinator(COORD, "Coord DG", True), site_profile=_profile(regime=regime),
        site=Site(SITE_ID, PROFILE_ID, "Site DG", True, planning_regime=regime),
        association=CoordinatorSiteAssociation(COORD, SITE_ID, True),
    )


def _employee(conn, employee_id: str, display_name: str, *, kind: MembershipKind = MembershipKind.LOCAL, enabled: bool = True, position_role_id: str | None = None) -> None:
    durable_inputs.update_employee(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        employee=Employee(employee_id, display_name, date(2020, 1, 1), None, False),
    )
    durable_inputs.update_membership(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        membership=SiteMembership(
            employee_id, SITE_ID, kind, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            position_role_id=position_role_id,
        ),
    )


def _fill_calendar(conn, month: date = MONTH) -> None:
    for d in range(1, calendar.monthrange(month.year, month.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, d), False))


def _delegation(conn, *, availability_id: str, employee_id: str, start: date, end: date, hours: int, active: bool = True) -> None:
    durable_inputs.append_availability(
        conn, coordinator_id=COORD, site_id=SITE_ID, availability_id=availability_id, employee_id=employee_id,
        kind=AvailabilityKind.DELEGACJA, start_date=start, end_date=end, active=active, delegation_hours=hours,
    )


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "rota.db")
    _bootstrap(connection)
    _fill_calendar(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


# --- DG-01/DG-03/DG-08: current MonthView shows a DEL-only LOCAL employee ---


def test_dg01_del_only_employee_appears_in_month_view_with_no_assignments(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 7), hours=8)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["assignments"] == []
    assert body["employees"] == [{"employee_id": "E1", "employee_display_name": "Jan Kowalski"}]
    # DG-03: exactly the covered days get a DEL entry, nothing outside the range.
    assert [d["date"] for d in body["delegation_days"]] == ["2026-11-05", "2026-11-06", "2026-11-07"]
    assert all(d["code"] == "DEL" and d["hours"] == 8 for d in body["delegation_days"])


def test_dg03_days_outside_the_record_range_carry_no_del(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 10), end=date(2026, 11, 10), hours=24)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    body = resp.json()
    assert len(body["delegation_days"]) == 1
    assert body["delegation_days"][0] == {"employee_id": "E1", "date": "2026-11-10", "code": "DEL", "hours": 24}


# --- DG-08: display name is the real Polish name, never a raw id -----------


def test_dg08_employee_display_name_is_never_the_raw_id(client, conn):
    _employee(conn, "E-RAW-1", "Anna Nowak")
    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    body = resp.json()
    assert body["employees"] == [{"employee_id": "E-RAW-1", "employee_display_name": "Anna Nowak"}]


# --- DG-05: cancelling/moving DEL then REPLAN drops the stale symbol --------


def test_dg05_cancelled_delegation_no_longer_shows_after_reload(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 7), hours=8)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    assert len(resp.json()["delegation_days"]) == 3

    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 7), hours=8, active=False)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    body = resp.json()
    assert body["delegation_days"] == []
    # The employee itself must stay off the grid too -- no assignment, no
    # active membership event left to justify a row for a since-cancelled
    # DEL-only appearance (still an active LOCAL member -- but this Task
    # never claims LOCAL alone hides/keeps rows; the roster still includes
    # every active enabled LOCAL, so the row remains, empty).
    assert body["employees"] == [{"employee_id": "E1", "employee_display_name": "Jan Kowalski"}]


def test_dg05_moved_delegation_reflects_only_the_current_chain_end(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 5), hours=8)
    # Supersede via the same availability_id -- append-only chain, brief
    # section 5: "stara wersja... nie może pozostać w podglądzie".
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 20), end=date(2026, 11, 20), hours=16)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    body = resp.json()
    assert [d["date"] for d in body["delegation_days"]] == ["2026-11-20"]
    assert body["delegation_days"][0]["hours"] == 16


# --- DG-06: no Assignment/demand/DEL persistence side effect ---------------


def test_dg06_del_projection_creates_no_assignment_demand_or_version(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 7), hours=8)

    client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")

    assert get_current_version_id(conn, SITE_ID, MONTH) is None


# --- DG-02: fresh PLAN result and persisted PlanPreview after reload agree --


def test_dg02_plan_result_and_reloaded_preview_show_the_same_del_row(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _employee(conn, "E2", "Ewa Zielinska")
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E1", month=MONTH, target_hours=100)
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E2", month=MONTH, target_hours=100)
    _delegation(conn, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 5), hours=8)

    plan_resp = client.post(
        f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    )
    assert plan_resp.status_code == 200
    plan_body = plan_resp.json()
    assert plan_body["status"] == "FEASIBLE"
    plan_del_days = sorted(plan_body["delegation_days"], key=lambda d: (d["employee_id"], d["date"]))
    assert {"employee_id": "E1", "date": "2026-11-05", "code": "DEL", "hours": 8} in plan_del_days

    reload_resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    reload_body = reload_resp.json()
    assert reload_body["plan_preview"] is not None
    reload_del_days = sorted(reload_body["plan_preview"]["delegation_days"], key=lambda d: (d["employee_id"], d["date"]))
    assert reload_del_days == plan_del_days
    assert sorted(reload_body["plan_preview"]["employees"], key=lambda e: e["employee_id"]) == sorted(
        plan_body["employees"], key=lambda e: e["employee_id"]
    )


# --- DG-09: OCHRONA and ORDINARY share one response contract ---------------


def test_dg09_ordinary_regime_uses_the_same_response_contract(tmp_path):
    connection = connect(tmp_path / "rota.db")
    _bootstrap(connection, regime=SitePlanningRegime.ORDINARY)
    _fill_calendar(connection)
    durable_inputs.save_site_role(
        connection, coordinator_id=COORD, site_id=SITE_ID,
        role=SiteRoleDefinition(role_id="ROLE-DG", site_id=SITE_ID, display_name="Sprzedawca", active=True),
    )
    _employee(connection, "E1", "Jan Kowalski", position_role_id="ROLE-DG")
    _delegation(connection, availability_id="AV-1", employee_id="E1", start=date(2026, 11, 5), end=date(2026, 11, 5), hours=8)
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["employees"] == [{"employee_id": "E1", "employee_display_name": "Jan Kowalski"}]
        assert [d["date"] for d in body["delegation_days"]] == ["2026-11-05"]
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


# --- regression: an ordinary employee with real Assignments is unaffected --


def test_regression_employee_with_assignments_and_no_delegation_is_unaffected(client, conn):
    _employee(conn, "E1", "Jan Kowalski")
    _employee(conn, "E2", "Ewa Zielinska")
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E1", month=MONTH, target_hours=100)
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E2", month=MONTH, target_hours=100)

    result = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    plan_ops.select_candidate(conn, site_id=SITE_ID, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)

    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH_STR}")
    body = resp.json()
    assert body["delegation_days"] == []
    assert {e["employee_id"] for e in body["employees"]} == {"E1", "E2"}
    assert len(body["assignments"]) > 0
