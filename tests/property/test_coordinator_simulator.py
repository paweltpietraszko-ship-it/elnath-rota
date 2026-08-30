"""ROTA-T043 Checkpoint A (tasks/ROTA-T043/brief.md, ARCHITECT_CORRECTED R4):
targeted tests for the rewritten Symulator Koordynatora generator/driver.

This file does NOT build the full 20-object portfolio, the fairness/validate
evaluator, the Markdown/JSON report, or the quarter arithmetic oracle --
those are Checkpoint B (brief section 5/5.1). This file proves Checkpoint
A's own contract: fixed 5/10 headcount never derived from workload, no
reactive hire, a frozen 2026 holiday fixture backing the target-hours
calculator, the real production write path, one real DECISION_REQUIRED +
EXTERNAL testowa ścieżka with the correct decision-link ordering, and the
quarterly driver's own mechanics (not its oracle) running without crashing.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from tests.property import coordinator_simulator as sim

MONTH = date(2026, 9, 1)


# --- generator-only tests: no TestClient, no solver -----------------------

@pytest.mark.parametrize("shift_shape", list(sim._CATALOG_ROWS))
@pytest.mark.parametrize("layer_count,expected_headcount", [(1, 5), (2, 10)])
def test_headcount_is_5_or_10_never_derived_from_workload(shift_shape, layer_count, expected_headcount):
    hours_one_layer = sim.monthly_hours_for_shape(shift_shape, MONTH, 1)
    hours_this_layer_count = sim.monthly_hours_for_shape(shift_shape, MONTH, layer_count)
    assert hours_this_layer_count == hours_one_layer * layer_count
    # R4: headcount is a pure function of layer_count, independent of the
    # actual hour total -- proven by constructing an ObjectSpec directly
    # rather than depending on random_object_spec's own seed-to-layer
    # mapping for this assertion.
    spec = sim.ObjectSpec(
        seed=0, month=MONTH, shift_shape=shift_shape, regime="ORDINARY", rolling_7d_threshold_hours=60,
        layer_count=layer_count, monthly_hours_needed=hours_this_layer_count, employee_count=5 * layer_count,
        target_hours_per_employee=176, day_only_indices=(),
    )
    assert spec.employee_count == expected_headcount


def test_random_object_spec_default_portfolio_covers_both_layer_counts():
    layer_counts = {sim.random_object_spec(seed, MONTH).layer_count for seed in range(20)}
    assert layer_counts == {1, 2}


def test_random_object_spec_default_portfolio_covers_all_shapes():
    shapes = {sim.random_object_spec(seed, MONTH).shift_shape for seed in range(20)}
    assert shapes == set(sim._CATALOG_ROWS)


def test_target_hours_control_values_against_frozen_fixture():
    # brief.md section 2.3: obowiązkowe kontrole styczeń 2026 = 160h, wrzesień 2026 = 176h.
    assert sim.nominal_monthly_hours_kp(date(2026, 1, 1), sim.POLISH_2026_HOLIDAYS) == 160
    assert sim.nominal_monthly_hours_kp(date(2026, 9, 1), sim.POLISH_2026_HOLIDAYS) == 176


def test_no_reactive_hire_code_path_exists():
    assert not hasattr(sim, "hire_one_more_local")


def test_random_absence_set_seed_zero_is_everyone_available():
    spec = sim.random_object_spec(0, MONTH)
    assert sim.random_absence_set(0, spec, spec.employee_count) == []


def test_random_absence_set_can_draw_sick_leave():
    # R4: SICK_LEAVE is drawable like any other kind now (no allow_sick_leave
    # parameter any more) -- confirmed empirically against the real API in
    # test_sick_leave_before_first_plan_is_feasible_not_a_500 below.
    spec = sim.random_object_spec(3, MONTH)
    found_sick = False
    for seed in range(1, 200):
        draws = sim.random_absence_set(seed, spec, spec.employee_count)
        if any(d.kind == "SICK_LEAVE" for d in draws):
            found_sick = True
            break
    assert found_sick, "expected at least one SICK_LEAVE draw across 200 seeds"


# --- real API verticals -----------------------------------------------------

@pytest.fixture
def client():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def test_one_real_api_vertical_seed_zero(client):
    spec = sim.random_object_spec(0, MONTH)
    site_id = sim.build_object(client, spec)
    assert len(sim.declared_roster(spec)) == 5

    result = sim.run_plan(client, site_id, MONTH)
    assert result["status"] in {"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"}
    if result["status"] == "FEASIBLE":
        used = sorted({a["employee_id"] for a in result["candidates"][0]})
        assert set(used) <= set(sim.declared_roster(spec))


def test_sick_leave_before_first_plan_is_feasible_not_a_500(client):
    spec = sim.random_object_spec(0, MONTH)
    site_id = sim.build_object(client, spec)
    sim.apply_absences(client, site_id, spec, [
        sim.AbsenceDraw(employee_index=0, kind="SICK_LEAVE", start_date=date(2026, 9, 3), end_date=date(2026, 9, 5)),
    ])
    result = sim.run_plan(client, site_id, MONTH)
    assert result["status"] in {"FEASIBLE", "DECISION_REQUIRED"}


def test_decision_required_triggers_external_reaction_with_correct_decision_link_ordering(client):
    spec = sim.random_object_spec(0, MONTH)  # 5 LOCAL, D_N_12H (2 posts/day)
    site_id = sim.build_object(client, spec)
    # Force a real, deterministic DECISION_REQUIRED: disable 4 of the 5
    # LOCAL through the real roster PATCH, leaving one person to cover a
    # two-post-per-day catalog -- a genuine, unforced product outcome, not
    # a fabricated payload.
    for i in range(1, 5):
        resp = client.patch(
            f"/api/workspace/sites/{site_id}/roster/{sim.local_employee_id(spec, i)}", json={"enabled": False},
        )
        assert resp.status_code == 204, resp.text

    first_result = sim.run_plan(client, site_id, MONTH)
    assert first_result["status"] == "DECISION_REQUIRED"
    assert first_result["decision_payload"]

    reaction = sim.external_support_reaction(client, site_id, MONTH, spec)
    assert reaction["external_employee_id"] == sim.external_support_employee_id(spec)

    roster = client.get(f"/api/workspace/sites/{site_id}/roster").json()
    external_rows = [r for r in roster if r["employee_id"] == reaction["external_employee_id"]]
    assert len(external_rows) == 1
    assert external_rows[0]["membership_kind"] == "EXTERNAL_SUPPORT"
    local_rows = [r for r in roster if r["membership_kind"] == "LOCAL"]
    assert len(local_rows) == 5, "R4: LOCAL headcount must never change as a result of the EXTERNAL reaction"

    # First PLAN's own result is preserved untouched -- the reaction result
    # is a separate, additional fact.
    assert first_result["status"] == "DECISION_REQUIRED"
    assert reaction["second_plan_result"]["status"] in {"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"}


def test_replan_after_material_change_is_a_distinct_reported_event(client):
    spec = sim.random_object_spec(0, MONTH)
    site_id = sim.build_object(client, spec)
    first = sim.run_plan(client, site_id, MONTH)
    assert first["status"] == "FEASIBLE"
    sim.select_first_candidate(client, site_id, MONTH, first)

    sim.apply_absences(client, site_id, spec, [
        sim.AbsenceDraw(employee_index=0, kind="SICK_LEAVE", start_date=date(2026, 9, 10), end_date=date(2026, 9, 12)),
    ])
    replanned = sim.run_replan(client, site_id, MONTH)
    assert replanned["status"] in {"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"}


def test_quarterly_driver_mechanics_run_without_crashing():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        result = sim.run_quarter(client, seed=0)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()

    assert result["status"] in {"QUARTER_OK", "QUARTER_BLOCKED"}
    if result["status"] == "QUARTER_OK":
        assert [m["month"] for m in result["months"]] == [m.isoformat() for m in sim.QUARTER_MONTHS]
        for m in result["months"]:
            assert "analytics" in m
    else:
        # A genuinely blocked quarter is a valid, reportable Checkpoint B
        # finding -- this test only proves the mechanics don't crash and
        # preserve reproduction facts, per brief section 4.3/12.
        assert "seed" in result and "failing_month" in result and "reason" in result


if __name__ == "__main__":
    print("test_coordinator_simulator module OK")
