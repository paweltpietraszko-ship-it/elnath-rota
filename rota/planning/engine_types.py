from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional

from rota.domain import Assignment


@dataclass
class BlockingDemand:
    demand_id: str
    start_datetime: datetime
    end_datetime: datetime


@dataclass
class Blocker:
    employee_id: str
    condition: str


@dataclass
class LoadBlocker:
    employee_id: str
    window_start: date
    window_end: date
    hours: int


@dataclass
class DecisionRequiredPayload:
    blocking_shift_demands: list[BlockingDemand]
    blockers: list[Blocker]
    load_blocker: Optional[LoadBlocker]
    unblocking_options: list[str]


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str]


@dataclass
class PlanningResult:
    status: Literal["FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR", "NO_ALTERNATIVE"]
    candidates: list[list[Assignment]]
    decision_payload: Optional[DecisionRequiredPayload]
    error_message: Optional[str]
    warnings: list[str]


if __name__ == "__main__":
    print("engine types OK")
