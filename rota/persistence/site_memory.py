"""SiteMemory retrieval / history API (tasks/ROTA-T005/brief.md RETRIEVAL / HISTORY API,
EFFECTIVE SELECTION).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime
from typing import Optional

from rota.persistence.site_rule_repository import get_site_rule_version
from rota.planning.engine_types import BlockingDemand, Blocker, DecisionRequiredPayload, LoadBlocker, UnblockingOption
from rota.site_memory_types import (
    ActionSourceKind,
    AffectedEntity,
    CoordinatorActionKind,
    CoordinatorActionRecord,
    DecisionRecord,
    DecisionRequiredSnapshotRecord,
    EffectiveRule,
    EffectiveSelection,
    NoActiveRule,
)

_DECISION_COLUMNS = (
    "decision_id, site_id, rule_id, chain_seq, statement, coordinator_id, "
    "recorded_at, effective_from, rule_version_id, rel, predecessor_decision_id"
)


class DecisionRecordNotFound(Exception):
    """Raised when a decision_id or rule_version_id has no owning decision."""


def _row_to_decision(row: tuple) -> DecisionRecord:
    (
        decision_id, site_id, rule_id, chain_seq, statement, coordinator_id,
        recorded_at, effective_from, rule_version_id, rel, predecessor_decision_id,
    ) = row
    return DecisionRecord(
        decision_id=decision_id, site_id=site_id, rule_id=rule_id, chain_seq=chain_seq,
        statement=statement, coordinator_id=coordinator_id,
        recorded_at=datetime.fromisoformat(recorded_at), effective_from=date.fromisoformat(effective_from),
        rule_version_id=rule_version_id, rel=rel, predecessor_decision_id=predecessor_decision_id,
    )


def rule_history(conn: sqlite3.Connection, site_id: str, rule_id: str) -> list[DecisionRecord]:
    """Item 1 (Historia reguły): the full linear chain, oldest to newest."""
    rows = conn.execute(
        f"SELECT {_DECISION_COLUMNS} FROM decision_records "
        "WHERE site_id = ? AND rule_id = ? ORDER BY chain_seq ASC",
        (site_id, rule_id),
    ).fetchall()
    return [_row_to_decision(row) for row in rows]


def effective_rule_on(conn: sqlite3.Connection, site_id: str, rule_id: str, as_of: date) -> EffectiveSelection:
    """Item 2 + EFFECTIVE SELECTION: never ORDER BY changed_at/effective_from --
    always walk the chain and take the latest-IN-CHAIN candidate whose
    effective_from has arrived, per the brief's 8-step algorithm."""
    chain = rule_history(conn, site_id, rule_id)
    candidates = [d for d in chain if d.effective_from <= as_of]
    if not candidates:
        return NoActiveRule(site_id, rule_id, as_of)
    chosen = candidates[-1]
    if chosen.rule_version_id is None:
        return NoActiveRule(site_id, rule_id, as_of)
    version = get_site_rule_version(conn, chosen.rule_version_id)
    if version.effective_to is not None and as_of > version.effective_to:
        return NoActiveRule(site_id, rule_id, as_of)
    return EffectiveRule(version, chosen)


def decision_for_rule_version(conn: sqlite3.Connection, rule_version_id: str) -> DecisionRecord:
    """Item 3 (Dlaczego obowiązuje): the decision that created rule_version_id."""
    row = conn.execute(
        f"SELECT {_DECISION_COLUMNS} FROM decision_records WHERE rule_version_id = ?", (rule_version_id,)
    ).fetchone()
    if row is None:
        raise DecisionRecordNotFound(rule_version_id)
    return _row_to_decision(row)


def rule_provenance(conn: sqlite3.Connection, rule_version_id: str) -> tuple[DecisionRecord, list[DecisionRecord]]:
    """Item 3: the creating decision, plus the earlier chain up to and
    including it -- enough for a UI to render "why does this rule hold,
    and what did it replace" without reading technical logs."""
    creating_decision = decision_for_rule_version(conn, rule_version_id)
    full_chain = rule_history(conn, creating_decision.site_id, creating_decision.rule_id)
    earlier_chain = [d for d in full_chain if d.chain_seq <= creating_decision.chain_seq]
    return creating_decision, earlier_chain


