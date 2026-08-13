"""R4 tests for the simplified real-object benchmark."""
from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import benchmarks.real_object as benchmark_runner
from benchmarks.real_object import _json_value, run_case, run_matrix
from benchmarks.real_object_checker import check_candidate, reshuffle_count, validate_ground_truth
from benchmarks.real_object_input import validate_scenario, validate_series_monotonicity
from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES, LOCAL_EMPLOYEES, calendar_scenarios, core_scenarios,
)
from benchmarks.real_object_types import (
    BenchmarkVerdict, ExpectedStatus, ExpectationKind, RuleSpec,
)
from rota.planning.engine import plan
from rota.planning.engine_types import Blocker, DecisionRequiredPayload, PlanningResult


def _case(case_id: str):
    return next(item for item in core_scenarios() if item.case_id == case_id)


def _clean_candidate():
    scenario = _case("calendar-28-feb-2027")
    result = plan(build_planning_state(scenario))
    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 1
    return scenario, result.candidates[0]


def test_fixed_roster_and_core_expectations_are_explicit():
    assert LOCAL_EMPLOYEES == ("A", "B", "C", "D", "E")
    assert EXTERNAL_EMPLOYEES == ("X", "Y")
    for scenario in core_scenarios():
        assert scenario.expected_status in {
            ExpectedStatus.FEASIBLE, ExpectedStatus.DECISION_REQUIRED,
        }
        assert scenario.expectation_kind is not None
        assert scenario.expectation_reason.strip()


def test_calendar_suite_is_exactly_24_known_feasible_cases():
    scenarios = calendar_scenarios()
    assert len(scenarios) == 24
    assert all(item.expected_status == ExpectedStatus.FEASIBLE for item in scenarios)


def test_ladder_1_through_14_is_present():
    covered = {step for scenario in core_scenarios() for step in scenario.ladder_steps}
    assert covered == set(range(1, 15))


def test_absence_ladder_is_monotonic_by_actual_facts():
    ladder = tuple(item for item in core_scenarios() if item.series_id == "absence-ladder")
    assert validate_series_monotonicity(ladder) == ()
    ordered = sorted(ladder, key=lambda item: item.series_level)
    for previous, current in zip(ordered, ordered[1:]):
        assert set(previous.availability) <= set(current.availability)


def test_ground_truth_is_short_and_local_not_general_unsat():
    case_ids = (
        "simple-no-eligible-night",
        "rest-pair-only-A",
        "load-decision-forced-72h",
        "load-boundary-above-60h",
        "external-before-confirmation",
        "external-after-confirmation",
    )
    for case_id in case_ids:
        assert validate_ground_truth(_case(case_id)) == (), case_id


def test_external_before_after_pair_differs_by_confirmed_window():
    before = _case("external-before-confirmation")
    after = _case("external-after-confirmation")
    assert before.availability == after.availability
    assert before.expected_status == ExpectedStatus.DECISION_REQUIRED
    assert after.expected_status == ExpectedStatus.FEASIBLE
    assert not before.external_windows
    assert after.external_windows


def test_replan_has_known_minimum_0_1_2():
    expected = {"replan-min-0": 0, "replan-min-1": 1, "replan-min-2": 2}
    for case_id, count in expected.items():
        scenario = _case(case_id)
        assert scenario.expectation_kind == ExpectationKind.REPLAN
        assert scenario.expected_reshuffles == count
        assert validate_ground_truth(scenario) == ()


def test_fixture_validation_checks_both_weekday_rule_families():
    scenario = _case("calendar-28-feb-2027")
    allowed = RuleSpec(
        "bad-allowed-weekdays", "EMPLOYEE_ALLOWED_WEEKDAYS", "A", weekdays=(0,),
    )
    forbidden = RuleSpec(
        "bad-forbidden-weekdays", "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS",
        "A", shift_kinds=("D",), weekdays=(8,),
    )
    errors_allowed = validate_scenario(replace(scenario, site_rules=(allowed,)))
    errors_forbidden = validate_scenario(replace(scenario, site_rules=(forbidden,)))
    assert any("invalid weekdays" in error for error in errors_allowed)
    assert any("invalid weekdays" in error for error in errors_forbidden)


def test_fixture_validation_rejects_noncanonical_boundary_and_global_duplicate_id():
    scenario = _case("calendar-28-feb-2027")
    first = scenario.boundary_assignments[0]
    shifted = replace(
        first, assignment_id="shifted-boundary",
        start=first.start.replace(hour=6), end=first.end.replace(hour=18),
    )
    errors = validate_scenario(
        replace(scenario, boundary_assignments=(shifted, *scenario.boundary_assignments[1:]))
    )
    assert any("canonical D/N geometry" in error for error in errors)

    duplicate = replace(first, demand_id=f"{scenario.month}-D")
    errors = validate_scenario(replace(scenario, fixed_demand_assignments=(duplicate,)))
    assert any("duplicate assignment_id across fixture" in error for error in errors)


