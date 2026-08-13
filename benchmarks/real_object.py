"""Run ROTA-REAL-OBJECT-01 against production PlanningEngine.

Correctness is judged against an independent reference oracle/checker.
Performance is reported separately and is not a correctness SLA.
"""
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

from benchmarks.real_object_checker import (
    check_candidate,
    external_unlock_pairs,
    independently_unassignable_demands,
)
from benchmarks.real_object_input import validate_scenario
from benchmarks.real_object_oracle import classify_reference, verify_load_claim
from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    all_scenarios,
    calendar_scenarios,
    core_scenarios,
    demands_for_month,
)
from benchmarks.real_object_types import (
    OracleClass,
    ReferenceClassification,
    ReferenceSolve,
    ScenarioSpec,
    SolveVerdict,
)
from rota.planning.engine import plan

BASE_PRODUCTION_SHA = "e010f004e90a1e4f426bb72298e7307045d32b56"


def _json_value(value):
    """Recursively convert dataclasses/enums/date-time values to JSON-safe data."""
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


def _reference_errors(
    scenario: ScenarioSpec, reference: ReferenceClassification,
) -> list[str]:
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


def _valid_blocking_ids(scenario: ScenarioSpec) -> set[str]:
    return {demand.demand_id for demand in demands_for_month(scenario)}


def _payload_common_errors(scenario: ScenarioSpec, result) -> list[str]:
    if result.status != "DECISION_REQUIRED":
        return [f"expected DECISION_REQUIRED, got {result.status}"]
    if result.candidates:
        return ["DECISION_REQUIRED unexpectedly contains candidate assignments"]
    payload = result.decision_payload
    if payload is None:
        return ["DECISION_REQUIRED lacks decision_payload"]
    valid_demands = _valid_blocking_ids(scenario)
    blocking_ids = {item.demand_id for item in payload.blocking_shift_demands}
    invalid = sorted(blocking_ids - valid_demands)
    errors = [f"payload contains unknown blocking demand(s): {invalid}"] if invalid else []
    known_employees = set((*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES))
    unknown_blockers = sorted({
        blocker.employee_id for blocker in payload.blockers
        if blocker.employee_id not in known_employees
    })
    if unknown_blockers:
        errors.append(f"payload contains unknown blocker employee(s): {unknown_blockers}")
    return errors


def _load_decision_errors(
    scenario: ScenarioSpec, reference: ReferenceClassification, result,
) -> tuple[list[str], dict | None]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors, None
    blocker = payload.load_blocker
    if blocker is None:
        return [*errors, "LOAD_DECISION_REQUIRED lacks load_blocker"], None
    if blocker.hours <= 60:
        errors.append(f"load_blocker does not exceed threshold: {blocker.hours}h")
    if not any(
        item.employee_id == blocker.employee_id and item.condition == "LOAD-01"
        for item in payload.blockers
    ):
        errors.append("load_blocker employee is not backed by a LOAD-01 blocker")

    proof = verify_load_claim(
        scenario,
        employee_id=blocker.employee_id,
        window_start=blocker.window_start,
        window_end=blocker.window_end,
        hours=blocker.hours,
    )
    if proof.verdict != SolveVerdict.FEASIBLE:
        errors.append(
            "production load certificate is not realizable by independent uncapped oracle"
        )
    if reference.capped.verdict != SolveVerdict.INFEASIBLE:
        errors.append("reference did not prove capped model infeasible")
    if reference.uncapped is None or reference.uncapped.verdict != SolveVerdict.FEASIBLE:
        errors.append("reference did not prove uncapped model feasible")
    return errors, _solve_dict(proof)


