"""Independent R3 reproducer for the public manual-correction bypass."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.deps import get_conn, get_coordinator_id
from api.main import app
from rota.domain import SiteRoleDefinition
from rota.persistence.schedule_repository import get_current_version_id
from rota.persistence.site_role_repository import save_site_role
from tests.test_t065_manual_middle_shift import COORD, EMP, MONTH, SITE, _seed


def test_generic_manual_correction_cannot_bypass_role_authorization():
    """Section 6 is a hard pre-check on every reachable creation path."""
    from rota.persistence.db import connect

    conn = connect(":memory:")
    _seed(conn)  # EMP's position is ROLE-KIER.
    save_site_role(conn, SiteRoleDefinition("ROLE-SPRZ", SITE, "Sprzedawca", True))
    before = get_current_version_id(conn, SITE, MONTH)

    app.dependency_overrides[get_conn] = lambda: (yield conn)
    app.dependency_overrides[get_coordinator_id] = lambda: COORD
    try:
        response = TestClient(app).post(
            f"/api/workspace/sites/{SITE}/schedule/{MONTH.isoformat()}/manual-correction",
            json={
                "upsert_assignments": [{
                    "assignment_id": "ASG-AUDIT-BYPASS",
                    "schedule_version_id": "",
                    "employee_id": EMP,
                    "start_datetime": "2026-09-10T10:00:00",
                    "end_datetime": "2026-09-10T16:00:00",
                    "role": "PRIMARY",
                    "state": "PLANNED",
                    "frozen": False,
                    "covers_demand_id": None,
                    "mentor_primary_assignment_id": None,
                    "operational_code": None,
                    "work_period_id": None,
                    "required_rest_after_hours": None,
                    "manual_work_role_id": "ROLE-SPRZ",
                    "manual_work_role_name": "Sprzedawca",
                }]
            },
        )
    finally:
        app.dependency_overrides.pop(get_conn, None)
        app.dependency_overrides.pop(get_coordinator_id, None)

    assert response.status_code == 400, response.text
    assert get_current_version_id(conn, SITE, MONTH) == before

