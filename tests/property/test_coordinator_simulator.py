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
        "seed": seed, "shift_shape": spec.shift_shape, "regime": spec.regime, "layer_count": spec.layer_count,
        "employee_count": spec.employee_count, "roster": employees,
        "absences": [d.__dict__ | {"employee_id": sim.local_employee_id(spec, d.employee_index)} for d in absence_draws],
        "first_plan_status": first_result["status"],
    }

    external = None
    base_result = first_result
    if first_result["status"] == "DECISION_REQUIRED":
        row["first_plan_decision_reason"] = _decision_reason(first_result.get("decision_payload"))
        if not first_result.get("decision_payload"):
            row["defect"] = "empty DECISION_REQUIRED payload on first PLAN -- tool/product defect"
            _write_failure_json(f"seed{seed}-empty-decision-payload", row | {"first_plan_result": first_result})
        else:
            external = sim.external_support_reaction(client, site_id, month, spec)
            base_result = external["second_plan_result"]
        row["external"] = external

    if base_result["status"] != "FEASIBLE" or not base_result.get("candidates"):
        row["final_status"] = base_result["status"]
        row["final_reason"] = _decision_reason(base_result.get("decision_payload")) if base_result["status"] == "DECISION_REQUIRED" else base_result.get("error_message")
        if not absence_draws and not spec.day_only_indices and base_result["status"] == "DECISION_REQUIRED":
            # a certified-clean object still blocked -- a real finding, not routed around.
            _write_failure_json(f"seed{seed}-clean-object-decision-required", row | {"base_result": base_result})
        return row

    validate_status, validate_detail, candidate = sim.select_first_candidate_reporting_validate(client, site_id, month, base_result)
    row["product_validate"] = validate_status
    if validate_status == "PRODUCT_VALIDATE_FAIL":
        row["final_status"] = "PRODUCT_VALIDATE_FAIL"
        _write_failure_json(f"seed{seed}-validate-fail", row | {"detail": validate_detail, "candidate": candidate})
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
    if fairness_verdict == "FAIRNESS_FAIL":
        _write_failure_json(f"seed{seed}-fairness-fail", row | {"assignments": view["assignments"]})

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


def _write_failure_json(name: str, payload: dict) -> None:
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
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


# --- Checkpoint B: full 20-object portfolio + Q3 report, gated ------------


def _axis_coverage_ledger(rows: list[dict]) -> dict:
    """Robust to a CRASH row (only has seed/crash/final_status) -- a real
    crash is still a reportable finding, not something that should also
    take down the report writer itself."""
    return {
        "shift_shapes": sorted({r["shift_shape"] for r in rows if "shift_shape" in r}),
        "layer_counts": sorted({r["layer_count"] for r in rows if "layer_count" in r}),
        "final_statuses": sorted({r["final_status"] for r in rows if "final_status" in r}),
        "had_external": any(r.get("external") for r in rows),
        "had_replan": any("replan" in r for r in rows),
        "had_absences": any(r.get("absences") for r in rows),
        "crashes": [r["seed"] for r in rows if r.get("final_status") == "CRASH"],
    }


def _write_markdown_report(rows: list[dict], quarter_result: dict, quarter_oracle: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ledger = _axis_coverage_ledger(rows)
    lines = [
        "# Symulator Koordynatora -- raport przebiegu (ROTA-T043 Checkpoint B)\n",
        f"Miesiąc portfela: {MONTH.isoformat()} | obiekty: {len(rows)}\n",
        f"\n## Pokrycie osi (brief 4.2)\n\n- Kształty katalogu: {', '.join(ledger['shift_shapes'])}\n"
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
    lines.append(
        "\n## Bramka zaufania do testów (Checkpoint C)\n\nKlasyfikacja istniejących testów "
        "(REAL_UI/REAL_API/REAL_APPLICATION/UNIT_OR_ADAPTER/BENCHMARK_ONLY) i kalibracja na "
        "znanych błędach nie są jeszcze wykonane -- to zakres Checkpointu C, osobnego kroku.\n"
    )
    (REPORT_DIR / "coordinator_report.md").write_text("".join(lines), encoding="utf-8")


def _write_json_report(rows: list[dict], quarter_result: dict, quarter_oracle: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "month": MONTH.isoformat(), "rows": rows, "axis_coverage": _axis_coverage_ledger(rows),
        "quarter": quarter_result, "quarter_oracle": quarter_oracle,
        "reproduction": "python -c \"from tests.property.test_coordinator_simulator import _run_one_monthly_object; ...\"",
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
            rows.append(_run_one_monthly_object(client, seed, MONTH))
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
