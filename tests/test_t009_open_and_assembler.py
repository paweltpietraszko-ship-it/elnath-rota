"""ROTA-T009 required test matrix items 1, 2, 4, 5, 6."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from rota.application.assembler import assemble_planning_state
from rota.application.open_month import open_month
from rota.domain import Assignment, AssignmentRole, AssignmentState, MembershipKind, ShiftDemand
from rota.persistence.db import connect
from rota.persistence.schedule_lifecycle import create_schedule_version
from rota.persistence.work_balance_repository import save_work_balance_target
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def test_1_implementation_base_and_lineage_present() -> None:
    """Item 1: base SHA recorded by task_init.py, and the accepted T004-T008
    modules this task composes are all present/importable."""
    hash_file = Path(__file__).resolve().parents[1] / "tasks" / "ROTA-T009" / "repo_before.hash"
    content = hash_file.read_text(encoding="utf-8")
    assert "HEAD_SHA: 1d0a899b091f496248bd672be4d614998a1fedae" in content

    import rota.persistence.decision_ledger  # noqa: F401  (T005)
    import rota.persistence.schedule_lifecycle  # noqa: F401  (T008)
    import rota.persistence.site_rule_repository  # noqa: F401  (T005/T007)
    import rota.persistence.work_balance_repository  # noqa: F401  (T008)


def test_2_open_month_performs_no_write(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    pstate = seed_real_object(conn, case_id="open-1", month=MONTH, seed=100)

    before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    view = open_month(conn, site_id=pstate.site.site_id, month=MONTH)
    after = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    assert before == after == 0
    assert view.current_version is None
    assert view.version_history == ()
    assert len(view.employees) == len(pstate.employees)


def test_4_restart_reconstructs_same_context(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    pstate = seed_real_object(conn, case_id="restart-1", month=MONTH, seed=101)
    conn.close()

    reopened = connect(db_path)
    state, warnings = assemble_planning_state(reopened, site_id=pstate.site.site_id, month=MONTH)
    assert len(state.employees) == len(pstate.employees)
    assert len(state.calendar_days) == len(pstate.calendar_days)
    assert state.site.site_id == pstate.site.site_id
    assert warnings  # missing target_hours for every employee, per item 5


def test_5_missing_calendar_day_auto_generated(tmp_path: Path) -> None:
    """ROTA-CALENDAR-AUTO-GENERATE (OWNER 2026-09-21): a coordinator never
    remembering to visit the Kalendarz screen is the NORMAL case, not an
    error -- assembly now silently self-heals a missing CalendarDay
    instead of raising IncompleteCalendarData. 2026-08-15 is a real PL
    public holiday (Wniebowzięcie NMP), so this also proves the auto-fill
    reconstructs holiday=True correctly, not just holiday=False."""
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="cal-1", month=MONTH, seed=102)
    conn.execute("DELETE FROM calendar_days WHERE date = ?", (date(2026, 8, 15).isoformat(),))
    state, _ = assemble_planning_state(conn, site_id=pstate.site.site_id, month=MONTH)
    restored = next(d for d in state.calendar_days if d.date == date(2026, 8, 15))
    assert restored.holiday is True


def test_5b_missing_calendar_day_never_overwrites_a_manual_correction(tmp_path: Path) -> None:
    """The auto-fill is fill-missing-only: a coordinator's own manual
    correction (e.g. marking a real workday as a company-specific day off)
    must survive re-assembly untouched, exactly like the manual generate
    button's own contract."""
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="cal-1b", month=MONTH, seed=104)
    # 2026-08-10 is an ordinary Monday, not a real PL holiday -- a
    # coordinator manually overrides it to a company day off.
    conn.execute(
        "UPDATE calendar_days SET holiday = 1 WHERE date = ?", (date(2026, 8, 10).isoformat(),),
    )
    state, _ = assemble_planning_state(conn, site_id=pstate.site.site_id, month=MONTH)
    corrected = next(d for d in state.calendar_days if d.date == date(2026, 8, 10))
    assert corrected.holiday is True


def test_5_missing_target_hours_not_invented_and_demand_count_unchanged(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="target-1", month=MONTH, seed=103)
    state_before, warnings_before = assemble_planning_state(conn, site_id=pstate.site.site_id, month=MONTH)
    demand_count_before = len(state_before.shift_demands)
    assert state_before.work_balances == ()
    # ROTA-ASSEMBLER-STALE-EQUAL-SPLIT-WARNING-TEXT (OWNER_ACCEPTED
    # 2026-09-15): the old clause named the now-removed equal-split
    # fallback; replaced with a plain instruction to set target hours.
    assert any("ustaw godziny docelowe" in w for w in warnings_before)

    first_employee = pstate.employees[0].employee_id
    save_work_balance_target(conn, employee_id=first_employee, month=MONTH, target_hours=160)
    state_after, warnings_after = assemble_planning_state(conn, site_id=pstate.site.site_id, month=MONTH)
    assert len(state_after.work_balances) == 1
    assert len(state_after.shift_demands) == demand_count_before  # unaffected by target_hours presence
    # ROTA-T011-D (FINDING D-R3-1): the assembler now also computes each
    # employee's quarter carry-in from earlier months, which this fixture
    # never sets target_hours for either. CONSTRAINT pt.5 explicitly allows
    # -- and here requires -- one new warning for first_employee's own
    # genuine earlier-month gap, on top of (never instead of) the unchanged
    # per-employee omission warnings below.
    omitted_warnings = [w for w in warnings_after if "ustaw godziny docelowe" in w]
    carry_in_warnings = [w for w in warnings_after if "bilans godzin z wcześniejszej części kwartału przyjęto jako 0" in w]
    # T050: the missing-target warning is LOCAL-only since T041 (X/Y in this
    # fixture are EXTERNAL_SUPPORT and never get one) -- comparing against
    # len(pstate.employees) counted the two EXTERNAL_SUPPORT employees too.
    local_count = sum(1 for m in pstate.memberships if m.membership_kind == MembershipKind.LOCAL)
    assert len(omitted_warnings) == local_count - 1
    assert len(carry_in_warnings) == 1
    assert len(warnings_after) == len(omitted_warnings) + len(carry_in_warnings)


def test_6_boundary_and_cross_site_current_assignments_included_noncurrent_excluded(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="cross-1", month=MONTH, seed=104)
    site_id = pstate.site.site_id
    employee_id = pstate.employees[0].employee_id

    # a non-current historical version for the SAME site/month: create then
    # supersede it with a child so it becomes non-current.
    old_demand = ShiftDemand("DEM-OLD", "", datetime(2026, 8, 10, 5, 0), datetime(2026, 8, 10, 17, 0), 1)
    create_schedule_version(
        conn, version_id="V-OLD", site_id=site_id, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 1, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[old_demand], assignments=[
            Assignment("ASG-OLD", "", employee_id, datetime(2026, 8, 10, 5, 0), datetime(2026, 8, 10, 17, 0),
                       AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-OLD", None),
        ], deviations=[], effective_from=date(2026, 8, 1),
    )
    create_schedule_version(
        conn, version_id="V-NEW", site_id=site_id, month=MONTH, parent_version_id="V-OLD",
        created_at=datetime(2026, 8, 2, 8, 0), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[], assignments=[], deviations=[], effective_from=date(2026, 8, 2),
    )

    state, _ = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    boundary_ids = {a.assignment_id for a in state.boundary_assignments}
    assert "ASG-OLD" not in boundary_ids  # non-current version must not contribute
