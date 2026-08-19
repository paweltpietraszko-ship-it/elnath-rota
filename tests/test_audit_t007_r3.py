"""Independent adversarial audit coverage for ROTA-T007, round 3."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    SiteMembership,
    SiteRuleVersion,
)
from rota.persistence.db import connect
from rota.persistence.decision_ledger import record_decision
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.planning.engine import plan
from rota.planning.site_rules import (
    EMPLOYEE_ALLOWED_SHIFT_KINDS,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
)
from rota.planning.state import SiteRuleApplicability
from rota.site_memory_types import NewRuleContent
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


MONTH = date(2026, 10, 1)
MONTH_END = date(2026, 10, 31)


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2026, 9, 1), None, day_only)


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(
        employee_id,
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )


def _demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "test-v1",
        datetime(2026, 10, day, 5),
        datetime(2026, 10, day, 17),
        1,
    )


def _night_demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "test-v1",
        datetime(2026, 10, day, 17),
        datetime(2026, 10, day + 1, 5),
        1,
    )


def _rule(rule_version_id: str, employee_id: str, allowed: object, *, description: str | None = None) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id,
        f"rule-{rule_version_id}",
        SITE_ID,
        RuleCategory.LOCAL_RULE,
        EMPLOYEE_ALLOWED_SHIFT_KINDS,
        {"employee_id": employee_id, "allowed_shift_kinds": allowed},
        RuleEnforcement.HARD,
        RuleResolution.RESOLVED,
        MONTH,
        None,
        datetime(2026, 9, 1),
        "COORD",
        None,
        description,
        None,
        None,
    )


def _content(rule_kind: str, parameters: object) -> NewRuleContent:
    return NewRuleContent(
        category=RuleCategory.LOCAL_RULE,
        rule_kind=rule_kind,
        structured_parameters=parameters,
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_to=None,
        description=None,
        source=None,
        reason=None,
    )


@pytest.mark.parametrize("profile_id", ["pilot-alpha", "variant-7-without-ochrona-name"])
def test_r3_profile_scope_does_not_depend_on_profile_id_text(profile_id: str) -> None:
    """SITE-RULE-EXEC-01-R1 clarification, consequence 1/5."""
    rule = _rule("RV-profile", "A", ["N"])
    state = base_state(
        employees=(_employee("A"),),
        memberships=(_membership("A"),),
        shift_demands=(_demand("D1", 1),),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-profile", MONTH, MONTH_END),),
    )
    state = replace(
        state,
        site=replace(state.site, profile_id=profile_id),
        profile=replace(state.profile, profile_id=profile_id, display_name="unrelated display text"),
    )

    result = plan(state)

    assert result.status == "DECISION_REQUIRED"
    assert any(blocker.condition == "Koliduje z zapisaną regułą obiektu" for blocker in result.decision_payload.blockers)


@pytest.mark.parametrize(
    ("rule_kind", "parameters"),
    [
        (
            EMPLOYEE_ALLOWED_SHIFT_KINDS,
            {"employee_id": "A", "allowed_shift_kinds": [["D"]]},
        ),
        (
            EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
            {"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": [{"kind": "D"}]},
        ),
    ],
)
def test_r3_json_valid_nested_values_fail_closed_at_public_plan_boundary(
    tmp_path, rule_kind: str, parameters: object
) -> None:
    """Malformed JSON shapes accepted by generic T005 transport must become
    TECHNICAL_ERROR with provenance, never escape plan() as a raw TypeError."""
    conn = connect(tmp_path / "rota.db")
    decision = record_decision(
        conn,
        site_id=SITE_ID,
        rule_id="R-malformed",
        statement="malformed executable rule",
        coordinator_id="COORD",
        recorded_at=datetime(2026, 9, 1),
        effective_from=MONTH,
        rel=None,
        rule_content=_content(rule_kind, parameters),
    )
    resolved, unresolved, applicability = assemble_monthly_site_rules(conn, SITE_ID, MONTH)
    conn.close()
    state = base_state(
        employees=(_employee("A"),),
        memberships=(_membership("A"),),
        shift_demands=(_demand("D1", 1),),
        site_rules=resolved,
        unresolved_site_rules=unresolved,
        site_rule_applicability=applicability,
    )

    result = plan(state)

    assert result.status == "TECHNICAL_ERROR"
    assert decision.rule_version_id in result.error_message


def _record_chain_rule_decision(conn, *, statement, recorded_at, effective_from, rel, allowed_shift_kinds):
    """Round 4 FINDING R4-2: mechanical helper extraction to bring the test
    below it under SIZE_FUNC=50 -- no assertion changes."""
    rule_content = (
        _content(EMPLOYEE_ALLOWED_SHIFT_KINDS, {"employee_id": "A", "allowed_shift_kinds": allowed_shift_kinds})
        if allowed_shift_kinds is not None
        else None
    )
    return record_decision(
        conn, site_id=SITE_ID, rule_id="R-chain", statement=statement, coordinator_id="COORD",
        recorded_at=recorded_at, effective_from=effective_from, rel=rel, rule_content=rule_content,
    )


@pytest.mark.parametrize("relation", ["supersedes", "corrects"])
def test_r3_monthly_projection_uses_real_chain_for_change_then_reject(tmp_path, relation: str) -> None:
    """Acceptance 2: real T005 selection, mid-month change and reject gap."""
    conn = connect(tmp_path / "rota.db")
    first = _record_chain_rule_decision(
        conn, statement="N only", recorded_at=datetime(2026, 9, 1), effective_from=MONTH,
        rel=None, allowed_shift_kinds=["N"],
    )
    second = _record_chain_rule_decision(
        conn, statement="D only", recorded_at=datetime(2026, 9, 2), effective_from=date(2026, 10, 16),
        rel=relation, allowed_shift_kinds=["D"],
    )
    _record_chain_rule_decision(
        conn, statement="rejected", recorded_at=datetime(2026, 9, 3), effective_from=date(2026, 10, 21),
        rel="rejects", allowed_shift_kinds=None,
    )

    resolved, unresolved, applicability = assemble_monthly_site_rules(conn, SITE_ID, MONTH)
    conn.close()

    assert unresolved == ()
    assert {rule.rule_version_id for rule in resolved} == {
        first.rule_version_id,
        second.rule_version_id,
    }
    spans = {
        item.rule_version_id: (item.applies_from, item.applies_to)
        for item in applicability
    }
    assert spans == {
        first.rule_version_id: (date(2026, 10, 1), date(2026, 10, 15)),
        second.rule_version_id: (date(2026, 10, 16), date(2026, 10, 20)),
    }


@pytest.mark.parametrize(
    ("rule_kind", "parameters"),
    [
        (
            EMPLOYEE_ALLOWED_SHIFT_KINDS,
            {"employee_id": "B", "allowed_shift_kinds": ["N"]},
        ),
        (
            EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
            {"employee_id": "B", "weekdays": [4], "forbidden_shift_kinds": ["D"]},
        ),
    ],
)
def test_r3_cross_demand_conflict_preserves_site_rule_provenance(
    rule_kind: str, parameters: object
) -> None:
    """A valid SiteRule can be the necessary cause of a REST conflict even
    when each demand separately has one eligible employee. The resulting
    DECISION_REQUIRED must still expose its exact rule_version_id."""
    day = _demand("D1", 1)  # Thursday
    night = _night_demand("N1", 1)
    rule = SiteRuleVersion(
        "RV-cross-conflict",
        "R-cross-conflict",
        SITE_ID,
        RuleCategory.LOCAL_RULE,
        rule_kind,
        parameters,
        RuleEnforcement.HARD,
        RuleResolution.RESOLVED,
        MONTH,
        None,
        datetime(2026, 9, 1),
        "COORD",
        None,
        None,
        None,
        None,
    )
    state = base_state(
        employees=(_employee("A"), _employee("B", day_only=True)),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=(day, night),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-cross-conflict", MONTH, MONTH_END),),
    )

    result = plan(state)

    assert result.status == "DECISION_REQUIRED"
    assert any(
        blocker.condition == "Koliduje z zapisaną regułą obiektu"
        for blocker in result.decision_payload.blockers
    )


@pytest.mark.parametrize(
    ("rule_kind", "parameters"),
    [
        (
            EMPLOYEE_ALLOWED_SHIFT_KINDS,
            {"employee_id": "B", "allowed_shift_kinds": ["N"]},
        ),
        (
            EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
            {
                "employee_id": "B",
                "weekdays": [4, 5, 6, 7, 1, 2],
                "forbidden_shift_kinds": ["D"],
            },
        ),
    ],
)
def test_r3_load_fallback_preserves_site_rule_provenance(
    rule_kind: str, parameters: object
) -> None:
    """The same provenance invariant applies when SiteRule exclusions force
    the only eligible employee over LOAD-01 rather than into REST-01."""
    demands = tuple(_demand(f"D{day}", day) for day in range(1, 7))
    rule = SiteRuleVersion(
        "RV-load-cause",
        "R-load-cause",
        SITE_ID,
        RuleCategory.LOCAL_RULE,
        rule_kind,
        parameters,
        RuleEnforcement.HARD,
        RuleResolution.RESOLVED,
        MONTH,
        None,
        datetime(2026, 9, 1),
        "COORD",
        None,
        None,
        None,
        None,
    )
    state = base_state(
        employees=(_employee("A"), _employee("B")),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=demands,
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-load-cause", MONTH, MONTH_END),),
    )

    result = plan(state)

    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert any(
        blocker.condition == "Koliduje z zapisaną regułą obiektu"
        for blocker in result.decision_payload.blockers
    )


def test_r3_site_rule_hard_then_minimal_reshuffle_then_soft() -> None:
    """T007 sequencing: HARD SiteRule > T006 reshuffle > ordinary SOFT."""
    d1, d2, d4 = _demand("D1", 1), _demand("D2", 2), _demand("D4", 4)
    baselines = tuple(
        Assignment(
            f"orig-{employee}",
            "test-v1",
            employee,
            demand.start_datetime,
            demand.end_datetime,
            AssignmentRole.PRIMARY,
            AssignmentState.PLANNED,
            False,
            demand.demand_id,
            None,
        )
        for employee, demand in (("A", d1), ("B", d2), ("D", d4))
    )
    leave_plan = AvailabilityRecord(
        "lp-A",
        "lp-A-v1",
        "A",
        AvailabilityKind.LEAVE_PLAN,
        date(2026, 10, 1),
        date(2026, 10, 1),
        True,
        None,
        None,
    )
    hard_rule = _rule("RV-D-no-day", "D", ["N"])
    state = base_state(
        employees=tuple(_employee(employee) for employee in ("A", "B", "D", "E")),
        memberships=tuple(_membership(employee) for employee in ("A", "B", "D", "E")),
        shift_demands=(d1, d2, d4),
        existing_assignments=baselines,
        availability_records=(leave_plan,),
        site_rules=(hard_rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-D-no-day", MONTH, MONTH_END),),
    )

    result = plan(state)

    assert result.status == "FEASIBLE"
    pairs = {(assignment.employee_id, assignment.covers_demand_id) for assignment in result.candidates[0]}
    assert ("D", "D4") not in pairs  # HARD SiteRule wins
    assert ("A", "D1") in pairs and ("B", "D2") in pairs  # no SOFT-motivated swap
