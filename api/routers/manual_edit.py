"""ROTA-T037 (tasks/ROTA-T037/brief.md): thin FastAPI wrap of
rota/application/manual_edit.py for the "Reczna korekta" section embedded
in the Planowanie miesiaca screen. Marshalling and a short, non-blocking
HARD-violation warning only -- no new persistence/validation logic and no
dry-run/preview split. apply_manual_correction/freeze_or_unfreeze/
mark_not_worked already never block a save on a HARD violation (it becomes
a Deviation on the new child ScheduleVersion instead); this router just
surfaces that resulting Deviation list back to the caller.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from api.routers.schedule import AssignmentIn, DeviationOut, _assignment_from_in, _deviation_out
from rota.application.manual_edit import apply_manual_correction, freeze_or_unfreeze, mark_not_worked
from rota.persistence.schedule_repository import get_schedule_snapshot

router = APIRouter(prefix="/workspace/sites", tags=["manual-edit"])


class ManualCorrectionResultOut(BaseModel):
    version_id: str
    status: str
    deviations: list[DeviationOut]


def _result_out(conn, version) -> ManualCorrectionResultOut:
    # ScheduleVersion itself carries no deviations field -- they live on the
    # persisted snapshot (deviations table), same as MonthViewOut reads them.
    snapshot = get_schedule_snapshot(conn, version.version_id)
    return ManualCorrectionResultOut(
        version_id=version.version_id, status=version.status.value,
        deviations=[_deviation_out(d) for d in snapshot.deviations],
    )


class ManualCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: str
    upsert_assignments: list[AssignmentIn]
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post(
    "/{site_id}/schedule/{month}/manual-correction", response_model=ManualCorrectionResultOut,
)
def post_manual_correction(
    site_id: str, month: date, payload: ManualCorrectionRequest, conn=Depends(get_conn),
) -> ManualCorrectionResultOut:
    try:
        version = apply_manual_correction(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            effective_from=date.fromisoformat(payload.effective_from),
            upsert_assignments=[_assignment_from_in(a) for a in payload.upsert_assignments],
            note=payload.note, responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
        return _result_out(conn, version)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class FreezeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: str
    assignment_id: str
    frozen: bool
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post(
    "/{site_id}/schedule/{month}/manual-correction/freeze", response_model=ManualCorrectionResultOut,
)
def post_freeze_or_unfreeze(
    site_id: str, month: date, payload: FreezeRequest, conn=Depends(get_conn),
) -> ManualCorrectionResultOut:
    try:
        version = freeze_or_unfreeze(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            effective_from=date.fromisoformat(payload.effective_from), assignment_id=payload.assignment_id,
            frozen=payload.frozen, note=payload.note,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
        return _result_out(conn, version)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class MarkNotWorkedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: str
    assignment_id: str
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post(
    "/{site_id}/schedule/{month}/manual-correction/mark-not-worked", response_model=ManualCorrectionResultOut,
)
def post_mark_not_worked(
    site_id: str, month: date, payload: MarkNotWorkedRequest, conn=Depends(get_conn),
) -> ManualCorrectionResultOut:
    try:
        version = mark_not_worked(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            effective_from=date.fromisoformat(payload.effective_from), assignment_id=payload.assignment_id,
            note=payload.note, responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
        return _result_out(conn, version)
    except Exception as exc:
        raise to_http_exception(exc) from exc
