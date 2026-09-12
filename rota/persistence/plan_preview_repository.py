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

from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftCatalogKind, ShiftDemand, ShiftKind
from rota.persistence import pii_crypto

# ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE brief.md section 2.1:
# constant class label bound into warnings_json's AAD alongside site_id and
# month, so a full ciphertext swap between two different (site, month)
# previews fails closed (L4a) instead of decrypting as if it belonged here.
_WARNINGS_AAD_CLASS = "PLAN_PREVIEW_WARNINGS"


def _warnings_aad(site_id: str, month: date) -> bytes:
    return pii_crypto.bind_aad(_WARNINGS_AAD_CLASS, site_id, month.isoformat())

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
    # ARCHITECT_DECISION 2026-09-06 (BOARD.md ROTA-T057): None before the
    # very first ScheduleVersion for (site_id, month) has ever been created
    # -- a preview may now exist before any real version does (T57-01).
    schedule_version_id: Optional[str]
    candidates: list[list[Assignment]]
    warnings: list[str]
    optimization_complete: bool
    # R2-03 audit fix: which operation family produced this preview
    # ("plan" or "replan") -- without it, a reload can't tell which
    # continuation ("Szukaj dalej" on PLAN vs. on REPLAN's narrow/wide
    # stage) a further search should retry.
    operation_kind: OperationKind
    # ROTA-T057: only meaningful (non-None) while schedule_version_id is
    # None -- the coordinator-supplied effective_from for the very first
    # ScheduleVersion of this (site_id, month), captured at PLAN time and
    # carried forward so select_candidate can create that first version at
    # acceptance without asking the caller to resupply it.
    effective_from: Optional[date] = None
    # ROTA-T057: the demands this preview's candidates were solved against.
    # Needed so the coordinator-facing grid can show D/N labels for a
    # not-yet-accepted candidate even when no ScheduleVersion exists yet to
    # source demands from (GET /schedule/{month} otherwise has nothing to
    # return demands from before acceptance).
    shift_demands: list[ShiftDemand] = ()


def _shift_demand_to_dict(d: ShiftDemand) -> dict:
    return {
        "demand_id": d.demand_id, "schedule_version_id": d.schedule_version_id,
        "start_datetime": d.start_datetime.isoformat(), "end_datetime": d.end_datetime.isoformat(),
        "required_primary_count": d.required_primary_count,
        "shift_kind": d.shift_kind.value if d.shift_kind else None,
        "catalog_kind": d.catalog_kind.value if d.catalog_kind else None,
        "required_rest_hours": d.required_rest_hours,
        "work_period_template_id": d.work_period_template_id, "work_period_component": d.work_period_component,
        "emergency_24h_rest_hours": d.emergency_24h_rest_hours,
    }


def _shift_demand_from_dict(d: dict) -> ShiftDemand:
    return ShiftDemand(
        demand_id=d["demand_id"], schedule_version_id=d["schedule_version_id"],
        start_datetime=datetime.fromisoformat(d["start_datetime"]), end_datetime=datetime.fromisoformat(d["end_datetime"]),
        required_primary_count=d["required_primary_count"],
        shift_kind=ShiftKind(d["shift_kind"]) if d["shift_kind"] else None,
        catalog_kind=ShiftCatalogKind(d["catalog_kind"]) if d["catalog_kind"] else None,
        required_rest_hours=d["required_rest_hours"],
        work_period_template_id=d["work_period_template_id"], work_period_component=d["work_period_component"],
        emergency_24h_rest_hours=d["emergency_24h_rest_hours"],
    )


def _shift_demands_to_json(demands: list[ShiftDemand]) -> str:
    return json.dumps([_shift_demand_to_dict(d) for d in demands])


def _shift_demands_from_json(raw: str) -> list[ShiftDemand]:
    return [_shift_demand_from_dict(d) for d in json.loads(raw)]


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
        """INSERT INTO plan_previews (site_id, month, schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind, effective_from, shift_demands_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(site_id, month) DO UPDATE SET
            schedule_version_id=excluded.schedule_version_id,
            candidates_json=excluded.candidates_json,
            warnings_json=excluded.warnings_json,
            optimization_complete=excluded.optimization_complete,
            operation_kind=excluded.operation_kind,
            effective_from=excluded.effective_from,
            shift_demands_json=excluded.shift_demands_json""",
        (
            preview.site_id, preview.month.isoformat(), preview.schedule_version_id,
            _candidates_to_json(preview.candidates),
            pii_crypto.encrypt_text(
                pii_crypto.resolve_key(conn), json.dumps(list(preview.warnings)),
                _warnings_aad(preview.site_id, preview.month),
            ),
            int(preview.optimization_complete), preview.operation_kind,
            preview.effective_from.isoformat() if preview.effective_from else None,
            _shift_demands_to_json(list(preview.shift_demands)),
        ),
    )


