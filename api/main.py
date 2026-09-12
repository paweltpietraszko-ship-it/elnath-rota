"""ROTA-T021 brief.md section 3.2: thin FastAPI pass-through in front of
rota/application/*.py. Dev-local only until real authentication (T025 F1)
exists -- must not be exposed on any network the coordinator's own
machine doesn't already trust.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
