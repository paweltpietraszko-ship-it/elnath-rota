"""ROTA-T010 implementation re-audit round 7: R6-1 closure only."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.application.manual_edit import apply_manual_correction
from rota.domain import AssignmentState, ScheduleStatus
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.db import connect
from rota.persistence.schedule_repository import (
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
)
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


@pytest.mark.parametrize(
    "mutation",
    ["employee_id", "start_datetime", "end_datetime", "covers_demand_id"],
)
def test_r7_d_nn_transition_preserves_contracted_assignment_identity_fields(
    tmp_path, mutation
) -> None:
    """The contracted child changes state/code, not the represented shift."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    original_demand = _demand(demand_id="DEMAND-ORIGINAL", day=1)
    other_demand = _demand(demand_id="DEMAND-OTHER", day=2)
    planned = _primary("AS-TARGET", EMP_A, original_demand)
    _create_parent(
        conn,
        version_id="SV-PARENT",
        demands=[original_demand, other_demand],
        assignments=[planned],
    )
    changes = {
        "employee_id": {"employee_id": EMP_B},
        "start_datetime": {"start_datetime": datetime(2026, 8, 1, 6)},
        "end_datetime": {"end_datetime": datetime(2026, 8, 1, 16)},
        "covers_demand_id": {"covers_demand_id": other_demand.demand_id},
    }
    invented_nn = replace(
        planned,
        state=AssignmentState.CANCELLED,
        operational_code="NN",
        **changes[mutation],
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(Exception):
        apply_manual_correction(
            conn,
            site_id=SITE_ID,
            month=MONTH,
            coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 8, 3),
            upsert_assignments=[invented_nn],
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before
    assert get_current_version_id(conn, SITE_ID, MONTH) == "SV-PARENT"
    parent = get_schedule_snapshot(conn, "SV-PARENT")
    assert parent.assignments == [replace(planned, schedule_version_id="SV-PARENT")]


def test_r7_d_finalize_replacement_cannot_introduce_nn_in_place(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    demand = _demand()
    planned = _primary("AS-TARGET", EMP_A, demand)
    _create_parent(conn, version_id="SV-WORKING", demands=[demand], assignments=[planned])

    with pytest.raises(Exception):
        lifecycle.finalize_schedule_version(
            conn,
            version_id="SV-WORKING",
            applied_rule_version_ids=[],
            shift_demands=[demand],
            assignments=[
                replace(planned, state=AssignmentState.CANCELLED, operational_code="NN")
            ],
            deviations=[],
        )

    assert get_schedule_version_header(conn, "SV-WORKING").status == ScheduleStatus.WORKING
    snapshot = get_schedule_snapshot(conn, "SV-WORKING")
    reread = next(item for item in snapshot.assignments if item.assignment_id == planned.assignment_id)
    assert reread.state == AssignmentState.PLANNED
    assert reread.operational_code is None
