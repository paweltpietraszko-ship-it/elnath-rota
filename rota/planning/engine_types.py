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
class UnblockingOption:
    """ROTA-T062: one coordinator-facing suggestion -- text plus a STABLE
    navigation target (or none, for pure information). Replaces the old
    bare-string list that frontend/src/screens/Decisions.tsx used to parse
    by matching Polish text prefixes; text may change freely now without
    touching navigation.

    target is one of the existing product places T062 is allowed to point
    at ("obsada", "obiekt") or None (information only, no button).
    requires_existing_schedule marks an option that only makes sense once a
    current ScheduleVersion exists (e.g. a manual-correction-style
    suggestion) -- ROTA-T061 is retired, so the application layer (plan_ops)
    must drop these when there is no current version yet."""
    text: str
    target: Optional[Literal["obsada", "obiekt"]] = None
    requires_existing_schedule: bool = False


@dataclass
class DecisionRequiredPayload:
    blocking_shift_demands: list[BlockingDemand]
    blockers: list[Blocker]
    load_blocker: Optional[LoadBlocker]
    unblocking_options: list[UnblockingOption]


@dataclass
class ValidationResult:
    passed: bool
    violations: list[str]


@dataclass
class PlanningResult:
    status: Literal[
        "FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR", "NO_ALTERNATIVE",
        "NARROW_SEARCH_EXHAUSTED", "SEARCH_INCOMPLETE",
        # ROTA-T058 (OWNER_CORRECTED 2026-09-08, brief section 7): a
        # genuinely non-decision result -- the automatic max-two-consecutive-
        # PRIMARY-shifts HARD blocked every legal candidate, but there is
        # nothing for the coordinator to decide (no automatic exception,
        # no override); deliberately NOT DECISION_REQUIRED.
        "THIRD_CONSECUTIVE_SHIFT_BLOCKED",
    ]
    candidates: list[list[Assignment]]
    decision_payload: Optional[DecisionRequiredPayload]
    error_message: Optional[str]
    warnings: list[str]
    # ROTA-T032 section 6.4: False only when the shared planning budget
    # (section 6, PLANNING_OPERATION_BUDGET_SECONDS) ran out before every required solver phase proved OPTIMAL --
    # the candidate is still HARD-valid (independent validator PASS). True
    # keeps every pre-T032 caller/constructor valid unchanged (T32-T8).
    optimization_complete: bool = True


if __name__ == "__main__":
    print("engine types OK")
