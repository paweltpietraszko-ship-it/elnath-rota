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


if __name__ == "__main__":
    print("persistence.schedule_errors module OK")
