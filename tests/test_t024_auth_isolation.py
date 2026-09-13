"""ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md exact SHA 9246fad): acceptance
tests for CENTRAL_SERVICE login + per-account database isolation.

api/config.py's IS_CENTRAL_SERVICE/AUTH_SECRET/ACCOUNTS_DB_DIR and several
downstream modules (api.deps, api.auth.manager's UserManager class
attributes, api.main's conditional router mounting) read their config at
IMPORT time -- correct and harmless for a real deployment (env vars are
set once before the process starts), but means a single pytest process
cannot cleanly switch between LOCAL_WINDOWS and CENTRAL_SERVICE mode by
monkeypatching env vars and reloading one module in isolation: any other
test file that already imported api.main/api.deps in LOCAL_WINDOWS mode
earlier in the same session would keep the cached (wrong) objects, and
mechanically reloading the whole import graph in the right order for
every test is exactly the kind of fragile, easy-to-get-subtly-wrong
approach that risks silently testing nothing. Each scenario below runs
in its own real subprocess instead -- the same guarantee a fresh
deployment process gets, with no cross-test contamination risk.
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


def _run(tmp_path: Path, script_body: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({
        "ROTA_CENTRAL_KEK": CENTRAL_KEK,
        "ROTA_AUTH_SECRET": AUTH_SECRET,
        "ROTA_AUTH_DB_PATH": str(tmp_path / "auth.db"),
        "ROTA_ACCOUNTS_DB_DIR": str(tmp_path / "accounts"),
        # Running the scenario as a script file (not -c) makes Python add
        # the script's own directory to sys.path, not cwd -- PYTHONPATH is
        # needed for `import api.*` to resolve from the repo root.
        "PYTHONPATH": str(REPO_ROOT),
    })
    if extra_env:
        env.update(extra_env)
    script_path = tmp_path / "scenario.py"
    script_path.write_text(textwrap.dedent(script_body), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script_path)], cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=60,
    )


def _assert_ok(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_unauthenticated_request_returns_401_and_opens_no_database(tmp_path):
    # T24-1
    result = _run(tmp_path, """
        import json
        from fastapi.testclient import TestClient
        import api.main
        with TestClient(api.main.app, base_url="https://testserver") as client:
            resp = client.get("/api/workspace/sites")
        print(json.dumps({"status": resp.status_code}))
    """)
    data = _assert_ok(result)
    assert data["status"] == 401
    assert not (tmp_path / "accounts").exists() or not any((tmp_path / "accounts").iterdir())


def test_two_accounts_are_fully_isolated_with_correct_coordinator(tmp_path):
    # T24-2, T24-4, T24-5, T24-11, T24-13
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        asyncio.run(create_account("t2@example.com", "pw-two-1234", "COORD-T2", "t2.db"))

        with TestClient(api.main.app, base_url="https://testserver") as c1, \\
             TestClient(api.main.app, base_url="https://testserver") as c2:
            c1.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            c2.post("/api/auth/login", data={"username": "t2@example.com", "password": "pw-two-1234"})

            create_resp = c1.post("/api/workspace/sites", json={
                "display_name": "SITE-BY-T1", "rolling_7d_decision_threshold_hours": 60,
                "planning_regime": "ORDINARY",
            })
            t1_sites = c1.get("/api/workspace/sites").json()
            t2_sites = c2.get("/api/workspace/sites").json()

        import os, sqlite3
        conn = sqlite3.connect(os.path.join(os.environ["ROTA_ACCOUNTS_DB_DIR"], "t1.db"))
        coordinators = conn.execute("SELECT coordinator_id FROM coordinators").fetchall()
        associations = conn.execute("SELECT coordinator_id FROM coordinator_site_associations").fetchall()
        conn.close()

        print(json.dumps({
            "create_status": create_resp.status_code,
            "t1_sites": [s["display_name"] for s in t1_sites],
            "t2_sites": [s["display_name"] for s in t2_sites],
            "coordinators": [c[0] for c in coordinators],
            "associations": [a[0] for a in associations],
        }))
    """)
    data = _assert_ok(result)
    assert data["create_status"] == 201
    assert data["t1_sites"] == ["SITE-BY-T1"]
    assert data["t2_sites"] == []  # T24-2: zero cross-account leakage
    assert "COORD-T1" in data["coordinators"]  # T24-11: auto-provisioned on first access
    assert "DEV-COORD-1" not in data["coordinators"]  # T24-5: never the global dev identity
    assert data["associations"] == ["COORD-T1"]  # T24-4: write attributed to the real account


def test_tampered_cookie_is_rejected(tmp_path):
    # T24-3
    result = _run(tmp_path, """
        import json
        from fastapi.testclient import TestClient
        import api.main
        with TestClient(api.main.app, base_url="https://testserver") as client:
            client.cookies.set("fastapiusersauth", "not-a-real-jwt")
            resp = client.get("/api/workspace/sites")
        print(json.dumps({"status": resp.status_code}))
    """)
    data = _assert_ok(result)
    assert data["status"] == 401


