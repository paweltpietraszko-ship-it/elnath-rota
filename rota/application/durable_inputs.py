"""Operation 6 (tasks/ROTA-T009/brief.md): thin commands for existing
durable facts needed by the coordinator workflow. Each validates
coordinator context and delegates to the existing repository -- no new
abstraction beyond that.

ROTA-T019b: every command below also durably records one coordinator-action
entry when the write is schedule-material (tasks/ROTA-T019b/operation_audit.md),
atomically with its domain write and any stale-current-question invalidation.
"""
from __future__ import annotations

from datetime import date, datetime

from rota.application.context import require_active_coordinator_context
from rota.application.errors import InvalidCoordinatorContext
from rota.domain import (
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    Site,
    SiteMembership,
    SiteProfile,
)
from rota.persistence import site_memory
from rota.persistence.availability_repository import append_availability_version_in_open_transaction, get_availability_history
from rota.persistence.calendar_repository import get_calendar_day, write_calendar_day_in_open_transaction
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.employee_repository import (
    EmployeeNotFound,
    get_employee,
    get_external_support_window,
    list_memberships_for_employee,
    list_memberships_for_site,
    write_employee_in_open_transaction,
    write_external_support_window_in_open_transaction,
    write_site_membership_in_open_transaction,
)
from rota.persistence.site_profile_repository import SiteProfileNotFound, get_site_profile, write_site_profile_in_open_transaction
from rota.persistence.site_repository import SiteNotFound, get_site, list_sites, write_site_in_open_transaction
from rota.persistence.work_balance_repository import get_work_balance_target, write_work_balance_target_in_open_transaction
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind


def _require_payload_belongs_to_site(payload_site_id: str, site_id: str) -> None:
    """R4-3-B: the coordinator's active context for site_id must not
    authorize mutating a payload whose own Site scope is a different Site."""
    if payload_site_id != site_id:
        raise InvalidCoordinatorContext(
            f"payload belongs to site {payload_site_id!r}, not the authorized site {site_id!r}"
        )


def _normalize_note(note: str | None) -> str | None:
    if note is None:
        return None
    trimmed = note.strip()
    return trimmed or None


def _employee_affected_site_ids(conn, employee_id: str, origin_site_id: str) -> list[str]:
    sites = sorted({m.site_id for m in list_memberships_for_employee(conn, employee_id) if m.enabled})
    return sites or [origin_site_id]


def _sites_bound_to_profile(conn, profile_id: str) -> list[str]:
    return sorted(s.site_id for s in list_sites(conn) if s.profile_id == profile_id)


def _add_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _months_overlapped(start_date: date, end_date: date) -> list[date]:
    months = []
    cursor = date(start_date.year, start_date.month, 1)
    end_marker = date(end_date.year, end_date.month, 1)
    while cursor <= end_marker:
        months.append(cursor)
        cursor = _add_month(cursor)
    return months


def _record_action_and_invalidate_no_commit(
    conn, *, action_kind: CoordinatorActionKind, origin_site_id: str, affected_site_ids: list[str],
    coordinator_id: str, recorded_at: datetime, effective_from: date | None, month: date | None,
    affected_entities: list[AffectedEntity], before_state: dict | None, after_state: dict | None,
    note: str | None, source_kind: ActionSourceKind, source_id: str | None,
    responds_to_decision_required_id: str | None, invalidate_months: list[date] | None,
) -> None:
    site_memory.record_coordinator_action_no_commit(
        conn, action_kind=action_kind, origin_site_id=origin_site_id, affected_site_ids=affected_site_ids,
        coordinator_id=coordinator_id, recorded_at=recorded_at, effective_from=effective_from, month=month,
        schedule_version_id=None, affected_entities=affected_entities, before_state=before_state,
        after_state=after_state, note=note, source_kind=source_kind, source_id=source_id,
        responds_to_decision_required_id=responds_to_decision_required_id,
    )
    site_memory.invalidate_current_decision_required_no_commit(conn, site_ids=affected_site_ids, months=invalidate_months)


