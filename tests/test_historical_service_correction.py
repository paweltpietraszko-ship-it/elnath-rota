"""ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT (brief 8aac3bc, Codex final
preimplementation PASS 92013f2): the backend is the sole owner of
effective_from for an ordinary manual correction (client-supplied values
are ignored, not merely defaulted), and an already-started Assignment
(start_datetime <= now) may only have its employee_id swapped, with a
mandatory reason, to record who actually worked it -- every other field
named in brief section 4 stays byte-identical. freeze_or_unfreeze,
mark_not_worked and mark_training_realized are explicitly NOT subject to
this guard (OWNER_CONFIRMED during implementation: they are inherently
retrospective, pre-existing mechanisms this Task does not touch).

Each test here monkeypatches manual_edit._now() directly (overriding
conftest.py's autouse freeze) to control which side of the now-vs-
start_datetime boundary a fixture Assignment falls on, rather than
depending on real wall-clock time.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from rota.application import manual_edit
from rota.application.errors import HistoricalServiceMutationRejected
from rota.domain import AssignmentRole, AssignmentState
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_and_select(conn, site_id: str):
    from rota.application import plan_ops
    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0], coordinator_id="COORD-1")


def _seed_and_plan(case_id: str, seed: int):
    conn = connect(":memory:")
    pstate = seed_real_object(conn, case_id=case_id, month=MONTH, seed=seed)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    return conn, site_id, pstate, v1


def _freeze_now(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(manual_edit, "_now", lambda: when)


# --- H1/H2: ordinary future correction -- backend always owns effective_from -


def test_h1_single_future_correction_gets_backend_today_ignoring_client_value(monkeypatch):
    conn, site_id, _pstate, v1 = _seed_and_plan("hist-h1", 500)
    _freeze_now(monkeypatch, datetime(2026, 7, 1))  # every August fixture Assignment is future
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    edited = replace(target, schedule_version_id="", end_datetime=target.start_datetime.replace(hour=13))
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
        upsert_assignments=[edited], effective_from=date(1999, 1, 1),  # type: ignore[arg-type]
    )
    assert v2.effective_from == date(2026, 7, 1)


def test_h2_multiple_future_assignments_one_child_one_effective_from(monkeypatch):
    conn, site_id, pstate, v1 = _seed_and_plan("hist-h2", 501)
    _freeze_now(monkeypatch, datetime(2026, 7, 1))
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    targets = [a for a in snapshot.assignments if a.role == AssignmentRole.PRIMARY][:2]
    other = next(e.employee_id for e in pstate.employees if e.employee_id not in {t.employee_id for t in targets})
    edited = [replace(t, schedule_version_id="", employee_id=other) for t in targets]
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", upsert_assignments=edited,
    )
    assert v2.effective_from == date(2026, 7, 1)
    assert v2.version_id != v1.version_id


# --- H4: an already-started Assignment cannot have a protected field changed


def test_h4_started_assignment_disallowed_field_change_is_rejected(monkeypatch):
    conn, site_id, _pstate, v1 = _seed_and_plan("hist-h4", 502)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    _freeze_now(monkeypatch, target.start_datetime)  # exactly at start -- started per section 2
    shrunk = replace(target, schedule_version_id="", end_datetime=target.start_datetime.replace(hour=13))
    with pytest.raises(HistoricalServiceMutationRejected):
        manual_edit.apply_manual_correction(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", upsert_assignments=[shrunk],
        )


# --- H5/H6: the one allowed exception -- employee_id swap with mandatory note


def test_h5_started_assignment_employee_swap_with_note_succeeds_and_is_recorded(monkeypatch):
    conn, site_id, pstate, v1 = _seed_and_plan("hist-h5", 503)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    _freeze_now(monkeypatch, target.start_datetime)
    other = next(e.employee_id for e in pstate.employees if e.employee_id != target.employee_id)
    swapped = replace(target, schedule_version_id="", employee_id=other)
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
        upsert_assignments=[swapped], note="Jan Kowalski faktycznie wykonał tę służbę zamiast zaplanowanej osoby.",
    )
    saved = next(a for a in get_schedule_snapshot(conn, v2.version_id).assignments if a.assignment_id == target.assignment_id)
    assert saved.employee_id == other
    # H5: every other field stays exactly as it was.
    assert saved.start_datetime == target.start_datetime
    assert saved.end_datetime == target.end_datetime
    assert saved.state == target.state


def test_h6_same_swap_without_a_reason_is_rejected(monkeypatch):
    conn, site_id, pstate, v1 = _seed_and_plan("hist-h6", 504)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    _freeze_now(monkeypatch, target.start_datetime)
    other = next(e.employee_id for e in pstate.employees if e.employee_id != target.employee_id)
    swapped = replace(target, schedule_version_id="", employee_id=other)
    with pytest.raises(HistoricalServiceMutationRejected):
        manual_edit.apply_manual_correction(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", upsert_assignments=[swapped],
        )


# --- H7/H8: a series mixing a historical exception with future corrections -


def test_h7_series_with_historical_exception_uses_earliest_historical_start(monkeypatch):
    conn, site_id, pstate, v1 = _seed_and_plan("hist-h7", 505)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    historical = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    future = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-05-D" and a.assignment_id != historical.assignment_id)
    _freeze_now(monkeypatch, historical.start_datetime + timedelta(hours=1))
    assert future.start_datetime > historical.start_datetime  # future must genuinely still be ahead of "now"
    other = next(e.employee_id for e in pstate.employees if e.employee_id != historical.employee_id)
    swapped = replace(historical, schedule_version_id="", employee_id=other)
    moved_future = replace(future, schedule_version_id="", employee_id=other)
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
        upsert_assignments=[swapped, moved_future], note="Faktyczny wykonawca zapisany po fakcie.",
    )
    assert v2.effective_from == historical.start_datetime.date()


def test_h8_historical_exception_does_not_open_a_side_door_for_another_historical_assignment(monkeypatch):
    """A second, already-started Assignment in the same batch must still be
    individually guarded -- a legal historical exception elsewhere in the
    same correction does not relax the rule for it."""
    conn, site_id, pstate, v1 = _seed_and_plan("hist-h8", 506)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    historical_a = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    historical_b = next(
        a for a in snapshot.assignments
        if a.covers_demand_id not in (None, historical_a.covers_demand_id) and a.role == AssignmentRole.PRIMARY
        and a.start_datetime <= historical_a.start_datetime + timedelta(days=1)
    )
    _freeze_now(monkeypatch, max(historical_a.start_datetime, historical_b.start_datetime))
    other = next(e.employee_id for e in pstate.employees if e.employee_id not in {historical_a.employee_id, historical_b.employee_id})
    legal_swap = replace(historical_a, schedule_version_id="", employee_id=other)
    illegal_shrink = replace(historical_b, schedule_version_id="", end_datetime=historical_b.start_datetime)
    with pytest.raises(HistoricalServiceMutationRejected):
        manual_edit.apply_manual_correction(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
            upsert_assignments=[legal_swap, illegal_shrink], note="Faktyczny wykonawca zapisany po fakcie.",
        )


# --- freeze/unfreeze and mark_not_worked stay retrospective, unguarded -----


def test_freeze_on_an_already_started_assignment_is_not_subject_to_the_guard(monkeypatch):
    conn, site_id, _pstate, v1 = _seed_and_plan("hist-freeze", 507)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    _freeze_now(monkeypatch, target.start_datetime)
    v2 = manual_edit.freeze_or_unfreeze(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", assignment_id=target.assignment_id, frozen=True,
    )
    saved = next(a for a in get_schedule_snapshot(conn, v2.version_id).assignments if a.assignment_id == target.assignment_id)
    assert saved.frozen is True


def test_mark_not_worked_on_an_already_started_assignment_is_not_subject_to_the_guard(monkeypatch):
    conn, site_id, _pstate, v1 = _seed_and_plan("hist-nn", 508)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    target = next(a for a in snapshot.assignments if a.covers_demand_id == "2026-08-01-D")
    _freeze_now(monkeypatch, target.start_datetime)
    v2 = manual_edit.mark_not_worked(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", assignment_id=target.assignment_id,
    )
    saved = next(a for a in get_schedule_snapshot(conn, v2.version_id).assignments if a.assignment_id == target.assignment_id)
    assert saved.state == AssignmentState.CANCELLED and saved.operational_code == "NN"


if __name__ == "__main__":
    print("test_historical_service_correction module OK")