def test_cancelled_boundary_does_not_satisfy_six_day_history():
    scenario = _case("calendar-28-feb-2027")
    cancelled = tuple(replace(item, state="CANCELLED") for item in scenario.boundary_assignments)
    errors = validate_scenario(replace(scenario, boundary_assignments=cancelled))
    assert any("one operative D and N" in error for error in errors)


def test_candidate_checker_detects_missing_coverage():
    scenario, candidate = _clean_candidate()
    checked = check_candidate(scenario, candidate[1:])
    assert any("COVERAGE-01" in error for error in checked.errors)


def test_candidate_checker_detects_illegal_employee():
    scenario, candidate = _clean_candidate()
    night = next(item for item in candidate if item.covers_demand_id.endswith("-N"))
    mutated = [
        replace(item, employee_id="C") if item.assignment_id == night.assignment_id else item
        for item in candidate
    ]
    checked = check_candidate(scenario, mutated)
    assert any("DAY_ONLY-01" in error for error in checked.errors)


def test_candidate_checker_detects_rest_violation():
    scenario, candidate = _clean_candidate()
    night = next(item for item in candidate if item.covers_demand_id.endswith("-N"))
    day_id = f"{night.start_datetime.date()}-D"
    day = next(item for item in candidate if item.covers_demand_id == day_id)
    mutated = [
        replace(item, employee_id=night.employee_id)
        if item.assignment_id == day.assignment_id else item
        for item in candidate
    ]
    checked = check_candidate(scenario, mutated)
    assert any("REST-01" in error for error in checked.errors)


def test_candidate_checker_detects_load_violation():
    scenario, candidate = _clean_candidate()
    target_ids = {f"{scenario.month.replace(day=day)}-D" for day in range(1, 7)}
    mutated = [
        replace(item, employee_id="A") if item.covers_demand_id in target_ids else item
        for item in candidate
    ]
    checked = check_candidate(scenario, mutated)
    assert any("LOAD-01" in error for error in checked.errors)


def test_controlled_shortage_rejects_false_feasible(monkeypatch):
    scenario = _case("simple-no-eligible-night")
    fake = PlanningResult("FEASIBLE", [[]], None, None, [])
    monkeypatch.setattr(benchmark_runner, "plan", lambda _state: fake)
    result = run_case(scenario)
    assert result["verdict"] == BenchmarkVerdict.PRODUCTION_MISMATCH.value
    assert any("false FEASIBLE" in error for error in result["errors"])


def test_decision_payload_wording_does_not_control_basic_pass(monkeypatch):
    scenario = _case("external-before-confirmation")
    payload = DecisionRequiredPayload(
        [], [Blocker("X", "EXTERNAL_SUPPORT_DISABLED")], None, ["whatever UI wording"],
    )
    fake = PlanningResult("DECISION_REQUIRED", [], payload, None, [])
    monkeypatch.setattr(benchmark_runner, "plan", lambda _state: fake)
    result = run_case(scenario)
    assert result["verdict"] == BenchmarkVerdict.PRODUCTION_PASS.value
    assert result["production"]["blockers"][0]["condition"] == "EXTERNAL_SUPPORT_DISABLED"


def test_reshuffle_counter_detects_unnecessary_change():
    scenario = _case("replan-min-0")
    baseline = scenario.fixed_demand_assignments[0]
    candidate = [SimpleNamespace(
        employee_id="A", covers_demand_id=baseline.demand_id,
        role="PRIMARY", state="PLANNED",
    )]
    assert reshuffle_count(scenario, candidate) == 1
    assert scenario.expected_reshuffles == 0


def test_unfrozen_expectation_is_inconclusive_not_production_failure():
    scenario = replace(
        _case("calendar-28-feb-2027"), case_id="exploratory-no-expectation",
        expected_status=None, expectation_kind=None, expectation_reason="",
    )
    result = run_case(scenario)
    assert result["verdict"] == BenchmarkVerdict.INCONCLUSIVE.value


def test_json_and_exact_replay_are_stable():
    scenario = _case("external-before-confirmation")
    first = run_case(scenario)
    second = run_case(scenario)
    assert first["seed"] == second["seed"]
    assert first["input_fingerprint"] == second["input_fingerprint"]
    report = run_matrix((scenario,))
    encoded = json.dumps(_json_value(report), ensure_ascii=False, sort_keys=True)
    assert json.loads(encoded)["results"][0]["case_id"] == scenario.case_id


if __name__ == "__main__":
    print("test_real_object_benchmark OK")