def add_external_support_window(
    conn, *, coordinator_id: str, site_id: str, window: ExternalSupportWindow,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(window.site_id, site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    try:
        before = get_external_support_window(conn, window.window_id)
        before_state = {
            "employee_id": before.employee_id, "site_id": before.site_id,
            "start_datetime": before.start_datetime, "end_datetime": before.end_datetime,
            "active": before.active, "allowed_shift_kind": before.allowed_shift_kind.value if before.allowed_shift_kind else None,
        }
    except KeyError:
        before_state = None
    with conn:
        write_external_support_window_in_open_transaction(conn, window)
        after_state = {
            "employee_id": window.employee_id, "site_id": window.site_id,
            "start_datetime": window.start_datetime, "end_datetime": window.end_datetime,
            "active": window.active, "allowed_shift_kind": window.allowed_shift_kind.value if window.allowed_shift_kind else None,
        }
        _record_action_and_invalidate_no_commit(
            conn, action_kind=CoordinatorActionKind.EXTERNAL_SUPPORT_WINDOW_CHANGED, origin_site_id=site_id,
            affected_site_ids=[window.site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=window.start_datetime.date(), month=None,
            affected_entities=[
                AffectedEntity("EMPLOYEE", window.employee_id),
                AffectedEntity("EXTERNAL_SUPPORT_WINDOW", window.window_id),
                AffectedEntity("SITE", window.site_id),
            ],
            before_state=before_state, after_state=after_state, note=_normalize_note(note),
            source_kind=ActionSourceKind.CURRENT_STATE, source_id=window.window_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
            invalidate_months=_months_overlapped(window.start_datetime.date(), window.end_datetime.date()),
        )


def append_availability(
    conn, *, coordinator_id: str, site_id: str, availability_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, active: bool, note: str | None = None,
    responds_to_decision_required_id: str | None = None,
):
    """Covers append/supersede (a new version in the same family) and
    deactivate (active=False) alike -- the append-only chain primitive
    already models all three as one operation. `note` is both the
    AvailabilityRecord note and the T019b action note (brief.md section 9)."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    history = get_availability_history(conn, availability_id)
    before = history[-1] if history else None
    before_state = None if before is None else {
        "kind": before.kind.value, "start_date": before.start_date, "end_date": before.end_date,
        "active": before.active, "note": before.note,
    }
    normalized_note = _normalize_note(note)
    with conn:
        record = append_availability_version_in_open_transaction(
            conn, availability_id=availability_id, employee_id=employee_id, kind=kind,
            start_date=start_date, end_date=end_date, active=active, note=normalized_note,
        )
        after_state = {
            "kind": record.kind.value, "start_date": record.start_date, "end_date": record.end_date,
            "active": record.active, "note": record.note,
        }
        affected_site_ids = _employee_affected_site_ids(conn, employee_id, site_id)
        _record_action_and_invalidate_no_commit(
            conn, action_kind=CoordinatorActionKind.AVAILABILITY_CHANGED, origin_site_id=site_id,
            affected_site_ids=affected_site_ids, coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=start_date, month=None,
            affected_entities=[AffectedEntity("EMPLOYEE", employee_id), AffectedEntity("AVAILABILITY", availability_id)],
            before_state=before_state, after_state=after_state, note=normalized_note,
            source_kind=ActionSourceKind.AVAILABILITY_VERSION, source_id=record.availability_version_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
            invalidate_months=_months_overlapped(start_date, end_date),
        )
    return record


def update_employee(
    conn, *, coordinator_id: str, site_id: str, employee: Employee,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    try:
        before = get_employee(conn, employee.employee_id)
    except EmployeeNotFound:
        before = None
    material = before is None or before.day_only != employee.day_only
    with conn:
        write_employee_in_open_transaction(conn, employee)
        if material:
            affected_site_ids = _employee_affected_site_ids(conn, employee.employee_id, site_id)
            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.EMPLOYEE_DAY_ONLY_CHANGED, origin_site_id=site_id,
                affected_site_ids=affected_site_ids, coordinator_id=coordinator_id, recorded_at=recorded_at,
                effective_from=recorded_at.date(), month=None,
                affected_entities=[AffectedEntity("EMPLOYEE", employee.employee_id)],
                before_state=None if before is None else {"employee_id": before.employee_id, "day_only": before.day_only},
                after_state={"employee_id": employee.employee_id, "day_only": employee.day_only},
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE, source_id=employee.employee_id,
                responds_to_decision_required_id=responds_to_decision_required_id, invalidate_months=None,
            )


def update_membership(
    conn, *, coordinator_id: str, site_id: str, membership: SiteMembership,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(membership.site_id, site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    before = next(
        (m for m in list_memberships_for_site(conn, site_id) if m.employee_id == membership.employee_id), None,
    )
    material = before is None or (
        before.membership_kind, before.enabled, before.readiness_state, before.readiness_source, before.can_work_24h
    ) != (
        membership.membership_kind, membership.enabled, membership.readiness_state, membership.readiness_source,
        membership.can_work_24h,
    )
    with conn:
        write_site_membership_in_open_transaction(conn, membership)
        if material:

            def _membership_state(m):
                return None if m is None else {
                    "employee_id": m.employee_id, "site_id": m.site_id, "membership_kind": m.membership_kind.value,
                    "enabled": m.enabled, "readiness_state": m.readiness_state.value,
                    "readiness_source": m.readiness_source.value, "can_work_24h": m.can_work_24h,
                }

            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.SITE_MEMBERSHIP_CHANGED, origin_site_id=site_id,
                affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
                effective_from=recorded_at.date(), month=None,
                affected_entities=[AffectedEntity("EMPLOYEE", membership.employee_id), AffectedEntity("SITE_MEMBERSHIP", f"{membership.employee_id}:{site_id}")],
                before_state=_membership_state(before), after_state=_membership_state(membership),
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE,
                source_id=f"{membership.employee_id}:{site_id}",
                responds_to_decision_required_id=responds_to_decision_required_id, invalidate_months=None,
            )


def set_target_hours(
    conn, *, coordinator_id: str, site_id: str, employee_id: str, month: date, target_hours: int,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    before = get_work_balance_target(conn, employee_id, month)
    with conn:
        write_work_balance_target_in_open_transaction(conn, employee_id=employee_id, month=month, target_hours=target_hours)
        if before != target_hours:
            affected_site_ids = _employee_affected_site_ids(conn, employee_id, site_id)
            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.TARGET_HOURS_CHANGED, origin_site_id=site_id,
                affected_site_ids=affected_site_ids, coordinator_id=coordinator_id, recorded_at=recorded_at,
                effective_from=month, month=month,
                affected_entities=[AffectedEntity("EMPLOYEE", employee_id), AffectedEntity("WORK_BALANCE_TARGET", f"{employee_id}:{month.isoformat()}")],
                before_state={"employee_id": employee_id, "month": month, "target_hours": before},
                after_state={"employee_id": employee_id, "month": month, "target_hours": target_hours},
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE,
                source_id=f"{employee_id}:{month.isoformat()}",
                responds_to_decision_required_id=responds_to_decision_required_id, invalidate_months=[month],
            )


def set_calendar_day(
    conn, *, coordinator_id: str, site_id: str, day: CalendarDay,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    """ROTA-T011-A (A-1): calendar_days is keyed by date alone, not scoped to
    a Site -- site_id here authorizes the coordinator's write, exactly like
    set_target_hours, and is never itself persisted."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    try:
        before = get_calendar_day(conn, day.date)
        before_holiday = before.holiday
    except KeyError:
        before_holiday = None
    with conn:
        write_calendar_day_in_open_transaction(conn, day)
        if before_holiday != day.holiday:
            affected_site_ids = [s.site_id for s in list_sites(conn)]
            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.CALENDAR_DAY_CHANGED, origin_site_id=site_id,
                affected_site_ids=affected_site_ids or [site_id], coordinator_id=coordinator_id,
                recorded_at=recorded_at, effective_from=day.date, month=date(day.date.year, day.date.month, 1),
                affected_entities=[AffectedEntity("CALENDAR_DAY", day.date.isoformat())],
                before_state={"date": day.date, "holiday": before_holiday},
                after_state={"date": day.date, "holiday": day.holiday},
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE, source_id=day.date.isoformat(),
                responds_to_decision_required_id=responds_to_decision_required_id,
                invalidate_months=[date(day.date.year, day.date.month, 1)],
            )


def update_site_profile(
    conn, *, coordinator_id: str, site_id: str, profile: SiteProfile,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    owning_site = get_site(conn, site_id)
    if profile.profile_id != owning_site.profile_id:
        raise InvalidCoordinatorContext(
            f"profile {profile.profile_id!r} does not belong to the authorized site {site_id!r}"
        )
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()

    def _planning_fields(p):
        return (
            p.active, tuple(p.standard_shifts), p.day_only_blocks_n, p.external_support_enabled,
            p.training_s_enabled, p.training_s_weekdays_only, p.training_s_default_readiness_threshold,
            p.rolling_7d_decision_threshold_hours,
        )

    try:
        before = get_site_profile(conn, profile.profile_id)
    except SiteProfileNotFound:
        before = None
    material = before is None or _planning_fields(before) != _planning_fields(profile)
    with conn:
        write_site_profile_in_open_transaction(conn, profile)
        if material:

            def _profile_state(p):
                return None if p is None else {
                    "profile_id": p.profile_id, "active": p.active,
                    "standard_shifts": [
                        {
                            "kind": s.kind.value, "start_time": s.start_time.isoformat(), "end_time": s.end_time.isoformat(),
                            "end_next_day": s.end_next_day, "required_primary_count": s.required_primary_count,
                            "catalog_kind": s.catalog_kind.value if s.catalog_kind else None,
                            "required_rest_hours": s.required_rest_hours, "active_weekdays": list(s.active_weekdays),
                        }
                        for s in p.standard_shifts
                    ],
                    "day_only_blocks_n": p.day_only_blocks_n, "external_support_enabled": p.external_support_enabled,
                    "training_s_enabled": p.training_s_enabled, "training_s_weekdays_only": p.training_s_weekdays_only,
                    "training_s_default_readiness_threshold": p.training_s_default_readiness_threshold,
                    "rolling_7d_decision_threshold_hours": p.rolling_7d_decision_threshold_hours,
                }

            affected_site_ids = _sites_bound_to_profile(conn, profile.profile_id)
            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.SITE_PROFILE_CHANGED, origin_site_id=site_id,
                affected_site_ids=affected_site_ids or [site_id], coordinator_id=coordinator_id,
                recorded_at=recorded_at, effective_from=recorded_at.date(), month=None,
                affected_entities=[AffectedEntity("SITE_PROFILE", profile.profile_id)],
                before_state=_profile_state(before), after_state=_profile_state(profile),
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE, source_id=profile.profile_id,
                responds_to_decision_required_id=responds_to_decision_required_id, invalidate_months=None,
            )


def update_site(
    conn, *, coordinator_id: str, site_id: str, site: Site,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> None:
    """ROTA-T011-C (B-2=W1): a plain upsert like update_employee/
    update_membership -- Site is a MUTABLE CURRENT-STATE ENTITY (T008),
    not a versioned one. profile_id may never change here: rebinding a
    Site to a different profile silently changes its standard-shift
    catalog and retroactively changes training-readiness qualification
    (training._qualifies_for_readiness reads the CURRENT profile, R6-4).
    That rebind is a separate, explicitly named operation with its own
    product question about retroactivity -- never a side effect of an
    ordinary name/active edit. profile_id stays settable only through
    bootstrap_or_resume_coordinator_context."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(site.site_id, site_id)
    owning_site = get_site(conn, site_id)
    if site.profile_id != owning_site.profile_id:
        raise InvalidCoordinatorContext(
            f"update_site must not rebind profile_id ({owning_site.profile_id!r} -> {site.profile_id!r}); "
            "changing a Site's profile is a separate, explicit operation"
        )
    site_memory.validate_decision_required_link_no_commit(
        conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
    )
    recorded_at = datetime.now()
    try:
        before = get_site(conn, site.site_id)
    except SiteNotFound:
        before = None
    material = before is None or before.active != site.active
    with conn:
        write_site_in_open_transaction(conn, site)
        if material:
            _record_action_and_invalidate_no_commit(
                conn, action_kind=CoordinatorActionKind.SITE_ACTIVE_CHANGED, origin_site_id=site_id,
                affected_site_ids=[site.site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
                effective_from=recorded_at.date(), month=None,
                affected_entities=[AffectedEntity("SITE", site.site_id)],
                before_state=None if before is None else {"site_id": before.site_id, "active": before.active},
                after_state={"site_id": site.site_id, "active": site.active},
                note=_normalize_note(note), source_kind=ActionSourceKind.CURRENT_STATE, source_id=site.site_id,
                responds_to_decision_required_id=responds_to_decision_required_id, invalidate_months=None,
            )


def update_coordinator(conn, *, coordinator_id: str, site_id: str, coordinator: Coordinator) -> None:
    """ROTA-T011-C (ROZSTRZYGNIĘCIE WŁAŚCICIELA 2026-08-14): deliberately no
    coordinator-identity check -- the acting coordinator may write another
    coordinator's own record (rename it, set active=False). This is an
    accepted product decision, not an oversight: this product has no
    multi-user-per-installation model (each coordinator gets their own
    installation) and login/permissions are separate, deferred work.
    Literal copy of update_employee's shape -- Coordinator carries no
    site_id to compare against.

    ROTA-T019b: NOT a material coordinator action (operation_audit.md) --
    access/identity metadata, not a scheduling decision."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    save_coordinator(conn, coordinator)


def update_association(conn, *, coordinator_id: str, site_id: str, association: CoordinatorSiteAssociation) -> None:
    """ROTA-T011-C (B-2=W1): a plain upsert -- save_coordinator_site_
    association has no WHERE clause and already allows active: 1 -> 0.
    The CAS-guarded activation path stays exclusive to bootstrap/resume;
    this is the ordinary edit path for a context that already exists.
    No coordinator-identity check either, same accepted decision as
    update_coordinator: only association.site_id is checked, matching the
    authorized site.

    ROTA-T019b: NOT a material coordinator action (operation_audit.md) --
    access metadata, not a schedule-content/planning-input decision."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    _require_payload_belongs_to_site(association.site_id, site_id)
    save_coordinator_site_association(conn, association)
