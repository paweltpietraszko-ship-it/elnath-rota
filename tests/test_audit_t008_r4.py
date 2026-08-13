"""Independent completion of the mandatory R1-2/R1-4 evidence matrix.

ROTA-T008 clarification requires representative changes of every preserved
REALIZED field and a non-current holiday row that cannot be hidden by set
deduplication. The implementation is expected to pass; these tests verify the
bug classes that the supplied single-field/duplicate-id tests do not cover.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import Assignment, AssignmentRole, AssignmentState, CalendarDay, Employee, ShiftDemand
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as repository
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.persistence.schedule_errors import RealizedWorkAltered, ScheduleVersionNotFound
from tests.support.t008_fixtures import seed_base_entities

MONTH = date(2026, 8, 1)


def _demand(demand_id: str, day: int = 1) -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "",
        datetime(2026, 8, day, 7),
        datetime(2026, 8, day, 19),
        1,
    )


def _primary(assignment_id: str, demand_id: str, state: AssignmentState = AssignmentState.REALIZED) -> Assignment:
    return Assignment(
        assignment_id,
        "",
        "EMP-1",
        datetime(2026, 8, 1, 7),
        datetime(2026, 8, 1, 19),
        AssignmentRole.PRIMARY,
        state,
        False,
        demand_id,
        None,
    )


def _trainee(mentor_id: str) -> Assignment:
    return Assignment(
        "TRAINEE",
        "",
        "EMP-1",
        datetime(2026, 8, 1, 7),
        datetime(2026, 8, 1, 19),
        AssignmentRole.TRAINEE,
        AssignmentState.REALIZED,
        False,
        None,
        mentor_id,
    )


def _seed_realized_parent(conn) -> tuple[list[ShiftDemand], list[Assignment]]:
    save_employee(conn, Employee("EMP-2", "Employee 2", date(2026, 1, 1), None, False))
    demands = [_demand("DEM-1"), _demand("DEM-2"), _demand("DEM-3")]
    assignments = [
        _primary("ASG-1", "DEM-1"),
        _primary("MENTOR-1", "DEM-2"),
        _primary("MENTOR-2", "DEM-3"),
        _trainee("MENTOR-1"),
    ]
    lifecycle.create_schedule_version(
        conn,
        version_id="V1",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=demands,
        assignments=assignments,
        deviations=[],
    )
    return demands, assignments


def _mutate_realized(assignments: list[Assignment], mutation: str) -> list[Assignment]:
    updated = list(assignments)
    target_index = 3 if mutation == "mentor_reference" else 0
    target = updated[target_index]
    changes = {
        "employee": {"employee_id": "EMP-2"},
        "start": {"start_datetime": datetime(2026, 8, 1, 8)},
        "end": {"end_datetime": datetime(2026, 8, 1, 18)},
        "planned": {"state": AssignmentState.PLANNED},
        "cancelled": {"state": AssignmentState.CANCELLED},
        "frozen": {"frozen": True},
        "demand_reference": {"covers_demand_id": "DEM-2"},
        "role": {
            "role": AssignmentRole.TRAINEE,
            "covers_demand_id": None,
            "mentor_primary_assignment_id": "MENTOR-1",
        },
        "mentor_reference": {"mentor_primary_assignment_id": "MENTOR-2"},
    }
    updated[target_index] = replace(target, **changes[mutation])
    return updated


@pytest.mark.parametrize(
    "mutation",
    ["employee", "start", "end", "planned", "cancelled", "frozen", "demand_reference", "role", "mentor_reference"],
)
def test_every_realized_field_change_is_rejected_atomically(tmp_path: Path, mutation: str) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    demands, assignments = _seed_realized_parent(conn)
    parent_before = repository.get_schedule_snapshot(conn, "V1")

    with pytest.raises(RealizedWorkAltered):
        lifecycle.create_schedule_version(
            conn,
            version_id="V2",
            site_id="SITE-1",
            month=MONTH,
            parent_version_id="V1",
            created_at=datetime(2026, 8, 2, 8),
            created_by="COORD-1",
            applied_rule_version_ids=[],
            shift_demands=demands,
            assignments=_mutate_realized(assignments, mutation),
            deviations=[],
        )

    with pytest.raises(ScheduleVersionNotFound):
        repository.get_schedule_version_header(conn, "V2")
    assert repository.get_current_version_id(conn, "SITE-1", MONTH) == "V1"
    assert repository.get_schedule_snapshot(conn, "V1") == parent_before


def test_parent_planned_assignment_may_become_realized_in_child(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    demand = _demand("DEM-1")
    planned = _primary("ASG-1", "DEM-1", AssignmentState.PLANNED)
    lifecycle.create_schedule_version(
        conn,
        version_id="V1",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[demand],
        assignments=[planned],
        deviations=[],
    )

    lifecycle.create_schedule_version(
        conn,
        version_id="V2",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id="V1",
        created_at=datetime(2026, 8, 2, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[demand],
        assignments=[replace(planned, state=AssignmentState.REALIZED)],
        deviations=[],
    )

    assert repository.get_schedule_snapshot(conn, "V2").assignments[0].state == AssignmentState.REALIZED


def test_noncurrent_holiday_assignment_with_distinct_id_is_excluded(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    save_calendar_day(conn, CalendarDay(date(2026, 8, 1), True))
    old_demand = _demand("DEM-OLD")
    current_demand = _demand("DEM-CURRENT")
    lifecycle.create_schedule_version(
        conn,
        version_id="V-OLD",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[old_demand],
        assignments=[_primary("ASG-OLD", "DEM-OLD")],
        deviations=[],
    )
    lifecycle.create_schedule_version(
        conn,
        version_id="V-CURRENT",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 8, 2, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[current_demand],
        assignments=[_primary("ASG-CURRENT", "DEM-CURRENT")],
        deviations=[],
    )

    result = repository.get_current_realized_primary_on_holidays(conn, "SITE-1")
    assert [assignment.assignment_id for assignment in result] == ["ASG-CURRENT"]
