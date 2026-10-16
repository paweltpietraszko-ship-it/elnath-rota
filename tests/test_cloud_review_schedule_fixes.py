"""ROTA-CLOUD-REVIEW-FIXES (tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md): targeted
evidence for F1 (manual third night -> LAW Deviation, no 500), F2 (night-streak
history window), F3 (NN date in PDF/Excel projection), F4 (first schedule
from a mid-month day) and F6 (every current violation reaches the month
banner in Polish). Real write paths (HTTP + application) and real readers."""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from api.schedule_validation_messages import describe_violation
from rota.application import plan_ops
from rota.application import schedule_export as SE
from rota.application.assembler import assemble_planning_state
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import append_availability, update_employee, update_membership
from rota.application.schedule_projection import build_schedule_projection
from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind, CalendarDay, Coordinator,
    CoordinatorSiteAssociation, Employee, MembershipKind, ReadinessSource, ReadinessState, ShiftDemand, ShiftKind,
    Site, SiteMembership, SitePlanningRegime, SiteProfile, SiteRuleVersion, RuleCategory, RuleEnforcement,
    RuleResolution, StandardShift,
)
from rota.persistence import schedule_lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header
from rota.persistence.site_memory import list_coordinator_actions
from rota.persistence.site_repository import SitePrintSettings, WorkCodeInterval, save_site_print_settings
from rota.planning.validator import validate
from rota.planning.validator_shared import ViolationDetail

COORD = DEV_COORDINATOR_ID
SITE = "SITE-CR"
PROFILE = "PROF-CR"
NAMES = {"E1": "Anna Kowalska", "E2": "Bartek Nowak", "E3": "Celina Wiśniewska", "E4": "Darek Zając", "E5": "Ewa Lis"}
FUTURE = date(2027, 3, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        PROFILE, "Ochrona D/N", True,
        [StandardShift(ShiftKind.D, time(6), time(18), False, 1), StandardShift(ShiftKind.N, time(18), time(6), True, 1)],
        True, False, False, False, 1, 72,
    )


def _calendar(conn, month: date) -> None:
    for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, day), False))


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Koordynator", True), site_profile=_profile(),
        site=Site(SITE, PROFILE, "Obiekt", True, planning_regime=SitePlanningRegime.OCHRONA),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    for employee_id, name in NAMES.items():
        update_employee(connection, coordinator_id=COORD, site_id=SITE,
                        employee=Employee(employee_id, name, date(2020, 1, 1), None, False))
        update_membership(connection, coordinator_id=COORD, site_id=SITE, membership=_local(employee_id))
    try:
        yield connection
    finally:
        connection.close()


def _local(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def _demand(kind: ShiftKind, d: date, version: str = "V0") -> ShiftDemand:
    start = datetime.combine(d, time(6) if kind == ShiftKind.D else time(18))
    return ShiftDemand(f"{kind.value}-{d.isoformat()}", version, start, start + timedelta(hours=12), 1, shift_kind=kind)


def _assignment(demand: ShiftDemand, employee_id: str) -> Assignment:
    return Assignment(
        f"A-{demand.demand_id}", demand.schedule_version_id, employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )


def _version(conn, month: date, plan: list[tuple[ShiftKind, int, str]], *, version_id: str = "V0",
             effective_from: date | None = None) -> list[Assignment]:
    demands, assignments = [], []
    for kind, day, employee_id in plan:
        demand = _demand(kind, date(month.year, month.month, day), version_id)
        demands.append(demand)
        assignments.append(_assignment(demand, employee_id))
    schedule_lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=SITE, month=month, parent_version_id=None,
        created_at=datetime(2026, 1, 1, 8), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=demands, assignments=assignments, deviations=[], effective_from=effective_from or month,
    )
    return assignments


