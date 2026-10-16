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
    """Data-integrity rejections only: an unknown/inactive/foreign role, no
    active membership, or a non-ORDINARY Site, before any child
    ScheduleVersion is created. A role different from the person's
    position without authorization is NOT rejected (ROTA-MANUAL-MIDDLE-
    ROLE-BLOCK, OWNER 2026-10-16) -- the validator records it as ROLE-01.
    A ValueError subclass so api/errors.py's existing generic
    ValueError->400 mapping applies without a new registration in that
    shared, out-of-scope module."""


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

    The site-regime/role-catalog/membership preconditions are hard
    data-integrity gates checked here, BEFORE any child ScheduleVersion is
    created. Working in a role other than one's position without a covering
    RoleCoverageAuthorization is a deliberate coordinator decision
    (ROTA-MANUAL-MIDDLE-ROLE-BLOCK): saved, and the validator's ROLE-01
    becomes a PREFERENCE Deviation. Hourly availability (UNAVAILABLE_TIME-01) and every
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
