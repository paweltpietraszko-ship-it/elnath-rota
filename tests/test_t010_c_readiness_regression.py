"""ROTA-T010-C -- regression gate only, NO production code changes
(tasks/ROTA-T010/part_c_training_readiness.md): S stays a manual TRAINEE,
the solver never creates training on its own, and NOT_READY vs
READY_FOR_PRIMARY membership makes no eligibility difference."""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    AssignmentRole,
    Employee,
    MembershipKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
)
from rota.planning.eligibility import check_eligibility
from rota.planning.engine import plan
from tests.support.minimal_state import ReadinessSource, ReadinessState, base_profile, base_state

EMP = "EMP-READY-CHECK"


def _employee() -> Employee:
    return Employee(EMP, "Emp", date(2026, 1, 1), None, False)


def _membership(readiness: ReadinessState) -> SiteMembership:
    return SiteMembership(EMP, "test-site", MembershipKind.LOCAL, True, readiness, ReadinessSource.DEFAULT)


def _demand() -> ShiftDemand:
    return ShiftDemand("D-1", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def test_readiness_state_does_not_affect_eligibility() -> None:
    demand = _demand()
    not_ready = check_eligibility(
        _employee(), _membership(ReadinessState.NOT_READY), demand, ShiftKind.D, base_profile(), [], [], "test-site", [],
    )
    ready = check_eligibility(
        _employee(), _membership(ReadinessState.READY_FOR_PRIMARY), demand, ShiftKind.D, base_profile(), [], [], "test-site", [],
    )
    assert not_ready == ready
    assert not_ready.eligible


def test_solver_never_creates_a_trainee_assignment() -> None:
    demand = _demand()
    state = base_state(
        employees=(_employee(),), memberships=(_membership(ReadinessState.NOT_READY),), shift_demands=(demand,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert all(a.role != AssignmentRole.TRAINEE for a in result.candidates[0])
