"""Independent Tor-1 regressions for ROTA-T021 Screen 2, round 13.

The tests cover sibling cases of R12-2 that become reachable only after an
edit or end has already been saved: restoring an ended availability family
and selecting exactly one displayed version of a matrix-rule family.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EMPLOYEE_DETAIL = (ROOT / "frontend/src/screens/EmployeeDetail.tsx").read_text(encoding="utf-8")


def test_ended_availability_log_row_still_exposes_its_restore_edit_action() -> None:
    """brief.md §5.1: every displayed family can be edited active=True."""
    edit_action = "onClick={() => setEditingId(r.availability_id)}"
    edit_position = EMPLOYEE_DETAIL.index(edit_action)
    nearby_guard = EMPLOYEE_DETAIL[max(0, edit_position - 250) : edit_position]
    assert "{r.active && (" not in nearby_guard, (
        "the edit action is inside the active-only guard: after the same family "
        "is ended with active=False, its required active=True correction/restore "
        "path disappears even though the row remains in the log"
    )


def test_matrix_history_versions_do_not_share_one_render_and_edit_identity() -> None:
    """brief.md §5.1: one clicked concrete cell/version opens one editor."""
    raw_family_identity = re.compile(
        r"cells\.map\(\(c\)\s*=>\s*"
        r"editingRuleId\s*===\s*c\.rule_id.*?"
        r"key=\{c\.rule_id\}",
        flags=re.DOTALL,
    )
    assert not raw_family_identity.search(EMPLOYEE_DETAIL), (
        "matrix versions in one rule family share rule_id; using that family id "
        "as both the React key and selected-row identity gives duplicate keys and "
        "opens every historical/current version when one row is clicked"
    )
