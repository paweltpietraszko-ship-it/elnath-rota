from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Optional

# --- Enums ---


class ShiftKind(str, Enum):
    D = "D"
    N = "N"


class AssignmentRole(str, Enum):
    PRIMARY = "PRIMARY"
    TRAINEE = "TRAINEE"


class AssignmentState(str, Enum):
    PLANNED = "PLANNED"
    REALIZED = "REALIZED"
    CANCELLED = "CANCELLED"


class AvailabilityKind(str, Enum):
    DAY_SHIFT_OFF = "DAY_SHIFT_OFF"
    UNAVAILABLE_24H = "UNAVAILABLE_24H"
    LEAVE_PLAN = "LEAVE_PLAN"
    LEAVE_GRANTED = "LEAVE_GRANTED"
    # SICK_LEAVE-01: owner decision 2026-08-12, from real ROYALPACK/APEXIM
    # schedules (Grafiki/). HARD-blocks automatic Assignment like
    # LEAVE_GRANTED, and accounts as a flat 8h/day against target_hours
    # regardless of actual shift length (12h D/N). Owner decision 2026-08-13:
    # LEAVE_GRANTED gets the identical 8h/day accounting too, but only in
    # rota.balance's quarterly WorkBalance tracking -- solver.py's live
    # TARGET-01 SOFT ranking stays SICK_LEAVE-only (see
    # rota/planning/absence.py for why: applying it there too shifted
    # ROTA-REG-001's frozen exact-hours oracle).
    SICK_LEAVE = "SICK_LEAVE"


class MembershipKind(str, Enum):
    LOCAL = "LOCAL"
    EXTERNAL_SUPPORT = "EXTERNAL_SUPPORT"


class ReadinessState(str, Enum):
    NOT_READY = "NOT_READY"
    READY_FOR_PRIMARY = "READY_FOR_PRIMARY"


class ReadinessSource(str, Enum):
    DEFAULT = "DEFAULT"
    COORDINATOR_OVERRIDE = "COORDINATOR_OVERRIDE"


class RuleCategory(str, Enum):
    CLIENT_REQUIREMENT = "CLIENT_REQUIREMENT"
    LOCAL_RULE = "LOCAL_RULE"
    CONFIRMED_EXCEPTION = "CONFIRMED_EXCEPTION"


