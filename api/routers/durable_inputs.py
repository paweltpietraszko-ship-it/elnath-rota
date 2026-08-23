"""Wraps rota.application.durable_inputs (brief.md section 3.2: one router
module per rota/application/*.py module it wraps). Marshalling only --
fill_missing_calendar_days composes the two already-contracted primitives
(list_calendar_days + set_calendar_day) itself, in the application layer;
this router never owns that composition.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.durable_inputs import fill_missing_calendar_days, set_calendar_day
from rota.domain import CalendarDay

router = APIRouter(prefix="/workspace/calendar", tags=["calendar"])


class SetDayRequest(BaseModel):
    date: str
    holiday: bool
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope


class BulkGenerateRequest(BaseModel):
    start: str
    end: str
    site_id: str


@router.post("/day", status_code=204)
def set_day(payload: SetDayRequest, conn=Depends(get_conn)) -> None:
    try:
        day_date = date.fromisoformat(payload.date)
        set_calendar_day(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id,
            day=CalendarDay(day_date, payload.holiday),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/bulk-generate", status_code=204)
def bulk_generate(payload: BulkGenerateRequest, conn=Depends(get_conn)) -> None:
    """Creates only the missing rows in [start, end]; an existing row
    (holiday=True or False) is skipped, never overwritten -- the
    coordinator's own toggles are never silently reverted by a later
    bulk-generate call."""
    try:
        start, end = date.fromisoformat(payload.start), date.fromisoformat(payload.end)
        fill_missing_calendar_days(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id,
            range_start=start, range_end=end,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
