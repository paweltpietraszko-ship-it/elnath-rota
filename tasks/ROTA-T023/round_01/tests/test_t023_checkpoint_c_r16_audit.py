"""Narrow Round-16 closure probe for Checkpoint C finding C-R15-3."""
from dataclasses import replace
from datetime import datetime

import pytest

from rota.application import schedule_export as SE
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    MembershipKind,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.employee_repository import list_memberships_for_employee, save_site_membership
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import _settings
from tests.test_t023 import MONTH, _accept_version, _leave, _setup_two_sites


@pytest.mark.parametrize(
    "membership_kind_b",
    [MembershipKind.LOCAL, MembershipKind.EXTERNAL_SUPPORT],
    ids=("local_disabled_after_capture", "external_disabled_after_capture"),
)
def test_r16_bound_site_period_not_discarded_by_later_membership_disable(
    tmp_path, membership_kind_b,
) -> None:
    """C-R15-3 closure: Site ownership comes from the immutable bound
    period, not the membership snapshot current when the PDF is read."""
    conn = _setup_two_sites(tmp_path, membership_kind_b=membership_kind_b)
    _accept_version(
        conn,
        version_id="SV-A",
        pairs=[],
        effective_from=MONTH,
        accepted_at=datetime(2020, 3, 1, 8, 0),
        site_id="SITE-A",
    )
    start, end = datetime(2027, 3, 8, 6, 0), datetime(2027, 3, 8, 18, 0)
    demand = ShiftDemand(
        "DEM-B",
        "SV-B",
        start,
        end,
        1,
        shift_kind=ShiftKind.D,
        catalog_kind=ShiftCatalogKind.H12,
    )
    assignment = Assignment(
        "ASG-B",
        "SV-B",
        "A",
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        "DEM-B",
        None,
    )
    _accept_version(
        conn,
        version_id="SV-B",
        pairs=[(demand, assignment)],
        effective_from=MONTH,
        accepted_at=datetime(2020, 3, 1, 8, 0),
        site_id="SITE-B",
    )
    _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=start.date(),
        end_date=start.date(),
        site_id="SITE-A",
    )
    lifecycle.replace_working_snapshot(
        conn,
        version_id="SV-B",
        applied_rule_version_ids=[],
        shift_demands=[],
        assignments=[],
        deviations=[],
    )
    membership_b = next(m for m in list_memberships_for_employee(conn, "A") if m.site_id == "SITE-B")
    save_site_membership(conn, replace(membership_b, enabled=False))
    save_site_print_settings(conn, _settings(site_id="SITE-B"))

    model = SE._assemble_export_model(conn, site_id="SITE-B", month=MONTH, period_label="x")
    rows = {row.employee_id: row for row in model.rows}

    assert "A" in rows
    index = model.days.index(start.date())
    assert rows["A"].plan[index] == "D1"
    assert rows["A"].wyk[index] == "C1"
