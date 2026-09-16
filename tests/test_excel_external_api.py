"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md sections 4/5/6: narrow vertical
tests for the external Excel router -- PLAN -> candidates -> explicit
select -> accepted schedule, REPLAN only before first acceptance, the
roster gate, the idempotent reconciler, TARGET_HOURS_REQUIRED's plain-
language blocker, and stale candidate_id rejection. Same real-subprocess
pattern as tests/test_t024_auth_isolation.py/test_excel_api_key_auth.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CENTRAL_KEK = "aa" * 32
AUTH_SECRET = "test-secret-must-be-at-least-32-bytes-long"
MONTH = "2026-11-01"


def _run(tmp_path: Path, script_body: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({
        "ROTA_CENTRAL_KEK": CENTRAL_KEK,
        "ROTA_AUTH_SECRET": AUTH_SECRET,
        "ROTA_AUTH_DB_PATH": str(tmp_path / "auth.db"),
        "ROTA_ACCOUNTS_DB_DIR": str(tmp_path / "accounts"),
        "PYTHONPATH": str(REPO_ROOT),
    })
    script_path = tmp_path / "scenario.py"
    script_path.write_text(textwrap.dedent(script_body), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script_path)], cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=60,
    )


def _assert_ok(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


# Shared bootstrap: one OCHRONA site, one D-only shift (1 required/day, every
# weekday), two LOCAL employees, a full calendar, and an issued API key.
# Emitted as Python source (not a function) so each scenario script can
# inline it before its own test-specific calls.
_BOOTSTRAP = f"""
import asyncio, json, uuid
from fastapi.testclient import TestClient
import api.main
from api.provision_account import create_account
from api.auth.api_key import generate_api_key, hash_api_key
from api.auth.db import session_maker
from api.auth.models import ApiKey
from api.provision_account import _user_manager

asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))

async def issue(email):
    async with session_maker()() as session:
        manager = await _user_manager(session)
        user = await manager.get_by_email(email)
        raw = generate_api_key()
        session.add(ApiKey(key_id=uuid.uuid4(), auth_user_id=user.id, key_hash=hash_api_key(raw), active=True))
        await session.commit()
    return raw

api_key = asyncio.run(issue("t1@example.com"))

cookie_client = TestClient(api.main.app, base_url="https://testserver")
cookie_client.post("/api/auth/login", data={{"username": "t1@example.com", "password": "pw-one-1234"}})
site_id = cookie_client.post("/api/workspace/sites", json={{
    "display_name": "SITE-1", "rolling_7d_decision_threshold_hours": 60, "planning_regime": "OCHRONA",
}}).json()["site_id"]
cookie_client.put(f"/api/workspace/sites/{{site_id}}/shift-catalog", json={{
    "shifts": [{{"kind": "D", "start_time": "06:00", "end_time": "18:00", "required_primary_count": 1, "active_weekdays": [0,1,2,3,4,5,6]}}],
}})
for eid, name in (("EMP-A", "Anna Testowa"), ("EMP-B", "Bartek Testowy")):
    cookie_client.post("/api/workspace/employees", json={{"employee_id": eid, "site_id": site_id, "display_name": name, "day_only": False}})
    cookie_client.post(f"/api/workspace/sites/{{site_id}}/roster", json={{"employee_id": eid}})
cookie_client.post("/api/workspace/calendar/generate", json={{"site_id": site_id, "month": "{MONTH}"}})
for eid in ("EMP-A", "EMP-B"):
    cookie_client.post(f"/api/workspace/employees/{{eid}}/target-hours", json={{"site_id": site_id, "month": "{MONTH}", "target_hours": 100}})

excel = TestClient(api.main.app, base_url="https://testserver")
excel_headers = {{"Authorization": f"Bearer {{api_key}}"}}
"""


def test_plan_select_replan_lifecycle(tmp_path):
    # XL-01/05/06/07/08/09
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        plan_resp = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [], "availability": [],
        }}, headers=excel_headers)
        plan_body = plan_resp.json()
        candidate = plan_body["candidates"][0]

        select_resp = excel.post("/api/external/excel/select-candidate", json={{
            "site_id": site_id, "month": "{MONTH}", "candidate_id": candidate["candidate_id"],
        }}, headers=excel_headers)

        schedule_resp = excel.get(f"/api/external/excel/schedule/{{site_id}}/{MONTH}", headers=excel_headers)

        replan_after_accept = excel.post("/api/external/excel/replan", json={{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [], "availability": [],
        }}, headers=excel_headers)

        recompute = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [], "availability": [],
        }}, headers=excel_headers)

        print(json.dumps({{
            "plan_status": plan_resp.status_code, "plan_result_status": plan_body["status"],
            "candidate_row_count": len(candidate["rows"]),
            "select_status": select_resp.status_code,
            "schedule_status": schedule_resp.status_code, "schedule_rows": len(schedule_resp.json()["rows"]),
            "replan_after_accept_status": replan_after_accept.json()["status"],
            "recompute_status": recompute.json()["status"],
        }}))
    """))
    data = _assert_ok(result)
    assert data["plan_status"] == 200
    assert data["plan_result_status"] == "FEASIBLE"
    assert data["candidate_row_count"] == 2  # both LOCAL employees present
    assert data["select_status"] == 204
    assert data["schedule_status"] == 200
    assert data["schedule_rows"] == 2
    # XL-09: REPLAN is refused once accepted; the existing lifecycle owns this.
    assert data["replan_after_accept_status"] == "REPLAN_NOT_AVAILABLE"
    # Przelicz Plan (plain PLAN) still works after acceptance.
    assert data["recompute_status"] == "FEASIBLE"


def test_roster_gate_rejects_whole_payload_before_any_write(tmp_path):
    # XL-18
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        resp = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id, "month": "{MONTH}",
            "target_hours": [{{"employee_id": "EMP-A", "target_hours": 55}}, {{"employee_id": "GHOST", "target_hours": 10}}],
            "availability": [],
        }}, headers=excel_headers)
        check = cookie_client.get("/api/workspace/employees/EMP-A/target-hours", params={{"month": "{MONTH}"}})
        print(json.dumps({{"status": resp.status_code, "emp_a_target_after": check.json()}}))
    """))
    data = _assert_ok(result)
    assert data["status"] == 400
    # The whole request was rejected before any write -- EMP-A's real
    # target_hours (100, set by the shared bootstrap) must be untouched,
    # never silently overwritten to 55 from the same rejected payload.
    assert data["emp_a_target_after"]["target_hours"] == 100


