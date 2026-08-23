"""ROTA-T011-B (tasks/ROTA-T011-B/brief.md): context-discovery reads
(active_coordinators/all_coordinators/active_sites_for_coordinator/
all_sites_for_coordinator) and months_with_schedule. Must never import
rota.persistence -- inactive states are built via bootstrap_or_resume_
coordinator_context with active=False entities, not direct repository
writes.
"""
from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, time

from rota.application import store
from rota.application.bootstrap import (
    active_coordinators,
    active_sites_for_coordinator,
    all_coordinators,
    all_sites_for_coordinator,
    bootstrap_or_resume_coordinator_context,
)
from rota.application.durable_inputs import set_calendar_day, update_employee, update_membership
from rota.application.manual_edit import apply_manual_correction
from rota.application.open_month import months_with_schedule
from rota.application.plan_ops import plan_month, select_candidate
from rota.application.assembler import assemble_planning_state
from rota.domain import (
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    SitePlanningRegime,
)

COORD_A = "COORD-T011B-A"
COORD_B = "COORD-T011B-B"
SITE_A = "SITE-T011B-A"
SITE_B = "SITE-T011B-B"
PROFILE = "PROFILE-T011B"
EMP = "EMP-T011B"
MONTH_1 = date(2026, 9, 1)
MONTH_2 = date(2026, 10, 1)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE, display_name="Profile T011B", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn, *, coordinator_id: str, site_id: str, coordinator_active=True, site_active=True, association_active=True) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coordinator_id, site_id=site_id,
        coordinator=Coordinator(coordinator_id, f"Coord {coordinator_id}", coordinator_active),
        site_profile=_profile(),
        site=Site(site_id, PROFILE, f"Site {site_id}", site_active, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(coordinator_id, site_id, association_active),
    )


