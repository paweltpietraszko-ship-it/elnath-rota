"""SiteMemory retrieval / history API (tasks/ROTA-T005/brief.md RETRIEVAL / HISTORY API,
EFFECTIVE SELECTION).
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from rota.persistence.site_rule_repository import get_site_rule_version
from rota.site_memory_types import DecisionRecord, EffectiveRule, EffectiveSelection, NoActiveRule

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


if __name__ == "__main__":
    print("persistence.site_memory module OK")
