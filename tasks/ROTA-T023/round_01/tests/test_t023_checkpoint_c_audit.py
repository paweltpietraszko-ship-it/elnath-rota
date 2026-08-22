"""Independent adversarial audit probes for ROTA-T023 Checkpoint C."""
from __future__ import annotations

from datetime import date, datetime, timedelta

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
from rota.persistence.site_repository import save_site_print_settings
from rota.persistence.work_balance_repository import absence_facts_for_employee
from rota.planning.absence import canonical_hours_in_range
from tests.test_t020 import _settings
from tests.test_t023 import (
    MONTH,
    _accept_one,
    _accept_version,
    _leave,
    _setup,
    _setup_two_sites,
)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2027, 2, 24), date(2027, 3, 5)),
        (date(2027, 3, 29), date(2027, 4, 7)),
    ],
    ids=("starts_in_previous_month", "ends_in_next_month"),
)
def test_c_audit_pre_plan_decomposition_is_clipped_to_export_month(tmp_path, start, end) -> None:
    """T23-35: a monthly T020 projection must equal the canonical result
    for that month, even when one PRE_PLAN snapshot crosses either month
    boundary."""
    conn = _setup(tmp_path)
    _accept_version(
        conn,
        version_id="SV-UNSELECTED",
        pairs=[],
        effective_from=MONTH,
        accepted_at=datetime(2020, 3, 1, 8, 0),
        record_action=False,
    )
    _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=start,
        end_date=end,
        seed_calendar=True,
    )
    save_site_print_settings(conn, _settings())

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    facts = absence_facts_for_employee(conn, "A", model.days[0], model.days[-1])

    assert row.urlop_hours == canonical_hours_in_range(facts, model.days[0], model.days[-1])


@pytest.mark.parametrize(
    ("absence_start", "absence_end", "shift_start"),
    [
        (date(2027, 2, 28), date(2027, 3, 1), datetime(2027, 3, 1, 6, 0)),
        (date(2027, 3, 31), date(2027, 4, 1), datetime(2027, 3, 31, 6, 0)),
    ],
    ids=("missing_before_month", "missing_after_month"),
)
def test_c_audit_out_of_month_missing_reference_does_not_poison_month_projection(
    tmp_path, absence_start, absence_end, shift_start,
) -> None:
    """T23-35 and the explicit-range contract: an out-of-range MISSING
    day cannot make an otherwise complete monthly projection fail."""
    conn = _setup(tmp_path)
    _accept_one(
        conn,
        "D-IN",
        "A-IN",
        "A",
        shift_start,
        shift_start + timedelta(hours=12),
    )
    _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=absence_start,
        end_date=absence_end,
    )
    lifecycle.replace_working_snapshot(
        conn,
        version_id="SV-1",
        applied_rule_version_ids=[],
        shift_demands=[],
        assignments=[],
        deviations=[],
    )
    save_site_print_settings(conn, _settings())

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    facts = absence_facts_for_employee(conn, "A", model.days[0], model.days[-1])

    assert row.l4_hours == canonical_hours_in_range(facts, model.days[0], model.days[-1]) == 12


@pytest.mark.parametrize(
    ("shift_kind", "start", "end", "expected_plan"),
    [
        (ShiftKind.D, datetime(2027, 3, 8, 6, 0), datetime(2027, 3, 8, 18, 0), "D1"),
        (ShiftKind.N, datetime(2027, 3, 8, 18, 0), datetime(2027, 3, 9, 6, 0), "N1"),
    ],
    ids=("day", "night"),
)
def test_c_audit_post_plan_preserves_bound_shift_family(
    tmp_path, shift_kind, start, end, expected_plan,
) -> None:
    """T23-40: the immutable bound shift_kind owns D/N presentation;
    equal duration alone must not turn N into D."""
    conn = _setup(tmp_path)
    demand = ShiftDemand(
        "DEM-1",
        "SV-1",
        start,
        end,
        1,
        shift_kind=shift_kind,
        catalog_kind=ShiftCatalogKind.H12,
    )
    assignment = Assignment(
        "ASG-1",
        "SV-1",
        "A",
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        False,
        "DEM-1",
        None,
    )
    _accept_version(
        conn,
        version_id="SV-1",
        pairs=[(demand, assignment)],
        effective_from=MONTH,
        accepted_at=datetime(2020, 3, 1, 8, 0),
    )
    _leave(
        conn,
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=start.date(),
        end_date=start.date(),
    )
    lifecycle.replace_working_snapshot(
        conn,
        version_id="SV-1",
        applied_rule_version_ids=[],
        shift_demands=[],
        assignments=[],
        deviations=[],
    )
    save_site_print_settings(conn, _settings())

    model = SE._assemble_export_model(conn, site_id="SITE-1", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    index = model.days.index(start.date())

    assert row.plan[index] == expected_plan
    assert row.wyk[index] == "C1"


@pytest.mark.parametrize(
    "membership_kind_b",
    [MembershipKind.LOCAL, MembershipKind.EXTERNAL_SUPPORT],
    ids=("local", "external_support"),
)
def test_c_audit_bound_site_period_keeps_employee_in_site_export_after_replan(
    tmp_path, membership_kind_b,
) -> None:
    """Frozen addendum sections 7 and 14: an actual bound Site period owns
    POST_PLAN presentation even after REPLAN removes that employee's
    operational assignment; membership kind must not discard it."""
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
    save_site_print_settings(conn, _settings(site_id="SITE-B"))

    model = SE._assemble_export_model(conn, site_id="SITE-B", month=MONTH, period_label="x")
    rows = {row.employee_id: row for row in model.rows}

    assert "A" in rows
    index = model.days.index(start.date())
    assert rows["A"].plan[index] == "D1"
    assert rows["A"].wyk[index] == "C1"
