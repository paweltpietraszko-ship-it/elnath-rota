"""ROTA-T023 Checkpoint B test matrix (brief.md section 17 subset, owner-
authorized narrow TASK_SCOPE amendment 2026-08-22): consumer equality
(T23-30..34), R5-3 REPLAN acceptance cutover (T23-R5-3A..F), HARD/
regression closure for this checkpoint (T23-50..54).

T23-35 ("T020 totals equal canonical source-mode projection") is explicitly
DEFERRED TO CHECKPOINT C PER brief.md SECTION 16 -- schedule_export.py is
Checkpoint C's own allowed production subset and is not yet rewired to the
canonical absence path. Not tested here; not a Checkpoint B gap or FAIL.

Reuses tests/test_t023.py's Checkpoint A fixtures (SITE/COORDINATOR/MONTH,
_setup, _employee, _primary, _accept_one, _accept_version, _leave) rather
than duplicating them -- no Checkpoint A test is moved, removed or
duplicated into this file."""
from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from rota.application import plan_ops
from rota.application.errors import CandidateRejected
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import site_memory
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.work_balance_repository import reconstruct_month_balance, save_work_balance_target
from rota.application.analytics_read import analytics_for_site_month
from rota.application.balance_read import quarter_balance
from rota.planning.engine import plan
from rota.planning.solver import _effective_targets
from rota.site_memory_types import CoordinatorActionKind
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state
from tests.test_t023 import (
    COORDINATOR,
    MONTH,
    SITE,
    _accept_one,
    _accept_version,
    _employee,
    _leave,
    _primary,
    _seed_full_month_calendar,
    _setup,
)

BASE_SHA = "e05dfb7dd4463370bf8174db7ae58a9b984cf99e"
# R5-3 needs facts genuinely BEFORE real wall-clock "now" (cutover_at =
# datetime.now() at select_candidate call time) -- MONTH (2027-03, reused
# from test_t023.py) is itself always in the future, so a dedicated past
# month is used for every "pre-cutover" fact below. ScheduleVersion content
# requires each ShiftDemand's own date to fall inside its version's month.
PAST_MONTH = date(2020, 1, 1)
PAST = datetime(2020, 1, 6, 5, 0)
PAST_END = datetime(2020, 1, 6, 17, 0)


def _full_month_calendar(month: date):
    import calendar as calendar_module

    from rota.domain import CalendarDay

    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


def _local_membership(employee_id: str, site_id: str = SITE_ID) -> SiteMembership:
    return SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


# --- T23-30..34 Consumer equality --------------------------------------------