def _external_decision_errors(
    scenario: ScenarioSpec, result,
) -> list[str]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors
    evidence = independently_unassignable_demands(scenario)
    unlock_pairs = external_unlock_pairs(scenario)
    blocking_ids = {item.demand_id for item in payload.blocking_shift_demands}
    unlock_demands = {demand_id for demand_id, _ in unlock_pairs}
    if not blocking_ids.intersection(unlock_demands):
        errors.append(
            "external-support decision does not name a demand independently unlocked by probe window"
        )
    blocker_pairs = {(item.employee_id, item.condition) for item in payload.blockers}
    if not any(
        demand_id in blocking_ids and (employee_id, "EXTERNAL-01") in blocker_pairs
        for demand_id, employee_id in unlock_pairs
    ):
        errors.append(
            "external-support decision lacks independently evidenced X/Y EXTERNAL-01 blocker"
        )
    if not payload.unblocking_options:
        errors.append("external-support decision lacks any unblocking option")
    if not evidence:
        errors.append("external-support class has no independently unassignable current demand")
    return errors


def _shortage_decision_errors(
    scenario: ScenarioSpec, result,
) -> list[str]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors
    evidence = independently_unassignable_demands(scenario)
    blocking_ids = {item.demand_id for item in payload.blocking_shift_demands}
    if not blocking_ids:
        errors.append("proven staffing shortage lacks blocking_shift_demands")
        return errors
    evidenced_ids = blocking_ids.intersection(evidence)
    if not evidenced_ids:
        errors.append(
            "reported blocking demands are not independently unassignable under current facts"
        )
        return errors

    for blocker in payload.blockers:
        if not any(
            blocker.condition in evidence[demand_id].get(blocker.employee_id, ())
            for demand_id in evidenced_ids
        ):
            errors.append(
                f"fictional blocker certificate: {blocker.employee_id}/{blocker.condition}"
            )
    return errors


def _decision_errors(
    scenario: ScenarioSpec, reference: ReferenceClassification, result,
) -> tuple[list[str], dict | None]:
    expected = reference.expected_class
    if expected == OracleClass.LOAD_DECISION_REQUIRED:
        return _load_decision_errors(scenario, reference, result)
    if expected == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED:
        return _external_decision_errors(scenario, result), None
    if expected == OracleClass.PROVEN_STAFFING_SHORTAGE:
        return _shortage_decision_errors(scenario, result), None
    return [f"unexpected decision class {expected.value}"], None


def _feasible_errors(
    scenario: ScenarioSpec, expected: OracleClass, result,
) -> tuple[list[str], dict]:
    if result.status != "FEASIBLE":
        return [f"expected FEASIBLE, got {result.status}"], {}
    if len(result.candidates) != 1:
        return [f"FEASIBLE candidate count must be 1, got {len(result.candidates)}"], {}
    candidate = result.candidates[0]
    checked = check_candidate(scenario, candidate)
    errors = list(checked.errors)
    if expected == OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT:
        used_external = [
            item for item in candidate if item.employee_id in EXTERNAL_EMPLOYEES
        ]
        if not used_external:
            errors.append("confirmed-support case is FEASIBLE without actually using X/Y")
    metrics = {
        "checker_errors": list(checked.errors),
        "monthly_hours": dict(checked.monthly_hours),
        "max_rolling_7d_hours": dict(checked.max_rolling_7d_hours),
        "load_violations": _json_value(checked.load_violations),
    }
    return errors, metrics


def _production_errors(
    scenario: ScenarioSpec, reference: ReferenceClassification, result,
) -> tuple[list[str], dict, dict | None]:
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
        errors, certificate = _decision_errors(scenario, reference, result)
        return errors, {}, certificate
    return ["cannot judge production against INCONCLUSIVE reference"], {}, None


