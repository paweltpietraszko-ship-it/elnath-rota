"""ROTA-T030 (tasks/ROTA-T030/brief.md): vertical API->application->
persistence tests for the Panel sterowania -> Obiekt shift catalog.
Backend groups T30-01..T30-05 from the reduced round-3 acceptance matrix;
T30-06..T30-08 (E2E, build, regression) live in frontend/e2e and delivery."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import Coordinator, CoordinatorSiteAssociation, Site, SitePlanningRegime, SiteProfile
from rota.persistence.db import connect
from rota.persistence.site_memory import list_coordinator_actions
from rota.site_memory_types import CoordinatorActionKind

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


ONE_ROW = {
    "kind": "D", "start_time": "06:00", "end_time": "18:00",
    "required_primary_count": 2, "active_weekdays": [1, 2, 3, 4, 5, 6, 7],
}


# T30-01: GET empty and existing catalog, stable order.
def test_get_empty_catalog(client):
    resp = client.get(f"/api/workspace/sites/{SITE}/shift-catalog")
    assert resp.status_code == 200
    assert resp.json() == {"shifts": []}


def test_get_existing_catalog_preserves_order(client):
    two_rows = {"shifts": [
        {"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1, 2, 3, 4, 5]},
        {"kind": "N", "start_time": "18:00", "end_time": "06:00", "required_primary_count": 1, "active_weekdays": [1, 2, 3, 4, 5]},
    ]}
    put = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json=two_rows)
    assert put.status_code == 204
    got = client.get(f"/api/workspace/sites/{SITE}/shift-catalog").json()
    assert [s["kind"] for s in got["shifts"]] == ["D", "N"]


# T30-02: PUT + durable end_next_day/catalog_kind (12h/24h/OTHER) + rest=11.
@pytest.mark.parametrize(
    "row,expected_kind,expected_hours",
    [
        ({"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1]}, "12h", 12),
        ({"kind": "N", "start_time": "18:00", "end_time": "06:00", "required_primary_count": 1, "active_weekdays": [1]}, "12h", 12),
        ({"kind": "D", "start_time": "08:00", "end_time": "08:00", "required_primary_count": 1, "active_weekdays": [1]}, "24h", 24),
        ({"kind": "D", "start_time": "08:00", "end_time": "16:00", "required_primary_count": 1, "active_weekdays": [1]}, "INNY", 8),
    ],
)
def test_put_computes_catalog_kind_and_duration(client, conn, row, expected_kind, expected_hours):
    resp = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": [row]})
    assert resp.status_code == 204
    got = client.get(f"/api/workspace/sites/{SITE}/shift-catalog").json()
    shift = got["shifts"][0]
    assert shift["catalog_kind"] == expected_kind
    assert shift["duration_hours"] == expected_hours

    from rota.persistence.site_profile_repository import get_site_profile
    profile = get_site_profile(conn, PROFILE)
    assert profile.standard_shifts[0].required_rest_hours == 11


# T30-03: parametrized validation rejects the whole request, including a
# bad SECOND row -- no partial write.
@pytest.mark.parametrize(
    "bad_row",
    [
        {"kind": "D", "start_time": "06:30", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1]},
        {"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 0, "active_weekdays": [1]},
        {"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": []},
        {"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1, 1]},
        {"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [8]},
    ],
)
def test_put_rejects_invalid_second_row_with_no_state_change(client, bad_row):
    first = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": [ONE_ROW]})
    assert first.status_code == 204

    resp = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": [ONE_ROW, bad_row]})
    assert resp.status_code == 400

    got = client.get(f"/api/workspace/sites/{SITE}/shift-catalog").json()
    assert len(got["shifts"]) == 1


def test_put_empty_list_rejected_by_api(client):
    resp = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": []})
    assert resp.status_code == 400


# T30-04: hidden profile fields survive a shift-catalog PUT; extra/
# unexpected request fields are rejected.
def test_put_preserves_hidden_profile_fields(client, conn):
    client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": [ONE_ROW]})
    from rota.persistence.site_profile_repository import get_site_profile
    profile = get_site_profile(conn, PROFILE)
    assert profile.external_support_enabled is True
    assert profile.day_only_blocks_n is True
    assert profile.training_s_enabled is False
    assert profile.rolling_7d_decision_threshold_hours == 40


def test_put_rejects_unexpected_extra_field(client):
    payload = {"shifts": [ONE_ROW], "profile_id": PROFILE}
    resp = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json=payload)
    assert resp.status_code == 422


# T30-05: one material PUT triggers the existing audit/invalidation;
# completeness stops reporting the missing shift once saved.
def test_material_put_records_site_profile_changed_and_completeness(client, conn):
    before = coordinator_context_completeness(conn)
    assert any("standard shift" in m for m in before.missing)

    resp = client.put(f"/api/workspace/sites/{SITE}/shift-catalog", json={"shifts": [ONE_ROW]})
    assert resp.status_code == 204

    actions = list_coordinator_actions(conn, site_id=SITE, action_kind=CoordinatorActionKind.SITE_PROFILE_CHANGED)
    assert len(actions) == 1

    after = coordinator_context_completeness(conn)
    assert not any("standard shift" in m for m in after.missing)


def coordinator_context_completeness(conn):
    return bootstrap.coordinator_context_completeness(conn, coordinator_id=COORD, site_id=SITE)
