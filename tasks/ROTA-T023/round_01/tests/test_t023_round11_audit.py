"""Narrow Round 11 boundary probes for A-R10-1 and A-R10-2."""
from datetime import date, datetime

from rota.domain import AvailabilityKind, MembershipKind
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from tests.test_t023 import (
    _accept_one,
    _accept_version,
    _leave,
    _primary,
    _seed_full_month_calendar,
    _setup,
    _setup_two_sites,
)


def test_r11_mixed_post_and_pre_plan_validates_only_pre_plan_month(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(
        conn,
        "D-MAR",
        "A-MAR",
        "A",
        datetime(2027, 3, 31, 5),
        datetime(2027, 3, 31, 17),
    )
    _seed_full_month_calendar(conn, date(2027, 4, 1), date(2027, 4, 1))

    record = _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2027, 3, 31),
        end_date=date(2027, 4, 1),
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert [day.source_mode for day in snapshot.days] == ["POST_PLAN_REFERENCE", "PRE_PLAN_LEAVE"]
    assert [day.hours for day in snapshot.days] == [12, 8]


def test_r11_effective_from_cutover_keeps_only_date_effective_work(tmp_path) -> None:
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
        datetime(2027, 3, 3, 5),
        datetime(2027, 3, 3, 17),
        version_id="SV-B-WORK",
    )
    _accept_version(
        conn,
        version_id="SV-B-WORK",
        pairs=[(demand, assignment)],
        effective_from=date(2027, 3, 1),
        accepted_at=datetime(2020, 3, 1, 8),
        site_id="SITE-B",
    )
    _accept_version(
        conn,
        version_id="SV-B-EMPTY",
        pairs=[],
        effective_from=date(2027, 3, 5),
        accepted_at=datetime(2020, 3, 2, 8),
        site_id="SITE-B",
        parent_version_id="SV-B-WORK",
    )

    record = _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 3),
        end_date=date(2027, 3, 8),
        site_id="SITE-A",
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_site_scope == ("SITE-A", "SITE-B")
    assert snapshot.days[0].hours == 12
    assert snapshot.days[-1].hours == 0
