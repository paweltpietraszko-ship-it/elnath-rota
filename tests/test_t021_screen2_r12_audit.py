"""Independent Tor-1 audit regressions for ROTA-T021 Screen 2.

These source-boundary tests cover frontend orchestration that cannot be
verified by the Python application tests: retry identity, wiring of the two
accepted edit commands, and the frozen day_only-exception AND composition.
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTROL_PANEL = (ROOT / "frontend/src/screens/ControlPanel.tsx").read_text(encoding="utf-8")
EMPLOYEE_DETAIL = (ROOT / "frontend/src/screens/EmployeeDetail.tsx").read_text(encoding="utf-8")


def test_new_employee_retry_identity_is_created_on_open_and_survives_reload() -> None:
    """brief.md §5.1 R9-1: retry must reuse one browser-held Employee id."""
    assert "sessionStorage" in CONTROL_PANEL, (
        "the accepted contract requires the in-progress employee_id to survive "
        "a reload until roster attachment succeeds"
    )
    submit_start = CONTROL_PANEL.index("const submit = async () =>")
    submit_end = CONTROL_PANEL.index("return (", submit_start)
    assert "crypto.randomUUID()" not in CONTROL_PANEL[submit_start:submit_end], (
        "employee_id is generated inside each submit attempt, so retry after a "
        "successful employee write and lost/failed attach can create another row"
    )


def test_saved_matrix_rule_has_a_frontend_period_edit_path() -> None:
    """brief.md §5.1: correcting a saved cell must call updateMatrixRule."""
    assert "api.updateMatrixRule(" in EMPLOYEE_DETAIL, (
        "the API client exposes updateMatrixRule, but EmployeeDetail never calls it"
    )


def test_saved_absence_has_an_active_period_edit_path_not_only_end() -> None:
    """brief.md §5.1: a selected log row supports both edit and end."""
    calls = re.findall(r"api\.updateAvailability\(.*?\n\s*\}\);", EMPLOYEE_DETAIL, flags=re.DOTALL)
    assert calls, "EmployeeDetail has no updateAvailability call"
    assert any("active: false" not in call for call in calls), (
        "every updateAvailability call is the active=False end path; no call edits "
        "the selected family's dates with an active current end"
    )


def test_day_only_exception_does_not_hide_an_independent_hard_nocka_ban() -> None:
    """T021b §3.3/§10: the exception exempts DAY_ONLY-01 only; other HARDs remain ANDed."""
    forbidden_shortcut = re.compile(
        r"day_only\s*\?\s*!dayOnlyExceptionActive\s*:\s*cellActiveToday\(cells,\s*\(c\)\s*=>\s*c\.cell\s*===\s*[\"']nocka[\"']\)"
    )
    assert not forbidden_shortcut.search(EMPLOYEE_DETAIL), (
        "when the day_only exception is active, the displayed Nocka status ignores "
        "a simultaneously active independent nocka HARD rule"
    )
