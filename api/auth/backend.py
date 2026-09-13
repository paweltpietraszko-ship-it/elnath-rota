"""ROTA-T024 brief.md section 3: cookie transport (HttpOnly, Secure under
hosted HTTPS, SameSite=Lax) + JWT session strategy, both entirely
library-owned. Exposes `fastapi_users`, `current_active_user`, and
`auth_router` (login/logout only -- brief section 3's reduction gate:
never mount get_users_router, which also exposes email-change and
admin GET/PATCH/DELETE /{user_id}).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from api.auth.manager import UserManager, get_user_manager
from api.auth.models import User
from api.auth.schemas import PasswordChangeRequest, UserRead, UserUpdate
from api.config import AUTH_SECRET

COOKIE_MAX_AGE_SECONDS = 60 * 60 * 8  # 8h session -- ordinary workday length, no "remember me"

cookie_transport = CookieTransport(
    cookie_max_age=COOKIE_MAX_AGE_SECONDS,
    cookie_secure=True,
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=AUTH_SECRET, lifetime_seconds=COOKIE_MAX_AGE_SECONDS)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# brief section 3: "chronione endpointy korzystają z jednego library-backed
# current_user/dependency zamiast własnej weryfikacji tokenu".
current_active_user = fastapi_users.current_user(active=True)

# Login + logout only -- the library's own get_auth_router, no
# registration/reset-password/verify router mounted anywhere (brief
# section 3/section 12 A15).
auth_router: APIRouter = fastapi_users.get_auth_router(auth_backend)


# brief section 3's reduction gate (Codex R3 precheck): a thin, Rota-owned
# GET current-user + PATCH password endpoint, never fastapi_users'
# get_users_router (which also exposes email change and admin
# GET/PATCH/DELETE /{user_id} -- wider surface than this Task accepts).
me_router = APIRouter(prefix="/auth", tags=["auth"])


@me_router.get("/me", response_model=UserRead)
async def read_current_user(user: User = Depends(current_active_user)) -> User:
    return user


@me_router.patch("/me/password", response_model=UserRead)
async def change_own_password(
    payload: PasswordChangeRequest,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
) -> User:
    # R4-02 fix: the public payload model (PasswordChangeRequest,
    # extra="forbid") is password-only and rejects any other field outright --
    # `UserUpdate`'s safe=True does NOT block email, so accepting it
    # directly let a password-only endpoint silently change the login
    # email. The actual hash/update still delegates entirely to the
    # library's own UserManager -- no Rota-side password logic.
    return await user_manager.update(UserUpdate(password=payload.password), user, safe=True)
