"""Run ROTA-REAL-OBJECT-01 against production PlanningEngine."""
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

from benchmarks.real_object_checker import check_candidate
from benchmarks.real_object_decisions import check_decision
from benchmarks.real_object_input import validate_scenario
from benchmarks.real_object_oracle import classify_reference
from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    all_scenarios,
    calendar_scenarios,
    core_scenarios,
)
from benchmarks.real_object_types import (
    OracleClass,
    ReferenceClassification,
    ReferenceSolve,
    ScenarioSpec,
)
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
        _scenario_dict(scenario), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _solve_dict(reference_solve: ReferenceSolve | None) -> dict | None:
    if reference_solve is None:
        return None
    return {
        "verdict": reference_solve.verdict.value,
        "status_name": reference_solve.status_name,
        "timed_out": reference_solve.timed_out,
        "elapsed_seconds": reference_solve.elapsed_seconds,
        "witness": [
            {"demand_id": demand_id, "employee_id": employee_id}
            for demand_id, employee_id in reference_solve.witness
        ],
        "witness_checker_errors": list(reference_solve.witness_checker_errors),
        "load_violations": _json_value(reference_solve.load_violations),
    }


def _reference_dict(reference: ReferenceClassification) -> dict:
    return {
        "expected_class": reference.expected_class.value,
        "capped": _solve_dict(reference.capped),
        "uncapped": _solve_dict(reference.uncapped),
        "without_external": _solve_dict(reference.without_external),
        "with_external_probe": _solve_dict(reference.with_external_probe),
        "with_external_probe_uncapped": _solve_dict(reference.with_external_probe_uncapped),
    }


def _all_reference_solves(reference: ReferenceClassification) -> tuple[ReferenceSolve, ...]:
    rows = (
        reference.capped,
        reference.uncapped,
        reference.without_external,
        reference.with_external_probe,
        reference.with_external_probe_uncapped,
    )
    return tuple(row for row in rows if row is not None)


def _reference_errors(scenario, reference: ReferenceClassification) -> list[str]:
    errors = []
    if reference.expected_class == OracleClass.INCONCLUSIVE:
        errors.append("reference oracle inconclusive")
    if scenario.declared_class is not None and reference.expected_class != scenario.declared_class:
        errors.append(
            f"scenario declaration mismatch: declared={scenario.declared_class.value} "
            f"oracle={reference.expected_class.value}"
        )
    for solve in _all_reference_solves(reference):
        if solve.witness_checker_errors:
            errors.append(
                f"reference witness failed independent checker ({solve.status_name}): "
                + "; ".join(solve.witness_checker_errors)
            )
    return errors


def _feasible_errors(scenario, expected: OracleClass, result) -> tuple[list[str], dict]:
    if result.status != "FEASIBLE":
        return [f"expected FEASIBLE, got {result.status}"], {}
    if len(result.candidates) != 1:
        return [f"FEASIBLE candidate count must be 1, got {len(result.candidates)}"], {}
    candidate = result.candidates[0]
    checked = check_candidate(scenario, candidate)
    errors = list(checked.errors)
    if expected == OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT:
        if not any(item.employee_id in EXTERNAL_EMPLOYEES for item in candidate):
            errors.append("confirmed-support case is FEASIBLE without actually using X/Y")
    metrics = {
        "checker_errors": list(checked.errors),
        "monthly_hours": dict(checked.monthly_hours),
        "max_rolling_7d_hours": dict(checked.max_rolling_7d_hours),
        "load_violations": _json_value(checked.load_violations),
    }
    return errors, metrics


def _production_errors(scenario, reference, result):
    expected = reference.expected_class
    if expected in {
        OracleClass.KNOWN_FEASIBLE,
        OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT,
    }:
        errors, checker = _feasible_errors(scenario, expected, result)
        return errors, checker, None
    if expected in {
        OracleClass.LOAD_DECISION_REQUIRED,
        OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED,
        OracleClass.PROVEN_STAFFING_SHORTAGE,
    }:
        errors, certificate = check_decision(scenario, reference, result)
        return errors, {}, certificate
    return ["cannot judge production against INCONCLUSIVE reference"], {}, None


