"""Wraps rota.application.durable_inputs (brief.md section 3.2: one router
module per rota/application/*.py module it wraps). Marshalling only.

ROTA-T064 (brief.md section 4): month generation is a thin batch command
in rota/application/durable_inputs.py (generate_calendar_month), backed by
the existing CalendarDay persistence path -- no new domain layer.
"""
from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn, get_coordinator_id
from api.errors import to_http_exception
from rota.application.durable_inputs import (
    add_external_support_window,
    append_availability,
    generate_calendar_month,
    generate_calendar_years,
    save_site_role,
    set_calendar_day,
    set_role_coverage_authorization,
    set_target_hours,
    set_target_hours_for_site_roster,
    update_employee,
    update_membership,
)
from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RoleCoverageAuthorization,
    ShiftKind,
    SiteMembership,
    SiteRoleDefinition,
)
from rota.persistence.employee_repository import get_employee, list_memberships_for_site

calendar_router = APIRouter(prefix="/workspace/calendar", tags=["calendar"])
roster_router = APIRouter(prefix="/workspace", tags=["roster"])


class SetDayRequest(BaseModel):
    date: str
    holiday: bool
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope


@calendar_router.post("/day", status_code=204)
def set_day(payload: SetDayRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        day_date = date.fromisoformat(payload.date)
        set_calendar_day(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id,
            day=CalendarDay(day_date, payload.holiday),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class GenerateMonthRequest(BaseModel):
    month: str  # "YYYY-MM-01" or "YYYY-MM" -- normalized below
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope


class GenerateMonthResponse(BaseModel):
    created: int


@calendar_router.post("/generate", response_model=GenerateMonthResponse)
def generate_month(payload: GenerateMonthRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> GenerateMonthResponse:
    """ROTA-T064: fill-missing-only batch generation for one month, PL
    public holidays via the `holidays` library. Never overwrites an
    existing CalendarDay (manual correction or earlier generate)."""
    try:
        month_str = payload.month if len(payload.month) > 7 else f"{payload.month}-01"
        month_date = date.fromisoformat(month_str)
        created = generate_calendar_month(conn, coordinator_id=coordinator_id, site_id=payload.site_id, month=month_date)
        return GenerateMonthResponse(created=created)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class GenerateYearsRequest(BaseModel):
    start_month: str  # "YYYY-MM-01" or "YYYY-MM" -- normalized below
    site_id: str  # any one of the coordinator's own site_ids -- auth only, never data scope
    years: int = 3


@calendar_router.post("/generate-years", response_model=GenerateMonthResponse)
def generate_years(payload: GenerateYearsRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> GenerateMonthResponse:
    """OWNER 2026-09-21: one click fills several years ahead instead of one
    month at a time -- same fill-missing-only, never-overwrite semantics as
    /generate, just looped (generate_calendar_years)."""
    try:
        month_str = payload.start_month if len(payload.start_month) > 7 else f"{payload.start_month}-01"
        start_month_date = date.fromisoformat(month_str)
        created = generate_calendar_years(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id, start_month=start_month_date, years=payload.years,
        )
        return GenerateMonthResponse(created=created)
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- Employee creation (brief.md section 5.1, round-9 R9-1) ---
# employee_id is frontend-generated (crypto.randomUUID()) so this call is
# idempotent under retry -- the API never generates or returns an id.


class CreateEmployeeRequest(BaseModel):
    employee_id: str
    site_id: str  # coordinator-context authorization only, not persisted on Employee
    display_name: str
    day_only: bool
    responds_to_decision_required_id: str | None = None


@roster_router.post("/employees", status_code=204)
def create_employee(payload: CreateEmployeeRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        update_employee(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id,
            employee=Employee(payload.employee_id, payload.display_name, date.today(), None, payload.day_only),
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class UpdateDayOnlyRequest(BaseModel):
    site_id: str
    day_only: bool


@roster_router.patch("/employees/{employee_id}", status_code=204)
def update_day_only(employee_id: str, payload: UpdateDayOnlyRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    """Reads the employee's current record first and resubmits every
    field unchanged except day_only (brief.md section 5.1, round-7
    R7-2) -- never blanks display_name/active_from/active_to."""
    try:
        current = get_employee(conn, employee_id)
        update_employee(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id,
            employee=Employee(current.employee_id, current.display_name, current.active_from, current.active_to, payload.day_only),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- Roster attach / remove / re-add / 24h (LOCAL only, brief.md section 5.1) ---


class AttachRosterRequest(BaseModel):
    employee_id: str
    # OWNER_CORRECTED (2026-08-27): "Wsparcie zewnętrzne" is not a separate
    # feature/screen -- it's the same roster row, just membership_kind=
    # EXTERNAL_SUPPORT (already a plain SiteMembership field, per
    # arch/T021_spec.md's own confirmed placement). Defaults to LOCAL so
    # every existing caller of this endpoint is unaffected.
    membership_kind: str = "LOCAL"
    responds_to_decision_required_id: str | None = None
    # ROTA-T065-CONFIGURABLE-ROLES R5-01: an ORDINARY site's active
    # SiteMembership must always name exactly one active position (brief
    # sections 4/9) -- attach is a normal write boundary too, so it must
    # be able to set the position atomically in the same call, not leave
    # it to a follow-up PATCH. None for a re-add carries the existing
    # row's own position forward unchanged.
    position_role_id: str | None = None


@roster_router.post("/sites/{site_id}/roster", status_code=204)
def attach_to_roster(site_id: str, payload: AttachRosterRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    """Shared by "nowy pracownik" (after employee creation) and
    "istniejący pracownik" (re-add a disabled row of either
    membership_kind). Reuses the disabled row's own can_work_24h/
    readiness fields when one exists, per brief.md section 5.1 round-8
    R8-1 -- never fabricates new defaults over an existing row."""
    try:
        kind = MembershipKind(payload.membership_kind)
        existing = next(
            (m for m in list_memberships_for_site(conn, site_id) if m.employee_id == payload.employee_id), None,
        )
        if existing is not None:
            position_role_id = payload.position_role_id if payload.position_role_id is not None else existing.position_role_id
            membership = SiteMembership(
                employee_id=payload.employee_id, site_id=site_id, membership_kind=kind,
                enabled=True, readiness_state=existing.readiness_state, readiness_source=existing.readiness_source,
                can_work_24h=existing.can_work_24h, position_role_id=position_role_id,
            )
        else:
            membership = SiteMembership(
                employee_id=payload.employee_id, site_id=site_id, membership_kind=kind,
                enabled=True, readiness_state=ReadinessState.NOT_READY, readiness_source=ReadinessSource.DEFAULT,
                can_work_24h=True, position_role_id=payload.position_role_id,
            )
        update_membership(
            conn, coordinator_id=coordinator_id, site_id=site_id, membership=membership,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class CreateSupportWindowRequest(BaseModel):
    site_id: str
    start_datetime: str
    end_datetime: str
    allowed_shift_kind: str | None = None  # "D" | "N" | None (None = both)
    responds_to_decision_required_id: str | None = None


@roster_router.post("/employees/{employee_id}/support-window", status_code=204)
def create_support_window(employee_id: str, payload: CreateSupportWindowRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    """OWNER_CORRECTED (2026-08-27): the simplest possible shape -- one
    date range the solver may use this EXTERNAL_SUPPORT person within.
    No list/management screen, no separate feature; add_external_support_window
    already does the real work (rota.application.durable_inputs).
    end_datetime is expected exact (frontend turns the owner-facing "do
    <dzień>" into midnight of the day AFTER -- owner ruling 2026-08-27:
    the named end day is included in full)."""
    try:
        window = ExternalSupportWindow(
            window_id=f"WIN-{employee_id}-{payload.start_datetime}", employee_id=employee_id, site_id=payload.site_id,
            start_datetime=datetime.fromisoformat(payload.start_datetime), end_datetime=datetime.fromisoformat(payload.end_datetime),
            active=True, allowed_shift_kind=ShiftKind(payload.allowed_shift_kind) if payload.allowed_shift_kind else None,
        )
        add_external_support_window(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id, window=window,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class UpdateRosterRequest(BaseModel):
    enabled: bool | None = None
    can_work_24h: bool | None = None
    # ROTA-T065-CONFIGURABLE-ROLES section 4/9: the coordinator's current
    # organizational position -- None (default) leaves it unchanged;
    # clear_position=True explicitly clears it to "no position" (a genuine
    # state, distinct from "not touched by this call"), matching
    # can_work_24h's own "only touch what's supplied" contract on this same
    # endpoint.
    position_role_id: str | None = None
    clear_position: bool = False


@roster_router.patch("/sites/{site_id}/roster/{employee_id}", status_code=204)
def update_roster_row(site_id: str, employee_id: str, payload: UpdateRosterRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    """Remove-from-roster (enabled=False), the 24h toggle, and the ORDINARY
    organizational position all flow through here: read the current row
    fresh, change only the supplied field(s), carry every other field over
    unchanged (brief.md section 5.1, round-7 R7-1; ROTA-T065-CONFIGURABLE-
    ROLES section 9 extends this same contract to position_role_id -- no
    second membership, no second endpoint)."""
    try:
        current = next((m for m in list_memberships_for_site(conn, site_id) if m.employee_id == employee_id), None)
        if current is None:
            raise ValueError(f"no membership for employee {employee_id!r} at site {site_id!r}")
        if payload.clear_position:
            position_role_id = None
        elif payload.position_role_id is not None:
            position_role_id = payload.position_role_id
        else:
            position_role_id = current.position_role_id
        membership = SiteMembership(
            employee_id=current.employee_id, site_id=current.site_id, membership_kind=current.membership_kind,
            enabled=current.enabled if payload.enabled is None else payload.enabled,
            readiness_state=current.readiness_state, readiness_source=current.readiness_source,
            can_work_24h=current.can_work_24h if payload.can_work_24h is None else payload.can_work_24h,
            position_role_id=position_role_id,
        )
        update_membership(conn, coordinator_id=coordinator_id, site_id=site_id, membership=membership)
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- Site role catalog + coverage authorizations (ROTA-T065-CONFIGURABLE-ROLES) ---


class SiteRoleIn(BaseModel):
    role_id: str
    display_name: str
    active: bool = True


@roster_router.put("/sites/{site_id}/roles/{role_id}", status_code=204)
def save_site_role_endpoint(site_id: str, role_id: str, payload: SiteRoleIn, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    """Create, rename, or retire (active=False) one entry in this Site's
    own role catalog -- section 3/9. role_id in the path and body must
    agree; the frontend generates a stable id once at "add role" time and
    reuses it for every later rename/retire (same idempotent-retry pattern
    as other durable-input ids in this router)."""
    try:
        if payload.role_id != role_id:
            raise ValueError("role_id in path and body must match")
        role = SiteRoleDefinition(role_id=role_id, site_id=site_id, display_name=payload.display_name, active=payload.active)
        save_site_role(conn, coordinator_id=coordinator_id, site_id=site_id, role=role)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class RoleCoverageAuthorizationIn(BaseModel):
    authorization_id: str
    employee_id: str
    covered_role_id: str
    start_datetime: str
    end_datetime: str
    active: bool = True


@roster_router.put("/sites/{site_id}/role-coverage-authorizations/{authorization_id}", status_code=204)
def set_role_coverage_authorization_endpoint(
    site_id: str, authorization_id: str, payload: RoleCoverageAuthorizationIn,
    conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id),
) -> None:
    """Create a new, or cancel (active=False) an existing, time-bounded
    RoleCoverageAuthorization -- section 7. Never changes the employee's
    position_role_id."""
    try:
        if payload.authorization_id != authorization_id:
            raise ValueError("authorization_id in path and body must match")
        authorization = RoleCoverageAuthorization(
            authorization_id=authorization_id, site_id=site_id, employee_id=payload.employee_id,
            covered_role_id=payload.covered_role_id,
            start_datetime=datetime.fromisoformat(payload.start_datetime),
            end_datetime=datetime.fromisoformat(payload.end_datetime), active=payload.active,
        )
        set_role_coverage_authorization(conn, coordinator_id=coordinator_id, site_id=site_id, authorization=authorization)
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- Availability (brief.md section 5.1, "Ogólna dostępność" + "Zgłoś nieobecność") ---
# Multiple independent periods per employee are allowed (architect
# resolution, arch/T021_screen2_availability_singularity_architect_brief_2026-08-23.md)
# -- no lookup/selection logic here. New period = frontend-generated
# availability_id (same idempotent-retry reasoning as R9-1); editing an
# existing period reuses that period's own id, supplied by the frontend
# from the list it already has loaded.


def _parse_full_hour(value: str) -> time:
    """ROTA-T065-ORDINARY-TIME-AVAILABILITY brief.md section 10: same
    full-hour precision as the rest of the product's time-of-day fields
    (e.g. api/routers/site_profile.py's shift-catalog rows) -- Availability
    had no time-of-day field before this Task, so there is no existing
    contract to defer to, and this implementation does not introduce
    finer precision on its own."""
    try:
        hour_str, minute_str = value.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid time format: {value!r}") from exc
    if minute != 0 or not (0 <= hour <= 23):
        raise ValueError(f"time must be a full hour 00:00-23:00, got {value!r}")
    return time(hour=hour, minute=0)


def _parse_optional_time(value: str | None) -> time | None:
    return None if value is None else _parse_full_hour(value)


class CreateAvailabilityRequest(BaseModel):
    site_id: str
    availability_id: str
    kind: str
    start_date: str
    end_date: str
    # ROTA-T065-ORDINARY-TIME-AVAILABILITY: set only for kind ==
    # UNAVAILABLE_TIME_WINDOW -- rota.persistence.availability_repository
    # is the one write boundary that rejects a missing/overnight/mismatched
    # combination, not this marshalling layer.
    start_time: str | None = None
    end_time: str | None = None
    # ROTA-DELEGACJA-ABSENCE-KIND brief.md section 11: set only for kind ==
    # DELEGACJA -- rota.persistence.availability_repository is the one
    # write boundary that rejects a missing/wrongly-present value, not this
    # marshalling layer.
    delegation_hours: int | None = None


@roster_router.post("/employees/{employee_id}/availability", status_code=204)
def create_availability(employee_id: str, payload: CreateAvailabilityRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        append_availability(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id,
            availability_id=payload.availability_id, employee_id=employee_id,
            kind=AvailabilityKind(payload.kind), start_date=date.fromisoformat(payload.start_date),
            end_date=date.fromisoformat(payload.end_date), active=True,
            start_time=_parse_optional_time(payload.start_time), end_time=_parse_optional_time(payload.end_time),
            delegation_hours=payload.delegation_hours,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class UpdateAvailabilityRequest(BaseModel):
    site_id: str
    kind: str
    start_date: str
    end_date: str
    active: bool
    start_time: str | None = None
    end_time: str | None = None
    delegation_hours: int | None = None


@roster_router.patch("/employees/{employee_id}/availability/{availability_id}", status_code=204)
def update_availability(
    employee_id: str, availability_id: str, payload: UpdateAvailabilityRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        append_availability(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id,
            availability_id=availability_id, employee_id=employee_id,
            kind=AvailabilityKind(payload.kind), start_date=date.fromisoformat(payload.start_date),
            end_date=date.fromisoformat(payload.end_date), active=payload.active,
            start_time=_parse_optional_time(payload.start_time), end_time=_parse_optional_time(payload.end_time),
            delegation_hours=payload.delegation_hours,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


# --- Target hours (brief.md section 5.1, round-7 R7-4) ---


class SetTargetHoursRequest(BaseModel):
    site_id: str
    month: str
    target_hours: int


@roster_router.post("/employees/{employee_id}/target-hours", status_code=204)
def set_employee_target_hours(employee_id: str, payload: SetTargetHoursRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        set_target_hours(
            conn, coordinator_id=coordinator_id, site_id=payload.site_id, employee_id=employee_id,
            month=date.fromisoformat(payload.month), target_hours=payload.target_hours,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ApplyTargetHoursToAllRequest(BaseModel):
    target_hours: int


# ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE section 2 ("Ustawienie
# wszystkim") / section 5.
@roster_router.post("/sites/{site_id}/target-hours/{month}/apply-to-all", status_code=204)
def apply_target_hours_to_all(site_id: str, month: str, payload: ApplyTargetHoursToAllRequest, conn=Depends(get_conn), coordinator_id: str = Depends(get_coordinator_id)) -> None:
    try:
        set_target_hours_for_site_roster(
            conn, coordinator_id=coordinator_id, site_id=site_id,
            month=date.fromisoformat(month), target_hours=payload.target_hours,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
