"""ROTA-T065-CONFIGURABLE-ROLES: acceptance CR-01..CR-10 not already
covered by tests/test_t065_ordinary_roles.py's re-expressed T65 scenarios.

Focus here: the NEW mechanics this brief actually introduces -- a per-Site
role catalog (no global enum), historical position-snapshot durability
across membership/catalog changes, and PlanPreview round-trip of dynamic
role ids/names.
"""
from __future__ import annotations

from datetime import date, datetime, time

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
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    SiteRoleDefinition,
    StandardShift,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import write_employee_in_open_transaction, write_site_membership_in_open_transaction
from rota.persistence.schedule_lifecycle import create_schedule_version
from rota.persistence.schedule_repository import get_schedule_version_employee_positions
from rota.persistence.site_role_repository import list_site_roles, save_site_role

COORD = DEV_COORDINATOR_ID
MONTH = date(2026, 10, 1)


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()


# --- CR-01: two Sites, unrelated role catalogs, no global enum ------------


def test_two_sites_have_independent_role_catalogs(conn):
    conn.execute("INSERT INTO coordinators (coordinator_id, display_name, active) VALUES (?, ?, ?)", (COORD, "C", 1))
    conn.execute("INSERT INTO site_profiles (profile_id, display_name, active, day_only_blocks_n, "
                 "external_support_enabled, training_s_enabled, training_s_weekdays_only, "
                 "training_s_default_readiness_threshold, rolling_7d_decision_threshold_hours) "
                 "VALUES ('P', 'P', 1, 0, 0, 0, 0, 1, 999)")
    for site_id in ("SITE-SHOP", "SITE-WAREHOUSE"):
        conn.execute(
            "INSERT INTO sites (site_id, profile_id, display_name, active, planning_regime) VALUES (?, 'P', ?, 1, 'ORDINARY')",
            (site_id, site_id),
        )
    save_site_role(conn, SiteRoleDefinition("ROLE-KIER", "SITE-SHOP", "Kierownik", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-SPRZ", "SITE-SHOP", "Sprzedawca", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-MAG", "SITE-WAREHOUSE", "Magazynier", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-WOZ", "SITE-WAREHOUSE", "Wózkowy", True))

    shop_roles = {r.role_id for r in list_site_roles(conn, "SITE-SHOP")}
    warehouse_roles = {r.role_id for r in list_site_roles(conn, "SITE-WAREHOUSE")}
    assert shop_roles == {"ROLE-KIER", "ROLE-SPRZ"}
    assert warehouse_roles == {"ROLE-MAG", "ROLE-WOZ"}


# --- CR-02: PUT shift-catalog rejects a role-less ORDINARY row -------------


@pytest.fixture
def ordinary_client_with_role(conn):
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id="SITE-1",
        coordinator=Coordinator(COORD, "Coordinator", True),
        site_profile=SiteProfile("PROF-1", "Profile", True, [], True, True, False, False, 1, 40),
        site=Site("SITE-1", "PROF-1", "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, "SITE-1", True),
    )
    save_site_role(conn, SiteRoleDefinition("ROLE-KIER", "SITE-1", "Kierownik", True))
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_ordinary_catalog_row_without_role_is_rejected(ordinary_client_with_role):
    resp = ordinary_client_with_role.put(
        "/api/workspace/sites/SITE-1/shift-catalog",
        json={"shifts": [{"start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1]}]},
    )
    assert resp.status_code == 400


def test_ordinary_catalog_row_with_unknown_role_is_rejected(ordinary_client_with_role):
    resp = ordinary_client_with_role.put(
        "/api/workspace/sites/SITE-1/shift-catalog",
        json={"shifts": [{
            "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1],
            "required_role_id": "ROLE-DOES-NOT-EXIST",
        }]},
    )
    assert resp.status_code == 400


def test_ordinary_catalog_row_with_known_role_succeeds(ordinary_client_with_role):
    resp = ordinary_client_with_role.put(
        "/api/workspace/sites/SITE-1/shift-catalog",
        json={"shifts": [{
            "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [1],
            "required_role_id": "ROLE-KIER",
        }]},
    )
    assert resp.status_code == 204
    got = ordinary_client_with_role.get("/api/workspace/sites/SITE-1/shift-catalog").json()
    assert got["shifts"][0]["required_role_id"] == "ROLE-KIER"


# --- CR-06/CR-07/CR-08: historical position snapshot durability -----------


def _bootstrap_position_site(conn) -> None:
    conn.execute("INSERT INTO coordinators (coordinator_id, display_name, active) VALUES (?, ?, ?)", (COORD, "C", 1))
    profile = SiteProfile(
        "PROF-POS", "Shop", True,
        [StandardShift(ShiftKind.D, time(5, 0), time(12, 0), False, 1, required_role_id="ROLE-KIER")],
        False, False, False, False, 1, 999,
    )
    from rota.persistence.site_profile_repository import save_site_profile
    save_site_profile(conn, profile)
    conn.execute(
        "INSERT INTO sites (site_id, profile_id, display_name, active, planning_regime) VALUES (?, ?, ?, ?, ?)",
        ("SITE-POS", "PROF-POS", "Shop", 1, "ORDINARY"),
    )
    conn.execute(
        "INSERT INTO coordinator_site_associations (coordinator_id, site_id, active) VALUES (?, ?, ?)",
        (COORD, "SITE-POS", 1),
    )
    save_site_role(conn, SiteRoleDefinition("ROLE-KIER", "SITE-POS", "Kierownik", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-SPRZ", "SITE-POS", "Sprzedawca", True))
    write_employee_in_open_transaction(conn, Employee("E1", "E1", date(2020, 1, 1), None, False))
    write_site_membership_in_open_transaction(conn, SiteMembership(
        "E1", "SITE-POS", MembershipKind.LOCAL, True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        position_role_id="ROLE-KIER",
    ))
    conn.commit()


def _accept_version(conn, version_id: str, role_id: str = "ROLE-KIER") -> None:
    demand = ShiftDemand(
        "DEM-1", version_id, datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1,
        shift_kind=ShiftKind.D, required_role_id=role_id, required_role_name="Kierownik",
    )
    assignment = Assignment(
        "A-1", version_id, "E1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    create_schedule_version(
        conn, version_id=version_id, site_id="SITE-POS", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 10, 1, 8, 0), created_by=COORD,
        applied_rule_version_ids=[], shift_demands=[demand], assignments=[assignment], deviations=[],
        effective_from=MONTH,
    )


def test_position_snapshot_captured_at_accept_time(conn):
    _bootstrap_position_site(conn)
    _accept_version(conn, "SV-1")
    positions = get_schedule_version_employee_positions(conn, "SV-1")
    assert positions["E1"].role_id == "ROLE-KIER"
    assert positions["E1"].role_name == "Kierownik"


def test_position_snapshot_survives_later_membership_change(conn):
    # CR-08: a historical reprint of an OLD version must never read today's
    # membership.
    _bootstrap_position_site(conn)
    _accept_version(conn, "SV-1")

    # Coordinator later moves E1 to a different position.
    write_site_membership_in_open_transaction(conn, SiteMembership(
        "E1", "SITE-POS", MembershipKind.LOCAL, True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        position_role_id="ROLE-SPRZ",
    ))
    conn.commit()

    positions = get_schedule_version_employee_positions(conn, "SV-1")
    assert positions["E1"].role_id == "ROLE-KIER", "old version's snapshot must not follow today's membership"


def test_position_snapshot_role_name_survives_later_rename(conn):
    # CR-07: renaming the live SiteRoleDefinition after a version is
    # accepted must not change that version's already-persisted snapshot
    # text, nor the demand's own required_role_name.
    _bootstrap_position_site(conn)
    _accept_version(conn, "SV-1")

    save_site_role(conn, SiteRoleDefinition("ROLE-KIER", "SITE-POS", "Kierownik Zmiany", True))

    positions = get_schedule_version_employee_positions(conn, "SV-1")
    assert positions["E1"].role_name == "Kierownik", "historical snapshot text must not follow a later rename"

    from rota.persistence.schedule_repository import get_schedule_snapshot
    snapshot = get_schedule_snapshot(conn, "SV-1")
    assert snapshot.shift_demands[0].required_role_name == "Kierownik"


def test_new_child_version_snapshots_position_at_its_own_creation_time(conn):
    # brief.md section 6: "nowy child ScheduleVersion... zapisuje własny
    # snapshot bieżących stanowisk... w chwili utworzenia childa" -- not the
    # parent's frozen snapshot.
    _bootstrap_position_site(conn)
    _accept_version(conn, "SV-1")

    write_site_membership_in_open_transaction(conn, SiteMembership(
        "E1", "SITE-POS", MembershipKind.LOCAL, True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        position_role_id="ROLE-SPRZ",
    ))
    conn.commit()

    demand2 = ShiftDemand(
        "DEM-2", "SV-2", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 12, 0), 1,
        shift_kind=ShiftKind.D, required_role_id="ROLE-SPRZ", required_role_name="Sprzedawca",
    )
    assignment2 = Assignment(
        "A-2", "SV-2", "E1", demand2.start_datetime, demand2.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand2.demand_id, None,
    )
    create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-POS", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 10, 2, 8, 0), created_by=COORD,
        applied_rule_version_ids=[], shift_demands=[demand2], assignments=[assignment2], deviations=[],
        effective_from=MONTH,
    )

    old_positions = get_schedule_version_employee_positions(conn, "SV-1")
    new_positions = get_schedule_version_employee_positions(conn, "SV-2")
    assert old_positions["E1"].role_id == "ROLE-KIER"
    assert new_positions["E1"].role_id == "ROLE-SPRZ"


def test_employee_with_no_position_gets_no_snapshot_row(conn):
    _bootstrap_position_site(conn)
    write_employee_in_open_transaction(conn, Employee("E2", "E2", date(2020, 1, 1), None, False))
    write_site_membership_in_open_transaction(conn, SiteMembership(
        "E2", "SITE-POS", MembershipKind.LOCAL, True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    ))
    conn.commit()
    demand = ShiftDemand(
        "DEM-1", "SV-1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, shift_kind=ShiftKind.D,
    )
    a1 = Assignment(
        "A-1", "SV-1", "E1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    a2 = Assignment(
        "A-2", "SV-1", "E2", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    create_schedule_version(
        conn, version_id="SV-1", site_id="SITE-POS", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 10, 1, 8, 0), created_by=COORD,
        applied_rule_version_ids=[], shift_demands=[demand], assignments=[a1, a2], deviations=[],
        effective_from=MONTH,
    )
    positions = get_schedule_version_employee_positions(conn, "SV-1")
    assert "E1" in positions  # has a position
    assert "E2" not in positions  # no position_role_id -- no row, not an error


if __name__ == "__main__":
    print("test_t065_configurable_roles module OK")
