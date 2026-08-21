"""ROTA-T022: planning integrity repair after the independent cross-cutting
audit (tasks/ROTA-T022/brief.md). Consolidated dedicated matrix for:

- whole-hour work granularity (OWNER-T022-01, Section 3);
- T022-F1: demand-anchor/kind HARD checks (DAY_ONLY-01, SiteRules, EXTERNAL-01);
- T022-F2/F3: interval-based normal-H24 same-person + malformed provenance
  fail-closed;
- T022-F4/OWNER-T022-02: H12+H12 cannot silently form 24h via rest=0;
- OWNER-T022-03 / CROSS-SITE-ZERO-GAP-01: cross-Site zero-gap continuation;
- T022-F5: REPLAN independent validator protects mentor-linked PRIMARY.

C3 (validator._check_rest not calling work_periods.violates_rest) and C6
(engine._decision_for_conflict's fixed REST-01 label) are explicitly out of
scope (brief.md SECTION 5) and are not exercised here.
"""
from __future__ import annotations

from datetime import date, datetime, time

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteRuleVersion,
    StandardShift,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_validation import validate_assignments, validate_demands
from rota.planning.engine import plan
from rota.planning.shift_catalog import (
    InvalidStandardShift,
    generate_catalog_demands,
    validate_standard_shift,
)
from rota.planning.state import SiteRuleApplicability
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, PROFILE_ID, SITE_ID, base_profile, base_state

VERSION_ID = "test-v1"


# --- shared helpers (self-contained, mirrors tests/test_t012.py conventions) --


def _membership(employee_id: str, *, can_work_24h: bool = True, site_id: str = SITE_ID) -> SiteMembership:
    return SiteMembership(
        employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT, can_work_24h=can_work_24h,
    )


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _demand(demand_id: str, start: datetime, end: datetime, count: int = 1, **kwargs) -> ShiftDemand:
    return ShiftDemand(demand_id, VERSION_ID, start, end, count, **kwargs)


def _primary(assignment_id: str, employee_id: str, demand: ShiftDemand, *, frozen: bool = False, **kwargs) -> Assignment:
    return Assignment(
        assignment_id, VERSION_ID, employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, demand.demand_id, None, **kwargs,
    )


def _spanning_primary(assignment_id: str, employee_id: str, start: datetime, end: datetime, covers_demand_id: str, *, frozen: bool = True, **kwargs) -> Assignment:
    return Assignment(
        assignment_id, VERSION_ID, employee_id, start, end,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, covers_demand_id, None, **kwargs,
    )


def _rule(rule_version_id: str, rule_kind: str, params: dict) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id=rule_version_id, site_id=SITE_ID,
        category=RuleCategory.LOCAL_RULE, rule_kind=rule_kind, structured_parameters=params,
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_from=date(2026, 10, 1), effective_to=None, changed_at=datetime(2026, 10, 1), changed_by="C1",
        supersedes_rule_version_id=None, description=None, source=None, reason=None,
    )


def _applicability(rule_version_id: str) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule_version_id, date(2026, 10, 1), date(2026, 10, 31))


def _h24_shift(kind: ShiftKind, start_h: int, rest: int) -> StandardShift:
    return StandardShift(kind, time(start_h, 0), time(start_h, 0), True, 1, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=rest)


# --- A: full-hour boundary (OWNER-T022-01, Section 3) --------------------


def test_a_standard_shift_sub_hour_start_rejected():
    shift = StandardShift(ShiftKind.D, time(5, 30), time(17, 0), False, 1)
    with pytest.raises(InvalidStandardShift):
        validate_standard_shift(shift)


def test_a_standard_shift_sub_hour_end_rejected():
    shift = StandardShift(ShiftKind.D, time(5, 0), time(17, 30), False, 1)
    with pytest.raises(InvalidStandardShift):
        validate_standard_shift(shift)


