"""ROTA-T042 Checkpoint C (tasks/ROTA-T042/brief.md section 4): the single
owner for the four fields every DecisionRequiredPayload renders as JSON.
api/routers/schedule.py and api/routers/decisions.py used to define
BlockingDemandOut/BlockerOut/LoadBlockerOut and the field-by-field mapping
independently (AUDIT-4 pair 9, tasks/ROTA-AUDIT4/round_01/tests/tests_r1.txt).
Each router still returns its own distinct top-level response shape
(schedule.py's DecisionRequiredPayloadOut, imported straight from here, vs.
decisions.py's flat DecisionRequiredOut with its own extra metadata fields)."""
from __future__ import annotations

from pydantic import BaseModel


class BlockingDemandOut(BaseModel):
    demand_id: str
    start_datetime: str
    end_datetime: str


class BlockerOut(BaseModel):
    employee_id: str
    condition: str


class LoadBlockerOut(BaseModel):
    employee_id: str
    window_start: str
    window_end: str
    hours: int


class UnblockingOptionOut(BaseModel):
    """ROTA-T062: text plus a stable navigation target (or None, information
    only) -- replaces the old bare string the frontend used to parse by
    matching Polish text prefixes."""
    text: str
    target: str | None = None


class DecisionRequiredPayloadOut(BaseModel):
    blocking_shift_demands: list[BlockingDemandOut]
    blockers: list[BlockerOut]
    load_blocker: LoadBlockerOut | None
    unblocking_options: list[UnblockingOptionOut]


def decision_payload_out(dp) -> DecisionRequiredPayloadOut:
    return DecisionRequiredPayloadOut(
        blocking_shift_demands=[
            BlockingDemandOut(
                demand_id=b.demand_id, start_datetime=b.start_datetime.isoformat(), end_datetime=b.end_datetime.isoformat(),
            )
            for b in dp.blocking_shift_demands
        ],
        blockers=[BlockerOut(employee_id=b.employee_id, condition=b.condition) for b in dp.blockers],
        load_blocker=LoadBlockerOut(
            employee_id=dp.load_blocker.employee_id, window_start=dp.load_blocker.window_start.isoformat(),
            window_end=dp.load_blocker.window_end.isoformat(), hours=dp.load_blocker.hours,
        ) if dp.load_blocker else None,
        unblocking_options=[UnblockingOptionOut(text=o.text, target=o.target) for o in dp.unblocking_options],
    )
