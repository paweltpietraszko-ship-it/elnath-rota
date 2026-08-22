"""Excused-absence day counting shared by TARGET-01 (solver.py) and
WorkBalance quarterly tracking (rota/balance.py).

Owner decision 2026-08-12/2026-08-13, from real ROYALPACK/APEXIM schedules
(Grafiki/): SICK_LEAVE and LEAVE_GRANTED both reduce the expected monthly
hour quota by a flat EXCUSED_ABSENCE_HOURS_PER_DAY (8h), regardless of
actual shift length (12h D/N) -- confirmed identical hour-accounting
treatment for both kinds. T018 owner decision 2026-08-19 superseded "per
calendar day" with "per qualified workday" (see
arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md); this remains purely
an hour-accounting rule, HARD blocking behavior for each kind is separate
and unchanged (eligibility.py / validator.py already block automatic
Assignment on both).

solver.py's live TARGET-01 SOFT ranking passes kinds=(SICK_LEAVE,) only,
deliberately excluding LEAVE_GRANTED: target_hours is a coordinator input
already set with planned leave in mind (known in advance, unlike sudden
sick leave), and ROTA-REG-001's frozen reference numbers were verified
against the original PoC run using raw target_hours. Applying the
LEAVE_GRANTED reduction there too shifted its exact target hours and broke
the frozen oracle -- a materially different question from "should the
quarterly balance also treat leave like sick leave", which the owner
answered yes to (rota/balance.py uses both kinds).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from rota.domain import AvailabilityKind, AvailabilityRecord, CalendarDay

EXCUSED_ABSENCE_KINDS = (AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED)
EXCUSED_ABSENCE_HOURS_PER_DAY = 8


class IncompleteAbsenceCalendarError(Exception):
    """T018 ABSENCE-WORKDAY-ACCOUNTING-01: raised when a month has at least
    one active, qualifying-kind AvailabilityRecord intersecting it but
    `calendar_days` does not cover every day of that month (missing days, a
    missing calendar entirely, or conflicting holiday values for the same
    date). Never falls back to a weekday-only guess -- CalendarDay is the
    sole source of truth for holidays."""


def workday_holiday_map(calendar_days: tuple, month_start: date, month_end: date) -> dict:
    holiday_by_date: dict[date, bool] = {}
    for entry in calendar_days:
        if entry.date < month_start or entry.date > month_end:
            continue
        if entry.date in holiday_by_date and holiday_by_date[entry.date] != entry.holiday:
            raise IncompleteAbsenceCalendarError(f"conflicting CalendarDay entries for {entry.date}")
        holiday_by_date[entry.date] = entry.holiday
    current = month_start
    while current <= month_end:
        if current not in holiday_by_date:
            raise IncompleteAbsenceCalendarError(
                f"missing CalendarDay for {current} required for excused-absence workday accounting"
            )
        current += timedelta(days=1)
    return holiday_by_date


def _absence_dates_by_employee(records: list[AvailabilityRecord], kinds: tuple, month_start: date, month_end: date) -> dict:
    """Union of active, kind-matching absence dates per employee, clipped to
    [month_start, month_end]. Overlapping/abutting records for the same
    employee (even across kinds) must not double-count a shared day (audit
    round 21 FINDING R21-1)."""
    dates_by_employee: dict[str, set] = {}
    for record in records:
        if not record.active or record.kind not in kinds:
            continue
        overlap_start = max(record.start_date, month_start)
        overlap_end = min(record.end_date, month_end)
        if overlap_start > overlap_end:
            continue
        current = overlap_start
        employee_dates = dates_by_employee.setdefault(record.employee_id, set())
        while current <= overlap_end:
            employee_dates.add(current)
            current += timedelta(days=1)
    return dates_by_employee


def excused_absence_days_in_month(
    records: list[AvailabilityRecord], month: date, kinds: tuple = EXCUSED_ABSENCE_KINDS,
    calendar_days: Optional[tuple[CalendarDay, ...]] = None,
) -> dict[str, int]:
    """Union of active excused-absence WORKDAYS (T018 owner decision
    2026-08-19, superseding "8h per calendar day"): a qualified workday is
    ISO weekday 1..5 AND CalendarDay.holiday=False; this is a pure
    hour-accounting rule, HARD availability blocking is unaffected. Fails
    closed via IncompleteAbsenceCalendarError when a qualifying record
    intersects the month but calendar_days does not fully cover it.

    `kinds` defaults to both SICK_LEAVE and LEAVE_GRANTED (rota.balance);
    solver.py passes kinds=(SICK_LEAVE,) only -- see module docstring for
    why LEAVE_GRANTED stays out of the live TARGET-01 objective."""
    num_days = calendar.monthrange(month.year, month.month)[1]
    month_start = date(month.year, month.month, 1)
    month_end = date(month.year, month.month, num_days)
    dates_by_employee = _absence_dates_by_employee(records, kinds, month_start, month_end)
    if not dates_by_employee:
        return {}
    holiday_by_date = workday_holiday_map(calendar_days or (), month_start, month_end)
    return {
        employee_id: sum(1 for d in dates if d.isoweekday() <= 5 and not holiday_by_date[d])
        for employee_id, dates in dates_by_employee.items()
    }


# ---------------------------------------------------------------------------
# ROTA-T023/T026: canonical POST_PLAN_REFERENCE/PRE_PLAN_LEAVE accounting
# owner (frozen addendum section 13 / brief.md section 8/12). Pure/
# persistence-free: callers in the persistence and application layers
# (the absence-reference repository module, rota.balance, rota.planning.
# solver, rota.application.analytics_read, rota.application.schedule_export)
# decode persisted absence_reference_snapshots rows into DailyAbsenceFact/
# DetailedDailyAbsenceFact themselves -- this module imports nothing from
# the persistence layer (that would be a layering cycle, since the
# repository module already imports rota.planning.validator/work_periods).
#
# The flat EXCUSED_ABSENCE_* functions above are retired for POST_PLAN/live
# TARGET accounting (T026); `excused_absence_days_in_month` remains only as
# the direct-call PRE_PLAN_LEAVE source and its own retained regression
# tests (frozen addendum section 2.1 / T018 helper history).
# ---------------------------------------------------------------------------


class IncompleteAbsenceReferenceError(Exception):
    """T023 frozen addendum section 4: a POST_PLAN_REFERENCE date whose
    winning DailyAbsenceFact is MISSING or AMBIGUOUS. Canonical hours must
    fail closed here -- never guessed as 0/8/12/24."""


@dataclass(frozen=True)
class DailyAbsenceFact:
    """Pure shape a caller decodes one persisted DayReference into (see the
    absence-reference repository module's DayReference) -- same fields, no
    persistence import."""

    the_date: date
    kind: AvailabilityKind  # SICK_LEAVE | LEAVE_GRANTED
    source_mode: str  # "PRE_PLAN_LEAVE" | "POST_PLAN_REFERENCE"
    status: str  # "BOUND" | "MISSING" | "AMBIGUOUS"
    hours: Optional[int]  # None when status != "BOUND"


def _winning_facts(facts) -> dict:
    """ROTA-T026: the one shared SICK-over-LEAVE_GRANTED same-date winner
    rule (frozen addendum section 4). Structural over any sequence of
    objects exposing `.the_date`/`.kind` -- both `DailyAbsenceFact` and
    `DetailedDailyAbsenceFact` qualify, so `canonical_daily_hours` and
    `canonical_site_absence_days` apply exactly one precedence path,
    never two independent implementations in this module."""
    winner_by_date: dict = {}
    for fact in facts:
        existing = winner_by_date.get(fact.the_date)
        if existing is None or (fact.kind == AvailabilityKind.SICK_LEAVE and existing.kind != AvailabilityKind.SICK_LEAVE):
            winner_by_date[fact.the_date] = fact
    return winner_by_date


def _require_bound(fact) -> None:
    """Shared status gate: never guess 0/8/12/24 for a MISSING/AMBIGUOUS winner."""
    if fact.status != "BOUND":
        raise IncompleteAbsenceReferenceError(
            f"{fact.the_date}: {fact.status} accepted reference for {fact.kind.value} ({fact.source_mode})"
        )


def canonical_daily_hours(facts: list[DailyAbsenceFact]) -> dict[date, int]:
    """Collapses possibly-multiple DailyAbsenceFact entries for the same
    date (an Employee can in principle carry more than one active
    SICK_LEAVE/LEAVE_GRANTED family) into one canonical per-date hour
    total. Raises IncompleteAbsenceReferenceError if the winning fact for
    any date is not BOUND -- never guesses 0/8/12/24."""
    winner_by_date = _winning_facts(facts)
    hours: dict[date, int] = {}
    for the_date, fact in winner_by_date.items():
        _require_bound(fact)
        hours[the_date] = fact.hours or 0
    return hours


def canonical_hours_in_range(facts: list[DailyAbsenceFact], range_start: date, range_end: date) -> int:
    """Frozen addendum section 12 / brief.md section 8: the canonical API
    accepts an explicit inclusive date range and returns the same canonical
    result for any caller-supplied window (seven-day/month/quarter alike) --
    no separate weekly convention, no persisted weekly row."""
    in_range = [f for f in facts if range_start <= f.the_date <= range_end]
    return sum(canonical_daily_hours(in_range).values())


# --- ROTA-T026: canonical Site-aware presentation projection (T020's own owner) ---


@dataclass(frozen=True)
class DetailedAbsencePeriodFact:
    """Pure mirror of the persistence-layer PeriodFact -- same fields, no
    persistence import (T026-2 layering: schedule_export.py mechanically
    maps persisted PeriodFact rows into this shape)."""

    assignment_id: str
    schedule_version_id: str
    site_id: str
    covers_demand_id: Optional[str]
    work_period_id: Optional[str]
    start_datetime: datetime
    end_datetime: datetime
    shift_kind: Optional[str] = None
    catalog_kind: Optional[str] = None
    required_rest_hours: Optional[int] = None
    work_period_template_id: Optional[str] = None
    work_period_component: Optional[int] = None


@dataclass(frozen=True)
class DetailedDailyAbsenceFact:
    """Pure mirror of the persistence-layer DayReference plus the owning
    AvailabilityRecord's kind -- same shape as DailyAbsenceFact, with the
    immutable bound-period detail T020 needs (D/N/24h/Site) that the
    WorkBalance-facing DailyAbsenceFact deliberately omits."""

    the_date: date
    kind: AvailabilityKind
    source_mode: str
    status: str
    hours: Optional[int]
    periods: tuple[DetailedAbsencePeriodFact, ...] = ()


@dataclass(frozen=True)
class CanonicalSiteAbsenceDay:
    """One winning day's canonical result plus its Site-scoped presentation
    slice. `canonical_hours` is the same Employee-global winning-day value
    `DailyAbsenceFact.hours`/`canonical_daily_hours` would produce for this
    date. `site_hours`/`site_periods` are POST_PLAN_REFERENCE-only: `None`/
    `()` for PRE_PLAN_LEAVE, which has no schedule Site provenance (T020's
    own already-frozen fail-closed multi-LOCAL attribution boundary)."""

    the_date: date
    kind: AvailabilityKind
    source_mode: str
    canonical_hours: int
    site_hours: Optional[int]
    site_periods: tuple[DetailedAbsencePeriodFact, ...]


def _site_period_hours(periods: tuple[DetailedAbsencePeriodFact, ...]) -> int:
    return sum(int((p.end_datetime - p.start_datetime).total_seconds() // 3600) for p in periods)


def canonical_site_absence_days(
    facts: list[DetailedDailyAbsenceFact], *, range_start: date, range_end: date, site_id: str,
) -> tuple[CanonicalSiteAbsenceDay, ...]:
    """T026-2: the one canonical, Site-aware presentation projection --
    range clipping, SICK/LEAVE precedence and fail-closed status all reuse
    `_winning_facts`/`_require_bound` (the same path `canonical_daily_hours`
    uses), so this module never carries two independent implementations of
    either rule. Callers (schedule_export.py) must not reimplement
    precedence or sum POST_PLAN period durations themselves."""
    in_range = [f for f in facts if range_start <= f.the_date <= range_end]
    winner_by_date = _winning_facts(in_range)
    days = []
    for the_date in sorted(winner_by_date):
        fact = winner_by_date[the_date]
        _require_bound(fact)
        if fact.source_mode == "PRE_PLAN_LEAVE":
            days.append(CanonicalSiteAbsenceDay(the_date, fact.kind, fact.source_mode, fact.hours or 0, None, ()))
            continue
        site_periods = tuple(p for p in fact.periods if p.site_id == site_id)
        days.append(CanonicalSiteAbsenceDay(
            the_date, fact.kind, fact.source_mode, fact.hours or 0, _site_period_hours(site_periods), site_periods,
        ))
    return tuple(days)


if __name__ == "__main__":
    print("absence module OK")
