"""ROTA-T009 required test matrix items 3, 7, 8, 9."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.application import plan_ops
from rota.application.assembler import assemble_planning_state
from rota.application.errors import CandidateRejected
from rota.domain import Assignment, AssignmentRole, AssignmentState, ExternalSupportWindow, ShiftDemand, ShiftKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header
from rota.planning.validator import validate
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_and_select(conn, site_id: str, month: date = MONTH):
    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id="COORD-1", effective_from=month)
    assert result.status == "FEASIBLE"
    version = plan_ops.select_candidate(conn, site_id=site_id, month=month, candidate=result.candidates[0], coordinator_id="COORD-1")
    return result, version


def test_3_first_plan_creates_full_profile_version_and_uses_remembered_rules(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="plan-1", month=MONTH, seed=200)
    site_id = pstate.site.site_id

    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    version_id = get_current_version_id(conn, site_id, MONTH)
    header = get_schedule_version_header(conn, version_id)
    snapshot = get_schedule_snapshot(conn, version_id)
    assert header.status.value == "WORKING"
    assert len(snapshot.assignments) == 0  # PLAN doesn't invent/persist assignments, only demands
    demand_kinds = {d.demand_id.rsplit("-", 1)[1] for d in snapshot.shift_demands}
    assert demand_kinds == {"D", "N"}


def test_7_feasible_candidate_not_persisted_until_selected_and_invalid_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="plan-2", month=MONTH, seed=201)
    site_id = pstate.site.site_id

    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    version_id = get_current_version_id(conn, site_id, MONTH)
    assert len(get_schedule_snapshot(conn, version_id).assignments) == 0  # not auto-saved

    # HARD-invalid but structurally storable: drop one assignment entirely,
    # leaving its ShiftDemand with zero PRIMARY coverage (COVERAGE-01).
    broken_candidate = list(result.candidates[0])[1:]
    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=broken_candidate, coordinator_id="COORD-1")
    assert len(get_schedule_snapshot(conn, version_id).assignments) == 0  # rejection didn't persist anything

    plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")
    assert len(get_schedule_snapshot(conn, version_id).assignments) == len(result.candidates[0])


def test_8_decision_required_then_external_window_then_replan_uses_window(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="plan-3", month=date(2027, 5, 1), seed=202)
    site_id = pstate.site.site_id
    month = date(2027, 5, 1)

    from rota.application.durable_inputs import append_availability, add_external_support_window
    from rota.domain import AvailabilityKind

    # Block N for everyone except C (DAY_ONLY, so C still cannot cover N
    # either) -- matches the real-object benchmark's own proven
    # external-before/after-confirmation shape: D stays coverable by C,
    # only N genuinely has no local eligible worker.
    blocked_employees = [e.employee_id for e in pstate.employees if e.employee_id not in ("X", "Y", "C")]
    day = date(2027, 5, 12)
    for employee_id in blocked_employees:
        append_availability(
            conn, coordinator_id="COORD-1", site_id=site_id, availability_id=f"AV-{employee_id}-{day}",
            employee_id=employee_id, kind=AvailabilityKind.DAY_SHIFT_OFF, start_date=day, end_date=day, active=True,
        )

    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id="COORD-1", effective_from=month)
    assert result.status == "DECISION_REQUIRED"

    window = ExternalSupportWindow(
        "WIN-X-12MAY", "X", site_id, datetime(2027, 5, 12, 17, 0), datetime(2027, 5, 13, 5, 0), True, ShiftKind.N,
    )
    add_external_support_window(conn, coordinator_id="COORD-1", site_id=site_id, window=window)

    replanned = plan_ops.replan(conn, site_id=site_id, month=month, coordinator_id="COORD-1", effective_from=date(2027, 5, 2))
    assert replanned.status == "FEASIBLE"
    covering = next(a for a in replanned.candidates[0] if a.covers_demand_id == f"{day}-N")
    assert covering.employee_id == "X"


def test_9_replan_creates_child_and_preserves_parent_history_and_frozen(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="plan-4", month=MONTH, seed=203)
    site_id = pstate.site.site_id

    _, v1 = _plan_and_select(conn, site_id)
    v1_snapshot_before = get_schedule_snapshot(conn, v1.version_id)

    replanned = plan_ops.replan(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2))
    assert replanned.status == "FEASIBLE"
    v2 = plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=replanned.candidates[0], coordinator_id="COORD-1")

    assert v2.version_id != v1.version_id
    assert v2.parent_version_id == v1.version_id
    assert get_schedule_snapshot(conn, v1.version_id) == v1_snapshot_before  # parent untouched
    assert get_current_version_id(conn, site_id, MONTH) == v2.version_id


# ROTA-T043 Checkpoint C (brief.md section 6.2 "nakładających się demandów"):
# tests/test_t041_checkpoint_a.py's a07-a13 exercise COVERAGE-01's overlap
# disambiguation only against a hand-built PlanningState (UNIT_OR_ADAPTER per
# brief 6.1 -- no real assemble_planning_state read). This is the smallest
# real pion for the same class: a real Site/roster/calendar (seed_real_object)
# and two custom, genuinely overlapping ShiftDemands written through the real
# persistence path (schedule_lifecycle.create_schedule_version, same idiom
# tests/test_t010_nn.py uses), then assemble_planning_state (real assembler
# read) + validate (real validator) -- no hand-built PlanningState anywhere.
def test_43c_two_legal_overlapping_demands_via_real_assembler_and_validator(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="overlap-real", month=MONTH, seed=210)
    site_id = pstate.site.site_id
    e1, e2 = pstate.memberships[0].employee_id, pstate.memberships[1].employee_id

    d1 = ShiftDemand("OVL-1", "", datetime(2026, 8, 5, 18, 0), datetime(2026, 8, 6, 6, 0), 1, shift_kind=ShiftKind.N)
    d2 = ShiftDemand("OVL-2", "", datetime(2026, 8, 5, 22, 0), datetime(2026, 8, 6, 10, 0), 1, shift_kind=ShiftKind.N)
    lifecycle.create_schedule_version(
        conn, version_id="SV-OVL-1", site_id=site_id, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[d1, d2], assignments=[], deviations=[],
        effective_from=date(2026, 8, 1),
    )
    state, _ = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    d1_real = next(d for d in state.shift_demands if d.demand_id == "OVL-1")
    d2_real = next(d for d in state.shift_demands if d.demand_id == "OVL-2")

    a1 = Assignment("A1", state.schedule_version_id, e1, d1_real.start_datetime, d1_real.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d1_real.demand_id, None)
    a2 = Assignment("A2", state.schedule_version_id, e2, d2_real.start_datetime, d2_real.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d2_real.demand_id, None)
    report_both = validate(state, [a1, a2])
    assert report_both.hard_pass, report_both.violations

    report_one_missing = validate(state, [a1])
    assert not report_one_missing.hard_pass
    assert any("COVERAGE-01" in v and "OVL-2" in v for v in report_one_missing.violations)
