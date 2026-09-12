"""Codex audit R4: equivalence-class tests for T009 application invariants."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date, datetime, time

import pytest

from rota.application import durable_inputs, lifecycle_ops, manual_edit, open_month, plan_ops, training
from rota.application.assembler import assemble_planning_state, generate_profile_demands
from rota.application.errors import CandidateRejected, IncompleteCalendarData, InvalidCoordinatorContext
from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind, CalendarDay, Coordinator,
    CoordinatorSiteAssociation, ExternalSupportWindow, MembershipKind,
    ReadinessSource, ReadinessState, ShiftKind, SiteMembership, SiteProfile,
    StandardShift,
)
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import (
    get_external_support_window, list_memberships_for_site, save_site_membership,
)
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.schedule_repository import (
    get_current_version_id, get_schedule_snapshot,
)
from rota.persistence.availability_repository import get_current_availability_for_employee
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_select(conn, site_id):
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH,
    )
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")


def _seed_two_sites(conn):
    first = seed_real_object(conn, case_id="audit-site-1", month=MONTH, seed=701)
    site_1 = first.site.site_id
    other_profile = replace(first.profile, profile_id="other-profile")
    save_site_profile(conn, other_profile)
    second_site = replace(
        first.site, site_id="other-site", display_name="Other", profile_id=other_profile.profile_id,
    )
    from rota.persistence.site_repository import save_site
    save_site(conn, second_site)
    for membership in first.memberships:
        save_site_membership(conn, replace(membership, site_id="other-site"))
    save_coordinator(conn, Coordinator("COORD-2", "Other coordinator", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-2", "other-site", True))
    return first, site_1


# APPLICATION CONTEXT invariant: a command authorized for site A must not mutate
# an object whose own site scope is B. Representative sibling commands cover an
# external window and a membership.
@pytest.mark.parametrize("kind", ["window", "membership", "profile"])
def test_r4_context_scope_rejects_payload_from_other_site(tmp_path, kind):
    conn = connect(tmp_path / "rota.db")
    state, site_1 = _seed_two_sites(conn)
    employee = state.employees[0].employee_id
    if kind == "window":
        payload = ExternalSupportWindow(
            "cross-site-window", employee, "other-site",
            datetime(2026, 8, 2, 5), datetime(2026, 8, 2, 17), True, ShiftKind.D,
        )
        with pytest.raises(InvalidCoordinatorContext):
            durable_inputs.add_external_support_window(
                conn, coordinator_id="COORD-1", site_id=site_1, window=payload,
            )
        with pytest.raises(KeyError):
            get_external_support_window(conn, payload.window_id)
    elif kind == "membership":
        payload = SiteMembership(
            employee, "other-site", MembershipKind.LOCAL, False,
            ReadinessState.NOT_READY, ReadinessSource.DEFAULT,
        )
        before = next(m for m in list_memberships_for_site(conn, "other-site") if m.employee_id == employee)
        with pytest.raises(InvalidCoordinatorContext):
            durable_inputs.update_membership(
                conn, coordinator_id="COORD-1", site_id=site_1, membership=payload,
            )
        after = next(m for m in list_memberships_for_site(conn, "other-site") if m.employee_id == employee)
        assert after == before
    else:
        from rota.persistence.site_profile_repository import get_site_profile

        payload = replace(state.profile, profile_id="other-profile", active=False)
        before = get_site_profile(conn, "other-profile")
        with pytest.raises(InvalidCoordinatorContext):
            durable_inputs.update_site_profile(
                conn, coordinator_id="COORD-1", site_id=site_1, profile=payload,
            )
        assert get_site_profile(conn, "other-profile") == before


@pytest.mark.parametrize("operation", ["select", "revalidate"])
def test_r4_every_coordinator_write_requires_active_context(tmp_path, operation):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-write-{operation}", month=MONTH, seed=710)
    result = plan_ops.plan_month(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH,
    )
    if operation == "revalidate":
        plan_ops.select_candidate(conn, site_id=state.site.site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")
    save_coordinator(conn, Coordinator("COORD-1", "Coord", False))
    with pytest.raises(InvalidCoordinatorContext):
        if operation == "select":
            plan_ops.select_candidate(conn, site_id=state.site.site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")
        else:
            lifecycle_ops.revalidate(conn, site_id=state.site.site_id, month=MONTH)


# Prepared-snapshot invariant: when a candidate child is validated, the durable
# parent cannot simultaneously enter REST/LOAD context as if it were other work.
def test_r4_prepared_manual_child_does_not_duplicate_current_parent(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-manual", month=MONTH, seed=702)
    v1 = _plan_select(conn, state.site.site_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = replace(snapshot.assignments[0], frozen=True)
    child = manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), upsert_assignments=[target],
    )
    assert not any(d.source_reference in {"REST-01", "LOAD-01"} for d in get_schedule_snapshot(conn, child.version_id).deviations)


def test_r4_assembler_honors_explicit_noncurrent_version(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-version", month=MONTH, seed=711)
    v1 = _plan_select(conn, state.site.site_id)
    first = get_schedule_snapshot(conn, v1.version_id).assignments[0]
    cancelled = replace(first, state=AssignmentState.CANCELLED)
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), upsert_assignments=[cancelled],
    )
    assert get_current_version_id(conn, state.site.site_id, MONTH) == v2.version_id
    requested, _ = assemble_planning_state(
        conn, site_id=state.site.site_id, month=MONTH, schedule_version_id=v1.version_id,
    )
    assert requested.schedule_version_id == v1.version_id
    assert next(a for a in requested.existing_assignments if a.assignment_id == first.assignment_id).state == AssignmentState.PLANNED


# Precheck invariant: already-fixed coverage consumes demand capacity. It must
# not report a shortage merely because no additional employee can cover a
# demand that is already fully covered.
def test_r4_precheck_respects_existing_full_coverage(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-precheck", month=MONTH, seed=703)
    _plan_select(conn, state.site.site_id)
    assembled, _ = assemble_planning_state(conn, site_id=state.site.site_id, month=MONTH)
    target = replace(assembled.existing_assignments[0], state=AssignmentState.REALIZED)
    manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), upsert_assignments=[target],
    )
    for employee in assembled.employees:
        durable_inputs.append_availability(
            conn, coordinator_id="COORD-1", site_id=state.site.site_id,
            availability_id=f"block-{employee.employee_id}", employee_id=employee.employee_id,
            kind=AvailabilityKind.UNAVAILABLE_24H, start_date=target.start_datetime.date(),
            end_date=target.start_datetime.date(), active=True,
        )
    refreshed, _ = assemble_planning_state(conn, site_id=state.site.site_id, month=MONTH)
    from rota.application.precheck import precheck
    result = precheck(refreshed)
    assert target.covers_demand_id not in result.under_covered_demand_ids


@pytest.mark.parametrize("operation", ["first-plan", "przelicz-plan"])
def test_r4_planning_failure_leaves_prior_version_aggregate_intact(tmp_path, operation):
    """ROTA-T057 (OWNER_RULING 2026-09-06): REPLAN only exists pre-
    acceptance; the post-acceptance atomicity case (was "replan", calling
    plan_ops.replan on an already-accepted month) now exercises Przelicz
    Plan (plan_ops.plan_month) instead, since that is the only solver-
    driven operation left once a version is accepted. Same invariant under
    test either way: a mid-operation failure leaves the prior aggregate
    untouched."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-first-plan", month=MONTH, seed=712)
    if operation == "przelicz-plan":
        _plan_select(conn, state.site.site_id)
    before_current = get_current_version_id(conn, state.site.site_id, MONTH)
    before_count = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    conn.execute("DELETE FROM calendar_days WHERE date = ?", (date(2026, 8, 15).isoformat(),))
    with pytest.raises(IncompleteCalendarData):
        if operation == "first-plan":
            plan_ops.plan_month(
                conn, site_id=state.site.site_id, month=MONTH,
                coordinator_id="COORD-1", effective_from=MONTH,
            )
        else:
            plan_ops.plan_month(
                conn, site_id=state.site.site_id, month=MONTH,
                coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
            )
    assert get_current_version_id(conn, state.site.site_id, MONTH) == before_current
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == before_count


