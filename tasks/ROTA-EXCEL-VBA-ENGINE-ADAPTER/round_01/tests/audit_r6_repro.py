from __future__ import annotations

import textwrap

from tests.test_excel_external_api import MONTH, _BOOTSTRAP, _assert_ok, _run


def test_candidate_projection_surfaces_leave_in_day_cell(tmp_path) -> None:
    """Brief 3.4/8/XL-12: candidate cells include absences via projection."""
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        response = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id,
            "month": "{MONTH}",
            "target_hours": [],
            "availability": [{{
                "availability_id": "AV-LEAVE",
                "employee_id": "EMP-A",
                "kind": "LEAVE_GRANTED",
                "start_date": "2026-11-10",
                "end_date": "2026-11-10",
                "active": True,
            }}],
        }}, headers=excel_headers)
        body = response.json()
        anna = next(row for row in body["candidates"][0]["rows"] if row["employee_id"] == "EMP-A")
        print(json.dumps({{
            "response_status": response.status_code,
            "result_status": body["status"],
            "leave_day_cell": anna["days"][9],
        }}))
    """))
    data = _assert_ok(result)

    assert data["response_status"] == 200
    assert data["result_status"] == "FEASIBLE"
    assert data["leave_day_cell"] != ""


def test_semantically_invalid_late_availability_is_validated_before_write(tmp_path) -> None:
    """Brief 4.2: semantic validation also precedes every write."""
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        response = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id,
            "month": "{MONTH}",
            "target_hours": [{{"employee_id": "EMP-A", "target_hours": 55}}],
            "availability": [{{
                "availability_id": "AV-BAD-RANGE",
                "employee_id": "EMP-A",
                "kind": "LEAVE_GRANTED",
                "start_date": "2026-11-20",
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
