"""ROTA-T060 (tasks/ROTA-T060/brief.md @ f5f76cd, preimplementation PASS
tasks/ROTA-T060/round_01/tests/tests_r3.txt @ 1aef9fc): technical
identifiers must never reach the coordinator. This file covers the
backend contract (api/errors.py's public-error marker + roster.py's
direct bypass) and the DAY_SHIFT_OFF-01 solver warning's display-name
resolution -- frontend screen coverage lives in the corresponding .test
files under frontend/src/screens (T60-05..T60-10 targeted vertical)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import PUBLIC_ERROR_HEADER_NAME, public_http_exception, to_http_exception
from api.main import app
from rota.application.errors import InvalidCoordinatorContext, NoCurrentScheduleVersion
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ShiftDemand,
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import EmployeeNotFound, save_employee
from rota.persistence.schedule_errors import ScheduleVersionNotFound
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import SiteNotFound, save_site
from rota.planning.solver import SolverSlot, _collect_warnings
from tests.support.minimal_state import base_state

# --- T60-01/T60-02: representative controlled exceptions never leak a raw id, status preserved ---


def test_t60_01_employee_not_found_has_no_raw_id_and_correct_status():
    exc = to_http_exception(EmployeeNotFound("EMP-SECRET-42 not found"))
    assert exc.status_code == 404
    assert "EMP-SECRET-42" not in exc.detail


def test_t60_01_site_not_found_has_no_raw_id_and_correct_status():
    exc = to_http_exception(SiteNotFound("SITE-SECRET-42 not found"))
    assert exc.status_code == 404
    assert "SITE-SECRET-42" not in exc.detail


def test_t60_01_schedule_version_not_found_has_no_raw_id_and_correct_status():
    exc = to_http_exception(ScheduleVersionNotFound("SV-deadbeef1234 not found"))
    assert exc.status_code == 404
    assert "SV-deadbeef1234" not in exc.detail


def test_t60_01_invalid_coordinator_context_has_no_raw_id_and_correct_status():
    exc = to_http_exception(InvalidCoordinatorContext("coordinator 'COORD-SECRET' is not active"))
    assert exc.status_code == 403
    assert "COORD-SECRET" not in exc.detail


def test_t60_01_no_current_schedule_version_has_no_raw_id_and_correct_status():
    exc = to_http_exception(NoCurrentScheduleVersion("no current ScheduleVersion for ('SITE-SECRET', 2026-08-01)"))
    assert exc.status_code == 404
    assert "SITE-SECRET" not in exc.detail


# --- T60-03/T60-13: every controlled AND fallback error carries the public marker ---


def test_t60_public_error_header_present_on_controlled_error():
    exc = to_http_exception(EmployeeNotFound("EMP-1"))
    assert exc.headers is not None and exc.headers.get(PUBLIC_ERROR_HEADER_NAME) == "1"


def test_t60_03_unmapped_error_falls_through_to_neutral_500_with_no_raw_detail():
    exc = to_http_exception(TypeError("internal programming error, secret_token=abc123"))
    assert exc.status_code == 500
    assert "secret_token" not in exc.detail
    assert "abc123" not in exc.detail
    # R2-01.5: even the neutral 500 fallback carries the public marker, since
    # its content has already been replaced with fixed, safe text.
    assert exc.headers is not None and exc.headers.get(PUBLIC_ERROR_HEADER_NAME) == "1"


def test_t60_public_http_exception_is_the_only_header_source():
    exc = public_http_exception(409, "Testowy bezpieczny komunikat.")
    assert exc.status_code == 409
    assert exc.detail == "Testowy bezpieczny komunikat."
    assert exc.headers == {PUBLIC_ERROR_HEADER_NAME: "1"}


# --- T60-01/T60-13: real vertical, roster.py's direct bypass ---


def _bootstrap_minimal_site(conn, *, site_id: str, coordinator_id: str) -> None:
    profile = SiteProfile(
        profile_id=f"{site_id}-P", display_name="P", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=999,
    )
    save_site_profile(conn, profile)
    save_site(conn, Site(site_id, profile.profile_id, site_id, True, planning_regime=SitePlanningRegime.ORDINARY))
    save_coordinator(conn, Coordinator(coordinator_id, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(coordinator_id, site_id, True))


def test_t60_13_roster_employee_detail_missing_membership_is_public_and_id_free(tmp_path):
    site_id = "SITE-T60-ROSTER"
    conn = connect(tmp_path / "rota.db")
    _bootstrap_minimal_site(conn, site_id=site_id, coordinator_id=DEV_COORDINATOR_ID)
    employee_id = "EMP-T60-SECRET"
    save_employee(conn, Employee(employee_id, "Jan Testowy", date(2020, 1, 1), None, False))
    # Deliberately no save_site_membership() for this site -- the exact
    # "employee exists, but not a member of this site" gap roster.py's
    # direct bypass handles.

    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app)
        resp = client.get(f"/api/workspace/employees/{employee_id}", params={"site_id": site_id})
        assert resp.status_code == 404
        assert resp.headers.get(PUBLIC_ERROR_HEADER_NAME) == "1"
        assert employee_id not in resp.json()["detail"]
        assert site_id not in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# --- T60-09/T60-15: DAY_SHIFT_OFF-01 SOFT warning resolves a real display name ---


def _n_demand_for(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def test_t60_09_day_shift_off_warning_uses_real_display_name_not_employee_id():
    employee = Employee("EMP-1", "Anna Kowalska", date(2020, 1, 1), None, False)
    state = replace(base_state(), employees=(employee,))
    demand = _n_demand_for("D-1", 6)
    slot = SolverSlot(employee_id="EMP-1", demand=demand, shift_kind=ShiftKind.N, leave_plan_collision=False, day_off_soft_entry=True)
    assignment = Assignment(
        "A-1", "v1", "EMP-1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None,
    )

    warnings = _collect_warnings([assignment], [slot], state)

    assert len(warnings) == 1
    assert "Anna Kowalska" in warnings[0]
    assert "EMP-1" not in warnings[0]


def test_t60_09_day_shift_off_warning_falls_back_to_neutral_when_unresolvable():
    # state.employees deliberately does not include the assigned employee_id
    # -- should not happen in real use (slots are built from the same
    # state.employees), but the fallback must still be ID-free, not crash.
    state = base_state()
    demand = _n_demand_for("D-1", 6)
    slot = SolverSlot(employee_id="EMP-GHOST", demand=demand, shift_kind=ShiftKind.N, leave_plan_collision=False, day_off_soft_entry=True)
    assignment = Assignment(
        "A-1", "v1", "EMP-GHOST", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None,
    )

    warnings = _collect_warnings([assignment], [slot], state)

    assert len(warnings) == 1
    assert "EMP-GHOST" not in warnings[0]
    assert "pracownik" in warnings[0]
