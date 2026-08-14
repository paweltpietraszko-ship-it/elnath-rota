"""ROTA-T010 implementation re-audit round 5: Part B only.

Adversarial sibling coverage for the R3-3/R3-4 fixes and the already-frozen
solver/independent-validator agreement. Parts A and D are outside this file.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.application.availability_matrix import employee_availability_matrix
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SiteRuleVersion,
)
from rota.persistence.db import connect
from rota.persistence.decision_ledger import record_decision
from rota.persistence.employee_repository import save_employee
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.eligibility import check_eligibility
from rota.planning.site_rules import (
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
)
from rota.planning.state import SiteRuleApplicability
from rota.planning.validator import validate
from rota.site_memory_types import NewRuleContent
from tests.support.minimal_state import PROFILE_ID, SITE_ID, base_profile, base_state


MONTH = date(2026, 10, 1)
EMP_A = "EMP-R5-A"
EMP_B = "EMP-R5-B"
EXCEPTION_ID = "RV-R5-EXCEPTION"


def _employee(employee_id: str, *, day_only: bool = True) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _membership(employee_id: str, *, enabled: bool = True) -> SiteMembership:
    return SiteMembership(
        employee_id,
        SITE_ID,
        MembershipKind.LOCAL,
        enabled,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )


def _demand(*, day: int = 12) -> ShiftDemand:
    return ShiftDemand(
        f"N-{day}",
        "test-v1",
        datetime(2026, 10, day, 17),
        datetime(2026, 10, day + 1, 5),
        1,
    )


def _assignment(employee_id: str, *, day: int = 12) -> Assignment:
    demand = _demand(day=day)
    return Assignment(
        f"AS-{employee_id}-{day}",
        "test-v1",
        employee_id,
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        demand.demand_id,
        None,
    )


def _rule(
    *,
    rule_version_id: str,
    rule_id: str,
    employee_id: str,
    rule_kind: str = EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    category: RuleCategory = RuleCategory.CONFIRMED_EXCEPTION,
    parameters: dict | None = None,
) -> SiteRuleVersion:
    if parameters is None:
        parameters = {"employee_id": employee_id}
    return SiteRuleVersion(
        rule_version_id=rule_version_id,
        rule_id=rule_id,
        site_id=SITE_ID,
        category=category,
        rule_kind=rule_kind,
        structured_parameters=parameters,
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
        changed_at=datetime(2026, 9, 1, 9),
        changed_by="COORD-R5",
        supersedes_rule_version_id=None,
        description=None,
        source=None,
        reason=None,
    )


def _applicability(rule: SiteRuleVersion) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule.rule_version_id, date(2026, 10, 1), date(2026, 10, 31))


def _eligibility(
    employee_id: str,
    *,
    membership_enabled: bool = True,
    availability: list[AvailabilityRecord] | None = None,
    rules: list[SiteRuleVersion] | None = None,
) -> object:
    return check_eligibility(
        _employee(employee_id),
        _membership(employee_id, enabled=membership_enabled),
        _demand(),
        ShiftKind.N,
        base_profile(),
        availability or [],
        [],
        SITE_ID,
        rules or [],
    )


@pytest.mark.parametrize(
    "wrong_category",
    [RuleCategory.LOCAL_RULE, RuleCategory.CLIENT_REQUIREMENT],
)
def test_r5_b_wrong_category_neither_eligibility_nor_validator_grants_exception(
    wrong_category,
) -> None:
    rule = _rule(
        rule_version_id="RV-WRONG-CATEGORY",
        rule_id="R-WRONG-CATEGORY",
        employee_id=EMP_A,
        category=wrong_category,
    )
    demand = _demand()
    state = base_state(
        employees=(_employee(EMP_A),),
        memberships=(_membership(EMP_A),),
        shift_demands=(demand,),
        site_rules=(rule,),
        site_rule_applicability=(_applicability(rule),),
    )

    eligible = _eligibility(EMP_A, rules=[rule])
    report = validate(state, [_assignment(EMP_A)])

    assert not eligible.eligible
    assert eligible.blocked_reason == "DAY_ONLY-01"
    assert any(detail.rule == "DAY_ONLY-01" for detail in report.violation_details)


def test_r5_b_confirmed_exception_applies_only_to_the_named_employee() -> None:
    rule = _rule(
        rule_version_id=EXCEPTION_ID,
        rule_id="R-EXCEPTION",
        employee_id=EMP_A,
    )
    demand = _demand()
    state = base_state(
        employees=(_employee(EMP_A), _employee(EMP_B)),
        memberships=(_membership(EMP_A), _membership(EMP_B)),
        shift_demands=(demand,),
        site_rules=(rule,),
        site_rule_applicability=(_applicability(rule),),
    )

    assert _eligibility(EMP_A, rules=[rule]).eligible
    assert not _eligibility(EMP_B, rules=[rule]).eligible

    report_a = validate(state, [_assignment(EMP_A)])
    report_b = validate(state, [_assignment(EMP_B)])
    assert not any(detail.rule == "DAY_ONLY-01" for detail in report_a.violation_details)
    assert any(detail.rule == "DAY_ONLY-01" for detail in report_b.violation_details)


def test_r5_b_other_hard_n_ban_still_blocks_in_eligibility_and_validator() -> None:
    exception = _rule(
        rule_version_id=EXCEPTION_ID,
        rule_id="R-EXCEPTION",
        employee_id=EMP_A,
    )
    ban = _rule(
        rule_version_id="RV-N-BAN",
        rule_id="R-N-BAN",
        employee_id=EMP_A,
        rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        category=RuleCategory.LOCAL_RULE,
        parameters={
            "employee_id": EMP_A,
            "weekdays": list(range(1, 8)),
            "forbidden_shift_kinds": ["N"],
        },
    )
    state = base_state(
        employees=(_employee(EMP_A),),
        memberships=(_membership(EMP_A),),
        shift_demands=(_demand(),),
        site_rules=(exception, ban),
        site_rule_applicability=(_applicability(exception), _applicability(ban)),
    )

    eligible = _eligibility(EMP_A, rules=[exception, ban])
    report = validate(state, [_assignment(EMP_A)])

    assert not eligible.eligible
    assert eligible.blocked_reason == ban.rule_version_id
    assert any(detail.rule == ban.rule_version_id for detail in report.violation_details)
    assert not any(detail.rule == "DAY_ONLY-01" for detail in report.violation_details)


@pytest.mark.parametrize(
    ("kind", "condition_code"),
    [
        (AvailabilityKind.SICK_LEAVE, "SICK_LEAVE-01"),
        (AvailabilityKind.LEAVE_GRANTED, "LEAVE_GRANTED-01"),
        (AvailabilityKind.UNAVAILABLE_24H, "UNAVAILABLE-01"),
    ],
)
def test_r5_b_exception_does_not_lift_blocking_availability_in_either_owner(
    kind, condition_code
) -> None:
    exception = _rule(
        rule_version_id=EXCEPTION_ID,
        rule_id="R-EXCEPTION",
        employee_id=EMP_A,
    )
    availability = AvailabilityRecord(
        availability_id=f"AV-{kind.value}",
        availability_version_id=f"AVV-{kind.value}",
        employee_id=EMP_A,
        kind=kind,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 12),
        active=True,
        supersedes_availability_version_id=None,
        note=None,
    )
    state = base_state(
        employees=(_employee(EMP_A),),
        memberships=(_membership(EMP_A),),
        availability_records=(availability,),
        shift_demands=(_demand(),),
        site_rules=(exception,),
        site_rule_applicability=(_applicability(exception),),
    )

    eligible = _eligibility(EMP_A, availability=[availability], rules=[exception])
    report = validate(state, [_assignment(EMP_A)])

    assert not eligible.eligible
    assert eligible.blocked_reason == condition_code
    assert any(detail.rule == condition_code for detail in report.violation_details)


def test_r5_b_exception_does_not_lift_disabled_membership_in_either_owner() -> None:
    exception = _rule(
        rule_version_id=EXCEPTION_ID,
        rule_id="R-EXCEPTION",
        employee_id=EMP_A,
    )
    state = base_state(
        employees=(_employee(EMP_A),),
        memberships=(_membership(EMP_A, enabled=False),),
        shift_demands=(_demand(),),
        site_rules=(exception,),
        site_rule_applicability=(_applicability(exception),),
    )

    eligible = _eligibility(EMP_A, membership_enabled=False, rules=[exception])
    report = validate(state, [_assignment(EMP_A)])

    assert not eligible.eligible
    assert eligible.blocked_reason == "MEMBERSHIP_DISABLED"
    assert any(detail.rule == "MEMBERSHIP-01" for detail in report.violation_details)


def _seed_projection_context(conn, *, include_second_site: bool = False) -> None:
    profile = base_profile()
    save_site_profile(conn, profile)
    save_site(conn, Site(SITE_ID, PROFILE_ID, "Site", True))
    if include_second_site:
        save_site(conn, Site("OTHER-SITE", PROFILE_ID, "Other Site", True))
    save_employee(conn, _employee(EMP_A, day_only=False))
    save_employee(conn, _employee(EMP_B, day_only=False))


def _content(employee_id: str, *, effective_to: date) -> NewRuleContent:
    return NewRuleContent(
        category=RuleCategory.LOCAL_RULE,
        rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        structured_parameters={
            "employee_id": employee_id,
            "weekdays": list(range(1, 8)),
            "forbidden_shift_kinds": ["N"],
        },
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_to=effective_to,
        description=None,
        source=None,
        reason=None,
    )


def _record_rule(
    conn,
    *,
    site_id: str,
    rule_id: str,
    employee_id: str,
    effective_from: date,
    effective_to: date,
    rel: str | None = None,
) -> None:
    record_decision(
        conn,
        site_id=site_id,
        rule_id=rule_id,
        statement=f"{rule_id} {effective_from}",
        coordinator_id="COORD-R5",
        recorded_at=datetime(2026, 9, 1, 9),
        effective_from=effective_from,
        rel=rel,
        rule_content=_content(employee_id, effective_to=effective_to),
    )


def test_r5_b_early_restore_has_exact_applicability_and_survives_restart(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_projection_context(conn)
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-EARLY-RESTORE",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
    )
    record_decision(
        conn,
        site_id=SITE_ID,
        rule_id="R-EARLY-RESTORE",
        statement="restore checkmark",
        coordinator_id="COORD-R5",
        recorded_at=datetime(2026, 10, 10, 9),
        effective_from=date(2026, 10, 15),
        rel="rejects",
        rule_content=None,
    )

    before_restart = employee_availability_matrix(
        conn, site_id=SITE_ID, employee_id=EMP_A, month=MONTH
    )
    conn.close()
    reopened = connect(db_path)
    after_restart = employee_availability_matrix(
        reopened, site_id=SITE_ID, employee_id=EMP_A, month=MONTH
    )

    assert before_restart == after_restart
    assert len(before_restart.weekday_and_exception_rules) == 1
    assert len(before_restart.rule_applicability) == 1
    applicability = before_restart.rule_applicability[0]
    assert applicability.applies_from == date(2026, 10, 1)
    assert applicability.applies_to == date(2026, 10, 14)


def test_r5_b_projection_preserves_correction_and_independent_family_slices(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_projection_context(conn)
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-CORRECTED",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
    )
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-CORRECTED",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 10),
        effective_to=date(2026, 10, 20),
        rel="supersedes",
    )
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-INDEPENDENT",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 25),
        effective_to=date(2026, 10, 27),
    )

    matrix = employee_availability_matrix(
        conn, site_id=SITE_ID, employee_id=EMP_A, month=MONTH
    )
    slices = {
        (item.applies_from, item.applies_to) for item in matrix.rule_applicability
    }

    assert len(matrix.weekday_and_exception_rules) == 3
    assert slices == {
        (date(2026, 10, 1), date(2026, 10, 9)),
        (date(2026, 10, 10), date(2026, 10, 20)),
        (date(2026, 10, 25), date(2026, 10, 27)),
    }


def test_r5_b_projection_filters_other_employee_and_other_site_applicability(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_projection_context(conn, include_second_site=True)
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-EMP-A",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 5),
    )
    _record_rule(
        conn,
        site_id=SITE_ID,
        rule_id="R-EMP-B",
        employee_id=EMP_B,
        effective_from=date(2026, 10, 6),
        effective_to=date(2026, 10, 10),
    )
    _record_rule(
        conn,
        site_id="OTHER-SITE",
        rule_id="R-OTHER-SITE",
        employee_id=EMP_A,
        effective_from=date(2026, 10, 11),
        effective_to=date(2026, 10, 15),
    )

    matrix = employee_availability_matrix(
        conn, site_id=SITE_ID, employee_id=EMP_A, month=MONTH
    )

    assert {rule.rule_id for rule in matrix.weekday_and_exception_rules} == {"R-EMP-A"}
    relevant_ids = {rule.rule_version_id for rule in matrix.weekday_and_exception_rules}
    assert {item.rule_version_id for item in matrix.rule_applicability} == relevant_ids
    assert matrix.rule_applicability[0].applies_from == date(2026, 10, 1)
    assert matrix.rule_applicability[0].applies_to == date(2026, 10, 5)