def test_retry_same_availability_payload_does_not_duplicate(tmp_path):
    # XL-19
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        payload = {{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [],
            "availability": [{{
                "availability_id": "AV-1", "employee_id": "EMP-A", "kind": "LEAVE_GRANTED",
                "start_date": "2026-11-10", "end_date": "2026-11-10", "active": True,
            }}],
        }}
        first = excel.post("/api/external/excel/plan", json=payload, headers=excel_headers)
        second = excel.post("/api/external/excel/plan", json=payload, headers=excel_headers)

        import sqlite3, os
        conn = sqlite3.connect(os.path.join(os.environ["ROTA_ACCOUNTS_DB_DIR"], "t1.db"))
        count = conn.execute("SELECT COUNT(*) FROM availability_versions WHERE availability_id = 'AV-1'").fetchone()[0]
        conn.close()
        print(json.dumps({{"first_status": first.status_code, "second_status": second.status_code, "version_count": count}}))
    """))
    data = _assert_ok(result)
    assert data["first_status"] == 200
    assert data["second_status"] == 200
    # Retry with an identical payload must not append a second version of
    # the same already-applied availability fact.
    assert data["version_count"] == 1


def test_missing_target_hours_returns_plain_language_blocker(tmp_path):
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        # A third LOCAL employee joins with no target_hours at all.
        cookie_client.post("/api/workspace/employees", json={{"employee_id": "EMP-C", "site_id": site_id, "display_name": "Celina Testowa", "day_only": False}})
        cookie_client.post(f"/api/workspace/sites/{{site_id}}/roster", json={{"employee_id": "EMP-C"}})

        resp = excel.post("/api/external/excel/plan", json={{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [], "availability": [],
        }}, headers=excel_headers)
        body = resp.json()
        print(json.dumps({{"status": resp.status_code, "result_status": body["status"], "blocker": body["blocker"]}}))
    """))
    data = _assert_ok(result)
    assert data["status"] == 200
    assert data["result_status"] == "TARGET_HOURS_REQUIRED"
    assert "Celina Testowa" in data["blocker"]["message"]
    assert "Przelicz" in data["blocker"]["message"]
    assert data["blocker"]["employee_ids"] == ["EMP-C"]


def test_stale_or_foreign_candidate_id_is_rejected(tmp_path):
    # XL-16
    result = _run(tmp_path, _BOOTSTRAP + textwrap.dedent(f"""
        excel.post("/api/external/excel/plan", json={{
            "site_id": site_id, "month": "{MONTH}", "target_hours": [], "availability": [],
        }}, headers=excel_headers)
        resp = excel.post("/api/external/excel/select-candidate", json={{
            "site_id": site_id, "month": "{MONTH}", "candidate_id": "not-a-real-hash",
        }}, headers=excel_headers)
        print(json.dumps({{"status": resp.status_code}}))
    """))
    data = _assert_ok(result)
    assert data["status"] == 409
