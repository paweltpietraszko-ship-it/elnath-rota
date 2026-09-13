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

from api.config import IS_CENTRAL_SERVICE
from api.deps import get_conn, get_db_path
from api.errors import to_http_exception
from api.runtime_log import RuntimeLogConfigurationError, resolve_log_dir
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
def download_backup(background_tasks: BackgroundTasks, conn=Depends(get_conn), db_path=Depends(get_db_path)) -> FileResponse:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    try:
        # ROTA-T024 brief.md section 8/T24-10: exactly this request's own
        # account database -- never the global DB_PATH constant (in
        # LOCAL_WINDOWS mode get_db_path() still resolves to it, so this
        # is a no-op there; in CENTRAL_SERVICE it is per-account).
        backup_database(conn, path, db_path=str(db_path))
    except Exception as exc:
        os.remove(path)
        raise to_http_exception(exc) from exc
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-backup-{_timestamp()}.zip", media_type="application/zip")


@router.post("/backup/recovery-key")
def download_recovery_key(background_tasks: BackgroundTasks, conn=Depends(get_conn), db_path=Depends(get_db_path)) -> FileResponse:
    """LOCAL_WINDOWS only (brief.md section 5.1/6): creates -- or
    re-creates -- the recovery kit for this installation's database and
    returns the raw recovery key as a small text file. The coordinator/
    installation owner must store this file somewhere OTHER than this
    computer; it is never written to disk by the backend itself.
    CENTRAL_SERVICE installations reuse their own deployment KEK for
    recovery instead and have no separate key to download here -- calling
    this there already fails closed (protector_kind_for returns "CENTRAL",
    not "DPAPI", so create_local_recovery_kit raises)."""
    try:
        recovery_key = create_local_recovery_kit(conn, db_path=str(db_path))
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
    runtime_log_dir = None
    if not IS_CENTRAL_SERVICE:
        # ROTA-T024 brief.md section 9/T24-12: the shared runtime-errors.log
        # can contain events from OTHER accounts in a hosted CENTRAL_SERVICE
        # deployment -- the user-facing diagnostic ZIP must never include it
        # there (operator/CC access to that log stays a deployment-side
        # concern, outside this endpoint). LOCAL_WINDOWS is single-user, so
        # its existing T021c/technical-error contract is unchanged.
        try:
            runtime_log_dir = resolve_log_dir()
        except RuntimeLogConfigurationError:
            # ROTA-TECHNICAL-ERROR-RECOVERY-UX brief.md section 5: a
            # misconfigured/absent log location must never break the
            # diagnostic ZIP itself -- it is produced without the runtime log.
            runtime_log_dir = None
    build_diagnostic_zip(conn, path, frontend_report=frontend_report, runtime_log_dir=runtime_log_dir)
    background_tasks.add_task(os.remove, path)
    return FileResponse(path, filename=f"rota-diagnostics-{_timestamp()}.zip", media_type="application/zip")
