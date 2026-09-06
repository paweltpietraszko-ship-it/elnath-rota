"""ROTA-T031 (tasks/ROTA-T031/brief.md): vertical API->application->
persistence tests for the Planowanie miesiaca screen. Backend groups
T31-01..T31-09 from the acceptance matrix; T31-10 (E2E) lives in
frontend/e2e, T31-11 (build/regression) in delivery."""
from __future__ import annotations

from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from api.main import app
from api.routers.schedule import _deviation_label
from rota.application import bootstrap
from rota.domain import (
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)
MONTH_STR = MONTH.isoformat()


def _strip_display_name(assignment: dict) -> dict:
    """AssignmentOut carries employee_display_name for rendering;
    AssignmentIn (extra="forbid") only accepts the fields select-candidate
    actually needs -- a real client would never echo the display name back."""
    return {k: v for k, v in assignment.items() if k != "employee_display_name"}


@pytest.fixture
def seeded():
    connection = connect(":memory:")
    pstate = seed_real_object(connection, case_id="t031-api", month=MONTH, seed=900, coordinator_id=DEV_COORDINATOR_ID)
    try:
        yield connection, pstate.site.site_id
    finally:
        connection.close()


@pytest.fixture
def conn(seeded):
    return seeded[0]


@pytest.fixture
def site_id(seeded):
    return seeded[1]


@pytest.fixture
def client(conn):
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


# T31-01: GET before any PLAN -- no current_version, no content.
def test_get_month_before_plan_has_no_current_version(client, site_id):
    resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_version"] is None
    assert body["assignments"] == []
    assert body["demands"] == []


# T31-02: PLAN with no current_version requires effective_from.
def test_plan_without_effective_from_rejected_when_no_current_version(client, site_id):
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={})
    assert resp.status_code == 400


def test_plan_creates_first_version_and_returns_candidates(client, site_id):
    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FEASIBLE"
    assert len(body["candidates"]) >= 1
    assert body["candidates"][0][0]["employee_display_name"]


# T31-03 (ROTA-T057 T57-01, rewritten): after PLAN alone, BEFORE accepting
# any candidate, no ScheduleVersion exists at all yet -- current_version
# must stay None. Whether/how GET should also surface the pending preview's
# demands without a current_version is a separate, not-yet-done increment
# (open_month.py phase-awareness); this test only pins down the version
# lifecycle side, which is in scope now.
def test_get_month_after_plan_shows_demands_but_no_assignments_yet(client, site_id):
    client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR})
    resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}")
    body = resp.json()
    assert body["current_version"] is None
    assert body["assignments"] == []


# T31-04: PLAN again (recompute) on an existing WORKING version does not
# create a second version. ROTA-T057: "an existing WORKING version" now
# requires accepting the first candidate first -- PLAN alone never creates
# one to recompute against.
def test_plan_again_on_existing_working_recomputes_without_new_version(client, site_id):
    first = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR}).json()
    candidate = [_strip_display_name(a) for a in first["candidates"][0]]
    client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate", json={"candidate": candidate})
    view_before = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    version_id_before = view_before["current_version"]["version_id"]

    second = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={}).json()
    view_after = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()

    assert view_after["current_version"]["version_id"] == version_id_before
    assert second["status"] == "FEASIBLE"
    assert first["status"] == "FEASIBLE"


# T31-05: select-candidate persists the chosen candidate onto the current WORKING version.
def test_select_candidate_persists_then_get_shows_assignments(client, site_id):
    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    candidate = [_strip_display_name(a) for a in plan_result["candidates"][0]]

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate", json={"candidate": candidate},
    )
    assert resp.status_code == 204

    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert len(view["assignments"]) == len(candidate)
    assert {a["assignment_id"] for a in view["assignments"]} == {a["assignment_id"] for a in candidate}


def test_select_candidate_rejects_invalid_candidate_with_no_state_change(client, site_id):
    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    candidate = [_strip_display_name(a) for a in plan_result["candidates"][0]]
    broken = [dict(candidate[0], employee_id="NO-SUCH-EMPLOYEE")] + candidate[1:]

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate", json={"candidate": broken},
    )
    assert resp.status_code == 400

    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view["assignments"] == []


# T31-06: REPLAN after a selection creates a child version and returns fresh candidates.
def test_replan_after_select_returns_new_candidates(client, site_id):
    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
        json={"candidate": [_strip_display_name(a) for a in plan_result["candidates"][0]]},
    )
    parent_id = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()["current_version"]["version_id"]

    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/replan",
        json={"effective_from": MONTH_STR},
    )
    assert resp.status_code == 200
    replan_body = resp.json()
    assert replan_body["status"] == "FEASIBLE"

    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view["current_version"]["version_id"] != parent_id
    assert view["current_version"]["parent_version_id"] == parent_id


