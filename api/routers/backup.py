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

from api.config import DB_PATH
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.backup import backup_database, build_diagnostic_zip, create_local_recovery_kit

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
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    try:
        backup_database(conn, path, db_path=DB_PATH)
    except Exception as exc:
        os.remove(path)
        raise to_http_exception(exc) from exc
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-backup-{_timestamp()}.zip", media_type="application/zip")


@router.post("/backup/recovery-key")
def download_recovery_key(background_tasks: BackgroundTasks, conn=Depends(get_conn)) -> FileResponse:
    """LOCAL_WINDOWS only (brief.md section 5.1/6): creates -- or
    re-creates -- the recovery kit for this installation's database and
    returns the raw recovery key as a small text file. The coordinator/
    installation owner must store this file somewhere OTHER than this
    computer; it is never written to disk by the backend itself.
    CENTRAL_SERVICE installations reuse their own deployment KEK for
    recovery instead and have no separate key to download here."""
    try:
        recovery_key = create_local_recovery_kit(conn, db_path=DB_PATH)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    with open(path, "w", encoding="ascii") as f:
        f.write(recovery_key.hex())
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-recovery-key-{_timestamp()}.txt", media_type="text/plain")


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
