"""ROTA-T033: usuwanie obiektu z Workspace bez usuwania go z historii
programu (owner decision 2026-08-26). Site.active toggles via the existing
durable_inputs.update_site / bootstrap_or_resume_coordinator_context write
paths -- no new domain logic, just the API surface + GET /workspace/sites
filtering (api/routers/bootstrap.py).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import Coordinator, CoordinatorSiteAssociation, Site, SitePlanningRegime, SiteProfile
from rota.persistence.db import connect

COORD = DEV_COORDINATOR_ID
SITE = "SITE-1"
PROFILE = "PROF-1"


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


def test_deactivate_hides_site_from_default_listing_but_not_include_inactive(client):
    assert [s["site_id"] for s in client.get("/api/workspace/sites").json()] == [SITE]

    resp = client.post(f"/api/workspace/sites/{SITE}/deactivate")
    assert resp.status_code == 204

    assert client.get("/api/workspace/sites").json() == []
    everyone = client.get("/api/workspace/sites?include_inactive=true").json()
    assert [(s["site_id"], s["active"]) for s in everyone] == [(SITE, False)]


def test_reactivate_brings_site_back_to_default_listing(client):
    client.post(f"/api/workspace/sites/{SITE}/deactivate")
    assert client.get("/api/workspace/sites").json() == []

    resp = client.post(f"/api/workspace/sites/{SITE}/reactivate")
    assert resp.status_code == 204

    assert [s["site_id"] for s in client.get("/api/workspace/sites").json()] == [SITE]


def test_deactivate_does_not_touch_schedule_or_employee_history(client, conn):
    """The whole point: hidden from Workspace, nothing deleted."""
    from datetime import date, datetime

    from rota.domain import Employee
    from rota.persistence.employee_repository import get_employee, save_employee
    from rota.persistence.schedule_lifecycle import create_schedule_version
    from rota.persistence.schedule_repository import get_schedule_version_header

    save_employee(conn, Employee("E1", "E1", date(2026, 1, 1), None, False))
    create_schedule_version(
        conn, version_id="SV-1", site_id=SITE, month=date(2026, 10, 1), parent_version_id=None,
        created_at=datetime(2026, 9, 1), created_by=COORD, applied_rule_version_ids=[], shift_demands=[],
        assignments=[], deviations=[], effective_from=date(2026, 10, 1),
    )

    resp = client.post(f"/api/workspace/sites/{SITE}/deactivate")
    assert resp.status_code == 204

    assert get_employee(conn, "E1") is not None
    assert get_schedule_version_header(conn, "SV-1") is not None


def test_reactivate_when_already_active_is_rejected(client):
    resp = client.post(f"/api/workspace/sites/{SITE}/reactivate")
    assert resp.status_code == 409


def test_deactivate_when_already_inactive_is_rejected(client):
    client.post(f"/api/workspace/sites/{SITE}/deactivate")
    resp = client.post(f"/api/workspace/sites/{SITE}/deactivate")
    assert resp.status_code == 403
