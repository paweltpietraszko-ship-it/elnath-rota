"""Assembly helper: effective SiteRuleVersions -> PlanningState's two rule
tuples (tasks/ROTA-T005/brief.md PROJECTION TO PLANNINGSTATE).

This module does its own DB I/O -- PlanningEngine itself never calls it and
never imports rota.persistence (verified by
tests/test_site_profile_persistence.py::test_planning_engine_has_no_persistence_coupling).
Wiring this into an actual PlanningState build is out of scope for T005.
"""
from __future__ import annotations

import sqlite3

from rota.domain import RuleResolution, SiteRuleVersion
from rota.persistence.site_memory import effective_rule_on
from rota.site_memory_types import EffectiveRule


def assemble_site_rules(
    conn: sqlite3.Connection, site_id: str, rule_ids: list[str], as_of
) -> tuple[tuple[SiteRuleVersion, ...], tuple[SiteRuleVersion, ...]]:
    """Returns (resolved, unresolved) -- matches PlanningState.site_rules /
    unresolved_site_rules. A rule_id with NO_ACTIVE_RULE on `as_of` simply
    contributes nothing (there is no rule to place in either bucket)."""
    resolved: list[SiteRuleVersion] = []
    unresolved: list[SiteRuleVersion] = []
    for rule_id in rule_ids:
        selection = effective_rule_on(conn, site_id, rule_id, as_of)
        if not isinstance(selection, EffectiveRule):
            continue
        version = selection.rule_version
        if version.resolution_status == RuleResolution.RESOLVED:
            resolved.append(version)
        elif version.resolution_status == RuleResolution.NEEDS_RESOLUTION:
            unresolved.append(version)
    return tuple(resolved), tuple(unresolved)


if __name__ == "__main__":
    print("persistence.site_rule_assembly module OK")
