"""Final ROTA-T010 A/B/C/D consistency audit matrix (round 9)."""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, datetime

from rota.application.availability_matrix import employee_availability_matrix
from rota.application.bootstrap import (
    coordinator_context_completeness,
    current_roster,
    month_plan_readiness,
)
from rota.application.manual_edit import mark_not_worked
from rota.domain import (
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    ReadinessState,
    ShiftKind,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import (
    save_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import (
    list_memberships_for_site,
    save_site_membership,
)
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.eligibility import check_eligibility
from rota.planning.site_rules import hard_rules_applicable_on
from tests.support.minimal_state import base_profile
from tests.test_t010_bootstrap_roster import (
    COORD,
    EMP,
    MONTH_A,
    SITE,
    _bootstrap_full,
    _fill_calendar,
    _profile,
)
from tests.test_t010_day_only_n_exception import (
    EMP as DAY_ONLY_EMP,
    SITE_ID as DAY_ONLY_SITE,
    _employee as day_only_employee,
    _make_assignment,
    _membership as day_only_membership,
    _n_demand,
    _record_exception,
    _resolved_and_applicability,
    _seed_context as seed_day_only_context,
    _validator_blocks_n,
)


def test_r9_a_and_c_share_membership_without_readiness_becoming_eligibility(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap_full(conn)
    _fill_calendar(conn, MONTH_A)
    membership = list_memberships_for_site(conn, SITE)[0]
    employee = current_roster(conn, site_id=SITE)[0]
    demand = _n_demand(12)

    assert coordinator_context_completeness(
        conn, coordinator_id=COORD, site_id=SITE
    ).complete
    ready = month_plan_readiness(conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A)
    assert ready.ready
    assert ready.target_hours_warnings

    ready_result = check_eligibility(
        employee,
        membership,
        demand,
        ShiftKind.D,
        _profile(),
        [],
        [],
        SITE,
        [],
    )
    not_ready_membership = replace(membership, readiness_state=ReadinessState.NOT_READY)
    not_ready_result = check_eligibility(
        employee,
        not_ready_membership,
        demand,
        ShiftKind.D,
        _profile(),
        [],
        [],
        SITE,
        [],
    )
    assert ready_result == not_ready_result

    save_site_membership(conn, replace(not_ready_membership, enabled=False))
    assert current_roster(conn, site_id=SITE) == ()
    assert not month_plan_readiness(
        conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A
    ).ready

    save_site_membership(conn, not_ready_membership)
    assert [item.employee_id for item in current_roster(conn, site_id=SITE)] == [EMP]
    assert month_plan_readiness(
        conn, coordinator_id=COORD, site_id=SITE, month=MONTH_A
    ).ready
    assert conn.execute(
        "SELECT COUNT(*) FROM site_memberships WHERE employee_id = ? AND site_id = ?",
        (EMP, SITE),
    ).fetchone()[0] == 1


def test_r9_b_c_d_day_only_exception_to_nn_keeps_inputs_and_history_consistent(
    tmp_path,
) -> None:
    month = date(2026, 10, 1)
    coordinator_id = "COORD-1"
    conn = connect(tmp_path / "rota.db")
    seed_day_only_context(conn)
    save_coordinator(conn, Coordinator(coordinator_id, "Coordinator", True))
    save_coordinator_site_association(
        conn,
        CoordinatorSiteAssociation(coordinator_id, DAY_ONLY_SITE, True),
    )
    for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(2026, 10, day), False))
    _record_exception(
        conn,
        effective_from=date(2026, 10, 10),
        effective_to=date(2026, 10, 15),
    )

    resolved, applicability = _resolved_and_applicability(conn, month)
    applicable = hard_rules_applicable_on(resolved, applicability, date(2026, 10, 12))
    demand = _n_demand(12)
    membership = day_only_membership()
    eligible = check_eligibility(
        day_only_employee(),
        membership,
        demand,
        ShiftKind.N,
        base_profile(),
        [],
        [],
        DAY_ONLY_SITE,
        applicable,
        allow_day_only_n_fallback=True,
    )
    not_ready = check_eligibility(
        day_only_employee(),
        replace(membership, readiness_state=ReadinessState.NOT_READY),
        demand,
        ShiftKind.N,
        base_profile(),
        [],
        [],
        DAY_ONLY_SITE,
        applicable,
        allow_day_only_n_fallback=True,
    )
    assert eligible == not_ready
    assert eligible.eligible
    assert not _validator_blocks_n(conn, 12, month)

    parent_id = "SV-R9-PARENT"
    planned = replace(_make_assignment(12), schedule_version_id=parent_id)
    persisted_demand = replace(demand, schedule_version_id=parent_id)
    lifecycle.create_schedule_version(
        conn,
        version_id=parent_id,
        site_id=DAY_ONLY_SITE,
        month=month,
        parent_version_id=None,
        created_at=datetime(2026, 9, 30, 9),
        created_by=coordinator_id,
        applied_rule_version_ids=[rule.rule_version_id for rule in resolved],
        shift_demands=[persisted_demand],
        assignments=[planned],
        deviations=[],
        effective_from=month,
    )
    matrix_before = employee_availability_matrix(
        conn,
        site_id=DAY_ONLY_SITE,
        employee_id=DAY_ONLY_EMP,
        month=month,
    )
    availability_before = conn.execute(
        "SELECT COUNT(*) FROM availability_versions"
    ).fetchone()[0]
    rules_before = conn.execute("SELECT COUNT(*) FROM site_rule_versions").fetchone()[0]
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    child = mark_not_worked(
        conn,
        site_id=DAY_ONLY_SITE,
        month=month,
        coordinator_id=coordinator_id,
        effective_from=date(2026, 10, 13),
        assignment_id=planned.assignment_id,
    )

    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == versions_before + 1
    assert conn.execute("SELECT COUNT(*) FROM availability_versions").fetchone()[0] == availability_before
    assert conn.execute("SELECT COUNT(*) FROM site_rule_versions").fetchone()[0] == rules_before
    assert employee_availability_matrix(
        conn,
        site_id=DAY_ONLY_SITE,
        employee_id=DAY_ONLY_EMP,
        month=month,
    ) == matrix_before

    parent = get_schedule_snapshot(conn, parent_id)
    original = next(item for item in parent.assignments if item.assignment_id == planned.assignment_id)
    assert original.state == AssignmentState.PLANNED
    assert original.operational_code is None

    current = get_schedule_snapshot(conn, child.version_id)
    nn = next(item for item in current.assignments if item.assignment_id == planned.assignment_id)
    assert nn.state == AssignmentState.CANCELLED
    assert nn.operational_code == "NN"
    assert (nn.employee_id, nn.start_datetime, nn.end_datetime, nn.covers_demand_id) == (
        original.employee_id,
        original.start_datetime,
        original.end_datetime,
        original.covers_demand_id,
    )
    assert any(
        deviation.category.value == "COVERAGE"
        and deviation.affected_assignment_or_employee == demand.demand_id
        for deviation in current.deviations
    )