def decision_fate(conn: sqlite3.Connection, decision_id: str) -> str:
    """ACTIVE / SUPERSEDED / REJECTED (LOS DECYZJI section) -- purely
    historical provenance, NOT the effective-on-date answer (that's
    effective_rule_on): a decision can be SUPERSEDED yet still be the
    effective rule for a past date before its successor's effective_from."""
    row = conn.execute(
        "SELECT rel FROM decision_relations WHERE to_decision_id = ?", (decision_id,)
    ).fetchone()
    if row is None:
        return "ACTIVE"
    rel: str = row[0]
    return {"supersedes": "SUPERSEDED", "corrects": "SUPERSEDED", "rejects": "REJECTED"}[rel]


class UnknownDecisionRequiredSnapshot(Exception):
    """Raised when a responds_to_decision_required_id names no snapshot."""


class DecisionRequiredLinkMismatch(Exception):
    """Raised when a responds_to_decision_required_id is not the current
    pointer for its own (site_id, month), or its site_id differs from the
    command's origin_site_id (brief.md section 10)."""


class CoordinatorActionNotFound(Exception):
    """Raised when an action_id has no matching coordinator_action_records row."""


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {value!r}")


def _serialize_state(state: Optional[dict]) -> Optional[str]:
    if state is None:
        return None
    return json.dumps(state, sort_keys=True, default=_json_default)


def _deserialize_state(raw: Optional[str]) -> Optional[dict]:
    return None if raw is None else json.loads(raw)


def _payload_to_dict(payload: DecisionRequiredPayload) -> dict:
    """T019b DECISION_REQUIRED SERIALIZATION (brief.md section 18): the one
    canonical mapping, deterministic and lossless for the final rendered
    T013 payload. Never re-derives text -- readback is what was shown then."""
    return {
        "blocking_shift_demands": [
            {"demand_id": d.demand_id, "start_datetime": d.start_datetime, "end_datetime": d.end_datetime}
            for d in payload.blocking_shift_demands
        ],
        "blockers": [{"employee_id": b.employee_id, "condition": b.condition} for b in payload.blockers],
        "load_blocker": (
            None if payload.load_blocker is None else {
                "employee_id": payload.load_blocker.employee_id,
                "window_start": payload.load_blocker.window_start,
                "window_end": payload.load_blocker.window_end,
                "hours": payload.load_blocker.hours,
            }
        ),
        "unblocking_options": [
            {"text": o.text, "target": o.target, "requires_existing_schedule": o.requires_existing_schedule}
            for o in payload.unblocking_options
        ],
    }


def _unblocking_option_from_raw(raw) -> UnblockingOption:
    """ROTA-T062 (brief section 4 point 4): old snapshots persisted
    `unblocking_options` as a bare list[str] -- read back as a target-less
    informational option, no table migration. New snapshots are dicts."""
    if isinstance(raw, str):
        return UnblockingOption(text=raw)
    return UnblockingOption(
        text=raw["text"], target=raw.get("target"), requires_existing_schedule=raw.get("requires_existing_schedule", False),
    )


def _payload_from_dict(data: dict) -> DecisionRequiredPayload:
    load_blocker = data["load_blocker"]
    return DecisionRequiredPayload(
        blocking_shift_demands=[
            BlockingDemand(
                demand_id=d["demand_id"], start_datetime=datetime.fromisoformat(d["start_datetime"]),
                end_datetime=datetime.fromisoformat(d["end_datetime"]),
            )
            for d in data["blocking_shift_demands"]
        ],
        blockers=[Blocker(employee_id=b["employee_id"], condition=b["condition"]) for b in data["blockers"]],
        load_blocker=(
            None if load_blocker is None else LoadBlocker(
                employee_id=load_blocker["employee_id"],
                window_start=date.fromisoformat(load_blocker["window_start"]),
                window_end=date.fromisoformat(load_blocker["window_end"]),
                hours=load_blocker["hours"],
            )
        ),
        unblocking_options=[_unblocking_option_from_raw(o) for o in data["unblocking_options"]],
    )