def test_a_standard_shift_microsecond_rejected():
    shift = StandardShift(ShiftKind.D, time(5, 0, 0, 1), time(17, 0), False, 1)
    with pytest.raises(InvalidStandardShift):
        validate_standard_shift(shift)


def test_a_whole_hour_standard_shift_still_valid():
    shift = StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1)
    validate_standard_shift(shift)  # must not raise


def test_a_shift_demand_write_sub_hour_start_rejected():
    d = _demand("D1", datetime(2026, 10, 5, 5, 30), datetime(2026, 10, 5, 17, 0))
    with pytest.raises(MalformedScheduleSnapshot):
        validate_demands(MONTH, [d])


def test_a_shift_demand_write_sub_hour_end_rejected():
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 30))
    with pytest.raises(MalformedScheduleSnapshot):
        validate_demands(MONTH, [d])


def test_a_assignment_write_sub_hour_rejected(tmp_path):
    conn = connect(tmp_path / "rota.db")
    save_employee(conn, _employee("E1"))
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0))
    demands_by_id = validate_demands(MONTH, [d])
    a = _primary("A1", "E1", d)
    a = a.__class__(a.assignment_id, a.schedule_version_id, a.employee_id, datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 15), a.role, a.state, a.frozen, a.covers_demand_id, a.mentor_primary_assignment_id)
    with pytest.raises(MalformedScheduleSnapshot):
        validate_assignments(conn, MONTH, [a], demands_by_id)


def test_a_direct_validate_malformed_demand_fails_closed():
    """Defense-in-depth: even if malformed in-memory state bypasses the
    write-time guard, the independent validator fails closed rather than
    reporting hard_pass=True."""
    d = _demand("D1", datetime(2026, 10, 5, 5, 30), datetime(2026, 10, 5, 17, 0))
    state = base_state(shift_demands=(d,))
    report = validate(state, [])
    assert not report.hard_pass
    assert any("FULL_HOUR-01" in v for v in report.violations)


def test_a_direct_validate_malformed_assignment_fails_closed():
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0))
    a = _primary("A1", "E1", d)
    a = Assignment(a.assignment_id, a.schedule_version_id, a.employee_id, a.start_datetime, datetime(2026, 10, 5, 17, 20), a.role, a.state, a.frozen, a.covers_demand_id, a.mentor_primary_assignment_id)
    state = base_state(shift_demands=(d,), memberships=(_membership("E1"),))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("FULL_HOUR-01" in v for v in report.violations)


def test_a_direct_plan_malformed_state_never_feasible():
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 45))
    state = base_state(shift_demands=(d,), employees=(_employee("E1"),), memberships=(_membership("E1"),))
    result = plan(state)
    assert result.status != "FEASIBLE"


# --- B: demand anchor and kind (T022-F1) ----------------------------------


def test_b_legacy_n_demand_day_only_via_spanning_primary():
    """Original F1 reproducer: legacy N demand (shift_kind=None), DAY_ONLY
    employee, frozen PRIMARY spanning from earlier than the demand's own
    start but covering it -- DAY_ONLY-01 must fire, anchored on the demand."""
    n_demand = _demand("N1", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0))
    a = _spanning_primary("A1", "E1", datetime(2026, 10, 5, 16, 0), datetime(2026, 10, 6, 5, 0), "N1")
    state = base_state(shift_demands=(n_demand,), employees=(_employee("E1", day_only=True),), memberships=(_membership("E1"),))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("DAY_ONLY-01" in v for v in report.violations)


def test_b_explicit_n_demand_authoritative_over_profile_fallback():
    n_demand = _demand("N1", datetime(2026, 10, 5, 3, 0), datetime(2026, 10, 5, 9, 0), shift_kind=ShiftKind.N)
    a = _primary("A1", "E1", n_demand)
    state = base_state(shift_demands=(n_demand,), employees=(_employee("E1", day_only=True),), memberships=(_membership("E1"),))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("DAY_ONLY-01" in v for v in report.violations)


