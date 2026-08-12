"""Independent regression audit for the ROTA-T007 round-4 correction."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.engine import plan
from rota.planning.state import SiteRuleApplicability
from tests.support.minimal_state import base_state
from tests.test_audit_t007_r3 import MONTH, MONTH_END, _demand, _employee, _membership, _rule


def test_r4_load_payload_does_not_attribute_an_unrelated_site_rule() -> None:
    """A SiteRule on day 20 is not provenance for a LOAD breach caused
    entirely by immutable work on days 1-6; removing it cannot clear LOAD."""
    historical = tuple(
        Assignment(
            f"realized-{day}",
            "test-v1",
            "A",
            datetime(2026, 10, day, 5),
            datetime(2026, 10, day, 17),
            AssignmentRole.PRIMARY,
            AssignmentState.REALIZED,
            True,
            None,
            None,
        )
        for day in range(1, 7)
    )
    late_demand = _demand("D20", 20)
    unrelated_rule = _rule("RV-unrelated", "B", ["N"])
    state = base_state(
        employees=(_employee("A"), _employee("B")),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=(late_demand,),
        existing_assignments=historical,
        site_rules=(unrelated_rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-unrelated", MONTH, MONTH_END),),
    )

    result = plan(state)
    without_rule = plan(replace(state, site_rules=(), site_rule_applicability=()))

    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert without_rule.status == "DECISION_REQUIRED"
    assert without_rule.decision_payload.load_blocker is not None
    assert all(
        blocker.condition != "RV-unrelated"
        for blocker in result.decision_payload.blockers
    )
