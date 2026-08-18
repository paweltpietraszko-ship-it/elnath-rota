"""ROTA-T012: 24h/12h/INNY shift catalog + work-period rest provenance.

Consolidates all T012 checkpoint (A/B/C/D) tests in one file per contract
(tasks/ROTA-T012/brief.md UNION TASK_SCOPE). This revision adds Part A
(tasks/ROTA-T012/part_a_catalog_persistence.md: catalog data model,
StandardShift/SiteMembership/ShiftDemand/Assignment persistence,
generate_catalog_demands) and Part B
(tasks/ROTA-T012/part_b_work_period_rest.md: per-work-period REST-01 via
rota.planning.work_periods, NORMAL 24h SAME-PERSON HARD/SHIFT-24-PAIR-01,
SHIFT-24-01 can_work_24h gating, same-site/cross-site/boundary rest
provenance). Emergency retry (Part C) and manual REST override (Part D)
are not exercised yet.
"""
from __future__ import annotations

import calendar
import sqlite3
from dataclasses import replace
from datetime import date, datetime, time, timedelta

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import LATEST_SCHEMA_VERSION, connect
from rota.persistence.employee_repository import list_memberships_for_site, save_employee, save_site_membership
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_lifecycle import create_schedule_version
from rota.persistence.schedule_validation import validate_assignments, validate_demands
from rota.persistence.site_profile_repository import get_site_profile, save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.engine import plan
from rota.planning.eligibility import check_eligibility
from rota.planning.shift_catalog import (
    AmbiguousEmergency24hCapability,
    InvalidStandardShift,
    classify_demand,
    generate_catalog_demands,
    normalized_catalog_kind,
)
from rota.planning.validator import validate
from rota.planning.work_periods import PeriodComponent, find_malformed_periods, resolve_required_rest
from tests.support.minimal_state import SITE_ID, base_state

MONTH = date(2026, 10, 1)  # 2026-10-01 is a Thursday (ISO weekday 4)


def _profile(profile_id: str, shifts: list[StandardShift]) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name="T012 profile", active=True, standard_shifts=shifts,
        day_only_blocks_n=True, external_support_enabled=False, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=60,
    )


# --- A: enum/value + StandardShift/SiteMembership persistence round-trip ---


def test_a_shift_catalog_kind_values():
    assert ShiftCatalogKind.H24.value == "24h"
    assert ShiftCatalogKind.H12.value == "12h"
    assert ShiftCatalogKind.OTHER.value == "INNY"


def test_a_standard_shift_t012_fields_round_trip(tmp_path):
    conn = connect(tmp_path / "rota.db")
    shift = StandardShift(
        ShiftKind.D, time(6, 0), time(18, 0), False, 2,
        catalog_kind=ShiftCatalogKind.H12, required_rest_hours=13, active_weekdays=(1, 2, 3, 4, 5),
    )
    save_site_profile(conn, _profile("P-A1", [shift]))
    fetched = get_site_profile(conn, "P-A1").standard_shifts[0]
    assert fetched.catalog_kind == ShiftCatalogKind.H12
    assert fetched.required_rest_hours == 13
    assert fetched.active_weekdays == (1, 2, 3, 4, 5)


