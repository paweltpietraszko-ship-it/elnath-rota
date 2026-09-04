"""ROTA-T055 -- implementation reproducers for the acceptance matrix in
tasks/ROTA-T055/brief.md section 9."""
from __future__ import annotations

from datetime import datetime

from rota.application.durable_inputs import append_availability
from rota.application.open_month import open_month
from rota.domain import Assignment, AssignmentRole, AssignmentState, AvailabilityKind, ShiftKind
from rota.persistence.db import connect
from tests.test_t020 import MONTH, _create_version, _seed, _work_item


def _s1(assignment_id: str, employee_id: str, start: datetime, end: datetime) -> Assignment:
    return Assignment(
        assignment_id, "", employee_id, start, end,
        AssignmentRole.PERIODIC_TRAINING, AssignmentState.PLANNED, False, None, None,
    )


def test_t55_03_real_rest_01_soft_reaches_get_month():
    """T55-03: an S1 with a real rest shortfall does not HARD-block (already
    covered by T052's own suite) but its REST-01 SOFT warning, previously
    computed and discarded by validate() on every write, now reaches a
    plain GET month."""
    conn = connect(":memory:")
    _seed(conn)
    night_demand, night = _work_item(3, 18, 6, kind=ShiftKind.N)  # ends 2026-08-04 06:00
    training = _s1("S1-A1", "EMP-1", datetime(2026, 8, 4, 9), datetime(2026, 8, 4, 11))  # only 3h gap
    _create_version(conn, [night_demand], [night, training])

    view = open_month(conn, site_id="SITE-1", month=MONTH)
    assert any("REST-01 SOFT" in w for w in view.warnings)
    conn.close()


def test_t55_03_reload_recomputes_rather_than_persists(tmp_path):
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed(conn)
    night_demand, night = _work_item(3, 18, 6, kind=ShiftKind.N)
    training = _s1("S1-A1", "EMP-1", datetime(2026, 8, 4, 9), datetime(2026, 8, 4, 11))
    _create_version(conn, [night_demand], [night, training])
    conn.close()

    conn = connect(db_path)  # simulates a plain reload -- fresh connection, same durable data
    view = open_month(conn, site_id="SITE-1", month=MONTH)
    assert any("REST-01 SOFT" in w for w in view.warnings)
    no_warning_table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%warning%'"
    ).fetchall()
    assert no_warning_table == []  # T55-04 architectural constraint: no persistence table for warnings
    conn.close()


def test_t55_08_month_without_current_version_skips_validate(tmp_path):
    """T55-08: no current ScheduleVersion -> no current snapshot to
    validate -- only pre-existing assembler/open-month warnings, no crash,
    no fabricated warning state."""
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed(conn)
    view = open_month(conn, site_id="SITE-1", month=MONTH)
    assert view.current_version is None
    assert not any("REST-01" in w or "WEEKLY-REST-01" in w for w in view.warnings)
    conn.close()


def test_r2_01_day_shift_off_soft_is_polish_and_employee_id_is_quoted(tmp_path):
    """Codex R2-01 (tests_r2.txt): the raw employee UUID and English text
    reaching the coordinator through T055's own new path. A real N shift
    ending inside a DAY_SHIFT_OFF window produces the SOFT warning;
    resolveWarningText()'s exact mechanism (substituting 'employee_id' for
    the roster display name) must now find a match, and no ASCII-only
    check should find raw English rule vocabulary in the body."""
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed(conn)
    append_availability(
        conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DAYOFF", employee_id="EMP-1",
        kind=AvailabilityKind.DAY_SHIFT_OFF, start_date=MONTH.replace(day=4), end_date=MONTH.replace(day=4), active=True,
    )
    night_demand, night = _work_item(3, 18, 6, kind=ShiftKind.N, state=AssignmentState.PLANNED)  # ends 2026-08-04 06:00, inside the day off
    _create_version(conn, [night_demand], [night])

    view = open_month(conn, site_id="SITE-1", month=MONTH)
    warning = next(w for w in view.warnings if "DAY_SHIFT_OFF-01 SOFT" in w)
    assert "'EMP-1'" in warning  # resolveWarningText()'s exact expected quote format
    assert "enters day off" not in warning  # the raw English text Codex reproduced
    conn.close()


def test_open_month_still_performs_no_write_with_a_current_version(tmp_path):
    """Extends the existing T009 no-write guarantee (test_t009_open_and_assembler.py)
    to the new branch: calling validate() inside open_month() for a month that
    DOES have a current ScheduleVersion must remain read-only."""
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed(conn)
    night_demand, night = _work_item(3, 18, 6, kind=ShiftKind.N)
    training = _s1("S1-A1", "EMP-1", datetime(2026, 8, 4, 9), datetime(2026, 8, 4, 11))
    _create_version(conn, [night_demand], [night, training])

    before_versions = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    before_assignments = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    open_month(conn, site_id="SITE-1", month=MONTH)
    after_versions = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    after_assignments = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]

    assert before_versions == after_versions
    assert before_assignments == after_assignments
    conn.close()