def test_b_monday_demand_sunday_starting_primary_checks_monday_site_rules():
    """Original F1 reproducer: PRIMARY starts Sunday, covers a Monday
    demand -- weekday SiteRule uses the demand's own date, not the
    Assignment's start date."""
    monday = _demand("D-MON", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D)
    a = _spanning_primary("A1", "E1", datetime(2026, 10, 4, 20, 0), datetime(2026, 10, 5, 17, 0), "D-MON")
    rule = _rule("R1", "EMPLOYEE_ALLOWED_WEEKDAYS", {"employee_id": "E1", "allowed_weekdays": [7]})  # Sunday only
    state = base_state(
        shift_demands=(monday,), employees=(_employee("E1"),), memberships=(_membership("E1"),),
        site_rules=(rule,), site_rule_applicability=(_applicability("R1"),),
    )
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("R1" in v for v in report.violations)


def test_b_reverse_weekday_sibling_does_not_false_block():
    """Sibling of the above: when the covered demand's own weekday IS
    allowed, no violation -- proves the anchor fix isn't overzealous."""
    sunday = _demand("D-SUN", datetime(2026, 10, 4, 5, 0), datetime(2026, 10, 4, 17, 0), shift_kind=ShiftKind.D)
    a = _primary("A1", "E1", sunday)
    rule = _rule("R1", "EMPLOYEE_ALLOWED_WEEKDAYS", {"employee_id": "E1", "allowed_weekdays": [7]})
    state = base_state(
        shift_demands=(sunday,), employees=(_employee("E1"),), memberships=(_membership("E1"),),
        site_rules=(rule,), site_rule_applicability=(_applicability("R1"),),
    )
    assert validate(state, [a]).hard_pass