def _production_dict(result, elapsed: float, checker: dict, certificate) -> dict:
    payload = result.decision_payload
    return {
        "status": result.status,
        "elapsed_seconds": elapsed,
        "error_message": result.error_message,
        "warnings": list(result.warnings),
        "blocking_demands": _json_value(payload.blocking_shift_demands) if payload else [],
        "blockers": _json_value(payload.blockers) if payload else [],
        "load_blocker": _json_value(payload.load_blocker) if payload and payload.load_blocker else None,
        "unblocking_options": list(payload.unblocking_options) if payload else [],
        "candidate_count": len(result.candidates),
        "independent_candidate_check": checker,
        "decision_certificate_check": certificate,
    }


def _invalid_case_result(scenario: ScenarioSpec, input_errors: tuple[str, ...]) -> dict:
    return {
        "case_id": scenario.case_id,
        "seed": scenario.seed,
        "input_fingerprint": _input_fingerprint(scenario),
        "ladder_steps": list(scenario.ladder_steps),
        "scenario": _scenario_dict(scenario),
        "reference": None,
        "production": {"skipped": True},
        "correctness": {
            "pass": False,
            "errors": [f"benchmark input invalid: {item}" for item in input_errors],
        },
    }


def run_case(scenario: ScenarioSpec) -> dict:
    input_errors = validate_scenario(scenario)
    if input_errors:
        return _invalid_case_result(scenario, input_errors)
    reference = classify_reference(scenario)
    reference_errors = _reference_errors(scenario, reference)
    state = build_planning_state(scenario)
    started = clock.perf_counter()
    result = plan(state)
    elapsed = clock.perf_counter() - started
    production_errors, checker, certificate = _production_errors(
        scenario, reference, result,
    )
    errors = [*reference_errors, *production_errors]
    return {
        "case_id": scenario.case_id,
        "seed": scenario.seed,
        "input_fingerprint": _input_fingerprint(scenario),
        "ladder_steps": list(scenario.ladder_steps),
        "series": {"id": scenario.series_id, "level": scenario.series_level},
        "scenario": _scenario_dict(scenario),
        "reference": _reference_dict(reference),
        "production": _production_dict(result, elapsed, checker, certificate),
        "correctness": {"pass": not errors, "errors": errors},
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _timing_summary(values: list[float]) -> dict:
    return {
        "mean_seconds": statistics.mean(values) if values else 0.0,
        "p50_seconds": _percentile(values, 0.50),
        "p95_seconds": _percentile(values, 0.95),
        "max_seconds": max(values, default=0.0),
    }


def _performance_by_class(results: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for result in results:
        reference = result.get("reference")
        key = reference["expected_class"] if reference else "INVALID_BENCHMARK_INPUT"
        grouped.setdefault(key, []).append(result)
    report = {}
    for class_name, rows in grouped.items():
        times = [
            row["production"]["elapsed_seconds"]
            for row in rows if "elapsed_seconds" in row["production"]
        ]
        report[class_name] = {
            **_timing_summary(times),
            "case_count": len(rows),
            "reference_timeout_count": _reference_timeout_count(rows),
            "production_timeout_count": _production_timeout_count(rows),
        }
    return report


def _reference_timeout_count(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        reference = row.get("reference") or {}
        for key in (
            "capped", "uncapped", "without_external",
            "with_external_probe", "with_external_probe_uncapped",
        ):
            solve = reference.get(key)
            count += int(bool(solve and solve.get("timed_out")))
    return count


def _production_timeout_count(rows: list[dict]) -> int:
    count = 0
    for row in rows:
        production = row.get("production") or {}
        message = (production.get("error_message") or "").upper()
        count += int(production.get("status") == "TECHNICAL_ERROR" and "UNKNOWN" in message)
    return count


def _series_errors(scenarios: Iterable[ScenarioSpec]) -> list[str]:
    grouped: dict[str, list[ScenarioSpec]] = {}
    for scenario in scenarios:
        if scenario.series_id:
            grouped.setdefault(scenario.series_id, []).append(scenario)
    errors = []
    for series_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.series_level)
        for previous, current in zip(ordered, ordered[1:]):
            if not set(previous.availability) <= set(current.availability):
                errors.append(
                    f"series {series_id} is not monotonic: level {previous.series_level} "
                    f"availability is not a subset of level {current.series_level}"
                )
    return errors


def _series_transitions(results: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in results:
        series = row.get("series") or {}
        if series.get("id"):
            grouped.setdefault(series["id"], []).append(row)
    transitions = []
    for series_id, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: row["series"]["level"])
        first = next((row for row in ordered if _non_feasible_reference(row)), None)
        transitions.append({
            "series_id": series_id,
            "levels": [
                {
                    "level": row["series"]["level"],
                    "case_id": row["case_id"],
                    "reference_class": row["reference"]["expected_class"] if row.get("reference") else None,
                }
                for row in ordered
            ],
            "first_non_feasible_level": first["series"]["level"] if first else None,
            "first_non_feasible_case_id": first["case_id"] if first else None,
        })
    return transitions


def _non_feasible_reference(row: dict) -> bool:
    return bool(
        row.get("reference")
        and row["reference"]["expected_class"] != OracleClass.KNOWN_FEASIBLE.value
    )


def run_matrix(scenarios: Iterable[ScenarioSpec]) -> dict:
    scenario_rows = tuple(scenarios)
    benchmark_errors = _series_errors(scenario_rows)
    results = [run_case(scenario) for scenario in scenario_rows]
    passed = sum(row["correctness"]["pass"] for row in results)
    case_pass = passed == len(results)
    return {
        "benchmark": "ROTA-REAL-OBJECT-01",
        "base_production_sha": BASE_PRODUCTION_SHA,
        "roster": {
            "local": list(LOCAL_EMPLOYEES),
            "day_only": "C",
            "external_support": list(EXTERNAL_EMPLOYEES),
        },
        "ladder_steps_covered": sorted({step for item in scenario_rows for step in item.ladder_steps}),
        "benchmark_errors": benchmark_errors,
        "correctness": {
            "passed": passed,
            "failed": len(results) - passed,
            "total": len(results),
            "pass": case_pass and not benchmark_errors,
        },
        "performance": _performance_by_class(results),
        "series_transitions": _series_transitions(results),
        "results": results,
    }


def _select_suite(name: str) -> tuple[ScenarioSpec, ...]:
    if name == "core":
        return core_scenarios()
    if name == "calendar":
        return calendar_scenarios()
    return all_scenarios()


def _select_cases(scenarios, case_ids: list[str], seed: int | None):
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
    correctness = report["correctness"]
    print(
        f"ROTA-REAL-OBJECT-01: {correctness['passed']}/{correctness['total']} "
        f"case correctness PASS; {correctness['failed']} case FAIL"
    )
    for error in report["benchmark_errors"]:
        print(f"BENCHMARK FAIL: {error}")
    print(f"LADDER: {report['ladder_steps_covered']}")
    for result in report["results"]:
        marker = "PASS" if result["correctness"]["pass"] else "FAIL"
        expected = result["reference"]["expected_class"] if result.get("reference") else "INVALID_BENCHMARK_INPUT"
        actual = result["production"].get("status", "SKIPPED")
        print(f"{marker:4} {result['case_id']} seed={result['seed']}: expected={expected} production={actual}")
        for error in result["correctness"]["errors"]:
            print(f"     - {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("core", "calendar", "all"), default="core")
    parser.add_argument("--case", action="append", default=[], help="exact case_id; repeatable")
    parser.add_argument("--seed", type=int, help="assert selected case(s) use this exact seed")
    parser.add_argument("--json", type=Path, help="write full audit report JSON")
    args = parser.parse_args(argv)
    scenarios = _select_cases(_select_suite(args.suite), args.case, args.seed)
    report = run_matrix(scenarios)
    if args.json:
        args.json.write_text(
            json.dumps(_json_value(report), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    _print_summary(report)
    return 0 if report["correctness"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
