from dataclasses import replace
from datetime import date, datetime

from rota.application import manual_edit, memory_read
from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.site_memory_types import CoordinatorActionKind
from tests.support.t009_fixtures import seed_real_object


MONTH = date(2026, 8, 1)


def test_one_recorded_at_owns_future_correction_effective_date(monkeypatch):
    """H1/H2/brief section 3+6: one captured recorded_at owns the date."""
    conn = connect(":memory:")
    state = seed_real_object(conn, case_id="audit-r3-clock", month=MONTH, seed=915)
    from rota.application import plan_ops

    result = plan_ops.plan_month(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", effective_from=MONTH,
    )
    assert result.status == "FEASIBLE"
    current = plan_ops.select_candidate(
        conn, site_id=state.site.site_id, month=MONTH,
        candidate=result.candidates[0], coordinator_id="COORD-1",
    )
    target = get_schedule_snapshot(conn, current.version_id).assignments[0]

    # Exposes that the implementation's effective-date clock and action
    # recorded_at clock are two different captures/owners.
    monkeypatch.setattr(manual_edit, "_now", lambda: datetime(2000, 1, 1, 23, 59, 59))
    child = manual_edit.apply_manual_correction(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", upsert_assignments=[replace(target, frozen=not target.frozen)],
    )
    action = next(
        a for a in memory_read.material_action_history(conn)
        if a.action_kind == CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION
        and a.schedule_version_id == child.version_id
    )
    assert child.effective_from == action.recorded_at.date()


def test_recompute_after_historical_nn_preserves_the_recorded_fact(monkeypatch):
    """H10 + OWNER NN ruling: automatic work cannot erase a historical NN."""
    conn = connect(":memory:")
    state = seed_real_object(conn, case_id="audit-r3-nn-recompute", month=MONTH, seed=916)
    from rota.application import plan_ops

    first = plan_ops.plan_month(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", effective_from=MONTH,
    )
    assert first.status == "FEASIBLE"
    live = plan_ops.select_candidate(
        conn, site_id=state.site.site_id, month=MONTH,
        candidate=first.candidates[0], coordinator_id="COORD-1",
    )
    target = get_schedule_snapshot(conn, live.version_id).assignments[0]
    monkeypatch.setattr(manual_edit, "_now", lambda: target.start_datetime)
    with_nn = manual_edit.mark_not_worked(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", assignment_id=target.assignment_id,
    )
    saved_nn = next(
        a for a in get_schedule_snapshot(conn, with_nn.version_id).assignments
        if a.assignment_id == target.assignment_id
    )
    assert saved_nn.operational_code == "NN"

    recomputed = plan_ops.plan_month(
        conn, site_id=state.site.site_id, month=MONTH,
        coordinator_id="COORD-1", effective_from=target.start_datetime.date(),
    )
    assert recomputed.status == "FEASIBLE"
    accepted = plan_ops.select_candidate(
        conn, site_id=state.site.site_id, month=MONTH,
        candidate=recomputed.candidates[0], coordinator_id="COORD-1",
    )
    assert any(
        a.assignment_id == target.assignment_id and a.operational_code == "NN"
        for a in get_schedule_snapshot(conn, accepted.version_id).assignments
    )


def test_cutover_guard_rejects_rewriting_historical_nn_with_same_id():
    """Minimal H10 reproducer, independent of solver candidate selection."""
    start = datetime(2026, 8, 1, 6)
    historical_nn = Assignment(
        "A-NN", "SV-OLD", "EMP-1", start, datetime(2026, 8, 1, 18),
        AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, "D-1", None,
        operational_code="NN",
    )
    rewritten = replace(
        historical_nn, state=AssignmentState.PLANNED, operational_code=None,
        employee_id="EMP-2",
    )
    from rota.application.plan_ops import _replan_cutover_violations

    assert _replan_cutover_violations(
        (historical_nn,), [rewritten], datetime(2026, 8, 2),
    )
