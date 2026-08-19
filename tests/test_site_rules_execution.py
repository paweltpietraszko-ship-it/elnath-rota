"""ROTA-T007 required test matrix A-M, O-Q (tasks/ROTA-T007/brief.md).
Matrix N (real SQLite two-month integration) lives in
tests/test_site_rule_execution_integration.py.
"""
from __future__ import annotations

from datetime import date, datetime

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    SiteMembership,
    SiteRuleVersion,
)
from rota.planning.engine import plan
from rota.planning.site_rules import (
    EMPLOYEE_ALLOWED_SHIFT_KINDS,
    EMPLOYEE_ALLOWED_WEEKDAYS,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
    UnsupportedOrMalformedSiteRule,
)
from rota.planning.state import SiteRuleApplicability
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

# October 2026: 1=Thu, 2=Fri, 3=Sat, 4=Sun, 5=Mon, 8=Thu, 9=Fri
MONTH_SPAN = (date(2026, 10, 1), date(2026, 10, 31))


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _employee(employee_id: str) -> Employee:
    return Employee(employee_id, employee_id, date(2026, 9, 1), None, False)


def _demand_d(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _demand_n(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _rule(
    rule_version_id: str, *, rule_id: str = "R1", rule_kind: str | None = EMPLOYEE_ALLOWED_SHIFT_KINDS,
    parameters: object = None, enforcement: RuleEnforcement = RuleEnforcement.HARD,
    resolution_status: RuleResolution = RuleResolution.RESOLVED,
) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id=rule_id, site_id=SITE_ID,
        category=RuleCategory.LOCAL_RULE, rule_kind=rule_kind, structured_parameters=parameters,
        enforcement=enforcement, resolution_status=resolution_status,
        effective_from=date(2026, 10, 1), effective_to=None,
        changed_at=datetime(2026, 10, 1), changed_by="COORD",
        supersedes_rule_version_id=None, description=None, source=None, reason=None,
    )


def _applicability(rule_version_id: str, span: tuple[date, date] = MONTH_SPAN) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule_version_id, span[0], span[1])


def _covering_pairs(assignments) -> set[tuple[str, str]]:
    return {(a.employee_id, a.covers_demand_id) for a in assignments if a.covers_demand_id}


# A. BASELINE NO RULES --------------------------------------------------------


def test_a_no_site_rules_behaves_exactly_as_before_t007():
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("A", "D1")}


# B. ONLY N ---------------------------------------------------------------
# Single-employee scenarios throughout B-G: with a second, unrestricted
# employee also eligible, CP-SAT's tie-break could hand the "allowed" demand
# to them instead, which would prove nothing about A's own eligibility. A
# demand FEASIBLE-covered by the only employee in the state is an
# unambiguous proof that the rule allowed it; DECISION_REQUIRED with no
# other eligible employee is an unambiguous proof that it blocked it.


def test_b_employee_allowed_shift_kinds_blocks_d():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("D1", 1),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def test_b_employee_allowed_shift_kinds_allows_n():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_n("N1", 1),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "N1") in _covering_pairs(result.candidates[0])


# C. ONLY WEEKENDS --------------------------------------------------------


