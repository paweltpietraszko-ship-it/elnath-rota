"""Independent T058 R7: H24 manual-decision preservation on SHA 3c8185b."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

from rota.application import manual_edit, plan_ops
from rota.application.durable_inputs import update_site_profile
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    DeviationCategory,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    StandardShift,
)
from rota.persistence import schedule_lifecycle
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from tests.test_t019b import COORD, MONTH, SITE, _bootstrap, _employee, _fill_calendar, _profile


class _August10(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 10, 12)
        return value if tz is None else value.replace(tzinfo=tz)


def _demand(demand_id: str, start: datetime, end: datetime, **provenance) -> ShiftDemand:
    return ShiftDemand(demand_id, "V0", start, end, 1, **provenance)


def _primary(
    assignment_id: str,
    employee_id: str,
    demand: ShiftDemand,
    *,
    frozen: bool = False,
    work_period_id: str | None = None,
) -> Assignment:
    return Assignment(
        assignment_id,
        "V0",
        employee_id,
        demand.start_datetime,
        demand.end_datetime,
        AssignmentRole.PRIMARY,
        AssignmentState.PLANNED,
        frozen,
        demand.demand_id,
        None,
        work_period_id=work_period_id,
        required_rest_after_hours=demand.required_rest_hours,
    )


def _seed_h24_manual_decision():
    conn = connect(":memory:")
    _bootstrap(conn)
    profile = _profile()
    update_site_profile(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        profile=replace(
            profile,
            standard_shifts=[
                *profile.standard_shifts,
                StandardShift(
                    ShiftKind.D,
                    time(6),
                    time(6),
                    True,
                    1,
                    catalog_kind=ShiftCatalogKind.H24,
                    required_rest_hours=12,
                ),
            ],
        ),
    )
    _employee(conn, "E1")
    _employee(conn, "E2")
    _fill_calendar(conn)

    d1 = _demand("D-1", datetime(2026, 8, 1, 6), datetime(2026, 8, 1, 18))
    d20 = _demand("D-20", datetime(2026, 8, 20, 6), datetime(2026, 8, 20, 18))
    d21 = _demand("D-21", datetime(2026, 8, 21, 6), datetime(2026, 8, 21, 18))
    h24_d = _demand(
        "H24-D-22",
        datetime(2026, 8, 22, 6),
        datetime(2026, 8, 22, 18),
        shift_kind=ShiftKind.D,
        catalog_kind=ShiftCatalogKind.H24,
        required_rest_hours=12,
        work_period_template_id="H24-22",
        work_period_component=1,
    )
    h24_n = _demand(
        "H24-N-22",
        datetime(2026, 8, 22, 18),
        datetime(2026, 8, 23, 6),
        shift_kind=ShiftKind.N,
        catalog_kind=ShiftCatalogKind.H24,
        required_rest_hours=12,
        work_period_template_id="H24-22",
        work_period_component=2,
    )
    work_period_id = f"{SITE}:H24-22"
    assignments = [
        _primary("A-1", "E2", d1),
        _primary("A-20", "E1", d20, frozen=True),
        _primary("A-21", "E1", d21, frozen=True),
        _primary("A-22-D", "E2", h24_d, work_period_id=work_period_id),
        _primary("A-22-N", "E2", h24_n, work_period_id=work_period_id),
    ]
    schedule_lifecycle.create_schedule_version(
        conn,
        version_id="V0",
        site_id=SITE,
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 7, 25, 12),
        created_by=COORD,
        applied_rule_version_ids=[],
        shift_demands=[d1, d20, d21, h24_d, h24_n],
        assignments=assignments,
        deviations=[],
        effective_from=MONTH,
    )

    manual = manual_edit.apply_manual_correction(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=MONTH,
        upsert_assignments=[
            replace(assignments[-2], employee_id="E1"),
            replace(assignments[-1], employee_id="E1"),
        ],
        note="świadoma ręczna służba 24h",
    )
    snapshot = get_schedule_snapshot(conn, manual.version_id)
    assert any(
        deviation.category == DeviationCategory.LAW
        and deviation.source_reference == "THIRD-CONSECUTIVE-SHIFT-01"
        for deviation in snapshot.deviations
    )

    saved = {
        assignment.assignment_id: assignment
        for assignment in snapshot.assignments
        if assignment.assignment_id in {"A-22-D", "A-22-N"}
    }
    assert saved["A-22-D"].employee_id == saved["A-22-N"].employee_id == "E1"
    return conn, saved


def test_h24_both_manually_edited_components_are_preserved_as_one_decision():
    """T58-02/06/15: both D+N components belong to the manually edited H24 day."""
    _, saved = _seed_h24_manual_decision()
    assert saved["A-22-D"].frozen is True
    assert saved["A-22-N"].frozen is True


def test_h24_manual_decision_does_not_block_later_przelicz_plan(monkeypatch):
    """T58-06/14: the preserved H24 decision is fixed, not a new solver decision."""
    conn, _ = _seed_h24_manual_decision()

    monkeypatch.setattr(plan_ops, "datetime", _August10)
    result = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=date(2026, 8, 10),
    )
    assert result.status == "FEASIBLE"
    for candidate in result.candidates:
        employees = {
            assignment.covers_demand_id: assignment.employee_id
            for assignment in candidate
            if assignment.covers_demand_id in {"H24-D-22", "H24-N-22"}
        }
        assert employees == {"H24-D-22": "E1", "H24-N-22": "E1"}


def test_explicit_unfreeze_remains_authoritative():
    """Control: the T058 heuristic must not immediately undo an explicit unfreeze."""
    conn, saved = _seed_h24_manual_decision()
    frozen_id = next(assignment_id for assignment_id, assignment in saved.items() if assignment.frozen)
    child = manual_edit.freeze_or_unfreeze(
        conn,
        site_id=SITE,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=MONTH,
        assignment_id=frozen_id,
        frozen=False,
    )
    snapshot = get_schedule_snapshot(conn, child.version_id)
    updated = next(assignment for assignment in snapshot.assignments if assignment.assignment_id == frozen_id)
    assert updated.frozen is False