def _assignment_in(a: dict) -> dict:
    keys = ("assignment_id", "schedule_version_id", "employee_id", "start_datetime", "end_datetime", "role", "state",
            "frozen", "covers_demand_id", "mentor_primary_assignment_id", "operational_code", "work_period_id",
            "required_rest_after_hours", "manual_work_role_id", "manual_work_role_name")
    return {k: a[k] for k in keys if k in a}


def _month_url(month: date, suffix: str = "") -> str:
    return f"/api/workspace/sites/{SITE}/schedule/{month.isoformat()}{suffix}"


# --- F6 / A1: every current violation reaches the existing banner -----------------------------

def test_f6_new_sick_leave_on_accepted_schedule_is_shown_and_disappears_after_fix(conn, client):
    _version(conn, FUTURE, [(ShiftKind.D, 20, "E1"), (ShiftKind.D, 21, "E2"), (ShiftKind.N, 21, "E3")])
    _calendar(conn, FUTURE)
    version_before = get_current_version_id(conn, SITE, FUTURE)
    actions_before = len(list_coordinator_actions(conn, site_id=SITE))

    append_availability(conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-L4", employee_id="E1",
                        kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 19), end_date=date(2027, 3, 22), active=True)
    body = client.get(_month_url(FUTURE)).json()
    expected = "Naruszenie: zwolnienie lekarskie — Anna Kowalska; 20.03."
    assert expected in body["warnings"], body["warnings"]
    for warning in (w for w in body["warnings"] if w.startswith("Naruszenie:")):
        assert "SICK_LEAVE" not in warning and "A-D-" not in warning and "E1" not in warning

    # GET never writes: same version, no new deviation, no new coordinator action.
    assert get_current_version_id(conn, SITE, FUTURE) == version_before
    assert get_schedule_snapshot(conn, version_before).deviations == []
    assert len(list_coordinator_actions(conn, site_id=SITE)) == actions_before + 1  # only the L4 write itself

    append_availability(conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-L4", employee_id="E1",
                        kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 19), end_date=date(2027, 3, 22), active=False)
    assert expected not in client.get(_month_url(FUTURE)).json()["warnings"]


@pytest.mark.parametrize("kind, label", [
    (AvailabilityKind.LEAVE_GRANTED, "urlop"),
    (AvailabilityKind.UNAVAILABLE_24H, "niedostępność"),
    (AvailabilityKind.DAY_SHIFT_OFF, "dzień wolny"),
])
def test_f6_other_availability_kinds_are_not_filtered(conn, client, kind, label):
    _version(conn, FUTURE, [(ShiftKind.D, 20, "E1")])
    _calendar(conn, FUTURE)
    append_availability(conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-X", employee_id="E1",
                        kind=kind, start_date=date(2027, 3, 20), end_date=date(2027, 3, 20), active=True)
    warnings = client.get(_month_url(FUTURE)).json()["warnings"]
    assert any(w.startswith(f"Naruszenie: {label} — Anna Kowalska") and "20.03" in w for w in warnings), warnings


def test_f6_non_availability_violation_and_concurrent_violations_all_shown(conn, client):
    _version(conn, FUTURE, [(ShiftKind.N, 21, "E2"), (ShiftKind.D, 20, "E1")])
    _calendar(conn, FUTURE)
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E2", NAMES["E2"], date(2020, 1, 1), None, True))
    append_availability(conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-L4", employee_id="E1",
                        kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 20), end_date=date(2027, 3, 20), active=True)
    warnings = client.get(_month_url(FUTURE)).json()["warnings"]
    assert "Naruszenie: tylko dniówka — Bartek Nowak; 21.03." in warnings, warnings
    assert "Naruszenie: zwolnienie lekarskie — Anna Kowalska; 20.03." in warnings, warnings


