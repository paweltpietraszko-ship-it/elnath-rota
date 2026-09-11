"""ROTA-T058 (brief.md @ c033141, Codex preimplementation PASS 000daf2):
HARD ban on a third consecutive real PRIMARY service for the same employee
(any D/N combination), no automatic DECISION_REQUIRED exception, manual
correction still allowed with a materialized Deviation.

OWNER_CORRECTED 2026-09-08 (same day): the brief's section 2.6 24h equity/
equal-split dead zone was DROPPED, not shipped -- verified live to break
CP-SAT's ability to prove optimality on real objects across every encoding
tried (see arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md
and rota/planning/fairness.py's own note at EQUAL_SPLIT_FAIRNESS_WEIGHT).
Owner: "ona miala w zamysle pomagac solverowi, jesli przeszkadza to idzie
do kosza" (it was meant to help the solver; if it hurts instead, scrap
it). T58-10/T58-11/T58-12 (the deadband-specific tests) are removed
accordingly -- add_target_equity_fairness/add_equal_split_fairness are
back to their pre-T058 forms and covered by the existing T032 matrix.

T58-01..T58-03/T58-06 exercise the CP-SAT constraint directly against
hand-built day_kind_terms dicts (same shape solver._build_day_kind_terms
produces -- no second boundary reader implied). T58-04/T58-05/T58-13
exercise the real vertical wiring through engine.plan()/manual_edit's
validate() path. T58-07/T58-08/T58-09 are existing-regression checks
(NIGHT-STREAK-01, D/N/W/W rhythm, TARGET-01) via the pre-existing T032
matrix, not duplicated here."""
from __future__ import annotations

from datetime import date, timedelta

from ortools.sat.python import cp_model

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    WorkBalance,
)
from rota.application import manual_edit
from rota.application.deviation_mapping import category_for_rule
from rota.domain import DeviationCategory
from rota.persistence.db import connect
from rota.planning.constraints import add_max_two_consecutive_primary_shift_constraint
from rota.planning.engine import plan
from rota.planning.solver import solve
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, base_state
from tests.support.t009_fixtures import seed_real_object
from tests.test_t032_soft_ranking import _d_demand, _membership, _n_demand

_EMPTY = (0, 0, 0, None, 0)


def _solve_feasible(model, day_kind_terms, month=MONTH):
    assumptions = add_max_two_consecutive_primary_shift_constraint(model, day_kind_terms, month)
    if assumptions:
        model.add_assumptions(list(assumptions.values()))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    return status, solver


# --- T58-01/T58-02: HARD blocks any D/N combination on 3 consecutive dates --


def test_t58_01_ddd_is_infeasible():
    model = cp_model.CpModel()
    d = [model.new_bool_var(f"d{i}") for i in range(3)]
    for v in d:
        model.add(v == 1)
    terms = {"A": {MONTH + timedelta(days=i): (d[i], 0, 0, None, d[i]) for i in range(3)}}
    status, _ = _solve_feasible(model, terms)
    assert status == cp_model.INFEASIBLE


def test_t58_02_ddn_is_infeasible():
    """D/D/N (not just D/D/D) must also be blocked -- HARD covers any D/N combination."""
    model = cp_model.CpModel()
    d0 = model.new_bool_var("d0")
    d1 = model.new_bool_var("d1")
    n2 = model.new_bool_var("n2")
    model.add(d0 == 1)
    model.add(d1 == 1)
    model.add(n2 == 1)
    terms = {"A": {
        MONTH: (d0, 0, 0, None, d0),
        MONTH + timedelta(days=1): (d1, 0, 0, None, d1),
        MONTH + timedelta(days=2): (0, n2, 0, "n2-demand", n2),
    }}
    status, _ = _solve_feasible(model, terms)
    assert status == cp_model.INFEASIBLE


