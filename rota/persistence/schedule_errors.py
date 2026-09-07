"""Typed errors for ScheduleVersion persistence (tasks/ROTA-T008/brief.md
ERROR MODEL) -- the public repository contract for expected invariant
failures, not raw sqlite3 exceptions.
"""
from __future__ import annotations


class ScheduleVersionNotFound(Exception):
    """Raised when a version_id has no matching row."""


class DuplicateScheduleVersionId(Exception):
    """Raised when creating a version whose version_id already exists."""


class InvalidScheduleLineage(Exception):
    """Raised for a missing/self/cross-Site/cross-month parent_version_id."""


class MalformedScheduleSnapshot(Exception):
    """Raised for an invalid ShiftDemand/Assignment/Deviation/applied-rule
    reference or shape within one ScheduleVersion's content."""


class RealizedWorkAltered(Exception):
    """Raised when child creation omits, changes, or does not exactly
    preserve a parent Assignment with state == REALIZED (R1-2)."""


class NonEditableScheduleVersion(Exception):
    """Raised when editing a version that is not the current WORKING/
    WORKING_WITH_DEVIATIONS version for its Site/month, or is FINAL."""


class InvalidCurrentVersionTarget(Exception):
    """Raised when restoring/selecting a version_id that does not belong to
    the requested (site_id, month)."""


class CannotDeleteLiveScheduleVersion(Exception):
    """ROTA-T057 (BOARD.md OWNER_RULING 2026-09-06, point 3): the current
    ScheduleVersion can only be deleted (its current-version pointer
    cleared) while it is not yet live. A live grafik must go through
    Przelicz Plan or Korekta reczna instead -- never deleted."""


class CannotRestoreLiveScheduleVersion(Exception):
    """ROTA-T057 follow-up (owner finding 2026-09-07): once a month is
    live, Przelicz Plan is the ONLY way to change its current version
    (contract point 6) -- restore_schedule_version used to move the
    current-version pointer to any older version unconditionally, with no
    check at all against already-realized, protected service content. For
    a live month that is now refused outright; the frontend offers a
    read-only "Podglad" of an old version's content there instead."""


if __name__ == "__main__":
    print("persistence.schedule_errors module OK")
