"""Typed errors for the T009 application layer (tasks/ROTA-T009/brief.md)."""
from __future__ import annotations


class InvalidCoordinatorContext(Exception):
    """Raised when the coordinator/Site/CoordinatorSiteAssociation triple is
    not all active for a coordinator-originated write."""


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


class UnknownDeviationSource(Exception):
    """Raised when a validator ViolationDetail's rule has no entry in the
    brief.md section 8 source_reference -> DeviationCategory mapping table
    -- fails closed instead of guessing (brief.md: 'Unknown future source
    fails closed instead of being guessed')."""
