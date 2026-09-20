"""ROTA-EXCEL-UI-PANEL: lets a logged-in coordinator download the Excel
template/add-in and read the install guide themselves from the "Excel"
panel, instead of an operator emailing the files from `excel/` by hand
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
from pydantic import BaseModel

from api.auth.backend import current_active_user

router = APIRouter(prefix="/excel", tags=["excel"])

_EXCEL_DIR = Path(__file__).resolve().parent.parent.parent / "excel"
_TEMPLATE_PATH = _EXCEL_DIR / "ELNATH_ROTA_TEMPLATE.xlsx"
_ADDIN_PATH = _EXCEL_DIR / "ELNATH_ROTA_ADDIN.xlam"
_INSTALL_GUIDE_PATH = _EXCEL_DIR / "INSTALL.md"


class InstallGuideOut(BaseModel):
    markdown: str


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


@router.get("/install-guide", dependencies=[Depends(current_active_user)])
def get_install_guide() -> InstallGuideOut:
    # Owner instruction (2026-09-20): the panel must show INSTALL.md in a
    # form the coordinator can actually read, not just offer it as a raw
    # file download. Returned as text, not FileResponse -- the frontend
    # renders it (InstallGuideModal), it never triggers a browser download.
    if not _INSTALL_GUIDE_PATH.is_file():
        raise HTTPException(status_code=404, detail="Instrukcja instalacji nie jest dostępna na tym serwerze.")
    return InstallGuideOut(markdown=_INSTALL_GUIDE_PATH.read_text(encoding="utf-8"))
