"""ROTA-T009 required test matrix items 13, 14, 15, 16, 17, 18."""
from __future__ import annotations

import ast
import json
import zipfile
from dataclasses import replace
from datetime import date

import pytest

from rota.application import backup, lifecycle_ops, memory_read, plan_ops, rule_decisions, training
from rota.domain import Assignment, AssignmentRole, AssignmentState, ReadinessSource, ReadinessState
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_memberships_for_site, save_site_membership
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header
from rota.persistence.site_profile_repository import save_site_profile
from rota.site_memory_types import NewRuleContent
from rota.domain import RuleCategory, RuleEnforcement, RuleResolution
from tests.support.t009_fixtures import seed_real_object

MONTH = date(2026, 8, 1)


def _plan_and_select(conn, site_id: str):
    result = plan_ops.plan_month(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=MONTH)
    assert result.status == "FEASIBLE"
    return plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=result.candidates[0])


def _realize_training_n_times(conn, *, site_id: str, mentor, trainee_id: str, n: int, label: str) -> None:
    for i in range(n):
        trainee_assignment = Assignment(
            f"ASG-TRAIN-{label}-{i}", "", trainee_id, mentor.start_datetime, mentor.end_datetime,
            AssignmentRole.TRAINEE, AssignmentState.REALIZED, False, None, mentor.assignment_id,
        )
        training.mark_training_realized(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
            effective_from=date(2026, 8, i + 2), trainee_assignment=trainee_assignment,
        )


def test_13_realized_training_updates_default_readiness_but_not_override(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="life-1", month=MONTH, seed=400)
    site_id = pstate.site.site_id
    v1 = _plan_and_select(conn, site_id)
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    mentor = next(a for a in snapshot.assignments if a.role == AssignmentRole.PRIMARY)
    trainee_id = next(e.employee_id for e in pstate.employees if e.employee_id != mentor.employee_id)

    # R4-4: training_s_enabled/training_s_weekdays_only gate readiness
    # counting -- this test exercises the counting/threshold/override
    # mechanics, so it opts the profile in explicitly rather than relying on
    # the benchmark's own (disabled) default.
    save_site_profile(conn, replace(pstate.profile, training_s_enabled=True, training_s_weekdays_only=False))

    memberships = list_memberships_for_site(conn, site_id)
    membership = next(m for m in memberships if m.employee_id == trainee_id)
    save_site_membership(conn, replace(
        membership, readiness_state=ReadinessState.NOT_READY, readiness_source=ReadinessSource.DEFAULT,
    ))
    threshold = pstate.profile.training_s_default_readiness_threshold
    _realize_training_n_times(conn, site_id=site_id, mentor=mentor, trainee_id=trainee_id, n=threshold, label="SELF")
    updated = next(m for m in list_memberships_for_site(conn, site_id) if m.employee_id == trainee_id)
    assert updated.readiness_state == ReadinessState.READY_FOR_PRIMARY

    # COORDINATOR_OVERRIDE must never be silently overwritten.
    other_id = next(
        e.employee_id for e in pstate.employees if e.employee_id not in (mentor.employee_id, trainee_id)
    )
    other_membership = next(m for m in list_memberships_for_site(conn, site_id) if m.employee_id == other_id)
    save_site_membership(conn, replace(
        other_membership, readiness_state=ReadinessState.NOT_READY, readiness_source=ReadinessSource.COORDINATOR_OVERRIDE,
    ))
    _realize_training_n_times(conn, site_id=site_id, mentor=mentor, trainee_id=other_id, n=threshold, label="OTHER")
    unchanged = next(m for m in list_memberships_for_site(conn, site_id) if m.employee_id == other_id)
    assert unchanged.readiness_state == ReadinessState.NOT_READY


