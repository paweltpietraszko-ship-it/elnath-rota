"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md section 7: an alternative
credential for the Excel add-in, alongside (never replacing) the
existing browser/PWA cookie/JWT auth (api/auth/backend.py,
api/auth/context.py). Administrator issues one key per account
(api/provision_account.py); the add-in sends it as
`Authorization: Bearer <key>` on every request, no interactive login.

Resolves the SAME AccountMapping -> db_path + coordinator_id the cookie
path resolves -- never a second identity model, never a caller-supplied
db_path/coordinator_id (XL-02/XL-03).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.db import get_async_session
from api.auth.models import AccountMapping, ApiKey

if TYPE_CHECKING:
    # Type-only: the real (runtime) import is deferred to function scope
    # inside get_authenticated_context_by_api_key below, to break an
    # import cycle -- api.auth.backend (which api.auth.context imports
    # current_active_user from) now also imports create_api_key from this
    # module (ROTA-EXCEL-UI-PANEL). `from __future__ import annotations`
    # above means this module-level import is never evaluated at runtime,
    # so it's safe here even though it's re-imported for real below.
    from api.auth.context import AuthenticatedContext

_KEY_PREFIX = "rota_"


def generate_api_key() -> str:
    return f"{_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    # raw_key is a 256-bit random token, not a human-chosen password -- a
    # fast, unsalted SHA-256 digest is the standard approach for
    # high-entropy API keys (unlike bcrypt for low-entropy user passwords,
    # which fastapi-users' own UserManager already owns for login
    # credentials -- this is an intentionally separate, simpler scheme).
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def create_api_key(session: AsyncSession, auth_user_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    """The one canonical key-issuance path -- api/provision_account.py's
    CLI and the self-service `/auth/me/excel-api-key` endpoint both call
    this instead of each inserting an ApiKey row themselves (ROTA-EXCEL-
    UI-PANEL). Returns (key_id, raw_key); only the hash is persisted, so
    the caller must show raw_key to the user now -- it is never
    recoverable again."""
    key_id = uuid.uuid4()
    raw_key = generate_api_key()
    session.add(ApiKey(key_id=key_id, auth_user_id=auth_user_id, key_hash=hash_api_key(raw_key), active=True))
    await session.commit()
    return key_id, raw_key


async def get_authenticated_context_by_api_key(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> AuthenticatedContext:
    """XL-02/XL-03: a valid key resolves the existing server-side
    AccountMapping; an invalid, malformed, or revoked key never reaches
    the domain database."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak nagłówka Authorization: Bearer <klucz>.")
    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key:
        raise HTTPException(status_code=401, detail="Pusty klucz dostępu.")
    key_hash = hash_api_key(raw_key)
    api_key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if api_key is None or not api_key.active:
        raise HTTPException(status_code=401, detail="Nieprawidłowy lub unieważniony klucz dostępu.")
    # Both deferred to function scope: ACCOUNTS_DB_DIR read fresh (mirrors
    # api/auth/context.py's own get_authenticated_context); AuthenticatedContext
    # breaks the api.auth.context <-> api.auth.backend <-> api.auth.api_key
    # import cycle created when api.auth.backend started importing
    # create_api_key from this module (ROTA-EXCEL-UI-PANEL) -- this is a
    # REAL runtime construction below, not just a type annotation, so it
    # cannot be a TYPE_CHECKING-only import.
    from api.auth.context import AuthenticatedContext
    from api.config import ACCOUNTS_DB_DIR

    mapping = await session.get(AccountMapping, api_key.auth_user_id)
    if mapping is None or not mapping.active:
        raise HTTPException(status_code=403, detail="Konto nie jest jeszcze skonfigurowane.")
    db_path = (ACCOUNTS_DB_DIR / mapping.db_filename).resolve()
    if db_path.parent != ACCOUNTS_DB_DIR.resolve():
        raise HTTPException(status_code=403, detail="Nieprawidłowa konfiguracja konta.")
    return AuthenticatedContext(
        user_id=str(api_key.auth_user_id), db_path=db_path, coordinator_id=mapping.coordinator_id,
    )
