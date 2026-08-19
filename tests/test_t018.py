"""ROTA-T018 Checkpoint A: absence workday accounting.

Owner decision 2026-08-19 (arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md):
SICK_LEAVE / LEAVE_GRANTED reduce the expected monthly quota by 8h only for
a qualified workday (ISO weekday 1..5 AND CalendarDay.holiday=False), not
for every calendar day in the absence range. Fail closed via
IncompleteAbsenceCalendarError when a qualifying absence exists but the
month's CalendarDay coverage is incomplete.
"""
from __future__ import annotations

import calendar as calendar_module
from dataclasses import replace
from datetime import date, datetime

import pytest

import rota.planning.engine as engine_module
from rota.balance import compute_month_balance
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    SiteMembership,
    SiteRuleVersion,
    WorkBalance,
)
from rota.planning.absence import IncompleteAbsenceCalendarError, excused_absence_days_in_month
from rota.planning.engine import plan
from rota.planning.site_rules import (
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
    day_only_n_exception_authorizing_rule_version_id,
    hard_rules_applicable_on,
)
from rota.planning.solver import SolverOutcome, _sick_adjusted_targets, solve
from rota.planning.state import SiteRuleApplicability
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


def _local_membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _full_month_calendar(month: date, holidays: frozenset = frozenset()) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(
        CalendarDay(date(month.year, month.month, day), date(month.year, month.month, day) in holidays)
        for day in range(1, last_day + 1)
    )


def _sick(employee_id: str, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(f"sick-{employee_id}-{start}", "v1", employee_id, AvailabilityKind.SICK_LEAVE, start, end, True, None, None)


def _leave(employee_id: str, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(f"leave-{employee_id}-{start}", "v1", employee_id, AvailabilityKind.LEAVE_GRANTED, start, end, True, None, None)


# A7.1 -----------------------------------------------------------------------


def test_a7_1_sick_leave_across_two_weekends_counts_only_weekdays():
    # 2026-10-01 (Thu) .. 2026-10-12 (Mon), spanning weekends 3-4 and 10-11.
    month = date(2026, 10, 1)
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 12))
    result = excused_absence_days_in_month([record], month, calendar_days=_full_month_calendar(month))
    assert result == {"A": 8}


# A7.2 -----------------------------------------------------------------------


def test_a7_2_leave_granted_gets_identical_workday_filter_in_workbalance():
    month = date(2026, 10, 1)
    leave = _leave("A", date(2026, 10, 1), date(2026, 10, 12))
    balance = compute_month_balance("A", month, 168, [], [leave], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -(168 - 8 * 8)


# A7.3 -----------------------------------------------------------------------


def test_a7_3_weekday_holiday_excluded_from_workday_count():
    month = date(2026, 10, 1)
    # 2026-10-01 is a Thursday; mark it a public holiday.
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 1))
    calendar_days = _full_month_calendar(month, holidays=frozenset({date(2026, 10, 1)}))
    assert excused_absence_days_in_month([record], month, calendar_days=calendar_days) == {"A": 0}


# A7.4 -----------------------------------------------------------------------


def test_a7_4_weekend_holiday_still_zero_no_double_effect():
    month = date(2026, 10, 1)
    # 2026-10-03 is a Saturday; also (redundantly) marked a holiday.
    record = _sick("A", date(2026, 10, 3), date(2026, 10, 3))
    calendar_days = _full_month_calendar(month, holidays=frozenset({date(2026, 10, 3)}))
    assert excused_absence_days_in_month([record], month, calendar_days=calendar_days) == {"A": 0}


# A7.5 -----------------------------------------------------------------------


def test_a7_5_overlapping_sick_and_leave_dedup_before_workday_filter():
    month = date(2026, 10, 1)
    # Union Oct 1-5 (Thu-Mon); overlap on Oct 3 (Sat) must not double-count.
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 3))
    leave = _leave("A", date(2026, 10, 3), date(2026, 10, 5))
    calendar_days = _full_month_calendar(month)
    result = excused_absence_days_in_month([sick, leave], month, calendar_days=calendar_days)
    assert result == {"A": 3}


# A7.6 -----------------------------------------------------------------------


