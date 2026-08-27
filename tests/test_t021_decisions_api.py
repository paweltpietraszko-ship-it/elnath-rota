"""ROTA-T021 Decyzje koordynatora: vertical API test for the new thin
read-only wrap (api/routers/decisions.py). No new backend logic --
current_decision_required_months_for_site is called directly (same
precedent as api/routers/bootstrap.py's SiteSummary), and the per-month
payload reuses rota.application.memory_read.current_decision_required
unchanged (the same source api/routers/schedule.py's MonthViewOut.decision_required
already surfaces)."""
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
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect

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
    _seed_days_of_month(connection, MONTH)
    try:
        yield connection, site_id
    finally:
        connection.close()


@pytest.fixture
def understaffed_client(understaffed_site):
    connection, _ = understaffed_site
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_no_pending_decisions_for_a_fresh_site(understaffed_site, understaffed_client):
    _, site_id = understaffed_site
    resp = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/months")
    assert resp.status_code == 200
    assert resp.json() == {"months": []}


def test_month_with_no_decision_returns_null(understaffed_site, understaffed_client):
    _, site_id = understaffed_site
    resp = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}")
    assert resp.status_code == 200
    assert resp.json() is None


def test_decision_required_appears_in_months_list_and_detail(understaffed_site, understaffed_client):
    _, site_id = understaffed_site
    plan_resp = understaffed_client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    )
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    months_resp = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/months")
    assert months_resp.json() == {"months": [MONTH_STR]}

    detail_resp = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["site_id"] == site_id
    assert detail["requested_by"] == DEV_COORDINATOR_ID
    assert detail["blocking_shift_demands"]
    assert detail["unblocking_options"]
    assert detail["linked_action_ids"] == []


if __name__ == "__main__":
    print("test_t021_decisions_api module OK")
