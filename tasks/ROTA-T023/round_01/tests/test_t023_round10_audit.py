"""Narrow Round 10 class probes for A-R9-1 and A-R9-2."""
from datetime import date, datetime

from rota.domain import AvailabilityKind, MembershipKind
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from tests.test_t023 import _accept_one, _accept_version, _leave, _primary, _setup, _setup_two_sites


def test_r10_post_plan_leave_does_not_require_calendar(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(
        conn,
        "D-A",
        "A-A",
        "A",
        datetime(2027, 3, 8, 5),
        datetime(2027, 3, 8, 17),
    )

    record = _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2027, 3, 8),
        end_date=date(2027, 3, 8),
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_status == "BOUND"
    assert snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert snapshot.days[0].hours == 12


def test_r10_superseded_accepted_external_parent_work_is_not_effective(tmp_path) -> None:
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
        accepted_at=accepted_at,
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
        start_date=date(2027, 3, 8),
        end_date=date(2027, 3, 8),
        site_id="SITE-A",
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_site_scope == ("SITE-A",)
    assert snapshot.reference_status == "BOUND"
    assert snapshot.days[0].hours == 0