def test_a7_6_cross_month_range_clips_and_filters_workdays():
    month = date(2026, 10, 1)
    # 2026-09-28 (Mon) .. 2026-10-02 (Fri); only Oct 1 (Thu) and Oct 2 (Fri)
    # are inside the counted month, both workdays.
    record = _sick("A", date(2026, 9, 28), date(2026, 10, 2))
    result = excused_absence_days_in_month([record], month, calendar_days=_full_month_calendar(month))
    assert result == {"A": 2}


# A7.7 -----------------------------------------------------------------------


def test_a7_7_weekend_absence_still_hard_blocks_assignment():
    # 2026-10-03 is a Saturday; a demand that day must still be HARD-blocked
    # by the active SICK_LEAVE even though it contributes 0h target reduction.
    demand = ShiftDemand("2026-10-03-D", "test-v1", datetime(2026, 10, 3, 5, 0), datetime(2026, 10, 3, 17, 0), 1)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 3), date(2026, 10, 3))
    state = base_state(
        employees=(employee,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.employee_id == "A" and b.condition == "Koliduje z zapisem: Chorobowe" for b in result.decision_payload.blockers)


# A7.8 -----------------------------------------------------------------------


def test_a7_8_incomplete_calendar_with_qualifying_absence_fails_closed():
    month = date(2026, 10, 1)
    record = _sick("A", date(2026, 10, 1), date(2026, 10, 5))
    full = _full_month_calendar(month)
    missing_one_day = full[:-1]  # drop Oct 31
    with pytest.raises(IncompleteAbsenceCalendarError):
        excused_absence_days_in_month([record], month, calendar_days=missing_one_day)


# A7.9 -----------------------------------------------------------------------


def test_a7_9_direct_plan_with_incomplete_calendar_and_sick_absence_is_technical_error():
    # Two employees so demand coverage is still reachable (no unassignable
    # short-circuit before the objective, where the calendar is consumed).
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 5))
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(sick,),
    )
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"


# A7.10 ----------------------------------------------------------------------


def test_a7_10_legacy_balance_call_without_absence_or_calendar_keeps_result():
    balance = compute_month_balance("A", date(2026, 10, 1), 156, [], [])
    assert balance.month_balance == -156


# A7.11 -- existing Round 23 reproducers, oracle unchanged ------------------


def test_a7_11a_round23_solver_l4_march_2027_reduces_target_to_56():
    month = date(2027, 3, 1)
    sick = _sick("B", date(2027, 3, 2), date(2027, 3, 19))
    state = base_state(
        employees=(), memberships=(), month=month, calendar_days=_full_month_calendar(month),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 56


def test_a7_11b_round23_quarter_balance_leave_march_2027_reduces_target_to_56():
    month = date(2027, 3, 1)
    leave = _leave("B", date(2027, 3, 2), date(2027, 3, 19))
    balance = compute_month_balance("B", month, 168, [], [leave], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -56


def test_a7_11c_round23_solver_l4_excludes_weekday_public_holiday():
    month = date(2027, 5, 1)
    sick = _sick("B", date(2027, 5, 1), date(2027, 5, 7))
    state = base_state(
        employees=(), memberships=(), month=month,
        calendar_days=_full_month_calendar(month, holidays=frozenset({date(2027, 5, 3)})),
        availability_records=(sick,), work_balances=(WorkBalance("B", month, 168, 0, 0, 0, 0, 0),),
    )
    assert _sick_adjusted_targets(state)["B"] == 136


# A7.12 -----------------------------------------------------------------------


def test_a7_12_march_2027_workbalance_target_56_at_target_168():
    month = date(2027, 3, 1)
    sick = _sick("B", date(2027, 3, 2), date(2027, 3, 19))
    balance = compute_month_balance("B", month, 168, [], [sick], calendar_days=_full_month_calendar(month))
    assert balance.month_balance == -56


# ============================================================================
# CHECKPOINT B: DAY_ONLY N FALLBACK
# (arch/FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01.md +
#  arch/FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01_R1_CLARIFICATION.md)
# ============================================================================

B_MONTH = date(2026, 10, 1)


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _membership(employee_id: str, *, enabled: bool = True, **overrides) -> SiteMembership:
    return SiteMembership(
        employee_id, SITE_ID, MembershipKind.LOCAL, enabled, ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT, **overrides,
    )


def _n_demand(day: int, demand_id: str | None = None) -> ShiftDemand:
    return ShiftDemand(
        demand_id or f"N-{day}", "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1,
    )


def _d_demand(day: int, demand_id: str | None = None) -> ShiftDemand:
    return ShiftDemand(demand_id or f"D-{day}", "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _exception_rule(
    rule_version_id: str, employee_id: str, *, rule_id: str | None = None,
    effective_from: date = date(2026, 10, 1), effective_to: date = date(2026, 10, 31),
) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id=rule_id or f"R-{rule_version_id}", site_id=SITE_ID,
        category=RuleCategory.CONFIRMED_EXCEPTION, rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        structured_parameters={"employee_id": employee_id}, enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED, effective_from=effective_from, effective_to=effective_to,
        changed_at=datetime(2026, 9, 1, 9), changed_by="COORD-T018", supersedes_rule_version_id=None,
        description=None, source=None, reason=None,
    )


def _applicability(rule: SiteRuleVersion) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule.rule_version_id, rule.effective_from, rule.effective_to)