def validate_decision_required_link_no_commit(
    conn: sqlite3.Connection, *, responds_to_decision_required_id: Optional[str], origin_site_id: str,
) -> None:
    """brief.md section 10: called INSIDE the same transaction as the
    business mutation it may gate, BEFORE any write. A None link is always
    valid (most commands don't answer a question). A non-None link must name
    an existing snapshot that is still the current pointer for its own
    (site_id, month) and whose site_id matches origin_site_id.

    The final currency check is a self-assigning UPDATE, not a SELECT: any
    UPDATE statement makes SQLite escalate to a RESERVED lock immediately,
    so a concurrent connection cannot change current_decision_required for
    this (site_id, month) between this check and the caller's own write in
    the same transaction -- closing the TOCTOU window a read-only SELECT
    would leave open under SQLite's deferred-transaction default."""
    if responds_to_decision_required_id is None:
        return
    row = conn.execute(
        "SELECT site_id, month FROM decision_required_snapshots WHERE decision_required_id = ?",
        (responds_to_decision_required_id,),
    ).fetchone()
    if row is None:
        raise UnknownDecisionRequiredSnapshot(responds_to_decision_required_id)
    site_id, month = row
    if site_id != origin_site_id:
        raise DecisionRequiredLinkMismatch(
            f"{responds_to_decision_required_id!r} belongs to site {site_id!r}, not {origin_site_id!r}"
        )
    cursor = conn.execute(
        "UPDATE current_decision_required SET decision_required_id = decision_required_id "
        "WHERE site_id = ? AND month = ? AND decision_required_id = ?",
        (site_id, month, responds_to_decision_required_id),
    )
    if cursor.rowcount != 1:
        raise DecisionRequiredLinkMismatch(
            f"{responds_to_decision_required_id!r} is not the current question for ({site_id!r}, {month!r})"
        )


_ACTION_COLUMNS = (
    "action_id, action_kind, origin_site_id, affected_site_ids_json, coordinator_id, recorded_at, "
    "effective_from, month, schedule_version_id, affected_entities_json, before_state_json, "
    "after_state_json, note, source_kind, source_id, responds_to_decision_required_id"
)


def _row_to_action(row: tuple) -> CoordinatorActionRecord:
    (
        action_id, action_kind, origin_site_id, affected_site_ids_json, coordinator_id, recorded_at,
        effective_from, month, schedule_version_id, affected_entities_json, before_state_json,
        after_state_json, note, source_kind, source_id, responds_to_decision_required_id,
    ) = row
    return CoordinatorActionRecord(
        action_id=action_id, action_kind=CoordinatorActionKind(action_kind), origin_site_id=origin_site_id,
        affected_site_ids=tuple(json.loads(affected_site_ids_json)), coordinator_id=coordinator_id,
        recorded_at=datetime.fromisoformat(recorded_at),
        effective_from=date.fromisoformat(effective_from) if effective_from else None,
        month=date.fromisoformat(month) if month else None, schedule_version_id=schedule_version_id,
        affected_entities=tuple(
            AffectedEntity(e["entity_kind"], e["entity_id"]) for e in json.loads(affected_entities_json)
        ),
        before_state=_deserialize_state(before_state_json), after_state=_deserialize_state(after_state_json),
        note=note, source_kind=ActionSourceKind(source_kind), source_id=source_id,
        responds_to_decision_required_id=responds_to_decision_required_id,
    )


def record_coordinator_action_no_commit(
    conn: sqlite3.Connection, *, action_kind: CoordinatorActionKind, origin_site_id: str,
    affected_site_ids: list[str], coordinator_id: str, recorded_at: datetime,
    effective_from: Optional[date], month: Optional[date], schedule_version_id: Optional[str],
    affected_entities: list[AffectedEntity], before_state: Optional[dict], after_state: Optional[dict],
    note: Optional[str], source_kind: ActionSourceKind, source_id: Optional[str],
    responds_to_decision_required_id: Optional[str],
) -> CoordinatorActionRecord:
    """One append-only action row. Does NOT (re)validate
    responds_to_decision_required_id -- callers must already have called
    validate_decision_required_link_no_commit BEFORE their business
    mutation; this insert only happens after that mutation succeeded."""
    action_id = f"ACT-{uuid.uuid4().hex}"
    affected_site_ids_sorted = sorted(set(affected_site_ids))
    entities_sorted = sorted(set(affected_entities), key=lambda e: (e.entity_kind, e.entity_id))
    conn.execute(
        f"INSERT INTO coordinator_action_records ({_ACTION_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            action_id, action_kind.value, origin_site_id, json.dumps(affected_site_ids_sorted), coordinator_id,
            recorded_at.isoformat(), effective_from.isoformat() if effective_from else None,
            month.isoformat() if month else None, schedule_version_id,
            json.dumps([{"entity_kind": e.entity_kind, "entity_id": e.entity_id} for e in entities_sorted]),
            _serialize_state(before_state), _serialize_state(after_state), note, source_kind.value, source_id,
            responds_to_decision_required_id,
        ),
    )
    return CoordinatorActionRecord(
        action_id=action_id, action_kind=action_kind, origin_site_id=origin_site_id,
        affected_site_ids=tuple(affected_site_ids_sorted), coordinator_id=coordinator_id, recorded_at=recorded_at,
        effective_from=effective_from, month=month, schedule_version_id=schedule_version_id,
        affected_entities=tuple(entities_sorted), before_state=before_state, after_state=after_state,
        note=note, source_kind=source_kind, source_id=source_id,
        responds_to_decision_required_id=responds_to_decision_required_id,
    )


