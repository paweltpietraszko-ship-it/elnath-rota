"""Independent validation of production DECISION_REQUIRED payloads.

Every element in a payload must be supported by benchmark evidence.  A single
correct blocker must never mask an unrelated blocker, demand or option.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from benchmarks.real_object_checker import (
    collective_shortage_evidence,
    eligibility_reasons,
    external_unlock_pairs,
    independently_unassignable_demands,
)
from benchmarks.real_object_oracle import verify_load_claim
from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    demands_for_month,
)
from benchmarks.real_object_types import (
    OracleClass,
    ReferenceClassification,
    SolveVerdict,
)


def _overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and end_a > start_b


def _payload_common_errors(scenario, result) -> list[str]:
    if result.status != "DECISION_REQUIRED":
        return [f"expected DECISION_REQUIRED, got {result.status}"]
    if result.candidates:
        return ["DECISION_REQUIRED unexpectedly contains candidate assignments"]
    payload = result.decision_payload
    if payload is None:
        return ["DECISION_REQUIRED lacks decision_payload"]

    demands = {item.demand_id: item for item in demands_for_month(scenario)}
    errors: list[str] = []
    seen_demands: set[str] = set()
    for item in payload.blocking_shift_demands:
        demand = demands.get(item.demand_id)
        if demand is None:
            errors.append(f"payload contains unknown blocking demand: {item.demand_id}")
            continue
        if item.demand_id in seen_demands:
            errors.append(f"payload duplicates blocking demand: {item.demand_id}")
        seen_demands.add(item.demand_id)
        if item.start_datetime != demand.start or item.end_datetime != demand.end:
            errors.append(f"blocking demand interval mismatch: {item.demand_id}")

    known = set((*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES))
    seen_blockers: set[tuple[str, str]] = set()
    for blocker in payload.blockers:
        key = (blocker.employee_id, blocker.condition)
        if blocker.employee_id not in known:
            errors.append(f"payload contains unknown blocker employee: {blocker.employee_id}")
        if not blocker.condition:
            errors.append(f"payload contains empty blocker condition for {blocker.employee_id}")
        if key in seen_blockers:
            errors.append(f"payload duplicates blocker: {blocker.employee_id}/{blocker.condition}")
        seen_blockers.add(key)
    return errors


def _blocking_ids(result) -> set[str]:
    payload = result.decision_payload
    if payload is None:
        return set()
    return {item.demand_id for item in payload.blocking_shift_demands}


def _eligibility_pairs(scenario, demand_ids: set[str]) -> set[tuple[str, str]]:
    demands = {item.demand_id: item for item in demands_for_month(scenario)}
    pairs: set[tuple[str, str]] = set()
    for demand_id in demand_ids:
        demand = demands.get(demand_id)
        if demand is None:
            continue
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES):
            for reason in eligibility_reasons(scenario, employee, demand):
                pairs.add((employee, reason))
    return pairs


def _load_relevant_ids(scenario, load_blocker) -> set[str]:
    if load_blocker is None:
        return set()
    start = datetime.combine(load_blocker.window_start, time())
    end = datetime.combine(load_blocker.window_end + timedelta(days=1), time())
    return {
        demand.demand_id
        for demand in demands_for_month(scenario)
        if _overlap(demand.start, demand.end, start, end)
    }


def _supported_option_kinds(conditions: set[str], *, collective_rest: bool) -> set[str]:
    kinds: set[str] = set()
    if "EXTERNAL-01" in conditions:
        kinds.add("EXTERNAL")
    if "DAY_SHIFT_OFF-01" in conditions:
        kinds.add("DAY_OFF")
    if "LEAVE_GRANTED-01" in conditions:
        kinds.add("LEAVE")
    if "DAY_ONLY-01" in conditions:
        kinds.add("DAY_ONLY")
    if "LOAD-01" in conditions:
        kinds.add("LOAD")
    if "REST-01" in conditions or collective_rest:
        kinds.add("MANUAL")
    if any(condition.startswith("bench-") or condition.endswith("-only") for condition in conditions):
        kinds.add("MANUAL")
    return kinds


def _option_kind(option: str) -> str | None:
    text = option.casefold()
    if "x/y" in text or ("external" in text and "support" in text):
        return "EXTERNAL"
    if "day_only" in text:
        return "DAY_ONLY"
    if "urlop" in text or "leave" in text:
        return "LEAVE"
    if "woln" in text or "day off" in text:
        return "DAY_OFF"
    if "7 kolejnych dni" in text or (">" in text and "h" in text):
        return "LOAD"
    if "ręczn" in text or "manual" in text or "odmro" in text:
        return "MANUAL"
    return None


def _option_errors(payload, supported: set[str], *, required: str | None) -> list[str]:
    if not payload.unblocking_options:
        return ["decision lacks unblocking_options"]
    errors: list[str] = []
    observed: set[str] = set()
    for option in payload.unblocking_options:
        kind = _option_kind(option)
        if kind is None:
            errors.append(f"unrecognized unblocking option: {option}")
            continue
        observed.add(kind)
        if kind not in supported:
            errors.append(f"unrelated unblocking option: {option}")
    if required is not None and required not in observed:
        errors.append(f"decision lacks required {required} unblocking option")
    return errors


def _blocker_errors(payload, supported_pairs: set[tuple[str, str]], extra_pairs=()) -> list[str]:
    supported = set(supported_pairs) | set(extra_pairs)
    errors = []
    for blocker in payload.blockers:
        if (blocker.employee_id, blocker.condition) not in supported:
            errors.append(f"fictional blocker certificate: {blocker.employee_id}/{blocker.condition}")
    return errors


def _load_errors(scenario, reference: ReferenceClassification, result) -> tuple[list[str], dict | None]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors, None
    blocker = payload.load_blocker
    if blocker is None:
        return [*errors, "LOAD_DECISION_REQUIRED lacks load_blocker"], None
    if blocker.hours <= 60:
        errors.append(f"load_blocker does not exceed threshold: {blocker.hours}h")

    proof = verify_load_claim(
        scenario,
        employee_id=blocker.employee_id,
        window_start=blocker.window_start,
        window_end=blocker.window_end,
        hours=blocker.hours,
    )
    if proof.verdict != SolveVerdict.FEASIBLE:
        errors.append("production load certificate is not realizable by independent uncapped oracle")
    if reference.capped.verdict != SolveVerdict.INFEASIBLE:
        errors.append("reference did not prove capped model infeasible")
    if reference.uncapped is None or reference.uncapped.verdict != SolveVerdict.FEASIBLE:
        errors.append("reference did not prove uncapped model feasible")

    relevant = _blocking_ids(result) | _load_relevant_ids(scenario, blocker)
    supported = _eligibility_pairs(scenario, relevant)
    load_employees = {blocker.employee_id}
    if reference.uncapped is not None:
        load_employees |= {item.employee_id for item in reference.uncapped.load_violations}
    extra = {(employee, "LOAD-01") for employee in load_employees}
    errors.extend(_blocker_errors(payload, supported, extra))
    if (blocker.employee_id, "LOAD-01") not in {
        (item.employee_id, item.condition) for item in payload.blockers
    }:
        errors.append("load_blocker employee is not backed by a LOAD-01 blocker")
    conditions = {condition for _, condition in supported | extra}
    errors.extend(_option_errors(payload, _supported_option_kinds(conditions, collective_rest=False), required="LOAD"))
    if payload.blocking_shift_demands:
        invalid = _blocking_ids(result) - relevant
        if invalid:
            errors.append(f"LOAD decision has unrelated blocking demand(s): {sorted(invalid)}")
    return errors, {
        "load_claim": {
            "employee_id": blocker.employee_id,
            "window_start": blocker.window_start,
            "window_end": blocker.window_end,
            "hours": blocker.hours,
            "verdict": proof.verdict.value,
            "status_name": proof.status_name,
        }
    }


def _external_errors(scenario, result) -> tuple[list[str], dict]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors, {}
    if payload.load_blocker is not None:
        errors.append("external-support decision unexpectedly contains load_blocker")
    blocking_ids = _blocking_ids(result)
    if not blocking_ids:
        errors.append("external-support decision lacks blocking_shift_demands")
    individually = independently_unassignable_demands(scenario)
    for demand_id in blocking_ids:
        if demand_id not in individually:
            errors.append(f"external blocking demand is not independently unassignable: {demand_id}")

    unlock_pairs = external_unlock_pairs(scenario)
    if not any(demand_id in blocking_ids for demand_id, _ in unlock_pairs):
        errors.append("external decision names no demand independently unlocked by probe window")
    supported = _eligibility_pairs(scenario, blocking_ids)
    errors.extend(_blocker_errors(payload, supported))
    blocker_pairs = {(item.employee_id, item.condition) for item in payload.blockers}
    if not any(
        demand_id in blocking_ids and (employee, "EXTERNAL-01") in blocker_pairs
        for demand_id, employee in unlock_pairs
    ):
        errors.append("external decision lacks evidenced X/Y EXTERNAL-01 blocker")
    conditions = {condition for _, condition in supported}
    errors.extend(_option_errors(payload, _supported_option_kinds(conditions, collective_rest=False), required="EXTERNAL"))
    return errors, {
        "individually_unassignable": sorted(individually),
        "external_unlock_pairs": sorted(unlock_pairs),
    }


def _shortage_errors(scenario, result) -> tuple[list[str], dict]:
    errors = _payload_common_errors(scenario, result)
    payload = result.decision_payload
    if payload is None:
        return errors, {}
    if payload.load_blocker is not None:
        errors.append("staffing-shortage decision unexpectedly contains load_blocker")
    blocking_ids = _blocking_ids(result)
    if not blocking_ids:
        errors.append("proven staffing shortage lacks blocking_shift_demands")
        return errors, {}
    if not payload.blockers:
        errors.append("proven staffing shortage lacks blockers")

    individually = independently_unassignable_demands(scenario)
    all_individual = all(demand_id in individually for demand_id in blocking_ids)
    collective = collective_shortage_evidence(scenario, blocking_ids)
    if not all_individual and not collective["infeasible"]:
        errors.append("reported blocking demand set is not independently proven infeasible")

    supported = _eligibility_pairs(scenario, blocking_ids)
    rest_pairs = {(employee, "REST-01") for employee in collective["rest_employees"]}
    errors.extend(_blocker_errors(payload, supported, rest_pairs))
    conditions = {condition for _, condition in supported | rest_pairs}
    errors.extend(_option_errors(
        payload,
        _supported_option_kinds(conditions, collective_rest=bool(rest_pairs)),
        required=None,
    ))
    return errors, {
        "all_blocking_demands_individually_unassignable": all_individual,
        "collective": collective,
    }


def check_decision(scenario, reference: ReferenceClassification, result) -> tuple[list[str], dict | None]:
    expected = reference.expected_class
    if expected == OracleClass.LOAD_DECISION_REQUIRED:
        return _load_errors(scenario, reference, result)
    if expected == OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED:
        return _external_errors(scenario, result)
    if expected == OracleClass.PROVEN_STAFFING_SHORTAGE:
        return _shortage_errors(scenario, result)
    return [f"unexpected decision class {expected.value}"], None


if __name__ == "__main__":
    print("real_object_decisions OK")
