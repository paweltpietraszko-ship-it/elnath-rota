"""Owner-requested proof that two Sites coexist in one LocalStore.

The shared-Employee cases assert the frozen EMP-03 boundary: Site-owned
schedule/rule state remains scoped, while REST and WorkBalance intentionally
see that Employee's current Assignments across Sites.
"""
from __future__ import annotations

import ast
from pathlib import Path

from benchmarks.t011_multisite_audit import (
    run_disjoint_full_cycle,
    run_shared_full_cycle,
    run_shared_rest_collision,
    write_evidence,
)


def test_two_disjoint_sites_complete_interleaved_full_cycles(tmp_path: Path) -> None:
    evidence = run_disjoint_full_cycle(tmp_path / "disjoint.db")
    assert evidence["status"] == "PASS"
    assert evidence["active_sites"] == ["SITE-MS-A", "SITE-MS-B"]
    assert evidence["assignments"]["SITE-MS-A"]["count"] == 31
    assert evidence["assignments"]["SITE-MS-A"]["employee_ids"] == ["EMP-MS-A"]
    assert evidence["assignments"]["SITE-MS-B"]["count"] == 31
    assert evidence["assignments"]["SITE-MS-B"]["employee_ids"] == ["EMP-MS-B"]
    assert evidence["current_versions"]["SITE-MS-A"] != evidence["current_versions"]["SITE-MS-B"]
    assert evidence["applied_rules"]["SITE-MS-A"]
    assert evidence["applied_rules"]["SITE-MS-B"] == []
    assert evidence["rule_history_keys"] == {
        "SITE-MS-A": ["RULE-MULTISITE-SITE-A-ONLY"],
        "SITE-MS-B": [],
    }
    assert evidence["months_with_schedule"] == {
        "SITE-MS-A": ["2026-10-01"],
        "SITE-MS-B": ["2026-10-01"],
    }
    assert evidence["quarter_planned_hours"] == {"EMP-MS-A": 372, "EMP-MS-B": 372}
    assert evidence["warnings"] == {"SITE-MS-A": [], "SITE-MS-B": []}
    assert evidence["site_a_unchanged_after_site_b_cycle"] is True
    write_evidence(evidence, tmp_path / "artifacts" / "disjoint_full_cycle.json")


def test_shared_employee_full_cycles_keep_site_state_separate_and_global_balance_combined(tmp_path: Path) -> None:
    evidence = run_shared_full_cycle(tmp_path / "shared.db")
    assert evidence["status"] == "PASS"
    assert evidence["shared_employee_id"] == "EMP-MS-SHARED"
    assert evidence["site_assignment_hours"] == {
        "SITE-MS-SHARED-A": 31,
        "SITE-MS-SHARED-B": 31,
    }
    assert evidence["global_quarter_planned_hours"] == 62
    assert evidence["open_month_planned_hours"] == {
        "SITE-MS-SHARED-A": 62,
        "SITE-MS-SHARED-B": 62,
    }
    assert evidence["other_site_assignment_counts"] == {
        "SITE-MS-SHARED-A": 31,
        "SITE-MS-SHARED-B": 31,
    }
    assert evidence["global_availability_counts"] == {
        "SITE-MS-SHARED-A": 1,
        "SITE-MS-SHARED-B": 1,
    }
    assert evidence["applied_rules"]["SITE-MS-SHARED-A"]
    assert evidence["applied_rules"]["SITE-MS-SHARED-B"] == []
    assert evidence["rule_history_keys"] == {
        "SITE-MS-SHARED-A": ["RULE-MULTISITE-SITE-A-ONLY"],
        "SITE-MS-SHARED-B": [],
    }
    assert evidence["current_versions"]["SITE-MS-SHARED-A"] != evidence["current_versions"]["SITE-MS-SHARED-B"]
    assert evidence["months_with_schedule"] == {
        "SITE-MS-SHARED-A": ["2026-10-01"],
        "SITE-MS-SHARED-B": ["2026-10-01"],
    }
    assert evidence["warnings"] == {"SITE-MS-SHARED-A": [], "SITE-MS-SHARED-B": []}
    assert evidence["site_a_assignments_unchanged_after_site_b_cycle"] is True
    write_evidence(evidence, tmp_path / "artifacts" / "shared_employee_full_cycle.json")


def test_shared_employee_illegal_cross_site_rest_stops_only_second_site(tmp_path: Path) -> None:
    evidence = run_shared_rest_collision(tmp_path / "rest-collision.db")
    assert evidence["status"] == "DECISION_REQUIRED"
    assert evidence["site_a_assignment_count"] == 31
    assert evidence["site_b_assignment_count"] == 0
    assert evidence["site_b_blocking_demand_count"] > 0
    assert evidence["site_b_blocker_conditions"] == ["REST-01"]
    assert evidence["site_b_months_with_schedule"] == []
    write_evidence(evidence, tmp_path / "artifacts" / "shared_employee_rest_collision.json")


def test_multisite_audit_uses_application_boundary_only() -> None:
    paths = (Path(__file__), Path("benchmarks/t011_multisite_audit.py"))
    offenders = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(alias.name for alias in node.names if alias.name.startswith("rota.persistence"))
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("rota.persistence"):
                offenders.append(node.module)
    assert offenders == []
