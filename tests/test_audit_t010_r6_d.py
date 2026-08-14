"""ROTA-T010 implementation re-audit round 6: Part D only.

Adversarial provenance, rejection, balance, and partial-coverage coverage for
NN. Parts A and B are deliberately outside this file and round-6 verdict.
"""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.application.manual_edit import apply_manual_correction, mark_not_worked
from rota.application.errors import NotWorkedRequiresPlannedPrimary
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    Site,
    SiteMembership,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import (
    save_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.persistence.work_balance_repository import reconstruct_month_balance, save_work_balance_target
from tests.support.minimal_state import base_profile


MONTH = date(2026, 8, 1)
SITE_ID = "SITE-T010-R6-D"
COORDINATOR_ID = "COORD-T010-R6-D"
EMP_A = "EMP-R6-A"
EMP_B = "EMP-R6-B"
EMP_C = "EMP-R6-C"


def _seed_context(conn) -> None:
    profile = base_profile()
    save_site_profile(conn, profile)
    save_site(conn, Site(SITE_ID, profile.profile_id, "Site D", True))
    save_coordinator(conn, Coordinator(COORDINATOR_ID, "Coordinator D", True))
    save_coordinator_site_association(
        conn, CoordinatorSiteAssociation(COORDINATOR_ID, SITE_ID, True)
    )
    for employee_id in (EMP_A, EMP_B, EMP_C):
        save_employee(conn, Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
        save_site_membership(
            conn,
            SiteMembership(
                employee_id,
                SITE_ID,
                MembershipKind.LOCAL,
                True,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
            ),
        )
    for day in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(MONTH.year, MONTH.month, day), False))


def _demand(*, demand_id: str = "DEMAND-1", day: int = 1) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "",
        datetime(2026, 8, day, 5),
        datetime(2026, 8, day, 17),
        1,
    )


def _primary(
    assignment_id: str,
    employee_id: str,
    demand: ShiftDemand,
    *,
    state: AssignmentState = AssignmentState.PLANNED,
    operational_code: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> Assignment:
    return Assignment(
        assignment_id,
        "",
        employee_id,
        start or demand.start_datetime,
        end or demand.end_datetime,
        AssignmentRole.PRIMARY,
        state,
        False,
        demand.demand_id,
        None,
        operational_code,
    )


def _trainee(
    assignment_id: str,
    employee_id: str,
    mentor_id: str,
    demand: ShiftDemand,
    *,
    state: AssignmentState = AssignmentState.PLANNED,
) -> Assignment:
    return Assignment(
        assignment_id,
        "",
        employee_id,
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.TRAINEE,
        state,
        False,
        None,
        mentor_id,
        None,
    )


def _create_parent(
    conn,
    *,
    version_id: str,
    demands: list[ShiftDemand],
    assignments: list[Assignment],
) -> None:
    lifecycle.create_schedule_version(
        conn,
        version_id=version_id,
        site_id=SITE_ID,
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 7, 25, 9),
        created_by=COORDINATOR_ID,
        applied_rule_version_ids=[],
        shift_demands=demands,
        assignments=assignments,
        deviations=[],
        effective_from=date(2026, 7, 25),
    )