def test_a_can_work_24h_default_and_round_trip(tmp_path):
    conn = connect(tmp_path / "rota.db")
    save_site_profile(conn, _profile("P-A1", [_d(5)]))
    save_site(conn, Site("SITE-A", "P-A1", "Site A", True))
    save_employee(conn, Employee("E1", "E1", date(2026, 1, 1), None, False))
    save_employee(conn, Employee("E2", "E2", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(
        "E1", "SITE-A", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
    ))
    save_site_membership(conn, SiteMembership(
        "E2", "SITE-A", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        can_work_24h=False,
    ))
    memberships = {m.employee_id: m for m in list_memberships_for_site(conn, "SITE-A")}
    assert memberships["E1"].can_work_24h is True
    assert memberships["E2"].can_work_24h is False


# --- A: catalog generation ---


def _d(start_h: int, rest: int = 11, weekdays=(1, 2, 3, 4, 5, 6, 7)) -> StandardShift:
    return StandardShift(ShiftKind.D, time(start_h, 0), time((start_h + 12) % 24, 0), False, 1,
                          catalog_kind=ShiftCatalogKind.H12, required_rest_hours=rest, active_weekdays=weekdays)


def _h24(kind: ShiftKind, start_h: int, rest: int) -> StandardShift:
    end_next_day = True
    return StandardShift(kind, time(start_h, 0), time(start_h, 0), end_next_day, 1,
                          catalog_kind=ShiftCatalogKind.H24, required_rest_hours=rest)


def _inny(start_h: int, length_h: int, rest: int) -> StandardShift:
    return StandardShift(ShiftKind.D, time(start_h, 0), time((start_h + length_h) % 24, 0), length_h >= 24 - start_h, 1,
                          catalog_kind=ShiftCatalogKind.OTHER, required_rest_hours=rest)


def test_a_mixed_12h_inny_24h_profile_generates_all_kinds():
    profile = _profile("MIXED", [_d(5), _h24(ShiftKind.N, 17, 12), _inny(9, 6, 10)])
    demands = generate_catalog_demands(profile, MONTH)
    kinds = {d.catalog_kind for d in demands}
    assert kinds == {ShiftCatalogKind.H12, ShiftCatalogKind.H24, ShiftCatalogKind.OTHER}


def test_a_arbitrary_multiple_inny_entries_generate_independent_occurrences():
    profile = _profile("MULTI-INNY", [_inny(0, 6, 10), _inny(8, 5, 10), _inny(15, 4, 10)])
    demands = generate_catalog_demands(profile, MONTH)
    inny_ids = {d.demand_id for d in demands if d.catalog_kind == ShiftCatalogKind.OTHER}
    assert len(inny_ids) == 31 * 3


def test_a_weekday_generation_weekday_only_vs_weekend_only():
    weekdays = _d(5, weekdays=(1, 2, 3, 4, 5))
    weekend = _d(9, weekdays=(6, 7))
    profile = _profile("WEEK", [weekdays, weekend])
    demands = generate_catalog_demands(profile, MONTH)
    for d in demands:
        iso = d.start_datetime.date().isoweekday()
        if d.start_datetime.time() == time(5, 0):
            assert iso in (1, 2, 3, 4, 5)
        else:
            assert iso in (6, 7)


def test_a_overlapping_same_kind_entries_get_distinct_ids():
    profile = _profile("OVERLAP", [_d(5), _d(5)])
    demands = generate_catalog_demands(profile, MONTH)
    day_1 = [d for d in demands if d.start_datetime.date() == date(2026, 10, 1)]
    assert len(day_1) == 2
    assert len({d.demand_id for d in day_1}) == 2


def _first_pair(demands):
    """The earliest-starting occurrence's two components, grouped by their
    shared work_period_template_id -- not an exact id string, since A-R4-1
    makes template_id per-occurrence (date-scoped), not per-catalog-entry."""
    by_template: dict = {}
    for d in demands:
        by_template.setdefault(d.work_period_template_id, []).append(d)
    pair = next(group for group in by_template.values() if len(group) == 2)
    return sorted(pair, key=lambda d: d.start_datetime)


def test_a_24h_d_start_produces_d_then_n_components():
    profile = _profile("H24-D", [_h24(ShiftKind.D, 5, 12)])
    demands = generate_catalog_demands(profile, MONTH)
    first, second = _first_pair(demands)
    assert [first.shift_kind, second.shift_kind] == [ShiftKind.D, ShiftKind.N]
    assert first.work_period_template_id == second.work_period_template_id
    assert (first.work_period_component, second.work_period_component) == (1, 2)
    assert first.end_datetime == second.start_datetime


def test_a_24h_n_start_produces_n_then_d_components():
    profile = _profile("H24-N", [_h24(ShiftKind.N, 17, 12)])
    demands = generate_catalog_demands(profile, MONTH)
    first, second = _first_pair(demands)
    assert [first.shift_kind, second.shift_kind] == [ShiftKind.N, ShiftKind.D]


def test_a_all_24_profile_data_case_can_work_24h_still_stores(tmp_path):
    """Part A is data-only: an all-24h profile is a legal data shape, and
    SiteMembership.can_work_24h still stores/reads normally even though its
    solver-side meaning (ignored on an all-24h profile) is Part C."""
    conn = connect(tmp_path / "rota.db")
    save_site_profile(conn, _profile("ALL24", [_h24(ShiftKind.D, 5, 12)]))
    save_site(conn, Site("SITE-ALL24", "ALL24", "All 24h", True))
    save_employee(conn, Employee("E3", "E3", date(2026, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(
        "E3", "SITE-ALL24", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT, can_work_24h=False,
    ))
    fetched = get_site_profile(conn, "ALL24")
    assert normalized_catalog_kind(fetched.standard_shifts[0]) == ShiftCatalogKind.H24
    assert list_memberships_for_site(conn, "SITE-ALL24")[0].can_work_24h is False


def test_a_ambiguous_emergency_24h_capability_fails_closed():
    conflicting = [_h24(ShiftKind.D, 5, 11), _h24(ShiftKind.D, 5, 12)]
    profile = _profile("AMBIGUOUS", conflicting)
    with pytest.raises(AmbiguousEmergency24hCapability):
        generate_catalog_demands(profile, MONTH)


def test_a_plain_12h_demand_snapshots_unambiguous_emergency_rest():
    profile = _profile("SNAP", [_d(5, rest=11), _h24(ShiftKind.D, 5, 14)])
    demands = generate_catalog_demands(profile, MONTH)
    plain = next(d for d in demands if d.catalog_kind == ShiftCatalogKind.H12 and d.start_datetime.date() == date(2026, 10, 1))
    assert plain.emergency_24h_rest_hours == 14


# --- A: legacy compatibility / migration ---


def test_a_legacy_standard_shift_defaults_readable(tmp_path):
    conn = connect(tmp_path / "rota.db")
    legacy = StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1)
    save_site_profile(conn, _profile("LEGACY-A", [legacy]))
    fetched = get_site_profile(conn, "LEGACY-A").standard_shifts[0]
    assert fetched.catalog_kind is None
    assert fetched.required_rest_hours == 11
    assert fetched.active_weekdays == (1, 2, 3, 4, 5, 6, 7)
    assert normalized_catalog_kind(fetched) == ShiftCatalogKind.H12


def test_a_current_schema_reconnect_is_idempotent(tmp_path):
    db_path = tmp_path / "rota.db"
    connect(db_path).close()
    conn = connect(db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION == 5
    save_site_profile(conn, _profile("REOPEN", [_d(5)]))
    assert get_site_profile(conn, "REOPEN").profile_id == "REOPEN"


def _seed_v4_legacy_db(db_path) -> None:
    """Raw SQL, deliberately bypassing repository code, against a connection
    held at PRAGMA user_version=4 (pre-T012) -- the actual old column set,
    not merely old *values* written by new code. Mirrors
    tests/test_local_store_schema_migration.py::_apply_only_migration_1's
    established staged-migration technique, extended through migration 4."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    _apply_migrations_up_to(conn, 4)
    with conn:
        _insert_v4_legacy_rows(conn)
    conn.close()


def _apply_migrations_up_to(conn: sqlite3.Connection, max_version: int) -> None:
    import rota.persistence.db as db_module

    conn.execute("BEGIN")
    for version, statements in db_module.MIGRATIONS:
        if version > max_version:
            continue
        for statement in statements:
            conn.execute(statement)
    conn.execute(f"PRAGMA user_version = {max_version}")
    conn.execute("COMMIT")


def _insert_v4_legacy_rows(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO site_profiles VALUES ('LEGACY-P', 'Legacy', 1, 1, 0, 0, 0, 1, 40)")
    conn.execute(
        "INSERT INTO standard_shifts (profile_id, seq, kind, start_time, end_time, end_next_day, "
        "required_primary_count) VALUES ('LEGACY-P', 0, 'D', '05:00:00', '17:00:00', 0, 1)"
    )
    conn.execute("INSERT INTO sites VALUES ('LEGACY-SITE', 'LEGACY-P', 'Legacy Site', 1)")
    conn.execute("INSERT INTO coordinators VALUES ('COORD-1', 'Coord', 1)")
    conn.execute(
        "INSERT INTO employees (employee_id, display_name, active_from, active_to, day_only) "
        "VALUES ('LEGACY-E', 'Legacy Emp', '2026-01-01', NULL, 0)"
    )
    conn.execute(
        "INSERT INTO site_memberships (employee_id, site_id, membership_kind, enabled, "
        "readiness_state, readiness_source) VALUES ('LEGACY-E', 'LEGACY-SITE', 'LOCAL', 1, "
        "'READY_FOR_PRIMARY', 'DEFAULT')"
    )
    conn.execute(
        "INSERT INTO schedule_versions (version_id, site_id, month, parent_version_id, created_at, "
        "created_by, status, effective_from) VALUES ('SV-LEGACY', 'LEGACY-SITE', '2026-10-01', NULL, "
        "'2026-10-01T00:00:00', 'COORD-1', 'WORKING', '2026-10-01')"
    )
    conn.execute("INSERT INTO current_schedule_versions VALUES ('LEGACY-SITE', '2026-10-01', 'SV-LEGACY')")
    conn.execute(
        "INSERT INTO shift_demands (schedule_version_id, demand_id, start_datetime, end_datetime, "
        "required_primary_count) VALUES ('SV-LEGACY', '2026-10-01-D', '2026-10-01T05:00:00', "
        "'2026-10-01T17:00:00', 1)"
    )
    conn.execute(
        "INSERT INTO assignments (schedule_version_id, assignment_id, employee_id, start_datetime, "
        "end_datetime, role, state, frozen, covers_demand_id, mentor_primary_assignment_id, "
        "operational_code) VALUES ('SV-LEGACY', 'A-LEGACY', 'LEGACY-E', '2026-10-01T05:00:00', "
        "'2026-10-01T17:00:00', 'PRIMARY', 'REALIZED', 0, '2026-10-01-D', NULL, NULL)"
    )


def test_a_real_nonempty_v4_db_migrates_to_v5_without_data_loss(tmp_path):
    db_path = tmp_path / "rota.db"
    _seed_v4_legacy_db(db_path)

    reopened = connect(db_path)
    assert reopened.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION

    profile = get_site_profile(reopened, "LEGACY-P")
    shift = profile.standard_shifts[0]
    assert shift.catalog_kind is None and shift.required_rest_hours == 11 and shift.active_weekdays == (1, 2, 3, 4, 5, 6, 7)

    membership = list_memberships_for_site(reopened, "LEGACY-SITE")[0]
    assert membership.can_work_24h is True

    from rota.persistence.schedule_repository import get_schedule_snapshot
    snapshot = get_schedule_snapshot(reopened, "SV-LEGACY")
    assert snapshot.shift_demands[0].shift_kind is None and snapshot.shift_demands[0].work_period_template_id is None
    assert snapshot.assignments[0].work_period_id is None and snapshot.assignments[0].required_rest_after_hours is None


# --- A round 4 audit closure (A-R4-1..5): occurrence identity, emergency ---
# --- snapshot direction, explicit shift_kind precedence, write-time shape ---
# --- validation, and normal 24h month-boundary persistence.               ---


def _shift(kind, start_hour, duration, catalog_kind, *, rest=11, weekdays=(1, 2, 3, 4, 5, 6, 7)) -> StandardShift:
    end_hour = (start_hour + duration) % 24
    return StandardShift(kind, time(start_hour), time(end_hour), start_hour + duration >= 24, 1,
                          catalog_kind=catalog_kind, required_rest_hours=rest, active_weekdays=weekdays)


@pytest.mark.parametrize(
    ("catalog_kind", "duration", "components"),
    [(ShiftCatalogKind.H12, 12, 1), (ShiftCatalogKind.OTHER, 6, 1), (ShiftCatalogKind.H24, 24, 2)],
)
def test_a_each_occurrence_has_its_own_template_id(catalog_kind, duration, components):
    demands = generate_catalog_demands(_profile("TEMPLATE", [_shift(ShiftKind.D, 5, duration, catalog_kind)]), MONTH)
    groups: dict = {}
    for d in demands:
        groups.setdefault(d.work_period_template_id, []).append(d)
    assert len(groups) == 31
    assert {len(g) for g in groups.values()} == {components}


def test_a_emergency_snapshot_is_directional_not_ambiguous():
    profile = _profile("DIRECTION", [
        _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12), _shift(ShiftKind.N, 17, 12, ShiftCatalogKind.H12),
        _shift(ShiftKind.D, 5, 24, ShiftCatalogKind.H24, rest=11), _shift(ShiftKind.N, 17, 24, ShiftCatalogKind.H24, rest=13),
    ])
    ordinary = [d for d in generate_catalog_demands(profile, MONTH) if d.catalog_kind == ShiftCatalogKind.H12]
    rests = {(d.shift_kind, d.start_datetime.time()): d.emergency_24h_rest_hours for d in ordinary}
    assert rests[(ShiftKind.D, time(5))] == 11
    assert rests[(ShiftKind.N, time(17))] == 13


@pytest.mark.parametrize("ordinary", [
    _shift(ShiftKind.N, 17, 12, ShiftCatalogKind.H12), _shift(ShiftKind.D, 5, 6, ShiftCatalogKind.OTHER),
])
def test_a_second_half_and_inny_do_not_receive_emergency_snapshot(ordinary):
    profile = _profile("NO-LEAK", [ordinary, _shift(ShiftKind.D, 5, 24, ShiftCatalogKind.H24, rest=14)])
    demands = generate_catalog_demands(profile, MONTH)
    ordinary_demand = next(d for d in demands if d.catalog_kind == ordinary.catalog_kind)
    assert ordinary_demand.emergency_24h_rest_hours is None


def test_a_explicit_shift_kind_precedes_legacy_profile_classifier():
    profile = _profile("CLASSIFY", [_shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12)])
    explicit = ShiftDemand(
        "explicit-N", "SV", datetime(2026, 10, 1, 17), datetime(2026, 10, 2, 5), 1,
        shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=11,
        work_period_template_id="WP", work_period_component=2,
    )
    assert classify_demand(explicit, profile) == ShiftKind.N


@pytest.mark.parametrize("invalid_shift", [
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12, rest=-1),
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12, weekdays=()),
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12, weekdays=(1, 1)),
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H12, weekdays=(0, 7)),
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.H24),
    _shift(ShiftKind.D, 5, 6, ShiftCatalogKind.H12),
    _shift(ShiftKind.D, 5, 12, ShiftCatalogKind.OTHER),
])
def test_a_new_or_updated_invalid_standard_shift_is_rejected_on_write(tmp_path, invalid_shift):
    conn = connect(tmp_path / "rota.db")
    with pytest.raises(InvalidStandardShift):
        save_site_profile(conn, _profile("INVALID", [invalid_shift]))


@pytest.mark.parametrize(("month", "start_hour"), [(date(2026, 10, 1), 17), (date(2026, 12, 1), 17)])
def test_a_normal_24h_occurrence_crossing_month_is_valid_month_content(month, start_hour):
    demands = list(generate_catalog_demands(_profile("BOUNDARY", [_shift(ShiftKind.N, start_hour, 24, ShiftCatalogKind.H24)]), month))
    validated = validate_demands(month, demands)
    assert validated.keys() == {d.demand_id for d in demands}


# --- A round 5 audit closure (A-R5-1): the month-boundary exception must ---
# --- reject malformed "pairs" and admit only the exactly-matching        ---
# --- Assignment of an accepted crossing demand.                          ---


def _boundary_demand(demand_id, start, end, kind, component, *, count=1, rest=11) -> ShiftDemand:
    return ShiftDemand(
        demand_id, "SV", start, end, count, shift_kind=kind, catalog_kind=ShiftCatalogKind.H24,
        required_rest_hours=rest, work_period_template_id="BOUNDARY-WP", work_period_component=component,
    )


@pytest.mark.parametrize(("first_end", "second_end", "second_count", "second_rest"), [
    (datetime(2026, 11, 1, 1), datetime(2026, 11, 1, 17), 1, 11),
    (datetime(2026, 11, 1, 5), datetime(2026, 11, 1, 17), 2, 11),
    (datetime(2026, 11, 1, 5), datetime(2026, 11, 1, 17), 1, 13),
])
def test_a_month_boundary_exception_rejects_malformed_24h_pair(first_end, second_end, second_count, second_rest):
    first = _boundary_demand("D1", datetime(2026, 10, 31, 17), first_end, ShiftKind.N, 1)
    second = _boundary_demand("D2", first_end, second_end, ShiftKind.D, 2, count=second_count, rest=second_rest)
    with pytest.raises(MalformedScheduleSnapshot):
        validate_demands(date(2026, 10, 1), [first, second])


def test_a_month_boundary_exception_rejects_unpaired_foreign_demand():
    foreign = _boundary_demand("D2", datetime(2026, 11, 1, 5), datetime(2026, 11, 1, 17), ShiftKind.D, 2)
    with pytest.raises(MalformedScheduleSnapshot):
        validate_demands(date(2026, 10, 1), [foreign])


def test_a_valid_month_crossing_24h_assignments_are_persistable_content(tmp_path):
    month = date(2026, 10, 1)
    demands = list(generate_catalog_demands(_profile("ASSIGN-BOUNDARY", [_shift(ShiftKind.N, 17, 24, ShiftCatalogKind.H24)]), month))
    crossing = sorted((d for d in demands if d.start_datetime >= datetime(2026, 10, 31, 17)), key=lambda d: d.start_datetime)
    demands_by_id = validate_demands(month, crossing)
    assignments = [
        Assignment(
            f"A{i}", "SV", "E1", d.start_datetime, d.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED,
            False, d.demand_id, None, work_period_id="WP1", required_rest_after_hours=11,
        )
        for i, d in enumerate(crossing, start=1)
    ]
    conn = connect(tmp_path / "rota.db")
    save_employee(conn, Employee("E1", "Employee", date(2026, 1, 1), None, False))
    assert len(validate_assignments(conn, month, assignments, demands_by_id)) == 2


# --- B: per-work-period REST-01, SHIFT-24-PAIR-01, SHIFT-24-01, cross-site --


def _membership(employee_id: str, *, can_work_24h: bool = True) -> SiteMembership:
    return SiteMembership(
        employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT, can_work_24h=can_work_24h,
    )


def _demand(demand_id: str, start: datetime, end: datetime, count: int = 1) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", start, end, count)


def _primary(assignment_id: str, employee_id: str, demand: ShiftDemand, *, frozen: bool = False, **kwargs) -> Assignment:
    return Assignment(
        assignment_id, "test-v1", employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, frozen, demand.demand_id, None, **kwargs,
    )


def _two_day_state_with_rest(rest: int):
    profile = _profile("B-RESTVAR", [_d(5, rest)])
    demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() in (date(2026, 10, 1), date(2026, 10, 2)))
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    return base_state(profile=profile, employees=(employee,), memberships=(_membership("A"),), shift_demands=demands)


def test_b_12h_rest_threshold_changes_feasibility():
    assert plan(_two_day_state_with_rest(8)).status == "FEASIBLE"
    assert plan(_two_day_state_with_rest(16)).status == "DECISION_REQUIRED"


def test_b_rest_is_directional_uses_earlier_periods_rest():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 2, 3, 0), datetime(2026, 10, 2, 15, 0))  # 10h gap
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))

    high_then_low = [_primary("A1", "E", d1, required_rest_after_hours=20), _primary("A2", "E", d2, required_rest_after_hours=5)]
    report = validate(state, high_then_low)
    assert not report.hard_pass and any("REST-01" in v for v in report.violations)

    low_then_high = [_primary("A1", "E", d1, required_rest_after_hours=5), _primary("A2", "E", d2, required_rest_after_hours=20)]
    assert validate(state, low_then_high).hard_pass


def test_b_period_rest_resolves_from_terminal_component():
    from rota.planning.work_periods import PeriodComponent, group_into_periods

    c1 = PeriodComponent("c1", "E", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), "WP", 99)
    c2 = PeriodComponent("c2", "E", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), "WP", 14)
    assert group_into_periods([c1, c2])[0].required_rest_after_hours == 14


def _h24_pair_demands(profile_id: str, kind: ShiftKind, rest: int):
    profile = _profile(profile_id, [_h24(kind, 5, rest)])
    demands = tuple(sorted(
        (d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1)),
        key=lambda d: d.start_datetime,
    ))
    return profile, demands


def test_b_24h_pair_has_no_internal_rest_and_pair_rest_governs_after():
    profile, (d1, d2) = _h24_pair_demands("B-H24", ShiftKind.D, 14)
    a1 = _primary("A1", "E", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E"),))
    assert validate(state, [a1, a2]).hard_pass  # 0h internal gap is legal within one period

    d3 = _demand("d3", d2.end_datetime + timedelta(hours=10), d2.end_datetime + timedelta(hours=22))
    a3 = _primary("A3", "E", d3, required_rest_after_hours=99)  # irrelevant -- pair's own rest (14h) governs
    state2 = base_state(profile=profile, shift_demands=(d1, d2, d3), memberships=(_membership("E"),))
    report = validate(state2, [a1, a2, a3])
    assert not report.hard_pass and any("REST-01" in v for v in report.violations)


def test_b_24h_halves_different_employees_is_hard_fail():
    profile, (d1, d2) = _h24_pair_demands("B-MISMATCH", ShiftKind.D, 12)
    a1 = _primary("A1", "E1", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E2", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=(_membership("E1"), _membership("E2")))
    report = validate(state, [a1, a2])
    assert not report.hard_pass and any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_b_mixed_profile_can_work_24h_false_blocks():
    profile = _profile("B-MIXED24", [_h24(ShiftKind.D, 5, 12), _d(9, 11)])
    demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1) and d.catalog_kind == ShiftCatalogKind.H24)
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(profile=profile, employees=(employee,), memberships=(_membership("A", can_work_24h=False),), shift_demands=demands)
    assert plan(state).status == "DECISION_REQUIRED"


def test_b_all_24h_profile_ignores_can_work_24h():
    profile, demands = _h24_pair_demands("B-ALL24", ShiftKind.D, 12)
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(profile=profile, employees=(employee,), memberships=(_membership("A", can_work_24h=False),), shift_demands=demands)
    assert plan(state).status == "FEASIBLE"


def test_b_inny_uses_its_own_rest():
    def inny_state(rest):
        profile = _profile("B-INNY", [_inny(5, 8, rest)])
        demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() in (date(2026, 10, 1), date(2026, 10, 2)))
        employee = Employee("A", "A", date(2026, 1, 1), None, False)
        return base_state(profile=profile, employees=(employee,), memberships=(_membership("A"),), shift_demands=demands)

    assert plan(inny_state(10)).status == "FEASIBLE"
    assert plan(inny_state(20)).status == "DECISION_REQUIRED"


def test_b_same_site_boundary_period_blocks_insufficient_rest():
    profile = _profile("B-BOUNDARY", [_d(5, 14)])
    demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1))
    boundary = Assignment(
        "BND1", "prev-v1", "A", datetime(2026, 9, 30, 5, 0), datetime(2026, 9, 30, 17, 0),
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None, required_rest_after_hours=14,
    )
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(
        profile=profile, employees=(employee,), memberships=(_membership("A"),),
        shift_demands=demands, boundary_assignments=(boundary,),
    )
    assert plan(state).status == "DECISION_REQUIRED"  # 12h gap < 14h boundary rest


def test_b_cross_site_persisted_24h_rest_blocks_regardless_of_current_profile():
    profile = _profile("B-CROSS", [_d(5, 8)])  # current site's own rest (8h) is irrelevant here
    demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1))
    other_site_pair = (
        Assignment("OS1", "other-v1", "A", datetime(2026, 9, 30, 5, 0), datetime(2026, 9, 30, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None, work_period_id="OS-WP", required_rest_after_hours=11),
        Assignment("OS2", "other-v1", "A", datetime(2026, 9, 30, 17, 0), datetime(2026, 10, 1, 5, 0),
                   AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None, work_period_id="OS-WP", required_rest_after_hours=20),
    )
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(
        profile=profile, employees=(employee,), memberships=(_membership("A"),),
        shift_demands=demands, other_site_assignments=other_site_pair,
    )
    assert plan(state).status == "DECISION_REQUIRED"  # merged other-site period ends 05:00, terminal rest=20h, gap=0h


def test_b_no_other_site_record_produces_no_invented_blocker():
    profile = _profile("B-NOOTHER", [_d(5, 11)])
    demands = tuple(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1))
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(profile=profile, employees=(employee,), memberships=(_membership("A"),), shift_demands=demands)
    assert plan(state).status == "FEASIBLE"


def test_b_legacy_assignment_without_provenance_defaults_to_11h():
    assert resolve_required_rest(None) == 11
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 2, 1, 0), datetime(2026, 10, 2, 13, 0))  # 8h gap < legacy 11h
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))
    report = validate(state, [_primary("A1", "E", d1), _primary("A2", "E", d2)])
    assert not report.hard_pass and any("REST-01" in v for v in report.violations)


# --- B contract-alignment round 2 (part_b_work_period_rest.md 9f7ff98) ---


def test_b_deviation_categories_are_frozen():
    from rota.application.deviation_mapping import category_for_rule
    from rota.domain import DeviationCategory

    assert category_for_rule("SHIFT-24-01", {}) == DeviationCategory.PREFERENCE
    assert category_for_rule("SHIFT-24-PAIR-01", {}) == DeviationCategory.COVERAGE


def test_b_mixed_can_work_24h_false_blocks_via_eligibility_directly():
    from rota.planning.eligibility import check_eligibility

    profile = _profile("B-ELIG24", [_h24(ShiftKind.D, 5, 12), _d(9, 11)])
    demand = next(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1) and d.catalog_kind == ShiftCatalogKind.H24)
    membership = _membership("A", can_work_24h=False)
    result = check_eligibility(Employee("A", "A", date(2026, 1, 1), None, False), membership, demand, demand.shift_kind, profile, [], [], SITE_ID)
    assert not result.eligible and result.blocked_reason == "SHIFT-24-01"


def test_b_fixed_half_forces_same_person_on_open_half():
    profile, (d1, d2) = _h24_pair_demands("B-FIXEDHALF", ShiftKind.D, 12)
    fixed = _primary("FIXED1", "E1", d1, work_period_id=f"{SITE_ID}:{d1.work_period_template_id}", required_rest_after_hours=d1.required_rest_hours, frozen=True)
    employees = (Employee("E1", "E1", date(2026, 1, 1), None, False), Employee("E2", "E2", date(2026, 1, 1), None, False))
    state = base_state(
        profile=profile, employees=employees, memberships=(_membership("E1"), _membership("E2")),
        shift_demands=(d1, d2), existing_assignments=(fixed,),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    solved_d2 = next(a for a in result.candidates[0] if a.covers_demand_id == d2.demand_id)
    assert solved_d2.employee_id == "E1"


def test_b_target_scoped_rest_ignores_history_vs_history_violation():
    profile = _profile("B-SCOPED", [_d(5, 11)])
    demand = next(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1))
    # Two boundary/other-site periods that violate REST-01 between themselves,
    # neither touching the target assignment being validated.
    boundary = Assignment("BND1", "prev-v1", "Z", datetime(2026, 9, 29, 5, 0), datetime(2026, 9, 29, 17, 0), AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None, required_rest_after_hours=11)
    other_site = Assignment("OS1", "other-v1", "Z", datetime(2026, 9, 29, 18, 0), datetime(2026, 9, 30, 6, 0), AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None, required_rest_after_hours=11)
    state = base_state(
        profile=profile, shift_demands=(demand,), memberships=(_membership("Z"),),
        boundary_assignments=(boundary,), other_site_assignments=(other_site,),
    )
    target = [_primary("TGT", "Z", demand, required_rest_after_hours=11)]
    report = validate(state, target)
    assert report.hard_pass  # the 1h boundary<->other-site gap is unrelated to the target


def test_b_malformed_period_more_than_two_components_fails_closed():
    d = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 9, 0))
    a1 = Assignment("A1", "v1", "E", datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 1, 4, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "d1", None, work_period_id="WP", required_rest_after_hours=11)
    a2 = Assignment("A2", "v1", "E", datetime(2026, 10, 1, 4, 0), datetime(2026, 10, 1, 8, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "d1", None, work_period_id="WP", required_rest_after_hours=11)
    a3 = Assignment("A3", "v1", "E", datetime(2026, 10, 1, 8, 0), datetime(2026, 10, 1, 9, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "d1", None, work_period_id="WP", required_rest_after_hours=11)
    state = base_state(shift_demands=(d,), memberships=(_membership("E"),))
    report = validate(state, [a1, a2, a3])
    assert not report.hard_pass and any("WORK_PERIOD-01" in v for v in report.violations)


def test_b_malformed_period_inconsistent_same_version_rest_fails_closed():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0))
    a1 = Assignment("A1", "v1", "E", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "d1", None, work_period_id="WP", required_rest_after_hours=11)
    a2 = Assignment("A2", "v1", "E", d2.start_datetime, d2.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "d2", None, work_period_id="WP", required_rest_after_hours=14)
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))
    report = validate(state, [a1, a2])
    assert not report.hard_pass and any("WORK_PERIOD-01" in v for v in report.violations)


def test_b_solved_legacy_assignment_gets_explicit_nonnone_provenance():
    profile = _profile("B-LEGACYPROV", [StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1)])
    demand = next(d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1))
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(profile=profile, employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand,))
    result = plan(state)
    assert result.status == "FEASIBLE"
    solved = result.candidates[0][0]
    assert solved.work_period_id is not None and solved.required_rest_after_hours == 11


def test_b_work_period_id_is_site_scoped():
    profile, (d1, _d2) = _h24_pair_demands("B-SITESCOPE", ShiftKind.D, 12)
    employees = (Employee("A", "A", date(2026, 1, 1), None, False), Employee("B", "B", date(2026, 1, 1), None, False))
    state = base_state(profile=profile, employees=employees, memberships=(_membership("A"), _membership("B")), shift_demands=(d1, _d2))
    result = plan(state)
    assert result.status == "FEASIBLE"
    solved = next(a for a in result.candidates[0] if a.covers_demand_id == d1.demand_id)
    assert solved.work_period_id.startswith(f"{SITE_ID}:")


def test_b_solver_feasible_candidate_independently_validates_hard_pass():
    # H24 occupies the entire day 1, so INNY is drawn from day 2 instead --
    # both catalog kinds represented without their windows overlapping.
    profile = _profile("B-CONSISTENCY", [_h24(ShiftKind.D, 5, 12), _inny(9, 6, 10)])
    all_demands = generate_catalog_demands(profile, MONTH)
    demands = tuple(
        d for d in all_demands
        if (d.start_datetime.date() == date(2026, 10, 1) and d.catalog_kind == ShiftCatalogKind.H24)
        or (d.start_datetime.date() == date(2026, 10, 2) and d.catalog_kind == ShiftCatalogKind.OTHER)
    )
    employees = (Employee("A", "A", date(2026, 1, 1), None, False), Employee("B", "B", date(2026, 1, 1), None, False))
    state = base_state(profile=profile, employees=employees, memberships=(_membership("A"), _membership("B")), shift_demands=demands)
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert validate(state, result.candidates[0]).hard_pass


# --- B round 10 audit closure (B-R10-1..4) + remaining minimum matrix ---


def test_b_r10_rest_context_is_not_capped_below_a_relevant_configured_rest(monkeypatch):
    import rota.application.assembler as assembler_module

    captured = {}

    def same_site(_conn, _site_id, start, end):
        captured["same"] = (start, end)
        return []

    def other_site(_conn, _employee_ids, start, end, **_kwargs):
        captured["other"] = (start, end)
        return []

    monkeypatch.setattr(assembler_module, "get_current_assignments_in_interval", same_site)
    monkeypatch.setattr(assembler_module, "get_current_assignments_for_employees", other_site)
    month = date(2026, 10, 1)
    assembler_module._assemble_cross_context(object(), SITE_ID, ["E"], month, frozenset())

    relevant_prior_end = datetime(2026, 10, 1) - timedelta(hours=9_000)
    relevant_future_start = datetime(2026, 10, 31) + timedelta(hours=9_000)
    for start, end in captured.values():
        assert start <= relevant_prior_end
        assert end >= relevant_future_start


@pytest.mark.parametrize(
    ("first_end", "second_start"),
    [(datetime(2026, 10, 1, 4), datetime(2026, 10, 1, 5)), (datetime(2026, 10, 1, 6), datetime(2026, 10, 1, 5))],
)
def test_b_r10_explicit_period_requires_continuous_nonoverlapping_chain(first_end, second_start):
    components = [
        PeriodComponent("A1", "E", datetime(2026, 10, 1, 0), first_end, "WP", 11, "V1"),
        PeriodComponent("A2", "E", second_start, datetime(2026, 10, 1, 9), "WP", 11, "V1"),
    ]
    assert find_malformed_periods(components)


@pytest.mark.parametrize("invalid_rest", [None, -1])
def test_b_r10_new_explicit_provenance_cannot_fall_back_or_accept_negative_rest(invalid_rest):
    components = [PeriodComponent("A1", "E", datetime(2026, 10, 1, 0), datetime(2026, 10, 1, 4), "EXPLICIT-WP", invalid_rest, "V1")]
    assert find_malformed_periods(components)


def test_b_r10_validator_checks_every_target_relevant_edge_not_only_adjacent_starts():
    demand = ShiftDemand("D-TARGET", "V1", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), 1)
    outer_history = _primary("OUTER", "E", ShiftDemand("d", "prev", datetime(2026, 9, 30, 0), datetime(2026, 10, 1, 10), 1))
    inner_history = _primary("INNER", "E", ShiftDemand("d", "prev", datetime(2026, 9, 30, 5), datetime(2026, 9, 30, 17), 1))
    target = _primary("TARGET", "E", demand)
    state = base_state(shift_demands=(demand,), memberships=(_membership("E"),), boundary_assignments=(outer_history, inner_history))
    codes = [item.rule for item in validate(state, [target]).violation_details]
    assert "REST-01" in codes


def test_b_rest_zero_is_legal():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0))
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))
    report = validate(state, [_primary("A1", "E", d1, required_rest_after_hours=0), _primary("A2", "E", d2, required_rest_after_hours=0)])
    assert report.hard_pass


def test_b_overlap_of_different_periods_is_hard_fail():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 1, 10, 0), datetime(2026, 10, 1, 22, 0))
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))
    a1 = _primary("A1", "E", d1, work_period_id="WP1", required_rest_after_hours=11)
    a2 = _primary("A2", "E", d2, work_period_id="WP2", required_rest_after_hours=11)
    report = validate(state, [a1, a2])
    assert not report.hard_pass and any("overlapping" in v for v in report.violations)


def test_b_minimum_rest_hours_not_lowered_by_internal_24h_boundary():
    profile, (d1, d2) = _h24_pair_demands("B-MINREST", ShiftKind.D, 14)
    d3 = _demand("d3", d2.end_datetime + timedelta(hours=20), d2.end_datetime + timedelta(hours=32))
    a1 = _primary("A1", "E", d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=d1.required_rest_hours)
    a2 = _primary("A2", "E", d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=d2.required_rest_hours)
    a3 = _primary("A3", "E", d3, required_rest_after_hours=11)
    state = base_state(profile=profile, shift_demands=(d1, d2, d3), memberships=(_membership("E"),))
    report = validate(state, [a1, a2, a3])
    assert report.hard_pass
    assert report.minimum_rest_hours == 20  # not 0 from the internal D/N boundary


def test_b_normal_24h_n_to_d_count_two_conflicting_fixed_sets_is_hard_fail():
    shift = StandardShift(ShiftKind.N, time(17), time(17), True, 2, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=12)
    profile = _profile("B-COUNT2", [shift])
    all_demands = generate_catalog_demands(profile, MONTH)
    first_template = next(d.work_period_template_id for d in all_demands if d.start_datetime.date() == date(2026, 10, 1))
    d1, d2 = sorted((d for d in all_demands if d.work_period_template_id == first_template), key=lambda d: d.start_datetime)
    a1 = [_primary(f"A1-{e}", e, d1, work_period_id=d1.work_period_template_id, required_rest_after_hours=12) for e in ("E1", "E2")]
    a2 = [_primary(f"A2-{e}", e, d2, work_period_id=d2.work_period_template_id, required_rest_after_hours=12) for e in ("E3", "E4")]
    state = base_state(profile=profile, shift_demands=(d1, d2), memberships=tuple(_membership(e) for e in ("E1", "E2", "E3", "E4")))
    report = validate(state, [*a1, *a2])
    assert not report.hard_pass and any("SHIFT-24-PAIR-01" in v for v in report.violations)


def test_b_can_work_24h_false_does_not_block_ordinary_h12_or_inny():
    profile = _profile("B-ORDINARY24", [_h24(ShiftKind.D, 5, 12), _d(9, 11), _inny(21, 2, 5)])
    demands = [d for d in generate_catalog_demands(profile, MONTH) if d.start_datetime.date() == date(2026, 10, 1) and d.catalog_kind != ShiftCatalogKind.H24]
    membership = _membership("A", can_work_24h=False)
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    for demand in demands:
        result = check_eligibility(employee, membership, demand, demand.shift_kind, profile, [], [], SITE_ID)
        assert result.eligible


def test_b_day_only_still_blocks_n_component_of_normal_24h():
    profile, (d1, d2) = _h24_pair_demands("B-DAYONLYN", ShiftKind.D, 12)  # day_only_blocks_n=True via _profile
    day_only_employee = Employee("A", "A", date(2026, 1, 1), None, True)
    membership = _membership("A")
    n_component = d2 if d2.shift_kind == ShiftKind.N else d1
    result = check_eligibility(day_only_employee, membership, n_component, ShiftKind.N, profile, [], [], SITE_ID)
    assert not result.eligible and result.blocked_reason == "DAY_ONLY-01"


def test_b_both_solved_h24_assignments_share_work_period_id_and_rest():
    profile, (d1, d2) = _h24_pair_demands("B-SHARED", ShiftKind.D, 15)
    employee = Employee("A", "A", date(2026, 1, 1), None, False)
    state = base_state(profile=profile, employees=(employee,), memberships=(_membership("A"),), shift_demands=(d1, d2))
    result = plan(state)
    assert result.status == "FEASIBLE"
    solved = {a.covers_demand_id: a for a in result.candidates[0]}
    assert solved[d1.demand_id].work_period_id == solved[d2.demand_id].work_period_id
    assert solved[d1.demand_id].required_rest_after_hours == solved[d2.demand_id].required_rest_after_hours == 15


def test_b_cancelled_excluded_from_work_period_rest_normalization():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 1, 18, 0), datetime(2026, 10, 2, 6, 0))
    state = base_state(shift_demands=(d2,), memberships=(_membership("E"),))
    cancelled = Assignment("A1", "test-v1", "E", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, d1.demand_id, None, required_rest_after_hours=11)
    a2 = _primary("A2", "E", d2, required_rest_after_hours=11)
    report = validate(state, [cancelled, a2])
    assert report.hard_pass  # the CANCELLED 1h-gap sibling must not participate in REST-01


def test_b_trainee_without_provenance_keeps_legacy_standalone_rest():
    d1 = _demand("d1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0))
    d2 = _demand("d2", datetime(2026, 10, 1, 18, 0), datetime(2026, 10, 2, 6, 0))
    state = base_state(shift_demands=(d1, d2), memberships=(_membership("E"),))
    mentor = _primary("MENTOR", "E", d1, required_rest_after_hours=11)
    trainee = Assignment(
        "TRAINEE", "test-v1", "E", d2.start_datetime, d2.end_datetime, AssignmentRole.TRAINEE,
        AssignmentState.PLANNED, False, None, "MENTOR",
    )
    report = validate(state, [mentor, trainee])
    assert not report.hard_pass and any("REST-01" in v for v in report.violations)  # 1h gap < legacy 11h


def _seed_history_site(conn, *, site_id: str, profile_id: str, employee_id: str) -> None:
    # rolling_7d_decision_threshold_hours is raised above a single
    # employee's worst-case 7*12=84h (one demand every day of the month,
    # LOAD-01 is not the fact under test here) so a full-month plan_month
    # control run is FEASIBLE on this fixture alone, with no history.
    profile = replace(_profile(profile_id, [_d(5, 11)]), rolling_7d_decision_threshold_hours=100)
    save_site_profile(conn, profile)
    save_site(conn, Site(site_id, profile_id, site_id, True))
    save_coordinator(conn, Coordinator("COORD-1", "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", site_id, True))
    save_employee(conn, Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    days_in_month = calendar.monthrange(MONTH.year, MONTH.month)[1]
    for day in range(1, days_in_month + 1):
        save_calendar_day(conn, CalendarDay(date(MONTH.year, MONTH.month, day), False))


def _write_history_version(conn, *, site_id: str, month: date, employee_id: str, start: datetime, end: datetime, rest: int) -> None:
    demand_id = f"hist-{start.date().isoformat()}"
    demand = ShiftDemand(demand_id, "", start, end, 1)
    assignment = Assignment(
        f"hist-a-{start.date().isoformat()}", "", employee_id, start, end, AssignmentRole.PRIMARY,
        AssignmentState.REALIZED, True, demand_id, None, required_rest_after_hours=rest,
    )
    create_schedule_version(
        conn, version_id=f"SV-{start.date().isoformat()}", site_id=site_id, month=month, parent_version_id=None,
        created_at=datetime(2020, 1, 1), created_by="COORD-1", applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[assignment], deviations=[], effective_from=month,
    )



# Real elapsed gap Jan 2015 -> Oct 2026 (~103,000h) and Oct 2026 -> Jan 2035
# (~74,000h) are both smaller than REST_HOURS_BEYOND_GAP, so a REST-01 block
# is only possible if the persisted period is actually still visible that
# far away -- proving B-R10-1's unbounded context, not a rest value the
# real elapsed time would have satisfied anyway (B-R10-4).
REST_HOURS_BEYOND_GAP = 110_000
OLD_HISTORY_MONTH = date(2015, 1, 1)
OLD_HISTORY_START = datetime(2015, 1, 1, 5)
OLD_HISTORY_END = datetime(2015, 1, 1, 17)
FUTURE_HISTORY_MONTH = date(2035, 1, 1)
FUTURE_HISTORY_START = datetime(2035, 1, 1, 5)
FUTURE_HISTORY_END = datetime(2035, 1, 1, 17)


def _plan_single_target_day(conn, *, site_id: str, day: date, rest: int | None = None):
    from rota.application.assembler import assemble_planning_state

    start, end = datetime.combine(day, time(5, 0)), datetime.combine(day, time(17, 0))
    kwargs = {"shift_kind": ShiftKind.D, "required_rest_hours": rest} if rest is not None else {}
    demand = ShiftDemand(f"single-{day.isoformat()}", "", start, end, 1, **kwargs)
    state, _warnings = assemble_planning_state(conn, site_id=site_id, month=MONTH, shift_demands=(demand,))
    return plan(state)


def test_b_persisted_prior_same_site_period_blocks_current_with_feasible_control(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _seed_history_site(conn, site_id="SITE-HIST-A", profile_id="PROF-HIST-A", employee_id="A")
    control = _plan_single_target_day(conn, site_id="SITE-HIST-A", day=date(2026, 10, 1))
    assert control.status == "FEASIBLE"  # identical fixture, no history yet -- rules out the fixture itself as the cause

    _write_history_version(conn, site_id="SITE-HIST-A", month=OLD_HISTORY_MONTH, employee_id="A", start=OLD_HISTORY_START, end=OLD_HISTORY_END, rest=REST_HOURS_BEYOND_GAP)
    blocked = _plan_single_target_day(conn, site_id="SITE-HIST-A", day=date(2026, 10, 1))
    assert blocked.status == "DECISION_REQUIRED"


def test_b_persisted_prior_cross_site_period_blocks_current_with_feasible_control(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _seed_history_site(conn, site_id="SITE-HIST-B1", profile_id="PROF-HIST-B1", employee_id="A")
    _seed_history_site(conn, site_id="SITE-HIST-B2", profile_id="PROF-HIST-B2", employee_id="A")
    control = _plan_single_target_day(conn, site_id="SITE-HIST-B2", day=date(2026, 10, 1))
    assert control.status == "FEASIBLE"

    _write_history_version(conn, site_id="SITE-HIST-B1", month=OLD_HISTORY_MONTH, employee_id="A", start=OLD_HISTORY_START, end=OLD_HISTORY_END, rest=REST_HOURS_BEYOND_GAP)
    blocked = _plan_single_target_day(conn, site_id="SITE-HIST-B2", day=date(2026, 10, 1))
    assert blocked.status == "DECISION_REQUIRED"


def test_b_persisted_future_cross_site_period_blocks_current_with_feasible_control(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _seed_history_site(conn, site_id="SITE-HIST-C1", profile_id="PROF-HIST-C1", employee_id="A")
    _seed_history_site(conn, site_id="SITE-HIST-C2", profile_id="PROF-HIST-C2", employee_id="A")
    # Target's OWN rest governs the wall toward a LATER known period, so it
    # -- not the future period's rest -- must exceed the real gap.
    control = _plan_single_target_day(conn, site_id="SITE-HIST-C1", day=date(2026, 10, 1), rest=REST_HOURS_BEYOND_GAP)
    assert control.status == "FEASIBLE"

    _write_history_version(conn, site_id="SITE-HIST-C2", month=FUTURE_HISTORY_MONTH, employee_id="A", start=FUTURE_HISTORY_START, end=FUTURE_HISTORY_END, rest=11)
    blocked = _plan_single_target_day(conn, site_id="SITE-HIST-C1", day=date(2026, 10, 1), rest=REST_HOURS_BEYOND_GAP)
    assert blocked.status == "DECISION_REQUIRED"


def test_b_normal_24h_n_to_d_count_two_positive_identical_employee_set():
    shift = StandardShift(ShiftKind.N, time(17), time(17), True, 2, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=12)
    profile = _profile("B-COUNT2POS", [shift])
    all_demands = generate_catalog_demands(profile, MONTH)
    first_template = next(d.work_period_template_id for d in all_demands if d.start_datetime.date() == date(2026, 10, 1))
    demands = tuple(d for d in all_demands if d.work_period_template_id == first_template)
    employees = tuple(Employee(e, e, date(2026, 1, 1), None, False) for e in ("E1", "E2", "E3"))
    state = base_state(profile=profile, employees=employees, memberships=tuple(_membership(e) for e in ("E1", "E2", "E3")), shift_demands=demands)
    result = plan(state)
    assert result.status == "FEASIBLE"
    by_demand: dict = {}
    for a in result.candidates[0]:
        by_demand.setdefault(a.covers_demand_id, set()).add(a.employee_id)
    d1, d2 = demands
    assert by_demand[d1.demand_id] == by_demand[d2.demand_id]
    assert len(by_demand[d1.demand_id]) == 2


def test_b_cross_month_normal_24h_normalizes_as_one_period():
    from rota.planning.work_periods import PeriodComponent, group_into_periods

    profile = _profile("B-CROSSMONTHNORM", [_h24(ShiftKind.N, 17, 13)])
    demands = list(generate_catalog_demands(profile, MONTH))
    crossing = sorted((d for d in demands if d.start_datetime >= datetime(2026, 10, 31, 17)), key=lambda d: d.start_datetime)
    d1, d2 = crossing
    wp_id = f"{SITE_ID}:{d1.work_period_template_id}"
    a1 = _primary("A1", "E", d1, work_period_id=wp_id, required_rest_after_hours=13)
    a2 = _primary("A2", "E", d2, work_period_id=wp_id, required_rest_after_hours=13)
    components = [PeriodComponent(a.assignment_id, "E", a.start_datetime, a.end_datetime, a.work_period_id, a.required_rest_after_hours, a.schedule_version_id) for a in (a1, a2)]
    periods = group_into_periods(components)
    assert len(periods) == 1
    assert periods[0].start == d1.start_datetime and periods[0].end == d2.end_datetime
    assert periods[0].required_rest_after_hours == 13


if __name__ == "__main__":
    print("test_t012 module OK")
