"""Shared exception -> HTTP status mapping (brief.md section 3.2: one
shared helper, never per-router ad-hoc handling).
"""
from __future__ import annotations

from fastapi import HTTPException

from rota.application.errors import (
    CandidateRejected,
    CoordinatorContextAlreadyActive,
    InvalidCoordinatorContext,
    NoCurrentScheduleVersion,
    ScheduleVersionNotWorking,
)
from rota.persistence.employee_repository import EmployeeNotFound
from rota.persistence.site_profile_repository import SiteProfileNotFound
from rota.persistence.site_repository import (
    InvalidSitePrintSettings,
    SiteNotFound,
    SiteRegimeChangeRejected,
    UnknownSiteProfile,
)
from rota.planning.shift_catalog import InvalidStandardShift

_STATUS_BY_EXCEPTION: tuple[tuple[type[Exception], int], ...] = (
    (SiteNotFound, 404),
    (UnknownSiteProfile, 404),
    (SiteProfileNotFound, 404),
    (EmployeeNotFound, 404),
    (NoCurrentScheduleVersion, 404),
    (InvalidCoordinatorContext, 403),
    (CoordinatorContextAlreadyActive, 409),
    (SiteRegimeChangeRejected, 409),
    (ScheduleVersionNotWorking, 409),
    (InvalidSitePrintSettings, 422),
    (InvalidStandardShift, 400),
    (CandidateRejected, 400),
    (ValueError, 400),
)


def to_http_exception(exc: Exception) -> HTTPException:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return HTTPException(status_code=status_code, detail=str(exc))
    return HTTPException(status_code=500, detail=f"unexpected error: {exc}")
