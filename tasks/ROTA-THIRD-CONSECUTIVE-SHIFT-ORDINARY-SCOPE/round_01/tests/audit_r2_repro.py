from datetime import date

from rota.domain import Employee, Site, SitePlanningRegime, WorkBalance
from rota.planning.engine import plan
from rota.planning.solver import solve
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, PROFILE_ID, SITE_ID, base_state
from tests.test_t032_soft_ranking import _d_demand, _membership


def test_same_schedule_shape_is_scoped_by_site_regime():
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    common = dict(
        employees=(employee,),
        memberships=(_membership("A"),),
        shift_demands=demands,
        work_balances=(WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),),
    )

    ordinary = base_state(**common)
    ordinary_result = plan(ordinary)
    assert ordinary_result.status == "FEASIBLE"
    candidate = ordinary_result.candidates[0]
    assert not any(
        v.rule == "THIRD-CONSECUTIVE-SHIFT-01" for v in validate(ordinary, candidate).violation_details
    )

    ochrona = base_state(
        **common,
        site=Site(SITE_ID, PROFILE_ID, "Test Site", True, planning_regime=SitePlanningRegime.OCHRONA),
    )
    assert solve(ochrona, enforce_load_cap=False).assignments is None
    assert any(v.rule == "THIRD-CONSECUTIVE-SHIFT-01" for v in validate(ochrona, candidate).violation_details)
