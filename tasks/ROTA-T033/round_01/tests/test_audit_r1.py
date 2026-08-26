"""Independent ROTA-T033 audit reproducers for exact SHA 43dc8cb.

These tests derive expectations only from the frozen owner decisions:
- REPLAN returns a different schedule or an honest search status;
- one narrow click has one 45 s budget and a timeout remains retryable;
- the normal planning error boundary remains intact;
- deactivation hides a Site without deleting its durable history.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.domain import AvailabilityKind, AvailabilityRecord, ShiftDemand
from rota.planning.engine import (
    plan,
    plan_requiring_different_result_narrow,
    plan_requiring_different_result_wide,
)
from rota.planning.engine_types import PlanningResult
from rota.planning.solver import SolverOutcome
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site
from tests.support.minimal_state import base_state
from tests.support.t009_fixtures import seed_real_object
from tests.test_t031_schedule_api import MONTH, MONTH_STR, _strip_display_name
from tests.test_t033_replan_must_differ import (
    EARLY_CUTOVER,
    _baseline,
    _covering_pairs,
    _demand_d,
    _employee,
    _membership,
)


def _partial_but_uniquely_completable_state():
    """D1 is stored; D2 is absent. Each demand has exactly one legal worker."""
    demand_1 = _demand_d("D1", 5)
    demand_2 = _demand_d("D2", 6)
    unavailable = (
        AvailabilityRecord(
            "uA", "uAv1", "A", AvailabilityKind.UNAVAILABLE_24H,
            date(2026, 10, 6), date(2026, 10, 6), True, None, None,
        ),
        AvailabilityRecord(
            "uB", "uBv1", "B", AvailabilityKind.UNAVAILABLE_24H,
            date(2026, 10, 5), date(2026, 10, 5), True, None, None,
        ),
    )
    return base_state(
        employees=(_employee("A"), _employee("B")),
        memberships=(_membership("A"), _membership("B")),
        shift_demands=(demand_1, demand_2),
        existing_assignments=(_baseline("stored-D1", "A", demand_1),),
        availability_records=unavailable,
    )


def test_r1_partial_schedule_completed_by_new_assignment_is_a_different_schedule():
    """Adding missing D2 changes the schedule even when stored D1 cannot move."""
    result = plan_requiring_different_result_narrow(
        _partial_but_uniquely_completable_state(), EARLY_CUTOVER,
    )

    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("A", "D1"), ("B", "D2")}


def test_r1_wide_must_not_claim_no_alternative_to_a_partial_schedule():
    """The exhaustive label must compare the complete result, including additions."""
    result = plan_requiring_different_result_wide(
        _partial_but_uniquely_completable_state(), EARLY_CUTOVER,
    )

    assert result.status == "FEASIBLE"
    assert _covering_pairs(result.candidates[0]) == {("A", "D1"), ("B", "D2")}


def test_r1_timeout_during_narrow_baseline_check_is_retryable(monkeypatch):
    """The same 45 s deadline applies, but consuming it is not a model error."""
    import rota.planning.engine as engine

    deadlines: list[float | None] = []

    def timed_out(*_args, **kwargs):
        deadlines.append(kwargs.get("deadline"))
        return SolverOutcome("UNKNOWN", None, [], [], {}, [], {})

    monkeypatch.setattr(engine, "solve", timed_out)
    result = engine.plan_requiring_different_result_narrow(base_state(), EARLY_CUTOVER)

    assert deadlines and deadlines[0] is not None
    assert result.status == "SEARCH_INCOMPLETE"


def test_r1_replan_preserves_public_model_error_mapping():
    """REPLAN is a public planning path just like PLAN; it must not throw raw model errors."""
    bad = ShiftDemand(
        "unclassified", "test-v1",
        datetime(2026, 10, 1, 8), datetime(2026, 10, 1, 16), 1,
    )
    state = base_state(shift_demands=(bad,))

    assert plan(state).status == "TECHNICAL_ERROR"
    result = plan_requiring_different_result_narrow(state, EARLY_CUTOVER)
    assert result.status == "TECHNICAL_ERROR"


def test_r1_real_api_replan_returns_and_persists_a_different_candidate():
    """Vertical API -> application -> assembler -> solver -> candidate selection."""
    conn = connect(":memory:")
    planning_state = seed_real_object(
        conn, case_id="t033-audit-r1", month=MONTH, seed=1901,
        coordinator_id=DEV_COORDINATOR_ID,
    )
    site_id = planning_state.site.site_id
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app)
        initial = client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan",
            json={"effective_from": MONTH_STR},
        ).json()
        baseline = [_strip_display_name(row) for row in initial["candidates"][0]]
        assert client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
            json={"candidate": baseline},
        ).status_code == 204
        before = {(row["employee_id"], row["covers_demand_id"]) for row in baseline}

        response = client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/replan",
            json={"effective_from": MONTH_STR},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "FEASIBLE"
        candidate = [_strip_display_name(row) for row in body["candidates"][0]]
        after = {(row["employee_id"], row["covers_demand_id"]) for row in candidate}
        assert after != before

        assert client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
            json={"candidate": candidate},
        ).status_code == 204
        persisted = client.get(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}",
        ).json()["assignments"]
        assert {(row["employee_id"], row["covers_demand_id"]) for row in persisted} == after
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


def test_r1_one_deadline_is_shared_by_baseline_and_diversity(monkeypatch):
    """Independent proof of the correction delivered in 43dc8cb."""
    import rota.planning.engine as engine

    seen: list[float | None] = []

    def baseline(_state, deadline=None):
        seen.append(deadline)
        return PlanningResult("FEASIBLE", [[]], None, None, [])

    def diversity(*_args, **kwargs):
        seen.append(kwargs.get("deadline"))
        return SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})

    monkeypatch.setattr(engine, "_plan", baseline)
    monkeypatch.setattr(engine, "solve", diversity)
    result = engine.plan_requiring_different_result_narrow(base_state(), EARLY_CUTOVER)

    assert result.status == "NARROW_SEARCH_EXHAUSTED"
    assert len(seen) == 2 and seen[0] is not None and seen[0] == seen[1]


def test_r1_site_hide_restore_keeps_real_roster_and_selected_schedule():
    """Vertical API -> existing active seam -> persistence -> restored screen reads."""
    conn = connect(":memory:")
    planning_state = seed_real_object(
        conn, case_id="t033-site-audit-r1", month=MONTH, seed=1902,
        coordinator_id=DEV_COORDINATOR_ID,
    )
    site_id = planning_state.site.site_id
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app)
        planned = client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/plan",
            json={"effective_from": MONTH_STR},
        ).json()
        candidate = [_strip_display_name(row) for row in planned["candidates"][0]]
        assert client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}/select-candidate",
            json={"candidate": candidate},
        ).status_code == 204
        membership_ids = [m.employee_id for m in list_memberships_for_site(conn, site_id)]

        assert client.post(f"/api/workspace/sites/{site_id}/deactivate").status_code == 204
        assert site_id not in {row["site_id"] for row in client.get("/api/workspace/sites").json()}
        hidden = client.get("/api/workspace/sites?include_inactive=true").json()
        assert any(row["site_id"] == site_id and row["active"] is False for row in hidden)

        assert client.post(f"/api/workspace/sites/{site_id}/reactivate").status_code == 204
        restored = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH_STR}").json()
        assert [m.employee_id for m in list_memberships_for_site(conn, site_id)] == membership_ids
        assert {
            (row["employee_id"], row["covers_demand_id"]) for row in restored["assignments"]
        } == {(row["employee_id"], row["covers_demand_id"]) for row in candidate}
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()
