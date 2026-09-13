"""Wraps rota.application.durable_inputs.update_site_profile /
rota.persistence.site_profile_repository.get_site_profile for the Panel
sterowania -> Obiekt shift catalog (tasks/ROTA-T030/brief.md). Marshalling
plus StandardShift row construction only -- no new persistence, versioning,
or repository layer; every write still goes through the one existing
update_site_profile() atomic full-profile write.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from api.deps import get_conn, get_coordinator_id
from api.errors import to_http_exception
from rota.application.durable_inputs import update_site_profile
from rota.domain import EmployeeRole, ShiftKind, StandardShift
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site
from rota.planning.shift_catalog import normalized_catalog_kind, shift_duration_hours, validate_standard_shift

router = APIRouter(prefix="/workspace/sites", tags=["site-profile"])


class ShiftRowOut(BaseModel):
    kind: str
    start_time: str
    end_time: str
    required_primary_count: int
    active_weekdays: list[int]
    duration_hours: float
    catalog_kind: str
    # ROTA-T065 brief.md section 6/13: None for OCHRONA/legacy shifts, which
    # never had a role concept. UI does not need a shift "code" -- this is
    # the only new business-meaning field ORDINARY's catalog carries.
    required_role: str | None = None


class ShiftCatalogOut(BaseModel):
    shifts: list[ShiftRowOut]


def _fmt_time(t: time) -> str:
    return t.strftime("%H:%M")


def _shift_out(shift: StandardShift) -> ShiftRowOut:
    return ShiftRowOut(
        kind=shift.kind.value,
        start_time=_fmt_time(shift.start_time),
        end_time=_fmt_time(shift.end_time),
        required_primary_count=shift.required_primary_count,
        active_weekdays=list(shift.active_weekdays),
        duration_hours=shift_duration_hours(shift),
        catalog_kind=normalized_catalog_kind(shift).value,
        required_role=shift.required_role.value if shift.required_role else None,
    )


@router.get("/{site_id}/shift-catalog", response_model=ShiftCatalogOut)
def get_shift_catalog(site_id: str, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> ShiftCatalogOut:
    try:
        site = get_site(conn, site_id)
        profile = get_site_profile(conn, site.profile_id)
        return ShiftCatalogOut(shifts=[_shift_out(s) for s in profile.standard_shifts])
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ShiftRowIn(BaseModel):
    # brief.md section 4: a PUT row accepts exactly these five input
    # fields -- never required_rest_hours/end_next_day/catalog_kind,
    # never a hidden profile field. Extra fields are a hard rejection,
    # not a silent ignore.
    # ROTA-T065 brief.md section 6/13: "UI nie wymaga biznesowego kodu
    # zmiany" -- kind is now optional (an ORDINARY-facing client never
    # sends it; _build_shift defaults to D, a purely internal technical
    # value carrying no OCHRONA legal meaning, see eligibility.py's D/N
    # gates, all of which are N-specific). OCHRONA's own client keeps
    # sending kind explicitly, unaffected. required_role is the one new
    # business field ORDINARY rows carry.
    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    start_time: str
    end_time: str
    required_primary_count: int
    active_weekdays: list[int]
    required_role: str | None = None


class ShiftCatalogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shifts: list[ShiftRowIn]
    # ROTA-T021 UI audit gate (round-16, OWNER_CORRECTED): "Zmień zapisaną
    # regułę" is a decision-response action per arch/T021_spec.md:595-596 --
    # update_site_profile already accepted this parameter, only this router
    # never exposed it (same gap already closed for the five employee
    # matrix endpoints in api/routers/rule_decisions.py).
    responds_to_decision_required_id: str | None = None


def _parse_full_hour(value: str) -> time:
    try:
        hour_str, minute_str = value.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid time format: {value!r}") from exc
    if minute != 0 or not (0 <= hour <= 23):
        raise ValueError(f"time must be a full hour 00:00-23:00, got {value!r}")
    return time(hour=hour, minute=0)


def _build_shift(row: ShiftRowIn) -> StandardShift:
    start = _parse_full_hour(row.start_time)
    end = _parse_full_hour(row.end_time)
    # brief.md section 3.5: end_time <= start_time means it spans into the
    # next day; equal times mean a full 24h shift, not a zero-length one.
    end_next_day = end <= start
    return StandardShift(
        kind=ShiftKind(row.kind) if row.kind is not None else ShiftKind.D,
        start_time=start,
        end_time=end,
        end_next_day=end_next_day,
        required_primary_count=row.required_primary_count,
        catalog_kind=None,
        required_rest_hours=11,
        active_weekdays=tuple(row.active_weekdays),
        required_role=EmployeeRole(row.required_role) if row.required_role else None,
    )


@router.put("/{site_id}/shift-catalog", status_code=204)
def put_shift_catalog(site_id: str, payload: ShiftCatalogIn, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        if not payload.shifts:
            raise ValueError("shift catalog must contain at least one shift")
        shifts = [_build_shift(row) for row in payload.shifts]
        for shift in shifts:
            validate_standard_shift(shift)
        site = get_site(conn, site_id)
        current_profile = get_site_profile(conn, site.profile_id)
        updated_profile = replace(current_profile, standard_shifts=shifts)
        update_site_profile(
            conn, coordinator_id=coordinator_id, site_id=site_id, profile=updated_profile,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