def _generic_nn_bypass_case(case: str) -> tuple[list[Assignment], Assignment]:
    demand = _demand()
    if case == "brand_new_cancelled_nn":
        original = _primary("AS-ORIGINAL", EMP_A, demand)
        synthetic = _primary(
            "AS-SYNTHETIC",
            EMP_B,
            demand,
            state=AssignmentState.CANCELLED,
            operational_code="NN",
        )
        return [original], synthetic
    if case == "previously_cancelled_primary":
        cancelled = _primary("AS-TARGET", EMP_A, demand, state=AssignmentState.CANCELLED)
        return [cancelled], replace(cancelled, operational_code="NN")
    if case == "previously_planned_trainee":
        mentor = _primary("AS-MENTOR", EMP_A, demand)
        trainee = _trainee("AS-TARGET", EMP_B, mentor.assignment_id, demand)
        converted = _primary(
            trainee.assignment_id,
            EMP_B,
            demand,
            state=AssignmentState.CANCELLED,
            operational_code="NN",
        )
        return [mentor, trainee], converted
    raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    [
        "brand_new_cancelled_nn",
        "previously_cancelled_primary",
        "previously_planned_trainee",
    ],
)
def test_r6_d_generic_manual_correction_cannot_invent_nn_without_planned_primary_parent(
    tmp_path, case
) -> None:
    """A legal field shape is still not NN without the contracted parent fact."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    parent_assignments, upsert = _generic_nn_bypass_case(case)
    _create_parent(
        conn,
        version_id="SV-PARENT",
        demands=[demand],
        assignments=parent_assignments,
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    current_before = get_current_version_id(conn, SITE_ID, MONTH)

    with pytest.raises(Exception):
        apply_manual_correction(
            conn,
            site_id=SITE_ID,
            month=MONTH,
            coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 8, 2),
            upsert_assignments=[upsert],
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before
    assert get_current_version_id(conn, SITE_ID, MONTH) == current_before


def test_r6_d_root_snapshot_cannot_start_with_nn_without_any_parent(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    synthetic = _primary(
        "AS-SYNTHETIC",
        EMP_A,
        demand,
        state=AssignmentState.CANCELLED,
        operational_code="NN",
    )

    with pytest.raises(Exception):
        _create_parent(
            conn,
            version_id="SV-ROOT-WITH-NN",
            demands=[demand],
            assignments=[synthetic],
        )

    assert get_current_version_id(conn, SITE_ID, MONTH) is None


def test_r6_d_in_place_replace_cannot_introduce_nn_and_destroy_planned_history(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    planned = _primary("AS-TARGET", EMP_A, demand)
    _create_parent(conn, version_id="SV-WORKING", demands=[demand], assignments=[planned])

    with pytest.raises(Exception):
        lifecycle.replace_working_snapshot(
            conn,
            version_id="SV-WORKING",
            applied_rule_version_ids=[],
            shift_demands=[demand],
            assignments=[
                replace(planned, state=AssignmentState.CANCELLED, operational_code="NN")
            ],
            deviations=[],
        )

    snapshot = get_schedule_snapshot(conn, "SV-WORKING")
    reread = next(item for item in snapshot.assignments if item.assignment_id == planned.assignment_id)
    assert reread.state == AssignmentState.PLANNED
    assert reread.operational_code is None


@pytest.mark.parametrize(
    ("role", "state"),
    [
        (AssignmentRole.PRIMARY, AssignmentState.REALIZED),
        (AssignmentRole.PRIMARY, AssignmentState.CANCELLED),
        (AssignmentRole.TRAINEE, AssignmentState.PLANNED),
    ],
)
def test_r6_d_named_command_rejects_every_non_planned_primary_without_child(
    tmp_path, role, state
) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    mentor = _primary("AS-MENTOR", EMP_A, demand)
    if role == AssignmentRole.TRAINEE:
        target = _trainee("AS-TARGET", EMP_B, mentor.assignment_id, demand, state=state)
        assignments = [mentor, target]
    else:
        target = _primary("AS-TARGET", EMP_A, demand, state=state)
        assignments = [target]
    _create_parent(
        conn,
        version_id="SV-PARENT",
        demands=[demand],
        assignments=assignments,
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(NotWorkedRequiresPlannedPrimary):
        mark_not_worked(
            conn,
            site_id=SITE_ID,
            month=MONTH,
            coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 8, 2),
            assignment_id=target.assignment_id,
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before
    assert get_current_version_id(conn, SITE_ID, MONTH) == "SV-PARENT"


def test_r6_d_second_nn_attempt_on_current_cancelled_nn_is_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    target = _primary("AS-TARGET", EMP_A, demand)
    _create_parent(conn, version_id="SV-PARENT", demands=[demand], assignments=[target])
    child = mark_not_worked(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(NotWorkedRequiresPlannedPrimary):
        mark_not_worked(
            conn,
            site_id=SITE_ID,
            month=MONTH,
            coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 8, 3),
            assignment_id=target.assignment_id,
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before
    assert get_current_version_id(conn, SITE_ID, MONTH) == child.version_id


def test_r6_d_existing_nn_can_be_preserved_unchanged_by_later_snapshot_write(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    target = _primary("AS-TARGET", EMP_A, demand)
    _create_parent(conn, version_id="SV-PARENT", demands=[demand], assignments=[target])
    child = mark_not_worked(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id,
    )
    snapshot = get_schedule_snapshot(conn, child.version_id)

    lifecycle.replace_working_snapshot(
        conn,
        version_id=child.version_id,
        applied_rule_version_ids=snapshot.applied_rule_version_ids,
        shift_demands=snapshot.shift_demands,
        assignments=snapshot.assignments,
        deviations=snapshot.deviations,
    )

    reread = get_schedule_snapshot(conn, child.version_id)
    nn = next(item for item in reread.assignments if item.assignment_id == target.assignment_id)
    assert nn.state == AssignmentState.CANCELLED
    assert nn.operational_code == "NN"


def test_r6_d_mixed_planned_realized_and_nn_hours_are_counted_by_state(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demands = [_demand(demand_id=f"DEMAND-{day}", day=day) for day in (1, 2, 3)]
    assignments = [
        _primary(f"AS-{day}", EMP_A, demand)
        for day, demand in zip((1, 2, 3), demands, strict=True)
    ]
    _create_parent(
        conn,
        version_id="SV-PARENT",
        demands=demands,
        assignments=assignments,
    )
    save_work_balance_target(conn, employee_id=EMP_A, month=MONTH, target_hours=24)

    apply_manual_correction(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 4),
        upsert_assignments=[
            replace(assignments[0], state=AssignmentState.CANCELLED, operational_code="NN"),
            replace(assignments[1], state=AssignmentState.REALIZED),
        ],
    )

    balance = reconstruct_month_balance(conn, employee_id=EMP_A, month=MONTH)
    assert balance.planned_hours == 12
    assert balance.realized_hours == 12
    assert balance.planned_hours + balance.realized_hours == 24


def test_r6_d_partial_then_complete_manual_replacement_uses_normal_coverage(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand(day=4)
    target = _primary("AS-TARGET", EMP_A, demand)
    _create_parent(conn, version_id="SV-PARENT", demands=[demand], assignments=[target])
    mark_not_worked(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 5),
        assignment_id=target.assignment_id,
    )

    first_half = _primary(
        "AS-FIRST-HALF",
        EMP_B,
        demand,
        start=demand.start_datetime,
        end=datetime(2026, 8, 4, 11),
    )
    partial = apply_manual_correction(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 6),
        upsert_assignments=[first_half],
    )
    partial_snapshot = get_schedule_snapshot(conn, partial.version_id)
    assert any(
        deviation.category.value == "COVERAGE"
        and deviation.affected_assignment_or_employee == demand.demand_id
        for deviation in partial_snapshot.deviations
    )

    second_half = _primary(
        "AS-SECOND-HALF",
        EMP_C,
        demand,
        start=datetime(2026, 8, 4, 11),
        end=demand.end_datetime,
    )
    complete = apply_manual_correction(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 7),
        upsert_assignments=[second_half],
    )
    complete_snapshot = get_schedule_snapshot(conn, complete.version_id)
    nn = next(
        item for item in complete_snapshot.assignments if item.assignment_id == target.assignment_id
    )
    assert nn.state == AssignmentState.CANCELLED
    assert nn.operational_code == "NN"
    assert not any(
        deviation.category.value == "COVERAGE"
        and deviation.affected_assignment_or_employee == demand.demand_id
        for deviation in complete_snapshot.deviations
    )
