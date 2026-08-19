"""Run the real-object benchmark against production PlanningEngine."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time as clock
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Iterable

from benchmarks.real_object_checker import check_candidate, reshuffle_count, validate_ground_truth
from benchmarks.real_object_input import validate_scenario, validate_series_monotonicity
from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES, LOCAL_EMPLOYEES, all_scenarios, calendar_scenarios, core_scenarios,
)
from benchmarks.real_object_types import BenchmarkVerdict, ExpectedStatus, ExpectationKind, ScenarioSpec
from rota.planning.engine import plan

BASE_PRODUCTION_SHA = "e010f004e90a1e4f426bb72298e7307045d32b56"


def _json_value(value):
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def _scenario_dict(scenario: ScenarioSpec) -> dict:
    raw = _json_value(scenario)
    raw["local_roster"] = list(LOCAL_EMPLOYEES)
    raw["day_only"] = "C"
    raw["external_memberships"] = {
        employee: "EXTERNAL_SUPPORT" for employee in EXTERNAL_EMPLOYEES
    }
    return raw


def _input_fingerprint(scenario: ScenarioSpec) -> str:
    encoded = json.dumps(
        _scenario_dict(scenario), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _payload_dict(result) -> dict:
    payload = result.decision_payload
    if payload is None:
        return {
            "blocking_demands": [], "blockers": [], "load_blocker": None,
            "unblocking_options": [],
        }
    return {
        "blocking_demands": _json_value(payload.blocking_shift_demands),
        "blockers": _json_value(payload.blockers),
        "load_blocker": _json_value(payload.load_blocker),
        "unblocking_options": list(payload.unblocking_options),
    }


def _candidate_contains_pair(candidate, employee_id: str, demand_id: str) -> bool:
    return any(
        item.employee_id == employee_id
        and item.covers_demand_id == demand_id
        and (item.state.value if hasattr(item.state, "value") else str(item.state)) != "CANCELLED"
        for item in candidate
    )


def _feasible_errors(scenario: ScenarioSpec, result) -> tuple[list[str], dict]:
    if result.status != ExpectedStatus.FEASIBLE.value:
        return [f"expected FEASIBLE, got {result.status}"], {}
    # T017: FEASIBLE legally returns 1-3 pairwise-diverse candidates; the
    # benchmark ground truth/checker still only inspects the first.
    if not (1 <= len(result.candidates) <= 3):
        return [f"FEASIBLE candidate count must be 1-3, got {len(result.candidates)}"], {}
    candidate = result.candidates[0]
    checked = check_candidate(scenario, candidate)
    errors = list(checked.errors)
    reshuffles = None
    if scenario.expectation_kind == ExpectationKind.EXTERNAL_AFTER:
        demand_id = scenario.expected_demand_ids[0]
        employee = scenario.expected_employee_id
        if not employee or not _candidate_contains_pair(candidate, employee, demand_id):
            errors.append(f"confirmed external resource is not used on {demand_id}")
    if scenario.expectation_kind == ExpectationKind.REPLAN:
        reshuffles = reshuffle_count(scenario, candidate)
        if reshuffles != scenario.expected_reshuffles:
            errors.append(f"reshuffle count {reshuffles}, expected {scenario.expected_reshuffles}")
    return errors, {
        "checker_errors": list(checked.errors),
        "monthly_hours": dict(checked.monthly_hours),
        "max_rolling_7d_hours": dict(checked.max_rolling_7d_hours),
        "load_violations": _json_value(checked.load_violations),
        "reshuffle_count": reshuffles,
    }


def _decision_errors(scenario: ScenarioSpec, result) -> tuple[list[str], dict]:
    if result.status == ExpectedStatus.DECISION_REQUIRED.value:
        return [], {}
    if result.status != ExpectedStatus.FEASIBLE.value:
        return [f"expected DECISION_REQUIRED, got {result.status}"], {}
    errors = ["controlled shortage/load case returned false FEASIBLE"]
    checker = {}
    if 1 <= len(result.candidates) <= 3:
        checked = check_candidate(scenario, result.candidates[0])
        checker = {
            "checker_errors": list(checked.errors),
            "monthly_hours": dict(checked.monthly_hours),
            "max_rolling_7d_hours": dict(checked.max_rolling_7d_hours),
            "load_violations": _json_value(checked.load_violations),
        }
        errors.extend(f"false-FEASIBLE candidate: {item}" for item in checked.errors)
    return errors, checker


def _production_errors(scenario: ScenarioSpec, result) -> tuple[list[str], dict]:
    if scenario.expected_status == ExpectedStatus.FEASIBLE:
        return _feasible_errors(scenario, result)
    if scenario.expected_status == ExpectedStatus.DECISION_REQUIRED:
        return _decision_errors(scenario, result)
    return [], {}


def _invalid_result(
    scenario: ScenarioSpec, verdict: BenchmarkVerdict, errors: tuple[str, ...] | list[str],
) -> dict:
    return {
        "case_id": scenario.case_id,
        "seed": scenario.seed,
        "input_fingerprint": _input_fingerprint(scenario),
        "scenario": _scenario_dict(scenario),
        "verdict": verdict.value,
        "production": {"skipped": True},
        "errors": list(errors),
    }


def _run_unfrozen(scenario: ScenarioSpec) -> dict:
    state = build_planning_state(scenario)
    started = clock.perf_counter()
    result = plan(state)
    elapsed = clock.perf_counter() - started
    return {
        "case_id": scenario.case_id,
        "seed": scenario.seed,
        "input_fingerprint": _input_fingerprint(scenario),
        "scenario": _scenario_dict(scenario),
        "verdict": BenchmarkVerdict.INCONCLUSIVE.value,
        "production": {
            "status": result.status,
            "elapsed_seconds": elapsed,
            "error_message": result.error_message,
            "warnings": list(result.warnings),
            **_payload_dict(result),
        },
        "errors": ["scenario has no frozen expected_status"],
    }


def _run_expected(scenario: ScenarioSpec) -> dict:
    state = build_planning_state(scenario)
    started = clock.perf_counter()
    result = plan(state)
    elapsed = clock.perf_counter() - started
    errors, checker = _production_errors(scenario, result)
    verdict = BenchmarkVerdict.PRODUCTION_PASS if not errors else BenchmarkVerdict.PRODUCTION_MISMATCH
    return {
        "case_id": scenario.case_id,
        "seed": scenario.seed,
        "input_fingerprint": _input_fingerprint(scenario),
        "ladder_steps": list(scenario.ladder_steps),
        "series": {"id": scenario.series_id, "level": scenario.series_level},
        "scenario": _scenario_dict(scenario),
        "expected": {
            "status": scenario.expected_status.value,
            "kind": scenario.expectation_kind.value if scenario.expectation_kind else None,
            "reason": scenario.expectation_reason,
            "expected_demand_ids": list(scenario.expected_demand_ids),
            "expected_employee_id": scenario.expected_employee_id,
            "expected_reshuffles": scenario.expected_reshuffles,
        },
        "verdict": verdict.value,
        "production": {
            "status": result.status,
            "elapsed_seconds": elapsed,
            "error_message": result.error_message,
            "warnings": list(result.warnings),
            "candidate_count": len(result.candidates),
            "candidate_check": checker,
            **_payload_dict(result),
        },
        "errors": errors,
    }


def run_case(scenario: ScenarioSpec) -> dict:
    """Validate fixture and small ground-truth claim before calling production."""
    structural = validate_scenario(scenario)
    if structural:
        return _invalid_result(scenario, BenchmarkVerdict.BENCHMARK_INVALID, structural)
    if scenario.expected_status is None:
        return _run_unfrozen(scenario)
    ground_truth = validate_ground_truth(scenario)
    if ground_truth:
        return _invalid_result(scenario, BenchmarkVerdict.BENCHMARK_INVALID, ground_truth)
    return _run_expected(scenario)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _performance(results: list[dict]) -> dict:
    values = [
        row["production"]["elapsed_seconds"]
        for row in results if "elapsed_seconds" in row.get("production", {})
    ]
    return {
        "mean_seconds": statistics.mean(values) if values else 0.0,
        "p50_seconds": _percentile(values, 0.50),
        "p95_seconds": _percentile(values, 0.95),
        "max_seconds": max(values, default=0.0),
    }


def _series_summary(results: list[dict]) -> list[dict]:
    grouped = {}
    for row in results:
        series = row.get("series") or {}
        if series.get("id"):
            grouped.setdefault(series["id"], []).append(row)
    summaries = []
    for series_id, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: row["series"]["level"])
        summaries.append({
            "series_id": series_id,
            "levels": [
                {
                    "level": row["series"]["level"], "case_id": row["case_id"],
                    "expected_status": row.get("expected", {}).get("status"),
                    "production_status": row.get("production", {}).get("status"),
                    "verdict": row["verdict"],
                }
                for row in ordered
            ],
        })
    return summaries


def run_matrix(scenarios: Iterable[ScenarioSpec]) -> dict:
    scenarios = tuple(scenarios)
    series_errors = validate_series_monotonicity(scenarios)
    results = [run_case(scenario) for scenario in scenarios]
    counts = {
        verdict.value: sum(row["verdict"] == verdict.value for row in results)
        for verdict in BenchmarkVerdict
    }
    all_pass = counts[BenchmarkVerdict.PRODUCTION_PASS.value] == len(results)
    return {
        "benchmark": "ROTA-REAL-OBJECT-01",
        "base_production_sha": BASE_PRODUCTION_SHA,
        "roster": {
            "local": list(LOCAL_EMPLOYEES), "day_only": "C",
            "external_support": list(EXTERNAL_EMPLOYEES),
        },
        "benchmark_errors": list(series_errors),
        "verdict_counts": counts,
        "pass": all_pass and not series_errors,
        "performance": _performance(results),
        "series": _series_summary(results),
        "results": results,
    }


def _select_suite(name: str) -> tuple[ScenarioSpec, ...]:
    if name == "core":
        return core_scenarios()
    if name == "calendar":
        return calendar_scenarios()
    return all_scenarios()


def _select_cases(
    scenarios: tuple[ScenarioSpec, ...], case_ids: list[str], seed: int | None,
) -> tuple[ScenarioSpec, ...]:
    selected = scenarios
    if case_ids:
        by_id = {scenario.case_id: scenario for scenario in scenarios}
        missing = [case_id for case_id in case_ids if case_id not in by_id]
        if missing:
            raise ValueError(f"unknown case_id(s): {', '.join(missing)}")
        selected = tuple(by_id[case_id] for case_id in case_ids)
    if seed is not None:
        mismatched = [item.case_id for item in selected if item.seed != seed]
        if mismatched:
            raise ValueError(f"seed {seed} does not match selected case(s): {', '.join(mismatched)}")
    return selected


def _print_summary(report: dict) -> None:
    counts = report["verdict_counts"]
    print(
        "ROTA-REAL-OBJECT-01: "
        f"{counts['PRODUCTION_PASS']} PASS, "
        f"{counts['PRODUCTION_MISMATCH']} MISMATCH, "
        f"{counts['BENCHMARK_INVALID']} INVALID, "
        f"{counts['INCONCLUSIVE']} INCONCLUSIVE"
    )
    for error in report["benchmark_errors"]:
        print(f"BENCHMARK_INVALID: {error}")
    for row in report["results"]:
        expected = row.get("expected", {}).get("status", "UNFROZEN")
        actual = row.get("production", {}).get("status", "SKIPPED")
        print(f"{row['verdict']:20} {row['case_id']}: expected={expected} actual={actual}")
        for error in row["errors"]:
            print(f"  - {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("core", "calendar", "all"), default="core")
    parser.add_argument("--case", action="append", default=[], help="exact case_id; repeatable")
    parser.add_argument("--seed", type=int, help="assert selected case(s) use this exact seed")
    parser.add_argument("--json", type=Path, help="write full report JSON")
    args = parser.parse_args(argv)
    scenarios = _select_cases(_select_suite(args.suite), args.case, args.seed)
    report = run_matrix(scenarios)
    if args.json:
        args.json.write_text(
            json.dumps(_json_value(report), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    _print_summary(report)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
