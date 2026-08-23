"""Wraps rota.application.durable_inputs (brief.md section 3.2: one router
module per rota/application/*.py module it wraps). Marshalling only.

Bulk-fill (brief.md section 4, round-2 audit A4) is NOT an API-layer or
application-layer operation: brief.md section 6 forbids this task from
modifying rota/**, so the missing-date loop is composed on the frontend
from the calendar read it already has, calling this single-day write once
per missing date.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.durable_inputs import set_calendar_day
from rota.domain import CalendarDay

router = APIRouter(prefix="/workspace/calendar", tags=["calendar"])


class SetDayRequest(BaseModel):
    date: str
    holiday: bool
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope


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
