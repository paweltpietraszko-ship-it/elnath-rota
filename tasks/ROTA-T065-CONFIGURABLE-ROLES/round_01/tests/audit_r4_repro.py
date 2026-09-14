"""Independent R4 reproducer for the ORDINARY position invariant."""
from datetime import date

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
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    SiteRoleDefinition,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import (
    list_memberships_for_site,
    save_employee,
    save_site_membership,
)
from rota.persistence.site_role_repository import save_site_role


@pytest.fixture
def ordinary_roster_client():
    conn = connect(":memory:")
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=DEV_COORDINATOR_ID,
        site_id="SITE-1",
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Koordynator", True),
        site_profile=SiteProfile("PROFILE-1", "Profil", True, [], False, True, False, False, 1, 40),
        site=Site("SITE-1", "PROFILE-1", "Sklep", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, "SITE-1", True),
    )
    save_site_role(conn, SiteRoleDefinition("ROLE-ACTIVE", "SITE-1", "Sprzedawca", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-INACTIVE", "SITE-1", "Dawna rola", False))
    save_employee(conn, Employee("EMP-1", "Jan", date(2026, 1, 1), None, False))
    save_site_membership(
        conn,
        SiteMembership(
            "EMP-1",
            "SITE-1",
            MembershipKind.LOCAL,
            True,
            ReadinessState.READY_FOR_PRIMARY,
            ReadinessSource.DEFAULT,
            True,
            "ROLE-ACTIVE",
        ),
    )
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app), conn
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


def test_enabled_ordinary_membership_cannot_clear_its_only_position(ordinary_roster_client):
    client, conn = ordinary_roster_client

    response = client.patch(
        "/api/workspace/sites/SITE-1/roster/EMP-1",
        json={"clear_position": True},
    )

    assert response.status_code >= 400
    assert list_memberships_for_site(conn, "SITE-1")[0].position_role_id == "ROLE-ACTIVE"


def test_enabled_ordinary_membership_cannot_select_retired_position(ordinary_roster_client):
    client, conn = ordinary_roster_client

    response = client.patch(
        "/api/workspace/sites/SITE-1/roster/EMP-1",
        json={"position_role_id": "ROLE-INACTIVE"},
    )

    assert response.status_code >= 400
    assert list_memberships_for_site(conn, "SITE-1")[0].position_role_id == "ROLE-ACTIVE"


def test_retired_role_is_not_available_for_a_new_shift_catalog_configuration(ordinary_roster_client):
    client, _ = ordinary_roster_client

    response = client.put(
        "/api/workspace/sites/SITE-1/shift-catalog",
        json={
            "shifts": [
                {
                    "start_time": "06:00",
                    "end_time": "14:00",
                    "required_primary_count": 1,
                    "active_weekdays": [1, 2, 3, 4, 5],
                    "required_role_id": "ROLE-INACTIVE",
                }
            ]
        },
    )

    assert response.status_code >= 400


def test_retired_role_is_not_available_for_a_new_coverage_authorization(ordinary_roster_client):
    client, _ = ordinary_roster_client

    response = client.put(
        "/api/workspace/sites/SITE-1/role-coverage-authorizations/AUTH-1",
        json={
            "authorization_id": "AUTH-1",
            "employee_id": "EMP-1",
            "covered_role_id": "ROLE-INACTIVE",
            "start_datetime": "2026-10-01T00:00:00",
            "end_datetime": "2026-10-31T23:59:59",
            "active": True,
        },
    )

    assert response.status_code >= 400
