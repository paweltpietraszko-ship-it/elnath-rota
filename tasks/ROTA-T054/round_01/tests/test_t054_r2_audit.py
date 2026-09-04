from datetime import date

import pytest

from api.routers.schedule import get_month
from rota.application import lifecycle_ops, plan_ops, store
from rota.application.assembler import assemble_planning_state
from rota.application.errors import CandidateRejected
from rota.persistence import plan_preview_repository
from rota.persistence.schedule_repository import get_current_schedule_snapshot, get_current_version_id
from tests.test_t047_print_export import _profile_d2_4h
from tests.test_vertical_full_stack import COORD, _bootstrap


MONTH = date(2026, 11, 1)


def _open_real_site(tmp_path, *, site_id: str):
    conn = store.open_store(tmp_path / f"{site_id}.db")
    _bootstrap(
        conn,
        site_id=site_id,
        profile_id=f"PROFILE-{site_id}",
        profile=_profile_d2_4h(f"PROFILE-{site_id}"),
        employees=(f"{site_id}-E1", f"{site_id}-E2"),
        month=MONTH,
    )
    return conn


def test_real_plan_preview_roundtrip_reject_and_select_lifecycle(tmp_path):
    """T54-01/04/05 through real SQLite -> assembler -> solver -> validator."""
    site_id = "SITE-T054-AUDIT-LIFECYCLE"
    db_path = tmp_path / f"{site_id}.db"
    conn = _open_real_site(tmp_path, site_id=site_id)

    result = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert result.status == "FEASIBLE"
    before_version = get_current_version_id(conn, site_id, MONTH)
    before_history_count = conn.execute("SELECT count(*) FROM schedule_versions").fetchone()[0]
    persisted = plan_preview_repository.get_plan_preview(conn, site_id, MONTH)
    assert persisted is not None
    assert persisted.candidates == result.candidates
    assert persisted.warnings == result.warnings
    assert persisted.optimization_complete == result.optimization_complete

    conn.close()
    conn = store.open_store(db_path)
    reloaded = plan_preview_repository.get_plan_preview(conn, site_id, MONTH)
    assert reloaded == persisted

    plan_ops.reject_plan_preview(conn, site_id=site_id, month=MONTH, coordinator_id=COORD)
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is None
    assert get_current_version_id(conn, site_id, MONTH) == before_version
    assert conn.execute("SELECT count(*) FROM schedule_versions").fetchone()[0] == before_history_count

    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD)
    assert result.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None
    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(
            conn, site_id=site_id, month=MONTH, candidate=[], coordinator_id=COORD
        )
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    plan_ops.select_candidate(
        conn,
        site_id=site_id,
        month=MONTH,
        candidate=result.candidates[0],
        coordinator_id=COORD,
    )
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is None
    conn.close()


def test_final_version_never_surfaces_an_unaccepted_working_preview(tmp_path):
    """T54-08: preview is visible only while its current version is WORKING."""
    site_id = "SITE-T054-AUDIT-FINAL"
    conn = _open_real_site(tmp_path, site_id=site_id)

    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    plan_ops.select_candidate(
        conn,
        site_id=site_id,
        month=MONTH,
        candidate=first.candidates[0],
        coordinator_id=COORD,
    )

    second = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD)
    assert second.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    state, _ = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    acknowledged_ids = {deviation.deviation_id for deviation in state.deviations}
    finalized = lifecycle_ops.finalize(
        conn,
        site_id=site_id,
        month=MONTH,
        coordinator_id=COORD,
        acknowledged_deviation_ids=acknowledged_ids,
    )
    assert finalized.status.value.startswith("FINAL")

    month_view = get_month(site_id, MONTH, conn)
    assert month_view.current_version is not None
    assert month_view.current_version.status.startswith("FINAL")
    assert month_view.plan_preview is None
    conn.close()


def test_corrupt_preview_read_is_isolated_from_real_month_view(tmp_path):
    """T54-07: broken preview data cannot hide the current schedule."""
    site_id = "SITE-T054-AUDIT-READ"
    conn = _open_real_site(tmp_path, site_id=site_id)
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert result.status == "FEASIBLE"
    current_id = get_current_version_id(conn, site_id, MONTH)
    conn.execute(
        "UPDATE plan_previews SET candidates_json = ? WHERE site_id = ? AND month = ?",
        ("{invalid", site_id, MONTH.isoformat()),
    )
    conn.commit()

    month_view = get_month(site_id, MONTH, conn)
    assert month_view.current_version is not None
    assert month_view.current_version.version_id == current_id
    assert month_view.plan_preview is None
    assert month_view.plan_preview_error
    conn.close()


def test_preview_write_failure_keeps_candidate_transient_and_schedule_unchanged(tmp_path):
    """T54-06 through a real SQLite write failure, without mocking plan()."""
    site_id = "SITE-T054-AUDIT-WRITE"
    conn = _open_real_site(tmp_path, site_id=site_id)
    conn.execute(
        """CREATE TRIGGER reject_t054_preview_insert
           BEFORE INSERT ON plan_previews
           BEGIN SELECT RAISE(ABORT, 'audit preview write failure'); END"""
    )
    conn.commit()

    result = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert result.status == "FEASIBLE"
    assert result.candidates
    assert any("PLAN_PREVIEW_NOT_PERSISTED" in warning for warning in result.warnings)
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is None
    current = get_current_schedule_snapshot(conn, site_id, MONTH)
    assert current is not None
    assert list(current[1].assignments) == []
    conn.close()


def test_reloaded_replan_preview_retains_its_operation_family(tmp_path):
    """A reloaded REPLAN retry must not be dispatched as ordinary PLAN."""
    site_id = "SITE-T054-AUDIT-REPLAN-SOURCE"
    conn = _open_real_site(tmp_path, site_id=site_id)
    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    plan_ops.select_candidate(
        conn,
        site_id=site_id,
        month=MONTH,
        candidate=first.candidates[0],
        coordinator_id=COORD,
    )

    result = plan_ops.replan(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert result.status == "FEASIBLE"
    view = get_month(site_id, MONTH, conn)
    assert view.current_version is not None
    assert view.current_version.parent_version_id is not None
    assert view.plan_preview is not None
    # MonthlyPlanning must know that "Szukaj dalej" continues REPLAN.
    # Without this, its default planResultSource="plan" sends POST /plan.
    # A-F2 architect audit fix: operation_kind is now 3-way (plan/
    # replan_narrow/replan_wide) so a reload can also tell REPLAN's narrow
    # vs. wide stage apart -- replan() itself is the narrow stage.
    assert getattr(view.plan_preview, "operation_kind", None) == "replan_narrow"
    conn.close()
