"""ROTA-T021 Historia i audyt: vertical API test for the new thin
read-only wrap (api/routers/history.py) over the existing, unchanged
rota.application.memory_read (material action history/detail + rule
decision history). No new backend logic -- this only proves the
marshalling wire is correct."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.application.durable_inputs import set_target_hours
from rota.domain import Coordinator, CoordinatorSiteAssociation, Employee, Site, SitePlanningRegime, SiteProfile
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee

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


def test_bootstrap_itself_is_the_only_recorded_action(client):
    """bootstrap_or_resume_coordinator_context (fixture setup) already
    records CONTEXT_CONFIGURATION_SAVED -- confirms the history stream
    reflects real actions, not an empty/mocked list."""
    resp = client.get(f"/api/workspace/sites/{SITE}/history/actions")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["action_kind"] == "CONTEXT_CONFIGURATION_SAVED"


def test_recorded_action_appears_in_history_and_detail(client, conn):
    save_employee(conn, Employee("A", "Anna A", date(2020, 1, 1), None, False))
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="A", month=MONTH, target_hours=160)

    resp = client.get(f"/api/workspace/sites/{SITE}/history/actions?action_kind=TARGET_HOURS_CHANGED")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["action_kind"] == "TARGET_HOURS_CHANGED"
    assert row["coordinator_id"] == COORD

    detail_resp = client.get(f"/api/workspace/history/actions/{row['action_id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["after_state"]["target_hours"] == 160
    assert detail["before_state"]["target_hours"] is None


def test_action_kind_filter_narrows_results(client, conn):
    save_employee(conn, Employee("A", "Anna A", date(2020, 1, 1), None, False))
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="A", month=MONTH, target_hours=160)
    resp = client.get(f"/api/workspace/sites/{SITE}/history/actions?action_kind=SCHEDULE_FINALIZED")
    assert resp.status_code == 200
    assert resp.json() == []


def test_unknown_action_id_returns_404(client):
    resp = client.get("/api/workspace/history/actions/does-not-exist")
    assert resp.status_code == 404


def test_rule_history_empty_for_site_with_no_rules(client):
    resp = client.get(f"/api/workspace/sites/{SITE}/history/rules")
    assert resp.status_code == 200
    assert resp.json() == {}


if __name__ == "__main__":
    print("test_t021_history_api module OK")
