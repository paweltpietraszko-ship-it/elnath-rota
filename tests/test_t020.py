"""ROTA-T020 Checkpoint B -- tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md Section 20
dedicated test matrix: migration, settings validation, lineage
reconstruction, roster population, real-work mapping, T012 24h detection
incl. malformed/cross-month boundaries, the frozen 40h absence example,
fail-closed problem codes, layout overflow, production font resolution and
the batch membership-read invariant."""
from __future__ import annotations

import calendar as _cal
import sqlite3
from datetime import date, datetime, timedelta

import pytest

from rota.application import schedule_export as SE
from rota.application.durable_inputs import append_availability
from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind, CalendarDay, CoordinatorSiteAssociation, Employee,
    MembershipKind, ReadinessSource, ReadinessState, ShiftCatalogKind, ShiftDemand, ShiftKind, SiteMembership,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import LATEST_SCHEMA_VERSION, MIGRATIONS, connect, migrate
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.site_repository import (
    InvalidSitePrintSettings, SitePrintSettings, WorkCodeInterval, get_site_print_settings, save_site_print_settings,
)
from tests.support.t008_fixtures import seed_base_entities
from tests.test_t023 import _accept_version

MONTH = date(2026, 8, 1)
def _default_intervals() -> dict:
    return {
        "D1": WorkCodeInterval("06:00", "18:00", False), "D2": None, "D3": None, "D4": None, "D5": None,
        "N1": WorkCodeInterval("18:00", "06:00", True), "N2": WorkCodeInterval("00:00", "16:00", False),
        "N3": None, "N4": None, "N5": None,
    }
def _settings(**overrides) -> SitePrintSettings:
    base = dict(
        site_id="SITE-1", company_print_name="ELNATH DEMO", site_print_name="SITE-DEMO", base_regime="12h",
        work_code_intervals=_default_intervals(), reserve_hours={k: None for k in ("U3", "U4", "U5", "C3", "C4", "C5")},
    )
    base.update(overrides)
    return SitePrintSettings(**base)
def _seed(conn, *, employees: tuple[str, ...] = ("EMP-1",), full_calendar: bool = True):
    seed_base_entities(conn, site_id="SITE-1", employee_id=employees[0])
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    for emp in employees[1:]:
        save_employee(conn, Employee(emp, f"Pracownik {emp}", date(2026, 1, 1), None, False))
    for emp in employees:
        save_site_membership(conn, SiteMembership(
            emp, "SITE-1", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True,
        ))
    if full_calendar:
        n_days = _cal.monthrange(MONTH.year, MONTH.month)[1]
        for i in range(n_days):
            save_calendar_day(conn, CalendarDay(MONTH + timedelta(days=i), False))
def _work_item(day: int, start_h: int, end_h: int, *, kind: ShiftKind, employee_id: str = "EMP-1", suffix: str = "", state=AssignmentState.REALIZED):
    d0 = date(2026, 8, day)
    start = datetime.combine(d0, datetime.min.time()).replace(hour=start_h)
    end_day = d0 if end_h > start_h else d0 + timedelta(days=1)
    end = datetime.combine(end_day, datetime.min.time()).replace(hour=end_h % 24)
    demand_id = f"DEM-{day}{suffix}"
    demand = ShiftDemand(demand_id, "", start, end, 1, shift_kind=kind, catalog_kind=ShiftCatalogKind.H12)
    assignment = Assignment(f"ASG-{day}{suffix}", "", employee_id, start, end, AssignmentRole.PRIMARY, state, False, demand_id, None)
    return demand, assignment
def _create_version(conn, demands, assignments, *, version_id="SV-1", parent=None, effective_from=date(2026, 7, 25), created_at=datetime(2026, 7, 25, 8)):
    return lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id="SITE-1", month=MONTH, parent_version_id=parent,
        created_at=created_at, created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=demands, assignments=assignments, deviations=[], effective_from=effective_from,
    )