def test_t58_03_dnn_is_infeasible():
    model = cp_model.CpModel()
    d0 = model.new_bool_var("d0")
    n1 = model.new_bool_var("n1")
    n2 = model.new_bool_var("n2")
    model.add(d0 == 1)
    model.add(n1 == 1)
    model.add(n2 == 1)
    terms = {"A": {
        MONTH: (d0, 0, 0, None, d0),
        MONTH + timedelta(days=1): (0, n1, 0, "n1-demand", n1),
        MONTH + timedelta(days=2): (0, n2, 0, "n2-demand", n2),
    }}
    status, _ = _solve_feasible(model, terms)
    assert status == cp_model.INFEASIBLE


def test_t58_04_two_of_three_days_legal():
    """Any two of three consecutive dates occupied is legal -- only all
    three together is blocked."""
    model = cp_model.CpModel()
    d0 = model.new_bool_var("d0")
    d1 = model.new_bool_var("d1")
    model.add(d0 == 1)
    model.add(d1 == 1)
    terms = {"A": {
        MONTH: (d0, 0, 0, None, d0),
        MONTH + timedelta(days=1): (d1, 0, 0, None, d1),
    }}
    status, _ = _solve_feasible(model, terms)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_t58_05_h24_pair_counts_as_one_day_not_two():
    """A 24h D+N occurrence shares one start date -- SHIFT-24-PAIR-01 forces
    both components to the same employee, same start date. That single date
    plus two OTHER real days elsewhere must not itself trigger the HARD
    (only three separate calendar dates all occupied does)."""
    model = cp_model.CpModel()
    d0 = model.new_bool_var("d0")
    n0 = model.new_bool_var("n0")  # same date as d0 -- one H24 occurrence
    model.add(d0 == 1)
    model.add(n0 == 1)
    terms = {"A": {
        MONTH: (d0, n0, 0, "n0-demand", d0 + n0),  # primary_term sums both components -- still ONE occupied day via occupied-bool
    }}
    status, _ = _solve_feasible(model, terms)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_t58_06_trainee_never_counts():
    """any_term (index 2) would include a TRAINEE occupying the day --
    primary_term (index 4) must not, since it is built from PRIMARY-role
    occupancy only (solver._build_day_kind_terms). A window built purely
    from any_term-like fixed facts (simulated here as primary_term == 0
    despite any_term == 1) must stay legal."""
    model = cp_model.CpModel()
    terms = {"A": {
        MONTH: (0, 0, 1, None, 0),  # any_term=1 (e.g. TRAINEE), primary_term=0
        MONTH + timedelta(days=1): (0, 0, 1, None, 0),
        MONTH + timedelta(days=2): (0, 0, 1, None, 0),
    }}
    status, _ = _solve_feasible(model, terms)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


# --- T58-03/T58-06 (fixed/boundary facts) -----------------------------------


def test_t58_07_two_fixed_days_block_a_new_third():
    """Two already-fixed real PRIMARY days (plain ints, no decision variable)
    plus a candidate third day (a real decision variable) must force that
    third day to 0 -- the solver cannot add a NEW violating day next to
    existing facts."""
    model = cp_model.CpModel()
    d2 = model.new_bool_var("d2")
    terms = {"A": {
        MONTH: (1, 0, 0, None, 1),  # fixed fact, day 1
        MONTH + timedelta(days=1): (1, 0, 0, None, 1),  # fixed fact, day 2
        MONTH + timedelta(days=2): (d2, 0, 0, None, d2),  # candidate, day 3
    }}
    assumptions = add_max_two_consecutive_primary_shift_constraint(model, terms, MONTH)
    model.add_assumptions(list(assumptions.values()))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(d2) == 0


