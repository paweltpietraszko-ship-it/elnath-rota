"""Codex audit R5: sibling cases left open by the R4 fixes."""
from __future__ import annotations

import calendar
import sqlite3
from dataclasses import replace
from datetime import date

import pytest

from rota.application import manual_edit, plan_ops, training
from rota.application.assembler import assemble_planning_state
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    ReadinessSource,
    ReadinessState,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_site_membership
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.validator import ViolationDetail
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_select(conn, site_id: str):
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH,
    )
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0])


def _training_setup(conn, *, threshold: int, weekdays_only: bool):
    state = seed_real_object(conn, case_id="audit-r5-training", month=MONTH, seed=801)
    version = _plan_select(conn, state.site.site_id)
    save_site_profile(conn, replace(
        state.profile,
        training_s_enabled=True,
        training_s_weekdays_only=weekdays_only,
        training_s_default_readiness_threshold=threshold,
    ))
    assignments = get_schedule_snapshot(conn, version.version_id).assignments
    mentors = [a for a in assignments if a.role == AssignmentRole.PRIMARY]
    trainee_id = next(e.employee_id for e in state.employees if e.employee_id != mentors[0].employee_id)
    membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    save_site_membership(conn, replace(
        membership,
        readiness_state=ReadinessState.NOT_READY,
        readiness_source=ReadinessSource.DEFAULT,
    ))
    return state, mentors, trainee_id


def _trainee(label: str, trainee_id: str, mentor) -> Assignment:
    return Assignment(
        label, "", trainee_id, mentor.start_datetime, mentor.end_datetime,
        AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor.assignment_id,
    )


@pytest.mark.parametrize("mismatch", ["site", "month"])
def test_r5_explicit_version_must_belong_to_requested_context(tmp_path, mismatch):
    """The canonical key is the whole (site_id, month, version_id) tuple."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-r5-version-{mismatch}", month=MONTH, seed=802)
    version = _plan_select(conn, state.site.site_id)

    requested_site, requested_month = state.site.site_id, MONTH
    if mismatch == "site":
        other_profile = replace(state.profile, profile_id="r5-other-profile")
        save_site_profile(conn, other_profile)
        other_site = replace(
            state.site, site_id="r5-other-site", profile_id=other_profile.profile_id,
        )
        save_site(conn, other_site)
        save_coordinator(conn, Coordinator("R5-COORD", "R5", True))
        save_coordinator_site_association(conn, CoordinatorSiteAssociation("R5-COORD", other_site.site_id, True))
        for membership in state.memberships:
            save_site_membership(conn, replace(membership, site_id=other_site.site_id))
        requested_site = other_site.site_id
    else:
        requested_month = date(2026, 9, 1)
        days = calendar.monthrange(requested_month.year, requested_month.month)[1]
        for day in range(1, days + 1):
            save_calendar_day(conn, CalendarDay(date(2026, 9, day), False))

    with pytest.raises(Exception):
        assemble_planning_state(
            conn,
            site_id=requested_site,
            month=requested_month,
            schedule_version_id=version.version_id,
        )


def test_r5_explicit_noncurrent_target_month_does_not_reenter_as_boundary(tmp_path):
    """Current V2 of the target month is not surrounding context for explicit V1."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-r5-version-boundary", month=MONTH, seed=803)
    v1 = _plan_select(conn, state.site.site_id)
    first = get_schedule_snapshot(conn, v1.version_id).assignments[0]
    v2 = manual_edit.apply_manual_correction(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2),
        upsert_assignments=[replace(first, frozen=True)],
    )

    explicit, _ = assemble_planning_state(
        conn, site_id=state.site.site_id, month=MONTH, schedule_version_id=v1.version_id,
    )
    assert not any(a.schedule_version_id == v2.version_id for a in explicit.boundary_assignments)


