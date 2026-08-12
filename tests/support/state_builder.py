"""Build a real rota.domain.PlanningState from a structured fixture dict.

This is test infrastructure, not the product. PlanningEngine itself must not
read JSON/CSV directly (CAL-04) — this module plays the role of the future
"PlanningState assembly" layer for test purposes only, so ROTA-REG-001 and
sibling scenarios can be exercised through the real domain types instead of
through ad-hoc arrays.

Generic over the fixture's year/month/employees/rules: nothing here assumes
October 2026 or the A-E employee set.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    WorkBalance,
)
from rota.planning.state import PlanningState

DEFAULT_SITE_ID = "test-site"
DEFAULT_PROFILE_ID = "OCHRONA"


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _build_shifts(fixture: dict) -> list[StandardShift]:
    demand = fixture["demand"]
    day_cfg = fixture["shifts"]["D"]
    night_cfg = fixture["shifts"]["N"]
    return [
        StandardShift(ShiftKind.D, _parse_time(day_cfg["start"]), _parse_time(day_cfg["end"]), False, demand["D_per_day"]),
        StandardShift(ShiftKind.N, _parse_time(night_cfg["start"]), _parse_time(night_cfg["end_next_day"]), True, demand["N_per_day"]),
    ]


def _build_profile(fixture: dict, profile_id: str) -> SiteProfile:
    rules = fixture["rules"]
    return SiteProfile(
        profile_id=profile_id,
        display_name=profile_id,
        active=True,
        standard_shifts=_build_shifts(fixture),
        day_only_blocks_n=True,
        external_support_enabled=any(rules.get("EXTERNAL_SUPPORT", {}).values()),
        training_s_enabled="TRAINING_S" in rules,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=rules["ROLLING_7D_MAX_HOURS_BEFORE_DECISION_REQUIRED"],
    )


def _build_employees(fixture: dict, month: date) -> tuple[Employee, ...]:
    day_only = fixture["rules"].get("DAY_ONLY", {})
    return tuple(
        Employee(employee_id=eid, display_name=eid, active_from=month, active_to=None, day_only=bool(day_only.get(eid)))
        for eid in fixture["employees"]
    )


def _build_memberships(fixture: dict, site_id: str) -> tuple[SiteMembership, ...]:
    return tuple(
        SiteMembership(
            employee_id=eid, site_id=site_id, membership_kind=MembershipKind.LOCAL, enabled=True,
            readiness_state=ReadinessState.READY_FOR_PRIMARY, readiness_source=ReadinessSource.DEFAULT,
        )
        for eid in fixture["employees"]
    )


def _availability_records(fixture: dict, month: date) -> tuple[AvailabilityRecord, ...]:
    records: list[AvailabilityRecord] = []
    rules = fixture["rules"]
    for eid, days in rules.get("DAY_SHIFT_OFF", {}).items():
        for day in days:
            d = date(month.year, month.month, day)
            records.append(_availability(f"dso-{eid}-{day}", eid, AvailabilityKind.DAY_SHIFT_OFF, d, d))
    for eid, ranges in rules.get("LEAVE_GRANTED", {}).items():
        for r in ranges:
            records.append(_availability(
                f"leave-{eid}-{r['from']}", eid, AvailabilityKind.LEAVE_GRANTED,
                date(month.year, month.month, r["from"]), date(month.year, month.month, r["to"]),
            ))
    for eid, days in rules.get("UNAVAILABLE_24H", {}).items():
        for day in days:
            d = date(month.year, month.month, day)
            records.append(_availability(f"unavail-{eid}-{day}", eid, AvailabilityKind.UNAVAILABLE_24H, d, d))
    return tuple(records)


def _availability(record_id: str, employee_id: str, kind: AvailabilityKind, start: date, end: date) -> AvailabilityRecord:
    return AvailabilityRecord(
        availability_id=record_id, availability_version_id=f"{record_id}-v1", employee_id=employee_id,
        kind=kind, start_date=start, end_date=end, active=True,
        supersedes_availability_version_id=None, note=None,
    )


def _shift_demands(fixture: dict, month: date, version_id: str) -> tuple[ShiftDemand, ...]:
    num_days = calendar.monthrange(month.year, month.month)[1]
    demand_cfg = fixture["demand"]
    shifts = fixture["shifts"]
    demands = []
    for day in range(1, num_days + 1):
        day_date = date(month.year, month.month, day)
        demands.append(_demand(day_date, "D", shifts["D"]["start"], shifts["D"]["end"], False, demand_cfg["D_per_day"], version_id))
        demands.append(_demand(day_date, "N", shifts["N"]["start"], shifts["N"]["end_next_day"], True, demand_cfg["N_per_day"], version_id))
    return tuple(demands)


def _demand(day: date, kind: str, start_str: str, end_str: str, end_next_day: bool, count: int, version_id: str) -> ShiftDemand:
    start_dt = datetime.combine(day, _parse_time(start_str))
    end_day = day + timedelta(days=1) if end_next_day else day
    end_dt = datetime.combine(end_day, _parse_time(end_str))
    return ShiftDemand(f"{day.isoformat()}-{kind}", version_id, start_dt, end_dt, count)


def _training_s_existing_assignment(fixture: dict, month: date, demands: tuple[ShiftDemand, ...], version_id: str):
    training = fixture["rules"].get("TRAINING_S")
    if not training:
        return ()
    demand_id = f"{date(month.year, month.month, training['date']).isoformat()}-{training['shift']}"
    matching = next(d for d in demands if d.demand_id == demand_id)
    assignment = Assignment(
        assignment_id=f"existing-{demand_id}", schedule_version_id=version_id, employee_id=training["mentor"],
        start_datetime=matching.start_datetime, end_datetime=matching.end_datetime, role=AssignmentRole.PRIMARY,
        # frozen=True: the coordinator attaching S to this shift is exactly
        # the kind of explicit decision that must not be redistributed by
        # REPLAN (rota.planning.solver.fixed_existing_assignments).
        state=AssignmentState.PLANNED, frozen=True, covers_demand_id=demand_id, mentor_primary_assignment_id=None,
    )
    return (assignment,)


def _work_balances(fixture: dict, month: date) -> tuple[WorkBalance, ...]:
    targets = fixture["rules"].get("TARGET_HOURS", {})
    return tuple(
        WorkBalance(eid, month, hours, 0, 0, 0, 0, 0) for eid, hours in targets.items()
    )


def _calendar_days(month: date) -> tuple[CalendarDay, ...]:
    num_days = calendar.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, d), False) for d in range(1, num_days + 1))


def build_state_from_fixture(
    fixture: dict, profile_id: str = DEFAULT_PROFILE_ID, site_id: str = DEFAULT_SITE_ID,
    version_id: str = "test-v1",
) -> PlanningState:
    """Build a full PlanningState from a ROTA-REG-001-shaped fixture dict."""
    month = date(fixture["period"]["year"], fixture["period"]["month"], 1)
    profile = _build_profile(fixture, profile_id)
    demands = _shift_demands(fixture, month, version_id)
    return PlanningState(
        site=Site(site_id, profile_id, site_id, True),
        profile=profile,
        month=month,
        calendar_days=_calendar_days(month),
        boundary_assignments=(),
        memberships=_build_memberships(fixture, site_id),
        employees=_build_employees(fixture, month),
        external_windows=(),
        availability_records=_availability_records(fixture, month),
        site_rules=(),
        unresolved_site_rules=(),
        shift_demands=demands,
        existing_assignments=_training_s_existing_assignment(fixture, month, demands, version_id),
        deviations=(),
        work_balances=_work_balances(fixture, month),
        holiday_history=(),
        other_site_assignments=(),
        schedule_version_id=version_id,
    )


if __name__ == "__main__":
    print("state_builder module OK")
