from dataclasses import replace
from datetime import date

from rota.domain import Employee
from rota.planning.engine import plan
from tests.support.minimal_state import base_state
from tests.test_t013 import _d_demand, _membership


def test_load_guidance_still_does_not_name_the_correction():
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
    assert option.text == "Sprawdź obsadę i dostępność: Anna, i zaplanuj ponownie"
    assert option.target == "obsada"
    # The message names an inspection, but no actual change from the
    # OWNER-approved action classes (add/change/correct) is stated.
    assert not any(word in option.text for word in ("Dodaj", "Zmień", "Skoryguj"))
