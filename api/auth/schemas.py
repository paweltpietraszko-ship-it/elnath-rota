"""ROTA-T024: minimal fastapi_users Pydantic schemas -- brief.md section 3
excludes public registration/reset flows, so only Read/Update are needed
(no Create schema, no registration router mounted anywhere)."""
from __future__ import annotations

import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class UserCreate(schemas.BaseUserCreate):
    """Used only by api/provision_account.py's CLI (brief section 4:
    accounts are created manually by the operator, never via a public
    registration endpoint -- no router exposes this schema)."""
