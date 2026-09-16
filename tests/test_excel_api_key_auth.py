"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 7 (XL-02/XL-03/XL-04):
the Excel add-in's API-key credential resolves the same server-side
AccountMapping the browser cookie path resolves, isolates tenants
exactly like the cookie path, and never disturbs the existing cookie/JWT
auth. Same real-subprocess pattern as tests/test_t024_auth_isolation.py
(api.config's IS_CENTRAL_SERVICE/AUTH_SECRET/ACCOUNTS_DB_DIR are read at
import time, so each scenario needs its own fresh process).
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


def test_valid_key_resolves_correct_account_isolated_from_others(tmp_path):
    # XL-02: a valid key resolves the existing AccountMapping, never a
    # foreign account's database/coordinator_id.
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account
        from api.auth.api_key import generate_api_key, hash_api_key
        from api.auth.db import session_maker
        from api.auth.models import ApiKey

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        asyncio.run(create_account("t2@example.com", "pw-two-1234", "COORD-T2", "t2.db"))

        async def issue(email):
            import uuid
            from api.provision_account import _user_manager
            async with session_maker()() as session:
                manager = await _user_manager(session)
                user = await manager.get_by_email(email)
                raw = generate_api_key()
                session.add(ApiKey(key_id=uuid.uuid4(), auth_user_id=user.id, key_hash=hash_api_key(raw), active=True))
                await session.commit()
            return raw

        key1 = asyncio.run(issue("t1@example.com"))

        # Attach one real site to t1's own account (via its cookie login)
        # so the API-key path below reads that SAME site from t1's own db.
        with TestClient(api.main.app, base_url="https://testserver") as cookie_client:
            cookie_client.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            create_resp = cookie_client.post("/api/workspace/sites", json={
                "display_name": "SITE-BY-T1", "rolling_7d_decision_threshold_hours": 60,
                "planning_regime": "OCHRONA",
            })
            site_id = create_resp.json()["site_id"]

        with TestClient(api.main.app, base_url="https://testserver") as client:
            resp_own_site = client.get(
                f"/api/external/excel/schedule/{site_id}/2026-11-01",
                headers={"Authorization": f"Bearer {key1}"},
            )
            resp_no_auth = client.get(f"/api/external/excel/schedule/{site_id}/2026-11-01")
        print(json.dumps({
            "resp_own_site": resp_own_site.status_code, "resp_own_site_body": resp_own_site.json(),
            "resp_no_auth": resp_no_auth.status_code,
        }))
    """)
    data = _assert_ok(result)
    # A resolvable key reading its OWN just-created, still-empty site is a
    # normal 200-with-empty-rows read -- proves it authenticated into
    # t1's own database, not t2's (which has no such site_id at all).
    assert data["resp_own_site"] == 200
    assert data["resp_own_site_body"] == {"rows": []}
    assert data["resp_no_auth"] == 401


def test_invalid_and_revoked_key_return_401_and_open_no_database(tmp_path):
    # XL-03
    result = _run(tmp_path, """
        import asyncio, json, uuid
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account, revoke_api_key
        from api.auth.db import session_maker
        from api.auth.models import ApiKey

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))

        async def issue_and_get_raw():
            from api.auth.api_key import generate_api_key, hash_api_key
            from api.provision_account import _user_manager
            async with session_maker()() as session:
                manager = await _user_manager(session)
                user = await manager.get_by_email("t1@example.com")
                raw = generate_api_key()
                key_id = uuid.uuid4()
                session.add(ApiKey(key_id=key_id, auth_user_id=user.id, key_hash=hash_api_key(raw), active=True))
                await session.commit()
            return raw, str(key_id)

        raw_key, key_id = asyncio.run(issue_and_get_raw())
        asyncio.run(revoke_api_key(key_id))

        with TestClient(api.main.app, base_url="https://testserver") as client:
            resp_revoked = client.get(
                "/api/external/excel/schedule/SITE-1/2026-11-01",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            resp_garbage = client.get(
                "/api/external/excel/schedule/SITE-1/2026-11-01",
                headers={"Authorization": "Bearer not-a-real-key"},
            )
        print(json.dumps({"revoked": resp_revoked.status_code, "garbage": resp_garbage.status_code}))
    """)
    data = _assert_ok(result)
    assert data["revoked"] == 401
    assert data["garbage"] == 401


def test_cookie_auth_still_works_unmodified_alongside_api_key_router(tmp_path):
    # XL-04
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            login = client.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            sites = client.get("/api/workspace/sites")
        print(json.dumps({"login": login.status_code, "sites": sites.status_code}))
    """)
    data = _assert_ok(result)
    assert data["login"] == 204
    assert data["sites"] == 200
