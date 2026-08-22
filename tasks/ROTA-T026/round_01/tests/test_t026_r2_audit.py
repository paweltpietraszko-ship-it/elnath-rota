"""Independent Round-2 sibling probes for the T026 implementation."""

from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.application import plan_ops
from rota.domain import AvailabilityKind, Employee, ShiftDemand
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.work_balance_repository import save_work_balance_target
from rota.planning.absence import (
    DetailedDailyAbsenceFact,
    IncompleteAbsenceReferenceError,
    canonical_site_absence_days,
)
from rota.planning.engine import plan
from tests.support.minimal_state import base_state
from tests.test_t018 import _local_membership, _sick
from tests.test_t023 import COORDINATOR, MONTH, SITE, _accept_version, _seed_full_month_calendar, _setup


@pytest.mark.parametrize("kind", [AvailabilityKind.SICK_LEAVE, AvailabilityKind.LEAVE_GRANTED])
def test_r2_raw_absence_family_remains_hard_at_direct_plan(kind) -> None:
    demand = ShiftDemand(
        "2026-10-06-D",
        "test-v1",
        datetime(2026, 10, 6, 5),
        datetime(2026, 10, 6, 17),
        1,
    )
    record = replace(_sick("A", date(2026, 10, 6), date(2026, 10, 6)), kind=kind)
    state = base_state(
        employees=(Employee("A", "A", date(2026, 9, 1), None, False),),
        memberships=(_local_membership("A"),),
        shift_demands=(demand,),
        availability_records=(record,),
    )

    assert plan(state).status == "DECISION_REQUIRED"


def test_r2_replan_fails_before_child_write_on_incomplete_reference(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, MONTH, MONTH)
    _accept_version(
        conn,
        version_id="SV-BASE",
        pairs=[],
        effective_from=MONTH,
        accepted_at=datetime(2020, 3, 1, 8),
        site_id=SITE,
    )
    save_work_balance_target(conn, employee_id="A", month=MONTH, target_hours=100)
    append_availability_version(
        conn,
        availability_id="AV-LEGACY-R2",
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 6),
        end_date=date(2027, 3, 6),
        active=True,
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(IncompleteAbsenceReferenceError):
        plan_ops.replan(
            conn,
            site_id=SITE,
            month=MONTH,
            coordinator_id=COORDINATOR,
            effective_from=MONTH,
        )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before


@pytest.mark.parametrize("status", ["MISSING", "AMBIGUOUS"])
def test_r2_out_of_range_incomplete_siblings_do_not_poison(status) -> None:
    facts = [
        DetailedDailyAbsenceFact(
            date(2027, 3, 8),
            AvailabilityKind.SICK_LEAVE,
            "POST_PLAN_REFERENCE",
            "BOUND",
            0,
            (),
        ),
        DetailedDailyAbsenceFact(
            date(2027, 4, 1),
            AvailabilityKind.SICK_LEAVE,
            "POST_PLAN_REFERENCE",
            status,
            None,
            (),
        ),
    ]

    result = canonical_site_absence_days(
        facts,
        range_start=date(2027, 3, 1),
        range_end=date(2027, 3, 31),
        site_id=SITE,
    )

    assert [day.the_date for day in result] == [date(2027, 3, 8)]


@pytest.mark.parametrize("status", ["MISSING", "AMBIGUOUS"])
def test_r2_in_range_winning_incomplete_siblings_fail_closed(status) -> None:
    fact = DetailedDailyAbsenceFact(
        date(2027, 3, 8),
        AvailabilityKind.SICK_LEAVE,
        "POST_PLAN_REFERENCE",
        status,
        None,
        (),
    )

    with pytest.raises(IncompleteAbsenceReferenceError):
        canonical_site_absence_days(
            [fact],
            range_start=date(2027, 3, 1),
            range_end=date(2027, 3, 31),
            site_id=SITE,
        )