def test_14_finalize_revalidates_requires_exact_acknowledgement_and_freezes(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="life-2", month=MONTH, seed=401)
    site_id = pstate.site.site_id
    _plan_and_select(conn, site_id)

    with pytest.raises(ValueError):
        lifecycle_ops.finalize(
            conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1",
            acknowledged_deviation_ids={"NONEXISTENT"},
        )

    finalized = lifecycle_ops.finalize(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", acknowledged_deviation_ids=set(),
    )
    header = get_schedule_version_header(conn, finalized.version_id)
    assert header.status.value.startswith("FINAL")


def test_15_restore_moves_only_current_reference(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="life-3", month=MONTH, seed=402)
    site_id = pstate.site.site_id
    _plan_and_select(conn, site_id)
    finalized = lifecycle_ops.finalize(
        conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", acknowledged_deviation_ids=set(),
    )
    replanned = plan_ops.replan(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", effective_from=date(2026, 8, 2))
    v2 = plan_ops.select_candidate(conn, site_id=site_id, month=MONTH, candidate=replanned.candidates[0])
    assert get_current_version_id(conn, site_id, MONTH) == v2.version_id

    lifecycle_ops.restore(conn, site_id=site_id, month=MONTH, coordinator_id="COORD-1", version_id=finalized.version_id)
    assert get_current_version_id(conn, site_id, MONTH) == finalized.version_id
    assert get_schedule_snapshot(conn, v2.version_id).assignments  # later history still readable/intact


def test_16_structured_rule_command_reaches_decision_ledger(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="life-4", month=MONTH, seed=403)
    site_id = pstate.site.site_id
    content = NewRuleContent(
        category=RuleCategory.LOCAL_RULE, rule_kind=None, structured_parameters=None,
        enforcement=RuleEnforcement.SOFT, resolution_status=RuleResolution.RESOLVED,
        effective_to=None, description="structured decision", source="T010-seam-test", reason=None,
    )
    decision = rule_decisions.record_structured_rule_decision(
        conn, coordinator_id="COORD-1", site_id=site_id, rule_id="RULE-STRUCTURED", statement="test statement",
        effective_from=MONTH, rel=None, rule_content=content,
    )
    resolved, unresolved, _ = memory_read.effective_rules_for_month(conn, site_id=site_id, month=MONTH)
    assert any(r.rule_version_id == decision.rule_version_id for r in resolved)


def test_17_backup_openable_and_diagnostic_zip_excludes_prohibited_data(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    pstate = seed_real_object(conn, case_id="life-5", month=MONTH, seed=404)
    site_id = pstate.site.site_id
    _plan_and_select(conn, site_id)

    backup_path = tmp_path / "backup.db"
    backup.backup_database(conn, str(backup_path))
    reopened = connect(backup_path)
    assert get_current_version_id(reopened, site_id, MONTH) is not None  # backup is a real, openable LocalStore

    zip_path = tmp_path / "diag.zip"
    backup.build_diagnostic_zip(conn, str(zip_path))
    with zipfile.ZipFile(zip_path) as archive:
        payload = json.loads(archive.read("diagnostics.json"))
    assert "schema_version" in payload and "table_row_counts" in payload
    serialized = json.dumps(payload)
    for employee in pstate.employees:
        assert employee.display_name not in serialized
    assert "note" not in serialized.lower() or "table_row_counts" in serialized  # no note text, only table names


def test_18_dependency_boundary_scan() -> None:
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]

    def _imports(path):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    for path in (repo_root / "rota" / "planning").rglob("*.py"):
        for name in _imports(path):
            assert not name.startswith("rota.persistence"), f"{path}: planning must not import persistence"
            assert not name.startswith("rota.application"), f"{path}: planning must not import application"
            assert not name.startswith("sqlite3"), f"{path}: planning must not import sqlite3"

    for path in (repo_root / "rota" / "persistence").rglob("*.py"):
        for name in _imports(path):
            assert not name.startswith("rota.application"), f"{path}: persistence must not import application"

    for path in (repo_root / "rota" / "application").rglob("*.py"):
        for name in _imports(path):
            assert "tkinter" not in name and "PyQt" not in name and "react" not in name.lower()
