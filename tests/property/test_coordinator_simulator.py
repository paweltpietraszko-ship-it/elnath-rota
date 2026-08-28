"""ROTA-T038 (tasks/ROTA-T038/brief.md): Symulator Koordynatora pytest entry
point.

COORDINATOR SIMULATOR INVARIANTS -- Rota's own already-published contract
promises, not new requirements invented for this test:

1. No seed ever raises an exception or returns a 5xx.
2. PLAN status is always one of FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.
3. When the generator built sufficient staffing, status MUST be FEASIBLE
   (catches a false DECISION_REQUIRED/TECHNICAL_ERROR).
4. Every FEASIBLE candidate, independently re-validated via
   rota.planning.validator.validate(), has hard_pass=True (catches
   solver/validator drift -- the same question REAL_OBJECT_BENCHMARK.md
   asks, on many random inputs instead of one frozen one).
5. mark-not-worked (a HARD-violation-creating manual correction) never
   blocks the save (still 200) and its COVERAGE deviation appears in the
   response.
6. finalize with the exact current deviation set succeeds; with a stale/
   wrong set it is rejected.

Default run is DEELIBERATELY small (see DEFAULT_SEED_COUNT) -- this suite
runs a real CP-SAT solve per seed and must not become the kind of slow
sweep that eats session budget. Set ROTA_SIM_SEEDS=500 for a deep,
manual/overnight run. Any seed that ever finds a real bug gets added to
REGRESSION_SEEDS below so it is never silently dropped from coverage
again -- do not remove entries from that tuple without a note explaining
why the bug class it caught is now provably unreachable.
"""
from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from tests.property.coordinator_simulator import (
    build_object,
    find_planned_primary,
    independently_revalidate,
    random_object_spec,
)

MONTH = date(2026, 9, 1)
DEFAULT_SEED_COUNT = 10

# Seeds that previously reproduced a real bug -- always checked, regardless
# of DEFAULT_SEED_COUNT/ROTA_SIM_SEEDS.
REGRESSION_SEEDS: tuple[int, ...] = ()


def _seeds() -> list[int]:
    count = int(os.environ.get("ROTA_SIM_SEEDS", DEFAULT_SEED_COUNT))
    return sorted(set(range(count)) | set(REGRESSION_SEEDS))


def _assignment_in(a: dict) -> dict:
    return {k: v for k, v in a.items() if k != "employee_display_name"}


def _run_one_seed(seed: int) -> None:
    conn = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app)
        spec = random_object_spec(seed, MONTH)

        site_id = build_object(client, conn, spec)

        plan_resp = client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/plan",
            json={"effective_from": MONTH.isoformat()},
        )
        assert plan_resp.status_code == 200, f"seed={seed} spec={spec}: {plan_resp.text}"
        result = plan_resp.json()

        assert result["status"] in ("FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"), (
            f"seed={seed} spec={spec}: illegal PLAN status {result['status']!r}"
        )
        assert result["status"] != "TECHNICAL_ERROR", f"seed={seed} spec={spec}: {result['error_message']}"

        if spec.sufficient_staffing:
            assert result["status"] == "FEASIBLE", (
                f"seed={seed} spec={spec}: sufficient staffing but got {result['status']!r} "
                f"(warnings={result['warnings']}, decision_payload={result['decision_payload']})"
            )
        else:
            if result["status"] == "DECISION_REQUIRED":
                payload = result["decision_payload"]
                assert payload is not None, f"seed={seed}: DECISION_REQUIRED with no payload"
                assert payload["blocking_shift_demands"] or payload["blockers"] or payload["load_blocker"], (
                    f"seed={seed}: DECISION_REQUIRED payload carries no evidence: {payload}"
                )
            return  # insufficient-staffing seeds stop here -- no candidate to select

        candidate = result["candidates"][0]
        select_resp = client.post(
            f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/select-candidate",
            json={"candidate": [_assignment_in(a) for a in candidate]},
        )
        assert select_resp.status_code == 204, f"seed={seed}: {select_resp.text}"

        view_resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}")
        assert view_resp.status_code == 200
        view = view_resp.json()
        version_id = view["current_version"]["version_id"]

        # Invariant 4: independent re-validation of the persisted candidate.
        assert independently_revalidate(conn, site_id, MONTH, version_id), (
            f"seed={seed} spec={spec}: solver/validator disagreement on a persisted FEASIBLE candidate"
        )

        # Invariant 5: mark-not-worked on ~1 in 3 seeds (deterministic on seed).
        if seed % 3 == 0:
            target = find_planned_primary(conn, version_id)
            if target is not None:
                nn_resp = client.post(
                    f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/manual-correction/mark-not-worked",
                    json={"effective_from": MONTH.isoformat(), "assignment_id": target.assignment_id},
                )
                assert nn_resp.status_code == 200, f"seed={seed}: mark-not-worked blocked: {nn_resp.text}"
                nn_body = nn_resp.json()
                assert any(d["category"] == "COVERAGE" for d in nn_body["deviations"]), (
                    f"seed={seed}: mark-not-worked left no COVERAGE deviation: {nn_body}"
                )

        # Invariant 6: finalize needs the EXACT current deviation set.
        view_resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}")
        current_deviation_ids = [d["deviation_id"] for d in view_resp.json()["deviations"]]

        if current_deviation_ids:
            # An empty ack set is only "wrong" when real deviations exist --
            # otherwise it IS the correct call and must not be repeated
            # (the version is already FINAL and a second finalize legitimately 409s).
            wrong_finalize = client.post(
                f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/finalize",
                json={"acknowledged_deviation_ids": []},
            )
            assert wrong_finalize.status_code != 204, f"seed={seed}: finalize accepted an empty ack set with real deviations present"

            finalize_resp = client.post(
                f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/finalize",
                json={"acknowledged_deviation_ids": current_deviation_ids},
            )
            assert finalize_resp.status_code == 204, f"seed={seed}: finalize with exact ack set rejected: {finalize_resp.text}"
        else:
            finalize_resp = client.post(
                f"/api/workspace/sites/{site_id}/schedule/{MONTH.isoformat()}/finalize",
                json={"acknowledged_deviation_ids": []},
            )
            assert finalize_resp.status_code == 204, f"seed={seed}: finalize with no deviations rejected: {finalize_resp.text}"
    finally:
        app.dependency_overrides.pop(get_conn, None)
        conn.close()


@pytest.mark.parametrize("seed", _seeds())
def test_coordinator_simulator(seed: int) -> None:
    _run_one_seed(seed)


if __name__ == "__main__":
    print("test_coordinator_simulator module OK")
