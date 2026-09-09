"""ROTA-T041 Checkpoint B (brief.md section 5): SICK_LEAVE known before the
first PLAN (OWNER-T041-02, AUDIT-1 C-02) and a fresh WORKING after a
material catalog change (OWNER-T041-03, AUDIT-1 C-04). Minimal vertical
matrix only -- lower-layer absence-reference/lifecycle contracts are not
re-copied here (see tests/test_t023.py, tests/test_t031_schedule_api.py)."""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application.durable_inputs import append_availability, update_site_profile
from rota.application import plan_ops
from rota.application.plan_ops import plan_month
from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_errors import DuplicateScheduleVersionId
from rota.persistence.schedule_lifecycle import finalize_schedule_version
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.application.errors import ScheduleVersionNotWorking
from rota.planning.absence import DailyAbsenceFact, DetailedDailyAbsenceFact, canonical_daily_hours, canonical_site_absence_days

SITE = "SITE-B41"
COORDINATOR = "COORD-B41"
MONTH = date(2027, 6, 1)


def _first_weekday_on_or_after(start: date, target_weekday: int) -> date:
    return start + timedelta(days=(target_weekday - start.weekday()) % 7)


MONDAY = _first_weekday_on_or_after(MONTH, 0)
SATURDAY = MONDAY + timedelta(days=5)  # same week as MONDAY, always after it


def _empty_profile(profile_id: str = "PROF-B41") -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name="B41", active=True, standard_shifts=[],
        day_only_blocks_n=False, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=0,
        rolling_7d_decision_threshold_hours=999,
    )


def _seed_minimal(conn, *, profile: SiteProfile | None = None) -> None:
    save_site_profile(conn, profile or _empty_profile())
    save_site(conn, Site(SITE, (profile or _empty_profile()).profile_id, "B41 Site", True, planning_regime=SitePlanningRegime.ORDINARY))
    save_coordinator(conn, Coordinator(COORDINATOR, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(COORDINATOR, SITE, True))


def _employee(conn, employee_id: str, *, kind: MembershipKind = MembershipKind.LOCAL) -> None:
    save_employee(conn, Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(employee_id, SITE, kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))


def _seed_month_calendar(conn, month: date, *, holidays: tuple[date, ...] = ()) -> None:
    last_day = calendar.monthrange(month.year, month.month)[1]
    for day in range(1, last_day + 1):
        d = date(month.year, month.month, day)
        save_calendar_day(conn, CalendarDay(d, d in holidays))


def _setup(tmp_path, db_name: str = "rota.db", *, profile: SiteProfile | None = None):
    conn = connect(str(tmp_path / db_name))
    _seed_minimal(conn, profile=profile)
    return conn


def _sick(conn, employee_id: str, start_date: date, end_date: date, *, availability_id: str | None = None):
    return append_availability(
        conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id=availability_id or f"AV-{employee_id}-{start_date}",
        employee_id=employee_id, kind=AvailabilityKind.SICK_LEAVE, start_date=start_date, end_date=end_date, active=True,
    )


# --- 5.1: SICK_LEAVE before first PLAN --------------------------------------


def test_t41_b01_sick_ordinary_monday_before_first_plan_is_8h(tmp_path):
    conn = _setup(tmp_path)
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH)
    record = _sick(conn, "A", MONDAY, MONDAY)
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "PRE_PLAN_LEAVE"
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 8


def test_t41_b02_sick_weekend_before_first_plan_is_0h(tmp_path):
    conn = _setup(tmp_path)
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH)
    sunday = SATURDAY + timedelta(days=1)
    record = _sick(conn, "A", SATURDAY, SATURDAY)
    assert get_absence_reference_snapshot(conn, record.availability_version_id).days[0].hours == 0
    record2 = _sick(conn, "A", sunday, sunday, availability_id="AV-A-sun")
    assert get_absence_reference_snapshot(conn, record2.availability_version_id).days[0].hours == 0


def test_t41_b03_sick_weekday_holiday_before_first_plan_is_0h(tmp_path):
    conn = _setup(tmp_path)
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH, holidays=(MONDAY,))
    record = _sick(conn, "A", MONDAY, MONDAY)
    assert get_absence_reference_snapshot(conn, record.availability_version_id).days[0].hours == 0


def test_t41_b04_sick_multiday_range_sums_per_day_rule(tmp_path):
    conn = _setup(tmp_path)
    _employee(conn, "A")
    tuesday = MONDAY + timedelta(days=1)
    _seed_month_calendar(conn, MONTH, holidays=(tuesday,))
    end = SATURDAY  # Mon(workday) Tue(holiday) Wed..Fri(workdays) Sat(weekend)
    record = _sick(conn, "A", MONDAY, end)
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    by_date = {d.the_date: d.hours for d in snapshot.days}
    assert by_date[MONDAY] == 8
    assert by_date[tuesday] == 0
    assert by_date[SATURDAY] == 0
    workdays_between = [MONDAY + timedelta(days=i) for i in range(1, (end - MONDAY).days) if MONDAY + timedelta(days=i) != tuesday]
    assert all(by_date[d] == 8 for d in workdays_between)
    assert sum(by_date.values()) == 8 * (1 + len(workdays_between))