def get_coordinator_action(conn: sqlite3.Connection, action_id: str) -> CoordinatorActionRecord:
    row = conn.execute(f"SELECT {_ACTION_COLUMNS} FROM coordinator_action_records WHERE action_id = ?", (action_id,)).fetchone()
    if row is None:
        raise CoordinatorActionNotFound(action_id)
    return _row_to_action(row)


def list_coordinator_actions(
    conn: sqlite3.Connection, *, site_id: Optional[str] = None, affected_entity_kind: Optional[str] = None,
    affected_entity_id: Optional[str] = None, action_kind: Optional[CoordinatorActionKind] = None,
    coordinator_id: Optional[str] = None, recorded_from: Optional[datetime] = None,
    recorded_to: Optional[datetime] = None,
) -> list[CoordinatorActionRecord]:
    """brief.md section 17.2: every filter optional and AND-composed, newest
    first. Site/entity filtering finishes in memory over the deterministic
    JSON arrays (section 5.4) -- no JSON-extension SQL dependency."""
    if (affected_entity_kind is None) != (affected_entity_id is None):
        raise ValueError("affected_entity_kind and affected_entity_id must be supplied together")
    rows = conn.execute(
        f"SELECT {_ACTION_COLUMNS} FROM coordinator_action_records ORDER BY recorded_at DESC, action_id DESC"
    ).fetchall()
    result = []
    for row in rows:
        record = _row_to_action(row)
        if site_id is not None and site_id not in record.affected_site_ids:
            continue
        if action_kind is not None and record.action_kind != action_kind:
            continue
        if coordinator_id is not None and record.coordinator_id != coordinator_id:
            continue
        if recorded_from is not None and record.recorded_at < recorded_from:
            continue
        if recorded_to is not None and record.recorded_at > recorded_to:
            continue
        if affected_entity_kind is not None and not any(
            e.entity_kind == affected_entity_kind and e.entity_id == affected_entity_id
            for e in record.affected_entities
        ):
            continue
        result.append(record)
    return result


def list_action_ids_linking_to(conn: sqlite3.Connection, decision_required_id: str) -> tuple[str, ...]:
    rows = conn.execute(
        "SELECT action_id FROM coordinator_action_records WHERE responds_to_decision_required_id = ? ORDER BY action_id",
        (decision_required_id,),
    ).fetchall()
    return tuple(row[0] for row in rows)


_SNAPSHOT_COLUMNS = "decision_required_id, site_id, month, schedule_version_id, requested_by, recorded_at, payload_json"


def _row_to_snapshot(row: tuple) -> DecisionRequiredSnapshotRecord:
    decision_required_id, site_id, month, schedule_version_id, requested_by, recorded_at, payload_json = row
    return DecisionRequiredSnapshotRecord(
        decision_required_id=decision_required_id, site_id=site_id, month=date.fromisoformat(month),
        schedule_version_id=schedule_version_id, requested_by=requested_by,
        recorded_at=datetime.fromisoformat(recorded_at), payload=_payload_from_dict(json.loads(payload_json)),
    )


