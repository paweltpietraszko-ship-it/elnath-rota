#!/usr/bin/env python3
"""
ROLE: run Wariant B (Symulator Koordynatora) full scenarios in parallel and
write one raw JSON report per seed. Lets anyone regenerate/expand the
manual-evaluation evidence directly, without going through an AI session.
Not part of the test suite -- a standalone, human-run tool.

CLI: run_variant_b_batch.py <start_seed> <end_seed> [--out DIR]
     [--replans N] [--workers N]
     <start_seed>/<end_seed> are inclusive.

Each worker runs one seed's full scenario (build object, absences, PLAN +
EXTERNAL loop if needed, select candidate, REPLAN) against a fresh
in-memory SQLite DB via the real API -- exactly what
tests/property/coordinator_simulator.py::run_full_scenario_b does.
num_search_workers=1 in the solver (rota/planning/solver.py) means running
many seeds as separate OS processes does not oversubscribe CPU.

OUTPUT: <out>/seed<N>.json per seed, printed per-seed status as it
completes, and a final SUMMARY line to stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_one(seed: int, replans: int) -> tuple[int, str, dict | None, str | None]:
    sys.path.insert(0, str(ROOT))
    from api.deps import get_conn
    from api.main import app
    from fastapi.testclient import TestClient
    from rota.persistence.db import connect
    from tests.property import coordinator_simulator as sim

    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        client = TestClient(app)
        result = sim.run_full_scenario_b(client, seed, num_replans=replans)
        spec = result["spec"]
        readback: dict = {}
        try:
            readback["analytics"] = sim.get_analytics(client, result["site_id"], spec.month)
        except Exception as exc:
            readback["analytics"] = {"error": str(exc)}
        try:
            readback["month_view"] = sim.get_month_view(client, result["site_id"], spec.month)
        except Exception as exc:
            readback["month_view"] = {"error": str(exc)}
        report = {
            "seed": seed, "month": spec.month.isoformat(), "regime": spec.regime,
            "atoms": [vars(a) for a in spec.atoms],
            "declared_local": sim.declared_roster_b(spec),
            "calculator_result": sim.layered_headcount_b(spec.atoms),
            "target_hours_per_employee": spec.target_hours_per_employee,
            "absence_draws": [vars(d) for d in result["absence_draws"]],
            "plan_result": result["plan_result"], "externals": result["externals"],
            "final_result": result["final_result"], "selected": result["selected"],
            "replan_results": result["replan_results"], "readback": readback,
            "reproduction": sim.reproduction_command_b(seed, len(result["replan_results"])),
        }
        return seed, report["final_result"]["status"], report, None
    except Exception as exc:
        return seed, "HARNESS_EXCEPTION", None, str(exc)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("start_seed", type=int)
    parser.add_argument("end_seed", type=int, help="inclusive")
    parser.add_argument("--out", default=None, help="output dir (default: tasks/ROTA-T044/round_01/tests/reports/adhoc_<start>-<end>)")
    parser.add_argument("--replans", type=int, default=1)
    parser.add_argument("--workers", type=int, default=8, help="parallel processes (default 8; safe up to CPU count, solver itself is single-threaded)")
    args = parser.parse_args()

    if args.end_seed < args.start_seed:
        parser.error("end_seed must be >= start_seed")

    out_dir = Path(args.out) if args.out else ROOT / "tasks" / "ROTA-T044" / "round_01" / "tests" / "reports" / f"adhoc_{args.start_seed}-{args.end_seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = list(range(args.start_seed, args.end_seed + 1))
    statuses: dict[int, str] = {}
    print(f"Running {len(seeds)} seed(s) with {args.workers} parallel worker(s) -> {out_dir}")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, seed, args.replans): seed for seed in seeds}
        for future in as_completed(futures):
            seed, status, report, error = future.result()
            statuses[seed] = status
            if report is not None:
                (out_dir / f"seed{seed}.json").write_text(
                    json.dumps(report, indent=2, default=str, ensure_ascii=False), encoding="utf-8",
                )
                print(f"seed {seed}: {status}")
            else:
                print(f"seed {seed}: HARNESS_EXCEPTION: {error}")

    print("SUMMARY:", {s: statuses[s] for s in sorted(statuses)})


if __name__ == "__main__":
    main()
