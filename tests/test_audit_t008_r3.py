"""Independent adversarial audit for ROTA-T008 implementation 3f48633.

These tests exercise storage-boundary invariants through alternate SQL paths
and public read/write composition, rather than repeating repository happy paths.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Deviation,
    DeviationCategory,
    ShiftDemand,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as repository
from rota.persistence.db import connect
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.work_balance_repository import save_work_balance_target
from tests.support.t008_fixtures import seed_base_entities

MONTH = date(2026, 8, 1)


def _demand(demand_id: str = "DEM-1") -> ShiftDemand:
    return ShiftDemand(
        demand_id,
        "",
        datetime(2026, 8, 1, 7),
        datetime(2026, 8, 1, 19),
        1,
    )


def _primary(assignment_id: str = "ASG-1", demand_id: str = "DEM-1") -> Assignment:
    return Assignment(
        assignment_id,
        "",
        "EMP-1",
        datetime(2026, 8, 1, 7),
        datetime(2026, 8, 1, 19),
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        demand_id,
        None,
    )


def _create(
    conn: sqlite3.Connection,
    version_id: str,
    *,
    site_id: str = "SITE-1",
    month: date = MONTH,
    parent_version_id: str | None = None,
    demand_id: str = "DEM-1",
    assignment_id: str = "ASG-1",
    deviations: list[Deviation] | None = None,
) -> None:
    lifecycle.create_schedule_version(
        conn,
        version_id=version_id,
        site_id=site_id,
        month=month,
        parent_version_id=parent_version_id,
        created_at=datetime(2026, 8, 1, 8),
        created_by="COORD-1" if site_id == "SITE-1" else "COORD-2",
        applied_rule_version_ids=[],
        shift_demands=[_demand(demand_id)],
        assignments=[_primary(assignment_id, demand_id)],
        deviations=deviations or [],
    )


@pytest.mark.parametrize(
    "mutation_sql",
    [
        "UPDATE assignments SET schedule_version_id='SV-FINAL', assignment_id='ASG-MOVED' "
        "WHERE schedule_version_id='SV-WORK' AND assignment_id='ASG-WORK'",
        "UPDATE shift_demands SET schedule_version_id='SV-FINAL', demand_id='DEM-MOVED' "
        "WHERE schedule_version_id='SV-WORK' AND demand_id='DEM-1'",
        "UPDATE deviations SET schedule_version_id='SV-FINAL', deviation_id='DEV-MOVED' "
        "WHERE schedule_version_id='SV-WORK' AND deviation_id='DEV-WORK'",
        "UPDATE schedule_version_applied_rules SET version_id='SV-FINAL' "
        "WHERE version_id='SV-WORK' AND seq=0",
    ],
)
def test_final_child_guard_rejects_update_that_moves_working_row_into_final(tmp_path, mutation_sql: str) -> None:
    """Every FINAL child table must check UPDATE's destination as well as source."""
    from tests.support.t008_fixtures import seed_rule_decision

    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    decision = seed_rule_decision(conn)
    _create(conn, "SV-FINAL")
    lifecycle.finalize_schedule_version(conn, version_id="SV-FINAL")
    deviation = Deviation(
        "DEV-WORK", "", DeviationCategory.HOURS, "TARGET-01", "EMP-1", False, None, None, None
    )
    lifecycle.create_schedule_version(
        conn,
        version_id="SV-WORK",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id="SV-FINAL",
        created_at=datetime(2026, 8, 2, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[decision.rule_version_id],
        shift_demands=[_demand()],
        assignments=[_primary("ASG-WORK")],
        deviations=[deviation],
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(mutation_sql)


@pytest.mark.parametrize("bad_version_id", ["SV-OTHER-SITE", "SV-OTHER-MONTH"])
def test_current_reference_storage_rejects_version_from_other_site_or_month(tmp_path, bad_version_id: str) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    seed_base_entities(
        conn,
        site_id="SITE-2",
        profile_id="PROF-2",
        coordinator_id="COORD-2",
        employee_id="EMP-2",
    )
    _create(conn, "SV-1")
    _create(conn, "SV-OTHER-SITE", site_id="SITE-2", demand_id="DEM-2", assignment_id="ASG-2")
    lifecycle.create_schedule_version(
        conn,
        version_id="SV-OTHER-MONTH",
        site_id="SITE-1",
        month=date(2026, 9, 1),
        parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[],
        assignments=[],
        deviations=[],
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE current_schedule_versions SET version_id = ? WHERE site_id = ? AND month = ?",
            (bad_version_id, "SITE-1", MONTH.isoformat()),
        )


@pytest.mark.parametrize(
    ("role", "covers", "mentor"),
    [
        ("PRIMARY", "DEMAND-ONLY-IN-OTHER-VERSION", None),
        ("TRAINEE", None, "MENTOR-ONLY-IN-OTHER-VERSION"),
    ],
)
def test_assignment_storage_rejects_cross_version_references(
    tmp_path, role: str, covers: str | None, mentor: str | None
) -> None:
    """Another repository/raw SQL must not create cross-version demand/mentor links."""
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create(
        conn,
        "SV-SOURCE",
        demand_id="DEMAND-ONLY-IN-OTHER-VERSION",
        assignment_id="MENTOR-ONLY-IN-OTHER-VERSION",
    )
    _create(conn, "SV-TARGET", parent_version_id="SV-SOURCE", demand_id="DEM-TARGET", assignment_id="ASG-TARGET")

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO assignments "
            "(schedule_version_id, assignment_id, employee_id, start_datetime, end_datetime, "
            "role, state, frozen, covers_demand_id, mentor_primary_assignment_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "SV-TARGET",
                f"BAD-{role}",
                "EMP-1",
                "2026-08-02T07:00:00",
                "2026-08-02T19:00:00",
                role,
                "PLANNED",
                0,
                covers,
                mentor,
            ),
        )


def test_schedule_month_must_be_first_calendar_day(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    with pytest.raises(MalformedScheduleSnapshot):
        _create(conn, "SV-NONCANONICAL", month=date(2026, 8, 15))


def test_work_balance_target_month_must_be_first_calendar_day(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    with pytest.raises(ValueError):
        save_work_balance_target(conn, employee_id="EMP-1", month=date(2026, 8, 15), target_hours=160)


@pytest.mark.parametrize("category", list(DeviationCategory))
def test_deviation_category_round_trip_preserves_enum_type(tmp_path, category: DeviationCategory) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    deviation = Deviation(
        "DEV-1",
        "",
        category,
        "TARGET-01",
        "EMP-1",
        False,
        None,
        None,
        None,
    )
    _create(conn, "SV-1", deviations=[deviation])
    snapshot = repository.get_schedule_snapshot(conn, "SV-1")

    assert isinstance(snapshot.deviations[0].category, DeviationCategory)


def test_loaded_snapshot_can_be_reused_by_public_replace_operation(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    deviation = Deviation(
        "DEV-1",
        "",
        DeviationCategory.HOURS,
        "TARGET-01",
        "EMP-1",
        False,
        None,
        None,
        None,
    )
    _create(conn, "SV-1", deviations=[deviation])
    snapshot = repository.get_schedule_snapshot(conn, "SV-1")

    lifecycle.replace_working_snapshot(
        conn,
        version_id="SV-1",
        applied_rule_version_ids=snapshot.applied_rule_version_ids,
        shift_demands=snapshot.shift_demands,
        assignments=snapshot.assignments,
        deviations=snapshot.deviations,
    )
