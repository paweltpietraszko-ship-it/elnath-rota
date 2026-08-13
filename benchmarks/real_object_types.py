"""Data types for ROTA-REAL-OBJECT-01.

Benchmark types are test infrastructure only. Product semantics remain owned by
frozen Rota contracts; these types make benchmark inputs and evidence explicit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class OracleClass(str, Enum):
    KNOWN_FEASIBLE = "KNOWN_FEASIBLE"
    LOAD_DECISION_REQUIRED = "LOAD_DECISION_REQUIRED"
    EXTERNAL_SUPPORT_DECISION_REQUIRED = "EXTERNAL_SUPPORT_DECISION_REQUIRED"
    KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT = "KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT"
    PROVEN_STAFFING_SHORTAGE = "PROVEN_STAFFING_SHORTAGE"
    INCONCLUSIVE = "INCONCLUSIVE"


class SolveVerdict(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class BenchmarkInputError(ValueError):
    """Scenario fixture is illegal and must not be used to judge production."""


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
    declared_class: Optional[OracleClass] = None
    strict_monthly_hours: tuple[tuple[str, int], ...] = ()
    note: str = ""


@dataclass(frozen=True)
class LoadViolation:
    employee_id: str
    window_start: date
    window_end: date
    hours: int


@dataclass(frozen=True)
class ReferenceSolve:
    verdict: SolveVerdict
    witness: tuple[tuple[str, str], ...]
    elapsed_seconds: float
    status_name: str = ""
    timed_out: bool = False
    witness_checker_errors: tuple[str, ...] = ()
    load_violations: tuple[LoadViolation, ...] = ()


@dataclass(frozen=True)
class ReferenceClassification:
    expected_class: OracleClass
    capped: ReferenceSolve
    uncapped: Optional[ReferenceSolve] = None
    without_external: Optional[ReferenceSolve] = None
    with_external_probe: Optional[ReferenceSolve] = None
    with_external_probe_uncapped: Optional[ReferenceSolve] = None


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
