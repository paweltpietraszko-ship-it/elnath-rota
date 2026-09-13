from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    EmployeeRole,
    MembershipKind,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
)
from rota.persistence.db import connect
from rota.planning.eligibility import check_eligibility
from rota.planning.validator import validate
from tests.support.minimal_state import PROFILE_ID, SITE_ID, base_profile, base_state


KIEROWNIK = EmployeeRole.KIEROWNIK
SPRZEDAWCA = EmployeeRole.SPRZEDAWCA_ZALOGA


def _employee(*, day_only: bool = False) -> Employee:
    return Employee("E1", "E1", date(2020, 1, 1), None, day_only)


def _membership(*roles: EmployeeRole) -> SiteMembership:
    from rota.domain import ReadinessSource, ReadinessState

    return SiteMembership(
        "E1",
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        allowed_roles=frozenset(roles),
    )


def _role_demand(demand_id: str, day: int, *, kind: ShiftKind = ShiftKind.N) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "test-v1",
        datetime(2026, 10, day, 22, 0),
        datetime(2026, 10, day + 1, 6, 0),
        1,
        shift_kind=kind,
        required_role=SPRZEDAWCA,
    )


def test_new_ordinary_role_demand_does_not_inherit_day_only_n_gate() -> None:
    demand = _role_demand("D-1", 1)
    result = check_eligibility(
        _employee(day_only=True),
        _membership(SPRZEDAWCA),
        demand,
        ShiftKind.N,
        base_profile(),  # existing new-Site defaults include day_only_blocks_n=True
        [],
        [],
        SITE_ID,
    )
    assert result.eligible is True, result.blocked_reason


def test_new_ordinary_role_demands_do_not_inherit_night_streak() -> None:
    demands = tuple(_role_demand(f"D-{day}", day) for day in range(1, 4))
    assignments = [
        Assignment(
            f"A-{day}",
            "test-v1",
            "E1",
            demand.start_datetime,
            demand.end_datetime,
            AssignmentRole.PRIMARY,
            AssignmentState.PLANNED,
            False,
            demand.demand_id,
            None,
        )
        for day, demand in enumerate(demands, 1)
    ]
    report = validate(
        base_state(
            employees=(_employee(),),
            memberships=(_membership(SPRZEDAWCA),),
            shift_demands=demands,
        ),
        assignments,
    )
    codes = {detail.rule for detail in report.violation_details}
    assert "NIGHT-STREAK-01" not in codes, codes


def test_validator_role_gate_cannot_be_bypassed_by_missing_demand_tag() -> None:
    demand = ShiftDemand(
        "D-MANAGER",
        "test-v1",
        datetime(2026, 10, 1, 5, 0),
        datetime(2026, 10, 1, 12, 0),
        1,
        shift_kind=ShiftKind.D,
        required_role=KIEROWNIK,
    )
    wrong_role_assignment = Assignment(
        "A-SELLER",
        "test-v1",
        "E1",
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        None,  # public manual-correction DTO permits this
        None,
    )
    report = validate(
        base_state(
            employees=(_employee(),),
            memberships=(_membership(SPRZEDAWCA),),
            shift_demands=(demand,),
        ),
        [wrong_role_assignment],
    )
    codes = {detail.rule for detail in report.violation_details}
    assert "COVERAGE-01" not in codes, codes
    assert "ROLE-01" in codes, codes


@pytest.fixture
def catalog_client(request):
    regime = request.param
    connection = connect(":memory:")
    site_id = f"SITE-{regime.value}"
    profile_id = f"PROFILE-{regime.value}"
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection,
        coordinator_id=DEV_COORDINATOR_ID,
        site_id=site_id,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True),
        site_profile=SiteProfile(profile_id, "Profile", True, [], True, True, False, False, 1, 60),
        site=Site(site_id, profile_id, "Site", True, regime),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, site_id, True),
    )
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app), site_id
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


@pytest.mark.parametrize("catalog_client", [SitePlanningRegime.ORDINARY], indirect=True)
def test_new_ordinary_catalog_rejects_missing_required_role(catalog_client) -> None:
    client, site_id = catalog_client
    row = {
        "kind": "N",
        "start_time": "22:00",
        "end_time": "06:00",
        "required_primary_count": 1,
        "active_weekdays": [1],
    }
    response = client.put(f"/api/workspace/sites/{site_id}/shift-catalog", json={"shifts": [row]})
    assert response.status_code >= 400, (response.status_code, response.text)


@pytest.mark.parametrize("catalog_client", [SitePlanningRegime.OCHRONA], indirect=True)
def test_ochrona_catalog_does_not_activate_store_roles(catalog_client) -> None:
    client, site_id = catalog_client
    row = {
        "kind": "N",
        "start_time": "22:00",
        "end_time": "06:00",
        "required_primary_count": 1,
        "active_weekdays": [1],
        "required_role": "KIEROWNIK",
    }
    response = client.put(f"/api/workspace/sites/{site_id}/shift-catalog", json={"shifts": [row]})
    if response.status_code < 400:
        persisted = client.get(f"/api/workspace/sites/{site_id}/shift-catalog").json()["shifts"][0]
        assert persisted["required_role"] is None, persisted
