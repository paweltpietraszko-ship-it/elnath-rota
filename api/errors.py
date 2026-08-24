"""Shared exception -> HTTP status mapping (brief.md section 3.2: one
shared helper, never per-router ad-hoc handling).
"""
from __future__ import annotations

from fastapi import HTTPException

from rota.application.errors import (
    CoordinatorContextAlreadyActive,
    InvalidCoordinatorContext,
)
from rota.persistence.employee_repository import EmployeeNotFound
from rota.persistence.site_repository import (
    InvalidSitePrintSettings,
    SiteNotFound,
    SiteRegimeChangeRejected,
    UnknownSiteProfile,
)

_STATUS_BY_EXCEPTION: tuple[tuple[type[Exception], int], ...] = (
    (SiteNotFound, 404),
    (UnknownSiteProfile, 404),
    (EmployeeNotFound, 404),
    (InvalidCoordinatorContext, 403),
    (CoordinatorContextAlreadyActive, 409),
    (SiteRegimeChangeRejected, 409),
    (InvalidSitePrintSettings, 422),
    (ValueError, 400),
)


def to_http_exception(exc: Exception) -> HTTPException:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return HTTPException(status_code=status_code, detail=str(exc))
    return HTTPException(status_code=500, detail=f"unexpected error: {exc}")
