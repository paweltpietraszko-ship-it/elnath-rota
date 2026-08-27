"""Read-only wrap for ROTA-T021 §Przeglad (arch/T021_spec.md). Per spec,
"no dedicated backend module exists for this screen" -- it is explicitly a
composition of reads already covered under other screens' sections
(decisions, schedule version, roster). This router composes them, exactly
as api/routers/bootstrap.py's _site_summary already composes 3 different
reads into one -- no new persistence/application function.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.domain import MembershipKind
from rota.persistence import site_memory
from rota.persistence.employee_repository import list_memberships_for_site, list_windows_for_site
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_version_header

router = APIRouter(prefix="/workspace", tags=["overview"])


class OverviewOut(BaseModel):
    month: str
    decision_months: list[str]
    version_id: str | None
    version_status: Optional[Literal["WORKING", "WORKING_WITH_DEVIATIONS", "FINAL_NO_DEVIATIONS", "FINAL_WITH_DEVIATIONS"]]
    resumable: bool
    headcount: int


@router.get("/sites/{site_id}/overview", response_model=OverviewOut)
def get_overview(site_id: str, month: date, conn=Depends(get_conn)) -> OverviewOut:
    try:
        decision_months = site_memory.current_decision_required_months_for_site(conn, site_id=site_id)
        version_id = get_current_version_id(conn, site_id, month)
        version_status = None
        resumable = False
        if version_id is not None:
            header = get_schedule_version_header(conn, version_id)
            version_status = header.status.value
            resumable = version_status in ("WORKING", "WORKING_WITH_DEVIATIONS")
        # OWNER_CORRECTED (2026-08-27, UI audit gate): spec's "LOCAL +
        # EXTERNAL_SUPPORT (if support is in use that month)" means an
        # EXTERNAL_SUPPORT membership counts only when it has an active
        # ExternalSupportWindow overlapping the queried month -- not every
        # enabled EXTERNAL_SUPPORT row regardless of window.
        days_in_month = calendar.monthrange(month.year, month.month)[1]
        month_start = datetime(month.year, month.month, 1)
        month_end = datetime(month.year, month.month, days_in_month, 23, 59, 59)
        windows = list_windows_for_site(conn, site_id)
        supported_employee_ids = {
            w.employee_id for w in windows
            if w.active and w.start_datetime <= month_end and w.end_datetime >= month_start
        }
        memberships = list_memberships_for_site(conn, site_id)
        headcount = sum(
            1 for m in memberships
            if m.enabled and (
                m.membership_kind == MembershipKind.LOCAL
                or (m.membership_kind == MembershipKind.EXTERNAL_SUPPORT and m.employee_id in supported_employee_ids)
            )
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return OverviewOut(
        month=month.isoformat(), decision_months=[m.isoformat() for m in decision_months],
        version_id=version_id, version_status=version_status, resumable=resumable, headcount=headcount,
    )


if __name__ == "__main__":
    print("api.routers.overview module OK")
