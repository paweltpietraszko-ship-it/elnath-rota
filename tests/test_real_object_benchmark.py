"""Adversarial infrastructure tests for ROTA-REAL-OBJECT-01."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

import benchmarks.real_object as benchmark_runner
from benchmarks.real_object import _json_value, run_case, run_matrix
from benchmarks.real_object_checker import check_reference_witness
from benchmarks.real_object_input import validate_scenario
from benchmarks.real_object_oracle import classify_reference
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    core_scenarios,
    demands_for_month,
)
from benchmarks.real_object_types import FixedAssignmentSpec, OracleClass
from rota.planning.engine_types import (
    Blocker,
    BlockingDemand,
    DecisionRequiredPayload,
    LoadBlocker,
    PlanningResult,
)


def _case(case_id: str):
    return next(case for case in core_scenarios() if case.case_id == case_id)


def test_roster_is_fixed_five_local_plus_explicit_external_support():
    assert LOCAL_EMPLOYEES == ("A", "B", "C", "D", "E")
    assert EXTERNAL_EMPLOYEES == ("X", "Y")
    assert len(LOCAL_EMPLOYEES) == 5
    assert LOCAL_EMPLOYEES[2] == "C"


def test_mandatory_ladder_1_through_14_is_present():
    covered = {step for scenario in core_scenarios() for step in scenario.ladder_steps}
    assert covered == set(range(1, 15))


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("reg-001-oct-2026", OracleClass.KNOWN_FEASIBLE),
        ("load-decision-forced-72h", OracleClass.LOAD_DECISION_REQUIRED),
        ("load-boundary-exact-60h", OracleClass.KNOWN_FEASIBLE),
        ("load-boundary-above-60h", OracleClass.LOAD_DECISION_REQUIRED),
        ("simple-no-eligible-night", OracleClass.PROVEN_STAFFING_SHORTAGE),
        ("external-before-confirmation", OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED),
        ("external-after-confirmation", OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT),
    ],
)
def test_key_declared_classes_are_proved_by_oracle(case_id, expected):
    reference = classify_reference(_case(case_id))
    assert reference.expected_class == expected


def test_external_support_pair_is_same_shortage_before_and_after_window():
    before_scenario = _case("external-before-confirmation")
    after_scenario = _case("external-after-confirmation")
    assert before_scenario.availability == after_scenario.availability
    assert before_scenario.month == after_scenario.month
    before = classify_reference(before_scenario)
    after = classify_reference(after_scenario)
    assert before.expected_class == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED
    assert after.expected_class == OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT


@pytest.mark.parametrize(
    "case_id",
    [
        "external-window-wrong-employee",
        "external-window-wrong-site",
        "external-window-inactive",
        "external-window-partial",
        "external-window-wrong-kind",
    ],
)
def test_invalid_external_window_variants_do_not_unlock(case_id):
    reference = classify_reference(_case(case_id))
    assert reference.expected_class == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED


def test_profile_disabled_blocks_even_structurally_valid_external_window():
    reference = classify_reference(_case("external-window-profile-disabled"))
    assert reference.expected_class == OracleClass.PROVEN_STAFFING_SHORTAGE


def test_every_feasible_oracle_witness_passes_independent_checker():
    for case_id in (
        "calendar-28-feb-2027",
        "load-decision-forced-72h",
        "external-after-confirmation",
    ):
        scenario = _case(case_id)
        reference = classify_reference(scenario)
        solves = (
            reference.capped,
            reference.uncapped,
            reference.with_external_probe,
        )
        for solve in solves:
            if solve is None or not solve.witness:
                continue
            windows = scenario.external_windows
            enforce_load = solve is reference.capped
            if solve is reference.with_external_probe:
                by_id = {
                    window.window_id: window
                    for window in (*scenario.external_windows, *scenario.external_probe_windows)
                }
                windows = tuple(by_id[key] for key in sorted(by_id))
            checked = check_reference_witness(
                scenario, solve.witness, windows=windows, enforce_load=enforce_load,
            )
            assert checked.errors == (), (case_id, solve.status_name, checked.errors)
            assert solve.witness_checker_errors == ()


def test_generator_rejects_illegal_boundary_before_production(monkeypatch):
    scenario = _case("calendar-28-feb-2027")
    first = scenario.boundary_assignments[0]
    bad = FixedAssignmentSpec(
        "bad-overlap", first.employee_id,
        first.start + timedelta(hours=1), first.end + timedelta(hours=1),
        "REALIZED", True, None,
    )
    illegal = replace(
        scenario,
        case_id="illegal-boundary",
        boundary_assignments=(*scenario.boundary_assignments, bad),
    )
    assert any("boundary overlap" in error for error in validate_scenario(illegal))

    called = False

    def _must_not_run(_state):
        nonlocal called
        called = True
        raise AssertionError("production must not run for invalid benchmark input")

    monkeypatch.setattr(benchmark_runner, "plan", _must_not_run)
    result = run_case(illegal)
    assert result["production"]["skipped"] is True
    assert called is False


def test_generator_rejects_illegal_fixed_assignment():
    scenario = _case("calendar-28-feb-2027")
    demand = next(item for item in demands_for_month(scenario) if item.kind == "N")
    illegal_fixed = FixedAssignmentSpec(
        "bad-C-night", "C", demand.start, demand.end, "PLANNED", True, demand.demand_id,
    )
    illegal = replace(
        scenario,
        case_id="illegal-fixed",
        fixed_demand_assignments=(illegal_fixed,),
    )
    errors = validate_scenario(illegal)
    assert any("DAY_ONLY C on N" in error for error in errors)


def test_fictional_external_decision_certificate_is_rejected(monkeypatch):
    scenario = _case("external-before-confirmation")
    fake = PlanningResult(
        "DECISION_REQUIRED",
        [],
        DecisionRequiredPayload(
            [BlockingDemand("2099-01-01-N", datetime(2099, 1, 1, 17), datetime(2099, 1, 2, 5))],
            [Blocker("X", "EXTERNAL-01")],
            None,
            ["external support"],
        ),
        None,
        [],
    )
    monkeypatch.setattr(benchmark_runner, "plan", lambda _state: fake)
    result = run_case(scenario)
    assert result["correctness"]["pass"] is False
    assert any("unknown blocking demand" in error for error in result["correctness"]["errors"])


def test_fictional_load_certificate_is_rejected(monkeypatch):
    scenario = _case("load-decision-forced-72h")
    fake = PlanningResult(
        "DECISION_REQUIRED",
        [],
        DecisionRequiredPayload(
            [],
            [Blocker("A", "LOAD-01")],
            LoadBlocker("A", scenario.month, scenario.month + timedelta(days=6), 999),
            ["accept load"],
        ),
        None,
        [],
    )
    monkeypatch.setattr(benchmark_runner, "plan", lambda _state: fake)
    result = run_case(scenario)
    assert result["correctness"]["pass"] is False
    assert any(
        "load certificate is not realizable" in error
        for error in result["correctness"]["errors"]
    )


def test_seed_and_input_fingerprint_are_stable():
    scenario = _case("calendar-28-feb-2027")
    first = run_case(scenario)
    second = run_case(scenario)
    assert first["seed"] == second["seed"]
    assert first["input_fingerprint"] == second["input_fingerprint"]
    assert first["reference"]["expected_class"] == second["reference"]["expected_class"]
    assert first["reference"]["capped"]["witness"] == second["reference"]["capped"]["witness"]


def test_report_is_json_serializable_even_for_decision_payload():
    report = run_matrix((_case("load-decision-forced-72h"),))
    encoded = json.dumps(_json_value(report), ensure_ascii=False, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["results"][0]["case_id"] == "load-decision-forced-72h"


def test_absence_ladder_reports_first_class_change():
    scenarios = tuple(
        scenario for scenario in core_scenarios()
        if scenario.series_id == "absence-ladder"
    )
    report = run_matrix(scenarios)
    transition = report["series_transitions"][0]
    assert transition["series_id"] == "absence-ladder"
    assert transition["first_non_feasible_level"] is not None


if __name__ == "__main__":
    print("test_real_object_benchmark module OK")
