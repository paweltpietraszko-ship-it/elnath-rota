"""Read-only wraps of employee_repository/availability_repository/
work_balance_repository -- persistence-layer, no owning application
module (brief.md section 5.1: "call directly", same already-accepted
missing-wrapper pattern as Screen 1's calendar read). Writes live in
api/routers/durable_inputs.py, matching the module they wrap.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.availability_matrix import employee_availability_matrix
from rota.persistence.employee_repository import (
    get_employee,
    list_employees,
    list_employees_by_ids,
    list_memberships_for_site,
)
from rota.persistence.availability_repository import get_current_availability_for_employee
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


class EmployeeOut(BaseModel):
    employee_id: str
    display_name: str
    day_only: bool


class MembershipOut(BaseModel):
    enabled: bool
    can_work_24h: bool
    readiness_state: str
    readiness_source: str


class AvailabilityRecordOut(BaseModel):
    availability_id: str
    kind: str
    start_date: str
    end_date: str
    active: bool


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
        raise HTTPException(status_code=404, detail=f"employee {employee_id!r} has no membership at site {site_id!r}")
    availability = get_current_availability_for_employee(conn, employee_id)
    return EmployeeDetailOut(
        employee=EmployeeOut(employee_id=employee.employee_id, display_name=employee.display_name, day_only=employee.day_only),
        membership=MembershipOut(
            enabled=membership.enabled, can_work_24h=membership.can_work_24h,
            readiness_state=membership.readiness_state.value, readiness_source=membership.readiness_source.value,
        ),
        availability=[
            AvailabilityRecordOut(
                availability_id=r.availability_id, kind=r.kind.value,
                start_date=r.start_date.isoformat(), end_date=r.end_date.isoformat(), active=r.active,
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
