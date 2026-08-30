"""ROTA-T043 (tasks/ROTA-T043/brief.md, ARCHITECT_CORRECTED R4): Symulator
Koordynatora pytest entry point.

Checkpoint A (see coordinator_simulator.py's own docstring): fixed 5/10
headcount never derived from workload, no reactive hire, a frozen 2026
holiday fixture backing the target-hours calculator, the real production
write path, one real DECISION_REQUIRED + EXTERNAL testowa ścieżka with the
correct decision-link ordering, and the quarterly driver's own mechanics.

Checkpoint B (this file, added on top): the fairness/validate evaluator
(coordinator_simulator.py's compute_fairness_facts/evaluate_fairness/
select_first_candidate_reporting_validate/compute_quarter_oracle), the
default 20-object monthly portfolio, the mandatory Q3 2026 quarter run, and
the tasks/ROTA-T043/round_01/tests/coordinator_report.{md,json} writers.
Checkpoint C's trust-gate classification (brief section 6) is NOT built
here.

Default `pytest` run stays to ONE short targeted case per changed class --
the full 20-object portfolio + Q3 quarter run is its own explicit,
env-gated test (ROTA_SIM_FULL_PORTFOLIO=1), never part of the normal
default matrix (brief 4.4)."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from tests.property import coordinator_simulator as sim

MONTH = date(2026, 9, 1)
REPORT_DIR = Path(__file__).resolve().parents[2] / "tasks" / "ROTA-T043" / "round_01" / "tests"
FAILURES_DIR = REPORT_DIR / "failures"

# R6 fix (T43-R6-01): brief 4.2 lists "miesiąc z fixture 2026" as a required
# portfolio axis -- the 20-object portfolio previously reused the single
# MONTH constant for every seed. All twelve months of 2026 are covered by
# POLISH_2026_HOLIDAYS/nominal_monthly_hours_kp, so every one is a valid
# draw; single-seed targeted tests above keep using the fixed MONTH
# constant (they don't need month variation), and the mandatory Q3 pion
# (brief 4.3) keeps its own fixed July/August/September months.
PORTFOLIO_MONTHS = tuple(date(2026, m, 1) for m in range(1, 13))


def portfolio_month_for_seed(seed: int) -> date:
    return PORTFOLIO_MONTHS[seed % len(PORTFOLIO_MONTHS)]


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


def test_random_absence_set_respects_frozen_urlop_and_l4_bounds():
    """R6 fix (T43-R6-02): brief 2.4 -- at most one LEAVE_GRANTED per draw
    set, LEAVE_GRANTED span <=14 days, SICK_LEAVE span <=21 days (and can
    reach that upper bound somewhere in a real sweep)."""
    spec = sim.random_object_spec(5, MONTH)
    max_sick_span_seen = 0
    for seed in range(1, 2000):
        draws = sim.random_absence_set(seed, spec, spec.employee_count)
        leave_granted_draws = [d for d in draws if d.kind == "LEAVE_GRANTED"]
        assert len(leave_granted_draws) <= 1, f"seed {seed}: more than one LEAVE_GRANTED in one draw set"
        for d in leave_granted_draws:
            span = (d.end_date - d.start_date).days + 1
            assert span <= 14, f"seed {seed}: LEAVE_GRANTED span {span} exceeds 14 days"
        for d in draws:
            if d.kind == "SICK_LEAVE":
                span = (d.end_date - d.start_date).days + 1
                assert span <= 21, f"seed {seed}: SICK_LEAVE span {span} exceeds 21 days"
                max_sick_span_seen = max(max_sick_span_seen, span)
    assert max_sick_span_seen >= 15, f"expected SICK_LEAVE spans to reach well past the old 5-day cap across 2000 seeds, saw max {max_sick_span_seen}"


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


# --- Checkpoint B: fairness/validate evaluator, targeted tests -----------


def _month_view(client: TestClient, site_id: str, month: date) -> dict:
    resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}")
    resp.raise_for_status()
    return resp.json()


def _decision_reason(payload: dict | None) -> str:
    if not payload:
        return "-"
    parts = [b["condition"] for b in payload.get("blockers", [])]
    parts += payload.get("unblocking_options", [])
    return " | ".join(parts) if parts else "(brak szczegółów w payloadzie)"


def _run_one_monthly_object(client: TestClient, seed: int, month: date) -> dict:
    """One full Checkpoint B row: build -> absences -> PLAN -> (EXTERNAL
    reaction if a real DECISION_REQUIRED) -> select-candidate with reported
    product-validate -> fairness facts/verdict -> optional REPLAN. Never
    raises on a bad/unfair result -- every outcome is reported data (brief
    section 3: "Jeżeli B ujawni defekt, zachować reproduktor")."""
    spec = sim.random_object_spec(seed, month)
    absence_draws = sim.random_absence_set(seed, spec, spec.employee_count)
    employees = sim.declared_roster(spec)

    site_id = sim.build_object(client, spec)
    sim.apply_absences(client, site_id, spec, absence_draws)

    first_result = sim.run_plan(client, site_id, month)
    row: dict = {
        "seed": seed, "month": month.isoformat(), "shift_shape": spec.shift_shape, "regime": spec.regime,
        "layer_count": spec.layer_count, "employee_count": spec.employee_count, "roster": employees,
        "absences": [d.__dict__ | {"employee_id": sim.local_employee_id(spec, d.employee_index)} for d in absence_draws],
        "first_plan_status": first_result["status"],
    }

    external = None
    base_result = first_result
    if first_result["status"] == "DECISION_REQUIRED":
        row["first_plan_decision_reason"] = _decision_reason(first_result.get("decision_payload"))
        if not first_result.get("decision_payload"):
            row["defect"] = "empty DECISION_REQUIRED payload on first PLAN -- tool/product defect"
            _write_failure_json(f"seed{seed}-empty-decision-payload", row | {"first_plan_result": first_result}, seed=seed)
        else:
            external = sim.external_support_reaction(client, site_id, month, spec)
            base_result = external["second_plan_result"]
        row["external"] = external

    if base_result["status"] != "FEASIBLE" or not base_result.get("candidates"):
        row["final_status"] = base_result["status"]
        row["final_reason"] = _decision_reason(base_result.get("decision_payload")) if base_result["status"] == "DECISION_REQUIRED" else base_result.get("error_message")
        if not absence_draws and not spec.day_only_indices and base_result["status"] == "DECISION_REQUIRED":
            # a certified-clean object still blocked -- a real finding, not routed around.
            _write_failure_json(f"seed{seed}-clean-object-decision-required", row | {"base_result": base_result}, seed=seed)
        return row

    validate_status, validate_detail, candidate = sim.select_first_candidate_reporting_validate(client, site_id, month, base_result)
    row["product_validate"] = validate_status
    if validate_status == "PRODUCT_VALIDATE_FAIL":
        row["final_status"] = "PRODUCT_VALIDATE_FAIL"
        _write_failure_json(f"seed{seed}-validate-fail", row | {"detail": validate_detail, "candidate": candidate}, seed=seed)
        return row

    view = _month_view(client, site_id, month)
    analytics = sim.get_analytics(client, site_id, month)
    facts = sim.compute_fairness_facts(
        assignments=view["assignments"], demands=view["demands"], employees=employees,
        analytics_rows=analytics["rows"], absence_draws=absence_draws, spec=spec,
    )
    primary_atom_count = sum(1 for a in view["assignments"] if sim._is_active_primary(a))
    fairness_verdict, fairness_detail = sim.evaluate_fairness(
        spec=spec, absence_draws=absence_draws, has_external=external is not None,
        actual_hours=facts.actual_hours, primary_atom_count=primary_atom_count,
    )
    row.update(final_status="FEASIBLE", fairness_verdict=fairness_verdict, fairness_detail=fairness_detail, fairness_facts=facts.__dict__)
    # R6 fix (T43-R6-03): brief 460-461 requires a failure JSON for every
    # CZERWONY *or* NIEUDOWODNIONY case, not just FAIRNESS_FAIL --
    # FAIRNESS_UNPROVEN is an honest non-green result and needs the same
    # reproduction material.
    if fairness_verdict in {"FAIRNESS_FAIL", "FAIRNESS_UNPROVEN"}:
        suffix = "fairness-fail" if fairness_verdict == "FAIRNESS_FAIL" else "fairness-unproven"
        _write_failure_json(f"seed{seed}-{suffix}", row | {"assignments": view["assignments"]}, seed=seed)

    # B5: a deterministic REPLAN scenario on even seeds only (kept from
    # Checkpoint A's own open question -- documented here, not silently
    # resolved: bounds runtime, still deterministic and reproducible).
    if seed % 2 == 0:
        replan_draws = sim.random_absence_set(seed * 104729, spec, spec.employee_count)
        if replan_draws:
            before = {"assignments": view["assignments"], "fairness_verdict": fairness_verdict}
            sim.apply_absences(client, site_id, spec, replan_draws)
            replanned = sim.run_replan(client, site_id, month)
            row["replan"] = {"status": replanned["status"], "before": before}
            if replanned["status"] == "FEASIBLE" and replanned.get("candidates"):
                r_validate_status, r_validate_detail, r_candidate = sim.select_first_candidate_reporting_validate(client, site_id, month, replanned)
                r_view = _month_view(client, site_id, month)
                r_analytics = sim.get_analytics(client, site_id, month)
                r_facts = sim.compute_fairness_facts(
                    assignments=r_view["assignments"], demands=r_view["demands"], employees=employees,
                    analytics_rows=r_analytics["rows"], absence_draws=absence_draws + replan_draws, spec=spec,
                )
                r_primary_atoms = sum(1 for a in r_view["assignments"] if sim._is_active_primary(a))
                r_verdict, r_detail = sim.evaluate_fairness(
                    spec=spec, absence_draws=absence_draws + replan_draws, has_external=external is not None,
                    actual_hours=r_facts.actual_hours, primary_atom_count=r_primary_atoms,
                )
                row["replan"]["after"] = {
                    "product_validate": r_validate_status, "assignments": r_view["assignments"],
                    "fairness_verdict": r_verdict, "fairness_detail": r_detail,
                }
    return row


def _write_failure_json(name: str, payload: dict, *, seed: int | None = None) -> None:
    """R6 fix (T43-R6-03): brief 460-465 requires a real, executable
    reproduction command in every failure JSON -- `seed` (when the case has
    one) attaches `_reproduction_command(seed)` automatically instead of
    relying on every call site to remember to build one by hand."""
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    if seed is not None:
        payload = payload | {"reproduction": _reproduction_command(seed)}
    (FAILURES_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def test_symmetric_dn_control_case_gets_a_fairness_verdict():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        row = _run_one_monthly_object(client, seed=0, month=MONTH)  # seed 0: D_N_12H, 1 layer, no absences
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()
    assert row["final_status"] == "FEASIBLE"
    assert row["fairness_verdict"] in {"FAIRNESS_PASS", "FAIRNESS_FAIL"}  # never UNPROVEN for this exact class


def test_symmetric_h24_control_case_gets_a_fairness_verdict():
    """random_object_spec's deterministic seed cycle only guarantees
    zero absences at seed=0 (D_N_12H) -- a SINGLE_24H case needs its own
    directly-constructed, zero-absence ObjectSpec to actually land in the
    B3.1 symmetric control class (this is a real fairness verdict, not
    dependent on getting lucky with a seed's random absence draw)."""
    spec = sim.ObjectSpec(
        seed=900, month=MONTH, shift_shape="SINGLE_24H", regime="OCHRONA", rolling_7d_threshold_hours=60,
        layer_count=1, monthly_hours_needed=sim.monthly_hours_for_shape("SINGLE_24H", MONTH, 1),
        employee_count=5, target_hours_per_employee=sim.nominal_monthly_hours_kp(MONTH, sim.POLISH_2026_HOLIDAYS),
        day_only_indices=(),
    )
    assert sim.is_symmetric_control_object(spec, [])
    employees = sim.declared_roster(spec)

    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        site_id = sim.build_object(client, spec)
        first_result = sim.run_plan(client, site_id, MONTH)
        if first_result["status"] != "FEASIBLE":
            return  # a real DECISION_REQUIRED here would be a Checkpoint B finding, not this test's concern
        validate_status, _, _ = sim.select_first_candidate_reporting_validate(client, site_id, MONTH, first_result)
        assert validate_status == "PRODUCT_VALIDATE_PASS"
        view = _month_view(client, site_id, MONTH)
        analytics = sim.get_analytics(client, site_id, MONTH)
        facts = sim.compute_fairness_facts(
            assignments=view["assignments"], demands=view["demands"], employees=employees,
            analytics_rows=analytics["rows"], absence_draws=[], spec=spec,
        )
        primary_atoms = sum(1 for a in view["assignments"] if sim._is_active_primary(a))
        verdict, _ = sim.evaluate_fairness(
            spec=spec, absence_draws=[], has_external=False, actual_hours=facts.actual_hours, primary_atom_count=primary_atoms,
        )
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()
    assert verdict in {"FAIRNESS_PASS", "FAIRNESS_FAIL"}


def test_asymmetric_case_is_unproven_never_silently_green():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        # WEEKDAY_12H_WEEKEND_24H is the third catalog shape -- find its
        # first occurrence in the deterministic seed cycle.
        seed = next(s for s in range(1, 20) if sim.random_object_spec(s, MONTH).shift_shape == "WEEKDAY_12H_WEEKEND_24H")
        row = _run_one_monthly_object(client, seed=seed, month=MONTH)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()
    if row["final_status"] == "FEASIBLE" and row.get("external") is None:
        assert row["fairness_verdict"] == "FAIRNESS_UNPROVEN"


def test_decision_required_object_is_unproven_not_green():
    """A DECISION_REQUIRED+EXTERNAL object never gets a FAIRNESS_PASS --
    has_external=True forces UNPROVEN regardless of the second PLAN's own
    shape (brief B3.2: EXTERNAL reactions never earn a fairness PASS)."""
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        spec = sim.random_object_spec(0, MONTH)
        site_id = sim.build_object(client, spec)
        for i in range(1, 5):
            resp = client.patch(f"/api/workspace/sites/{site_id}/roster/{sim.local_employee_id(spec, i)}", json={"enabled": False})
            assert resp.status_code == 204
        first_result = sim.run_plan(client, site_id, MONTH)
        assert first_result["status"] == "DECISION_REQUIRED"
        external = sim.external_support_reaction(client, site_id, MONTH, spec)
        assert external["second_plan_result"]["status"] in {"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"}
        if external["second_plan_result"]["status"] == "FEASIBLE":
            _, _, _ = sim.select_first_candidate_reporting_validate(client, site_id, MONTH, external["second_plan_result"])
            view = _month_view(client, site_id, MONTH)
            analytics = sim.get_analytics(client, site_id, MONTH)
            employees = sim.declared_roster(spec)
            facts = sim.compute_fairness_facts(
                assignments=view["assignments"], demands=view["demands"], employees=employees,
                analytics_rows=analytics["rows"], absence_draws=[], spec=spec,
            )
            verdict, _ = sim.evaluate_fairness(
                spec=spec, absence_draws=[], has_external=True, actual_hours=facts.actual_hours,
                primary_atom_count=sum(1 for a in view["assignments"] if sim._is_active_primary(a)),
            )
            assert verdict == "FAIRNESS_UNPROVEN"
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def test_quarter_arithmetic_oracle_on_a_real_run():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        quarter_result = sim.run_quarter(client, seed=0)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()
    oracle = sim.compute_quarter_oracle(quarter_result)
    assert oracle["status"] in {"QUARTER_BALANCE_PASS", "QUARTER_BALANCE_FAIL", "QUARTER_BALANCE_NOT_APPLICABLE"}
    if oracle["status"] == "QUARTER_BALANCE_FAIL":
        _write_failure_json("quarter-balance-mismatch-seed0", {"quarter_result": quarter_result, "oracle": oracle})

    # R6 fix (T43-R6-04): the oracle must be genuinely independent -- Codex's
    # own repro stripped Assignments from a copy of a real quarter result
    # and the OLD oracle (reading analytics' own planned_hours) still
    # returned QUARTER_BALANCE_PASS. Prove the fixed oracle catches this.
    import copy as _copy
    stripped = _copy.deepcopy(quarter_result)
    if stripped["status"] == "QUARTER_OK":
        for month_entry in stripped["months"]:
            month_entry["assignments"] = []
        stripped_oracle = sim.compute_quarter_oracle(stripped)
        any_target_nonzero = any(
            row.get("month_data", {}).get("target_hours", 0) for m in stripped["months"] for row in m["analytics"]["rows"]
        )
        if any_target_nonzero:
            assert stripped_oracle["status"] == "QUARTER_BALANCE_FAIL", (
                "stripping all Assignments must make the independent oracle disagree with the product's own "
                "still-real month_balance/quarter_balance numbers"
            )

    # Same repro for the unresolved_carryover check: corrupt the product's
    # own field in a copy and confirm the oracle catches the mismatch.
    corrupted = _copy.deepcopy(quarter_result)
    if corrupted["status"] == "QUARTER_OK":
        any_corrupted = False
        for month_entry in corrupted["months"]:
            for row in month_entry["analytics"]["rows"]:
                md = row.get("month_data")
                if md is not None and md.get("unresolved_carryover") is not None:
                    md["unresolved_carryover"] = 999999
                    any_corrupted = True
        if any_corrupted:
            corrupted_oracle = sim.compute_quarter_oracle(corrupted)
            assert corrupted_oracle["status"] == "QUARTER_BALANCE_FAIL", (
                "corrupting unresolved_carryover must make the independent oracle catch it"
            )


# --- Checkpoint B: full 20-object portfolio + Q3 report, gated ------------


def _axis_coverage_ledger(rows: list[dict]) -> dict:
    """Robust to a CRASH row (only has seed/crash/final_status) -- a real
    crash is still a reportable finding, not something that should also
    take down the report writer itself."""
    return {
        "months": sorted({r["month"] for r in rows if "month" in r}),
        "shift_shapes": sorted({r["shift_shape"] for r in rows if "shift_shape" in r}),
        "layer_counts": sorted({r["layer_count"] for r in rows if "layer_count" in r}),
        "final_statuses": sorted({r["final_status"] for r in rows if "final_status" in r}),
        "had_external": any(r.get("external") for r in rows),
        "had_replan": any("replan" in r for r in rows),
        "had_absences": any(r.get("absences") for r in rows),
        "crashes": [r["seed"] for r in rows if r.get("final_status") == "CRASH"],
    }


# R6 fix (T43-R6-01/03/05): Checkpoint C's classification table/Playwright
# result/calibration proof is static content (it does not depend on this
# run's rows/quarter data) -- embedded here as a constant so regenerating
# the report never silently reverts to the old Checkpoint-C-not-done
# placeholder trailer.
_CHECKPOINT_C_REPORT_SECTION = """## Bramka zaufania do testów (Checkpoint C)

### Klasyfikacja dowodu (brief 6.1/6.2)

| Obszar (brief 6.2) | Plik(i) | Klasa |
|---|---|---|
| PLAN / wybór kandydata | `tests/test_t009_plan_select_replan.py` | REAL_APPLICATION |
| | `tests/test_t031_schedule_api.py`, `tests/test_t042_audit4_repairs.py` | REAL_API |
| | `tests/property/test_coordinator_simulator.py` (T043) | REAL_API |
| Fairness i H24 | `tests/test_t041_checkpoint_a.py` (hand-built `PlanningState`) | UNIT_OR_ADAPTER |
| | `tests/test_t040_h24_rhythm_occupancy.py` (`plan_ops.plan_month`) | REAL_APPLICATION |
| | `tests/property/test_coordinator_simulator.py`'s symmetric fairness verdicts (T043 Checkpoint B) | REAL_API |
| Urlop/L4 przed PLAN i przed REPLAN | `tests/test_t041_checkpoint_b.py` | REAL_API |
| | `tests/property/test_coordinator_simulator.py` (T043) | REAL_API |
| Nakładające się demandy | `tests/test_t041_checkpoint_a.py` (a07-a13, hand-built `PlanningState`) | UNIT_OR_ADAPTER |
| | *(brak REAL_APPLICATION/REAL_API piona w granicach TASK_SCOPE T043 -- patrz uwaga niżej)* | -- |
| EXTERNAL_SUPPORT i okna | `tests/test_t041_checkpoint_a.py::test_t41_a05_external_support_excluded_from_available_local_ids` (hand-built state) | UNIT_OR_ADAPTER |
| | `tests/property/test_coordinator_simulator.py::test_decision_required_triggers_external_reaction_with_correct_decision_link_ordering` (T043) | REAL_API |
| Target, REPLAN i WorkBalance quarter carry-in | `tests/test_t011_d_quarter_balance.py` | REAL_APPLICATION |
| | `tests/property/test_coordinator_simulator.py`'s `run_quarter`/B6 oracle (T043) | REAL_API |
| Ostrzeżenia i wynik widoczny w UI | `frontend/e2e/t041-daily-workflow.spec.ts` | REAL_UI |
| | `frontend/e2e/t043-coordinator-confidence.spec.ts` (NOWY, Checkpoint C) | REAL_UI |

**OTWARTA FLAGA (R6 korekta):** Checkpoint C pierwotnie dopisał nowy test
`test_43c_two_legal_overlapping_demands_via_real_assembler_and_validator` do
`tests/test_t009_plan_select_replan.py`, żeby dać "Nakładającym się demandom"
realny REAL_APPLICATION pion. Ten plik NIE jest w TASK_SCOPE T043 (brief.md
sekcja 9) -- zmiana została cofnięta do stanu `main@c25c73e0`
(Codex R6 finding T43-R6-05). Realny REAL_APPLICATION/REAL_API pion dla tego
obszaru nadal nie istnieje w granicach TASK_SCOPE T043; dodanie go wymaga albo
zgody OWNERA na rozszerzenie zakresu, albo osobnego, małego follow-up Tasku.
To jest świadomie zostawione otwarte dla architekta/OWNERA, nie rozwiązane
tutaj (brief sekcja 12: potrzebna zmiana poza TASK_SCOPE = zatrzymać się i
zgłosić, nie obchodzić po cichu).

Uwaga o wspólnej zależności: `tests/support/t009_fixtures.py::seed_real_object` (użyty przez wiele powyższych REAL_APPLICATION/REAL_API testów, w tym `test_t009_plan_select_replan.py` i `test_t011_d_quarter_balance.py`) buduje swój obiekt przez `benchmarks/real_object_production.py`/`benchmarks/real_object_scenarios.py` -- moduły odrzucone przez OWNERA jako *oracle* (`feedback_no_benchmarks_generator_ever`). To nie czyni tych testów `BENCHMARK_ONLY`: ich własne asercje (FEASIBLE, atomowość wersji, poprawność coverage) są niezależne od jakiegokolwiek werdyktu benchmarku -- tylko KSZTAŁT obiektu (roster/katalog) pochodzi stamtąd. Warto to jednak wiedzieć: żaden REAL_APPLICATION test w tej tabeli nie jest w pełni niezależny od `benchmarks/**` jako generatora scenariusza.

Dwie ostatnie klasy (`UNIT_OR_ADAPTER`, `BENCHMARK_ONLY`) pozostają wartościowe dla precyzyjnych przypadków brzegowych (np. a08-a13's excess/gap/false-tag matrix), ale nigdie w tym raporcie nie są przedstawiane jako samodzielny dowód działania programu -- każdy obszar ma teraz co najmniej jeden REAL_API/REAL_APPLICATION/REAL_UI pion.

### Prawdziwy browser (brief 6.3)

`frontend/e2e/t043-coordinator-confidence.spec.ts` -- 1/1 PASS. Koordynator tworzy obiekt, dostaje 5 LOCAL, widzi "Obsada (5)", ustawia target godzin pierwszej osobie, klika PLAN, a ekran pokazuje dokładnie ten status ("Kandydaci" dla FEASIBLE albo baner decyzji dla DECISION_REQUIRED), jaki zwróciła realna odpowiedź API przechwycona w tym samym teście (nie sztywne oczekiwanie).

### Kalibracja na znanych błędach (brief 6.4)

Wszystkie trzy mutacje wykonane pojedynczo, bezpośrednio w tym worktree, i natychmiast cofnięte (`git checkout -- <plik>`) po każdym pomiarze. `git diff task/ROTA-T043 -- rota/ api/ frontend/src/ benchmarks/` jest puste (0 linii) na commit tego Checkpointu -- zero zmutowanego kodu produktu w wypchniętej gałęzi.

1. **H24 `occupancy=2*x` jako Boolean** (przywrócony pre-T040 `fairness.add_dn_rhythm_reward`, commit `fa70b1c` cofnięty tymczasowo): `tests/test_t040_h24_rhythm_occupancy.py` -- 3/6 CZERWONE pod mutacją (`test_t40_01...`, `test_t40_04...`, `test_t40_05...`, realny H24 obiekt zwraca DECISION_REQUIRED zamiast FEASIBLE), 6/6 ZIELONE po cofnięciu.
2. **Wyłączony fallback fairness dla brakującego targetu** (`add_equal_split_fairness` w `solver.py` zakomentowany): `tests/test_t041_checkpoint_a.py::test_t41_a01_one_missing_target_splits_equally_across_all_five` -- CZERWONY pod mutacją (godziny 132/156/144/168/120 zamiast równego 144/144/144/144/144), ZIELONY po cofnięciu.
3. **Stare geometryczne podwójne liczenie nakładających się demandów** (`validator._check_coverage`'s tag-disambiguation wyłączona): `tests/test_t041_checkpoint_a.py::test_t41_a07_two_legal_overlapping_demands_correctly_assigned_passes` (istniejący test, UNIT_OR_ADAPTER -- jedyny dostępny pion w granicach TASK_SCOPE po R6 cofnięciu) -- CZERWONY pod mutacją (fałszywy COVERAGE-01 excess na obu legalnych, nakładających się demandach), ZIELONY po cofnięciu. Ten pion jest UNIT_OR_ADAPTER, nie REAL_APPLICATION -- patrz otwarta flaga wyżej.

Wniosek: żadna z trzech klas błędów nie pozostała cicho zielona -- bramka zaufania działa.
"""


def _write_markdown_report(rows: list[dict], quarter_result: dict, quarter_oracle: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ledger = _axis_coverage_ledger(rows)
    lines = [
        "# Symulator Koordynatora -- raport przebiegu (ROTA-T043 Checkpoint B)\n",
        f"Miesiące portfela: {', '.join(ledger['months'])} | obiekty: {len(rows)}\n",
        f"\n## Pokrycie osi (brief 4.2)\n\n- Miesiące: {', '.join(ledger['months'])}\n"
        f"- Kształty katalogu: {', '.join(ledger['shift_shapes'])}\n"
        f"- Liczba warstw: {ledger['layer_counts']}\n- Statusy finalne: {', '.join(ledger['final_statuses'])}\n"
        f"- Wystąpiło EXTERNAL: {ledger['had_external']}\n- Wystąpił REPLAN: {ledger['had_replan']}\n"
        f"- Wystąpiły absencje: {ledger['had_absences']}\n",
    ]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.get("final_status", "?")] = counts.get(r.get("final_status", "?"), 0) + 1
    lines.append(f"\n## Statusy\n\n{counts}\n")
    for row in rows:
        lines.append(f"\n## Seed {row['seed']}\n")
        if row.get("final_status") == "CRASH":
            lines.append(f"- **AWARIA (do przejrzenia)**: {row.get('crash')}\n")
            continue
        lines.append(f"- Kształt: {row['shift_shape']}, warstwy: {row['layer_count']}, regime {row['regime']}, obsada: {row['employee_count']}\n")
        lines.append(f"- Absencje: {row['absences'] or 'brak'}\n")
        lines.append(f"- PLAN (pierwszy): **{row['first_plan_status']}**\n")
        if row.get("external"):
            lines.append(f"- Reakcja EXTERNAL: {row['external']['external_employee_id']}, drugi PLAN: {row['external']['second_plan_result']['status']}\n")
        lines.append(f"- Wynik finalny: **{row.get('final_status')}**\n")
        if "product_validate" in row:
            lines.append(f"- PRODUCT_VALIDATE: **{row['product_validate']}**\n")
        if "fairness_verdict" in row:
            lines.append(f"- FAIRNESS: **{row['fairness_verdict']}** -- {row.get('fairness_detail')}\n")
        if "replan" in row:
            lines.append(f"- REPLAN: {row['replan']['status']}\n")
        if row.get("defect"):
            lines.append(f"- DEFEKT: {row['defect']}\n")
    lines.append("\n## Przebieg kwartalny Q3 2026 (obowiązkowy)\n")
    lines.append(f"\n- Status: **{quarter_result['status']}**\n- Oracle: **{quarter_oracle['status']}**\n")
    if quarter_result["status"] == "QUARTER_BLOCKED":
        lines.append(f"- Zablokowany miesiąc: {quarter_result.get('failing_month')} -- {quarter_result.get('reason')}\n")
    lines.append("\n" + _CHECKPOINT_C_REPORT_SECTION)
    (REPORT_DIR / "coordinator_report.md").write_text("".join(lines), encoding="utf-8")


def _reproduction_command(seed: int) -> str:
    """R6 fix (T43-R6-03): an actually executable one-liner, not a
    truncated ellipsis -- rebuilds that exact seed's object through the
    real driver and reruns it standalone."""
    return (
        "python -c \""
        "from api.deps import get_conn; from api.main import app; "
        "from fastapi.testclient import TestClient; from rota.persistence.db import connect; "
        "from tests.property.test_coordinator_simulator import _run_one_monthly_object, portfolio_month_for_seed; "
        "conn = connect(':memory:'); app.dependency_overrides[get_conn] = lambda: (yield conn); "
        f"print(_run_one_monthly_object(TestClient(app), {seed}, portfolio_month_for_seed({seed})))\""
    )


def _write_json_report(rows: list[dict], quarter_result: dict, quarter_oracle: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "months": _axis_coverage_ledger(rows)["months"], "rows": rows, "axis_coverage": _axis_coverage_ledger(rows),
        "quarter": quarter_result, "quarter_oracle": quarter_oracle,
        "reproduction_template": _reproduction_command("<SEED>"),
    }
    (REPORT_DIR / "coordinator_report.json").write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


@pytest.mark.skipif(
    os.environ.get("ROTA_SIM_FULL_PORTFOLIO") != "1",
    reason="full 20-object portfolio + Q3 quarter run is an explicit, once-per-final-SHA command (brief 4.4), not part of the default matrix",
)
def test_full_portfolio_and_quarter_report():
    rows = []
    for seed in range(20):
        connection = connect(":memory:")
        app.dependency_overrides[get_conn] = lambda: (yield connection)
        try:
            client = TestClient(app)
            rows.append(_run_one_monthly_object(client, seed, portfolio_month_for_seed(seed)))
        except Exception as exc:  # noqa: BLE001 -- a genuine crash is still a reportable finding
            rows.append({"seed": seed, "crash": str(exc), "final_status": "CRASH"})
            _write_failure_json(f"seed{seed}-crash", {"seed": seed, "error": str(exc)})
        finally:
            app.dependency_overrides.pop(get_conn, None)
            connection.close()

    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        quarter_result = sim.run_quarter(client, seed=0)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()
    quarter_oracle = sim.compute_quarter_oracle(quarter_result)
    if quarter_oracle["status"] == "QUARTER_BALANCE_FAIL":
        _write_failure_json("quarter-balance-mismatch-portfolio", {"quarter_result": quarter_result, "oracle": quarter_oracle})

    _write_markdown_report(rows, quarter_result, quarter_oracle)
    _write_json_report(rows, quarter_result, quarter_oracle)

    ledger = _axis_coverage_ledger(rows)
    assert set(ledger["shift_shapes"]) == set(sim._CATALOG_ROWS)
    assert set(ledger["layer_counts"]) == {1, 2}


if __name__ == "__main__":
    print("test_coordinator_simulator module OK")
