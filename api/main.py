"""ROTA-T021 brief.md section 3.2: thin FastAPI pass-through in front of
rota/application/*.py. Dev-local only until real authentication (T025 F1)
exists -- must not be exposed on any network the coordinator's own
machine doesn't already trust.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import IS_CENTRAL_SERVICE
from api.errors import to_http_exception
from api.routers import (
    analytics, backup, bootstrap, calendar, decisions, durable_inputs, export, history, manual_edit, overview,
    roster, rule_decisions, schedule, site_profile,
)

app = FastAPI(title="Rota API (dev)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server only
    allow_methods=["*"],
    allow_headers=["*"],
)

if IS_CENTRAL_SERVICE:
    # ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md section 3): login/logout
    # (library-owned) + the thin current-user/change-password endpoints
    # (brief's reduction gate -- never the library's full get_users_router,
    # which also exposes email-change and admin /{user_id} endpoints).
    # Mounted ONLY for CENTRAL_SERVICE -- LOCAL_WINDOWS has no login screen
    # and no auth surface at all (brief section 9/11).
    from api.auth.backend import auth_router, me_router
    from api.auth.db import create_auth_db_and_tables

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(me_router, prefix="/api")

    # ROTA-EXCEL-VBA-ENGINE-ADAPTER: the Excel add-in's external API key
    # resolves the same CENTRAL_SERVICE AccountMapping the cookie path
    # does -- mounted only here, same as auth_router/me_router above.
    from api.routers import excel_external

    app.include_router(excel_external.router, prefix="/api")

    @app.on_event("startup")
    async def _create_auth_tables() -> None:
        await create_auth_db_and_tables()

app.include_router(bootstrap.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(durable_inputs.calendar_router, prefix="/api")
app.include_router(durable_inputs.roster_router, prefix="/api")
app.include_router(roster.router, prefix="/api")
app.include_router(rule_decisions.router, prefix="/api")
app.include_router(backup.router, prefix="/api")
app.include_router(site_profile.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(overview.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(manual_edit.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md A1/TASK_SCOPE, Codex R3-02
    on 05f2e2a): a router's own `except Exception: raise to_http_exception(exc)`
    only ever catches exceptions inside its own body -- a dependency
    failure (get_conn), middleware, or response-validation error never
    reaches it and previously fell through to FastAPI's bare, unlogged
    500. Starlette dispatches by the most specific registered exception
    type, so an HTTPException (every router's own `to_http_exception`
    result) still goes to FastAPI's own default handler, never here --
    this only ever sees a genuinely unclassified exception, and
    `to_http_exception` logs it exactly once (its own fallback branch)."""
    http_exc = to_http_exception(exc)
    return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail}, headers=http_exc.headers)