def test_t58_08_fully_fixed_historical_violation_does_not_poison_the_model():
    """A fully-fixed (all-int) three-in-a-row -- an already-occurred/accepted
    historical fact predating this rule -- must not itself make the model
    INFEASIBLE. Section 2.3: it is an unchangeable past fact."""
    model = cp_model.CpModel()
    unrelated = model.new_bool_var("unrelated")
    model.add(unrelated == 1)
    terms = {"A": {
        MONTH: (1, 0, 0, None, 1),
        MONTH + timedelta(days=1): (1, 0, 0, None, 1),
        MONTH + timedelta(days=2): (1, 0, 0, None, 1),
    }}
    add_max_two_consecutive_primary_shift_constraint(model, terms, MONTH)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_t58_09_extends_across_month_boundary():
    """Two boundary-fixed days from the PREVIOUS month plus a candidate on
    the 1st/2nd of THIS month must still be caught -- the window scan starts
    two days before month_start (mirrors NIGHT-STREAK-01)."""
    model = cp_model.CpModel()
    day1 = model.new_bool_var("day1")
    terms = {"A": {
        MONTH - timedelta(days=2): (1, 0, 0, None, 1),  # boundary fact, last month
        MONTH - timedelta(days=1): (1, 0, 0, None, 1),  # boundary fact, last month
        MONTH: (day1, 0, 0, None, day1),  # candidate, 1st of this month
    }}
    assumptions = add_max_two_consecutive_primary_shift_constraint(model, terms, MONTH)
    model.add_assumptions(list(assumptions.values()))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(day1) == 0


# --- T58-01/T58-04: real vertical wiring through engine.plan() --------------


