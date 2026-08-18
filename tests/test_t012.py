"""ROTA-T012: 24h/12h/INNY shift catalog + work-period rest provenance.

Consolidates all T012 checkpoint (A/B/C/D) tests in one file per contract
(tasks/ROTA-T012/brief.md UNION TASK_SCOPE). This revision adds Part A only
(tasks/ROTA-T012/part_a_catalog_persistence.md): catalog data model,
StandardShift/SiteMembership/ShiftDemand/Assignment persistence, and
generate_catalog_demands. No solver/eligibility/emergency-retry semantics
are exercised yet -- those are Part B/C/D.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
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
from rota.persistence.db import LATEST_SCHEMA_VERSION, connect
from rota.persistence.employee_repository import list_memberships_for_site, save_employee, save_site_membership
from rota.persistence.schedule_errors import MalformedScheduleSnapshot
from rota.persistence.schedule_validation import validate_assignments, validate_demands
from rota.persistence.site_profile_repository import get_site_profile, save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.shift_catalog import (
    AmbiguousEmergency24hCapability,
    InvalidStandardShift,
    classify_demand,
    generate_catalog_demands,
    normalized_catalog_kind,
)

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


if __name__ == "__main__":
    print("test_t012 module OK")
