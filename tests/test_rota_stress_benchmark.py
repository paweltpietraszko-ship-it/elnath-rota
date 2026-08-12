"""Smoke tests for the executable PlanningEngine stress benchmark."""
from benchmarks.rota_stress import generate_case, run_benchmark, summary_dict


def test_generated_case_has_a_valid_known_witness():
    case = generate_case(index=2, seed=991827)
    assert case.required_primary_count == 2
    assert len(case.witness) == len(case.state.shift_demands) * 2


def test_stress_benchmark_smoke_is_repeatable_and_clean():
    first = run_benchmark(cases=3, seed=20260812)
    second = run_benchmark(cases=3, seed=20260812)
    assert first.ok, summary_dict(first)["failures"]
    assert second.ok, summary_dict(second)["failures"]
    assert [(r.seed, r.month, r.status) for r in first.results] == [
        (r.seed, r.month, r.status) for r in second.results
    ]
