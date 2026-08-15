"""Integrated T011 A-E operational audit requested by the owner.

The scenarios exercise a full calendar month rather than isolated API calls:
approved leave, sickness, day-shift-off requests with N still available, a
dated day-only N exception, FINAL persistence/restart, quarter reads, and an
intentional staffing wall.  State construction and verification use the
application layer; the benchmark module also writes lightweight SVG/CSV/JSON
evidence when run as a script.
"""
from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

from benchmarks.t011_pipeline_audit import (
    DAY_ONLY_EMPLOYEE,
    boundary_spec,
    coordinator_wall_spec,
    normal_spec,
    run_coordinator_wall_retry,
    run_exception_retry,
    run_scenario,
    write_artifacts,
)
from rota.domain import AssignmentRole, AssignmentState, AvailabilityKind


def _active_primary(outcome):
    return [
        assignment for assignment in outcome.assignments
        if assignment.role == AssignmentRole.PRIMARY and assignment.state != AssignmentState.CANCELLED
    ]


def _assert_full_month_coverage(outcome) -> None:
    assignments = _active_primary(outcome)
    assert len(assignments) == 62
    by_day_and_kind = {}
    for assignment in assignments:
        kind = "D" if assignment.start_datetime.hour == 6 else "N"
        key = (assignment.start_datetime.date(), kind)
        by_day_and_kind[key] = by_day_and_kind.get(key, 0) + 1
    assert set(by_day_and_kind.values()) == {1}
    assert len(by_day_and_kind) == 62


def _assignment_overlaps_record(assignment, record) -> bool:
    return assignment.start_datetime.date() <= record.end_date and assignment.end_datetime.date() >= record.start_date


def _assert_absence_and_day_off_contract(outcome) -> None:
    assignments = _active_primary(outcome)
    for record in outcome.availability:
        employee_assignments = [a for a in assignments if a.employee_id == record.employee_id]
        if record.kind in (AvailabilityKind.LEAVE_GRANTED, AvailabilityKind.SICK_LEAVE):
            assert not any(_assignment_overlaps_record(assignment, record) for assignment in employee_assignments)
        if record.kind == AvailabilityKind.DAY_SHIFT_OFF:
            assert not any(
                assignment.start_datetime.date() == record.start_date and assignment.start_datetime.hour == 6
                for assignment in employee_assignments
            )


def test_normal_month_with_leave_sickness_and_three_day_off_requests(tmp_path: Path) -> None:
    outcome = run_scenario(normal_spec(), tmp_path / "normal.db")
    assert outcome.status == "FEASIBLE"
    assert outcome.quarter_balance_warnings == ()
    _assert_full_month_coverage(outcome)
    _assert_absence_and_day_off_contract(outcome)
    assert not any(
        assignment.employee_id == DAY_ONLY_EMPLOYEE and assignment.start_datetime.hour == 18
        for assignment in _active_primary(outcome)
    )
    paths = write_artifacts(outcome, tmp_path / "artifacts")
    assert {path.suffix for path in paths} == {".json", ".csv", ".svg"}
    assert all(path.stat().st_size > 100 for path in paths)
    ElementTree.parse(next(path for path in paths if path.suffix == ".svg"))


def test_boundary_month_adds_seven_day_sickness_and_dated_n_exception(tmp_path: Path) -> None:
    spec = boundary_spec()
    outcome = run_scenario(spec, tmp_path / "boundary.db")
    assert outcome.status == "FEASIBLE"
    assert outcome.quarter_balance_warnings == ()
    _assert_full_month_coverage(outcome)
    _assert_absence_and_day_off_contract(outcome)
    exception_start, exception_end = spec.exception_window
    day_only_nights = [
        assignment for assignment in _active_primary(outcome)
        if assignment.employee_id == DAY_ONLY_EMPLOYEE and assignment.start_datetime.hour == 18
    ]
    assert day_only_nights
    assert all(exception_start <= assignment.start_datetime.date() <= exception_end for assignment in day_only_nights)
    assert not any(assignment.start_datetime.date() == exception_start - timedelta(days=1) for assignment in day_only_nights)
    assert not any(assignment.start_datetime.date() == exception_end + timedelta(days=1) for assignment in day_only_nights)
    paths = write_artifacts(outcome, tmp_path / "artifacts")
    assert {path.suffix for path in paths} == {".json", ".csv", ".svg"}