# FINALIZE atomicity invariant: an invalid acknowledgement request must not
# persist the preceding revalidation or otherwise change the aggregate.
def test_r4_finalize_rejection_leaves_working_snapshot_unchanged(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-finalize", month=MONTH, seed=704)
    version = _plan_select(conn, state.site.site_id)
    first = get_schedule_snapshot(conn, version.version_id).assignments[0]
    durable_inputs.append_availability(
        conn, coordinator_id="COORD-1", site_id=state.site.site_id,
        availability_id="fresh-finalize-conflict", employee_id=first.employee_id,
        kind=AvailabilityKind.UNAVAILABLE_24H, start_date=first.start_datetime.date(),
        end_date=first.start_datetime.date(), active=True,
    )
    before = get_schedule_snapshot(conn, version.version_id)
    with pytest.raises(ValueError):
        lifecycle_ops.finalize(
            conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
            acknowledged_deviation_ids={"not-current"},
        )
    assert get_schedule_snapshot(conn, version.version_id) == before


def test_r4_finalize_storage_failure_rolls_back_acknowledgement(tmp_path, monkeypatch):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-finalize-2", month=MONTH, seed=7042)
    version = _plan_select(conn, state.site.site_id)
    first = get_schedule_snapshot(conn, version.version_id).assignments[0]
    durable_inputs.append_availability(
        conn, coordinator_id="COORD-1", site_id=state.site.site_id,
        availability_id="fresh-finalize-conflict-2", employee_id=first.employee_id,
        kind=AvailabilityKind.UNAVAILABLE_24H, start_date=first.start_datetime.date(),
        end_date=first.start_datetime.date(), active=True,
    )
    lifecycle_ops.revalidate(conn, site_id=state.site.site_id, month=MONTH)
    before = get_schedule_snapshot(conn, version.version_id)
    ids = {d.deviation_id for d in before.deviations}

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("final status write failed")

    monkeypatch.setattr(lifecycle_ops.lifecycle, "finalize_schedule_version", boom)
    with pytest.raises(sqlite3.OperationalError):
        lifecycle_ops.finalize(
            conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
            acknowledged_deviation_ids=ids,
        )
    assert get_schedule_snapshot(conn, version.version_id) == before


# Training is one coordinator write: the schedule child and derived readiness
# update must commit or roll back together.
def test_r4_training_readiness_failure_rolls_back_schedule_child(tmp_path, monkeypatch):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-training", month=MONTH, seed=705)
    version = _plan_select(conn, state.site.site_id)
    save_site_profile(conn, replace(state.profile, training_s_default_readiness_threshold=1))
    snapshot = get_schedule_snapshot(conn, version.version_id)
    mentor = next(a for a in snapshot.assignments if a.role == AssignmentRole.PRIMARY)
    trainee_id = next(e.employee_id for e in state.employees if e.employee_id != mentor.employee_id)
    trainee_membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id)
        if m.employee_id == trainee_id
    )
    save_site_membership(conn, replace(
        trainee_membership,
        readiness_state=ReadinessState.NOT_READY,
        readiness_source=ReadinessSource.DEFAULT,
    ))
    trainee = Assignment(
        "audit-trainee", "", trainee_id, mentor.start_datetime, mentor.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor.assignment_id,
    )
    before_current = get_current_version_id(conn, state.site.site_id, MONTH)
    before_count = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("readiness write failed")

    monkeypatch.setattr(training, "save_site_membership", boom)
    with pytest.raises(sqlite3.OperationalError):
        training.mark_training_realized(
            conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2), trainee_assignment=trainee,
        )
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == before_count
    assert get_current_version_id(conn, state.site.site_id, MONTH) == before_current


