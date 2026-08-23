"""Wraps rota.application.rule_decisions (brief.md section 3.2: one
router module per rota/application/*.py module it wraps). Marshalling
only -- rule_id continuity, statement text and shape validation are all
owned by T021b's application-layer functions (tasks/ROTA-T021b/brief.md);
this router never constructs SiteRuleVersion/NewRuleContent itself.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.rule_decisions import (
    create_day_only_n_exception,
    create_employee_shift_unavailability,
    create_employee_weekday_unavailability,
    end_employee_matrix_rule_early,
    update_employee_matrix_rule_period,
)
from rota.domain import ShiftKind

router = APIRouter(prefix="/workspace/employees", tags=["matrix"])


class CreateShiftUnavailabilityRequest(BaseModel):
    site_id: str
    shift_kind: str  # "D" | "N"
    effective_from: str
    effective_to: str


@router.post("/{employee_id}/matrix/shift-unavailability", status_code=204)
def create_shift_unavailability(employee_id: str, payload: CreateShiftUnavailabilityRequest, conn=Depends(get_conn)) -> None:
    try:
        create_employee_shift_unavailability(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id, employee_id=employee_id,
            shift_kind=ShiftKind(payload.shift_kind),
            effective_from=date.fromisoformat(payload.effective_from), effective_to=date.fromisoformat(payload.effective_to),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class CreateWeekdayUnavailabilityRequest(BaseModel):
    site_id: str
    iso_weekday: int
    effective_from: str
    effective_to: str


@router.post("/{employee_id}/matrix/weekday-unavailability", status_code=204)
def create_weekday_unavailability(employee_id: str, payload: CreateWeekdayUnavailabilityRequest, conn=Depends(get_conn)) -> None:
    try:
        create_employee_weekday_unavailability(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id, employee_id=employee_id,
            iso_weekday=payload.iso_weekday,
            effective_from=date.fromisoformat(payload.effective_from), effective_to=date.fromisoformat(payload.effective_to),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class CreateDayOnlyExceptionRequest(BaseModel):
    site_id: str
    effective_from: str
    effective_to: str


@router.post("/{employee_id}/matrix/day-only-exception", status_code=204)
def create_day_only_exception(employee_id: str, payload: CreateDayOnlyExceptionRequest, conn=Depends(get_conn)) -> None:
    try:
        create_day_only_n_exception(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id, employee_id=employee_id,
            effective_from=date.fromisoformat(payload.effective_from), effective_to=date.fromisoformat(payload.effective_to),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class UpdateMatrixRuleRequest(BaseModel):
    site_id: str
    effective_from: str
    effective_to: str


@router.patch("/{employee_id}/matrix/{rule_id}", status_code=204)
def update_matrix_rule(employee_id: str, rule_id: str, payload: UpdateMatrixRuleRequest, conn=Depends(get_conn)) -> None:
    try:
        update_employee_matrix_rule_period(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id, rule_id=rule_id,
            effective_from=date.fromisoformat(payload.effective_from), effective_to=date.fromisoformat(payload.effective_to),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class EndMatrixRuleRequest(BaseModel):
    site_id: str
    effective_from: str


@router.post("/{employee_id}/matrix/{rule_id}/end-early", status_code=204)
def end_matrix_rule_early(employee_id: str, rule_id: str, payload: EndMatrixRuleRequest, conn=Depends(get_conn)) -> None:
    try:
        end_employee_matrix_rule_early(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=payload.site_id, rule_id=rule_id,
            effective_from=date.fromisoformat(payload.effective_from),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
