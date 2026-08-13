"""Run the architect-owned benchmark against production PlanningEngine.

Correctness is judged against an independent reference oracle and checker.
Performance is reported separately and has no pass/fail SLA in this benchmark.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time as clock
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from benchmarks.real_object_checker import check_candidate
from benchmarks.real_object_oracle import classify_reference
from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    all_scenarios,
    calendar_scenarios,
    core_scenarios,
)
from benchmarks.real_object_types import OracleClass, ReferenceClassification, ScenarioSpec
from rota.planning.engine import plan


def _reference_errors(scenario: ScenarioSpec, reference: ReferenceClassification) -> list[str]:
    """Return benchmark-construction errors before production is judged."""
    errors = []
    if reference.expected_class == OracleClass.INCONCLUSIVE:
        errors.append("reference oracle inconclusive")
    if scenario.declared_class is not None and reference.expected_class != scenario.declared_class:
        errors.append(
            f"scenario declaration mismatch: declared={scenario.declared_class.value} "
            f"oracle={reference.expected_class.value}"
        )
    return errors


def _decision_errors(expected: OracleClass, result) -> list[str]:
    """Check DECISION_REQUIRED payload by semantics, not UI wording."""
    if result.status != "DECISION_REQUIRED":
        return [f"expected DECISION_REQUIRED, got {result.status}"]
    if result.candidates:
        return ["DECISION_REQUIRED unexpectedly contains candidate assignments"]
    payload = result.decision_payload
    if payload is None:
        return ["DECISION_REQUIRED lacks decision_payload"]
    if expected == OracleClass.LOAD_DECISION_REQUIRED:
        if payload.load_blocker is None:
            return ["LOAD_DECISION_REQUIRED lacks load_blocker"]
        if payload.load_blocker.hours <= 60:
            return [f"load_blocker does not exceed threshold: {payload.load_blocker.hours}h"]
    if expected == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED:
        external_block = any(
            blocker.employee_id in EXTERNAL_EMPLOYEES and blocker.condition == "EXTERNAL-01"
            for blocker in payload.blockers
        )
        if not external_block:
            return ["external-support decision lacks X/Y EXTERNAL-01 blocker evidence"]
    if expected == OracleClass.PROVEN_STAFFING_SHORTAGE and not payload.blocking_shift_demands:
        return ["proven staffing shortage lacks blocking_shift_demands"]
    return []


def _feasible_errors(scenario: ScenarioSpec, expected: OracleClass, result) -> tuple[list[str], dict]:
    """Check a production FEASIBLE result with the independent checker."""
    errors = []
    if result.status != "FEASIBLE":
        return [f"expected FEASIBLE, got {result.status}"], {}
    if not result.candidates:
        return ["FEASIBLE contains no candidate"], {}
    candidate = result.candidates[0]
    checked = check_candidate(scenario, candidate)
    errors.extend(checked.errors)
    if expected == OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT:
        if not any(assignment.employee_id in EXTERNAL_EMPLOYEES for assignment in candidate):
            errors.append("reference proves external support is necessary, but candidate uses no X/Y")
    metrics = {
        "monthly_hours": dict(checked.monthly_hours),
        "max_rolling_7d_hours": dict(checked.max_rolling_7d_hours),
    }
    return errors, metrics


def _production_errors(scenario: ScenarioSpec, reference: ReferenceClassification, result) -> tuple[list[str], dict]:
    """Compare production result with the independently classified expected class."""
    expected = reference.expected_class
    if expected in {OracleClass.KNOWN_FEASIBLE, OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT}:
        return _feasible_errors(scenario, expected, result)
    if expected in {
        OracleClass.LOAD_DECISION_REQUIRED,
        OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED,
        OracleClass.PROVEN_STAFFING_SHORTAGE,
    }:
        return _decision_errors(expected, result), {}
    return ["cannot judge production against INCONCLUSIVE reference"], {}


def _solve_dict(reference_solve) -> dict | None:
    """Serialize one optional ReferenceSolve."""
    if reference_solve is None:
        return None
    return {
        "verdict": reference_solve.verdict.value,
        "elapsed_seconds": reference_solve.elapsed_seconds,
        "witness": [{"demand_id": demand, "employee_id": employee} for demand, employee in reference_solve.witness],
    }


def _reference_dict(reference: ReferenceClassification) -> dict:
    """Serialize reference classification without hiding intermediate proofs."""
    return {
        "expected_class": reference.expected_class.value,
        "capped": _solve_dict(reference.capped),
        "uncapped": _solve_dict(reference.uncapped),
        "without_external": _solve_dict(reference.without_external),
        "with_external_probe": _solve_dict(reference.with_external_probe),
    }


def _scenario_dict(scenario: ScenarioSpec) -> dict:
    """Serialize the scenario inputs needed to replay or audit it."""
    raw = asdict(scenario)
    raw["month"] = scenario.month.isoformat()
    raw["declared_class"] = scenario.declared_class.value if scenario.declared_class else None
    for record in raw["availability"]:
        record["start_date"] = record["start_date"].isoformat()
        record["end_date"] = record["end_date"].isoformat()
    for key in ("boundary_assignments", "fixed_demand_assignments"):
        for assignment in raw[key]:
            assignment["start"] = assignment["start"].isoformat()
            assignment["end"] = assignment["end"].isoformat()
    for key in ("external_windows", "external_probe_windows"):
        for window in raw[key]:
            window["start"] = window["start"].isoformat()
            window["end"] = window["end"].isoformat()
    return raw


def run_case(scenario: ScenarioSpec) -> dict:
    """Classify independently, then run production code and compare outcomes."""
    reference = classify_reference(scenario)
    reference_errors = _reference_errors(scenario, reference)
    state = build_planning_state(scenario)
    started = clock.perf_counter()
    result = plan(state)
    production_seconds = clock.perf_counter() - started
    production_errors, metrics = _production_errors(scenario, reference, result)
    errors = [*reference_errors, *production_errors]
    payload = result.decision_payload
    return {
        "case_id": scenario.case_id,
        "scenario": _scenario_dict(scenario),
        "reference": _reference_dict(reference),
        "production": {
            "status": result.status,
            "elapsed_seconds": production_seconds,
            "error_message": result.error_message,
            "blocking_demands": [item.demand_id for item in payload.blocking_shift_demands] if payload else [],
            "blockers": [
                {"employee_id": item.employee_id, "condition": item.condition}
                for item in payload.blockers
            ] if payload else [],
            "load_blocker": asdict(payload.load_blocker) if payload and payload.load_blocker else None,
            "unblocking_option_count": len(payload.unblocking_options) if payload else 0,
            "candidate_count": len(result.candidates),
            "metrics": metrics,
        },
        "correctness": {"pass": not errors, "errors": errors},
    }


def _percentile(values: list[float], percentile: float) -> float:
    """Return a deterministic nearest-rank percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _performance(results: list[dict]) -> dict:
    """Summarize timing without converting speed into correctness."""
    values = [result["production"]["elapsed_seconds"] for result in results]
    return {
        "mean_seconds": statistics.mean(values) if values else 0.0,
        "p50_seconds": _percentile(values, 0.50),
        "p95_seconds": _percentile(values, 0.95),
        "max_seconds": max(values, default=0.0),
    }


