"""Adversarial implementation-audit tests for ROTA-T023b round 5."""
from __future__ import annotations

import json
from dataclasses import MISSING, replace
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from ortools.sat.python import cp_model

from rota.application.manual_edit import apply_manual_correction
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    ShiftCatalogKind,
    ShiftDemand,
    ShiftKind,
    Site,
    SitePlanningRegime,
)
from rota.persistence.db import connect
from rota.planning.constraints import add_weekly_rest_constraints
from rota.planning.validator import validate
from tests.test_t023b import MONTH, _bare_state, _create_version, _seed


def _daily_assignments(*, state: AssignmentState) -> list[Assignment]:
    start = datetime(2026, 8, 1)
    return [
        Assignment(
            f"A-{day}", "SV-X", "EMP-1", start + timedelta(days=day),
            start + timedelta(days=day, hours=12), AssignmentRole.PRIMARY,
            state, False, None, None,
        )
        for day in range(7)
    ]


def test_r5_required_site_regime_cannot_be_omitted() -> None:
    """T23b-01: a new real Site must not infer ORDINARY from omission."""
    field = Site.__dataclass_fields__["planning_regime"]
    assert field.default is MISSING


def test_r5_cancelled_work_does_not_interrupt_weekly_rest() -> None:
    """Frozen addendum section 6: only non-CANCELLED work occupies time."""
    cancelled = _daily_assignments(state=AssignmentState.CANCELLED)
    state = _bare_state(
        regime=SitePlanningRegime.OCHRONA,
        existing_assignments=tuple(cancelled),
    )
    report = validate(state, cancelled)
    assert not any(v.rule == "WEEKLY-REST-01" for v in report.violation_details)


def test_r5_solver_allows_free_gap_spanning_unselected_slot_boundaries() -> None:
    """T23b-30: candidate slot endpoints cannot split otherwise free time."""
    model = cp_model.CpModel()
    x = {}
    slots = []
    start = datetime(2026, 8, 1)
    for day in range(7):
        demand_id = f"D-{day}"
        demand = SimpleNamespace(
            demand_id=demand_id,
            start_datetime=start + timedelta(days=day),
            end_datetime=start + timedelta(days=day, hours=12),
        )
        slots.append(SimpleNamespace(employee_id="EMP-1", demand=demand))
        x["EMP-1", demand_id] = model.new_bool_var(f"x_{day}")
        model.add(x["EMP-1", demand_id] == 0)

    add_weekly_rest_constraints(model, x, slots, {}, MONTH, True)
    status = cp_model.CpSolver().solve(model)
    assert status in (cp_model.FEASIBLE, cp_model.OPTIMAL)


def test_r5_solver_checks_employee_with_only_fixed_target_work() -> None:
    """T23b-30: fixed-only employees are part of the same HARD invariant."""
    model = cp_model.CpModel()
    start = datetime(2026, 8, 1)
    fixed = {
        "EMP-1": [
            (start + timedelta(days=day), start + timedelta(days=day, hours=12))
            for day in range(7)
        ]
    }
    add_weekly_rest_constraints(model, {}, [], fixed, MONTH, True)
    status = cp_model.CpSolver().solve(model)
    assert status == cp_model.INFEASIBLE


def test_r5_manual_24h_floor_violation_records_rest_override() -> None:
    """T23b-31: the new 24h floor uses the existing REST override path."""
    conn = connect(":memory:")
    _seed(conn, regime=SitePlanningRegime.OCHRONA)
    first_start = datetime(2026, 8, 1)
    next_start = first_start + timedelta(hours=44)  # 24h work + only 20h rest
    demands = [
        ShiftDemand(
            "D-24-1", "", first_start, first_start + timedelta(hours=12), 1,
            shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H24,
            required_rest_hours=11, work_period_template_id="TPL-24",
            work_period_component=1,
        ),
        ShiftDemand(
            "D-24-2", "", first_start + timedelta(hours=12),
            first_start + timedelta(hours=24), 1,
            shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H24,
            required_rest_hours=11, work_period_template_id="TPL-24",
            work_period_component=2,
        ),
        ShiftDemand(
            "D-NEXT", "", next_start, next_start + timedelta(hours=12), 1,
            shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12,
            required_rest_hours=11,
        ),
    ]
    assignments = [
        Assignment(
            "A-24-1", "", "EMP-1", demands[0].start_datetime,
            demands[0].end_datetime, AssignmentRole.PRIMARY,
            AssignmentState.PLANNED, False, "D-24-1", None,
            work_period_id="WP-24", required_rest_after_hours=11,
        ),
        Assignment(
            "A-24-2", "", "EMP-1", demands[1].start_datetime,
            demands[1].end_datetime, AssignmentRole.PRIMARY,
            AssignmentState.PLANNED, False, "D-24-2", None,
            work_period_id="WP-24", required_rest_after_hours=11,
        ),
        Assignment(
            "A-NEXT", "", "EMP-1", demands[2].start_datetime,
            demands[2].end_datetime, AssignmentRole.PRIMARY,
            AssignmentState.PLANNED, False, "D-NEXT", None,
            work_period_id="WP-NEXT", required_rest_after_hours=11,
        ),
    ]
    parent = _create_version(conn, demands, assignments)
    child = apply_manual_correction(
        conn, site_id="SITE-1", month=MONTH, coordinator_id="COORD-1",
        effective_from=date(2026, 7, 27),
        upsert_assignments=[replace(assignments[0], schedule_version_id=parent.version_id)],
    )
    row = conn.execute(
        "SELECT structured_parameters FROM site_rule_versions WHERE rule_id = ?",
        (f"REST-OVERRIDE:{child.version_id}",),
    ).fetchone()
    assert row is not None
    parameters = json.loads(row[0])
    assert parameters["rest_pairs"][0]["required_rest_hours"] == 24
