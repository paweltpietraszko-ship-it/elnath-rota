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
from tests.support.t008_fixtures import seed_base_entities


MONTH = date(2026, 8, 1)


def test_hiding_nonempty_version_preserves_complete_snapshot_and_sql_delete_guard(tmp_path):
    conn = connect(tmp_path / "rota.db")
    seed_base_entities(conn)
    demand = ShiftDemand(
        "DEM-1", "", datetime(2026, 8, 3, 5), datetime(2026, 8, 3, 17), 1
    )
    assignment = Assignment(
        "ASG-1", "", "EMP-1", datetime(2026, 8, 3, 5), datetime(2026, 8, 3, 17),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-1", None,
    )
    deviation = Deviation(
        "DEV-1", "", DeviationCategory.HOURS, "AUDIT", "EMP-1", False, None, None, None
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-1", site_id="SITE-1", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[demand], assignments=[assignment],
        deviations=[deviation], effective_from=MONTH,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-2", site_id="SITE-1", month=MONTH, parent_version_id="SV-1",
        created_at=datetime(2026, 8, 2, 8), created_by="COORD-1",
        applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[], effective_from=MONTH,
    )
    before = repository.get_schedule_snapshot(conn, "SV-1")

    lifecycle.exclude_version_from_history(
        conn, site_id="SITE-1", month=MONTH, version_id="SV-1"
    )

    after = repository.get_schedule_snapshot(conn, "SV-1")
    assert after == before
    assert [d.demand_id for d in after.shift_demands] == ["DEM-1"]
    assert [a.assignment_id for a in after.assignments] == ["ASG-1"]
    assert [d.deviation_id for d in after.deviations] == ["DEV-1"]
    assert repository.get_current_version_id(conn, "SITE-1", MONTH) == "SV-2"
    assert [v.version_id for v in repository.list_schedule_versions(conn, "SITE-1", MONTH)] == ["SV-2"]
    assert [v.version_id for v in repository.list_schedule_versions(
        conn, "SITE-1", MONTH, include_excluded=True
    )] == ["SV-1", "SV-2"]
    with pytest.raises(sqlite3.IntegrityError, match="physical delete"):
        conn.execute("DELETE FROM schedule_versions WHERE version_id = 'SV-1'")
