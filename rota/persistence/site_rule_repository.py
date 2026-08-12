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


class RuleFamilyIntegrityError(Exception):
    """Raised when a write would let one rule_id span two site_id, or link
    a SiteRuleVersion to a supersedes target outside its own family
    (RULE-07 / brief.md RULE FAMILY INTEGRITY)."""


def ensure_rule_family(conn: sqlite3.Connection, rule_id: str, site_id: str) -> None:
    """Register rule_id's owning site_id on first sight; reject any later
    write for the same rule_id under a different site_id. Shared by both
    write paths that can create/extend a family (record_decision and this
    module's insert_site_rule_version) so neither can bypass the other."""
    row = conn.execute("SELECT site_id FROM rule_families WHERE rule_id = ?", (rule_id,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO rule_families (rule_id, site_id) VALUES (?, ?)", (rule_id, site_id))
    elif row[0] != site_id:
        raise RuleFamilyIntegrityError(f"rule_id {rule_id!r} belongs to site {row[0]!r}, not {site_id!r}")


def _dump_parameters(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    try:
        dumped = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"structured_parameters must be JSON-compatible: {exc}") from exc
    if json.loads(dumped) != value:
        # Python's json module silently coerces on encode (non-string dict
        # keys -> str, tuple -> list) instead of rejecting them -- round-trip
        # comparison catches any such lossy encoding generically, without
        # special-casing each Python type that isn't real JSON.
        raise TypeError(
            "structured_parameters is not exactly JSON-representable "
            "(e.g. non-string dict keys or tuples would silently change on round-trip)"
        )
    return dumped


def _load_parameters(raw: Optional[str]) -> Optional[object]:
    return None if raw is None else json.loads(raw)


def _check_supersedes_same_family(conn: sqlite3.Connection, version: SiteRuleVersion) -> None:
    if version.supersedes_rule_version_id is None:
        return
    target = get_site_rule_version(conn, version.supersedes_rule_version_id)
    if target.rule_id != version.rule_id or target.site_id != version.site_id:
        raise RuleFamilyIntegrityError(
            f"supersedes_rule_version_id {version.supersedes_rule_version_id!r} belongs to "
            f"({target.site_id!r}, {target.rule_id!r}), not ({version.site_id!r}, {version.rule_id!r})"
        )


def insert_site_rule_version(conn: sqlite3.Connection, version: SiteRuleVersion) -> None:
    """Insert-only. Callers needing atomicity with a Decision Record use
    decision_ledger.record_decision instead of calling this directly."""
    ensure_rule_family(conn, version.rule_id, version.site_id)
    _check_supersedes_same_family(conn, version)
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