def test_t41_b05_known_sick_before_first_plan_does_not_500(tmp_path):
    conn = _setup(tmp_path, profile=_empty_profile())
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH)
    save_coordinator(conn, Coordinator(DEV_COORDINATOR_ID, "Dev Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(DEV_COORDINATOR_ID, SITE, True))
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/workspace/employees/A/availability",
            json={"site_id": SITE, "availability_id": "AV-A-SICK", "kind": "SICK_LEAVE",
                  "start_date": MONDAY.isoformat(), "end_date": MONDAY.isoformat()},
        )
        assert resp.status_code == 204
        resp = client.post(
            f"/api/workspace/sites/{SITE}/schedule/{MONTH.isoformat()}/plan",
            json={"effective_from": MONTH.isoformat()},
        )
        assert resp.status_code != 500
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_t41_b06_sick_after_accepted_plan_uses_scheduled_hours(tmp_path):
    """Regression: T041 only fixes the no-accepted-plan gap; a date already
    covered by an accepted PRIMARY period is unaffected (rota/planning
    absence.py::_resolve_from_accepted_periods, untouched by this task)."""
    from rota.persistence import schedule_lifecycle as lifecycle
    from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftDemand
    from rota.site_memory_types import ActionSourceKind, CoordinatorActionKind
    from rota.persistence import site_memory

    conn = _setup(tmp_path)
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH)
    version_id = "SV-1"
    demand = ShiftDemand("D-1", version_id, datetime.combine(MONDAY, time(5, 0)), datetime.combine(MONDAY, time(17, 0)), 1)
    assignment = Assignment(
        "A-1", version_id, "A", demand.start_datetime, demand.end_datetime, AssignmentRole.PRIMARY,
        AssignmentState.PLANNED, True, demand.demand_id, None,
    )
    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=SITE, month=MONTH, parent_version_id=None,
        created_at=datetime(2020, 1, 1), created_by=COORDINATOR, applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[assignment], deviations=[], effective_from=MONTH,
    )
    site_memory.record_coordinator_action_no_commit(
        conn, action_kind=CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED, origin_site_id=SITE,
        affected_site_ids=[SITE], coordinator_id=COORDINATOR, recorded_at=datetime(2020, 1, 1, 9, 0),
        effective_from=MONTH, month=MONTH, schedule_version_id=version_id,
        affected_entities=[], before_state=None, after_state=None, note=None,
        source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=version_id, responds_to_decision_required_id=None,
    )
    conn.commit()
    record = _sick(conn, "A", MONDAY, MONDAY)
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert snapshot.days[0].hours == 12  # real scheduled hours, not the 8h pre-plan default


def test_t41_b07_sick_over_leave_precedence_and_read_after_restart(tmp_path):
    """Regression: shared SICK-over-LEAVE_GRANTED precedence (rota.planning.
    absence._winning_facts, untouched by T041) and that a captured reference
    survives a fresh connection to the same DB."""
    sick = DailyAbsenceFact(MONDAY, AvailabilityKind.SICK_LEAVE, "PRE_PLAN_LEAVE", "BOUND", 8)
    leave = DailyAbsenceFact(MONDAY, AvailabilityKind.LEAVE_GRANTED, "PRE_PLAN_LEAVE", "BOUND", 8)
    assert canonical_daily_hours([leave, sick])[MONDAY] == 8  # SICK wins regardless of list order
    assert canonical_daily_hours([sick, leave])[MONDAY] == 8

    db_path = tmp_path / "restart.db"
    conn = connect(str(db_path))
    _seed_minimal(conn)
    _employee(conn, "A")
    _seed_month_calendar(conn, MONTH)
    record = _sick(conn, "A", MONDAY, MONDAY)
    before = get_absence_reference_snapshot(conn, record.availability_version_id)
    conn.close()
    reopened = connect(str(db_path))
    after = get_absence_reference_snapshot(reopened, record.availability_version_id)
    assert after == before


def test_t41_b08_export_recognizes_pre_plan_sick_as_sick():
    """Regression: schedule_export.py's SICK/LEAVE letter is keyed off
    DetailedDailyAbsenceFact.kind, not source_mode -- a PRE_PLAN_LEAVE SICK
    fact is not misclassified as LEAVE_GRANTED for the printout."""
    fact = DetailedDailyAbsenceFact(MONDAY, AvailabilityKind.SICK_LEAVE, "PRE_PLAN_LEAVE", "BOUND", 8, ())
    days = canonical_site_absence_days([fact], range_start=MONDAY, range_end=MONDAY, site_id=SITE)
    assert len(days) == 1
    assert days[0].kind == AvailabilityKind.SICK_LEAVE
    assert days[0].source_mode == "PRE_PLAN_LEAVE"
    assert days[0].canonical_hours == 8


# --- 5.2: fresh WORKING after catalog change --------------------------------


def _dn_profile(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name="B41-DN", active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1, required_rest_hours=11),
        ],
        day_only_blocks_n=False, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=0,
        rolling_7d_decision_threshold_hours=999,
    )