def test_t23_30_workbalance_absence_hours_equals_canonical_and_effective_target(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_work_balance_target(conn, employee_id="A", month=MONTH, target_hours=100)
    wb = reconstruct_month_balance(conn, employee_id="A", month=MONTH)
    assert wb.absence_hours == 12  # exact scheduled hours, the canonical result already proven by test_t023.py's Checkpoint A matrix
    effective_target = max(0, wb.target_hours - wb.absence_hours)
    assert wb.month_balance == wb.planned_hours + wb.realized_hours - effective_target


def test_t23_31_equal_canonical_sick_leave_results_reduce_target_equally(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    # One shared accepted ScheduleVersion for both Employees at SITE -- two
    # separate accepted versions for the same (site, month) would make the
    # second supersede the first as CURRENT, breaking the first Employee's
    # own accepted-plan resolution (unrelated to what this test proves).
    d_a, a_a = _primary("D-8a", "A-8a", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-1")
    d_b, a_b = _primary("D-8b", "A-8b", "B", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), version_id="SV-1")
    _accept_version(conn, version_id="SV-1", pairs=[(d_a, a_a), (d_b, a_b)], effective_from=MONTH, accepted_at=datetime(2020, 3, 1, 8, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    _leave(conn, employee_id="B", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_work_balance_target(conn, employee_id="A", month=MONTH, target_hours=100)
    save_work_balance_target(conn, employee_id="B", month=MONTH, target_hours=100)
    wb_a = reconstruct_month_balance(conn, employee_id="A", month=MONTH)
    wb_b = reconstruct_month_balance(conn, employee_id="B", month=MONTH)
    assert wb_a.absence_hours == wb_b.absence_hours == 12  # equal canonical SICK vs LEAVE result for equal scheduled hours
    targets = _effective_targets(base_state(work_balances=(wb_a, wb_b)))
    assert targets["A"] == targets["B"] == 88


def test_t23_32_solver_effective_targets_reads_absence_hours_field_only() -> None:
    """No CalendarDay/flat recount/source-mode choice inside the solver --
    _effective_targets consumes WorkBalance.absence_hours as-is."""
    import inspect

    source = inspect.getsource(_effective_targets)
    assert "calendar_days" not in source
    assert "excused_absence_days_in_month" not in source
    assert "wb.absence_hours" in source


def test_t23_33_analytics_matches_workbalance_absence_and_effective_target(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_work_balance_target(conn, employee_id="A", month=MONTH, target_hours=100)
    wb = reconstruct_month_balance(conn, employee_id="A", month=MONTH)
    view = analytics_for_site_month(conn, site_id=SITE, month=MONTH)
    row = next(r for r in view.rows if r.employee_id == "A")
    assert row.month_data.effective_target_hours == wb.target_hours - wb.absence_hours
    assert row.month_data.month_balance == wb.month_balance


def test_t23_34_quarter_uses_same_month_results_and_never_guesses(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    for m in (date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)):
        save_work_balance_target(conn, employee_id="A", month=m, target_hours=100)
    balances, warnings = quarter_balance(conn, employee_id="A", quarter_first_month=date(2027, 3, 1))
    assert warnings == []
    march = next(b for b in balances if b.month == date(2027, 3, 1))
    direct = reconstruct_month_balance(
        conn, employee_id="A", month=date(2027, 3, 1), quarter_balance_before=march.quarter_balance - march.month_balance,
    )
    assert march.absence_hours == direct.absence_hours == 12
    assert march.month_balance == direct.month_balance  # quarter reconstruction matches the same per-month canonical result

    conn2 = _setup(tmp_path, db_name="rota2.db")
    for m in (date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)):
        save_work_balance_target(conn2, employee_id="A", month=m, target_hours=100)
    _leave(conn2, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))  # no accepted plan anywhere -> MISSING
    balances2, warnings2 = quarter_balance(conn2, employee_id="A", quarter_first_month=date(2027, 3, 1))
    assert balances2 == []
    assert warnings2 != []  # never a guessed partial quarter result


# --- T23-R5-3 REPLAN acceptance cutover --------------------------------------


def _seed_parent_and_child(conn, *, prior_facts, extra_child_demands=(), month=MONTH):
    """Accepts SV-1 as the parent carrying prior_facts (each a
    (demand_id, assignment_id, employee_id, start, end, state) tuple), then
    creates SV-2 as its REPLAN child (WORKING, current) directly -- the same
    clone-then-select shape as plan_ops.replan(), without needing the
    solver. extra_child_demands are open (uncovered) ShiftDemands added only
    to the child, modelling fresh REPLAN demand generation. assemble_
    planning_state requires a fully seeded calendar for `month`
    unconditionally, independent of any absence-specific requirement."""
    _seed_full_month_calendar(conn, month, month)
    pairs = [
        _primary(demand_id, assignment_id, employee_id, start, end, version_id="SV-1", state=state)
        for demand_id, assignment_id, employee_id, start, end, state in prior_facts
    ]
    _accept_version(conn, version_id="SV-1", pairs=pairs, effective_from=month, accepted_at=datetime(2020, 1, 1, 8, 0), month=month)
    child_assignments = [replace(a, schedule_version_id="SV-2") for _, a in pairs]
    child_demands = [replace(d, schedule_version_id="SV-2") for d, _ in pairs]
    child_demands += [replace(d, schedule_version_id="SV-2") for d in extra_child_demands]
    lifecycle.create_schedule_version(
        conn, version_id="SV-2", site_id=SITE, month=month, parent_version_id="SV-1",
        created_at=datetime(2020, 1, 2, 8, 0), created_by=COORDINATOR, applied_rule_version_ids=[],
        shift_demands=child_demands, assignments=child_assignments, deviations=[], effective_from=month,
    )
    return "SV-2", child_assignments


def test_t23_r5_3a_candidate_may_change_future_primary_at_or_after_cutover(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    child_id, prior = _seed_parent_and_child(conn, prior_facts=[
        ("D-FUT", "A-FUT", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), AssignmentState.PLANNED),
    ], month=MONTH)
    candidate = [replace(prior[0], employee_id="B")]  # solver reassigns the still-future shift to B
    selected = plan_ops.select_candidate(conn, site_id=SITE, month=MONTH, candidate=candidate, coordinator_id=COORDINATOR)
    # ROTA-T057 (BOARD.md OWNER_RULING 2026-09-06): acceptance always creates
    # a NEW child now, never overwrites "SV-2" in place -- history preserved.
    assert selected.version_id != "SV-2"
    assert selected.parent_version_id == "SV-2"
    snapshot = get_schedule_snapshot(conn, selected.version_id)
    assert snapshot.assignments[0].employee_id == "B"


def test_t23_r5_3b_removing_pre_cutover_primary_rejected(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_parent_and_child(conn, prior_facts=[
        ("D-PAST", "A-PAST", "A", PAST, PAST_END, AssignmentState.PLANNED),
    ], month=PAST_MONTH)
    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(conn, site_id=SITE, month=PAST_MONTH, candidate=[], coordinator_id=COORDINATOR)


@pytest.mark.parametrize("mutation", ["employee_id", "frozen", "operational_code"])
def test_t23_r5_3c_mutating_pre_cutover_primary_rejected(tmp_path, mutation) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _, prior = _seed_parent_and_child(conn, prior_facts=[
        ("D-PAST", "A-PAST", "A", PAST, PAST_END, AssignmentState.PLANNED),
    ], month=PAST_MONTH)
    field_value = {"employee_id": "B", "frozen": True, "operational_code": "X"}[mutation]
    mutated = replace(prior[0], **{mutation: field_value})
    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(conn, site_id=SITE, month=PAST_MONTH, candidate=[mutated], coordinator_id=COORDINATOR)


def test_t23_r5_3d_new_pre_cutover_primary_added_rejected(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    extra_demand = ShiftDemand("D-NEW-PAST", "SV-2", PAST, PAST_END, 1)
    _seed_parent_and_child(conn, prior_facts=[], extra_child_demands=[extra_demand], month=PAST_MONTH)
    new_past = _primary("D-NEW-PAST", "A-NEW-PAST", "B", PAST, PAST_END, version_id="SV-2")[1]
    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(conn, site_id=SITE, month=PAST_MONTH, candidate=[new_past], coordinator_id=COORDINATOR)


def test_t23_r5_3e_cutover_timestamp_equals_recorded_at(tmp_path, monkeypatch) -> None:
    """No behavioral seam exists to read cutover_at directly, so this proves
    equality indirectly: a PRIMARY starting EXACTLY at the frozen clock value
    is, by the strict '<' comparison, never pre-cutover -- if select_candidate
    used a different value for the cutover check than for recorded_at, either
    this candidate would be wrongly rejected or the persisted recorded_at
    would not equal fixed_now."""
    conn = _setup(tmp_path)
    edge_month = date(2025, 6, 1)
    fixed_now = datetime(2025, 6, 1, 12, 0, 0)
    child_id, prior = _seed_parent_and_child(conn, prior_facts=[
        ("D-EDGE", "A-EDGE", "A", fixed_now, fixed_now + timedelta(hours=8), AssignmentState.PLANNED),
    ], month=edge_month)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(plan_ops, "datetime", _FixedDateTime)
    selected = plan_ops.select_candidate(conn, site_id=SITE, month=edge_month, candidate=prior, coordinator_id=COORDINATOR)
    # ROTA-T057: the action is now recorded against the newly-created child,
    # not the pre-existing `child_id` being replaced.
    actions = site_memory.list_coordinator_actions(conn, action_kind=CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED)
    matching = [a for a in actions if a.schedule_version_id == selected.version_id]
    assert matching[-1].recorded_at == fixed_now


def test_t23_r5_3f_initial_plan_not_subject_to_cutover_guard(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, PAST_MONTH, PAST_MONTH)
    demand = ShiftDemand("D-PAST", "SV-1", PAST, PAST_END, 1)
    assignment = Assignment("A-PAST", "SV-1", "A", PAST, PAST_END, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-PAST", None)
    lifecycle.create_schedule_version(
        conn, version_id="SV-1", site_id=SITE, month=PAST_MONTH, parent_version_id=None,
        created_at=datetime(2020, 1, 1, 8, 0), created_by=COORDINATOR, applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[assignment], deviations=[], effective_from=PAST_MONTH,
    )
    mutated = replace(assignment, frozen=True)  # rejected on a REPLAN child per T23-R5-3C; here parent_version_id is None, so R5-3 does not apply
    selected = plan_ops.select_candidate(conn, site_id=SITE, month=PAST_MONTH, candidate=[mutated], coordinator_id=COORDINATOR)
    # ROTA-T057: acceptance always creates a new child now, even from a
    # parentless base version -- SV-1 stays in history, untouched.
    assert selected.version_id != "SV-1"
    assert selected.parent_version_id == "SV-1"


# --- T23-50..54 HARD / regressions -------------------------------------------


def test_t23_50_sick_hard_unavailable_across_inclusive_range() -> None:
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    for day in (1, 3, 5):  # start, middle, end of the inclusive range
        demand = ShiftDemand(f"D-{day}", "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)
        state = base_state(
            employees=(Employee("A", "A", date(2026, 9, 1), None, False),), memberships=(_local_membership("A"),),
            shift_demands=(demand,), availability_records=(sick,), calendar_days=_full_month_calendar(date(2026, 10, 1)),
        )
        result = plan(state)
        assert result.status == "DECISION_REQUIRED"


def test_t23_51_leave_granted_hard_unavailable_outside_range_eligible() -> None:
    leave = AvailabilityRecord("l1", "l1v1", "A", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    inside = ShiftDemand("D-3", "test-v1", datetime(2026, 10, 3, 5, 0), datetime(2026, 10, 3, 17, 0), 1)
    state_inside = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(inside,), availability_records=(leave,))
    assert plan(state_inside).status == "DECISION_REQUIRED"

    outside = ShiftDemand("D-6", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    state_outside = base_state(employees=(employee,), memberships=(_local_membership("A"),), shift_demands=(outside,), availability_records=(leave,))
    result_outside = plan(state_outside)
    assert result_outside.status == "FEASIBLE"
    assert result_outside.candidates[0][0].employee_id == "A"


def test_t23_52_absent_employee_never_covers_replacement_or_decision_required() -> None:
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 5), True, None, None)
    demand = ShiftDemand("D-3", "test-v1", datetime(2026, 10, 3, 5, 0), datetime(2026, 10, 3, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    employee_b = Employee("B", "B", date(2026, 9, 1), None, False)

    with_replacement = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(sick,), calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result_with_b = plan(with_replacement)
    assert result_with_b.status == "FEASIBLE"
    assert result_with_b.candidates[0][0].employee_id == "B"  # absent A never covers it

    without_replacement = base_state(
        employees=(employee_a,), memberships=(_local_membership("A"),),
        shift_demands=(demand,), availability_records=(sick,), calendar_days=_full_month_calendar(date(2026, 10, 1)),
    )
    result_alone = plan(without_replacement)
    assert result_alone.status == "DECISION_REQUIRED"  # no nominal Assignment to the absent Employee either


def test_t23_53_calendarday_no_longer_changes_post_plan_absence_hours(tmp_path) -> None:
    from rota.domain import CalendarDay
    from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
    from rota.persistence.calendar_repository import save_calendar_day

    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    save_calendar_day(conn, CalendarDay(date(2027, 3, 8), holiday=True))  # unrelated calendar rule, still recorded
    record = _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.days[0].status == "BOUND"
    assert snapshot.days[0].hours == 12  # exact scheduled hours, unaffected by holiday=True


def test_t23_54_t012_legality_rest_modules_unmodified_by_checkpoint_b() -> None:
    """T012 normal/emergency 24h legality/rest semantics live in
    eligibility.py/constraints.py/work_periods.py -- all explicitly OUT OF
    SCOPE for T023 (brief.md section 15). This is a source-diff proof that
    Checkpoint B's WorkBalance/solver/analytics/REPLAN rewiring touched none
    of them, not a duplicate of tests/test_t012.py's own behavioral
    assertions (already unmodified and still green in the full suite)."""
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["git", "diff", "--name-only", BASE_SHA, "--",
         "rota/planning/eligibility.py", "rota/planning/constraints.py", "rota/planning/work_periods.py"],
        capture_output=True, text=True, cwd=repo_root,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
