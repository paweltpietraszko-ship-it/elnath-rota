"""Owner's March 2027 scenario through catalog generation, planner and validator."""
from __future__ import annotations

import calendar
import json
from collections import Counter
from datetime import date, datetime, time

from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftCatalogKind,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    SiteRuleVersion,
    StandardShift,
    WorkBalance,
)
from rota.planning.engine import plan
from rota.planning.shift_catalog import generate_catalog_demands
from rota.planning.site_rules import EMPLOYEE_ALLOWED_SHIFT_KINDS, EMPLOYEE_DAY_ONLY_N_EXCEPTION
from rota.planning.state import PlanningState, SiteRuleApplicability
from rota.planning.timeutil import overlaps_date_range
from rota.planning.validator import validate


SITE_ID = "SITE-MARCH-2027"
PROFILE_ID = "PROFILE-MARCH-2027"
MONTH = date(2027, 3, 1)
DAY_ONLY_EXCEPTION_ID = "RULE-A-DAY-ONLY-N-EXCEPTION"


def build_profile() -> SiteProfile:
    shifts = [
        StandardShift(
            ShiftKind.D, time(5), time(17), False, 1,
            ShiftCatalogKind.H12, 11,
        ),
        StandardShift(
            ShiftKind.N, time(17), time(5), True, 1,
            ShiftCatalogKind.H12, 11,
        ),
    ]
    return SiteProfile(
        PROFILE_ID, "Single coverage 05-17 / 17-05", True, shifts,
        True, False, False, False, 1, 60,
    )


def _availability(
    availability_id: str, employee_id: str, kind: AvailabilityKind,
    start: date, end: date,
) -> AvailabilityRecord:
    return AvailabilityRecord(
        availability_id, "march-availability-v1", employee_id, kind,
        start, end, True, None, None,
    )


def _rule(
    version_id: str, rule_id: str, rule_kind: str, params: dict,
    start: date, end: date, category: RuleCategory = RuleCategory.LOCAL_RULE,
) -> SiteRuleVersion:
    return SiteRuleVersion(
        version_id, rule_id, SITE_ID, category, rule_kind, params,
        RuleEnforcement.HARD, RuleResolution.RESOLVED, start, end,
        datetime(2027, 2, 20, 12), "COORD-1", None,
        "March 2027 scenario rule", "owner scenario", "declared availability",
    )


def _rules() -> tuple[tuple[SiteRuleVersion, ...], tuple[SiteRuleApplicability, ...]]:
    exception = _rule(
        DAY_ONLY_EXCEPTION_ID, "R-A-DAY-ONLY-N", EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        {"employee_id": "A"}, date(2027, 3, 1), date(2027, 3, 31),
        RuleCategory.CONFIRMED_EXCEPTION,
    )
    doctor_2 = _rule(
        "RULE-C-DOCTOR-02", "R-C-DOCTOR-02", EMPLOYEE_ALLOWED_SHIFT_KINDS,
        {"employee_id": "C", "allowed_shift_kinds": ["N"]},
        date(2027, 3, 2), date(2027, 3, 2),
    )
    doctor_17 = _rule(
        "RULE-C-DOCTOR-17", "R-C-DOCTOR-17", EMPLOYEE_ALLOWED_SHIFT_KINDS,
        {"employee_id": "C", "allowed_shift_kinds": ["N"]},
        date(2027, 3, 17), date(2027, 3, 17),
    )
    rules = (exception, doctor_2, doctor_17)
    applicability = tuple(
        SiteRuleApplicability(rule.rule_version_id, rule.effective_from, rule.effective_to)
        for rule in rules
    )
    return rules, applicability


def build_scenario(*, with_day_only_exception: bool = True) -> PlanningState:
    profile = build_profile()
    demands = generate_catalog_demands(profile, MONTH)
    employees = (
        Employee("A", "Day only", date(2020, 1, 1), None, True),
        Employee("B", "Sick leave", date(2020, 1, 1), None, False),
        Employee("C", "Doctor visits", date(2020, 1, 1), None, False),
        Employee("D", "Wedding leave", date(2020, 1, 1), None, False),
        Employee("E", "Friday treatments", date(2020, 1, 1), None, False),
    )
    memberships = tuple(
        SiteMembership(
            employee.employee_id, SITE_ID, MembershipKind.LOCAL, True,
            ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        )
        for employee in employees
    )
    fridays = [
        date(2027, 3, day) for day in range(1, calendar.monthrange(2027, 3)[1] + 1)
        if date(2027, 3, day).isoweekday() == 5
    ]
    availability = (
        _availability("B-L4", "B", AvailabilityKind.SICK_LEAVE, date(2027, 3, 2), date(2027, 3, 19)),
        _availability("D-WEDDING", "D", AvailabilityKind.LEAVE_GRANTED, date(2027, 3, 17), date(2027, 3, 21)),
        *(
            _availability(f"E-FRIDAY-{day}", "E", AvailabilityKind.UNAVAILABLE_24H, day, day)
            for day in fridays
        ),
    )
    rules, applicability = _rules()
    if not with_day_only_exception:
        rules = tuple(rule for rule in rules if rule.rule_version_id != DAY_ONLY_EXCEPTION_ID)
        applicability = tuple(item for item in applicability if item.rule_version_id != DAY_ONLY_EXCEPTION_ID)
    work_balances = tuple(WorkBalance(employee.employee_id, MONTH, 168, 0, 0, 0, 0, 0) for employee in employees)
    # T018 R10: A-R4-1 fail-closed requires complete CalendarDay coverage
    # whenever a qualifying SICK_LEAVE (B, above) intersects the month --
    # this synthetic harness supplies its own complete, non-holiday March
    # 2027 calendar rather than leaving the fail-closed gate unfed.
    calendar_days = tuple(
        CalendarDay(date(2027, 3, day), False) for day in range(1, calendar.monthrange(2027, 3)[1] + 1)
    )
    return PlanningState(
        site=Site(SITE_ID, PROFILE_ID, "Owner March 2027", True),
        profile=profile, month=MONTH, calendar_days=calendar_days, boundary_assignments=(),
        memberships=memberships, employees=employees, external_windows=(),
        availability_records=availability, site_rules=rules, unresolved_site_rules=(),
        site_rule_applicability=applicability, shift_demands=demands,
        existing_assignments=(), deviations=(), work_balances=work_balances,
        holiday_history=(), other_site_assignments=(), schedule_version_id="march-2027-v1",
        boundary_shift_demands=(),
    )