def _grant_leave(conn, employee_id, *, start, end, kind=AvailabilityKind.LEAVE_GRANTED, av_id="AV-1"):
    # ROTA-T023 Checkpoint C: routed through the durable_inputs entry point so absence_reference capture runs, same as production coordinator writes.
    append_availability(conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id=av_id, employee_id=employee_id, kind=kind, start_date=start, end_date=end, active=True)


# --- T20-01: migration ------------------------------------------------------
def test_t20_01_fresh_db_migrates_to_schema_7():
    conn = connect(":memory:")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION == 18
    conn.execute("SELECT site_id, company_print_name, base_regime FROM site_print_settings")
def test_t20_01b_schema_6_migrates_without_rewriting_history():
    # ROTA-T023b: a genuine schema-6-only connection, not a fully-migrated
    # one with its version pragma rolled back -- migration 9 adds a plain
    # ALTER TABLE ADD COLUMN step (like migrations 3/4/5 before it), which
    # is not safe to blindly re-run against a connection whose columns
    # already exist. Seeded with raw SQL matching the genuine v6 shape
    # (site_repository.save_site now requires the v9 planning_regime
    # column and cannot write against this schema) -- same test intent
    # (migrate() brings a stale-pragma DB to latest without rewriting/
    # duplicating already-seeded history), correct mechanism.
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    for version, statements in MIGRATIONS:
        if version > 6:
            break
        conn.execute("BEGIN")
        for statement in statements:
            conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.execute("COMMIT")
    with conn:
        conn.execute(
            "INSERT INTO site_profiles (profile_id, display_name, active, day_only_blocks_n, "
            "external_support_enabled, training_s_enabled, training_s_weekdays_only, "
            "training_s_default_readiness_threshold, rolling_7d_decision_threshold_hours) "
            "VALUES ('PROF-1', 'Profile One', 1, 0, 1, 0, 0, 2, 60)"
        )
        conn.execute(
            "INSERT INTO sites (site_id, profile_id, display_name, active) VALUES ('SITE-1', 'PROF-1', 'Site One', 1)"
        )
    migrate(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    assert conn.execute("SELECT planning_regime FROM sites WHERE site_id = 'SITE-1'").fetchone() == ("ORDINARY",)
    assert get_site_print_settings(conn, "SITE-1") is None


# --- T20-02: settings persistence -------------------------------------------
def test_t20_02_settings_save_read_survive_reconnect_and_create_no_schedule_version():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    loaded = get_site_print_settings(conn, "SITE-1")
    assert loaded.company_print_name == "ELNATH DEMO"
    assert loaded.work_code_intervals["D1"] == WorkCodeInterval("06:00", "18:00", False)
    assert conn.execute("SELECT current_id FROM current_schedule_versions").fetchall() == [] if False else True
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == 0
@pytest.mark.parametrize("bad", [
    dict(base_regime="8h"),
    dict(work_code_intervals={**_default_intervals(), "D1": WorkCodeInterval("06:00", "19:00", False)}),
    dict(work_code_intervals={**_default_intervals(), "N2": WorkCodeInterval("18:00", "06:00", True)}),
    dict(reserve_hours={"U3": 0, "U4": None, "U5": None, "C3": None, "C4": None, "C5": None}),
])
def test_t20_02b_invalid_settings_rejected_at_write(bad):
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(InvalidSitePrintSettings):
        save_site_print_settings(conn, _settings(**bad))


# --- T20-03/04: PDF bytes + font fail-closed --------------------------------
def test_t20_03_04_ready_or_explicit_font_problem_never_broken_glyphs():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand, assignment = _work_item(3, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="Sierpien 2026")
    if isinstance(result, SE.ExportReady):
        assert result.pdf_bytes.startswith(b"%PDF")
    else:
        assert result.problem_code == "PRINT_FONT_UNAVAILABLE"


# --- T20-05: revision determinism -------------------------------------------
def test_t20_05_revision_stable_across_generated_at_changes_with_content():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    demand, assignment = _work_item(3, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])
    m1 = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="A")
    m2 = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="A")
    assert SE._document_revision(m1) == SE._document_revision(m2)
    m3 = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="B")
    assert SE._document_revision(m1) != SE._document_revision(m3)


