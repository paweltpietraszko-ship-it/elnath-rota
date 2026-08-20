"""ROTA-T010-A -- first configuration + current roster
(tasks/ROTA-T010/part_a_bootstrap_roster.md).

One application-layer write path serves both the very first save and later
resumes of the same Coordinator -> SiteProfile -> Site ->
CoordinatorSiteAssociation chain. No separate onboarding flag, no onboarding
step number, no UI here. Once (coordinator_id, site_id) already has an
active CoordinatorSiteAssociation, this operation refuses -- ordinary edits
go through require_active_coordinator_context() + the existing T009
rota.application.durable_inputs functions instead.

DECYZJA WLASCICIELA 2026-08-14 (part_a_bootstrap_roster.md): every function
below takes an explicit site_id -- multi-object management (a coordinator
managing more than one Site) is out of scope for T010, but nothing here may
assume "at most one context per coordinator" as a permanent constraint,
since Panel Sterowania (T012) will call these same functions again with a
different site_id for a second object.

Two separate reads (part_a_bootstrap_roster.md DWA ODCZYTY, DWA ZNACZENIA):
- coordinator_context_completeness(): durable, month-independent.
- month_plan_readiness(): the above plus a full CalendarDay for every day
  of one specific month. Missing target_hours is reported but never blocks
  readiness (T009 SOFT/balance concern, not a PLAN precondition).
"""
from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from datetime import date, datetime

from rota.application.context import require_active_coordinator_context
from rota.application.errors import CoordinatorContextAlreadyActive, InvalidCoordinatorContext
from rota.domain import (
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    Site,
    SiteProfile,
    StandardShift,
)
from rota.persistence import site_memory
from rota.persistence.calendar_repository import list_calendar_days
from rota.persistence.coordinator_repository import (
    CoordinatorNotFound,
    activate_association_if_not_already_active_in_open_transaction,
    get_coordinator,
    list_associations_for_coordinator,
    list_coordinators,
    write_coordinator_in_open_transaction,
)
from rota.persistence.employee_repository import get_employee, list_memberships_for_site
from rota.persistence.site_profile_repository import SiteProfileNotFound, get_site_profile, write_site_profile_in_open_transaction
from rota.persistence.site_repository import SiteNotFound, get_site, write_site_in_open_transaction
from rota.persistence.work_balance_repository import get_work_balance_target
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind


def _is_valid_standard_shift(shift: StandardShift) -> bool:
    """R3-1: a row present in standard_shifts is not by itself proof of a
    usable configuration -- it must be able to produce a legal ShiftDemand
    (same invariants as assembler.generate_profile_demands /
    schedule_validation.validate_demands: end > start, required_primary_count
    > 0). end_next_day always yields end > start regardless of the times."""
    if shift.required_primary_count <= 0:
        return False
    return shift.end_next_day or shift.end_time > shift.start_time


def _has_active_association(conn, *, coordinator_id: str, site_id: str) -> bool:
    return any(
        a.site_id == site_id and a.active
        for a in list_associations_for_coordinator(conn, coordinator_id)
    )


def _has_full_active_context(conn, *, coordinator_id: str, site_id: str) -> bool:
    """ROTA-T011-C (FINDING C-R3-1): bootstrap must refuse resume exactly
    when the ordinary edit path (require_active_coordinator_context) is
    already usable -- not merely when the Association row is active. T011-C
    added update_site/update_coordinator, which can deactivate Site.active
    or Coordinator.active while the Association stays active; in that state
    durable_inputs is already blocked by the guard, so refusing resume here
    on Association-alone would leave no public path back at all, the exact
    permanent lockout the brief's 'samozablokowanie jest odwracalne' promise
    forbids. Reuses require_active_coordinator_context's own three-part
    definition of "active" instead of duplicating it."""
    try:
        require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
        return True
    except InvalidCoordinatorContext:
        return False


def _require_id_match(label: str, actual: tuple[str, ...], expected: tuple[str, ...]) -> None:
    if actual != expected:
        raise ValueError(f"{label} {actual!r} != {expected!r}")


