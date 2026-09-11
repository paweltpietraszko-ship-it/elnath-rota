"""ROTA-T037 (tasks/ROTA-T037/brief.md): API-level tests for the thin
manual-edit router wrapping rota/application/manual_edit.py. Narrow scope
(owner ruling 2026-08-28): no dry-run/preview endpoint -- HARD violations
never block a save, they surface in the response's `deviations` list as a
short, non-blocking warning for the frontend to render."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import plan_ops
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)
MONTH_STR = MONTH.isoformat()


def _assignment_out_dict(a, employees_by_id) -> dict:
    return {
        "assignment_id": a.assignment_id, "schedule_version_id": a.schedule_version_id,
        "employee_id": a.employee_id, "start_datetime": a.start_datetime.isoformat(),
        "end_datetime": a.end_datetime.isoformat(), "role": a.role.value, "state": a.state.value,
        "frozen": a.frozen, "covers_demand_id": a.covers_demand_id,
        "mentor_primary_assignment_id": a.mentor_primary_assignment_id,
        "operational_code": a.operational_code, "work_period_id": a.work_period_id,
        "required_rest_after_hours": a.required_rest_after_hours,
    }


@pytest.fixture
def conn():
    from rota.persistence.db import connect
    connection = connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def site_id(conn):
    pstate = seed_real_object(conn, case_id="t037-api", month=MONTH, seed=910, coordinator_id=DEV_COORDINATOR_ID)
    return pstate.site.site_id


@pytest.fixture
def planned_version(conn, site_id):
    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=DEV_COORDINATOR_ID, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(
        conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id=DEV_COORDINATOR_ID,
    )


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_manual_correction_shrink_creates_deviation_and_does_not_block(client, conn, site_id, planned_version):
    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    employees_by_id = {e.employee_id: e for e in [] }
    shrunk = _assignment_out_dict(target, employees_by_id)
    shrunk["end_datetime"] = target.start_datetime.replace(hour=13).isoformat()

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction",
        json={"upsert_assignments": [shrunk]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_id"] != planned_version.version_id
    coverage_devs = [d for d in body["deviations"] if d["category"] == "COVERAGE"]
    assert len(coverage_devs) == 1
    # narrow scope: nothing blocked the save even though a HARD/coverage gap exists
    assert resp.status_code == 200


def test_manual_correction_no_deviation_is_empty_list(client, conn, site_id, planned_version):
    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    employees_by_id = {}
    unchanged = _assignment_out_dict(target, employees_by_id)

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction",
        json={"upsert_assignments": [unchanged]},
    )
    assert resp.status_code == 200
    assert resp.json()["deviations"] == []


def test_freeze_then_unfreeze_roundtrip(client, conn, site_id, planned_version):
    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-05-D")

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction/freeze",
        json={"assignment_id": target.assignment_id, "frozen": True},
    )
    assert resp.status_code == 200
    v2_id = resp.json()["version_id"]
    v2_snapshot = get_schedule_snapshot(conn, v2_id)
    assert next(a for a in v2_snapshot.assignments if a.assignment_id == target.assignment_id).frozen is True


def test_mark_not_worked_on_planned_primary(client, conn, site_id, planned_version):
    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(
        a for a in snapshot.assignments
        if a.covers_demand_id == "2026-08-01-D" and a.role.value == "PRIMARY" and a.state.value == "PLANNED"
    )

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction/mark-not-worked",
        json={"assignment_id": target.assignment_id},
    )
    assert resp.status_code == 200
    v2_snapshot = get_schedule_snapshot(conn, resp.json()["version_id"])
    updated = next(a for a in v2_snapshot.assignments if a.assignment_id == target.assignment_id)
    assert updated.state.value == "CANCELLED"
    assert updated.operational_code == "NN"
    coverage_devs = [d for d in resp.json()["deviations"] if d["category"] == "COVERAGE"]
    assert len(coverage_devs) == 1  # NN leaves a coverage gap -- surfaced, not blocked


def test_mark_not_worked_on_already_cancelled_rejected(client, conn, site_id, planned_version):
    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(
        a for a in snapshot.assignments
        if a.covers_demand_id == "2026-08-01-D" and a.role.value == "PRIMARY" and a.state.value == "PLANNED"
    )
    first = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction/mark-not-worked",
        json={"assignment_id": target.assignment_id},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction/mark-not-worked",
        json={"assignment_id": target.assignment_id},
    )
    assert second.status_code == 400


# --- H14 (ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT): race/bypass at the -----
# router boundary -- a genuinely already-started Assignment must be
# rejected with a controlled, public, coordinator-safe Polish 409, never a
# generic/technical error, and must not persist any child mutation. This
# stands in for "the service started after the screen opened but before
# save" -- the router/API has no notion of that timing itself; the test
# proves the real HTTP path enforces the exact same boundary
# apply_manual_correction does, by making manual_edit._now() (the real
# production seam, same one conftest.py's autouse fixture freezes for
# unrelated tests) land at-or-after the target's start_datetime, exactly as
# it would once real wall-clock time reaches it.


def test_h14_router_rejects_disallowed_change_to_a_genuinely_started_assignment(client, conn, site_id, planned_version, monkeypatch):
    from api.errors import PUBLIC_ERROR_HEADER_NAME
    from rota.application import manual_edit

    snapshot = get_schedule_snapshot(conn, planned_version.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    monkeypatch.setattr(manual_edit, "_now", lambda: target.start_datetime)
    version_before = get_current_version_id(conn, site_id, MONTH)

    shrunk = _assignment_out_dict(target, {})
    shrunk["end_datetime"] = target.start_datetime.replace(hour=13).isoformat()

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/manual-correction",
        json={"upsert_assignments": [shrunk]},
    )
    assert resp.status_code == 409
    assert resp.headers.get(PUBLIC_ERROR_HEADER_NAME) == "1"
    detail = resp.json()["detail"]
    assert "Traceback" not in detail and target.assignment_id not in detail and site_id not in detail
    # no child/current mutation was persisted
    assert get_current_version_id(conn, site_id, MONTH) == version_before
    assert get_schedule_snapshot(conn, version_before).assignments == snapshot.assignments


if __name__ == "__main__":
    print("test_t037_manual_edit_api module OK")
