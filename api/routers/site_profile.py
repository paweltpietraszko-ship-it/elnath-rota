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
from rota.application.durable_inputs import update_site, update_site_profile
from rota.domain import ShiftKind, SitePlanningRegime, StandardShift
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site
from rota.persistence.site_role_repository import list_site_roles
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
    # ROTA-T065-CONFIGURABLE-ROLES section 5: None for OCHRONA/legacy
    # shifts, which never had a role concept. Mandatory for every ORDINARY
    # row (enforced at PUT time by _validate_role_matches_regime) -- UI does
    # not need a shift "code", this is the only new business-meaning field
    # ORDINARY's catalog carries.
    required_role_id: str | None = None


class ShiftCatalogOut(BaseModel):
    shifts: list[ShiftRowOut]
    # ROTA-T065 audit R2-03 fix: the ONE place the frontend learns the
    # site's regime from this same existing call, instead of a second
    # endpoint or prop-threading through screens outside this Task's
    # literal TASK_SCOPE (brief.md section 19).
    planning_regime: str


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
        required_role_id=shift.required_role_id,
    )


@router.get("/{site_id}/shift-catalog", response_model=ShiftCatalogOut)
def get_shift_catalog(site_id: str, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> ShiftCatalogOut:
    try:
        site = get_site(conn, site_id)
        profile = get_site_profile(conn, site.profile_id)
        return ShiftCatalogOut(
            shifts=[_shift_out(s) for s in profile.standard_shifts],
            planning_regime=site.planning_regime.value,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ShiftRowIn(BaseModel):
    # brief.md section 4: a PUT row accepts exactly these five input
    # fields -- never required_rest_hours/end_next_day/catalog_kind,
    # never a hidden profile field. Extra fields are a hard rejection,
    # not a silent ignore.
    # ROTA-T065-CONFIGURABLE-ROLES section 5/9: "UI nie wymaga biznesowego
    # kodu zmiany" -- kind is now optional (an ORDINARY-facing client never
    # sends it; _build_shift defaults to D, a purely internal technical
    # value carrying no OCHRONA legal meaning, see eligibility.py's D/N
    # gates, all of which are N-specific). OCHRONA's own client keeps
    # sending kind explicitly, unaffected. required_role_id is the one new
    # business field ORDINARY rows carry -- mandatory for ORDINARY, forbidden
    # for OCHRONA (_validate_role_matches_regime).
    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    start_time: str
    end_time: str
    required_primary_count: int
    active_weekdays: list[int]
    required_role_id: str | None = None


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
        required_role_id=row.required_role_id,
    )


def _validate_role_matches_regime(conn, site_id: str, shifts: list[StandardShift], regime: SitePlanningRegime) -> None:
    """ROTA-T065-CONFIGURABLE-ROLES section 5/9: OCHRONA must never accept/
    persist a shop role (OCHRONA keeps its exact existing D/N behavior, no
    shop role field). ORDINARY now REQUIRES a role on every row -- the
    "— brak —" option is gone (OWNER_DECISION 2026-09-13: every ORDINARY
    demand always has a role; the earlier ambiguity was CC's own
    misunderstanding, see BOARD.md ROTA-T065-CONFIGURABLE-ROLES) -- and
    that role must belong to this Site's own catalog, never an arbitrary
    string."""
    if regime == SitePlanningRegime.OCHRONA:
        if any(shift.required_role_id is not None for shift in shifts):
            raise ValueError("obiekt Ochrony nie może mieć zmian z przypisaną rolą sklepową")
        return
    if any(shift.required_role_id is None for shift in shifts):
        raise ValueError("każda zmiana obiektu standardowego musi mieć przypisaną rolę")
    # brief section 3: active = available for NEW configurations -- a
    # retired role must never become the required role of a newly-written
    # catalog row, even though already-persisted demands keep their frozen
    # required_role_name snapshot untouched.
    active_role_ids = {r.role_id for r in list_site_roles(conn, site_id, include_inactive=False)}
    for shift in shifts:
        if shift.required_role_id not in active_role_ids:
            raise ValueError(f"rola {shift.required_role_id!r} nie należy do aktywnego katalogu ról tego obiektu")


@router.put("/{site_id}/shift-catalog", status_code=204)
def put_shift_catalog(site_id: str, payload: ShiftCatalogIn, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        if not payload.shifts:
            raise ValueError("shift catalog must contain at least one shift")
        shifts = [_build_shift(row) for row in payload.shifts]
        for shift in shifts:
            validate_standard_shift(shift)
        site = get_site(conn, site_id)
        _validate_role_matches_regime(conn, site_id, shifts, site.planning_regime)
        current_profile = get_site_profile(conn, site.profile_id)
        updated_profile = replace(current_profile, standard_shifts=shifts)
        update_site_profile(
            conn, coordinator_id=coordinator_id, site_id=site_id, profile=updated_profile,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- ROTA-DELEGACJA-ABSENCE-KIND brief.md section 4: one narrow Site-default resource ---


class DelegationDefaultHoursOut(BaseModel):
    delegation_default_hours: int | None


class DelegationDefaultHoursIn(BaseModel):
    delegation_default_hours: int


@router.get("/{site_id}/delegation-default-hours", response_model=DelegationDefaultHoursOut)
def get_delegation_default_hours(
    site_id: str, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id),
) -> DelegationDefaultHoursOut:
    try:
        site = get_site(conn, site_id)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return DelegationDefaultHoursOut(delegation_default_hours=site.delegation_default_hours)


@router.put("/{site_id}/delegation-default-hours", status_code=204)
def put_delegation_default_hours(
    site_id: str, payload: DelegationDefaultHoursIn,
    conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id),
) -> None:
    try:
        if payload.delegation_default_hours <= 0:
            raise ValueError("delegation_default_hours must be a positive integer")
        site = get_site(conn, site_id)
        updated_site = replace(site, delegation_default_hours=payload.delegation_default_hours)
        update_site(conn, coordinator_id=coordinator_id, site_id=site_id, site=updated_site)
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- ROTA-OCHRONA-EDIT-7D-LIMIT brief.md: OCHRONA-only edit of the
# existing rolling_7d_decision_threshold_hours, reusing update_site_profile
# unchanged -- no new field, no new write path, no ORDINARY exposure. ---

ROLLING_7D_WARNING_THRESHOLD_HOURS = 72


class Rolling7dLimitOut(BaseModel):
    rolling_7d_decision_threshold_hours: int
    planning_regime: str


class Rolling7dLimitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rolling_7d_decision_threshold_hours: int
    # brief.md: required (server-enforced, not just UI) above 72h -- a
    # direct API call without it must be refused exactly like the modal's
    # own unchecked box would refuse to submit.
    confirmed_over_72h: bool = False
    responds_to_decision_required_id: str | None = None


@router.get("/{site_id}/rolling-7d-limit", response_model=Rolling7dLimitOut)
def get_rolling_7d_limit(site_id: str, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> Rolling7dLimitOut:
    try:
        site = get_site(conn, site_id)
        profile = get_site_profile(conn, site.profile_id)
        return Rolling7dLimitOut(
            rolling_7d_decision_threshold_hours=profile.rolling_7d_decision_threshold_hours,
            planning_regime=site.planning_regime.value,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.put("/{site_id}/rolling-7d-limit", status_code=204)
def put_rolling_7d_limit(
    site_id: str, payload: Rolling7dLimitIn, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id),
) -> None:
    try:
        site = get_site(conn, site_id)
        if site.planning_regime != SitePlanningRegime.OCHRONA:
            raise ValueError("limit obciążenia w ruchomych 7 dniach można zmieniać wyłącznie dla obiektów OCHRONA")
        if payload.rolling_7d_decision_threshold_hours <= 0:
            raise ValueError("limit godzin w ruchomych 7 dniach musi być dodatnią liczbą całkowitą")
        if payload.rolling_7d_decision_threshold_hours > ROLLING_7D_WARNING_THRESHOLD_HOURS and not payload.confirmed_over_72h:
            raise ValueError(
                "wartość powyżej 72 godzin wymaga świadomego potwierdzenia ostrzeżenia przed zapisem"
            )
        current_profile = get_site_profile(conn, site.profile_id)
        updated_profile = replace(
            current_profile, rolling_7d_decision_threshold_hours=payload.rolling_7d_decision_threshold_hours,
        )
        update_site_profile(
            conn, coordinator_id=coordinator_id, site_id=site_id, profile=updated_profile,
            note=(
                "Potwierdzono ostrzeżenie o limicie obciążenia >72h w ruchomych 7 dniach"
                if payload.confirmed_over_72h else None
            ),
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
