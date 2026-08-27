"""ROTA-T021 (owner correction 2026-08-27): "Wsparcie zewnetrzne" is not a
separate feature/screen -- it's the existing Obsada roster row
(SiteMembership.membership_kind=EXTERNAL_SUPPORT) plus one simple date
range the solver may use that person within (ExternalSupportWindow).
api/routers/durable_inputs.py's existing roster-attach endpoint now
accepts membership_kind (was hardcoded LOCAL); a new minimal endpoint
creates one window. No new screen, no list/management UI."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import Coordinator, CoordinatorSiteAssociation, Employee, Site, SitePlanningRegime, SiteProfile
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, list_windows_for_site, save_employee

SITE = "SITE-1"
PROFILE = "PROF-1"


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=DEV_COORDINATOR_ID, site_id=SITE,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True),
        site_profile=SiteProfile(PROFILE, "Profile", True, [], True, True, False, False, 1, 40),
        site=Site(SITE, PROFILE, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, SITE, True),
    )
    save_employee(connection, Employee("EXT-1", "External Ela", date(2020, 1, 1), None, False))
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


def test_attach_to_roster_still_defaults_to_local(client, conn):
    save_employee(conn, Employee("LOC-1", "Local Larry", date(2020, 1, 1), None, False))
    resp = client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "LOC-1"})
    assert resp.status_code == 204
    membership = next(m for m in list_memberships_for_site(conn, SITE) if m.employee_id == "LOC-1")
    assert membership.membership_kind.value == "LOCAL"


def test_attach_to_roster_as_external_support(client, conn):
    resp = client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"})
    assert resp.status_code == 204
    membership = next(m for m in list_memberships_for_site(conn, SITE) if m.employee_id == "EXT-1")
    assert membership.membership_kind.value == "EXTERNAL_SUPPORT"


def test_create_support_window(client, conn):
    client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"})
    resp = client.post(
        "/api/workspace/employees/EXT-1/support-window",
        json={"site_id": SITE, "start_datetime": "2026-10-05T00:00:00", "end_datetime": "2026-10-10T00:00:00", "allowed_shift_kind": None},
    )
    assert resp.status_code == 204
    windows = list_windows_for_site(conn, SITE)
    assert len(windows) == 1
    assert windows[0].employee_id == "EXT-1"
    assert windows[0].active is True


if __name__ == "__main__":
    print("test_t021_external_support_roster module OK")
