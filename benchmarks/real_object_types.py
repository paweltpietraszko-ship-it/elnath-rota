"""Data types for the architect-owned real-object benchmark.

This package is test infrastructure.  It deliberately does not define product
semantics; it encodes already-frozen Rota facts into reproducible benchmark
cases that can be checked independently of the production solver.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class OracleClass(str, Enum):
    """Independent expected class for one benchmark case."""

    KNOWN_FEASIBLE = "KNOWN_FEASIBLE"
    LOAD_DECISION_REQUIRED = "LOAD_DECISION_REQUIRED"
    EXTERNAL_SUPPORT_DECISION_REQUIRED = "EXTERNAL_SUPPORT_DECISION_REQUIRED"
    KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT = "KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT"
    PROVEN_STAFFING_SHORTAGE = "PROVEN_STAFFING_SHORTAGE"
    INCONCLUSIVE = "INCONCLUSIVE"


class SolveVerdict(str, Enum):
    """Reference solve result; UNKNOWN is never evidence of correctness."""

    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DemandSpec:
    """One required PRIMARY shift."""

    demand_id: str
    kind: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class AvailabilitySpec:
    """One active benchmark availability fact."""

    employee_id: str
    kind: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class RuleSpec:
    """One RESOLVED+HARD SiteRule from the T007 executable catalog."""

    rule_version_id: str
    rule_kind: str
    employee_id: str
    shift_kinds: tuple[str, ...] = ()
    weekdays: tuple[int, ...] = ()


@dataclass(frozen=True)
class ExternalWindowSpec:
    """One explicit coordinator-confirmed external support window."""

    window_id: str
    employee_id: str
    start: datetime
    end: datetime
    allowed_shift_kind: Optional[str] = None
    active: bool = True
    site_id: str = "real-object"


@dataclass(frozen=True)
class FixedAssignmentSpec:
    """Assignment that is already a fixed fact before production plan()."""

    assignment_id: str
    employee_id: str
    start: datetime
    end: datetime
    state: str = "REALIZED"
    frozen: bool = True
    demand_id: Optional[str] = None


@dataclass(frozen=True)
class ScenarioSpec:
    """Complete deterministic input recipe for one Site/month benchmark case."""

    case_id: str
    month: date
    availability: tuple[AvailabilitySpec, ...] = ()
    site_rules: tuple[RuleSpec, ...] = ()
    boundary_assignments: tuple[FixedAssignmentSpec, ...] = ()
    fixed_demand_assignments: tuple[FixedAssignmentSpec, ...] = ()
    external_windows: tuple[ExternalWindowSpec, ...] = ()
    external_probe_windows: tuple[ExternalWindowSpec, ...] = ()
    external_support_enabled: bool = False
    declared_class: Optional[OracleClass] = None
    strict_monthly_hours: tuple[tuple[str, int], ...] = ()
    note: str = ""


@dataclass(frozen=True)
class ReferenceSolve:
    """One independent CP-SAT existence check."""

    verdict: SolveVerdict
    witness: tuple[tuple[str, str], ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class ReferenceClassification:
    """Independent case classification before production code is evaluated."""

    expected_class: OracleClass
    capped: ReferenceSolve
    uncapped: Optional[ReferenceSolve] = None
    without_external: Optional[ReferenceSolve] = None
    with_external_probe: Optional[ReferenceSolve] = None


@dataclass(frozen=True)
class CheckResult:
    """Independent checker result for one production candidate."""

    errors: tuple[str, ...]
    monthly_hours: tuple[tuple[str, int], ...]
    max_rolling_7d_hours: tuple[tuple[str, int], ...]

    @property
    def hard_pass(self) -> bool:
        """Return True when the candidate has no independent HARD error."""
        return not self.errors


if __name__ == "__main__":
    print("real_object_types OK")
