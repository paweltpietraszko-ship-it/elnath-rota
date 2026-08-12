"""Assembly helper: effective SiteRuleVersions -> PlanningState's two rule
tuples (tasks/ROTA-T005/brief.md PROJECTION TO PLANNINGSTATE).

This module does its own DB I/O -- PlanningEngine itself never calls it and
never imports rota.persistence (verified by
tests/test_site_profile_persistence.py::test_planning_engine_has_no_persistence_coupling).
Wiring this into an actual PlanningState build is out of scope for T005.
"""
from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta

from rota.domain import RuleResolution, SiteRuleVersion
from rota.persistence.site_memory import effective_rule_on
from rota.persistence.site_rule_repository import list_rule_ids_for_site
from rota.planning.state import SiteRuleApplicability
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


def _month_dates(month: date) -> list[date]:
    num_days = calendar.monthrange(month.year, month.month)[1]
    return [date(month.year, month.month, day) for day in range(1, num_days + 1)]


def _coalesce_dates(dates: list[date]) -> list[tuple[date, date]]:
    """Consecutive-date runs -> inclusive (start, end) slices."""
    ordered = sorted(dates)
    slices: list[tuple[date, date]] = []
    run_start = run_end = ordered[0]
    for current in ordered[1:]:
        if current == run_end + timedelta(days=1):
            run_end = current
        else:
            slices.append((run_start, run_end))
            run_start = run_end = current
    slices.append((run_start, run_end))
    return slices


def _collect_monthly_selections(
    conn: sqlite3.Connection, site_id: str, month: date
) -> tuple[dict[str, list[date]], dict[str, SiteRuleVersion]]:
    dates_by_version: dict[str, list[date]] = {}
    versions_by_id: dict[str, SiteRuleVersion] = {}
    for rule_id in list_rule_ids_for_site(conn, site_id):
        for day in _month_dates(month):
            selection = effective_rule_on(conn, site_id, rule_id, day)
            if not isinstance(selection, EffectiveRule):
                continue
            version = selection.rule_version
            versions_by_id[version.rule_version_id] = version
            dates_by_version.setdefault(version.rule_version_id, []).append(day)
    return dates_by_version, versions_by_id


def assemble_monthly_site_rules(
    conn: sqlite3.Connection, site_id: str, month: date
) -> tuple[tuple[SiteRuleVersion, ...], tuple[SiteRuleVersion, ...], tuple[SiteRuleApplicability, ...]]:
    """ROTA-T007 MONTHLY APPLICABILITY PROJECTION (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md):
    auto-discovers every rule family for site_id (caller supplies no
    rule_id list), walks each calendar day of `month` through T005's
    effective_rule_on, and coalesces consecutive same-version days into
    SiteRuleApplicability slices. Never rewrites persisted SiteRuleVersion;
    NO_ACTIVE_RULE days contribute nothing."""
    dates_by_version, versions_by_id = _collect_monthly_selections(conn, site_id, month)

    applicability: list[SiteRuleApplicability] = []
    resolved: list[SiteRuleVersion] = []
    unresolved: list[SiteRuleVersion] = []
    for rule_version_id, dates in dates_by_version.items():
        version = versions_by_id[rule_version_id]
        applicability.extend(
            SiteRuleApplicability(rule_version_id, start, end) for start, end in _coalesce_dates(dates)
        )
        if version.resolution_status == RuleResolution.RESOLVED:
            resolved.append(version)
        elif version.resolution_status == RuleResolution.NEEDS_RESOLUTION:
            unresolved.append(version)

    return tuple(resolved), tuple(unresolved), tuple(applicability)


if __name__ == "__main__":
    print("persistence.site_rule_assembly module OK")
