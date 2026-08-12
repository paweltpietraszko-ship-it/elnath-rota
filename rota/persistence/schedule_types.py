"""ScheduleVersion persistence DTO (tasks/ROTA-T008/brief.md SCHEDULEVERSION
-- PERSISTED AGGREGATE). Transport-only; no UI/application semantics.
"""
from __future__ import annotations

from dataclasses import dataclass

from rota.domain import Assignment, Deviation, ScheduleStatus, ShiftDemand


@dataclass(frozen=True)
class ScheduleSnapshot:
    status: ScheduleStatus
    applied_rule_version_ids: list[str]
    shift_demands: list[ShiftDemand]
    assignments: list[Assignment]
    deviations: list[Deviation]


if __name__ == "__main__":
    print("persistence.schedule_types module OK")