def _planning_fields(p) -> tuple:
    if isinstance(p, SiteProfile):
        return (
            p.active, tuple(p.standard_shifts), p.day_only_blocks_n, p.external_support_enabled,
            p.training_s_enabled, p.training_s_weekdays_only, p.training_s_default_readiness_threshold,
            p.rolling_7d_decision_threshold_hours,
        )
    return (p.profile_id, p.active)  # Site: profile_id/active are the planning-relevant fields


def _profile_state(p: SiteProfile | None) -> dict | None:
    if p is None:
        return None
    return {
        "profile_id": p.profile_id, "active": p.active,
        "standard_shifts": [
            {
                "kind": s.kind.value, "start_time": s.start_time.isoformat(), "end_time": s.end_time.isoformat(),
                "end_next_day": s.end_next_day, "required_primary_count": s.required_primary_count,
            }
            for s in p.standard_shifts
        ],
        "day_only_blocks_n": p.day_only_blocks_n, "external_support_enabled": p.external_support_enabled,
        "training_s_enabled": p.training_s_enabled, "training_s_weekdays_only": p.training_s_weekdays_only,
        "training_s_default_readiness_threshold": p.training_s_default_readiness_threshold,
        "rolling_7d_decision_threshold_hours": p.rolling_7d_decision_threshold_hours,
    }


def _site_state(s: Site | None) -> dict | None:
    return None if s is None else {"site_id": s.site_id, "profile_id": s.profile_id, "active": s.active}


def _record_context_configuration_no_commit(
    conn, *, coordinator_id: str, site_id: str, recorded_at: datetime,
    before_profile: SiteProfile | None, site_profile: SiteProfile | None,
    before_site: Site | None, site: Site | None,
) -> None:
    entities = []
    if site_profile is not None:
        entities.append(AffectedEntity("SITE_PROFILE", site_profile.profile_id))
    if site is not None:
        entities.append(AffectedEntity("SITE", site.site_id))
    site_memory.record_coordinator_action_no_commit(
        conn, action_kind=CoordinatorActionKind.CONTEXT_CONFIGURATION_SAVED, origin_site_id=site_id,
        affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
        effective_from=recorded_at.date(), month=None, schedule_version_id=None, affected_entities=entities,
        before_state={"site_profile": _profile_state(before_profile), "site": _site_state(before_site)},
        after_state={"site_profile": _profile_state(site_profile), "site": _site_state(site)},
        note=None, source_kind=ActionSourceKind.CURRENT_STATE, source_id=site_id,
        responds_to_decision_required_id=None,
    )
    site_memory.invalidate_current_decision_required_no_commit(conn, site_ids=[site_id], months=None)


def _material_config_change(conn, *, site_id: str, site_profile, site):
    """ROTA-T019b: whether this bootstrap call's site_profile/site pieces
    are a planning-relevant change worth one CONTEXT_CONFIGURATION_SAVED
    action, and their before-state for it. origin_site_id is a hard FK to
    sites.site_id: a config action cannot be attributed to a Site row that
    does not exist yet -- if this call itself creates the Site that's fine
    (written earlier in the same transaction), otherwise the action is
    deferred until a later call actually establishes the Site."""
    before_profile = None
    if site_profile is not None:
        try:
            before_profile = get_site_profile(conn, site_profile.profile_id)
        except SiteProfileNotFound:
            before_profile = None
    try:
        before_site = get_site(conn, site_id)
    except SiteNotFound:
        before_site = None
    profile_changed = site_profile is not None and (
        before_profile is None or _planning_fields(before_profile) != _planning_fields(site_profile)
    )
    site_changed = site is not None and (before_site is None or _planning_fields(before_site) != _planning_fields(site))
    site_exists_or_created = site is not None or before_site is not None
    material = (profile_changed or site_changed) and site_exists_or_created
    return material, before_profile, before_site


def bootstrap_or_resume_coordinator_context(
    conn,
    *,
    coordinator_id: str,
    site_id: str,
    coordinator: Coordinator | None = None,
    site_profile: SiteProfile | None = None,
    site: Site | None = None,
    association: CoordinatorSiteAssociation | None = None,
) -> None:
    """The one small write operation from part_a_bootstrap_roster.md. Persists
    whichever of the four entities are supplied this call -- callers resume
    a partial context over several calls by re-supplying the same
    coordinator_id/site_id with more pieces filled in each time.

    R3-2/C-R3-1: the upfront _has_full_active_context check is a fast,
    friendly rejection; the real exclusivity guard is
    activate_association_if_not_already_active_in_open_transaction's atomic
    UPSERT...WHERE, called last -- after coordinator/profile/site writes
    (idempotent resume data, harmless either way).

    ROTA-T019b: coordinator/site_profile/site writes plus the one conditional
    CONTEXT_CONFIGURATION_SAVED action commit as a single transaction.
    Association activation stays its own separate transaction (no material
    action of its own; must keep its idempotent-resume-survives-a-lost-race
    behavior)."""
    if _has_full_active_context(conn, coordinator_id=coordinator_id, site_id=site_id):
        raise CoordinatorContextAlreadyActive(
            f"({coordinator_id!r}, {site_id!r}) already has an active context; "
            "use the T009 authorized edit operations instead"
        )
    if coordinator is not None:
        _require_id_match("coordinator.coordinator_id", (coordinator.coordinator_id,), (coordinator_id,))
    if site is not None:
        _require_id_match("site.site_id", (site.site_id,), (site_id,))

    recorded_at = datetime.now()
    material, before_profile, before_site = _material_config_change(conn, site_id=site_id, site_profile=site_profile, site=site)

    with conn:
        if coordinator is not None:
            write_coordinator_in_open_transaction(conn, coordinator)
        if site_profile is not None:
            write_site_profile_in_open_transaction(conn, site_profile)
        if site is not None:
            write_site_in_open_transaction(conn, site)
        if material:
            _record_context_configuration_no_commit(
                conn, coordinator_id=coordinator_id, site_id=site_id, recorded_at=recorded_at,
                before_profile=before_profile, site_profile=site_profile, before_site=before_site, site=site,
            )

    if association is not None:
        _require_id_match(
            "association (coordinator_id, site_id)",
            (association.coordinator_id, association.site_id), (coordinator_id, site_id),
        )
        _activate_association_or_raise(conn, coordinator_id=coordinator_id, site_id=site_id, association=association)


def _activate_association_or_raise(conn, *, coordinator_id: str, site_id: str, association: CoordinatorSiteAssociation) -> None:
    with conn:
        won = activate_association_if_not_already_active_in_open_transaction(conn, association)
    if not won:
        raise CoordinatorContextAlreadyActive(
            f"({coordinator_id!r}, {site_id!r}) was activated by a concurrent bootstrap first"
        )


@dataclass(frozen=True)
class ContextCompleteness:
    complete: bool
    missing: tuple[str, ...]


def coordinator_context_completeness(conn, *, coordinator_id: str, site_id: str) -> ContextCompleteness:
    """Durable, month-independent: active Coordinator/SiteProfile/Site/
    Association, >=1 standard shift, >=1 active LOCAL SiteMembership with an
    existing Employee."""
    missing: list[str] = []

    try:
        coordinator = get_coordinator(conn, coordinator_id)
        if not coordinator.active:
            missing.append(f"coordinator {coordinator_id!r} is not active")
    except CoordinatorNotFound:
        missing.append(f"coordinator {coordinator_id!r} does not exist")

    try:
        site = get_site(conn, site_id)
        if not site.active:
            missing.append(f"site {site_id!r} is not active")
        else:
            profile = get_site_profile(conn, site.profile_id)
            if not profile.active:
                missing.append(f"site profile {site.profile_id!r} is not active")
            elif not any(_is_valid_standard_shift(s) for s in profile.standard_shifts):
                missing.append(f"site profile {site.profile_id!r} has no valid standard shift")
    except SiteNotFound:
        missing.append(f"site {site_id!r} does not exist")

    if not _has_active_association(conn, coordinator_id=coordinator_id, site_id=site_id):
        missing.append(f"no active CoordinatorSiteAssociation for ({coordinator_id!r}, {site_id!r})")

    memberships = list_memberships_for_site(conn, site_id)
    has_local_roster = any(
        m.enabled and m.membership_kind == MembershipKind.LOCAL and _employee_exists(conn, m.employee_id)
        for m in memberships
    )
    if not has_local_roster:
        missing.append(f"site {site_id!r} has no active LOCAL SiteMembership")

    return ContextCompleteness(complete=not missing, missing=tuple(missing))


def _employee_exists(conn, employee_id: str) -> bool:
    try:
        get_employee(conn, employee_id)
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class MonthPlanReadiness:
    ready: bool
    missing: tuple[str, ...]
    target_hours_warnings: tuple[str, ...]


def month_plan_readiness(conn, *, coordinator_id: str, site_id: str, month: date) -> MonthPlanReadiness:
    """Context completeness plus a full CalendarDay for every day of
    `month`. Computed independently per month -- the same Site can be ready
    for one month and not ready for another. Missing target_hours never
    blocks readiness; it is reported separately for the existing T009
    SOFT/balance concern."""
    if month.day != 1:
        raise ValueError(f"month {month} is not the first day of its month")

    completeness = coordinator_context_completeness(conn, coordinator_id=coordinator_id, site_id=site_id)
    missing = list(completeness.missing)

    days_in_month = _calendar.monthrange(month.year, month.month)[1]
    range_start = date(month.year, month.month, 1)
    range_end = date(month.year, month.month, days_in_month)
    existing_days = {d.date for d in list_calendar_days(conn, range_start, range_end)}
    for day in range(1, days_in_month + 1):
        current = date(month.year, month.month, day)
        if current not in existing_days:
            missing.append(f"missing CalendarDay for {current.isoformat()}")

    target_hours_warnings: list[str] = []
    if completeness.complete:
        for m in list_memberships_for_site(conn, site_id):
            if m.enabled and m.membership_kind == MembershipKind.LOCAL:
                if get_work_balance_target(conn, m.employee_id, range_start) is None:
                    target_hours_warnings.append(
                        f"missing target_hours for employee {m.employee_id!r}, month {range_start.isoformat()}"
                    )

    return MonthPlanReadiness(
        ready=not missing,
        missing=tuple(missing),
        target_hours_warnings=tuple(target_hours_warnings),
    )


def current_roster(conn, *, site_id: str) -> tuple[Employee, ...]:
    """Bierzaca obsada: Employee rows for every enabled=true SiteMembership
    of this Site. Disabling (enabled=false) removes an Employee from this
    read without deleting the Employee row or its membership history; a
    later re-enable of the same membership makes it reappear here."""
    memberships = list_memberships_for_site(conn, site_id)
    return tuple(get_employee(conn, m.employee_id) for m in memberships if m.enabled)


def active_coordinators(conn) -> tuple[Coordinator, ...]:
    """ROTA-T011-B (A-3, B-3=W3): 'w co mogę wejść' -- only Coordinator.active."""
    return tuple(c for c in list_coordinators(conn) if c.active)


def all_coordinators(conn) -> tuple[Coordinator, ...]:
    """ROTA-T011-B (A-3, B-3=W3): 'co istnieje' -- unfiltered, for T012's
    administrative panel."""
    return tuple(list_coordinators(conn))


def active_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]:
    """ROTA-T011-B (A-3, B-3=W3): only associations with active=True, mapped
    to Site, keeping only Site.active=True. Does not check the coordinator's
    own active flag -- that is active_coordinators's and
    require_active_coordinator_context's job."""
    associations = list_associations_for_coordinator(conn, coordinator_id)
    sites = (get_site(conn, a.site_id) for a in associations if a.active)
    return tuple(s for s in sites if s.active)


def all_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]:
    """ROTA-T011-B (A-3, B-3=W3): every association for this coordinator,
    active or not, mapped to Site without any Site.active filter."""
    associations = list_associations_for_coordinator(conn, coordinator_id)
    return tuple(get_site(conn, a.site_id) for a in associations)