class RuleEnforcement(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    INFORMATIONAL = "INFORMATIONAL"


class RuleResolution(str, Enum):
    RESOLVED = "RESOLVED"
    NEEDS_RESOLUTION = "NEEDS_RESOLUTION"


class DeviationCategory(str, Enum):
    LAW = "LAW"
    CLIENT_REQUIREMENT = "CLIENT_REQUIREMENT"
    LEAVE_OR_TIME_OFF = "LEAVE_OR_TIME_OFF"
    HOURS = "HOURS"
    PREFERENCE = "PREFERENCE"
    COVERAGE = "COVERAGE"


class ScheduleStatus(str, Enum):
    WORKING = "WORKING"
    WORKING_WITH_DEVIATIONS = "WORKING_WITH_DEVIATIONS"
    FINAL_NO_DEVIATIONS = "FINAL_NO_DEVIATIONS"
    FINAL_WITH_DEVIATIONS = "FINAL_WITH_DEVIATIONS"


# --- Value objects ---


@dataclass(frozen=True)
class StandardShift:
    kind: ShiftKind
    start_time: time
    end_time: time
    end_next_day: bool
    required_primary_count: int


# --- Entities ---


@dataclass
class SiteProfile:
    profile_id: str
    display_name: str
    active: bool
    standard_shifts: list[StandardShift]
    day_only_blocks_n: bool
    external_support_enabled: bool
    training_s_enabled: bool
    training_s_weekdays_only: bool
    training_s_default_readiness_threshold: int
    rolling_7d_decision_threshold_hours: int


@dataclass
class Site:
    site_id: str
    profile_id: str
    display_name: str
    active: bool


@dataclass
class Coordinator:
    coordinator_id: str
    display_name: str
    active: bool


@dataclass
class CoordinatorSiteAssociation:
    coordinator_id: str
    site_id: str
    active: bool


@dataclass
class Employee:
    employee_id: str
    display_name: str
    active_from: date
    active_to: Optional[date]
    day_only: bool


@dataclass
class SiteMembership:
    employee_id: str
    site_id: str
    membership_kind: MembershipKind
    enabled: bool
    readiness_state: ReadinessState
    readiness_source: ReadinessSource


@dataclass
class ExternalSupportWindow:
    window_id: str
    employee_id: str
    site_id: str
    start_datetime: datetime
    end_datetime: datetime
    active: bool
    allowed_shift_kind: Optional[ShiftKind]


@dataclass(frozen=True)
class CalendarDay:
    date: date
    holiday: bool


@dataclass
class AvailabilityRecord:
    availability_id: str
    availability_version_id: str
    employee_id: str
    kind: AvailabilityKind
    start_date: date
    end_date: date  # inclusive; == start_date dla 1 dnia
    active: bool
    supersedes_availability_version_id: Optional[str]
    note: Optional[str]


@dataclass
class SiteRule:
    rule_id: str


RuleParameters = object  # CONTRACT_GAP — osobny task
# typed union per rule_kind; zamrozone 2026-08-11


@dataclass
class SiteRuleVersion:
    rule_version_id: str
    rule_id: str
    site_id: str
    category: RuleCategory
    rule_kind: Optional[str]
    structured_parameters: Optional["RuleParameters"]
    # rule_kind catalog: CONTRACT_GAP — osobny task
    enforcement: RuleEnforcement
    resolution_status: RuleResolution
    effective_from: date
    effective_to: Optional[date]
    changed_at: datetime
    changed_by: str  # coordinator_id
    supersedes_rule_version_id: Optional[str]
    description: Optional[str]
    source: Optional[str]
    reason: Optional[str]


@dataclass
class WorkBalance:
    employee_id: str
    month: date  # pierwszy dzien miesiaca
    target_hours: int
    planned_hours: int
    realized_hours: int
    month_balance: int
    unresolved_carryover: int
    quarter_balance: int


@dataclass
class ScheduleVersion:
    version_id: str
    site_id: str
    month: date  # pierwszy dzien miesiaca
    parent_version_id: Optional[str]
    created_at: datetime
    created_by: str  # coordinator_id
    status: ScheduleStatus
    applied_rule_version_ids: list[str]


@dataclass
class ShiftDemand:
    demand_id: str
    schedule_version_id: str
    start_datetime: datetime
    end_datetime: datetime
    required_primary_count: int


@dataclass
class Assignment:
    assignment_id: str
    schedule_version_id: str
    employee_id: str
    start_datetime: datetime
    end_datetime: datetime
    role: AssignmentRole
    state: AssignmentState
    frozen: bool
    covers_demand_id: Optional[str]
    # wymagane gdy role=PRIMARY; absent gdy TRAINEE
    mentor_primary_assignment_id: Optional[str]
    # wymagane gdy role=TRAINEE; absent gdy PRIMARY


@dataclass
class Deviation:
    deviation_id: str
    schedule_version_id: str
    category: DeviationCategory
    source_reference: str
    # SiteRule.rule_version_id lub built-in code
    affected_assignment_or_employee: str
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    reason: Optional[str]


if __name__ == "__main__":
    print(f"ShiftKind: {list(ShiftKind)}")
    print(f"AssignmentRole: {list(AssignmentRole)}")
    print(f"AssignmentState: {list(AssignmentState)}")
    print(f"AvailabilityKind: {list(AvailabilityKind)}")
    print(f"MembershipKind: {list(MembershipKind)}")
    print(f"ReadinessState: {list(ReadinessState)}")
    print(f"ReadinessSource: {list(ReadinessSource)}")
    print(f"RuleCategory: {list(RuleCategory)}")
    print(f"RuleEnforcement: {list(RuleEnforcement)}")
    print(f"RuleResolution: {list(RuleResolution)}")
    print(f"DeviationCategory: {list(DeviationCategory)}")
    print(f"ScheduleStatus: {list(ScheduleStatus)}")
    print(
        StandardShift(
            kind=ShiftKind.D,
            start_time=time(5, 0),
            end_time=time(17, 0),
            end_next_day=False,
            required_primary_count=1,
        )
    )
