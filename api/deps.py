"""Connection-per-request lifecycle. Opening/closing is the API layer's
own concern (brief.md section 3.2) -- never exposed to the frontend.

ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md exact SHA 9246fad, section 11):
get_conn/get_coordinator_id are defined ONCE per process, branching on
api.config.IS_CENTRAL_SERVICE at import time -- never per-request. A
given deployment is one mode for its whole process lifetime, so this
keeps every router's own `Depends(get_conn)` call site unchanged
regardless of mode; only the implementation swaps.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from rota.persistence.db import connect

from api.config import DB_PATH, DEV_COORDINATOR_ID, IS_CENTRAL_SERVICE

if IS_CENTRAL_SERVICE:
    from fastapi import Depends

    from api.auth.context import AuthenticatedContext, get_authenticated_context
    from rota.persistence.coordinator_repository import CoordinatorNotFound, get_coordinator, save_coordinator
    from rota.domain import Coordinator

    def _ensure_coordinator_exists(conn: sqlite3.Connection, coordinator_id: str) -> None:
        # brief.md section 7: a freshly-provisioned account's first access
        # bootstraps exactly one active Coordinator matching its own
        # coordinator_id -- read-then-maybe-write so this stays a no-op
        # write on every later request, not an UPSERT every time.
        try:
            get_coordinator(conn, coordinator_id)
        except CoordinatorNotFound:
            save_coordinator(conn, Coordinator(coordinator_id=coordinator_id, display_name="Koordynator", active=True))

    def get_conn(context: AuthenticatedContext = Depends(get_authenticated_context)) -> Iterator[sqlite3.Connection]:
        conn = connect(context.db_path)
        _ensure_coordinator_exists(conn, context.coordinator_id)
        try:
            yield conn
        finally:
            conn.close()

    def get_coordinator_id(context: AuthenticatedContext = Depends(get_authenticated_context)) -> str:
        return context.coordinator_id

    def get_db_path(context: AuthenticatedContext = Depends(get_authenticated_context)):
        return context.db_path

else:
    def get_conn() -> Iterator[sqlite3.Connection]:
        conn = connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()

    def get_coordinator_id() -> str:
        return DEV_COORDINATOR_ID

    def get_db_path() -> str:
        return DB_PATH
