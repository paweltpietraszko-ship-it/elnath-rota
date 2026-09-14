"""Independent narrow audit reproductions for implementation 9f3c86d."""
from datetime import date, datetime, time

import pytest

from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
)
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.planning.engine import plan
from tests.support.minimal_state import SITE_ID, base_state


def _employee() -> Employee:
    return Employee("E-1", "Jan", date(2020, 1, 1), None, False)


def _membership() -> SiteMembership:
    return SiteMembership(
        "E-1",
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )


def test_write_boundary_rejects_partial_hours(tmp_path):
    """Brief section 10 freezes full-clock-hour precision at the write boundary."""
    conn = connect(tmp_path / "audit.db")
    save_employee(conn, _employee())

    with pytest.raises(ValueError, match="full hour"):
        append_availability_version(
            conn,
            availability_id="AV-PARTIAL",
            employee_id="E-1",
            kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 1),
            active=True,
            start_time=time(8, 30),
            end_time=time(12, 0),
        )


def test_real_plan_chain_blocks_overlapping_ordinary_demand():
    """Independent vertical check: PlanningState -> PLAN -> coordinator result."""
    demand = ShiftDemand(
        "D-1",
        "test-v1",
        datetime(2026, 10, 1, 10, 0),
        datetime(2026, 10, 1, 18, 0),
        1,
        shift_kind=ShiftKind.D,
        catalog_kind=ShiftCatalogKind.H12,
        required_rest_hours=11,
    )
    record = AvailabilityRecord(
        "AV-1",
        "AVV-1",
        "E-1",
        AvailabilityKind.UNAVAILABLE_TIME_WINDOW,
        date(2026, 10, 1),
        date(2026, 10, 1),
        True,
        None,
        None,
        time(0, 0),
        time(12, 0),
    )
    state = base_state(
        employees=(_employee(),),
        memberships=(_membership(),),
        availability_records=(record,),
        shift_demands=(demand,),
    )

    result = plan(state)

    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload is not None
    assert any(
        blocker.condition == "Koliduje z dostępnością godzinową"
        for blocker in result.decision_payload.blockers
    )
    assert any(
        option.text == "Zmień dostępność godzinową: Jan"
        for option in result.decision_payload.unblocking_options
    )
