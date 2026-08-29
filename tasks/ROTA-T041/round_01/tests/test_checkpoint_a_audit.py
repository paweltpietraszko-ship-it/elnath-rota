"""Independent reproducers for ROTA-T041 Checkpoint A audit.

These tests intentionally target boundaries not covered by the implementer's
matrix.  They are audit evidence, not product implementation tests.
"""
from __future__ import annotations

from datetime import date, datetime

from ortools.sat.python import cp_model

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.fairness import (
    add_equal_split_fairness,
    add_holiday_fairness,
    add_weekend_fairness,
)
from rota.planning.solver import SolverSlot
from rota.planning.validator import validate
from tests.support.minimal_state import SITE_ID, base_state


def _employee(employee_id: str) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, False)


def _membership(employee_id: str, kind: MembershipKind) -> SiteMembership:
    return SiteMembership(
        employee_id,
        SITE_ID,
        kind,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )


def _demand(demand_id: str, start: datetime, end: datetime) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", start, end, 1)


def _primary(
    assignment_id: str,
    employee_id: str,
    start: datetime,
    end: datetime,
    covers_demand_id: str,
) -> Assignment:
    return Assignment(
        assignment_id,
        "test-v1",
        employee_id,
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        True,
        covers_demand_id,
        None,
    )


def _combined_objective_for_holiday_assignment(assign_to_e1: bool) -> int:
    """Evaluate the real T041 equal-split and existing holiday terms.

    E1/E2 start with 12/24 actual hours.  The one 12h weekend+holiday shift
    can go to E1 (actual spread 0) or E2 (actual spread 24).  Historical
    holiday and fixed weekend hours are deliberately reversed, exposing
    whether equal-split is truly the primary ordering or merely an
    equal-weight peer of the older fairness terms.
    """
    model = cp_model.CpModel()
    choose_e1 = model.new_bool_var("choose_e1")
    model.add(choose_e1 == int(assign_to_e1))

    demand = _demand(
        "HOLIDAY",
        datetime(2026, 10, 4, 5, 0),
        datetime(2026, 10, 4, 17, 0),
    )
    slot_e1 = SolverSlot("E1", demand, None, False, False)
    slot_e2 = SolverSlot("E2", demand, None, False, False)
    x = {
        ("E1", demand.demand_id): choose_e1,
        ("E2", demand.demand_id): 1 - choose_e1,
    }
    actual_hours = {
        "E1": 12 + 12 * choose_e1,
        "E2": 24 + 12 * (1 - choose_e1),
    }
    penalties: list[object] = []
    add_equal_split_fairness(model, actual_hours, {"E1", "E2"}, penalties)
    add_holiday_fairness(
        model,
        x,
        {"E1": [slot_e1], "E2": [slot_e2]},
        {date(2026, 10, 4)},
        {"E1": 100, "E2": 0},
        penalties,
    )
    add_weekend_fairness(
        model,
        x,
        {"E1": [slot_e1], "E2": [slot_e2]},
        {"E1": 12, "E2": 0},
        penalties,
    )
    model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    assert solver.solve(model) == cp_model.OPTIMAL
    return round(solver.objective_value)


def test_missing_target_spread_has_priority_over_other_soft_fairness_terms():
    """OWNER-T041-01 requires the smallest achievable actual-hours spread."""
    best_spread_objective = _combined_objective_for_holiday_assignment(True)
    worse_spread_objective = _combined_objective_for_holiday_assignment(False)

    # The 0h-spread candidate must rank ahead of the 24h-spread candidate.
    assert best_spread_objective < worse_spread_objective


def test_missing_target_fallback_does_not_prefer_external_over_available_locals():
    """A real solve must not outsource merely to make LOCAL spread zero."""
    demand = _demand(
        "D1",
        datetime(2026, 10, 1, 5, 0),
        datetime(2026, 10, 1, 17, 0),
    )
    state = base_state(
        employees=(_employee("E1"), _employee("E2"), _employee("X1")),
        memberships=(
            _membership("E1", MembershipKind.LOCAL),
            _membership("E2", MembershipKind.LOCAL),
            _membership("X1", MembershipKind.EXTERNAL_SUPPORT),
        ),
        external_windows=(
            ExternalSupportWindow(
                "W1",
                "X1",
                SITE_ID,
                datetime(2026, 10, 1, 0, 0),
                datetime(2026, 10, 2, 0, 0),
                True,
                None,
            ),
        ),
        shift_demands=(demand,),
        work_balances=(),
    )

    result = plan(state)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    assert validate(state, candidate).hard_pass
    assert {a.employee_id for a in candidate} <= {"E1", "E2"}


def test_partial_overlap_keeps_geometry_for_nonconcurrent_tail():
    """Lineage disambiguates the overlap, not the adjacent non-overlap tail."""
    d1 = _demand(
        "D1",
        datetime(2026, 10, 5, 18, 0),
        datetime(2026, 10, 6, 6, 0),
    )
    d2 = _demand(
        "D2",
        datetime(2026, 10, 5, 22, 0),
        datetime(2026, 10, 6, 10, 0),
    )
    # A1 covers D1 and continues across D2's nonconcurrent 06:00-10:00 tail.
    a1 = _primary(
        "A1",
        "E1",
        datetime(2026, 10, 5, 18, 0),
        datetime(2026, 10, 6, 10, 0),
        "D1",
    )
    # A2 owns only D2's concurrent 22:00-06:00 segment.
    a2 = _primary(
        "A2",
        "E2",
        datetime(2026, 10, 5, 22, 0),
        datetime(2026, 10, 6, 6, 0),
        "D2",
    )
    state = base_state(
        shift_demands=(d1, d2),
        memberships=(
            _membership("E1", MembershipKind.LOCAL),
            _membership("E2", MembershipKind.LOCAL),
        ),
    )

    report = validate(state, [a1, a2])
    assert not any("COVERAGE-01" in violation for violation in report.violations), report.violations
