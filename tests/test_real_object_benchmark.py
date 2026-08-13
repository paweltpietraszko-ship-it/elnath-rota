"""Infrastructure tests for ROTA-REAL-OBJECT-01.

These tests validate the benchmark itself.  Full production correctness is
reported by ``python -m benchmarks.real_object`` and may intentionally be red
when the benchmark discovers a solver defect.
"""
from __future__ import annotations

from benchmarks.real_object import run_case
from benchmarks.real_object_oracle import classify_reference
from benchmarks.real_object_scenarios import EXTERNAL_EMPLOYEES, LOCAL_EMPLOYEES, core_scenarios
from benchmarks.real_object_types import OracleClass


def _case(case_id: str):
    """Return one core case by stable id."""
    return next(case for case in core_scenarios() if case.case_id == case_id)


def test_roster_is_fixed_five_local_plus_explicit_external_support():
    """The benchmark must never recreate the old hidden 6/10-person pool."""
    assert LOCAL_EMPLOYEES == ("A", "B", "C", "D", "E")
    assert EXTERNAL_EMPLOYEES == ("X", "Y")
    assert len(LOCAL_EMPLOYEES) == 5
    assert LOCAL_EMPLOYEES[2] == "C"


def test_declared_reference_classes_are_proved_by_independent_oracle():
    """Curated cases fail as benchmark bugs if their intended class drifts."""
    for scenario in core_scenarios():
        if scenario.declared_class is None:
            continue
        reference = classify_reference(scenario)
        assert reference.expected_class == scenario.declared_class, scenario.case_id


def test_external_support_is_a_true_before_after_pair():
    """No-window shortage must become feasible only after explicit X window."""
    before = classify_reference(_case("external-before-confirmation"))
    after = classify_reference(_case("external-after-confirmation"))
    assert before.expected_class == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED
    assert after.expected_class == OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT
    assert before.with_external_probe is not None
    assert after.without_external is not None


def test_reference_replay_is_deterministic_for_same_case():
    """One case id must produce the same oracle class and witness on replay."""
    scenario = _case("calendar-28-feb-2027")
    first = classify_reference(scenario)
    second = classify_reference(scenario)
    assert first.expected_class == second.expected_class
    assert first.capped.verdict == second.capped.verdict
    assert first.capped.witness == second.capped.witness


def test_runner_preserves_red_production_result_as_data():
    """Runner reports correctness instead of rewriting expectations to green."""
    report = run_case(_case("reg-001-oct-2026"))
    assert report["reference"]["expected_class"] == OracleClass.KNOWN_FEASIBLE.value
    assert report["production"]["status"] in {"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"}
    assert isinstance(report["correctness"]["errors"], list)


if __name__ == "__main__":
    print("test_real_object_benchmark module OK")
