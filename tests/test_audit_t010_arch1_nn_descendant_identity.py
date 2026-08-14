"""ROTA-T010 architect verdict ARCH-1: an already-NN Assignment must not be
"moved" onto a different employee/interval/demand in a later descendant or
in-place write -- the same identity requirement R7-1 established for the
first PLANNED PRIMARY -> CANCELLED+NN transition, applied to the
already-NN-preserved branch of validate_nn_provenance too."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.application.manual_edit import apply_manual_correction, mark_not_worked
from rota.domain import AssignmentState
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from tests.test_audit_t010_r6_d import (
    COORDINATOR_ID,
    EMP_A,
    EMP_B,
    MONTH,
    SITE_ID,
    _create_parent,
    _demand,
    _primary,
    _seed_context,
)


def _existing_nn_child(conn):
    original_demand = _demand(demand_id="DEMAND-ORIGINAL", day=1)
    other_demand = _demand(demand_id="DEMAND-OTHER", day=2)
    target = _primary("AS-TARGET", EMP_A, original_demand)
    _create_parent(
        conn, version_id="SV-PARENT", demands=[original_demand, other_demand], assignments=[target],
    )
    child = mark_not_worked(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 2), assignment_id=target.assignment_id,
    )
    return child, target, other_demand


@pytest.mark.parametrize(
    "mutation",
    ["employee_id", "start_datetime", "end_datetime", "covers_demand_id"],
)
def test_arch1_existing_nn_cannot_be_moved_onto_a_different_shift(tmp_path, mutation) -> None:
    from rota.persistence.db import connect

    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    child, target, other_demand = _existing_nn_child(conn)
    nn_assignment = next(a for a in get_schedule_snapshot(conn, child.version_id).assignments if a.assignment_id == target.assignment_id)

    changes = {
        "employee_id": {"employee_id": EMP_B},
        "start_datetime": {"start_datetime": datetime(2026, 8, 1, 6)},
        "end_datetime": {"end_datetime": datetime(2026, 8, 1, 16)},
        "covers_demand_id": {"covers_demand_id": other_demand.demand_id},
    }
    moved_nn = replace(nn_assignment, **changes[mutation])
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(Exception):
        apply_manual_correction(
            conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 8, 3), upsert_assignments=[moved_nn],
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before
    assert get_current_version_id(conn, SITE_ID, MONTH) == child.version_id
    unchanged = get_schedule_snapshot(conn, child.version_id)
    reread = next(a for a in unchanged.assignments if a.assignment_id == target.assignment_id)
    assert reread == nn_assignment


def test_arch1_existing_nn_preserved_unchanged_still_passes(tmp_path) -> None:
    from rota.persistence.db import connect

    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    child, target, _other_demand = _existing_nn_child(conn)
    snapshot = get_schedule_snapshot(conn, child.version_id)

    replayed = apply_manual_correction(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID,
        effective_from=date(2026, 8, 4), upsert_assignments=list(snapshot.assignments),
    )
    replayed_snapshot = get_schedule_snapshot(conn, replayed.version_id)
    nn = next(a for a in replayed_snapshot.assignments if a.assignment_id == target.assignment_id)
    assert nn.state == AssignmentState.CANCELLED
    assert nn.operational_code == "NN"
    assert nn.employee_id == target.employee_id
    assert nn.start_datetime == target.start_datetime
    assert nn.end_datetime == target.end_datetime
    assert nn.covers_demand_id == target.covers_demand_id