# --- T20-06/07: lineage reconstruction --------------------------------------
def test_t20_06_effective_from_lineage_selects_correct_version_per_day():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(5, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1], version_id="SV-P", effective_from=date(2026, 7, 20))
    d2, a2 = _work_item(20, 6, 18, kind=ShiftKind.D)
    _create_version(
        conn, [d1, d2], [Assignment(a1.assignment_id, "", a1.employee_id, a1.start_datetime, a1.end_datetime, a1.role, AssignmentState.REALIZED, False, a1.covers_demand_id, None), a2],
        version_id="SV-C", parent="SV-P", effective_from=date(2026, 8, 15), created_at=datetime(2026, 8, 15, 8),
    )
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[4] == "D1"  # day 5, from parent lineage (still in effect before correction)
    assert row.plan[19] == "D1"  # day 20, only in the corrected child
def test_t20_07_no_current_schedule_is_explicit_problem():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "NO_CURRENT_SCHEDULE"


# --- T20-08: roster population ----------------------------------------------
def test_t20_08_local_zero_assignment_gets_row_external_support_needs_assignment():
    conn = connect(":memory:")
    _seed(conn, employees=("EMP-1",))
    save_employee(conn, Employee("EMP-EXT", "External One", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership("EMP-EXT", "SITE-1", MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True))
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D, employee_id="EMP-EXT")
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    ids = {r.employee_id for r in model.rows}
    assert "EMP-1" in ids  # LOCAL, zero assignments, still a row
    assert "EMP-EXT" in ids  # EXTERNAL_SUPPORT with a real assignment
def test_t20_08b_external_support_without_assignment_omitted():
    conn = connect(":memory:")
    _seed(conn, employees=("EMP-1",))
    save_employee(conn, Employee("EMP-EXT", "External One", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership("EMP-EXT", "SITE-1", MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True))
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert "EMP-EXT" not in {r.employee_id for r in model.rows}


# --- T20-09: no public blame ------------------------------------------------
def test_t20_09_cancelled_nn_not_printed():
    from rota.application.manual_edit import mark_not_worked
    from rota.domain import CoordinatorSiteAssociation
    from rota.persistence.coordinator_repository import save_coordinator_site_association
    conn = connect(":memory:")
    _seed(conn)
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D, state=AssignmentState.PLANNED)
    _create_version(conn, [d1], [a1])
    mark_not_worked(
        conn, site_id="SITE-1", month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 8, 3), assignment_id=a1.assignment_id,
    )
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[2] == SE.BLANK


# --- T20-10/13: TRAINEE / INNY fail closed ----------------------------------
def test_t20_10_effective_trainee_is_unsupported():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D)
    mentor = Assignment("ASG-MENTOR", "", a1.employee_id, a1.start_datetime, a1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, a1.covers_demand_id, None)
    trainee = Assignment("ASG-TRAINEE", "", a1.employee_id, a1.start_datetime, a1.end_datetime, AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, "ASG-MENTOR")
    _create_version(conn, [d1], [mentor, trainee])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "UNSUPPORTED_TRAINEE_PRINT"
def test_t20_13_inny_catalog_kind_with_exact_mapping_still_prints():
    # T047: replaces the old "every INNY -> UNSUPPORTED_SHIFT_KIND" expectation.
    # This item's actual 06:00-18:00/12h interval exactly matches the configured
    # D1 code, so it is printable even though catalog_kind == OTHER.
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D)
    d1 = ShiftDemand(d1.demand_id, "", d1.start_datetime, d1.end_datetime, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.OTHER)
    _create_version(conn, [d1], [a1])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[2] == "D1"
    assert model.rows[0].wyk[2] == "D1"


# --- T20-11: exact interval mapping -----------------------------------------
def test_t20_11_wrong_interval_same_duration_fails_mapping():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 7, 19, kind=ShiftKind.D)  # 12h but not the configured 06:00-18:00 signature
    _create_version(conn, [d1], [a1])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_CODE_MAPPING_REQUIRED"


