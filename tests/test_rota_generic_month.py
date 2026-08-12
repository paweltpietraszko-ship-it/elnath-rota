"""Genericity check: the engine is not hardcoded to October 2026 / employees A-E.

Runs a second, differently-shaped scenario through the exact same
rota.planning.engine.plan() code path used by ROTA-REG-001:
- different year/month (February 2027, 28 days, different weekday layout);
- different shift boundary times (06:00-18:00 / 18:00-06:00, not 05:00-17:00);
- different employee set and rule assignments;
- different training-S date and mentor.

This does not replace ROTA-REG-001 (which pins the verified reference
numbers); it demonstrates the same code produces a valid schedule for an
unrelated month, which is the measurable "any month" acceptance criterion.
"""
from __future__ import annotations

from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.state_builder import build_state_from_fixture

FIXTURE = {
    "period": {"year": 2027, "month": 2},
    "employees": ["P", "Q", "R", "S", "T"],
    "shifts": {
        "D": {"start": "06:00", "end": "18:00"},
        "N": {"start": "18:00", "end_next_day": "06:00"},
    },
    "demand": {"D_per_day": 1, "N_per_day": 1},
    "rules": {
        "DAY_ONLY": {"R": True},
        "DAY_SHIFT_OFF": {"P": [5, 15, 25]},
        "LEAVE_GRANTED": {"Q": [{"from": 10, "to": 12}]},
        "UNAVAILABLE_24H": {"S": [3, 20]},
        "EXTERNAL_SUPPORT": {"X": False, "Y": False},
        "ROLLING_7D_MAX_HOURS_BEFORE_DECISION_REQUIRED": 60,
        "TRAINING_S": {"date": 14, "shift": "D", "mentor": "P", "hours": 6, "requires_mentor_primary": True},
        "TARGET_HOURS": {"P": 134, "Q": 134, "R": 134, "S": 134, "T": 136},
    },
}


def test_generic_month_is_feasible_with_full_coverage():
    state = build_state_from_fixture(FIXTURE, profile_id="OCHRONA-FEB")
    result = plan(state)
    assert result.status == "FEASIBLE", result.error_message or result.decision_payload
    covered = {a.covers_demand_id for a in result.candidates[0]}
    assert covered == {d.demand_id for d in state.shift_demands}
    assert len(state.shift_demands) == 28 * 2


def test_generic_month_independent_hard_pass():
    state = build_state_from_fixture(FIXTURE, profile_id="OCHRONA-FEB")
    result = plan(state)
    report = validate(state, result.candidates[0])
    assert report.hard_pass, report.violations


def test_generic_month_respects_day_only_and_mentor_rule():
    state = build_state_from_fixture(FIXTURE, profile_id="OCHRONA-FEB")
    result = plan(state)
    assignments = result.candidates[0]
    assert all(not (a.employee_id == "R" and a.start_datetime.time().hour == 18) for a in assignments)
    day14_d = [a for a in assignments if a.covers_demand_id == "2027-02-14-D"]
    assert len(day14_d) == 1
    assert day14_d[0].employee_id == "P"


if __name__ == "__main__":
    print("test_rota_generic_month module OK")
