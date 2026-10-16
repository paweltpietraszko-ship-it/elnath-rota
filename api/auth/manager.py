"""ROTA-T024 brief.md section 3: password hashing/verification and the
whole user-record lifecycle belong to fastapi-users' UserManager, not to
Rota code. This file only supplies the two required secrets and a
provisioning-time hook that seeds AccountMapping (brief section 7 talks
about the DOMAIN database's first-use Coordinator; this hook is the
auth-side equivalent -- a brand new account is useless without a mapping
row, and CLI provisioning always creates both together, see
api/provision_account.py).
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from typing import Union

from fastapi import Depends
from fastapi_users import BaseUserManager, InvalidPasswordException, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase

from api.auth.schemas import UserCreate

from api.auth.db import get_user_db
from api.auth.models import User
from api.config import AUTH_SECRET


MIN_PASSWORD_LENGTH = 8
PASSWORD_TOO_SHORT_MESSAGE = f"Nowe hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków."


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    # brief section 3: no public registration/reset-mail flow is mounted,
    # but BaseUserManager still requires these two secrets to exist (they
    # sign verification/reset tokens even though those routers are never
    # wired up in api/main.py).
    reset_password_token_secret = AUTH_SECRET
    verification_token_secret = AUTH_SECRET

    async def validate_password(self, password: str, user: Union[UserCreate, User]) -> None:
        """ROTA-CLOUD-REVIEW-FIXES F7/O3: the one length rule for every NEW
        password -- the library calls this hook from create() and update(),
        so self-service change, operator provisioning and operator reset all
        share it. Login never calls it: an older shorter password still logs in."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(reason=PASSWORD_TOO_SHORT_MESSAGE)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)
