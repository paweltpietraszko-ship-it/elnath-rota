"""ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md section 4/13): manual account
provisioning + manual password reset for the operator (Paweł). No public
registration/reset-mail flow exists anywhere -- this CLI is the only way
a CENTRAL_SERVICE account is ever created or its password reset, and it
uses the exact same library-owned UserManager.create/update path a
logged-in user's own password-change endpoint uses (api/auth/backend.py).

Usage (from repo root, CENTRAL_SERVICE env already set):
    python -m api.provision_account create <email> <password> <coordinator_id> <db_filename>
    python -m api.provision_account reset-password <email> <new_password>
"""
from __future__ import annotations

import asyncio
import sys

from fastapi_users.exceptions import UserAlreadyExists, UserNotExists
from sqlalchemy import select

from api.auth.db import AccountMapping, create_auth_db_and_tables, get_user_db, session_maker
from api.auth.manager import UserManager
from api.auth.schemas import UserCreate, UserUpdate
from api.config import ACCOUNTS_DB_DIR, IS_CENTRAL_SERVICE


class DbFilenameAlreadyInUse(Exception):
    """R4-01: db_filename is the owning boundary between accounts -- two
    accounts must never be able to read/write the same domain database."""


async def _user_manager(session):
    async for user_db in get_user_db(session):
        return UserManager(user_db)
    raise RuntimeError("get_user_db yielded nothing")  # pragma: no cover -- generator always yields once


async def create_account(email: str, password: str, coordinator_id: str, db_filename: str) -> None:
    await create_auth_db_and_tables()
    ACCOUNTS_DB_DIR.mkdir(parents=True, exist_ok=True)
    async with session_maker()() as session:
        existing = await session.scalar(
            select(AccountMapping).where(AccountMapping.db_filename == db_filename)
        )
        if existing is not None:
            raise DbFilenameAlreadyInUse(
                f"db_filename {db_filename!r} is already assigned to another account"
            )
        manager = await _user_manager(session)
        try:
            user = await manager.create(UserCreate(email=email, password=password), safe=False)
        except UserAlreadyExists:
            print(f"account {email!r} already exists")
            return
        session.add(AccountMapping(auth_user_id=user.id, coordinator_id=coordinator_id, db_filename=db_filename))
        await session.commit()
    print(f"created account {email!r} -> coordinator_id={coordinator_id!r} db_filename={db_filename!r}")


async def reset_password(email: str, new_password: str) -> None:
    async with session_maker()() as session:
        manager = await _user_manager(session)
        try:
            user = await manager.get_by_email(email)
        except UserNotExists:
            print(f"no account {email!r}")
            return
        # brief.md T24-9: same library-supported password helper the
        # user's own change-password endpoint uses -- never a second,
        # Rota-written hashing path.
        await manager.update(UserUpdate(password=new_password), user, safe=False)
    print(f"password reset for {email!r}")


def main() -> None:
    if not IS_CENTRAL_SERVICE:
        print("ROTA_CENTRAL_KEK is not set -- this CLI only applies to a CENTRAL_SERVICE deployment.")
        sys.exit(1)
    args = sys.argv[1:]
    if len(args) == 5 and args[0] == "create":
        asyncio.run(create_account(args[1], args[2], args[3], args[4]))
    elif len(args) == 3 and args[0] == "reset-password":
        asyncio.run(reset_password(args[1], args[2]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
