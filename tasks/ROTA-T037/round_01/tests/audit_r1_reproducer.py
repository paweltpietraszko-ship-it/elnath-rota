"""Independent T037 vertical: FastAPI -> application owner -> SQLite readback.

One solver setup is reused for all three newly exposed write paths.  The
assertions stay at the T037 seam: child/current version, parent immutability,
and the existing month-view projection of the saved correction/deviation.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application.plan_ops import plan_month, select_candidate
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from tests.support.t009_fixtures import seed_real_object


MONTH = date(2026, 8, 1)


def _assignment_input(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "employee_display_name"}


def test_t037_api_vertical_all_three_operations() -> None:
    conn = connect(":memory:")
    try:
        state = seed_real_object(
            conn,
            case_id="t037-codex-r1",
            month=MONTH,
            seed=937,
            coordinator_id=DEV_COORDINATOR_ID,
        )
        planned = plan_month(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id=DEV_COORDINATOR_ID,
            effective_from=MONTH,
        )
        assert planned.status == "FEASIBLE"
        parent = select_candidate(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            candidate=planned.candidates[0],
            coordinator_id=DEV_COORDINATOR_ID,
        )
        parent_snapshot = get_schedule_snapshot(conn, parent.version_id)

        app.dependency_overrides[get_conn] = lambda: (yield conn)
        client = TestClient(app)
        base = f"/api/workspace/sites/{state.site.site_id}/schedule/{MONTH.isoformat()}"

        first_view = client.get(base)
        assert first_view.status_code == 200
        target = next(
            row for row in first_view.json()["assignments"]
            if row["role"] == "PRIMARY" and row["state"] == "PLANNED"
        )
        roster = client.get(f"/api/workspace/sites/{state.site.site_id}/roster")
        assert roster.status_code == 200
        replacement = next(
            row for row in roster.json()
            if row["enabled"] and row["employee_id"] != target["employee_id"]
        )

        corrected = _assignment_input(target)
        corrected["employee_id"] = replacement["employee_id"]
        correction = client.post(
            f"{base}/manual-correction",
            json={"effective_from": "2026-08-02", "upsert_assignments": [corrected]},
        )
        assert correction.status_code == 200
        corrected_version_id = correction.json()["version_id"]
        after_correction = client.get(base).json()
        assert after_correction["current_version"]["version_id"] == corrected_version_id
        corrected_row = next(
            row for row in after_correction["assignments"]
            if row["assignment_id"] == target["assignment_id"]
        )
        assert corrected_row["employee_id"] == replacement["employee_id"]
        original = next(
            row for row in parent_snapshot.assignments
            if row.assignment_id == target["assignment_id"]
        )
        assert original.employee_id == target["employee_id"]

        freeze = client.post(
            f"{base}/manual-correction/freeze",
            json={
                "effective_from": "2026-08-03",
                "assignment_id": target["assignment_id"],
                "frozen": True,
            },
        )
        assert freeze.status_code == 200
        after_freeze = client.get(base).json()
        frozen_row = next(
            row for row in after_freeze["assignments"]
            if row["assignment_id"] == target["assignment_id"]
        )
        assert frozen_row["frozen"] is True

        nn = client.post(
            f"{base}/manual-correction/mark-not-worked",
            json={
                "effective_from": "2026-08-04",
                "assignment_id": target["assignment_id"],
            },
        )
        assert nn.status_code == 200
        after_nn = client.get(base).json()
        assert after_nn["current_version"]["version_id"] == nn.json()["version_id"]
        nn_row = next(
            row for row in after_nn["assignments"]
            if row["assignment_id"] == target["assignment_id"]
        )
        assert nn_row["state"] == "CANCELLED"
        assert nn_row["operational_code"] == "NN"
        assert any(d["category"] == "COVERAGE" for d in after_nn["deviations"])

        forbidden = client.post(
            f"{base}/manual-correction/freeze",
            json={
                "effective_from": "2026-08-05",
                "assignment_id": target["assignment_id"],
                "frozen": False,
                "invented_field": True,
            },
        )
        assert forbidden.status_code == 422
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()