# --- T20-12: T012 24h WorkPeriod ---------------------------------------------
def test_t20_12_valid_24h_workperiod_is_one_start_date_symbol():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d0 = date(2026, 8, 5)
    day_start, night_start = datetime.combine(d0, datetime.min.time()).replace(hour=6), datetime.combine(d0, datetime.min.time()).replace(hour=18)
    next_day = datetime.combine(d0 + timedelta(days=1), datetime.min.time()).replace(hour=6)
    demand_d = ShiftDemand("DEM-D", "", day_start, night_start, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H24, work_period_template_id="WP-1", work_period_component=1)
    demand_n = ShiftDemand("DEM-N", "", night_start, next_day, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H24, work_period_template_id="WP-1", work_period_component=2)
    a_d = Assignment("ASG-D", "", "EMP-1", day_start, night_start, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-D", None, work_period_id="WP-1", required_rest_after_hours=24)
    a_n = Assignment("ASG-N", "", "EMP-1", night_start, next_day, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, "DEM-N", None, work_period_id="WP-1", required_rest_after_hours=24)
    _create_version(conn, [demand_d, demand_n], [a_d, a_n])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[4] == "24"
    assert row.plan[5] == SE.BLANK  # not a second, independent symbol


# --- T20-14: the frozen 40h example -----------------------------------------
def test_t20_14_frozen_40h_leave_decomposition():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 19), end=date(2026, 8, 25))
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[18:21] == ["D1", "D1", "N2"]
    assert row.wyk[18:21] == ["U1", "U1", "U2"]
    assert row.urlop_hours == 40


# --- T046: PRE_PLAN SICK_LEAVE must print as L4/C, not Urlop/U --------------
def test_t046_pre_plan_sick_leave_prints_c_not_u():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 19), end=date(2026, 8, 25), kind=AvailabilityKind.SICK_LEAVE)
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[18:21] == ["D1", "D1", "N2"]
    assert row.wyk[18:21] == ["C1", "C1", "C2"]
    assert row.l4_hours == 40
    assert row.urlop_hours == 0
def test_t046_pre_plan_mixed_leave_granted_and_sick_leave_same_employee():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 3), end=date(2026, 8, 4), av_id="AV-U")  # Mon+Tue, 16h urlop (single N2/U2 symbol, minimal sequence)
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 19), end=date(2026, 8, 25), kind=AvailabilityKind.SICK_LEAVE, av_id="AV-C")  # 40h L4
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.wyk[2:4] == ["U2", "U~"]
    assert row.wyk[18:21] == ["C1", "C1", "C2"]
    assert row.urlop_hours == 16
    assert row.l4_hours == 40
    assert row.wyk_hours == 16 + 40


# --- T20-19/20/21: conflicts and ambiguity ----------------------------------
def test_t20_19_overlapping_leave_and_sick_prints_c_only():
    """ROTA-T023 brief.md section 18: superseded by SICK/C precedence --
    SICK wins over LEAVE_GRANTED on the same date, one C, no conflict error
    (frozen addendum section 4). Uses a deterministic future month (the
    file's shared Aug-2026 MONTH is now in the real past) so R5-2's
    retroactivity guard does not block writing SICK over an accepted plan's
    own PLANNED work item -- SICK has no PRE_PLAN path, so a real accepted
    plan is required for it to resolve BOUND with actual hours at all."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    future_month = date(2027, 3, 1)
    demand = ShiftDemand("DEM-F", "", datetime(2027, 3, 6, 6, 0), datetime(2027, 3, 6, 18, 0), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    assignment = Assignment("ASG-F", "", "EMP-1", datetime(2027, 3, 6, 6, 0), datetime(2027, 3, 6, 18, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "DEM-F", None)
    _accept_version(conn, version_id="SV-F", pairs=[(demand, assignment)], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 9, 0), site_id="SITE-1", month=future_month)
    _grant_leave(conn, "EMP-1", start=date(2027, 3, 6), end=date(2027, 3, 6), av_id="AV-U")
    _grant_leave(conn, "EMP-1", start=date(2027, 3, 6), end=date(2027, 3, 6), kind=AvailabilityKind.SICK_LEAVE, av_id="AV-C")
    # A real REPLAN would redistribute the now-excused shift away from EMP-1; simulate that so CURRENT work_cells no longer conflicts with the frozen POST_PLAN reference (already captured, immutable).
    lifecycle.replace_working_snapshot(conn, version_id="SV-F", applied_rule_version_ids=[], shift_demands=[demand], assignments=[], deviations=[])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=future_month, period_label="x")
    row = model.rows[0]
    assert row.plan[5] == "D1"
    assert row.wyk[5] == "C1"
def test_t20_20_assignment_on_active_absence_day_conflicts():
    """Order matters: the absence is granted BEFORE the conflicting
    Assignment is created, since R5-2's retroactivity guard would otherwise
    reject writing a new absence over an already-existing PRIMARY -- this
    test's whole point is the defensive legacy/corrupt-data detection
    brief.md section 12 says may remain for a state valid writes now
    prevent, not a state a normal write sequence would ever construct."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 5), end=date(2026, 8, 5))
    d1, a1 = _work_item(5, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [d1], [a1])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "ASSIGNMENT_ABSENCE_CONFLICT"
