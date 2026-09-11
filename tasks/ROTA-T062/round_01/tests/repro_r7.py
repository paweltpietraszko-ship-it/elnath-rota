from dataclasses import replace
from datetime import date

from rota.domain import Employee
from rota.planning.engine import plan
from tests.support.minimal_state import base_state
from tests.test_t013 import _d_demand, _membership


def test_load_guidance_names_the_change_without_choosing_a_person():
    employee = Employee("A", "Anna", date(2026, 9, 1), None, False)
    state = base_state(
        employees=(employee,),
        memberships=(_membership("A"),),
        shift_demands=(_d_demand("D1", 1),),
    )
    state = replace(
        state,
        profile=replace(state.profile, rolling_7d_decision_threshold_hours=11),
    )

    result = plan(state)

    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    option = result.decision_payload.unblocking_options[0]
    assert option.text == "Dodaj pracownika do obsady i zaplanuj ponownie"
    assert option.target == "obsada"
    assert employee.display_name not in option.text
