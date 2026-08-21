"""Independent adversarial matrix for ROTA-T022 implementation Round 1.

These tests encode only requirements already frozen in tasks/ROTA-T022/brief.md:
fail-closed full-hour inputs, fail-closed legacy demand classification,
H12+H12-only continuous-pair handling, normal-H24 provenance, and the
cross-Site zero-gap addendum.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta

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
    StandardShift,
)
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_validation import validate_demands
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, SITE_ID, base_profile, base_state

VERSION_ID = "audit-v1"


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(
        employee_id,
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        can_work_24h=True,
    )


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _demand(
    demand_id: str,
    start: datetime,
    end: datetime,
    *,
    shift_kind: ShiftKind | None = ShiftKind.D,
    catalog_kind: ShiftCatalogKind | None = ShiftCatalogKind.H12,
    required_rest_hours: int | None = 0,
    template_id: str | None = None,
    component: int | None = None,
) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        VERSION_ID,
        start,
        end,
        1,
        shift_kind=shift_kind,
        catalog_kind=catalog_kind,
        required_rest_hours=required_rest_hours,
        work_period_template_id=template_id,
        work_period_component=component,
    )


def _primary(
    assignment_id: str,
    employee_id: str,
    demand: ShiftDemand,
    *,
    schedule_version_id: str = VERSION_ID,
    work_period_id: str | None = None,
    required_rest_after_hours: int | None = 0,
) -> Assignment:
    return Assignment(
        assignment_id,
        schedule_version_id,
        employee_id,
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        demand.demand_id,
        None,
        work_period_id=work_period_id,
        required_rest_after_hours=required_rest_after_hours,
    )


def test_r1_unclassifiable_legacy_demand_must_not_skip_hard_validation():
    demand = _demand(
        "LEGACY",
        datetime(2026, 10, 5, 6),
        datetime(2026, 10, 5, 18),
        shift_kind=None,
        catalog_kind=None,
        required_rest_hours=None,
    )
    assignment = _primary("A", "E", demand, required_rest_after_hours=None)
    state = base_state(
        shift_demands=(demand,),
        employees=(_employee("E", day_only=True),),
        memberships=(_membership("E"),),
    )

    assert not validate(state, [assignment]).hard_pass


def test_r1_direct_plan_and_validation_reject_fractional_profile_catalog():
    profile = replace(
        base_profile(),
        standard_shifts=[StandardShift(ShiftKind.D, time(5, 30), time(17), False, 1)],
    )
    demand = _demand("D", datetime(2026, 10, 5, 5), datetime(2026, 10, 5, 17))
    assignment = _primary("A", "E", demand)
    state = base_state(
        profile=profile,
        shift_demands=(demand,),
        employees=(_employee("E"),),
        memberships=(_membership("E"),),
    )

    observed = (validate(state, [assignment]).hard_pass, plan(state).status)
    assert observed == (False, "TECHNICAL_ERROR")


@pytest.mark.parametrize("source", ["boundary_assignment", "other_site_assignment", "boundary_demand"])
def test_r1_fractional_legacy_context_must_fail_closed(source: str):
    demand = _demand("FOREIGN-D", datetime(2026, 9, 30, 5, 30), datetime(2026, 9, 30, 17))
    assignment = _primary("FOREIGN-A", "E", demand, schedule_version_id="foreign-v1")
    overrides = {
        "boundary_assignment": {"boundary_assignments": (assignment,)},
        "other_site_assignment": {"other_site_assignments": (assignment,)},
        "boundary_demand": {"boundary_shift_demands": (demand,)},
    }[source]
    state = base_state(**overrides)

    observed = (validate(state, []).hard_pass, plan(state).status)
    assert observed == (False, "TECHNICAL_ERROR")


@pytest.mark.parametrize("first_hours,second_hours", [(6, 18), (8, 16), (10, 14)])
def test_r1_zero_rest_inny_pairs_totalling_24h_remain_legal(first_hours: int, second_hours: int):
    start = datetime(2026, 10, 5, 5)
    middle = start + timedelta(hours=first_hours)
    end = middle + timedelta(hours=second_hours)
    d1 = _demand("I1", start, middle, catalog_kind=ShiftCatalogKind.OTHER)
    d2 = _demand("I2", middle, end, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.OTHER)
    assignments = (_primary("A1", "E", d1), _primary("A2", "E", d2))
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))

    assert validate(state, list(assignments)).hard_pass


def test_r1_cross_site_shared_work_period_id_must_fail_closed():
    other_demand = _demand("OTHER-D", datetime(2026, 10, 5, 5), datetime(2026, 10, 5, 17))
    current_demand = _demand("CURRENT-D", datetime(2026, 10, 5, 17), datetime(2026, 10, 6, 5), shift_kind=ShiftKind.N)
    other = _primary("OTHER-A", "E", other_demand, schedule_version_id="other-v1", work_period_id="COLLISION")
    current = _primary("CURRENT-A", "E", current_demand, work_period_id="COLLISION")
    state = base_state(
        shift_demands=(current_demand,),
        memberships=(_membership("E"),),
        other_site_assignments=(other,),
    )

    assert not validate(state, [current]).hard_pass


def test_r1_explicit_h24_without_template_is_malformed_at_write_and_validation():
    demand = _demand(
        "H24-ONLY",
        datetime(2026, 10, 5, 5),
        datetime(2026, 10, 5, 17),
        catalog_kind=ShiftCatalogKind.H24,
        template_id=None,
        component=1,
    )
    assignment = _primary("A", "E", demand)
    state = base_state(shift_demands=(demand,), memberships=(_membership("E"),))

    try:
        validate_demands(MONTH, [demand])
        write_rejected = False
    except MalformedScheduleSnapshot:
        write_rejected = True
    observed = (write_rejected, validate(state, [assignment]).hard_pass)
    assert observed == (True, False)


def test_r1_direct_validator_rejects_h24_demand_rest_mismatch():
    d1 = _demand(
        "H1",
        datetime(2026, 10, 5, 5),
        datetime(2026, 10, 5, 17),
        catalog_kind=ShiftCatalogKind.H24,
        required_rest_hours=11,
        template_id="T",
        component=1,
    )
    d2 = _demand(
        "H2",
        datetime(2026, 10, 5, 17),
        datetime(2026, 10, 6, 5),
        shift_kind=ShiftKind.N,
        catalog_kind=ShiftCatalogKind.H24,
        required_rest_hours=12,
        template_id="T",
        component=2,
    )
    assignments = (
        _primary("A1", "E", d1, work_period_id="T", required_rest_after_hours=11),
        _primary("A2", "E", d2, work_period_id="T", required_rest_after_hours=11),
    )
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))

    assert not validate(state, list(assignments)).hard_pass
