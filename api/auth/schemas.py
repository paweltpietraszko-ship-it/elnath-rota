"""ROTA-T024: minimal fastapi_users Pydantic schemas -- brief.md section 3
excludes public registration/reset flows, so only Read/Update are needed
(no Create schema, no registration router mounted anywhere)."""
from __future__ import annotations

import uuid

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class UserCreate(schemas.BaseUserCreate):
    """Used only by api/provision_account.py's CLI (brief section 4:
    accounts are created manually by the operator, never via a public
    registration endpoint -- no router exposes this schema)."""


class PasswordChangeRequest(BaseModel):
    """R4-02 fix: PATCH /api/auth/me/password's public payload contract is
    password-only. Rejects any other field (including email/is_active/
    is_superuser/is_verified, which the full UserUpdate would silently
    accept) instead of relying on UserManager.update(safe=True), which
    does not block email changes."""

    model_config = ConfigDict(extra="forbid")

    password: str


class ApiKeyIssuedOut(BaseModel):
    """ROTA-EXCEL-UI-PANEL: response for self-service Excel API key
    issuance -- raw_key is shown exactly once, matching
    api/provision_account.py's CLI (issue-api-key) behavior; only its
    hash is ever persisted (api.auth.api_key.create_api_key)."""

    key_id: uuid.UUID
    raw_key: str
