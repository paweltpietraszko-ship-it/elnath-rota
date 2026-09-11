"""ROTA-T009 required test matrix items 10, 11, 12, and
review_01/review_02_architect_clarification.md's focused tests."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.application import manual_edit
from rota.application.deviation_mapping import materialize_deviations
from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftDemand
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.planning.validator import validate
from tests.support.minimal_state import base_state
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _demand(start_hour: int = 5, end_hour: int = 17) -> ShiftDemand:
    return ShiftDemand("2026-08-01-D", "v1", datetime(2026, 8, 1, start_hour), datetime(2026, 8, 1, end_hour), 1)


def _assignment(assignment_id: str, employee: str, start_hour: int, end_hour: int, end_day: int = 1) -> Assignment:
    return Assignment(
        assignment_id, "v1", employee, datetime(2026, 8, 1, start_hour), datetime(2026, 8, end_day, end_hour),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "2026-08-01-D", None,
    )


# --- R1 clarification focused tests 1-4: interval-geometric COVERAGE-01 ----


def test_r1_1_split_coverage_is_complete() -> None:
    demand = _demand()
    p = _assignment("P", "P", 5, 13)
    b = _assignment("B", "B", 13, 17)
    state = base_state(shift_demands=[demand])
    report = validate(state, [p, b])
    assert not any(v.rule == "COVERAGE-01" for v in report.violation_details)


def test_r1_2_partial_coverage_reports_exact_gap() -> None:
    demand = _demand()
    p = _assignment("P", "P", 5, 13)
    state = base_state(shift_demands=[demand])
    report = validate(state, [p])
    coverage = [v for v in report.violation_details if v.rule == "COVERAGE-01"]
    assert len(coverage) == 1
    assert coverage[0].demand_ids == ("2026-08-01-D",)
    assert "13:00:00-2026-08-01 17:00:00" in coverage[0].message


def test_r1_3_excess_coverage_reported() -> None:
    demand = _demand()
    a = _assignment("A", "A", 5, 17)
    b = _assignment("B", "B", 5, 17)
    state = base_state(shift_demands=[demand])
    report = validate(state, [a, b])
    coverage = [v for v in report.violation_details if v.rule == "COVERAGE-01"]
    assert len(coverage) == 1
    assert "excess" in coverage[0].message


def test_r1_4_cross_demand_contribution_not_double_counted() -> None:
    d_demand = _demand(5, 17)
    n_demand = ShiftDemand("2026-08-01-N", "v1", datetime(2026, 8, 1, 17), datetime(2026, 8, 2, 5), 1)
    p = _assignment("P", "P", 5, 13)
    b = Assignment("B", "v1", "B", datetime(2026, 8, 1, 13), datetime(2026, 8, 2, 5), AssignmentRole.PRIMARY,
                   AssignmentState.REALIZED, False, "2026-08-01-N", None)
    state = base_state(shift_demands=[d_demand, n_demand])
    report = validate(state, [p, b])
    assert not any(v.rule == "COVERAGE-01" for v in report.violation_details)
    assert report.monthly_hours["B"] == 16  # 13:00-05:00 counted once, not split into two fake periods


# --- R1 focused test 8: coverage-gap Deviation targets the ShiftDemand -----


def test_r1_8_coverage_gap_deviation_targets_demand_not_invented_employee() -> None:
    demand = _demand()
    p = _assignment("P", "P", 5, 13)
    state = base_state(shift_demands=[demand])
    report = validate(state, [p])
    deviations = materialize_deviations(report.violation_details, ())
    coverage_devs = [d for d in deviations if d.category.value == "COVERAGE"]
    assert len(coverage_devs) == 1
    assert coverage_devs[0].affected_assignment_or_employee == "2026-08-01-D"


# --- Application-layer atomic manual correction (items 10-12, R1-5/6/7, R2) -


def _plan_and_select(conn, site_id: str):
    from rota.application import plan_ops
    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")


def test_10_manual_coverage_gap_stored_and_validates_no_implicit_replan(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="edit-1", month=MONTH, seed=300)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    shrunk = Assignment(
        target.assignment_id, "", target.employee_id, target.start_datetime,
        target.start_datetime.replace(hour=13), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False,
        target.covers_demand_id, None,
    )
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        upsert_assignments=[shrunk],
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    coverage_devs = [d for d in v2_snapshot.deviations if d.category.value == "COVERAGE"]
    assert len(coverage_devs) == 1
    assert coverage_devs[0].affected_assignment_or_employee == "2026-08-01-D"
    assert v2.version_id != v1.version_id  # no implicit REPLAN: exactly one child, not a full re-solve
    assert len(v2_snapshot.assignments) == len(get_schedule_snapshot(conn, v1.version_id).assignments)


def test_11_manual_split_coverage_storable_and_validates(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="edit-2", month=MONTH, seed=301)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    other = next(e.employee_id for e in pstate.employees if e.employee_id != target.employee_id)
    shrunk = Assignment(target.assignment_id, "", target.employee_id, target.start_datetime,
                         target.start_datetime.replace(hour=13), AssignmentRole.PRIMARY, AssignmentState.PLANNED,
                         False, target.covers_demand_id, None)
    fill = Assignment("ASG-FILL", "", other, target.start_datetime.replace(hour=13), target.end_datetime,
                       AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, target.covers_demand_id, None)
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        upsert_assignments=[shrunk, fill],
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    coverage_devs = [d for d in v2_snapshot.deviations if d.category.value == "COVERAGE"]
    assert coverage_devs == []


def test_12_freeze_affects_later_replan(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="edit-3", month=MONTH, seed=302)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-05-D")

    v2 = manual_edit.freeze_or_unfreeze(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
        assignment_id=target.assignment_id, frozen=True,
    )
    from rota.application import plan_ops
    replanned = plan_ops.replan(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 3))
    assert replanned.status == "FEASIBLE"
    frozen_still_there = next(a for a in replanned.candidates[0] if a.assignment_id == target.assignment_id)
    assert frozen_still_there.employee_id == target.employee_id  # T006: frozen is untouched by REPLAN
    assert get_schedule_snapshot(conn, v2.version_id).assignments  # sanity: v2 itself persisted correctly


# --- R1 focused tests 5-7: child creation + effective_from provenance ------


def test_r1_5_6_7_child_creation_and_effective_from_provenance(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="edit-4", month=MONTH, seed=303)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    v1_snapshot_before = get_schedule_snapshot(conn, v1.version_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    edited = Assignment(target.assignment_id, "", target.employee_id, target.start_datetime,
                         target.start_datetime.replace(hour=13), AssignmentRole.PRIMARY, AssignmentState.PLANNED,
                         False, target.covers_demand_id, None)

    # ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT: the client is no longer the
    # owner of effective_from at all -- any caller-supplied value is now
    # ignored (ROTA-T009's own review_01 clarification for R1-6 pinned the
    # opposite; OWNER_CORRECTED 2026-09-11 supersedes it). The backend
    # always computes it itself as today's date (this Assignment is still
    # in the future relative to conftest's frozen manual_edit._now()).
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
        upsert_assignments=[edited],
    )
    # R1-5: one child, parent unchanged/readable, child becomes current.
    assert v2.version_id != v1.version_id
    assert v2.parent_version_id == v1.version_id
    assert get_schedule_snapshot(conn, v1.version_id) == v1_snapshot_before
    assert get_current_version_id(conn, site_id, MONTH) == v2.version_id
    # R1-6 (superseded): automatic created_at + backend-computed effective_from.
    assert v2.created_at is not None
    assert v2.effective_from == manual_edit._now().date()

    # R1-7: a second correction still creates another child, not a history
    # rewrite -- both get the same backend-computed effective_from since
    # this Task never varies "today" within one test/process.
    snapshot2 = get_schedule_snapshot(conn, v2.version_id)
    target2 = next(a for a in snapshot2.assignments if a.assignment_id == target.assignment_id)
    v3 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
        upsert_assignments=[target2],
    )
    assert v3.version_id != v2.version_id
    assert v3.effective_from == manual_edit._now().date()
    assert get_schedule_snapshot(conn, v2.version_id).assignments == snapshot2.assignments  # v2 untouched


# --- R2 focused test: atomicity of the manual correction flow -------------


def test_r2_failed_validation_preparation_leaves_no_partial_child(tmp_path, monkeypatch) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="edit-5", month=MONTH, seed=304)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure before ScheduleVersion creation")

    monkeypatch.setattr("rota.application.manual_edit.materialize_deviations", _boom)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    edited = Assignment(target.assignment_id, "", target.employee_id, target.start_datetime,
                         target.start_datetime.replace(hour=13), AssignmentRole.PRIMARY, AssignmentState.PLANNED,
                         False, target.covers_demand_id, None)
    with pytest.raises(RuntimeError):
        manual_edit.apply_manual_correction(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2),
            upsert_assignments=[edited],
        )
    versions_after = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    assert versions_after == versions_before  # no partial child
    assert get_current_version_id(conn, site_id, MONTH) == v1.version_id  # current unchanged
