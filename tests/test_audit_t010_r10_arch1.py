"""Narrow re-audit of T010 architect finding ARCH-1."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.db import connect
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_repository import (
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
)
from tests.test_audit_t010_arch1_nn_descendant_identity import _existing_nn_child
from tests.test_audit_t010_r6_d import EMP_B, MONTH, SITE_ID, _seed_context


@pytest.mark.parametrize("operation", ["replace", "finalize"])
@pytest.mark.parametrize(
    "mutation",
    ["employee_id", "start_datetime", "end_datetime", "covers_demand_id"],
)
def test_r10_arch1_all_in_place_writers_reject_moved_existing_nn(
    tmp_path, operation, mutation
) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    child, target, other_demand = _existing_nn_child(conn)
    snapshot_before = get_schedule_snapshot(conn, child.version_id)
    header_before = get_schedule_version_header(conn, child.version_id)
    nn = next(
        item
        for item in snapshot_before.assignments
        if item.assignment_id == target.assignment_id
    )
    changes = {
        "employee_id": {"employee_id": EMP_B},
        "start_datetime": {"start_datetime": datetime(2026, 8, 1, 6)},
        "end_datetime": {"end_datetime": datetime(2026, 8, 1, 16)},
        "covers_demand_id": {"covers_demand_id": other_demand.demand_id},
    }
    moved = replace(nn, **changes[mutation])
    assignments = [
        moved if item.assignment_id == nn.assignment_id else item
        for item in snapshot_before.assignments
    ]

    with pytest.raises(MalformedScheduleSnapshot):
        if operation == "replace":
            lifecycle.replace_working_snapshot(
                conn,
                version_id=child.version_id,
                applied_rule_version_ids=list(snapshot_before.applied_rule_version_ids),
                shift_demands=list(snapshot_before.shift_demands),
                assignments=assignments,
                deviations=list(snapshot_before.deviations),
            )
        else:
            lifecycle.finalize_schedule_version(
                conn,
                version_id=child.version_id,
                applied_rule_version_ids=list(snapshot_before.applied_rule_version_ids),
                shift_demands=list(snapshot_before.shift_demands),
                assignments=assignments,
                deviations=[],
            )

    assert get_current_version_id(conn, SITE_ID, MONTH) == child.version_id
    assert get_schedule_version_header(conn, child.version_id) == header_before
    assert get_schedule_snapshot(conn, child.version_id) == snapshot_before
