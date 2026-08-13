"""ROTA-T008 R3-5 test-evidence gaps flagged by Codex round 3
(tasks/ROTA-T008/round_01/tests/tests_r3.txt): a dedicated negative case for
modifying (not omitting) a parent REALIZED Assignment field under R1-2, and
a full exclusion matrix for the holiday-history query
(PLANNED/CANCELLED/TRAINEE/non-current/non-holiday).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import Assignment, AssignmentRole, AssignmentState, CalendarDay, ScheduleStatus, ShiftDemand
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as repo
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.schedule_errors import RealizedWorkAltered
from tests.support.t008_fixtures import seed_base_entities

MONTH = date(2026, 8, 1)


def _demand(demand_id: str = "DEM-1") -> ShiftDemand:
    return ShiftDemand(demand_id, "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), 1)


def _realized(assignment_id: str = "ASG-1") -> Assignment:
    return Assignment(
        assignment_id, "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-1", None,
    )


def test_r1_2_rejects_modified_not_only_omitted_realized_field(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    lifecycle.create_schedule_version(
        conn, version_id="V1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_realized()], deviations=[],
    )
    altered = replace(_realized(), start_datetime=datetime(2026, 8, 1, 8, 0))  # same id, different field
    with pytest.raises(RealizedWorkAltered):
        lifecycle.create_schedule_version(
            conn, version_id="V2", site_id="SITE-1", month=MONTH, parent_version_id="V1",
            created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
            shift_demands=[_demand()], assignments=[altered], deviations=[],
        )


def _seed_holiday_matrix(conn) -> None:
    seed_base_entities(conn)
    save_calendar_day(conn, CalendarDay(date(2026, 8, 1), True))
    save_calendar_day(conn, CalendarDay(date(2026, 8, 2), False))  # non-holiday control day
    demands = [_demand("DEM-1"), _demand("DEM-NONHOL")]
    demands[1] = replace(demands[1], start_datetime=datetime(2026, 8, 2, 7, 0), end_datetime=datetime(2026, 8, 2, 19, 0))
    mentor = _realized("ASG-REALIZED")
    trainee = Assignment(
        "ASG-TRAINEE", "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, "ASG-REALIZED",
    )
    planned = replace(_realized("ASG-PLANNED"), state=AssignmentState.PLANNED)
    cancelled = replace(_realized("ASG-CANCELLED"), state=AssignmentState.CANCELLED)
    non_holiday = Assignment(
        "ASG-NONHOL", "", "EMP-1", datetime(2026, 8, 2, 7, 0), datetime(2026, 8, 2, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-NONHOL", None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="V1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=demands, assignments=[mentor, trainee, planned, cancelled, non_holiday], deviations=[],
    )


def test_holiday_history_exclusion_matrix(tmp_path: Path) -> None:
    """Only current REALIZED PRIMARY work on a stored holiday date qualifies
    -- PLANNED, CANCELLED, TRAINEE, and non-holiday-date work must all be
    excluded, and superseded (non-current) versions must not contribute."""
    conn = connect(tmp_path / "rota.db")
    _seed_holiday_matrix(conn)
    assert {a.assignment_id for a in repo.get_current_realized_primary_on_holidays(conn, "SITE-1")} == {"ASG-REALIZED"}

    # V2 preserves V1's content byte-for-byte (R1-2 requires every parent
    # REALIZED assignment to survive unchanged) -- used purely to prove that
    # once V2 is current and then V1 is restored, results reflect exactly
    # one current version's worth of holiday history, never a doubled or
    # stale count from the non-current one.
    v1_snapshot = repo.get_schedule_snapshot(conn, "V1")
    superseding = lifecycle.create_schedule_version(
        conn, version_id="V2", site_id="SITE-1", month=MONTH, parent_version_id="V1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=v1_snapshot.applied_rule_version_ids,
        shift_demands=v1_snapshot.shift_demands, assignments=v1_snapshot.assignments, deviations=[],
    )
    assert superseding.status == ScheduleStatus.WORKING
    assert {a.assignment_id for a in repo.get_current_realized_primary_on_holidays(conn, "SITE-1")} == {"ASG-REALIZED"}

    lifecycle.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id="V1")
    assert {a.assignment_id for a in repo.get_current_realized_primary_on_holidays(conn, "SITE-1")} == {"ASG-REALIZED"}