def test_f6_final_month_still_shows_new_violation(conn, client):
    from rota.application.lifecycle_ops import finalize

    _version(conn, FUTURE, [(ShiftKind.D, 20, "E1")])
    _calendar(conn, FUTURE)
    finalize(conn, site_id=SITE, month=FUTURE, coordinator_id=COORD, acknowledged_deviation_ids=set())
    assert get_schedule_version_header(conn, get_current_version_id(conn, SITE, FUTURE)).status.value.startswith("FINAL")
    append_availability(conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-L4", employee_id="E1",
                        kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 20), end_date=date(2027, 3, 20), active=True)
    assert "Naruszenie: zwolnienie lekarskie — Anna Kowalska; 20.03." in client.get(_month_url(FUTURE)).json()["warnings"]


def _rule(rule_version_id: str, description: str | None) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id="R", site_id=SITE, category=RuleCategory.CLIENT_REQUIREMENT,
        rule_kind=None, structured_parameters=None, enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED, effective_from=date(2027, 1, 1), effective_to=None,
        changed_at=datetime(2027, 1, 1), changed_by=COORD, supersedes_rule_version_id=None,
        description=description, source=None, reason=None,
    )


def test_f6_formatter_never_drops_hides_or_invents():
    a = _assignment(_demand(ShiftKind.N, date(2027, 3, 5)), "E1")
    d = _demand(ShiftKind.D, date(2027, 3, 6))
    lookups = dict(
        labels={"COVERAGE-01": "brak pokrycia zmiany", "SICK_LEAVE-01": "zwolnienie lekarskie"},
        assignments_by_id={a.assignment_id: a}, demands_by_id={d.demand_id: d},
        employees_by_id={"E1": Employee("E1", "Anna Kowalska", date(2020, 1, 1), None, False)},
        site_rules_by_id={"RV-1": _rule("RV-1", "Bez nocek w weekend"), "RV-2": _rule("RV-2", None)},
    )
    assert describe_violation(ViolationDetail("COVERAGE-01", (), "x", demand_ids=(d.demand_id,)), **lookups) == \
        "Naruszenie: brak pokrycia zmiany — 06.03 06:00–18:00."
    assert describe_violation(ViolationDetail("RV-1", (a.assignment_id,), "x"), **lookups) == \
        "Naruszenie: reguła obiektu „Bez nocek w weekend” — Anna Kowalska; 05.03."
    assert describe_violation(ViolationDetail("RV-2", (), "x"), **lookups) == \
        "Naruszenie: reguła obiektu — brak szczegółów osoby i daty."
    unknown = describe_violation(ViolationDetail("NEW-RULE-99", (a.assignment_id, "GONE"), "eng text"), **lookups)
    assert unknown == "Naruszenie: naruszenie reguły planowania — Anna Kowalska; 05.03; część szczegółów niedostępna."
    assert "NEW-RULE-99" not in unknown and "eng text" not in unknown


# --- F1 / A4: deliberate manual N/N/N is a LAW Deviation, never a 500 -------------------------

def test_f1_manual_third_night_is_saved_as_law_deviation_with_polish_label(conn, client):
    _calendar(conn, FUTURE)
    assignments = _version(conn, FUTURE, [(ShiftKind.N, 10, "E1"), (ShiftKind.N, 11, "E1"), (ShiftKind.N, 12, "E2")])
    actions_before = len(list_coordinator_actions(conn, site_id=SITE))
    third = replace(assignments[2], employee_id="E1")
    payload = {"upsert_assignments": [_assignment_in({
        **third.__dict__, "start_datetime": third.start_datetime.isoformat(), "end_datetime": third.end_datetime.isoformat(),
        "role": third.role.value, "state": third.state.value,
    })], "note": "świadoma decyzja koordynatora"}
    resp = client.post(_month_url(FUTURE, "/manual-correction"), json=payload)
    assert resp.status_code == 200, resp.text
    deviations = {d["source_reference"]: d for d in resp.json()["deviations"]}
    assert deviations["NIGHT-STREAK-01"]["category"] == "LAW"
    assert deviations["NIGHT-STREAK-01"]["label"] == "trzecia nocka pod rząd"
    assert deviations["NIGHT-STREAK-01"]["acknowledged"] is False
    assert len(list_coordinator_actions(conn, site_id=SITE)) == actions_before + 1


