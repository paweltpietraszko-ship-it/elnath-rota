"""ROTA-T065-MANUAL-MIDDLE-SHIFT acceptance tests (brief.md section 11,
MM-01..MM-11). Covers: the one legal manual "środek" shape (marker pair,
mutually exclusive with covers_demand_id), role-substitution authorization
as a hard pre-check (not a Deviation), the shared UNAVAILABLE_TIME-01 gate,
non-participation in ShiftDemand-derived checks (COVERAGE-01/ROLE-01/
DAY_ONLY-01), and PRINT-GAP's ORDINARY presentation of the resulting real
work."""
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, time, timedelta

import pytest

from rota.application import manual_middle_work
from rota.application import schedule_export as SE
from rota.application.durable_inputs import append_availability
from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind, CalendarDay, CoordinatorSiteAssociation, Employee,
    MembershipKind, ReadinessSource, ReadinessState, RoleCoverageAuthorization, ShiftCatalogKind, ShiftDemand,
    ShiftKind, SiteMembership, SiteRoleDefinition,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.site_repository import save_site_print_settings
from rota.persistence.site_role_repository import save_role_coverage_authorization, save_site_role
from tests.support.t008_fixtures import seed_base_entities
from tests.test_t020 import _settings

MONTH = date(2026, 9, 1)
COORD = "COORD-1"
SITE = "SITE-1"
EMP = "EMP-1"
KIER = ("ROLE-KIER", "Kierownik")
SPRZ = ("ROLE-SPRZ", "Sprzedawca")


def _seed(conn, *, role: tuple[str, str] = KIER):
    # seed_base_entities defaults to SitePlanningRegime.ORDINARY (ROTA-T065-CONFIGURABLE-ROLES).
    seed_base_entities(conn, site_id=SITE, employee_id=EMP)
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(COORD, SITE, True))
    role_id, role_name = role
    save_site_role(conn, SiteRoleDefinition(role_id, SITE, role_name, True))
    save_site_membership(conn, SiteMembership(
        EMP, SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True,
        position_role_id=role_id,
    ))
    n_days = _cal.monthrange(MONTH.year, MONTH.month)[1]
    for i in range(n_days):
        save_calendar_day(conn, CalendarDay(MONTH + timedelta(days=i), False))
    lifecycle.create_schedule_version(
        conn, version_id="SV-BASE", site_id=SITE, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 8, 25, 8), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[], assignments=[], deviations=[], effective_from=MONTH,
    )


def _add(conn, *, employee_id=EMP, day=10, start_h=10, end_h=16, role_id="ROLE-KIER", note=None):
    return manual_middle_work.add_manual_middle_work(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, employee_id=employee_id,
        start_datetime=datetime(2026, 9, day, start_h), end_datetime=datetime(2026, 9, day, end_h),
        manual_work_role_id=role_id, note=note,
    )


# --- MM-01/02: happy path -----------------------------------------------
def test_mm_01_02_add_manual_middle_creates_child_with_markers():
    conn = connect(":memory:")
    _seed(conn)
    version = _add(conn)
    assert version.version_id != "SV-BASE"
    assert get_current_version_id(conn, SITE, MONTH) == version.version_id
    snapshot = get_schedule_snapshot(conn, version.version_id)
    a = next(x for x in snapshot.assignments if x.employee_id == EMP)
    assert a.covers_demand_id is None
    assert a.role == AssignmentRole.PRIMARY
    assert a.manual_work_role_id == "ROLE-KIER"
    assert a.manual_work_role_name == "Kierownik"


# --- MM-03: fail-closed marker shape (persistence invariant) ------------
def test_mm_03_primary_without_demand_and_without_both_markers_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    bad = Assignment(
        "ASG-BAD", "", EMP, datetime(2026, 9, 10, 10), datetime(2026, 9, 10, 16),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
        manual_work_role_id="ROLE-KIER", manual_work_role_name=None,  # only one of the two markers
    )
    with pytest.raises(MalformedScheduleSnapshot):
        lifecycle.create_schedule_version(
            conn, version_id="SV-BAD", site_id=SITE, month=MONTH, parent_version_id="SV-BASE",
            created_at=datetime(2026, 9, 10, 8), created_by=COORD, applied_rule_version_ids=[],
            shift_demands=[], assignments=[bad], deviations=[], effective_from=MONTH,
        )


