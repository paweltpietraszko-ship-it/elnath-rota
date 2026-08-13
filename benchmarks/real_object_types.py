"""Small data model for ROTA-REAL-OBJECT-01 benchmark."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class ExpectedStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    DECISION_REQUIRED = "DECISION_REQUIRED"


class ExpectationKind(str, Enum):
    FEASIBLE = "FEASIBLE"
    SIMPLE_SHORTAGE = "SIMPLE_SHORTAGE"
    REST_PAIR_SHORTAGE = "REST_PAIR_SHORTAGE"
    EXTERNAL_BEFORE = "EXTERNAL_BEFORE"
    EXTERNAL_AFTER = "EXTERNAL_AFTER"
    FORCED_LOAD = "FORCED_LOAD"
    FIXED_LOAD = "FIXED_LOAD"
    REPLAN = "REPLAN"


class BenchmarkVerdict(str, Enum):
    PRODUCTION_PASS = "PRODUCTION_PASS"
    PRODUCTION_MISMATCH = "PRODUCTION_MISMATCH"
    BENCHMARK_INVALID = "BENCHMARK_INVALID"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class DemandSpec:
    demand_id: str
    kind: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class AvailabilitySpec:
    employee_id: str
    kind: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class RuleSpec:
    rule_version_id: str
    rule_kind: str
    employee_id: str
    shift_kinds: tuple[str, ...] = ()
    weekdays: tuple[int, ...] = ()


@dataclass(frozen=True)
class ExternalWindowSpec:
    window_id: str
    employee_id: str
    start: datetime
    end: datetime
    allowed_shift_kind: Optional[str] = None
    active: bool = True
    site_id: str = "real-object"


@dataclass(frozen=True)
class FixedAssignmentSpec:
    assignment_id: str
    employee_id: str
    start: datetime
    end: datetime
    state: str = "REALIZED"
    frozen: bool = True
    demand_id: Optional[str] = None


@dataclass(frozen=True)
class ScenarioSpec:
    case_id: str
    month: date
    seed: int = 0
    ladder_steps: tuple[int, ...] = ()
    perturbations: tuple[str, ...] = ()
    series_id: str = ""
    series_level: int = 0
    availability: tuple[AvailabilitySpec, ...] = ()
    site_rules: tuple[RuleSpec, ...] = ()
    boundary_assignments: tuple[FixedAssignmentSpec, ...] = ()
    other_site_assignments: tuple[FixedAssignmentSpec, ...] = ()
    fixed_demand_assignments: tuple[FixedAssignmentSpec, ...] = ()
    external_windows: tuple[ExternalWindowSpec, ...] = ()
    external_probe_windows: tuple[ExternalWindowSpec, ...] = ()
    external_support_enabled: bool = False
    strict_monthly_hours: tuple[tuple[str, int], ...] = ()
    expected_status: Optional[ExpectedStatus] = None
    expectation_kind: Optional[ExpectationKind] = None
    expectation_reason: str = ""
    expected_demand_ids: tuple[str, ...] = ()
    expected_employee_id: Optional[str] = None
    expected_reshuffles: Optional[int] = None
    note: str = ""


@dataclass(frozen=True)
class LoadViolation:
    employee_id: str
    window_start: date
    window_end: date
    hours: int


@dataclass(frozen=True)
class CheckResult:
    errors: tuple[str, ...]
    monthly_hours: tuple[tuple[str, int], ...]
    max_rolling_7d_hours: tuple[tuple[str, int], ...]
    load_violations: tuple[LoadViolation, ...] = ()

    @property
    def hard_pass(self) -> bool:
        return not self.errors


if __name__ == "__main__":
    print("real_object_types OK")
