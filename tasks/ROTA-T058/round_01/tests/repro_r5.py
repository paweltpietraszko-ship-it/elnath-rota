"""Independent re-check matrix for ROTA-T058 fix 1f072fa."""
from __future__ import annotations

from datetime import date, datetime

from rota.application.deviation_mapping import materialize_deviations
from rota.domain import Assignment, AssignmentRole, AssignmentState, DeviationCategory
from rota.planning.validator import validate
from tests.support.minimal_state import base_state


RULE = "THIRD-CONSECUTIVE-SHIFT-01"


def _primary(assignment_id: str, day: date, *, employee_id: str = "A", version_id: str = "V") -> Assignment:
    return Assignment(
        assignment_id,
        version_id,
        employee_id,
        datetime(day.year, day.month, day.day, 5),
        datetime(day.year, day.month, day.day, 17),
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        True,
        None,
        None,
    )


def _third_details(state, assignments):
    return [detail for detail in validate(state, assignments).violation_details if detail.rule == RULE]


def test_far_boundary_only_history_is_not_this_months_violation() -> None:
    boundary = tuple(
        _primary(f"JUL-{day}", date(2026, 7, day), version_id="JUL")
        for day in (1, 2, 3)
    )
    assert _third_details(base_state(boundary_assignments=boundary), []) == []


def test_backward_mixed_boundary_is_still_detected() -> None:
    boundary = (
        _primary("SEP-29", date(2026, 9, 29), version_id="SEP"),
        _primary("SEP-30", date(2026, 9, 30), version_id="SEP"),
    )
    current = _primary("OCT-01", date(2026, 10, 1), version_id="OCT")
    details = _third_details(base_state(boundary_assignments=boundary), [current])
    assert len(details) == 1
    assert details[0].assignment_ids == ("OCT-01",)


def test_forward_mixed_boundary_is_still_detected() -> None:
    current = _primary("OCT-31", date(2026, 10, 31), version_id="OCT")
    boundary = (
        _primary("NOV-01", date(2026, 11, 1), version_id="NOV"),
        _primary("NOV-02", date(2026, 11, 2), version_id="NOV"),
    )
    details = _third_details(base_state(boundary_assignments=boundary), [current])
    assert len(details) == 1
    assert details[0].assignment_ids == ("OCT-31",)


def test_current_month_manual_violation_still_materializes_as_law() -> None:
    assignments = [
        _primary(f"OCT-{day:02d}", date(2026, 10, day), version_id="OCT")
        for day in (10, 11, 12)
    ]
    details = _third_details(base_state(), assignments)
    deviations = materialize_deviations(details, ())
    assert len(deviations) == 1
    assert deviations[0].category == DeviationCategory.LAW
    assert deviations[0].affected_assignment_or_employee == "OCT-10"
