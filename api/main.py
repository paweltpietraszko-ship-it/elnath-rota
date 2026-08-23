"""ROTA-T021 brief.md section 3.2: thin FastAPI pass-through in front of
rota/application/*.py. Dev-local only until real authentication (T025 F1)
exists -- must not be exposed on any network the coordinator's own
machine doesn't already trust.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import backup, bootstrap, calendar, durable_inputs

app = FastAPI(title="Rota API (dev)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server only
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bootstrap.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(durable_inputs.router, prefix="/api")
app.include_router(backup.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
