"""Codex audit R6: generalized regressions for the R5 repair delta."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from rota.application import manual_edit, plan_ops, training
from rota.domain import Assignment, AssignmentRole, AssignmentState, ReadinessSource, ReadinessState
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_site_membership
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.planning.engine_types import PlanningResult
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_and_select(conn, site_id: str, month: date = MONTH):
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=month, coordinator_id="COORD-1", effective_from=month,
    )
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(
        conn, site_id=site_id, month=month, coordinator_id="COORD-1", candidate=result.candidates[0],
    )


@pytest.mark.parametrize("operation", ["initial-plan", "replan"])
def test_r6_engine_state_names_the_current_version_it_is_planning(tmp_path, monkeypatch, operation):
    """The canonical assembler result must carry the exact target version id."""
    conn = connect(tmp_path / "rota.db")
    state = seed_real_object(conn, case_id=f"audit-r6-state-{operation}", month=MONTH, seed=901)
    captured = []

    def capture(planning_state, *_args, **_kwargs):
        captured.append(planning_state)
        return PlanningResult("TECHNICAL_ERROR", [], None, "audit stop", [])

    monkeypatch.setattr(plan_ops, "plan", capture)
    # ROTA-T033: REPLAN now calls plan_requiring_different_result_narrow
    # (owner decision 2026-08-26, REPLAN must never hand back the same
    # schedule), not plan() -- the audit's own capture must intercept
    # whichever one the exercised operation actually uses.
    monkeypatch.setattr(plan_ops, "plan_requiring_different_result_narrow", capture)
    if operation == "initial-plan":
        plan_ops.plan_month(
            conn, site_id=state.site.site_id, month=MONTH,
            coordinator_id="COORD-1", effective_from=MONTH,
        )
    else:
        # Establish a parent without relying on a solver result, then audit
        # which version the explicit REPLAN passes to PlanningEngine.
        plan_ops.plan_month(
            conn, site_id=state.site.site_id, month=MONTH,
            coordinator_id="COORD-1", effective_from=MONTH,
        )
        captured.clear()
        plan_ops.replan(
            conn, site_id=state.site.site_id, month=MONTH,
            coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        )

    # ROTA-T057 (T57-01): plan()/plan_requiring_different_result_narrow is
    # mocked to fail before ever producing a FEASIBLE result to accept, so
    # under the new contract NO ScheduleVersion is ever created here (PLAN
    # and pre-acceptance REPLAN both stay preview-only) -- current_id is
    # correctly None for both parametrizations. What this test can still
    # verify: the ephemeral placeholder id handed to the solver is
    # non-empty and consistently shared between the state and its demands
    # (R6-1's original concern). The "matches a real, already-accepted
    # current_id" case is exercised by tests that DO select a candidate
    # first (e.g. test_t041_checkpoint_b.py's catalog-change scenario).
    assert get_current_version_id(conn, state.site.site_id, MONTH) is None
    assert len(captured) == 1
    version_id = captured[0].schedule_version_id
    assert version_id
    assert all(d.schedule_version_id == version_id for d in captured[0].shift_demands)


@pytest.mark.parametrize("fixed_kind", ["frozen", "realized", "trainee"])
def test_r6_replan_candidate_with_fixed_facts_can_be_selected(tmp_path, fixed_kind, monkeypatch):
    """All T006 fixed-fact branches must survive the new child identity.

    ROTA-T023 Checkpoint B (owner-authorized narrow TASK_SCOPE amendment,
    2026-08-22): the "trainee" case alone runs in a deterministic future
    month. MONTH (2026-08) is already elapsed relative to real wall-clock
    "now", so select_candidate's R5-3 cutover_at (captured at call time) is
    later than every shift in MONTH -- the solver's ordinary, unprotected
    redistribution of the non-fixed PRIMARY it swaps for the TRAINEE's
    mentor then spuriously trips the pre-cutover-PRIMARY guard. A future
    month keeps every shift after cutover_at, matching what R5-3 actually
    protects (accepted-plan facts, not merely elapsed ones).

    ROTA-T057 follow-up (2026-09-07): Przelicz Plan (plan_month on the
    existing current version) now also requires the grafik to already be
    live (OWNER_RULING point 3) -- a future month is otherwise never live,
    so "now" is frozen to just after the month's own first shift start for
    the trainee case only, making it live while keeping cutover_at early
    enough that it protects only that first shift, avoiding the original
    elapsed-month bug this comment describes."""
    conn = connect(tmp_path / "rota.db")
    month = date(2027, 2, 1) if fixed_kind == "trainee" else MONTH
    correction_effective_from = date(month.year, month.month, 2)
    state = seed_real_object(conn, case_id=f"audit-r6-fixed-{fixed_kind}", month=month, seed=902)
    selected = _plan_and_select(conn, state.site.site_id, month)
    snapshot = get_schedule_snapshot(conn, selected.version_id)
    mentor = snapshot.assignments[0]

    if fixed_kind == "trainee":
        fixed_now = min(a.start_datetime for a in snapshot.assignments) + timedelta(minutes=1)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        monkeypatch.setattr(plan_ops, "datetime", _FixedDateTime)

    if fixed_kind == "frozen":
        upsert = [replace(mentor, frozen=True)]
    elif fixed_kind == "realized":
        upsert = [replace(mentor, state=AssignmentState.REALIZED)]
    else:
        trainee_employee = next(e.employee_id for e in state.employees if e.employee_id != mentor.employee_id)
        upsert = [Assignment(
            "audit-r6-trainee", selected.version_id, trainee_employee,
            mentor.start_datetime, mentor.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, mentor.assignment_id,
        )]

    manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=month, coordinator_id="COORD-1",
        effective_from=correction_effective_from, upsert_assignments=upsert,
    )
    # ROTA-T057: REPLAN no longer exists once anything has been accepted --
    # Przelicz Plan (plan_month on the existing current) is the recompute now.
    replanned = plan_ops.plan_month(conn, site_id=state.site.site_id, month=month, coordinator_id="COORD-1")
    assert replanned.status == "FEASIBLE"
    plan_ops.select_candidate(
        conn, site_id=state.site.site_id, month=month,
        coordinator_id="COORD-1", candidate=replanned.candidates[0],
    )


def _prepare_training_month(conn, month: date, seed: int, trainee_id: str | None = None):
    state = seed_real_object(conn, case_id=f"audit-r6-training-{month}", month=month, seed=seed)
    save_site_profile(conn, replace(
        state.profile, training_s_enabled=True, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=2,
    ))
    version = _plan_and_select(conn, state.site.site_id, month)
    assignments = get_schedule_snapshot(conn, version.version_id).assignments
    if trainee_id is None:
        trainee_id = state.employees[0].employee_id
    membership = next(m for m in list_memberships_for_site(conn, state.site.site_id) if m.employee_id == trainee_id)
    save_site_membership(conn, replace(
        membership, readiness_state=ReadinessState.NOT_READY, readiness_source=ReadinessSource.DEFAULT,
    ))
    mentor = next(a for a in assignments if a.role == AssignmentRole.PRIMARY and a.employee_id != trainee_id)
    return state, trainee_id, mentor


def test_r6_distinct_trainings_with_same_local_id_in_different_versions_both_count(tmp_path):
    """T008 identity is (schedule_version_id, assignment_id), not bare id."""
    conn = connect(tmp_path / "rota.db")
    august, trainee_id, mentor_1 = _prepare_training_month(conn, MONTH, 904)
    training.mark_training_realized(
        conn, site_id=august.site.site_id, month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2),
        trainee_assignment=Assignment(
            "reusable-local-id", "", trainee_id, mentor_1.start_datetime, mentor_1.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor_1.assignment_id,
        ),
    )

    september_month = date(2026, 9, 1)
    september, _, mentor_2 = _prepare_training_month(conn, september_month, 905, trainee_id)
    training.mark_training_realized(
        conn, site_id=september.site.site_id, month=september_month, coordinator_id="COORD-1",
        effective_from=date(2026, 9, 2),
        trainee_assignment=Assignment(
            "reusable-local-id", "", trainee_id, mentor_2.start_datetime, mentor_2.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor_2.assignment_id,
        ),
    )

    membership = next(
        m for m in list_memberships_for_site(conn, september.site.site_id) if m.employee_id == trainee_id
    )
    assert membership.readiness_state == ReadinessState.READY_FOR_PRIMARY


def test_r6_training_is_not_persisted_as_a_second_record_type(tmp_path):
    """Operation 9 freezes ordinary Assignment data and explicitly no TrainingRecord."""
    conn = connect(tmp_path / "rota.db")
    tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "training_readiness_credits" not in tables
