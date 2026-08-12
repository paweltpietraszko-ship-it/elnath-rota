"""ROTA-T008 test matrix categories M (CURRENT-ONLY OPERATIONAL QUERIES), N
(WORKBALANCE).
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from rota.balance import MissingTargetHoursError
from rota.domain import Assignment, AssignmentRole, AssignmentState, CalendarDay, Employee, ShiftDemand
from rota.persistence import schedule_lifecycle as lc
from rota.persistence import schedule_repository as repo
from rota.persistence import work_balance_repository as wb
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.persistence.site_repository import save_site
from rota.domain import Site
from tests.support.t008_fixtures import make_profile, seed_base_entities
from rota.persistence.site_profile_repository import save_site_profile

MONTH = date(2026, 8, 1)


def _demand(demand_id: str = "DEM-1") -> ShiftDemand:
    return ShiftDemand(demand_id, "", datetime(2026, 8, 1, 7, 0), datetime(2026, 8, 1, 19, 0), 1)


def _assignment(
    assignment_id: str = "ASG-1", employee_id: str = "EMP-1", state: AssignmentState = AssignmentState.REALIZED,
    start: datetime = datetime(2026, 8, 1, 7, 0), end: datetime = datetime(2026, 8, 1, 19, 0), covers: str = "DEM-1",
) -> Assignment:
    return Assignment(assignment_id, "", employee_id, start, end, AssignmentRole.PRIMARY, state, False, covers, None)


def _create(conn, **overrides):
    kwargs = dict(
        version_id="SV-1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    kwargs.update(overrides)
    return lc.create_schedule_version(conn, **kwargs)


def _seed_second_site(conn) -> None:
    save_site_profile(conn, make_profile("PROF-2"))
    save_site(conn, Site("SITE-2", "PROF-2", "Site Two", True))


# --- M. CURRENT-ONLY OPERATIONAL QUERIES -------------------------------------


def test_m1_boundary_context_uses_current_versions_only(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_assignment(assignment_id="ASG-2")], deviations=[],
    )
    found = repo.get_current_assignments_in_interval(
        conn, "SITE-1", datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 2, 0, 0),
    )
    assert [a.assignment_id for a in found] == ["ASG-2"]  # not SV-1's ASG-1


def test_m2_cross_site_employee_assignments_use_current_versions_only(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _seed_second_site(conn)
    save_employee(conn, Employee("EMP-1", "Emp One", date(2026, 1, 1), None, False))
    lc.create_schedule_version(
        conn, version_id="SV-A", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_assignment()], deviations=[],
    )
    lc.create_schedule_version(
        conn, version_id="SV-B", site_id="SITE-2", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand("DEM-2")],
        assignments=[_assignment("ASG-2", start=datetime(2026, 8, 1, 20, 0), end=datetime(2026, 8, 2, 7, 0), covers="DEM-2")],
        deviations=[],
    )
    found = repo.get_current_assignments_for_employees(
        conn, ["EMP-1"], datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 3, 0, 0),
    )
    assert {a.assignment_id for a in found} == {"ASG-1", "ASG-2"}
    excluded_site1 = repo.get_current_assignments_for_employees(
        conn, ["EMP-1"], datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 3, 0, 0), exclude_site_id="SITE-1",
    )
    assert {a.assignment_id for a in excluded_site1} == {"ASG-2"}


def test_m3_holiday_history_uses_current_versions_and_stored_calendar_day(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    save_calendar_day(conn, CalendarDay(date(2026, 8, 1), True))
    _create(conn)
    holidays = repo.get_current_realized_primary_on_holidays(conn, "SITE-1")
    assert [a.assignment_id for a in holidays] == ["ASG-1"]


def test_m4_cancelled_excluded_from_current_only_queries(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    cancelled = _assignment(state=AssignmentState.CANCELLED)
    _create(conn, assignments=[cancelled])
    found = repo.get_current_assignments_in_interval(
        conn, "SITE-1", datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 2, 0, 0),
    )
    assert found == []


def test_m5_restore_changes_query_results_immediately(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create(conn)
    lc.finalize_schedule_version(conn, version_id="SV-1")
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_assignment(assignment_id="ASG-2")], deviations=[],
    )
    lc.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id="SV-1")
    found = repo.get_current_assignments_in_interval(
        conn, "SITE-1", datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 2, 0, 0),
    )
    assert [a.assignment_id for a in found] == ["ASG-1"]


# --- N. WORKBALANCE -----------------------------------------------------------


def test_n1_target_hours_persist_and_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    seed_base_entities(conn)
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    conn.close()
    reopened = connect(db_path)
    assert wb.get_work_balance_target(reopened, "EMP-1", MONTH) == 160


def test_n2_missing_target_is_not_guessed_as_zero(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _create(conn)
    with pytest.raises(MissingTargetHoursError):
        wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)


def test_n3_planned_and_realized_derive_from_current_versions_only(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    _create(conn, assignments=[_assignment(state=AssignmentState.REALIZED)])
    lc.finalize_schedule_version(conn, version_id="SV-1")
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_assignment(state=AssignmentState.REALIZED)], deviations=[],
    )
    balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert balance.realized_hours == 12  # not double-counted across SV-1 + SV-2


def test_n4_historical_versions_not_double_counted(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    _create(conn, assignments=[_assignment(state=AssignmentState.PLANNED)])
    lc.finalize_schedule_version(conn, version_id="SV-1")
    for i in range(3):
        lc.create_schedule_version(
            conn, version_id=f"SV-{i + 2}", site_id="SITE-1", month=MONTH, parent_version_id=f"SV-{i + 1}",
            created_at=datetime(2026, 8, i + 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
            shift_demands=[_demand()], assignments=[_assignment(state=AssignmentState.PLANNED)], deviations=[],
        )
    balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert balance.planned_hours == 12


def test_n5_cross_site_current_assignments_for_same_employee_included(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    _seed_second_site(conn)
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    lc.create_schedule_version(
        conn, version_id="SV-A", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand()], assignments=[_assignment(state=AssignmentState.REALIZED)], deviations=[],
    )
    lc.create_schedule_version(
        conn, version_id="SV-B", site_id="SITE-2", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[_demand("DEM-2")],
        assignments=[_assignment(
            "ASG-2", state=AssignmentState.REALIZED,
            start=datetime(2026, 8, 2, 7, 0), end=datetime(2026, 8, 2, 19, 0), covers="DEM-2",
        )],
        deviations=[],
    )
    balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert balance.realized_hours == 24  # 12h from each Site


def test_n6_restore_changes_reconstructed_balance_without_writing_derived_hours(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    wb.save_work_balance_target(conn, employee_id="EMP-1", month=MONTH, target_hours=160)
    _create(conn, assignments=[_assignment(state=AssignmentState.REALIZED)])
    lc.finalize_schedule_version(conn, version_id="SV-1")
    lc.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[], assignments=[], deviations=[],
    )
    empty_balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert empty_balance.realized_hours == 0

    lc.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id="SV-1")
    restored_balance = wb.reconstruct_month_balance(conn, employee_id="EMP-1", month=MONTH)
    assert restored_balance.realized_hours == 12
