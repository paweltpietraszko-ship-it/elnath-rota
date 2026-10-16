from dataclasses import replace
from datetime import date, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import pytest
from ortools.sat.python import cp_model
from tests import test_preserved_facts_replan as setup
from rota.planning.preserved_violations import is_preserved_violation
from rota.planning.constraints import add_max_two_consecutive_night_constraints, _fixed_part
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot
from rota.domain import AssignmentState

conn = setup.conn
client = setup.client

@pytest.mark.parametrize('gap_minutes,expected', [(0, True), (1, False), (-1, False)])
def test_partial_multi_person_gap(conn, client, gap_minutes, expected):
    state, candidate, target = setup._nn_state(conn, client)
    demands = tuple(replace(d, required_primary_count=2) if d.demand_id == target.covers_demand_id else d for d in state.shift_demands)
    middle = target.start_datetime + timedelta(hours=6)
    first = replace(target, assignment_id='AUDIT-A', employee_id='E4', state=AssignmentState.PLANNED, operational_code=None, end_datetime=middle)
    second = replace(first, assignment_id='AUDIT-B', employee_id='E5', start_datetime=middle + timedelta(minutes=gap_minutes), end_datetime=target.end_datetime)
    assert is_preserved_violation(replace(state, shift_demands=demands), setup._gap(target.covers_demand_id), candidate + [first, second]) is expected

def test_two_real_replans_preserve_nn(conn, client):
    month, target = setup._nn_yesterday(conn, client)
    original_id = get_current_version_id(conn, setup.SITE, month)
    original = get_schedule_snapshot(conn, original_id)
    old_nn = next(a for a in original.assignments if a.assignment_id == target.assignment_id)
    for _ in range(2):
        response = setup._plan(client, month)
        assert response['status'] == 'FEASIBLE', response
        assert setup._accept(client, month, response['candidates'][0]).status_code == 204
        child = get_schedule_snapshot(conn, get_current_version_id(conn, setup.SITE, month))
        nn = next(a for a in child.assignments if a.assignment_id == target.assignment_id)
        assert replace(nn, schedule_version_id=old_nn.schedule_version_id) == old_nn
        assert any(d.source_reference == 'COVERAGE-01' and d.affected_assignment_or_employee == target.covers_demand_id for d in child.deviations)
    assert get_schedule_snapshot(conn, original_id) == original

@pytest.mark.parametrize('mixed', [False, True])
def test_fixed_nights_and_new_fourth(mixed):
    model = cp_model.CpModel()
    terms = {}
    for day in range(10, 13):
        term = model.new_bool_var(f'optional{day}') + 1 if mixed else 1
        assert _fixed_part(term) == 1
        if mixed:
            # Existing fixed night occupies this date; optional slot unchosen.
            model.add(term == 1)
        terms[date(2027, 3, day)] = (0, term, term, f'N{day}', term)
    fourth = model.new_bool_var('fourth')
    terms[date(2027, 3, 13)] = (0, fourth, fourth, 'N13', fourth)
    assumptions = add_max_two_consecutive_night_constraints(model, {'E1': terms}, date(2027, 3, 1))
    for literal, _ in assumptions.values():
        model.add(literal == 1)
    solver = cp_model.CpSolver()
    assert solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL)
    assert solver.value(fourth) == 0
    model.add(fourth == 1)
    assert solver.solve(model) == cp_model.INFEASIBLE