def _result_summary(state: PlanningState) -> dict:
    result = plan(state)
    assignments = result.candidates[0] if result.candidates else []
    validation = validate(state, assignments) if assignments else None
    demand_by_id = {d.demand_id: d for d in state.shift_demands}
    by_employee: dict[str, Counter] = {employee.employee_id: Counter() for employee in state.employees}
    for assignment in assignments:
        demand = demand_by_id[assignment.covers_demand_id]
        by_employee[assignment.employee_id][demand.shift_kind.value] += 1
    fridays = [date(2027, 3, day) for day in (5, 12, 19, 26)]
    constraint_checks = {
        "B_assignments_overlapping_sick_leave": sum(
            assignment.employee_id == "B"
            and overlaps_date_range(assignment.start_datetime, assignment.end_datetime, date(2027, 3, 2), date(2027, 3, 19))
            for assignment in assignments
        ),
        "D_assignments_overlapping_wedding_leave": sum(
            assignment.employee_id == "D"
            and overlaps_date_range(assignment.start_datetime, assignment.end_datetime, date(2027, 3, 17), date(2027, 3, 21))
            for assignment in assignments
        ),
        "E_assignments_overlapping_friday_treatments": sum(
            assignment.employee_id == "E"
            and any(overlaps_date_range(assignment.start_datetime, assignment.end_datetime, day, day) for day in fridays)
            for assignment in assignments
        ),
        "C_day_shifts_starting_on_doctor_days": sum(
            assignment.employee_id == "C"
            and demand_by_id[assignment.covers_demand_id].shift_kind == ShiftKind.D
            and demand_by_id[assignment.covers_demand_id].start_datetime.date() in {date(2027, 3, 2), date(2027, 3, 17)}
            for assignment in assignments
        ),
    }
    return {
        "status": result.status,
        "assignment_count": len(assignments),
        "hard_pass": bool(validation and validation.hard_pass),
        "violations": [] if validation is None else validation.violations,
        "warning_count": 0 if validation is None else len(validation.warnings),
        "shifts_by_employee": {
            employee_id: {"D": counts["D"], "N": counts["N"], "hours": 12 * sum(counts.values())}
            for employee_id, counts in by_employee.items()
        },
        "doctor_day_assignments": sorted(
            (demand.start_datetime.date().isoformat(), demand.shift_kind.value)
            for assignment in assignments if assignment.employee_id == "C"
            for demand in (demand_by_id[assignment.covers_demand_id],)
            if demand.start_datetime.date() in {date(2027, 3, 2), date(2027, 3, 17)}
        ),
        "constraint_checks": constraint_checks,
    }


def run_probe() -> dict:
    with_exception = _result_summary(build_scenario(with_day_only_exception=True))
    without_exception = _result_summary(build_scenario(with_day_only_exception=False))
    return {
        "scenario": "owner March 2027 single coverage",
        "generated_demand_count": 62,
        "with_day_only_n_exception": with_exception,
        "without_day_only_n_exception_control": without_exception,
    }


def test_owner_march_2027_scenario() -> None:
    report = run_probe()
    assert report["generated_demand_count"] == 62
    with_exception = report["with_day_only_n_exception"]
    assert with_exception["status"] == "FEASIBLE"
    assert with_exception["assignment_count"] == 62
    assert with_exception["hard_pass"] is True
    assert all(kind == "N" for _, kind in with_exception["doctor_day_assignments"])
    assert set(with_exception["constraint_checks"].values()) == {0}
    # Owner decision 2026-08-19: an applicable exception is fallback
    # permission, not ordinary N eligibility. The same month is feasible
    # without the exception, so the first normal pass must win with A on 0 N.
    assert with_exception["shifts_by_employee"]["A"]["N"] == 0
    without_exception = report["without_day_only_n_exception_control"]
    assert without_exception["status"] == "FEASIBLE"
    assert without_exception["assignment_count"] == 62
    assert without_exception["hard_pass"] is True
    assert without_exception["shifts_by_employee"]["A"]["N"] == 0
    assert set(without_exception["constraint_checks"].values()) == {0}


if __name__ == "__main__":
    print(json.dumps(run_probe(), ensure_ascii=False, indent=2))