# --- F2 / A5: night-streak history window ---------------------------------------------------

def test_f2_old_triple_elsewhere_does_not_touch_another_month_but_boundary_triple_does(conn, client):
    june, september, october = date(2027, 6, 1), date(2027, 9, 1), date(2027, 10, 1)
    # Legal manual exception on the same object (F1 path) leaves a June N/N/N in history.
    _calendar(conn, june)
    june_assignments = _version(conn, june, [(ShiftKind.N, 10, "E1"), (ShiftKind.N, 11, "E1"), (ShiftKind.N, 12, "E2")],
                                version_id="V-JUNE")
    third = replace(june_assignments[2], employee_id="E1")
    resp = client.post(_month_url(june, "/manual-correction"), json={"upsert_assignments": [_assignment_in({
        **third.__dict__, "start_datetime": third.start_datetime.isoformat(), "end_datetime": third.end_datetime.isoformat(),
        "role": third.role.value, "state": third.state.value,
    })], "note": "świadomy wyjątek"})
    assert resp.status_code == 200, resp.text
    # September ends with N on 29 and 30 for E1.
    _version(conn, september, [(ShiftKind.N, 29, "E1"), (ShiftKind.N, 30, "E1")], version_id="V-SEPT")

    state, _ = assemble_planning_state(conn, site_id=SITE, month=october)
    d10 = _assignment(replace(_demand(ShiftKind.D, date(2027, 10, 10)), schedule_version_id="V-OCT"), "E2")
    report = validate(replace(state, shift_demands=(*state.shift_demands, _demand(ShiftKind.D, date(2027, 10, 10), "V-OCT"))),
                      [d10])
    assert not [v for v in report.violation_details if v.rule == "NIGHT-STREAK-01"], report.violation_details

    n1 = _assignment(_demand(ShiftKind.N, date(2027, 10, 1), "V-OCT"), "E1")
    report = validate(replace(state, shift_demands=(*state.shift_demands, _demand(ShiftKind.N, date(2027, 10, 1), "V-OCT"))),
                      [n1])
    streaks = [v for v in report.violation_details if v.rule == "NIGHT-STREAK-01"]
    assert streaks and n1.assignment_id in streaks[0].assignment_ids


# --- F3 / A3: NN effective from the service's own day ----------------------------------------

def _print_settings() -> SitePrintSettings:
    intervals = {k: None for k in ("D1", "D2", "D3", "D4", "D5", "N1", "N2", "N3", "N4", "N5")}
    intervals["D1"] = WorkCodeInterval("06:00", "18:00", False)
    intervals["N1"] = WorkCodeInterval("18:00", "06:00", True)
    return SitePrintSettings(
        site_id=SITE, company_print_name="FIRMA", site_print_name="OBIEKT", base_regime="12h",
        work_code_intervals=intervals, reserve_hours={k: None for k in ("U3", "U4", "U5", "C3", "C4", "C5")},
    )


