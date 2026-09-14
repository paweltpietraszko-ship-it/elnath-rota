"""Independent R5 reproducer for the remaining ORDINARY onboarding gap."""
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
    Site,
    SitePlanningRegime,
    SiteProfile,
    SiteRoleDefinition,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_employee
from rota.persistence.site_role_repository import save_site_role


@pytest.fixture
def ordinary_site_with_unattached_employee():
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
    save_site_role(conn, SiteRoleDefinition("ROLE-SELLER", "SITE-1", "Sprzedawca", True))
    save_employee(conn, Employee("EMP-NEW", "Nowa osoba", date(2026, 1, 1), None, False))
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app), conn
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


def test_ordinary_attach_cannot_create_enabled_membership_without_position(
    ordinary_site_with_unattached_employee,
):
    client, conn = ordinary_site_with_unattached_employee

    response = client.post(
        "/api/workspace/sites/SITE-1/roster",
        json={"employee_id": "EMP-NEW", "membership_kind": "LOCAL"},
    )

    assert response.status_code >= 400
    assert list_memberships_for_site(conn, "SITE-1") == []
