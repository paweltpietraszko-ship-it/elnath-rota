"""ROTA-EXCEL-UI-PANEL: lets a logged-in coordinator download the Excel
template/add-in themselves from the "Excel" panel, instead of an
operator emailing the files from `excel/` by hand
(ROTA-EXCEL-VBA-ENGINE-ADAPTER's original distribution path). Cookie-
authenticated (current_active_user) -- these are the same static files
for every account, not per-account data, so no AuthenticatedContext/
domain database is involved. Mounted only for IS_CENTRAL_SERVICE
(api/main.py), matching excel_external.py and the panel's own gating.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.auth.backend import current_active_user

router = APIRouter(prefix="/excel", tags=["excel"])

_EXCEL_DIR = Path(__file__).resolve().parent.parent.parent / "excel"
_TEMPLATE_PATH = _EXCEL_DIR / "ELNATH_ROTA_TEMPLATE.xlsx"
_ADDIN_PATH = _EXCEL_DIR / "ELNATH_ROTA_ADDIN.xlam"


def _download(path: Path, filename: str, media_type: str) -> FileResponse:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{filename} nie jest dostępny na tym serwerze.")
    return FileResponse(path, filename=filename, media_type=media_type)


@router.post("/template", dependencies=[Depends(current_active_user)])
def download_template() -> FileResponse:
    return _download(
        _TEMPLATE_PATH, "ELNATH_ROTA_TEMPLATE.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/addin", dependencies=[Depends(current_active_user)])
def download_addin() -> FileResponse:
    return _download(_ADDIN_PATH, "ELNATH_ROTA_ADDIN.xlam", "application/vnd.ms-excel.addin.macroEnabled.12")
