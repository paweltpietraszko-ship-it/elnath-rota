"""ROTA-T021 Analityka i bilanse: vertical API test for the new thin
read-only wrap (api/routers/analytics.py) over the existing, unchanged
rota.application.analytics_read.analytics_for_site_month. No new backend
logic -- this only proves the marshalling wire is correct."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.application.durable_inputs import set_target_hours
from rota.domain import (
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership

COORD = DEV_COORDINATOR_ID
SITE = "SITE-1"
PROFILE = "PROF-1"
MONTH = date(2026, 10, 1)


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coordinator", True),
        site_profile=SiteProfile(PROFILE, "Profile", True, [], True, True, False, False, 1, 40),
        site=Site(SITE, PROFILE, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
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


def _add_local_employee(conn, employee_id: str, display_name: str) -> None:
    save_employee(conn, Employee(employee_id, display_name, date(2020, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership(employee_id, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def test_empty_roster_returns_no_rows(client):
    resp = client.get(f"/api/workspace/sites/{SITE}/analytics?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["site_id"] == SITE
    assert body["rows"] == []
    assert body["hours_scope"] == "ALL_SITES"


def test_missing_target_hours_degrades_with_a_warning(client, conn):
    _add_local_employee(conn, "A", "Anna A")
    resp = client.get(f"/api/workspace/sites/{SITE}/analytics?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    row = resp.json()["rows"][0]
    assert row["employee_id"] == "A"
    assert row["status"] == "UNAVAILABLE"
    assert row["month_data"] is None
    assert row["warnings"]


def test_target_hours_set_for_full_quarter_produces_available_row(client, conn):
    _add_local_employee(conn, "A", "Anna A")
    for offset in range(3):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="A", month=date(2026, 10 + offset, 1), target_hours=160)
    resp = client.get(f"/api/workspace/sites/{SITE}/analytics?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    row = resp.json()["rows"][0]
    assert row["status"] == "AVAILABLE"
    assert row["month_data"]["target_hours"] == 160
    assert len(row["quarter_months"]) == 3


def test_invalid_month_maps_to_400():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/workspace/sites/{SITE}/analytics?month=2026-10-15")
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def test_external_support_never_gets_a_row(client, conn):
    save_employee(conn, Employee("X", "External X", date(2020, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership("X", SITE, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    resp = client.get(f"/api/workspace/sites/{SITE}/analytics?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    assert resp.json()["rows"] == []


if __name__ == "__main__":
    print("test_t021_analytics_api module OK")
