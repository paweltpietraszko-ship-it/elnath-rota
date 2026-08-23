"""ROTA-T010-D tests (tasks/ROTA-T010/part_d_nn.md): operational_code="NN"
on a previously PLANNED PRIMARY the employee did not work."""
from __future__ import annotations

from datetime import date, datetime

from rota.application import manual_edit, plan_ops
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.work_balance_repository import reconstruct_month_balance, save_work_balance_target
from tests.support.minimal_state import ReadinessSource, ReadinessState, base_profile
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_and_select(conn, site_id: str):
    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")


def test_nn_marks_cancelled_and_parent_unchanged(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="nn-1", month=MONTH, seed=400)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    v1_snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in v1_snapshot.assignments if a.role == AssignmentRole.PRIMARY)

    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    nn_assignment = next(a for a in v2_snapshot.assignments if a.assignment_id == target.assignment_id)
    assert nn_assignment.state == AssignmentState.CANCELLED
    assert nn_assignment.operational_code == "NN"

    parent_again = get_schedule_snapshot(conn, v1.version_id)
    original_again = next(a for a in parent_again.assignments if a.assignment_id == target.assignment_id)
    assert original_again.state == AssignmentState.PLANNED
    assert original_again.operational_code is None


def test_nn_survives_restart(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    pstate = seed_real_object(conn, case_id="nn-2", month=MONTH, seed=401)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    target = next(a for a in get_schedule_snapshot(conn, v1.version_id).assignments if a.role == AssignmentRole.PRIMARY)
    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    conn.close()

    reopened = connect(db_path)
    reread = next(a for a in get_schedule_snapshot(reopened, v2.version_id).assignments if a.assignment_id == target.assignment_id)
    assert reread.state == AssignmentState.CANCELLED
    assert reread.operational_code == "NN"


def test_nn_without_replacement_materializes_coverage_deviation(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="nn-3", month=MONTH, seed=402)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    target = next(a for a in get_schedule_snapshot(conn, v1.version_id).assignments if a.role == AssignmentRole.PRIMARY)

    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    coverage_devs = [d for d in v2_snapshot.deviations if d.category.value == "COVERAGE"]
    assert any(d.affected_assignment_or_employee == target.covers_demand_id for d in coverage_devs)


def test_nn_with_manual_replacement_no_coverage_gap(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="nn-4", month=MONTH, seed=403)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    target = next(a for a in get_schedule_snapshot(conn, v1.version_id).assignments if a.role == AssignmentRole.PRIMARY)
    other = next(e.employee_id for e in pstate.employees if e.employee_id != target.employee_id)

    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    replacement = Assignment(
        "ASG-NN-FILL", "", other, target.start_datetime, target.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, target.covers_demand_id, None,
    )
    v3 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 3),
        upsert_assignments=[replacement],
    )
    v3_snapshot = get_schedule_snapshot(conn, v3.version_id)
    coverage_devs = [
        d for d in v3_snapshot.deviations
        if d.category.value == "COVERAGE" and d.affected_assignment_or_employee == target.covers_demand_id
    ]
    assert coverage_devs == []
    assert v2.version_id != v3.version_id  # no automatic REPLAN merged these -- two explicit child versions


def _seed_minimal_context(conn) -> tuple[str, str]:
    profile = base_profile()
    from rota.persistence.site_profile_repository import save_site_profile
    from rota.persistence.site_repository import save_site
    from rota.persistence.calendar_repository import save_calendar_day
    from rota.domain import CalendarDay, Site
    import calendar as cal
    site_id, coordinator_id, employee_id = "SITE-NN", "COORD-NN", "EMP-NN"
    save_site_profile(conn, profile)
    save_site(conn, Site(site_id, profile.profile_id, "NN Site", True, planning_regime=SitePlanningRegime.ORDINARY))
    save_coordinator(conn, Coordinator(coordinator_id, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(coordinator_id, site_id, True))
    save_employee(conn, Employee(employee_id, "Emp NN", date(2026, 1, 1), None, False))
    save_site_membership(
        conn, SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    days_in_month = cal.monthrange(MONTH.year, MONTH.month)[1]
    for day in range(1, days_in_month + 1):
        save_calendar_day(conn, CalendarDay(date=date(MONTH.year, MONTH.month, day), holiday=False))
    return site_id, employee_id


def test_nn_reduces_planned_hours_168_to_156(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    site_id, employee_id = _seed_minimal_context(conn)

    demands, assignments = [], []
    for day in range(1, 15):  # 14 x 12h D shifts
        demand_id = f"D-{day}"
        start = datetime(2026, 8, day, 5, 0)
        end = datetime(2026, 8, day, 17, 0)
        demands.append(ShiftDemand(demand_id, "", start, end, 1))
        assignments.append(Assignment(
            f"AS-{day}", "", employee_id, start, end, AssignmentRole.PRIMARY, AssignmentState.PLANNED,
            False, demand_id, None,
        ))
    lifecycle.create_schedule_version(
        conn, version_id="SV-NN-1", site_id=site_id, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 7, 25), created_by="COORD-NN",
        applied_rule_version_ids=[], shift_demands=demands, assignments=assignments, deviations=[],
        effective_from=date(2026, 7, 25),
    )
    save_work_balance_target(conn, employee_id=employee_id, month=MONTH, target_hours=160)

    before = reconstruct_month_balance(conn, employee_id=employee_id, month=MONTH)
    assert before.planned_hours == 168
    assert before.realized_hours == 0

    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-NN", effective_from=date(2026, 8, 2),
        assignment_id="AS-1",
    )
    assert v2.version_id  # sanity: child created

    after = reconstruct_month_balance(conn, employee_id=employee_id, month=MONTH)
    assert after.planned_hours == 156
    assert after.realized_hours == 0


def test_nn_no_availability_record_or_site_rule_side_effect(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="nn-5", month=MONTH, seed=404)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    target = next(a for a in get_schedule_snapshot(conn, v1.version_id).assignments if a.role == AssignmentRole.PRIMARY)

    availability_before = conn.execute("SELECT COUNT(*) FROM availability_versions").fetchone()[0]
    rules_before = conn.execute("SELECT COUNT(*) FROM site_rule_versions").fetchone()[0]
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )

    assert conn.execute("SELECT COUNT(*) FROM availability_versions").fetchone()[0] == availability_before
    assert conn.execute("SELECT COUNT(*) FROM site_rule_versions").fetchone()[0] == rules_before
    # exactly one new ScheduleVersion -- no automatic REPLAN chaining extra versions
    versions_after = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    assert versions_after == versions_before + 1


def test_plain_cancelled_without_nn_still_legal(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="nn-6", month=MONTH, seed=405)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    target = next(a for a in get_schedule_snapshot(conn, v1.version_id).assignments if a.role == AssignmentRole.PRIMARY)

    from dataclasses import replace
    plain_cancelled = replace(target, state=AssignmentState.CANCELLED)
    assert plain_cancelled.operational_code is None
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        upsert_assignments=[plain_cancelled],
    )
    reread = next(a for a in get_schedule_snapshot(conn, v2.version_id).assignments if a.assignment_id == target.assignment_id)
    assert reread.state == AssignmentState.CANCELLED
    assert reread.operational_code is None
