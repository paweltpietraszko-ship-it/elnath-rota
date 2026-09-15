"""Read-only wraps of employee_repository/availability_repository/
work_balance_repository -- persistence-layer, no owning application
module (brief.md section 5.1: "call directly", same already-accepted
missing-wrapper pattern as Screen 1's calendar read). Writes live in
api/routers/durable_inputs.py, matching the module they wrap.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import public_http_exception, to_http_exception
from rota.application.availability_matrix import employee_availability_matrix
from rota.persistence.employee_repository import (
    get_employee,
    list_employees,
    list_employees_by_ids,
    list_memberships_for_site,
)
from rota.persistence.availability_repository import get_current_availability_for_employee
from rota.persistence.site_role_repository import list_role_coverage_authorizations_for_site, list_site_roles
from rota.persistence.work_balance_repository import get_work_balance_target
from rota.planning.site_rules import EMPLOYEE_DAY_ONLY_N_EXCEPTION

router = APIRouter(prefix="/workspace", tags=["roster"])

_ALL_WEEKDAYS = list(range(1, 8))


def _classify_matrix_rule(version) -> tuple[str, int | None]:
    """Same canonical shape mapping T021b's own _describe_matrix_family
    uses server-side (tasks/ROTA-T021b/brief.md section 2) -- marshalling
    of an already-frozen shape, not a new decision."""
    if version.rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION:
        return "day_only_exception", None
    params = version.structured_parameters
    weekdays = params.get("weekdays") if isinstance(params, dict) else None
    forbidden = params.get("forbidden_shift_kinds") if isinstance(params, dict) else None
    if weekdays == _ALL_WEEKDAYS and forbidden == ["D"]:
        return "dniowka", None
    if weekdays == _ALL_WEEKDAYS and forbidden == ["N"]:
        return "nocka", None
    if isinstance(weekdays, list) and len(weekdays) == 1 and forbidden == ["D", "N"]:
        return "weekday", weekdays[0]
    return "other", None


class RosterRow(BaseModel):
    employee_id: str
    display_name: str
    enabled: bool
    can_work_24h: bool
    readiness_state: str
    membership_kind: str
    # ROTA-T065-CONFIGURABLE-ROLES section 4: None for OCHRONA/legacy
    # memberships, or an ORDINARY employee never assigned a position.
    position_role_id: str | None


class EmployeeOut(BaseModel):
    employee_id: str
    display_name: str
    day_only: bool


class MembershipOut(BaseModel):
    enabled: bool
    can_work_24h: bool
    readiness_state: str
    readiness_source: str
    position_role_id: str | None


class AvailabilityRecordOut(BaseModel):
    availability_id: str
    kind: str
    start_date: str
    end_date: str
    active: bool
    # ROTA-T065-ORDINARY-TIME-AVAILABILITY: set only for kind ==
    # UNAVAILABLE_TIME_WINDOW; None for every other (whole-day) kind.
    start_time: str | None = None
    end_time: str | None = None
    # ROTA-DELEGACJA-ABSENCE-KIND (owner-confirmed TASK_SCOPE extension,
    # 2026-09-15): set only for kind == DELEGACJA. Required read-side --
    # the write boundary requires this value on every append of an
    # existing DELEGACJA family (including deactivation), so the frontend
    # must have it to resubmit a valid update.
    delegation_hours: int | None = None


class EmployeeDetailOut(BaseModel):
    employee: EmployeeOut
    membership: MembershipOut
    availability: list[AvailabilityRecordOut]


class PickableEmployeeOut(BaseModel):
    employee_id: str
    display_name: str
    reason: str  # "new" | "re-add" -- which action selecting this employee performs


class TargetHoursOut(BaseModel):
    target_hours: int | None


class MatrixCellOut(BaseModel):
    rule_id: str
    rule_version_id: str  # round-13 R12-2B: one family can have >1 version
    # effective on different days within one queried month (a mid-period
    # correction) -- this is the per-version render/selection identity;
    # rule_id (the family) is still what update/end-early are called with.
    cell: str  # "dniowka" | "nocka" | "weekday" | "day_only_exception" | "other"
    weekday: int | None
    effective_from: str
    effective_to: str | None
    applies_from: str | None
    applies_to: str | None


class EmployeeMatrixOut(BaseModel):
    cells: list[MatrixCellOut]


@router.get("/sites/{site_id}/roster", response_model=list[RosterRow])
def list_roster(site_id: str, conn=Depends(get_conn)) -> list[RosterRow]:
    """OWNER_CORRECTED (2026-08-27): both LOCAL and EXTERNAL_SUPPORT rows --
    the earlier LOCAL-only scope predates membership_kind being settable
    on this same "+ Dodaj osobę" flow and made EXTERNAL_SUPPORT people
    invisible on their own roster (couldn't be seen or removed here).
    Both enabled and disabled rows, the UI marks disabled ones
    distinctly and offers re-add, never hides them."""
    memberships = list(list_memberships_for_site(conn, site_id))
    employees = list_employees_by_ids(conn, [m.employee_id for m in memberships])
    return [
        RosterRow(
            employee_id=m.employee_id,
            display_name=employees[m.employee_id].display_name,
            enabled=m.enabled,
            can_work_24h=m.can_work_24h,
            readiness_state=m.readiness_state.value,
            membership_kind=m.membership_kind.value,
            position_role_id=m.position_role_id,
        )
        for m in memberships
    ]


@router.get("/sites/{site_id}/roster/pickable", response_model=list[PickableEmployeeOut])
def list_pickable_employees(site_id: str, conn=Depends(get_conn)) -> list[PickableEmployeeOut]:
    """Existing-employee picker for "+ Dodaj osobę". OWNER_CORRECTED
    (2026-08-27): a disabled row of EITHER membership_kind is pickable
    for re-add, same as LOCAL always was -- insert/remove is meant to be
    a full cycle regardless of kind (only an ENABLED row, of any kind,
    stays excluded since it's already on the roster)."""
    memberships_by_employee = {m.employee_id: m for m in list_memberships_for_site(conn, site_id)}
    out: list[PickableEmployeeOut] = []
    for employee in list_employees(conn):
        membership = memberships_by_employee.get(employee.employee_id)
        if membership is None:
            out.append(PickableEmployeeOut(employee_id=employee.employee_id, display_name=employee.display_name, reason="new"))
        elif not membership.enabled:
            out.append(PickableEmployeeOut(employee_id=employee.employee_id, display_name=employee.display_name, reason="re-add"))
    return out


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut)
def get_employee_detail(employee_id: str, site_id: str, conn=Depends(get_conn)) -> EmployeeDetailOut:
    try:
        employee = get_employee(conn, employee_id)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    membership = next((m for m in list_memberships_for_site(conn, site_id) if m.employee_id == employee_id), None)
    if membership is None:
        # ROTA-T060 (ARCHITECT_RULING R2, brief 2.1.3): this direct bypass
        # must use the same shared public-error contract as to_http_exception
        # -- never a locally copied header/message.
        raise public_http_exception(404, "Pracownik nie jest przypisany do tego obiektu.")
    availability = get_current_availability_for_employee(conn, employee_id)
    return EmployeeDetailOut(
        employee=EmployeeOut(employee_id=employee.employee_id, display_name=employee.display_name, day_only=employee.day_only),
        membership=MembershipOut(
            enabled=membership.enabled, can_work_24h=membership.can_work_24h,
            readiness_state=membership.readiness_state.value, readiness_source=membership.readiness_source.value,
            position_role_id=membership.position_role_id,
        ),
        availability=[
            AvailabilityRecordOut(
                availability_id=r.availability_id, kind=r.kind.value,
                start_date=r.start_date.isoformat(), end_date=r.end_date.isoformat(), active=r.active,
                start_time=r.start_time.strftime("%H:%M") if r.start_time is not None else None,
                end_time=r.end_time.strftime("%H:%M") if r.end_time is not None else None,
                delegation_hours=r.delegation_hours,
            )
            for r in availability
        ],
    )


@router.get("/employees/{employee_id}/target-hours", response_model=TargetHoursOut)
def get_target_hours(employee_id: str, month: str, conn=Depends(get_conn)) -> TargetHoursOut:
    return TargetHoursOut(target_hours=get_work_balance_target(conn, employee_id, date.fromisoformat(month)))


@router.get("/employees/{employee_id}/matrix", response_model=EmployeeMatrixOut)
def get_employee_matrix(employee_id: str, site_id: str, month: str, conn=Depends(get_conn)) -> EmployeeMatrixOut:
    """Dniówka/Nocka/weekday/day_only-exception cells (brief.md section
    5.1) -- rota.application.availability_matrix.employee_availability_matrix
    is the effective-state read owner (T021b brief section 8), not
    get_current_availability_for_employee (that's the separate Ogólna
    dostępność mechanism)."""
    try:
        matrix = employee_availability_matrix(conn, site_id=site_id, employee_id=employee_id, month=date.fromisoformat(month))
    except Exception as exc:
        raise to_http_exception(exc) from exc
    applicability_by_version = {a.rule_version_id: a for a in matrix.rule_applicability}
    cells = []
    for version in matrix.weekday_and_exception_rules:
        applicability = applicability_by_version.get(version.rule_version_id)
        cell, weekday = _classify_matrix_rule(version)
        cells.append(MatrixCellOut(
            rule_id=version.rule_id, rule_version_id=version.rule_version_id, cell=cell, weekday=weekday,
            effective_from=version.effective_from.isoformat(),
            effective_to=version.effective_to.isoformat() if version.effective_to else None,
            applies_from=applicability.applies_from.isoformat() if applicability else None,
            applies_to=applicability.applies_to.isoformat() if applicability else None,
        ))
    return EmployeeMatrixOut(cells=cells)


# --- Site role catalog + coverage authorizations (ROTA-T065-CONFIGURABLE-ROLES) ---
# Writes live in api/routers/durable_inputs.py, matching this whole file's
# own established read/write split.


class SiteRoleOut(BaseModel):
    role_id: str
    display_name: str
    active: bool


@router.get("/sites/{site_id}/roles", response_model=list[SiteRoleOut])
def list_site_roles_endpoint(site_id: str, conn=Depends(get_conn)) -> list[SiteRoleOut]:
    return [SiteRoleOut(role_id=r.role_id, display_name=r.display_name, active=r.active) for r in list_site_roles(conn, site_id)]


class RoleCoverageAuthorizationOut(BaseModel):
    authorization_id: str
    employee_id: str
    covered_role_id: str
    start_datetime: str
    end_datetime: str
    active: bool


@router.get("/sites/{site_id}/role-coverage-authorizations", response_model=list[RoleCoverageAuthorizationOut])
def list_role_coverage_authorizations_endpoint(site_id: str, conn=Depends(get_conn)) -> list[RoleCoverageAuthorizationOut]:
    return [
        RoleCoverageAuthorizationOut(
            authorization_id=a.authorization_id, employee_id=a.employee_id, covered_role_id=a.covered_role_id,
            start_datetime=a.start_datetime.isoformat(), end_datetime=a.end_datetime.isoformat(), active=a.active,
        )
        for a in list_role_coverage_authorizations_for_site(conn, site_id)
    ]
