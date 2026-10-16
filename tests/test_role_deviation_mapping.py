"""ROTA-UNMAPPED-DEVIATION-RULES (brief section 4, R1-R4): a coordinator's
deliberate manual correction putting a person without the demand's required
role on an ORDINARY shift is saved, and ROLE-01 becomes a PREFERENCE
Deviation (OWNER 2026-10-16: the program never forbids the coordinator,
it records the decision). The automatic ROLE-01 gate is unchanged."""
from __future__ import annotations

import calendar
from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.deviation_mapping import category_for_rule
from rota.application.durable_inputs import update_employee, update_membership
from rota.application.errors import UnknownDeviationSource
from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, CalendarDay, Coordinator, CoordinatorSiteAssociation,
    DeviationCategory, Employee, MembershipKind, ReadinessSource, ReadinessState, ShiftDemand, ShiftKind, Site,
    SiteMembership, SitePlanningRegime, SiteProfile, SiteRoleDefinition, StandardShift,
)
from rota.persistence import schedule_lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_memory import list_coordinator_actions
from rota.persistence.site_role_repository import save_site_role

COORD = DEV_COORDINATOR_ID
SITE = "SITE-ROLE"
PROFILE = "PROF-ROLE"
KIER, SPRZ = "ROLE-KIER", "ROLE-SPRZ"
FUTURE = date(2027, 3, 1)
POSITIONS = {"E1": KIER, "E2": SPRZ, "E3": SPRZ}


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Koordynator", True),
        site_profile=SiteProfile(PROFILE, "Sklep", True, [StandardShift(ShiftKind.D, time(8), time(16), False, 1)],
                                 True, False, False, False, 1, 72),
        site=Site(SITE, PROFILE, "Sklep", True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    save_site_role(connection, SiteRoleDefinition(KIER, SITE, "Kierownik", True))
    save_site_role(connection, SiteRoleDefinition(SPRZ, SITE, "Sprzedawca", True))
    for employee_id, role_id in POSITIONS.items():
        update_employee(connection, coordinator_id=COORD, site_id=SITE,
                        employee=Employee(employee_id, f"Pracownik {employee_id}", date(2020, 1, 1), None, False))
        update_membership(connection, coordinator_id=COORD, site_id=SITE, membership=SiteMembership(
            employee_id, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            position_role_id=role_id,
        ))
    for day in range(1, calendar.monthrange(FUTURE.year, FUTURE.month)[1] + 1):
        save_calendar_day(connection, CalendarDay(date(FUTURE.year, FUTURE.month, day), False))
    demand = ShiftDemand("D-SPRZ", "V0", datetime(2027, 3, 10, 8), datetime(2027, 3, 10, 16), 1,
                         shift_kind=ShiftKind.D, required_role_id=SPRZ, required_role_name="Sprzedawca")
    schedule_lifecycle.create_schedule_version(
        connection, version_id="V0", site_id=SITE, month=FUTURE, parent_version_id=None,
        created_at=datetime(2026, 10, 1, 8), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[demand], deviations=[], effective_from=FUTURE,
        assignments=[Assignment("A-1", "V0", "E2", demand.start_datetime, demand.end_datetime,
                                AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-SPRZ", None)],
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


def _reassign(client, employee_id: str):
    return client.post(f"/api/workspace/sites/{SITE}/schedule/{FUTURE.isoformat()}/manual-correction", json={
        "upsert_assignments": [{
            "assignment_id": "A-1", "schedule_version_id": "V0", "employee_id": employee_id,
            "start_datetime": "2027-03-10T08:00:00", "end_datetime": "2027-03-10T16:00:00",
            "role": "PRIMARY", "state": "PLANNED", "frozen": False, "covers_demand_id": "D-SPRZ",
            "mentor_primary_assignment_id": None,
        }],
        "note": "świadoma decyzja koordynatora",
    })


def _positions(conn) -> dict[str, str | None]:
    return {m.employee_id: m.position_role_id for m in list_memberships_for_site(conn, SITE)}


def test_r1_r2_manual_reassign_without_role_saved_as_preference_deviation(conn, client):
    actions_before = len(list_coordinator_actions(conn, site_id=SITE))
    resp = _reassign(client, "E1")  # Kierownik on a Sprzedawca demand
    assert resp.status_code == 200, resp.text
    child_id = get_current_version_id(conn, SITE, FUTURE)
    assert child_id != "V0"
    child = get_schedule_snapshot(conn, child_id)
    role_devs = [d for d in child.deviations if d.source_reference == "ROLE-01"]
    assert len(role_devs) == 1 and role_devs[0].category == DeviationCategory.PREFERENCE
    assert get_schedule_snapshot(conn, "V0").assignments[0].employee_id == "E2"  # parent untouched
    assert _positions(conn) == POSITIONS  # no role granted to the person
    assert len(list_coordinator_actions(conn, site_id=SITE)) == actions_before + 1
    month = client.get(f"/api/workspace/sites/{SITE}/schedule/{FUTURE.isoformat()}").json()
    labels = {d["source_reference"]: d["label"] for d in month["deviations"]}
    assert labels["ROLE-01"] == "brak wymaganej roli"


def test_r3_reassign_to_person_with_required_role_has_no_role_deviation(conn, client):
    resp = _reassign(client, "E3")
    assert resp.status_code == 200, resp.text
    child = get_schedule_snapshot(conn, get_current_version_id(conn, SITE, FUTURE))
    assert not [d for d in child.deviations if d.source_reference == "ROLE-01"]


def test_r4_unknown_rule_code_still_fails_closed():
    assert category_for_rule("ROLE-01", {}) == DeviationCategory.PREFERENCE
    with pytest.raises(UnknownDeviationSource):
        category_for_rule("NOT-A-RULE-01", {})