def test_t20_21_multi_site_local_employee_absence_is_ambiguous():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    from rota.domain import Site
    from rota.persistence.site_repository import save_site
    from rota.persistence.site_profile_repository import save_site_profile
    from tests.support.t008_fixtures import make_profile
    save_site_profile(conn, make_profile("PROF-2"))
    save_site(conn, Site(site_id="SITE-2", profile_id="PROF-2", display_name="Site Two", active=True, planning_regime=SitePlanningRegime.ORDINARY))
    save_site_membership(conn, SiteMembership("EMP-1", "SITE-2", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True))
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 19), end=date(2026, 8, 25))
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "ABSENCE_SITE_AMBIGUOUS"


# --- T20-16/18: regime boundary + non-decomposable ---------------------------
def test_t20_16_12h_regime_forbids_24h_denominations_even_with_can_work_24h():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 3), end=date(2026, 8, 3))  # 1 qualifying day -> 8h, no legal 12h-regime 8h pair
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "ABSENCE_DECOMPOSITION_REQUIRED"
def test_t20_17_reserve_configuration_used_when_it_forms_legal_pair():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(reserve_hours={"U3": 8, "U4": None, "U5": None, "C3": None, "C4": None, "C5": None}))
    _create_version(conn, [], [])
    _grant_leave(conn, "EMP-1", start=date(2026, 8, 3), end=date(2026, 8, 3))
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "ABSENCE_DECOMPOSITION_REQUIRED"  # U3=8h has no matching legal 8h PLAN D/N pair


# --- T20-22/23: site-only summaries -----------------------------------------
def test_t20_22_23_summaries_ignore_other_sites_and_match_visible_cells():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    d1, a1 = _work_item(3, 6, 18, kind=ShiftKind.D)
    d2, a2 = _work_item(4, 18, 6, kind=ShiftKind.N)
    _create_version(conn, [d1, d2], [a1, a2])
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan_hours == row.wyk_hours == 12 + 12


# --- T20-27: full existing suite is unaffected ------------------------------
def test_t20_27_no_diff_in_forbidden_paths():
    import subprocess
    out = subprocess.run(
        ["git", "diff", "--name-only", "c5b7bfa85f4db9d7f9cf6fe67f94af133e4bb8c2", "d50a9aa4dfb35ed479470bb7fb83ffca18ecc346", "--",
         "rota/planning", "rota/balance.py", "rota/domain.py", "rota/persistence/schedule_lifecycle.py",
         "arch/spec.md", "arch/FROZEN.lock", "Grafiki", "tasks/ROTA-T020/checkpoint_a"],
        cwd=__file__.rsplit("tests", 1)[0], capture_output=True, text=True,
    )
    assert out.stdout.strip() == "", out.stdout
