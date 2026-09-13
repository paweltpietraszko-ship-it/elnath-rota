from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteRuleVersion,
)
from rota.planning.engine import plan
from rota.planning.site_rules import EMPLOYEE_ALLOWED_SHIFT_KINDS
from rota.planning.state import SiteRuleApplicability
from tests.support.minimal_state import MONTH, ReadinessSource, ReadinessState, SITE_ID, base_state


def _employee() -> Employee:
    return Employee("E1", "E1", date(2020, 1, 1), None, False)


def _membership(kind: MembershipKind) -> SiteMembership:
    return SiteMembership(
        "E1", SITE_ID, kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
    )


def _legacy_n_demand() -> ShiftDemand:
    # No T065 role and no explicit shift_kind: this is the preserved legacy
    # path classified as N from the existing profile, not a new ORDINARY row.
    return ShiftDemand(
        "LEGACY-N", "v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1,
        shift_kind=None, required_role=None,
    )


def _d_only_rule() -> SiteRuleVersion:
    return SiteRuleVersion(
        "RV-D-ONLY", "R-D-ONLY", SITE_ID, RuleCategory.LOCAL_RULE,
        EMPLOYEE_ALLOWED_SHIFT_KINDS, {"employee_id": "E1", "allowed_shift_kinds": ["D"]},
        RuleEnforcement.HARD, RuleResolution.RESOLVED, MONTH, None,
        datetime(2026, 10, 1), "COORD", None, None, None, None,
    )


def test_legacy_ordinary_dn_site_rule_is_not_silently_widened() -> None:
    demand = _legacy_n_demand()
    rule = _d_only_rule()
    state = base_state(
        employees=(_employee(),),
        memberships=(_membership(MembershipKind.LOCAL),),
        shift_demands=(demand,),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability(rule.rule_version_id, MONTH, date(2026, 10, 31)),),
    )
    result = plan(state)
    assert result.status != "FEASIBLE", "legacy D-only SiteRule was silently treated as no restriction"


def test_legacy_ordinary_dn_external_window_is_not_silently_widened() -> None:
    demand = _legacy_n_demand()
    window = ExternalSupportWindow(
        "W-D-ONLY", "E1", SITE_ID, datetime(2026, 10, 1), datetime(2026, 10, 3), True, ShiftKind.D,
    )
    state = base_state(
        employees=(_employee(),),
        memberships=(_membership(MembershipKind.EXTERNAL_SUPPORT),),
        shift_demands=(demand,),
        external_windows=(window,),
    )
    result = plan(state)
    assert result.status != "FEASIBLE", "legacy D-only external window was silently treated as unrestricted"