def insert_decision_required_snapshot_no_commit(
    conn: sqlite3.Connection, *, site_id: str, month: date, schedule_version_id: Optional[str],
    requested_by: str, recorded_at: datetime, payload: DecisionRequiredPayload,
) -> DecisionRequiredSnapshotRecord:
    decision_required_id = f"DR-{uuid.uuid4().hex}"
    conn.execute(
        f"INSERT INTO decision_required_snapshots ({_SNAPSHOT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            decision_required_id, site_id, month.isoformat(), schedule_version_id, requested_by,
            recorded_at.isoformat(), json.dumps(_payload_to_dict(payload), sort_keys=True, default=_json_default),
        ),
    )
    return DecisionRequiredSnapshotRecord(
        decision_required_id=decision_required_id, site_id=site_id, month=month,
        schedule_version_id=schedule_version_id, requested_by=requested_by, recorded_at=recorded_at, payload=payload,
    )


def get_decision_required_snapshot(conn: sqlite3.Connection, decision_required_id: str) -> Optional[DecisionRequiredSnapshotRecord]:
    row = conn.execute(
        f"SELECT {_SNAPSHOT_COLUMNS} FROM decision_required_snapshots WHERE decision_required_id = ?",
        (decision_required_id,),
    ).fetchone()
    return None if row is None else _row_to_snapshot(row)


def get_current_decision_required(conn: sqlite3.Connection, *, site_id: str, month: date) -> Optional[DecisionRequiredSnapshotRecord]:
    row = conn.execute(
        "SELECT decision_required_id FROM current_decision_required WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    return None if row is None else get_decision_required_snapshot(conn, row[0])


def set_current_decision_required_no_commit(conn: sqlite3.Connection, *, site_id: str, month: date, decision_required_id: str) -> None:
    conn.execute(
        """INSERT INTO current_decision_required (site_id, month, decision_required_id) VALUES (?, ?, ?)
           ON CONFLICT(site_id, month) DO UPDATE SET decision_required_id = excluded.decision_required_id""",
        (site_id, month.isoformat(), decision_required_id),
    )


def clear_current_decision_required_no_commit(conn: sqlite3.Connection, *, site_id: str, month: date) -> None:
    conn.execute("DELETE FROM current_decision_required WHERE site_id = ? AND month = ?", (site_id, month.isoformat()))


def reuse_or_insert_decision_required_snapshot_no_commit(
    conn: sqlite3.Connection, *, site_id: str, month: date, schedule_version_id: Optional[str],
    requested_by: str, recorded_at: datetime, payload: DecisionRequiredPayload,
) -> DecisionRequiredSnapshotRecord:
    """brief.md section 11: repeated identical PLAN clicks against the same
    schedule context reuse the current snapshot instead of creating a
    duplicate row. Same schedule_version_id + canonically identical payload
    is the only reuse condition -- a genuinely changed question always gets
    a new immutable snapshot and moves the pointer."""
    current = get_current_decision_required(conn, site_id=site_id, month=month)
    if (
        current is not None and current.schedule_version_id == schedule_version_id
        and _payload_to_dict(current.payload) == _payload_to_dict(payload)
    ):
        return current
    snapshot = insert_decision_required_snapshot_no_commit(
        conn, site_id=site_id, month=month, schedule_version_id=schedule_version_id,
        requested_by=requested_by, recorded_at=recorded_at, payload=payload,
    )
    set_current_decision_required_no_commit(conn, site_id=site_id, month=month, decision_required_id=snapshot.decision_required_id)
    return snapshot


def current_decision_required_months_for_site(conn: sqlite3.Connection, *, site_id: str) -> list[date]:
    rows = conn.execute("SELECT month FROM current_decision_required WHERE site_id = ?", (site_id,)).fetchall()
    return [date.fromisoformat(row[0]) for row in rows]


def invalidate_current_decision_required_no_commit(
    conn: sqlite3.Connection, *, site_ids: list[str], months: Optional[list[date]] = None,
) -> None:
    """brief.md section 12: staleness invalidation, never inferred question
    -> action linkage. months=None clears every current question for the
    given Sites; an explicit months list clears only those exact months."""
    for site_id in site_ids:
        if months is None:
            conn.execute("DELETE FROM current_decision_required WHERE site_id = ?", (site_id,))
        else:
            for month in months:
                conn.execute(
                    "DELETE FROM current_decision_required WHERE site_id = ? AND month = ?",
                    (site_id, month.isoformat()),
                )


if __name__ == "__main__":
    print("persistence.site_memory module OK")