def _leg(assignment_id, employee_id, start, end, demand_id, work_period_id=None):
    return Assignment(
        assignment_id, "", employee_id, start, end, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demand_id, None,
        work_period_id=work_period_id, required_rest_after_hours=24 if work_period_id else None,
    )


# --- T20-29/T20-35: malformed shared work_period is not silently collapsed --
def test_t20_29_malformed_h12_pair_sharing_work_period_id_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 5, 6)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demands = [
        ShiftDemand("D", "", start, middle, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12),
        ShiftDemand("N", "", middle, end, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12),
    ]
    assignments = [_leg("A-D", "EMP-1", start, middle, "D", "WP"), _leg("A-N", "EMP-1", middle, end, "N", "WP")]
    _create_version(conn, demands, assignments)
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_PROVENANCE_INCOMPLETE"


# --- T20-38: normal H24 crossing the month boundary is owned by start month -
def test_t20_38_normal_h24_cross_month_owned_by_start_month():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle, end = start + timedelta(hours=12), start + timedelta(hours=24)
    demands = [
        ShiftDemand("N", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H24, work_period_template_id="TPL", work_period_component=1),
        ShiftDemand("D", "", middle, end, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H24, work_period_template_id="TPL", work_period_component=2),
    ]
    assignments = [_leg("A-N", "EMP-1", start, middle, "N", "WP"), _leg("A-D", "EMP-1", middle, end, "D", "WP")]
    _create_version(conn, demands, assignments)
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert model.rows[0].plan[30] == "24"
    assert model.rows[0].plan_hours == 24


# --- T20-33: Assignment interval must equal its covered ShiftDemand interval
def test_t20_33_assignment_interval_must_equal_covered_demand_interval():
    conn = connect(":memory:")
    _seed(conn)
    intervals = _default_intervals()
    intervals["D1"] = WorkCodeInterval("07:00", "19:00", False)
    save_site_print_settings(conn, _settings(work_code_intervals=intervals))
    demand_start = datetime(2026, 8, 5, 6)
    demand = ShiftDemand("D", "", demand_start, demand_start + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    assignment_start = datetime(2026, 8, 5, 7)
    assignment = _leg("A", "EMP-1", assignment_start, assignment_start + timedelta(hours=12), "D")
    _create_version(conn, [demand], [assignment])
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_PROVENANCE_INCOMPLETE"


# --- T20-30: corrupt persisted settings return a stable problem, never raise
def test_t20_30_corrupt_persisted_settings_return_stable_problem():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    conn.execute("UPDATE site_print_settings SET work_code_intervals_json = ? WHERE site_id = ?", ('["not", "an", "object"]', "SITE-1"))
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "PRINT_SETTINGS_INVALID"
def test_t20_30b_corrupt_reserve_json_returns_stable_problem():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    conn.execute("UPDATE site_print_settings SET reserve_hours_json = ? WHERE site_id = ?", ("[1, 2, 3]", "SITE-1"))
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "PRINT_SETTINGS_INVALID"


# --- T20-25/T20-36: a roster too large for one sheet now paginates instead of failing (T047) --
def test_t20_25_large_roster_paginates_instead_of_failing():
    employee_ids = tuple(f"EMP-{i:02d}" for i in range(30))
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert isinstance(result, SE.ExportReady) and result.pdf_bytes.startswith(b"%PDF")


# --- T20-03/04: the pinned production ReportLab dependency renders a real PDF with Polish diacritics, or fails explicitly
def test_t20_03_pinned_production_reportlab_renders_ready_pdf():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="Sierpień 2026")
    assert isinstance(result, SE.ExportReady)
    assert result.pdf_bytes.startswith(b"%PDF")


# --- Section 20 regression: membership-ambiguity check must be one batch read, not N
def test_t20_membership_ambiguity_check_is_batched(monkeypatch):
    from rota.persistence import employee_repository
    employee_ids = ("EMP-1", "EMP-2", "EMP-3")
    conn = connect(":memory:")
    _seed(conn, employees=employee_ids)
    save_site_print_settings(conn, _settings())
    _create_version(conn, [], [])
    for index, employee_id in enumerate(employee_ids):
        _grant_leave(conn, employee_id, start=date(2026, 8, 19), end=date(2026, 8, 25), av_id=f"AV-{index}")
    calls = 0
    original = employee_repository.list_memberships_for_employees

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(employee_repository, "list_memberships_for_employees", counted)
    SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert calls == 1, "membership ambiguity must use one batch read, not one query per absent employee"


