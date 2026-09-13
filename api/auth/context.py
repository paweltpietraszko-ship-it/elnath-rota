"""ROTA-T024 brief.md section 6: the one request-scoped owner of Rota
identity for CENTRAL_SERVICE -- carries the authenticated account id,
its resolved database path, and its coordinator_id together, so no
downstream code ever mixes one account's database with another's
coordinator_id or vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.backend import current_active_user
from api.auth.db import get_async_session
from api.auth.models import AccountMapping, User


@dataclass(frozen=True)
class AuthenticatedContext:
    user_id: str
    db_path: Path
    coordinator_id: str


async def get_authenticated_context(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> AuthenticatedContext:
    """brief.md T24-3: db_path/coordinator_id are resolved ONLY from this
    server-side mapping, keyed by the authenticated account id -- never
    from any request body/query/path parameter."""
    # Read fresh, not at import time -- api.config.ACCOUNTS_DB_DIR must
    # reflect whatever the current process/test actually configured.
    from api.config import ACCOUNTS_DB_DIR

    mapping = await session.get(AccountMapping, user.id)
    if mapping is None or not mapping.active:
        # brief section 5: an authenticated-but-unprovisioned/deactivated
        # account must not reach any domain database.
        raise HTTPException(status_code=403, detail="Konto nie jest jeszcze skonfigurowane.")
    # brief section 5: db_filename is a bare filename, resolved against
    # the ONE trusted directory -- never a caller-influenced path.
    db_path = (ACCOUNTS_DB_DIR / mapping.db_filename).resolve()
    if db_path.parent != ACCOUNTS_DB_DIR.resolve():
        # Fails closed if a filename ever contained a path separator --
        # should be structurally impossible (provisioning controls this),
        # but this is the one boundary that must never trust it blindly.
        raise HTTPException(status_code=403, detail="Nieprawidłowa konfiguracja konta.")
    return AuthenticatedContext(user_id=str(user.id), db_path=db_path, coordinator_id=mapping.coordinator_id)
