"""ONE CANONICAL PLANNINGSTATE ASSEMBLER (tasks/ROTA-T009/brief.md).

Read-only. Builds a PlanningState for (site_id, month) from LocalStore, or
(when shift_demands/assignments/deviations are supplied directly) around a
prepared-but-not-yet-persisted ScheduleVersion snapshot -- used by the
atomic manual-correction flow (review_02_architect_clarification.md) to
validate a child before it is ever written.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from rota.application.errors import IncompleteCalendarData, ScheduleVersionContextMismatch
from rota.balance import MissingTargetHoursError
from rota.domain import (
    Assignment,
    AvailabilityRecord,
    CalendarDay,
    Deviation,
    Employee,
    ExternalSupportWindow,
    ShiftDemand,
    SiteMembership,
    WorkBalance,
)
from rota.persistence.availability_repository import get_current_availability_for_employee
from rota.persistence.calendar_repository import list_calendar_days
from rota.persistence.employee_repository import get_employee, list_memberships_for_site, list_windows_for_site
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.persistence.schedule_repository import (
    get_current_assignments_for_employees,
    get_current_assignments_in_interval,
    get_current_realized_primary_on_holidays,
    get_current_schedule_snapshot,
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
)
from rota.persistence.work_balance_repository import reconstruct_month_balance
from rota.planning.state import PlanningState


def resolved_rule_version_ids(conn, site_id: str, month: date) -> list[str]:
    """Shared by every operation that must set applied_rule_version_ids from
    the currently assembled RESOLVED monthly rule versions (brief.md
    sections 3, 5, 8)."""
    resolved, _, _ = assemble_monthly_site_rules(conn, site_id, month)
    return [r.rule_version_id for r in resolved]


def generate_profile_demands(profile, month: date) -> tuple[ShiftDemand, ...]:
    """INITIAL SHIFTDEMAND GENERATION: pure data expansion from
    SiteProfile.standard_shifts, independent of roster/target_hours/
    absences/X-Y. One occurrence of every configured StandardShift per
    calendar day.

    R4-8: demand_id stays exactly "{date}-{kind}" for the common case (one
    StandardShift per ShiftKind), preserving every existing id assumption --
    a profile with more than one StandardShift of the SAME kind (e.g. two
    differently-timed D shifts) instead gets a "-{n}" occurrence suffix so
    each configured shift still gets its own distinct, deterministic demand
    per day."""
    days = calendar.monthrange(month.year, month.month)[1]
    kind_counts: dict = {}
    for shift in profile.standard_shifts:
        kind_counts[shift.kind] = kind_counts.get(shift.kind, 0) + 1
    demands = []
    for day in range(1, days + 1):
        current = date(month.year, month.month, day)
        kind_seen: dict = {}
        for shift in profile.standard_shifts:
            start = datetime.combine(current, shift.start_time)
            end = start + timedelta(days=1 if shift.end_next_day else 0)
            end = datetime.combine(end.date(), shift.end_time)
            occurrence = kind_seen.get(shift.kind, 0)
            kind_seen[shift.kind] = occurrence + 1
            suffix = f"-{occurrence}" if kind_counts[shift.kind] > 1 else ""
            demand_id = f"{current.isoformat()}-{shift.kind.value}{suffix}"
            demands.append(ShiftDemand(demand_id, "", start, end, shift.required_primary_count))
    return tuple(demands)


def _assemble_calendar(conn, month: date) -> tuple[CalendarDay, ...]:
    days = calendar.monthrange(month.year, month.month)[1]
    range_start, range_end = date(month.year, month.month, 1), date(month.year, month.month, days)
    rows = {day.date: day for day in list_calendar_days(conn, range_start, range_end)}
    result = []
    for day in range(1, days + 1):
        current = date(month.year, month.month, day)
        if current not in rows:
            raise IncompleteCalendarData(f"missing CalendarDay for {current}")
        result.append(rows[current])
    return tuple(result)


def _assemble_roster(conn, site_id: str) -> tuple[tuple[SiteMembership, ...], tuple[Employee, ...]]:
    memberships = tuple(list_memberships_for_site(conn, site_id))
    employees = tuple(get_employee(conn, m.employee_id) for m in memberships)
    return memberships, employees


def _assemble_windows_and_availability(
    conn, site_id: str, employee_ids: list[str],
) -> tuple[tuple[ExternalSupportWindow, ...], tuple[AvailabilityRecord, ...]]:
    """brief.md ONE CANONICAL PLANNINGSTATE ASSEMBLER: 'current active
    AvailabilityRecords' -- the chain-end record for an inactive family is
    still current (correct for other reads) but must not enter PlanningState
    as if it were live availability data (R4-11-A)."""
    windows = tuple(list_windows_for_site(conn, site_id))
    availability: list[AvailabilityRecord] = []
    for employee_id in employee_ids:
        availability.extend(
            record for record in get_current_availability_for_employee(conn, employee_id) if record.active
        )
    return windows, tuple(availability)


def _assemble_work_balances(conn, employee_ids: list[str], month: date) -> tuple[tuple[WorkBalance, ...], list[str]]:
    balances, warnings = [], []
    for employee_id in employee_ids:
        try:
            balances.append(reconstruct_month_balance(conn, employee_id=employee_id, month=month))
        except MissingTargetHoursError:
            warnings.append(f"missing target_hours for employee {employee_id!r}: omitted from WorkBalance context")
    return tuple(balances), warnings


def _context_window(month: date) -> tuple[datetime, datetime]:
    days = calendar.monthrange(month.year, month.month)[1]
    context_start = datetime.combine(month, datetime.min.time()) - timedelta(days=6)
    month_end = date(month.year, month.month, days)
    context_end = datetime.combine(month_end, datetime.min.time()) + timedelta(days=8)
    return context_start, context_end


def _assemble_cross_context(
    conn, site_id: str, employee_ids: list[str], month: date, exclude_version_ids: frozenset[str],
) -> tuple[tuple[Assignment, ...], tuple[Assignment, ...]]:
    context_start, context_end = _context_window(month)
    boundary_raw = get_current_assignments_in_interval(conn, site_id, context_start, context_end)
    boundary = tuple(a for a in boundary_raw if a.schedule_version_id not in exclude_version_ids)
    other_site = tuple(
        get_current_assignments_for_employees(conn, employee_ids, context_start, context_end, exclude_site_id=site_id)
    )
    return boundary, other_site


def _assemble_version_content(
    conn, site_id: str, month: date, shift_demands, assignments, deviations, schedule_version_id, profile,
) -> tuple[tuple[ShiftDemand, ...], tuple[Assignment, ...], tuple[Deviation, ...], str]:
    """Either uses the explicitly supplied (prepared-in-memory or otherwise
    overridden) content, or reads one specific durable ScheduleVersion when
    schedule_version_id names one explicitly (R4-6: this must work for a
    non-current version too, not silently fall back to current), or reads
    the durable current ScheduleVersion, or -- when none exists yet --
    generates ephemeral profile-derived demands with no assignments/
    deviations (read-only: nothing is persisted here)."""
    if shift_demands is not None:
        return tuple(shift_demands), tuple(assignments or ()), tuple(deviations or ()), schedule_version_id or ""
    if schedule_version_id is not None:
        header = get_schedule_version_header(conn, schedule_version_id)
        # R5-2: the canonical target is the whole (site_id, month,
        # schedule_version_id) tuple -- an existing version_id belonging to
        # a different Site or month is a caller error, not a silent read.
        if header.site_id != site_id or header.month != month:
            raise ScheduleVersionContextMismatch(
                f"{schedule_version_id!r} belongs to ({header.site_id!r}, {header.month!r}), "
                f"not requested ({site_id!r}, {month!r})",
            )
        snapshot = get_schedule_snapshot(conn, schedule_version_id)
        return snapshot.shift_demands, snapshot.assignments, snapshot.deviations, header.version_id
    current = get_current_schedule_snapshot(conn, site_id, month)
    if current is not None:
        header, snapshot = current
        return snapshot.shift_demands, snapshot.assignments, snapshot.deviations, header.version_id
    return generate_profile_demands(profile, month), (), (), ""


def assemble_planning_state(
    conn, *, site_id: str, month: date,
    shift_demands=None, assignments=None, deviations=None, schedule_version_id=None,
) -> tuple[PlanningState, list[str]]:
    site = get_site(conn, site_id)
    profile = get_site_profile(conn, site.profile_id)
    calendar_days = _assemble_calendar(conn, month)
    memberships, employees = _assemble_roster(conn, site_id)
    employee_ids = [e.employee_id for e in employees]
    windows, availability = _assemble_windows_and_availability(conn, site_id, employee_ids)
    resolved, unresolved, applicability = assemble_monthly_site_rules(conn, site_id, month)

    demands, existing, devs, version_id = _assemble_version_content(
        conn, site_id, month, shift_demands, assignments, deviations, schedule_version_id, profile,
    )
    # R4-2/R4-6/R5-2: the assembled target version's own content (whether
    # read fresh, explicitly named, or a prepared-in-memory snapshot) must
    # never also re-enter through boundary/holiday_history -- both of those
    # exist only for OTHER (surrounding/cross-Site/other-month) current
    # work. The requested target MONTH is never its own surrounding
    # context either, so its current version is excluded even when an
    # explicit non-current version_id was requested instead.
    current_target_version_id = get_current_version_id(conn, site_id, month)
    exclude_version_ids = frozenset(v for v in (version_id, current_target_version_id) if v)
    boundary, other_site = _assemble_cross_context(conn, site_id, employee_ids, month, exclude_version_ids)
    work_balances, warnings = _assemble_work_balances(conn, employee_ids, month)
    holiday_history_raw = get_current_realized_primary_on_holidays(conn, site_id)
    holiday_history = tuple(a for a in holiday_history_raw if a.schedule_version_id not in exclude_version_ids)

    state = PlanningState(
        site=site, profile=profile, month=month, calendar_days=calendar_days,
        boundary_assignments=boundary, memberships=memberships, employees=employees,
        external_windows=windows, availability_records=availability,
        site_rules=resolved, unresolved_site_rules=unresolved, site_rule_applicability=applicability,
        shift_demands=demands, existing_assignments=existing, deviations=devs,
        work_balances=work_balances, holiday_history=holiday_history, other_site_assignments=other_site,
        schedule_version_id=version_id,
    )
    return state, warnings
