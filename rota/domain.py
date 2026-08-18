from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Optional, TypedDict, Union

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


# ROTA-T012: a SiteProfile catalog entry's length category, orthogonal to
# ShiftKind (D/N) -- no ShiftKind.H24 is added; a 24h occurrence is always
# two chained 12h D/N StandardShift components of the same PRIMARY
# (arch/spec.md T012 amendment, owner mandate 2026-08-18).
class ShiftCatalogKind(str, Enum):
    H24 = "24h"
    H12 = "12h"
    OTHER = "INNY"


# --- Value objects ---


@dataclass(frozen=True)
class StandardShift:
    kind: ShiftKind
    start_time: time
    end_time: time
    end_next_day: bool
    required_primary_count: int
    # ROTA-T012: appended, compatibility-defaulted fields -- catalog_kind=None
    # means "legacy row, normalize from actual duration" (see
    # rota.planning.shift_catalog.normalized_catalog_kind); required_rest_hours=11
    # is only the legacy-compatible default (REST_MIN_HOURS), never a
    # program-enforced legal minimum; active_weekdays defaults to every day.
    catalog_kind: Optional["ShiftCatalogKind"] = None
    required_rest_hours: int = 11
    active_weekdays: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)


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
    # ROTA-T012: per-(employee, site) qualification for 24h occurrences on a
    # mixed 12h/24h profile, default=True. Ignored on an all-24h profile.
    # Does not disable membership.enabled, DAY_ONLY, Availability, SiteRule,
    # EXTERNAL or any other existing HARD gate.
    can_work_24h: bool = True


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


class EmployeeAllowedShiftKindsParams(TypedDict):
    """ROTA-T007 rule_kind=EMPLOYEE_ALLOWED_SHIFT_KINDS."""

    employee_id: str
    allowed_shift_kinds: list[str]  # non-empty, values in {"D", "N"}


class EmployeeAllowedWeekdaysParams(TypedDict):
    """ROTA-T007 rule_kind=EMPLOYEE_ALLOWED_WEEKDAYS."""

    employee_id: str
    allowed_weekdays: list[int]  # non-empty, ISO weekdays 1..7


class EmployeeForbiddenShiftKindsOnWeekdaysParams(TypedDict):
    """ROTA-T007 rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS."""

    employee_id: str
    weekdays: list[int]  # non-empty, ISO weekdays 1..7
    forbidden_shift_kinds: list[str]  # non-empty, values in {"D", "N"}


class EmployeeDayOnlyNExceptionParams(TypedDict):
    """ROTA-T010-B rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION
    (arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md): a single named,
    narrow exception to DAY_ONLY-01 for one employee -- never a general HARD
    override. Must be category=CONFIRMED_EXCEPTION, enforcement=HARD,
    resolution_status=RESOLVED."""

    employee_id: str


# CONTRACT_GAP narrowed by ROTA-T007 (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md)
# to exactly the three initial executable rule_kind parameter shapes below,
# extended by ROTA-T010-B (arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md)
# with the one narrow EMPLOYEE_DAY_ONLY_N_EXCEPTION shape.
# Persistence (rota/persistence/site_rule_repository.py) stores whatever is
# JSON-compatible and does not require it to match one of these shapes --
# execution-time validation (rota/planning/site_rules.py) is what enforces
# the shape, only for RESOLVED+HARD rules.
RuleParameters = Union[
    EmployeeAllowedShiftKindsParams,
    EmployeeAllowedWeekdaysParams,
    EmployeeForbiddenShiftKindsOnWeekdaysParams,
    EmployeeDayOnlyNExceptionParams,
]


@dataclass
class SiteRuleVersion:
    rule_version_id: str
    rule_id: str
    site_id: str
    category: RuleCategory
    rule_kind: Optional[str]
    structured_parameters: Optional["RuleParameters"]
    # rule_kind catalog: initial 3-kind catalog frozen by ROTA-T007
    # (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md); only future catalog
    # extension beyond those three kinds remains CONTRACT_GAP
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
    # ROTA-T009 review_01: coordinator-facing "Obowiazuje od". System
    # created_at remains automatic provenance; effective_from is always
    # coordinator-supplied for a new version and never derived. None only
    # for legacy pre-T009 rows, where it is genuinely unknown.
    effective_from: Optional[date] = None


@dataclass
class ShiftDemand:
    demand_id: str
    schedule_version_id: str
    start_datetime: datetime
    end_datetime: datetime
    required_primary_count: int
    # ROTA-T012: appended provenance fields, all None for legacy demands
    # (classify_demand() remains the legacy fallback). T012-generated
    # demands always set shift_kind explicitly -- current SiteProfile is
    # never used to reconstruct historical REST from an old demand.
    shift_kind: Optional["ShiftKind"] = None
    catalog_kind: Optional["ShiftCatalogKind"] = None
    required_rest_hours: Optional[int] = None
    # Shared by both components of one 24h occurrence (normal or same-month
    # emergency-extended); a plain 12h/INNY demand gets its own unique id.
    work_period_template_id: Optional[str] = None
    work_period_component: Optional[int] = None
    # Snapshotted only when exactly one matching 24h capability exists for
    # this demand's (kind, start time-of-day) -- see
    # rota.planning.shift_catalog. None means no emergency 24h rescue is
    # possible for this demand.
    emergency_24h_rest_hours: Optional[int] = None


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
    # ROTA-T010-D: jedyna dozwolona wartosc to "NN" -- oznacza wczesniej
    # PLANNED PRIMARY, ktorego pracownik nie wykonal (state=CANCELLED w
    # tym samym Assignment). Domyslnie None dla kazdego innego Assignment.
    operational_code: Optional[str] = None
    # ROTA-T012: appended work-period/rest provenance. Identity for REST-01
    # purposes is (employee_id, work_period_id); a legacy Assignment with no
    # work_period_id is its own standalone period. required_rest_after_hours
    # is the rest owed after THIS work period ends (legacy None means 11h,
    # the REST_MIN_HOURS compatibility fallback).
    work_period_id: Optional[str] = None
    required_rest_after_hours: Optional[int] = None


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