def _tracking_solve(monkeypatch):
    """Replace engine_module.solve with a pass-through wrapper that records
    every (allow_day_only_n_fallback, allow_emergency_24h) call, still
    delegating to the real solver."""
    real_solve = solve
    calls: list[tuple] = []

    def _wrapped(state, **kwargs):
        calls.append((kwargs.get("allow_day_only_n_fallback", False), kwargs.get("allow_emergency_24h", False)))
        return real_solve(state, **kwargs)

    monkeypatch.setattr(engine_module, "solve", _wrapped)
    return calls


# B10.1 -----------------------------------------------------------------------


def test_b10_1_stage1_feasible_ignores_active_exception_and_skips_fallback_stages(monkeypatch):
    demand = _n_demand(6)
    a = _employee("A", day_only=True)
    c = _employee("C")
    rule = _exception_rule("RV-1", "A")
    calls = _tracking_solve(monkeypatch)
    state = base_state(
        employees=(a, c), memberships=(_membership("A"), _membership("C")),
        shift_demands=(demand,), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert calls == [(False, False)]
    assert [a.employee_id for a in result.candidates[0]] == ["C"]
    assert not any("DAY_ONLY-N-FALLBACK-01" in w for w in result.warnings)


# B10.2 -----------------------------------------------------------------------


def test_b10_2_exactly_one_exceptional_n_with_warning():
    demand = _n_demand(6)
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-2", "A")
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(demand,), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert [a.employee_id for a in result.candidates[0]] == ["A"]
    fallback_warnings = [w for w in result.warnings if "DAY_ONLY-N-FALLBACK-01" in w]
    assert len(fallback_warnings) == 1
    assert "employee=A" in fallback_warnings[0]
    assert "rule_version_id=RV-2" in fallback_warnings[0]


# B10.3 -----------------------------------------------------------------------


def test_b10_3_two_exceptional_n_needed_gives_exactly_two():
    d1, d2 = _n_demand(6), _n_demand(13)
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-3", "A")
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(d1, d2), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert {a.covers_demand_id for a in result.candidates[0]} == {"N-6", "N-13"}
    assert len([w for w in result.warnings if "DAY_ONLY-N-FALLBACK-01" in w]) == 2


# B10.4 / B10.5 -----------------------------------------------------------------


def test_b10_4_5_global_minimum_exceptional_n_not_inflated_for_fairness():
    """Two authorized day_only employees exist, but only ONE of the two N
    demands genuinely requires the fallback (C covers the other without any
    exception) -- the lexicographic minimum must stay at 1, never 2, even
    though giving the first N to a day_only employee too would look more
    'fair' under the ordinary TARGET/fairness objective."""
    d1, d2 = _n_demand(6), _n_demand(13)
    a = _employee("A", day_only=True)
    b = _employee("B", day_only=True)
    c = _employee("C")
    rule_a = _exception_rule("RV-4A", "A")
    rule_b = _exception_rule("RV-4B", "B")
    c_leave = AvailabilityRecord("c-leave", "av1", "C", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 13), date(2026, 10, 13), True, None, None)
    state = base_state(
        employees=(a, b, c), memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(d1, d2), availability_records=(c_leave,),
        site_rules=(rule_a, rule_b), site_rule_applicability=(_applicability(rule_a), _applicability(rule_b)),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    # T017: FEASIBLE may legally return 1-3 diverse candidates; the first
    # candidate keeps the pre-T017 placement oracle, and exceptional_n_count
    # (== exactly one DAY_ONLY-N-FALLBACK-01 warning) must hold for EVERY
    # returned candidate, not just the first.
    by_demand = {a.covers_demand_id: a.employee_id for a in result.candidates[0]}
    assert by_demand["N-6"] == "C"
    assert by_demand["N-13"] in {"A", "B"}
    fallback_warnings = [w for w in result.warnings if "DAY_ONLY-N-FALLBACK-01" in w]
    assert len(fallback_warnings) == len(result.candidates)
    if len(result.candidates) > 1:
        for index in range(1, len(result.candidates) + 1):
            assert len([w for w in fallback_warnings if w.startswith(f"candidate={index} | ")]) == 1


# B10.6 -----------------------------------------------------------------------


def test_b10_6_effective_date_boundaries():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-6", "A", effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))

    def _plan_for(day: int):
        state = base_state(
            employees=(a,), memberships=(_membership("A"),),
            shift_demands=(_n_demand(day),), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
            month=B_MONTH,
        )
        return plan(state)

    assert _plan_for(9).status == "DECISION_REQUIRED"
    assert _plan_for(10).status == "FEASIBLE"
    assert _plan_for(15).status == "FEASIBLE"
    assert _plan_for(16).status == "DECISION_REQUIRED"


# B10.7 -----------------------------------------------------------------------


def test_b10_7a_sick_leave_still_blocks_in_fallback_pass():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-7A", "A")
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 6), date(2026, 10, 6), True, None, None)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(_n_demand(6),), availability_records=(sick,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH, calendar_days=_full_month_calendar(B_MONTH),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisem: Chorobowe" for b in result.decision_payload.blockers)


def test_b10_7b_membership_disabled_still_blocks_in_fallback_pass():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-7B", "A")
    state = base_state(
        employees=(a,), memberships=(_membership("A", enabled=False),),
        shift_demands=(_n_demand(6),), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    # T013: MEMBERSHIP_DISABLED is coordinator-invisible (section E).
    assert result.decision_payload.blocking_shift_demands
    assert not any(b.employee_id == "A" for b in result.decision_payload.blockers)


def test_b10_7c_leave_granted_still_blocks_in_fallback_pass():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-7C", "A")
    leave = AvailabilityRecord("l1", "l1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 6), date(2026, 10, 6), True, None, None)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(_n_demand(6),), availability_records=(leave,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisem: Urlop" for b in result.decision_payload.blockers)


def test_b10_7d_another_site_rule_still_blocks_in_fallback_pass():
    n_demand = _n_demand(6)
    weekday = n_demand.start_datetime.isoweekday()
    exception = _exception_rule("RV-7D-EXC", "A")
    ban = SiteRuleVersion(
        rule_version_id="RV-7D-BAN", rule_id="R-7D-BAN", site_id=SITE_ID,
        category=RuleCategory.LOCAL_RULE, rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        structured_parameters={"employee_id": "A", "weekdays": [weekday], "forbidden_shift_kinds": ["N"]},
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 31),
        changed_at=datetime(2026, 9, 1, 9), changed_by="COORD-T018", supersedes_rule_version_id=None,
        description=None, source=None, reason=None,
    )
    state = base_state(
        employees=(_employee("A", day_only=True),), memberships=(_membership("A"),),
        shift_demands=(n_demand,), site_rules=(exception, ban),
        site_rule_applicability=(_applicability(exception), _applicability(ban)),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z zapisaną regułą obiektu" for b in result.decision_payload.blockers)


def test_b10_7e_rest_still_independently_enforced_alongside_active_exception():
    """Validator-level: a legally exempted DAY_ONLY N Assignment (no
    DAY_ONLY-01) must still trip REST-01 independently against a too-close
    fixed Assignment -- the exception composes with REST-01 via AND, it does
    not short-circuit the rest of validate()."""
    demand_n = _n_demand(6)
    a = _employee("A", day_only=True)
    earlier_fixed = Assignment(
        "earlier", "test-v1", "A", datetime(2026, 10, 6, 7, 0), datetime(2026, 10, 6, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None,
    )
    exceptional_n = Assignment(
        "exceptional-n", "test-v1", "A", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_n.demand_id, None,
    )
    rule = _exception_rule("RV-7E", "A")
    state = base_state(
        employees=(a,), shift_demands=(demand_n,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),), month=B_MONTH,
    )
    report = validate(state, [earlier_fixed, exceptional_n])
    assert not report.hard_pass
    assert any(d.rule == "REST-01" for d in report.violation_details)
    assert not any(d.rule == "DAY_ONLY-01" for d in report.violation_details)


def test_b10_7f_load_still_independently_enforced_alongside_active_exception():
    """Validator-level: LOAD-01 is re-derived independently of DAY_ONLY-01 --
    a legally exempted N Assignment still counts toward the rolling-window
    hour total and can still trip LOAD-01."""
    demand_n = _n_demand(6)
    a = _employee("A", day_only=True)
    heavy_fixed = tuple(
        Assignment(f"heavy-{d}", "test-v1", "A", datetime(2026, 10, d, 5, 0), datetime(2026, 10, d, 17, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None)
        for d in (1, 2, 3, 4, 5)
    )
    exceptional_n = Assignment(
        "exceptional-n", "test-v1", "A", demand_n.start_datetime, demand_n.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand_n.demand_id, None,
    )
    rule = _exception_rule("RV-7F", "A")
    state = base_state(
        employees=(a,), shift_demands=(demand_n,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),), month=B_MONTH,
    )
    state = replace(state, profile=replace(state.profile, rolling_7d_decision_threshold_hours=11))
    report = validate(state, list(heavy_fixed) + [exceptional_n])
    assert not report.hard_pass
    assert any(d.rule == "LOAD-01" for d in report.violation_details)
    assert not any(d.rule == "DAY_ONLY-01" for d in report.violation_details)


def test_b10_7g_day_shift_off_still_blocks_in_fallback_pass():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-7G", "A")
    day_off = AvailabilityRecord("do1", "do1v1", "A", AvailabilityKind.DAY_SHIFT_OFF, date(2026, 10, 6), date(2026, 10, 6), True, None, None)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(_n_demand(6),), availability_records=(day_off,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "DAY_SHIFT_OFF-01" for b in result.decision_payload.blockers)


def test_b10_7h_unavailable_24h_still_blocks_in_fallback_pass():
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-7H", "A")
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 6), date(2026, 10, 6), True, None, None)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(_n_demand(6),), availability_records=(unavailable,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z checkbox: Ogólna dostępność" for b in result.decision_payload.blockers)


# B10.8 -----------------------------------------------------------------------


def test_b10_8_stage1_no_eligible_employee_reaches_stage2(monkeypatch):
    demand = _n_demand(6)
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-8", "A")
    calls = _tracking_solve(monkeypatch)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(demand,), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert [c[0] for c in calls] == [False, True]


# B10.9 -----------------------------------------------------------------------


def test_b10_9_technical_stage1_status_stops_without_retry(monkeypatch):
    calls = []

    def _fake(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False):
        calls.append(allow_day_only_n_fallback)
        return SolverOutcome("UNKNOWN", None, [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake)
    state = base_state(shift_demands=(_n_demand(6),), month=B_MONTH)
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert calls == [False]


# B10.10 ----------------------------------------------------------------------


def test_b10_10_stage2_failure_reaches_stage3(monkeypatch):
    calls = []

    def _fake(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False):
        calls.append((allow_day_only_n_fallback, allow_emergency_24h))
        return SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake)
    state = base_state(shift_demands=(_n_demand(6),), month=B_MONTH)
    plan(state)
    assert (True, True) in calls


# B10.11 ----------------------------------------------------------------------


def test_b10_11_day_only_fallback_alone_wins_without_reaching_emergency(monkeypatch):
    demand = _n_demand(6)
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-11", "A")
    calls = _tracking_solve(monkeypatch)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),),
        shift_demands=(demand,), site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert calls == [(False, False), (True, False)]
    assert not any("emergency" in (a.work_period_id or "") for a in result.candidates[0])


