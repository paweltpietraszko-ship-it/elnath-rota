"""ROTA-T038 (tasks/ROTA-T038/brief.md, KOREKTA 3): Symulator Koordynatora
pytest entry point.

This does NOT judge whether the solver is right (see
coordinator_simulator.py's module docstring). It runs many invented,
internally-consistent objects (staffing derived from each object's own
hourly workload, no margin, no pre-provisioned external support) through
randomly-drawn absence combinations, drives the real PLAN endpoint --
reactively hiring one more LOCAL employee and re-PLANning on
DECISION_REQUIRED, exactly as a real coordinator must (owner ruling
2026-08-28: "musi kogoś znaleźć, choćby miał siedzieć na obiekcie sam") --
and writes a human-readable report of what happened. REPLAN is a DISTINCT,
separately-reported mid-month event, never an automatic step after an
already-successful PLAN. The ONLY assertion is "nothing crashed" -- every
other outcome is a reported fact, not a pass/fail judgment.

Default run is small (see DEFAULT_SEED_COUNT) -- each seed can run several
real CP-SAT solves (one per hire attempt, plus REPLAN on the mid-month
seeds) and must not become a slow sweep that eats session budget.
ROTA_SIM_SEEDS=<N> for a deeper manual run.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from tests.property.coordinator_simulator import (
    apply_absences,
    build_object,
    declared_roster,
    hire_one_more_local,
    local_employee_id,
    random_absence_set,
    random_object_spec,
)

MONTH = date(2026, 9, 1)
DEFAULT_SEED_COUNT = 5  # each seed can run several real solves -- keep the default sweep bounded
MAX_HIRES = 4  # a coordinator keeps finding people, but the simulator caps attempts to keep a seed bounded
REPORT_PATH = Path(__file__).resolve().parents[2] / "tasks" / "ROTA-T038" / "round_01" / "tests" / "simulator_report.md"


def _seeds() -> list[int]:
    return list(range(int(os.environ.get("ROTA_SIM_SEEDS", DEFAULT_SEED_COUNT))))


def _absence_lines(draws, spec) -> str:
    if not draws:
        return "brak (wszyscy dostępni)"
    return "; ".join(
        f"{local_employee_id(spec, d.employee_index)}: {d.kind} {d.start_date.isoformat()}..{d.end_date.isoformat()}"
        for d in draws
    )


def _decision_reason(payload: dict | None) -> str:
    if payload is None:
        return "-"
    parts = [b["condition"] for b in payload.get("blockers", [])]
    parts += payload.get("unblocking_options", [])
    return " | ".join(parts) if parts else "(brak szczegółów w payloadzie)"


def _assignment_in(a: dict) -> dict:
    return {k: v for k, v in a.items() if k != "employee_display_name"}


def _used_employees(candidate: list[dict]) -> list[str]:
    return sorted({a["employee_id"] for a in candidate})


def _run_plan(client: TestClient, site_id: str) -> dict:
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/plan", json={"effective_from": MONTH.isoformat()})
    resp.raise_for_status()
    return resp.json()


def _select_first_candidate(client: TestClient, site_id: str, result: dict) -> None:
    candidate = result["candidates"][0]
    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/select-candidate",
        json={"candidate": [_assignment_in(a) for a in candidate]},
    )
    resp.raise_for_status()


def _run_replan(client: TestClient, site_id: str) -> dict:
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/replan", json={"effective_from": MONTH.isoformat()})
    resp.raise_for_status()
    return resp.json()


def _phase_facts(result: dict) -> tuple[str, str, list[str]]:
    status = result["status"]
    if status == "FEASIBLE":
        return status, "-", _used_employees(result["candidates"][0]) if result["candidates"] else []
    if status == "TECHNICAL_ERROR":
        return status, f"DO PRZEJRZENIA: {result.get('error_message')}", []
    return status, _decision_reason(result.get("decision_payload")), []


def _plan_with_reactive_hiring(client: TestClient, site_id: str, spec) -> tuple[dict, int, list[str]]:
    """PLAN, then -- exactly as a real coordinator must -- hire one more
    LOCAL and PLAN again on DECISION_REQUIRED, up to MAX_HIRES times.
    Returns (final plan result, employee_count after hiring, hire log)."""
    employee_count = spec.employee_count
    hires: list[str] = []
    result = _run_plan(client, site_id)
    attempts = 0
    while result["status"] == "DECISION_REQUIRED" and attempts < MAX_HIRES:
        new_id = hire_one_more_local(client, site_id, spec, employee_count)
        hires.append(new_id)
        employee_count += 1
        attempts += 1
        result = _run_plan(client, site_id)
    return result, employee_count, hires


def _maybe_replan_mid_month(client: TestClient, site_id: str, spec, employee_count: int, seed: int) -> dict:
    """A DISTINCT, separately-reported scenario -- never automatic after a
    successful PLAN. Deterministic on seed (even seeds only) so the report
    is reproducible and this is describable without another hidden draw."""
    if seed % 2 != 0:
        return {"status": "nie dotyczy", "reason": "brak zdarzenia w trakcie miesiąca (nieparzysty seed)", "used": []}
    # Mid-month, post-select-candidate: SICK_LEAVE is the ONE fully-supported
    # path (see arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md).
    mid_month_draws = random_absence_set(seed * 104729, spec, employee_count, allow_sick_leave=True)
    if not mid_month_draws:
        return {"status": "nie dotyczy", "reason": "wylosowano zero zdarzeń w trakcie miesiąca", "used": []}
    apply_absences(client, site_id, spec, mid_month_draws)
    result = _run_replan(client, site_id)
    status, reason, used = _phase_facts(result)
    return {"status": status, "reason": reason, "used": used, "absences": _absence_lines(mid_month_draws, spec)}


def _run_one_seed(seed: int) -> dict:
    """Returns one report row dict. Raises only on a genuine crash/5xx --
    every other outcome is captured as data, not raised."""
    conn = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    row: dict = {"seed": seed}
    try:
        client = TestClient(app)
        spec = random_object_spec(seed, MONTH)
        # Before any PLAN exists: SICK_LEAVE excluded, see
        # arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md -- a known,
        # reported product gap (IncompleteAbsenceReferenceError -> 500),
        # not something to silently route around by testing it anyway.
        initial_draws = random_absence_set(seed, spec, spec.employee_count, allow_sick_leave=False)
        row.update(
            shift_shape=spec.shift_shape, regime=spec.regime, monthly_hours_needed=spec.monthly_hours_needed,
            initial_roster=declared_roster(spec, spec.employee_count), absences=_absence_lines(initial_draws, spec),
        )

        site_id = build_object(client, conn, spec)
        apply_absences(client, site_id, spec, initial_draws)

        plan_result, final_count, hires = _plan_with_reactive_hiring(client, site_id, spec)
        plan_status, plan_reason, plan_used = _phase_facts(plan_result)
        row.update(
            hires=hires, final_roster=declared_roster(spec, final_count),
            plan_status=plan_status, plan_reason=plan_reason, plan_used=plan_used,
        )

        if plan_status != "FEASIBLE" or not plan_result["candidates"]:
            row["replan"] = {"status": "pominięto", "reason": "brak grafiku bazowego po wyczerpaniu prób zatrudnienia", "used": []}
            return row

        _select_first_candidate(client, site_id, plan_result)
        row["replan"] = _maybe_replan_mid_month(client, site_id, spec, final_count, seed)
        return row
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


def _write_report(rows: list[dict], crashes: list[tuple[int, str]]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Symulator Koordynatora -- raport przebiegu\n",
        f"Miesiąc: {MONTH.isoformat()} | seedy: {len(rows) + len(crashes)}\n",
        "\nZnany, zgłoszony brak: SICK_LEAVE przed pierwszym PLAN nie jest tu "
        "testowane (patrz arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md) "
        "-- SICK_LEAVE po select-candidate/przed REPLAN jest w pełni testowane.\n",
    ]
    for row in rows:
        lines.append(f"\n## Seed {row['seed']}\n")
        lines.append(f"- Zapotrzebowanie: {row['shift_shape']}, regime {row['regime']}, {row['monthly_hours_needed']}h/mies.\n")
        lines.append(f"- Obiekt startowy ({len(row['initial_roster'])} osób): {', '.join(row['initial_roster'])}\n")
        lines.append(f"- Absencje (przed pierwszym PLAN): {row['absences']}\n")
        if row["hires"]:
            lines.append(f"- Koordynator dopisał w reakcji na DECISION_REQUIRED: {', '.join(row['hires'])}\n")
        lines.append(f"- PLAN (finalny): **{row['plan_status']}** -- {row['plan_reason']}\n")
        if row["plan_used"]:
            declared = row["final_roster"]
            mismatch = " *(ROZBIEŻNOŚĆ vs deklaracja!)*" if set(row["plan_used"]) - set(declared) else ""
            lines.append(f"  - Użyte osoby ({len(row['plan_used'])}): {', '.join(row['plan_used'])}{mismatch}\n")
        rp = row["replan"]
        if "absences" in rp:
            lines.append(f"- Absencje (zdarzenie w trakcie miesiąca): {rp['absences']}\n")
        lines.append(f"- REPLAN: **{rp['status']}** -- {rp['reason']}\n")
        if rp["used"]:
            declared = row["final_roster"]
            mismatch = " *(ROZBIEŻNOŚĆ vs deklaracja!)*" if set(rp["used"]) - set(declared) else ""
            lines.append(f"  - Użyte osoby ({len(rp['used'])}): {', '.join(rp['used'])}{mismatch}\n")
    if crashes:
        lines.append("\n## Awarie (do przejrzenia)\n")
        for seed, error in crashes:
            lines.append(f"- Seed {seed}: {error}\n")
    REPORT_PATH.write_text("".join(lines), encoding="utf-8")


def test_coordinator_simulator_report() -> None:
    rows, crashes = [], []
    for seed in _seeds():
        try:
            rows.append(_run_one_seed(seed))
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: any crash is reported, not swallowed
            crashes.append((seed, str(exc)))
    _write_report(rows, crashes)
    if crashes:
        pytest.fail(f"{len(crashes)} seed(y) zakończone wyjątkiem/5xx: {crashes}")


if __name__ == "__main__":
    print("test_coordinator_simulator module OK")