# ROTA-T033 (owner-corrected 2026-08-26, step 2 "Szukaj szerzej"): reachable
# from the API, and creates no further ScheduleVersion of its own.
def test_replan_wider_search_creates_no_new_version(client, site_id):
    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
        json={"candidate": [_strip_display_name(a) for a in plan_result["candidates"][0]]},
    )
    client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/replan", json={"effective_from": MONTH_STR})
    version_id_before = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()["current_version"]["version_id"]

    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/replan/wider-search")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"FEASIBLE", "DECISION_REQUIRED", "NO_ALTERNATIVE", "SEARCH_INCOMPLETE"}

    version_id_after = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()["current_version"]["version_id"]
    assert version_id_after == version_id_before


# T31-07: finalize requires exactly the current deviation set.
def test_finalize_requires_exact_acknowledged_set(client, site_id):
    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
        json={"candidate": [_strip_display_name(a) for a in plan_result["candidates"][0]]},
    )

    bad = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/finalize",
        json={"acknowledged_deviation_ids": ["NONEXISTENT"]},
    )
    assert bad.status_code == 400

    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    current_ids = [d["deviation_id"] for d in view["deviations"]]

    good = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/finalize",
        json={"acknowledged_deviation_ids": current_ids},
    )
    assert good.status_code == 204

    final_view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert final_view["current_version"]["status"].startswith("FINAL")


# T31-08: restore moves the current pointer to an older version without deleting anything.
def test_restore_moves_current_pointer(client, site_id):
    first_plan = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
        json={"candidate": [_strip_display_name(a) for a in first_plan["candidates"][0]]},
    )
    parent_id = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()["current_version"]["version_id"]
    client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/replan", json={"effective_from": MONTH_STR})
    child_id = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()["current_version"]["version_id"]
    assert child_id != parent_id

    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/restore", json={"version_id": parent_id})
    assert resp.status_code == 204

    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view["current_version"]["version_id"] == parent_id

    history_ids = {v["version_id"] for v in view["version_history"]}
    assert {parent_id, child_id} <= history_ids


# T31-09: deviation labels -- known codes get a Polish label, unknown codes fall back to the raw code.
def test_deviation_label_known_and_unknown_codes():
    assert _deviation_label("WEEKLY-REST-01") == "odpoczynek tygodniowy (35h, OCHRONA)"
    assert _deviation_label("REST-01") == "odpoczynek dobowy"
    assert _deviation_label("SOME-FUTURE-CODE") == "SOME-FUTURE-CODE"


def test_precheck_endpoint_returns_status(client, site_id):
    resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/precheck")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("NO_OBVIOUS_SHORTAGE", "LIKELY_INSUFFICIENT")


def test_months_with_schedule_reflects_state(client, site_id):
    before = client.get(f"/api/workspace/sites/{site_id}/schedule/months").json()["months"]
    assert MONTH_STR not in before

    plan_result = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    ).json()
    client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
        json={"candidate": [_strip_display_name(a) for a in plan_result["candidates"][0]]},
    )

    after = client.get(f"/api/workspace/sites/{site_id}/schedule/months").json()["months"]
    assert MONTH_STR in after


def test_plan_rejects_unexpected_extra_field(client, site_id):
    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan",
        json={"effective_from": MONTH_STR, "site_id": site_id},
    )
    assert resp.status_code == 422


# R1-5 (round-1 audit): api/errors.py no longer maps every TypeError to 400
# -- a TypeError this shared boundary doesn't recognize must still fall
# through to 500, exactly as it did before T031 touched api/errors.py.
def test_unmapped_type_error_still_falls_through_to_500():
    exc = to_http_exception(TypeError("internal programming error"))
    assert exc.status_code == 500


def _seed_days_of_month(conn, month: date) -> None:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = month
    while day < next_month:
        save_calendar_day(conn, CalendarDay(day, False))
        day = date.fromordinal(day.toordinal() + 1)


# R1-2 (round-1 audit): DECISION_REQUIRED must be a persistent readback
# (current_decision_required), not only a transient PlanningResult -- a
# minimal one-shift/zero-roster scenario forces it deterministically,
# unlike seed_real_object's already-staffed benchmark.
@pytest.fixture
def understaffed_site():
    connection = connect(":memory:")
    site_id, profile_id = "SITE-UNDERSTAFFED", "PROF-UNDERSTAFFED"
    profile = SiteProfile(
        profile_id, "Profile", True,
        [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        True, True, False, False, 1, 40,
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "Coordinator", True),
        site_profile=profile,
        site=Site(site_id, profile_id, "Understaffed", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, site_id, True),
    )
    _seed_days_of_month(connection, MONTH)
    try:
        yield connection, site_id
    finally:
        connection.close()


@pytest.fixture
def understaffed_client(understaffed_site):
    connection, _ = understaffed_site
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def test_decision_required_is_persistent_across_get(understaffed_site, understaffed_client):
    _, site_id = understaffed_site
    plan_resp = understaffed_client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan", json={"effective_from": MONTH_STR},
    )
    assert plan_resp.json()["status"] == "DECISION_REQUIRED"

    view = understaffed_client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view["decision_required"] is not None
    assert view["decision_required"]["blocking_shift_demands"]

    # simulates a reload: a second, independent GET must still see it.
    view_again = understaffed_client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view_again["decision_required"] is not None


def test_decision_required_absent_for_a_feasible_month(client, site_id):
    view = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
    assert view["decision_required"] is None
