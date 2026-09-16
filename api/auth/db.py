"""ROTA-T024 brief.md section 5: the small, separate async SQLAlchemy
engine backing the auth SQLite (AUTH_DB_PATH) -- fastapi-users requires
an async session; this file owns exactly that, and Rota's own
AccountMapping table lives in the same engine/database.

The engine/sessionmaker are lazily constructed and memoized (same pattern
as api/runtime_log.py's logger) rather than built at import time: a real
CENTRAL_SERVICE process sets ROTA_AUTH_DB_PATH once before startup, so
this only matters for tests that need a fresh engine per AUTH_DB_PATH --
reset_for_tests() (mirroring runtime_log.reset_for_tests()) drops the
memoized engine so the next call re-reads api.config.AUTH_DB_PATH.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from api.auth.models import AccountMapping, ApiKey, Base, User

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def reset_for_tests() -> None:
    global _engine, _session_maker
    _engine = None
    _session_maker = None


def _get_engine() -> AsyncEngine:
    global _engine, _session_maker
    if _engine is None:
        from api.config import AUTH_DB_PATH

        _engine = create_async_engine(f"sqlite+aiosqlite:///{AUTH_DB_PATH}")
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    _get_engine()
    assert _session_maker is not None  # noqa: S101 -- _get_engine() always sets it
    return _session_maker


async def create_auth_db_and_tables() -> None:
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def session_maker() -> async_sessionmaker[AsyncSession]:
    """Public accessor for callers outside a FastAPI dependency chain
    (api/provision_account.py's CLI)."""
    return _get_session_maker()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_maker()() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User)


__all__ = [
    "AccountMapping", "ApiKey", "create_auth_db_and_tables", "get_async_session", "get_user_db",
    "reset_for_tests", "session_maker",
]