# B10.12 ----------------------------------------------------------------------


def test_b10_12_stage3_infeasible_advances_to_uncapped_stage4(monkeypatch):
    calls = []

    def _fake(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False):
        calls.append((enforce_load_cap, allow_day_only_n_fallback, allow_emergency_24h))
        return SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})

    monkeypatch.setattr(engine_module, "solve", _fake)
    state = base_state(shift_demands=(_n_demand(6),), month=B_MONTH)
    plan(state)
    assert (False, True, True) in calls


# B10.13 ----------------------------------------------------------------------


def test_b10_13_replan_reshuffle_and_exceptional_n_coexist_correctly():
    """Baseline keeps C on D1 (0 reshuffle); C is unavailable on N2's date, so
    N2 is only coverable by A via the exception (1 exceptional N). Both
    phases run and neither corrupts the other's result -- REPLAN-MIN-01's own
    priority over ordinary SOFT is covered unchanged by
    test_replan_minimal_reshuffle.py."""
    d1 = _d_demand(6)
    n2 = _n_demand(13)
    a = _employee("A", day_only=True)
    c = _employee("C")
    rule = _exception_rule("RV-13", "A")
    c_leave = AvailabilityRecord("c-leave", "av1", "C", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 13), date(2026, 10, 13), True, None, None)
    baseline = Assignment(
        "baseline-c-d1", "test-v1", "C", d1.start_datetime, d1.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d1.demand_id, None,
    )
    state = base_state(
        employees=(a, c), memberships=(_membership("A"), _membership("C")),
        shift_demands=(d1, n2), existing_assignments=(baseline,), availability_records=(c_leave,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    by_demand = {a.covers_demand_id: a.employee_id for a in result.candidates[0]}
    assert by_demand[d1.demand_id] == "C"
    assert by_demand[n2.demand_id] == "A"


# B10.14 ----------------------------------------------------------------------


def _b10_14_seed_context(conn, coord: str, site: str, profile_id: str, emp: str, month: date):
    from rota.application import bootstrap, durable_inputs, rule_decisions
    from rota.domain import Coordinator, CoordinatorSiteAssociation, ShiftKind, Site, SiteProfile, StandardShift

    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coord, site_id=site, coordinator=Coordinator(coord, "B14 coordinator", True),
        site_profile=SiteProfile(profile_id, "B14 profile", True, [StandardShift(ShiftKind.N, datetime(2026, 10, 1, 17).time(), datetime(2026, 10, 2, 5).time(), True, 1)], True, False, False, False, 1, 999),
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coord, site_id=site, site=Site(site, profile_id, "B14 site", True),
        association=CoordinatorSiteAssociation(coord, site, True),
    )
    durable_inputs.update_employee(conn, coordinator_id=coord, site_id=site, employee=_employee(emp, day_only=True))
    membership = SiteMembership(emp, site, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    durable_inputs.update_membership(conn, coordinator_id=coord, site_id=site, membership=membership)
    durable_inputs.set_target_hours(conn, coordinator_id=coord, site_id=site, employee_id=emp, month=month, target_hours=372)
    for day in range(1, calendar_module.monthrange(2026, 10)[1] + 1):
        durable_inputs.set_calendar_day(conn, coordinator_id=coord, site_id=site, day=CalendarDay(date(2026, 10, day), False))
    return rule_decisions.record_structured_rule_decision(
        conn, coordinator_id=coord, site_id=site, rule_id="B14-RULE", statement="authorized fallback",
        effective_from=month, recorded_at=datetime(2026, 9, 1, 9),
        rule_content=rule_decisions.NewRuleContent(
            RuleCategory.CONFIRMED_EXCEPTION, EMPLOYEE_DAY_ONLY_N_EXCEPTION, {"employee_id": emp},
            RuleEnforcement.HARD, RuleResolution.RESOLVED, date(2026, 10, 31), None, None, None,
        ),
    )


def test_b10_14_durable_provenance_reconstructible_from_applied_rule_version_ids(tmp_path):
    """B-R11-2: exercise the real persisted path -- open_store -> bootstrap ->
    PLAN -> select_candidate -> finalize -> close -> reopen -> reconstruct
    the canonical rule_version_id from ScheduleVersion.applied_rule_version_ids
    -- not an in-memory surrogate of the same computation."""
    from rota.application import lifecycle_ops, memory_read, open_month, plan_ops, store
    from rota.application.assembler import assemble_planning_state

    coord, site, profile_id, emp = "B14-COORD", "B14-SITE", "B14-PROFILE", "B14-EMP"
    month = date(2026, 10, 1)
    db_path = tmp_path / "t018-b10-14.db"

    conn = store.open_store(db_path)
    original = _b10_14_seed_context(conn, coord, site, profile_id, emp, month)
    result = plan_ops.plan_month(conn, site_id=site, month=month, coordinator_id=coord, effective_from=month)
    assert result.status == "FEASIBLE"
    warning = next(w for w in result.warnings if "DAY_ONLY-N-FALLBACK-01" in w)
    plan_ops.select_candidate(conn, site_id=site, month=month, candidate=result.candidates[0], coordinator_id=coord)
    lifecycle_ops.finalize(conn, site_id=site, month=month, coordinator_id=coord, acknowledged_deviation_ids=set())
    conn.close()

    reopened = store.open_store(db_path)
    view = open_month.open_month(reopened, site_id=site, month=month)
    state, _ = assemble_planning_state(reopened, site_id=site, month=month)
    applied = set(view.current_version.applied_rule_version_ids)
    assert original.rule_version_id in applied
    assignment = next(a for a in state.existing_assignments if a.employee_id == emp)
    demand = next(d for d in state.shift_demands if d.demand_id == assignment.covers_demand_id)
    resolved, _, applicability = memory_read.effective_rules_for_month(reopened, site_id=site, month=month)
    applicable = hard_rules_applicable_on([r for r in resolved if r.rule_version_id in applied], applicability, demand.start_datetime.date())
    reconstructed = day_only_n_exception_authorizing_rule_version_id(applicable, emp)
    assert reconstructed == original.rule_version_id
    assert f"demand={demand.demand_id}" in warning
    assert f"rule_version_id={reconstructed}" in warning
    reopened.close()


# B10.15 ----------------------------------------------------------------------


def test_b10_15_validator_independently_catches_unauthorized_day_only_n():
    demand = _n_demand(6)
    a = _employee("A", day_only=True)
    assignment = Assignment(
        "unauthorized-n", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    state = base_state(employees=(a,), shift_demands=(demand,), month=B_MONTH)
    report = validate(state, [assignment])
    assert not report.hard_pass
    assert any("DAY_ONLY-01" in v for v in report.violations)


# B10.16 ----------------------------------------------------------------------


def test_b10_16_two_equivalent_exception_families_give_one_canonical_id_regardless_of_order():
    rule_a = _exception_rule("RV-16-B", "A", rule_id="R-FAMILY-1")
    rule_b = _exception_rule("RV-16-A", "A", rule_id="R-FAMILY-2")  # lexicographically smaller
    assert day_only_n_exception_authorizing_rule_version_id([rule_a, rule_b], "A") == "RV-16-A"
    assert day_only_n_exception_authorizing_rule_version_id([rule_b, rule_a], "A") == "RV-16-A"

    demand = _n_demand(6)
    state = base_state(
        employees=(_employee("A", day_only=True),), memberships=(_membership("A"),),
        shift_demands=(demand,), site_rules=(rule_a, rule_b),
        site_rule_applicability=(_applicability(rule_a), _applicability(rule_b)),
        month=B_MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    fallback_warnings = [w for w in result.warnings if "DAY_ONLY-N-FALLBACK-01" in w]
    assert len(fallback_warnings) == 1
    assert "rule_version_id=RV-16-A" in fallback_warnings[0]


# B10.17 ----------------------------------------------------------------------


def test_b10_17_later_non_applied_rule_does_not_change_historical_reconstruction():
    original_rule = _exception_rule("RV-17-ORIGINAL", "A")
    later_rule = _exception_rule("RV-17-A-LATER", "A")  # smaller id, would win if wrongly considered
    applied_rule_version_ids = {"RV-17-ORIGINAL"}
    persisted_rules = tuple(r for r in (original_rule, later_rule) if r.rule_version_id in applied_rule_version_ids)
    applicable = hard_rules_applicable_on(
        persisted_rules, (_applicability(original_rule), _applicability(later_rule)), date(2026, 10, 6)
    )
    reconstructed_id = day_only_n_exception_authorizing_rule_version_id(applicable, "A")
    assert reconstructed_id == "RV-17-ORIGINAL"


if __name__ == "__main__":
    print("test_t018 module OK")
