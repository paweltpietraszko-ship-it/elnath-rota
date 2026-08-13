"""Durable R3 regressions for Codex R2 findings."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from benchmarks.real_object_checker import (
    collective_shortage_evidence,
    eligibility_reasons,
)
from benchmarks.real_object_decisions import check_decision
from benchmarks.real_object_input import validate_scenario
from benchmarks.real_object_oracle import classify_reference
from benchmarks.real_object_scenarios import (
    core_scenarios,
    demands_for_month,
)
from benchmarks.real_object_types import AvailabilitySpec, FixedAssignmentSpec, OracleClass
from rota.planning.engine_types import (
    Blocker,
    BlockingDemand,
    DecisionRequiredPayload,
    PlanningResult,
)


def _case(case_id: str):
    return next(item for item in core_scenarios() if item.case_id == case_id)


def _blocking(scenario, demand_id: str) -> BlockingDemand:
    demand = next(item for item in demands_for_month(scenario) if item.demand_id == demand_id)
    return BlockingDemand(demand.demand_id, demand.start, demand.end)


def _decision(payload: DecisionRequiredPayload) -> PlanningResult:
    return PlanningResult("DECISION_REQUIRED", [], payload, None, [])


def test_external_rejects_extra_fictional_blocker() -> None:
    scenario = _case("external-before-confirmation")
    reference = classify_reference(scenario)
    demand_id = "2027-05-12-N"
    payload = DecisionRequiredPayload(
        [_blocking(scenario, demand_id)],
        [Blocker("X", "EXTERNAL-01"), Blocker("A", "SICK_LEAVE-01")],
        None,
        ["potwierdzenie X/Y"],
    )
    errors, _ = check_decision(scenario, reference, _decision(payload))
    assert any("A/SICK_LEAVE-01" in error for error in errors)


def test_external_requires_semantically_matching_unblocking_option() -> None:
    scenario = _case("external-before-confirmation")
    reference = classify_reference(scenario)
    payload = DecisionRequiredPayload(
        [_blocking(scenario, "2027-05-12-N")],
        [Blocker("X", "EXTERNAL-01")],
        None,
        ["świadome wyłączenie DAY_ONLY"],
    )
    errors, _ = check_decision(scenario, reference, _decision(payload))
    assert any("required EXTERNAL" in error for error in errors)


def test_shortage_rejects_empty_blocker_list() -> None:
    scenario = _case("simple-no-eligible-night")
    reference = classify_reference(scenario)
    payload = DecisionRequiredPayload(
        [_blocking(scenario, "2027-06-10-N")], [], None,
        ["potwierdzenie X/Y"],
    )
    errors, _ = check_decision(scenario, reference, _decision(payload))
    assert "proven staffing shortage lacks blockers" in errors


def _collective_rest_scenario():
    base = _case("calendar-28-feb-2027")
    day = base.month.replace(day=8)
    absent = tuple(
        AvailabilitySpec(employee, "DAY_SHIFT_OFF", day, day)
        for employee in ("B", "C", "D", "E")
    )
    return replace(
        base,
        case_id="collective-rest-shortage-r3",
        seed=31001,
        ladder_steps=(),
        strict_monthly_hours=(),
        availability=absent,
        declared_class=OracleClass.PROVEN_STAFFING_SHORTAGE,
    )


def test_collective_rest_shortage_has_positive_independent_certificate() -> None:
    scenario = _collective_rest_scenario()
    demand_ids = {"2027-02-08-D", "2027-02-08-N"}
    proof = collective_shortage_evidence(scenario, demand_ids)
    assert proof["infeasible"] is True
    assert "A" in proof["rest_employees"]
    reference = classify_reference(scenario)
    payload = DecisionRequiredPayload(
        [_blocking(scenario, demand_id) for demand_id in sorted(demand_ids)],
        [Blocker("A", "REST-01")], None,
        ["świadoma ręczna korekta zgodnie z kontraktem"],
    )
    errors, _ = check_decision(scenario, reference, _decision(payload))
    assert errors == []


def test_target_site_boundary_rejects_noncanonical_geometry() -> None:
    scenario = _case("calendar-28-feb-2027")
    first = scenario.boundary_assignments[0]
    bad = replace(
        first,
        assignment_id="bad-geometry",
        start=datetime(2027, 1, 26, 6),
        end=datetime(2027, 1, 26, 18),
    )
    invalid = replace(scenario, case_id="bad-geometry-case", boundary_assignments=(bad, *scenario.boundary_assignments[1:]))
    assert any("canonical D/N geometry" in error for error in validate_scenario(invalid))


def test_assignment_ids_are_unique_across_boundary_and_fixed_collections() -> None:
    scenario = _case("replan-realized-frozen-baseline")
    boundary = scenario.boundary_assignments[0]
    fixed = scenario.fixed_demand_assignments[0]
    duplicate = replace(fixed, assignment_id=boundary.assignment_id)
    invalid = replace(
        scenario,
        case_id="duplicate-global-fixed-id",
        fixed_demand_assignments=(duplicate, *scenario.fixed_demand_assignments[1:]),
    )
    assert any("duplicate assignment id across fixed inputs" in error for error in validate_scenario(invalid))


def test_cancelled_rows_cannot_satisfy_required_six_day_history() -> None:
    scenario = _case("calendar-28-feb-2027")
    cancelled = tuple(replace(item, state="CANCELLED") for item in scenario.boundary_assignments)
    invalid = replace(scenario, case_id="cancelled-history", boundary_assignments=cancelled)
    errors = validate_scenario(invalid)
    assert any("CANCELLED is not an operative fixed fact" in error for error in errors)
    assert any("six-day history must be REALIZED" in error for error in errors)


def test_absence_ladder_is_monotonic_in_actual_facts() -> None:
    rows = sorted(
        (item for item in core_scenarios() if item.series_id == "absence-ladder"),
        key=lambda item: item.series_level,
    )
    for previous, current in zip(rows, rows[1:]):
        assert set(previous.availability) <= set(current.availability)


def test_profile_disabled_uses_canonical_external_01_in_benchmark_evidence() -> None:
    scenario = _case("external-window-profile-disabled")
    demand = next(item for item in demands_for_month(scenario) if item.demand_id == "2027-05-12-N")
    reasons = eligibility_reasons(scenario, "X", demand)
    assert "EXTERNAL-01" in reasons
    assert "EXTERNAL_SUPPORT_DISABLED" not in reasons


@pytest.mark.parametrize(
    ("case_id", "rest_blocked"),
    [("rest-boundary-exact-11h", False), ("rest-boundary-below-11h", True)],
)
def test_rest_threshold_uses_explicit_cross_site_context(case_id: str, rest_blocked: bool) -> None:
    scenario = _case(case_id)
    assert validate_scenario(scenario) == ()
    demand = next(item for item in demands_for_month(scenario) if item.demand_id == "2027-08-01-D")
    reasons = eligibility_reasons(scenario, "E", demand)
    assert ("REST-01" in reasons) is rest_blocked


if __name__ == "__main__":
    print("test_real_object_benchmark_r3 OK")
