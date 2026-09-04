"""Independent implementation-audit reproducers for ROTA-T052."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
)
from rota.planning.solver import solve
from rota.planning.validator import validate
from rota.application import plan_ops, schedule_export as schedule_export
from rota.balance import compute_month_balance
from rota.persistence.db import connect
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.site_repository import WorkCodeInterval, get_site_print_settings, save_site_print_settings
from tests.support.minimal_state import SITE_ID, base_state
from tests.test_t020 import _create_version, _seed, _settings, _work_item


def _local_employee() -> tuple[Employee, SiteMembership]:
    employee = Employee("E1", "Anna", date(2020, 1, 1), None, False)
    membership = SiteMembership(
        "E1",
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )
    return employee, membership


def _s1(start: datetime, end: datetime) -> Assignment:
    return Assignment(
        "S1-A1",
        "test-v1",
        "E1",
        start,
        end,
        AssignmentRole.PERIODIC_TRAINING,
        AssignmentState.PLANNED,
        False,
        None,
        None,
    )


def _night(start: datetime, end: datetime) -> ShiftDemand:
    return ShiftDemand(
        "N-DEMAND",
        "test-v1",
        start,
        end,
        1,
        ShiftKind.N,
        ShiftCatalogKind.H12,
        11,
    )


@pytest.mark.parametrize(
    ("training", "demand"),
    [
        # T52-05: a night ending at 05:00 must not block S1 at 08:00.
        (
            _s1(datetime(2026, 10, 2, 8), datetime(2026, 10, 2, 12)),
            _night(datetime(2026, 10, 1, 17), datetime(2026, 10, 2, 5)),
        ),
        # T52-06: S1 ending at 12:00 must not create an 11-hour wall
        # before a non-overlapping night starting at 17:00.
        (
            _s1(datetime(2026, 10, 2, 8), datetime(2026, 10, 2, 12)),
            _night(datetime(2026, 10, 2, 17), datetime(2026, 10, 3, 5)),
        ),
    ],
)
def test_solver_does_not_hard_block_a_shift_around_s1(training: Assignment, demand: ShiftDemand) -> None:
    employee, membership = _local_employee()
    state = base_state(
        employees=(employee,),
        memberships=(membership,),
        shift_demands=(demand,),
        existing_assignments=(training,),
    )

    # The independent validator accepts the exact witness as HARD-valid;
    # only the solver-side fixed-period constraint rejects it.
    witness = Assignment(
        "N-A1",
        "test-v1",
        "E1",
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        demand.demand_id,
        None,
        required_rest_after_hours=11,
    )
    validation = validate(state, [training, witness])
    assert validation.hard_pass, validation.violations

    outcome = solve(state)

    assert outcome.status_name == "FEASIBLE", outcome


def test_pdf_model_keeps_non_overlapping_s1_and_primary_from_the_same_day() -> None:
    """T52-06 + T52-08 + T52-12: a legal same-day pair must remain printable."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand, primary = _work_item(3, 18, 6, kind=ShiftKind.N)
    training = Assignment(
        "S1-A1",
        "",
        "EMP-1",
        datetime(2026, 8, 3, 10),
        datetime(2026, 8, 3, 14),
        AssignmentRole.PERIODIC_TRAINING,
        AssignmentState.PLANNED,
        False,
        None,
        None,
    )
    _create_version(conn, [demand], [primary, training])

    model = schedule_export._assemble_export_model(
        conn, site_id="SITE-1", month=date(2026, 8, 1), period_label="Sierpień 2026"
    )

    cell = model.rows[0].plan[2]
    assert "S1" in cell and "N1" in cell


def test_real_plan_chain_does_not_turn_s1_rest_exception_into_decision_required() -> None:
    """The same REST defect through SQLite -> assembler -> plan_month -> solver."""
    conn = connect(":memory:")
    _seed(conn)
    training = Assignment(
        "S1-A1",
        "",
        "EMP-1",
        datetime(2026, 8, 3, 8),
        datetime(2026, 8, 3, 12),
        AssignmentRole.PERIODIC_TRAINING,
        AssignmentState.PLANNED,
        False,
        None,
        None,
    )
    demand, _ = _work_item(3, 18, 6, kind=ShiftKind.N)
    _create_version(conn, [demand], [training])

    result = plan_ops.plan_month(
        conn,
        site_id="SITE-1",
        month=date(2026, 8, 1),
        coordinator_id="COORD-1",
        effective_from=date(2026, 8, 1),
    )

    assert result.status == "FEASIBLE", result


def test_s1_default_interval_round_trips_and_has_no_fixed_duration() -> None:
    conn = connect(":memory:")
    _seed(conn)
    for start, end in (("10:00", "12:00"), ("10:00", "14:00")):
        save_site_print_settings(
            conn,
            _settings(s1_default_interval=WorkCodeInterval(start, end, False)),
        )
        saved = get_site_print_settings(conn, "SITE-1")
        assert saved is not None
        assert saved.s1_default_interval == WorkCodeInterval(start, end, False)


def test_s1_counts_once_in_planned_and_realized_balance() -> None:
    planned = _s1(datetime(2026, 10, 2, 8), datetime(2026, 10, 2, 10))
    realized = Assignment(
        **{
            **planned.__dict__,
            "assignment_id": "S1-A2",
            "start_datetime": datetime(2026, 10, 3, 8),
            "end_datetime": datetime(2026, 10, 3, 12),
            "state": AssignmentState.REALIZED,
        }
    )
    balance = compute_month_balance("E1", date(2026, 10, 1), 8, [planned, realized], [])
    assert balance.planned_hours == 2
    assert balance.realized_hours == 4


def test_persistence_rejects_s1_that_claims_demand_coverage() -> None:
    conn = connect(":memory:")
    _seed(conn)
    demand, _ = _work_item(3, 18, 6, kind=ShiftKind.N)
    invalid = Assignment(
        "S1-A1",
        "",
        "EMP-1",
        datetime(2026, 8, 3, 10),
        datetime(2026, 8, 3, 14),
        AssignmentRole.PERIODIC_TRAINING,
        AssignmentState.PLANNED,
        False,
        demand.demand_id,
        None,
    )
    with pytest.raises(MalformedScheduleSnapshot):
        _create_version(conn, [demand], [invalid])


def test_validator_still_rejects_real_s1_overlap() -> None:
    first = _s1(datetime(2026, 10, 2, 8), datetime(2026, 10, 2, 12))
    second = Assignment(
        **{
            **first.__dict__,
            "assignment_id": "S1-A2",
            "start_datetime": datetime(2026, 10, 2, 10),
            "end_datetime": datetime(2026, 10, 2, 14),
        }
    )
    report = validate(base_state(), [first, second])
    assert not report.hard_pass
    assert any(v.startswith("REST-01") for v in report.violations)
