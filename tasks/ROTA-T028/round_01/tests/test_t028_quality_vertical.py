"""Owner-accepted 2026-08-26 quality checks through the real T032 backend.

Run explicitly until the owning product changes land:
python -m pytest tasks/ROTA-T028/round_01/tests/test_t028_quality_vertical.py -q
"""
from __future__ import annotations

import pytest

from tools import solver_scenario_lab as lab


@pytest.mark.parametrize("family", lab.QUALITY_FAMILIES)
def test_production_planning_flow_satisfies_owner_quality_contract(family):
    outcome = lab.execute_scenario(lab.build_scenario(family, 3201))

    assert outcome.ok, (
        f"{outcome.category}: {outcome.message}; statuses={outcome.statuses}; "
        f"replay=python -m tools.solver_scenario_lab --family {family} --case-seed 3201"
    )