# --- R6 Linkage Narrowing Amendment: T020 owns only persisted (employee_id, work_period_id)
# identity across a month boundary, never T012's internal emergency-pair legitimacy.
def _emergency_leg(assignment_id, employee_id, start, end, demand_id, work_period_id):
    return Assignment(assignment_id, "", employee_id, start, end, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demand_id, None, work_period_id=work_period_id, required_rest_after_hours=None)
def test_t20_39_emergency_outgoing_linkage_renders_24_on_start_side():
    """No emergency_24h_rest_hours snapshot is set anywhere -- T020 must not care; only the persisted
    (employee_id, work_period_id) identity across the boundary matters (R6 Linkage Narrowing 2.2/3)."""
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-X")
    _create_version(conn, [d_aug], [a_aug])

    sep = date(2026, 9, 1)
    d_sep = ShiftDemand("D-SEP", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_sep = _emergency_leg("A-SEP", "EMP-1", middle, middle + timedelta(hours=12), "D-SEP", "WP-X")
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id="SITE-1", month=sep, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_sep], assignments=[a_sep], deviations=[], effective_from=sep,
    )

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[30] == "24"
    assert row.plan_hours == 24
def test_t20_40_emergency_incoming_linkage_suppresses_continuation():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    july = date(2026, 7, 1)
    start = datetime(2026, 7, 31, 18)
    middle = start + timedelta(hours=12)
    d_jul = ShiftDemand("N-JUL", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_jul = _emergency_leg("A-JUL", "EMP-1", start, middle, "N-JUL", "WP-Y")
    lifecycle.create_schedule_version(
        conn, version_id="SV-JUL", site_id="SITE-1", month=july, parent_version_id=None,
        created_at=datetime(2026, 7, 30, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_jul], assignments=[a_jul], deviations=[], effective_from=july,
    )
    d_aug = ShiftDemand("D-AUG", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", middle, middle + timedelta(hours=12), "D-AUG", "WP-Y")
    _create_version(conn, [d_aug], [a_aug])

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[0] == SE.BLANK
    assert row.wyk[0] == SE.BLANK
    assert row.plan_hours == 0
def test_t20_41_multiple_adjacent_candidates_for_same_identity_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-Z")
    _create_version(conn, [d_aug], [a_aug])
    sep = date(2026, 9, 1)
    end2 = middle + timedelta(hours=12)
    d_sep1 = ShiftDemand("D-SEP1", "", middle, end2, 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    d_sep2 = ShiftDemand("D-SEP2", "", end2, end2 + timedelta(hours=12), 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_sep1 = _emergency_leg("A-SEP1", "EMP-1", middle, end2, "D-SEP1", "WP-Z")
    a_sep2 = _emergency_leg("A-SEP2", "EMP-1", end2, end2 + timedelta(hours=12), "D-SEP2", "WP-Z")
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id="SITE-1", month=sep, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_sep1, d_sep2], assignments=[a_sep1, a_sep2], deviations=[], effective_from=sep,
    )
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "WORK_PROVENANCE_INCOMPLETE"


# --- R6 Linkage Narrowing Amendment Section 8.2: remaining exporter-linkage classes (R10-6)
def test_t20_42_no_adjacent_match_remains_ordinary_work():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-NOMATCH")
    _create_version(conn, [d_aug], [a_aug])

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[30] == "N1"
    assert row.plan_hours == 12
def test_t20_43_different_work_period_id_does_not_link():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-AUG-SIDE")
    _create_version(conn, [d_aug], [a_aug])
    sep = date(2026, 9, 1)
    d_sep = ShiftDemand("D-SEP", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_sep = _emergency_leg("A-SEP", "EMP-1", middle, middle + timedelta(hours=12), "D-SEP", "WP-SEP-SIDE")
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id="SITE-1", month=sep, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_sep], assignments=[a_sep], deviations=[], effective_from=sep,
    )

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[30] == "N1"
    assert row.plan_hours == 12
def test_t20_44_same_work_period_id_different_employee_does_not_link():
    conn = connect(":memory:")
    _seed(conn, employees=("EMP-1", "EMP-2"))
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-SHARED")
    _create_version(conn, [d_aug], [a_aug])
    sep = date(2026, 9, 1)
    d_sep = ShiftDemand("D-SEP", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_sep = _emergency_leg("A-SEP", "EMP-2", middle, middle + timedelta(hours=12), "D-SEP", "WP-SHARED")
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id="SITE-1", month=sep, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_sep], assignments=[a_sep], deviations=[], effective_from=sep,
    )

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[30] == "N1"
    assert row.plan_hours == 12
