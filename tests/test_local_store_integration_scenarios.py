"""ROTA-T008 REQUIRED INTEGRATION SCENARIO (VERSION / RESTART / RESTORE),
REQUIRED CRASH-CONSISTENCY SCENARIO, and test matrix category O (CRASH
CONSISTENCY, O1/O2; O3 lives in tests/test_local_store_schema_migration.py
as test_a5).
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Deviation,
    DeviationCategory,
    Employee,
    ScheduleStatus,
    ShiftDemand,
    SiteMembership,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as repo
from rota.persistence import work_balance_repository as wb
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from tests.support.t008_fixtures import seed_base_entities, seed_rule_decision

MONTH = date(2026, 8, 1)


def _demand_daytime() -> ShiftDemand:
    return ShiftDemand("DEM-DAY", "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), 1)


def _demand_overnight_cross_month() -> ShiftDemand:
    return ShiftDemand("DEM-NIGHT", "", datetime(2026, 8, 31, 19, 0), datetime(2026, 9, 1, 7, 0), 1)


def _realized_assignment() -> Assignment:
    return Assignment(
        "ASG-REALIZED", "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-DAY", None,
    )


def _planned_future_assignment(employee_id: str = "EMP-1") -> Assignment:
    return Assignment(
        "ASG-FUTURE", "", employee_id, datetime(2026, 8, 31, 19, 0), datetime(2026, 9, 1, 7, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-NIGHT", None,
    )


def _demand_split_target() -> ShiftDemand:
    return ShiftDemand("DEM-SPLIT", "", datetime(2026, 8, 2, 7, 0), datetime(2026, 8, 2, 19, 0), 1)


def _manual_split_assignment() -> Assignment:
    """Delta 3 (clarification): R1-1 truthful manual split/partial-coverage
    -- the PRIMARY interval is intentionally shorter than its covered
    ShiftDemand's interval. Storage must accept this without requiring
    interval equality. Also lands on the second holiday day (2026-08-02),
    but PLANNED not REALIZED -- feeds delta 5's REALIZED-vs-PLANNED check."""
    return Assignment(
        "ASG-SPLIT", "", "EMP-1", datetime(2026, 8, 2, 7, 0), datetime(2026, 8, 2, 13, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-SPLIT", None,
    )


def _seed_master_data_and_rule(conn) -> str:
    """Steps 1-3: SiteProfile/Site/Coordinator/Employee/membership/CalendarDay
    facts + WorkBalance target_hours + a real T005 rule. Returns rule_version_id."""
    seed_base_entities(conn)
    save_employee(conn, Employee("EMP-2", "Emp Two", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(
        "EMP-1", "SITE-1", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
    ))
    save_calendar_day(conn, CalendarDay(date(2026, 8, 1), True))
    save_calendar_day(conn, CalendarDay(date(2026, 8, 2), True))
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    return seed_rule_decision(conn, rule_id="RULE-1", site_id="SITE-1").rule_version_id


def _create_and_finalize_v1(conn, rule_version_id: str):
    """Steps 4-5: WORKING V1 with complete ShiftDemands, an overnight
    cross-month Assignment, a real applied rule, no Deviations -- then
    finalize it."""
    v1 = lifecycle.create_schedule_version(
        conn, version_id="V1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[rule_version_id],
        shift_demands=[_demand_daytime(), _demand_overnight_cross_month()],
        assignments=[_realized_assignment(), _planned_future_assignment()], deviations=[],
    )
    assert v1.status == ScheduleStatus.WORKING
    v1 = lifecycle.finalize_schedule_version(conn, version_id="V1")
    assert v1.status == ScheduleStatus.FINAL_NO_DEVIATIONS


def _create_v2_child(conn, rule_version_id: str):
    """Step 6: complete WORKING child V2 (parent=V1), materially changing
    the future PLANNED Assignment (different employee) while preserving the
    REALIZED one byte-for-byte (R1-2). Also carries delta 3's manual split
    (ASG-SPLIT / DEM-SPLIT)."""
    v2 = lifecycle.create_schedule_version(
        conn, version_id="V2", site_id="SITE-1", month=MONTH, parent_version_id="V1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[rule_version_id],
        shift_demands=[_demand_daytime(), _demand_overnight_cross_month(), _demand_split_target()],
        assignments=[
            _realized_assignment(), _planned_future_assignment(employee_id="EMP-2"), _manual_split_assignment(),
        ],
        deviations=[],
    )
    assert v2.status == ScheduleStatus.WORKING


def _seed_predecessor_month_context(conn, rule_version_id: str) -> None:
    """Delta 4: a separate CURRENT ScheduleVersion for the month before the
    target month, REALIZED in its trailing six days -- proves the boundary
    query is a genuine [start, end) interval query across ScheduleVersion.month
    boundaries, not limited to overlap with the target month."""
    demands = [
        ShiftDemand(f"DEM-JUL-{day}", "", datetime(2026, 7, day, 7, 0), datetime(2026, 7, day, 19, 0), 1)
        for day in range(26, 32)
    ]
    assignments = [
        Assignment(
            f"ASG-JUL-{day}", "", "EMP-1", datetime(2026, 7, day, 7, 0), datetime(2026, 7, day, 19, 0),
            AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, f"DEM-JUL-{day}", None,
        )
        for day in range(26, 32)
    ]
    v0 = lifecycle.create_schedule_version(
        conn, version_id="V0-JULY", site_id="SITE-1", month=date(2026, 7, 1), parent_version_id=None,
        created_at=datetime(2026, 7, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[rule_version_id], shift_demands=demands, assignments=assignments, deviations=[],
    )
    assert v0.status == ScheduleStatus.WORKING


def _exercise_deviation_status_transition(conn) -> None:
    """Delta 6: a working-snapshot replacement moving Deviation count from
    zero to non-zero, and back, must move ScheduleStatus in lockstep. Ends
    back at zero Deviations so V2's snapshot is unchanged for later
    equality assertions."""
    snapshot = repo.get_schedule_snapshot(conn, "V2")
    deviation = Deviation("DEV-V2-1", "", DeviationCategory.HOURS, "MANUAL", "EMP-2", False, None, None, None)
    with_deviation = lifecycle.replace_working_snapshot(
        conn, version_id="V2", applied_rule_version_ids=snapshot.applied_rule_version_ids,
        shift_demands=snapshot.shift_demands, assignments=snapshot.assignments, deviations=[deviation],
    )
    assert with_deviation.status == ScheduleStatus.WORKING_WITH_DEVIATIONS
    back_to_zero = lifecycle.replace_working_snapshot(
        conn, version_id="V2", applied_rule_version_ids=snapshot.applied_rule_version_ids,
        shift_demands=snapshot.shift_demands, assignments=snapshot.assignments, deviations=[],
    )
    assert back_to_zero.status == ScheduleStatus.WORKING


def _assert_deltas_3_and_5(conn) -> None:
    """Delta 3: manual split truthfully stored -- ASG-SPLIT's interval must
    not equal its covered demand's interval. Delta 5: holiday history
    distinguishes current REALIZED PRIMARY (ASG-REALIZED) from current
    PLANNED work on the same/other holiday day (ASG-SPLIT)."""
    snapshot = repo.get_schedule_snapshot(conn, "V2")
    split = next(a for a in snapshot.assignments if a.assignment_id == "ASG-SPLIT")
    demand = next(d for d in snapshot.shift_demands if d.demand_id == "DEM-SPLIT")
    assert (split.start_datetime, split.end_datetime) != (demand.start_datetime, demand.end_datetime)

    holidays = repo.get_current_realized_primary_on_holidays(conn, "SITE-1")
    assert {a.assignment_id for a in holidays} == {"ASG-REALIZED"}


def _assert_delta_4_predecessor_context(conn) -> None:
    """Delta 4: [7/26, 8/1) does not overlap the target month at all, yet
    must still return the predecessor ScheduleVersion's REALIZED work."""
    context = repo.get_current_assignments_in_interval(
        conn, "SITE-1", datetime(2026, 7, 26, 0, 0), datetime(2026, 8, 1, 0, 0),
    )
    assert {a.assignment_id for a in context} == {f"ASG-JUL-{d}" for d in range(26, 32)}


def test_version_restart_restore_integration_scenario(tmp_path: Path, monkeypatch) -> None:
    # ROTA-T057 follow-up (2026-09-07): restore_schedule_version now refuses
    # a live month -- this test is about restore's own persistence
    # mechanics (pointer move, reconstruction across restart, history),
    # not about live-protection, so liveness is neutralized here.
    monkeypatch.setattr(lifecycle, "is_schedule_version_live", lambda conn, version_id, now: False)
    db_path = tmp_path / "rota.db"

    conn = connect(db_path)
    rule_version_id = _seed_master_data_and_rule(conn)
    _seed_predecessor_month_context(conn, rule_version_id)
    _create_and_finalize_v1(conn, rule_version_id)
    v1_snapshot_before_child = repo.get_schedule_snapshot(conn, "V1")
    _create_v2_child(conn, rule_version_id)
    _assert_deltas_3_and_5(conn)
    _assert_delta_4_predecessor_context(conn)

    # 7: V2 is current; V1 is unchanged/immutable.
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "V2"
    assert repo.get_schedule_snapshot(conn, "V1") == v1_snapshot_before_child

    # 8: close and reopen.
    conn.close()
    conn = connect(db_path)

    # 9: V2 reconstructs exactly; current points to V2.
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "V2"
    reconstructed_v2 = repo.get_schedule_snapshot(conn, "V2")
    assert {a.assignment_id: a.employee_id for a in reconstructed_v2.assignments} == {
        "ASG-REALIZED": "EMP-1", "ASG-FUTURE": "EMP-2", "ASG-SPLIT": "EMP-1",
    }

    # Delta 6: WORKING <-> WORKING_WITH_DEVIATIONS transition on V2 while it
    # is still current, before restoring V1 below.
    _exercise_deviation_status_transition(conn)

    conn = _restore_v1_and_verify_history_and_queries(conn, db_path, reconstructed_v2)


def _restore_v1_and_verify_history_and_queries(conn, db_path: Path, reconstructed_v2):
    # 10: restore V1 as current.
    lifecycle.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id="V1")

    # 11: V2 still exists, unchanged, in history.
    assert repo.get_schedule_snapshot(conn, "V2") == reconstructed_v2
    all_versions = {v.version_id for v in repo.list_schedule_versions(conn, "SITE-1", MONTH)}
    assert all_versions == {"V1", "V2"}

    # 12: current-only queries now reflect V1, not V2, without any manual
    # rewrite of derived balance rows.
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "V1"
    boundary = repo.get_current_assignments_in_interval(
        conn, "SITE-1", datetime(2026, 8, 31, 0, 0), datetime(2026, 9, 2, 0, 0),
    )
    assert {a.assignment_id: a.employee_id for a in boundary} == {"ASG-FUTURE": "EMP-1"}  # V1's original, not V2's EMP-2
    balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert balance.realized_hours == 12  # only V1's ASG-REALIZED, reconstructed fresh -- no stored second truth

    # 13: close/reopen again, restored current reference persists.
    conn.close()
    conn = connect(db_path)
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "V1"
    return conn


def _seed_v1(conn) -> None:
    seed_base_entities(conn)
    lifecycle.create_schedule_version(
        conn, version_id="V1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand_daytime()], assignments=[_realized_assignment()], deviations=[],
    )


def test_o1_failed_create_leaves_no_partial_version_and_old_current_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_v1(conn)

    def _failing_insert_content(*args, **kwargs):
        conn.execute(
            "INSERT INTO shift_demands (schedule_version_id, demand_id, start_datetime, end_datetime, "
            "required_primary_count) VALUES ('V2', 'DEM-PARTIAL', '2026-08-01T07:00:00', '2026-08-01T19:00:00', 1)"
        )
        raise RuntimeError("simulated crash mid multi-row schedule creation")

    monkeypatch.setattr(lifecycle, "_insert_content", _failing_insert_content)
    with pytest.raises(RuntimeError):
        lifecycle.create_schedule_version(
            conn, version_id="V2", site_id="SITE-1", month=MONTH, parent_version_id="V1",
            created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
            shift_demands=[_demand_daytime()], assignments=[_realized_assignment()], deviations=[],
        )
    conn.close()

    reopened = connect(db_path)
    assert reopened.execute("SELECT 1 FROM schedule_versions WHERE version_id = 'V2'").fetchone() is None
    assert reopened.execute("SELECT 1 FROM shift_demands WHERE schedule_version_id = 'V2'").fetchone() is None
    assert repo.get_current_version_id(reopened, "SITE-1", MONTH) == "V1"


def test_o2_failed_working_replacement_leaves_one_complete_snapshot_never_mixed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_v1(conn)
    original_snapshot = repo.get_schedule_snapshot(conn, "V1")

    def _failing_insert_content(*args, **kwargs):
        conn.execute(
            "INSERT INTO shift_demands (schedule_version_id, demand_id, start_datetime, end_datetime, "
            "required_primary_count) VALUES ('V1', 'DEM-PARTIAL', '2026-08-01T07:00:00', '2026-08-01T19:00:00', 1)"
        )
        raise RuntimeError("simulated crash mid working-snapshot replacement")

    monkeypatch.setattr(lifecycle, "_insert_content", _failing_insert_content)
    with pytest.raises(RuntimeError):
        lifecycle.replace_working_snapshot(
            conn, version_id="V1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
        )
    conn.close()

    reopened = connect(db_path)
    assert repo.get_schedule_snapshot(reopened, "V1") == original_snapshot  # original whole, not mixed with partial new
