from datetime import date

from api.routers.schedule import get_month
from rota.application import plan_ops, store
from rota.planning.engine_types import PlanningResult
from rota.persistence import plan_preview_repository
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


def test_af1_non_feasible_result_clears_stale_preview(tmp_path):
    """Architect A-F1: a new PLAN/REPLAN that does NOT end FEASIBLE must
    remove any stale preview left by a prior FEASIBLE run, not just leave
    it in place for a later GET/reload to resurrect."""
    site_id = "SITE-T054-AF1"
    conn = _open_real_site(tmp_path, site_id=site_id)

    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    non_feasible = PlanningResult(
        status="TECHNICAL_ERROR",
        candidates=[],
        decision_payload=None,
        error_message="synthetic audit failure",
        warnings=[],
    )
    plan_ops._persist_plan_preview(
        conn,
        site_id=site_id,
        month=MONTH,
        schedule_version_id="irrelevant-for-this-branch",
        result=non_feasible,
        operation_kind="plan",
    )
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is None

    view = get_month(site_id, MONTH, conn)
    assert view.plan_preview is None
    conn.close()


def test_af2_wide_search_operation_kind_survives_persist_and_reload(tmp_path):
    """Architect A-F2: replan_wider_search's preview must record
    'replan_wide' (not the old coarse 'replan'), and a fresh connection
    (simulating reload) must still read it back as 'replan_wide' -- so
    the frontend's lastWideSearch reconstruction dispatches "Szukaj
    dalej" to the wide continuation, not a narrow retry."""
    site_id = "SITE-T054-AF2"
    db_path = tmp_path / f"{site_id}.db"
    conn = _open_real_site(tmp_path, site_id=site_id)

    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    plan_ops.select_candidate(
        conn, site_id=site_id, month=MONTH, candidate=first.candidates[0], coordinator_id=COORD,
    )

    narrow = plan_ops.replan(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert narrow.status == "FEASIBLE"
    narrow_preview = plan_preview_repository.get_plan_preview(conn, site_id, MONTH)
    assert narrow_preview is not None
    assert narrow_preview.operation_kind == "replan_narrow"

    wide = plan_ops.replan_wider_search(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD,
    )
    assert wide.status == "FEASIBLE"
    wide_preview = plan_preview_repository.get_plan_preview(conn, site_id, MONTH)
    assert wide_preview is not None
    assert wide_preview.operation_kind == "replan_wide"

    conn.close()
    conn = store.open_store(db_path)
    view = get_month(site_id, MONTH, conn)
    assert view.plan_preview is not None
    assert view.plan_preview.operation_kind == "replan_wide"
    conn.close()
