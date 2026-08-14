"""Typed errors for the T009 application layer (tasks/ROTA-T009/brief.md)."""
from __future__ import annotations

from datetime import date, datetime


class InvalidCoordinatorContext(Exception):
    """Raised when the coordinator/Site/CoordinatorSiteAssociation triple is
    not all active for a coordinator-originated write."""


class CoordinatorContextAlreadyActive(Exception):
    """Raised by bootstrap_or_resume_coordinator_context (ROTA-T010-A) when
    (coordinator_id, site_id) already has an active CoordinatorSiteAssociation
    -- further writes to that context must go through the T009 authorized
    edit operations instead of the bootstrap/resume path."""


class IncompleteCalendarData(Exception):
    """Raised when a CalendarDay is missing for some date in the target
    month -- brief.md ONE CANONICAL PLANNINGSTATE ASSEMBLER: never guessed
    as holiday=false, never fetched from a network calendar."""


class NoCurrentScheduleVersion(Exception):
    """Raised when an operation requires an existing current ScheduleVersion
    but none exists yet for (site_id, month)."""


class ScheduleVersionNotWorking(Exception):
    """Raised when an operation requires the current ScheduleVersion to be
    WORKING/WORKING_WITH_DEVIATIONS (e.g. PLAN on a FINAL current version)."""


class CandidateRejected(Exception):
    """Raised when a caller-supplied FEASIBLE candidate fails fresh
    independent validation before being persisted."""


class ScheduleVersionContextMismatch(Exception):
    """Raised when an explicit schedule_version_id does not belong to the
    requested (site_id, month) -- brief.md ONE CANONICAL PLANNINGSTATE
    ASSEMBLER targets the whole (site_id, month, schedule_version_id)
    tuple, not just an existing version_id."""


class UnknownDeviationSource(Exception):
    """Raised when a validator ViolationDetail's rule has no entry in the
    brief.md section 8 source_reference -> DeviationCategory mapping table
    -- fails closed instead of guessing (brief.md: 'Unknown future source
    fails closed instead of being guessed')."""


def require_real_date(value: object, *, field_name: str = "effective_from") -> date:
    """tasks/ROTA-T009/review_01_architect_clarification.md SCHEDULEVERSION
    DATES: every new version requires a coordinator-supplied real date, and
    Rota MUST NOT derive/guess it. `datetime` is a subclass of `date` in
    Python, so `isinstance(value, date)` alone would silently accept a
    timestamp -- checked separately and rejected."""
    if isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a date, not a datetime (got {value!r})")
    if not isinstance(value, date):
        raise TypeError(f"{field_name} must be a date (got {type(value).__name__})")
    return value