def test_r5_nonqualifying_weekend_training_does_not_count_toward_threshold(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state, mentors, trainee_id = _training_setup(conn, threshold=2, weekdays_only=True)
    weekend = next(a for a in mentors if a.start_datetime.weekday() >= 5)
    weekday = next(a for a in mentors if a.start_datetime.weekday() < 5)

    training.mark_training_realized(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2),
        trainee_assignment=_trainee("r5-weekend", trainee_id, weekend),
    )
    training.mark_training_realized(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 3),
        trainee_assignment=_trainee("r5-weekday", trainee_id, weekday),
    )

    membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    assert membership.readiness_state == ReadinessState.NOT_READY


def test_r5_training_recorded_while_disabled_does_not_later_count_toward_threshold(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state, mentors, trainee_id = _training_setup(conn, threshold=2, weekdays_only=False)
    profile = state.profile
    save_site_profile(conn, replace(
        profile,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=2,
    ))
    training.mark_training_realized(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2),
        trainee_assignment=_trainee("r5-disabled", trainee_id, mentors[0]),
    )
    save_site_profile(conn, replace(
        profile,
        training_s_enabled=True,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=2,
    ))
    training.mark_training_realized(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 3),
        trainee_assignment=_trainee("r5-enabled", trainee_id, mentors[1]),
    )

    membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    assert membership.readiness_state == ReadinessState.NOT_READY


def test_r5_same_realized_training_cannot_increment_threshold_twice(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state, mentors, trainee_id = _training_setup(conn, threshold=2, weekdays_only=False)
    supplied = _trainee("r5-one-event", trainee_id, mentors[0])

    for effective_from in (date(2026, 8, 2), date(2026, 8, 3)):
        training.mark_training_realized(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-1",
            effective_from=effective_from,
            trainee_assignment=supplied,
        )

    membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    assert membership.readiness_state == ReadinessState.NOT_READY


def test_r5_training_failure_after_membership_write_rolls_back_whole_action(tmp_path, monkeypatch):
    """Fault injection after the helper write catches an accidental nested commit."""
    conn = connect(tmp_path / "rota.db")
    state, mentors, trainee_id = _training_setup(conn, threshold=1, weekdays_only=False)
    supplied = _trainee("r5-atomic", trainee_id, mentors[0])
    before_current = get_current_version_id(conn, state.site.site_id, MONTH)
    before_count = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    before_membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    original = training.save_site_membership

    def write_then_fail(open_conn, membership):
        original(open_conn, membership)
        raise sqlite3.OperationalError("failure after membership write")

    monkeypatch.setattr(training, "save_site_membership", write_then_fail)
    with pytest.raises(sqlite3.OperationalError):
        training.mark_training_realized(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2),
            trainee_assignment=supplied,
        )

    assert get_current_version_id(conn, state.site.site_id, MONTH) == before_current
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == before_count
    after_membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    assert after_membership == before_membership


def test_r5_invalid_mentor_training_does_not_promote_readiness(tmp_path):
    """A TRAINEE violating the frozen mentor invariant is not qualifying training."""
    conn = connect(tmp_path / "rota.db")
    state, mentors, trainee_id = _training_setup(conn, threshold=1, weekdays_only=False)
    supplied = replace(
        _trainee("r5-invalid-mentor", trainee_id, mentors[0]),
        mentor_primary_assignment_id="missing-primary",
    )

    with pytest.raises(Exception):
        training.mark_training_realized(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2),
            trainee_assignment=supplied,
        )

    membership = next(
        m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id
    )
    assert membership.readiness_state == ReadinessState.NOT_READY


