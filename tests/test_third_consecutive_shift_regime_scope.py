"""ROTA-THIRD-CONSECUTIVE-SHIFT-ORDINARY-SCOPE (brief.md, Codex
preimplementation PASS 5c91225): THIRD-CONSECUTIVE-SHIFT-01 (ROTA-T058) is
now OCHRONA-only -- OWNER_RULING 2026-09-15, for ORDINARY the only HARD
limits on work rhythm remain the labor-code rules (REST-01/WEEKLY-REST-01).
T058's own OCHRONA-side contract is unchanged and stays covered by
tests/test_t058.py (T58-11/T58-13 there were switched to an explicit
OCHRONA Site so they keep exercising it after this file's regime split).

TCSO-03/08 (solver+plan, no block) and TCSO-05 (manual correction, no
Deviation) are exercised here for ORDINARY. TCSO-04 (isolation from
REST-01/WEEKLY-REST-01/LOAD-01) is not a new fixture: this change touches
only the two THIRD-CONSECUTIVE-SHIFT-01 enforcement points (constraints.py
solver call site + validator_checks_patterns.py), never REST/WEEKLY-REST/
LOAD code, so their own existing test matrices are the isolation proof."""
from __future__ import annotations

from datetime import date, timedelta

from rota.application import manual_edit, plan_ops
from rota.domain import Employee, WorkBalance
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.engine import plan
from rota.planning.solver import solve
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, base_state
from tests.support.t009_fixtures import seed_real_object
from tests.test_t032_soft_ranking import _d_demand, _membership


def test_tcso_03_ordinary_three_consecutive_days_feasible():
    """Same shape as test_t058.py's T58-11 (one employee, three mandatory D
    demands, no alternative) but ORDINARY (base_state's own default regime,
    unchanged here) -- T058 no longer blocks it: the solver assigns all
    three, plan() reaches FEASIBLE, and the independent validator raises no
    THIRD-CONSECUTIVE-SHIFT-01 finding (TCSO-03/TCSO-08)."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.assignments is not None
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.status != "THIRD_CONSECUTIVE_SHIFT_BLOCKED"
    report = validate(state, result.candidates[0])
    assert not any(v.rule == "THIRD-CONSECUTIVE-SHIFT-01" for v in report.violation_details)


def test_tcso_05_ordinary_manual_correction_never_materializes_the_deviation():
    """seed_real_object's own default Site is ORDINARY (benchmarks/
    real_object_production.py) -- a manually forced third-consecutive-day
    Assignment must not materialize a THIRD-CONSECUTIVE-SHIFT-01 Deviation
    here, unlike test_t058.py's T58-13 (explicitly switched to OCHRONA)."""
    from rota.domain import AssignmentRole, AssignmentState, Assignment

    conn = connect(":memory:")
    pstate = seed_real_object(conn, case_id="tcso-manual", month=date(2026, 8, 1), seed=5058)
    site_id = pstate.site.site_id
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=date(2026, 8, 1), coordinator_id="COORD-1", effective_from=date(2026, 8, 1),
    )
    assert result.status == "FEASIBLE"
    v1 = plan_ops.select_candidate(
        conn, site_id=site_id, month=date(2026, 8, 1), candidate=result.candidates[0], coordinator_id="COORD-1",
    )
    snapshot = get_schedule_snapshot(conn, v1.version_id)
    dates_by_employee: dict[str, set] = {}
    for a in snapshot.assignments:
        if a.role == AssignmentRole.PRIMARY and a.covers_demand_id:
            dates_by_employee.setdefault(a.employee_id, set()).add(a.start_datetime.date())
    demands_by_date = {}
    for d in snapshot.shift_demands:
        demands_by_date.setdefault(d.start_datetime.date(), []).append(d)

    employee_id = None
    third_day_demand = None
    for candidate_employee, dates in dates_by_employee.items():
        for d in dates:
            if (d + timedelta(days=1)) in dates and (d + timedelta(days=2)) not in dates:
                for demand in demands_by_date.get(d + timedelta(days=2), []):
                    employee_id = candidate_employee
                    third_day_demand = demand
                    break
            if third_day_demand is not None:
                break
        if third_day_demand is not None:
            break
    if third_day_demand is None:
        return  # this seed's roster shape offers no same-employee 2-consecutive-days + open 3rd day -- nothing to force
    forced = Assignment(
        f"AS-forced-{third_day_demand.demand_id}", "", employee_id, third_day_demand.start_datetime,
        third_day_demand.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False,
        third_day_demand.demand_id, None,
    )
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=date(2026, 8, 1), coordinator_id="COORD-1",
        effective_from=date(2026, 8, 2), upsert_assignments=[forced],
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    assert not any(d.source_reference == "THIRD-CONSECUTIVE-SHIFT-01" for d in v2_snapshot.deviations)


if __name__ == "__main__":
    print("test_third_consecutive_shift_regime_scope module OK")
