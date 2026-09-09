"""Independent Codex reproducers for ROTA-T058 code audit round 4."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.application import manual_edit, plan_ops
from rota.application.deviation_mapping import materialize_deviations
from rota.domain import Assignment, AssignmentRole, AssignmentState, Employee, ShiftDemand, WorkBalance
from rota.persistence import schedule_lifecycle, site_memory
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import base_state
from tests.test_t032_soft_ranking import _d_demand, _membership
from tests.test_t019b import (
    COORD,
    MONTH,
    SITE,
    _seed_decision_required,
    _seed_feasible_and_select,
    _unblock_employee,
)


def _primary(assignment_id: str, day: int) -> Assignment:
    return Assignment(
        assignment_id,
        "historical-version",
        "E-HISTORY",
        datetime(2026, 7, day, 6),
        datetime(2026, 7, day, 18),
        AssignmentRole.PRIMARY,
        AssignmentState.REALIZED,
        True,
        None,
        None,
    )


def test_unrelated_boundary_only_triple_does_not_break_deviation_materialization() -> None:
    """A fully existing triple in another month is not a new correction."""
    state = base_state(boundary_assignments=tuple(_primary(f"H-{day}", day) for day in (1, 2, 3)))
    report = validate(state, [])
    assert any(
        detail.rule == "THIRD-CONSECUTIVE-SHIFT-01" and not detail.assignment_ids
        for detail in report.violation_details
    )

    # This is the exact validate -> materialize seam used by every manual
    # correction and revalidation. It must not throw because of an unrelated,
    # fully existing cross-month fact.
    materialize_deviations(report.violation_details, ())


def test_real_manual_correction_survives_unrelated_prior_month_triple() -> None:
    """Real DB-backed manual_edit vertical for the same failure class."""
    conn = connect(":memory:")
    current = _seed_feasible_and_select(conn)

    historical_version = "SV-HISTORY-JUL"
    demands = [
        ShiftDemand(
            f"HD-{day}", historical_version, datetime(2026, 7, day, 6), datetime(2026, 7, day, 18), 1
        )
        for day in (1, 2, 3)
    ]
    assignments = [
        Assignment(
            f"HA-{day}", historical_version, "E1", demand.start_datetime, demand.end_datetime,
            AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, demand.demand_id, None,
        )
        for day, demand in zip((1, 2, 3), demands)
    ]
    schedule_lifecycle.create_schedule_version(
        conn,
        version_id=historical_version,
        site_id=SITE,
        month=date(2026, 7, 1),
        parent_version_id=None,
        created_at=datetime(2026, 7, 1, 5),
        created_by=COORD,
        applied_rule_version_ids=[],
        shift_demands=demands,
        assignments=assignments,
        deviations=[],
        effective_from=date(2026, 7, 1),
    )

    target = get_schedule_snapshot(conn, current.version_id).assignments[0]
    corrected = manual_edit.apply_manual_correction(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=MONTH,
        upsert_assignments=[replace(target, frozen=not target.frozen)],
    )
    assert corrected.version_id != current.version_id


def test_new_nondecision_result_clears_stale_decision_required_readback() -> None:
    """The UI must not retain an obsolete coordinator question beside T058's block."""
    conn = connect(":memory:")
    _seed_decision_required(conn)
    first = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=date(2026, 8, 1)
    )
    assert first.status == "DECISION_REQUIRED"
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is not None

    # One worker becomes available. The old shortage question is no longer
    # truthful, but this one-worker/every-day shape is now blocked by T058.
    _unblock_employee(conn, "E1")
    second = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=date(2026, 8, 1)
    )
    assert second.status == "THIRD_CONSECUTIVE_SHIFT_BLOCKED"
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None


def test_real_solver_blocks_current_month_last_day_against_two_next_month_facts() -> None:
    """Independent forward N -> N+1 boundary check through engine.plan()."""
    month = date(2026, 10, 1)
    demand = _d_demand(31)
    boundary = tuple(
        Assignment(
            f"NEXT-{offset}", "accepted-next-month", "A",
            datetime(2026, 11, offset, 5), datetime(2026, 11, offset, 17),
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None,
        )
        for offset in (1, 2)
    )
    state = base_state(
        month=month,
        employees=(Employee("A", "A", date(2020, 1, 1), None, False),),
        memberships=(_membership("A"),),
        shift_demands=(demand,),
        boundary_assignments=boundary,
        work_balances=(WorkBalance("A", month, 12, 0, 0, 0, 0, 0),),
    )

    result = plan(state)
    assert result.status == "THIRD_CONSECUTIVE_SHIFT_BLOCKED"
    assert result.decision_payload is None
