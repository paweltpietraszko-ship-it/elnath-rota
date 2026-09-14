"""ROTA-T065-MANUAL-MIDDLE-SHIFT: the one legal way to add a manually
scheduled ORDINARY "środek" (seasonal/event extra real work). New logic
lives here rather than growing rota/application/manual_edit.py past the
600-line file-size limit (that file was 551 lines before this Task) --
manual_edit.py's apply_manual_correction()/lifecycle stays the single
mechanism this delegates to, per brief section 3.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from rota.application.manual_edit import apply_manual_correction
from rota.domain import Assignment, AssignmentRole, AssignmentState, ScheduleVersion, SitePlanningRegime
from rota.persistence import employee_repository, site_role_repository
from rota.persistence.site_repository import get_site


class ManualMiddleShiftRejected(ValueError):
    """ROTA-T065-MANUAL-MIDDLE-SHIFT brief section 6: an unauthorized role
    substitution, an unknown/inactive role, or a non-ORDINARY Site is
    rejected here, before any child ScheduleVersion is created -- never
    saved as an ordinary Deviation ("ROLE-01 Deviation nie jest
    alternatywną zgodą na zastępstwo"). A ValueError subclass so
    api/errors.py's existing generic ValueError->400 mapping applies
    without a new registration in that shared, out-of-scope module."""


def _authorizes_manual_work_role(
    conn, *, site_id: str, employee_id: str, role_id: str, start: datetime, end: datetime,
) -> bool:
    """The ONE authorization mechanism for performing a role different from
    one's own position (brief section 6): an active RoleCoverageAuthorization
    for this exact (site, employee, role) whose interval fully covers
    [start, end). Reads the single owner in site_role_repository.py --
    no local copy of RoleCoverageAuthorization."""
    return any(
        auth.active and auth.employee_id == employee_id and auth.covered_role_id == role_id
        and auth.start_datetime <= start and auth.end_datetime >= end
        for auth in site_role_repository.list_role_coverage_authorizations_for_site(conn, site_id)
    )


def add_manual_middle_work(
    conn, *, site_id: str, month: date, coordinator_id: str, employee_id: str,
    start_datetime: datetime, end_datetime: datetime, manual_work_role_id: str,
    note: Optional[str] = None, responds_to_decision_required_id: Optional[str] = None,
) -> ScheduleVersion:
    """ROTA-T065-MANUAL-MIDDLE-SHIFT: the one legal way to add a manually
    scheduled ORDINARY "środek" (seasonal/event extra real work) -- a real
    PRIMARY Assignment with no ShiftDemand, created only through this
    function -> the existing apply_manual_correction() lifecycle (brief
    sections 1/3). Never a second endpoint/table/validator/solver pass.

    Role-substitution authorization (section 6) and the site-regime/role-
    catalog preconditions are hard gates checked here, BEFORE any child
    ScheduleVersion is created -- rejecting outright, not materializing an
    ordinary Deviation. Hourly availability (UNAVAILABLE_TIME-01) and every
    other real-work check (overlap/REST/LOAD/WorkBalance/cross-Site) are NOT
    duplicated here -- they run through validate() exactly as for any other
    manual correction, inside apply_manual_correction() below."""
    site = get_site(conn, site_id)
    if site.planning_regime != SitePlanningRegime.ORDINARY:
        raise ManualMiddleShiftRejected(f"{site_id}: manual middle work is only defined for SitePlanningRegime.ORDINARY")
    try:
        role = site_role_repository.get_site_role(conn, manual_work_role_id)
    except KeyError:
        raise ManualMiddleShiftRejected(f"unknown role {manual_work_role_id!r}") from None
    if role.site_id != site_id or not role.active:
        raise ManualMiddleShiftRejected(f"role {manual_work_role_id!r} is not an active role of site {site_id!r}")
    membership = next(
        (m for m in employee_repository.list_memberships_for_employee(conn, employee_id) if m.site_id == site_id and m.enabled),
        None,
    )
    if membership is None:
        raise ManualMiddleShiftRejected(f"{employee_id} has no enabled membership at site {site_id!r}")
    if membership.position_role_id != manual_work_role_id and not _authorizes_manual_work_role(
        conn, site_id=site_id, employee_id=employee_id, role_id=manual_work_role_id,
        start=start_datetime, end=end_datetime,
    ):
        raise ManualMiddleShiftRejected(
            f"{employee_id} has no active RoleCoverageAuthorization for role {manual_work_role_id!r} "
            f"covering {start_datetime.isoformat()}–{end_datetime.isoformat()}"
        )
    assignment = Assignment(
        assignment_id=f"ASG-{uuid.uuid4().hex}", schedule_version_id="", employee_id=employee_id,
        start_datetime=start_datetime, end_datetime=end_datetime, role=AssignmentRole.PRIMARY,
        state=AssignmentState.PLANNED, frozen=False, covers_demand_id=None, mentor_primary_assignment_id=None,
        manual_work_role_id=manual_work_role_id, manual_work_role_name=role.display_name,
    )
    return apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, upsert_assignments=[assignment],
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )
