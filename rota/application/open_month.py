"""Operation 1: Open Site/month (tasks/ROTA-T009/brief.md). Read-only --
never creates a version, never calls plan(), never changes the current
reference or writes business data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from rota.application.assembler import assemble_planning_state
from rota.domain import (
    AvailabilityRecord,
    Employee,
    ScheduleVersion,
    Site,
    SiteMembership,
    SiteProfile,
    SiteRuleVersion,
    WorkBalance,
)
from rota.persistence.schedule_repository import (
    get_current_version_id,
    get_schedule_version_header,
    list_months_with_assignments,
    list_schedule_versions,
)
from rota.planning.validator import validate


@dataclass(frozen=True)
class OpenMonthView:
    site: Site
    profile: SiteProfile
    employees: tuple[Employee, ...]
    memberships: tuple[SiteMembership, ...]
    availability_records: tuple[AvailabilityRecord, ...]
    resolved_rules: tuple[SiteRuleVersion, ...]
    unresolved_rules: tuple[SiteRuleVersion, ...]
    current_version: Optional[ScheduleVersion]
    version_history: tuple[ScheduleVersion, ...]
    work_balances: tuple[WorkBalance, ...]
    warnings: tuple[str, ...]


def open_month(conn, *, site_id: str, month: date) -> OpenMonthView:
    """R4-9: operation 1 literally requires current availability among the
    returned read-model data -- the assembler already loads it for
    PlanningState, it just needs to be surfaced here too.

    ROTA-T055: the independent validator's own `IndependentValidationReport.warnings`
    (computed today in select_candidate/apply_manual_correction and discarded every
    time) is re-derived here, read-only, from the current snapshot on every plain
    GET -- there is nothing else to persist; a warning is a pure function of the
    current schedule and current rules. `validate()` only makes sense against a
    current snapshot, so this is skipped entirely when no ScheduleVersion exists yet."""
    state, warnings = assemble_planning_state(conn, site_id=site_id, month=month)
    current_id = get_current_version_id(conn, site_id, month)
    current_version = get_schedule_version_header(conn, current_id) if current_id else None
    if current_version is not None:
        report = validate(state, list(state.existing_assignments))
        warnings = [*warnings, *report.warnings]
    history = tuple(list_schedule_versions(conn, site_id, month))
    return OpenMonthView(
        site=state.site, profile=state.profile, employees=state.employees, memberships=state.memberships,
        availability_records=state.availability_records,
        resolved_rules=state.site_rules, unresolved_rules=state.unresolved_site_rules,
        current_version=current_version, version_history=history, work_balances=state.work_balances,
        warnings=tuple(warnings),
    )


def months_with_schedule(conn, *, site_id: str) -> tuple[date, ...]:
    """ROTA-T011-B (B-6=W1+filtr obsady): months whose CURRENT version has
    at least one Assignment -- a month whose only version is the empty root
    plan_month creates before ever calling the solver does not qualify."""
    return tuple(list_months_with_assignments(conn, site_id))