def _staff(conn, *, coordinator_id: str, site_id: str, employee_id: str = EMP) -> None:
    update_employee(conn, coordinator_id=coordinator_id, site_id=site_id, employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
    update_membership(
        conn, coordinator_id=coordinator_id, site_id=site_id,
        membership=SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )


def _fill_calendar(conn, *, coordinator_id: str, site_id: str, month: date) -> None:
    days = calendar.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        set_calendar_day(conn, coordinator_id=coordinator_id, site_id=site_id, day=CalendarDay(date(month.year, month.month, d), False))


def _plan_and_select(conn, *, coordinator_id: str, site_id: str, month: date):
    result = plan_month(conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=month)
    assert result.status == "FEASIBLE"
    return select_candidate(conn, site_id=site_id, month=month, candidate=result.candidates[0], coordinator_id=coordinator_id)


def test_1_empty_store_returns_empty_tuples(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    assert active_coordinators(conn) == ()
    assert all_coordinators(conn) == ()
    assert active_sites_for_coordinator(conn, coordinator_id=COORD_A) == ()
    assert all_sites_for_coordinator(conn, coordinator_id=COORD_A) == ()


def test_2_one_full_context_appears_in_all_four_reads(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    assert [c.coordinator_id for c in active_coordinators(conn)] == [COORD_A]
    assert [c.coordinator_id for c in all_coordinators(conn)] == [COORD_A]
    assert [s.site_id for s in active_sites_for_coordinator(conn, coordinator_id=COORD_A)] == [SITE_A]
    assert [s.site_id for s in all_sites_for_coordinator(conn, coordinator_id=COORD_A)] == [SITE_A]


def test_3_inactive_site_only_in_full_read(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A, site_active=False)
    assert active_sites_for_coordinator(conn, coordinator_id=COORD_A) == ()
    assert [s.site_id for s in all_sites_for_coordinator(conn, coordinator_id=COORD_A)] == [SITE_A]


def test_4_inactive_association_only_in_full_read(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A, association_active=False)
    assert active_sites_for_coordinator(conn, coordinator_id=COORD_A) == ()
    assert [s.site_id for s in all_sites_for_coordinator(conn, coordinator_id=COORD_A)] == [SITE_A]


def test_5_inactive_coordinator_only_in_full_read(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator_active=False)
    assert active_coordinators(conn) == ()
    assert [c.coordinator_id for c in all_coordinators(conn)] == [COORD_A]


def test_6_sites_scoped_to_the_right_coordinator(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _bootstrap(conn, coordinator_id=COORD_B, site_id=SITE_B)
    assert [s.site_id for s in active_sites_for_coordinator(conn, coordinator_id=COORD_A)] == [SITE_A]


def test_7_months_with_schedule_empty_when_nothing_planned(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    assert months_with_schedule(conn, site_id=SITE_A) == ()


def test_8_months_with_schedule_lists_planned_months_ascending_without_duplicates(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)
    _fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_2)
    _plan_and_select(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_2)
    _plan_and_select(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)

    result = months_with_schedule(conn, site_id=SITE_A)
    assert result == (MONTH_1, MONTH_2)


def test_9_months_with_schedule_scoped_to_site(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _bootstrap(conn, coordinator_id=COORD_B, site_id=SITE_B)
    _staff(conn, coordinator_id=COORD_B, site_id=SITE_B)
    _fill_calendar(conn, coordinator_id=COORD_B, site_id=SITE_B, month=MONTH_1)
    _plan_and_select(conn, coordinator_id=COORD_B, site_id=SITE_B, month=MONTH_1)

    assert months_with_schedule(conn, site_id=SITE_B) == (MONTH_1,)
    assert months_with_schedule(conn, site_id=SITE_A) == ()


def _all_five_reads(conn):
    return (
        active_coordinators(conn),
        all_coordinators(conn),
        active_sites_for_coordinator(conn, coordinator_id=COORD_A),
        all_sites_for_coordinator(conn, coordinator_id=COORD_A),
        months_with_schedule(conn, site_id=SITE_A),
    )


def test_10_restart_yields_the_same_reads(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)
    _plan_and_select(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)

    before = _all_five_reads(conn)
    conn.close()

    reopened = store.open_store(db_path)
    after = _all_five_reads(reopened)
    assert after == before


def test_11_abandoned_plan_without_select_candidate_is_not_noise(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)

    result = plan_month(conn, site_id=SITE_A, month=MONTH_1, coordinator_id=COORD_A, effective_from=MONTH_1)
    assert result.status == "FEASIBLE"
    assert months_with_schedule(conn, site_id=SITE_A) == ()

    select_candidate(conn, site_id=SITE_A, month=MONTH_1, candidate=result.candidates[0], coordinator_id=COORD_A)
    assert months_with_schedule(conn, site_id=SITE_A) == (MONTH_1,)


def test_12_nn_does_not_remove_the_month_from_navigation(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)
    _plan_and_select(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH_1)

    # Real assignment_ids obtained through assemble_planning_state
    # (application layer), the same source open_month itself reads from.
    # B-R4-2: EVERY PRIMARY assignment of the month is converted to
    # CANCELLED/NN in one manual correction, not just one -- otherwise any
    # of the remaining ordinary PLANNED rows would independently keep the
    # month qualified, and the test would prove nothing about NN itself.
    state, _ = assemble_planning_state(conn, site_id=SITE_A, month=MONTH_1)
    primary_assignments = [a for a in state.existing_assignments if a.role == AssignmentRole.PRIMARY]
    assert primary_assignments  # sanity: there is real coverage to convert

    all_nn = [replace(a, state=AssignmentState.CANCELLED, operational_code="NN") for a in primary_assignments]
    apply_manual_correction(
        conn, site_id=SITE_A, month=MONTH_1, coordinator_id=COORD_A,
        effective_from=date(MONTH_1.year, MONTH_1.month, 2), upsert_assignments=all_nn,
    )

    state_after, _ = assemble_planning_state(conn, site_id=SITE_A, month=MONTH_1)
    assert state_after.existing_assignments  # not silently emptied
    assert all(
        a.state == AssignmentState.CANCELLED and a.operational_code == "NN" for a in state_after.existing_assignments
    )  # explicit confirmation: no other Assignment state remains to independently qualify the month

    assert months_with_schedule(conn, site_id=SITE_A) == (MONTH_1,)


def test_13_this_file_never_imports_rota_persistence_at_module_scope() -> None:
    """T011-B's own contract requires the application-layer test file to
    avoid rota.persistence entirely. This file needs one PLANNED assignment
    id to call mark_not_worked with in test 12, which it obtains via
    rota.application.assembler (application layer) instead."""
    import ast
    from pathlib import Path

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("rota.persistence"), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("rota.persistence"), node.module
