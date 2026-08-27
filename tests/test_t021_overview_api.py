"""ROTA-T021 Przeglad: vertical API test for the new composition-only
router (api/routers/overview.py). Per arch/T021_spec.md, this screen has
no dedicated backend module -- it composes existing reads already covered
under other screens (decisions, schedule version, roster), same pattern
api/routers/bootstrap.py's _site_summary already uses."""
from __future__ import annotations

from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import (
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
    StandardShift,
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
        site_profile=SiteProfile(
            PROFILE, "Profile", True, [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
            True, True, False, False, 1, 40,
        ),
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


def test_fresh_site_has_no_version_no_decisions_and_zero_headcount(client):
    resp = client.get(f"/api/workspace/sites/{SITE}/overview?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_id"] is None
    assert body["version_status"] is None
    assert body["resumable"] is False
    assert body["decision_months"] == []
    assert body["headcount"] == 0


def test_headcount_counts_local_and_external_support(client, conn):
    save_employee(conn, Employee("A", "Anna A", date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership("A", SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    save_employee(conn, Employee("X", "External X", date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership("X", SITE, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    save_employee(conn, Employee("D", "Disabled D", date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership("D", SITE, MembershipKind.LOCAL, False, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))

    resp = client.get(f"/api/workspace/sites/{SITE}/overview?month={MONTH.isoformat()}")
    assert resp.status_code == 200
    assert resp.json()["headcount"] == 2


def test_working_version_is_resumable():
    """Uses the same real-object fixture test_t031_schedule_api relies on
    (seed_real_object) -- a bare hand-built roster has no shift catalog and
    can't reach FEASIBLE, so this is its own isolated client/conn pair."""
    from tests.support.t009_fixtures import seed_real_object

    connection = connect(":memory:")
    pstate = seed_real_object(connection, case_id="t021-overview", month=MONTH, seed=900, coordinator_id=COORD)
    site_id = pstate.site.site_id
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        overview_client = TestClient(app)
        plan_resp = overview_client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/plan", json={"effective_from": MONTH.isoformat()},
        )
        assert plan_resp.json()["status"] == "FEASIBLE"
        candidate = plan_resp.json()["candidates"][0]
        select_resp = overview_client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/select-candidate",
            json={"candidate": [{k: v for k, v in a.items() if k != "employee_display_name"} for a in candidate]},
        )
        assert select_resp.status_code == 204

        resp = overview_client.get(f"/api/workspace/sites/{site_id}/overview?month={MONTH.isoformat()}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version_status"] in ("WORKING", "WORKING_WITH_DEVIATIONS")
        assert body["resumable"] is True
        assert body["version_id"] is not None
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


if __name__ == "__main__":
    print("test_t021_overview_api module OK")
