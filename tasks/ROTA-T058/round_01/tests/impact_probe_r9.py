"""Read-only-style operational T058 probe; run only against a disposable DB copy."""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, timedelta
import time

from rota.application.assembler import assemble_planning_state
from rota.domain import AssignmentRole, AssignmentState, MembershipKind
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.engine import plan


def _triple_windows(assignments) -> int:
    dates: dict[str, set[date]] = {}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY or assignment.state == AssignmentState.CANCELLED:
            continue
        dates.setdefault(assignment.employee_id, set()).add(assignment.start_datetime.date())
    return sum(
        1
        for employee_dates in dates.values()
        for day in employee_dates
        if day + timedelta(days=1) in employee_dates and day + timedelta(days=2) in employee_dates
    )


def _run(state):
    started = time.perf_counter()
    result = plan(state)
    elapsed = time.perf_counter() - started
    candidate_triples = None
    if result.status == "FEASIBLE" and result.candidates:
        candidate_triples = _triple_windows(result.candidates[0])
    detail = result.error_message
    if result.decision_payload is not None:
        detail = ",".join(
            sorted(
                {
                    str(getattr(blocker, "rule_code", getattr(blocker, "rule_version_id", "unknown")))
                    for blocker in result.decision_payload.blockers
                }
            )
        )
    return result.status, round(elapsed, 3), candidate_triples, detail


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("db")
    parser.add_argument("--month", default="2026-09-01")
    parser.add_argument("--cutover", default="2026-09-09T12:00:00")
    parser.add_argument("--object-index", type=int, action="append")
    args = parser.parse_args()
    month = date.fromisoformat(args.month)
    cutover = datetime.fromisoformat(args.cutover)

    conn = connect(args.db)  # migrations are allowed only because db is a disposable copy
    rows = conn.execute(
        "SELECT site_id, version_id FROM current_schedule_versions WHERE month=? ORDER BY site_id",
        (month.isoformat(),),
    ).fetchall()
    print(f"MONTH={month} OBJECTS={len(rows)}")
    for index, (site_id, version_id) in enumerate(rows, start=1):
        if args.object_index is not None and index not in args.object_index:
            continue
        state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
        snapshot = get_schedule_snapshot(conn, version_id)
        local_count = sum(
            membership.enabled and membership.membership_kind == MembershipKind.LOCAL
            for membership in state.memberships
        )
        current_triples = _triple_windows(snapshot.assignments)
        fresh = replace(state, existing_assignments=(), deviations=(), cutover_at=None)
        live = replace(state, cutover_at=cutover)
        fresh_status, fresh_seconds, fresh_triples, fresh_detail = _run(fresh)
        live_status, live_seconds, live_triples, live_detail = _run(live)
        print(
            f"OBJECT={index} LOCAL={local_count} DEMANDS={len(state.shift_demands)} "
            f"CURRENT_TRIPLES={current_triples} "
            f"FRESH={fresh_status}/{fresh_seconds}s/triples={fresh_triples}/detail={fresh_detail} "
            f"LIVE={live_status}/{live_seconds}s/triples={live_triples}/detail={live_detail}"
        )


if __name__ == "__main__":
    main()
