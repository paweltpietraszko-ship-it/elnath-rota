"""ROTA-PRESERVED-FACTS-REPLAN (tasks/ROTA-PRESERVED-FACTS-REPLAN/brief.md
section 5, R1-R5): Przelicz Plan after a historical NN and after a saved,
fully fixed N/N/N works for the still-plannable future; the preserved facts
stay exact and visible; new proposals still obey every HARD rule. Real write
paths (HTTP mark-not-worked / manual-correction / plan / select-candidate)
plus the shared classifier on real assembled state."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from rota.application.assembler import assemble_planning_state
from rota.domain import AssignmentRole, AssignmentState, DeviationCategory, ShiftKind
from rota.persistence import schedule_lifecycle
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.planning.engine import plan
from rota.planning.preserved_violations import gating_hard_pass, is_preserved_violation
from rota.planning.validator import validate
from rota.planning.validator_shared import ViolationDetail
from tests import test_cloud_review_schedule_fixes as _cr
from tests.test_cloud_review_schedule_fixes import COORD, SITE, _assignment, _assignment_in, _calendar, _demand, _month_url

# Same OCHRONA site/5 employees/HTTP client as ROTA-CLOUD-REVIEW-FIXES.
conn = _cr.conn
client = _cr.client

EMPS = ["E1", "E2", "E3", "E4", "E5"]


def _days_in(month: date) -> int:
    nxt = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    return (nxt - month).days


def _rotation(month: date, version_id: str = "V0", *, frozen: dict | None = None, overrides: dict | None = None):
    """Two shifts a day, five people, no accidental N/N/N (E_k gets N only on
    days d with 2d+1 = k mod 5). overrides[(kind, day)] = employee."""
    demands, assignments = [], []
    for d in range(1, _days_in(month) + 1):
        for kind, idx in ((ShiftKind.D, 2 * d), (ShiftKind.N, 2 * d + 1)):
            demand = _demand(kind, date(month.year, month.month, d), version_id)
            employee = (overrides or {}).get((kind, d), EMPS[idx % 5])
            a = _assignment(demand, employee)
            if (frozen or {}).get((kind, d)):
                a = replace(a, frozen=True)
            demands.append(demand)
            assignments.append(a)
    return demands, assignments


def _save(conn, month, demands, assignments, version_id="V0", effective_from=None):
    _calendar(conn, month)
    schedule_lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=SITE, month=month, parent_version_id=None,
        created_at=datetime(2026, 1, 1, 8), created_by=COORD, applied_rule_version_ids=[],
        shift_demands=demands, assignments=assignments, deviations=[], effective_from=effective_from or month,
    )


def _plan(client, month):
    resp = client.post(_month_url(month, "/plan"), json={"effective_from": None})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _accept(client, month, candidate):
    return client.post(_month_url(month, "/select-candidate"), json={"candidate": [_assignment_in(a) for a in candidate]})


def _n_days(candidate, employee_id, month):
    return sorted(
        date.fromisoformat(a["start_datetime"][:10]) for a in candidate
        if a["employee_id"] == employee_id and a["role"] == "PRIMARY" and a["state"] != "CANCELLED"
        and a["start_datetime"][11:13] == "18" and a["start_datetime"][:7] == month.isoformat()[:7]
    )


# --- R1: historical NN -> Przelicz -> accept --------------------------------

def _nn_yesterday(conn, client):
    yesterday = date.today() - timedelta(days=1)
    month = yesterday.replace(day=1)
    demands, assignments = _rotation(month)
    _save(conn, month, demands, assignments, effective_from=month - timedelta(days=5))
    target = next(a for a in assignments if a.start_datetime.date() == yesterday and a.start_datetime.hour == 6)
    resp = client.post(_month_url(month, "/manual-correction/mark-not-worked"), json={"assignment_id": target.assignment_id})
    assert resp.status_code == 200, resp.text
    return month, target


def test_r1_nn_yesterday_replan_and_accept_keeps_exact_nn_and_visible_gap(conn, client):
    month, target = _nn_yesterday(conn, client)
    parent_id = get_current_version_id(conn, SITE, month)
    parent = get_schedule_snapshot(conn, parent_id)
    result = _plan(client, month)
    assert result["status"] == "FEASIBLE", result.get("error_message")
    candidate = result["candidates"][0]
    nn = [a for a in candidate if a["assignment_id"] == target.assignment_id]
    assert len(nn) == 1 and nn[0]["state"] == "CANCELLED" and nn[0]["operational_code"] == "NN"
    # never back-filled: no working PRIMARY on the NN demand
    assert not [a for a in candidate if a["covers_demand_id"] == target.covers_demand_id and a["state"] != "CANCELLED"]
    assert _accept(client, month, candidate).status_code == 204
    child_id = get_current_version_id(conn, SITE, month)
    assert child_id != parent_id
    child = get_schedule_snapshot(conn, child_id)
    child_nn = next(a for a in child.assignments if a.assignment_id == target.assignment_id)
    assert (child_nn.state, child_nn.operational_code, child_nn.employee_id) == (AssignmentState.CANCELLED, "NN", target.employee_id)
    gaps = [d for d in child.deviations if d.source_reference == "COVERAGE-01"]
    assert [d.affected_assignment_or_employee for d in gaps] == [target.covers_demand_id]
    assert gaps[0].category == DeviationCategory.COVERAGE and gaps[0].acknowledged is False
    assert get_schedule_snapshot(conn, parent_id) == parent  # parent untouched
    month_view = client.get(_month_url(month)).json()
    assert month_view["current_version"]["version_id"] == child_id


def test_r5_forged_candidate_dropping_or_backfilling_nn_is_rejected(conn, client):
    month, target = _nn_yesterday(conn, client)
    candidate = _plan(client, month)["candidates"][0]
    current = get_current_version_id(conn, SITE, month)
    without_nn = [a for a in candidate if a["assignment_id"] != target.assignment_id]
    assert _accept(client, month, without_nn).status_code >= 400
    worked = [dict(a, state="PLANNED", operational_code=None) if a["assignment_id"] == target.assignment_id else a
              for a in candidate]
    assert _accept(client, month, worked).status_code >= 400
    assert get_current_version_id(conn, SITE, month) == current


# --- R2: saved, fully fixed N/N/N -> Przelicz -> accept ---------------------

MARCH = date(2027, 3, 1)


def _manual_nnn(conn, client, month: date, first: int):
    """One deliberate manual correction writes the N/N/N of E1 on
    first..first+2 (real path: LAW Deviation + T058 freeze of the corrected
    targets, so the whole trio is fixed). first % 5 == 1 keeps the own D
    days of E1 clear."""
    demands, assignments = _rotation(month)
    _save(conn, month, demands, assignments, effective_from=month - timedelta(days=5))
    by_key = {(a.start_datetime.day, a.start_datetime.hour): a for a in assignments}
    ups = []
    for day in (first, first + 1, first + 2):
        a = replace(by_key[day, 18], employee_id="E1")
        ups.append(_assignment_in({**a.__dict__, "start_datetime": a.start_datetime.isoformat(),
                                   "end_datetime": a.end_datetime.isoformat(), "role": a.role.value, "state": a.state.value}))
    resp = client.post(_month_url(month, "/manual-correction"), json={"upsert_assignments": ups, "note": "świadomie"})
    assert resp.status_code == 200, resp.text
    assert "NIGHT-STREAK-01" in {d["source_reference"] for d in resp.json()["deviations"]}
    snap = get_schedule_snapshot(conn, get_current_version_id(conn, SITE, month))
    trio = [a for a in snap.assignments if a.employee_id == "E1" and a.start_datetime.hour == 18
            and first <= a.start_datetime.day <= first + 2]
    assert len(trio) == 3 and all(a.frozen for a in trio)
    return trio


def test_r2_frozen_manual_nnn_replan_and_accept_keeps_law_deviation(conn, client):
    """Live current month (Przelicz only exists once a grafik has started)."""
    today = date.today()
    month = today.replace(day=1)
    first = next((d for d in range(today.day + 2, _days_in(month) - 2) if d % 5 == 1), None)
    if first is None:
        pytest.skip("needs a free N/N/N window at least two days ahead in the current month")
    trio = _manual_nnn(conn, client, month, first)
    result = _plan(client, month)
    assert result["status"] == "FEASIBLE", (result["status"], result.get("error_message"))
    candidate = result["candidates"][0]
    assert {a.assignment_id for a in trio} <= {a["assignment_id"] for a in candidate}
    e1 = _n_days(candidate, "E1", month)
    assert date(month.year, month.month, first - 1) not in e1 and date(month.year, month.month, first + 3) not in e1
    assert _accept(client, month, candidate).status_code == 204
    child = get_schedule_snapshot(conn, get_current_version_id(conn, SITE, month))
    law = [d for d in child.deviations if d.source_reference == "NIGHT-STREAK-01"]
    assert law and all(d.category == DeviationCategory.LAW and not d.acknowledged for d in law)


@pytest.mark.parametrize("fact_state", ["frozen", "started", "realized"])
def test_r2_fully_fixed_nnn_variants_classified_preserved(conn, client, fact_state):
    """frozen / already started (cutover) / REALIZED: the same N/N/N window
    is a preserved fact for the shared classifier, never a new decision,
    and the solver plans the rest instead of going INFEASIBLE."""
    overrides = {(ShiftKind.N, 13): "E1", (ShiftKind.N, 14): "E1"}
    demands, assignments = _rotation(MARCH, overrides=overrides)
    trio = [a for a in assignments if a.employee_id == "E1" and a.start_datetime.hour == 18 and a.start_datetime.day in (12, 13, 14)]
    ids = {a.assignment_id for a in trio}
    if fact_state == "frozen":
        assignments = [replace(a, frozen=True) if a.assignment_id in ids else a for a in assignments]
    if fact_state == "realized":
        assignments = [replace(a, state=AssignmentState.REALIZED) if a.assignment_id in ids else a for a in assignments]
    _save(conn, MARCH, demands, assignments)
    state, _ = assemble_planning_state(conn, site_id=SITE, month=MARCH)
    if fact_state == "started":
        state = replace(state, cutover_at=datetime(2027, 3, 15, 5))  # N14 started, D15 (06:00) not yet
    report = validate(state, list(state.existing_assignments))
    streak = [d for d in report.violation_details if d.rule == "NIGHT-STREAK-01"]
    assert streak and all(is_preserved_violation(state, d, list(state.existing_assignments)) for d in streak)
    result = plan(state)
    assert result.status == "FEASIBLE", (result.status, result.error_message)
    assert ids <= {a.assignment_id for a in result.candidates[0]}
    if fact_state != "started":
        # the same window with one movable night is not a preserved fact
        movable = replace(state, existing_assignments=tuple(
            replace(a, frozen=False, state=AssignmentState.PLANNED) if a.assignment_id == trio[2].assignment_id else a
            for a in state.existing_assignments))
        assert not all(is_preserved_violation(movable, d, list(movable.existing_assignments)) for d in streak)


# --- R3: new proposals still obey NIGHT-STREAK-01 at both month edges --------

def _n_dates(candidate, employee_id):
    return {a.start_datetime.date() for a in candidate if a.employee_id == employee_id and a.role == AssignmentRole.PRIMARY
            and a.state != AssignmentState.CANCELLED and a.start_datetime.hour == 18}


@pytest.mark.parametrize("month", [MARCH, date(2027, 12, 1)])
def test_r3_two_fixed_nights_across_month_end_block_a_new_third(conn, client, month):
    """E1: frozen N on the last day + an accepted next-month N on day 1; a
    movable N of E1 on last-1 must be moved away (window last-1, last, 1st)."""
    last = _days_in(month)
    nxt = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    overrides = {(ShiftKind.N, last): "E1", (ShiftKind.N, last - 1): "E1"}
    demands, assignments = _rotation(month, overrides=overrides, frozen={(ShiftKind.N, last): True})
    _save(conn, month, demands, assignments)
    nd = _demand(ShiftKind.N, nxt, "VN")
    _calendar(conn, nxt)
    schedule_lifecycle.create_schedule_version(
        conn, version_id="VN", site_id=SITE, month=nxt, parent_version_id=None, created_at=datetime(2026, 1, 1, 8),
        created_by=COORD, applied_rule_version_ids=[], shift_demands=[nd], assignments=[_assignment(nd, "E1")],
        deviations=[], effective_from=nxt,
    )
    state, _ = assemble_planning_state(conn, site_id=SITE, month=month)
    result = plan(state)
    assert result.status == "FEASIBLE", (result.status, result.error_message)
    for candidate in result.candidates:
        n = _n_dates(candidate, "E1")
        assert date(month.year, month.month, last) in n
        assert date(month.year, month.month, last - 1) not in n


def test_r3_fixed_trio_gives_no_licence_for_a_fourth_night(conn, client):
    overrides = {(ShiftKind.N, 13): "E1", (ShiftKind.N, 14): "E1", (ShiftKind.N, 15): "E1", (ShiftKind.N, 11): "E1"}
    frozen = {(ShiftKind.N, 12): True, (ShiftKind.N, 13): True, (ShiftKind.N, 14): True}
    demands, assignments = _rotation(MARCH, overrides=overrides, frozen=frozen)
    _save(conn, MARCH, demands, assignments)
    state, _ = assemble_planning_state(conn, site_id=SITE, month=MARCH)
    result = plan(state)
    assert result.status == "FEASIBLE", (result.status, result.error_message)
    for candidate in result.candidates:
        n = _n_dates(candidate, "E1")
        assert {date(2027, 3, 12), date(2027, 3, 13), date(2027, 3, 14)} <= n
        assert date(2027, 3, 15) not in n and date(2027, 3, 11) not in n


# --- R4/R5: narrow negatives of the shared classifier -----------------------

def _nn_state(conn, client):
    month, target = _nn_yesterday(conn, client)
    state, _ = assemble_planning_state(conn, site_id=SITE, month=month)
    state = replace(state, cutover_at=datetime.now())
    candidate = list(state.existing_assignments)
    return state, candidate, target


def _gap(demand_id):
    return ViolationDetail("COVERAGE-01", (), f"COVERAGE-01: demand {demand_id} gap", demand_ids=(demand_id,))


def test_r4_nn_shortage_is_preserved_only_for_its_own_exact_gap(conn, client):
    state, candidate, target = _nn_state(conn, client)
    detail = _gap(target.covers_demand_id)
    assert is_preserved_violation(state, detail, candidate)
    # another demand's gap is never explained by this NN
    other = next(d for d in state.shift_demands if d.demand_id != target.covers_demand_id)
    assert not is_preserved_violation(state, _gap(other.demand_id), candidate)
    # NN not yet started relative to cutover -> not a historical fact
    early = replace(state, cutover_at=target.start_datetime - timedelta(hours=1))
    assert not is_preserved_violation(early, detail, candidate)
    # NN dropped from / altered in the candidate -> no exception
    assert not is_preserved_violation(state, detail, [a for a in candidate if a.assignment_id != target.assignment_id])
    altered = [replace(a, employee_id="E5") if a.assignment_id == target.assignment_id else a for a in candidate]
    assert not is_preserved_violation(state, detail, altered)


def test_r4_plain_cancelled_excess_and_multi_person_partial_are_not_preserved(conn, client):
    state, candidate, target = _nn_state(conn, client)
    detail = _gap(target.covers_demand_id)
    plain = [replace(a, operational_code=None) if a.assignment_id == target.assignment_id else a for a in candidate]
    plain_state = replace(state, existing_assignments=tuple(plain))
    assert not is_preserved_violation(plain_state, detail, plain)
    # excess: an extra working PRIMARY on the NN demand
    extra = replace(target, assignment_id="A-EXTRA", employee_id="E5", state=AssignmentState.PLANNED, operational_code=None)
    assert not is_preserved_violation(state, detail, candidate + [extra, replace(extra, assignment_id="A-EXTRA2", employee_id="E4")])
    # required 2, one NN: the second missing person is not explained
    two = tuple(replace(d, required_primary_count=2) if d.demand_id == target.covers_demand_id else d for d in state.shift_demands)
    assert not is_preserved_violation(replace(state, shift_demands=two), detail, candidate)


def test_r5_preserved_plus_new_violation_still_gates(conn, client):
    state, candidate, target = _nn_state(conn, client)
    nn_gap = _gap(target.covers_demand_id)
    movable = next(a for a in candidate if a.start_datetime > datetime.now() and a.role == AssignmentRole.PRIMARY)
    new_rest = ViolationDetail("REST-01", (movable.assignment_id,), "REST-01: new")
    assert gating_hard_pass(state, SimpleNamespace(hard_pass=False, violation_details=[nn_gap]), candidate)
    assert not gating_hard_pass(state, SimpleNamespace(hard_pass=False, violation_details=[nn_gap, new_rest]), candidate)
    assert not gating_hard_pass(state, SimpleNamespace(hard_pass=False, violation_details=[]), candidate)
    assert not is_preserved_violation(state, ViolationDetail("ASSIGN-04", (target.assignment_id,), "x"), candidate)


@pytest.mark.parametrize("month", [MARCH, date(2027, 12, 1)])
def test_r3_validator_names_night_trio_crossing_month_end(conn, client, month):
    """3A: NIGHT-STREAK-01 windows start up to month_end (context to
    month_end+2), so a trio (last-1, last, next 1st) is named in THIS month
    with its in-month ids -- not only as the generic third-service rule."""
    last = _days_in(month)
    nxt = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    overrides = {(ShiftKind.N, last): "E1", (ShiftKind.N, last - 1): "E1"}
    demands, assignments = _rotation(month, overrides=overrides)
    _save(conn, month, demands, assignments)
    nd = _demand(ShiftKind.N, nxt, "VN")
    _calendar(conn, nxt)
    schedule_lifecycle.create_schedule_version(
        conn, version_id="VN", site_id=SITE, month=nxt, parent_version_id=None, created_at=datetime(2026, 1, 1, 8),
        created_by=COORD, applied_rule_version_ids=[], shift_demands=[nd], assignments=[_assignment(nd, "E1")],
        deviations=[], effective_from=nxt,
    )
    state, _ = assemble_planning_state(conn, site_id=SITE, month=month)
    streak = [d for d in validate(state, list(state.existing_assignments)).violation_details if d.rule == "NIGHT-STREAK-01"]
    in_month = {a.assignment_id for a in assignments if a.employee_id == "E1" and a.start_datetime.day in (last - 1, last)
                and a.start_datetime.hour == 18}
    assert any(set(d.assignment_ids) == in_month for d in streak)
