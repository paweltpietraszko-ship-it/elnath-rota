"""Narrow Round 9 class probes for A-R8-1 and A-R8-2."""
from datetime import date, datetime

import pytest

from rota.domain import AvailabilityKind, MembershipKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.planning.absence import IncompleteAbsenceCalendarError
from tests.test_t023 import (
    _accept_version,
    _leave,
    _primary,
    _seed_calendar_range,
    _setup,
    _setup_two_sites,
)


def test_r9_pre_plan_leave_requires_complete_month_calendar(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_calendar_range(conn, date(2027, 3, 8), date(2027, 3, 12))

    with pytest.raises(IncompleteAbsenceCalendarError):
        _leave(
            conn,
            employee_id="A",
            kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2027, 3, 8),
            end_date=date(2027, 3, 12),
        )


def test_r9_restored_away_external_work_is_not_effective_reference_work(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.EXTERNAL_SUPPORT)
    accepted_at = datetime(2020, 3, 1, 8)
    _accept_version(
        conn,
        version_id="SV-A",
        pairs=[],
        effective_from=date(2027, 3, 1),
        accepted_at=accepted_at,
        site_id="SITE-A",
    )
    _accept_version(
        conn,
        version_id="SV-B-ROOT",
        pairs=[],
        effective_from=date(2027, 3, 1),
        accepted_at=accepted_at,
        site_id="SITE-B",
    )
    demand, assignment = _primary(
        "D-B",
        "A-B",
        "A",
        datetime(2027, 3, 8, 5),
        datetime(2027, 3, 8, 17),
        version_id="SV-B-WORK",
    )
    _accept_version(
        conn,
        version_id="SV-B-WORK",
        pairs=[(demand, assignment)],
        effective_from=date(2027, 3, 1),
        accepted_at=datetime(2020, 3, 2, 8),
        site_id="SITE-B",
        parent_version_id="SV-B-ROOT",
    )
    lifecycle.restore_schedule_version(
        conn,
        site_id="SITE-B",
        month=date(2027, 3, 1),
        version_id="SV-B-ROOT",
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
