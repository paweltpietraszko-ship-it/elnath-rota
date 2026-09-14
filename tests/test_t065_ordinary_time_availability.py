"""ROTA-T065-ORDINARY-TIME-AVAILABILITY (tasks/ROTA-T065-ORDINARY-TIME-AVAILABILITY/brief.md):
acceptance matrix TA-01..TA-11. One append-only AvailabilityRecord kind
(UNAVAILABLE_TIME_WINDOW), one shared pure oracle
(rota.planning.availability.unavailable_time_window_overlaps), consumed
identically by eligibility.py (automatic PLAN) and validator.py (manual
correction/REPLAN recheck), plus the ORDINARY can_work_24h/SHIFT-24-01
regime carve-out.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application.availability_matrix import employee_availability_matrix
from rota.application.durable_inputs import append_availability
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    CalendarDay,
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
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    StandardShift,
)
from rota.persistence.availability_repository import (
    append_availability_version,
    get_availability_history,
    get_current_availability_for_employee,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.planning.availability import unavailable_time_window_overlaps
from rota.planning.decision_guidance import build_unblocking_options, render_coordinator_blockers
from rota.planning.eligibility import check_eligibility
from rota.planning.engine_types import Blocker
from rota.planning.validator import validate
from tests.support.minimal_state import PROFILE_ID, SITE_ID, base_state

EMP = "EMP-1"


def _record(start_date_, end_date_, start_time_, end_time_, *, active=True):
    """A standalone AvailabilityRecord, not persisted -- the oracle takes
    values, not a live connection."""
    from rota.domain import AvailabilityRecord

    return AvailabilityRecord(
        availability_id="AV-1", availability_version_id="AVV-1", employee_id=EMP,
        kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW, start_date=start_date_, end_date=end_date_,
        active=active, supersedes_availability_version_id=None, note=None,
        start_time=start_time_, end_time=end_time_,
    )


def _demand(demand_id, start_dt, end_dt, *, catalog_kind=None, required_role_id=None):
    return ShiftDemand(demand_id, "test-v1", start_dt, end_dt, 1, catalog_kind=catalog_kind, required_role_id=required_role_id)


def _membership(employee_id=EMP, *, kind=MembershipKind.LOCAL, can_work_24h=True):
    return SiteMembership(
        employee_id, SITE_ID, kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        can_work_24h=can_work_24h,
    )


def _employee(employee_id=EMP):
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, False)


# --- TA-01: persistence round-trip ------------------------------------------


def test_ta01_append_only_write_read_preserves_dates_and_times_after_restart(tmp_path):
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    append_availability_version(
        conn, availability_id="AV-1", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
        start_date=date(2026, 9, 14), end_date=date(2026, 9, 20), active=True,
        start_time=time(0, 0), end_time=time(12, 0),
    )
    conn.close()

    reconnected = connect(db_path)
    current = get_current_availability_for_employee(reconnected, EMP)
    record = next(r for r in current if r.kind == AvailabilityKind.UNAVAILABLE_TIME_WINDOW)
    assert record.start_date == date(2026, 9, 14)
    assert record.end_date == date(2026, 9, 20)
    assert record.start_time == time(0, 0)
    assert record.end_time == time(12, 0)

    history = get_availability_history(reconnected, "AV-1")
    assert len(history) == 1
    assert history[0].start_time == time(0, 0) and history[0].end_time == time(12, 0)


def test_ta01_other_kinds_keep_start_time_end_time_none(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    record = append_availability_version(
        conn, availability_id="AV-2", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
    )
    assert record.start_time is None and record.end_time is None


def test_write_boundary_rejects_a_non_window_kind_carrying_hourly_fields(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError):
        append_availability_version(
            conn, availability_id="AV-3", employee_id=EMP, kind=AvailabilityKind.SICK_LEAVE,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
            start_time=time(0, 0), end_time=time(12, 0),
        )


def test_write_boundary_rejects_missing_times_for_the_window_kind(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError):
        append_availability_version(
            conn, availability_id="AV-4", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
        )


# --- Audit R4-01: full-hour precision enforced at the write boundary itself,
# not only by the API's own parser -------------------------------------------


def test_write_boundary_rejects_partial_start_time(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError, match="full hour"):
        append_availability_version(
            conn, availability_id="AV-7", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
            start_time=time(8, 30), end_time=time(12, 0),
        )


def test_write_boundary_rejects_partial_end_time(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError, match="full hour"):
        append_availability_version(
            conn, availability_id="AV-8", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
            start_time=time(8, 0), end_time=time(12, 15),
        )


# --- TA-04: overnight rejected at the write boundary ------------------------


def test_ta04_write_boundary_rejects_overnight_window(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError):
        append_availability_version(
            conn, availability_id="AV-5", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
            start_time=time(20, 0), end_time=time(6, 0),
        )


def test_ta04_write_boundary_rejects_equal_start_and_end(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    with pytest.raises(ValueError):
        append_availability_version(
            conn, availability_id="AV-6", employee_id=EMP, kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 5), active=True,
            start_time=time(8, 0), end_time=time(8, 0),
        )


# --- TA-02/TA-03: half-open per-day oracle -----------------------------------


def test_ta02_window_blocks_a_demand_starting_inside_it():
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    assert unavailable_time_window_overlaps(record, datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 15, 12, 0))


def test_ta02_window_blocks_a_demand_overlapping_its_tail():
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    assert unavailable_time_window_overlaps(record, datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 15, 18, 0))


def test_ta03_window_does_not_block_a_demand_starting_exactly_at_its_end():
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    assert not unavailable_time_window_overlaps(record, datetime(2026, 9, 15, 12, 0), datetime(2026, 9, 15, 19, 0))


def test_oracle_ignores_a_day_outside_the_dated_range():
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    assert not unavailable_time_window_overlaps(record, datetime(2026, 9, 21, 5, 0), datetime(2026, 9, 21, 10, 0))


def test_oracle_ignores_an_inactive_record():
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0), active=False)
    assert not unavailable_time_window_overlaps(record, datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 15, 12, 0))


def test_oracle_ignores_a_different_kind():
    record = replace(
        _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0)),
        kind=AvailabilityKind.SICK_LEAVE,
    )
    assert not unavailable_time_window_overlaps(record, datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 15, 12, 0))


# --- TA-07: automatic eligibility, LOCAL and EXTERNAL_SUPPORT identical -----


@pytest.mark.parametrize("kind", [MembershipKind.LOCAL, MembershipKind.EXTERNAL_SUPPORT])
def test_ta07_eligibility_blocks_both_membership_kinds_identically(kind):
    from rota.domain import ExternalSupportWindow

    profile = SiteProfile(PROFILE_ID, "P", True, [StandardShift(ShiftKind.D, time(5, 0), time(12, 0), False, 1)], False, True, False, False, 1, 999)
    demand = _demand("D1", datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 15, 12, 0))
    membership = _membership(kind=kind)
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    windows = ()
    if kind == MembershipKind.EXTERNAL_SUPPORT:
        windows = (ExternalSupportWindow("W1", EMP, SITE_ID, datetime(2026, 9, 1, 0, 0), datetime(2026, 10, 1, 0, 0), True, None),)
    result = check_eligibility(
        _employee(), membership, demand, ShiftKind.D, profile, [record], list(windows), SITE_ID,
        regime=SitePlanningRegime.ORDINARY,
    )
    assert not result.eligible and result.blocked_reason == "UNAVAILABLE_TIME-01"


def test_eligibility_allows_work_after_the_window_ends():
    profile = SiteProfile(PROFILE_ID, "P", True, [StandardShift(ShiftKind.D, time(12, 0), time(19, 0), False, 1)], False, True, False, False, 1, 999)
    demand = _demand("D2", datetime(2026, 9, 15, 12, 0), datetime(2026, 9, 15, 19, 0))
    membership = _membership()
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    result = check_eligibility(
        _employee(), membership, demand, ShiftKind.D, profile, [record], [], SITE_ID,
        regime=SitePlanningRegime.ORDINARY,
    )
    assert result.eligible


# --- TA-05/TA-11: can_work_24h/SHIFT-24-01 is OCHRONA-only ------------------


def test_ta05_ordinary_ignores_can_work_24h_on_an_h24_catalog_demand():
    profile = SiteProfile(PROFILE_ID, "P", True, [StandardShift(ShiftKind.D, time(5, 0), time(5, 0), True, 1, catalog_kind=ShiftCatalogKind.H24)], False, True, False, False, 1, 999)
    demand = _demand("D3", datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 16, 5, 0), catalog_kind=ShiftCatalogKind.H24)
    membership = _membership(can_work_24h=False)
    result = check_eligibility(
        _employee(), membership, demand, ShiftKind.D, profile, [], [], SITE_ID,
        regime=SitePlanningRegime.ORDINARY,
    )
    assert result.eligible


def test_ta11_ochrona_still_enforces_shift_24_01():
    profile = SiteProfile(PROFILE_ID, "P", True, [
        StandardShift(ShiftKind.D, time(5, 0), time(5, 0), True, 1, catalog_kind=ShiftCatalogKind.H24),
        StandardShift(ShiftKind.D, time(9, 0), time(11, 0), False, 1),
    ], False, True, False, False, 1, 999)
    demand = _demand("D4", datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 16, 5, 0), catalog_kind=ShiftCatalogKind.H24)
    membership = _membership(can_work_24h=False)
    result = check_eligibility(
        _employee(), membership, demand, ShiftKind.D, profile, [], [], SITE_ID,
        regime=SitePlanningRegime.OCHRONA,
    )
    assert not result.eligible and result.blocked_reason == "SHIFT-24-01"


# --- TA-08: manual correction validator, same oracle ------------------------


def test_ta08_validator_detects_the_same_overlap_as_eligibility():
    demand = _demand("D5", datetime(2026, 9, 15, 5, 0), datetime(2026, 9, 15, 12, 0))
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    state = base_state(shift_demands=(demand,), employees=(_employee(),), memberships=(_membership(),), availability_records=(record,))
    assignment = Assignment(
        "A1", "test-v1", EMP, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    report = validate(state, [assignment])
    assert not report.hard_pass
    assert any(d.rule == "UNAVAILABLE_TIME-01" for d in report.violation_details)


def test_validator_does_not_flag_work_starting_exactly_at_window_end():
    demand = _demand("D6", datetime(2026, 9, 15, 12, 0), datetime(2026, 9, 15, 19, 0))
    record = _record(date(2026, 9, 14), date(2026, 9, 20), time(0, 0), time(12, 0))
    state = base_state(shift_demands=(demand,), employees=(_employee(),), memberships=(_membership(),), availability_records=(record,))
    assignment = Assignment(
        "A2", "test-v1", EMP, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    report = validate(state, [assignment])
    assert report.hard_pass


# --- TA-06: coordinator guidance --------------------------------------------


def test_ta06_guidance_text_and_action_are_dedicated_and_never_shift24_or_nocka():
    state = base_state()
    blockers = [Blocker(EMP, "UNAVAILABLE_TIME-01")]
    rendered = render_coordinator_blockers(state, blockers)
    assert rendered == [Blocker(EMP, "Koliduje z dostępnością godzinową")]
    options = build_unblocking_options(state, blockers, None)
    texts = [o.text for o in options]
    assert f"Zmień dostępność godzinową: {EMP}" in texts
    assert not any("Zmień 24" in t or "Zmień Nocka" in t for t in texts)


# --- TA-09: availability_matrix keeps whole-day facts alongside the window --


def test_ta09_availability_matrix_includes_both_whole_day_and_hourly_records(tmp_path):
    conn = connect(tmp_path / "rota.db")
    from rota.application import bootstrap

    profile = SiteProfile(PROFILE_ID, "P", True, [], False, True, False, False, 1, 999)
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id="COORD-1", site_id=SITE_ID,
        coordinator=Coordinator("COORD-1", "Coord", True), site_profile=profile,
        site=Site(SITE_ID, PROFILE_ID, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation("COORD-1", SITE_ID, True),
    )
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, _employee())
    for day in range(1, 31):
        save_calendar_day(conn, CalendarDay(date(2026, 9, day), False))
    append_availability(
        conn, coordinator_id="COORD-1", site_id=SITE_ID, availability_id="AV-SICK", employee_id=EMP,
        kind=AvailabilityKind.SICK_LEAVE, start_date=date(2026, 9, 1), end_date=date(2026, 9, 3), active=True,
    )
    append_availability(
        conn, coordinator_id="COORD-1", site_id=SITE_ID, availability_id="AV-WINDOW", employee_id=EMP,
        kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW, start_date=date(2026, 9, 14), end_date=date(2026, 9, 20),
        active=True, start_time=time(0, 0), end_time=time(12, 0),
    )
    matrix = employee_availability_matrix(conn, site_id=SITE_ID, employee_id=EMP, month=date(2026, 9, 1))
    kinds = {r.kind for r in matrix.availability_records}
    assert AvailabilityKind.SICK_LEAVE in kinds
    assert AvailabilityKind.UNAVAILABLE_TIME_WINDOW in kinds


# --- API boundary: api/routers/durable_inputs.py + api/routers/roster.py ---


@pytest.fixture
def api_client():
    from rota.application import bootstrap
    from rota.persistence.employee_repository import save_employee, save_site_membership

    conn = connect(":memory:")
    profile = SiteProfile(PROFILE_ID, "P", True, [], False, True, False, False, 1, 999)
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=DEV_COORDINATOR_ID, site_id=SITE_ID,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True), site_profile=profile,
        site=Site(SITE_ID, PROFILE_ID, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, SITE_ID, True),
    )
    save_employee(conn, _employee())
    save_site_membership(conn, _membership())
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app), conn
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


def test_api_creates_a_valid_time_window_and_serializes_it_back(api_client):
    client, _ = api_client
    resp = client.post(
        f"/api/workspace/employees/{EMP}/availability",
        json={
            "site_id": SITE_ID, "availability_id": "AV-API-1", "kind": "UNAVAILABLE_TIME_WINDOW",
            "start_date": "2026-09-14", "end_date": "2026-09-20", "start_time": "00:00", "end_time": "12:00",
        },
    )
    assert resp.status_code == 204
    detail = client.get(f"/api/workspace/employees/{EMP}", params={"site_id": SITE_ID}).json()
    record = next(r for r in detail["availability"] if r["availability_id"] == "AV-API-1")
    assert record["start_time"] == "00:00" and record["end_time"] == "12:00"


def test_api_rejects_an_overnight_window(api_client):
    client, _ = api_client
    resp = client.post(
        f"/api/workspace/employees/{EMP}/availability",
        json={
            "site_id": SITE_ID, "availability_id": "AV-API-2", "kind": "UNAVAILABLE_TIME_WINDOW",
            "start_date": "2026-09-14", "end_date": "2026-09-20", "start_time": "20:00", "end_time": "06:00",
        },
    )
    assert resp.status_code >= 400


def test_api_rejects_a_non_window_kind_with_hourly_fields(api_client):
    client, _ = api_client
    resp = client.post(
        f"/api/workspace/employees/{EMP}/availability",
        json={
            "site_id": SITE_ID, "availability_id": "AV-API-3", "kind": "SICK_LEAVE",
            "start_date": "2026-09-14", "end_date": "2026-09-20", "start_time": "00:00", "end_time": "12:00",
        },
    )
    assert resp.status_code >= 400


if __name__ == "__main__":
    print("test_t065_ordinary_time_availability module OK")