def test_coordinator_wall_overnight_boundary_needs_exception_one_day_earlier(tmp_path: Path) -> None:
    outcome = run_scenario(coordinator_wall_spec(), tmp_path / "wall.db")
    assert outcome.status == "DECISION_REQUIRED"
    assert outcome.assignments == ()
    # Sick leave begins on 14 October, but the N shift covering its first
    # hours starts on 13 October.  An exception effective only from the 14th
    # does not retroactively legalize that preceding N demand.
    assert "2026-10-13-N" in outcome.blocking_demand_ids
    assert {condition for _employee, condition in outcome.blockers} >= {
        "LEAVE_GRANTED-01", "SICK_LEAVE-01", "DAY_ONLY-01",
    }
    assert outcome.unblocking_options
    paths = write_artifacts(outcome, tmp_path / "artifacts")
    assert len(paths) == 1
    assert paths[0].suffix == ".json"


def test_coordinator_can_correct_exception_and_retry_same_working(tmp_path: Path) -> None:
    before, after = run_exception_retry(tmp_path / "exception-retry.db")
    assert before.status == "DECISION_REQUIRED"
    assert before.assignments == ()
    assert before.blocking_demand_ids == ("2026-10-13-N",)
    assert (DAY_ONLY_EMPLOYEE, "DAY_ONLY-01") in before.blockers

    assert after.status == "FEASIBLE"
    active = _active_primary(after)
    assert len(active) == 31
    assert {assignment.start_datetime.day for assignment in active} == set(range(1, 32))
    assert {assignment.start_datetime.hour for assignment in active} == {18}
    filip_nights = {
        assignment.start_datetime.date()
        for assignment in active
        if assignment.employee_id == DAY_ONLY_EMPLOYEE
    }
    assert filip_nights == {
        before.availability[0].start_date - timedelta(days=1),
        before.availability[0].start_date,
    }
    paths = write_artifacts(after, tmp_path / "artifacts")
    assert {path.suffix for path in paths} == {".json", ".csv", ".svg"}


def test_coordinator_wall_retry_recalculates_to_independent_rest_wall(tmp_path: Path) -> None:
    before, after = run_coordinator_wall_retry(tmp_path / "coordinator-wall-retry.db")
    assert before.status == "DECISION_REQUIRED"
    assert "2026-10-13-N" in before.blocking_demand_ids
    assert {condition for _employee, condition in before.blockers} >= {
        "LEAVE_GRANTED-01", "SICK_LEAVE-01", "DAY_ONLY-01",
    }

    assert after.status == "DECISION_REQUIRED"
    assert after.assignments == ()
    assert after.blocking_demand_ids
    assert {condition for _employee, condition in after.blockers} == {"REST-01"}
    assert {employee for employee, _condition in after.blockers} == {"ANNA", "BARTEK", DAY_ONLY_EMPLOYEE}
    assert all("DAY_ONLY-01" not in condition for _employee, condition in after.blockers)

    before_paths = write_artifacts(before, tmp_path / "artifacts")
    after_paths = write_artifacts(after, tmp_path / "artifacts")
    assert {path.suffix for path in before_paths + after_paths} == {".json"}


def test_audit_harness_does_not_import_persistence() -> None:
    paths = (Path(__file__), Path("benchmarks/t011_pipeline_audit.py"))
    offenders = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(alias.name for alias in node.names if alias.name.startswith("rota.persistence"))
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("rota.persistence"):
                offenders.append(node.module)
    assert offenders == []
