from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from rota.planning.engine_types import DecisionRequiredPayload
from tools import solver_scenario_lab as lab


def test_real_runner_calls_the_imported_production_plan_and_validator(monkeypatch):
    plan_calls = 0
    validation_calls = 0
    real_plan_month = lab.plan_month
    real_validate = lab.validate

    def counted_plan_month(*args, **kwargs):
        nonlocal plan_calls
        plan_calls += 1
        return real_plan_month(*args, **kwargs)

    def counted_validate(*args, **kwargs):
        nonlocal validation_calls
        validation_calls += 1
        return real_validate(*args, **kwargs)

    monkeypatch.setattr(lab, "plan_month", counted_plan_month)
    monkeypatch.setattr(lab, "validate", counted_validate)

    outcome = lab.execute_scenario(lab.build_scenario("ordinary_12h_single_5", 10))

    assert outcome.ok, outcome.message
    assert plan_calls == 1
    assert validation_calls >= 1


@pytest.mark.parametrize("variant", lab.OBJECT_VARIANTS, ids=lambda item: item.name)
@pytest.mark.parametrize("seed", range(10, 15))
def test_every_returned_candidate_has_complete_coverage_and_nonoverlapping_work_periods(variant, seed):
    spec = lab.build_scenario(variant.name, seed)
    outcome = lab.execute_scenario(spec)
    assert outcome.ok, outcome.message

    expected_demands = lab.calendar.monthrange(spec.month.year, spec.month.month)[1] * 2
    for item in outcome.candidates:
        assignments = item["assignments"]
        by_demand = defaultdict(list)
        for assignment in assignments:
            by_demand[assignment["covers_demand_id"]].append(assignment)
        assert len(by_demand) == expected_demands
        assert {len(group) for group in by_demand.values()} == {spec.required_primary_count}

        periods_by_employee = defaultdict(dict)
        for assignment in assignments:
            employee_periods = periods_by_employee[assignment["employee_id"]]
            period = employee_periods.setdefault(
                assignment["work_period_id"],
                {
                    "start": datetime.fromisoformat(assignment["start"]),
                    "end": datetime.fromisoformat(assignment["end"]),
                    "rest": assignment["required_rest_after_hours"],
                },
            )
            period["start"] = min(period["start"], datetime.fromisoformat(assignment["start"]))
            period["end"] = max(period["end"], datetime.fromisoformat(assignment["end"]))
            period["rest"] = max(period["rest"], assignment["required_rest_after_hours"])

        for periods in periods_by_employee.values():
            ordered = sorted(periods.values(), key=lambda value: value["start"])
            for previous, following in zip(ordered, ordered[1:]):
                assert previous["end"] + timedelta(hours=previous["rest"]) <= following["start"]


def test_incomplete_decision_required_payload_must_not_be_reported_as_pass(monkeypatch):
    empty_payload = DecisionRequiredPayload(
        blocking_shift_demands=[], blockers=[], load_blocker=None, unblocking_options=[]
    )
    fake_result = SimpleNamespace(
        status="DECISION_REQUIRED",
        candidates=[],
        decision_payload=empty_payload,
        warnings=[],
        error_message=None,
    )
    monkeypatch.setattr(lab, "plan_month", lambda *args, **kwargs: fake_result)

    outcome = lab.execute_scenario(lab.build_scenario("ordinary_12h_single_5", 10))

    assert not outcome.ok
    assert outcome.category == "SOLVER_MISMATCH"


@pytest.mark.parametrize(
    ("family", "seed"),
    [
        *[(variant.name, 14) for variant in lab.OBJECT_VARIANTS],
        ("ochrona_24h_single_4", 11),
        ("ochrona_24h_single_4", 12),
        ("ochrona_24h_single_4", 13),
    ],
)
def test_actual_decision_required_results_are_explained(family, seed, monkeypatch):
    decision_payloads = []
    real_plan_month = lab.plan_month
    real_replan = lab.replan

    def capture(callable_, *args, **kwargs):
        result = callable_(*args, **kwargs)
        if result.status == "DECISION_REQUIRED":
            decision_payloads.append(result.decision_payload)
        return result

    monkeypatch.setattr(
        lab, "plan_month", lambda *args, **kwargs: capture(real_plan_month, *args, **kwargs)
    )
    monkeypatch.setattr(lab, "replan", lambda *args, **kwargs: capture(real_replan, *args, **kwargs))

    outcome = lab.execute_scenario(lab.build_scenario(family, seed))

    assert outcome.ok, outcome.message
    assert decision_payloads
    for payload in decision_payloads:
        assert payload is not None
        assert payload.blocking_shift_demands or payload.load_blocker is not None
        assert payload.unblocking_options
        assert payload.blockers or payload.load_blocker is not None


def test_24h_scenario_does_not_preconfigure_the_rest_that_backend_owns():
    spec = lab.build_scenario("ochrona_24h_single_5", 10)

    shifts = lab._shifts(spec)

    assert {shift.required_rest_hours for shift in shifts} == {11}
