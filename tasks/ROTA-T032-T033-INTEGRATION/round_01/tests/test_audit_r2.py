"""Round-2 independent seam checks for exact integration delivery."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from api.routers import schedule
from rota.persistence.db import connect
from rota.planning.engine_types import PlanningResult
from rota.planning.solver import SolverOutcome
from tests.support.minimal_state import base_state
from tests.support.t009_fixtures import seed_real_object
from tests.test_t033_replan_must_differ import EARLY_CUTOVER


def _outcome(status: str, assignments):
    return SolverOutcome(status, assignments, [], [], {}, [], {}, optimization_complete=status == "OPTIMAL")


def test_plan_api_passes_nonpersistent_attempt_and_rejects_negative(monkeypatch):
    seen: list[int] = []
    monkeypatch.setattr(schedule, "get_current_version_id", lambda *_args, **_kwargs: "SV-CURRENT")
    monkeypatch.setattr(
        schedule,
        "plan_month",
        lambda *_args, search_attempt, **_kwargs: (
            seen.append(search_attempt)
            or PlanningResult("FEASIBLE", [[]], None, None, [], optimization_complete=False)
        ),
    )
    conn = connect(":memory:")
    try:
        payload = schedule.post_plan(
            "SITE-A", date(2026, 8, 1), schedule.PlanRequest(search_attempt=4), conn,
        )
    finally:
        conn.close()

    assert seen == [4]
    assert payload.optimization_complete is False
    with pytest.raises(ValidationError):
        schedule.PlanRequest(search_attempt=-1)


def test_narrow_attempt_reaches_baseline_and_diversity(monkeypatch):
    import rota.planning.engine as engine

    seen: list[tuple[str, int]] = []

    def fake_plan(_state, _deadline, search_attempt):
        seen.append(("baseline", search_attempt))
        return PlanningResult("FEASIBLE", [[]], None, None, [])

    def fake_solve(_state, **kwargs):
        seen.append(("diversity", kwargs["search_attempt"]))
        return _outcome("UNKNOWN", None)

    monkeypatch.setattr(engine, "_plan", fake_plan)
    monkeypatch.setattr(engine, "solve", fake_solve)

    result = engine.plan_requiring_different_result_narrow(base_state(), EARLY_CUTOVER, search_attempt=7)

    assert seen == [("baseline", 7), ("diversity", 7)]
    assert (result.status, result.optimization_complete) == ("SEARCH_INCOMPLETE", False)


def test_wide_attempt_reaches_ordinary_and_diversity_timeout(monkeypatch):
    import rota.planning.engine as engine

    seen: list[int] = []
    outcomes = iter((_outcome("OPTIMAL", []), _outcome("UNKNOWN", None)))

    def fake_solve(_state, **kwargs):
        seen.append(kwargs["search_attempt"])
        return next(outcomes)

    monkeypatch.setattr(engine, "solve", fake_solve)

    result = engine.plan_requiring_different_result_wide(base_state(), EARLY_CUTOVER, search_attempt=9)

    assert seen == [9, 9]
    assert (result.status, result.optimization_complete) == ("SEARCH_INCOMPLETE", False)


def test_replan_retry_endpoint_uses_retry_seam_not_new_replan(monkeypatch):
    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        schedule,
        "replan_retry_narrow",
        lambda *_args, search_attempt, **_kwargs: (
            calls.append(("retry", search_attempt))
            or PlanningResult("SEARCH_INCOMPLETE", [], None, None, [], optimization_complete=False)
        ),
    )
    monkeypatch.setattr(
        schedule,
        "replan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("retry created a new REPLAN child")),
    )
    conn = connect(":memory:")
    try:
        payload = schedule.post_replan_retry(
            "SITE-A", date(2026, 8, 1), schedule.ReplanRetryRequest(search_attempt=3), conn,
        )
    finally:
        conn.close()

    assert calls == [("retry", 3)]
    assert payload.optimization_complete is False


def test_real_api_replan_retry_reuses_current_child_version():
    """Real API -> application -> assembler -> solver -> persistence seam."""
    month = date(2026, 8, 1)
    conn = connect(":memory:")
    state = seed_real_object(
        conn, case_id="audit-r2-retry", month=month, seed=321,
        coordinator_id=DEV_COORDINATOR_ID,
    )
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    client = TestClient(app)
    try:
        base = f"/api/workspace/sites/{state.site.site_id}/schedule/{month.isoformat()}"
        planned = client.post(f"{base}/plan", json={"effective_from": month.isoformat()}).json()
        assert planned["status"] == "FEASIBLE"
        chosen = [
            {key: value for key, value in assignment.items() if key != "employee_display_name"}
            for assignment in planned["candidates"][0]
        ]
        assert client.post(f"{base}/select-candidate", json={"candidate": chosen}).status_code == 204
        assert client.post(f"{base}/replan", json={"effective_from": month.isoformat()}).status_code == 200
        child_before = client.get(base).json()["current_version"]["version_id"]

        retried = client.post(f"{base}/replan/retry", json={"search_attempt": 1})

        assert retried.status_code == 200
        assert retried.json()["status"] in {
            "FEASIBLE", "DECISION_REQUIRED", "NARROW_SEARCH_EXHAUSTED", "SEARCH_INCOMPLETE",
        }
        assert client.get(base).json()["current_version"]["version_id"] == child_before
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()