def run_matrix(scenarios: Iterable[ScenarioSpec]) -> dict:
    """Run a fixed scenario collection and return one structured report."""
    results = [run_case(scenario) for scenario in scenarios]
    passed = sum(result["correctness"]["pass"] for result in results)
    return {
        "benchmark": "ROTA-REAL-OBJECT-01",
        "roster": {
            "local": list(LOCAL_EMPLOYEES),
            "day_only": "C",
            "external_support": list(EXTERNAL_EMPLOYEES),
        },
        "correctness": {
            "passed": passed,
            "failed": len(results) - passed,
            "total": len(results),
            "pass": passed == len(results),
        },
        "performance": _performance(results),
        "results": results,
    }


def _select_suite(name: str) -> tuple[ScenarioSpec, ...]:
    """Resolve CLI suite name."""
    if name == "core":
        return core_scenarios()
    if name == "calendar":
        return calendar_scenarios()
    return all_scenarios()


def _select_cases(scenarios: tuple[ScenarioSpec, ...], case_ids: list[str]) -> tuple[ScenarioSpec, ...]:
    """Filter exact case ids and fail loudly on typos."""
    if not case_ids:
        return scenarios
    by_id = {scenario.case_id: scenario for scenario in scenarios}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"unknown case_id(s): {', '.join(missing)}")
    return tuple(by_id[case_id] for case_id in case_ids)


def _print_summary(report: dict) -> None:
    """Print a concise human summary while JSON remains the audit artifact."""
    correctness = report["correctness"]
    print(
        f"ROTA-REAL-OBJECT-01: {correctness['passed']}/{correctness['total']} correctness PASS; "
        f"{correctness['failed']} FAIL"
    )
    for result in report["results"]:
        marker = "PASS" if result["correctness"]["pass"] else "FAIL"
        expected = result["reference"]["expected_class"]
        actual = result["production"]["status"]
        print(f"{marker:4} {result['case_id']}: expected={expected} production={actual}")
        for error in result["correctness"]["errors"]:
            print(f"     - {error}")
    perf = report["performance"]
    print(
        "PERFORMANCE (not SLA): "
        f"mean={perf['mean_seconds']:.3f}s p50={perf['p50_seconds']:.3f}s "
        f"p95={perf['p95_seconds']:.3f}s max={perf['max_seconds']:.3f}s"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; non-zero means correctness or benchmark construction failed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("core", "calendar", "all"), default="core")
    parser.add_argument("--case", action="append", default=[], help="exact case_id; repeatable")
    parser.add_argument(
        "--json", type=Path,
        help="write replayable report JSON; scenario/classification are deterministic, timing values naturally vary",
    )
    args = parser.parse_args(argv)
    scenarios = _select_cases(_select_suite(args.suite), args.case)
    report = run_matrix(scenarios)
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _print_summary(report)
    return 0 if report["correctness"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
