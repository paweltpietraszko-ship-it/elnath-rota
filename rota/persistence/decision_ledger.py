"""Decision Ledger write path (tasks/ROTA-T005/brief.md).

record_decision() is the ONLY way to add a decision: it always targets the
live current end of the (site_id, rule_id) chain itself -- callers never
pass a predecessor/target id -- so a decision structurally cannot skip the
chain end, branch, or point at an arbitrary older ancestor (LINEAR DECISION
CHAIN). Decision Record + SiteRuleVersion + relation are written in one
transaction (ATOMICITY).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime
from typing import Optional

from rota.domain import SiteRuleVersion
from rota.persistence.site_rule_repository import ensure_rule_family, insert_site_rule_version
from rota.site_memory_types import DECISION_RELATIONS, DecisionRecord, NewRuleContent


class ChainIntegrityError(Exception):
    """Raised when a decision would violate the linear-chain invariant."""


def _current_chain_end(conn: sqlite3.Connection, site_id: str, rule_id: str) -> Optional[tuple]:
    return conn.execute(
        "SELECT decision_id, chain_seq, rule_version_id FROM decision_records "
        "WHERE site_id = ? AND rule_id = ? ORDER BY chain_seq DESC LIMIT 1",
        (site_id, rule_id),
    ).fetchone()


def _resolve_predecessor(
    end_row: Optional[tuple], rel: Optional[str], rule_content: Optional[NewRuleContent]
) -> tuple[Optional[str], Optional[int], Optional[str], int]:
    if end_row is None:
        if rel is not None:
            raise ChainIntegrityError("first decision in a family cannot carry a rel")
        if rule_content is None:
            raise ChainIntegrityError("first decision in a family must establish a rule")
        return None, None, None, 0
    predecessor_id, predecessor_chain_seq, predecessor_rule_version_id = end_row
    if rel is None or rel not in DECISION_RELATIONS:
        raise ChainIntegrityError(f"a non-first decision requires rel in {DECISION_RELATIONS}, got {rel!r}")
    return predecessor_id, predecessor_chain_seq, predecessor_rule_version_id, predecessor_chain_seq + 1


def _new_version_id_and_supersedes(
    rel: Optional[str], rule_content: Optional[NewRuleContent],
    predecessor_id: Optional[str], predecessor_rule_version_id: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    if rel == "rejects":
        if rule_content is not None:
            raise ChainIntegrityError("rejects must not carry rule_content")
        if predecessor_id is not None and predecessor_rule_version_id is None:
            raise ChainIntegrityError("cannot reject a decision that has no active rule_version_id")
        return None, None
    if rule_content is None:
        raise ChainIntegrityError(f"{rel or 'first decision'} requires rule_content")
    if rel == "corrects" and predecessor_rule_version_id is None:
        raise ChainIntegrityError("corrects requires the corrected decision to have a rule_version_id")
    return f"RV-{uuid.uuid4().hex}", predecessor_rule_version_id


def _build_site_rule_version(
    *, rule_version_id: str, supersedes_rule_version_id: Optional[str], rule_id: str, site_id: str,
    coordinator_id: str, recorded_at: datetime, effective_from: date, rule_content: NewRuleContent,
) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id=rule_id, site_id=site_id,
        category=rule_content.category, rule_kind=rule_content.rule_kind,
        structured_parameters=rule_content.structured_parameters,
        enforcement=rule_content.enforcement, resolution_status=rule_content.resolution_status,
        effective_from=effective_from, effective_to=rule_content.effective_to,
        changed_at=recorded_at, changed_by=coordinator_id,
        supersedes_rule_version_id=supersedes_rule_version_id,
        description=rule_content.description, source=rule_content.source, reason=rule_content.reason,
    )


def _insert_decision_and_relation(
    conn: sqlite3.Connection, *, decision_id: str, site_id: str, rule_id: str, chain_seq: int,
    statement: str, coordinator_id: str, recorded_at: datetime, effective_from: date,
    rule_version_id: Optional[str], rel: Optional[str], predecessor_id: Optional[str],
) -> None:
    conn.execute(
        """INSERT INTO decision_records
           (decision_id, site_id, rule_id, chain_seq, statement, coordinator_id,
            recorded_at, effective_from, rule_version_id, rel, predecessor_decision_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            decision_id, site_id, rule_id, chain_seq, statement, coordinator_id,
            recorded_at.isoformat(), effective_from.isoformat(), rule_version_id, rel, predecessor_id,
        ),
    )
    if predecessor_id is not None:
        conn.execute(
            "INSERT INTO decision_relations (from_decision_id, rel, to_decision_id, created_at) "
            "VALUES (?, ?, ?, ?)",
            (decision_id, rel, predecessor_id, recorded_at.isoformat()),
        )


def record_decision_no_commit(
    conn: sqlite3.Connection,
    *,
    site_id: str,
    rule_id: str,
    statement: str,
    coordinator_id: str,
    recorded_at: datetime,
    effective_from: date,
    rel: Optional[str],
    rule_content: Optional[NewRuleContent],
) -> DecisionRecord:
    """ROTA-T012-D ATOMICITY: transaction-neutral core of record_decision(),
    for a caller that must combine this insert with another write (e.g.
    manual_edit.apply_manual_correction's REST override record) inside an
    ALREADY-OPEN transaction (create_schedule_version's on_success hook).
    Never opens or commits its own `with conn:` -- the caller owns that."""
    ensure_rule_family(conn, rule_id, site_id)
    end_row = _current_chain_end(conn, site_id, rule_id)
    predecessor_id, _, predecessor_rule_version_id, chain_seq = _resolve_predecessor(
        end_row, rel, rule_content
    )
    rule_version_id, supersedes_rule_version_id = _new_version_id_and_supersedes(
        rel, rule_content, predecessor_id, predecessor_rule_version_id
    )
    if rule_version_id is not None:
        version = _build_site_rule_version(
            rule_version_id=rule_version_id, supersedes_rule_version_id=supersedes_rule_version_id,
            rule_id=rule_id, site_id=site_id, coordinator_id=coordinator_id,
            recorded_at=recorded_at, effective_from=effective_from, rule_content=rule_content,
        )
        insert_site_rule_version(conn, version)

    decision_id = f"DEC-{uuid.uuid4().hex}"
    _insert_decision_and_relation(
        conn, decision_id=decision_id, site_id=site_id, rule_id=rule_id, chain_seq=chain_seq,
        statement=statement, coordinator_id=coordinator_id, recorded_at=recorded_at,
        effective_from=effective_from, rule_version_id=rule_version_id, rel=rel,
        predecessor_id=predecessor_id,
    )
    return DecisionRecord(
        decision_id=decision_id, site_id=site_id, rule_id=rule_id, chain_seq=chain_seq,
        statement=statement, coordinator_id=coordinator_id, recorded_at=recorded_at,
        effective_from=effective_from, rule_version_id=rule_version_id, rel=rel,
        predecessor_decision_id=predecessor_id,
    )


def record_decision(
    conn: sqlite3.Connection,
    *,
    site_id: str,
    rule_id: str,
    statement: str,
    coordinator_id: str,
    recorded_at: datetime,
    effective_from: date,
    rel: Optional[str],
    rule_content: Optional[NewRuleContent],
) -> DecisionRecord:
    with conn:
        return record_decision_no_commit(
            conn, site_id=site_id, rule_id=rule_id, statement=statement, coordinator_id=coordinator_id,
            recorded_at=recorded_at, effective_from=effective_from, rel=rel, rule_content=rule_content,
        )


if __name__ == "__main__":
    print("persistence.decision_ledger module OK")
