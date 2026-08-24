"""Wraps rota.application.backup. Destination paths are resolved
server-side (a temp file); the frontend only ever triggers a download,
never chooses a filesystem path itself (brief.md section 4 Writes).
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.deps import get_conn
from rota.application.backup import backup_database, build_diagnostic_zip

router = APIRouter(prefix="/workspace", tags=["backup"])


class DiagnosticsRequest(BaseModel):
    # ROTA-T021c: opaque frontend diagnostic report (see
    # frontend/src/diagnostics/types.ts). The backend never inspects or
    # validates its shape -- it is embedded into the ZIP as-is.
    frontend_report: dict | None = None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@router.post("/backup")
def download_backup(background_tasks: BackgroundTasks, conn=Depends(get_conn)) -> FileResponse:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    backup_database(conn, path)
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-backup-{_timestamp()}.db", media_type="application/octet-stream")


@router.post("/diagnostics")
def download_diagnostics(
    background_tasks: BackgroundTasks,
    payload: DiagnosticsRequest | None = None,
    conn=Depends(get_conn),
) -> FileResponse:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    frontend_report = payload.frontend_report if payload is not None else None
    build_diagnostic_zip(conn, path, frontend_report=frontend_report)
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-diagnostics-{_timestamp()}.zip", media_type="application/zip")
