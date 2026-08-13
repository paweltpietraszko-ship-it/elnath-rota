"""Operation 9 (tasks/ROTA-T009/brief.md): Training S readiness. Training
remains ordinary Assignment data (no TrainingRecord) -- add/edit/cancel
TRAINEE already goes through operation 8's manual correction mechanism.
This module adds only the readiness-threshold side effect of marking a
TRAINEE Assignment REALIZED.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

from rota.application import manual_edit
from rota.domain import Assignment, AssignmentRole, AssignmentState, ReadinessSource, ReadinessState, ScheduleVersion
from rota.persistence.employee_repository import get_employee, list_memberships_for_site, save_site_membership
from rota.persistence.schedule_repository import get_current_assignments_for_employees
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site


def _realized_training_count(conn, employee_id: str, active_from: date) -> int:
    window_start = datetime.combine(active_from, datetime.min.time())
    window_end = window_start + timedelta(days=365 * 100)
    assignments = get_current_assignments_for_employees(conn, [employee_id], window_start, window_end)
    return sum(1 for a in assignments if a.role == AssignmentRole.TRAINEE and a.state == AssignmentState.REALIZED)


def _maybe_update_readiness(conn, *, site_id: str, employee_id: str) -> None:
    membership = next(
        (m for m in list_memberships_for_site(conn, site_id) if m.employee_id == employee_id), None,
    )
    if membership is None or membership.readiness_source != ReadinessSource.DEFAULT:
        return  # COORDINATOR_OVERRIDE is never overwritten
    profile = get_site_profile(conn, get_site(conn, site_id).profile_id)
    employee = get_employee(conn, employee_id)
    count = _realized_training_count(conn, employee_id, employee.active_from)
    if count >= profile.training_s_default_readiness_threshold:
        save_site_membership(conn, replace(membership, readiness_state=ReadinessState.READY_FOR_PRIMARY))


def mark_training_realized(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date, trainee_assignment: Assignment,
) -> ScheduleVersion:
    """Marks one TRAINEE Assignment REALIZED via the manual correction
    mechanism (mentor/weekday/profile rules stay whatever they already are
    -- unchanged), then updates membership readiness if the profile's
    threshold is reached and readiness_source is still DEFAULT."""
    new_version = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[trainee_assignment],
    )
    _maybe_update_readiness(conn, site_id=site_id, employee_id=trainee_assignment.employee_id)
    return new_version
