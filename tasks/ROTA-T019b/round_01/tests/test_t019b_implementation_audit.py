"""Independent final implementation probes for ROTA-T019b."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time
import sqlite3

import pytest

import rota.application.bootstrap as bootstrap_module
from rota.application import lifecycle_ops, manual_edit, memory_read, plan_ops, training
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import (
    add_external_support_window,
    append_availability,
    set_target_hours,
    update_employee,
    update_membership,
)
from rota.application.errors import CoordinatorContextAlreadyActive
from rota.application.rule_decisions import record_structured_rule_decision
from rota.domain import (
    AvailabilityKind,
    AssignmentRole,
    AssignmentState,
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
    ShiftCatalogKind,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import MIGRATIONS, connect
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.persistence.work_balance_repository import get_work_balance_target
from rota.persistence import site_memory
from rota.site_memory_types import CoordinatorActionKind, NewRuleContent


SITE = "AUDIT-S1"
PROFILE = "AUDIT-P1"
COORD = "AUDIT-C1"
MONTH = date(2026, 8, 1)


def _profile(*, complete_catalog: bool = False) -> SiteProfile:
    shift = StandardShift(
        ShiftKind.D,
        time(6),
        time(18),
        False,
        1,
        catalog_kind=ShiftCatalogKind.H12 if complete_catalog else None,
        required_rest_hours=23 if complete_catalog else 11,
        active_weekdays=(1, 3, 5) if complete_catalog else (1, 2, 3, 4, 5, 6, 7),
    )
    return SiteProfile(PROFILE, "Profile", True, [shift], False, False, False, False, 1, 999)


def _bootstrap(conn, *, profile: SiteProfile | None = None) -> None:
    bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        coordinator=Coordinator(COORD, "Coordinator", True),
        site_profile=profile or _profile(),
        site=Site(SITE, PROFILE, "Site", True),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )


def _employee(conn) -> None:
    update_employee(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        employee=Employee("E1", "Employee", date(2020, 1, 1), None, False),
    )
    update_membership(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        membership=SiteMembership(
            "E1", SITE, MembershipKind.LOCAL, True,
            ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        ),
    )


def _calendar(conn) -> None:
    for day in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(2026, 8, day), False))


def test_noop_external_support_window_creates_no_action_or_invalidation(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    window = ExternalSupportWindow(
        "W1", "E1", SITE, datetime(2026, 8, 2), datetime(2026, 8, 5), True, None,
    )
    add_external_support_window(conn, coordinator_id=COORD, site_id=SITE, window=window)
    _calendar(conn)
    append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        active=True,
    )
    result = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    assert result.status == "DECISION_REQUIRED"
    pointer_before = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH)
    action_count_before = len(memory_read.material_action_history(conn))

    add_external_support_window(conn, coordinator_id=COORD, site_id=SITE, window=window)

    observed = (
        len(memory_read.material_action_history(conn)),
        site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH),
    )
    assert observed == (action_count_before, pointer_before)


def test_bootstrap_failure_rolls_back_all_supplied_pieces_and_action(tmp_path, monkeypatch) -> None:
    conn = connect(tmp_path / "rota.db")
    monkeypatch.setattr(
        bootstrap_module,
        "activate_association_if_not_already_active_in_open_transaction",
        lambda *_args, **_kwargs: False,
    )

    with pytest.raises(CoordinatorContextAlreadyActive):
        _bootstrap(conn)

    observed_counts = tuple(
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("coordinators", "site_profiles", "sites", "coordinator_action_records")
    )
    assert observed_counts == (0, 0, 0, 0)


def test_bootstrap_snapshot_contains_complete_standard_shift_catalog(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn, profile=_profile(complete_catalog=True))
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.CONTEXT_CONFIGURATION_SAVED
    )
    shift = memory_read.material_action_detail(conn, action_id=action.action_id).after_state["site_profile"]["standard_shifts"][0]

    assert shift["catalog_kind"] == ShiftCatalogKind.H12.value
    assert shift["required_rest_hours"] == 23
    assert shift["active_weekdays"] == [1, 3, 5]


def test_rule_action_snapshot_contains_new_rule_content(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    content = NewRuleContent(
        category=RuleCategory.LOCAL_RULE,
        rule_kind="CUSTOM",
        structured_parameters={"limit": 7},
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_to=date(2026, 8, 31),
        description="description",
        source="source",
        reason="reason",
    )
    record_structured_rule_decision(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id="RULE-1",
        statement="statement",
        effective_from=MONTH,
        rule_content=content,
    )
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.RULE_DECISION_RECORDED
    )
    after = memory_read.material_action_detail(conn, action_id=action.action_id).after_state

    assert after["content"] == {
        "category": RuleCategory.LOCAL_RULE.value,
        "rule_kind": "CUSTOM",
        "structured_parameters": {"limit": 7},
        "enforcement": RuleEnforcement.HARD.value,
        "resolution_status": RuleResolution.RESOLVED.value,
        "effective_to": "2026-08-31",
        "description": "description",
        "source": "source",
        "reason": "reason",
    }


def test_rule_action_snapshot_contains_predecessor_decision_and_rule_refs(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    content = NewRuleContent(
        RuleCategory.LOCAL_RULE, "CUSTOM", None, RuleEnforcement.HARD,
        RuleResolution.RESOLVED, None, None, None, None,
    )
    predecessor = record_structured_rule_decision(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id="RULE-1",
        statement="first",
        effective_from=MONTH,
        rule_content=content,
    )
    record_structured_rule_decision(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id="RULE-1",
        statement="second",
        effective_from=date(2026, 8, 2),
        rel="supersedes",
        rule_content=content,
    )
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.RULE_DECISION_RECORDED
    )
    before = memory_read.material_action_detail(conn, action_id=action.action_id).before_state

    assert before["predecessor_decision_id"] == predecessor.decision_id
    assert before["predecessor_rule_version_id"] == predecessor.rule_version_id


def test_availability_snapshot_contains_chain_record_identity(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    first = append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        active=True,
    )
    second = append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 3),
        active=True,
    )
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.AVAILABILITY_CHANGED
    )
    detail = memory_read.material_action_detail(conn, action_id=action.action_id)

    assert detail.before_state["availability_id"] == first.availability_id
    assert detail.before_state["availability_version_id"] == first.availability_version_id
    assert detail.after_state["availability_id"] == second.availability_id
    assert detail.after_state["availability_version_id"] == second.availability_version_id
    assert detail.after_state["supersedes_availability_version_id"] == first.availability_version_id


@pytest.mark.parametrize("mode", ["generic", "freeze", "nn", "training"])
def test_manual_action_snapshot_has_lineage_and_complete_assignment_fact(tmp_path, mode) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    if mode == "training":
        update_employee(
            conn, coordinator_id=COORD, site_id=SITE,
            employee=Employee("E2", "Trainee", date(2020, 1, 1), None, False),
        )
        update_membership(
            conn, coordinator_id=COORD, site_id=SITE,
            membership=SiteMembership(
                "E2", SITE, MembershipKind.LOCAL, True,
                ReadinessState.NOT_READY, ReadinessSource.DEFAULT,
            ),
        )
    _calendar(conn)
    plan = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    selected = plan_ops.select_candidate(
        conn, site_id=SITE, month=MONTH, candidate=plan.candidates[0], coordinator_id=COORD,
    )
    target = get_schedule_snapshot(conn, selected.version_id).assignments[0]
    common = dict(
        conn=conn, site_id=SITE, month=MONTH, coordinator_id=COORD,
        effective_from=MONTH,
    )
    if mode == "generic":
        child = manual_edit.apply_manual_correction(
            **common, upsert_assignments=[replace(target, frozen=True)],
        )
        expected_kind = CoordinatorActionKind.MANUAL_SCHEDULE_CORRECTION
    elif mode == "freeze":
        child = manual_edit.freeze_or_unfreeze(
            **common, assignment_id=target.assignment_id, frozen=True,
        )
        expected_kind = CoordinatorActionKind.ASSIGNMENT_FREEZE_CHANGED
    elif mode == "nn":
        child = manual_edit.mark_not_worked(
            **common, assignment_id=target.assignment_id,
        )
        expected_kind = CoordinatorActionKind.ASSIGNMENT_NOT_WORKED
    else:
        trainee = replace(
            target, assignment_id="AUDIT-TRAINEE", employee_id="E2",
            role=AssignmentRole.TRAINEE, state=AssignmentState.REALIZED,
            covers_demand_id=None, mentor_primary_assignment_id=target.assignment_id,
            work_period_id=None, required_rest_after_hours=None,
        )
        child = training.mark_training_realized(
            **common, trainee_assignment=trainee,
        )
        expected_kind = CoordinatorActionKind.TRAINING_REALIZED
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == expected_kind
    )
    detail = memory_read.material_action_detail(conn, action_id=action.action_id)

    assert detail.before_state["parent_version_id"] == selected.version_id
    assert detail.after_state["child_version_id"] == child.version_id
    fact = detail.after_state["assignments"][0]
    persisted = next(
        assignment for assignment in get_schedule_snapshot(conn, child.version_id).assignments
        if assignment.assignment_id == fact["assignment_id"]
    )
    # Compare against the row actually read back from the child. In
    # particular, a trainee's explicit required_rest_after_hours=None stays
    # None; it is not inherited from the mentor.
    assert fact == {
        "schedule_version_id": persisted.schedule_version_id,
        "assignment_id": persisted.assignment_id,
        "employee_id": persisted.employee_id,
        "start_datetime": persisted.start_datetime.isoformat(),
        "end_datetime": persisted.end_datetime.isoformat(),
        "role": persisted.role.value,
        "state": persisted.state.value,
        "frozen": persisted.frozen,
        "covers_demand_id": persisted.covers_demand_id,
        "mentor_primary_assignment_id": persisted.mentor_primary_assignment_id,
        "operational_code": persisted.operational_code,
        "work_period_id": persisted.work_period_id,
        "required_rest_after_hours": persisted.required_rest_after_hours,
    }


def test_candidate_selection_snapshot_uses_complete_assignment_facts(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _calendar(conn)
    plan = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    plan_ops.select_candidate(
        conn, site_id=SITE, month=MONTH, candidate=plan.candidates[0], coordinator_id=COORD,
    )
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED
    )
    added = memory_read.material_action_detail(conn, action_id=action.action_id).after_state["added"]
    assert added
    required_fields = {
        "schedule_version_id", "mentor_primary_assignment_id", "required_rest_after_hours",
    }
    assert all(required_fields <= fact.keys() for fact in added)


def _all_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _all_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_dicts(child)


def test_finalize_snapshot_contains_deviation_acknowledgement_before_and_after(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _calendar(conn)
    plan = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    selected = plan_ops.select_candidate(
        conn, site_id=SITE, month=MONTH, candidate=plan.candidates[0], coordinator_id=COORD,
    )
    target = get_schedule_snapshot(conn, selected.version_id).assignments[0]
    manual_edit.mark_not_worked(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=MONTH,
        assignment_id=target.assignment_id,
    )
    current_id = get_current_version_id(conn, SITE, MONTH)
    deviations = get_schedule_snapshot(conn, current_id).deviations
    deviation_ids = {deviation.deviation_id for deviation in deviations}
    assert deviation_ids

    lifecycle_ops.finalize(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        acknowledged_deviation_ids=deviation_ids,
        reason="accepted by coordinator",
    )
    action = next(
        action for action in memory_read.material_action_history(conn)
        if action.action_kind == CoordinatorActionKind.SCHEDULE_FINALIZED
    )
    detail = memory_read.material_action_detail(conn, action_id=action.action_id)
    before_by_id = {
        item["deviation_id"]: item
        for item in _all_dicts(detail.before_state)
        if "deviation_id" in item
    }
    after_by_id = {
        item["deviation_id"]: item
        for item in _all_dicts(detail.after_state)
        if "deviation_id" in item
    }

    assert set(before_by_id) == deviation_ids
    assert all(item["acknowledged"] is False for item in before_by_id.values())
    assert set(after_by_id) == deviation_ids
    assert all(item["acknowledged"] is True for item in after_by_id.values())
    assert all(item["acknowledged_by"] == COORD for item in after_by_id.values())
    assert all(item["reason"] == "accepted by coordinator" for item in after_by_id.values())


def test_explicit_question_link_cannot_become_noncurrent_before_mutation(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _bootstrap(conn)
    _employee(conn)
    _calendar(conn)
    append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        active=True,
    )
    result = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    assert result.status == "DECISION_REQUIRED"
    snapshot = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH)
    action_count_before = len(memory_read.material_action_history(conn))
    original_validate = site_memory.validate_decision_required_link_no_commit

    def validate_then_lose_current_pointer(open_conn, **kwargs) -> None:
        original_validate(open_conn, **kwargs)
        competing = connect(db_path)
        with competing:
            site_memory.clear_current_decision_required_no_commit(
                competing, site_id=SITE, month=MONTH,
            )
        competing.close()

    monkeypatch.setattr(
        site_memory,
        "validate_decision_required_link_no_commit",
        validate_then_lose_current_pointer,
    )

    with pytest.raises(Exception):
        set_target_hours(
            conn,
            coordinator_id=COORD,
            site_id=SITE,
            employee_id="E1",
            month=MONTH,
            target_hours=120,
            responds_to_decision_required_id=snapshot.decision_required_id,
        )

    assert get_work_balance_target(conn, "E1", MONTH) is None
    assert len(memory_read.material_action_history(conn)) == action_count_before


def test_sequential_link_to_known_but_noncurrent_question_fails_before_mutation(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    _employee(conn)
    _calendar(conn)
    append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        active=True,
    )
    blocked = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    assert blocked.status == "DECISION_REQUIRED"
    old_snapshot = site_memory.get_current_decision_required(conn, site_id=SITE, month=MONTH)
    append_availability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        availability_id="A1",
        employee_id="E1",
        kind=AvailabilityKind.UNAVAILABLE_24H,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        active=False,
    )
    feasible = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=MONTH,
    )
    assert feasible.status == "FEASIBLE"

    with pytest.raises(site_memory.DecisionRequiredLinkMismatch):
        set_target_hours(
            conn,
            coordinator_id=COORD,
            site_id=SITE,
            employee_id="E1",
            month=MONTH,
            target_hours=120,
            responds_to_decision_required_id=old_snapshot.decision_required_id,
        )

    assert get_work_balance_target(conn, "E1", MONTH) is None


def test_real_v5_to_v6_migration_preserves_data_and_adds_exactly_three_tables(tmp_path) -> None:
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
    tables_before = {
        row[0] for row in legacy.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    legacy.close()

    migrated = connect(db_path)
    tables_after = {
        row[0] for row in migrated.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert migrated.execute("PRAGMA user_version").fetchone()[0] == 6
    assert migrated.execute(
        "SELECT holiday FROM calendar_days WHERE date='2026-08-03'"
    ).fetchone() == (1,)
    assert tables_after - tables_before == {
        "coordinator_action_records",
        "decision_required_snapshots",
        "current_decision_required",
    }