def test_mm_03b_primary_without_demand_and_no_markers_at_all_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    bad = Assignment(
        "ASG-BAD2", "", EMP, datetime(2026, 9, 10, 10), datetime(2026, 9, 10, 16),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    with pytest.raises(MalformedScheduleSnapshot):
        lifecycle.create_schedule_version(
            conn, version_id="SV-BAD2", site_id=SITE, month=MONTH, parent_version_id="SV-BASE",
            created_at=datetime(2026, 9, 10, 8), created_by=COORD, applied_rule_version_ids=[],
            shift_demands=[], assignments=[bad], deviations=[], effective_from=MONTH,
        )


def test_mm_03c_demand_and_manual_markers_are_mutually_exclusive():
    conn = connect(":memory:")
    _seed(conn)
    demand = ShiftDemand("D-1", "", datetime(2026, 9, 10, 10), datetime(2026, 9, 10, 16), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    bad = Assignment(
        "ASG-BAD3", "", EMP, datetime(2026, 9, 10, 10), datetime(2026, 9, 10, 16),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None,
        manual_work_role_id="ROLE-KIER", manual_work_role_name="Kierownik",
    )
    with pytest.raises(MalformedScheduleSnapshot):
        lifecycle.create_schedule_version(
            conn, version_id="SV-BAD3", site_id=SITE, month=MONTH, parent_version_id="SV-BASE",
            created_at=datetime(2026, 9, 10, 8), created_by=COORD, applied_rule_version_ids=[],
            shift_demands=[demand], assignments=[bad], deviations=[], effective_from=MONTH,
        )


# --- MM-05/06: role-substitution authorization is a hard pre-check ------
def test_mm_05_unauthorized_role_substitution_rejected_before_child_created():
    conn = connect(":memory:")
    _seed(conn, role=KIER)
    save_site_role(conn, SiteRoleDefinition(SPRZ[0], SITE, SPRZ[1], True))
    with pytest.raises(manual_middle_work.ManualMiddleShiftRejected):
        _add(conn, role_id=SPRZ[0])
    # rejected before any child version was created
    assert get_current_version_id(conn, SITE, MONTH) == "SV-BASE"


def test_mm_06_authorized_role_substitution_succeeds_position_unchanged():
    conn = connect(":memory:")
    _seed(conn, role=KIER)
    save_site_role(conn, SiteRoleDefinition(SPRZ[0], SITE, SPRZ[1], True))
    save_role_coverage_authorization(conn, RoleCoverageAuthorization(
        "AUTH-1", SITE, EMP, SPRZ[0], datetime(2026, 9, 1), datetime(2026, 9, 30), True,
    ))
    version = _add(conn, role_id=SPRZ[0])
    snapshot = get_schedule_snapshot(conn, version.version_id)
    a = next(x for x in snapshot.assignments if x.employee_id == EMP)
    assert a.manual_work_role_id == SPRZ[0]
    assert a.manual_work_role_name == "Sprzedawca"
    # position itself (SiteMembership.position_role_id) is never touched by this flow --
    # nothing here writes site_memberships, so it trivially stays "Kierownik".


def test_mm_authorization_must_cover_the_whole_interval():
    conn = connect(":memory:")
    _seed(conn, role=KIER)
    save_site_role(conn, SiteRoleDefinition(SPRZ[0], SITE, SPRZ[1], True))
    # Authorization covers only part of the requested interval (ends at 13:00, work is 10-16).
    save_role_coverage_authorization(conn, RoleCoverageAuthorization(
        "AUTH-2", SITE, EMP, SPRZ[0], datetime(2026, 9, 10, 8), datetime(2026, 9, 10, 13), True,
    ))
    with pytest.raises(manual_middle_work.ManualMiddleShiftRejected):
        _add(conn, role_id=SPRZ[0])


def test_mm_unknown_role_rejected():
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(manual_middle_work.ManualMiddleShiftRejected):
        _add(conn, role_id="ROLE-DOES-NOT-EXIST")


# --- MM-07: shared UNAVAILABLE_TIME-01 oracle ----------------------------
def test_mm_07_unavailable_time_window_detected_via_shared_oracle():
    conn = connect(":memory:")
    _seed(conn)
    append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-1", employee_id=EMP,
        kind=AvailabilityKind.UNAVAILABLE_TIME_WINDOW, start_date=date(2026, 9, 10), end_date=date(2026, 9, 10),
        active=True, start_time=time(0, 0), end_time=time(12, 0),
    )
    version = _add(conn, day=10, start_h=10, end_h=16)
    snapshot = get_schedule_snapshot(conn, version.version_id)
    assert any(d.source_reference == "UNAVAILABLE_TIME-01" for d in snapshot.deviations)


# --- Non-participation in ShiftDemand-derived checks ---------------------
def test_manual_middle_never_attributed_to_shift_demand_coverage():
    """A manual middle geometrically overlapping a real, already-fully-staffed
    ShiftDemand must never inflate its COVERAGE-01 count -- it is extra real
    work outside the demand/coverage system entirely (brief section 1/8)."""
    conn = connect(":memory:")
    _seed(conn)
    save_employee(conn, Employee("EMP-2", "Pracownik EMP-2", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(
        "EMP-2", SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, True,
        position_role_id="ROLE-KIER",
    ))
    demand = ShiftDemand("D-1", "", datetime(2026, 9, 10, 6), datetime(2026, 9, 10, 18), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    regular = Assignment("ASG-REG", "", "EMP-2", datetime(2026, 9, 10, 6), datetime(2026, 9, 10, 18), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None)
    lifecycle.create_schedule_version(
        conn, version_id="SV-STAFFED", site_id=SITE, month=MONTH, parent_version_id="SV-BASE",
        created_at=datetime(2026, 9, 1, 8), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[regular], deviations=[], effective_from=MONTH,
    )
    version = _add(conn, employee_id=EMP, day=10, start_h=10, end_h=16)  # fully inside the regular demand's window
    snapshot = get_schedule_snapshot(conn, version.version_id)
    assert not any(d.source_reference == "COVERAGE-01" for d in snapshot.deviations)
    assert not any(d.source_reference == "ROLE-01" for d in snapshot.deviations)
    assert not any(d.source_reference == "DAY_ONLY-01" for d in snapshot.deviations)


# --- MM-10: PRINT-GAP consumes the resulting real work correctly --------
def test_mm_10_print_gap_shows_manual_middle_hours_without_role_in_cell():
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(conn, _settings(site_id=SITE))
    _add(conn, day=10, start_h=10, end_h=16)
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.ordinary_rows if r.employee_id == EMP)
    assert row.position_label == "Kierownik"
    assert row.day_cells[9] == ["10–16"]  # index 9 == 2026-09-10, only literal hours, no role
