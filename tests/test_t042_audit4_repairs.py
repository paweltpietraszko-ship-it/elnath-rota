"""ROTA-T042 Checkpoint C (tasks/ROTA-T042/brief.md section 4, matrix
T42-C01..C04): api/routers/schedule.py's DecisionRequiredPayloadOut and
api/routers/decisions.py's flat DecisionRequiredOut now both build their
four shared fields (blocking_shift_demands, blockers, load_blocker,
unblocking_options) through the single api/decision_payload.py adapter
(AUDIT-4 pair 9, tasks/ROTA-AUDIT4/round_01/tests/tests_r1.txt). These
tests compare real endpoint responses, not source text -- they would
catch a field/type/nesting drift introduced on either side of the shared
adapter.
"""
from __future__ import annotations

from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.decision_payload import decision_payload_out
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
from rota.planning.engine_types import Blocker, BlockingDemand, DecisionRequiredPayload, LoadBlocker, UnblockingOption

MONTH = date(2026, 8, 1)
MONTH_STR = MONTH.isoformat()

_SHARED_FIELDS = ["blocking_shift_demands", "blockers", "load_blocker", "unblocking_options"]


def _seed_days_of_month(conn, month: date) -> None:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = month
    while day < next_month:
        save_calendar_day(conn, CalendarDay(day, False))
        day = date.fromordinal(day.toordinal() + 1)


# Same shape as test_t031_schedule_api.py's understaffed_site: one shift,
# zero roster, forces DECISION_REQUIRED deterministically.
@pytest.fixture
def understaffed_client():
    connection = connect(":memory:")
    site_id, profile_id = "SITE-T042-UNDERSTAFFED", "PROF-T042-UNDERSTAFFED"
    profile = SiteProfile(
        profile_id, "Profile", True,
        [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        True, True, False, False, 1, 40,
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True),
        site_profile=profile,
        site=Site(site_id, profile_id, "T042 Understaffed", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, site_id, True),
    )
    _seed_days_of_month(connection, MONTH)
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app), site_id
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def test_t42_c01_c04_schedule_and_decisions_endpoints_agree_on_shared_fields(understaffed_client):
    client, site_id = understaffed_client

    plan_resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    )
    assert plan_resp.status_code == 200
    plan_body = plan_resp.json()
    assert plan_body["status"] == "DECISION_REQUIRED"
    assert plan_body["decision_payload"] is not None

    # T42-C04: the PLAN response's own decision_payload already carries the
    # same shape as the persisted readback below.
    for field in _SHARED_FIELDS:
        assert field in plan_body["decision_payload"]

    month_view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert month_view["decision_required"] is not None

    decision_detail = client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()
    assert decision_detail is not None

    # T42-C01: the four fields both endpoints derive from the same
    # DecisionRequiredPayload via api/decision_payload.py must be equal.
    for field in _SHARED_FIELDS:
        assert month_view["decision_required"][field] == decision_detail[field], field

    # T42-C03: decisions.py's own metadata fields are untouched by the
    # shared adapter.
    for field in ["decision_required_id", "site_id", "month", "schedule_version_id", "requested_by", "recorded_at", "linked_action_ids"]:
        assert field in decision_detail

    # Reload -- a second, independent GET pair must still agree.
    month_view_again = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    decision_detail_again = client.get(f"/api/workspace/sites/{site_id}/decisions/{MONTH_STR}").json()
    for field in _SHARED_FIELDS:
        assert month_view_again["decision_required"][field] == decision_detail_again[field], field


def test_t42_c02_shared_adapter_preserves_shape_with_and_without_load_blocker():
    without = DecisionRequiredPayload(
        blocking_shift_demands=[BlockingDemand("D-1", MONTH, MONTH)],
        blockers=[Blocker("E-1", "no eligible employee")],
        load_blocker=None,
        unblocking_options=[UnblockingOption("dodaj pracownika")],
    )
    with_load = DecisionRequiredPayload(
        blocking_shift_demands=[BlockingDemand("D-1", MONTH, MONTH)],
        blockers=[Blocker("E-1", "no eligible employee")],
        load_blocker=LoadBlocker("E-1", MONTH, MONTH, 72),
        unblocking_options=[UnblockingOption("dodaj pracownika")],
    )

    out_without = decision_payload_out(without).model_dump()
    out_with = decision_payload_out(with_load).model_dump()

    assert out_without["load_blocker"] is None
    assert out_with["load_blocker"] == {
        "employee_id": "E-1", "window_start": MONTH.isoformat(), "window_end": MONTH.isoformat(), "hours": 72,
    }
    # Every other field keeps the same shape regardless of load_blocker.
    for field in ["blocking_shift_demands", "blockers", "unblocking_options"]:
        assert out_without[field] == out_with[field]
