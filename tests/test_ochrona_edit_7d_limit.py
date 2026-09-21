"""ROTA-OCHRONA-EDIT-7D-LIMIT (tasks/ROTA-OCHRONA-EDIT-7D-LIMIT/brief.md):
OCHRONA-only edit of the existing rolling_7d_decision_threshold_hours via
the new GET/PUT /workspace/sites/{site_id}/rolling-7d-limit endpoints.
Covers all 5 acceptance tests from the brief."""
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
from rota.persistence.site_profile_repository import get_site_profile
from rota.site_memory_types import CoordinatorActionKind

COORD = DEV_COORDINATOR_ID
SITE = "SITE-1"
PROFILE = "PROF-1"


def _profile(threshold: int = 40) -> SiteProfile:
    return SiteProfile(PROFILE, "Profile", True, [], True, True, False, False, 1, threshold)


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coordinator", True),
        site_profile=_profile(),
        site=Site(SITE, PROFILE, "Site", True, SitePlanningRegime.OCHRONA),
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


def _get(client):
    return client.get(f"/api/workspace/sites/{SITE}/rolling-7d-limit")


def _put(client, hours, confirmed=False):
    return client.put(
        f"/api/workspace/sites/{SITE}/rolling-7d-limit",
        json={"rolling_7d_decision_threshold_hours": hours, "confirmed_over_72h": confirmed},
    )


# T1: OCHRONA read existing 40h, write 48/60/72, re-read.
@pytest.mark.parametrize("new_value", [48, 60, 72])
def test_ochrona_read_write_read(client, new_value):
    resp = _get(client)
    assert resp.status_code == 200
    assert resp.json() == {"rolling_7d_decision_threshold_hours": 40, "planning_regime": "OCHRONA"}

    resp = _put(client, new_value)
    assert resp.status_code == 204

    resp = _get(client)
    assert resp.json()["rolling_7d_decision_threshold_hours"] == new_value


# T2: >72h without confirmation is refused (also via direct API); with
# confirmation, saved and the decision is recorded.
@pytest.mark.parametrize("over_value", [73, 100])
def test_over_72_requires_confirmation(client, conn, over_value):
    resp = _put(client, over_value, confirmed=False)
    assert resp.status_code == 400

    resp = _get(client)
    assert resp.json()["rolling_7d_decision_threshold_hours"] == 40  # unchanged

    resp = _put(client, over_value, confirmed=True)
    assert resp.status_code == 204

    resp = _get(client)
    assert resp.json()["rolling_7d_decision_threshold_hours"] == over_value

    actions = list_coordinator_actions(conn, site_id=SITE, action_kind=CoordinatorActionKind.SITE_PROFILE_CHANGED)
    assert len(actions) == 1
    assert "72h" in (actions[0].note or "")


# T3: ORDINARY has no way to change it via the API; value stays the same.
def test_ordinary_rejects_change(conn):
    ordinary_site, ordinary_profile = "SITE-ORD", "PROF-ORD"
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=ordinary_site,
        site_profile=SiteProfile(ordinary_profile, "Ordinary", True, [], True, True, False, False, 1, 50),
        site=Site(ordinary_site, ordinary_profile, "Ordinary Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, ordinary_site, True),
    )
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        c = TestClient(app)
        resp = c.put(
            f"/api/workspace/sites/{ordinary_site}/rolling-7d-limit",
            json={"rolling_7d_decision_threshold_hours": 48, "confirmed_over_72h": False},
        )
        assert resp.status_code == 400
        assert get_site_profile(conn, ordinary_profile).rolling_7d_decision_threshold_hours == 50
    finally:
        app.dependency_overrides.pop(get_conn, None)


# T4: change is scoped to the one site's profile, doesn't touch the shift
# catalog or anything else on the profile.
def test_change_is_scoped_to_profile_field_only(client, conn):
    before = get_site_profile(conn, PROFILE)
    resp = _put(client, 55)
    assert resp.status_code == 204
    after = get_site_profile(conn, PROFILE)
    assert after.rolling_7d_decision_threshold_hours == 55
    assert after.standard_shifts == before.standard_shifts
    assert after.active == before.active


# T5: invalid values rejected the same as any other profile write (positive
# integer only) -- existing validation, no new rule invented.
@pytest.mark.parametrize("bad_value", [0, -5])
def test_non_positive_value_rejected(client, bad_value):
    resp = _put(client, bad_value)
    assert resp.status_code == 400