@pytest.mark.parametrize(
    "role,state_value",
    [(AssignmentRole.PRIMARY, AssignmentState.REALIZED), (AssignmentRole.TRAINEE, AssignmentState.PLANNED)],
)
def test_r4_mark_training_realized_rejects_nonqualifying_assignment(tmp_path, role, state_value):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-training-shape", month=MONTH, seed=713)
    version = _plan_select(conn, state.site.site_id)
    mentor = get_schedule_snapshot(conn, version.version_id).assignments[0]
    trainee_id = next(e.employee_id for e in state.employees if e.employee_id != mentor.employee_id)
    trainee_membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id)
        if m.employee_id == trainee_id
    )
    save_site_membership(conn, replace(
        trainee_membership,
        readiness_state=ReadinessState.NOT_READY,
        readiness_source=ReadinessSource.DEFAULT,
    ))
    supplied = Assignment(
        "not-qualifying-training", "", trainee_id, mentor.start_datetime, mentor.end_datetime,
        role, state_value, False,
        mentor.covers_demand_id if role == AssignmentRole.PRIMARY else None,
        None if role == AssignmentRole.PRIMARY else mentor.assignment_id,
    )
    before = get_current_version_id(conn, state.site.site_id, MONTH)
    with pytest.raises(ValueError):
        training.mark_training_realized(
            conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2), trainee_assignment=supplied,
        )
    assert get_current_version_id(conn, state.site.site_id, MONTH) == before


