"""Adapter from independent benchmark scenarios to production PlanningState.

Only this module knows production domain types. The reference oracle does not
import or call this adapter; neutral demand recipes live with scenario data.
"""
from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta

from benchmarks.real_object_scenarios import (
    EXTERNAL_EMPLOYEES,
    LOCAL_EMPLOYEES,
    SITE_ID,
    demands_for_month,
)
from benchmarks.real_object_types import RuleSpec, ScenarioSpec
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    ExternalSupportWindow,
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
    SiteProfile,
    SiteRuleVersion,
    StandardShift,
    WorkBalance,
)
from rota.planning.state import PlanningState, SiteRuleApplicability

PROFILE_ID = "BENCHMARK-OCHRONA"


def _profile(scenario: ScenarioSpec) -> SiteProfile:
    """Build the production profile used by every real-object case."""
    shifts = [
        StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1),
        StandardShift(ShiftKind.N, time(17, 0), time(5, 0), True, 1),
    ]
    return SiteProfile(
        PROFILE_ID, "Benchmark Ochrona", True, shifts, True,
        scenario.external_support_enabled, False, True, 2, 60,
    )


def _employees(scenario: ScenarioSpec) -> tuple[Employee, ...]:
    """Build exactly five LOCAL people plus explicit X/Y external people."""
    active_from = scenario.month - timedelta(days=365)
    return tuple(
        Employee(employee, employee, active_from, None, employee == "C")
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    )


def _memberships() -> tuple[SiteMembership, ...]:
    """Build five LOCAL memberships and X/Y EXTERNAL_SUPPORT memberships."""
    memberships = []
    for employee in LOCAL_EMPLOYEES:
        memberships.append(SiteMembership(
            employee, SITE_ID, MembershipKind.LOCAL, True,
            ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        ))
    for employee in EXTERNAL_EMPLOYEES:
        memberships.append(SiteMembership(
            employee, SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True,
            ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        ))
    return tuple(memberships)


def _availability(scenario: ScenarioSpec) -> tuple[AvailabilityRecord, ...]:
    """Map benchmark availability facts without using production builders."""
    records = []
    for index, spec in enumerate(scenario.availability):
        kind = AvailabilityKind(spec.kind)
        record_id = f"bench-av-{scenario.case_id}-{index}"
        records.append(AvailabilityRecord(
            record_id, f"{record_id}-v1", spec.employee_id, kind,
            spec.start_date, spec.end_date, True, None, "real-object benchmark",
        ))
    return tuple(records)


def _windows(scenario: ScenarioSpec) -> tuple[ExternalSupportWindow, ...]:
    """Map only currently confirmed windows; probe windows never reach production."""
    return tuple(
        ExternalSupportWindow(
            spec.window_id, spec.employee_id, spec.site_id, spec.start, spec.end,
            spec.active, ShiftKind(spec.allowed_shift_kind) if spec.allowed_shift_kind else None,
        )
        for spec in scenario.external_windows
    )


def _rule_params(spec: RuleSpec) -> dict:
    """Map benchmark rule data to one T007 parameter shape."""
    if spec.rule_kind == "EMPLOYEE_ALLOWED_SHIFT_KINDS":
        return {"employee_id": spec.employee_id, "allowed_shift_kinds": list(spec.shift_kinds)}
    if spec.rule_kind == "EMPLOYEE_ALLOWED_WEEKDAYS":
        return {"employee_id": spec.employee_id, "allowed_weekdays": list(spec.weekdays)}
    if spec.rule_kind == "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS":
        return {
            "employee_id": spec.employee_id,
            "weekdays": list(spec.weekdays),
            "forbidden_shift_kinds": list(spec.shift_kinds),
        }
    raise ValueError(f"unsupported benchmark rule_kind: {spec.rule_kind}")


def _site_rules(scenario: ScenarioSpec) -> tuple[tuple[SiteRuleVersion, ...], tuple[SiteRuleApplicability, ...]]:
    """Build RESOLVED+HARD rules and whole-month applicability slices."""
    end_day = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    month_end = scenario.month.replace(day=end_day)
    rules = []
    applicability = []
    for index, spec in enumerate(scenario.site_rules):
        rule = SiteRuleVersion(
            spec.rule_version_id, f"bench-family-{scenario.case_id}-{index}", SITE_ID,
            RuleCategory.LOCAL_RULE, spec.rule_kind, _rule_params(spec),
            RuleEnforcement.HARD, RuleResolution.RESOLVED, scenario.month, month_end,
            datetime.combine(scenario.month, time()), "benchmark-owner", None,
            "real-object benchmark rule", "benchmark", None,
        )
        rules.append(rule)
        applicability.append(SiteRuleApplicability(spec.rule_version_id, scenario.month, month_end))
    return tuple(rules), tuple(applicability)


def _demands(scenario: ScenarioSpec, version_id: str) -> tuple[ShiftDemand, ...]:
    """Map independent demand facts to production ShiftDemand objects."""
    return tuple(
        ShiftDemand(demand.demand_id, version_id, demand.start, demand.end, 1)
        for demand in demands_for_month(scenario)
    )


def _assignment(spec, version_id: str) -> Assignment:
    """Map one fixed benchmark fact to a production Assignment."""
    return Assignment(
        spec.assignment_id, version_id, spec.employee_id, spec.start, spec.end,
        AssignmentRole.PRIMARY, AssignmentState(spec.state), spec.frozen,
        spec.demand_id, None,
    )


def _calendar(scenario: ScenarioSpec) -> tuple[CalendarDay, ...]:
    """Build a complete deterministic non-holiday calendar for this benchmark."""
    count = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    return tuple(CalendarDay(scenario.month.replace(day=day), False) for day in range(1, count + 1))


def _targets(scenario: ScenarioSpec) -> tuple[WorkBalance, ...]:
    """Provide SOFT targets without changing any HARD reference classification."""
    strict = dict(scenario.strict_monthly_hours)
    default_target = 144
    return tuple(
        WorkBalance(employee, scenario.month, strict.get(employee, default_target), 0, 0, 0, 0, 0)
        for employee in (*LOCAL_EMPLOYEES, *EXTERNAL_EMPLOYEES)
    )


def build_planning_state(scenario: ScenarioSpec) -> PlanningState:
    """Build the exact production input that will be tested against the oracle."""
    version_id = f"benchmark-{scenario.case_id}"
    rules, applicability = _site_rules(scenario)
    return PlanningState(
        site=Site(SITE_ID, PROFILE_ID, "Real Object Benchmark", True),
        profile=_profile(scenario),
        month=scenario.month,
        calendar_days=_calendar(scenario),
        boundary_assignments=tuple(_assignment(item, "benchmark-boundary") for item in scenario.boundary_assignments),
        memberships=_memberships(),
        employees=_employees(scenario),
        external_windows=_windows(scenario),
        availability_records=_availability(scenario),
        site_rules=rules,
        unresolved_site_rules=(),
        site_rule_applicability=applicability,
        shift_demands=_demands(scenario, version_id),
        existing_assignments=tuple(_assignment(item, version_id) for item in scenario.fixed_demand_assignments),
        deviations=(),
        work_balances=_targets(scenario),
        holiday_history=(),
        other_site_assignments=(),
        schedule_version_id=version_id,
    )


if __name__ == "__main__":
    from benchmarks.real_object_scenarios import core_scenarios

    print(build_planning_state(core_scenarios()[0]).site)
