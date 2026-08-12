"""Independent boundary audit for the ROTA-T007 round-5 correction."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.planning.engine import plan
from rota.planning.state import SiteRuleApplicability
from tests.support.minimal_state import base_state
from tests.test_audit_t007_r3 import (
    MONTH,
    MONTH_END,
    _employee,
    _membership,
    _night_demand,
    _rule,
)


def _realized_day_assignments() -> tuple[Assignment, ...]:
    return tuple(
        Assignment(
            f"realized-{day}", "test-v1", "A",
            datetime(2026, 10, day, 5), datetime(2026, 10, day, 17),
            AssignmentRole.PRIMARY, AssignmentState.REALIZED,
            True, None, None,
        )
        for day in range(4, 9)
    )


def test_r5_load_provenance_includes_overnight_shift_entering_worst_window() -> None:
    """N starts Oct 1, but contributes 5h to the actual worst Oct 2-8
    rolling window. Its SiteRule exclusion is therefore relevant provenance."""
    night = _night_demand("N1", 1)
    rule = _rule("RV-night-cause", "B", ["D"])
    state = base_state(
        employees=(_employee("A"), _employee("B")),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=(night,),
        existing_assignments=_realized_day_assignments(),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-night-cause", MONTH, MONTH_END),),
    )

    result = plan(state)
    without_rule = plan(replace(state, site_rules=(), site_rule_applicability=()))

    assert without_rule.status == "FEASIBLE"
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker.window_start == date(2026, 10, 2)
    assert any(
        blocker.condition == "RV-night-cause"
        for blocker in result.decision_payload.blockers
    )
