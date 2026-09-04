from datetime import date

from api.routers.schedule import get_month
from rota.application import durable_inputs, plan_ops, store
from rota.domain import MembershipKind, ReadinessSource, ReadinessState, SiteMembership
from rota.planning.engine_types import PlanningResult
from rota.persistence import plan_preview_repository
from tests.test_t047_print_export import _profile_d2_4h
from tests.test_vertical_full_stack import COORD, _bootstrap


MONTH = date(2026, 11, 1)


def _site(tmp_path, site_id: str):
    conn = store.open_store(tmp_path / f"{site_id}.db")
    employees = (f"{site_id}-E1", f"{site_id}-E2")
    _bootstrap(
        conn,
        site_id=site_id,
        profile_id=f"PROFILE-{site_id}",
        profile=_profile_d2_4h(f"PROFILE-{site_id}"),
        employees=employees,
        month=MONTH,
    )
    return conn, employees


def _disable_local_roster(conn, site_id: str, employees: tuple[str, ...]):
    for employee_id in employees:
        durable_inputs.update_membership(
            conn,
            coordinator_id=COORD,
            site_id=site_id,
            membership=SiteMembership(
                employee_id,
                site_id,
                MembershipKind.LOCAL,
                False,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
            ),
        )


def test_real_second_plan_non_feasible_removes_previous_preview(tmp_path):
    site_id = "SITE-T054-R5-NONFEASIBLE"
    conn, employees = _site(tmp_path, site_id)
    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    _disable_local_roster(conn, site_id, employees)
    second = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD)
    assert second.status == "DECISION_REQUIRED"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is None
    assert get_month(site_id, MONTH, conn).plan_preview is None
    conn.close()


def test_failed_replacement_delete_must_not_silently_resurrect_old_preview(tmp_path):
    site_id = "SITE-T054-R5-DELETE-FAILURE"
    conn, employees = _site(tmp_path, site_id)
    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    conn.execute(
        """CREATE TRIGGER reject_t054_preview_delete
           BEFORE DELETE ON plan_previews
           BEGIN SELECT RAISE(ABORT, 'audit preview delete failure'); END"""
    )
    conn.commit()
    _disable_local_roster(conn, site_id, employees)

    second = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id=COORD)
    assert second.status == "DECISION_REQUIRED"
    view = get_month(site_id, MONTH, conn)
    assert {
        "failure_reported": any("PLAN_PREVIEW" in warning for warning in second.warnings),
        "old_preview_hidden": view.plan_preview is None,
    } == {"failure_reported": True, "old_preview_hidden": True}
    conn.close()


def test_failed_cleanup_is_hidden_for_non_feasible_result_without_decision_readback(tmp_path):
    """A-F1 also owns TECHNICAL_ERROR/search outcomes, which have no DR readback."""
    site_id = "SITE-T054-R5-NO-READBACK"
    conn, _ = _site(tmp_path, site_id)
    first = plan_ops.plan_month(
        conn, site_id=site_id, month=MONTH, coordinator_id=COORD, effective_from=MONTH
    )
    assert first.status == "FEASIBLE"
    assert plan_preview_repository.get_plan_preview(conn, site_id, MONTH) is not None

    conn.execute(
        """CREATE TRIGGER reject_t054_preview_delete_without_readback
           BEFORE DELETE ON plan_previews
           BEGIN SELECT RAISE(ABORT, 'audit preview delete failure'); END"""
    )
    conn.commit()
    failed_attempt = PlanningResult(
        status="TECHNICAL_ERROR",
        candidates=[],
        decision_payload=None,
        error_message="audit technical failure",
        warnings=[],
    )
    result = plan_ops._persist_plan_preview(
        conn,
        site_id=site_id,
        month=MONTH,
        schedule_version_id="same-working-version",
        result=failed_attempt,
        operation_kind="plan",
    )
    view = get_month(site_id, MONTH, conn)
    assert {
        "failure_reported": any("PLAN_PREVIEW_CLEANUP_FAILED" in warning for warning in result.warnings),
        "old_preview_hidden": view.plan_preview is None,
    } == {"failure_reported": True, "old_preview_hidden": True}
    conn.close()
