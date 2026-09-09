"""Independent semantic reproducer for T58-06 on product SHA 1f072fa."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from rota.application import manual_edit, memory_read, plan_ops
from rota.domain import Assignment, AssignmentRole, AssignmentState, DeviationCategory, ShiftDemand
from rota.persistence import schedule_lifecycle
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.site_memory_types import CoordinatorActionKind
from tests.test_t019b import COORD, MONTH, SITE, _bootstrap, _employee, _fill_calendar


class _August10(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 10, 12, 0)
        return value if tz is None else value.replace(tzinfo=tz)


def _demand(day: int) -> ShiftDemand:
    return ShiftDemand(
        f"D-{day}", "V0", datetime(2026, 8, day, 6), datetime(2026, 8, day, 18), 1,
    )


def _assignment(day: int, employee_id: str) -> Assignment:
    return Assignment(
        f"A-{day}", "V0", employee_id,
        datetime(2026, 8, day, 6), datetime(2026, 8, day, 18),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, f"D-{day}", None,
    )


def test_przelicz_plan_preserves_recorded_future_manual_decision(monkeypatch):
    """T58-06: a later automatic recompute must not undo a recorded manual decision."""
    conn = connect(":memory:")
    _bootstrap(conn)
    _employee(conn, "E1")
    _employee(conn, "E2")
    _fill_calendar(conn)

    demands = [_demand(day) for day in (1, 20, 21, 22)]
    assignments = [
        _assignment(1, "E2"),
        replace(_assignment(20, "E1"), frozen=True),
        replace(_assignment(21, "E1"), frozen=True),
        _assignment(22, "E2"),
    ]
    schedule_lifecycle.create_schedule_version(
        conn,
        version_id="V0",
        site_id=SITE,
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 7, 25, 12),
        created_by=COORD,
        applied_rule_version_ids=[],
        shift_demands=demands,
        assignments=assignments,
        deviations=[],
        effective_from=MONTH,
    )

    # The coordinator deliberately makes 20-22 August a three-day sequence.
    manual = manual_edit.apply_manual_correction(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=date(2026, 8, 9),
        upsert_assignments=[replace(assignments[-1], employee_id="E1")],
        note="świadoma decyzja koordynatora",
    )
    manual_snapshot = get_schedule_snapshot(conn, manual.version_id)
    assert any(
        deviation.category == DeviationCategory.LAW
        and deviation.source_reference == "THIRD-CONSECUTIVE-SHIFT-01"
        for deviation in manual_snapshot.deviations
    )
    assert any(
        action.action_kind == CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION
        and action.schedule_version_id == manual.version_id
        for action in memory_read.material_action_history(conn)
    )

    # On 10 August the schedule is live, but the recorded decision concerns
    # future duties. A protective Przelicz Plan must keep that decision.
    monkeypatch.setattr(plan_ops, "datetime", _August10)
    result = plan_ops.plan_month(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=date(2026, 8, 10),
    )
    assert result.status == "FEASIBLE"
    expected = {"D-22": "E1"}
    for candidate in result.candidates:
        actual = {
            assignment.covers_demand_id: assignment.employee_id
            for assignment in candidate
            if assignment.covers_demand_id in expected
        }
        assert actual == expected
