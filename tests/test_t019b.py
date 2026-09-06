"""ROTA-T019b (tasks/ROTA-T019b/brief.md): durable memory of material
coordinator actions + final DECISION_REQUIRED readback -- dedicated matrix.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import replace
from datetime import date, datetime, time

import pytest

from rota.application import lifecycle_ops, manual_edit, memory_read, plan_ops, training
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import (
    add_external_support_window,
    append_availability,
    set_calendar_day,
    set_target_hours,
    update_employee,
    update_membership,
    update_site,
    update_site_profile,
)
from rota.application.plan_ops import MissingCoordinatorActor
from rota.application.rule_decisions import record_structured_rule_decision
from rota.domain import (
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    Site,
    SiteMembership,
    SiteProfile,
    ShiftKind,
    StandardShift,
    SitePlanningRegime,
)
from rota.persistence import site_memory
from rota.persistence.availability_repository import get_availability_history
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import LATEST_SCHEMA_VERSION, MIGRATIONS, connect
from rota.persistence.employee_repository import EmployeeNotFound, get_employee
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.site_memory_types import CoordinatorActionKind, NewRuleContent

SITE = "S1"
PROFILE = "P1"
COORD = "C1"
MONTH = date(2026, 8, 1)

def _profile() -> SiteProfile:
    return SiteProfile(
        PROFILE, PROFILE, True, [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        False, False, False, False, 1, 999,
    )

def _bootstrap(conn, *, site_id: str = SITE) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id,
        coordinator=Coordinator(COORD, "Coord", True), site_profile=_profile(),
        site=Site(site_id, PROFILE, site_id, True, planning_regime=SitePlanningRegime.ORDINARY), association=CoordinatorSiteAssociation(COORD, site_id, True),
    )

def _employee(conn, employee_id: str = "E1", *, site_id: str = SITE, day_only: bool = False) -> None:
    update_employee(conn, coordinator_id=COORD, site_id=site_id, employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only))
    update_membership(
        conn, coordinator_id=COORD, site_id=site_id,
        membership=SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )

def _fill_calendar(conn, month: date = MONTH) -> None:
    for d in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, d), False))

def _block_employee(conn, employee_id: str = "E1", *, site_id: str = SITE) -> None:
    append_availability(
        conn, coordinator_id=COORD, site_id=site_id, availability_id=f"AV-{employee_id}", employee_id=employee_id,
        kind=AvailabilityKind.UNAVAILABLE_24H, start_date=date(2026, 8, 1), end_date=date(2026, 8, 31), active=True,
    )

def _unblock_employee(conn, employee_id: str = "E1", *, site_id: str = SITE) -> None:
    append_availability(
        conn, coordinator_id=COORD, site_id=site_id, availability_id=f"AV-{employee_id}", employee_id=employee_id,
        kind=AvailabilityKind.UNAVAILABLE_24H, start_date=date(2026, 8, 1), end_date=date(2026, 8, 31), active=False,
    )

def _seed_decision_required(conn) -> None:
    _bootstrap(conn)
    _employee(conn)
    _fill_calendar(conn)
    _block_employee(conn)

def _seed_feasible_and_select(conn):
    _bootstrap(conn)
    _employee(conn)
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)

# ---------------------------------------------------------------------------
# A. Schema / append-only / restart
# ---------------------------------------------------------------------------

def test_a1_real_v5_to_latest_migration_preserves_data_and_adds_expected_tables(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    legacy = sqlite3.connect(db_path)
    for version, statements in MIGRATIONS:
        if version > 5:
            break
        legacy.execute("BEGIN")
        for statement in statements:
            legacy.execute(statement)
        legacy.execute(f"PRAGMA user_version = {version}")
        legacy.execute("COMMIT")
    legacy.execute("INSERT INTO calendar_days (date, holiday) VALUES ('2026-08-03', 1)")
    legacy.commit()
    tables_before = {r[0] for r in legacy.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    legacy.close()

    conn = connect(db_path)
    tables_after = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION == 17
    assert conn.execute("SELECT holiday FROM calendar_days WHERE date='2026-08-03'").fetchone() == (1,)
    assert tables_after - tables_before == {
        "coordinator_action_records", "decision_required_snapshots", "current_decision_required", "site_print_settings",
        "absence_reference_snapshots", "plan_previews", "site_monthly_extra_work_codes", "plan_attempt_signatures",
    }

def test_a2_a5_action_and_snapshot_update_delete_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    action_id = memory_read.material_action_history(conn)[0].action_id
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    for sql in (
        "UPDATE coordinator_action_records SET note='x' WHERE action_id=?",
        "DELETE FROM coordinator_action_records WHERE action_id=?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (action_id,))
    for sql in (
        "UPDATE decision_required_snapshots SET requested_by='X' WHERE decision_required_id=?",
        "DELETE FROM decision_required_snapshots WHERE decision_required_id=?",
    ):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (dr_id,))

def test_a6_current_pointer_may_replace_and_clear(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is not None
    _unblock_employee(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None

def test_a7_restart_preserves_history_and_links(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100, responds_to_decision_required_id=dr_id)
    before = memory_read.material_action_history(conn)
    conn.close()

    reopened = connect(db_path)
    after = memory_read.material_action_history(reopened)
    assert before == after
    assert any(a.responds_to_decision_required_id == dr_id for a in after)

# ---------------------------------------------------------------------------
# B. Current-state material history
# ---------------------------------------------------------------------------

def test_b8_day_only_records_actor_time_before_after_note(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, day_only=False)
    before_count = len(memory_read.material_action_history(conn))
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True), note="  requested by employee  ")
    actions = memory_read.material_action_history(conn)
    assert len(actions) == before_count + 1
    a = actions[0]
    assert a.action_kind == CoordinatorActionKind.EMPLOYEE_DAY_ONLY_CHANGED
    assert a.coordinator_id == COORD and a.note == "requested by employee"
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail.before_state == {"employee_id": "E1", "day_only": False}
    assert detail.after_state == {"employee_id": "E1", "day_only": True}

def test_b9_display_name_only_change_no_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, day_only=False)
    before_count = len(memory_read.material_action_history(conn))
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "Renamed", date(2020, 1, 1), None, False))
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "Renamed", date(2099, 1, 1), None, False))
    assert len(memory_read.material_action_history(conn)) == before_count

def test_b10_membership_change_records_before_after(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    update_membership(conn, coordinator_id=COORD, site_id=SITE, membership=SiteMembership("E1", SITE, MembershipKind.LOCAL, False, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.SITE_MEMBERSHIP_CHANGED]
    assert len(actions) == 2
    detail = memory_read.material_action_detail(conn, action_id=actions[0].action_id)
    assert detail.before_state["enabled"] is True and detail.after_state["enabled"] is False

def test_b11_target_records_old_new_and_effective_from_is_month(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=120)
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.TARGET_HOURS_CHANGED and a.effective_from == MONTH
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail.before_state["target_hours"] == 100 and detail.after_state["target_hours"] == 120

def test_b12_calendar_day_records_old_new_and_global_sites(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _bootstrap(conn, site_id="S2")
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(2026, 8, 15), False))
    set_calendar_day(conn, coordinator_id=COORD, site_id=SITE, day=CalendarDay(date(2026, 8, 15), True))
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.CALENDAR_DAY_CHANGED
    assert set(a.affected_site_ids) == {SITE, "S2"}

def test_b13_profile_catalog_change_records_before_after_display_name_no_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    before_count = len(memory_read.material_action_history(conn))
    renamed = SiteProfile(PROFILE, "Renamed", True, _profile().standard_shifts, False, False, False, False, 1, 999)
    update_site_profile(conn, coordinator_id=COORD, site_id=SITE, profile=renamed)
    assert len(memory_read.material_action_history(conn)) == before_count

    changed = SiteProfile(PROFILE, "Renamed", True, [StandardShift(ShiftKind.D, time(7, 0), time(19, 0), False, 1)], False, False, False, False, 1, 999)
    update_site_profile(conn, coordinator_id=COORD, site_id=SITE, profile=changed)
    actions = memory_read.material_action_history(conn)
    assert actions[0].action_kind == CoordinatorActionKind.SITE_PROFILE_CHANGED
    assert len(actions) == before_count + 1

def test_b14_site_active_change_records_display_name_no_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    before_count = len(memory_read.material_action_history(conn))
    update_site(conn, coordinator_id=COORD, site_id=SITE, site=Site(SITE, PROFILE, "Renamed", True, planning_regime=SitePlanningRegime.ORDINARY))
    assert len(memory_read.material_action_history(conn)) == before_count
    update_site(conn, coordinator_id=COORD, site_id=SITE, site=Site(SITE, PROFILE, "Renamed", False, planning_regime=SitePlanningRegime.ORDINARY))
    actions = memory_read.material_action_history(conn)
    assert actions[0].action_kind == CoordinatorActionKind.SITE_ACTIVE_CHANGED

def test_b15_external_support_window_records_before_after_and_date_range(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    window = ExternalSupportWindow("WIN-1", "E1", SITE, datetime(2026, 8, 1), datetime(2026, 8, 10), True, None)
    add_external_support_window(conn, coordinator_id=COORD, site_id=SITE, window=window)
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.EXTERNAL_SUPPORT_WINDOW_CHANGED
    assert a.effective_from == date(2026, 8, 1)

def test_b16_availability_append_records_one_action_chain_intact(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _block_employee(conn)
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.AVAILABILITY_CHANGED
    assert len(get_availability_history(conn, "AV-E1")) == 1

def test_b17_noop_current_state_value_produces_no_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, day_only=True)
    before_count = len(memory_read.material_action_history(conn))
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True))
    assert len(memory_read.material_action_history(conn)) == before_count

# ---------------------------------------------------------------------------
# C. Existing histories / one logical action
# ---------------------------------------------------------------------------

def _rule_content() -> NewRuleContent:
    return NewRuleContent(
        category=RuleCategory.LOCAL_RULE, rule_kind="CUSTOM", structured_parameters=None,
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_to=None, description="d", source=None, reason=None,
    )

def test_c18_structured_rule_decision_one_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE, rule_id="RULE-1", statement="s",
        effective_from=date(2026, 8, 1), rule_content=_rule_content(),
    )
    actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.RULE_DECISION_RECORDED]
    assert len(actions) == 1
    assert conn.execute("SELECT COUNT(*) FROM decision_records").fetchone()[0] == 1

def test_c19_rest_override_side_effect_no_second_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    sel = _seed_feasible_and_select(conn)
    snap = get_schedule_snapshot(conn, sel.version_id)
    target = snap.assignments[0]
    corrected = replace(target, start_datetime=target.start_datetime.replace(hour=0), end_datetime=target.start_datetime.replace(hour=23))
    manual_edit.apply_manual_correction(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, upsert_assignments=[corrected],
    )
    manual_actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION]
    assert len(manual_actions) == 1

def test_c20_generic_manual_correction_one_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    sel = _seed_feasible_and_select(conn)
    snap = get_schedule_snapshot(conn, sel.version_id)
    target = snap.assignments[0]
    updated = replace(target, frozen=True)
    manual_edit.apply_manual_correction(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, upsert_assignments=[updated])
    actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION]
    assert len(actions) == 1

@pytest.mark.parametrize("mode", ["freeze", "nn"])
def test_c21_c22_freeze_and_nn_one_action_each(tmp_path, mode) -> None:
    conn = connect(tmp_path / "rota.db")
    sel = _seed_feasible_and_select(conn)
    snap = get_schedule_snapshot(conn, sel.version_id)
    if mode == "freeze":
        target = snap.assignments[0]
        manual_edit.freeze_or_unfreeze(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, assignment_id=target.assignment_id, frozen=True)
        expected = CoordinatorActionKind.ASSIGNMENT_FREEZE_CHANGED
    else:
        target = next(a for a in snap.assignments if a.state == AssignmentState.PLANNED)
        manual_edit.mark_not_worked(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, assignment_id=target.assignment_id)
        expected = CoordinatorActionKind.ASSIGNMENT_NOT_WORKED
    kinds = [a.action_kind for a in memory_read.material_action_history(conn)]
    assert kinds[0] == expected
    assert CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION not in kinds

def _build_trainee(primary, trainee_employee_id: str):
    return replace(
        primary, assignment_id=f"AS-{uuid.uuid4().hex}", employee_id=trainee_employee_id,
        role=AssignmentRole.TRAINEE, state=AssignmentState.REALIZED,
        mentor_primary_assignment_id=primary.assignment_id, covers_demand_id=None,
        work_period_id=None, required_rest_after_hours=None,
    )

def test_c23_training_realized_one_action_with_readiness(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1")
    _employee(conn, "E2")
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    sel = plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)
    snap = get_schedule_snapshot(conn, sel.version_id)
    primary = next(a for a in snap.assignments if a.role == AssignmentRole.PRIMARY)
    trainee_employee_id = "E2" if primary.employee_id != "E2" else "E1"
    trainee = _build_trainee(primary, trainee_employee_id)
    training.mark_training_realized(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, trainee_assignment=trainee)
    actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.TRAINING_REALIZED]
    assert len(actions) == 1
    assert not any(a.action_kind == CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION for a in memory_read.material_action_history(conn))

def test_c24_finalize_n_deviations_one_action(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    sel = _seed_feasible_and_select(conn)
    target = get_schedule_snapshot(conn, sel.version_id).assignments[0]
    manual_edit.mark_not_worked(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, assignment_id=target.assignment_id)
    current = get_current_version_id(conn, SITE, MONTH)
    dev_ids = {d.deviation_id for d in get_schedule_snapshot(conn, current).deviations}
    lifecycle_ops.finalize(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, acknowledged_deviation_ids=dev_ids)
    finalized = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.SCHEDULE_FINALIZED]
    assert len(finalized) == 1

def test_c25_restore_one_action_with_pointer_before_after(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    sel = _seed_feasible_and_select(conn)
    target = get_schedule_snapshot(conn, sel.version_id).assignments[0]
    v2 = manual_edit.freeze_or_unfreeze(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, assignment_id=target.assignment_id, frozen=True)
    lifecycle_ops.restore(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, version_id=sel.version_id)
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.SCHEDULE_RESTORED
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail.before_state == {"current_version_id": v2.version_id}
    assert detail.after_state == {"current_version_id": sel.version_id}

def test_c26_przelicz_plan_accept_one_action(tmp_path) -> None:
    """ROTA-T057 (BOARD.md OWNER_RULING 2026-09-06): REPLAN no longer exists
    once anything has been accepted, and no longer creates a ScheduleVersion
    of its own (SCHEDULE_REPLAN_CREATED is dead). Przelicz Plan (plan_month
    on the existing current) followed by select_candidate is the recompute
    now, and records exactly one SCHEDULE_CANDIDATE_SELECTED action for the
    new child -- same mechanism as the very first acceptance."""
    conn = connect(tmp_path / "rota.db")
    _seed_feasible_and_select(conn)
    recomputed = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD)
    assert recomputed.status == "FEASIBLE"
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=recomputed.candidates[0], coordinator_id=COORD)
    actions = [a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED]
    assert len(actions) == 2  # first-ever accept + this Przelicz Plan accept

def test_c27_candidate_selection_one_action_delta_only(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)
    a = memory_read.material_action_history(conn)[0]
    assert a.action_kind == CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert set(detail.after_state.keys()) == {"added", "changed"}

# ---------------------------------------------------------------------------
# D. Actor / dates / notes
# ---------------------------------------------------------------------------

def test_d28_select_candidate_without_actor_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    before_count = len(memory_read.material_action_history(conn))
    with pytest.raises(MissingCoordinatorActor):
        plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=None)
    assert len(memory_read.material_action_history(conn)) == before_count
    # ROTA-T057 (T57-01): rejected before anything is created -- no
    # ScheduleVersion exists at all, PLAN never created one either.
    assert get_current_version_id(conn, SITE, MONTH) is None

def test_d29_candidate_selection_records_actual_actor(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
    save_coordinator(conn, Coordinator("C2", "Second", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("C2", SITE, True))
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id="C2")
    a = memory_read.material_action_history(conn)[0]
    assert a.coordinator_id == "C2"

def test_d30_31_note_none_and_roundtrip(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100)
    assert memory_read.material_action_history(conn)[0].note is None
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=110, note="  coordinator note  ")
    assert memory_read.material_action_history(conn)[0].note == "coordinator note"

def test_d32_current_state_never_claims_future_effective(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    a = memory_read.material_action_history(conn)[0]
    assert a.effective_from == datetime.now().date()

def test_d33_rule_availability_target_preserve_existing_effective_dates(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100)
    assert memory_read.material_action_history(conn)[0].effective_from == MONTH
    _block_employee(conn)
    assert memory_read.material_action_history(conn)[0].effective_from == date(2026, 8, 1)

# ---------------------------------------------------------------------------
# E. Final DECISION_REQUIRED readback
# ---------------------------------------------------------------------------

def test_e34_dr_survives_restart_exact_payload(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_decision_required(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    conn.close()
    reopened = connect(db_path)
    readback = memory_read.current_decision_required(reopened, site_id=SITE, month=MONTH)
    assert readback is not None
    assert readback.payload == result.decision_payload

def test_e35_repeated_identical_plan_reuses_snapshot(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    id1 = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    id2 = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    assert id1 == id2
    assert conn.execute("SELECT COUNT(*) FROM decision_required_snapshots").fetchone()[0] == 1

def test_e36_changed_dr_creates_new_snapshot(tmp_path) -> None:
    """Both employees stay HARD-blocked throughout (DECISION_REQUIRED never
    lifts), but E2's blocking reason changes -- a genuinely different
    rendered payload, not just a re-run of the same question."""
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    _employee(conn, "E2")
    _block_employee(conn, "E2")
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    id1 = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-E2", employee_id="E2",
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 8, 1), end_date=date(2026, 8, 31), active=True,
    )
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "DECISION_REQUIRED"
    id2 = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    assert id1 != id2
    assert conn.execute("SELECT COUNT(*) FROM decision_required_snapshots").fetchone()[0] == 2

def test_e37_feasible_clears_pointer_not_snapshots(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    _unblock_employee(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    assert conn.execute("SELECT COUNT(*) FROM decision_required_snapshots").fetchone()[0] == 1

def test_e38_technical_error_preserves_previous_pointer(tmp_path, monkeypatch) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    before_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id

    def _boom(state, **kwargs):
        from rota.planning.engine_types import PlanningResult
        return PlanningResult(status="TECHNICAL_ERROR", candidates=[], decision_payload=None, error_message="injected", warnings=[])

    monkeypatch.setattr("rota.application.plan_ops.plan", _boom)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "TECHNICAL_ERROR"
    after_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    assert after_id == before_id

def test_e39_no_intermediate_retry_state_stored(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    readback = memory_read.current_decision_required(conn, site_id=SITE, month=MONTH)
    assert readback.payload.blockers and all(b.employee_id for b in readback.payload.blockers)

@pytest.mark.parametrize("target", ["reuse_or_insert_decision_required_snapshot_no_commit", "clear_current_decision_required_no_commit"])
def test_e40_e41_persist_failure_fails_closed(tmp_path, monkeypatch, target) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    if target == "clear_current_decision_required_no_commit":
        plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
        _unblock_employee(conn)
    monkeypatch.setattr(
        f"rota.application.plan_ops.site_memory.{target}",
        lambda *a, **kw: (_ for _ in ()).throw(sqlite3.OperationalError("injected")),
    )
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "TECHNICAL_ERROR" and result.candidates == [] and result.decision_payload is None

# ---------------------------------------------------------------------------
# F. Explicit link / staleness
# ---------------------------------------------------------------------------

def test_f42_action_without_link_stays_unlinked(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=date(2026, 9, 1), target_hours=100)
    a = memory_read.material_action_history(conn)[0]
    assert a.responds_to_decision_required_id is None

def test_f43_explicit_link_succeeds_and_detail_shows_historical_question(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    # A September target does not overlap/invalidate the August question.
    set_target_hours(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=date(2026, 9, 1), target_hours=100,
        responds_to_decision_required_id=dr_id,
    )
    a = next(a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.TARGET_HOURS_CHANGED)
    assert a.responds_to_decision_required_id == dr_id
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is not None
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail.responds_to is not None and detail.responds_to.decision_required_id == dr_id

    # now resolve it for real -- pointer clears, but detail still resolves the historical snapshot.
    _unblock_employee(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "FEASIBLE"
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    detail_after = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail_after.responds_to is not None and detail_after.responds_to.decision_required_id == dr_id

def test_f44_link_to_unknown_or_wrong_site_fails_before_mutation(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    before = memory_read.material_action_history(conn)
    with pytest.raises(site_memory.UnknownDecisionRequiredSnapshot):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=999, responds_to_decision_required_id="DR-nope")
    assert memory_read.material_action_history(conn) == before

    _bootstrap(conn, site_id="S2")
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    with pytest.raises(site_memory.DecisionRequiredLinkMismatch):
        set_target_hours(conn, coordinator_id=COORD, site_id="S2", employee_id="E1", month=MONTH, target_hours=999, responds_to_decision_required_id=dr_id)

    # known, but no longer current (superseded by a later FEASIBLE plan)
    old_dr_id = dr_id
    _unblock_employee(conn)
    feasible = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert feasible.status == "FEASIBLE"
    with pytest.raises(site_memory.DecisionRequiredLinkMismatch):
        set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=999, responds_to_decision_required_id=old_dr_id)

def test_f45_material_action_invalidates_without_claiming_solved(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100)
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    a = memory_read.material_action_history(conn)[0]
    assert a.responds_to_decision_required_id is None  # invalidation is not an inferred link

def test_f46_target_invalidates_only_affected_month(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    site_memory.set_current_decision_required_no_commit(conn, site_id=SITE, month=date(2026, 9, 1), decision_required_id=site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id)
    conn.commit()
    set_target_hours(conn, coordinator_id=COORD, site_id=SITE, employee_id="E1", month=MONTH, target_hours=100)
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=date(2026, 9, 1)) is not None

def test_f47_availability_invalidates_overlapped_months(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    site_memory.set_current_decision_required_no_commit(conn, site_id=SITE, month=date(2026, 9, 1), decision_required_id=dr_id)
    conn.commit()
    # ROTA-T023 A-R9-1: workday_holiday_map's completeness check is
    # MONTH-granular, not range-granular -- seed both full months touched.
    for d in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(2026, 8, d), False))
    for d in range(1, 31):
        save_calendar_day(conn, CalendarDay(date(2026, 9, d), False))
    append_availability(
        conn, coordinator_id=COORD, site_id=SITE, availability_id="AV-SPAN", employee_id="E1",
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2026, 8, 20), end_date=date(2026, 9, 5), active=True,
    )
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=date(2026, 9, 1)) is None

def test_f48_global_employee_or_profile_change_invalidates_all_affected_sites(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    site_memory.set_current_decision_required_no_commit(conn, site_id=SITE, month=date(2027, 1, 1), decision_required_id=dr_id)
    conn.commit()
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True))
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=date(2027, 1, 1)) is None

def test_f49_rule_decision_invalidates_only_intersecting_months(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    dr_id = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH).decision_required_id
    site_memory.set_current_decision_required_no_commit(conn, site_id=SITE, month=date(2027, 1, 1), decision_required_id=dr_id)
    conn.commit()
    limited = NewRuleContent(
        category=RuleCategory.LOCAL_RULE, rule_kind="CUSTOM", structured_parameters=None,
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_to=date(2026, 8, 31), description=None, source=None, reason=None,
    )
    record_structured_rule_decision(conn, coordinator_id=COORD, site_id=SITE, rule_id="R1", statement="s", effective_from=date(2026, 8, 1), rule_content=limited)
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH) is None
    assert site_memory.get_current_decision_required(conn, site_id=SITE, month=date(2027, 1, 1)) is not None

# ---------------------------------------------------------------------------
# G. Atomicity (fault injection: action insert must roll back the domain write)
# ---------------------------------------------------------------------------

def _boom_action_insert(monkeypatch, target: str) -> None:
    monkeypatch.setattr(target, lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("injected")))


def test_g50_52_current_state_and_rule_rollback(tmp_path, monkeypatch) -> None:
    """One scenario per MATERIAL command family: injecting a failure into
    the action-index insert must roll back the paired domain write too --
    history must never lag a successful human write (section 13)."""
    durable_target = "rota.application.durable_inputs.site_memory.record_coordinator_action_no_commit"

    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, durable_target)
        update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True))
    with pytest.raises(EmployeeNotFound):
        get_employee(conn, "E1")

    conn = connect(tmp_path / "rota2.db")
    _bootstrap(conn)
    _employee(conn)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, durable_target)
        _block_employee(conn)
    assert get_availability_history(conn, "AV-E1") == []

    conn = connect(tmp_path / "rota3.db")
    _bootstrap(conn)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.rule_decisions.site_memory.record_coordinator_action_no_commit")
        record_structured_rule_decision(conn, coordinator_id=COORD, site_id=SITE, rule_id="R1", statement="s", effective_from=date(2026, 8, 1), rule_content=_rule_content())
    assert conn.execute("SELECT COUNT(*) FROM decision_records").fetchone()[0] == 0


def test_g53_54_candidate_and_manual_child_rollback(tmp_path, monkeypatch) -> None:
    conn = connect(tmp_path / "rota4.db")
    sel = _seed_feasible_and_select(conn)
    target = get_schedule_snapshot(conn, sel.version_id).assignments[0]
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.manual_edit.site_memory.record_coordinator_action_no_commit")
        manual_edit.apply_manual_correction(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, upsert_assignments=[replace(target, frozen=True)])
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions WHERE site_id=?", (SITE,)).fetchone()[0] == 1

    conn = connect(tmp_path / "rota9.db")
    _bootstrap(conn)
    _employee(conn)
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    # ROTA-T057 (T57-01): PLAN alone creates no ScheduleVersion -- this is
    # now the "first-ever acceptance" rollback path (_select_first_candidate_hook).
    assert get_current_version_id(conn, SITE, MONTH) is None
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.plan_ops.site_memory.record_coordinator_action_no_commit")
        plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)
    assert get_current_version_id(conn, SITE, MONTH) is None  # atomic rollback: still no version at all


def test_g55_58_training_finalize_restore_replan_rollback(tmp_path, monkeypatch) -> None:
    conn = connect(tmp_path / "rota5.db")
    _bootstrap(conn)
    _employee(conn, "E1")
    _employee(conn, "E2")
    _fill_calendar(conn)
    result = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    sel = plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)
    version_count_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    primary = next(a for a in get_schedule_snapshot(conn, sel.version_id).assignments if a.role == AssignmentRole.PRIMARY)
    trainee = _build_trainee(primary, "E2" if primary.employee_id != "E2" else "E1")
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.manual_edit.site_memory.record_coordinator_action_no_commit")
        training.mark_training_realized(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, trainee_assignment=trainee)
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == version_count_before

    conn = connect(tmp_path / "rota6.db")
    sel = _seed_feasible_and_select(conn)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.lifecycle_ops.site_memory.record_coordinator_action_no_commit")
        lifecycle_ops.finalize(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, acknowledged_deviation_ids=set())
    from rota.persistence.schedule_repository import get_schedule_version_header
    assert get_schedule_version_header(conn, sel.version_id).status.value == "WORKING"

    conn = connect(tmp_path / "rota7.db")
    sel = _seed_feasible_and_select(conn)
    target = get_schedule_snapshot(conn, sel.version_id).assignments[0]
    v2 = manual_edit.freeze_or_unfreeze(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH, assignment_id=target.assignment_id, frozen=True)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.lifecycle_ops.site_memory.record_coordinator_action_no_commit")
        lifecycle_ops.restore(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, version_id=sel.version_id)
    assert get_current_version_id(conn, SITE, MONTH) == v2.version_id

    # ROTA-T057 (BOARD.md OWNER_RULING 2026-09-06): REPLAN no longer exists
    # once anything has been accepted -- Przelicz Plan (plan_month +
    # select_candidate) is the recompute now, and its acceptance must roll
    # back atomically the same way every other accept path here does.
    conn = connect(tmp_path / "rota8.db")
    sel = _seed_feasible_and_select(conn)
    count_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    recomputed = plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD)
    with monkeypatch.context() as mp, pytest.raises(RuntimeError):
        _boom_action_insert(mp, "rota.application.plan_ops.site_memory.record_coordinator_action_no_commit")
        plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=recomputed.candidates[0], coordinator_id=COORD)
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == count_before
    assert get_current_version_id(conn, SITE, MONTH) == sel.version_id

# ---------------------------------------------------------------------------
# H. Read API / filters / determinism
# ---------------------------------------------------------------------------

def test_h59_history_sorted_newest_first(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn, "E1")
    _employee(conn, "E2")
    actions = memory_read.material_action_history(conn)
    assert list(actions) == sorted(actions, key=lambda a: (a.recorded_at, a.action_id), reverse=True)

def test_h60_site_filter_by_affected_site_ids_no_storage_duplication(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _bootstrap(conn, site_id="S2")
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, False))
    update_membership(conn, coordinator_id=COORD, site_id=SITE, membership=SiteMembership("E1", SITE, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    update_membership(conn, coordinator_id=COORD, site_id="S2", membership=SiteMembership("E1", "S2", MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT))
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True))
    # exactly one storage row for the day_only flip itself (the earlier
    # creation call is a separate, distinct action) -- never duplicated per
    # affected Site even though E1 has enabled LOCAL membership on both.
    total = conn.execute(
        "SELECT COUNT(*) FROM coordinator_action_records WHERE action_kind='EMPLOYEE_DAY_ONLY_CHANGED' AND after_state_json LIKE '%true%'"
    ).fetchone()[0]
    assert total == 1
    flip = next(a for a in memory_read.material_action_history(conn) if a.action_kind == CoordinatorActionKind.EMPLOYEE_DAY_ONLY_CHANGED)
    assert set(flip.affected_site_ids) == {SITE, "S2"}
    assert flip in memory_read.material_action_history(conn, site_id=SITE)
    assert flip in memory_read.material_action_history(conn, site_id="S2")

def test_h61_entity_filter_requires_pair(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    with pytest.raises(ValueError):
        memory_read.material_action_history(conn, affected_entity_kind="EMPLOYEE")
    matches = memory_read.material_action_history(conn, affected_entity_kind="EMPLOYEE", affected_entity_id="E1")
    assert all(any(e.entity_kind == "EMPLOYEE" and e.entity_id == "E1" for e in a.affected_entities) for a in matches)

def test_h62_action_kind_filter(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    matches = memory_read.material_action_history(conn, action_kind=CoordinatorActionKind.EMPLOYEE_DAY_ONLY_CHANGED)
    assert matches and all(a.action_kind == CoordinatorActionKind.EMPLOYEE_DAY_ONLY_CHANGED for a in matches)

def test_h63_coordinator_filter(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    assert memory_read.material_action_history(conn, coordinator_id=COORD)
    assert memory_read.material_action_history(conn, coordinator_id="NOBODY") == ()

def test_h64_inclusive_recorded_range(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    a = memory_read.material_action_history(conn)[0]
    assert memory_read.material_action_history(conn, recorded_from=a.recorded_at, recorded_to=a.recorded_at)

def test_h65_detail_returns_before_after_source_note_link(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    update_employee(conn, coordinator_id=COORD, site_id=SITE, employee=Employee("E1", "E1", date(2020, 1, 1), None, True), note="x")
    a = memory_read.material_action_history(conn)[0]
    detail = memory_read.material_action_detail(conn, action_id=a.action_id)
    assert detail.before_state is not None and detail.after_state is not None and detail.note == "x"
    assert detail.source_kind and detail.source_id

def test_h66_unknown_action_id_raises(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    with pytest.raises(site_memory.CoordinatorActionNotFound):
        memory_read.material_action_detail(conn, action_id="ACT-nope")

def test_h67_current_decision_required_validates_first_day(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    with pytest.raises(ValueError):
        memory_read.current_decision_required(conn, site_id=SITE, month=date(2026, 8, 15))

def test_h68_no_raw_historical_question_list_api() -> None:
    assert not hasattr(memory_read, "list_decision_required_snapshots")
    assert not hasattr(memory_read, "all_decision_required")

# ---------------------------------------------------------------------------
# I. Non-regression spot checks (full suite carries the rest)
# ---------------------------------------------------------------------------

def test_i77_planning_module_has_no_persistence_import() -> None:
    import ast
    import pathlib
    for path in pathlib.Path("rota/planning").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "persistence" not in node.module, f"{path}: {node.module}"
                assert "site_memory" not in node.module, f"{path}: {node.module}"

def test_i78_action_and_dr_tables_absent_from_planning_state_assembly(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_decision_required(conn)
    plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    from rota.application.assembler import assemble_planning_state
    queries = []
    conn.set_trace_callback(lambda sql: queries.append(sql))
    assemble_planning_state(conn, site_id=SITE, month=MONTH)
    conn.set_trace_callback(None)
    memory_tables = ("coordinator_action_records", "decision_required_snapshots", "current_decision_required")
    assert not any(table in sql for sql in queries for table in memory_tables)