@pytest.mark.parametrize("restriction", ["disabled", "weekday-only"])
def test_r4_mark_training_realized_enforces_profile_qualification(tmp_path, restriction):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-training-{restriction}", month=MONTH, seed=716)
    version = _plan_select(conn, state.site.site_id)
    snapshot = get_schedule_snapshot(conn, version.version_id)
    if restriction == "disabled":
        save_site_profile(conn, replace(
            state.profile, training_s_enabled=False, training_s_default_readiness_threshold=1,
        ))
        mentor = next(a for a in snapshot.assignments if a.role == AssignmentRole.PRIMARY)
    else:
        save_site_profile(conn, replace(
            state.profile, training_s_enabled=True, training_s_weekdays_only=True,
            training_s_default_readiness_threshold=1,
        ))
        mentor = next(
            a for a in snapshot.assignments
            if a.role == AssignmentRole.PRIMARY and a.start_datetime.weekday() >= 5
        )
    trainee_id = next(e.employee_id for e in state.employees if e.employee_id != mentor.employee_id)
    trainee_membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id)
        if m.employee_id == trainee_id
    )
    save_site_membership(conn, replace(
        trainee_membership,
        readiness_state=ReadinessState.NOT_READY,
        readiness_source=ReadinessSource.DEFAULT,
    ))
    supplied = Assignment(
        f"training-{restriction}", "", trainee_id, mentor.start_datetime, mentor.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor.assignment_id,
    )
    training.mark_training_realized(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), trainee_assignment=supplied,
    )
    updated = next(
        m for m in list_memberships_for_site(conn, state.site.site_id)
        if m.employee_id == trainee_id
    )
    assert updated.readiness_state != ReadinessState.READY_FOR_PRIMARY