def test_t41_b09_first_plan_empty_catalog_creates_empty_working(tmp_path):
    conn = _setup(tmp_path)
    _seed_month_calendar(conn, MONTH)
    result = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)
    assert result.status != "TECHNICAL_ERROR"
    # ROTA-T057: PLAN alone no longer creates a ScheduleVersion (T57-01) --
    # accept the candidate first to get one worth inspecting.
    version = plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORDINATOR)
    snapshot = get_schedule_snapshot(conn, version.version_id)
    assert not snapshot.shift_demands


def _run_catalog_change_scenario(tmp_path):
    profile = _empty_profile("PROF-B10")
    conn = _setup(tmp_path, profile=profile)
    _employee(conn, "A")
    _employee(conn, "B")
    _seed_month_calendar(conn, MONTH)
    first = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)
    # ROTA-T057: accept the first candidate so there is a real current
    # version for the profile-change PLAN below to recompute against.
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=first.candidates[0], coordinator_id=COORDINATOR)
    old_version_id = get_current_version_id(conn, SITE, MONTH)

    update_site_profile(conn, coordinator_id=COORDINATOR, site_id=SITE, profile=_dn_profile("PROF-B10"))
    result = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR)

    new_version_id = get_current_version_id(conn, SITE, MONTH)
    assert new_version_id != old_version_id
    new_snapshot = get_schedule_snapshot(conn, new_version_id)
    days_in_month = calendar.monthrange(MONTH.year, MONTH.month)[1]
    assert len(new_snapshot.shift_demands) == days_in_month
    assert result.status != "TECHNICAL_ERROR"
    return conn, old_version_id, new_version_id


def test_t41_b10_catalog_save_then_plan_creates_fresh_working(tmp_path):
    _run_catalog_change_scenario(tmp_path)


def test_t41_b11_old_working_untouched_in_history(tmp_path):
    conn, old_version_id, _ = _run_catalog_change_scenario(tmp_path)
    old_snapshot = get_schedule_snapshot(conn, old_version_id)
    assert not old_snapshot.shift_demands  # the original empty-catalog WORKING, never mutated


def test_t41_b12_replan_without_material_change_does_not_create_new_version(tmp_path, monkeypatch):
    profile = _dn_profile("PROF-B12")
    conn = _setup(tmp_path, profile=profile)
    _employee(conn, "A")
    # ROTA-T058 (owner-authorized fixture fix, 2026-09-08): a single employee
    # covering every day of the month now genuinely trips the new HARD
    # max-two-consecutive-PRIMARY-shifts rule -- this test is about replan
    # version-identity, not staffing tightness, so a second employee restores
    # real slack.
    _employee(conn, "B")
    _seed_month_calendar(conn, MONTH)
    first = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=first.candidates[0], coordinator_id=COORDINATOR)
    version_id = get_current_version_id(conn, SITE, MONTH)
    # ROTA-T057 follow-up (2026-09-07): Przelicz Plan now also requires the
    # grafik to already be live (OWNER_RULING point 3) -- MONTH is future,
    # so "now" is frozen to just after it starts for this recompute.
    fixed_now = datetime(MONTH.year, MONTH.month, MONTH.day, 12, 0, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(plan_ops, "datetime", _FixedDateTime)
    plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR)
    assert get_current_version_id(conn, SITE, MONTH) == version_id


def test_t41_b13_final_current_still_rejects_plan(tmp_path):
    conn = _setup(tmp_path)
    _seed_month_calendar(conn, MONTH)
    first = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=first.candidates[0], coordinator_id=COORDINATOR)
    version_id = get_current_version_id(conn, SITE, MONTH)
    finalize_schedule_version(conn, version_id=version_id)
    with pytest.raises(ScheduleVersionNotWorking):
        plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR)
    assert get_current_version_id(conn, SITE, MONTH) == version_id


def test_t41_b14_error_path_leaves_current_pointer_untouched(tmp_path, monkeypatch):
    profile = _empty_profile("PROF-B14")
    conn = _setup(tmp_path, profile=profile)
    _seed_month_calendar(conn, MONTH)
    first = plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)
    accepted = plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=first.candidates[0], coordinator_id=COORDINATOR)
    version_id = get_current_version_id(conn, SITE, MONTH)
    original_snapshot = get_schedule_snapshot(conn, version_id)

    # ROTA-T057: select_candidate's own action record already consumed a
    # uuid4() call with a real random value -- freeze uuid4 to REPRODUCE the
    # just-accepted version's id only now, so the second plan_month below
    # collides with it, without also colliding with the action record
    # already inserted above (same shared `uuid` module every caller uses).
    fixed = uuid.UUID(accepted.version_id.removeprefix("SV-"))
    monkeypatch.setattr(plan_ops.uuid, "uuid4", lambda: fixed)

    update_site_profile(conn, coordinator_id=COORDINATOR, site_id=SITE, profile=_dn_profile("PROF-B14"))
    with pytest.raises(DuplicateScheduleVersionId):
        plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR)

    assert get_current_version_id(conn, SITE, MONTH) == version_id
    assert get_schedule_snapshot(conn, version_id).shift_demands == original_snapshot.shift_demands