def test_b_spanning_assignment_cannot_hide_n_behind_d_tag():
    """A manual PRIMARY spans both a D and an N demand but is tagged only
    to the D demand -- the actually-covered N segment must still be
    checked for DAY_ONLY-01."""
    d_demand = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D)
    n_demand = _demand("N1", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N)
    a = _spanning_primary("A1", "E1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 6, 5, 0), "D1")
    state = base_state(shift_demands=(d_demand, n_demand), employees=(_employee("E1", day_only=True),), memberships=(_membership("E1"),))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("DAY_ONLY-01" in v for v in report.violations)


def test_b_external_allowed_kind_cannot_be_bypassed_by_tag():
    d_demand = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D)
    n_demand = _demand("N1", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N)
    a = _spanning_primary("A1", "E1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 6, 5, 0), "D1")
    membership = SiteMembership("E1", SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    window = ExternalSupportWindow("W1", "E1", SITE_ID, datetime(2026, 10, 5, 0, 0), datetime(2026, 10, 6, 5, 0), True, ShiftKind.D)
    state = base_state(shift_demands=(d_demand, n_demand), employees=(_employee("E1"),), memberships=(membership,), external_windows=(window,))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("EXTERNAL-01" in v for v in report.violations)


def test_b_every_applicable_site_rule_remains_and():
    monday = _demand("D-MON", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D)
    a = _primary("A1", "E1", monday)
    ok_rule = _rule("R-OK", "EMPLOYEE_ALLOWED_WEEKDAYS", {"employee_id": "E1", "allowed_weekdays": [1, 2, 3, 4, 5, 6, 7]})
    bad_rule = _rule("R-BAD", "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS", {"employee_id": "E1", "weekdays": [1], "forbidden_shift_kinds": ["D"]})
    state = base_state(
        shift_demands=(monday,), employees=(_employee("E1"),), memberships=(_membership("E1"),),
        site_rules=(ok_rule, bad_rule), site_rule_applicability=(_applicability("R-OK"), _applicability("R-BAD")),
    )
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("R-BAD" in v for v in report.violations)


# --- C: normal H24 (T022-F2/F3) -------------------------------------------


def _h24_demands(profile_shifts, day=1):
    profile = base_profile().__class__(
        profile_id=PROFILE_ID, display_name="C", active=True, standard_shifts=profile_shifts,
        day_only_blocks_n=True, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=60,
    )
    all_demands = generate_catalog_demands(profile, MONTH)
    component1 = next(d for d in all_demands if d.start_datetime.date() == date(2026, 10, day) and d.work_period_component == 1)
    template_id = component1.work_period_template_id
    pair = tuple(sorted((d for d in all_demands if d.work_period_template_id == template_id), key=lambda d: d.start_datetime))
    return profile, pair


def test_c_tagged_component_mismatch_fails():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E2", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_c_interval_covered_component_hidden_behind_other_tag_fails():
    """Original F2 reproducer: component 2's interval is actually covered by
    a different employee whose Assignment is tagged to a different (later)
    demand -- interval truth must still catch the mismatch."""
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    # E2's Assignment covers d2's interval exactly but is tagged to a demand outside the template.
    a2 = _spanning_primary("A2", "E2", d2.start_datetime, d2.end_datetime, "OUTSIDE-TAG")
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_c_malformed_only_one_component_fails_closed():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1,), memberships=(_membership("E1"),))
    report = validate(state, [a1])
    assert not report.hard_pass
    assert any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_c_malformed_duplicate_component_number_fails_closed():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    d2_bad = ShiftDemand(d2.demand_id, d2.schedule_version_id, d2.start_datetime, d2.end_datetime, d2.required_primary_count, shift_kind=d2.shift_kind, catalog_kind=d2.catalog_kind, required_rest_hours=d2.required_rest_hours, work_period_template_id=d2.work_period_template_id, work_period_component=1)  # duplicate component=1
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id)
    a2 = _primary("A2", "E1", d2_bad, work_period_id=d2_bad.work_period_template_id)
    state = base_state(profile=profile, shift_demands=(d1, d2_bad), memberships=(_membership("E1"),))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_c_malformed_wrong_duration_fails_closed():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    d2_bad = ShiftDemand(d2.demand_id, d2.schedule_version_id, d2.start_datetime, d2.end_datetime.replace(hour=(d2.end_datetime.hour - 2) % 24), d2.required_primary_count, shift_kind=d2.shift_kind, catalog_kind=d2.catalog_kind, required_rest_hours=d2.required_rest_hours, work_period_template_id=d2.work_period_template_id, work_period_component=2)
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id)
    a2 = _primary("A2", "E1", d2_bad, work_period_id=d2_bad.work_period_template_id)
    state = base_state(profile=profile, shift_demands=(d1, d2_bad), memberships=(_membership("E1"),))
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_c_valid_generated_pair_passes():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 5, 12)])
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E1", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E1"),))
    assert validate(state, [a1, a2]).hard_pass


def test_c_month_end_boundary_pair_remains_valid():
    profile, (d1, d2) = _h24_demands([_h24_shift(ShiftKind.D, 17, 12)], day=31)
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E1", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E1"),))
    assert validate(state, [a1, a2]).hard_pass


# --- D: H12+H12 continuous 24h (T022-F4 / OWNER-T022-02 / CROSS-SITE-ZERO-GAP-01) --


