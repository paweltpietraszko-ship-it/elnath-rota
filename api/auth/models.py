"""ROTA-T024 brief.md section 5: two separate responsibilities in one small
technical SQLite -- fastapi-users' own User table (credentials, hashing,
active flag, all owned by the library) and Rota's own AccountMapping table
(auth_user_id -> coordinator_id + db_filename). Never mixed with a
tester's own domain database.
"""
from __future__ import annotations

import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Boolean, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Credentials, password hash, and active flag are entirely
    library-owned fields (SQLAlchemyBaseUserTableUUID) -- Rota adds no
    columns here, per brief.md section 3 ("hashowanie... należą do
    biblioteki, nie do kodu Rota")."""


class AccountMapping(Base):
    """brief.md section 5: 'db_filename -- tylko nazwa pliku w zaufanym
    katalogu, nie dowolna ścieżka' -- resolved against api.config.
    ACCOUNTS_DB_DIR by the caller, never stored/accepted as a full path.
    Never returned to the frontend or included in a diagnostic ZIP."""

    __tablename__ = "account_mapping"

    auth_user_id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True)
    coordinator_id: Mapped[str] = mapped_column(String, nullable=False)
    db_filename: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
