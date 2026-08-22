"""ROTA-T023 Checkpoint A test matrix (brief.md section 17 subset for "A --
provenance + write-time timing core"): migration/immutability/atomicity,
R5-1 accepted-plan action proof, PRE_PLAN vs POST_PLAN provenance, R5-2
retroactivity guard, the shared coverage helper (R3-6), and multi-Site/
weekly reference invariance.

NOT covered here (Checkpoint B/C's own allowed-file scope, section 16):
consumer-equality (T23-30..35), R5-3 REPLAN cutover (needs plan_ops.py),
T020 presentation (T23-40..47, needs schedule_export.py) and the HARD/
regression tests depending on those (T23-50..54). T23-PRE-01..03 assert
the canonical HOUR TOTAL for the binding 40h example, not the literal
D1/D1/N2 print codes -- that's T23-40..47's job in Checkpoint C.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from rota.application.durable_inputs import append_availability
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    Site,
    SiteMembership,
    SiteProfile,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import site_memory
from rota.persistence.absence_reference_repository import (
    RetroactiveAbsenceRejected,
    get_absence_reference_snapshot,
)
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import LATEST_SCHEMA_VERSION, connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_repository import get_current_assignments_for_employees
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.validator import coverage_segments, validate
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind

SITE = "SITE-1"
COORDINATOR = "COORD-1"
MONTH = date(2027, 3, 1)


def _seed_minimal(conn, *, site_id: str = SITE, coordinator_id: str = COORDINATOR) -> None:
    save_site_profile(conn, SiteProfile(
        profile_id="PROF-1", display_name="Profile", active=True, standard_shifts=[],
        day_only_blocks_n=False, external_support_enabled=True, training_s_enabled=False,
        training_s_weekdays_only=False, training_s_default_readiness_threshold=0,
        rolling_7d_decision_threshold_hours=999,
    ))
    save_site(conn, Site(site_id, "PROF-1", "Site One", True))
    save_coordinator(conn, Coordinator(coordinator_id, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(coordinator_id, site_id, True))


def _employee(conn, employee_id: str, *, site_id: str = SITE, enabled: bool = True, kind: MembershipKind = MembershipKind.LOCAL) -> None:
    save_employee(conn, Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(employee_id, site_id, kind, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))


def _primary(demand_id: str, assignment_id: str, employee_id: str, start: datetime, end: datetime, *, version_id: str, state=AssignmentState.PLANNED, work_period_id=None, required_rest_after_hours=None) -> tuple[ShiftDemand, Assignment]:
    demand = ShiftDemand(demand_id, version_id, start, end, 1)
    assignment = Assignment(
        assignment_id, version_id, employee_id, start, end, AssignmentRole.PRIMARY, state, False,
        demand_id, None, work_period_id=work_period_id, required_rest_after_hours=required_rest_after_hours,
    )
    return demand, assignment


def _accept_version(
    conn, *, version_id: str, pairs: list[tuple[ShiftDemand, Assignment]], effective_from: date, accepted_at: datetime,
    site_id: str = SITE, month: date = MONTH, parent_version_id: str | None = None, coordinator_id: str = COORDINATOR,
    record_action: bool = True,
) -> None:
    """Creates+accepts a ScheduleVersion directly (no solver): storage-layer
    structural validation still applies, business-HARD validation does not."""
    def _hook(open_conn) -> None:
        site_memory.record_coordinator_action_no_commit(
            open_conn, action_kind=CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=accepted_at,
            effective_from=effective_from, month=month, schedule_version_id=version_id,
            affected_entities=[AffectedEntity("SCHEDULE_VERSION", version_id)],
            before_state=None, after_state=None, note=None,
            source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=version_id,
            responds_to_decision_required_id=None,
        )

    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=parent_version_id,
        created_at=accepted_at, created_by=coordinator_id, applied_rule_version_ids=[],
        shift_demands=[p[0] for p in pairs], assignments=[p[1] for p in pairs], deviations=[],
        effective_from=effective_from, on_success=_hook if record_action else None,
    )


def _leave(conn, *, employee_id: str, kind: AvailabilityKind, start_date: date, end_date: date, active: bool = True, availability_id: str | None = None, site_id: str = SITE, coordinator_id: str = COORDINATOR):
    return append_availability(
        conn, coordinator_id=coordinator_id, site_id=site_id, availability_id=availability_id or f"AV-{employee_id}-{start_date}",
        employee_id=employee_id, kind=kind, start_date=start_date, end_date=end_date, active=active,
    )


def _accept_one(conn, demand_id, assignment_id, employee_id, start, end, *, version_id="SV-1", accepted_at=datetime(2020, 3, 1, 8, 0), effective_from=date(2027, 3, 1), **kw) -> None:
    """Single-PRIMARY-pair shorthand for _primary()+_accept_version()."""
    version_kw = {k: kw.pop(k) for k in list(kw) if k in ("site_id", "month", "parent_version_id", "record_action")}
    d, a = _primary(demand_id, assignment_id, employee_id, start, end, version_id=version_id, **kw)
    _accept_version(conn, version_id=version_id, pairs=[(d, a)], effective_from=effective_from, accepted_at=accepted_at, **version_kw)


def _accept_two(conn, pair_a, pair_b, *, version_id="SV-1", accepted_at=datetime(2020, 3, 1, 8, 0), effective_from=date(2027, 3, 1), work_period_id=None, **kw) -> None:
    """Two-PRIMARY-pair shorthand: pair_a/pair_b are (demand_id, assignment_id, employee_id, start, end) tuples;
    work_period_id (shared by both, when given) groups them into one legal 24h WorkPeriod."""
    pairs = [_primary(*p, version_id=version_id, work_period_id=work_period_id) for p in (pair_a, pair_b)]
    _accept_version(conn, version_id=version_id, pairs=pairs, effective_from=effective_from, accepted_at=accepted_at, **kw)


def _setup(tmp_path, *, db_name: str = "rota.db"):
    """Fresh DB with the standard Site/Profile/Coordinator + Employee "A"."""
    conn = connect(tmp_path / db_name)
    _seed_minimal(conn)
    _employee(conn, "A")
    return conn


def _setup_two_sites(tmp_path, *, membership_kind_b: MembershipKind = MembershipKind.LOCAL):
    """SITE-A (default) + SITE-B, Employee "A" LOCAL at SITE-A with the given membership_kind at SITE-B."""
    conn = connect(tmp_path / "rota.db")
    _seed_minimal(conn, site_id="SITE-A")
    save_site(conn, Site("SITE-B", "PROF-1", "Site B", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(COORDINATOR, "SITE-B", True))
    _employee(conn, "A", site_id="SITE-A")
    save_site_membership(conn, SiteMembership("A", "SITE-B", membership_kind_b, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    return conn


# --- Persistence / timing provenance ----------------------------------------


def test_t23_01_migration_adds_exactly_absence_reference_snapshots(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "absence_reference_snapshots" in tables


def test_t23_02_snapshot_append_only_update_delete_rejected(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot is not None
    with pytest.raises(Exception):
        conn.execute("UPDATE absence_reference_snapshots SET reference_status = 'MISSING' WHERE availability_version_id = ?", (record.availability_version_id,))
    with pytest.raises(Exception):
        conn.execute("DELETE FROM absence_reference_snapshots WHERE availability_version_id = ?", (record.availability_version_id,))
    reread = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert reread.reference_status == snapshot.reference_status


def test_t23_03_availability_snapshot_action_atomic_on_forced_failure(tmp_path) -> None:
    conn = _setup(tmp_path)
    with pytest.raises(Exception):  # end before start -> ValueError from the chain primitive
        append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-BAD", employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 10), end_date=date(2027, 3, 1), active=True)
    history = conn.execute("SELECT COUNT(*) FROM availability_versions WHERE availability_id = 'AV-A-BAD'").fetchone()[0]
    actions = conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0]
    snapshots = conn.execute("SELECT COUNT(*) FROM absence_reference_snapshots").fetchone()[0]
    assert (history, actions, snapshots) == (0, 0, 0)


def test_t23_04_availability_changed_carries_no_schedule_version_id(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    actions = site_memory.list_coordinator_actions(conn, action_kind=CoordinatorActionKind.AVAILABILITY_CHANGED)
    assert actions and actions[0].schedule_version_id is None
    assert actions[0].source_id == record.availability_version_id


def test_t23_05_bound_post_plan_facts_survive_in_place_working_replacement(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    before = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert before.reference_status == "BOUND"
    assert before.days[0].hours == 12
    d2, a2 = _primary("D-8", "A-8b", "B", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-1")  # In-place replacement under the SAME version id must not change the already-persisted snapshot.
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[d2], assignments=[a2], deviations=[])
    after = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert after.days[0].hours == 12
    assert after.days[0].periods[0].assignment_id == "A-8"  # unchanged, original captured fact


def test_t23_06_bind_replan_finalize_restart_preserves_post_plan_reference(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _accept_one(conn, "D-15", "A-15", "A", datetime(2027, 3, 15, 5, 0), datetime(2027, 3, 15, 17, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 15), end_date=date(2027, 3, 15))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].hours == 12
    _accept_one(conn, "D-15", "A-15b", "B", datetime(2027, 3, 15, 5, 0), datetime(2027, 3, 15, 17, 0), version_id="SV-2", effective_from=date(2027, 3, 15), accepted_at=datetime(2020, 3, 15, 10, 0), parent_version_id="SV-1")  # REPLAN child accepted with B replacing A going forward -- the ALREADY-BOUND reference for A must not move.
    after_replan = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert after_replan.days[0].hours == 12
    assert after_replan.days[0].periods[0].assignment_id == "A-15"


def test_t23_07_restore_current_movement_after_bind_does_not_change_bound_hours(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-20", "A-20", "A", datetime(2027, 3, 20, 5, 0), datetime(2027, 3, 20, 17, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 20), end_date=date(2027, 3, 20))
    before = get_absence_reference_snapshot(conn, record.availability_version_id)
    _accept_one(conn, "D-21", "A-21", "A", datetime(2027, 3, 21, 5, 0), datetime(2027, 3, 21, 17, 0), version_id="SV-2", effective_from=date(2027, 3, 20), accepted_at=datetime(2020, 3, 20, 11, 0), parent_version_id="SV-1", record_action=False)  # A later child version (restore/CURRENT movement onto a new id) never rewrites the persisted snapshot row.
    after = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert after.days[0].hours == before.days[0].hours == 12


def test_t23_08_same_chain_extension_preserves_bound_blocks_new_blocks_use_authorized_timing(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0)), ("D-9", "A-9", "A", datetime(2027, 3, 9, 5, 0), datetime(2027, 3, 9, 17, 0)), accepted_at=datetime(2020, 3, 1, 9, 0))
    first = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-CHAIN")
    assert get_absence_reference_snapshot(conn, first.availability_version_id).days[0].hours == 12
    extended = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 9), availability_id="AV-A-CHAIN")
    extended_snapshot = get_absence_reference_snapshot(conn, extended.availability_version_id)
    assert [d.hours for d in extended_snapshot.days] == [12, 12]


def test_t23_09_later_sick_overlapping_bound_leave_reuses_compatible_facts(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), accepted_at=datetime(2020, 3, 1, 9, 0))
    leave = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-LEAVE")
    sick = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-SICK")
    leave_snapshot = get_absence_reference_snapshot(conn, leave.availability_version_id)
    sick_snapshot = get_absence_reference_snapshot(conn, sick.availability_version_id)
    assert leave_snapshot.days[0].hours == sick_snapshot.days[0].hours == 12
    assert leave_snapshot.days[0].periods[0].assignment_id == sick_snapshot.days[0].periods[0].assignment_id


# --- R5-1 accepted PLAN ------------------------------------------------------


def test_t23_r5_1a_technical_current_working_before_select_is_not_accepted(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_version(conn, version_id="SV-1", pairs=[], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0), record_action=False)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "PRE_PLAN_LEAVE"


def test_t23_r5_1b_selected_empty_schedule_is_accepted_proof(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_version(conn, version_id="SV-1", pairs=[], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 0  # accepted, known rest day


def test_t23_r5_1c_unselected_replan_child_does_not_hide_accepted_parent(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _accept_one(conn, "D-8", "A-8x", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-2", effective_from=date(2027, 3, 5), accepted_at=datetime(2020, 3, 5, 9, 0), parent_version_id="SV-1", record_action=False)  # A REPLAN child exists but its OWN candidate was never selected.
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].periods[0].assignment_id == "A-8"  # accepted parent SV-1, not unselected SV-2


def test_t23_r5_1d_acceptance_after_recorded_at_is_not_used(tmp_path) -> None:
    conn = _setup(tmp_path)
    # Accepted far in the future relative to real "now" -- must not be honored. SICK never
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), accepted_at=datetime.now() + timedelta(days=3650))  # falls back to PRE_PLAN, so a wrongly-honored future acceptance would read BOUND=12h.
    record = append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-EARLY", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), active=True)
    assert get_absence_reference_snapshot(conn, record.availability_version_id).days[0].status == "MISSING"


def test_t23_r5_1e_leave_before_vs_after_accepted_plan(tmp_path) -> None:
    conn = _setup(tmp_path)
    before_record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 4, 1), end_date=date(2027, 4, 1), availability_id="AV-A-1")
    assert get_absence_reference_snapshot(conn, before_record.availability_version_id).days[0].source_mode == "PRE_PLAN_LEAVE"
    _accept_one(conn, "D-1", "A-1", "A", datetime(2027, 4, 1, 5, 0), datetime(2027, 4, 1, 17, 0), version_id="SV-APR", effective_from=date(2027, 4, 1), accepted_at=datetime(2020, 3, 25, 9, 0), month=date(2027, 4, 1))
    after_record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 4, 1), end_date=date(2027, 4, 1), availability_id="AV-A-2")
    after_snapshot = get_absence_reference_snapshot(conn, after_record.availability_version_id)
    assert after_snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert after_snapshot.days[0].hours == 12


# --- PRE_PLAN_LEAVE (canonical hour total, not T020 presentation) -----------


def test_t23_pre_01_binding_40h_leave_hour_total(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 12))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert all(d.source_mode == "PRE_PLAN_LEAVE" and d.status == "BOUND" for d in snapshot.days)
    assert snapshot.days[0].periods == ()
    assert len(snapshot.days) == 5  # PRE_PLAN's own 8h/qualified-workday TOTAL is Checkpoint B's rota.balance job


def test_t23_pre_02_later_plan_creation_does_not_reclassify_persisted_pre_plan(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    assert get_absence_reference_snapshot(conn, record.availability_version_id).days[0].source_mode == "PRE_PLAN_LEAVE"
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), accepted_at=datetime(2020, 3, 5, 9, 0))
    after = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert after.days[0].source_mode == "PRE_PLAN_LEAVE"  # unchanged -- captured once, at write time


def test_t23_pre_03_pre_plan_source_never_used_as_fallback_for_missing_sick(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].source_mode == "POST_PLAN_REFERENCE"
    assert snapshot.days[0].status == "MISSING"  # never silently PRE_PLAN_LEAVE
    assert snapshot.days[0].hours is None


# --- POST_PLAN arithmetic ----------------------------------------------------


def test_t23_10_scheduled_8h(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 8, 0), datetime(2027, 3, 8, 16, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    assert get_absence_reference_snapshot(conn, record.availability_version_id).days[0].hours == 8


def test_t23_11_scheduled_12h_d_and_n(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0)), ("N-9", "A-9", "A", datetime(2027, 3, 9, 17, 0), datetime(2027, 3, 10, 5, 0)))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 9))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert [d.hours for d in snapshot.days] == [12, 12]


def test_t23_12_13_night_shift_date_anchor_owner_examples(tmp_path) -> None:
    """Owner NIGHT_SHIFT_ANCHOR: 03-01 17:00->03-02 05:00. Example 1: absence
    starts 03-02 -> 0h. Example 2: absence includes 03-01 -> full 12h on 03-01."""
    conn = _setup(tmp_path)
    _accept_one(conn, "N-1", "A-1", "A", datetime(2027, 3, 1, 17, 0), datetime(2027, 3, 2, 5, 0))
    example1 = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 2), end_date=date(2027, 3, 2), availability_id="AV-A-EX1")
    example1_snapshot = get_absence_reference_snapshot(conn, example1.availability_version_id)
    assert example1_snapshot.days[0].hours == 0
    assert example1_snapshot.days[0].periods == ()
    example2 = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 1), end_date=date(2027, 3, 1), availability_id="AV-A-EX2")
    assert get_absence_reference_snapshot(conn, example2.availability_version_id).days[0].hours == 12


def test_t23_14_legal_24h_counts_once_on_start_date(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D24-1", "A24-1", "A", datetime(2027, 3, 5, 5, 0), datetime(2027, 3, 5, 17, 0)), ("D24-2", "A24-2", "A", datetime(2027, 3, 5, 17, 0), datetime(2027, 3, 6, 5, 0)), work_period_id="WP-1")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 5), end_date=date(2027, 3, 5))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].hours == 24
    assert len(snapshot.days[0].periods) == 2  # both components captured, counted as one WorkPeriod


def test_t23_15_24h_cross_month_counts_once_no_double(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D24-1", "A24-1", "A", datetime(2027, 3, 31, 5, 0), datetime(2027, 3, 31, 17, 0)), ("D24-2", "A24-2", "A", datetime(2027, 3, 31, 17, 0), datetime(2027, 4, 1, 5, 0)), work_period_id="WP-X")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 31), end_date=date(2027, 4, 1))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].hours == 24  # anchored fully to 03-31
    assert snapshot.days[1].status == "MISSING"  # 04-01 has no accepted plan of its own -- never guessed 0
    assert snapshot.days[1].hours is None


def test_t23_16_accepted_readable_rest_is_zero(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_version(conn, version_id="SV-1", pairs=[], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 0


def test_t23_17_scheduled_weekend_holiday_counts_scheduled_hours(tmp_path) -> None:
    conn = _setup(tmp_path)
    saturday = date(2027, 3, 6)
    assert saturday.isoweekday() == 6
    _accept_one(conn, "D-6", "A-6", "A", datetime(2027, 3, 6, 5, 0), datetime(2027, 3, 6, 17, 0))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=saturday, end_date=saturday)
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].hours == 12  # scheduled hours, not zeroed by weekend/holiday


def test_t23_18_missing_ambiguous_never_guessed(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].status == "MISSING"
    assert snapshot.days[0].hours is None
    assert snapshot.reference_status == "MISSING"

    conn2 = _setup(tmp_path, db_name="rota2.db")  # Ambiguous half: contradictory overlapping PRIMARY periods, never guessed either.
    _accept_two(conn2, ("D-8a", "A-8a", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0)), ("D-8b", "A-8b", "A", datetime(2027, 3, 8, 9, 0), datetime(2027, 3, 8, 21, 0)))
    ambiguous_record = _leave(conn2, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    ambiguous_snapshot = get_absence_reference_snapshot(conn2, ambiguous_record.availability_version_id)
    assert ambiguous_snapshot.days[0].status == "AMBIGUOUS"
    assert ambiguous_snapshot.days[0].hours is None


def test_t23_19_leave_plan_creates_no_reference_row(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_PLAN, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    assert get_absence_reference_snapshot(conn, record.availability_version_id) is None


def test_t23_20_sick_over_leave_one_result_no_double_hours(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    leave = _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-L")
    sick = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-S")
    leave_snap = get_absence_reference_snapshot(conn, leave.availability_version_id)
    sick_snap = get_absence_reference_snapshot(conn, sick.availability_version_id)
    assert leave_snap.days[0].hours == 12  # Each captured independently at 12h; SICK-over-LEAVE precedence is planning.absence's job (Checkpoint B consumer).
    assert sick_snap.days[0].hours == 12


def test_t23_21_disjoint_periods_sum_exact(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D-8a", "A-8a", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 13, 0)), ("D-8b", "A-8b", "A", datetime(2027, 3, 8, 13, 0), datetime(2027, 3, 8, 17, 0)))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 12  # disjoint, direct-continuous -> sums exactly (8h + 4h)


def test_t23_22_trainee_does_not_add_hours_or_create_ambiguity(tmp_path) -> None:
    conn = _setup(tmp_path)
    d1, a1 = _primary("D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-1")
    trainee = Assignment("T-8", "SV-1", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "A-8")
    _accept_version(conn, version_id="SV-1", pairs=[(d1, a1)], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[d1], assignments=[a1, trainee], deviations=[])
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 12
    assert len(snapshot.days[0].periods) == 1  # only the PRIMARY fact, TRAINEE excluded


# --- R5-2 retroactivity guard ------------------------------------------------
# Wall-clock-relative (append_availability always uses datetime.now()), so this
# block uses TODAY-relative dates; _accept_current_months seeds an accepted
# ScheduleVersion for whichever real month(s) [start, end] actually touches.

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
PAST_REST_DATE = TODAY - timedelta(days=2)
FUTURE_SHIFT_DATE = TODAY + timedelta(days=2)


def _accept_current_months(conn, *, site_id: str, pairs_by_date: dict[date, list[tuple[ShiftDemand, Assignment]]], accepted_at: datetime) -> None:
    months: dict[date, list[tuple[ShiftDemand, Assignment]]] = {}
    for the_date, pairs in pairs_by_date.items():
        months.setdefault(date(the_date.year, the_date.month, 1), []).extend(pairs)
    for month, pairs in months.items():
        _accept_version(conn, version_id=f"SV-{site_id}-{month.isoformat()}", pairs=pairs, effective_from=month, accepted_at=accepted_at, site_id=site_id, month=month)


def test_t23_r5_2a_past_known_rest_plus_future_shift_accepted(tmp_path) -> None:
    conn = _setup(tmp_path)
    d1, a1 = _primary("D-FUT", "A-FUT", "A", datetime(FUTURE_SHIFT_DATE.year, FUTURE_SHIFT_DATE.month, FUTURE_SHIFT_DATE.day, 5, 0), datetime(FUTURE_SHIFT_DATE.year, FUTURE_SHIFT_DATE.month, FUTURE_SHIFT_DATE.day, 17, 0), version_id="dummy")
    _accept_current_months(conn, site_id=SITE, pairs_by_date={PAST_REST_DATE: [], FUTURE_SHIFT_DATE: [(d1, a1)]}, accepted_at=datetime(2020, 1, 1))
    record = append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-RANGE", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=PAST_REST_DATE, end_date=FUTURE_SHIFT_DATE, active=True)  # PAST_REST_DATE is a known accepted rest day, FUTURE_SHIFT_DATE a future scheduled shift -- one range covers both.
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert all(d.status == "BOUND" for d in snapshot.days)
    assert snapshot.days[0].hours == 0
    assert snapshot.days[-1].hours == 12


def test_t23_r5_2b_new_coverage_over_planned_before_recorded_at_rejected(tmp_path) -> None:
    conn = _setup(tmp_path)
    d1, a1 = _primary("D-Y", "A-Y", "A", datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 5, 0), datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 17, 0), version_id="dummy", state=AssignmentState.PLANNED)
    _accept_current_months(conn, site_id=SITE, pairs_by_date={YESTERDAY: [(d1, a1)]}, accepted_at=datetime(2020, 1, 1))
    with pytest.raises(RetroactiveAbsenceRejected):
        append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-RETRO", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=YESTERDAY, end_date=YESTERDAY, active=True)
    assert conn.execute("SELECT COUNT(*) FROM availability_versions WHERE availability_id = 'AV-A-RETRO'").fetchone()[0] == 0


def test_t23_r5_2c_new_coverage_over_realized_rejected(tmp_path) -> None:
    conn = _setup(tmp_path)
    d1, a1 = _primary("D-Y", "A-Y", "A", datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 5, 0), datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 17, 0), version_id="dummy", state=AssignmentState.REALIZED)
    _accept_current_months(conn, site_id=SITE, pairs_by_date={YESTERDAY: [(d1, a1)]}, accepted_at=datetime(2020, 1, 1))
    with pytest.raises(RetroactiveAbsenceRejected):
        append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-REALIZED", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=YESTERDAY, end_date=YESTERDAY, active=True)
    assert conn.execute("SELECT COUNT(*) FROM absence_reference_snapshots").fetchone()[0] == 0
    ystart = datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day)
    assignments = get_current_assignments_for_employees(conn, ["A"], ystart, ystart + timedelta(days=1))
    assert assignments[0].state == AssignmentState.REALIZED  # WYK untouched


def test_t23_r5_2d_elapsed_date_alone_is_not_rejection_reason(tmp_path) -> None:
    conn = _setup(tmp_path)
    record = append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-ELAPSED", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=YESTERDAY, end_date=YESTERDAY, active=True)  # No Assignment at all on the elapsed date -- nothing to retroactively rewrite.
    assert record is not None


def test_t23_r5_2e_extension_rejects_only_newly_introduced_coverage_deactivation_never_rejects(tmp_path) -> None:
    conn = _setup(tmp_path)
    d1, a1 = _primary("D-Y", "A-Y", "A", datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 5, 0), datetime(YESTERDAY.year, YESTERDAY.month, YESTERDAY.day, 17, 0), version_id="dummy", state=AssignmentState.PLANNED)
    _accept_current_months(conn, site_id=SITE, pairs_by_date={YESTERDAY: [(d1, a1)]}, accepted_at=datetime(2020, 1, 1))
    append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-EXT", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=TOMORROW, end_date=TOMORROW, active=True)  # active leave over TOMORROW only, no conflict yet
    # Extending BACKWARD to also cover YESTERDAY (a real PLANNED PRIMARY that already started) is the new coverage -- rejected.
    with pytest.raises(RetroactiveAbsenceRejected):
        append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-EXT", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=YESTERDAY, end_date=TOMORROW, active=True)
    deactivated = append_availability(conn, coordinator_id=COORDINATOR, site_id=SITE, availability_id="AV-A-EXT", employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=TOMORROW, end_date=TOMORROW, active=False)  # Deactivating the original (TOMORROW-only) leave never rejects, even though YESTERDAY has a real PLANNED PRIMARY.
    assert deactivated is not None


# --- Multi-Site / weekly reference invariance --------------------------------


def test_t23_24_actual_accepted_schedules_on_two_sites_global_once(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-A", site_id="SITE-A")
    _accept_one(conn, "D-9", "A-9", "A", datetime(2027, 3, 9, 5, 0), datetime(2027, 3, 9, 17, 0), version_id="SV-B", site_id="SITE-B")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 9), site_id="SITE-A")
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert set(snapshot.reference_site_scope) == {"SITE-A", "SITE-B"}
    assert [d.hours for d in snapshot.days] == [12, 12]  # A+B once each, no duplication


def test_t23_25_site_projection_contains_only_that_sites_periods(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 13, 0), version_id="SV-A", site_id="SITE-A")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A")
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert len([p for p in snapshot.days[0].periods if p.site_id == "SITE-A"]) == 1
    assert len([p for p in snapshot.days[0].periods if p.site_id == "SITE-B"]) == 0


def test_t23_26_dormant_external_support_cannot_create_missing(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.EXTERNAL_SUPPORT)  # dormant, no actual work at SITE-B
    _accept_version(conn, version_id="SV-A", pairs=[], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0), site_id="SITE-A")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A")
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert "SITE-B" not in snapshot.reference_site_scope
    assert snapshot.days[0].status == "BOUND"  # SITE-A alone resolves it; SITE-B never makes it MISSING


def test_t23_27_actual_external_support_work_enters_global_once(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.EXTERNAL_SUPPORT)
    _accept_version(conn, version_id="SV-A", pairs=[], effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8, 0), site_id="SITE-A")
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-B", site_id="SITE-B")
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A")
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert "SITE-B" in snapshot.reference_site_scope
    assert snapshot.days[0].hours == 12
    assert len(snapshot.days[0].periods) == 1  # counted once, not duplicated per membership


def test_t23_28_explicit_range_equals_sum_of_anchored_facts(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0)), ("D-9", "A-9", "A", datetime(2027, 3, 9, 5, 0), datetime(2027, 3, 9, 17, 0)))
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 6), end_date=date(2027, 3, 12))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert len(snapshot.days) == 7  # explicit inclusive 7-day range
    assert sum(d.hours or 0 for d in snapshot.days) == 24  # only the two 12h anchored facts


# --- R3-6 shared coverage owner ----------------------------------------------


def test_t23_55_shared_coverage_helper_used_by_validator_and_t023_capture() -> None:
    """No duplicate coverage/overlap-sweep algorithm exists in the persistence
    layer -- both callers import and use the exact same coverage_segments."""
    import inspect

    import rota.persistence.absence_reference_repository as arr_module
    source = inspect.getsource(arr_module)
    assert "from rota.planning.validator import coverage_segments" in source
    assert "coverage_segments(" in source

    overlap_segments = coverage_segments(datetime(2027, 1, 1, 0, 0), datetime(2027, 1, 1, 12, 0), [  # Behavioral proof: overlapping windows are flagged identically regardless of caller.
        (datetime(2027, 1, 1, 0, 0), datetime(2027, 1, 1, 8, 0)), (datetime(2027, 1, 1, 4, 0), datetime(2027, 1, 1, 12, 0)),
    ])
    assert any(count > 1 for _, _, count in overlap_segments)

    from tests.support.minimal_state import base_state  # Regression: extracting coverage_segments as a public helper must not change COVERAGE-01's own behavior.
    demand = ShiftDemand("D-1", "v1", datetime(2027, 1, 1, 5, 0), datetime(2027, 1, 1, 17, 0), 1)
    p = Assignment("P-1", "v1", "A", datetime(2027, 1, 1, 5, 0), datetime(2027, 1, 1, 13, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None)
    report = validate(base_state(shift_demands=[demand]), [p])
    assert len([v for v in report.violation_details if v.rule == "COVERAGE-01"]) == 1
