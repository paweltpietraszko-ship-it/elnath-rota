"""Read-only wrap for ROTA-T021 §Przeglad (arch/T021_spec.md). Per spec,
"no dedicated backend module exists for this screen" -- it is explicitly a
composition of reads already covered under other screens' sections
(decisions, schedule version, roster). This router composes them, exactly
as api/routers/bootstrap.py's _site_summary already composes 3 different
reads into one -- no new persistence/application function.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.domain import MembershipKind
from rota.persistence import site_memory
from rota.persistence.employee_repository import list_memberships_for_site
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_version_header

router = APIRouter(prefix="/workspace", tags=["overview"])


class OverviewOut(BaseModel):
    month: str
    decision_months: list[str]
    version_id: str | None
    version_status: str | None
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
        # Simplification, flagged not a precise spec algorithm: counts every
        # enabled LOCAL + EXTERNAL_SUPPORT membership, not narrowed to an
        # EXTERNAL_SUPPORT window active specifically in `month` -- "current
        # crew size" for a quick glance tile, not a billing-grade figure.
        headcount = sum(
            1 for m in list_memberships_for_site(conn, site_id)
            if m.enabled and m.membership_kind in (MembershipKind.LOCAL, MembershipKind.EXTERNAL_SUPPORT)
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return OverviewOut(
        month=month.isoformat(), decision_months=[m.isoformat() for m in decision_months],
        version_id=version_id, version_status=version_status, resumable=resumable, headcount=headcount,
    )


if __name__ == "__main__":
    print("api.routers.overview module OK")
