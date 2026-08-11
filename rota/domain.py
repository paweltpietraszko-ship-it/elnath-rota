from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum

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