@pytest.mark.parametrize("operation", ["first-plan", "replan"])
@pytest.mark.parametrize("bad_value", [None, datetime(2026, 8, 2, 9, 30)])
def test_r4_new_versions_require_a_real_date_effective_from(tmp_path, operation, bad_value):
    """ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT: the "manual" case was dropped
    from this parametrization -- apply_manual_correction no longer accepts a
    caller-supplied effective_from for an ordinary correction at all (the
    backend always computes it itself; section 1/6), so a bad client value
    is no longer even looked at, let alone rejected with TypeError/ValueError.
    plan_month/replan are untouched by that Task and keep this exact
    contract."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-date-{operation}", month=MONTH, seed=714)
    version = None if operation == "first-plan" else _plan_select(conn, state.site.site_id)
    before_count = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    with pytest.raises((TypeError, ValueError)):
        if operation == "first-plan":
            plan_ops.plan_month(
                conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
                effective_from=bad_value,  # type: ignore[arg-type]
            )
        else:
            plan_ops.replan(
                conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
                effective_from=bad_value,  # type: ignore[arg-type]
            )
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == before_count
    assert get_current_version_id(conn, state.site.site_id, MONTH) == (
        None if version is None else version.version_id
    )


def test_r4_open_month_returns_current_availability(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-open", month=MONTH, seed=715)
    employee_id = state.employees[0].employee_id
    durable_inputs.append_availability(
        conn, coordinator_id="COORD-1", site_id=state.site.site_id,
        availability_id="open-visible", employee_id=employee_id,
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 11), active=True,
    )
    expected = get_current_availability_for_employee(conn, employee_id)
    view = open_month.open_month(conn, site_id=state.site.site_id, month=MONTH)
    assert hasattr(view, "availability_records")
    assert {r.availability_version_id for r in view.availability_records} >= {
        r.availability_version_id for r in expected
    }


def test_r4_profile_demand_generation_keeps_distinct_occurrence_per_configured_shift():
    duplicate_kind = SiteProfile(
        profile_id="two-day-shifts",
        display_name="Two day shifts",
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(5), time(13), False, 1),
            StandardShift(ShiftKind.D, time(13), time(21), False, 1),
        ],
        day_only_blocks_n=True,
        external_support_enabled=True,
        training_s_enabled=True,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=3,
        rolling_7d_decision_threshold_hours=60,
    )
    demands = generate_profile_demands(duplicate_kind, date(2027, 2, 1))
    assert len(demands) == 56
    assert len({d.demand_id for d in demands}) == 56


def test_r4_assembler_excludes_inactive_availability_from_planning_state(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-inactive-availability", month=MONTH, seed=717)
    employee_id = state.employees[0].employee_id
    durable_inputs.append_availability(
        conn, coordinator_id="COORD-1", site_id=state.site.site_id,
        availability_id="inactive-input", employee_id=employee_id,
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 11), active=False,
    )
    assembled, _ = assemble_planning_state(conn, site_id=state.site.site_id, month=MONTH)
    assert not any(r.availability_id == "inactive-input" for r in assembled.availability_records)


def test_r4_holiday_history_does_not_double_count_current_realized_assignment(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-holiday-history", month=MONTH, seed=718)
    version = _plan_select(conn, state.site.site_id)
    target = get_schedule_snapshot(conn, version.version_id).assignments[0]
    save_calendar_day(conn, CalendarDay(target.start_datetime.date(), True))
    realized = replace(target, state=AssignmentState.REALIZED)
    manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), upsert_assignments=[realized],
    )
    assembled, _ = assemble_planning_state(conn, site_id=state.site.site_id, month=MONTH)
    from rota.planning.solver import _base_holiday_hours

    hours = _base_holiday_hours(assembled, {target.start_datetime.date()})
    assert hours[target.employee_id] == pytest.approx(
        (target.end_datetime - target.start_datetime).total_seconds() / 3600
    )


# Cross-demand geometry does not relax Assignment referential integrity: a
# long interval may contribute geometrically to adjacent demands, but its
# explicit covers_demand_id must still resolve in the version.
def test_r4_cross_demand_assignment_still_requires_real_demand_reference(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-coverage", month=MONTH, seed=706)
    version = _plan_select(conn, state.site.site_id)
    snapshot = get_schedule_snapshot(conn, version.version_id)
    first = snapshot.assignments[0]
    invalid = replace(first, covers_demand_id="nonexistent-demand")
    before = get_current_version_id(conn, state.site.site_id, MONTH)
    with pytest.raises(Exception):
        manual_edit.apply_manual_correction(
            conn, site_id=state.site.site_id, month=MONTH, coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2), upsert_assignments=[invalid],
        )
    assert get_current_version_id(conn, state.site.site_id, MONTH) == before


@pytest.mark.parametrize("bypass", ["availability", "day-only", "external-window"])
def test_r4_select_candidate_does_not_trust_caller_fabricated_realized(tmp_path, bypass):
    """ROTA-T057 (BOARD.md OWNER_RULING 2026-09-06): PLAN/REPLAN never
    create a ScheduleVersion before first acceptance -- there is no longer
    an "empty WORKING version" placeholder for select_candidate to have
    populated before validation. A rejected select_candidate on a fresh
    month therefore leaves no current version at all (None), not an empty
    one; updated from asserting an empty snapshot to asserting no version
    exists."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-realized-{bypass}", month=MONTH, seed=720)
    result = plan_ops.plan_month(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", effective_from=MONTH,
    )
    candidate = list(result.candidates[0])
    if bypass == "availability":
        target = candidate[0]
        durable_inputs.append_availability(
            conn, coordinator_id="COORD-1", site_id=state.site.site_id,
            availability_id="candidate-unavailable", employee_id=target.employee_id,
            kind=AvailabilityKind.UNAVAILABLE_24H,
            start_date=target.start_datetime.date(), end_date=target.start_datetime.date(), active=True,
        )
        candidate[0] = replace(target, state=AssignmentState.REALIZED)
    elif bypass == "day-only":
        target = next(a for a in candidate if a.covers_demand_id.endswith("-N"))
        employee = next(e for e in state.employees if e.employee_id == target.employee_id)
        durable_inputs.update_employee(
            conn, coordinator_id="COORD-1", site_id=state.site.site_id,
            employee=replace(employee, day_only=True),
        )
        candidate = [
            replace(a, state=AssignmentState.REALIZED)
            if a.employee_id == employee.employee_id and a.covers_demand_id.endswith("-N") else a
            for a in candidate
        ]
    else:
        target = candidate[0]
        candidate[0] = replace(target, employee_id="X", state=AssignmentState.REALIZED)

    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(
            conn, site_id=state.site.site_id, month=MONTH, candidate=candidate, coordinator_id="COORD-1",
        )
    assert get_current_version_id(conn, state.site.site_id, MONTH) is None


def test_r4_application_package_contains_no_sql_or_table_names():
    application_root = __import__("pathlib").Path(__file__).resolve().parents[1] / "rota" / "application"
    offenders = []
    for path in application_root.glob("*.py"):
        source = path.read_text(encoding="utf-8").upper()
        if "CONN.EXECUTE(" in source:
            offenders.append(path.name)
    assert offenders == []
