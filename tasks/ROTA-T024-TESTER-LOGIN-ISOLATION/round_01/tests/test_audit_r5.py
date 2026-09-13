from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
CENTRAL_KEK = "bb" * 32


def _run(tmp_path: Path, body: str) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "ROTA_AUTH_SECRET": "audit-secret-long-enough-for-tests",
            "ROTA_CENTRAL_KEK": CENTRAL_KEK,
            "ROTA_AUTH_DB_PATH": str(tmp_path / "auth.db"),
            "ROTA_ACCOUNTS_DB_DIR": str(tmp_path / "accounts"),
            "ROTA_LOG_DIR": str(tmp_path / "logs"),
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    script = tmp_path / "audit_r5_scenario.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_password_endpoint_rejects_login_change_and_preserves_account(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, json
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account

        asyncio.run(create_account("old@example.com", "password-1", "COORD-A", "a.db"))
        with TestClient(api.main.app, base_url="https://testserver") as client:
            login = client.post("/api/auth/login", data={"username": "old@example.com", "password": "password-1"})
            changed = client.patch(
                "/api/auth/me/password",
                json={"password": "password-2", "email": "new@example.com"},
            )

        with TestClient(api.main.app, base_url="https://testserver") as verifier:
            old_password = verifier.post(
                "/api/auth/login", data={"username": "old@example.com", "password": "password-1"}
            )
            new_password = verifier.post(
                "/api/auth/login", data={"username": "old@example.com", "password": "password-2"}
            )
            new_email = verifier.post(
                "/api/auth/login", data={"username": "new@example.com", "password": "password-1"}
            )
        print(json.dumps({
            "login": login.status_code,
            "changed": changed.status_code,
            "old_password": old_password.status_code,
            "new_password": new_password.status_code,
            "new_email": new_email.status_code,
        }))
        """,
    )
    assert data == {
        "login": 204,
        "changed": 422,
        "old_password": 204,
        "new_password": 400,
        "new_email": 400,
    }


def test_duplicate_mapping_is_rejected_then_valid_account_reaches_own_backup(tmp_path: Path) -> None:
    data = _run(
        tmp_path,
        """
        import asyncio, io, json, sqlite3, tempfile, zipfile
        from fastapi.testclient import TestClient
        import api.main
        from api.provision_account import create_account, DbFilenameAlreadyInUse

        asyncio.run(create_account("a@example.com", "password-a", "COORD-A", "shared.db"))
        duplicate_error = None
        try:
            asyncio.run(create_account("b@example.com", "password-b", "COORD-B", "shared.db"))
        except DbFilenameAlreadyInUse as exc:
            duplicate_error = type(exc).__name__

        # A rejected account must not exist. Provision B correctly and exercise
        # the real login -> authenticated workspace context -> backup chain.
        asyncio.run(create_account("b@example.com", "password-b", "COORD-B", "b.db"))
        with TestClient(api.main.app, base_url="https://testserver") as a, TestClient(
            api.main.app, base_url="https://testserver"
        ) as b:
            a_login = a.post("/api/auth/login", data={"username": "a@example.com", "password": "password-a"})
            b_login = b.post("/api/auth/login", data={"username": "b@example.com", "password": "password-b"})
            created = a.post("/api/workspace/sites", json={
                "display_name": "A-ONLY",
                "rolling_7d_decision_threshold_hours": 60,
                "planning_regime": "ORDINARY",
            })
            b_context = b.get("/api/workspace/sites")
            b_backup = b.post("/api/workspace/backup")

        archive = zipfile.ZipFile(io.BytesIO(b_backup.content))
        with tempfile.TemporaryDirectory() as extracted:
            snapshot = archive.extract("snapshot.db", extracted)
            conn = sqlite3.connect(snapshot)
            leaked_names = [row[0] for row in conn.execute("SELECT display_name FROM sites").fetchall()]
            conn.close()
        print(json.dumps({
            "duplicate_error": duplicate_error,
            "a_login": a_login.status_code,
            "b_login": b_login.status_code,
            "created": created.status_code,
            "b_context": b_context.status_code,
            "b_context_rows": b_context.json(),
            "b_backup": b_backup.status_code,
            "leaked_names": leaked_names,
        }))
        """,
    )
    assert data["duplicate_error"] == "DbFilenameAlreadyInUse"
    assert data["a_login"] == 204
    assert data["b_login"] == 204
    assert data["created"] == 201
    assert data["b_context"] == 200
    assert data["b_context_rows"] == []
    assert data["b_backup"] == 200
    assert data["leaked_names"] == []
