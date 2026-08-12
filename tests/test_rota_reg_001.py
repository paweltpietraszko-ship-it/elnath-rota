"""ROTA-REG-001 regression test (tests/regression/oracle_rota_reg_001.md).

Builds a real PlanningState from tests/fixtures/rota_reg_001.json and runs it
through the production rota.planning.engine.plan() path (CP-SAT adapter +
independent validator), then checks the 7 PASS conditions verbatim from the
oracle document. This does not use the standalone PoC script; it exercises
the actual domain types and engine.
"""
from __future__ import annotations

import json
from pathlib import Path

from rota.planning.engine import plan
from tests.support.state_builder import build_state_from_fixture

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "rota_reg_001.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_oracle_condition_1_full_coverage():
    fixture = _load_fixture()
    state = build_state_from_fixture(fixture)
    result = plan(state)
    assert result.status == "FEASIBLE", result.error_message or result.decision_payload
    covered = {a.covers_demand_id for a in result.candidates[0]}
    assert covered == {d.demand_id for d in state.shift_demands}


def test_oracle_condition_2_solver_success():
    state = build_state_from_fixture(_load_fixture())
    result = plan(state)
    assert result.status == "FEASIBLE"


def test_oracle_condition_3_independent_hard_pass():
    from rota.planning.validator import validate

    state = build_state_from_fixture(_load_fixture())
    result = plan(state)
    report = validate(state, result.candidates[0])
    assert report.hard_pass, report.violations


def test_oracle_condition_4_no_hard_violations():
    from rota.planning.validator import validate

    state = build_state_from_fixture(_load_fixture())
    result = plan(state)
    report = validate(state, result.candidates[0])
    assert report.violations == []


def test_oracle_condition_5_mentor_primary_oct_8():
    state = build_state_from_fixture(_load_fixture())
    result = plan(state)
    day8_d = [a for a in result.candidates[0] if a.covers_demand_id == "2026-10-08-D"]
    assert len(day8_d) == 1
    assert day8_d[0].employee_id == "A"


def test_oracle_condition_6_rolling_7d_within_threshold():
    from rota.planning.validator import validate

    fixture = _load_fixture()
    state = build_state_from_fixture(fixture)
    threshold = fixture["rules"]["ROLLING_7D_MAX_HOURS_BEFORE_DECISION_REQUIRED"]
    result = plan(state)
    report = validate(state, result.candidates[0])
    assert all(hours <= threshold for hours in report.maximum_rolling_7d_hours.values())


def test_oracle_condition_7_exact_monthly_hours():
    from rota.planning.validator import validate

    fixture = _load_fixture()
    state = build_state_from_fixture(fixture)
    result = plan(state)
    report = validate(state, result.candidates[0])
    assert report.monthly_hours == fixture["rules"]["TARGET_HOURS"]


if __name__ == "__main__":
    print("test_rota_reg_001 module OK")
