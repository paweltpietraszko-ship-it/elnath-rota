from __future__ import annotations

import json
import textwrap
from datetime import date, datetime

from api.routers.excel_external import _candidate_day_grid
from rota.domain import Assignment, AssignmentRole, AssignmentState
from tests.test_excel_external_api import MONTH, _BOOTSTRAP, _assert_ok, _run


def _assignment(assignment_id: str, start_hour: int, end_hour: int, code: str) -> Assignment:
    return Assignment(
        assignment_id=assignment_id,
        schedule_version_id="PREVIEW",
        employee_id="EMP-A",
        start_datetime=datetime(2026, 11, 1, start_hour),
        end_datetime=datetime(2026, 11, 1, end_hour),
        role=AssignmentRole.PRIMARY,
        state=AssignmentState.PLANNED,
        frozen=False,
        covers_demand_id=None,
        mentor_primary_assignment_id=None,
        operational_code=code,
    )


def test_external_candidate_projection_preserves_all_same_day_work() -> None:
    """Brief section 8 / XL-12: Excel must use the shared projection.

    ORDINARY permits several independent, non-overlapping assignments on one
    day.  Both contribute to the displayed cell and total hours.
    """
    first = _assignment("A-1", 6, 12, "D1")
    second = _assignment("A-2", 14, 18, "D4")
    days = [date(2026, 11, d) for d in range(1, 31)]

    cells, total_hours = _candidate_day_grid([first, second], {}, days, {})["EMP-A"]

    assert total_hours == 10
    assert "D1" in cells[0] and "D4" in cells[0]


def test_invalid_late_availability_is_validated_before_any_write(tmp_path) -> None:
    """Brief 4.2/XL-18: validate the complete payload before first write."""
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        response = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id,
            "month": "{MONTH}",
            "target_hours": [{{"employee_id": "EMP-A", "target_hours": 55}}],
            "availability": [{{
                "availability_id": "AV-BAD",
                "employee_id": "EMP-A",
                "kind": "NOT_A_REAL_KIND",
                "start_date": "2026-11-10",
                "end_date": "2026-11-10",
                "active": True,
            }}],
        }}, headers=excel_headers)
        check = cookie_client.get(
            "/api/workspace/employees/EMP-A/target-hours",
            params={{"month": "{MONTH}"}},
        )
        print(json.dumps({{
            "response_status": response.status_code,
            "target_hours_after": check.json()["target_hours"],
        }}))
    """))
    data = _assert_ok(result)

    assert data["response_status"] == 400
    assert data["target_hours_after"] == 100