def test_d_rest_zero_and_can_work_24h_false_cannot_be_feasible():
    d1 = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    d2 = _demand("D2", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    state = base_state(shift_demands=(d1, d2), employees=(_employee("E1"),), memberships=(_membership("E1", can_work_24h=False),))
    assert plan(state).status != "FEASIBLE"


def test_d_rest_zero_and_flag_true_still_needs_emergency_capability():
    """can_work_24h=True alone does not authorize an ordinary pass to join
    two H12 periods -- the T012 emergency mechanism must actually engage
    (site 24h capability / emergency_24h_rest_hours snapshot)."""
    d1 = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    d2 = _demand("D2", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    state = base_state(shift_demands=(d1, d2), employees=(_employee("E1"),), memberships=(_membership("E1", can_work_24h=True),))
    a1 = _primary("A1", "E1", d1, required_rest_after_hours=0)
    a2 = _primary("A2", "E1", d2, required_rest_after_hours=0)
    report = validate(state, [a1, a2])
    assert not report.hard_pass
    assert any("REST-01" in v for v in report.violations)


def test_d_ordinary_normal_pass_different_employees_remains_legal():
    d1 = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    d2 = _demand("D2", datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    a1 = _primary("A1", "E1", d1, required_rest_after_hours=0)
    a2 = _primary("A2", "E2", d2, required_rest_after_hours=0)
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E1"), _membership("E2")))
    assert validate(state, [a1, a2]).hard_pass


def test_d_cross_site_zero_gap_rejected_even_with_rest_zero_and_can_work_24h_true():
    """OWNER-T022-03 core reproducer: Site A ends exactly when Site B
    starts, earlier persisted rest is 0, can_work_24h is True -- still
    illegal, never merged into a 24h WorkPeriod."""
    site_b_end = datetime(2026, 10, 5, 17, 0)
    other_site_assignment = Assignment(
        "OTHER-A1", "other-v1", "E1", datetime(2026, 10, 5, 5, 0), site_b_end,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, "OTHER-D1", None,
        work_period_id="other-wp", required_rest_after_hours=0,
    )
    d = _demand("D1", site_b_end, datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    a = _primary("A1", "E1", d, required_rest_after_hours=0)
    state = base_state(shift_demands=(d,), memberships=(_membership("E1", can_work_24h=True),), other_site_assignments=(other_site_assignment,))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("REST-01" in v for v in report.violations)


def test_d_cross_site_positive_gap_uses_existing_rest_provenance():
    other_site_assignment = Assignment(
        "OTHER-A1", "other-v1", "E1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, "OTHER-D1", None,
        work_period_id="other-wp", required_rest_after_hours=2,
    )
    d = _demand("D1", datetime(2026, 10, 5, 19, 0), datetime(2026, 10, 6, 7, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    a = _primary("A1", "E1", d, required_rest_after_hours=0)
    state = base_state(shift_demands=(d,), memberships=(_membership("E1", can_work_24h=True),), other_site_assignments=(other_site_assignment,))
    assert validate(state, [a]).hard_pass  # 2h gap >= 2h required


def test_d_cross_site_work_period_ids_are_naturally_distinct():
    """Solver-assigned work_period_id is always Site-scoped
    (f"{site_id}:..." for emergency pairs, per-Site template ids for normal
    24h) -- a genuinely different-Site Assignment therefore never collides
    onto the same id as this Site's own periods by construction."""
    site_b_end = datetime(2026, 10, 5, 17, 0)
    other_site_assignment = Assignment(
        "OTHER-A1", "other-v1", "E1", datetime(2026, 10, 5, 5, 0), site_b_end,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, "OTHER-D1", None,
        work_period_id="OTHER-SITE:wp", required_rest_after_hours=0,
    )
    d = _demand("D1", site_b_end, datetime(2026, 10, 6, 5, 0), shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=0)
    a = _primary("A1", "E1", d, work_period_id=f"{SITE_ID}:wp", required_rest_after_hours=0)
    state = base_state(shift_demands=(d,), memberships=(_membership("E1", can_work_24h=True),), other_site_assignments=(other_site_assignment,))
    report = validate(state, [a])
    assert not report.hard_pass
    assert any("REST-01" in v for v in report.violations)


# --- E: REPLAN mentor pinning (T022-F5) -----------------------------------


def _mentor_state(mentor: Assignment, trainee: Assignment):
    return base_state(
        existing_assignments=(mentor, trainee),
        employees=(_employee("MENTOR"), _employee("TRAINEE")),
        memberships=(_membership("MENTOR"), _membership("TRAINEE")),
    )


def _mentor_pair(mentor_start=datetime(2026, 10, 5, 5, 0), mentor_end=datetime(2026, 10, 5, 17, 0)):
    mentor = Assignment("MENTOR-A", VERSION_ID, "MENTOR", mentor_start, mentor_end, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None)
    trainee = Assignment("TRAINEE-A", VERSION_ID, "TRAINEE", mentor_start, mentor_end, AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "MENTOR-A")
    return mentor, trainee


def test_e_mentor_primary_removed_fails():
    mentor, trainee = _mentor_pair()
    state = _mentor_state(mentor, trainee)
    report = validate(state, [trainee])  # mentor missing from candidate
    assert not report.hard_pass
    assert any("ASSIGN-03/04" in v for v in report.violations)


def test_e_mentor_primary_employee_changed_fails():
    mentor, trainee = _mentor_pair()
    state = _mentor_state(mentor, trainee)
    changed_mentor = Assignment(mentor.assignment_id, mentor.schedule_version_id, "SOMEONE-ELSE", mentor.start_datetime, mentor.end_datetime, mentor.role, mentor.state, mentor.frozen, mentor.covers_demand_id, mentor.mentor_primary_assignment_id)
    report = validate(state, [changed_mentor, trainee])
    assert not report.hard_pass
    assert any("ASSIGN-03/04" in v for v in report.violations)


def test_e_unchanged_mentor_primary_passes():
    mentor, trainee = _mentor_pair()
    d1 = _demand("D1", mentor.start_datetime, mentor.end_datetime)
    state = base_state(
        existing_assignments=(mentor, trainee), shift_demands=(d1,),
        employees=(_employee("MENTOR"), _employee("TRAINEE")),
        memberships=(_membership("MENTOR"), _membership("TRAINEE")),
    )
    report = validate(state, [mentor, trainee])
    assert not any("ASSIGN-03/04" in v for v in report.violations)


def test_e_cancelled_trainee_does_not_pin_former_mentor():
    mentor, trainee = _mentor_pair()
    cancelled_trainee = Assignment(trainee.assignment_id, trainee.schedule_version_id, trainee.employee_id, trainee.start_datetime, trainee.end_datetime, trainee.role, AssignmentState.CANCELLED, trainee.frozen, trainee.covers_demand_id, trainee.mentor_primary_assignment_id)
    state = base_state(
        existing_assignments=(mentor, cancelled_trainee),
        employees=(_employee("MENTOR"), _employee("TRAINEE")),
        memberships=(_membership("MENTOR"), _membership("TRAINEE")),
    )
    changed_mentor = Assignment(mentor.assignment_id, mentor.schedule_version_id, "SOMEONE-ELSE", mentor.start_datetime, mentor.end_datetime, mentor.role, mentor.state, mentor.frozen, mentor.covers_demand_id, mentor.mentor_primary_assignment_id)
    report = validate(state, [changed_mentor])
    assert not any("ASSIGN-03/04" in v for v in report.violations)


def test_e_multiple_trainees_pointing_to_one_primary():
    mentor, trainee1 = _mentor_pair()
    trainee2 = Assignment("TRAINEE-B", VERSION_ID, "TRAINEE2", mentor.start_datetime, mentor.end_datetime, AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "MENTOR-A")
    state = base_state(
        existing_assignments=(mentor, trainee1, trainee2),
        employees=(_employee("MENTOR"), _employee("TRAINEE"), _employee("TRAINEE2")),
        memberships=(_membership("MENTOR"), _membership("TRAINEE"), _membership("TRAINEE2")),
    )
    report = validate(state, [trainee1, trainee2])  # mentor still missing
    assert not report.hard_pass
    assert any("ASSIGN-03/04" in v for v in report.violations)


# --- F: regression ---------------------------------------------------------


def test_f_simple_valid_candidate_passes_independent_validation():
    d = _demand("D1", datetime(2026, 10, 5, 5, 0), datetime(2026, 10, 5, 17, 0), shift_kind=ShiftKind.D)
    state = base_state(shift_demands=(d,), employees=(_employee("E1"),), memberships=(_membership("E1"),))
    result = plan(state)
    assert result.status == "FEASIBLE"
    report = validate(state, result.candidates[0])
    assert report.hard_pass
