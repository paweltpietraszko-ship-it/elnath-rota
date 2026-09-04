"""ROTA-T054: persisted PLAN/REPLAN preview.

The one, current, unaccepted result of the last successful FEASIBLE
planning operation for (site_id, month) -- so leaving the screen or
reloading shows exactly what that operation returned, without re-running
the solver. NOT a ScheduleVersion status, NOT a history: overwritten by the
next FEASIBLE result for the same (site_id, month), and deleted the moment
its candidate is accepted (select_candidate) or explicitly rejected. A
pure snapshot of an already-computed rota.planning.engine_types.PlanningResult
-- no validator/solver logic lives here.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional

from rota.domain import Assignment, AssignmentRole, AssignmentState

# A-F2 (architect review): "replan" alone loses which REPLAN stage produced
# it -- a reload could not tell narrow (replan()/replan_retry_narrow()) from
# wide (replan_wider_search()) apart, so a subsequent "Szukaj dalej" could
# dispatch to the wrong continuation (retryNarrow instead of widerSearch).
OperationKind = Literal["plan", "replan_narrow", "replan_wide"]


@dataclass(frozen=True)
class PlanPreview:
    site_id: str
    month: date
    # The exact WORKING version this preview was computed against -- a
    # reader compares this to the CURRENT version to detect a stale preview
    # left behind by e.g. a REPLAN whose own solve never came back FEASIBLE.
    schedule_version_id: str
    candidates: list[list[Assignment]]
    warnings: list[str]
    optimization_complete: bool
    # R2-03 audit fix: which operation family produced this preview
    # ("plan" or "replan") -- without it, a reload can't tell which
    # continuation ("Szukaj dalej" on PLAN vs. on REPLAN's narrow/wide
    # stage) a further search should retry.
    operation_kind: OperationKind


def _assignment_to_dict(a: Assignment) -> dict:
    return {
        "assignment_id": a.assignment_id, "schedule_version_id": a.schedule_version_id, "employee_id": a.employee_id,
        "start_datetime": a.start_datetime.isoformat(), "end_datetime": a.end_datetime.isoformat(),
        "role": a.role.value, "state": a.state.value, "frozen": a.frozen,
        "covers_demand_id": a.covers_demand_id, "mentor_primary_assignment_id": a.mentor_primary_assignment_id,
        "operational_code": a.operational_code, "work_period_id": a.work_period_id,
        "required_rest_after_hours": a.required_rest_after_hours,
    }


def _assignment_from_dict(d: dict) -> Assignment:
    return Assignment(
        assignment_id=d["assignment_id"], schedule_version_id=d["schedule_version_id"], employee_id=d["employee_id"],
        start_datetime=datetime.fromisoformat(d["start_datetime"]), end_datetime=datetime.fromisoformat(d["end_datetime"]),
        role=AssignmentRole(d["role"]), state=AssignmentState(d["state"]), frozen=d["frozen"],
        covers_demand_id=d["covers_demand_id"], mentor_primary_assignment_id=d["mentor_primary_assignment_id"],
        operational_code=d["operational_code"], work_period_id=d["work_period_id"],
        required_rest_after_hours=d["required_rest_after_hours"],
    )


def _candidates_to_json(candidates: list[list[Assignment]]) -> str:
    return json.dumps([[_assignment_to_dict(a) for a in candidate] for candidate in candidates])


def _candidates_from_json(raw: str) -> list[list[Assignment]]:
    return [[_assignment_from_dict(d) for d in candidate] for candidate in json.loads(raw)]


def save_plan_preview_in_open_transaction(conn: sqlite3.Connection, preview: PlanPreview) -> None:
    """Atomic upsert, no separate commit -- caller (plan_ops) owns the
    transaction boundary. At most one current preview per (site_id, month):
    a new save always replaces whatever was there (OWNER decision 3)."""
    conn.execute(
        """INSERT INTO plan_previews (site_id, month, schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(site_id, month) DO UPDATE SET
            schedule_version_id=excluded.schedule_version_id,
            candidates_json=excluded.candidates_json,
            warnings_json=excluded.warnings_json,
            optimization_complete=excluded.optimization_complete,
            operation_kind=excluded.operation_kind""",
        (
            preview.site_id, preview.month.isoformat(), preview.schedule_version_id,
            _candidates_to_json(preview.candidates), json.dumps(list(preview.warnings)),
            int(preview.optimization_complete), preview.operation_kind,
        ),
    )


def save_plan_preview(conn: sqlite3.Connection, preview: PlanPreview) -> None:
    with conn:
        save_plan_preview_in_open_transaction(conn, preview)


def get_plan_preview(conn: sqlite3.Connection, site_id: str, month: date) -> Optional[PlanPreview]:
    row = conn.execute(
        "SELECT schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind "
        "FROM plan_previews WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    if row is None:
        return None
    schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind = row
    return PlanPreview(
        site_id=site_id, month=month, schedule_version_id=schedule_version_id,
        candidates=_candidates_from_json(candidates_json), warnings=json.loads(warnings_json),
        optimization_complete=bool(optimization_complete), operation_kind=operation_kind,
    )


def delete_plan_preview_in_open_transaction(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    conn.execute("DELETE FROM plan_previews WHERE site_id = ? AND month = ?", (site_id, month.isoformat()))


def delete_plan_preview(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    with conn:
        delete_plan_preview_in_open_transaction(conn, site_id, month)


if __name__ == "__main__":
    print("persistence.plan_preview_repository module OK")
