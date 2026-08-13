"""Operation 1: Open Site/month (tasks/ROTA-T009/brief.md). Read-only --
never creates a version, never calls plan(), never changes the current
reference or writes business data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from rota.application.assembler import assemble_planning_state
from rota.domain import Employee, ScheduleVersion, Site, SiteMembership, SiteProfile, SiteRuleVersion, WorkBalance
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_version_header, list_schedule_versions


@dataclass(frozen=True)
class OpenMonthView:
    site: Site
    profile: SiteProfile
    employees: tuple[Employee, ...]
    memberships: tuple[SiteMembership, ...]
    resolved_rules: tuple[SiteRuleVersion, ...]
    unresolved_rules: tuple[SiteRuleVersion, ...]
    current_version: Optional[ScheduleVersion]
    version_history: tuple[ScheduleVersion, ...]
    work_balances: tuple[WorkBalance, ...]
    warnings: tuple[str, ...]


def open_month(conn, *, site_id: str, month: date) -> OpenMonthView:
    state, warnings = assemble_planning_state(conn, site_id=site_id, month=month)
    current_id = get_current_version_id(conn, site_id, month)
    current_version = get_schedule_version_header(conn, current_id) if current_id else None
    history = tuple(list_schedule_versions(conn, site_id, month))
    return OpenMonthView(
        site=state.site, profile=state.profile, employees=state.employees, memberships=state.memberships,
        resolved_rules=state.site_rules, unresolved_rules=state.unresolved_site_rules,
        current_version=current_version, version_history=history, work_balances=state.work_balances,
        warnings=tuple(warnings),
    )
