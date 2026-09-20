"""ROTA-T021 brief.md section 3.2: thin FastAPI pass-through in front of
rota/application/*.py. LOCAL_WINDOWS deployment must not be exposed on any
network the coordinator's own machine doesn't already trust; a
CENTRAL_SERVICE deployment (Railway) is real-auth-gated (T024) and is the
only mode meant to be reachable over the open internet.

ROTA-RAILWAY-DEPLOY: ROTA_ALLOWED_ORIGINS lets a CENTRAL_SERVICE deployment
allow its own real origin (e.g. https://elnath-rota.up.railway.app)
instead of the hardcoded Vite dev-server origin -- comma-separated, no
default beyond the dev origin so a misconfigured deployment fails closed
(CORS rejects) rather than silently open.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from api.config import IS_CENTRAL_SERVICE
from api.errors import to_http_exception
from api.routers import (
    analytics, backup, bootstrap, calendar, decisions, durable_inputs, export, history, manual_edit, overview,
    roster, rule_decisions, schedule, site_profile,
)

app = FastAPI(title="Rota API (dev)")

_dev_origin = "http://localhost:5173"
_extra_origins = [o.strip() for o in os.environ.get("ROTA_ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_dev_origin, *_extra_origins],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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
    from api.routers import excel_downloads, excel_external

    app.include_router(excel_external.router, prefix="/api")
    app.include_router(excel_downloads.router, prefix="/api")

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


class _FrontendStaticFiles(StaticFiles):
    """ROTA-RAILWAY-DEPLOY cache fix (2026-09-20, found live: a redeploy was
    invisible on an already-open phone tab). Vite's own JS/CSS filenames are
    content-hashed (frontend/dist/assets/*) -- safe to cache forever, a
    changed file always gets a new name. index.html is NOT hashed and had
    no explicit Cache-Control at all, so a browser's own heuristic caching
    could keep serving a stale index.html (and therefore the OLD, no-longer-
    served asset filenames it references) indefinitely across deploys.
    file_response is the one method every StaticFiles.get_response code
    path (a real file, the html=True directory-index fallback, and the
    404.html fallback) already funnels through -- see Starlette's own
    source, never reimplemented here."""

    def file_response(self, full_path, stat_result, scope: Scope, status_code: int = 200):
        response = super().file_response(full_path, stat_result, scope, status_code=status_code)
        if f"{os.sep}assets{os.sep}" in str(full_path):
            response.headers["cache-control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["cache-control"] = "no-cache"
        return response


# ROTA-RAILWAY-DEPLOY: a single container serves both the API and the built
# frontend (`vite build` output) so Railway only needs one service and the
# browser never makes a cross-origin request in production. Mounted last so
# it never shadows an /api/* route above. Absent in local dev (no build
# artifact on disk) -- `npm run dev`'s own Vite server serves the frontend
# there instead, proxying /api to this backend (frontend/vite.config.ts).
_frontend_dist = Path(os.environ.get("ROTA_FRONTEND_DIST", "frontend/dist"))
if _frontend_dist.is_dir():
    app.mount("/", _FrontendStaticFiles(directory=_frontend_dist, html=True), name="frontend")
