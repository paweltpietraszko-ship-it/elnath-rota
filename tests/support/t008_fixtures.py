"""Shared builders for ROTA-T008 LocalStore tests (tasks/ROTA-T008/brief.md).
Not a test file itself -- no test_ functions here.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time

from rota.domain import (
    Coordinator,
    Employee,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftKind,
    Site,
    SiteProfile,
    SiteRuleVersion,
    StandardShift,
)
from rota.persistence.coordinator_repository import save_coordinator
from rota.persistence.decision_ledger import record_decision
from rota.persistence.employee_repository import save_employee
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.persistence.site_rule_repository import insert_site_rule_version
from rota.site_memory_types import DecisionRecord, NewRuleContent


def make_profile(profile_id: str = "PROF-1") -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name="Profile", active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(7, 0), time(19, 0), end_next_day=False, required_primary_count=1),
            StandardShift(ShiftKind.N, time(19, 0), time(7, 0), end_next_day=True, required_primary_count=1),
        ],
        day_only_blocks_n=True, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=40,
    )


def seed_base_entities(
    conn: sqlite3.Connection, *, site_id: str = "SITE-1", profile_id: str = "PROF-1",
    coordinator_id: str = "COORD-1", employee_id: str = "EMP-1",
) -> None:
    save_site_profile(conn, make_profile(profile_id))
    save_site(conn, Site(site_id=site_id, profile_id=profile_id, display_name="Site One", active=True))
    save_coordinator(conn, Coordinator(coordinator_id=coordinator_id, display_name="Coord", active=True))
    save_employee(conn, Employee(
        employee_id=employee_id, display_name="Emp One", active_from=date(2026, 1, 1), active_to=None, day_only=False,
    ))


def make_rule_version(
    *, rule_version_id: str = "RV-1", rule_id: str = "RULE-1", site_id: str = "SITE-1",
    changed_by: str = "COORD-1", changed_at: datetime = datetime(2026, 8, 1, 8, 0),
) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id=rule_version_id, rule_id=rule_id, site_id=site_id, category=RuleCategory.LOCAL_RULE,
        rule_kind=None, structured_parameters=None, enforcement=RuleEnforcement.SOFT,
        resolution_status=RuleResolution.RESOLVED, effective_from=date(2026, 8, 1), effective_to=None,
        changed_at=changed_at, changed_by=changed_by, supersedes_rule_version_id=None,
        description="fixture rule", source="test", reason=None,
    )


def seed_rule_version(conn: sqlite3.Connection, **overrides) -> SiteRuleVersion:
    version = make_rule_version(**overrides)
    insert_site_rule_version(conn, version)
    return version


def seed_rule_decision(
    conn: sqlite3.Connection, *, rule_id: str = "RULE-1", site_id: str = "SITE-1",
    coordinator_id: str = "COORD-1", recorded_at: datetime = datetime(2026, 8, 1, 8, 0),
    effective_from: date = date(2026, 8, 1),
) -> DecisionRecord:
    """A real T005 decision + rule_version pair, via the accepted
    decision_ledger path (not a raw site_rule_versions insert)."""
    content = NewRuleContent(
        category=RuleCategory.LOCAL_RULE, rule_kind=None, structured_parameters=None,
        enforcement=RuleEnforcement.SOFT, resolution_status=RuleResolution.RESOLVED,
        effective_to=None, description="fixture rule", source="test", reason=None,
    )
    return record_decision(
        conn, site_id=site_id, rule_id=rule_id, statement="fixture decision",
        coordinator_id=coordinator_id, recorded_at=recorded_at, effective_from=effective_from,
        rel=None, rule_content=content,
    )
