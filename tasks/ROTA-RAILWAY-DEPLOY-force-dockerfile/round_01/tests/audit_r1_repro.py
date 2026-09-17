from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

from api import config


def test_railway_config_forces_root_dockerfile_builder() -> None:
    deployment = json.loads(Path("railway.json").read_text(encoding="utf-8"))

    assert deployment["build"] == {
        "builder": "DOCKERFILE",
        "dockerfilePath": "Dockerfile",
    }


def test_fresh_auth_db_parent_is_created_before_sqlite_connect(monkeypatch, tmp_path: Path) -> None:
    auth_path = tmp_path / "fresh-volume" / "auth" / "rota_auth.db"
    assert not auth_path.parent.exists()
    monkeypatch.setattr(config, "AUTH_DB_PATH", str(auth_path))

    # Load the exact owner with only its third-party imports stubbed. The local
    # audit venv has a pre-existing incompatible fastapi-users version, which
    # otherwise stops module import before this Task's code can execute.
    fake_fastapi = types.ModuleType("fastapi")
    fake_fastapi.Depends = lambda dependency: dependency
    fake_users_db = types.ModuleType("fastapi_users_db_sqlalchemy")
    fake_users_db.SQLAlchemyUserDatabase = object
    fake_models = types.ModuleType("api.auth.models")
    for name in ("AccountMapping", "ApiKey", "Base", "User"):
        setattr(fake_models, name, object())

    calls: list[str] = []
    fake_asyncio = types.ModuleType("sqlalchemy.ext.asyncio")
    fake_asyncio.AsyncEngine = object
    fake_asyncio.AsyncSession = object

    def create_async_engine(url: str):
        assert auth_path.parent.is_dir()
        calls.append(url)
        return object()

    fake_asyncio.create_async_engine = create_async_engine
    fake_asyncio.async_sessionmaker = lambda engine, expire_on_commit: object()

    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)
    monkeypatch.setitem(sys.modules, "fastapi_users_db_sqlalchemy", fake_users_db)
    monkeypatch.setitem(sys.modules, "api.auth.models", fake_models)
    monkeypatch.setitem(sys.modules, "sqlalchemy.ext.asyncio", fake_asyncio)

    spec = importlib.util.spec_from_file_location("audit_auth_db", Path("api/auth/db.py"))
    assert spec and spec.loader
    auth_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auth_db)
    auth_db._get_engine()

    assert calls == [f"sqlite+aiosqlite:///{auth_path}"]
    with sqlite3.connect(auth_path):
        pass
    assert auth_path.is_file()
