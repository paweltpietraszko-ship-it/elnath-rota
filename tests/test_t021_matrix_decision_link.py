"""ROTA-T021 UI audit gate round-15 FINDING 2: api/routers/rule_decisions.py
now exposes responds_to_decision_required_id on its five matrix-mutation
endpoints (the application layer, rota.application.rule_decisions, already
accepted it -- only the router never forwarded it). This proves the real
end-to-end link: resolving a genuine DECISION_REQUIRED via a matrix change
clears that month from the pending-decisions list, exactly as
site_memory.invalidate_current_decision_required_no_commit already does
for every other durable_inputs write."""
from __future__ import annotations

from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import (
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee

MONTH = date(2026, 8, 1)
MONTH_STR = MONTH.isoformat()


def _seed_days_of_month(conn, month: date) -> None:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = month
    while day < next_month:
        save_calendar_day(conn, CalendarDay(day, False))
        day = date.fromordinal(day.toordinal() + 1)


@pytest.fixture
def understaffed_site():
    connection = connect(":memory:")
    site_id, profile_id = "SITE-UNDERSTAFFED", "PROF-UNDERSTAFFED"
    profile = SiteProfile(
        profile_id, "Profile", True,
        [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        True, True, False, False, 1, 40,
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True),
        site_profile=profile,
        site=Site(site_id, profile_id, "Understaffed", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, site_id, True),
    )
    save_employee(connection, Employee("EMP-1", "Jan Kowalski", date(2020, 1, 1), None, False))
    _seed_days_of_month(connection, MONTH)
    try:
        yield connection, site_id
    finally:
        connection.close()


@pytest.fixture
def client(understaffed_site):
    connection, _ = understaffed_site
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_matrix_write_with_responds_to_decision_required_id_clears_the_decision(understaffed_site, client):
    _, site_id = understaffed_site
    plan_resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    months_resp = client.get(f"/api/workspace/sites/{site_id}/decisions/months")
    assert months_resp.json() == {"months": [MONTH_STR]}
    detail = client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()
    decision_id = detail["decision_required_id"]

    matrix_resp = client.post(
        "/api/workspace/employees/EMP-1/matrix/shift-unavailability",
        json={
            "site_id": site_id, "shift_kind": "N", "effective_from": MONTH_STR,
            "responds_to_decision_required_id": decision_id,
        },
    )
    assert matrix_resp.status_code == 204

    months_after = client.get(f"/api/workspace/sites/{site_id}/decisions/months").json()
    assert months_after == {"months": []}


def test_matrix_write_with_unknown_decision_id_is_rejected(understaffed_site, client):
    _, site_id = understaffed_site
    resp = client.post(
        "/api/workspace/employees/EMP-1/matrix/shift-unavailability",
        json={
            "site_id": site_id, "shift_kind": "D", "effective_from": MONTH_STR,
            "responds_to_decision_required_id": "DR-does-not-exist",
        },
    )
    assert resp.status_code >= 400


def test_shift_catalog_write_with_responds_to_decision_required_id_clears_the_decision(understaffed_site, client):
    """Round-16 OWNER_CORRECTED: 'Zmien zapisana regule' -> Obiekt -> Katalog
    zmian is also a decision-response action per arch/T021_spec.md:595-596 --
    same gap, same fix shape as the five matrix endpoints."""
    _, site_id = understaffed_site
    plan_resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    detail = client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()
    decision_id = detail["decision_required_id"]

    # required_primary_count=2 (fixture's catalog has 1) so the write is a
    # genuinely material profile change -- update_site_profile only records
    # an action (and invalidates the decision) when the planning-relevant
    # fields actually differ, matching every other durable_inputs "if
    # before != after" no-op guard.
    catalog_resp = client.put(
        f"/api/workspace/sites/{site_id}/shift-catalog",
        json={
            "shifts": [{"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 2, "active_weekdays": [1, 2, 3, 4, 5, 6, 7]}],
            "responds_to_decision_required_id": decision_id,
        },
    )
    assert catalog_resp.status_code == 204

    months_after = client.get(f"/api/workspace/sites/{site_id}/decisions/months").json()
    assert months_after == {"months": []}


if __name__ == "__main__":
    print("test_t021_matrix_decision_link module OK")
