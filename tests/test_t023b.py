"""ROTA-T023b -- ochrona rest-rule enforcement
(arch/FROZEN_ADDENDUM_OCHRONA_REST_RULES_01.md, tasks/ROTA-T023b/brief.md
section 10 minimum test matrix)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from rota.application.durable_inputs import correct_site_planning_regime
from rota.application.manual_edit import apply_manual_correction
from rota.application.plan_ops import select_candidate
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import schedule_repository as sr
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import LATEST_SCHEMA_VERSION, connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_lifecycle import RegimeReplanRequired
from rota.persistence.site_repository import SiteRegimeChangeRejected, get_site, save_site
from rota.planning.state import PlanningState
from rota.planning.validator import validate
from rota.planning.work_periods import (
    WEEKLY_REST_REQUIRED_HOURS,
    WorkPeriod,
    effective_required_rest_after_hours,
    max_uninterrupted_free_hours,
    weekly_settlement_windows,
)
from tests.support.t008_fixtures import make_profile

MONTH = date(2026, 8, 1)


def _seed(conn, *, regime: SitePlanningRegime = SitePlanningRegime.ORDINARY, employees=("EMP-1",)):
    from rota.persistence.coordinator_repository import save_coordinator
    from rota.persistence.site_profile_repository import save_site_profile
    save_site_profile(conn, make_profile("PROF-1"))
    save_site(conn, Site(site_id="SITE-1", profile_id="PROF-1", display_name="Site One", active=True, planning_regime=regime))
    save_coordinator(conn, Coordinator("COORD-1", "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    for emp in employees:
        save_employee(conn, Employee(emp, f"Pracownik {emp}", date(2026, 1, 1), None, False))
        save_site_membership(conn, SiteMembership(
            emp, "SITE-1", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True,
        ))
    from rota.persistence.calendar_repository import save_calendar_day
    from rota.domain import CalendarDay
    import calendar as _cal
    n_days = _cal.monthrange(MONTH.year, MONTH.month)[1]
    for i in range(n_days):
        save_calendar_day(conn, CalendarDay(MONTH + timedelta(days=i), False))


def _create_version(conn, demands, assignments, *, version_id="SV-1", parent=None, effective_from=date(2026, 7, 25)):
    return lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id="SITE-1", month=MONTH, parent_version_id=parent,
        created_at=datetime(2026, 7, 25, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=demands, assignments=assignments, deviations=[], effective_from=effective_from,
    )


def _planned(day, start_h, end_h, *, employee_id="EMP-1", suffix="", demand_id=None):
    d0 = date(2026, 8, day)
    start = datetime.combine(d0, datetime.min.time()).replace(hour=start_h)
    end_day = d0 if end_h > start_h else d0 + timedelta(days=1)
    end = datetime.combine(end_day, datetime.min.time()).replace(hour=end_h % 24)
    did = demand_id or f"DEM-{day}{suffix}"
    demand = ShiftDemand(did, "", start, end, 1, shift_kind=ShiftKind.D if start_h < 12 else ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    assignment = Assignment(f"ASG-{day}{suffix}", "", employee_id, start, end, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, did, None)
    return demand, assignment


# --- T23b-01: migration -------------------------------------------------
def test_t23b_01_migration_v9_adds_planning_regime_with_ordinary_default():
    conn = connect(":memory:")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION == 9
    _seed(conn)
    assert get_site(conn, "SITE-1").planning_regime == SitePlanningRegime.ORDINARY
    assert conn.execute("SELECT planning_regime FROM sites WHERE site_id='SITE-1'").fetchone() == ("ORDINARY",)


def test_t23b_01b_ochrona_site_round_trips():
    conn = connect(":memory:")
    _seed(conn, regime=SitePlanningRegime.OCHRONA)
    assert get_site(conn, "SITE-1").planning_regime == SitePlanningRegime.OCHRONA


# --- T23b-02/03: regime write protection + correction command -----------
def test_t23b_02_ordinary_write_rejects_regime_change():
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(SiteRegimeChangeRejected):
        save_site(conn, Site(site_id="SITE-1", profile_id="PROF-1", display_name="Renamed", active=True, planning_regime=SitePlanningRegime.OCHRONA))


def test_t23b_02b_correction_changes_regime_records_one_action_no_schedule_mutation():
    conn = connect(":memory:")
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    _create_version(conn, [d1], [a1])
    before_count = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0]
    months = correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    assert get_site(conn, "SITE-1").planning_regime == SitePlanningRegime.OCHRONA
    after_count = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0]
    assert after_count == before_count + 1
    assert months == (MONTH,)  # PLANNED content, ORDINARY provenance != new OCHRONA regime
    # unchanged: no new ScheduleVersion, no Assignment mutation
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == 1
    assert conn.execute("SELECT state FROM assignments WHERE assignment_id='ASG-1'").fetchone() == ("PLANNED",)


def test_t23b_03_same_regime_correction_is_noop():
    conn = connect(":memory:")
    _seed(conn)
    before = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0]
    result = correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.ORDINARY)
    after = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0]
    assert after == before
    assert result == sr.list_regime_replan_required_months(conn, "SITE-1")


# --- T23b-04..07: durable lifecycle gate ---------------------------------
def test_t23b_04_stale_regime_planned_version_requires_replan_after_reconnect(tmp_path):
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    conn.close()
    reopened = connect(db_path)
    current_id = sr.get_current_version_id(reopened, "SITE-1", MONTH)
    assert sr.version_requires_regime_replan(reopened, current_id) is True


def test_t23b_04b_realized_only_version_never_requires_replan():
    conn = connect(":memory:")
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    a1 = a1.__class__(**{**a1.__dict__, "state": AssignmentState.REALIZED})
    _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    current_id = sr.get_current_version_id(conn, "SITE-1", MONTH)
    assert sr.version_requires_regime_replan(conn, current_id) is False


def test_t23b_05_finalize_rejects_stale_regime_version():
    conn = connect(":memory:")
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    version = _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    with pytest.raises(RegimeReplanRequired):
        lifecycle.finalize_schedule_version(conn, version_id=version.version_id)
    assert conn.execute("SELECT status FROM schedule_versions WHERE version_id=?", (version.version_id,)).fetchone()[0].startswith("WORKING")


def test_t23b_06_restore_rejects_stale_regime_target():
    conn = connect(":memory:")
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    root = _create_version(conn, [d1], [a1])
    child = _create_version(conn, [d1], [a1], version_id="SV-2", parent=root.version_id, effective_from=date(2026, 7, 26))
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    with pytest.raises(RegimeReplanRequired):
        lifecycle.restore_schedule_version(conn, site_id="SITE-1", month=MONTH, version_id=root.version_id)
    assert sr.get_current_version_id(conn, "SITE-1", MONTH) == child.version_id


def test_t23b_07_export_fails_closed_on_regime_replan_required():
    from rota.application import schedule_export as SE
    conn = connect(":memory:")
    _seed(conn)
    d1, a1 = _planned(1, 5, 17)
    _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._reconstruct_lineage(conn, "SITE-1", MONTH)
    assert exc.value.code == "REGIME_REPLAN_REQUIRED"


# --- T23b-08/09: provenance inheritance + adoption ------------------------
def test_t23b_08_root_version_inherits_current_site_regime():
    conn = connect(":memory:")
    _seed(conn, regime=SitePlanningRegime.OCHRONA)
    d1, a1 = _planned(1, 5, 17)
    version = _create_version(conn, [d1], [a1])
    assert version.planning_regime == SitePlanningRegime.OCHRONA


def test_t23b_08b_replan_child_inherits_parent_provenance_not_current_site():
    conn = connect(":memory:")
    _seed(conn)  # ORDINARY
    d1, a1 = _planned(1, 5, 17)
    root = _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    child = _create_version(conn, [d1], [a1], version_id="SV-2", parent=root.version_id, effective_from=date(2026, 7, 26))
    assert child.planning_regime == SitePlanningRegime.ORDINARY  # inherits parent, not current Site


def test_t23b_09_selected_candidate_adopts_current_site_regime():
    conn = connect(":memory:")
    _seed(conn)  # ORDINARY
    d1, a1 = _planned(1, 5, 17)
    _create_version(conn, [d1], [a1])
    correct_site_planning_regime(conn, coordinator_id="COORD-1", site_id="SITE-1", planning_regime=SitePlanningRegime.OCHRONA)
    header = select_candidate(conn, site_id="SITE-1", month=MONTH, candidate=[a1], coordinator_id="COORD-1")
    assert header.planning_regime == SitePlanningRegime.OCHRONA
    assert sr.version_requires_regime_replan(conn, header.version_id) is False


# --- pure arithmetic (work_periods.py) ------------------------------------
def test_effective_rest_floor_only_for_exact_24h_under_ochrona():
    p24 = WorkPeriod("E1", "k", datetime(2026, 8, 1, 5), datetime(2026, 8, 2, 5), 11, ("a",))
    assert effective_required_rest_after_hours(p24, ochrona=True) == 24
    assert effective_required_rest_after_hours(p24, ochrona=False) == 11
    p12 = WorkPeriod("E1", "k", datetime(2026, 8, 1, 5), datetime(2026, 8, 1, 17), 11, ("a",))
    assert effective_required_rest_after_hours(p12, ochrona=True) == 11
    p24_high = WorkPeriod("E1", "k", datetime(2026, 8, 1, 5), datetime(2026, 8, 2, 5), 30, ("a",))
    assert effective_required_rest_after_hours(p24_high, ochrona=True) == 30  # configured stronger value wins


@pytest.mark.parametrize("year,month,expected_windows", [
    (2026, 8, 4),  # 31 days -> 4 complete weeks, 3 trailing days excluded
    (2026, 9, 4),  # 30 days -> 4 complete weeks, 2 trailing days excluded
    (2026, 2, 4),  # 28 days -> exactly 4 weeks
    (2028, 2, 4),  # 29 days (leap) -> 4 weeks, 1 trailing day excluded
])
def test_weekly_settlement_windows_shapes(year, month, expected_windows):
    windows = weekly_settlement_windows(date(year, month, 1))
    assert len(windows) == expected_windows
    assert windows[0][0] == datetime(year, month, 1)
    for start, end in windows:
        assert (end - start) == timedelta(days=7)


def test_weekly_settlement_windows_no_cross_month_window():
    windows = weekly_settlement_windows(date(2026, 8, 1))
    assert all(w[1] <= datetime(2026, 9, 1) for w in windows)


@pytest.mark.parametrize("free_hours,should_pass", [
    (34.983333, False),  # 34h59m
    (35.0, True),
    (35.016667, True),  # 35h01m
])
def test_max_uninterrupted_free_hours_boundary(free_hours, should_pass):
    # Work pressed against both window boundaries so only the middle gap is
    # under test -- no boundary free-time to confound the assertion.
    window_start = datetime(2026, 8, 1)
    work_end = window_start + timedelta(hours=12)
    work_start_2 = work_end + timedelta(hours=free_hours)
    window_end = work_start_2 + timedelta(hours=12)
    free = max_uninterrupted_free_hours(window_start, window_end, [(window_start, work_end), (work_start_2, work_start_2 + timedelta(hours=12))])
    assert (free >= WEEKLY_REST_REQUIRED_HOURS) == should_pass


def test_max_uninterrupted_free_hours_empty_window_is_fully_free():
    window_start = datetime(2026, 8, 1)
    window_end = window_start + timedelta(days=7)
    assert max_uninterrupted_free_hours(window_start, window_end, []) == 168.0


# --- validator: REST-01 24h floor + WEEKLY-REST-01 ------------------------
def _bare_state(*, regime, shift_demands=(), existing_assignments=(), month=MONTH, boundary_assignments=()):
    profile = make_profile("PROF-1")
    return PlanningState(
        site=Site("SITE-1", "PROF-1", "Site One", True, planning_regime=regime),
        profile=profile, month=month, calendar_days=(), boundary_assignments=boundary_assignments,
        memberships=(), employees=(), external_windows=(), availability_records=(),
        site_rules=(), unresolved_site_rules=(), site_rule_applicability=(),
        shift_demands=shift_demands, existing_assignments=existing_assignments, deviations=(),
        work_balances=(), holiday_history=(), other_site_assignments=(), schedule_version_id="SV-X",
    )


def _h24_pair(employee_id, day, *, rest_after=11, period="WP-1", state=AssignmentState.PLANNED):
    d0 = date(2026, 8, day)
    start = datetime.combine(d0, datetime.min.time())
    a1 = Assignment(f"A1-{day}", "SV-X", employee_id, start, start + timedelta(hours=12), AssignmentRole.PRIMARY, state, False, None, None, work_period_id=period, required_rest_after_hours=rest_after)
    a2 = Assignment(f"A2-{day}", "SV-X", employee_id, start + timedelta(hours=12), start + timedelta(hours=24), AssignmentRole.PRIMARY, state, False, None, None, work_period_id=period, required_rest_after_hours=rest_after)
    return a1, a2


def test_validator_rest01_raises_floor_to_24h_under_ochrona():
    a1, a2 = _h24_pair("EMP-1", 1, rest_after=11)
    next_start = datetime(2026, 8, 2, 12)  # only 12h after the 24h shift ends (2026-08-02 00:00)
    a3 = Assignment("A3", "SV-X", "EMP-1", next_start, next_start + timedelta(hours=12), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None, work_period_id="WP-2", required_rest_after_hours=11)
    state = _bare_state(regime=SitePlanningRegime.OCHRONA, existing_assignments=(a1, a2, a3))
    report = validate(state, [a1, a2, a3])
    assert any(v.rule == "REST-01" for v in report.violation_details)


def test_validator_rest01_ordinary_keeps_configured_rest():
    a1, a2 = _h24_pair("EMP-1", 1, rest_after=11)
    next_start = datetime(2026, 8, 2, 11)  # exactly 11h after the 24h shift ends
    a3 = Assignment("A3", "SV-X", "EMP-1", next_start, next_start + timedelta(hours=12), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None, work_period_id="WP-2", required_rest_after_hours=11)
    state = _bare_state(regime=SitePlanningRegime.ORDINARY, existing_assignments=(a1, a2, a3))
    report = validate(state, [a1, a2, a3])
    assert not any(v.rule == "REST-01" for v in report.violation_details)


def test_validator_weekly_rest01_fires_under_ochrona_only():
    # One 12h shift/day, every day of the week: max gap anywhere is 12h,
    # never 35h -- a genuine weekly-rest violation regardless of window
    # boundary placement.
    intervals = []
    d = date(2026, 8, 1)
    for i in range(7):
        start = datetime.combine(d, datetime.min.time()) + timedelta(hours=24 * i)
        end = start + timedelta(hours=12)
        intervals.append(Assignment(f"W{i}", "SV-X", "EMP-1", start, end, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None))
    state_ochrona = _bare_state(regime=SitePlanningRegime.OCHRONA, existing_assignments=tuple(intervals))
    report = validate(state_ochrona, intervals)
    assert any(v.rule == "WEEKLY-REST-01" for v in report.violation_details)

    state_ordinary = _bare_state(regime=SitePlanningRegime.ORDINARY, existing_assignments=tuple(intervals))
    report2 = validate(state_ordinary, intervals)
    assert not any(v.rule == "WEEKLY-REST-01" for v in report2.violation_details)


def test_validator_weekly_rest01_passes_with_one_big_gap():
    d = date(2026, 8, 1)
    start = datetime.combine(d, datetime.min.time())
    a1 = Assignment("W1", "SV-X", "EMP-1", start, start + timedelta(hours=12), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None)
    a2 = Assignment("W2", "SV-X", "EMP-1", start + timedelta(hours=12 + 36), start + timedelta(hours=12 + 36 + 12), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None)
    state = _bare_state(regime=SitePlanningRegime.OCHRONA, existing_assignments=(a1, a2))
    report = validate(state, [a1, a2])
    assert not any(v.rule == "WEEKLY-REST-01" for v in report.violation_details)


# --- architect review A1: same-Site boundary_assignments parity -----------
def test_validator_weekly_rest01_counts_same_site_boundary_work():
    """Architect review A1: previous-month same-Site work spilling into day 1
    (state.boundary_assignments) must occupy time in the first settlement
    week, matching solver's target_fixed exactly. Without it, this exact
    scenario would wrongly report the week as compliant (the round-8
    regression this test guards against)."""
    window_start = datetime(2026, 8, 1)
    # Previous-month boundary work clipped to [Aug1 00:00, Aug1 08:00) -- 8h.
    boundary = Assignment(
        "BND-1", "SV-PREV", "EMP-1", datetime(2026, 7, 31, 20), datetime(2026, 8, 1, 8),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, None, None,
    )
    # First target shift starts 40h into the window: 0h->40h gap without the
    # boundary (>=35h, wrongly PASS); 8h->40h = 32h with it (<35h, correct FAIL).
    target = []
    for i in range(5):
        s = window_start + timedelta(hours=40 + 24 * i)
        target.append(Assignment(
            f"TGT-{i}", "SV-X", "EMP-1", s, s + timedelta(hours=12),
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
        ))
    state = _bare_state(regime=SitePlanningRegime.OCHRONA, existing_assignments=tuple(target), boundary_assignments=(boundary,))
    report = validate(state, target)
    assert any(v.rule == "WEEKLY-REST-01" for v in report.violation_details), "boundary work must close the otherwise-large first-week gap"

    # Without the boundary fact, the same target work alone leaves a >=35h
    # gap at the start of the week -- confirms the scenario genuinely
    # depends on boundary_assignments, not just the target shifts.
    state_no_boundary = _bare_state(regime=SitePlanningRegime.OCHRONA, existing_assignments=tuple(target))
    report_no_boundary = validate(state_no_boundary, target)
    assert not any(v.rule == "WEEKLY-REST-01" for v in report_no_boundary.violation_details)


def test_manual_correction_weekly_rest_facts_include_boundary_work():
    """Architect review A1: manual_edit._weekly_rest_override_facts must
    reconstruct the same boundary-inclusive fact set as the validator."""
    conn = connect(":memory:")
    _seed(conn, regime=SitePlanningRegime.OCHRONA)
    prev_month = date(2026, 7, 1)
    boundary_demand = ShiftDemand(
        "DEM-BND", "", datetime(2026, 7, 31, 20), datetime(2026, 8, 1, 8), 1,
        shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12,
    )
    boundary_assignment = Assignment(
        "ASG-BND", "", "EMP-1", boundary_demand.start_datetime, boundary_demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-BND", None,
    )
    lifecycle.create_schedule_version(
        conn, version_id="SV-PREV", site_id="SITE-1", month=prev_month, parent_version_id=None,
        created_at=datetime(2026, 7, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[boundary_demand], assignments=[boundary_assignment], deviations=[], effective_from=prev_month,
    )

    target_demands, target_assignments = [], []
    for i in range(5):
        s = datetime(2026, 8, 1) + timedelta(hours=40 + 24 * i)
        did = f"DEM-TGT-{i}"
        target_demands.append(ShiftDemand(did, "", s, s + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12))
        target_assignments.append(Assignment(f"ASG-TGT-{i}", "", "EMP-1", s, s + timedelta(hours=12), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, did, None))
    version = _create_version(conn, target_demands, target_assignments)
    updated = target_assignments[0].__class__(**{**target_assignments[0].__dict__, "schedule_version_id": version.version_id})
    child = apply_manual_correction(
        conn, site_id="SITE-1", month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 7, 27),
        upsert_assignments=[updated],
    )
    row = conn.execute(
        "SELECT structured_parameters FROM site_rule_versions WHERE rule_id = ?", (f"REST-OVERRIDE:{child.version_id}",),
    ).fetchone()
    assert row is not None, "boundary-inclusive weekly-rest fact must trigger a REST_OVERRIDE_RECORD"
    import json
    params = json.loads(row[0])
    assert params["weekly_rest_facts"], "expected a recorded weekly-rest fact once boundary work is counted"


# --- negative scope --------------------------------------------------------
def test_no_new_coordinator_action_kind_introduced():
    from rota.site_memory_types import CoordinatorActionKind
    names = {k.name for k in CoordinatorActionKind}
    assert not any("REGIME" in n for n in names)


def test_deviation_mapping_weekly_rest_is_law():
    from rota.application.deviation_mapping import category_for_rule
    from rota.domain import DeviationCategory
    assert category_for_rule("WEEKLY-REST-01", {}) == DeviationCategory.LAW


# --- manual correction override facts -------------------------------------
def test_manual_correction_records_weekly_rest_override_facts():
    conn = connect(":memory:")
    _seed(conn, regime=SitePlanningRegime.OCHRONA)
    d = date(2026, 8, 1)
    start = datetime.combine(d, datetime.min.time())
    demands, assignments = [], []
    for i in range(7):
        s = start + timedelta(hours=24 * i)
        e = s + timedelta(hours=12)
        did = f"DEM-W{i}"
        demands.append(ShiftDemand(did, "", s, e, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12))
        assignments.append(Assignment(f"ASG-W{i}", "", "EMP-1", s, e, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, did, None))
    version = _create_version(conn, demands, assignments)
    updated = assignments[0].__class__(**{**assignments[0].__dict__, "schedule_version_id": version.version_id})
    child = apply_manual_correction(
        conn, site_id="SITE-1", month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 7, 27),
        upsert_assignments=[updated],
    )
    row = conn.execute(
        "SELECT structured_parameters FROM site_rule_versions WHERE rule_id = ?", (f"REST-OVERRIDE:{child.version_id}",),
    ).fetchone()
    assert row is not None
    import json
    params = json.loads(row[0])
    assert params["weekly_rest_facts"], "expected at least one recorded weekly-rest fact"
    assert params["weekly_rest_facts"][0]["required_rest_hours"] == 35