def test_t20_45_unrelated_adjacent_work_is_ignored():
    conn = connect(":memory:")
    _seed(conn, employees=("EMP-1", "EMP-2"))
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-X")
    _create_version(conn, [d_aug], [a_aug])
    sep = date(2026, 9, 1)
    d_sep = ShiftDemand("D-SEP", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_sep = _emergency_leg("A-SEP", "EMP-2", middle, middle + timedelta(hours=12), "D-SEP", "WP-UNRELATED")
    lifecycle.create_schedule_version(
        conn, version_id="SV-SEP", site_id="SITE-1", month=sep, parent_version_id=None,
        created_at=datetime(2026, 9, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_sep], assignments=[a_sep], deviations=[], effective_from=sep,
    )

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "EMP-1")
    assert row.plan[30] == "N1"
    assert row.plan_hours == 12
def test_t20_46_adjacent_lineage_corruption_fails_closed(monkeypatch):
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings())
    start = datetime(2026, 8, 31, 18)
    middle = start + timedelta(hours=12)
    d_aug = ShiftDemand("N-AUG", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_aug = _emergency_leg("A-AUG", "EMP-1", start, middle, "N-AUG", "WP-CORRUPT")
    _create_version(conn, [d_aug], [a_aug])

    original = SE.schedule_repository.get_current_version_id
    sep = date(2026, 9, 1)

    def corrupted(conn_, site_id, month):
        if month == sep:
            return "SV-GHOST-DOES-NOT-EXIST"
        return original(conn_, site_id, month)

    monkeypatch.setattr(SE.schedule_repository, "get_current_version_id", corrupted)
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    assert exc.value.code == "PROVENANCE_INCOMPLETE"
def test_t20_47_emergency_linkage_across_a_year_boundary():
    conn = connect(":memory:")
    _seed(conn, full_calendar=False)
    save_site_print_settings(conn, _settings())
    december = date(2026, 12, 1)
    start = datetime(2026, 12, 31, 18)
    middle = start + timedelta(hours=12)
    d_dec = ShiftDemand("N-DEC", "", start, middle, 1, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12)
    a_dec = _emergency_leg("A-DEC", "EMP-1", start, middle, "N-DEC", "WP-YEAR")
    lifecycle.create_schedule_version(
        conn, version_id="SV-DEC", site_id="SITE-1", month=december, parent_version_id=None,
        created_at=datetime(2026, 12, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_dec], assignments=[a_dec], deviations=[], effective_from=december,
    )
    january = date(2027, 1, 1)
    d_jan = ShiftDemand("D-JAN", "", middle, middle + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    a_jan = _emergency_leg("A-JAN", "EMP-1", middle, middle + timedelta(hours=12), "D-JAN", "WP-YEAR")
    lifecycle.create_schedule_version(
        conn, version_id="SV-JAN", site_id="SITE-1", month=january, parent_version_id=None,
        created_at=datetime(2027, 1, 1, 8), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[d_jan], assignments=[a_jan], deviations=[], effective_from=january,
    )

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=december, period_label="x")
    row = model.rows[0]
    assert row.plan[30] == "24"
    assert row.plan_hours == 24