def _production_dict(result, elapsed: float, checker: dict, certificate: dict | None) -> dict:
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
    """Validate fixture, classify independently, then invoke production."""
    input_errors = validate_scenario(scenario)
    if input_errors:
        return _invalid_case_result(scenario, input_errors)

    reference = classify_reference(scenario)
    reference_errors = _reference_errors(scenario, reference)
    state = build_planning_state(scenario)
    started = clock.perf_counter()
    result = plan(state)
    production_seconds = clock.perf_counter() - started
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
        "production": _production_dict(
            result, production_seconds, checker, certificate,
        ),
        "correctness": {"pass": not errors, "errors": errors},
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(
        0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))),
    )
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
        if not reference:
            grouped.setdefault("INVALID_BENCHMARK_INPUT", []).append(result)
            continue
        grouped.setdefault(reference["expected_class"], []).append(result)

    report = {}
    for class_name, rows in grouped.items():
        production_times = [
            row["production"]["elapsed_seconds"]
            for row in rows if "elapsed_seconds" in row["production"]
        ]
        reference_timeouts = 0
        production_timeouts = 0
        for row in rows:
            reference = row.get("reference") or {}
            for key in (
                "capped", "uncapped", "without_external",
                "with_external_probe", "with_external_probe_uncapped",
            ):
                solve = reference.get(key)
                reference_timeouts += int(bool(solve and solve.get("timed_out")))
            production = row.get("production") or {}
            message = (production.get("error_message") or "").upper()
            production_timeouts += int(
                production.get("status") == "TECHNICAL_ERROR" and "UNKNOWN" in message
            )
        report[class_name] = {
            **_timing_summary(production_times),
            "case_count": len(rows),
            "reference_timeout_count": reference_timeouts,
            "production_timeout_count": production_timeouts,
        }
    return report


def _series_transitions(results: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in results:
        series = row.get("series") or {}
        series_id = series.get("id")
        if series_id:
            grouped.setdefault(series_id, []).append(row)
    transitions = []
    for series_id, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: row["series"]["level"])
        first_changed = next(
            (
                row for row in ordered
                if row.get("reference")
                and row["reference"]["expected_class"] != OracleClass.KNOWN_FEASIBLE.value
            ),
            None,
        )
        transitions.append({
            "series_id": series_id,
            "levels": [
                {
                    "level": row["series"]["level"],
                    "case_id": row["case_id"],
                    "reference_class": (
                        row["reference"]["expected_class"] if row.get("reference") else None
                    ),
                }
                for row in ordered
            ],
            "first_non_feasible_level": (
                first_changed["series"]["level"] if first_changed else None
            ),
            "first_non_feasible_case_id": (
                first_changed["case_id"] if first_changed else None
            ),
        })
    return transitions


def run_matrix(scenarios: Iterable[ScenarioSpec]) -> dict:
    results = [run_case(scenario) for scenario in scenarios]
    passed = sum(row["correctness"]["pass"] for row in results)
    ladder_covered = sorted({
        step for scenario in scenarios for step in scenario.ladder_steps
    })
    return {
        "benchmark": "ROTA-REAL-OBJECT-01",
        "base_production_sha": BASE_PRODUCTION_SHA,
        "roster": {
            "local": list(LOCAL_EMPLOYEES),
            "day_only": "C",
            "external_support": list(EXTERNAL_EMPLOYEES),
        },
        "ladder_steps_covered": ladder_covered,
        "correctness": {
            "passed": passed,
            "failed": len(results) - passed,
            "total": len(results),
            "pass": passed == len(results),
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


def _select_cases(
    scenarios: tuple[ScenarioSpec, ...],
    case_ids: list[str],
    seed: int | None,
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
            raise ValueError(
                f"seed {seed} does not match selected case(s): {', '.join(mismatched)}"
            )
    return selected


def _print_summary(report: dict) -> None:
    correctness = report["correctness"]
    print(
        f"ROTA-REAL-OBJECT-01: {correctness['passed']}/{correctness['total']} "
        f"correctness PASS; {correctness['failed']} FAIL"
    )
    print(f"LADDER: {report['ladder_steps_covered']}")
    for result in report["results"]:
        marker = "PASS" if result["correctness"]["pass"] else "FAIL"
        expected = (
            result["reference"]["expected_class"] if result.get("reference")
            else "INVALID_BENCHMARK_INPUT"
        )
        actual = result["production"].get("status", "SKIPPED")
        print(
            f"{marker:4} {result['case_id']} seed={result['seed']}: "
            f"expected={expected} production={actual}"
        )
        for error in result["correctness"]["errors"]:
            print(f"     - {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", choices=("core", "calendar", "all"), default="core",
    )
    parser.add_argument(
        "--case", action="append", default=[], help="exact case_id; repeatable",
    )
    parser.add_argument(
        "--seed", type=int, help="assert the selected case(s) use this exact seed",
    )
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
