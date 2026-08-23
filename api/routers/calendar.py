"""Read-only wrap of calendar_repository.list_calendar_days -- a
persistence-layer call with no owning application module (brief.md
section 4: "persistence-layer, no application wrapper exists for reads --
call directly"). Writes live in api/routers/durable_inputs.py, matching
the module they wrap (brief.md section 3.2: one router module per
rota/application/*.py module it wraps).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.persistence.calendar_repository import list_calendar_days

router = APIRouter(prefix="/workspace/calendar", tags=["calendar"])


class CalendarDayOut(BaseModel):
    date: str
    holiday: bool


@router.get("", response_model=list[CalendarDayOut])
def get_range(start: str, end: str, conn=Depends(get_conn)) -> list[CalendarDayOut]:
    """Only persisted rows -- an absent date is NOT returned as
    holiday=False. The frontend must render the gap, never assume it."""
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise to_http_exception(exc) from exc
    days = list_calendar_days(conn, start_date, end_date)
    return [CalendarDayOut(date=d.date.isoformat(), holiday=d.holiday) for d in days]
