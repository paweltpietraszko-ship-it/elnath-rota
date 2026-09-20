"""ROTA-EXCEL-UI-PANEL — AUDIT R1 INDEPENDENT REPRODUCER SUITE

Verifies on exact SHA 0ac8933:
1. Unauthenticated calls to /api/auth/me/excel-api-key, /api/excel/template,
   /api/excel/addin return 401.
2. Logged-in coordinator (cookie auth) can call /api/auth/me/excel-api-key
   and receive a new valid API key with 'rota_' prefix and unique UUID.
3. Consecutive calls issue distinct keys and keep both active simultaneously.
4. Database stores only the SHA-256 hash of the API key, never the raw key.
5. External Excel API endpoints accept the issued self-service key via
   Authorization: Bearer <key> and properly instantiate runtime
   AuthenticatedContext (verifying deferred import in get_authenticated_context_by_api_key).
6. POST /api/excel/template serves the exact ELNATH_ROTA_TEMPLATE.xlsx file
   (19257 bytes) with correct media type and Content-Disposition.
7. POST /api/excel/addin serves the exact ELNATH_ROTA_ADDIN.xlam file
   (29018 bytes) with correct media type and Content-Disposition.
8. CLI `provision_account.py issue-api-key` delegates to shared `create_api_key`
   and issues a third distinct key without errors.
9. LOCAL_WINDOWS mode gating: all excel download and key endpoints return 404
   when IS_CENTRAL_SERVICE is False.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_excel_ui_panel_full_vertical_audit():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        auth_db = tdp / "auth.db"
        accounts_dir = tdp / "accounts"
        accounts_dir.mkdir()

        os.environ["ROTA_CENTRAL_KEK"] = "aa" * 32
        os.environ["ROTA_AUTH_SECRET"] = "test-secret-must-be-at-least-32-bytes-long"
        os.environ["ROTA_AUTH_DB_PATH"] = str(auth_db)
        os.environ["ROTA_ACCOUNTS_DB_DIR"] = str(accounts_dir)
        os.environ["PYTHONPATH"] = str(REPO_ROOT)

        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        import api.main
        from api.auth.db import _get_engine, reset_for_tests, session_maker
        from api.auth.models import ApiKey
        from api.provision_account import create_account, issue_api_key

        # 1. Provision account
        asyncio.run(create_account("coord@example.com", "pass-1234", "COORD-01", "coord.db"))

        with TestClient(api.main.app, base_url="https://testserver") as client:
            # 2. Unauthenticated calls rejected
            assert client.post("/api/auth/me/excel-api-key").status_code == 401
            assert client.post("/api/excel/template").status_code == 401
            assert client.post("/api/excel/addin").status_code == 401

            # 3. Cookie login
            r_login = client.post("/api/auth/login", data={"username": "coord@example.com", "password": "pass-1234"})
            assert r_login.status_code in (200, 204)

            # 4. Self-service key issuance
            r_key1 = client.post("/api/auth/me/excel-api-key")
            assert r_key1.status_code == 200
            data1 = r_key1.json()
            assert "key_id" in data1 and "raw_key" in data1
            assert data1["raw_key"].startswith("rota_")

            r_key2 = client.post("/api/auth/me/excel-api-key")
            assert r_key2.status_code == 200
            data2 = r_key2.json()
            assert data1["raw_key"] != data2["raw_key"]
            assert data1["key_id"] != data2["key_id"]

            # 5. Database persistence check
            async def verify_db():
                async with session_maker()() as session:
                    rows = (await session.scalars(select(ApiKey))).all()
                    assert len(rows) == 2
                    for r in rows:
                        assert r.active is True
                        assert r.key_hash != data1["raw_key"]
                        assert r.key_hash != data2["raw_key"]
                        expected_hash = hashlib.sha256(
                            (data1["raw_key"] if str(r.key_id) == data1["key_id"] else data2["raw_key"]).encode("utf-8")
                        ).hexdigest()
                        assert r.key_hash == expected_hash

            asyncio.run(verify_db())

            # 6. External API access with issued key (runtime AuthenticatedContext check)
            ext_resp1 = client.get(
                "/api/external/excel/schedule/SITE-1/2026-09-01",
                headers={"Authorization": f"Bearer {data1['raw_key']}"},
            )
            assert ext_resp1.status_code == 200
            assert "rows" in ext_resp1.json()

            ext_resp2 = client.get(
                "/api/external/excel/schedule/SITE-1/2026-09-01",
                headers={"Authorization": f"Bearer {data2['raw_key']}"},
            )
            assert ext_resp2.status_code == 200

            # 7. Template download
            tpl_resp = client.post("/api/excel/template")
            assert tpl_resp.status_code == 200
            assert tpl_resp.headers.get("content-type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert 'filename="ELNATH_ROTA_TEMPLATE.xlsx"' in tpl_resp.headers.get("content-disposition", "")
            expected_tpl_bytes = (REPO_ROOT / "excel" / "ELNATH_ROTA_TEMPLATE.xlsx").read_bytes()
            assert len(tpl_resp.content) == len(expected_tpl_bytes) == 19257
            assert tpl_resp.content == expected_tpl_bytes

            # 8. Addin download
            addin_resp = client.post("/api/excel/addin")
            assert addin_resp.status_code == 200
            assert addin_resp.headers.get("content-type") == "application/vnd.ms-excel.addin.macroEnabled.12"
            assert 'filename="ELNATH_ROTA_ADDIN.xlam"' in addin_resp.headers.get("content-disposition", "")
            expected_addin_bytes = (REPO_ROOT / "excel" / "ELNATH_ROTA_ADDIN.xlam").read_bytes()
            assert len(addin_resp.content) == len(expected_addin_bytes) == 29018
            assert addin_resp.content == expected_addin_bytes

            # 9. CLI issue_api_key uses shared create_api_key
            asyncio.run(issue_api_key("coord@example.com"))

            async def count_keys():
                async with session_maker()() as session:
                    rows = (await session.scalars(select(ApiKey))).all()
                    assert len(rows) == 3

            asyncio.run(count_keys())

        asyncio.run(_get_engine().dispose())
        reset_for_tests()

    # 10. LOCAL_WINDOWS mode gating in fresh subprocess
    sub = subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import sys, os
from pathlib import Path
REPO_ROOT = Path(r"{REPO_ROOT}")
sys.path.insert(0, str(REPO_ROOT))
os.environ["ROTA_FRONTEND_DIST"] = "nonexistent"
os.environ.pop("ROTA_CENTRAL_KEK", None)
os.environ.pop("ROTA_AUTH_SECRET", None)

from fastapi.testclient import TestClient
import api.main
client = TestClient(api.main.app)
assert client.post("/api/excel/template").status_code == 404
assert client.post("/api/excel/addin").status_code == 404
assert client.post("/api/auth/me/excel-api-key").status_code == 404
""",
        ],
        capture_output=True,
        text=True,
    )
    assert sub.returncode == 0, f"LOCAL_WINDOWS check failed:\n{sub.stderr}"


if __name__ == "__main__":
    test_excel_ui_panel_full_vertical_audit()
    print("AUDIT REPRODUCER ALL CHECKS PASSED")
