"""ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE: dedicated matrix for the
target-hours gate (brief.md section 6, TH-01..TH-10). Narrow -- exercises
the gate itself, the bulk apply-to-all write, DEL's effect on the solver
target, and removal of the old equal-split fallback; not a full regression
of PLAN/REPLAN/precheck behavior (already covered elsewhere).
"""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap, durable_inputs, plan_ops
from rota.application.plan_ops import TargetHoursRequired
from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    SiteRoleDefinition,
    StandardShift,
    WorkBalance,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id
from rota.persistence.site_role_repository import save_site_role
from rota.persistence.work_balance_repository import get_work_balance_target
from rota.planning import fairness as fairness_module
from rota.planning import solver as solver_module
from tests.support.minimal_state import base_state

ROLE_ID = "ROLE-TH"

# api/deps.py's dev-mode get_coordinator_id() always returns DEV_COORDINATOR_ID
# regardless of what a test bootstraps -- the TH-10 (TestClient) tests below
# need this exact id to have an active association; reused everywhere in this
# file for one consistent coordinator across the app-layer and API-layer tests.
COORD = DEV_COORDINATOR_ID
SITE_ID = "SITE-TH"
PROFILE_ID = "PROFILE-TH"
MONTH = date(2026, 11, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID, display_name="TH profile", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=True,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn, regime: SitePlanningRegime = SitePlanningRegime.ORDINARY) -> None:
    # ROTA-OCHRONA-EQUITY-SURGICAL-FIX (OWNER 2026-09-20): this whole TH
    # matrix exercises the require_complete_target_hours GATE, which stays
    # mandatory for ORDINARY -- its only live repro (FF) was always
    # ORDINARY. Defaulted to ORDINARY (was OCHRONA); OCHRONA is now
    # deliberately exempt from this gate, see test_th11_ochrona_exempt_*
    # below and decisive_finding.md.
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        coordinator=Coordinator(COORD, "Coord TH", True), site_profile=_profile(),
        site=Site(SITE_ID, PROFILE_ID, "Site TH", True, planning_regime=regime),
        association=CoordinatorSiteAssociation(COORD, SITE_ID, True),
    )
    if regime == SitePlanningRegime.ORDINARY:
        # ROTA-T065-CONFIGURABLE-ROLES: an enabled ORDINARY membership must
        # name an active role from this Site's own catalog -- one generic
        # role is enough for this file's gate-focused tests.
        save_site_role(conn, SiteRoleDefinition(ROLE_ID, SITE_ID, "TH role", True))


def _employee(
    conn, employee_id: str, *, kind: MembershipKind = MembershipKind.LOCAL, enabled: bool = True,
    position_role_id: str | None = None,
) -> None:
    durable_inputs.update_employee(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False),
    )
    durable_inputs.update_membership(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        membership=SiteMembership(
            employee_id, SITE_ID, kind, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            position_role_id=position_role_id,
        ),
    )


def _fill_calendar(conn, month: date = MONTH) -> None:
    for d in range(1, calendar.monthrange(month.year, month.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, d), False))


# --- TH-01/TH-02: the gate blocks PLAN/REPLAN/precheck before the solver ----


