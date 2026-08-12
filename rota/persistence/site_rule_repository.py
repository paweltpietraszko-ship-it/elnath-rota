"""SiteRuleVersion persistence -- append-only (tasks/ROTA-T005/brief.md RULE STORE).

No UPDATE/DELETE API is exposed here on purpose (see db.py's SQL triggers,
which forbid it at the schema level too): a version is inserted once, never
mutated -- a rule change is always a new row.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Optional

from rota.domain import RuleCategory, RuleEnforcement, RuleResolution, SiteRuleVersion


class SiteRuleVersionNotFound(Exception):
    """Raised when rule_version_id has no matching row."""


def _dump_parameters(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(value)
    except TypeError as exc:
        raise TypeError(f"structured_parameters must be JSON-compatible: {exc}") from exc


def _load_parameters(raw: Optional[str]) -> Optional[object]:
    return None if raw is None else json.loads(raw)


def insert_site_rule_version(conn: sqlite3.Connection, version: SiteRuleVersion) -> None:
    """Insert-only. Callers needing atomicity with a Decision Record use
    decision_ledger.record_decision instead of calling this directly."""
    conn.execute(
        """INSERT INTO site_rule_versions
           (rule_version_id, rule_id, site_id, category, rule_kind, structured_parameters,
            enforcement, resolution_status, effective_from, effective_to, changed_at,
            changed_by, supersedes_rule_version_id, description, source, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            version.rule_version_id,
            version.rule_id,
            version.site_id,
            version.category.value,
            version.rule_kind,
            _dump_parameters(version.structured_parameters),
            version.enforcement.value,
            version.resolution_status.value,
            version.effective_from.isoformat(),
            version.effective_to.isoformat() if version.effective_to else None,
            version.changed_at.isoformat(),
            version.changed_by,
            version.supersedes_rule_version_id,
            version.description,
            version.source,
            version.reason,
        ),
    )


_COLUMNS = (
    "rule_version_id, rule_id, site_id, category, rule_kind, structured_parameters, "
    "enforcement, resolution_status, effective_from, effective_to, changed_at, "
    "changed_by, supersedes_rule_version_id, description, source, reason"
)


def _row_to_version(row: tuple) -> SiteRuleVersion:
    (
        rule_version_id, rule_id, site_id, category, rule_kind, structured_parameters,
        enforcement, resolution_status, effective_from, effective_to, changed_at,
        changed_by, supersedes_rule_version_id, description, source, reason,
    ) = row
    return SiteRuleVersion(
        rule_version_id=rule_version_id,
        rule_id=rule_id,
        site_id=site_id,
        category=RuleCategory(category),
        rule_kind=rule_kind,
        structured_parameters=_load_parameters(structured_parameters),
        enforcement=RuleEnforcement(enforcement),
        resolution_status=RuleResolution(resolution_status),
        effective_from=date.fromisoformat(effective_from),
        effective_to=date.fromisoformat(effective_to) if effective_to else None,
        changed_at=datetime.fromisoformat(changed_at),
        changed_by=changed_by,
        supersedes_rule_version_id=supersedes_rule_version_id,
        description=description,
        source=source,
        reason=reason,
    )


def get_site_rule_version(conn: sqlite3.Connection, rule_version_id: str) -> SiteRuleVersion:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM site_rule_versions WHERE rule_version_id = ?", (rule_version_id,)
    ).fetchone()
    if row is None:
        raise SiteRuleVersionNotFound(rule_version_id)
    return _row_to_version(row)


if __name__ == "__main__":
    print("persistence.site_rule_repository module OK")
