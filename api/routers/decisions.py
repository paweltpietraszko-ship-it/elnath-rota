"""Read-only wrap for ROTA-T021 §Decyzje koordynatora (arch/T021_spec.md).
No dedicated memory_read.py wrapper exists yet for
current_decision_required_months_for_site (spec-flagged gap) -- calling
rota.persistence.site_memory directly here follows the same
already-accepted pattern api/routers/bootstrap.py uses for the identical
call. The per-month payload reuses rota.application.memory_read.
current_decision_required unchanged (same source MonthViewOut.decision_required
already surfaces on Planowanie miesiąca)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.decision_payload import BlockerOut, BlockingDemandOut, LoadBlockerOut, UnblockingOptionOut, decision_payload_out
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.memory_read import current_decision_required
from rota.persistence import site_memory

router = APIRouter(prefix="/workspace", tags=["decisions"])


class DecisionMonthsOut(BaseModel):
    months: list[str]


class DecisionRequiredOut(BaseModel):
    decision_required_id: str
    site_id: str
    month: str
    schedule_version_id: str | None
    requested_by: str
    recorded_at: str
    blocking_shift_demands: list[BlockingDemandOut]
    blockers: list[BlockerOut]
    load_blocker: LoadBlockerOut | None
    unblocking_options: list[UnblockingOptionOut]
    linked_action_ids: list[str]


@router.get("/sites/{site_id}/decisions/months", response_model=DecisionMonthsOut)
def get_decision_months(site_id: str, conn=Depends(get_conn)) -> DecisionMonthsOut:
    months = site_memory.current_decision_required_months_for_site(conn, site_id=site_id)
    return DecisionMonthsOut(months=[m.isoformat() for m in months])


@router.get("/sites/{site_id}/decisions/{month}", response_model=DecisionRequiredOut | None)
def get_decision_for_month(site_id: str, month: date, conn=Depends(get_conn)) -> DecisionRequiredOut | None:
    try:
        readback = current_decision_required(conn, site_id=site_id, month=month)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    if readback is None:
        return None
    fields = decision_payload_out(readback.payload)
    return DecisionRequiredOut(
        decision_required_id=readback.decision_required_id, site_id=readback.site_id, month=readback.month.isoformat(),
        schedule_version_id=readback.schedule_version_id, requested_by=readback.requested_by,
        recorded_at=readback.recorded_at.isoformat(),
        **fields.model_dump(),
        linked_action_ids=list(readback.linked_action_ids),
    )


if __name__ == "__main__":
    print("api.routers.decisions module OK")