@pytest.mark.parametrize("operation", ["first-plan", "replan"])
def test_r5_post_write_assembly_failure_leaves_prior_aggregate_intact(tmp_path, monkeypatch, operation):
    """R4-1 applies after every step, not only to the first dry-run read."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-r5-atomic-{operation}", month=MONTH, seed=804)
    if operation == "replan":
        _plan_select(conn, state.site.site_id)
    before_current = get_current_version_id(conn, state.site.site_id, MONTH)
    before_count = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    original = plan_ops.assemble_planning_state
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise sqlite3.OperationalError("post-write context read failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(plan_ops, "assemble_planning_state", fail_second)
    with pytest.raises(sqlite3.OperationalError):
        if operation == "first-plan":
            plan_ops.plan_month(
                conn,
                site_id=state.site.site_id,
                month=MONTH,
                coordinator_id="COORD-1",
                effective_from=MONTH,
            )
        else:
            plan_ops.replan(
                conn,
                site_id=state.site.site_id,
                month=MONTH,
                coordinator_id="COORD-1",
                effective_from=date(2026, 8, 2),
            )

    assert get_current_version_id(conn, state.site.site_id, MONTH) == before_current
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == before_count


@pytest.mark.parametrize("operation", ["select", "revalidate"])
def test_r5_write_requires_the_acting_coordinator_context(tmp_path, operation):
    """Authorization/provenance cannot be inferred from the version creator."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-r5-select-actor", month=MONTH, seed=805)
    result = plan_ops.plan_month(
        conn,
        site_id=state.site.site_id,
        month=MONTH,
        coordinator_id="COORD-1",
        effective_from=MONTH,
    )
    save_coordinator(conn, Coordinator("COORD-2", "Second", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-2", state.site.site_id, True))

    if operation == "select":
        selected = plan_ops.select_candidate(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-2",
            candidate=result.candidates[0],
        )
        assert selected.version_id == get_current_version_id(conn, state.site.site_id, MONTH)
    else:
        plan_ops.select_candidate(
            conn, site_id=state.site.site_id, month=MONTH, candidate=result.candidates[0],
        )
        from rota.application import lifecycle_ops

        updated = lifecycle_ops.revalidate(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-2",
        )
        assert updated.version_id == get_current_version_id(conn, state.site.site_id, MONTH)


@pytest.mark.parametrize("rule", ["ASSIGN", "ASSIGN-03/04"])
def test_r5_manual_structural_violation_fails_before_writing_a_child(tmp_path, monkeypatch, rule):
    """Unknown mappings fail closed, but must not leave a partial version."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-r5-structural-{rule}", month=MONTH, seed=806)
    version = _plan_select(conn, state.site.site_id)
    before = get_schedule_snapshot(conn, version.version_id)
    original_validate = manual_edit.validate

    def structural_report(planning_state, assignments):
        report = original_validate(planning_state, assignments)
        report.hard_pass = False
        report.violation_details = [ViolationDetail(rule, (assignments[0].assignment_id,), "structural")]
        return report

    monkeypatch.setattr(manual_edit, "validate", structural_report)
    with pytest.raises(Exception):
        manual_edit.apply_manual_correction(
            conn,
            site_id=state.site.site_id,
            month=MONTH,
            coordinator_id="COORD-1",
            effective_from=date(2026, 8, 2),
            upsert_assignments=[replace(before.assignments[0], frozen=True)],
        )
    assert get_current_version_id(conn, state.site.site_id, MONTH) == version.version_id
    assert get_schedule_snapshot(conn, version.version_id) == before


def test_r5_structured_rule_decision_requires_a_real_effective_date(tmp_path):
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id="audit-r5-rule-date", month=MONTH, seed=807)
    from datetime import datetime

    from rota.application import rule_decisions
    from rota.domain import RuleCategory, RuleEnforcement, RuleResolution
    from rota.site_memory_types import NewRuleContent

    content = NewRuleContent(
        category=RuleCategory.LOCAL_RULE,
        rule_kind=None,
        structured_parameters=None,
        enforcement=RuleEnforcement.SOFT,
        resolution_status=RuleResolution.RESOLVED,
        effective_to=None,
        description="test",
        source="audit",
        reason=None,
    )
    with pytest.raises((TypeError, ValueError)):
        rule_decisions.record_structured_rule_decision(
            conn,
            coordinator_id="COORD-1",
            site_id=state.site.site_id,
            rule_id="R5-RULE",
            statement="test",
            effective_from=datetime(2026, 8, 1, 12, 0),
            rule_content=content,
        )
    assert conn.execute("SELECT COUNT(*) FROM decision_records").fetchone()[0] == 0
