"""ROTA-CLOUD-REVIEW-FIXES F7/O3 (A7): self-service password change needs the
current password, every NEW password (change, operator create, operator
reset) has at least 8 characters, an older shorter password still logs in
and can be changed. CENTRAL_SERVICE config is read at import time, so each
scenario runs in its own subprocess -- same reason as test_t024_auth_isolation."""
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

_HEADER = """
import asyncio, json
from fastapi.testclient import TestClient
import api.main
from api.provision_account import create_account, reset_password


def login(email, password):
    client = TestClient(api.main.app, base_url="https://testserver")
    status = client.post("/api/auth/login", data={"username": email, "password": password}).status_code
    return client, status
"""


def _run(tmp_path: Path, body: str) -> dict:
    env = os.environ.copy()
    env.update({
        "ROTA_CENTRAL_KEK": CENTRAL_KEK,
        "ROTA_AUTH_SECRET": AUTH_SECRET,
        "ROTA_AUTH_DB_PATH": str(tmp_path / "auth.db"),
        "ROTA_ACCOUNTS_DB_DIR": str(tmp_path / "accounts"),
        "ROTA_FRONTEND_DIST": str(tmp_path / "no-frontend-dist"),
        "PYTHONPATH": str(REPO_ROOT),
    })
    script = tmp_path / "scenario.py"
    script.write_text(textwrap.dedent(_HEADER) + textwrap.dedent(body), encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], cwd=str(REPO_ROOT), env=env,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_change_requires_correct_current_password_and_eight_characters(tmp_path):
    data = _run(tmp_path, """
        asyncio.run(create_account("t1@example.com", "stare-haslo-1", "COORD-T1", "t1.db"))
        client, _ = login("t1@example.com", "stare-haslo-1")
        missing = client.patch("/api/auth/me/password", json={"password": "nowe-haslo-1"})
        wrong = client.patch("/api/auth/me/password", json={"current_password": "zle", "password": "nowe-haslo-1"})
        short = client.patch("/api/auth/me/password", json={"current_password": "stare-haslo-1", "password": "1234567"})
        _, still_old = login("t1@example.com", "stare-haslo-1")
        ok = client.patch("/api/auth/me/password", json={"current_password": "stare-haslo-1", "password": "12345678"})
        _, old_after = login("t1@example.com", "stare-haslo-1")
        _, new_after = login("t1@example.com", "12345678")
        sites = client.get("/api/workspace/sites").status_code
        print(json.dumps({
            "missing": missing.status_code,
            "wrong": [wrong.status_code, wrong.json()["detail"], wrong.headers.get("X-Elnath-Public-Error")],
            "short": [short.status_code, short.json()["detail"], short.headers.get("X-Elnath-Public-Error")],
            "still_old": still_old, "ok": ok.status_code, "old_after": old_after, "new_after": new_after,
            "sites": sites,
        }))
    """)
    assert data["missing"] == 422
    assert data["wrong"] == [400, "Obecne hasło jest nieprawidłowe.", "1"]
    assert data["short"] == [400, "Nowe hasło musi mieć co najmniej 8 znaków.", "1"]
    assert data["still_old"] == 204  # refused changes leave the account working
    assert data["ok"] == 200
    assert data["old_after"] == 400 and data["new_after"] == 204
    assert data["sites"] == 200  # mapping/coordinator untouched


def test_operator_create_and_reset_share_the_same_minimum(tmp_path):
    data = _run(tmp_path, """
        from fastapi_users import InvalidPasswordException

        def refused(coro):
            try:
                asyncio.run(coro)
            except InvalidPasswordException:
                return True
            return False

        create_short = refused(create_account("t2@example.com", "1234567", "COORD-T2", "t2.db"))
        asyncio.run(create_account("t3@example.com", "12345678", "COORD-T3", "t3.db"))
        reset_short = refused(reset_password("t3@example.com", "short"))
        _, login_after_refused_reset = login("t3@example.com", "12345678")
        print(json.dumps({"create_short": create_short, "reset_short": reset_short,
                          "login_after_refused_reset": login_after_refused_reset}))
    """)
    assert data == {"create_short": True, "reset_short": True, "login_after_refused_reset": 204}


def test_older_short_password_still_logs_in_and_can_be_changed(tmp_path):
    data = _run(tmp_path, """
        from sqlalchemy import update
        from api.auth.db import session_maker
        from api.auth.models import User
        from fastapi_users.password import PasswordHelper

        asyncio.run(create_account("t4@example.com", "dlugie-haslo-1", "COORD-T4", "t4.db"))

        async def set_legacy_short_password():
            async with session_maker()() as session:
                await session.execute(update(User).where(User.email == "t4@example.com")
                                      .values(hashed_password=PasswordHelper().hash("abc")))
                await session.commit()

        asyncio.run(set_legacy_short_password())
        client, legacy_login = login("t4@example.com", "abc")
        changed = client.patch("/api/auth/me/password", json={"current_password": "abc", "password": "nowe-dlugie-1"})
        _, new_login = login("t4@example.com", "nowe-dlugie-1")
        print(json.dumps({"legacy_login": legacy_login, "changed": changed.status_code, "new_login": new_login}))
    """)
    assert data == {"legacy_login": 204, "changed": 200, "new_login": 204}
