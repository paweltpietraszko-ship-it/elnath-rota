from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CENTRAL_KEK = "bb" * 32


def _run(tmp_path: Path, body: str, *, auth_secret: str | None = "audit-secret-long-enough-for-tests") -> dict:
    env = os.environ.copy()
    env.update(
        {
            "ROTA_CENTRAL_KEK": CENTRAL_KEK,
            "ROTA_AUTH_DB_PATH": str(tmp_path / "auth.db"),
            "ROTA_ACCOUNTS_DB_DIR": str(tmp_path / "accounts"),
            "ROTA_LOG_DIR": str(tmp_path / "logs"),
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    if auth_secret is None:
        env.pop("ROTA_AUTH_SECRET", None)
    else:
        env["ROTA_AUTH_SECRET"] = auth_secret
    script = tmp_path / "audit_scenario.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=REPO_ROOT, env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_missing_auth_secret_fails_closed_without_issuing_session(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("a@example.com", "password-1", "COORD-A", "a.db"))
        with TestClient(api.main.app, base_url="https://testserver", raise_server_exceptions=False) as client:
            response = client.post("/api/auth/login", data={"username": "a@example.com", "password": "password-1"})
        print(json.dumps({"status": response.status_code,
                          "cookie_set": "fastapiusersauth=" in response.headers.get("set-cookie", "")}))
        """,
        auth_secret=None,
    )
    assert data["status"] == 500
    assert data["cookie_set"] is False


def test_password_only_endpoint_rejects_email_update(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, io, json, sqlite3, tempfile, zipfile
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("old@example.com", "password-1", "COORD-A", "a.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            client.post("/api/auth/login", data={"username": "old@example.com", "password": "password-1"})
            changed = client.patch("/api/auth/me/password", json={"email": "new@example.com"})
        with TestClient(api.main.app, base_url="https://testserver") as client:
            old_login = client.post("/api/auth/login", data={"username": "old@example.com", "password": "password-1"})
            new_login = client.post("/api/auth/login", data={"username": "new@example.com", "password": "password-1"})
        print(json.dumps({"changed": changed.status_code, "old": old_login.status_code, "new": new_login.status_code}))
        """,
    )
    assert data["changed"] in {400, 422}
    assert data["old"] == 204
    assert data["new"] != 204


def test_provisioning_rejects_two_accounts_for_one_domain_database(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, io, json, sqlite3, tempfile, zipfile
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("a@example.com", "password-a", "COORD-A", "shared.db"))
        second_rejected = False
        try:
            asyncio.run(create_account("b@example.com", "password-b", "COORD-B", "shared.db"))
        except Exception:
            second_rejected = True

        with TestClient(api.main.app, base_url="https://testserver") as a, TestClient(api.main.app, base_url="https://testserver") as b:
            a.post("/api/auth/login", data={"username": "a@example.com", "password": "password-a"})
            b.post("/api/auth/login", data={"username": "b@example.com", "password": "password-b"})
            created = a.post("/api/workspace/sites", json={
                "display_name": "A-ONLY", "rolling_7d_decision_threshold_hours": 60,
                "planning_regime": "ORDINARY",
            })
            b_backup = b.post("/api/workspace/backup")
        archive = zipfile.ZipFile(io.BytesIO(b_backup.content))
        with tempfile.TemporaryDirectory() as extracted:
            snapshot = archive.extract("snapshot.db", extracted)
            conn = sqlite3.connect(snapshot)
            leaked_names = [row[0] for row in conn.execute("SELECT display_name FROM sites").fetchall()]
            conn.close()
        print(json.dumps({"second_rejected": second_rejected, "created": created.status_code,
                          "b_backup": b_backup.status_code, "leaked_names": leaked_names}))
        """,
    )
    assert data["created"] == 201
    assert data["b_backup"] == 200
    assert data["leaked_names"] == [], data
    assert data["second_rejected"] is True


def test_distinct_accounts_remain_isolated_under_parallel_requests_and_logout(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, concurrent.futures, json, os, sqlite3
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("a@example.com", "password-a", "COORD-A", "a.db"))
        asyncio.run(create_account("b@example.com", "password-b", "COORD-B", "b.db"))

        def create_for(email, password, name):
            with TestClient(api.main.app, base_url="https://testserver") as client:
                login = client.post("/api/auth/login", data={"username": email, "password": password})
                created = client.post("/api/workspace/sites", json={
                    "display_name": name, "rolling_7d_decision_threshold_hours": 60,
                    "planning_regime": "ORDINARY",
                })
                logout = client.post("/api/auth/logout")
                after_logout = client.get("/api/workspace/sites")
                return [login.status_code, created.status_code, logout.status_code, after_logout.status_code]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            a_future = pool.submit(create_for, "a@example.com", "password-a", "A-ONLY")
            b_future = pool.submit(create_for, "b@example.com", "password-b", "B-ONLY")
            a_status = a_future.result()
            b_status = b_future.result()

        def names(filename):
            conn = sqlite3.connect(os.path.join(os.environ["ROTA_ACCOUNTS_DB_DIR"], filename))
            result = [row[0] for row in conn.execute("SELECT display_name FROM sites").fetchall()]
            conn.close()
            return result

        print(json.dumps({"a_status": a_status, "b_status": b_status,
                          "a_names": names("a.db"), "b_names": names("b.db")}))
        """,
    )
    assert data["a_status"] == [204, 201, 204, 401]
    assert data["b_status"] == [204, 201, 204, 401]
    assert data["a_names"] == ["A-ONLY"]
    assert data["b_names"] == ["B-ONLY"]


def test_local_windows_keeps_workspace_without_auth_surface(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("ROTA_CENTRAL_KEK", None)
    env.pop("ROTA_AUTH_SECRET", None)
    env.update({"ROTA_DB_PATH": str(tmp_path / "local.db"), "PYTHONPATH": str(REPO_ROOT)})
    script = tmp_path / "local_scenario.py"
    script.write_text(
        textwrap.dedent(
            """
            import json
            from fastapi.testclient import TestClient
            import api.main
            with TestClient(api.main.app) as client:
                workspace = client.get("/api/workspace/sites")
                login = client.post("/api/auth/login", data={"username": "x", "password": "x"})
            print(json.dumps({"workspace": workspace.status_code, "login": login.status_code}))
            """
        ),
        encoding="utf-8",
    )
    result = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data == {"workspace": 200, "login": 404}