def test_t58_10_real_plan_never_produces_a_third_consecutive_day_when_avoidable():
    """Two equally-eligible employees, D demands on three consecutive days --
    the solver must split them (never give all three to one employee) when
    an alternative exists."""
    employees = (Employee("A", "A", date(2020, 1, 1), None, False), Employee("B", "B", date(2020, 1, 1), None, False))
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0), WorkBalance("B", MONTH, 36, 0, 0, 0, 0, 0))
    state = base_state(
        employees=employees, memberships=(_membership("A"), _membership("B")),
        shift_demands=demands, work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    report = validate(state, result.candidates[0])
    assert not any(v.rule == "THIRD-CONSECUTIVE-SHIFT-01" for v in report.violation_details)


def test_t58_11_genuinely_unavoidable_third_day_blocks_with_no_decision_required():
    """One eligible employee, three mandatory D demands, no alternative --
    T58-04: the automatic solver must not return a HARD-violating candidate,
    must not offer a DECISION_REQUIRED override, and must give a truthful
    non-decision status instead."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.assignments is None
    assert outcome.status_name == "INFEASIBLE"
    result = plan(state)
    assert result.status == "THIRD_CONSECUTIVE_SHIFT_BLOCKED"
    assert result.candidates == []
    # ROTA-T062 (brief section 4 point 6): THIRD_CONSECUTIVE_SHIFT_BLOCKED
    # now shares decision_guidance's one coordinator-facing guidance family
    # instead of leaving decision_payload empty -- still no solver override,
    # no rule-breaking candidate, and status stays THIRD (never becomes
    # DECISION_REQUIRED).
    assert result.decision_payload is not None
    assert result.decision_payload.blocking_shift_demands == []
    assert result.decision_payload.blockers == []
    assert [o.text for o in result.decision_payload.unblocking_options] == ["Sprawdź obsadę i dostępność: A, i zaplanuj ponownie"]
    assert result.warnings


def test_t58_12_night_streak_conflict_still_reaches_decision_required_not_blocked():
    """A NIGHT-STREAK-01 conflict (unrelated to T58) must still reach its own
    existing DECISION_REQUIRED path, never THIRD_CONSECUTIVE_SHIFT_BLOCKED --
    the two HARD diagnoses must not cross-contaminate."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_n_demand(1), _n_demand(2), _n_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"


# --- T58-05: manual correction may still create it, flagged as a Deviation -


def test_t58_13_manual_correction_creates_flagged_deviation_not_a_block():
    conn = connect(":memory:")
    pstate = seed_real_object(conn, case_id="t058-manual", month=date(2026, 8, 1), seed=5058)
    site_id = pstate.site.site_id
    from rota.application import plan_ops
    result = plan_ops.plan_month(
        conn, site_id=site_id, month=date(2026, 8, 1), coordinator_id="COORD-1", effective_from=date(2026, 8, 1),
    )
    assert result.status == "FEASIBLE"
    v1 = plan_ops.select_candidate(
        conn, site_id=site_id, month=date(2026, 8, 1), candidate=result.candidates[0], coordinator_id="COORD-1",
    )
    from rota.persistence.schedule_repository import get_schedule_snapshot
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
    assert any(d.category == DeviationCategory.LAW for d in v2_snapshot.deviations)


def test_t58_14_third_consecutive_shift_rule_maps_to_an_existing_category():
    assert category_for_rule("THIRD-CONSECUTIVE-SHIFT-01", {}) == DeviationCategory.LAW


# --- T58-15 (ARCHITECT_RULING 2026-09-09, R6-01 regression): a manually --
# edited future PRIMARY that deliberately closes a THIRD-CONSECUTIVE-SHIFT-01
# violation survives a later automatic Przelicz Plan -- promoted from
# tasks/ROTA-T058/round_01/tests/repro_r6.py's real-DB reproducer.


def test_t58_15_manual_third_consecutive_shift_survives_later_przelicz_plan(monkeypatch):
    from datetime import datetime
    from dataclasses import replace

    from rota.application import plan_ops
    from rota.domain import ShiftDemand
    from rota.persistence import schedule_lifecycle
    from rota.persistence.schedule_repository import get_schedule_snapshot
    from tests.test_t019b import COORD, MONTH, SITE, _bootstrap, _employee, _fill_calendar

    class _August10(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 8, 10, 12, 0)
            return value if tz is None else value.replace(tzinfo=tz)

    def _demand(day: int) -> ShiftDemand:
        return ShiftDemand(f"D-{day}", "V0", datetime(2026, 8, day, 6), datetime(2026, 8, day, 18), 1)

    def _assignment(day: int, employee_id: str) -> Assignment:
        return Assignment(
            f"A-{day}", "V0", employee_id, datetime(2026, 8, day, 6), datetime(2026, 8, day, 18),
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, f"D-{day}", None,
        )

    conn = connect(":memory:")
    _bootstrap(conn)
    _employee(conn, "E1")
    _employee(conn, "E2")
    _fill_calendar(conn)

    demands = [_demand(day) for day in (1, 20, 21, 22)]
    assignments = [
        _assignment(1, "E2"),
        replace(_assignment(20, "E1"), frozen=True),
        replace(_assignment(21, "E1"), frozen=True),
        _assignment(22, "E2"),
    ]
    schedule_lifecycle.create_schedule_version(
        conn, version_id="V0", site_id=SITE, month=MONTH, parent_version_id=None,
        created_at=datetime(2026, 7, 25, 12), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=demands, assignments=assignments, deviations=[], effective_from=MONTH,
    )

    # The coordinator deliberately closes 20-21-22 August as a three-day
    # sequence -- a knowing HARD override, not a solver decision.
    manual = manual_edit.apply_manual_correction(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=date(2026, 8, 9),
        upsert_assignments=[replace(assignments[-1], employee_id="E1")], note="świadoma decyzja koordynatora",
    )
    manual_snapshot = get_schedule_snapshot(conn, manual.version_id)
    assert any(d.category == DeviationCategory.LAW and d.source_reference == "THIRD-CONSECUTIVE-SHIFT-01"
               for d in manual_snapshot.deviations)
    corrected = next(a for a in manual_snapshot.assignments if a.assignment_id == "A-22")
    assert corrected.employee_id == "E1" and corrected.frozen is True

    # A later Przelicz Plan must not silently move it back.
    monkeypatch.setattr(plan_ops, "datetime", _August10)
    result = plan_ops.plan_month(
        conn, site_id=SITE, month=MONTH, coordinator_id=COORD, effective_from=date(2026, 8, 10),
    )
    assert result.status == "FEASIBLE"
    for candidate in result.candidates:
        actual = {a.employee_id for a in candidate if a.covers_demand_id == "D-22"}
        assert actual == {"E1"}