@pytest.mark.parametrize("service_day", ["previous_month", "yesterday"])
def test_f3_not_worked_disappears_from_pdf_and_excel_projection(conn, client, service_day):
    today = date.today()
    if service_day == "previous_month":
        first_of_this = today.replace(day=1)
        month = (first_of_this - timedelta(days=1)).replace(day=1)
        day = 10
    else:
        yesterday = today - timedelta(days=1)
        month, day = yesterday.replace(day=1), yesterday.day
    other = 1 if day != 1 else 2
    _calendar(conn, month)
    save_site_print_settings(conn, _print_settings())
    assignments = _version(conn, month, [(ShiftKind.D, other, "E1"), (ShiftKind.D, day, "E1")],
                           effective_from=month - timedelta(days=5))
    target = assignments[1]

    resp = client.post(_month_url(month, "/manual-correction/mark-not-worked"), json={"assignment_id": target.assignment_id})
    assert resp.status_code == 200, resp.text
    child = get_schedule_version_header(conn, resp.json()["version_id"])
    assert child.effective_from == date(month.year, month.month, day)
    parent_row = next(a for a in get_schedule_snapshot(conn, "V0").assignments if a.assignment_id == target.assignment_id)
    assert parent_row.state == AssignmentState.PLANNED  # history untouched

    for model in (SE._assemble_export_model(conn, site_id=SITE, month=month, period_label="x"),
                  build_schedule_projection(conn, site_id=SITE, month=month, period_label="x")):
        row = next(r for r in model.rows if r.employee_id == "E1")
        assert row.wyk[day - 1] != "D1", row.wyk
        assert row.wyk[other - 1] == "D1"
        assert row.wyk_hours == 12


# --- F4 / A6: first schedule from a mid-month day ---------------------------------------------

def _plan_and_accept(client, month: date, effective_from: date) -> list[dict]:
    resp = client.post(_month_url(month, "/plan"), json={"effective_from": effective_from.isoformat()})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "FEASIBLE", body
    candidate = body["candidates"][0]
    resp = client.post(_month_url(month, "/select-candidate"), json={"candidate": [_assignment_in(a) for a in candidate]})
    assert resp.status_code == 204, resp.text
    return candidate


def _no_three_night_streak(assignments: list[dict]) -> bool:
    nights: dict[str, set] = {}
    for a in assignments:
        start = datetime.fromisoformat(a["start_datetime"])
        if start.hour == 18:
            nights.setdefault(a["employee_id"], set()).add(start.date())
    return not any(d + timedelta(days=1) in ds and d + timedelta(days=2) in ds for ds in nights.values() for d in ds)


def test_f4_first_plan_from_the_10th_plans_nothing_before_it(conn, client):
    _calendar(conn, FUTURE)
    effective_from = date(2027, 3, 10)
    candidate = _plan_and_accept(client, FUTURE, effective_from)
    assert all(datetime.fromisoformat(a["start_datetime"]).date() >= effective_from for a in candidate)
    assert _no_three_night_streak(candidate)  # A4 negative control: the automat never builds N/N/N

    body = client.get(_month_url(FUTURE)).json()
    starts = [datetime.fromisoformat(d["start_datetime"]).date() for d in body["demands"]]
    assert min(starts) == effective_from and date(2027, 3, 9) not in starts  # the 9th's night is excluded too
    assert all(datetime.fromisoformat(a["start_datetime"]).date() >= effective_from for a in body["assignments"])
    assert not [w for w in body["warnings"] if "brak pokrycia" in w]
    assert body["current_version"]["effective_from"] == effective_from.isoformat()


@pytest.mark.parametrize("day", [1, 31])
def test_f4_boundaries_first_and_last_day(conn, client, day):
    _calendar(conn, FUTURE)
    effective_from = date(2027, 3, day)
    candidate = _plan_and_accept(client, FUTURE, effective_from)
    days = {datetime.fromisoformat(a["start_datetime"]).date() for a in candidate}
    assert min(days) == effective_from
    assert len(days) == (31 if day == 1 else 1)


def test_f4_application_path_used_by_excel_honours_the_same_bound(conn):
    _calendar(conn, FUTURE)
    effective_from = date(2027, 3, 20)
    result = plan_ops.plan_month(conn, site_id=SITE, month=FUTURE, coordinator_id=COORD, effective_from=effective_from)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    assert all(a.start_datetime.date() >= effective_from for a in candidate)
    version = plan_ops.select_candidate(conn, site_id=SITE, month=FUTURE, candidate=list(candidate), coordinator_id=COORD)
    snapshot = get_schedule_snapshot(conn, version.version_id)
    assert all(d.start_datetime.date() >= effective_from for d in snapshot.shift_demands)
    assert version.effective_from == effective_from
