"""Operation 9 (tasks/ROTA-T009/brief.md): Training S readiness. Training
remains ordinary Assignment data (no TrainingRecord) -- add/edit/cancel
TRAINEE already goes through operation 8's manual correction mechanism.
This module adds only the readiness-threshold side effect of marking a
TRAINEE Assignment REALIZED.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.application import manual_edit
from rota.domain import Assignment, AssignmentRole, AssignmentState, ReadinessSource, ReadinessState, ScheduleVersion
from rota.persistence.employee_repository import (
    list_memberships_for_site,
    write_site_membership_in_open_transaction,
)
from rota.persistence.schedule_repository import get_current_assignments_for_employees
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site


def save_site_membership(conn, membership) -> None:
    """R5-1: the on_success hook below runs INSIDE create_schedule_version's
    still-open transaction, so this write must NOT open (and commit) a
    transaction of its own -- a nested `with conn:` would commit everything
    written so far (the schedule child included) the moment this call
    returns, making a failure raised immediately afterward unable to roll
    anything back. Kept as a module-level function (not inlined) so it
    stays the name tests patch to inject that exact failure."""
    write_site_membership_in_open_transaction(conn, membership)


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
    itself is still a legitimate record of training that happened.

    R6-4 (owner decision): evaluated against the CURRENT profile only, at
    count time -- SiteProfile is not versioned, so there is no frozen way
    to know what it was when a past Assignment was recorded, and operation
    9 must not persist a second training record to remember that. A
    profile toggle can therefore change what past Assignments count from
    this point forward; that is accepted, not a defect."""
    if not profile.training_s_enabled:
        return False
    if profile.training_s_weekdays_only and trainee_assignment.start_datetime.weekday() >= 5:
        return False
    return True


def _current_qualifying_training_count(conn, *, employee_id: str, profile) -> int:
    """R6-3/R6-4: counts current REALIZED TRAINEE Assignments straight from
    ordinary Assignment data -- no separate ledger. Scoped to CURRENT
    ScheduleVersions only, so a superseded version (e.g. a re-submitted
    assignment_id cloned into a later child) is naturally not double
    counted, and two distinct months' current versions reusing the same
    local assignment_id are naturally two distinct rows, not one.

    ROTA-T016: the query window is a fixed, technical all-time range, not
    derived from Employee.active_from -- that field is retired legacy
    metadata after T016 and must not gate which historical training counts
    (owner decision 2026-08-16: the program does not decide who may work,
    so it must not silently narrow readiness history off that field
    either)."""
    assignments = get_current_assignments_for_employees(conn, [employee_id], datetime.min, datetime.max)
    return sum(
        1 for a in assignments
        if a.role == AssignmentRole.TRAINEE and a.state == AssignmentState.REALIZED
        and _qualifies_for_readiness(a, profile)
    )


def _build_readiness_hook(conn, *, site_id: str, trainee_assignment: Assignment, profile):
    """R4-1/R5-1: the schedule child write and the derived readiness update
    are one coordinator write -- whenever there is a DEFAULT-sourced
    membership to (re)save at all, that save must go through the SAME
    transaction as the schedule child, via the hook run by
    create_schedule_version() INSIDE its own open transaction. When the
    training doesn't qualify for promotion (R4-4), the hook still runs but
    resaves the membership's own current readiness_state unchanged -- the
    write, not just its outcome, is part of what must be atomic with the
    schedule child."""
    membership = next(
        (m for m in list_memberships_for_site(conn, site_id) if m.employee_id == trainee_assignment.employee_id), None,
    )
    if membership is None or membership.readiness_source != ReadinessSource.DEFAULT:
        return None

    def _apply(open_conn) -> None:
        # By this point create_schedule_version() has already inserted the
        # new Assignment and pointed current at this version, so the count
        # below already includes it -- no manual +1.
        count = _current_qualifying_training_count(
            open_conn, employee_id=trainee_assignment.employee_id, profile=profile,
        )
        target_state = membership.readiness_state
        if count >= profile.training_s_default_readiness_threshold:
            target_state = ReadinessState.READY_FOR_PRIMARY
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
    profile = get_site_profile(conn, get_site(conn, site_id).profile_id)
    on_success = _build_readiness_hook(conn, site_id=site_id, trainee_assignment=trainee_assignment, profile=profile)
    return manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        upsert_assignments=[trainee_assignment], on_success=on_success,
    )
