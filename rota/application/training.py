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


def _require_qualifying_shape(trainee_assignment: Assignment) -> None:
    """R4-4: mark_training_realized names exactly what it does -- only a
    genuine TRAINEE Assignment already marked REALIZED by the caller
    qualifies; anything else is a caller error, not a silent no-op."""
    if trainee_assignment.role != AssignmentRole.TRAINEE:
        raise ValueError(f"{trainee_assignment.assignment_id!r}: mark_training_realized requires role=TRAINEE")
    if trainee_assignment.state != AssignmentState.REALIZED:
        raise ValueError(f"{trainee_assignment.assignment_id!r}: mark_training_realized requires state=REALIZED")


def _qualifies_for_readiness(trainee_assignment: Assignment, profile) -> bool:
    """R4-4: arch/spec.md SiteProfile training_s_enabled/
    training_s_weekdays_only gate whether a REALIZED TRAINEE counts toward
    readiness at all -- silently, not as an error, since the Assignment
    itself is still a legitimate record of training that happened."""
    if not profile.training_s_enabled:
        return False
    if profile.training_s_weekdays_only and trainee_assignment.start_datetime.weekday() >= 5:
        return False
    return True


def _realized_training_count(conn, employee_id: str, active_from: date) -> int:
    window_start = datetime.combine(active_from, datetime.min.time())
    window_end = window_start + timedelta(days=365 * 100)
    assignments = get_current_assignments_for_employees(conn, [employee_id], window_start, window_end)
    return sum(1 for a in assignments if a.role == AssignmentRole.TRAINEE and a.state == AssignmentState.REALIZED)


def _build_readiness_hook(conn, *, site_id: str, trainee_assignment: Assignment, qualifies: bool):
    """R4-1: the schedule child write and the derived readiness update are
    one coordinator write -- whenever there is a DEFAULT-sourced membership
    to (re)save at all, that save must go through the SAME transaction as
    the schedule child, via the hook run by create_schedule_version()
    INSIDE its own open transaction (not a second, separately-committing
    call). When the training doesn't qualify for promotion (R4-4), the
    hook still runs but resaves the membership's own current
    readiness_state unchanged -- the write, not just its outcome, is part
    of what must be atomic with the schedule child."""
    membership = next(
        (m for m in list_memberships_for_site(conn, site_id) if m.employee_id == trainee_assignment.employee_id), None,
    )
    if membership is None or membership.readiness_source != ReadinessSource.DEFAULT:
        return None
    target_state = membership.readiness_state
    if qualifies:
        profile = get_site_profile(conn, get_site(conn, site_id).profile_id)
        employee = get_employee(conn, trainee_assignment.employee_id)
        # +1 for the Assignment being recorded in this same transaction --
        # it is not yet visible to a query run before the write completes.
        count = _realized_training_count(conn, trainee_assignment.employee_id, employee.active_from) + 1
        if count >= profile.training_s_default_readiness_threshold:
            target_state = ReadinessState.READY_FOR_PRIMARY

    def _apply(open_conn) -> None:
        # save_site_membership's own `with conn:` commits the transaction
        # so far -- including the just-written schedule child -- as one
        # unit; on failure it raises before committing, so the child
        # insert rolls back too.
        save_site_membership(open_conn, replace(membership, readiness_state=target_state))

    return _apply


def mark_training_realized(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date, trainee_assignment: Assignment,
) -> ScheduleVersion:
    """Marks one TRAINEE Assignment REALIZED via the manual correction
    mechanism (mentor/weekday/profile rules stay whatever they already are
    -- unchanged), then atomically resaves membership readiness, promoting
    it only if the profile's threshold is reached and readiness_source is
    still DEFAULT."""
    _require_qualifying_shape(trainee_assignment)
    qualifies = _qualifies_for_readiness(trainee_assignment, get_site_profile(conn, get_site(conn, site_id).profile_id))
    on_success = _build_readiness_hook(conn, site_id=site_id, trainee_assignment=trainee_assignment, qualifies=qualifies)
    return manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[trainee_assignment], on_success=on_success,
    )
