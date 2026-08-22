"""Narrow Round 8 sibling probes for A-R7-1 and A-R7-6."""
from datetime import date, datetime

import pytest

from rota.domain import AvailabilityKind, CalendarDay, MembershipKind
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.persistence.calendar_repository import save_calendar_day
from rota.planning.absence import IncompleteAbsenceCalendarError
from tests.test_t023 import _accept_version, _leave, _primary, _setup, _setup_two_sites


def test_r8_pre_plan_leave_does_not_guess_missing_calendar_day(tmp_path) -> None:
    conn = _setup(tmp_path)
    for day in (8, 9, 11, 12):
        save_calendar_day(conn, CalendarDay(date(2027, 3, day), False))

    with pytest.raises(IncompleteAbsenceCalendarError):
        _leave(
            conn,
            employee_id="A",
            kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2027, 3, 8),
            end_date=date(2027, 3, 12),
        )


def test_r8_unselected_external_current_is_not_accepted_reference_work(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.EXTERNAL_SUPPORT)
    _accept_version(
        conn,
        version_id="SV-A",
        pairs=[],
        effective_from=date(2027, 3, 1),
        accepted_at=datetime(2020, 3, 1, 8),
        site_id="SITE-A",
    )
    demand, assignment = _primary(
        "D-B",
        "A-B",
        "A",
        datetime(2027, 3, 8, 5),
        datetime(2027, 3, 8, 17),
        version_id="SV-B-UNSELECTED",
    )
    _accept_version(
        conn,
        version_id="SV-B-UNSELECTED",
        pairs=[(demand, assignment)],
        effective_from=date(2027, 3, 1),
        accepted_at=datetime(2020, 3, 1, 8),
        site_id="SITE-B",
        record_action=False,
    )

    record = _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8),
        end_date=date(2027, 3, 8),
        site_id="SITE-A",
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_site_scope == ("SITE-A",)
    assert snapshot.reference_status == "BOUND"
    assert snapshot.days[0].hours == 0
