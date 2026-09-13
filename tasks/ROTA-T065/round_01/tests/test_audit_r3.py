from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

from rota.domain import (
    Employee,
    EmployeeRole,
    ExternalSupportWindow,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteRuleVersion,
    StandardShift,
)
from rota.planning.eligibility import check_eligibility
from rota.planning.engine import plan
from rota.planning.shift_catalog import generate_catalog_demands
from rota.planning.site_rules import EMPLOYEE_ALLOWED_SHIFT_KINDS
from rota.planning.state import SiteRuleApplicability
from tests.support.minimal_state import (
    MONTH,
    ReadinessSource,
    ReadinessState,
    SITE_ID,
    base_profile,
    base_state,
)


SPRZEDAWCA = EmployeeRole.SPRZEDAWCA_ZALOGA


def _employee() -> Employee:
    return Employee("E1", "E1", date(2020, 1, 1), None, False)


def _membership(*, external: bool = False) -> SiteMembership:
    return SiteMembership(
        "E1",
        SITE_ID,
        MembershipKind.EXTERNAL_SUPPORT if external else MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
        allowed_roles=frozenset({SPRZEDAWCA}),
    )


def _allowed_kind_rule(kind: ShiftKind = ShiftKind.D) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id="RV-D-ONLY",
        rule_id="R-D-ONLY",
        site_id=SITE_ID,
        category=RuleCategory.LOCAL_RULE,
        rule_kind=EMPLOYEE_ALLOWED_SHIFT_KINDS,
        structured_parameters={"employee_id": "E1", "allowed_shift_kinds": [kind.value]},
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_from=MONTH,
        effective_to=None,
        changed_at=datetime(2026, 10, 1),
        changed_by="COORD",
        supersedes_rule_version_id=None,
        description=None,
        source=None,
        reason=None,
    )


def _role_demand(kind: ShiftKind) -> ShiftDemand:
    return ShiftDemand(
        "D-1",
        "v1",
        datetime(2026, 10, 1, 22, 0),
        datetime(2026, 10, 2, 6, 0),
        1,
        shift_kind=kind,
        required_role=SPRZEDAWCA,
    )


def test_new_ordinary_site_rule_result_cannot_depend_on_technical_dn() -> None:
    rule = _allowed_kind_rule()
    results = []
    for kind in (ShiftKind.D, ShiftKind.N):
        result = check_eligibility(
            _employee(),
            _membership(),
            _role_demand(kind),
            kind,
            base_profile(),
            [],
            [],
            SITE_ID,
            [rule],
        )
        results.append((result.eligible, result.blocked_reason))
    assert results[0] == results[1], results


def test_new_ordinary_external_result_cannot_depend_on_technical_dn() -> None:
    window = ExternalSupportWindow(
        "W-D-ONLY",
        "E1",
        SITE_ID,
        datetime(2026, 10, 1),
        datetime(2026, 10, 3),
        True,
        ShiftKind.D,
    )
    results = []
    for kind in (ShiftKind.D, ShiftKind.N):
        result = check_eligibility(
            _employee(),
            _membership(external=True),
            _role_demand(kind),
            kind,
            replace(base_profile(), external_support_enabled=True),
            [],
            [window],
            SITE_ID,
        )
        results.append((result.eligible, result.blocked_reason))
    assert results[0] == results[1], results


def test_roleless_new_ordinary_catalog_demand_does_not_inherit_dn_site_rule() -> None:
    # OWNER_DECISION 2026-09-13: a new ORDINARY row may legitimately have no
    # store role.  It is still new ORDINARY, so its technical catalog kind
    # cannot turn an old D/N SiteRule into business meaning.
    profile = replace(
        base_profile(),
        standard_shifts=[
            StandardShift(
                ShiftKind.D,
                time(22, 0),
                time(6, 0),
                True,
                1,
                active_weekdays=(4,),
                required_role=None,
            )
        ],
    )
    generated = generate_catalog_demands(profile, MONTH)
    demand = generated[0]
    rule = _allowed_kind_rule(ShiftKind.N)
    state = base_state(
        profile=profile,
        employees=(_employee(),),
        memberships=(_membership(),),
        shift_demands=(demand,),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability(rule.rule_version_id, MONTH, date(2026, 10, 31)),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE", result.status
