"""ROTA-T065 (tasks/ROTA-T065/brief.md): ORDINARY store roles.

Acceptance scenarios T65-01..T65-11 and technical acceptance T65-A1..A11
from the brief, using the same lightweight tests/support/minimal_state.py
harness test_eligibility_matrix.py already uses for full-pipeline
eligibility invariants -- no persistence/API needed for the planning-layer
proofs; a separate persistence round-trip section exercises the actual
read/write path.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date, datetime, time

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    EmployeeRole,
    ExternalSupportWindow,
    MembershipKind,
    ShiftDemand,
    ShiftKind,
    SiteMembership,
    SiteProfile,
    StandardShift,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_site_membership
from rota.persistence.schedule_lifecycle import create_schedule_version
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.site_profile_repository import get_site_profile, save_site_profile
from rota.planning.eligibility import check_eligibility
from rota.planning.engine import plan
from rota.planning.shift_catalog import generate_catalog_demands
from rota.planning.validator import validate
from tests.support.minimal_state import PROFILE_ID, ReadinessSource, ReadinessState, SITE_ID, base_profile, base_state

MONTH = date(2026, 10, 1)
KIEROWNIK = EmployeeRole.KIEROWNIK
SPRZEDAWCA = EmployeeRole.SPRZEDAWCA_ZALOGA


def _membership(employee_id: str, *, kind=MembershipKind.LOCAL, roles: frozenset = frozenset()) -> SiteMembership:
    return SiteMembership(
        employee_id, SITE_ID, kind, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        allowed_roles=roles,
    )


def _employee(employee_id: str) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, False)


# --- eligibility.py: ROLE-01 gate (T65-A3) ---------------------------------


def test_role_gate_blocks_without_role_and_allows_with_role_local():
    demand = ShiftDemand("D-1", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=KIEROWNIK)
    membership_no_role = _membership("E1")
    membership_with_role = _membership("E1", roles=frozenset({KIEROWNIK}))
    employee = _employee("E1")
    profile = base_profile()

    blocked = check_eligibility(
        employee, membership_no_role, demand, ShiftKind.D, profile, [], [], SITE_ID,
    )
    assert blocked.eligible is False
    assert blocked.blocked_reason == "ROLE-01"

    allowed = check_eligibility(
        employee, membership_with_role, demand, ShiftKind.D, profile, [], [], SITE_ID,
    )
    assert allowed.eligible is True


def test_role_gate_applies_identically_to_external_support():
    demand = ShiftDemand("D-1", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=SPRZEDAWCA)
    profile = base_profile()
    employee = _employee("E1")
    window = ExternalSupportWindow("W1", "E1", SITE_ID, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None)

    membership_no_role = _membership("E1", kind=MembershipKind.EXTERNAL_SUPPORT)
    blocked = check_eligibility(
        employee, membership_no_role, demand, ShiftKind.D, profile, [], [window], SITE_ID,
    )
    assert blocked.eligible is False
    assert blocked.blocked_reason == "ROLE-01"

    membership_with_role = _membership("E1", kind=MembershipKind.EXTERNAL_SUPPORT, roles=frozenset({SPRZEDAWCA}))
    allowed = check_eligibility(
        employee, membership_with_role, demand, ShiftKind.D, profile, [], [window], SITE_ID,
    )
    assert allowed.eligible is True


def test_role_gate_is_no_op_for_legacy_ochrona_demand():
    # required_role=None (every OCHRONA/legacy demand) -- strict no-op
    # regardless of the membership's allowed_roles (empty by default).
    demand = ShiftDemand("D-1", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    result = check_eligibility(
        _employee("E1"), _membership("E1"), demand, ShiftKind.D, base_profile(), [], [], SITE_ID,
    )
    assert result.eligible is True


# --- T65-01: two roles, one pipeline, no per-role second solve -------------


def test_two_roles_overlapping_demands_one_plan_pipeline():
    manager_demand = ShiftDemand(
        "D-MGR", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=KIEROWNIK,
    )
    staff_demand = ShiftDemand(
        "D-STAFF", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=SPRZEDAWCA,
    )
    state = base_state(
        employees=(_employee("MGR"), _employee("STAFF")),
        memberships=(
            _membership("MGR", roles=frozenset({KIEROWNIK})),
            _membership("STAFF", roles=frozenset({SPRZEDAWCA})),
        ),
        shift_demands=(manager_demand, staff_demand),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    by_demand = {a.covers_demand_id: a.employee_id for a in candidate if a.role == AssignmentRole.PRIMARY}
    assert by_demand["D-MGR"] == "MGR"
    assert by_demand["D-STAFF"] == "STAFF"


# --- T65-03: no hidden role fallback ----------------------------------------


def test_free_manager_does_not_silently_cover_staff_demand():
    staff_demand = ShiftDemand(
        "D-STAFF", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=SPRZEDAWCA,
    )
    # Only a KIEROWNIK-only employee exists -- no one is eligible for the
    # staff demand, and the solver must not invent an interchangeability
    # it was never given.
    state = base_state(
        employees=(_employee("MGR"),),
        memberships=(_membership("MGR", roles=frozenset({KIEROWNIK})),),
        shift_demands=(staff_demand,),
    )
    result = plan(state)
    assert result.status != "FEASIBLE"


# --- T65-02: explicit role addition, then a normal re-plan -----------------


def test_explicit_role_addition_enables_coverage_on_next_plan():
    staff_demand = ShiftDemand(
        "D-STAFF", "v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=SPRZEDAWCA,
    )
    kierownik_only = base_state(
        employees=(_employee("MGR"),),
        memberships=(_membership("MGR", roles=frozenset({KIEROWNIK})),),
        shift_demands=(staff_demand,),
    )
    assert plan(kierownik_only).status != "FEASIBLE"

    # Coordinator explicitly adds SPRZEDAWCA_ZALOGA to the SAME membership
    # (no second Employee/SiteMembership) -- a normal subsequent PLAN now
    # succeeds.
    both_roles = replace(
        kierownik_only,
        memberships=(_membership("MGR", roles=frozenset({KIEROWNIK, SPRZEDAWCA})),),
    )
    result = plan(both_roles)
    assert result.status == "FEASIBLE"
    assert result.candidates[0][0].employee_id == "MGR"


# --- validator.py: independent ROLE-01 mirror (T65-11) ---------------------


def test_validator_role_mirror_flags_manual_violation():
    demand = ShiftDemand("D-1", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=KIEROWNIK)
    state = base_state(
        employees=(_employee("E1"),),
        memberships=(_membership("E1"),),  # no roles
        shift_demands=(demand,),
    )
    assignment = Assignment(
        "A-1", "test-v1", "E1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    report = validate(state, [assignment])
    codes = {d.rule for d in report.violation_details}
    assert "ROLE-01" in codes


def test_validator_role_mirror_passes_with_correct_role():
    demand = ShiftDemand("D-1", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1, required_role=KIEROWNIK)
    state = base_state(
        employees=(_employee("E1"),),
        memberships=(_membership("E1", roles=frozenset({KIEROWNIK})),),
        shift_demands=(demand,),
    )
    assignment = Assignment(
        "A-1", "test-v1", "E1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )
    report = validate(state, [assignment])
    codes = {d.rule for d in report.violation_details}
    assert "ROLE-01" not in codes


# --- shift_catalog.py: required_role propagation (T65-04/A2) ---------------


def test_generate_catalog_demands_propagates_required_role_and_reuses_generator():
    profile = SiteProfile(
        profile_id=PROFILE_ID, display_name="Shop", active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(5, 0), time(12, 0), False, 1, required_role=KIEROWNIK),
            StandardShift(ShiftKind.D, time(12, 0), time(19, 0), False, 1, required_role=SPRZEDAWCA),
            # A third, overlapping/"middle" INNY shift -- proves reuse of the
            # existing generator for arbitrary full-hour intervals, not a
            # new shop-specific one (T65-04).
            StandardShift(ShiftKind.D, time(10, 0), time(18, 0), False, 1, required_role=SPRZEDAWCA),
        ],
        day_only_blocks_n=False, external_support_enabled=True,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )
    demands = generate_catalog_demands(profile, MONTH)
    assert len(demands) == 3 * 31  # October has 31 days, all weekdays active
    roles_seen = {d.required_role for d in demands}
    assert roles_seen == {KIEROWNIK, SPRZEDAWCA}


def test_24h_occurrence_keeps_same_required_role_on_both_components():
    profile = SiteProfile(
        profile_id=PROFILE_ID, display_name="24/7 shop", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(6, 0), True, 1, required_role=SPRZEDAWCA)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )
    demands = generate_catalog_demands(profile, MONTH)
    assert len(demands) == 31 * 2  # 24h -> two 12h components per day
    assert all(d.required_role == SPRZEDAWCA for d in demands)
    # kind flips D/N between the two halves (existing T012 shape); role does not.
    kinds = {d.shift_kind for d in demands}
    assert kinds == {ShiftKind.D, ShiftKind.N}


# --- T65-05: through midnight, no accidental OCHRONA night semantics ------


def test_midnight_crossing_ordinary_demand_never_triggers_night_streak():
    # Three consecutive days of a role-bearing "night" 22:00-06:00 shop
    # shift, internally shift_kind=D throughout (the neutral bucket) --
    # NIGHT-STREAK-01 must never fire, since it only ever looks at N.
    demands = tuple(
        ShiftDemand(
            f"D-{i}", "test-v1", datetime(2026, 10, i, 22, 0), datetime(2026, 10, i + 1, 6, 0), 1,
            shift_kind=ShiftKind.D, required_role=SPRZEDAWCA,
        )
        for i in range(1, 4)
    )
    state = base_state(
        employees=(_employee("E1"),),
        memberships=(_membership("E1", roles=frozenset({SPRZEDAWCA})),),
        shift_demands=demands,
    )
    assignments = [
        Assignment(
            f"A-{i}", "test-v1", "E1", d.start_datetime, d.end_datetime,
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d.demand_id, None,
        )
        for i, d in enumerate(demands)
    ]
    report = validate(state, assignments)
    codes = {d.rule for d in report.violation_details}
    assert "NIGHT-STREAK-01" not in codes
    assert "ROLE-01" not in codes


# --- T65-09: OCHRONA D/N regression is untouched ---------------------------


def test_ochrona_dn_gate_unaffected_by_role_field_being_none():
    demand = ShiftDemand("D-1", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1, shift_kind=ShiftKind.N)
    profile = base_profile()  # day_only_blocks_n=True
    day_only_employee = Employee("E1", "E1", date(2020, 1, 1), None, True)
    result = check_eligibility(
        day_only_employee, _membership("E1"), demand, ShiftKind.N, profile, [], [], SITE_ID,
    )
    assert result.eligible is False
    assert result.blocked_reason == "DAY_ONLY-01"


# --- Persistence round trip: allowed_roles / required_role (T65-06/A1/A2) -


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "rota.db")
    yield connection
    connection.close()


def _bootstrap_ordinary_site(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO coordinators (coordinator_id, display_name, active) VALUES (?, ?, ?)",
        ("COORD-T065", "Coord", 1),
    )
    profile = SiteProfile(
        profile_id="PROF-T065", display_name="Shop", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(5, 0), time(12, 0), False, 1, required_role=KIEROWNIK)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )
    save_site_profile(conn, profile)
    conn.execute(
        "INSERT INTO sites (site_id, profile_id, display_name, active, planning_regime) VALUES (?, ?, ?, ?, ?)",
        ("SITE-T065", "PROF-T065", "Shop", 1, "ORDINARY"),
    )
    conn.execute(
        "INSERT INTO coordinator_site_associations (coordinator_id, site_id, active) VALUES (?, ?, ?)",
        ("COORD-T065", "SITE-T065", 1),
    )


def test_allowed_roles_round_trips_through_site_membership_persistence(conn):
    _bootstrap_ordinary_site(conn)
    conn.execute(
        "INSERT INTO employees (employee_id, display_name, active_from, active_to, day_only) VALUES (?, ?, ?, ?, ?)",
        ("E1", "E1", "2020-01-01", None, 0),
    )
    membership = SiteMembership(
        employee_id="E1", site_id="SITE-T065", membership_kind=MembershipKind.LOCAL, enabled=True,
        readiness_state=ReadinessState.READY_FOR_PRIMARY, readiness_source=ReadinessSource.DEFAULT,
        allowed_roles=frozenset({KIEROWNIK, SPRZEDAWCA}),
    )
    save_site_membership(conn, membership)
    reloaded = list_memberships_for_site(conn, "SITE-T065")[0]
    assert reloaded.allowed_roles == frozenset({KIEROWNIK, SPRZEDAWCA})


def test_required_role_round_trips_through_site_profile_persistence(conn):
    _bootstrap_ordinary_site(conn)
    profile = get_site_profile(conn, "PROF-T065")
    assert profile.standard_shifts[0].required_role == KIEROWNIK


def test_required_role_round_trips_through_schedule_version_persistence(conn):
    _bootstrap_ordinary_site(conn)
    demand = ShiftDemand(
        "DEM-1", "SV-1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1,
        shift_kind=ShiftKind.D, required_role=KIEROWNIK,
    )
    create_schedule_version(
        conn, version_id="SV-1", site_id="SITE-T065", month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 10, 1, 8, 0), created_by="COORD-T065",
        applied_rule_version_ids=[], shift_demands=[demand], assignments=[], deviations=[], effective_from=MONTH,
    )
    snapshot = get_schedule_snapshot(conn, "SV-1")
    assert snapshot.shift_demands[0].required_role == KIEROWNIK


def test_legacy_membership_and_shift_default_to_no_role(conn):
    """A pre-T065 OCHRONA row (NULL allowed_roles/required_role) reads back
    as empty/None, never crashes, never invents a role."""
    _bootstrap_ordinary_site(conn)
    conn.execute(
        "INSERT INTO employees (employee_id, display_name, active_from, active_to, day_only) VALUES (?, ?, ?, ?, ?)",
        ("LEGACY", "Legacy", "2020-01-01", None, 0),
    )
    conn.execute(
        "INSERT INTO site_memberships (employee_id, site_id, membership_kind, enabled, readiness_state, "
        "readiness_source, can_work_24h) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("LEGACY", "SITE-T065", "LOCAL", 1, "READY_FOR_PRIMARY", "DEFAULT", 1),
    )
    reloaded = next(m for m in list_memberships_for_site(conn, "SITE-T065") if m.employee_id == "LEGACY")
    assert reloaded.allowed_roles == frozenset()


# --- Audit R2 regression guards ---------------------------------------------


def test_role_gate_cannot_be_bypassed_by_untagged_assignment():
    # R2-01: a manual PRIMARY with no covers_demand_id must still be caught
    # by ROLE-01 via overlap-based fallback matching.
    demand = ShiftDemand(
        "D-MANAGER", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 12, 0), 1,
        shift_kind=ShiftKind.D, required_role=KIEROWNIK,
    )
    wrong_role_assignment = Assignment(
        "A-SELLER", "test-v1", "E1", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, None, None,
    )
    report = validate(
        base_state(
            employees=(_employee("E1"),), memberships=(_membership("E1", roles=frozenset({SPRZEDAWCA})),),
            shift_demands=(demand,),
        ),
        [wrong_role_assignment],
    )
    codes = {d.rule for d in report.violation_details}
    assert "ROLE-01" in codes
    assert "COVERAGE-01" not in codes


def test_role_based_demand_never_triggers_day_only_or_night_streak():
    # R2-02: eligibility.py + validator.py both exempt role-bearing demands
    # from D/N-specific HARD rules regardless of their technical shift_kind.
    demand = ShiftDemand(
        "D-1", "test-v1", datetime(2026, 10, 1, 22, 0), datetime(2026, 10, 2, 6, 0), 1,
        shift_kind=ShiftKind.N, required_role=SPRZEDAWCA,
    )
    eligibility_result = check_eligibility(
        Employee("E1", "E1", date(2020, 1, 1), None, True),  # day_only=True
        _membership("E1", roles=frozenset({SPRZEDAWCA})), demand, ShiftKind.N, base_profile(), [], [], SITE_ID,
    )
    assert eligibility_result.eligible is True, eligibility_result.blocked_reason

    demands = tuple(
        ShiftDemand(
            f"D-{day}", "test-v1", datetime(2026, 10, day, 22, 0), datetime(2026, 10, day + 1, 6, 0), 1,
            shift_kind=ShiftKind.N, required_role=SPRZEDAWCA,
        )
        for day in range(1, 4)
    )
    assignments = [
        Assignment(
            f"A-{i}", "test-v1", "E1", d.start_datetime, d.end_datetime,
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, d.demand_id, None,
        )
        for i, d in enumerate(demands)
    ]
    report = validate(
        base_state(
            employees=(_employee("E1"),), memberships=(_membership("E1", roles=frozenset({SPRZEDAWCA})),),
            shift_demands=demands,
        ),
        assignments,
    )
    codes = {d.rule for d in report.violation_details}
    assert "NIGHT-STREAK-01" not in codes


def test_solver_day_kind_terms_exclude_role_based_demands_from_night_count():
    # R2-02: the solver's OWN CP-SAT NIGHT-STREAK-01 term builder
    # (_build_day_kind_terms) must not count a role-bearing N-classified
    # demand's slot toward the per-day "n" term at all -- checked directly
    # against the term-builder rather than through a full plan() (a
    # single-employee 3+-night PLAN scenario also legitimately trips the
    # unrelated, correct T058 THIRD-CONSECUTIVE-SHIFT-01 global cap,
    # which would confound the result either way)."""
    from ortools.sat.python import cp_model

    from rota.planning.solver import SolverSlot, _build_day_kind_terms

    role_demand = ShiftDemand(
        "D-1", "v1", datetime(2026, 10, 1, 22, 0), datetime(2026, 10, 2, 6, 0), 1,
        shift_kind=ShiftKind.N, required_role=SPRZEDAWCA,
    )
    model = cp_model.CpModel()
    var = model.NewBoolVar("x")
    x = {("E1", role_demand.demand_id): var}
    slot = SolverSlot(employee_id="E1", demand=role_demand, shift_kind=ShiftKind.N, leave_plan_collision=False, day_off_soft_entry=False)
    state = base_state(employees=(_employee("E1"),), shift_demands=(role_demand,))

    terms = _build_day_kind_terms(state, x, [slot], [])
    n_term = terms["E1"][date(2026, 10, 1)][1]
    assert n_term == 0, "a role-based demand's slot must never contribute to the NIGHT-STREAK-01 n-term"


if __name__ == "__main__":
    print("test_t065_ordinary_roles module OK")
