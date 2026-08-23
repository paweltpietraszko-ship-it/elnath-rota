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

from api.deps import get_conn
from rota.application.backup import backup_database, build_diagnostic_zip

router = APIRouter(prefix="/workspace", tags=["backup"])


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
def download_diagnostics(background_tasks: BackgroundTasks, conn=Depends(get_conn)) -> FileResponse:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    build_diagnostic_zip(conn, path)
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-diagnostics-{_timestamp()}.zip", media_type="application/zip")
