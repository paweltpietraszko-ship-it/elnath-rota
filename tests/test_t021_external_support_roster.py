"""ROTA-T021 (owner correction 2026-08-27): "Wsparcie zewnetrzne" is not a
separate feature/screen -- it's the existing Obsada roster row
(SiteMembership.membership_kind=EXTERNAL_SUPPORT) plus one simple date
range the solver may use that person within (ExternalSupportWindow).
api/routers/durable_inputs.py's existing roster-attach endpoint now
accepts membership_kind (was hardcoded LOCAL); a new minimal endpoint
creates one window. No new screen, no list/management UI."""
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


# --- Codex round-16 OWNER_DECISION_NEEDED findings (owner-ruled 2026-08-27) ---
# Real gaps only: end-inclusive date + decision-link threading + roster/
# pickable visibility. Atomicity-of-3-writes and a window management screen
# were explicitly rejected by the owner as unrequested new architecture.


def test_list_roster_includes_external_support(client, conn):
    """FINDING 5: list_roster used to filter to LOCAL only, so an
    EXTERNAL_SUPPORT person was invisible on their own roster screen --
    could not be seen or removed via the normal "Usuń z obsady" button."""
    client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"})
    rows = client.get(f"/api/workspace/sites/{SITE}/roster").json()
    row = next(r for r in rows if r["employee_id"] == "EXT-1")
    assert row["membership_kind"] == "EXTERNAL_SUPPORT"
    assert row["enabled"] is True


def test_disabled_external_support_is_pickable_for_readd(client, conn):
    """FINDING 5: a disabled EXTERNAL_SUPPORT row used to be excluded from
    the picker entirely, so re-adding the same support person a second
    time (a normal insert/remove/insert-again cycle) was impossible."""
    client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"})
    client.patch(f"/api/workspace/sites/{SITE}/roster/EXT-1", json={"enabled": False})
    pickable = client.get(f"/api/workspace/sites/{SITE}/roster/pickable").json()
    row = next(r for r in pickable if r["employee_id"] == "EXT-1")
    assert row["reason"] == "re-add"


def test_enabled_external_support_is_not_pickable(client, conn):
    client.post(f"/api/workspace/sites/{SITE}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"})
    pickable = client.get(f"/api/workspace/sites/{SITE}/roster/pickable").json()
    assert all(r["employee_id"] != "EXT-1" for r in pickable)


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
    site_id, profile_id = "SITE-UNDERSTAFFED-EXT", "PROF-UNDERSTAFFED-EXT"
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
    save_employee(connection, Employee("EXT-1", "External Ela", date(2020, 1, 1), None, False))
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


def test_attach_to_roster_with_responds_to_decision_required_id_clears_the_decision(understaffed_site, understaffed_client):
    """FINDING 2: attach_to_roster never threaded responds_to_decision_required_id,
    so resolving a DECISION_REQUIRED via "+ Dodaj osobę" from the Decisions
    screen left the decision open even though the underlying membership
    write went through."""
    _, site_id = understaffed_site
    plan_resp = understaffed_client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    decision_id = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()["decision_required_id"]

    resp = understaffed_client.post(
        f"/api/workspace/sites/{site_id}/roster",
        json={"employee_id": "EXT-1", "responds_to_decision_required_id": decision_id},
    )
    assert resp.status_code == 204

    months_after = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/months").json()
    assert months_after == {"months": []}


def test_create_support_window_with_responds_to_decision_required_id_clears_the_decision(understaffed_site, understaffed_client):
    """Mirrors the real "+ Dodaj osobę" sequencing: attaching membership is
    an intermediate step (it already invalidates every current decision
    for the site on its own -- any roster change forces re-plan), so only
    the LAST write, the window, carries the decision link. Linking BOTH
    steps to the same id would hand the second call an already-stale id
    (owner-caught bug while implementing OWNER_CORRECTED finding 2)."""
    _, site_id = understaffed_site
    plan_resp = understaffed_client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    decision_id = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()["decision_required_id"]

    understaffed_client.post(
        f"/api/workspace/sites/{site_id}/roster", json={"employee_id": "EXT-1", "membership_kind": "EXTERNAL_SUPPORT"},
    )
    # Membership attach already invalidated the current decision above --
    # re-plan to get a fresh, still-current decision id for this month
    # before exercising the window endpoint's own linking.
    understaffed_client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    decision_id = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()["decision_required_id"]

    resp = understaffed_client.post(
        f"/api/workspace/employees/EXT-1/support-window",
        json={
            "site_id": site_id, "start_datetime": f"{MONTH_STR}T00:00:00", "end_datetime": "2026-09-01T00:00:00",
            "allowed_shift_kind": None, "responds_to_decision_required_id": decision_id,
        },
    )
    assert resp.status_code == 204

    months_after = understaffed_client.get(f"/api/workspace/sites/{site_id}/decisions/months").json()
    assert months_after == {"months": []}


if __name__ == "__main__":
    print("test_t021_external_support_roster module OK")
