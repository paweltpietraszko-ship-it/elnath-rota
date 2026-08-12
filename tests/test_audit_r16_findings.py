"""Regression tests for tasks/ROTA-T003/round_01/tests/tests_r16.txt.

FINDING R16-1: the solver never filtered state.memberships to the current
site, so an other-site-only membership wrongly authorized eligibility
(variant A), and a multi-site Employee (EMP-03) was duplicated in the CP-SAT
model, corrupting the coverage constraint (variant B).

FINDING R16-2: SiteProfile.external_support_enabled=false did not block
EXTERNAL_SUPPORT eligibility even with a fully valid, covering window.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.domain import (
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)


def _local_membership(employee_id: str, site_id: str) -> SiteMembership:
    return SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# FINDING R16-1 -----------------------------------------------------------


def test_r16_1a_other_site_only_membership_is_decision_required_not_technical_error():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A", "other-site"),), shift_demands=(DEMAND_D,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def test_r16_1b_multi_site_employee_is_not_duplicated_in_the_model():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,),
        memberships=(_local_membership("A", SITE_ID), _local_membership("A", "other-site")),
        shift_demands=(DEMAND_D,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert len(result.candidates[0]) == 1


# FINDING R16-2 ---------------------------------------------------------------


def test_r16_2_external_support_disabled_blocks_external_even_with_valid_window():
    employee = Employee("X", "X", date(2026, 9, 1), None, False)
    membership = SiteMembership("X", SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    window = ExternalSupportWindow("win-1", "X", SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None)
    state = base_state(
        employees=(employee,), memberships=(membership,), external_windows=(window,), shift_demands=(DEMAND_D,),
    )
    state = replace(state, profile=replace(state.profile, external_support_enabled=False))
    result = plan(state)
    assert result.status != "FEASIBLE"


if __name__ == "__main__":
    print("test_audit_r16_findings module OK")
