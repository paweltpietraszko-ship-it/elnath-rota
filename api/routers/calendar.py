"""Wraps calendar_repository (read, no application wrapper exists) and
durable_inputs.set_calendar_day (write). brief.md section 4
Calendar/holidays (round-2 A4): three states, bulk-generate only fills
missing rows with holiday=False and never overwrites an existing row.
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
from rota.persistence.calendar_repository import list_calendar_days

router = APIRouter(prefix="/workspace/calendar", tags=["calendar"])


class CalendarDayOut(BaseModel):
    date: str
    holiday: bool


class SetDayRequest(BaseModel):
    date: str
    holiday: bool
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope


class BulkGenerateRequest(BaseModel):
    start: str
    end: str
    site_id: str


@router.get("", response_model=list[CalendarDayOut])
def get_range(start: str, end: str, conn=Depends(get_conn)) -> list[CalendarDayOut]:
    """Only persisted rows -- an absent date is NOT returned as
    holiday=False. The frontend must render the gap, never assume it."""
    days = list_calendar_days(conn, date.fromisoformat(start), date.fromisoformat(end))
    return [CalendarDayOut(date=d.date.isoformat(), holiday=d.holiday) for d in days]


@router.post("/day", status_code=204)
def set_day(payload: SetDayRequest, conn=Depends(get_conn)) -> None:
    try:
        set_calendar_day(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id,
            day=CalendarDay(date.fromisoformat(payload.date), payload.holiday),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/bulk-generate", status_code=204)
def bulk_generate(payload: BulkGenerateRequest, conn=Depends(get_conn)) -> None:
    """Creates only the missing rows in [start, end] as holiday=False;
    an existing row (holiday=True or False) is skipped, never
    overwritten -- the coordinator's own toggles are never silently
    reverted by a later bulk-generate call."""
    start, end = date.fromisoformat(payload.start), date.fromisoformat(payload.end)
    existing = {d.date for d in list_calendar_days(conn, start, end)}
    current = start
    while current <= end:
        if current not in existing:
            try:
                set_calendar_day(
                    conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id,
                    day=CalendarDay(current, False),
                )
            except Exception as exc:
                raise to_http_exception(exc) from exc
        current = date.fromordinal(current.toordinal() + 1)