def save_plan_preview(conn: sqlite3.Connection, preview: PlanPreview) -> None:
    with conn:
        save_plan_preview_in_open_transaction(conn, preview)


def _row_to_preview(key: bytes, site_id: str, month: date, row: tuple) -> PlanPreview:
    (schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind,
     effective_from, shift_demands_json) = row
    warnings_plaintext = pii_crypto.decrypt_text(key, warnings_json, _warnings_aad(site_id, month))
    return PlanPreview(
        site_id=site_id, month=month, schedule_version_id=schedule_version_id,
        candidates=_candidates_from_json(candidates_json), warnings=json.loads(warnings_plaintext),
        optimization_complete=bool(optimization_complete), operation_kind=operation_kind,
        effective_from=date.fromisoformat(effective_from) if effective_from else None,
        shift_demands=_shift_demands_from_json(shift_demands_json) if shift_demands_json else [],
    )


def get_plan_preview(conn: sqlite3.Connection, site_id: str, month: date) -> Optional[PlanPreview]:
    row = conn.execute(
        "SELECT schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind, effective_from, shift_demands_json "
        "FROM plan_previews WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    if row is None:
        return None
    return _row_to_preview(pii_crypto.resolve_key(conn), site_id, month, row)


def get_plan_preview_with_key(conn: sqlite3.Connection, site_id: str, month: date, key: bytes) -> Optional[PlanPreview]:
    """Same as get_plan_preview but decrypts warnings_json with an
    externally-supplied key rather than resolve_key(conn) -- for
    disaster-recovery flows reading a detached snapshot copy
    (rota/application/backup.py), which has no meaningful keystore of
    its own to resolve (brief.md section 6/L7)."""
    row = conn.execute(
        "SELECT schedule_version_id, candidates_json, warnings_json, optimization_complete, operation_kind, effective_from, shift_demands_json "
        "FROM plan_previews WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    if row is None:
        return None
    return _row_to_preview(key, site_id, month, row)


def delete_plan_preview_in_open_transaction(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    conn.execute("DELETE FROM plan_previews WHERE site_id = ? AND month = ?", (site_id, month.isoformat()))


def delete_plan_preview(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    with conn:
        delete_plan_preview_in_open_transaction(conn, site_id, month)


# ROTA-T057: pre-acceptance REPLAN "podejscie" (attempt) memory -- OWNER_RULING
# (BOARD.md, 2026-09-06): each subsequent REPLAN variant must differ by
# >=15% staffing from EVERY variant already shown in this attempt, not just
# the last one, and this memory must survive a reload. A "signature" here is
# the T017 canonical S(C): a list of [demand_id, employee_id] pairs actually
# selected (mirrors solver._candidate_signature's frozenset shape, JSON has
# no frozenset so it round-trips as a list of 2-item lists).
Signature = frozenset


def _signature_to_json(signature: frozenset[tuple[str, str]]) -> str:
    return json.dumps([list(pair) for pair in sorted(signature)])


def _signature_from_json(raw: str) -> frozenset[tuple[str, str]]:
    return frozenset(tuple(pair) for pair in json.loads(raw))


def get_attempt_signatures(conn: sqlite3.Connection, site_id: str, month: date) -> list[frozenset[tuple[str, str]]]:
    rows = conn.execute(
        "SELECT signature_json FROM plan_attempt_signatures WHERE site_id = ? AND month = ? ORDER BY seq",
        (site_id, month.isoformat()),
    ).fetchall()
    return [_signature_from_json(row[0]) for row in rows]


def append_attempt_signature_in_open_transaction(
    conn: sqlite3.Connection, site_id: str, month: date, signature: frozenset[tuple[str, str]],
) -> None:
    """Appends one more shown-variant signature to the active attempt.
    Caller (plan_ops) is responsible for having cleared prior signatures
    when a NEW attempt starts (fresh PLAN with no existing preview, or
    after an explicit reject) -- this function only ever adds."""
    next_seq = conn.execute(
        "SELECT COALESCE(MAX(seq), -1) + 1 FROM plan_attempt_signatures WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO plan_attempt_signatures (site_id, month, seq, signature_json) VALUES (?, ?, ?, ?)",
        (site_id, month.isoformat(), next_seq, _signature_to_json(signature)),
    )


def clear_attempt_signatures_in_open_transaction(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    """Ends the active attempt -- called when a fresh PLAN starts a new one,
    on explicit 'Odrzuc wynik', and on acceptance (the accepted variant is no
    longer a 'shown alternative' to diverge from, it's now the schedule)."""
    conn.execute("DELETE FROM plan_attempt_signatures WHERE site_id = ? AND month = ?", (site_id, month.isoformat()))


def clear_attempt_signatures(conn: sqlite3.Connection, site_id: str, month: date) -> None:
    with conn:
        clear_attempt_signatures_in_open_transaction(conn, site_id, month)


if __name__ == "__main__":
    print("persistence.plan_preview_repository module OK")