def test_c_employee_allowed_weekdays_blocks_monday():
    rule = _rule("RV-1", rule_kind=EMPLOYEE_ALLOWED_WEEKDAYS, parameters={"employee_id": "A", "allowed_weekdays": [6, 7]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("MON", 5),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def test_c_employee_allowed_weekdays_allows_saturday():
    rule = _rule("RV-1", rule_kind=EMPLOYEE_ALLOWED_WEEKDAYS, parameters={"employee_id": "A", "allowed_weekdays": [6, 7]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("SAT", 3),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "SAT") in _covering_pairs(result.candidates[0])


# D. FRIDAY D BLOCKED / N ALLOWED ------------------------------------------


def test_d_forbidden_shift_kinds_on_weekdays_blocks_friday_d():
    rule = _rule(
        "RV-1", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["D"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("FRI_D", 2),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


def test_d_forbidden_shift_kinds_on_weekdays_allows_friday_n():
    rule = _rule(
        "RV-1", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["D"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_n("FRI_N", 2),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "FRI_N") in _covering_pairs(result.candidates[0])


# E. OVERNIGHT DAY ANCHOR ---------------------------------------------------


def test_e_thursday_n_is_anchored_to_thursday_not_its_friday_end_date():
    """Forbid N on Friday (weekday=5). A Thursday N (ends Friday 05:00) is
    anchored to Thursday, so it must remain allowed."""
    rule = _rule(
        "RV-1", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["N"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_n("THU_N", 1),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "THU_N") in _covering_pairs(result.candidates[0])


def test_e_friday_n_is_anchored_to_friday_and_blocked():
    rule = _rule(
        "RV-1", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["N"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_n("FRI_N", 2),),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


# F. MID-MONTH SUPERSESSION -------------------------------------------------


def test_f_mid_month_supersession_v1_still_governs_before_the_effective_date():
    v1 = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    v2 = _rule("RV-2", parameters={"employee_id": "A", "allowed_shift_kinds": ["D"]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("EARLY_D", 10),),
        site_rules=(v1, v2),
        site_rule_applicability=(
            SiteRuleApplicability("RV-1", date(2026, 10, 1), date(2026, 10, 15)),
            SiteRuleApplicability("RV-2", date(2026, 10, 16), date(2026, 10, 31)),
        ),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"  # v1 (N-only) still governs Oct 10


def test_f_mid_month_supersession_v2_governs_on_and_after_the_effective_date():
    v1 = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    v2 = _rule("RV-2", parameters={"employee_id": "A", "allowed_shift_kinds": ["D"]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("LATE_D", 20),),
        site_rules=(v1, v2),
        site_rule_applicability=(
            SiteRuleApplicability("RV-1", date(2026, 10, 1), date(2026, 10, 15)),
            SiteRuleApplicability("RV-2", date(2026, 10, 16), date(2026, 10, 31)),
        ),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "LATE_D") in _covering_pairs(result.candidates[0])


# G. MID-MONTH REJECT ---------------------------------------------------------


def test_g_reject_leaves_no_applicability_after_its_date():
    """A rule active only through Oct 10 (rejected afterwards) has no
    applicability slice covering Oct 20 -- this test only proves the
    planning-side effect; T005 owns storage-side immutability."""
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("LATE_D", 20),),
        site_rules=(rule,),
        site_rule_applicability=(SiteRuleApplicability("RV-1", date(2026, 10, 1), date(2026, 10, 10)),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "LATE_D") in _covering_pairs(result.candidates[0])


# H. NEEDS_RESOLUTION ---------------------------------------------------------


def test_h_needs_resolution_rule_has_zero_planning_effect_even_if_malformed():
    unresolved = _rule(
        "RV-1", rule_kind="TOTALLY_UNKNOWN_KIND", parameters={"garbage": True},
        resolution_status=RuleResolution.NEEDS_RESOLUTION,
    )
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        unresolved_site_rules=(unresolved,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"


# I. INFORMATIONAL ------------------------------------------------------------


def test_i_resolved_informational_rule_never_executes_or_errors_even_if_malformed():
    informational = _rule(
        "RV-1", rule_kind="UNKNOWN_KIND", parameters={"not": "validated"},
        enforcement=RuleEnforcement.INFORMATIONAL,
    )
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(informational,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "D1") in _covering_pairs(result.candidates[0])


# J. UNKNOWN/MALFORMED EXECUTABLE ---------------------------------------------


def test_j_unknown_resolved_hard_rule_kind_is_technical_error_with_rule_version_id():
    rule = _rule("RV-1", rule_kind="NOT_A_REAL_KIND", parameters={"employee_id": "A"})
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert "RV-1" in result.error_message


def test_j_malformed_resolved_hard_parameters_is_technical_error_with_rule_version_id():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": []})  # empty -> malformed
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert "RV-1" in result.error_message


def test_j_resolved_soft_site_rule_is_technical_error():
    rule = _rule("RV-1", enforcement=RuleEnforcement.SOFT, parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    demand = _demand_d("D1", 1)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert "RV-1" in result.error_message


# K. CONFLICT / DECISION_REQUIRED ----------------------------------------------


def test_k_valid_hard_site_rule_shortage_is_decision_required_with_rule_version_id():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    demand = _demand_d("D1", 1)  # only A exists, and A can't do D per the rule
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisaną regułą obiektu" for b in result.decision_payload.blockers)


# L. MULTIPLE RULES -------------------------------------------------------------


def test_l_multiple_hard_rules_combine_by_and_blocks_friday_d():
    allowed_weekend_plus_friday = _rule(
        "RV-1", rule_kind=EMPLOYEE_ALLOWED_WEEKDAYS, rule_id="R1",
        parameters={"employee_id": "A", "allowed_weekdays": [5, 6, 7]},
    )
    forbidden_friday_d = _rule(
        "RV-2", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS, rule_id="R2",
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["D"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_d("FRI_D", 2),),
        site_rules=(allowed_weekend_plus_friday, forbidden_friday_d),
        site_rule_applicability=(_applicability("RV-1"), _applicability("RV-2")),
    )
    result = plan(state)
    # rule 1 (allowed_weekdays) alone would allow Friday -- only combining
    # with rule 2 (forbidden D on Friday) correctly blocks this demand.
    assert result.status == "DECISION_REQUIRED"


def test_l_multiple_hard_rules_combine_by_and_allows_friday_n():
    allowed_weekend_plus_friday = _rule(
        "RV-1", rule_kind=EMPLOYEE_ALLOWED_WEEKDAYS, rule_id="R1",
        parameters={"employee_id": "A", "allowed_weekdays": [5, 6, 7]},
    )
    forbidden_friday_d = _rule(
        "RV-2", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS, rule_id="R2",
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["D"]},
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(_demand_n("FRI_N", 2),),
        site_rules=(allowed_weekend_plus_friday, forbidden_friday_d),
        site_rule_applicability=(_applicability("RV-1"), _applicability("RV-2")),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert ("A", "FRI_N") in _covering_pairs(result.candidates[0])


# M. INDEPENDENT VALIDATOR -------------------------------------------------------


def test_m_independent_validator_catches_a_site_rule_violation_solver_never_produced():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    demand = _demand_d("D1", 1)
    forbidden_candidate = Assignment(
        "hand-crafted-1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    report = validate(state, [forbidden_candidate])
    assert not report.hard_pass
    assert any(d.rule == "RV-1" for d in report.violation_details)


# O. NO PLANNING I/O -------------------------------------------------------------


def test_o_site_rules_module_has_no_persistence_or_sqlite_coupling():
    from pathlib import Path

    planning_dir = Path(__file__).resolve().parent.parent / "rota" / "planning"
    for path in planning_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "rota.persistence" not in source, f"{path} imports persistence"
        assert "import sqlite3" not in source, f"{path} imports sqlite3 directly"


# P. REPLAN FROZEN CONFLICT -------------------------------------------------------


def test_p_frozen_assignment_conflicting_with_hard_site_rule_is_decision_required_not_moved():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    demand = _demand_d("D1", 1)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand.demand_id, None,
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        existing_assignments=(frozen,), site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisaną regułą obiektu" for b in result.decision_payload.blockers)


# Q. REALIZED HISTORY -------------------------------------------------------------


def test_q_later_site_rule_does_not_retroactively_invalidate_realized_work():
    rule = _rule("RV-1", parameters={"employee_id": "A", "allowed_shift_kinds": ["N"]})
    demand = _demand_d("D1", 1)  # a D shift -- forbidden by RV-1 if it applied retroactively
    realized = Assignment(
        "realized-1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demand.demand_id, None,
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(), shift_demands=(demand,),
        existing_assignments=(realized,), site_rules=(rule,), site_rule_applicability=(_applicability("RV-1"),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.candidates[0] == [realized]


def test_unsupported_or_malformed_site_rule_carries_rule_version_id():
    try:
        raise UnsupportedOrMalformedSiteRule("RV-42", "test reason")
    except UnsupportedOrMalformedSiteRule as exc:
        assert exc.rule_version_id == "RV-42"
        assert "RV-42" in str(exc)