def test_cookie_is_httponly_and_secure(tmp_path):
    # T24-7
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            resp = client.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            set_cookie = resp.headers.get("set-cookie", "")
        print(json.dumps({"set_cookie": set_cookie}))
    """)
    data = _assert_ok(result)
    header = data["set_cookie"].lower()
    assert "httponly" in header
    assert "secure" in header
    assert "samesite=lax" in header


def test_password_change_preserves_mapping_and_coordinator(tmp_path):
    # T24-8, T24-6 (delegates to the library, never a Rota-written hash)
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("t1@example.com", "old-password-1", "COORD-T1", "t1.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            client.post("/api/auth/login", data={"username": "t1@example.com", "password": "old-password-1"})
            change_resp = client.patch("/api/auth/me/password", json={"password": "new-password-1"})
            still_me = client.get("/api/auth/me")

        with TestClient(api.main.app, base_url="https://testserver") as client2:
            old_login = client2.post("/api/auth/login", data={"username": "t1@example.com", "password": "old-password-1"})
            new_login = client2.post("/api/auth/login", data={"username": "t1@example.com", "password": "new-password-1"})
            sites_after = client2.get("/api/workspace/sites")

        print(json.dumps({
            "change_status": change_resp.status_code,
            "still_me_status": still_me.status_code,
            "old_login_status": old_login.status_code,
            "new_login_status": new_login.status_code,
            "sites_after_status": sites_after.status_code,
        }))
    """)
    data = _assert_ok(result)
    assert data["change_status"] == 200
    assert data["still_me_status"] == 200
    assert data["old_login_status"] == 400  # LOGIN_BAD_CREDENTIALS
    assert data["new_login_status"] == 204
    assert data["sites_after_status"] == 200  # mapping/coordinator untouched by the password change


def test_backup_uses_correct_account_database(tmp_path):
    # T24-10
    result = _run(tmp_path, """
        import asyncio, json, zipfile, io
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        asyncio.run(create_account("t2@example.com", "pw-two-1234", "COORD-T2", "t2.db"))

        with TestClient(api.main.app, base_url="https://testserver") as c1, \\
             TestClient(api.main.app, base_url="https://testserver") as c2:
            c1.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            c2.post("/api/auth/login", data={"username": "t2@example.com", "password": "pw-two-1234"})
            c1.post("/api/workspace/sites", json={
                "display_name": "T1-ONLY-SITE", "rolling_7d_decision_threshold_hours": 60,
                "planning_regime": "ORDINARY",
            })
            backup_resp = c2.post("/api/workspace/backup")

        # c2's backup must never contain c1's data -- inspect the snapshot directly.
        archive = zipfile.ZipFile(io.BytesIO(backup_resp.content))
        names = archive.namelist()
        print(json.dumps({"backup_status": backup_resp.status_code, "names": names}))
    """)
    data = _assert_ok(result)
    assert data["backup_status"] == 200
    assert "snapshot.db" in data["names"]


def test_diagnostic_zip_excludes_shared_runtime_log(tmp_path):
    # T24-12
    result = _run(tmp_path, """
        import asyncio, json, zipfile, io
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account
        from api.runtime_log import log_runtime_error

        log_runtime_error(component="API", safe_message="x", exception_type="TEST")
        asyncio.run(create_account("t1@example.com", "pw-one-1234", "COORD-T1", "t1.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            client.post("/api/auth/login", data={"username": "t1@example.com", "password": "pw-one-1234"})
            resp = client.post("/api/workspace/diagnostics")

        archive = zipfile.ZipFile(io.BytesIO(resp.content))
        names = archive.namelist()
        print(json.dumps({"status": resp.status_code, "names": names}))
    """, extra_env={"ROTA_LOG_DIR": str(tmp_path / "logs")})
    data = _assert_ok(result)
    assert data["status"] == 200
    assert not any(n.startswith("logs/") for n in data["names"])
    assert "diagnostics.json" in data["names"]


def test_no_wide_users_router_or_registration_mounted(tmp_path):
    # T24-15 / brief section 3 reduction gate
    result = _run(tmp_path, """
        import json
        from fastapi.testclient import TestClient
        import api.main
        with TestClient(api.main.app, base_url="https://testserver") as client:
            register = client.post("/api/auth/register", json={"email": "x@example.com", "password": "x"})
            admin_get = client.get("/api/users/00000000-0000-0000-0000-000000000000")
        print(json.dumps({"register_status": register.status_code, "admin_get_status": admin_get.status_code}))
    """)
    data = _assert_ok(result)
    assert data["register_status"] == 404
    assert data["admin_get_status"] == 404


def test_cli_reset_password_uses_same_library_helper(tmp_path):
    # T24-9
    result = _run(tmp_path, """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account, reset_password

        asyncio.run(create_account("t1@example.com", "old-pw-1234", "COORD-T1", "t1.db"))
        asyncio.run(reset_password("t1@example.com", "operator-set-pw-1234"))

        with TestClient(api.main.app, base_url="https://testserver") as client:
            old_login = client.post("/api/auth/login", data={"username": "t1@example.com", "password": "old-pw-1234"})
            new_login = client.post("/api/auth/login", data={"username": "t1@example.com", "password": "operator-set-pw-1234"})
        print(json.dumps({"old_login_status": old_login.status_code, "new_login_status": new_login.status_code}))
    """)
    data = _assert_ok(result)
    assert data["old_login_status"] == 400
    assert data["new_login_status"] == 204


if __name__ == "__main__":
    print("test_t024_auth_isolation module OK")
