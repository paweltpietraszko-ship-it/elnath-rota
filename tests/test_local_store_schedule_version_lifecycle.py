"""ROTA-T008 test matrix categories E (SNAPSHOT ROUND-TRIP), F (CURRENT
REFERENCE), G (FINAL IMMUTABILITY), H (WORKING EDIT), I (LINEAGE).
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Deviation,
    DeviationCategory,
    ScheduleStatus,
    ShiftDemand,
)
from rota.persistence import schedule_lifecycle as lc
from rota.persistence import schedule_repository as repo
from rota.persistence.db import connect
from rota.persistence.schedule_errors import (
    DuplicateScheduleVersionId,
    InvalidCurrentVersionTarget,
    InvalidScheduleLineage,
    NonEditableScheduleVersion,
)
from tests.support.t008_fixtures import seed_base_entities

MONTH = date(2026, 8, 1)


def _demand() -> ShiftDemand:
    return ShiftDemand("DEM-1", "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), 1)


def _assignment(state: AssignmentState = AssignmentState.PLANNED) -> Assignment:
    return Assignment(
        "ASG-1", "", "EMP-1", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.PRIMARY, state, False, "DEM-1", None,
    )


def _create_v1(conn: sqlite3.Connection, **overrides) -> ScheduleStatus:
    kwargs = dict(
        version_id="SV-1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    kwargs.update(overrides)
    return lc.create_schedule_version(conn, **kwargs)


# --- E. SCHEDULE SNAPSHOT ROUND-TRIP ----------------------------------------


def test_e_complete_version_reconstructs_exactly_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    deviation = Deviation("DEV-1", "", DeviationCategory.HOURS, "MANUAL", "EMP-1", False, None, None, "note")
    _create_v1(conn, deviations=[deviation])
    conn.close()

    reopened = connect(db_path)
    header = repo.get_schedule_version_header(reopened, "SV-1")
    snapshot = repo.get_schedule_snapshot(reopened, "SV-1")
    assert header.status == ScheduleStatus.WORKING_WITH_DEVIATIONS
    assert header.applied_rule_version_ids == []
    assert snapshot.shift_demands == [replace(_demand(), schedule_version_id="SV-1")]
    assert snapshot.assignments == [replace(_assignment(), schedule_version_id="SV-1")]
    assert snapshot.deviations == [replace(deviation, schedule_version_id="SV-1")]


# --- F. CURRENT REFERENCE ----------------------------------------------------


def test_f1_first_create_creates_exactly_one_current_reference(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "SV-1"


def test_f2_child_creation_atomically_switches_current(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "SV-2"


def test_f3_restore_switches_current_without_deleting_history(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    lc.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id="SV-1")
    assert repo.get_current_version_id(conn, "SITE-1", MONTH) == "SV-1"
    assert repo.get_schedule_version_header(conn, "SV-2") is not None  # SV-2 still exists


def test_f4_wrong_site_month_target_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    with pytest.raises(InvalidCurrentVersionTarget):
        lc.restore_schedule_version(conn, site_id="SITE-1", month=date(2026, 9, 1), version_id="SV-1")


def test_f5_current_reference_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    _create_v1(conn)
    conn.close()

    reopened = connect(db_path)
    assert repo.get_current_version_id(reopened, "SITE-1", MONTH) == "SV-1"


# --- G. FINAL IMMUTABILITY ---------------------------------------------------


def test_g1_finalize_no_deviations(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    result = lc.finalize_schedule_version(conn, version_id="SV-1")
    assert result.status == ScheduleStatus.FINAL_NO_DEVIATIONS


def test_g2_finalize_with_deviations_requires_acknowledgement(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    unacknowledged = Deviation("DEV-1", "", DeviationCategory.HOURS, "MANUAL", "EMP-1", False, None, None, None)
    _create_v1(conn, deviations=[unacknowledged])
    with pytest.raises(Exception):
        lc.finalize_schedule_version(conn, version_id="SV-1")

    acknowledged = Deviation(
        "DEV-1", "", DeviationCategory.HOURS, "MANUAL", "EMP-1", True, "COORD-1", datetime(2026, 8, 1, 9, 0), None,
    )
    lc.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[_demand()],
        assignments=[_assignment()], deviations=[acknowledged],
    )
    result = lc.finalize_schedule_version(conn, version_id="SV-1")
    assert result.status == ScheduleStatus.FINAL_WITH_DEVIATIONS


def test_g3_direct_header_mutation_after_final_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE schedule_versions SET created_by = 'COORD-1' WHERE version_id = 'SV-1'")
    with pytest.raises(NonEditableScheduleVersion):
        lc.replace_working_snapshot(
            conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[_demand()],
            assignments=[_assignment()], deviations=[],
        )


def test_g4_child_content_mutation_under_final_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE assignments SET frozen = 1 WHERE schedule_version_id = 'SV-1'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM assignments WHERE schedule_version_id = 'SV-1'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO shift_demands (schedule_version_id, demand_id, start_datetime, end_datetime, "
            "required_primary_count) VALUES ('SV-1', 'DEM-X', '2026-08-01T07:00:00', '2026-08-01T19:00:00', 1)"
        )


def test_g5_applied_rule_mutation_under_final_rejected(tmp_path: Path) -> None:
    from tests.support.t008_fixtures import seed_rule_decision

    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    decision = seed_rule_decision(conn)
    _create_v1(conn, applied_rule_version_ids=[decision.rule_version_id])
    lc.finalize_schedule_version(conn, version_id="SV-1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM schedule_version_applied_rules WHERE version_id = 'SV-1'")


def test_g6_physical_delete_of_final_or_history_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM schedule_versions WHERE version_id = 'SV-1'")


# --- H. WORKING EDIT ----------------------------------------------------------


def test_h1_current_working_aggregate_fully_replaceable_atomically(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    replaced = lc.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
    )
    assert repo.get_schedule_snapshot(conn, "SV-1").shift_demands == []
    assert replaced.status == ScheduleStatus.WORKING


def test_h2_immutable_header_fields_cannot_change_via_replace(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    header_before = _create_v1(conn)
    lc.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
    )
    header_after = repo.get_schedule_version_header(conn, "SV-1")
    assert header_after.site_id == header_before.site_id
    assert header_after.month == header_before.month
    assert header_after.created_at == header_before.created_at
    assert header_after.created_by == header_before.created_by


def test_h3_non_current_version_edit_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    with pytest.raises(NonEditableScheduleVersion):
        lc.replace_working_snapshot(
            conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
        )


def test_h4_failed_replace_leaves_original_snapshot_intact(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    bad_assignment = Assignment(
        "ASG-BAD", "", "NO-SUCH-EMPLOYEE", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-1", None,
    )
    with pytest.raises(Exception):
        lc.replace_working_snapshot(
            conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[_demand()],
            assignments=[bad_assignment], deviations=[],
        )
    snapshot = repo.get_schedule_snapshot(conn, "SV-1")
    assert snapshot.assignments == [replace(_assignment(), schedule_version_id="SV-1")]  # original, not a mixed/partial one


# --- I. LINEAGE ----------------------------------------------------------------


def test_i1_child_same_site_month_parent_accepted(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    child = lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 9, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    assert child.parent_version_id == "SV-1"


def test_i2_cross_site_cross_month_missing_self_parent_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)

    with pytest.raises(InvalidScheduleLineage):  # missing parent
        lc.create_schedule_version(
            conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="NO-SUCH-PARENT",
            created_at=datetime(2026, 9, 1, 8, 0), created_by="COORD-1",
            applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
        )

    with pytest.raises(InvalidScheduleLineage):  # self parent: a fresh id referencing itself
        lc.create_schedule_version(
            conn, version_id="SV-SELF", site_id="SITE-1", month=MONTH, parent_version_id="SV-SELF",
            created_at=datetime(2026, 9, 1, 8, 0), created_by="COORD-1",
            applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
        )

    with pytest.raises(InvalidScheduleLineage):  # cross-month parent
        lc.create_schedule_version(
            conn, version_id="SV-3", site_id="SITE-1", month=date(2026, 9, 1), parent_version_id="SV-1",
            created_at=datetime(2026, 9, 1, 8, 0), created_by="COORD-1",
            applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
        )


def test_i2b_duplicate_version_id_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    with pytest.raises(DuplicateScheduleVersionId):
        _create_v1(conn)


def test_i3_final_parent_not_mutated_when_child_created(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create_v1(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    parent_before = repo.get_schedule_snapshot(conn, "SV-1")
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 9, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[],
    )
    parent_after = repo.get_schedule_snapshot(conn, "SV-1")
    assert parent_before == parent_after