def test_th01_missing_target_blocks_plan_before_solver_and_version(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1", position_role_id=ROLE_ID)
    _fill_calendar(conn)

    with pytest.raises(TargetHoursRequired) as exc:
        plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert exc.value.employee_ids == ["E1"]
    assert get_current_version_id(conn, SITE_ID, MONTH) is None


def test_th02_gate_covers_replan(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1", position_role_id=ROLE_ID)
    _fill_calendar(conn)

    with pytest.raises(TargetHoursRequired):
        plan_ops.replan(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    with pytest.raises(TargetHoursRequired):
        plan_ops.replan_retry_narrow(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD)
    with pytest.raises(TargetHoursRequired):
        plan_ops.replan_wider_search(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD)


# --- TH-03: EXTERNAL_SUPPORT and a disabled membership never block ---------


def test_th03_external_support_and_disabled_membership_do_not_block(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1", position_role_id=ROLE_ID)
    # A second real LOCAL employee: one alone covering every day of the
    # month trips the independent HARD max-two-consecutive-PRIMARY-shifts
    # rule, unrelated to what this test isolates (same fixture pattern as
    # e.g. tests/test_t019b.py's _seed_feasible_and_select).
    _employee(conn, "E4", position_role_id=ROLE_ID)
    _employee(conn, "X1", kind=MembershipKind.EXTERNAL_SUPPORT, position_role_id=ROLE_ID)  # no target, must not block
    _employee(conn, "E2", enabled=False)  # disabled, no target, must not block
    _fill_calendar(conn)
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E1", month=MONTH, target_hours=100)
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E4", month=MONTH, target_hours=100)

    result = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"


# --- TH-04: bulk apply-to-all --------------------------------------------


def test_th04_apply_to_all_overwrites_everyone_active_local(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1", position_role_id=ROLE_ID)
    _employee(conn, "E2", position_role_id=ROLE_ID)  # gets a different pre-existing target, must be overwritten
    _employee(conn, "X1", kind=MembershipKind.EXTERNAL_SUPPORT, position_role_id=ROLE_ID)
    _employee(conn, "E3", enabled=False)
    durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=SITE_ID, employee_id="E2", month=MONTH, target_hours=50)

    durable_inputs.set_target_hours_for_site_roster(conn, coordinator_id=COORD, site_id=SITE_ID, month=MONTH, target_hours=168)

    assert get_work_balance_target(conn, "E1", MONTH) == 168
    assert get_work_balance_target(conn, "E2", MONTH) == 168
    assert get_work_balance_target(conn, "X1", MONTH) is None
    assert get_work_balance_target(conn, "E3", MONTH) is None


# --- TH-06/TH-07: DELEGACJA realizes part of the target, current-record only -


def _delegation_record(employee_id: str, hours: int, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(
        f"AV-{employee_id}", f"AV-{employee_id}-v1", employee_id, AvailabilityKind.DELEGACJA,
        start, end, True, None, None, None, None, delegation_hours=hours,
    )


def test_th06_active_delegation_reduces_effective_target():
    # delegation_hours is a per-day rate (rota.planning.absence.
    # delegation_hours_in_range); a single delegation day worth 35h matches
    # the brief's own example (168h target + 35h DEL day -> 133h remaining).
    wb = WorkBalance("E1", MONTH, 168, 0, 0, 0, 0, 0)
    delegation = _delegation_record("E1", 35, date(2026, 11, 1), date(2026, 11, 1))
    state = base_state(month=MONTH, work_balances=(wb,), availability_records=(delegation,))
    assert solver_module._effective_targets(state) == {"E1": 133}


def test_th07_cancelled_delegation_no_longer_reduces_target():
    wb = WorkBalance("E1", MONTH, 168, 0, 0, 0, 0, 0)
    cancelled = replace(_delegation_record("E1", 35, date(2026, 11, 1), date(2026, 11, 1)), active=False)
    state = base_state(month=MONTH, work_balances=(wb,), availability_records=(cancelled,))
    assert solver_module._effective_targets(state) == {"E1": 168}


# --- TH-08: Urlop/L4 still reduce target the existing way ------------------


def test_th08_absence_hours_still_reduce_target_without_delegation():
    wb = WorkBalance("E1", MONTH, 168, 0, 0, 0, 0, 0, absence_hours=24)
    state = base_state(month=MONTH, work_balances=(wb,))
    assert solver_module._effective_targets(state) == {"E1": 144}


# --- TH-09: the fallback is really gone -------------------------------------


def test_th09_equal_split_fallback_removed_from_production():
    assert not hasattr(fairness_module, "add_equal_split_fairness")
    assert not hasattr(solver_module, "add_equal_split_fairness")


# --- TH-11: OWNER 2026-09-20 -- OCHRONA is exempt from this gate -----------


def test_th11_ochrona_exempt_from_gate(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn, regime=SitePlanningRegime.OCHRONA)
    _employee(conn, "E1")
    _fill_calendar(conn)

    # Must not raise -- decisive_finding.md: OCHRONA never had the
    # absence-blindness bug this gate was built for (ORDINARY/FF only),
    # and solver.add_ochrona_hours_fairness is absence/delegation-aware
    # with or without a complete target vector.
    plan_ops.require_complete_target_hours(conn, site_id=SITE_ID, month=MONTH)


# --- TH-10: exact response shape on TARGET_HOURS_REQUIRED -------------------


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "rota.db")
    _bootstrap(connection)
    _employee(connection, "E1", position_role_id=ROLE_ID)
    _fill_calendar(connection)
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


def test_th10_plan_response_shape_on_target_hours_required(client):
    resp = client.post(
        f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH.isoformat()}/plan", json={"effective_from": MONTH.isoformat()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "TARGET_HOURS_REQUIRED"
    assert body["candidates"] == []
    assert body["decision_payload"] is None
    assert body["error_message"] is None
    assert body["optimization_complete"] is False
    assert body["missing_target_hours"] == [{"employee_id": "E1", "employee_display_name": "E1"}]
    assert "E1" not in "".join(body["warnings"])


def test_th10_precheck_response_shape_on_target_hours_required(client):
    resp = client.get(f"/api/workspace/sites/{SITE_ID}/schedule/{MONTH.isoformat()}/precheck")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "TARGET_HOURS_REQUIRED"
    assert body["under_covered_demand_ids"] == []
    assert body["missing_target_hours"] == [{"employee_id": "E1", "employee_display_name": "E1"}]
